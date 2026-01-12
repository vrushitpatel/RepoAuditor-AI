"""Command parser for extracting and parsing slash commands from PR comments."""

import re
import shlex
from typing import List, Optional, Tuple, Union

from app.commands.registry import get_registry
from app.models.commands import Command, CommandError


class CommandParser:
    """Parser for extracting commands from GitHub PR comment text."""

    # Regex to match slash commands at the start of a line
    COMMAND_PATTERN = re.compile(r"^\s*/([a-zA-Z0-9_-]+)(?:\s+(.+))?$", re.MULTILINE)

    def __init__(self) -> None:
        """Initialize the command parser."""
        self.registry = get_registry()

    def parse_comment(
        self,
        comment_body: str,
        pr_number: int,
        repo_name: str,
        user: str,
    ) -> Union[Command, CommandError]:
        """Parse a command from a GitHub comment.

        Args:
            comment_body: The text of the comment
            pr_number: The PR number
            repo_name: The repository name (owner/repo)
            user: The GitHub username who made the comment

        Returns:
            Command object if parsing succeeds, CommandError if parsing fails
        """
        # Extract command from comment
        match = self._find_command(comment_body)
        if not match:
            return CommandError(
                message="No valid command found in comment",
                raw_text=comment_body,
                suggestion="Commands must start with / (e.g., /help, /explain)",
            )

        command_name = match.group(1)
        args_text = match.group(2) or ""

        # Validate command exists
        if not self.registry.exists(command_name):
            return CommandError(
                message=f"Unknown command: /{command_name}",
                raw_text=comment_body,
                suggestion=f"Use /help to see available commands. Did you mean: {self._suggest_command(command_name)}?",
            )

        # Parse arguments
        try:
            args, kwargs = self._parse_arguments(args_text)
        except ValueError as e:
            return CommandError(
                message=f"Failed to parse arguments: {str(e)}",
                raw_text=comment_body,
                suggestion="Check for unmatched quotes or invalid syntax",
            )

        # Validate argument count
        validation_error = self.registry.validate_args(command_name, args)
        if validation_error:
            cmd_def = self.registry.get(command_name)
            return CommandError(
                message=validation_error,
                raw_text=comment_body,
                suggestion=f"Usage: {cmd_def.usage}" if cmd_def else "",
            )

        # Create command object
        return Command(
            command=command_name,
            args=args,
            kwargs=kwargs,
            raw_text=comment_body,
            user=user,
            pr_number=pr_number,
            repo_name=repo_name,
        )

    def _find_command(self, text: str) -> Optional[re.Match]:
        """Find the first command in the text.

        Args:
            text: Text to search for commands

        Returns:
            Match object if command found, None otherwise
        """
        return self.COMMAND_PATTERN.search(text)

    def _parse_arguments(self, args_text: str) -> Tuple[List[str], dict]:
        """Parse arguments from argument text.

        Handles:
        - Space-separated arguments
        - Quoted arguments (single or double quotes)
        - Key=value pairs for kwargs

        Args:
            args_text: The argument text to parse

        Returns:
            Tuple of (positional args list, kwargs dict)

        Raises:
            ValueError: If argument parsing fails
        """
        if not args_text.strip():
            return [], {}

        # Use shlex to handle quoted strings properly
        try:
            tokens = shlex.split(args_text)
        except ValueError as e:
            raise ValueError(f"Invalid argument syntax: {e}") from e

        args = []
        kwargs = {}

        for token in tokens:
            # Check if it's a key=value pair
            if "=" in token:
                key, value = token.split("=", 1)
                kwargs[key.strip()] = value.strip()
            else:
                args.append(token)

        return args, kwargs

    def _suggest_command(self, invalid_command: str) -> str:
        """Suggest a similar command based on the invalid command.

        Uses simple string similarity to find close matches.

        Args:
            invalid_command: The invalid command name

        Returns:
            Suggested command name
        """
        commands = [cmd.name for cmd in self.registry.list_commands()]
        if not commands:
            return "help"

        # Simple similarity: find command with longest common prefix
        best_match = max(
            commands,
            key=lambda cmd: self._common_prefix_length(invalid_command, cmd),
        )

        # If no good match, suggest help
        if self._common_prefix_length(invalid_command, best_match) < 2:
            return "help"

        return best_match

    def _common_prefix_length(self, s1: str, s2: str) -> int:
        """Calculate length of common prefix between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Length of common prefix
        """
        min_len = min(len(s1), len(s2))
        for i in range(min_len):
            if s1[i].lower() != s2[i].lower():
                return i
        return min_len

    def extract_all_commands(self, text: str) -> List[str]:
        """Extract all command names from text.

        Args:
            text: Text to search for commands

        Returns:
            List of command names found (without /)
        """
        matches = self.COMMAND_PATTERN.findall(text)
        return [match[0] for match in matches]

    def is_command(self, text: str) -> bool:
        """Check if text contains a valid command.

        Args:
            text: Text to check

        Returns:
            True if text contains a command, False otherwise
        """
        match = self._find_command(text)
        if not match:
            return False
        command_name = match.group(1)
        return self.registry.exists(command_name)


# Convenience function for quick parsing
def parse_command(
    comment_body: str,
    pr_number: int,
    repo_name: str,
    user: str,
) -> Union[Command, CommandError]:
    """Parse a command from a comment (convenience function).

    Args:
        comment_body: The text of the comment
        pr_number: The PR number
        repo_name: The repository name (owner/repo)
        user: The GitHub username who made the comment

    Returns:
        Command object if parsing succeeds, CommandError if parsing fails
    """
    parser = CommandParser()
    return parser.parse_comment(comment_body, pr_number, repo_name, user)
