"""Finding cache for storing code review findings temporarily.

This module provides a file-based cache for storing findings from code reviews,
allowing users to reference them later with /jira command.

Storage: JSON files in data/finding_cache/
TTL: 48 hours
No database dependencies - uses file system
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

from app.models.review_findings import Finding
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class CachedFinding:
    """Finding with additional metadata for caching."""

    finding_id: int
    finding_data: Dict[str, Any]  # Serialized Finding
    created_at: str  # ISO format timestamp


@dataclass
class FindingCache:
    """Cache entry for a PR's findings."""

    repo_name: str
    pr_number: int
    findings: List[CachedFinding]
    created_at: str
    expires_at: str


class FindingCacheManager:
    """
    Manager for caching code review findings.

    Uses file-based storage with automatic cleanup.
    No database dependencies.
    """

    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 48):
        """
        Initialize finding cache manager.

        Args:
            cache_dir: Directory for cache files (default: data/finding_cache)
            ttl_hours: Time-to-live in hours (default: 48)
        """
        if cache_dir is None:
            # Default to data/finding_cache relative to project root
            project_root = Path(__file__).parent.parent.parent
            cache_dir = project_root / "data" / "finding_cache"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

        logger.info(f"Initialized finding cache at {self.cache_dir}")

    def _get_cache_path(self, repo_name: str, pr_number: int) -> Path:
        """
        Get cache file path for a specific PR.

        Args:
            repo_name: Repository name (e.g., "owner/repo")
            pr_number: PR number

        Returns:
            Path to cache file
        """
        # Sanitize repo name for filename
        safe_repo = repo_name.replace("/", "_")
        filename = f"{safe_repo}_pr_{pr_number}.json"
        return self.cache_dir / filename

    def save_findings(
        self,
        repo_name: str,
        pr_number: int,
        findings: List[Finding],
    ) -> None:
        """
        Save findings to cache.

        Args:
            repo_name: Repository name (e.g., "owner/repo")
            pr_number: PR number
            findings: List of findings to cache
        """
        logger.info(f"Caching {len(findings)} findings for {repo_name} PR #{pr_number}")

        now = datetime.now(timezone.utc)
        expires_at = now + self.ttl

        # Convert findings to cached format with IDs
        cached_findings = []
        for idx, finding in enumerate(findings, start=1):
            cached = CachedFinding(
                finding_id=idx,
                finding_data=finding.model_dump(),  # Serialize Pydantic model
                created_at=now.isoformat(),
            )
            cached_findings.append(cached)

        # Create cache entry
        cache_entry = FindingCache(
            repo_name=repo_name,
            pr_number=pr_number,
            findings=cached_findings,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        )

        # Write to file
        cache_path = self._get_cache_path(repo_name, pr_number)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(asdict(cache_entry), f, indent=2)

            logger.info(f"Saved findings to {cache_path}")

        except Exception as e:
            logger.error(f"Failed to save findings cache: {e}", exc_info=True)

    def get_findings(
        self,
        repo_name: str,
        pr_number: int,
    ) -> Optional[List[Finding]]:
        """
        Get cached findings for a PR.

        Args:
            repo_name: Repository name
            pr_number: PR number

        Returns:
            List of findings with IDs, or None if not found/expired
        """
        cache_path = self._get_cache_path(repo_name, pr_number)

        if not cache_path.exists():
            logger.debug(f"No cache found for {repo_name} PR #{pr_number}")
            return None

        try:
            # Read cache file
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cache_entry = FindingCache(**data)

            # Check expiration
            expires_at = datetime.fromisoformat(cache_entry.expires_at)
            now = datetime.now(timezone.utc)

            if now > expires_at:
                logger.info(f"Cache expired for {repo_name} PR #{pr_number}")
                # Delete expired cache
                cache_path.unlink()
                return None

            # Convert back to Finding objects
            findings = []
            for cached in cache_entry.findings:
                # cached might be a dict if loaded from JSON
                if isinstance(cached, dict):
                    finding_data = cached["finding_data"]
                else:
                    finding_data = cached.finding_data

                finding = Finding(**finding_data)
                findings.append(finding)

            logger.info(f"Loaded {len(findings)} findings from cache")
            return findings

        except Exception as e:
            logger.error(f"Failed to load findings cache: {e}", exc_info=True)
            return None

    def get_finding_by_id(
        self,
        repo_name: str,
        pr_number: int,
        finding_id: int,
    ) -> Optional[Finding]:
        """
        Get a specific finding by ID.

        Args:
            repo_name: Repository name
            pr_number: PR number
            finding_id: Finding ID (1-indexed)

        Returns:
            Finding object, or None if not found
        """
        findings = self.get_findings(repo_name, pr_number)

        if not findings:
            return None

        # Finding IDs are 1-indexed
        if finding_id < 1 or finding_id > len(findings):
            logger.warning(f"Finding ID {finding_id} out of range (1-{len(findings)})")
            return None

        return findings[finding_id - 1]

    def get_latest_critical_finding(
        self,
        repo_name: str,
        pr_number: int,
    ) -> Optional[tuple[int, Finding]]:
        """
        Get the most recent CRITICAL or HIGH severity finding.

        Args:
            repo_name: Repository name
            pr_number: PR number

        Returns:
            Tuple of (finding_id, finding), or None if not found
        """
        findings = self.get_findings(repo_name, pr_number)

        if not findings:
            return None

        # Find first CRITICAL or HIGH finding (they're ordered by severity)
        for idx, finding in enumerate(findings, start=1):
            if finding.severity in ["CRITICAL", "HIGH"]:
                logger.info(f"Found latest critical finding: #{idx} ({finding.severity})")
                return (idx, finding)

        logger.info("No CRITICAL or HIGH findings found")
        return None

    def cleanup_expired(self) -> int:
        """
        Clean up expired cache files.

        Returns:
            Number of files deleted
        """
        logger.info("Cleaning up expired finding caches")

        deleted_count = 0
        now = datetime.now(timezone.utc)

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                cache_entry = FindingCache(**data)
                expires_at = datetime.fromisoformat(cache_entry.expires_at)

                if now > expires_at:
                    cache_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted expired cache: {cache_file.name}")

            except Exception as e:
                logger.error(f"Error processing cache file {cache_file}: {e}")

        logger.info(f"Cleaned up {deleted_count} expired cache files")
        return deleted_count

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_files = len(cache_files)

        total_findings = 0
        expired_files = 0
        now = datetime.now(timezone.utc)

        for cache_file in cache_files:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                cache_entry = FindingCache(**data)
                total_findings += len(cache_entry.findings)

                expires_at = datetime.fromisoformat(cache_entry.expires_at)
                if now > expires_at:
                    expired_files += 1

            except Exception:
                pass

        return {
            "total_cache_files": total_files,
            "active_cache_files": total_files - expired_files,
            "expired_cache_files": expired_files,
            "total_cached_findings": total_findings,
            "cache_directory": str(self.cache_dir),
        }


# Global cache instance
_cache_instance: Optional[FindingCacheManager] = None


def get_finding_cache() -> FindingCacheManager:
    """
    Get the global finding cache instance.

    Returns:
        FindingCacheManager instance
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = FindingCacheManager()

    return _cache_instance
