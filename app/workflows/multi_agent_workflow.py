"""Unified multi-agent workflow using LangGraph.

This module creates a single workflow that routes to different agents
based on event type (PR opened, command received, etc.).

Architecture:
    Entry → Route → Agent (Code Review/Explainer/Test/CICD) → Post Result → End
"""

from datetime import datetime
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState, Command
from app.integrations.github_client import GitHubClient
from app.integrations.gemini_client import GeminiClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# NODE: Initialize State
# ============================================================================

def initialize_state_node(state: AgentState) -> AgentState:
    """
    Initialize state from webhook event.

    This is the entry point that sets up metadata and validates the state.
    """
    logger.info(
        f"Initializing workflow for {state['event_type']}",
        extra={
            "extra_fields": {
                "event_type": state["event_type"],
                "repo": state.get("repo_name"),
                "pr": state.get("pr_number"),
            }
        }
    )

    # Initialize metadata if not present
    if "metadata" not in state or state["metadata"] is None:
        state["metadata"] = {
            "started_at": datetime.utcnow().isoformat(),
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "duration_seconds": 0.0,
        }

    # Initialize empty results
    if "agent_result" not in state:
        state["agent_result"] = None

    if "error" not in state:
        state["error"] = None

    return state


# ============================================================================
# NODE: Route to Agent
# ============================================================================

def route_to_agent_node(state: AgentState) -> AgentState:
    """
    Determine which agent should handle this event.

    Routing logic:
    - PR opened/synchronized → code_review
    - /explain command → explain
    - /test command → test
    - /generate-ci command → cicd
    - /review command → code_review
    """
    event_type = state["event_type"]
    command = state.get("command")

    logger.info(f"Routing event: {event_type}")

    # Route based on event type
    if event_type in ["pr_opened", "pr_synchronized", "pr_reopened"]:
        state["target_agent"] = "code_review"
        logger.info("Routing to code reviewer (PR event)")

    elif event_type == "command_created" and command:
        command_name = command["name"]

        if command_name == "explain":
            state["target_agent"] = "explain"
            logger.info("Routing to explainer (command)")
        elif command_name == "test":
            state["target_agent"] = "test"
            logger.info("Routing to test analyst (command)")
        elif command_name == "generate-ci":
            state["target_agent"] = "cicd"
            logger.info("Routing to CI/CD generator (command)")
        elif command_name == "review":
            state["target_agent"] = "code_review"
            logger.info("Routing to code reviewer (command)")
        else:
            state["error"] = f"Unknown command: {command_name}"
            state["target_agent"] = "error"
            logger.warning(f"Unknown command: {command_name}")

    else:
        state["error"] = f"Unsupported event type: {event_type}"
        state["target_agent"] = "error"
        logger.warning(f"Unsupported event type: {event_type}")

    return state


def determine_agent(state: AgentState) -> Literal["code_review", "explain", "test", "cicd", "error"]:
    """
    Conditional edge function that determines which agent to route to.

    Returns the target agent name for conditional edge routing.
    """
    target = state.get("target_agent", "error")
    logger.debug(f"Determined target agent: {target}")
    return target


# ============================================================================
# NODE: Code Review Agent
# ============================================================================

async def code_review_node(state: AgentState) -> AgentState:
    """
    Execute code review workflow.

    This wraps the existing code review workflow.
    """
    logger.info(
        "Executing code review",
        extra={
            "extra_fields": {
                "repo": state["repo_name"],
                "pr": state["pr_number"],
            }
        }
    )

    try:
        # Import here to avoid circular dependencies
        from app.workflows.executor import execute_workflow_from_state

        # Execute the code review workflow
        result = await execute_workflow_from_state(state)

        state["agent_result"] = result.get("summary", "Code review completed")
        state["metadata"].update({
            "tokens_used": result.get("tokens_used", 0),
            "cost_usd": result.get("cost_usd", 0.0),
        })

        logger.info("Code review completed successfully")

    except Exception as e:
        logger.error(f"Code review failed: {e}", exc_info=True)
        state["error"] = f"Code review failed: {str(e)}"
        state["agent_result"] = None

    return state


# ============================================================================
# NODE: Explainer Agent
# ============================================================================

async def explainer_node(state: AgentState) -> AgentState:
    """
    Execute explainer workflow.

    Explains code changes from PR or specific files.
    """
    logger.info(
        "Executing explainer",
        extra={
            "extra_fields": {
                "repo": state["repo_name"],
                "pr": state["pr_number"],
            }
        }
    )

    try:
        # Import here to avoid circular dependencies
        from app.agents.explainer_agent import ExplainerAgent

        github_client = state.get("github_client")
        gemini_client = state.get("gemini_client")

        if not github_client or not gemini_client:
            raise ValueError("Missing required clients")

        explainer = ExplainerAgent(
            gemini_client=gemini_client,
            github_client=github_client,
        )

        # Get command args if present
        command = state.get("command")
        file_reference = command["args"] if command and command.get("args") else None

        pr_data = state["pr_data"]

        if file_reference:
            # Explain specific file
            response = await explainer.explain_from_reference(
                repo_name=state["repo_name"],
                pr_number=state["pr_number"],
                installation_id=state["installation_id"],
                file_reference=file_reference,
                pr_title=pr_data.get("pr_title", ""),
                pr_description=pr_data.get("pr_description", ""),
                head_sha=pr_data.get("head_sha", ""),
                base_sha=pr_data.get("base_sha", ""),
            )
        else:
            # Explain entire PR
            response = await explainer.explain_pr_diff(
                repo_name=state["repo_name"],
                pr_number=state["pr_number"],
                installation_id=state["installation_id"],
                pr_title=pr_data.get("pr_title", ""),
                pr_description=pr_data.get("pr_description", ""),
                head_sha=pr_data.get("head_sha", ""),
                base_sha=pr_data.get("base_sha", ""),
            )

        state["agent_result"] = response.explanation
        state["metadata"].update({
            "tokens_used": response.tokens_used,
            "cost_usd": response.cost_usd,
            "model_name": "gemini-2.0-flash-exp",
        })

        logger.info("Explainer completed successfully")

    except Exception as e:
        logger.error(f"Explainer failed: {e}", exc_info=True)
        state["error"] = f"Explanation failed: {str(e)}"
        state["agent_result"] = None

    return state


# ============================================================================
# NODE: Test Analyst Agent
# ============================================================================

async def test_analyst_node(state: AgentState) -> AgentState:
    """
    Execute test analyst workflow.

    Analyzes test coverage and suggests improvements.
    """
    logger.info(
        "Executing test analyst",
        extra={
            "extra_fields": {
                "repo": state["repo_name"],
                "pr": state["pr_number"],
            }
        }
    )

    try:
        # Placeholder for test analyst implementation
        state["agent_result"] = (
            "## Test Analysis\n\n"
            "🚧 Test analyst agent is under development.\n\n"
            "This agent will:\n"
            "- Analyze test coverage\n"
            "- Identify missing tests\n"
            "- Suggest test improvements\n"
            "- Check test quality\n"
        )

        logger.info("Test analyst completed (placeholder)")

    except Exception as e:
        logger.error(f"Test analyst failed: {e}", exc_info=True)
        state["error"] = f"Test analysis failed: {str(e)}"
        state["agent_result"] = None

    return state


# ============================================================================
# NODE: CI/CD Generator Agent
# ============================================================================

async def cicd_generator_node(state: AgentState) -> AgentState:
    """
    Execute CI/CD generator workflow.

    Generates GitHub Actions workflows.
    """
    logger.info(
        "Executing CI/CD generator",
        extra={
            "extra_fields": {
                "repo": state["repo_name"],
                "pr": state["pr_number"],
            }
        }
    )

    try:
        # Import here to avoid circular dependencies
        from app.agents.cicd_generator import CICDGenerator

        github_client = state.get("github_client")
        gemini_client = state.get("gemini_client")

        if not github_client or not gemini_client:
            raise ValueError("Missing required clients")

        generator = CICDGenerator(
            gemini_client=gemini_client,
            github_client=github_client,
        )

        # Parse workflow types from command args
        command = state.get("command")
        workflow_types_str = command["args"] if command and command.get("args") else "all"

        # Parse workflow types
        if workflow_types_str.lower() in ["all", ""]:
            workflow_types = ["test", "lint", "build", "deploy"]
        else:
            workflow_types = [wt.strip() for wt in workflow_types_str.split()]

        # Generate workflows
        workflows = await generator.generate_workflows(
            repo_name=state["repo_name"],
            installation_id=state["installation_id"],
            workflow_types=workflow_types,
            pr_number=state["pr_number"],
        )

        # Format result
        result_lines = ["## CI/CD Workflows Generated\n"]
        for wf in workflows:
            result_lines.append(f"### {wf['name']}\n")
            result_lines.append(f"```yaml\n{wf['content']}\n```\n")

        state["agent_result"] = "\n".join(result_lines)
        state["metadata"].update({
            "workflows_generated": len(workflows),
            "workflow_types": workflow_types,
        })

        logger.info(f"CI/CD generator completed ({len(workflows)} workflows)")

    except Exception as e:
        logger.error(f"CI/CD generator failed: {e}", exc_info=True)
        state["error"] = f"CI/CD generation failed: {str(e)}"
        state["agent_result"] = None

    return state


# ============================================================================
# NODE: Post Result
# ============================================================================

async def post_result_node(state: AgentState) -> AgentState:
    """
    Post agent result to GitHub.

    This node posts the result as a comment on the PR.
    """
    logger.info("Posting result to GitHub")

    try:
        github_client = state.get("github_client")
        if not github_client:
            raise ValueError("GitHub client not available")

        # Get result or error message
        message = state.get("agent_result") or state.get("error", "No result")

        # Add metadata footer
        metadata = state.get("metadata", {})
        if metadata:
            footer_parts = []
            if "tokens_used" in metadata:
                footer_parts.append(f"🔢 Tokens: {metadata['tokens_used']}")
            if "cost_usd" in metadata:
                footer_parts.append(f"💰 Cost: ${metadata['cost_usd']:.4f}")
            if "duration_seconds" in metadata:
                footer_parts.append(f"⏱️ Duration: {metadata['duration_seconds']:.2f}s")

            if footer_parts:
                message += f"\n\n---\n*{' • '.join(footer_parts)}*"

        # Post comment
        command = state.get("command")
        if command and command.get("comment_id"):
            # Reply to command comment
            github_client.post_pr_comment(
                repo_name=state["repo_name"],
                pr_number=state["pr_number"],
                installation_id=state["installation_id"],
                comment_body=message,
            )
        else:
            # Post new comment for PR events
            github_client.post_pr_comment(
                repo_name=state["repo_name"],
                pr_number=state["pr_number"],
                installation_id=state["installation_id"],
                comment_body=message,
            )

        logger.info("Result posted to GitHub successfully")

    except Exception as e:
        logger.error(f"Failed to post result: {e}", exc_info=True)
        state["error"] = f"Failed to post result: {str(e)}"

    return state


# ============================================================================
# NODE: Handle Error
# ============================================================================

async def handle_error_node(state: AgentState) -> AgentState:
    """
    Handle agent execution errors.

    Posts error message to GitHub.
    """
    logger.error(f"Handling error: {state.get('error')}")

    error_message = (
        "## ❌ Error\n\n"
        f"{state.get('error', 'Unknown error occurred')}\n\n"
        "Please check the logs for more details."
    )

    state["agent_result"] = error_message

    # Post error to GitHub
    return await post_result_node(state)


# ============================================================================
# WORKFLOW: Create Multi-Agent Workflow
# ============================================================================

def create_multi_agent_workflow() -> StateGraph:
    """
    Create the unified multi-agent workflow.

    This workflow routes to different agents based on event type:
    - PR opened → Code Reviewer
    - /explain command → Explainer
    - /test command → Test Analyst
    - /generate-ci command → CI/CD Generator

    Returns:
        Compiled StateGraph workflow
    """
    logger.info("Creating multi-agent workflow")

    # Create graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("initialize", initialize_state_node)
    graph.add_node("route", route_to_agent_node)
    graph.add_node("code_reviewer", code_review_node)
    graph.add_node("explainer", explainer_node)
    graph.add_node("test_analyst", test_analyst_node)
    graph.add_node("cicd_generator", cicd_generator_node)
    graph.add_node("post_result", post_result_node)
    graph.add_node("error", handle_error_node)

    # Set entry point
    graph.set_entry_point("initialize")

    # Connect initialize to route
    graph.add_edge("initialize", "route")

    # Conditional routing based on target agent
    graph.add_conditional_edges(
        "route",
        determine_agent,
        {
            "code_review": "code_reviewer",
            "explain": "explainer",
            "test": "test_analyst",
            "cicd": "cicd_generator",
            "error": "error",
        }
    )

    # All agents go to post_result
    graph.add_edge("code_reviewer", "post_result")
    graph.add_edge("explainer", "post_result")
    graph.add_edge("test_analyst", "post_result")
    graph.add_edge("cicd_generator", "post_result")

    # Post result and error both end
    graph.add_edge("post_result", END)
    graph.add_edge("error", END)

    logger.info("Multi-agent workflow created successfully")

    return graph.compile()


# ============================================================================
# WORKFLOW INSTANCE: Global Singleton
# ============================================================================

_workflow_instance = None


def get_multi_agent_workflow() -> StateGraph:
    """
    Get the global multi-agent workflow instance.

    Returns:
        Compiled workflow instance
    """
    global _workflow_instance

    if _workflow_instance is None:
        _workflow_instance = create_multi_agent_workflow()
        logger.info("Multi-agent workflow singleton initialized")

    return _workflow_instance
