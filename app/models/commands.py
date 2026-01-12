"""Command models for parsing slash commands from GitHub PR comments."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Command:
    """Represents a parsed command from a PR comment.

    Attributes:
        command: The command name (e.g., "explain", "test")
        args: Positional arguments passed to the command
        kwargs: Key-value arguments passed to the command
        raw_text: Original comment text
        user: GitHub username who issued the command
        pr_number: Pull request number
        repo_name: Repository name in format "owner/repo"
    """

    command: str
    args: List[str] = field(default_factory=list)
    kwargs: Dict[str, str] = field(default_factory=dict)
    raw_text: str = ""
    user: str = ""
    pr_number: int = 0
    repo_name: str = ""

    def has_arg(self, index: int) -> bool:
        """Check if positional argument exists at given index."""
        return index < len(self.args)

    def get_arg(self, index: int, default: Optional[str] = None) -> Optional[str]:
        """Get positional argument at index, or default if not found."""
        return self.args[index] if self.has_arg(index) else default

    def get_kwarg(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get keyword argument by key, or default if not found."""
        return self.kwargs.get(key, default)

    def __str__(self) -> str:
        """String representation of the command."""
        args_str = " ".join(self.args)
        kwargs_str = " ".join(f"{k}={v}" for k, v in self.kwargs.items())
        parts = [f"/{self.command}", args_str, kwargs_str]
        return " ".join(filter(None, parts))


@dataclass
class CommandError:
    """Represents an error during command parsing or validation.

    Attributes:
        message: Error message
        raw_text: Original comment text that caused the error
        suggestion: Optional suggestion for fixing the error
    """

    message: str
    raw_text: str = ""
    suggestion: str = ""

    def __str__(self) -> str:
        """String representation of the error."""
        parts = [f"Error: {self.message}"]
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return "\n".join(parts)
