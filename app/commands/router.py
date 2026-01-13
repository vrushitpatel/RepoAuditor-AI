"""Command router for directing commands to appropriate agents."""

import re
from datetime import datetime
from typing import Dict, Optional, Pattern

from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from app.integrations.github_client import GitHubClient
from app.integrations.gemini_client import GeminiClient
from app.models.webhook_events import IssueCommentEvent
from app.utils.logger import setup_logger
from app.utils.helpers import format_duration, format_cost, format_tokens

logger = setup_logger(__name__)


class CommandRouter:
    """
    Routes commands to appropriate agents.

    The router:
    1. Parses commands from comments
    2. Matches commands to registered agents
    3. Creates agent context
    4. Executes agent
    5. Posts response to GitHub
    """

    def __init__(
        self,
        github_client: GitHubClient,
        gemini_client: Optional[GeminiClient] = None,
    ):
        """
        Initialize command router.

        Args:
            github_client: GitHub client for API operations
            gemini_client: Optional Gemini client for AI operations
        """
        self.github_client = github_client
        self.gemini_client = gemini_client
        self.agents: Dict[str, BaseAgent] = {}
        self.patterns: Dict[Pattern, str] = {}  # Pattern -> command name

        logger.info("Command router initialized")

    def register(
        self,
        command: str,
        agent: BaseAgent,
        pattern: Optional[str] = None,
    ) -> None:
        """
        Register an agent for a command.

        Args:
            command: Command name (e.g., "explain")
            agent: Agent instance to handle this command
            pattern: Optional regex pattern to match (default: ^command)

        Example:
            >>> router.register("explain", ExplainerAgent())
            >>> router.register("test", TestAnalystAgent(), pattern=r"^test\b")
        """
        # Normalize command (lowercase, no slash)
        command = command.lower().lstrip("/")

        # Store agent
        self.agents[command] = agent

        # Create and store pattern
        if pattern is None:
            # Default pattern: matches /command or command at start
            pattern = rf"^/?{re.escape(command)}\b"

        compiled_pattern = re.compile(pattern, re.IGNORECASE)
        self.patterns[compiled_pattern] = command

        logger.info(
            f"Registered agent: {agent.name} for command '/{command}'",
            extra={
                "extra_fields": {
                    "command": command,
                    "agent": agent.name,
                    "pattern": pattern,
                }
            },
        )

    def match_command(self, text: str) -> Optional[tuple[str, str]]:
        """
        Match text against registered command patterns.

        Args:
            text: Comment text to check

        Returns:
            Tuple of (command_name, command_args) if matched, None otherwise

        Example:
            >>> router.match_command("/explain app/main.py")
            ("explain", "app/main.py")
        """
        text = text.strip()

        for pattern, command_name in self.patterns.items():
            match = pattern.match(text)
            if match:
                # Extract command and remaining text as args
                command_part = match.group(0)
                remaining = text[len(command_part):].strip()

                logger.debug(
                    f"Matched command: {command_name}",
                    extra={
                        "extra_fields": {
                            "command": command_name,
                            "text": text[:100],
                            "args": remaining[:100] if remaining else None,
                        }
                    },
                )

                return command_name, remaining

        return None

    async def route(self, event: IssueCommentEvent) -> bool:
        """
        Route a comment event to the appropriate agent.

        This is the main entry point for processing commands.

        Args:
            event: Issue comment event from GitHub

        Returns:
            True if command was handled successfully, False otherwise
        """
        comment_body = event.comment.body.strip()

        logger.info(
            f"Routing command from comment",
            extra={
                "extra_fields": {
                    "repo": event.repository.full_name,
                    "pr_number": event.issue.number,
                    "commenter": event.comment.user.login,
                    "comment_preview": comment_body[:100],
                }
            },
        )

        # Match command
        result = self.match_command(comment_body)
        if result is None:
            logger.warning(
                f"No matching command found",
                extra={
                    "extra_fields": {
                        "comment": comment_body[:100],
                        "registered_commands": list(self.agents.keys()),
                    }
                },
            )
            await self._post_unknown_command_error(event, comment_body)
            return False

        command_name, command_args = result

        # Get agent
        agent = self.agents.get(command_name)
        if agent is None:
            logger.error(f"Agent not found for command: {command_name}")
            await self._post_internal_error(event, command_name)
            return False

        # Execute agent
        return await self._execute_agent(event, agent, command_name, command_args)

    async def _execute_agent(
        self,
        event: IssueCommentEvent,
        agent: BaseAgent,
        command_name: str,
        command_args: str,
    ) -> bool:
        """
        Execute an agent with proper context and error handling.

        Args:
            event: Issue comment event
            agent: Agent to execute
            command_name: Normalized command name
            command_args: Command arguments

        Returns:
            True if execution succeeded, False otherwise
        """
        start_time = datetime.utcnow()

        try:
            # Fetch PR details for context
            pr_details = self.github_client.get_pr_details(
                repo_name=event.repository.full_name,
                pr_number=event.issue.number,
                installation_id=event.installation.id,
            )

            # Create agent context
            context = AgentContext(
                github_client=self.github_client,
                repo_name=event.repository.full_name,
                pr_number=event.issue.number,
                installation_id=event.installation.id,
                pr_title=pr_details.get("title", ""),
                pr_description=pr_details.get("body", ""),
                pr_author=pr_details.get("author", ""),
                head_sha=pr_details.get("head_sha", ""),
                base_sha=pr_details.get("base_sha", ""),
                command=command_name,
                command_args=command_args,
                commenter=event.comment.user.login,
                comment_id=event.comment.id,
                gemini_client=self.gemini_client,
                metadata={},
            )

            logger.info(
                f"Executing agent: {agent.name}",
                extra={
                    "extra_fields": {
                        "agent": agent.name,
                        "command": command_name,
                        "repo": context.repo_name,
                        "pr_number": context.pr_number,
                    }
                },
            )

            # Execute agent
            response = await agent.handle(context)

            # Calculate duration
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            # Add metadata footer if AI was used
            final_message = self._add_metadata_footer(
                response.message,
                response.metadata,
                duration,
            )

            # Post response
            await self._post_response(event, final_message)

            logger.info(
                f"Agent execution completed",
                extra={
                    "extra_fields": {
                        "agent": agent.name,
                        "success": response.success,
                        "duration": duration,
                    }
                },
            )

            return response.success

        except Exception as e:
            logger.error(
                f"Agent execution failed: {e}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "agent": agent.name,
                        "command": command_name,
                        "error": str(e),
                    }
                },
            )

            # Post error message
            error_response = agent.create_error_response(e)
            await self._post_response(event, error_response.message)

            return False

    def _add_metadata_footer(
        self,
        message: str,
        metadata: Dict,
        duration: float,
    ) -> str:
        """
        Add metadata footer to response if applicable.

        Args:
            message: Response message
            metadata: Response metadata
            duration: Execution duration in seconds

        Returns:
            Message with metadata footer appended
        """
        # Check if message already has metadata section
        if "Generation Metadata" in message or "metadata" in message.lower():
            return message

        # Check if we have AI-related metadata
        has_ai_metadata = any(
            key in metadata
            for key in ["tokens_used", "cost_usd", "model_name"]
        )

        if not has_ai_metadata:
            # Just add simple footer
            return f"{message}\n\n---\n*Processing time: {format_duration(duration)}*"

        # Add full metadata footer
        model_name = metadata.get("model_name", "Unknown")
        tokens = metadata.get("tokens_used", 0)
        cost = metadata.get("cost_usd", 0.0)

        footer = f"""
---
<details>
<summary>📊 Generation Metadata</summary>

- **Model:** {model_name}
- **Tokens Used:** {format_tokens(tokens)}
- **Cost:** {format_cost(cost)}
- **Processing Time:** {format_duration(duration)}

</details>
"""
        return f"{message}\n{footer}"

    async def _post_response(self, event: IssueCommentEvent, message: str) -> None:
        """
        Post response message to GitHub PR.

        Args:
            event: Issue comment event
            message: Message to post
        """
        self.github_client.post_pr_comment(
            repo_name=event.repository.full_name,
            pr_number=event.issue.number,
            body=message,
            installation_id=event.installation.id,
        )

    async def _post_unknown_command_error(
        self,
        event: IssueCommentEvent,
        comment_text: str,
    ) -> None:
        """Post error message for unknown command."""
        available_commands = ", ".join(f"`/{cmd}`" for cmd in sorted(self.agents.keys()))

        message = f"""## ❓ Unknown Command

I didn't recognize that command. Here's what I can help with:

**Available commands:** {available_commands}

**What you tried:**
```
{comment_text[:200]}
```

**Get help:** Use `/help` to see detailed information about all commands.

**Tip:** Commands must start with `/` (e.g., `/explain`, `/review`)
"""
        await self._post_response(event, message)

    async def _post_internal_error(
        self,
        event: IssueCommentEvent,
        command_name: str,
    ) -> None:
        """Post error message for internal routing error."""
        message = f"""## ⚠️ Internal Error

I recognized the command `/{command_name}`, but encountered an internal error while trying to process it.

This is likely a configuration issue. Please:
1. Try the command again
2. If it persists, report this issue to the repository maintainers

**Command:** `/{command_name}`
**Error:** Agent not properly registered
"""
        await self._post_response(event, message)

    def list_commands(self) -> Dict[str, str]:
        """
        List all registered commands.

        Returns:
            Dictionary of {command_name: agent_description}
        """
        return {
            cmd: agent.description
            for cmd, agent in self.agents.items()
        }

    def get_agent(self, command: str) -> Optional[BaseAgent]:
        """
        Get agent for a command.

        Args:
            command: Command name (with or without /)

        Returns:
            Agent instance if found, None otherwise
        """
        command = command.lower().lstrip("/")
        return self.agents.get(command)
