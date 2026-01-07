"""Pydantic models for GitHub webhook events."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    """GitHub user model."""

    login: str
    id: int
    type: str


class Repository(BaseModel):
    """GitHub repository model."""

    id: int
    name: str
    full_name: str
    private: bool
    owner: User
    html_url: str
    default_branch: str = Field(default="main")


class PullRequest(BaseModel):
    """GitHub pull request model."""

    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    user: User
    head: Dict[str, Any]
    base: Dict[str, Any]
    html_url: str
    diff_url: str
    commits: int
    additions: int
    deletions: int
    changed_files: int


class Installation(BaseModel):
    """GitHub App installation model."""

    id: int
    account: User


class PullRequestEvent(BaseModel):
    """GitHub pull request webhook event."""

    action: str
    number: int
    pull_request: PullRequest
    repository: Repository
    installation: Installation
    sender: User


class FileChange(BaseModel):
    """Model for a file change in a pull request."""

    filename: str
    status: str  # added, modified, removed, renamed
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    contents_url: str
    raw_url: str


class ReviewComment(BaseModel):
    """Model for a code review comment."""

    path: str
    position: Optional[int] = None
    body: str
    line: Optional[int] = None
    side: str = Field(default="RIGHT")  # RIGHT or LEFT
    start_line: Optional[int] = None
    start_side: Optional[str] = None


class ReviewResult(BaseModel):
    """Model for AI review results."""

    summary: str
    comments: List[ReviewComment]
    severity: str = Field(default="info")  # info, warning, error
    issues_found: int = 0


class Comment(BaseModel):
    """GitHub comment model."""

    id: int
    body: str
    user: User
    created_at: str
    updated_at: str
    html_url: str


class Issue(BaseModel):
    """GitHub issue model (also used for PRs in issue_comment events)."""

    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    user: User
    html_url: str
    pull_request: Optional[Dict[str, Any]] = None  # Present if this is a PR


class IssueCommentEvent(BaseModel):
    """GitHub issue_comment webhook event.

    Triggered when a comment is created on an issue or PR.
    """

    action: str  # created, edited, deleted
    issue: Issue
    comment: Comment
    repository: Repository
    installation: Installation
    sender: User


class PullRequestReviewComment(BaseModel):
    """GitHub pull request review comment model."""

    id: int
    body: str
    user: User
    path: str
    position: Optional[int] = None
    original_position: Optional[int] = None
    commit_id: str
    original_commit_id: str
    diff_hunk: str
    line: Optional[int] = None
    original_line: Optional[int] = None
    created_at: str
    updated_at: str
    html_url: str
    pull_request_url: str
    in_reply_to_id: Optional[int] = None


class PullRequestReviewCommentEvent(BaseModel):
    """GitHub pull_request_review_comment webhook event.

    Triggered when a comment is created on a PR diff.
    """

    action: str  # created, edited, deleted
    comment: PullRequestReviewComment
    pull_request: PullRequest
    repository: Repository
    installation: Installation
    sender: User
