"""GitHub API client for interacting with repositories and pull requests."""

import time
from typing import Any, Dict, List, Optional

import jwt
import requests
from github import Github, GithubIntegration, PullRequest as GHPullRequest

from app.config import settings
from app.models.webhook_events import FileChange, ReviewComment
from app.utils.logger import setup_logger
from app.utils.retry import retry

logger = setup_logger(__name__)


class GitHubClient:
    """Client for GitHub API operations."""

    def __init__(self) -> None:
        """Initialize GitHub client with App credentials."""
        self.app_id = settings.github_app_id
        self.private_key = settings.github_private_key
        self._integration: Optional[GithubIntegration] = None

    def _get_integration(self) -> GithubIntegration:
        """Get or create GitHub integration instance."""
        if self._integration is None:
            self._integration = GithubIntegration(
                self.app_id,
                self.private_key,
            )
        return self._integration

    def _get_installation_client(self, installation_id: int) -> Github:
        """
        Get authenticated GitHub client for an installation.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            Authenticated GitHub client
        """
        integration = self._get_integration()
        access_token = integration.get_access_token(installation_id).token
        return Github(access_token)

    @retry(max_attempts=3, delay=1.0)
    def get_pull_request(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
    ) -> GHPullRequest:
        """
        Get a pull request.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Full repository name (owner/repo)
            pr_number: Pull request number

        Returns:
            Pull request object
        """
        client = self._get_installation_client(installation_id)
        repo = client.get_repo(repo_full_name)
        return repo.get_pull(pr_number)

    @retry(max_attempts=3, delay=1.0)
    def get_pull_request_files(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
    ) -> List[FileChange]:
        """
        Get files changed in a pull request.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Full repository name (owner/repo)
            pr_number: Pull request number

        Returns:
            List of changed files
        """
        pr = self.get_pull_request(installation_id, repo_full_name, pr_number)

        files = []
        for file in pr.get_files():
            files.append(
                FileChange(
                    filename=file.filename,
                    status=file.status,
                    additions=file.additions,
                    deletions=file.deletions,
                    changes=file.changes,
                    patch=file.patch,
                    contents_url=file.contents_url,
                    raw_url=file.raw_url,
                )
            )

        logger.info(f"Retrieved {len(files)} changed files from PR #{pr_number}")
        return files

    @retry(max_attempts=3, delay=1.0)
    def get_file_content(
        self,
        installation_id: int,
        repo_full_name: str,
        file_path: str,
        ref: str,
    ) -> str:
        """
        Get content of a file from repository.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Full repository name (owner/repo)
            file_path: Path to file in repository
            ref: Git reference (branch, tag, or commit SHA)

        Returns:
            File content as string
        """
        client = self._get_installation_client(installation_id)
        repo = client.get_repo(repo_full_name)
        content_file = repo.get_contents(file_path, ref=ref)

        if isinstance(content_file, list):
            raise ValueError(f"{file_path} is a directory, not a file")

        return content_file.decoded_content.decode("utf-8")

    @retry(max_attempts=3, delay=1.0)
    def create_review_comment(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
        comment: ReviewComment,
        commit_id: str,
    ) -> None:
        """
        Create a review comment on a pull request.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Full repository name (owner/repo)
            pr_number: Pull request number
            comment: Review comment to post
            commit_id: Commit SHA to comment on
        """
        pr = self.get_pull_request(installation_id, repo_full_name, pr_number)

        kwargs: Dict[str, Any] = {
            "body": comment.body,
            "commit_id": pr.head.sha,
            "path": comment.path,
        }

        # Add position or line based on what's available
        if comment.position is not None:
            kwargs["position"] = comment.position
        elif comment.line is not None:
            kwargs["line"] = comment.line
            kwargs["side"] = comment.side

        pr.create_review_comment(**kwargs)
        logger.info(f"Created review comment on {comment.path}")

    @retry(max_attempts=3, delay=1.0)
    def create_review(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: Optional[List[ReviewComment]] = None,
    ) -> None:
        """
        Create a review on a pull request.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Full repository name (owner/repo)
            pr_number: Pull request number
            body: Review body/summary
            event: Review event type (COMMENT, APPROVE, REQUEST_CHANGES)
            comments: Optional list of review comments
        """
        pr = self.get_pull_request(installation_id, repo_full_name, pr_number)

        review_comments = []
        if comments:
            for comment in comments:
                review_comment: Dict[str, Any] = {
                    "path": comment.path,
                    "body": comment.body,
                }

                if comment.line is not None:
                    review_comment["line"] = comment.line
                    review_comment["side"] = comment.side
                elif comment.position is not None:
                    review_comment["position"] = comment.position

                review_comments.append(review_comment)

        pr.create_review(
            body=body,
            event=event,
            comments=review_comments if review_comments else None,
        )

        logger.info(f"Created review on PR #{pr_number} with {len(review_comments)} comments")

    @retry(max_attempts=3, delay=1.0)
    def add_pr_comment(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
        body: str,
    ) -> None:
        """
        Add a general comment to a pull request.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Full repository name (owner/repo)
            pr_number: Pull request number
            body: Comment body
        """
        pr = self.get_pull_request(installation_id, repo_full_name, pr_number)
        pr.create_issue_comment(body)
        logger.info(f"Added comment to PR #{pr_number}")
