"""Command handler for /fix-security-issues."""

from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from app.workflows.security_fix_workflow import get_security_fix_workflow
from app.models.workflow_states import create_security_fix_state
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class FixSecurityHandler(BaseAgent):
    """Handler for /fix-security-issues command."""

    def __init__(self):
        """Initialize handler."""
        super().__init__(
            name="FixSecurityHandler",
            description="Scans for security issues, generates fixes, and creates PR",
        )

    async def handle(self, context: AgentContext) -> AgentResponse:
        """
        Handle /fix-security-issues command.

        Args:
            context: Agent context with PR and command details

        Returns:
            Agent response with workflow results
        """
        self.log_start(context)

        try:
            # Get PR details
            pr_details = context.github_client.get_pr_details(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
                installation_id=context.installation_id,
            )

            # Create initial state
            initial_state = create_security_fix_state(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
                installation_id=context.installation_id,
                github_client=context.github_client,
                gemini_client=context.gemini_client,
                command={"name": context.command, "commenter": context.commenter},
                pr_data={
                    "diff": pr_details.get("diff", ""),
                    "files": pr_details.get("files", []),
                },
            )

            # Execute workflow
            workflow = get_security_fix_workflow()
            final_state = await workflow.ainvoke(initial_state)

            # Extract result
            message = final_state.get("agent_result", "Workflow completed")
            success = final_state.get("error") is None

            self.log_success(context, final_state["metadata"])

            return AgentResponse(
                success=success,
                message=message,
                metadata=final_state["metadata"],
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)
