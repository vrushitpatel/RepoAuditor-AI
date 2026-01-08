"""Helper functions for common tasks across the application.

This module provides reusable utility functions for cache key generation,
formatting, and common operations used throughout the workflow.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from app.utils.cache import get_cache
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# Cache Key Generation
# ============================================================================

def generate_pr_cache_key(repo_name: str, pr_number: int, action: str = "review") -> str:
    """
    Generate a cache key for PR-related operations.

    Args:
        repo_name: Full repository name (owner/repo)
        pr_number: Pull request number
        action: Type of action (review, explain, etc.)

    Returns:
        Cache key string

    Example:
        >>> generate_pr_cache_key("owner/repo", 123, "review")
        'pr:review:owner/repo:123'
    """
    return f"pr:{action}:{repo_name}:{pr_number}"


def generate_commit_cache_key(repo_name: str, commit_sha: str) -> str:
    """
    Generate a cache key for commit-related operations.

    Args:
        repo_name: Full repository name (owner/repo)
        commit_sha: Commit SHA hash

    Returns:
        Cache key string

    Example:
        >>> generate_commit_cache_key("owner/repo", "abc123")
        'commit:owner/repo:abc123'
    """
    return f"commit:{repo_name}:{commit_sha}"


# ============================================================================
# Review Prevention / Duplicate Detection
# ============================================================================

def should_skip_review(
    repo_name: str,
    pr_number: int,
    ttl_seconds: int = 300
) -> tuple[bool, Optional[str]]:
    """
    Check if a PR review should be skipped due to recent review.

    Checks the cache to see if this PR was reviewed recently (within TTL).
    This prevents duplicate reviews triggered by multiple webhook events.

    Args:
        repo_name: Full repository name (owner/repo)
        pr_number: Pull request number
        ttl_seconds: Time window in seconds to consider (default: 300 = 5 minutes)

    Returns:
        Tuple of (should_skip: bool, reason: Optional[str])

    Example:
        >>> should_skip, reason = should_skip_review("owner/repo", 123)
        >>> if should_skip:
        >>>     print(f"Skipping: {reason}")
    """
    cache = get_cache()
    cache_key = generate_pr_cache_key(repo_name, pr_number, "review")

    cached_value = cache.get(cache_key)

    if cached_value:
        logger.info(
            f"Skipping duplicate review for {repo_name}#{pr_number}",
            extra={
                "extra_fields": {
                    "repo_name": repo_name,
                    "pr_number": pr_number,
                    "cached_at": cached_value.get("reviewed_at"),
                    "ttl_seconds": ttl_seconds,
                }
            },
        )
        return True, f"PR was reviewed recently at {cached_value.get('reviewed_at')}"

    return False, None


def mark_pr_as_reviewed(
    repo_name: str,
    pr_number: int,
    ttl_seconds: int = 300,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Mark a PR as reviewed in the cache to prevent duplicates.

    Args:
        repo_name: Full repository name (owner/repo)
        pr_number: Pull request number
        ttl_seconds: Time to cache in seconds (default: 300 = 5 minutes)
        metadata: Optional metadata to store with the cache entry

    Example:
        >>> mark_pr_as_reviewed("owner/repo", 123, metadata={"cost": 0.05})
    """
    cache = get_cache()
    cache_key = generate_pr_cache_key(repo_name, pr_number, "review")

    cache_data = {
        "reviewed_at": datetime.utcnow().isoformat(),
        "repo_name": repo_name,
        "pr_number": pr_number,
    }

    if metadata:
        cache_data.update(metadata)

    cache.set(cache_key, cache_data, ttl_seconds=ttl_seconds)

    logger.debug(
        f"Marked PR {repo_name}#{pr_number} as reviewed",
        extra={
            "extra_fields": {
                "cache_key": cache_key,
                "ttl_seconds": ttl_seconds,
            }
        },
    )


# ============================================================================
# Formatting Helpers
# ============================================================================

def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string

    Example:
        >>> format_duration(125.5)
        '2m 5s'
        >>> format_duration(45.2)
        '45s'
        >>> format_duration(3665)
        '1h 1m 5s'
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def format_cost(cost_usd: float) -> str:
    """
    Format cost in USD to readable string.

    Args:
        cost_usd: Cost in USD

    Returns:
        Formatted cost string

    Example:
        >>> format_cost(0.0125)
        '$0.0125'
        >>> format_cost(1.5)
        '$1.50'
    """
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    elif cost_usd < 1:
        return f"${cost_usd:.3f}"
    else:
        return f"${cost_usd:.2f}"


def format_tokens(tokens: int) -> str:
    """
    Format token count to readable string with thousands separator.

    Args:
        tokens: Token count

    Returns:
        Formatted token string

    Example:
        >>> format_tokens(1234567)
        '1,234,567'
    """
    return f"{tokens:,}"


# ============================================================================
# Summary Generation
# ============================================================================

def generate_execution_summary(
    repo_name: str,
    pr_number: int,
    duration_seconds: float,
    findings_count: int,
    cost_usd: float,
    tokens: int,
    severity_counts: Optional[Dict[str, int]] = None,
    success: bool = True,
    error: Optional[str] = None
) -> str:
    """
    Generate a formatted execution summary for logging.

    Args:
        repo_name: Repository name
        pr_number: PR number
        duration_seconds: Execution duration
        findings_count: Number of findings
        cost_usd: Total cost in USD
        tokens: Total tokens used
        severity_counts: Counts by severity level
        success: Whether execution succeeded
        error: Error message if failed

    Returns:
        Formatted summary string

    Example:
        >>> summary = generate_execution_summary(
        ...     "owner/repo", 123, 45.5, 5, 0.025, 15000,
        ...     {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 2}
        ... )
    """
    status = "SUCCESS" if success else "FAILED"

    summary = f"""
Workflow Execution Summary
{'=' * 50}
Repository: {repo_name}
PR Number: #{pr_number}
Status: {status}
Duration: {format_duration(duration_seconds)}
"""

    if success:
        summary += f"""
Findings:
  Total: {findings_count}
"""
        if severity_counts:
            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    summary += f"  {severity}: {count}\n"

        summary += f"""
Cost & Usage:
  Cost: {format_cost(cost_usd)}
  Tokens: {format_tokens(tokens)}
"""
    else:
        summary += f"""
Error: {error or 'Unknown error'}
"""

    return summary


def validate_webhook_payload(payload: Dict[str, Any], event_type: str) -> tuple[bool, Optional[str]]:
    """
    Validate webhook payload has required fields.

    Args:
        payload: Webhook payload dictionary
        event_type: Type of GitHub event

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])

    Example:
        >>> valid, error = validate_webhook_payload(payload, "pull_request")
        >>> if not valid:
        >>>     print(f"Invalid payload: {error}")
    """
    # Common required fields
    if "repository" not in payload:
        return False, "Missing 'repository' field in payload"

    if "full_name" not in payload.get("repository", {}):
        return False, "Missing 'repository.full_name' field in payload"

    # Event-specific validation
    if event_type == "pull_request":
        if "pull_request" not in payload:
            return False, "Missing 'pull_request' field in payload"

        if "number" not in payload:
            return False, "Missing 'number' field in payload"

        if "installation" not in payload:
            return False, "Missing 'installation' field in payload"

    elif event_type in ["issue_comment", "pull_request_review_comment"]:
        if "comment" not in payload:
            return False, "Missing 'comment' field in payload"

    return True, None


# ============================================================================
# Error Handling Helpers
# ============================================================================

def extract_error_context(
    error: Exception,
    repo_name: Optional[str] = None,
    pr_number: Optional[int] = None
) -> Dict[str, Any]:
    """
    Extract context from an exception for logging.

    Args:
        error: Exception object
        repo_name: Optional repository name
        pr_number: Optional PR number

    Returns:
        Dictionary with error context

    Example:
        >>> try:
        >>>     raise ValueError("Something went wrong")
        >>> except Exception as e:
        >>>     context = extract_error_context(e, "owner/repo", 123)
        >>>     logger.error("Error occurred", extra={"extra_fields": context})
    """
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    if repo_name:
        context["repo_name"] = repo_name

    if pr_number:
        context["pr_number"] = pr_number

    # Add traceback info if available
    if hasattr(error, "__traceback__"):
        import traceback
        context["traceback"] = "".join(
            traceback.format_tb(error.__traceback__)[-3:]  # Last 3 frames
        )

    return context


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.

    Args:
        error: Exception object

    Returns:
        True if the error should be retried, False otherwise

    Example:
        >>> try:
        >>>     # API call
        >>>     pass
        >>> except Exception as e:
        >>>     if is_retryable_error(e):
        >>>         # Retry logic
        >>>         pass
    """
    # Network errors, timeouts, rate limits are retryable
    retryable_errors = [
        "TimeoutError",
        "ConnectionError",
        "HTTPStatusError",
        "RateLimitError",
        "ServiceUnavailable",
    ]

    error_type = type(error).__name__

    # Check error type
    if error_type in retryable_errors:
        return True

    # Check error message for rate limiting
    error_msg = str(error).lower()
    if any(keyword in error_msg for keyword in ["rate limit", "timeout", "connection", "503", "502", "504"]):
        return True

    return False
