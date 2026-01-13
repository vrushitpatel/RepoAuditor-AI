"""Wrapper for CI/CD Generator to work with command router."""

from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from app.agents.cicd_generator import CICDGenerator
from app.integrations.gemini_client import GeminiClient
from app.utils.project_detector import ProjectDetector


class CICDAgentWrapper(BaseAgent):
    """Wrapper for CI/CD Generator that implements the router interface."""

    def __init__(self):
        """Initialize CI/CD agent wrapper."""
        super().__init__(
            name="CICDAgent",
            description="Generates customized CI/CD workflows for your project",
        )

    async def handle(self, context: AgentContext) -> AgentResponse:
        """
        Handle generate-ci command.

        Supports:
        - /generate-ci -> Generate all applicable workflows
        - /generate-ci all -> Generate all workflows
        - /generate-ci test -> Generate test workflow only
        - /generate-ci lint -> Generate lint workflow only
        - /generate-ci build -> Generate build workflow only
        - /generate-ci deploy -> Generate deploy workflow only

        Args:
            context: Agent context

        Returns:
            AgentResponse with generated workflows
        """
        self.log_start(context)

        try:
            # Parse workflow types from args
            workflow_types = self._parse_workflow_types(context.command_args)

            self.logger.info(
                f"Generating workflows: {workflow_types}",
                extra={
                    "extra_fields": {
                        "workflow_types": workflow_types,
                        "repo": context.repo_name,
                    }
                },
            )

            # Initialize clients
            if context.gemini_client is None:
                context.gemini_client = GeminiClient(use_flash=True)

            # Initialize CI/CD generator
            cicd_generator = CICDGenerator(
                gemini_client=context.gemini_client,
                github_client=context.github_client,
            )

            # Generate workflows
            workflows = await cicd_generator.generate_workflows(
                repo_name=context.repo_name,
                installation_id=context.installation_id,
                workflow_types=workflow_types,
                pr_number=context.pr_number,
            )

            if not workflows:
                raise ValueError("No workflows were generated")

            # Get project info for formatting
            detector = ProjectDetector(context.github_client)
            project_info = await detector.detect_project(
                repo_name=context.repo_name,
                installation_id=context.installation_id,
                pr_number=context.pr_number,
            )

            # Format workflows for comment
            formatted_message = cicd_generator.format_workflows_for_comment(
                workflows=workflows,
                project_info=project_info,
            )

            metadata = {
                "workflows_generated": len(workflows),
                "workflow_types": workflow_types,
                "project_type": project_info.project_type,
                "framework": project_info.framework,
            }

            self.log_success(context, metadata)

            return AgentResponse(
                success=True,
                message=formatted_message,
                metadata=metadata,
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)

    def _parse_workflow_types(self, args: str) -> list[str]:
        """
        Parse workflow types from command arguments.

        Args:
            args: Command arguments string

        Returns:
            List of workflow types to generate
        """
        args = args.strip().lower()

        # Default to "all" if no args
        if not args:
            return ["all"]

        # Split by spaces and filter valid types
        valid_types = {"all", "test", "lint", "build", "deploy"}
        types = [t for t in args.split() if t in valid_types]

        # Return "all" if no valid types found
        return types if types else ["all"]
