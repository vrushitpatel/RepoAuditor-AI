"""Command handler for /jira-all - Create ONE JIRA ticket with ALL findings.

This is a simplified version that creates a single comprehensive ticket
instead of one ticket per finding.
"""

from typing import List
from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from app.integrations.jira_client import JIRAClient, JIRAError
from app.models.jira_models import JIRAConfig
from app.models.review_findings import Finding
from app.utils.finding_cache import get_finding_cache
from app.utils.logger import setup_logger
from app.config import get_settings

logger = setup_logger(__name__)


class JiraAllHandler(BaseAgent):
    """Handler for /jira-all command - Create ONE ticket with ALL findings."""

    def __init__(self):
        """Initialize handler."""
        super().__init__(
            name="JiraAllHandler",
            description="Create a single JIRA ticket with all code review findings",
        )
        self.settings = get_settings()
        self.finding_cache = get_finding_cache()

    async def handle(self, context: AgentContext) -> AgentResponse:
        """
        Handle /jira-all command.

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
            # Get ALL findings from cache
            findings = self.finding_cache.get_findings(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
            )

            if not findings:
                return AgentResponse(
                    success=False,
                    message="## ❌ No Findings Found\n\nNo cached findings. Please run `/review` first.",
                )

            # Get project key from config
            project_key = self.settings.jira.default_project_key
            if not project_key:
                return AgentResponse(
                    success=False,
                    message="## ❌ No JIRA Project Configured\n\nPlease set `JIRA_DEFAULT_PROJECT_KEY` in `.env` file.",
                )

            logger.info(f"Creating combined JIRA ticket for {len(findings)} findings in project {project_key}")

            # Create combined JIRA ticket
            issue = await self._create_combined_ticket(
                context=context,
                findings=findings,
                project_key=project_key,
            )

            if issue:
                message = self._format_success_message(
                    issue_key=issue.key,
                    issue_url=issue.url,
                    findings_count=len(findings),
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

        except JIRAError as e:
            logger.error(f"JIRA error: {e.message}")
            return AgentResponse(
                success=False,
                message=f"❌ **JIRA Error**\n\n{e.message}\n\nPlease check your configuration.",
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)

    async def _create_combined_ticket(
        self,
        context: AgentContext,
        findings: List[Finding],
        project_key: str,
    ):
        """
        Create a single JIRA ticket with all findings combined.

        Args:
            context: Agent context
            findings: List of all findings
            project_key: JIRA project key

        Returns:
            JIRA issue or None
        """
        # Group findings by severity
        critical = [f for f in findings if f.severity == "CRITICAL"]
        high = [f for f in findings if f.severity == "HIGH"]
        medium = [f for f in findings if f.severity == "MEDIUM"]
        low = [f for f in findings if f.severity == "LOW"]
        info = [f for f in findings if f.severity == "INFO"]

        # Determine overall priority (highest severity found)
        if critical:
            priority = "Highest"
            priority_emoji = "🔴"
        elif high:
            priority = "High"
            priority_emoji = "🟠"
        elif medium:
            priority = "Medium"
            priority_emoji = "🟡"
        else:
            priority = "Low"
            priority_emoji = "🟢"

        # Build title
        total_count = len(findings)
        critical_count = len(critical)
        high_count = len(high)

        if critical_count > 0:
            title = f"Code Review: {critical_count} Critical Issue{'s' if critical_count != 1 else ''} Found"
        elif high_count > 0:
            title = f"Code Review: {high_count} High Severity Issue{'s' if high_count != 1 else ''} Found"
        else:
            title = f"Code Review: {total_count} Issue{'s' if total_count != 1 else ''} Found"

        # Build description (plain text)
        pr_url = f"https://github.com/{context.repo_name}/pull/{context.pr_number}"

        description = f"""{priority_emoji} Code Review Findings
{"=" * 60}

Pull Request: {context.repo_name} #{context.pr_number}
{pr_url}

Summary: Found {total_count} issue(s) during automated code review:
- {len(critical)} CRITICAL
- {len(high)} HIGH
- {len(medium)} MEDIUM
- {len(low)} LOW
- {len(info)} INFO

{"-" * 60}

"""

        # Add findings by severity
        if critical:
            description += "CRITICAL Issues:\n\n"
            for idx, finding in enumerate(critical, 1):
                description += self._format_finding(idx, finding)
                description += "\n"

        if high:
            description += "HIGH Severity Issues:\n\n"
            for idx, finding in enumerate(high, 1):
                description += self._format_finding(idx, finding)
                description += "\n"

        if medium:
            description += "MEDIUM Severity Issues:\n\n"
            for idx, finding in enumerate(medium, 1):
                description += self._format_finding(idx, finding)
                description += "\n"

        if low:
            description += "LOW Severity Issues:\n\n"
            for idx, finding in enumerate(low, 1):
                description += self._format_finding(idx, finding)
                description += "\n"

        description += f"""{"-" * 60}

Next Steps:
1. Review each finding above
2. Fix critical and high severity issues first
3. Consider addressing medium/low issues
4. Re-run code review after fixes

Generated by RepoAuditor AI
"""

        # Create JIRA config
        jira_config = JIRAConfig(
            base_url=self.settings.jira.base_url,
            email=self.settings.jira.email,
            api_token=self.settings.jira.api_token,
        )

        # Create ticket
        async with JIRAClient(jira_config) as jira:
            issue = await jira.create_issue(
                project_key=project_key,
                summary=title,
                description=description,
                issue_type="Bug",
                priority=priority,
                labels=["code-review", "security", "automated"],
            )
            return issue

    def _format_finding(self, index: int, finding: Finding) -> str:
        """Format a single finding for JIRA description (plain text)."""
        output = f"{index}. {finding.title}\n\n"
        output += f"{finding.description}\n\n"

        if finding.location:
            output += f"Location: {finding.location.file_path}"
            if finding.location.line_start:
                output += f":{finding.location.line_start}"
            output += "\n\n"

            if finding.location.code_snippet:
                output += f"Code:\n{finding.location.code_snippet}\n\n"

        if finding.recommendation:
            output += f"Fix: {finding.recommendation}\n\n"

        return output

    def _format_success_message(
        self,
        issue_key: str,
        issue_url: str,
        findings_count: int,
    ) -> str:
        """Format success message."""
        return f"""## ✅ JIRA Ticket Created

**Ticket:** [{issue_key}]({issue_url})

**Findings Included:** {findings_count} issue(s)

### 🎟️ What Was Created

Created a single comprehensive JIRA ticket containing all {findings_count} findings from the code review.

Click the link above to view the ticket in JIRA.

🤖 Powered by RepoAuditor AI
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
   JIRA_DEFAULT_PROJECT_KEY=VCR
   ```

2. Generate an API token at:
   https://id.atlassian.com/manage-profile/security/api-tokens

3. Restart the server

For detailed setup instructions, see `docs/JIRA_Integration.md`.
"""
