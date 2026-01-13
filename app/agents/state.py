"""Shared state definitions for LangGraph agents."""

from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
from copy import deepcopy

from app.models.webhook_events import FileChange, PullRequestEvent, ReviewComment


class Command(TypedDict):
    """Command structure extracted from comments."""

    name: str  # Command name (e.g., "explain", "review", "test")
    args: str  # Command arguments
    commenter: str  # Who issued the command
    comment_id: int  # GitHub comment ID


class AgentState(TypedDict):
    """
    State for multi-agent workflow.

    This state flows through the unified LangGraph workflow,
    enabling routing between different agents based on event type.
    """

    # Event information
    event_type: str  # "pr_opened", "pr_synchronized", "command_created"

    # Command information (for command events)
    command: Optional[Command]

    # PR data
    pr_data: Dict[str, Any]  # Full PR details (repo, number, sha, etc.)

    # Agent execution results
    agent_result: Optional[str]  # Result from agent execution (markdown)

    # Error handling
    error: Optional[str]  # Error message if execution failed

    # Metadata
    metadata: Dict[str, Any]  # Additional metadata (tokens, cost, duration, etc.)

    # Routing information
    target_agent: Optional[str]  # Which agent to route to

    # GitHub context
    installation_id: int
    repo_name: str
    pr_number: int

    # Clients (passed through workflow)
    github_client: Optional[Any]  # GitHubClient instance
    gemini_client: Optional[Any]  # GeminiClient instance


class WorkflowState(TypedDict):
    """
    General workflow state for LangGraph orchestration.

    This state is managed in-memory by LangGraph during workflow execution.
    No database persistence is required.
    """

    # PR and repository data
    pr_data: Dict[str, Any]  # Contains: repo_name, pr_number, diff, files, etc.

    # Review findings and results
    review_results: List[Dict[str, Any]]  # List of findings from code analysis

    # Workflow tracking
    current_step: str  # Current step in the workflow (e.g., "analyzing", "reviewing", "posting")

    # Error handling
    error: Optional[str]  # Error message if workflow fails

    # Metadata for tracking and analytics
    metadata: Dict[str, Any]  # Contains: timestamps, costs, token_usage, model_info, etc.


class CodeReviewState(TypedDict):
    """State for code review workflow."""

    # Input data
    event: PullRequestEvent
    installation_id: int
    repo_full_name: str
    pr_number: int
    pr_title: str
    pr_description: Optional[str]
    commit_sha: str

    # Files to review
    files: List[FileChange]
    files_analyzed: bool

    # AI analysis
    analysis: Optional[str]
    summary: Optional[str]

    # Review comments
    comments: List[ReviewComment]

    # Status tracking
    review_posted: bool
    jira_issue_created: bool
    error: Optional[str]


# State Helper Functions

def create_initial_workflow_state(
    repo_name: str,
    pr_number: int,
    diff: str = "",
    files: Optional[List[Dict[str, Any]]] = None,
    **extra_pr_data
) -> WorkflowState:
    """
    Create a new workflow state with initial values.

    Args:
        repo_name: Full repository name (owner/repo)
        pr_number: Pull request number
        diff: Git diff content
        files: List of changed files
        **extra_pr_data: Additional PR data to include

    Returns:
        Initialized WorkflowState
    """
    return WorkflowState(
        pr_data={
            "repo_name": repo_name,
            "pr_number": pr_number,
            "diff": diff,
            "files": files or [],
            **extra_pr_data
        },
        review_results=[],
        current_step="initialized",
        error=None,
        metadata={
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "model_calls": 0,
        }
    )


def update_state(state: WorkflowState, **kwargs) -> WorkflowState:
    """
    Update workflow state immutably.

    Creates a deep copy of the state and applies updates.
    This ensures LangGraph can track state changes properly.

    Args:
        state: Current workflow state
        **kwargs: Fields to update

    Returns:
        New WorkflowState with updates applied

    Example:
        new_state = update_state(
            state,
            current_step="analyzing",
            metadata={**state["metadata"], "model_calls": state["metadata"]["model_calls"] + 1}
        )
    """
    new_state = deepcopy(state)

    # Update the timestamp whenever state changes
    if "metadata" in new_state:
        new_state["metadata"]["updated_at"] = datetime.utcnow().isoformat()

    # Apply all updates
    for key, value in kwargs.items():
        if key in new_state:
            new_state[key] = value

    return new_state


def add_review_finding(
    state: WorkflowState,
    finding: Dict[str, Any]
) -> WorkflowState:
    """
    Add a review finding to the state immutably.

    Args:
        state: Current workflow state
        finding: Finding to add (should contain: severity, type, title, description, etc.)

    Returns:
        New WorkflowState with finding added
    """
    new_results = state["review_results"].copy()
    new_results.append(finding)

    return update_state(state, review_results=new_results)


def set_error(state: WorkflowState, error_message: str) -> WorkflowState:
    """
    Set an error on the workflow state.

    Args:
        state: Current workflow state
        error_message: Error message to set

    Returns:
        New WorkflowState with error set and step updated
    """
    return update_state(
        state,
        error=error_message,
        current_step="failed"
    )


def update_metadata(
    state: WorkflowState,
    cost_usd: float = 0.0,
    tokens: int = 0,
    model_call: bool = False,
    **extra_metadata
) -> WorkflowState:
    """
    Update workflow metadata immutably.

    Args:
        state: Current workflow state
        cost_usd: Cost to add to total
        tokens: Tokens to add to total
        model_call: Whether to increment model call count
        **extra_metadata: Additional metadata fields to add/update

    Returns:
        New WorkflowState with metadata updated
    """
    current_metadata = state["metadata"].copy()

    # Update cumulative values
    current_metadata["total_cost_usd"] = current_metadata.get("total_cost_usd", 0.0) + cost_usd
    current_metadata["total_tokens"] = current_metadata.get("total_tokens", 0) + tokens

    if model_call:
        current_metadata["model_calls"] = current_metadata.get("model_calls", 0) + 1

    # Add any extra metadata
    current_metadata.update(extra_metadata)
    current_metadata["updated_at"] = datetime.utcnow().isoformat()

    return update_state(state, metadata=current_metadata)


# State Validation Functions

def validate_workflow_state(state: WorkflowState) -> tuple[bool, Optional[str]]:
    """
    Validate that workflow state has all required fields and correct types.

    Args:
        state: Workflow state to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required top-level keys
    required_keys = {"pr_data", "review_results", "current_step", "error", "metadata"}
    missing_keys = required_keys - set(state.keys())

    if missing_keys:
        return False, f"Missing required keys: {missing_keys}"

    # Validate pr_data structure
    if not isinstance(state["pr_data"], dict):
        return False, "pr_data must be a dictionary"

    required_pr_keys = {"repo_name", "pr_number"}
    missing_pr_keys = required_pr_keys - set(state["pr_data"].keys())

    if missing_pr_keys:
        return False, f"pr_data missing required keys: {missing_pr_keys}"

    # Validate review_results is a list
    if not isinstance(state["review_results"], list):
        return False, "review_results must be a list"

    # Validate current_step is a string
    if not isinstance(state["current_step"], str):
        return False, "current_step must be a string"

    # Validate error is optional string
    if state["error"] is not None and not isinstance(state["error"], str):
        return False, "error must be None or a string"

    # Validate metadata is a dict
    if not isinstance(state["metadata"], dict):
        return False, "metadata must be a dictionary"

    return True, None


def validate_pr_data(pr_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate PR data structure.

    Args:
        pr_data: PR data dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_keys = {"repo_name", "pr_number"}
    missing_keys = required_keys - set(pr_data.keys())

    if missing_keys:
        return False, f"PR data missing required keys: {missing_keys}"

    # Validate repo_name format
    if not isinstance(pr_data["repo_name"], str) or "/" not in pr_data["repo_name"]:
        return False, "repo_name must be in format 'owner/repo'"

    # Validate pr_number is positive integer
    if not isinstance(pr_data["pr_number"], int) or pr_data["pr_number"] <= 0:
        return False, "pr_number must be a positive integer"

    # Validate files if present
    if "files" in pr_data:
        if not isinstance(pr_data["files"], list):
            return False, "files must be a list"

    return True, None


def validate_finding(finding: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate a review finding structure.

    Args:
        finding: Finding dictionary to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    recommended_keys = {"severity", "type", "title", "description"}

    if not isinstance(finding, dict):
        return False, "Finding must be a dictionary"

    # Check for recommended keys (warning, not error)
    missing_keys = recommended_keys - set(finding.keys())
    if missing_keys:
        # This is just a warning - findings can have different structures
        pass

    # Validate severity if present
    valid_severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
    if "severity" in finding and finding["severity"] not in valid_severities:
        return False, f"Invalid severity. Must be one of: {valid_severities}"

    return True, None
