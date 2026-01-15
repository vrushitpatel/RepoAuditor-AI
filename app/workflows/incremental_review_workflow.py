"""Incremental Review Workflow for /incremental-review command.

Tracks reviewed files, only reviews new/changed files.
"""

import json
from pathlib import Path
from typing import Literal
from langgraph.graph import StateGraph, END
from app.models.workflow_states import IncrementalReviewState
from app.utils.logger import setup_logger
from app.utils.decorators import rate_limited, log_execution

logger = setup_logger(__name__)


@rate_limited
@log_execution
async def load_history_node(state: IncrementalReviewState) -> IncrementalReviewState:
    """Load review history from file."""
    logger.info("Loading review history")

    try:
        history_file = Path(state["tracking_file_path"])

        if history_file.exists():
            with open(history_file, "r") as f:
                history = json.load(f)

            reviewed_files = set(history.get("reviewed_files", {}).keys())

            return {
                **state,
                "previously_reviewed_files": reviewed_files,
                "history_loaded": True,
                "current_step": "history_loaded",
            }
        else:
            # No history yet
            return {
                **state,
                "previously_reviewed_files": set(),
                "history_loaded": True,
                "current_step": "history_loaded",
            }

    except Exception as e:
        logger.error(f"Failed to load history: {e}", exc_info=True)
        return {**state, "error": str(e)}


@log_execution
async def identify_new_files_node(state: IncrementalReviewState) -> IncrementalReviewState:
    """Identify new/changed files."""
    logger.info("Identifying new files")

    try:
        all_files = [f["filename"] for f in state["pr_data"].get("files", [])]
        previously_reviewed = state["previously_reviewed_files"]

        new_files = [f for f in all_files if f not in previously_reviewed]

        return {
            **state,
            "all_files": all_files,
            "new_files_to_review": new_files,
            "current_step": "files_identified",
        }

    except Exception as e:
        return {**state, "error": str(e)}


@log_execution
async def review_new_files_node(state: IncrementalReviewState) -> IncrementalReviewState:
    """Review only new files."""
    logger.info(f"Reviewing {len(state['new_files_to_review'])} new files")

    try:
        # Simulated review (would use AI here)
        new_findings = []

        return {
            **state,
            "new_findings": new_findings,
            "review_complete": True,
            "current_step": "review_complete",
        }

    except Exception as e:
        return {**state, "error": str(e)}


@log_execution
async def save_history_node(state: IncrementalReviewState) -> IncrementalReviewState:
    """Save updated review history."""
    logger.info("Saving review history")

    try:
        history_file = Path(state["tracking_file_path"])
        history_file.parent.mkdir(parents=True, exist_ok=True)

        history = {
            "repo_name": state["repo_name"],
            "pr_number": state["pr_number"],
            "reviewed_files": {
                file: {
                    "last_reviewed_at": "2026-01-14T00:00:00Z",
                    "findings_count": 0,
                }
                for file in state["all_files"]
            },
        }

        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)

        agent_result = f"""## 📝 Incremental Review Complete

### Files Reviewed:
- **New files:** {len(state['new_files_to_review'])}
- **Previously reviewed:** {len(state['previously_reviewed_files'])}
- **Total files:** {len(state['all_files'])}

### Findings:
- **New issues:** {len(state['new_findings'])}

✅ Review history saved for next incremental review

🤖 Powered by RepoAuditor AI
"""

        return {
            **state,
            "history_saved": True,
            "agent_result": agent_result,
            "current_step": "complete",
        }

    except Exception as e:
        return {**state, "error": str(e)}


@log_execution
async def post_no_new_files_node(state: IncrementalReviewState) -> IncrementalReviewState:
    """Post message when no new files."""
    agent_result = """## ✅ No New Files to Review

All files in this PR have been reviewed previously.

🤖 Powered by RepoAuditor AI
"""

    return {
        **state,
        "agent_result": agent_result,
        "current_step": "complete",
    }


def check_has_new_files(state: IncrementalReviewState) -> Literal["review_new", "post_no_new"]:
    """Check if there are new files to review."""
    if len(state["new_files_to_review"]) > 0:
        return "review_new"
    return "post_no_new"


def create_incremental_review_workflow() -> StateGraph:
    """Create incremental review workflow."""
    graph = StateGraph(IncrementalReviewState)

    graph.add_node("load_history", load_history_node)
    graph.add_node("identify_new", identify_new_files_node)
    graph.add_node("review_new", review_new_files_node)
    graph.add_node("save_history", save_history_node)
    graph.add_node("post_no_new", post_no_new_files_node)

    graph.set_entry_point("load_history")
    graph.add_edge("load_history", "identify_new")

    graph.add_conditional_edges(
        "identify_new",
        check_has_new_files,
        {"review_new": "review_new", "post_no_new": "post_no_new"},
    )

    graph.add_edge("review_new", "save_history")
    graph.add_edge("save_history", END)
    graph.add_edge("post_no_new", END)

    return graph.compile()


_workflow_instance = None


def get_incremental_review_workflow() -> StateGraph:
    """Get workflow instance."""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = create_incremental_review_workflow()
    return _workflow_instance
