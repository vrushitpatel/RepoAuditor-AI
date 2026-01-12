"""Explainer Agent - A friendly, witty, educational code explainer with personality."""

from typing import Optional

from app.integrations.gemini_client import GeminiClient
from app.integrations.github_client import GitHubClient
from app.models.review_findings import ExplanationResponse
from app.prompts.explainer_prompts import (
    EXPLAINER_SYSTEM_PROMPT,
    get_architecture_explanation_prompt,
    get_comparison_explanation_prompt,
    get_file_explanation_prompt,
    get_function_explanation_prompt,
    get_pr_diff_explanation_prompt,
)
from app.utils.code_fetcher import CodeFetcher
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExplainerAgent:
    """
    A friendly, witty, educational code explainer with personality.

    This agent acts like a helpful senior developer at 2am, explaining code
    in a way that's both educational and entertaining. Uses ELI5 approach
    with analogies, humor, and genuine encouragement.
    """

    def __init__(
        self,
        gemini_client: GeminiClient,
        github_client: GitHubClient,
    ):
        """
        Initialize the Explainer Agent.

        Args:
            gemini_client: Client for Gemini AI
            github_client: Client for GitHub API
        """
        self.gemini = gemini_client
        self.github = github_client
        self.code_fetcher = CodeFetcher(github_client)

        logger.info("Explainer Agent initialized")

    async def explain_file(
        self,
        repo_name: str,
        file_path: str,
        installation_id: int,
        pr_number: Optional[int] = None,
        context: str = "",
        pr_title: str = "",
        ref: Optional[str] = None,
    ) -> ExplanationResponse:
        """
        Explain an entire file with personality.

        Args:
            repo_name: Repository name (owner/repo)
            file_path: Path to the file
            installation_id: GitHub App installation ID
            pr_number: Optional PR number for context
            context: Additional context about the request
            pr_title: PR title for additional context
            ref: Branch/commit ref (optional)

        Returns:
            ExplanationResponse with friendly explanation

        Raises:
            Exception: If file cannot be fetched or explained
        """
        logger.info(
            f"Explaining file: {repo_name}/{file_path}",
            extra={
                "extra_fields": {
                    "repo": repo_name,
                    "file_path": file_path,
                    "pr_number": pr_number,
                }
            },
        )

        try:
            # Fetch file content
            file_content = await self.code_fetcher.fetch_file_content(
                repo_name=repo_name,
                file_path=file_path,
                installation_id=installation_id,
                ref=ref,
            )

            if not file_content:
                raise ValueError(f"Could not fetch file: {file_path}")

            # Truncate if too large
            file_content = self.code_fetcher.truncate_content(file_content)

            # Generate explanation with personality
            prompt = get_file_explanation_prompt(
                file_path=file_path,
                file_content=file_content,
                context=context,
                pr_title=pr_title,
            )

            response = await self.gemini.generate_text(
                prompt=prompt,
                system_message=EXPLAINER_SYSTEM_PROMPT,
            )

            logger.info(
                f"Generated explanation for {file_path}",
                extra={
                    "extra_fields": {
                        "file_path": file_path,
                        "tokens": response.tokens_used,
                        "cost": response.cost_usd,
                    }
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to explain file {file_path}: {e}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "file_path": file_path,
                        "error": str(e),
                    }
                },
            )
            raise

    async def explain_function_or_class(
        self,
        repo_name: str,
        file_path: str,
        target_name: str,
        installation_id: int,
        ref: Optional[str] = None,
    ) -> ExplanationResponse:
        """
        Explain a specific function or class with personality.

        Args:
            repo_name: Repository name (owner/repo)
            file_path: Path to the file
            target_name: Name of function or class to explain
            installation_id: GitHub App installation ID
            ref: Branch/commit ref (optional)

        Returns:
            ExplanationResponse with focused explanation

        Raises:
            Exception: If function/class cannot be found or explained
        """
        logger.info(
            f"Explaining {target_name} in {file_path}",
            extra={
                "extra_fields": {
                    "repo": repo_name,
                    "file_path": file_path,
                    "target": target_name,
                }
            },
        )

        try:
            # Fetch file content
            file_content = await self.code_fetcher.fetch_file_content(
                repo_name=repo_name,
                file_path=file_path,
                installation_id=installation_id,
                ref=ref,
            )

            if not file_content:
                raise ValueError(f"Could not fetch file: {file_path}")

            # Extract specific function/class
            extracted_code, surrounding_context = (
                self.code_fetcher.extract_function_or_class(
                    file_content=file_content,
                    target_name=target_name,
                )
            )

            if not extracted_code:
                raise ValueError(
                    f"Could not find function/class '{target_name}' in {file_path}"
                )

            # Generate focused explanation
            prompt = get_function_explanation_prompt(
                file_path=file_path,
                function_name=target_name,
                function_code=extracted_code,
                surrounding_context=surrounding_context or "",
            )

            response = await self.gemini.generate_text(
                prompt=prompt,
                system_message=EXPLAINER_SYSTEM_PROMPT,
            )

            logger.info(
                f"Generated explanation for {target_name}",
                extra={
                    "extra_fields": {
                        "target": target_name,
                        "tokens": response.tokens_used,
                        "cost": response.cost_usd,
                    }
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to explain {target_name}: {e}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "file_path": file_path,
                        "target": target_name,
                        "error": str(e),
                    }
                },
            )
            raise

    async def explain_pr_diff(
        self,
        repo_name: str,
        pr_number: int,
        installation_id: int,
        pr_title: str = "",
        pr_description: str = "",
        specific_file: Optional[str] = None,
    ) -> ExplanationResponse:
        """
        Explain PR changes with personality and narrative.

        Args:
            repo_name: Repository name (owner/repo)
            pr_number: Pull request number
            installation_id: GitHub App installation ID
            pr_title: PR title
            pr_description: PR description
            specific_file: Optional specific file to focus on

        Returns:
            ExplanationResponse with narrative explanation of changes

        Raises:
            Exception: If diff cannot be fetched or explained
        """
        logger.info(
            f"Explaining PR diff: {repo_name}#{pr_number}",
            extra={
                "extra_fields": {
                    "repo": repo_name,
                    "pr_number": pr_number,
                    "specific_file": specific_file,
                }
            },
        )

        try:
            # Fetch PR diff
            diff_content = self.github.get_pr_diff(
                repo_name=repo_name,
                pr_number=pr_number,
                installation_id=installation_id,
            )

            if not diff_content:
                raise ValueError(f"Could not fetch diff for PR #{pr_number}")

            # Filter diff if specific file requested
            if specific_file:
                # TODO: Filter diff to only show specific file
                # For now, just include the whole diff with a note
                pass

            # Truncate if too large
            diff_content = self.code_fetcher.truncate_content(diff_content)

            # Generate narrative explanation
            prompt = get_pr_diff_explanation_prompt(
                pr_title=pr_title or f"PR #{pr_number}",
                pr_description=pr_description,
                diff_content=diff_content,
                file_path=specific_file or "",
            )

            response = await self.gemini.generate_text(
                prompt=prompt,
                system_message=EXPLAINER_SYSTEM_PROMPT,
            )

            logger.info(
                f"Generated PR diff explanation for #{pr_number}",
                extra={
                    "extra_fields": {
                        "pr_number": pr_number,
                        "tokens": response.tokens_used,
                        "cost": response.cost_usd,
                    }
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to explain PR diff #{pr_number}: {e}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "pr_number": pr_number,
                        "error": str(e),
                    }
                },
            )
            raise

    async def compare_versions(
        self,
        repo_name: str,
        file_path: str,
        pr_number: int,
        installation_id: int,
        context: str = "",
    ) -> ExplanationResponse:
        """
        Compare before/after versions of a file in a PR.

        Args:
            repo_name: Repository name (owner/repo)
            file_path: Path to the file
            pr_number: Pull request number
            installation_id: GitHub App installation ID
            context: Additional context

        Returns:
            ExplanationResponse with comparison

        Raises:
            Exception: If versions cannot be fetched or compared
        """
        logger.info(
            f"Comparing versions: {file_path} in PR #{pr_number}",
            extra={
                "extra_fields": {
                    "repo": repo_name,
                    "file_path": file_path,
                    "pr_number": pr_number,
                }
            },
        )

        try:
            # Fetch both versions
            base_content, head_content = (
                await self.code_fetcher.fetch_pr_file_content(
                    repo_name=repo_name,
                    file_path=file_path,
                    pr_number=pr_number,
                    installation_id=installation_id,
                )
            )

            # Handle cases where file is new or deleted
            if not base_content and head_content:
                context += " (This is a new file added in this PR)"
                base_content = "[File did not exist before]"
            elif base_content and not head_content:
                context += " (This file was deleted in this PR)"
                head_content = "[File was deleted]"
            elif not base_content and not head_content:
                raise ValueError(f"Could not fetch either version of {file_path}")

            # Truncate if too large
            base_content = self.code_fetcher.truncate_content(base_content)
            head_content = self.code_fetcher.truncate_content(head_content)

            # Generate comparison explanation
            prompt = get_comparison_explanation_prompt(
                old_code=base_content,
                new_code=head_content,
                file_path=file_path,
                context=context,
            )

            response = await self.gemini.generate_text(
                prompt=prompt,
                system_message=EXPLAINER_SYSTEM_PROMPT,
            )

            logger.info(
                f"Generated comparison for {file_path}",
                extra={
                    "extra_fields": {
                        "file_path": file_path,
                        "tokens": response.tokens_used,
                        "cost": response.cost_usd,
                    }
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to compare versions of {file_path}: {e}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "file_path": file_path,
                        "pr_number": pr_number,
                        "error": str(e),
                    }
                },
            )
            raise

    async def explain_from_reference(
        self,
        repo_name: str,
        reference: str,
        installation_id: int,
        pr_number: Optional[int] = None,
        context: str = "",
        pr_title: str = "",
        ref: Optional[str] = None,
    ) -> ExplanationResponse:
        """
        Smart explanation that handles different reference formats.

        Handles:
        - "app/main.py" -> Explain entire file
        - "app/main.py:MyClass" -> Explain specific class
        - "app/main.py:my_function" -> Explain specific function

        Args:
            repo_name: Repository name (owner/repo)
            reference: File reference (with optional :target)
            installation_id: GitHub App installation ID
            pr_number: Optional PR number
            context: Additional context
            pr_title: PR title
            ref: Git reference (branch, tag, or commit SHA)

        Returns:
            ExplanationResponse appropriate for the reference type

        Raises:
            Exception: If reference cannot be explained
        """
        logger.info(
            f"Explaining reference: {reference}",
            extra={
                "extra_fields": {
                    "repo": repo_name,
                    "reference": reference,
                    "pr_number": pr_number,
                }
            },
        )

        # Parse reference
        file_path, target_name = self.code_fetcher.parse_file_reference(reference)

        if target_name:
            # Explain specific function/class
            return await self.explain_function_or_class(
                repo_name=repo_name,
                file_path=file_path,
                target_name=target_name,
                installation_id=installation_id,
                ref=ref,
            )
        else:
            # Explain entire file
            return await self.explain_file(
                repo_name=repo_name,
                file_path=file_path,
                installation_id=installation_id,
                pr_number=pr_number,
                context=context,
                pr_title=pr_title,
                ref=ref,
            )


# Convenience functions for quick explanations

async def explain_code(
    reference: str,
    repo_name: str,
    installation_id: int,
    gemini_client: GeminiClient,
    github_client: GitHubClient,
    **kwargs,
) -> ExplanationResponse:
    """
    Quick convenience function for explaining code.

    Args:
        reference: File reference (e.g., "app/main.py" or "app/main.py:MyClass")
        repo_name: Repository name
        installation_id: GitHub App installation ID
        gemini_client: Gemini client
        github_client: GitHub client
        **kwargs: Additional arguments passed to explain_from_reference

    Returns:
        ExplanationResponse with explanation
    """
    agent = ExplainerAgent(gemini_client, github_client)
    return await agent.explain_from_reference(
        repo_name=repo_name,
        reference=reference,
        installation_id=installation_id,
        **kwargs,
    )
