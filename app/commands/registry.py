"""Command registry for managing available slash commands."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CommandDefinition:
    """Definition of a command with its metadata.

    Attributes:
        name: Command name (without the /)
        description: Short description of what the command does
        usage: Usage example
        args_description: Description of expected arguments
        min_args: Minimum number of required arguments
        max_args: Maximum number of allowed arguments (None = unlimited)
    """

    name: str
    description: str
    usage: str
    args_description: str = ""
    min_args: int = 0
    max_args: Optional[int] = None


class CommandRegistry:
    """Registry of all available commands."""

    def __init__(self) -> None:
        """Initialize the command registry with default commands."""
        self._commands: Dict[str, CommandDefinition] = {}
        self._register_default_commands()

    def _register_default_commands(self) -> None:
        """Register the default set of commands."""
        self.register(
            CommandDefinition(
                name="explain",
                description="Explain a specific file or class/function in your codebase",
                usage="/explain app/main.py or /explain app/utils/cache.py:SimpleCache",
                args_description=(
                    "file_path - Path to the file to explain\n"
                    "Optional: file_path:ClassName or file_path:function_name for specific items"
                ),
                min_args=1,
                max_args=1,
            )
        )

        self.register(
            CommandDefinition(
                name="explain-diff",
                description="Explain the changes in this PR",
                usage="/explain-diff or /explain-diff app/main.py",
                args_description="Optional: file_path - Specific file to explain (default: all files)",
                min_args=0,
                max_args=1,
            )
        )

        self.register(
            CommandDefinition(
                name="test",
                description="Generate tests for the PR changes",
                usage="/test or /test pytest",
                args_description="Optional: framework - Testing framework to use (pytest, unittest)",
                min_args=0,
                max_args=1,
            )
        )

        self.register(
            CommandDefinition(
                name="generate-ci",
                description="Generate CI/CD workflow configuration",
                usage="/generate-ci or /generate-ci build or /generate-ci test",
                args_description=(
                    "Optional: type - CI/CD type to generate (build, test, deploy, all)"
                ),
                min_args=0,
                max_args=1,
            )
        )

        self.register(
            CommandDefinition(
                name="review",
                description="Trigger a full code review of the PR",
                usage="/review",
                args_description="No arguments required",
                min_args=0,
                max_args=0,
            )
        )

        self.register(
            CommandDefinition(
                name="help",
                description="Show available commands and their usage",
                usage="/help",
                args_description="No arguments required",
                min_args=0,
                max_args=0,
            )
        )

    def register(self, command_def: CommandDefinition) -> None:
        """Register a new command definition.

        Args:
            command_def: Command definition to register
        """
        self._commands[command_def.name] = command_def

    def get(self, command_name: str) -> Optional[CommandDefinition]:
        """Get command definition by name.

        Args:
            command_name: Name of the command (without /)

        Returns:
            CommandDefinition if found, None otherwise
        """
        return self._commands.get(command_name)

    def exists(self, command_name: str) -> bool:
        """Check if a command exists in the registry.

        Args:
            command_name: Name of the command (without /)

        Returns:
            True if command exists, False otherwise
        """
        return command_name in self._commands

    def list_commands(self) -> List[CommandDefinition]:
        """Get list of all registered commands.

        Returns:
            List of all command definitions
        """
        return list(self._commands.values())

    def get_help_text(self) -> str:
        """Generate help text for all commands.

        Returns:
            Formatted help text with all commands
        """
        lines = ["# Available Commands\n"]
        for cmd in sorted(self._commands.values(), key=lambda c: c.name):
            lines.append(f"## `/{cmd.name}`")
            lines.append(f"{cmd.description}\n")
            lines.append(f"**Usage:** `{cmd.usage}`")
            if cmd.args_description:
                lines.append(f"\n**Arguments:**\n{cmd.args_description}")
            lines.append("\n---\n")
        return "\n".join(lines)

    def validate_args(self, command_name: str, args: List[str]) -> Optional[str]:
        """Validate that command has correct number of arguments.

        Args:
            command_name: Name of the command
            args: List of arguments provided

        Returns:
            Error message if validation fails, None if valid
        """
        cmd_def = self.get(command_name)
        if not cmd_def:
            return f"Unknown command: {command_name}"

        num_args = len(args)

        if num_args < cmd_def.min_args:
            return (
                f"Command '{command_name}' requires at least {cmd_def.min_args} "
                f"argument(s), but got {num_args}"
            )

        if cmd_def.max_args is not None and num_args > cmd_def.max_args:
            return (
                f"Command '{command_name}' accepts at most {cmd_def.max_args} "
                f"argument(s), but got {num_args}"
            )

        return None


# Global registry instance
_registry = CommandRegistry()


def get_registry() -> CommandRegistry:
    """Get the global command registry instance.

    Returns:
        CommandRegistry instance
    """
    return _registry
