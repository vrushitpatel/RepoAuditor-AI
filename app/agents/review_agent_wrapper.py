"""Wrapper for code review workflow to work with command router."""

from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from app.workflows.executor import execute_code_review_workflow


class ReviewAgentWrapper(BaseAgent):
    """Wrapper for code review workflow that implements the router interface."""

    def __init__(self):
        """Initialize review agent wrapper."""
        super().__init__(
            name="ReviewAgent",
            description="Performs comprehensive AI-powered code review",
        )

    async def handle(self, context: AgentContext) -> AgentResponse:
        """
        Handle review command.

        Executes comprehensive code review workflow that checks for:
        - Security vulnerabilities
        - Performance issues
        - Code quality
        - Best practices
        - Bug risks

        Args:
            context: Agent context

        Returns:
            AgentResponse with review results
        """
        self.log_start(context)

        try:
            # Execute code review workflow
            result = await execute_code_review_workflow(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
                installation_id=context.installation_id,
                pr_title=context.pr_title,
                pr_author=context.pr_author,
                pr_description=context.pr_description,
                commit_sha=context.head_sha,
            )

            if result.get("error"):
                error_msg = result.get("error", "Unknown error")
                self.logger.error(f"Review workflow failed: {error_msg}")
                raise ValueError(error_msg)

            # Extract review results
            review_results = result.get("review_results", [])
            findings_count = len(review_results)

            # Get metadata
            metadata_info = result.get("metadata", {})
            tokens_used = metadata_info.get("total_tokens", 0)
            cost_usd = metadata_info.get("total_cost_usd", 0.0)

            # Format review message (the workflow already posts to GitHub,
            # but we return the message for consistency)
            message = f"""## ✅ Code Review Completed

Found **{findings_count}** findings in this pull request.

The detailed review has been posted to the PR. Check the comments for specific suggestions and improvements.

### Review Summary
- **Findings:** {findings_count}
- **Files Analyzed:** {result.get('files_analyzed', 'N/A')}
- **Analysis Time:** {result.get('duration', 'N/A')}

Use `/help` to see other available commands.
"""

            metadata = {
                "findings_count": findings_count,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "model_name": "gemini-2.5-flash",
            }

            self.log_success(context, metadata)

            return AgentResponse(
                success=True,
                message=message,
                metadata=metadata,
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)
