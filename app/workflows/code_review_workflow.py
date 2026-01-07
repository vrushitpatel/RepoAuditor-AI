"""Code review workflow using LangGraph."""

from typing import Dict

from langgraph.graph import StateGraph, END

from app.agents.code_reviewer import (
    analyze_code,
    fetch_pr_files,
    post_review,
    should_continue_review,
)
from app.agents.state import CodeReviewState
from app.models.webhook_events import PullRequestEvent
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_code_review_workflow() -> StateGraph:
    """
    Create the code review workflow graph.

    Returns:
        Configured workflow graph
    """
    workflow = StateGraph(CodeReviewState)

    # Add nodes
    workflow.add_node("fetch_files", fetch_pr_files)
    workflow.add_node("analyze", analyze_code)
    workflow.add_node("post", post_review)

    # Set entry point
    workflow.set_entry_point("fetch_files")

    # Add edges
    workflow.add_edge("fetch_files", "analyze")
    workflow.add_edge("analyze", "post")
    workflow.add_edge("post", END)

    return workflow


async def process_pull_request_review(event: PullRequestEvent) -> Dict[str, bool]:
    """
    Process a pull request review workflow.

    Args:
        event: Pull request webhook event

    Returns:
        Result indicating success or failure
    """
    logger.info(f"Starting review workflow for PR #{event.number}")

    # Initialize state
    initial_state: CodeReviewState = {
        "event": event,
        "installation_id": event.installation.id,
        "repo_full_name": event.repository.full_name,
        "pr_number": event.number,
        "pr_title": event.pull_request.title,
        "pr_description": event.pull_request.body,
        "commit_sha": event.pull_request.head["sha"],
        "files": [],
        "files_analyzed": False,
        "analysis": None,
        "summary": None,
        "comments": [],
        "review_posted": False,
        "jira_issue_created": False,
        "error": None,
    }

    try:
        # Create and compile workflow
        workflow = create_code_review_workflow()
        app = workflow.compile()

        # Execute workflow
        final_state = await app.ainvoke(initial_state)

        if final_state.get("error"):
            logger.error(f"Workflow completed with error: {final_state['error']}")
            return {"success": False, "error": final_state["error"]}

        logger.info(f"Review workflow completed for PR #{event.number}")
        return {"success": True}

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
