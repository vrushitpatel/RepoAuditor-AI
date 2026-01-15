"""Pydantic models for JIRA API objects.

These models represent JIRA issues, comments, and related objects for
type-safe interaction with the JIRA REST API.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class JIRAUser(BaseModel):
    """JIRA user information."""

    account_id: str = Field(..., description="Atlassian account ID")
    email: Optional[str] = Field(None, description="User email address")
    display_name: str = Field(..., description="User display name")
    active: bool = Field(True, description="Whether user is active")

    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow extra fields from JIRA API


class JIRAIssueFields(BaseModel):
    """JIRA issue fields."""

    summary: str = Field(..., description="Issue summary/title")
    description: Optional[Any] = Field(None, description="Issue description (string or Atlassian Document Format)")
    issuetype: Dict[str, Any] = Field(..., description="Issue type")
    project: Dict[str, Any] = Field(..., description="Project information")
    priority: Optional[Dict[str, Any]] = Field(None, description="Issue priority")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    assignee: Optional[Dict[str, Any]] = Field(None, description="Assignee information")
    reporter: Optional[Dict[str, Any]] = Field(None, description="Reporter information")
    status: Optional[Dict[str, Any]] = Field(None, description="Issue status")
    created: Optional[datetime] = Field(None, description="Creation timestamp")
    updated: Optional[datetime] = Field(None, description="Update timestamp")

    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow extra fields from JIRA API


class JIRAIssue(BaseModel):
    """JIRA issue object."""

    id: Optional[str] = Field(None, description="Issue ID")
    key: Optional[str] = Field(None, description="Issue key (e.g., TECH-123)")
    self: Optional[HttpUrl] = Field(None, description="API URL for this issue")
    fields: JIRAIssueFields = Field(..., description="Issue fields")

    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow extra fields from JIRA API

    @property
    def url(self) -> Optional[str]:
        """Get the web URL for this issue."""
        if self.self and self.key:
            # Convert API URL to web URL
            # https://yourcompany.atlassian.net/rest/api/3/issue/TECH-123
            # -> https://yourcompany.atlassian.net/browse/TECH-123
            base_url = str(self.self).split("/rest/api/")[0]
            return f"{base_url}/browse/{self.key}"
        return None


class JIRAComment(BaseModel):
    """JIRA comment object."""

    id: Optional[str] = Field(None, description="Comment ID")
    self: Optional[HttpUrl] = Field(None, description="API URL for this comment")
    author: Optional[JIRAUser] = Field(None, description="Comment author")
    body: str = Field(..., description="Comment body")
    created: Optional[datetime] = Field(None, description="Creation timestamp")
    updated: Optional[datetime] = Field(None, description="Update timestamp")

    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow extra fields from JIRA API


class JIRASearchResult(BaseModel):
    """JIRA search result object."""

    expand: Optional[str] = Field(None, description="Expand options")
    start_at: int = Field(0, description="Starting index")
    max_results: int = Field(50, description="Maximum results per page")
    total: int = Field(0, description="Total number of results")
    issues: List[JIRAIssue] = Field(default_factory=list, description="List of issues")

    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow extra fields from JIRA API


class JIRAErrorResponse(BaseModel):
    """JIRA error response."""

    error_messages: List[str] = Field(default_factory=list, description="Error messages")
    errors: Dict[str, str] = Field(default_factory=dict, description="Field-specific errors")


class JIRAConfig(BaseModel):
    """JIRA configuration."""

    base_url: str = Field(..., description="JIRA base URL (e.g., https://yourcompany.atlassian.net)")
    email: str = Field(..., description="User email for authentication")
    api_token: str = Field(..., description="API token for authentication")
    default_project_key: Optional[str] = Field(None, description="Default project key")
    enabled: bool = Field(True, description="Whether JIRA integration is enabled")

    class Config:
        """Pydantic config."""
        str_strip_whitespace = True


class JIRAPriority(BaseModel):
    """JIRA priority mapping."""

    name: str = Field(..., description="Priority name (e.g., Highest, High)")
    id: Optional[str] = Field(None, description="Priority ID")

    @staticmethod
    def from_severity(severity: str) -> str:
        """
        Map code review severity to JIRA priority name.

        Args:
            severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO)

        Returns:
            JIRA priority name
        """
        severity_to_priority = {
            "CRITICAL": "Highest",
            "HIGH": "High",
            "MEDIUM": "Medium",
            "LOW": "Low",
            "INFO": "Lowest",
        }
        return severity_to_priority.get(severity.upper(), "Medium")


class CreateIssueRequest(BaseModel):
    """Request model for creating a JIRA issue."""

    project_key: str = Field(..., description="Project key (e.g., TECH)")
    summary: str = Field(..., max_length=255, description="Issue summary")
    description: Optional[str] = Field(None, description="Issue description")
    issue_type: str = Field("Task", description="Issue type (Task, Bug, Story, etc.)")
    priority: Optional[str] = Field(None, description="Priority name")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    assignee_account_id: Optional[str] = Field(None, description="Assignee account ID")

    class Config:
        """Pydantic config."""
        str_strip_whitespace = True
