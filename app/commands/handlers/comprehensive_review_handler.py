"""Command handler for /comprehensive-review."""

from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from app.workflows.comprehensive_review_workflow import get_comprehensive_review_workflow
from app.models.workflow_states import create_comprehensive_review_state
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ComprehensiveReviewHandler(BaseAgent):
    """Handler for /comprehensive-review command."""

    def __init__(self):
        """Initialize handler."""
        super().__init__(
            name="ComprehensiveReviewHandler",
            description="Runs parallel security, performance, and quality analysis",
        )

    async def handle(self, context: AgentContext) -> AgentResponse:
        """Handle /comprehensive-review command."""
        self.log_start(context)

        try:
            pr_details = context.github_client.get_pr_details(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
                installation_id=context.installation_id,
            )

            # Fetch PR diff separately (get_pr_details doesn't include the unified diff)
            pr_diff = context.github_client.get_pr_diff(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
                installation_id=context.installation_id,
            )

            initial_state = create_comprehensive_review_state(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
                installation_id=context.installation_id,
                github_client=context.github_client,
                gemini_client=context.gemini_client,
                command={"name": context.command, "commenter": context.commenter},
                pr_data={"diff": pr_diff, "files": pr_details.get("files", [])},
            )

            workflow = get_comprehensive_review_workflow()
            final_state = await workflow.ainvoke(initial_state)

            message = final_state.get("agent_result", "Review completed")
            success = final_state.get("error") is None

            self.log_success(context, final_state["metadata"])

            return AgentResponse(success=success, message=message, metadata=final_state["metadata"])

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)
