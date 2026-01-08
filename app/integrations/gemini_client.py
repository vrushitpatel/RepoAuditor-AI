"""Google Gemini API client for AI-powered code analysis."""

import json
from typing import Dict, List, Optional, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.models.review_findings import (
    ExplanationResponse,
    Finding,
    FixSuggestion,
    ModelConfig,
    ReviewAnalysis,
)
from app.models.webhook_events import FileChange
from app.prompts.code_review_prompts import (
    SYSTEM_PROMPT,
    format_best_practices_prompt,
    format_bugs_prompt,
    format_explanation_prompt,
    format_fix_prompt,
    format_general_prompt,
    format_performance_prompt,
    format_security_prompt,
    get_analysis_prompt,
)
from app.utils.logger import setup_logger
from app.utils.retry import retry

logger = setup_logger(__name__)


class GeminiClient:
    """
    Google Gemini API client for AI-powered code analysis.

    Features:
    - Multiple analysis types (security, performance, bugs, best practices)
    - Structured response parsing
    - Token counting and cost tracking
    - Easy model switching (Flash vs Pro)
    - Retry logic for API failures
    - Streaming support

    Example:
        ```python
        client = GeminiClient()

        # Analyze for security issues
        findings = await client.analyze_code(pr_diff, "security")

        # Generate explanation
        explanation = await client.generate_explanation(code_snippet, "API endpoint")

        # Suggest fix
        fix = await client.suggest_fix("Memory leak in loop", code_context)
        ```
    """

    def __init__(
        self,
        model_config: Optional[ModelConfig] = None,
        use_flash: bool = True,
    ) -> None:
        """
        Initialize Gemini client.

        Args:
            model_config: Optional model configuration (uses default if not provided)
            use_flash: If True, uses Flash model (faster, cheaper), else uses Pro
        """
        # Use provided config or create default based on use_flash
        if model_config is None:
            model_config = ModelConfig.flash() if use_flash else ModelConfig.pro()

        self.model_config = model_config

        # Initialize the model
        # Note: response_mime_type may help force JSON output but is not guaranteed to be supported
        self.model = ChatGoogleGenerativeAI(
            model=model_config.model_name,
            google_api_key=settings.gemini.api_key,
            temperature=model_config.temperature,
            max_output_tokens=model_config.max_output_tokens,
            top_p=model_config.top_p,
            top_k=model_config.top_k,
        )

        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

        logger.info(
            f"Initialized Gemini client with model: {model_config.model_name}",
            extra={
                "extra_fields": {
                    "model": model_config.model_name,
                    "temperature": model_config.temperature,
                }
            },
        )

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    async def analyze_code(
        self,
        code_diff: str,
        analysis_type: str = "general",
    ) -> ReviewAnalysis:
        """
        Analyze code diff for specific issues.

        Args:
            code_diff: Unified diff or code changes
            analysis_type: Type of analysis - "security", "performance",
                          "best_practices", "bugs", or "general"

        Returns:
            ReviewAnalysis object with structured findings

        Example:
            ```python
            client = GeminiClient()
            analysis = await client.analyze_code(diff, "security")

            for finding in analysis.findings:
                if finding.severity in ["CRITICAL", "HIGH"]:
                    print(f"{finding.title}: {finding.description}")
            ```

        Raises:
            ValueError: If analysis_type is not supported
        """
        # Get appropriate prompt
        if analysis_type == "security":
            prompt = format_security_prompt(code_diff)
        elif analysis_type == "performance":
            prompt = format_performance_prompt(code_diff)
        elif analysis_type == "best_practices":
            prompt = format_best_practices_prompt(code_diff)
        elif analysis_type == "bugs":
            prompt = format_bugs_prompt(code_diff)
        elif analysis_type == "general":
            prompt = format_general_prompt(code_diff)
        else:
            raise ValueError(f"Invalid analysis type: {analysis_type}")

        # Create messages
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        # Get AI response
        logger.info(f"Starting {analysis_type} analysis")
        response = await self.model.ainvoke(messages)
        content = str(response.content)

        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        input_tokens = len(prompt) // 4
        output_tokens = len(content) // 4

        # Update tracking
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        cost = self.model_config.calculate_cost(input_tokens, output_tokens)
        self.total_cost_usd += cost

        # Parse JSON response
        try:
            findings_data = self._extract_json(content)

            findings = [Finding(**f) for f in findings_data.get("findings", [])]

            analysis = ReviewAnalysis(
                findings=findings,
                summary=findings_data.get("summary", "Analysis complete"),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
            )
            analysis.count_by_severity()

            logger.info(
                f"Analysis complete: {len(findings)} findings ({analysis.critical_count} critical, {analysis.high_count} high)",
                extra={
                    "extra_fields": {
                        "analysis_type": analysis_type,
                        "total_issues": analysis.total_issues,
                        "critical": analysis.critical_count,
                        "high": analysis.high_count,
                        "tokens": input_tokens + output_tokens,
                        "cost_usd": cost,
                    }
                },
            )

            return analysis

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                f"Failed to parse structured response: {e}",
                extra={
                    "extra_fields": {
                        "error_type": type(e).__name__,
                        "error_msg": str(e),
                        "response_preview": content[:1000] if content else "empty",
                        "analysis_type": analysis_type,
                    }
                }
            )

            # Log full response to file for debugging
            logger.debug(f"Full AI response that failed to parse:\n{content}")

            # Fallback: Return unstructured analysis with the raw content
            # This helps us see what the AI actually returned
            return ReviewAnalysis(
                findings=[],
                summary=f"⚠️ Failed to parse AI response. Raw output:\n\n{content[:2000]}",
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
            )

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    async def generate_explanation(
        self,
        code_snippet: str,
        context: str = "",
    ) -> ExplanationResponse:
        """
        Generate detailed explanation of code.

        Args:
            code_snippet: Code to explain
            context: Additional context about the code

        Returns:
            ExplanationResponse with detailed explanation

        Example:
            ```python
            client = GeminiClient()
            explanation = await client.generate_explanation(
                code_snippet="def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
                context="Recursive function"
            )
            print(explanation.explanation)
            print(f"Complexity: {explanation.complexity}")
            ```
        """
        prompt = format_explanation_prompt(code_snippet, context)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        logger.info("Generating code explanation")
        response = await self.model.ainvoke(messages)
        content = str(response.content)

        # Token tracking
        input_tokens = len(prompt) // 4
        output_tokens = len(content) // 4
        cost = self.model_config.calculate_cost(input_tokens, output_tokens)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost

        # Parse response
        try:
            data = self._extract_json(content)
            explanation = ExplanationResponse(
                explanation=data.get("explanation", content),
                key_concepts=data.get("key_concepts", []),
                complexity=data.get("complexity"),
                suggestions=data.get("suggestions", []),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
            )

            logger.info(
                f"Explanation generated ({len(explanation.explanation)} chars)",
                extra={
                    "extra_fields": {
                        "tokens": input_tokens + output_tokens,
                        "cost_usd": cost,
                    }
                },
            )

            return explanation

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse explanation response: {e}")
            return ExplanationResponse(
                explanation=content,
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
            )

    @retry(max_attempts=3, delay=2.0, backoff=2.0)
    async def suggest_fix(
        self,
        issue_description: str,
        code_context: str,
    ) -> FixSuggestion:
        """
        Suggest fix for a code issue.

        Args:
            issue_description: Description of the problem
            code_context: Current code that needs fixing

        Returns:
            FixSuggestion with recommended fix

        Example:
            ```python
            client = GeminiClient()
            fix = await client.suggest_fix(
                issue_description="SQL injection vulnerability",
                code_context='query = f"SELECT * FROM users WHERE id = {user_id}"'
            )
            print(f"Fixed code:\\n{fix.fixed_code}")
            print(f"Explanation: {fix.explanation}")
            ```
        """
        prompt = format_fix_prompt(issue_description, code_context)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        logger.info(f"Suggesting fix for: {issue_description[:50]}...")
        response = await self.model.ainvoke(messages)
        content = str(response.content)

        # Token tracking
        input_tokens = len(prompt) // 4
        output_tokens = len(content) // 4
        cost = self.model_config.calculate_cost(input_tokens, output_tokens)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost

        # Parse response
        try:
            data = self._extract_json(content)
            fix = FixSuggestion(
                original_code=data.get("original_code", code_context),
                fixed_code=data.get("fixed_code", ""),
                explanation=data.get("explanation", ""),
                trade_offs=data.get("trade_offs", []),
                alternatives=data.get("alternatives", []),
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
            )

            logger.info(
                f"Fix suggestion generated",
                extra={
                    "extra_fields": {
                        "tokens": input_tokens + output_tokens,
                        "cost_usd": cost,
                    }
                },
            )

            return fix

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse fix suggestion response: {e}")
            return FixSuggestion(
                original_code=code_context,
                fixed_code=content,
                explanation="See suggested code above",
                tokens_used=input_tokens + output_tokens,
                cost_usd=cost,
            )

    async def analyze_code_stream(
        self,
        code_diff: str,
        analysis_type: str = "general",
    ):
        """
        Analyze code with streaming response (for future use).

        Args:
            code_diff: Code diff to analyze
            analysis_type: Type of analysis

        Yields:
            Chunks of the response as they arrive

        Example:
            ```python
            client = GeminiClient()
            async for chunk in client.analyze_code_stream(diff, "security"):
                print(chunk, end="", flush=True)
            ```
        """
        prompt_template = get_analysis_prompt(analysis_type)
        prompt = prompt_template.format(code_diff=code_diff)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        logger.info(f"Starting streaming {analysis_type} analysis")

        # Stream response
        async for chunk in self.model.astream(messages):
            if hasattr(chunk, "content"):
                yield chunk.content

    def switch_model(self, use_flash: bool = True) -> None:
        """
        Switch between Flash and Pro models.

        Args:
            use_flash: If True, switch to Flash model, else switch to Pro

        Example:
            ```python
            client = GeminiClient(use_flash=True)  # Start with Flash

            # For complex analysis, switch to Pro
            client.switch_model(use_flash=False)
            analysis = await client.analyze_code(diff, "security")

            # Switch back to Flash for simpler tasks
            client.switch_model(use_flash=True)
            ```
        """
        old_model = self.model_config.model_name
        self.model_config = ModelConfig.flash() if use_flash else ModelConfig.pro()

        self.model = ChatGoogleGenerativeAI(
            model=self.model_config.model_name,
            google_api_key=settings.gemini.api_key,
            temperature=self.model_config.temperature,
            max_output_tokens=self.model_config.max_output_tokens,
            top_p=self.model_config.top_p,
            top_k=self.model_config.top_k,
        )

        logger.info(
            f"Switched model: {old_model} -> {self.model_config.model_name}",
            extra={
                "extra_fields": {
                    "old_model": old_model,
                    "new_model": self.model_config.model_name,
                }
            },
        )

    def get_usage_stats(self) -> Dict[str, Union[int, float]]:
        """
        Get token usage and cost statistics.

        Returns:
            Dictionary with usage stats

        Example:
            ```python
            client = GeminiClient()
            # ... perform several analyses ...
            stats = client.get_usage_stats()
            print(f"Total cost: ${stats['total_cost_usd']:.4f}")
            print(f"Total tokens: {stats['total_tokens']}")
            ```
        """
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "model": self.model_config.model_name,
        }

    def reset_usage_stats(self) -> None:
        """Reset token usage and cost tracking."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        logger.info("Usage stats reset")

    def _fix_json_string(self, json_str: str) -> str:
        """
        Attempt to fix common JSON formatting issues.

        Args:
            json_str: Potentially malformed JSON string

        Returns:
            Fixed JSON string
        """
        import re

        # Remove any trailing commas before } or ]
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

        # Fix unescaped newlines in strings (this is tricky and may not catch all cases)
        # This is a best-effort attempt

        return json_str

    def _extract_json(self, content: str) -> Dict:
        """
        Extract JSON from response content.

        Handles cases where JSON is wrapped in markdown code blocks.

        Args:
            content: Response content that may contain JSON

        Returns:
            Parsed JSON dict

        Raises:
            json.JSONDecodeError: If JSON cannot be extracted
        """
        # Try to extract JSON from markdown code blocks
        json_str = content.strip()

        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                json_str = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                json_str = content[start:end].strip()

        # Try to find JSON object if not already extracted
        if not json_str.startswith("{"):
            # Look for first { to last }
            start_idx = content.find("{")
            end_idx = content.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx + 1]

        # Try to fix common JSON issues
        json_str = self._fix_json_string(json_str)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON parse error: {e}",
                extra={
                    "extra_fields": {
                        "content_preview": content[:500],
                        "json_str_preview": json_str[:500] if len(json_str) > 0 else "empty",
                    }
                }
            )
            raise

    # Legacy methods (keeping for backward compatibility)

    @retry(max_attempts=3, delay=2.0)
    async def analyze_code_changes(
        self,
        files: List[FileChange],
        pr_title: str,
        pr_description: Optional[str] = None,
    ) -> str:
        """
        Analyze code changes using Gemini AI (legacy method).

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
        Build prompt for code analysis (legacy method).

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
        max_files = settings.features.max_files_per_review
        for file in files[:max_files]:
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

        if len(files) > max_files:
            prompt_parts.append(
                f"\n*Note: Showing {max_files} of {len(files)} files*"
            )

        return "\n".join(prompt_parts)

    @retry(max_attempts=3, delay=2.0)
    async def generate_review_summary(
        self,
        analysis: str,
        files_count: int,
    ) -> str:
        """
        Generate a concise summary of the review (legacy method).

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
