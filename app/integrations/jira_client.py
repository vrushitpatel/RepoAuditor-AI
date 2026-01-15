"""JIRA REST API client for creating and managing tickets.

This module provides a comprehensive client for interacting with JIRA Cloud
(Atlassian) to create issues from code review findings, add comments,
search issues, and manage tickets.
"""

import asyncio
import base64
from typing import Optional, List, Dict, Any
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.models.jira_models import (
    JIRAConfig,
    JIRAIssue,
    JIRAComment,
    JIRASearchResult,
    JIRAErrorResponse,
    CreateIssueRequest,
    JIRAIssueFields,
)
from app.models.review_findings import Finding
from app.utils.jira_formatter import JIRAFormatter
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class JIRAError(Exception):
    """Base exception for JIRA errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        """
        Initialize JIRA error.

        Args:
            message: Error message
            status_code: HTTP status code
            response: API response data
        """
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class JIRAAuthenticationError(JIRAError):
    """JIRA authentication error (401)."""

    pass


class JIRARateLimitError(JIRAError):
    """JIRA rate limit error (429)."""

    pass


class JIRAValidationError(JIRAError):
    """JIRA validation error (400)."""

    pass


class JIRAClient:
    """
    JIRA REST API client for Atlassian Cloud.

    Supports:
    - Email + API token authentication
    - Creating issues from code review findings
    - Adding comments
    - Searching issues with JQL
    - Automatic retry on rate limits
    - Rich JIRA markdown formatting
    """

    def __init__(self, config: JIRAConfig):
        """
        Initialize JIRA client.

        Args:
            config: JIRA configuration
        """
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.api_base = f"{self.base_url}/rest/api/3"

        # Create auth header (Basic auth with email:token)
        credentials = f"{config.email}:{config.api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_credentials}"

        # HTTP client
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": self.auth_header,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

        logger.info(f"Initialized JIRA client for {self.base_url}")

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Handle error responses from JIRA API.

        Args:
            response: HTTP response

        Raises:
            JIRAAuthenticationError: For 401 errors
            JIRARateLimitError: For 429 errors
            JIRAValidationError: For 400 errors
            JIRAError: For other errors
        """
        try:
            error_data = response.json()
        except Exception:
            error_data = {"errorMessages": [response.text]}

        error_response = JIRAErrorResponse(**error_data)
        error_msg = "; ".join(error_response.error_messages) or "Unknown error"

        if error_response.errors:
            field_errors = ", ".join(
                f"{field}: {msg}" for field, msg in error_response.errors.items()
            )
            error_msg = f"{error_msg}. Field errors: {field_errors}"

        if response.status_code == 401:
            raise JIRAAuthenticationError(
                f"Authentication failed: {error_msg}",
                status_code=401,
                response=error_data,
            )
        elif response.status_code == 429:
            raise JIRARateLimitError(
                f"Rate limit exceeded: {error_msg}",
                status_code=429,
                response=error_data,
            )
        elif response.status_code == 400:
            raise JIRAValidationError(
                f"Validation error: {error_msg}",
                status_code=400,
                response=error_data,
            )
        else:
            raise JIRAError(
                f"JIRA API error ({response.status_code}): {error_msg}",
                status_code=response.status_code,
                response=error_data,
            )

    @retry(
        retry=retry_if_exception_type(JIRARateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to JIRA API with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to api_base)
            json_data: JSON data for request body
            params: Query parameters

        Returns:
            Response data

        Raises:
            JIRAError: On API errors
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"

        logger.debug(f"JIRA API {method} {url}")

        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
            )

            if response.status_code >= 400:
                self._handle_error_response(response)

            # Handle 204 No Content
            if response.status_code == 204:
                return {}

            return response.json()

        except JIRAError:
            raise
        except Exception as e:
            logger.error(f"JIRA API request failed: {e}", exc_info=True)
            raise JIRAError(f"Request failed: {str(e)}")

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: Optional[str] = None,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignee_account_id: Optional[str] = None,
    ) -> JIRAIssue:
        """
        Create a JIRA issue.

        Args:
            project_key: Project key (e.g., "TECH")
            summary: Issue summary (max 255 chars)
            description: Issue description (JIRA markdown)
            issue_type: Issue type (Task, Bug, Story, etc.)
            priority: Priority name (Highest, High, Medium, Low, Lowest)
            labels: List of labels
            assignee_account_id: Assignee Atlassian account ID

        Returns:
            Created JIRA issue

        Raises:
            JIRAValidationError: If validation fails
            JIRAError: On other errors
        """
        logger.info(f"Creating JIRA issue in project {project_key}: {summary[:50]}...")

        # Validate inputs
        if len(summary) > 255:
            raise JIRAValidationError("Summary must be 255 characters or less")

        # Build issue payload
        fields: Dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }

        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description,
                            }
                        ],
                    }
                ],
            }

        if priority:
            fields["priority"] = {"name": priority}

        if labels:
            fields["labels"] = labels

        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}

        payload = {"fields": fields}

        # Create issue
        try:
            response_data = await self._make_request("POST", "/issue", json_data=payload)

            # Fetch full issue details
            issue_key = response_data.get("key")
            if issue_key:
                return await self.get_issue(issue_key)
            else:
                # Fallback: construct from response
                return JIRAIssue(
                    id=response_data.get("id"),
                    key=response_data.get("key"),
                    self=response_data.get("self"),
                    fields=JIRAIssueFields(
                        summary=summary,
                        description=description,
                        issuetype={"name": issue_type},
                        project={"key": project_key},
                        priority={"name": priority} if priority else None,
                        labels=labels or [],
                    ),
                )

        except JIRAValidationError as e:
            logger.error(f"Issue creation validation failed: {e.message}")
            raise
        except JIRAError as e:
            logger.error(f"Issue creation failed: {e.message}")
            raise

    async def get_issue(self, issue_key: str) -> JIRAIssue:
        """
        Get a JIRA issue by key.

        Args:
            issue_key: Issue key (e.g., "TECH-123")

        Returns:
            JIRA issue

        Raises:
            JIRAError: If issue not found or other error
        """
        logger.debug(f"Fetching JIRA issue {issue_key}")

        try:
            data = await self._make_request("GET", f"/issue/{issue_key}")
            return JIRAIssue(**data)
        except JIRAError as e:
            logger.error(f"Failed to fetch issue {issue_key}: {e.message}")
            raise

    async def add_comment(
        self,
        issue_key: str,
        comment: str,
    ) -> JIRAComment:
        """
        Add a comment to a JIRA issue.

        Args:
            issue_key: Issue key (e.g., "TECH-123")
            comment: Comment text (JIRA markdown)

        Returns:
            Created comment

        Raises:
            JIRAError: On error
        """
        logger.info(f"Adding comment to JIRA issue {issue_key}")

        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment,
                            }
                        ],
                    }
                ],
            }
        }

        try:
            data = await self._make_request(
                "POST",
                f"/issue/{issue_key}/comment",
                json_data=payload,
            )
            return JIRAComment(**data)
        except JIRAError as e:
            logger.error(f"Failed to add comment to {issue_key}: {e.message}")
            raise

    async def search_issues(
        self,
        jql_query: str,
        max_results: int = 50,
        start_at: int = 0,
    ) -> JIRASearchResult:
        """
        Search JIRA issues using JQL.

        Args:
            jql_query: JQL query string
            max_results: Maximum results to return
            start_at: Starting index for pagination

        Returns:
            Search results

        Raises:
            JIRAError: On error

        Example JQL:
            - "project = TECH AND status = Open"
            - "assignee = currentUser() ORDER BY created DESC"
            - "labels = code-review AND created >= -7d"
        """
        logger.debug(f"Searching JIRA issues: {jql_query}")

        params = {
            "jql": jql_query,
            "maxResults": max_results,
            "startAt": start_at,
        }

        try:
            data = await self._make_request("POST", "/search", params=params)
            return JIRASearchResult(**data)
        except JIRAError as e:
            logger.error(f"Issue search failed: {e.message}")
            raise

    async def create_issue_from_finding(
        self,
        project_key: str,
        finding: Finding,
        pr_url: Optional[str] = None,
        repo_name: Optional[str] = None,
        assignee_account_id: Optional[str] = None,
    ) -> JIRAIssue:
        """
        Create a JIRA issue from a code review finding.

        This is a convenience method that formats the finding using JIRAFormatter
        and creates an issue with appropriate labels, priority, and formatting.

        Args:
            project_key: Project key (e.g., "TECH")
            finding: Code review finding
            pr_url: Optional PR URL for reference
            repo_name: Optional repository name
            assignee_account_id: Optional assignee account ID

        Returns:
            Created JIRA issue

        Raises:
            JIRAError: On error
        """
        logger.info(
            f"Creating JIRA issue from finding: {finding.type} ({finding.severity})"
        )

        # Format finding as JIRA description
        description = JIRAFormatter.format_finding_description(
            finding=finding,
            pr_url=pr_url,
            repo_name=repo_name,
        )

        # Generate summary
        summary = JIRAFormatter.get_summary_from_finding(finding)

        # Get labels
        labels = JIRAFormatter.get_labels_from_finding(finding)

        # Get priority
        priority = JIRAFormatter.get_priority_from_finding(finding)

        # Determine issue type based on finding type
        issue_type = "Bug" if finding.severity in ["CRITICAL", "HIGH"] else "Task"

        # Create issue
        try:
            issue = await self.create_issue(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type=issue_type,
                priority=priority,
                labels=labels,
                assignee_account_id=assignee_account_id,
            )

            logger.info(f"Created JIRA issue {issue.key}: {issue.url}")
            return issue

        except JIRAError as e:
            logger.error(f"Failed to create issue from finding: {e.message}")
            raise

    async def validate_config(self) -> bool:
        """
        Validate JIRA configuration by checking authentication.

        Returns:
            True if authentication is successful

        Raises:
            JIRAAuthenticationError: If authentication fails
            JIRAError: On other errors
        """
        logger.info("Validating JIRA configuration")

        try:
            # Simple request to verify auth
            await self._make_request("GET", "/myself")
            logger.info("JIRA authentication successful")
            return True
        except JIRAAuthenticationError:
            logger.error("JIRA authentication failed")
            raise
        except JIRAError as e:
            logger.error(f"JIRA validation failed: {e.message}")
            raise

    async def get_project(self, project_key: str) -> Dict[str, Any]:
        """
        Get project information.

        Args:
            project_key: Project key

        Returns:
            Project data

        Raises:
            JIRAError: If project not found
        """
        logger.debug(f"Fetching project {project_key}")

        try:
            return await self._make_request("GET", f"/project/{project_key}")
        except JIRAError as e:
            logger.error(f"Failed to fetch project {project_key}: {e.message}")
            raise

    async def get_issue_types(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get available issue types for a project.

        Args:
            project_key: Project key

        Returns:
            List of issue types

        Raises:
            JIRAError: On error
        """
        logger.debug(f"Fetching issue types for project {project_key}")

        try:
            project = await self.get_project(project_key)
            return project.get("issueTypes", [])
        except JIRAError as e:
            logger.error(f"Failed to fetch issue types: {e.message}")
            raise
