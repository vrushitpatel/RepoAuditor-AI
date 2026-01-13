"""Global command router instance.

This module provides a singleton router instance that is used throughout
the application. Agents are registered here at startup.
"""

from app.commands.router import CommandRouter
from app.agents.help_agent import HelpAgent
from app.agents.explainer_agent_wrapper import ExplainerAgentWrapper
from app.agents.review_agent_wrapper import ReviewAgentWrapper
from app.agents.cicd_agent_wrapper import CICDAgentWrapper
from app.integrations.github_client import GitHubClient
from app.integrations.gemini_client import GeminiClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Global router instance
_router: CommandRouter = None


def get_router() -> CommandRouter:
    """
    Get the global command router instance.

    Initializes the router on first call.

    Returns:
        CommandRouter instance
    """
    global _router

    if _router is None:
        _router = initialize_router()

    return _router


def initialize_router() -> CommandRouter:
    """
    Initialize and configure the command router.

    Registers all available agents with their command patterns.

    Returns:
        Configured CommandRouter instance
    """
    logger.info("Initializing command router")

    # Create GitHub and Gemini clients
    github_client = GitHubClient()
    gemini_client = GeminiClient(use_flash=True)

    # Create router
    router = CommandRouter(
        github_client=github_client,
        gemini_client=gemini_client,
    )

    # Register agents
    # Note: Agents are registered with command name (without /)
    # and optional regex pattern for matching

    # Help command
    router.register(
        command="help",
        agent=HelpAgent(),
        pattern=r"^/?help\b",
    )

    # Explain command (with variations)
    router.register(
        command="explain",
        agent=ExplainerAgentWrapper(),
        pattern=r"^/?explain\b",
    )

    # Review command
    router.register(
        command="review",
        agent=ReviewAgentWrapper(),
        pattern=r"^/?review\b",
    )

    # CI/CD generation command
    router.register(
        command="generate-ci",
        agent=CICDAgentWrapper(),
        pattern=r"^/?generate-ci\b",
    )

    logger.info(
        f"Router initialized with {len(router.list_commands())} commands",
        extra={
            "extra_fields": {
                "commands": list(router.list_commands().keys()),
            }
        },
    )

    return router


def reset_router() -> None:
    """Reset the global router instance (useful for testing)."""
    global _router
    _router = None
    logger.info("Router reset")
