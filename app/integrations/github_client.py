"""GitHub API client for interacting with repositories and pull requests."""

from typing import Any, Dict, List, Optional

import requests
from github import Github, GithubException, PullRequest as GHPullRequest
from github.Commit import Commit
from github.CommitStatus import CommitStatus
from github.Issue import Issue
from github.IssueComment import IssueComment
from github.PullRequestComment import PullRequestComment
from github.Reaction import Reaction

from app.config import settings
from app.integrations.github_auth import GitHubAuth
from app.models.webhook_events import FileChange, ReviewComment
from app.utils.logger import setup_logger
from app.utils.retry import retry

logger = setup_logger(__name__)


class GitHubClient:
    """
    GitHub API client wrapper with authentication, rate limiting, and error handling.

    This client provides easy-to-use methods for interacting with GitHub API:
    - Automatic token management and refresh
    - Exponential backoff retry on rate limits
    - Comprehensive error handling and logging
    - Easy to mock for testing

    Example:
        ```python
        client = GitHubClient()

        # Get PR details
        pr = await client.get_pr_details("owner/repo", 123, installation_id=456)

        # Get PR diff
        diff = await client.get_pr_diff("owner/repo", 123, installation_id=456)

        # Post comment
        await client.post_pr_comment("owner/repo", 123, "LGTM!", installation_id=456)
        ```
    """

    def __init__(self, auth: Optional[GitHubAuth] = None) -> None:
        """
        Initialize GitHub client with authentication.

        Args:
            auth: Optional GitHubAuth instance (creates new if not provided)
        """
        self.auth = auth or GitHubAuth()
        self._clients: Dict[int, Github] = {}  # Cache Github instances

    def _get_installation_client(self, installation_id: int) -> Github:
        """
        Get authenticated GitHub client for an installation.

        Caches clients per installation for better performance.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            Authenticated GitHub client instance

        Note:
            Automatically handles token refresh if expired.
        """
        # Check if we have a valid cached client
        if installation_id in self._clients:
            # Verify token is still valid
            if self.auth.is_token_valid(installation_id):
                return self._clients[installation_id]
            else:
                # Token expired, remove cached client
                del self._clients[installation_id]

        # Get new token and create client
        access_token = self.auth.get_installation_token(installation_id)
        client = Github(access_token)
        self._clients[installation_id] = client

        logger.debug(
            f"Created GitHub client for installation {installation_id}",
            extra={"extra_fields": {"installation_id": installation_id}},
        )

        return client

    @retry(max_attempts=3, delay=1.0, backoff=2.0)
    def get_pr_details(
        self,
        repo_name: str,
        pr_number: int,
        installation_id: int,
    ) -> Dict[str, Any]:
        """
        Get detailed information about a pull request.

        Args:
            repo_name: Repository name in format "owner/repo"
            pr_number: Pull request number
            installation_id: GitHub App installation ID

        Returns:
            Dictionary with PR details including:
            - number, title, body, state
            - author, created_at, updated_at
            - head_ref, base_ref, head_sha, base_sha
            - additions, deletions, changed_files, commits
            - mergeable, merged, draft
            - html_url, diff_url, patch_url

        Example:
            ```python
            client = GitHubClient()
            pr_details = client.get_pr_details("owner/repo", 123, installation_id=456)
            print(f"PR Title: {pr_details['title']}")
            print(f"Changed files: {pr_details['changed_files']}")
            ```

        Raises:
            GithubException: If PR not found or API error occurs
        """
        try:
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # Fetch the list of changed files
            files = []
            for file in pr.get_files():
                files.append({
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": file.patch or "",
                })

            details = {
                "number": pr.number,
                "title": pr.title,
                "body": pr.body or "",
                "state": pr.state,
                "author": pr.user.login,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "head_ref": pr.head.ref,
                "base_ref": pr.base.ref,
                "head_sha": pr.head.sha,
                "base_sha": pr.base.sha,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "commits": pr.commits,
                "mergeable": pr.mergeable,
                "merged": pr.merged,
                "draft": pr.draft,
                "html_url": pr.html_url,
                "diff_url": pr.diff_url,
                "patch_url": pr.patch_url,
                "files": files,
            }

            logger.info(
                f"Retrieved PR details for {repo_name}#{pr_number}",
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "pr_number": pr_number,
                        "changed_files": details["changed_files"],
                    }
                },
            )

            return details

        except GithubException as e:
            logger.error(
                f"Failed to get PR details for {repo_name}#{pr_number}: {e}",
                exc_info=True,
            )
            raise

    @retry(max_attempts=3, delay=1.0, backoff=2.0)
    def get_pr_diff(
        self,
        repo_name: str,
        pr_number: int,
        installation_id: int,
    ) -> str:
        """
        Get the unified diff for a pull request.

        Args:
            repo_name: Repository name in format "owner/repo"
            pr_number: Pull request number
            installation_id: GitHub App installation ID

        Returns:
            Unified diff as string

        Example:
            ```python
            client = GitHubClient()
            diff = client.get_pr_diff("owner/repo", 123, installation_id=456)
            print(diff)  # Shows full diff with +/- lines
            ```

        Raises:
            GithubException: If PR not found or API error occurs
            requests.RequestException: If HTTP request fails
        """
        try:
            # Use the GitHub API endpoint instead of the web URL
            # The correct API endpoint is: https://api.github.com/repos/{owner}/{repo}/pulls/{number}
            api_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"
            token = self.auth.get_installation_token(installation_id)

            response = requests.get(
                api_url,
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3.diff",
                },
                timeout=30,
            )
            response.raise_for_status()

            diff_content = response.text

            logger.info(
                f"Retrieved diff for {repo_name}#{pr_number} ({len(diff_content)} chars)",
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "pr_number": pr_number,
                        "diff_size": len(diff_content),
                    }
                },
            )

            return diff_content

        except (GithubException, requests.RequestException) as e:
            logger.error(
                f"Failed to get PR diff for {repo_name}#{pr_number}: {e}",
                exc_info=True,
            )
            raise

    @retry(max_attempts=3, delay=1.0, backoff=2.0)
    def post_pr_comment(
        self,
        repo_name: str,
        pr_number: int,
        body: str,
        installation_id: int,
    ) -> IssueComment:
        """
        Post a comment on a pull request.

        Args:
            repo_name: Repository name in format "owner/repo"
            pr_number: Pull request number
            body: Comment body (Markdown supported)
            installation_id: GitHub App installation ID

        Returns:
            Created comment object

        Example:
            ```python
            client = GitHubClient()
            comment = client.post_pr_comment(
                "owner/repo",
                123,
                "LGTM! :+1:",
                installation_id=456
            )
            print(f"Comment posted: {comment.html_url}")
            ```

        Raises:
            GithubException: If PR not found or API error occurs
        """
        try:
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            comment = pr.create_issue_comment(body)

            logger.info(
                f"Posted comment on {repo_name}#{pr_number}",
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "pr_number": pr_number,
                        "comment_id": comment.id,
                        "body_length": len(body),
                    }
                },
            )

            return comment

        except GithubException as e:
            logger.error(
                f"Failed to post comment on {repo_name}#{pr_number}: {e}",
                exc_info=True,
            )
            raise

    @retry(max_attempts=3, delay=1.0, backoff=2.0)
    def post_review_comment_reply(
        self,
        repo_name: str,
        pr_number: int,
        comment_id: int,
        body: str,
        installation_id: int,
    ) -> IssueComment:
        """
        Reply to an existing review comment on a pull request.

        Args:
            repo_name: Repository name in format "owner/repo"
            pr_number: Pull request number
            comment_id: ID of the comment to reply to
            body: Reply body (Markdown supported)
            installation_id: GitHub App installation ID

        Returns:
            Created reply comment object

        Example:
            ```python
            client = GitHubClient()
            reply = client.post_review_comment_reply(
                "owner/repo",
                123,
                comment_id=456789,
                body="Thanks for the feedback!",
                installation_id=456
            )
            print(f"Reply posted: {reply.html_url}")
            ```

        Raises:
            GithubException: If comment not found or API error occurs
        """
        try:
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(repo_name)
            pr = repo.get_pull(pr_number)

            # Get the review comment and reply to it
            review_comment = pr.get_review_comment(comment_id)
            reply = review_comment.create_reply(body)

            logger.info(
                f"Posted reply to review comment {comment_id} on {repo_name}#{pr_number}",
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "pr_number": pr_number,
                        "comment_id": comment_id,
                    }
                },
            )

            return reply

        except GithubException as e:
            logger.error(
                f"Failed to post review comment reply on {repo_name}#{pr_number}: {e}",
                exc_info=True,
            )
            raise

    @retry(max_attempts=3, delay=1.0, backoff=2.0)
    def add_reaction(
        self,
        repo_name: str,
        comment_id: int,
        reaction: str,
        installation_id: int,
    ) -> Reaction:
        """
        Add a reaction to a comment.

        Args:
            repo_name: Repository name in format "owner/repo"
            comment_id: Comment ID
            reaction: Reaction type ('+1', '-1', 'laugh', 'confused', 'heart',
                                    'hooray', 'rocket', 'eyes')
            installation_id: GitHub App installation ID

        Returns:
            Created reaction object

        Example:
            ```python
            client = GitHubClient()
            reaction = client.add_reaction(
                "owner/repo",
                comment_id=98765,
                reaction="+1",
                installation_id=456
            )
            ```

        Raises:
            GithubException: If comment not found or API error occurs
            ValueError: If reaction type is invalid
        """
        valid_reactions = {"+1", "-1", "laugh", "confused", "heart", "hooray", "rocket", "eyes"}
        if reaction not in valid_reactions:
            raise ValueError(
                f"Invalid reaction: {reaction}. Must be one of: {', '.join(valid_reactions)}"
            )

        try:
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(repo_name)

            # Get the issue (comments are on issues, PRs are issues)
            issue = repo.get_issue(comment_id)
            comment = issue.get_comment(comment_id)

            reaction_obj = comment.create_reaction(reaction)

            logger.info(
                f"Added reaction '{reaction}' to comment {comment_id} in {repo_name}",
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "comment_id": comment_id,
                        "reaction": reaction,
                    }
                },
            )

            return reaction_obj

        except GithubException as e:
            logger.error(
                f"Failed to add reaction to comment {comment_id}: {e}",
                exc_info=True,
            )
            raise

    @retry(max_attempts=3, delay=1.0, backoff=2.0)
    def get_file_contents(
        self,
        repo_name: str,
        path: str,
        ref: str,
        installation_id: int,
    ) -> str:
        """
        Get contents of a file from repository.

        Args:
            repo_name: Repository name in format "owner/repo"
            path: Path to file in repository
            ref: Git reference (branch, tag, or commit SHA)
            installation_id: GitHub App installation ID

        Returns:
            File contents as string

        Example:
            ```python
            client = GitHubClient()
            content = client.get_file_contents(
                "owner/repo",
                "src/main.py",
                ref="main",
                installation_id=456
            )
            print(content)
            ```

        Raises:
            GithubException: If file not found or API error occurs
            ValueError: If path points to directory, not a file
        """
        try:
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(repo_name)
            content_file = repo.get_contents(path, ref=ref)

            if isinstance(content_file, list):
                raise ValueError(f"{path} is a directory, not a file")

            file_content = content_file.decoded_content.decode("utf-8")

            logger.info(
                f"Retrieved file contents: {repo_name}:{path}@{ref}",
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "path": path,
                        "ref": ref,
                        "size": len(file_content),
                    }
                },
            )

            return file_content

        except GithubException as e:
            logger.error(
                f"Failed to get file contents for {repo_name}:{path}@{ref}: {e}",
                exc_info=True,
            )
            raise

    @retry(max_attempts=3, delay=1.0, backoff=2.0)
    def update_commit_status(
        self,
        repo_name: str,
        sha: str,
        state: str,
        description: str,
        installation_id: int,
        context: str = "RepoAuditor AI",
        target_url: Optional[str] = None,
    ) -> CommitStatus:
        """
        Update commit status (check run).

        Args:
            repo_name: Repository name in format "owner/repo"
            sha: Commit SHA
            state: Status state ('pending', 'success', 'error', 'failure')
            description: Short description of the status
            installation_id: GitHub App installation ID
            context: Status context label (default: "RepoAuditor AI")
            target_url: Optional URL with more details

        Returns:
            Created commit status object

        Example:
            ```python
            client = GitHubClient()

            # Set pending status
            client.update_commit_status(
                "owner/repo",
                sha="abc123",
                state="pending",
                description="Code review in progress...",
                installation_id=456
            )

            # Set success status
            client.update_commit_status(
                "owner/repo",
                sha="abc123",
                state="success",
                description="Code review completed!",
                installation_id=456,
                target_url="https://example.com/review/123"
            )
            ```

        Raises:
            GithubException: If commit not found or API error occurs
            ValueError: If state is invalid
        """
        valid_states = {"pending", "success", "error", "failure"}
        if state not in valid_states:
            raise ValueError(
                f"Invalid state: {state}. Must be one of: {', '.join(valid_states)}"
            )

        try:
            client = self._get_installation_client(installation_id)
            repo = client.get_repo(repo_name)
            commit = repo.get_commit(sha)

            status = commit.create_status(
                state=state,
                description=description,
                context=context,
                target_url=target_url,
            )

            logger.info(
                f"Updated commit status for {repo_name}@{sha[:7]}: {state}",
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "sha": sha,
                        "state": state,
                        "context": context,
                    }
                },
            )

            return status

        except GithubException as e:
            logger.error(
                f"Failed to update commit status for {repo_name}@{sha}: {e}",
                exc_info=True,
            )
            raise

    # Legacy methods (keeping for backward compatibility)

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
