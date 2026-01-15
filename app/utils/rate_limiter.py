"""File-based rate limiter with automatic cleanup.

This module provides a thread-safe, file-based rate limiting system
to prevent spam and abuse across users, PRs, and repositories.
"""

import asyncio
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimitExceeded(Exception):
    """Raised when a rate limit is exceeded."""

    def __init__(self, limit_type: str, limit: int, window: str):
        """
        Initialize rate limit exception.

        Args:
            limit_type: Type of limit exceeded (User, PR, Repository)
            limit: Numeric limit value
            window: Time window description (hour, total, day)
        """
        self.limit_type = limit_type
        self.limit = limit
        self.window = window
        message = f"{limit_type} rate limit exceeded: {limit} per {window}"
        super().__init__(message)


class RateLimiter:
    """
    File-based rate limiter with automatic cleanup.

    Enforces three types of rate limits:
    - Per user: 5 commands per hour
    - Per PR: 10 commands total
    - Per repository: 50 commands per day

    Example:
        ```python
        limiter = RateLimiter()

        try:
            await limiter.check_and_record(
                user="octocat",
                repo="owner/repo",
                pr_number=123,
                command="fix-security-issues"
            )
        except RateLimitExceeded as e:
            print(f"Rate limit exceeded: {e}")
        ```
    """

    def __init__(self, data_file: Optional[Path] = None):
        """
        Initialize rate limiter.

        Args:
            data_file: Path to rate limits JSON file (defaults to data/rate_limits.json)
        """
        if data_file is None:
            data_file = Path("data/rate_limits.json")

        self.data_file = data_file
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

        # Ensure file exists
        if not self.data_file.exists():
            self._initialize_file()

        # Thread lock for file operations
        self._lock = threading.Lock()

        # Rate limit configurations
        self.USER_LIMIT = 5  # commands per hour
        self.PR_LIMIT = 10  # commands per PR (total)
        self.REPO_LIMIT = 50  # commands per day

        # Time windows
        self.USER_WINDOW = timedelta(hours=1)
        self.CLEANUP_INTERVAL = timedelta(hours=1)

        logger.info(
            f"Rate limiter initialized",
            extra={
                "extra_fields": {
                    "data_file": str(self.data_file),
                    "user_limit": self.USER_LIMIT,
                    "pr_limit": self.PR_LIMIT,
                    "repo_limit": self.REPO_LIMIT,
                }
            },
        )

    @staticmethod
    def _parse_datetime(dt_str: str) -> datetime:
        """
        Parse ISO format datetime string and ensure it's timezone-aware.

        Args:
            dt_str: ISO format datetime string

        Returns:
            Timezone-aware datetime in UTC
        """
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            # If naive, treat as UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _initialize_file(self) -> None:
        """Initialize rate limits file with default structure."""
        initial_data = {
            "version": "1.0",
            "last_cleanup": datetime.now(timezone.utc).isoformat(),
            "limits": {"per_user": {}, "per_pr": {}, "per_repo": {}},
        }

        with open(self.data_file, "w") as f:
            json.dump(initial_data, f, indent=2)

        logger.info(f"Initialized rate limits file: {self.data_file}")

    async def check_and_record(
        self, user: str, repo: str, pr_number: int, command: str
    ) -> None:
        """
        Check rate limits and record command if within limits.

        This is the main entry point for rate limiting. It checks all three
        limit types and raises RateLimitExceeded if any limit is hit.

        Args:
            user: GitHub username
            repo: Repository name (owner/repo)
            pr_number: Pull request number
            command: Command name

        Raises:
            RateLimitExceeded: If any limit is exceeded

        Example:
            ```python
            await limiter.check_and_record(
                user="octocat",
                repo="owner/repo",
                pr_number=123,
                command="fix-security-issues"
            )
            ```
        """
        # Use asyncio lock for async operations
        with self._lock:
            data = self._load_data()

            # Check user limit
            user_count = self._count_user_commands(data, user)
            if user_count >= self.USER_LIMIT:
                logger.warning(
                    f"User rate limit exceeded",
                    extra={
                        "extra_fields": {
                            "user": user,
                            "count": user_count,
                            "limit": self.USER_LIMIT,
                        }
                    },
                )
                raise RateLimitExceeded("User", self.USER_LIMIT, "hour")

            # Check PR limit
            pr_key = f"{repo}#{pr_number}"
            pr_count = self._count_pr_commands(data, pr_key)
            if pr_count >= self.PR_LIMIT:
                logger.warning(
                    f"PR rate limit exceeded",
                    extra={
                        "extra_fields": {
                            "pr": pr_key,
                            "count": pr_count,
                            "limit": self.PR_LIMIT,
                        }
                    },
                )
                raise RateLimitExceeded("PR", self.PR_LIMIT, "total")

            # Check repo limit
            repo_count = self._count_repo_commands(data, repo)
            if repo_count >= self.REPO_LIMIT:
                logger.warning(
                    f"Repository rate limit exceeded",
                    extra={
                        "extra_fields": {
                            "repo": repo,
                            "count": repo_count,
                            "limit": self.REPO_LIMIT,
                        }
                    },
                )
                raise RateLimitExceeded("Repository", self.REPO_LIMIT, "day")

            # All checks passed - record command
            self._record_command(data, user, repo, pr_number, command)

            # Cleanup if needed
            if self._should_cleanup(data):
                self._cleanup_old_entries(data)

            # Save updated data
            self._save_data(data)

            logger.info(
                f"Command recorded",
                extra={
                    "extra_fields": {
                        "user": user,
                        "repo": repo,
                        "pr_number": pr_number,
                        "command": command,
                        "user_count": user_count + 1,
                        "pr_count": pr_count + 1,
                        "repo_count": repo_count + 1,
                    }
                },
            )

    def _load_data(self) -> Dict[str, Any]:
        """
        Load rate limit data from JSON file.

        Returns:
            Rate limit data dictionary
        """
        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)

            # Validate structure
            if "limits" not in data:
                logger.warning("Invalid data structure, reinitializing")
                self._initialize_file()
                return self._load_data()

            return data

        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading rate limit data: {e}", exc_info=True)
            self._initialize_file()
            return self._load_data()

    def _save_data(self, data: Dict[str, Any]) -> None:
        """
        Save rate limit data to JSON file atomically.

        Args:
            data: Rate limit data to save
        """
        try:
            # Write to temporary file first (atomic operation)
            temp_file = self.data_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            # Rename (atomic on most filesystems)
            temp_file.replace(self.data_file)

        except Exception as e:
            logger.error(f"Error saving rate limit data: {e}", exc_info=True)

    def _count_user_commands(self, data: Dict[str, Any], user: str) -> int:
        """
        Count user commands within the time window.

        Args:
            data: Rate limit data
            user: GitHub username

        Returns:
            Number of commands in the last hour
        """
        now = datetime.now(timezone.utc)
        cutoff = now - self.USER_WINDOW

        user_data = data["limits"]["per_user"].get(user, {})
        commands = user_data.get("commands", [])

        # Count commands after cutoff
        count = sum(
            1
            for cmd in commands
            if self._parse_datetime(cmd["timestamp"]) > cutoff
        )

        return count

    def _count_pr_commands(self, data: Dict[str, Any], pr_key: str) -> int:
        """
        Count total commands for a PR.

        Args:
            data: Rate limit data
            pr_key: PR key (owner/repo#number)

        Returns:
            Total number of commands for this PR
        """
        pr_data = data["limits"]["per_pr"].get(pr_key, {})
        return pr_data.get("total_count", 0)

    def _count_repo_commands(self, data: Dict[str, Any], repo: str) -> int:
        """
        Count repository commands today.

        Args:
            data: Rate limit data
            repo: Repository name (owner/repo)

        Returns:
            Number of commands today
        """
        today = datetime.now(timezone.utc).date().isoformat()
        repo_data = data["limits"]["per_repo"].get(repo, {})

        # Reset if different day
        if repo_data.get("date") != today:
            return 0

        return repo_data.get("count_today", 0)

    def _record_command(
        self,
        data: Dict[str, Any],
        user: str,
        repo: str,
        pr_number: int,
        command: str,
    ) -> None:
        """
        Record a command execution.

        Args:
            data: Rate limit data
            user: GitHub username
            repo: Repository name
            pr_number: PR number
            command: Command name
        """
        now = datetime.now(timezone.utc).isoformat()

        # Record for user
        if user not in data["limits"]["per_user"]:
            data["limits"]["per_user"][user] = {"commands": []}

        data["limits"]["per_user"][user]["commands"].append(
            {"command": command, "timestamp": now}
        )

        # Record for PR
        pr_key = f"{repo}#{pr_number}"
        if pr_key not in data["limits"]["per_pr"]:
            data["limits"]["per_pr"][pr_key] = {"commands": [], "total_count": 0}

        data["limits"]["per_pr"][pr_key]["commands"].append(
            {"command": command, "timestamp": now, "user": user}
        )
        data["limits"]["per_pr"][pr_key]["total_count"] += 1

        # Record for repo
        today = datetime.now(timezone.utc).date().isoformat()
        if repo not in data["limits"]["per_repo"]:
            data["limits"]["per_repo"][repo] = {
                "commands": [],
                "count_today": 0,
                "date": today,
            }

        repo_data = data["limits"]["per_repo"][repo]

        # Reset if new day
        if repo_data.get("date") != today:
            repo_data["commands"] = []
            repo_data["count_today"] = 0
            repo_data["date"] = today

        repo_data["commands"].append({"command": command, "timestamp": now})
        repo_data["count_today"] += 1

    def _should_cleanup(self, data: Dict[str, Any]) -> bool:
        """
        Check if cleanup should run.

        Args:
            data: Rate limit data

        Returns:
            True if cleanup should run
        """
        last_cleanup = self._parse_datetime(data["last_cleanup"])
        return datetime.now(timezone.utc) - last_cleanup > self.CLEANUP_INTERVAL

    def _cleanup_old_entries(self, data: Dict[str, Any]) -> None:
        """
        Remove old entries beyond rate limit windows.

        Args:
            data: Rate limit data
        """
        now = datetime.now(timezone.utc)
        user_cutoff = now - self.USER_WINDOW

        # Cleanup user data
        for user, user_data in list(data["limits"]["per_user"].items()):
            commands = user_data.get("commands", [])
            filtered = [
                cmd
                for cmd in commands
                if self._parse_datetime(cmd["timestamp"]) > user_cutoff
            ]

            if filtered:
                data["limits"]["per_user"][user]["commands"] = filtered
            else:
                # Remove user entirely if no recent commands
                del data["limits"]["per_user"][user]

        # Cleanup repo data (keep only today)
        today = datetime.now(timezone.utc).date().isoformat()
        for repo, repo_data in list(data["limits"]["per_repo"].items()):
            if repo_data.get("date") != today:
                del data["limits"]["per_repo"][repo]

        # Update cleanup timestamp
        data["last_cleanup"] = now.isoformat()

        logger.info(
            "Rate limit data cleanup completed",
            extra={"extra_fields": {"timestamp": now.isoformat()}},
        )

    async def get_limits_status(
        self, user: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """
        Get current rate limit status for a user/repo/PR.

        Args:
            user: GitHub username
            repo: Repository name
            pr_number: PR number

        Returns:
            Dictionary with current counts and limits
        """
        with self._lock:
            data = self._load_data()

            pr_key = f"{repo}#{pr_number}"

            return {
                "user": {
                    "count": self._count_user_commands(data, user),
                    "limit": self.USER_LIMIT,
                    "window": "hour",
                    "remaining": self.USER_LIMIT - self._count_user_commands(data, user),
                },
                "pr": {
                    "count": self._count_pr_commands(data, pr_key),
                    "limit": self.PR_LIMIT,
                    "window": "total",
                    "remaining": self.PR_LIMIT - self._count_pr_commands(data, pr_key),
                },
                "repo": {
                    "count": self._count_repo_commands(data, repo),
                    "limit": self.REPO_LIMIT,
                    "window": "day",
                    "remaining": self.REPO_LIMIT
                    - self._count_repo_commands(data, repo),
                },
            }


# Global instance
_rate_limiter_instance: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.

    Returns:
        Global RateLimiter instance
    """
    global _rate_limiter_instance

    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter()

    return _rate_limiter_instance
