"""Base agent class for command handlers.

All agents must inherit from this base class and implement the handle() method.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.integrations.github_client import GitHubClient
from app.integrations.gemini_client import GeminiClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class AgentContext:
    """Context passed to agents for executing commands."""

    # GitHub context
    github_client: GitHubClient
    repo_name: str
    pr_number: int
    installation_id: int

    # PR details
    pr_title: str = ""
    pr_description: str = ""
    pr_author: str = ""
    head_sha: str = ""
    base_sha: str = ""

    # Command context
    command: str = ""
    command_args: str = ""
    commenter: str = ""
    comment_id: int = 0

    # Optional clients
    gemini_client: Optional[GeminiClient] = None

    # Additional metadata
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AgentResponse:
    """Response from an agent."""

    success: bool
    message: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class BaseAgent(ABC):
    """
    Abstract base class for all command agents.

    All agents must implement the handle() method which processes
    a command and returns a response.
    """

    def __init__(self, name: str, description: str):
        """
        Initialize base agent.

        Args:
            name: Agent name (e.g., "ExplainerAgent")
            description: Brief description of what the agent does
        """
        self.name = name
        self.description = description
        self.logger = setup_logger(f"{__name__}.{name}")

    @abstractmethod
    async def handle(self, context: AgentContext) -> AgentResponse:
        """
        Handle a command with the given context.

        Args:
            context: Agent context containing all necessary information

        Returns:
            AgentResponse with success status and message

        Raises:
            Exception: If command processing fails
        """
        pass

    def log_start(self, context: AgentContext) -> None:
        """Log agent execution start."""
        self.logger.info(
            f"{self.name} handling command for {context.repo_name}#{context.pr_number}",
            extra={
                "extra_fields": {
                    "agent": self.name,
                    "repo": context.repo_name,
                    "pr_number": context.pr_number,
                    "command": context.command,
                    "command_args": context.command_args,
                }
            },
        )

    def log_success(self, context: AgentContext, metadata: Dict[str, Any] = None) -> None:
        """Log successful command execution."""
        self.logger.info(
            f"{self.name} completed successfully",
            extra={
                "extra_fields": {
                    "agent": self.name,
                    "repo": context.repo_name,
                    "pr_number": context.pr_number,
                    **(metadata or {}),
                }
            },
        )

    def log_error(self, context: AgentContext, error: Exception) -> None:
        """Log command execution error."""
        self.logger.error(
            f"{self.name} failed: {error}",
            exc_info=True,
            extra={
                "extra_fields": {
                    "agent": self.name,
                    "repo": context.repo_name,
                    "pr_number": context.pr_number,
                    "error": str(error),
                }
            },
        )

    def create_error_response(self, error: Exception) -> AgentResponse:
        """
        Create a standardized error response.

        Args:
            error: Exception that occurred

        Returns:
            AgentResponse with error details
        """
        error_message = f"""## ❌ Command Failed

I encountered an error while processing your command:

```
{str(error)}
```

**What you can try:**
- Check that the command syntax is correct
- Use `/help` to see available commands
- Try the command again

If the issue persists, this might be a bug. Please report it to the repository maintainers.
"""
        return AgentResponse(
            success=False,
            message=error_message,
            metadata={"error": str(error), "error_type": type(error).__name__},
        )


class SimpleAgent(BaseAgent):
    """
    Simple agent for commands that don't need async processing.

    Useful for simple commands like /help that just return static content.
    """

    def __init__(self, name: str, description: str, response_template: str):
        """
        Initialize simple agent.

        Args:
            name: Agent name
            description: Agent description
            response_template: Template for response message
        """
        super().__init__(name, description)
        self.response_template = response_template

    async def handle(self, context: AgentContext) -> AgentResponse:
        """
        Handle command by returning template response.

        Args:
            context: Agent context

        Returns:
            AgentResponse with template message
        """
        self.log_start(context)

        try:
            # Format template with context
            message = self.response_template.format(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
                command=context.command,
                command_args=context.command_args,
            )

            self.log_success(context)

            return AgentResponse(success=True, message=message)

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)
