"""Jira API client for issue tracking integration."""

from typing import Dict, Optional

import requests
from requests.auth import HTTPBasicAuth

from app.config import settings
from app.utils.logger import setup_logger
from app.utils.retry import retry

logger = setup_logger(__name__)


class JiraClient:
    """Client for Jira API operations."""

    def __init__(self) -> None:
        """Initialize Jira client."""
        if not settings.jira_enabled:
            logger.warning("Jira integration is not configured")
            return

        self.base_url = settings.jira_base_url
        self.auth = HTTPBasicAuth(
            settings.jira_email or "",
            settings.jira_api_token or "",
        )
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @retry(max_attempts=3, delay=1.0)
    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: str = "Medium",
    ) -> Optional[Dict[str, str]]:
        """
        Create a Jira issue.

        Args:
            project_key: Jira project key
            summary: Issue summary
            description: Issue description
            issue_type: Type of issue (Task, Bug, Story, etc.)
            priority: Issue priority

        Returns:
            Created issue details or None if Jira is not configured
        """
        if not settings.jira_enabled:
            logger.warning("Jira integration not enabled, skipping issue creation")
            return None

        url = f"{self.base_url}/rest/api/3/issue"

        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": issue_type},
                "priority": {"name": priority},
            }
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            auth=self.auth,
            timeout=10,
        )
        response.raise_for_status()

        issue_data = response.json()
        issue_key = issue_data.get("key")
        issue_url = f"{self.base_url}/browse/{issue_key}"

        logger.info(f"Created Jira issue: {issue_key}")

        return {
            "key": issue_key,
            "url": issue_url,
            "id": issue_data.get("id"),
        }

    @retry(max_attempts=3, delay=1.0)
    def add_comment(
        self,
        issue_key: str,
        comment: str,
    ) -> Optional[bool]:
        """
        Add a comment to a Jira issue.

        Args:
            issue_key: Jira issue key
            comment: Comment text

        Returns:
            True if successful, None if Jira is not configured
        """
        if not settings.jira_enabled:
            logger.warning("Jira integration not enabled, skipping comment")
            return None

        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"

        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            auth=self.auth,
            timeout=10,
        )
        response.raise_for_status()

        logger.info(f"Added comment to Jira issue: {issue_key}")
        return True

    @retry(max_attempts=3, delay=1.0)
    def get_issue(self, issue_key: str) -> Optional[Dict[str, str]]:
        """
        Get details of a Jira issue.

        Args:
            issue_key: Jira issue key

        Returns:
            Issue details or None if Jira is not configured
        """
        if not settings.jira_enabled:
            return None

        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"

        response = requests.get(
            url,
            headers=self.headers,
            auth=self.auth,
            timeout=10,
        )
        response.raise_for_status()

        issue_data = response.json()

        return {
            "key": issue_data.get("key"),
            "summary": issue_data["fields"]["summary"],
            "status": issue_data["fields"]["status"]["name"],
            "url": f"{self.base_url}/browse/{issue_key}",
        }
