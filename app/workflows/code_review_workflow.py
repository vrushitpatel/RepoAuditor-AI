"""LangGraph workflow definition for automated code review.

This module defines the code review workflow graph with conditional routing
based on severity of issues found. The workflow orchestrates multiple agents
to fetch PR data, analyze code, classify findings, and post results.

Workflow Steps:
1. start → Initialize state
2. fetch_pr → Get PR details and diff from GitHub
3. review_code → AI-powered code analysis
4. classify_severity → Categorize findings by severity
5. post_review → Post results to GitHub
6. check_critical → Determine if approval needed
7a. If critical → request_approval → end
7b. If no critical → end
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from app.agents.state import WorkflowState
from app.workflows.nodes import (
    start_node,
    fetch_pr_node,
    review_code_node,
    classify_severity_node,
    post_review_node,
    check_critical_node,
    request_approval_node,
    end_node,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# Conditional Routing Functions
# ============================================================================

def should_request_approval(state: WorkflowState) -> Literal["request_approval", "end"]:
    """
    Determine if approval should be requested based on severity of issues.

    This is a conditional routing function used after check_critical node.
    Routes to request_approval if critical or high severity issues found,
    otherwise routes directly to end.

    Args:
        state: Current workflow state with metadata

    Returns:
        "request_approval" if critical/high issues found, "end" otherwise
    """
    requires_approval = state["metadata"].get("requires_approval", False)

    if requires_approval:
        logger.info("Critical/high severity issues found - routing to approval request")
        return "request_approval"
    else:
        logger.info("No critical issues - routing to end")
        return "end"


def should_skip_review(state: WorkflowState) -> Literal["review_code", "end"]:
    """
    Determine if code review should be skipped.

    Skips review if:
    - No diff available
    - No files changed
    - Error occurred in previous step

    Args:
        state: Current workflow state

    Returns:
        "review_code" to continue, "end" to skip
    """
    # Skip if error occurred
    if state.get("error"):
        logger.warning("Error detected - skipping review")
        return "end"

    # Skip if no diff
    diff = state["pr_data"].get("diff", "")
    if not diff:
        logger.warning("No diff available - skipping review")
        return "end"

    # Skip if no files changed
    files_count = len(state["pr_data"].get("files", []))
    if files_count == 0:
        logger.warning("No files changed - skipping review")
        return "end"

    logger.info(f"Proceeding with review of {files_count} files")
    return "review_code"


# ============================================================================
# Workflow Graph Definition
# ============================================================================

def create_code_review_workflow() -> StateGraph:
    """
    Create and configure the code review workflow graph.

    Graph Structure:
    ```
    start
      ↓
    fetch_pr
      ↓
    review_code (conditional: may skip if no diff)
      ↓
    classify_severity
      ↓
    post_review
      ↓
    check_critical
      ↓
    [conditional routing]
      ├─→ request_approval → end (if critical issues)
      └─→ end (if no critical issues)
    ```

    Returns:
        Configured StateGraph ready to compile
    """
    logger.info("Creating code review workflow graph")

    # Initialize graph with WorkflowState schema
    workflow = StateGraph(WorkflowState)

    # ========================================================================
    # Add Nodes
    # ========================================================================

    # Node 1: Initialize workflow
    workflow.add_node("start", start_node)

    # Node 2: Fetch PR details from GitHub (async)
    workflow.add_node("fetch_pr", fetch_pr_node)

    # Node 3: Run AI code review (async)
    workflow.add_node("review_code", review_code_node)

    # Node 4: Classify findings by severity
    workflow.add_node("classify_severity", classify_severity_node)

    # Node 5: Post review to GitHub (async)
    workflow.add_node("post_review", post_review_node)

    # Node 6: Check if critical issues found
    workflow.add_node("check_critical", check_critical_node)

    # Node 7: Request approval for critical issues (async)
    workflow.add_node("request_approval", request_approval_node)

    # Node 8: Finalize workflow
    workflow.add_node("end", end_node)

    # ========================================================================
    # Set Entry Point
    # ========================================================================

    workflow.set_entry_point("start")

    # ========================================================================
    # Add Edges (Sequential Flow)
    # ========================================================================

    # start → fetch_pr
    workflow.add_edge("start", "fetch_pr")

    # fetch_pr → review_code (with conditional skip)
    workflow.add_conditional_edges(
        "fetch_pr",
        should_skip_review,
        {
            "review_code": "review_code",
            "end": "end"
        }
    )

    # review_code → classify_severity
    workflow.add_edge("review_code", "classify_severity")

    # classify_severity → post_review
    workflow.add_edge("classify_severity", "post_review")

    # post_review → check_critical
    workflow.add_edge("post_review", "check_critical")

    # check_critical → [conditional routing]
    workflow.add_conditional_edges(
        "check_critical",
        should_request_approval,
        {
            "request_approval": "request_approval",
            "end": "end"
        }
    )

    # request_approval → end
    workflow.add_edge("request_approval", "end")

    # end → END (terminal node)
    workflow.add_edge("end", END)

    logger.info("Workflow graph created successfully")

    return workflow


def compile_workflow() -> StateGraph:
    """
    Create and compile the workflow graph.

    Returns:
        Compiled workflow ready for execution

    Example:
        ```python
        workflow = compile_workflow()
        result = await workflow.ainvoke(initial_state)
        ```
    """
    graph = create_code_review_workflow()
    compiled = graph.compile()

    logger.info("Workflow compiled and ready for execution")

    return compiled


# ============================================================================
# Workflow Visualization
# ============================================================================

def visualize_workflow() -> str:
    """
    Generate ASCII visualization of the workflow graph.

    Returns:
        ASCII diagram of workflow structure
    """
    return """
Code Review Workflow Graph
═══════════════════════════

    ┌─────────┐
    │  START  │  Initialize workflow state
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ FETCH_PR│  Get PR details & diff from GitHub
    └────┬────┘
         │
         ▼
    ┌──────────────┐
    │ Conditional  │  Has diff & files?
    └──┬────────┬──┘
       │ Yes    │ No
       ▼        └─────────────────┐
    ┌─────────────┐               │
    │ REVIEW_CODE │  AI analysis  │
    └──────┬──────┘               │
           │                      │
           ▼                      │
    ┌───────────────────┐         │
    │ CLASSIFY_SEVERITY │         │
    └─────────┬─────────┘         │
              │                   │
              ▼                   │
    ┌──────────────┐              │
    │ POST_REVIEW  │  Post to PR │
    └──────┬───────┘              │
           │                      │
           ▼                      │
    ┌───────────────┐             │
    │ CHECK_CRITICAL│             │
    └───┬───────┬───┘             │
        │ Crit  │ OK              │
        │       └──────────┬──────┘
        ▼                  │
    ┌──────────────────┐  │
    │ REQUEST_APPROVAL │  │
    └────────┬─────────┘  │
             │            │
             ▼            ▼
           ┌───────────────┐
           │      END      │  Finalize & log metrics
           └───────────────┘
                   │
                   ▼
                 (DONE)

Legend:
───────
  │ ▼   = Sequential flow
  ├─┤   = Conditional branch
  ■     = Node/Step
  ()    = Terminal state
"""


# ============================================================================
# Workflow Metadata
# ============================================================================

def get_workflow_info() -> dict:
    """
    Get information about the workflow structure.

    Returns:
        Dictionary with workflow metadata
    """
    return {
        "name": "Code Review Workflow",
        "version": "1.0.0",
        "description": "LangGraph-based automated code review with conditional routing",
        "nodes": [
            {
                "name": "start",
                "description": "Initialize workflow state from webhook",
                "type": "sync"
            },
            {
                "name": "fetch_pr",
                "description": "Fetch PR details and diff from GitHub",
                "type": "async"
            },
            {
                "name": "review_code",
                "description": "AI-powered code analysis with Gemini",
                "type": "async"
            },
            {
                "name": "classify_severity",
                "description": "Classify findings by severity level",
                "type": "sync"
            },
            {
                "name": "post_review",
                "description": "Post review results to GitHub PR",
                "type": "async"
            },
            {
                "name": "check_critical",
                "description": "Check if critical issues found",
                "type": "sync"
            },
            {
                "name": "request_approval",
                "description": "Request manual approval for critical issues",
                "type": "async"
            },
            {
                "name": "end",
                "description": "Finalize workflow and log metrics",
                "type": "sync"
            }
        ],
        "conditional_edges": [
            {
                "from": "fetch_pr",
                "function": "should_skip_review",
                "routes": ["review_code", "end"]
            },
            {
                "from": "check_critical",
                "function": "should_request_approval",
                "routes": ["request_approval", "end"]
            }
        ],
        "features": [
            "Immutable state management",
            "Conditional routing based on findings",
            "Cost tracking and analytics",
            "Error handling at each node",
            "GitHub integration",
            "AI-powered analysis",
            "Automated approval requests"
        ]
    }


# ============================================================================
# Main Entry Point (for testing)
# ============================================================================

if __name__ == "__main__":
    # Print workflow visualization
    print(visualize_workflow())

    # Print workflow info
    import json
    print("\nWorkflow Information:")
    print(json.dumps(get_workflow_info(), indent=2))

    # Create and compile workflow
    print("\nCompiling workflow...")
    workflow = compile_workflow()
    print("✓ Workflow compiled successfully!")
