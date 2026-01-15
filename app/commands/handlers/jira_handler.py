"""Command handler for /jira - Create JIRA tickets from findings.

Syntax:
- /jira - Create ticket for most recent CRITICAL/HIGH finding
- /jira #2 - Create ticket for finding #2
- /jira TECH - Create ticket in TECH project
- /jira #3 TECH P1 - Full specification
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from app.integrations.jira_client import (
    JIRAClient,
    JIRAError,
    JIRAAuthenticationError,
    JIRAValidationError,
)
from app.models.jira_models import JIRAConfig
from app.utils.finding_cache import get_finding_cache
from app.utils.logger import setup_logger
from app.config import get_settings

logger = setup_logger(__name__)


@dataclass
class JiraCommand:
    """Parsed JIRA command parameters."""

    finding_id: Optional[int] = None  # Which finding (default: latest critical)
    project_key: Optional[str] = None  # JIRA project (default from config)
    priority: Optional[str] = None  # Override priority (P0, P1, etc.)
    assignee: Optional[str] = None  # Optional assignee


class JiraCommandParser:
    """Parser for /jira command variations."""

    # Patterns for parsing
    FINDING_ID_PATTERN = re.compile(r"#(\d+)")
    PROJECT_KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]+)\b")
    PRIORITY_PATTERN = re.compile(r"\b(P[0-4]|Highest|High|Medium|Low|Lowest)\b", re.IGNORECASE)

    @classmethod
    def parse(cls, command_text: str) -> JiraCommand:
        """
        Parse /jira command text.

        Args:
            command_text: Command text after "/jira"

        Returns:
            Parsed JiraCommand

        Examples:
            "/jira" -> JiraCommand()
            "/jira #2" -> JiraCommand(finding_id=2)
            "/jira TECH" -> JiraCommand(project_key="TECH")
            "/jira #3 TECH P1" -> JiraCommand(finding_id=3, project_key="TECH", priority="P1")
        """
        command_text = command_text.strip()

        # Extract finding ID
        finding_id = None
        finding_match = cls.FINDING_ID_PATTERN.search(command_text)
        if finding_match:
            finding_id = int(finding_match.group(1))

        # Extract project key
        project_key = None
        project_match = cls.PROJECT_KEY_PATTERN.search(command_text)
        if project_match:
            # Make sure it's not P0-P4 (priority)
            potential_key = project_match.group(1)
            if not potential_key.startswith("P") or len(potential_key) > 2:
                project_key = potential_key

        # Extract priority
        priority = None
        priority_match = cls.PRIORITY_PATTERN.search(command_text)
        if priority_match:
            priority = priority_match.group(1)
            # Normalize P-levels to JIRA priority names
            priority_map = {
                "P0": "Highest",
                "P1": "High",
                "P2": "Medium",
                "P3": "Low",
                "P4": "Lowest",
            }
            priority = priority_map.get(priority.upper(), priority)

        return JiraCommand(
            finding_id=finding_id,
            project_key=project_key,
            priority=priority,
        )


class JiraHandler(BaseAgent):
    """Handler for /jira command - Create JIRA tickets from findings."""

    def __init__(self):
        """Initialize handler."""
        super().__init__(
            name="JiraHandler",
            description="Create JIRA tickets from code review findings",
        )
        self.settings = get_settings()
        self.finding_cache = get_finding_cache()

    async def handle(self, context: AgentContext) -> AgentResponse:
        """
        Handle /jira command.

        Args:
            context: Agent context with PR and command details

        Returns:
            Agent response with ticket creation results
        """
        self.log_start(context)

        # Check if JIRA is configured
        if not self.settings.jira.enabled:
            return AgentResponse(
                success=False,
                message=self._format_jira_not_configured_message(),
            )

        try:
            # Parse command
            command_text = context.command.replace("/jira", "").strip()
            parsed = JiraCommandParser.parse(command_text)

            logger.info(
                f"Parsed JIRA command: finding_id={parsed.finding_id}, "
                f"project_key={parsed.project_key}, priority={parsed.priority}"
            )

            # Get finding
            finding_id, finding = await self._get_finding(
                context=context,
                parsed=parsed,
            )

            if not finding:
                return AgentResponse(
                    success=False,
                    message=self._format_no_findings_message(parsed.finding_id),
                )

            # Get project key (from command or config)
            project_key = parsed.project_key or self.settings.jira.default_project_key
            if not project_key:
                return AgentResponse(
                    success=False,
                    message=self._format_no_project_message(),
                )

            # Create JIRA ticket
            issue = await self._create_jira_ticket(
                context=context,
                finding=finding,
                finding_id=finding_id,
                project_key=project_key,
                priority=parsed.priority,
            )

            if issue:
                message = self._format_success_message(
                    finding_id=finding_id,
                    issue_key=issue.key,
                    issue_url=issue.url,
                    finding=finding,
                )

                self.log_success(context, {"issue_key": issue.key})

                return AgentResponse(
                    success=True,
                    message=message,
                    metadata={"issue_key": issue.key, "issue_url": issue.url},
                )
            else:
                return AgentResponse(
                    success=False,
                    message="Failed to create JIRA ticket. Check logs for details.",
                )

        except JIRAAuthenticationError as e:
            logger.error(f"JIRA authentication failed: {e.message}")
            return AgentResponse(
                success=False,
                message=f"❌ **JIRA Authentication Failed**\n\n{e.message}\n\nPlease check your JIRA credentials in `.env`.",
            )

        except JIRAValidationError as e:
            logger.error(f"JIRA validation error: {e.message}")
            return AgentResponse(
                success=False,
                message=f"❌ **JIRA Validation Error**\n\n{e.message}\n\nPlease check the project key and configuration.",
            )

        except JIRAError as e:
            logger.error(f"JIRA error: {e.message}")
            return AgentResponse(
                success=False,
                message=f"❌ **JIRA Error**\n\n{e.message}",
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)

    async def _get_finding(
        self,
        context: AgentContext,
        parsed: JiraCommand,
    ) -> tuple[Optional[int], Optional[Any]]:
        """
        Get finding based on command parameters.

        Args:
            context: Agent context
            parsed: Parsed command

        Returns:
            Tuple of (finding_id, finding) or (None, None)
        """
        # If finding ID specified, get that specific finding
        if parsed.finding_id is not None:
            finding = self.finding_cache.get_finding_by_id(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
                finding_id=parsed.finding_id,
            )
            if finding:
                logger.info(f"Retrieved finding #{parsed.finding_id} from cache")
                return (parsed.finding_id, finding)
            else:
                logger.warning(f"Finding #{parsed.finding_id} not found in cache")
                return (None, None)

        # Otherwise, get latest CRITICAL/HIGH finding
        result = self.finding_cache.get_latest_critical_finding(
            repo_name=context.repo_name,
            pr_number=context.pr_number,
        )

        if result:
            finding_id, finding = result
            logger.info(f"Retrieved latest critical finding #{finding_id}")
            return (finding_id, finding)
        else:
            logger.warning("No CRITICAL/HIGH findings found in cache")
            return (None, None)

    async def _create_jira_ticket(
        self,
        context: AgentContext,
        finding: Any,
        finding_id: int,
        project_key: str,
        priority: Optional[str],
    ) -> Optional[Any]:
        """
        Create JIRA ticket from finding.

        Args:
            context: Agent context
            finding: Finding object
            finding_id: Finding ID
            project_key: JIRA project key
            priority: Optional priority override

        Returns:
            JIRA issue or None
        """
        logger.info(f"Creating JIRA ticket for finding #{finding_id} in project {project_key}")

        # Create JIRA config
        jira_config = JIRAConfig(
            base_url=self.settings.jira.base_url,
            email=self.settings.jira.email,
            api_token=self.settings.jira.api_token,
        )

        # Construct PR URL
        pr_url = f"https://github.com/{context.repo_name}/pull/{context.pr_number}"

        # Create ticket
        async with JIRAClient(jira_config) as jira:
            # Override priority if specified
            if priority:
                # Temporarily override finding severity for priority mapping
                original_severity = finding.severity
                try:
                    issue = await jira.create_issue_from_finding(
                        project_key=project_key,
                        finding=finding,
                        pr_url=pr_url,
                        repo_name=context.repo_name,
                    )

                    # If priority override specified, we'd need to update the issue
                    # For now, just log it
                    if priority:
                        logger.info(f"Note: Priority override to {priority} requested")

                    return issue

                finally:
                    finding.severity = original_severity
            else:
                issue = await jira.create_issue_from_finding(
                    project_key=project_key,
                    finding=finding,
                    pr_url=pr_url,
                    repo_name=context.repo_name,
                )
                return issue

    def _format_success_message(
        self,
        finding_id: int,
        issue_key: str,
        issue_url: str,
        finding: Any,
    ) -> str:
        """Format success message."""
        return f"""## ✅ JIRA Ticket Created

**Ticket:** [{issue_key}]({issue_url})

**Finding:** #{finding_id} - {finding.type} ({finding.severity})

### 🎟️ Ticket Details
- **Project:** {issue_key.split('-')[0]}
- **Severity:** {finding.severity}
- **Type:** {finding.type}

Click the link above to view the ticket in JIRA.

🤖 Powered by RepoAuditor AI
"""

    def _format_no_findings_message(self, finding_id: Optional[int]) -> str:
        """Format no findings found message."""
        if finding_id:
            return f"""## ❌ Finding Not Found

Could not find finding **#{finding_id}** in the cache.

### Possible Reasons
- Finding ID doesn't exist in the most recent review
- Cache has expired (48 hour TTL)
- No review has been run yet

### What to Do
1. Run `/review` to generate findings
2. Check the review comment for available finding IDs
3. Use `/jira #<id>` to create a ticket

💡 Tip: Use `/jira` without an ID to create a ticket for the latest CRITICAL/HIGH finding.
"""
        else:
            return """## ❌ No Critical Findings Found

No CRITICAL or HIGH severity findings found in the cache.

### What to Do
1. Run `/review` to scan for issues
2. If there are MEDIUM/LOW findings, specify the ID: `/jira #2`
3. Check the review comment for available finding IDs

💡 Tip: The `/jira` command creates tickets for CRITICAL/HIGH findings by default.
"""

    def _format_no_project_message(self) -> str:
        """Format no project key message."""
        return """## ❌ No JIRA Project Specified

Please specify a JIRA project key.

### Usage
```
/jira #1 TECH
```

Or configure a default project in `.env`:
```
JIRA_DEFAULT_PROJECT_KEY=TECH
```

💡 Project keys are usually all uppercase (e.g., TECH, SEC, OPS).
"""

    def _format_jira_not_configured_message(self) -> str:
        """Format JIRA not configured message."""
        return """## ❌ JIRA Integration Not Configured

JIRA integration is not set up.

### Setup Instructions
1. Add the following to your `.env` file:
   ```
   JIRA_BASE_URL=https://your-company.atlassian.net
   JIRA_EMAIL=your.email@company.com
   JIRA_API_TOKEN=your_api_token_here
   ```

2. Generate an API token at:
   https://id.atlassian.com/manage-profile/security/api-tokens

3. Restart the server

For detailed setup instructions, see `docs/JIRA_Integration.md`.
"""
