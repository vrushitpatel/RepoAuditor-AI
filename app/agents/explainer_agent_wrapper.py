"""Wrapper for ExplainerAgent to work with command router."""

from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from app.agents.explainer import ExplainerAgent as OriginalExplainerAgent
from app.integrations.gemini_client import GeminiClient


class ExplainerAgentWrapper(BaseAgent):
    """Wrapper for ExplainerAgent that implements the router interface."""

    def __init__(self):
        """Initialize explainer agent wrapper."""
        super().__init__(
            name="ExplainerAgent",
            description="Explains code changes with AI-powered insights",
        )

    async def handle(self, context: AgentContext) -> AgentResponse:
        """
        Handle explain command.

        Supports:
        - /explain -> Explain entire PR diff
        - /explain <file> -> Explain specific file
        - /explain <file>:<target> -> Explain specific function/class

        Args:
            context: Agent context

        Returns:
            AgentResponse with explanation
        """
        self.log_start(context)

        try:
            # Initialize original explainer
            if context.gemini_client is None:
                context.gemini_client = GeminiClient(use_flash=True)

            explainer = OriginalExplainerAgent(
                gemini_client=context.gemini_client,
                github_client=context.github_client,
            )

            # Determine what to explain based on command args
            file_reference = context.command_args.strip() if context.command_args else None

            if file_reference:
                # Explain specific file or function/class
                self.logger.info(f"Explaining reference: {file_reference}")
                response = await explainer.explain_from_reference(
                    repo_name=context.repo_name,
                    reference=file_reference,
                    installation_id=context.installation_id,
                    pr_number=context.pr_number,
                    context=f"From PR #{context.pr_number}: {context.pr_title}",
                    pr_title=context.pr_title,
                    ref=context.head_sha,
                )
            else:
                # Explain entire PR diff
                self.logger.info(f"Explaining PR diff")
                response = await explainer.explain_pr_diff(
                    repo_name=context.repo_name,
                    pr_number=context.pr_number,
                    installation_id=context.installation_id,
                    pr_title=context.pr_title,
                    pr_description=context.pr_description,
                )

            # Build metadata
            metadata = {
                "model_name": context.gemini_client.model_config.model_name,
                "tokens_used": response.tokens_used,
                "cost_usd": response.cost_usd,
            }

            self.log_success(context, metadata)

            return AgentResponse(
                success=True,
                message=response.explanation,
                metadata=metadata,
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)
