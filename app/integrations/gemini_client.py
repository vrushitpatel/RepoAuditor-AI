"""Google Gemini API client for AI-powered code analysis."""

from typing import List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.models.webhook_events import FileChange
from app.utils.logger import setup_logger
from app.utils.retry import retry

logger = setup_logger(__name__)


class GeminiClient:
    """Client for Google Gemini API operations."""

    def __init__(self) -> None:
        """Initialize Gemini client."""
        self.model = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.3,
            max_output_tokens=8192,
        )

    @retry(max_attempts=3, delay=2.0)
    async def analyze_code_changes(
        self,
        files: List[FileChange],
        pr_title: str,
        pr_description: Optional[str] = None,
    ) -> str:
        """
        Analyze code changes using Gemini AI.

        Args:
            files: List of changed files
            pr_title: Pull request title
            pr_description: Pull request description

        Returns:
            AI-generated analysis and review
        """
        # Build analysis prompt
        prompt = self._build_analysis_prompt(files, pr_title, pr_description)

        # Get AI response
        response = await self.model.ainvoke(prompt)
        analysis = response.content

        logger.info(f"Generated analysis for {len(files)} files")
        return str(analysis)

    def _build_analysis_prompt(
        self,
        files: List[FileChange],
        pr_title: str,
        pr_description: Optional[str] = None,
    ) -> str:
        """
        Build prompt for code analysis.

        Args:
            files: List of changed files
            pr_title: Pull request title
            pr_description: Pull request description

        Returns:
            Formatted prompt for AI
        """
        prompt_parts = [
            "You are an expert code reviewer. Analyze the following pull request changes and provide a comprehensive review.",
            "",
            f"**Pull Request Title:** {pr_title}",
        ]

        if pr_description:
            prompt_parts.append(f"**Description:** {pr_description}")

        prompt_parts.extend(
            [
                "",
                "**Changed Files:**",
                "",
                "Please review the code for:",
                "1. Code quality and best practices",
                "2. Potential bugs or errors",
                "3. Security vulnerabilities",
                "4. Performance issues",
                "5. Code style and consistency",
                "6. Missing error handling",
                "7. Documentation and comments",
                "",
                "Provide specific, actionable feedback for each issue found.",
                "",
                "---",
                "",
            ]
        )

        # Add file changes
        for file in files[:settings.max_files_per_review]:
            prompt_parts.extend(
                [
                    f"### File: {file.filename}",
                    f"**Status:** {file.status}",
                    f"**Changes:** +{file.additions} -{file.deletions}",
                    "",
                ]
            )

            if file.patch:
                prompt_parts.extend(
                    [
                        "**Diff:**",
                        "```diff",
                        file.patch,
                        "```",
                        "",
                    ]
                )

        if len(files) > settings.max_files_per_review:
            prompt_parts.append(
                f"\n*Note: Showing {settings.max_files_per_review} of {len(files)} files*"
            )

        return "\n".join(prompt_parts)

    @retry(max_attempts=3, delay=2.0)
    async def generate_review_summary(
        self,
        analysis: str,
        files_count: int,
    ) -> str:
        """
        Generate a concise summary of the review.

        Args:
            analysis: Detailed analysis from AI
            files_count: Number of files reviewed

        Returns:
            Summary of the review
        """
        prompt = f"""Based on the following detailed code review, create a concise summary (2-3 paragraphs) highlighting:
1. Overall code quality
2. Critical issues (if any)
3. Recommendations

Review:
{analysis}

Files reviewed: {files_count}
"""

        response = await self.model.ainvoke(prompt)
        return str(response.content)
