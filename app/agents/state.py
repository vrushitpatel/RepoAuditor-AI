"""Shared state definitions for LangGraph agents."""

from typing import List, Optional, TypedDict

from app.models.webhook_events import FileChange, PullRequestEvent, ReviewComment


class CodeReviewState(TypedDict):
    """State for code review workflow."""

    # Input data
    event: PullRequestEvent
    installation_id: int
    repo_full_name: str
    pr_number: int
    pr_title: str
    pr_description: Optional[str]
    commit_sha: str

    # Files to review
    files: List[FileChange]
    files_analyzed: bool

    # AI analysis
    analysis: Optional[str]
    summary: Optional[str]

    # Review comments
    comments: List[ReviewComment]

    # Status tracking
    review_posted: bool
    jira_issue_created: bool
    error: Optional[str]
