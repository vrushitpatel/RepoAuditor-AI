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
