# AI Agent Architecture - LangGraph State Management Explained

This document provides a comprehensive explanation of RepoAuditor AI's LangGraph-based agent architecture and state management system.

## Table of Contents

### Part 1: State Management

1. [Overview](#overview)
2. [What is LangGraph?](#what-is-langgraph)
3. [Why LangGraph for Code Review?](#why-langgraph-for-code-review)
4. [State Management Architecture](#state-management-architecture)
5. [The WorkflowState Schema](#the-workflowstate-schema)
6. [Immutability Pattern](#immutability-pattern)
7. [State Helper Functions](#state-helper-functions)
8. [State Validation](#state-validation)
9. [Real-World Workflow Examples](#real-world-workflow-examples)
10. [Best Practices](#best-practices)
11. [Common Patterns](#common-patterns)
12. [Troubleshooting](#troubleshooting)

### Part 2: Workflow Orchestration

13. [LangGraph Workflow Architecture](#langgraph-workflow-architecture)
14. [Workflow Graph Structure](#workflow-graph-structure)
15. [Workflow Nodes Explained](#workflow-nodes-explained)
16. [Conditional Routing](#conditional-routing)
17. [Error Handling in Workflows](#error-handling-in-workflows)
18. [Workflow Execution](#workflow-execution)
19. [Testing Workflows](#testing-workflows)
20. [Workflow Best Practices](#workflow-best-practices)

---

## Overview

RepoAuditor AI uses **LangGraph**, a library for building stateful, multi-agent AI applications with LLMs. Our implementation focuses on orchestrating complex code review workflows with proper state management, cost tracking, and error handling.

### Key Design Principles

1. **Immutability**: All state updates create new state objects, never mutating existing ones
2. **Type Safety**: TypedDict ensures compile-time type checking and IDE support
3. **No Database**: State lives entirely in memory during workflow execution
4. **Pure Functions**: State helper functions are side-effect free
5. **Cost Awareness**: Built-in tracking for API costs and token usage

---

## What is LangGraph?

**LangGraph** is a framework for building stateful, multi-agent applications with LLMs. It provides:

- **State Management**: Maintains conversation state across multiple agent interactions
- **Graph-Based Workflows**: Define workflows as directed graphs with nodes and edges
- **Conditional Routing**: Route between different agents based on state
- **Memory**: Built-in support for conversation memory and context
- **Tool Integration**: Easy integration with external tools and APIs

### LangGraph vs Traditional Orchestration

| Feature             | Traditional         | LangGraph                    |
| ------------------- | ------------------- | ---------------------------- |
| State Management    | Manual, error-prone | Built-in, automatic          |
| Workflow Definition | Hardcoded logic     | Declarative graphs           |
| Error Handling      | Manual try-catch    | Built-in checkpointing       |
| Agent Coordination  | Complex callbacks   | Simple edges and conditions  |
| Debugging           | Difficult           | State inspection at any node |

---

## Why LangGraph for Code Review?

Code review workflows are inherently multi-step and stateful:

```
GitHub PR Event → Parse PR Data → Fetch Diff → Analyze Code → Generate Findings → Post Comment → Update Status
```

Each step needs to:

- Access data from previous steps
- Handle errors gracefully
- Track costs and usage
- Make decisions based on results

LangGraph provides:

1. **Structured State**: Type-safe state container that flows through workflow
2. **Step Tracking**: Know exactly where you are in the workflow
3. **Error Recovery**: Gracefully handle failures and provide context
4. **Cost Tracking**: Accumulate costs across multiple AI API calls
5. **Testability**: Each step can be tested independently

---

## State Management Architecture

### The Flow of State

```
┌─────────────────────────────────────────────────────────────────┐
│                         Webhook Event                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  create_initial_workflow_state()                                │
│  - Parse PR data (repo, number, diff, files)                    │
│  - Initialize empty review_results                              │
│  - Set current_step = "initialized"                             │
│  - Create metadata with timestamps                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Code Analysis (Gemini AI)                              │
│  - update_state(current_step="analyzing")                       │
│  - Call Gemini API with diff                                    │
│  - Extract findings                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: Process Findings                                       │
│  - For each finding: add_review_finding()                       │
│  - update_metadata(cost, tokens, model_call)                    │
│  - update_state(current_step="analysis_complete")               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Generate Summary                                       │
│  - update_state(current_step="generating_summary")              │
│  - Aggregate findings by severity                               │
│  - Format Markdown comment                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: Post to GitHub                                         │
│  - update_state(current_step="posting_comment")                 │
│  - Call GitHub API to post comment                              │
│  - Handle errors with set_error() if needed                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: Complete                                               │
│  - update_state(current_step="completed")                       │
│  - Log final metrics (cost, tokens, duration)                   │
│  - State is discarded after workflow completes                  │
└─────────────────────────────────────────────────────────────────┘
```

### In-Memory State Lifecycle

```python
# 1. State is created when webhook arrives
state = create_initial_workflow_state(
    repo_name="owner/repo",
    pr_number=123,
    diff=pr_diff,
    files=changed_files
)

# 2. State flows through workflow nodes
state = analyze_code_node(state)
state = generate_summary_node(state)
state = post_comment_node(state)

# 3. State is discarded after workflow completes
# No database writes, no persistence needed
```

---

## The WorkflowState Schema

Located in `app/agents/state.py`:

```python
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
    current_step: str  # Current step in the workflow

    # Error handling
    error: Optional[str]  # Error message if workflow fails

    # Metadata for tracking and analytics
    metadata: Dict[str, Any]  # Contains: timestamps, costs, token_usage, model_info
```

### Field Breakdown

#### `pr_data: Dict[str, Any]`

Contains all PR-related information:

```python
{
    "repo_name": "owner/repo",           # Full repository name
    "pr_number": 123,                    # PR number
    "diff": "diff --git a/...",          # Git unified diff
    "files": [                           # List of changed files
        {
            "filename": "app/main.py",
            "status": "modified",
            "additions": 10,
            "deletions": 5
        }
    ],
    "pr_title": "Fix SQL injection",     # PR title
    "pr_author": "developer123",         # PR author username
    "commit_sha": "abc123def456",        # HEAD commit SHA
    # ... any additional PR metadata
}
```

**Why a Dict?**

- Flexible: Can add any PR metadata without schema changes
- Easy to pass around between functions
- Simple to serialize for logging/debugging

#### `review_results: List[Dict[str, Any]]`

Contains findings from AI code analysis:

```python
[
    {
        "severity": "HIGH",
        "type": "security",
        "title": "SQL Injection Vulnerability",
        "description": "Direct string interpolation in SQL query allows SQL injection",
        "file_path": "app/main.py",
        "line_start": 15,
        "line_end": 15,
        "code_snippet": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
        "recommendation": "Use parameterized queries instead",
        "example_fix": "query = \"SELECT * FROM users WHERE id = ?\"\ncursor.execute(query, (user_id,))",
        "references": ["https://owasp.org/www-community/attacks/SQL_Injection"]
    },
    {
        "severity": "MEDIUM",
        "type": "best_practices",
        "title": "Missing Error Handling",
        # ...
    }
]
```

**Structure:**

- Each finding is a complete, self-contained dictionary
- Findings are added immutably using `add_review_finding()`
- Can be filtered, sorted, or grouped by severity/type

#### `current_step: str`

Tracks workflow progress:

```python
# Possible values:
"initialized"           # Workflow created
"analyzing"            # AI analyzing code
"analysis_complete"    # Analysis finished
"generating_summary"   # Creating summary
"posting_comment"      # Posting to GitHub
"completed"            # Workflow successful
"failed"               # Workflow failed (check error field)
```

**Benefits:**

- Easy to debug: Know exactly where workflow is
- Conditional routing: Different paths based on step
- Metrics: Track time spent in each step
- Resume capability: Could resume from any step

#### `error: Optional[str]`

Stores error information if workflow fails:

```python
# Success case
error = None

# Failure case
error = "GitHub API rate limit exceeded. Retry after 60 seconds."
```

**Error Handling Pattern:**

```python
try:
    # Attempt operation
    result = github_client.post_comment(...)
    state = update_state(state, current_step="completed")
except Exception as e:
    state = set_error(state, f"Failed to post comment: {str(e)}")
    # Workflow stops, state shows "failed" step
```

#### `metadata: Dict[str, Any]`

Tracks workflow analytics and costs:

```python
{
    "created_at": "2026-01-07T10:30:15.123456",     # Workflow start
    "updated_at": "2026-01-07T10:30:18.789012",     # Last update
    "total_cost_usd": 0.0023,                       # Cumulative API costs
    "total_tokens": 1543,                           # Total tokens used
    "model_calls": 2,                               # Number of AI API calls
    "model_name": "gemini-2.5-flash-lite",           # Model used
    "duration_seconds": 3.67,                       # Total duration
    # ... custom metadata
}
```

**Cost Tracking Example:**

```python
# First API call
state = update_metadata(state, cost_usd=0.001, tokens=500, model_call=True)
# metadata["total_cost_usd"] = 0.001, metadata["total_tokens"] = 500

# Second API call
state = update_metadata(state, cost_usd=0.002, tokens=1043, model_call=True)
# metadata["total_cost_usd"] = 0.003, metadata["total_tokens"] = 1543
```

---

## Immutability Pattern

### Why Immutability?

**Problem with Mutable State:**

```python
# BAD: Mutating state directly
def analyze_code(state):
    state["current_step"] = "analyzing"  # Mutation!
    state["review_results"].append(finding)  # Mutation!
    return state  # Same object, modified
```

**Issues:**

1. LangGraph can't track state changes properly
2. Can't rollback to previous state
3. Debugging is harder (state history lost)
4. Race conditions in concurrent workflows
5. Unpredictable behavior

**Solution with Immutability:**

```python
# GOOD: Creating new state
def analyze_code(state):
    new_state = update_state(state, current_step="analyzing")
    new_state = add_review_finding(new_state, finding)
    return new_state  # New object, original unchanged
```

**Benefits:**

1. LangGraph tracks all state transitions
2. Can inspect state at any point in workflow
3. Easy to debug and test
4. Predictable, reproducible workflows
5. No side effects

### How We Achieve Immutability

Using Python's `copy.deepcopy()`:

```python
from copy import deepcopy

def update_state(state: WorkflowState, **kwargs) -> WorkflowState:
    """Update workflow state immutably."""
    new_state = deepcopy(state)  # Deep copy entire state

    # Update timestamp automatically
    if "metadata" in new_state:
        new_state["metadata"]["updated_at"] = datetime.utcnow().isoformat()

    # Apply updates
    for key, value in kwargs.items():
        if key in new_state:
            new_state[key] = value

    return new_state  # Return NEW state
```

### Deep Copy vs Shallow Copy

```python
# Shallow copy (WRONG for nested structures)
new_state = state.copy()
new_state["review_results"].append(finding)  # Modifies ORIGINAL state!

# Deep copy (CORRECT)
new_state = deepcopy(state)
new_state["review_results"].append(finding)  # Only modifies new state
```

**Why Deep Copy?**

- `pr_data` is a nested dict
- `review_results` is a list of dicts
- `metadata` is a nested dict
- Shallow copy only copies references, not actual objects

### Immutability in Action

```python
# Original state
state1 = create_initial_workflow_state("owner/repo", 123)
print(state1["current_step"])  # "initialized"
print(len(state1["review_results"]))  # 0

# Update state
state2 = update_state(state1, current_step="analyzing")
print(state2["current_step"])  # "analyzing"
print(state1["current_step"])  # Still "initialized" - unchanged!

# Add finding
state3 = add_review_finding(state2, {"severity": "HIGH", "title": "Issue"})
print(len(state3["review_results"]))  # 1
print(len(state2["review_results"]))  # Still 0 - unchanged!
print(len(state1["review_results"]))  # Still 0 - unchanged!
```

---

## State Helper Functions

### `create_initial_workflow_state()`

**Purpose**: Initialize new workflow state with default values.

**Location**: `app/agents/state.py:65-103`

**Signature:**

```python
def create_initial_workflow_state(
    repo_name: str,
    pr_number: int,
    diff: str = "",
    files: Optional[List[Dict[str, Any]]] = None,
    **extra_pr_data
) -> WorkflowState:
```

**What It Does:**

1. Creates `pr_data` dict with required fields
2. Initializes empty `review_results` list
3. Sets `current_step` to "initialized"
4. Sets `error` to None
5. Creates `metadata` with timestamps and cost tracking

**Example Usage:**

```python
# Minimal usage
state = create_initial_workflow_state(
    repo_name="owner/repo",
    pr_number=123
)

# With PR diff
state = create_initial_workflow_state(
    repo_name="owner/repo",
    pr_number=123,
    diff="diff --git a/app/main.py ...",
    files=[{"filename": "app/main.py", "status": "modified"}]
)

# With extra metadata
state = create_initial_workflow_state(
    repo_name="owner/repo",
    pr_number=123,
    pr_title="Fix security issue",
    pr_author="developer123",
    commit_sha="abc123def456"
)
```

**Returns:**

```python
WorkflowState(
    pr_data={
        "repo_name": "owner/repo",
        "pr_number": 123,
        "diff": "",
        "files": [],
        # ... any extra_pr_data
    },
    review_results=[],
    current_step="initialized",
    error=None,
    metadata={
        "created_at": "2026-01-07T10:30:15.123456",
        "updated_at": "2026-01-07T10:30:15.123456",
        "total_cost_usd": 0.0,
        "total_tokens": 0,
        "model_calls": 0
    }
)
```

---

### `update_state()`

**Purpose**: Update workflow state immutably.

**Location**: `app/agents/state.py:106-138`

**Signature:**

```python
def update_state(state: WorkflowState, **kwargs) -> WorkflowState:
```

**What It Does:**

1. Creates deep copy of state
2. Updates `metadata.updated_at` timestamp automatically
3. Applies any provided updates
4. Returns new state (original unchanged)

**Example Usage:**

```python
# Update current step
state = update_state(state, current_step="analyzing")

# Update multiple fields
state = update_state(
    state,
    current_step="completed",
    metadata={**state["metadata"], "duration": 3.5}
)

# Update nested pr_data
state = update_state(
    state,
    pr_data={**state["pr_data"], "analyzed": True}
)
```

**Common Pattern:**

```python
# Chaining updates (each returns new state)
state = create_initial_workflow_state("owner/repo", 123)
state = update_state(state, current_step="analyzing")
state = update_state(state, current_step="analysis_complete")
state = update_state(state, current_step="completed")
```

**What NOT to do:**

```python
# WRONG: Mutating state directly
state["current_step"] = "analyzing"  # Don't do this!

# WRONG: Mutating nested structures
state["review_results"].append(finding)  # Don't do this!

# CORRECT: Use helper functions
state = update_state(state, current_step="analyzing")
state = add_review_finding(state, finding)
```

---

### `add_review_finding()`

**Purpose**: Add a review finding to state immutably.

**Location**: `app/agents/state.py:141-158`

**Signature:**

```python
def add_review_finding(
    state: WorkflowState,
    finding: Dict[str, Any]
) -> WorkflowState:
```

**What It Does:**

1. Copies existing `review_results` list
2. Appends new finding to copy
3. Updates state with new list
4. Returns new state

**Example Usage:**

```python
# Add a security finding
state = add_review_finding(state, {
    "severity": "HIGH",
    "type": "security",
    "title": "SQL Injection",
    "description": "Unsafe SQL query construction",
    "file_path": "app/main.py",
    "line_start": 15,
    "recommendation": "Use parameterized queries"
})

# Add multiple findings
for finding in analysis.findings:
    state = add_review_finding(state, {
        "severity": finding.severity,
        "type": finding.type,
        "title": finding.title,
        "description": finding.description,
        "file_path": finding.location.file_path if finding.location else None,
        "line_start": finding.location.line_start if finding.location else None,
        "recommendation": finding.recommendation
    })
```

**Finding Structure (Recommended):**

```python
{
    "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO",
    "type": "security" | "performance" | "bug" | "best_practices" | "style",
    "title": "Short title",
    "description": "Detailed description of the issue",
    "file_path": "path/to/file.py",
    "line_start": 15,
    "line_end": 20,
    "code_snippet": "problematic code",
    "recommendation": "How to fix it",
    "example_fix": "Fixed code example",
    "references": ["https://..."]
}
```

---

### `set_error()`

**Purpose**: Mark workflow as failed with error message.

**Location**: `app/agents/state.py:161-176`

**Signature:**

```python
def set_error(state: WorkflowState, error_message: str) -> WorkflowState:
```

**What It Does:**

1. Sets `error` field with message
2. Updates `current_step` to "failed"
3. Updates timestamp
4. Returns new state

**Example Usage:**

```python
# Handle API error
try:
    result = github_client.post_comment(...)
except GithubException as e:
    state = set_error(state, f"GitHub API error: {str(e)}")
    # State now shows: current_step="failed", error="GitHub API error: ..."

# Handle validation error
if not pr_data["diff"]:
    state = set_error(state, "PR diff is empty, cannot analyze")

# Handle rate limit
if rate_limit_exceeded:
    state = set_error(state, "API rate limit exceeded. Retry after 60 seconds.")
```

**Error Recovery Pattern:**

```python
def execute_workflow(state: WorkflowState) -> WorkflowState:
    try:
        # Step 1
        state = update_state(state, current_step="analyzing")
        analysis = analyze_code(state["pr_data"]["diff"])

        # Step 2
        state = update_state(state, current_step="posting")
        post_comment(analysis)

        # Success
        state = update_state(state, current_step="completed")

    except Exception as e:
        # Failure
        state = set_error(state, f"Workflow failed: {str(e)}")

    finally:
        # Log results
        log_workflow_result(state)

    return state
```

---

### `update_metadata()`

**Purpose**: Update workflow metadata with costs and usage.

**Location**: `app/agents/state.py:179-212`

**Signature:**

```python
def update_metadata(
    state: WorkflowState,
    cost_usd: float = 0.0,
    tokens: int = 0,
    model_call: bool = False,
    **extra_metadata
) -> WorkflowState:
```

**What It Does:**

1. Copies current metadata
2. Accumulates `total_cost_usd` (adds to existing)
3. Accumulates `total_tokens` (adds to existing)
4. Increments `model_calls` if `model_call=True`
5. Adds any extra metadata fields
6. Updates timestamp
7. Returns new state

**Example Usage:**

```python
# After first AI API call
state = update_metadata(
    state,
    cost_usd=0.001,
    tokens=500,
    model_call=True,
    model_name="gemini-2.5-flash-lite"
)
# metadata["total_cost_usd"] = 0.001
# metadata["total_tokens"] = 500
# metadata["model_calls"] = 1

# After second AI API call
state = update_metadata(
    state,
    cost_usd=0.002,
    tokens=1043,
    model_call=True
)
# metadata["total_cost_usd"] = 0.003 (cumulative)
# metadata["total_tokens"] = 1543 (cumulative)
# metadata["model_calls"] = 2

# Add custom metadata without costs
state = update_metadata(
    state,
    files_analyzed=10,
    analysis_type="security"
)
```

**Cost Tracking Workflow:**

```python
# Initialize
state = create_initial_workflow_state("owner/repo", 123)

# AI Analysis 1: Security
gemini = GeminiClient(use_flash=True)
analysis1 = await gemini.analyze_code(diff, "security")
state = update_metadata(
    state,
    cost_usd=analysis1.cost_usd,
    tokens=analysis1.input_tokens + analysis1.output_tokens,
    model_call=True,
    analysis_type="security"
)

# AI Analysis 2: Performance
analysis2 = await gemini.analyze_code(diff, "performance")
state = update_metadata(
    state,
    cost_usd=analysis2.cost_usd,
    tokens=analysis2.input_tokens + analysis2.output_tokens,
    model_call=True,
    analysis_type="performance"
)

# Final costs
print(f"Total cost: ${state['metadata']['total_cost_usd']:.4f}")
print(f"Total tokens: {state['metadata']['total_tokens']}")
print(f"Model calls: {state['metadata']['model_calls']}")
```

---

## State Validation

### Why Validate?

Validation ensures:

1. State has correct structure before processing
2. Data types are correct
3. Required fields are present
4. Values are within acceptable ranges

### Validation Functions

#### `validate_workflow_state()`

**Purpose**: Validate complete workflow state structure.

**Location**: `app/agents/state.py:217-260`

**Returns**: `Tuple[bool, Optional[str]]`

- `(True, None)` if valid
- `(False, "error message")` if invalid

**Example Usage:**

```python
# Validate state
is_valid, error = validate_workflow_state(state)

if not is_valid:
    logger.error(f"Invalid workflow state: {error}")
    raise ValueError(f"State validation failed: {error}")

# Continue with valid state
process_workflow(state)
```

**What It Checks:**

1. All required top-level keys present (`pr_data`, `review_results`, `current_step`, `error`, `metadata`)
2. `pr_data` is a dict with `repo_name` and `pr_number`
3. `review_results` is a list
4. `current_step` is a string
5. `error` is None or string
6. `metadata` is a dict

---

#### `validate_pr_data()`

**Purpose**: Validate PR data structure.

**Location**: `app/agents/state.py:263-292`

**Example Usage:**

```python
# Validate before creating state
pr_data = {
    "repo_name": "owner/repo",
    "pr_number": 123,
    "diff": "...",
    "files": [...]
}

is_valid, error = validate_pr_data(pr_data)
if not is_valid:
    raise ValueError(f"Invalid PR data: {error}")

# Create state with validated data
state = create_initial_workflow_state(**pr_data)
```

**What It Checks:**

1. `repo_name` is present and format is "owner/repo"
2. `pr_number` is positive integer
3. `files` is a list (if present)

---

#### `validate_finding()`

**Purpose**: Validate review finding structure.

**Location**: `app/agents/state.py:295-321`

**Example Usage:**

```python
# Validate before adding to state
finding = {
    "severity": "HIGH",
    "type": "security",
    "title": "SQL Injection",
    "description": "..."
}

is_valid, error = validate_finding(finding)
if not is_valid:
    logger.warning(f"Invalid finding: {error}")
else:
    state = add_review_finding(state, finding)
```

**What It Checks:**

1. Finding is a dict
2. Severity (if present) is one of: CRITICAL, HIGH, MEDIUM, LOW, INFO

---

## Real-World Workflow Examples

### Example 1: Complete Code Review Workflow

```python
async def code_review_workflow(
    repo_name: str,
    pr_number: int,
    diff: str,
    files: List[Dict],
    installation_id: int
):
    """Complete end-to-end code review workflow."""

    # Step 1: Initialize state
    state = create_initial_workflow_state(
        repo_name=repo_name,
        pr_number=pr_number,
        diff=diff,
        files=files
    )

    # Step 2: Validate state
    is_valid, error = validate_workflow_state(state)
    if not is_valid:
        return set_error(state, f"Invalid state: {error}")

    try:
        # Step 3: Analyze code with AI
        state = update_state(state, current_step="analyzing")

        gemini = GeminiClient(use_flash=True)
        analysis = await gemini.analyze_code(diff, "security")

        # Step 4: Process findings
        state = update_state(state, current_step="processing_findings")

        for finding in analysis.findings:
            state = add_review_finding(state, {
                "severity": finding.severity,
                "type": finding.type,
                "title": finding.title,
                "description": finding.description,
                "file_path": finding.location.file_path if finding.location else None,
                "line_start": finding.location.line_start if finding.location else None,
                "recommendation": finding.recommendation
            })

        # Step 5: Update costs
        state = update_metadata(
            state,
            cost_usd=analysis.cost_usd,
            tokens=analysis.input_tokens + analysis.output_tokens,
            model_call=True,
            model_name=gemini.model_name
        )

        # Step 6: Generate summary
        state = update_state(state, current_step="generating_summary")

        summary = generate_review_summary(state)

        # Step 7: Post to GitHub
        state = update_state(state, current_step="posting_comment")

        github = GitHubClient()
        github.post_pr_comment(
            repo_name=repo_name,
            pr_number=pr_number,
            body=summary,
            installation_id=installation_id
        )

        # Step 8: Complete
        state = update_state(state, current_step="completed")

        # Log success
        logger.info(
            f"Code review completed for {repo_name}#{pr_number}",
            extra={
                "findings": len(state["review_results"]),
                "cost": state["metadata"]["total_cost_usd"],
                "tokens": state["metadata"]["total_tokens"]
            }
        )

    except GithubException as e:
        state = set_error(state, f"GitHub API error: {str(e)}")
        logger.error(f"GitHub error: {e}")

    except Exception as e:
        state = set_error(state, f"Unexpected error: {str(e)}")
        logger.error(f"Workflow error: {e}", exc_info=True)

    return state


def generate_review_summary(state: WorkflowState) -> str:
    """Generate Markdown summary from state."""
    findings = state["review_results"]
    metadata = state["metadata"]

    # Count by severity
    critical = sum(1 for f in findings if f["severity"] == "CRITICAL")
    high = sum(1 for f in findings if f["severity"] == "HIGH")
    medium = sum(1 for f in findings if f["severity"] == "MEDIUM")
    low = sum(1 for f in findings if f["severity"] == "LOW")

    # Build summary
    summary = f"## Code Review Summary\n\n"
    summary += f"**Total Issues Found:** {len(findings)}\n\n"

    if critical > 0:
        summary += f"- ⛔ **Critical:** {critical}\n"
    if high > 0:
        summary += f"- 🔴 **High:** {high}\n"
    if medium > 0:
        summary += f"- 🟡 **Medium:** {medium}\n"
    if low > 0:
        summary += f"- 🔵 **Low:** {low}\n"

    summary += f"\n---\n\n"

    # Add findings
    for i, finding in enumerate(findings, 1):
        severity_emoji = {
            "CRITICAL": "⛔",
            "HIGH": "🔴",
            "MEDIUM": "🟡",
            "LOW": "🔵",
            "INFO": "ℹ️"
        }.get(finding["severity"], "")

        summary += f"### {i}. {severity_emoji} {finding['title']}\n\n"
        summary += f"**Severity:** {finding['severity']}  \n"
        summary += f"**Type:** {finding['type']}  \n"

        if finding.get("file_path"):
            summary += f"**Location:** `{finding['file_path']}:{finding['line_start']}`  \n"

        summary += f"\n{finding['description']}\n\n"

        if finding.get("recommendation"):
            summary += f"**Recommendation:** {finding['recommendation']}\n\n"

        summary += f"---\n\n"

    # Add metadata
    summary += f"\n*Analysis cost: ${metadata['total_cost_usd']:.4f} | "
    summary += f"Tokens: {metadata['total_tokens']} | "
    summary += f"Model: {metadata.get('model_name', 'Unknown')}*\n"

    return summary
```

### Example 2: Multi-Stage Analysis with Different Models

```python
async def comprehensive_review_workflow(repo_name: str, pr_number: int, diff: str):
    """Multi-stage review using different AI models."""

    # Initialize
    state = create_initial_workflow_state(repo_name, pr_number, diff=diff)

    try:
        # Stage 1: Quick security scan with Flash model
        state = update_state(state, current_step="security_scan")

        flash_client = GeminiClient(use_flash=True)
        security_analysis = await flash_client.analyze_code(diff, "security")

        for finding in security_analysis.findings:
            state = add_review_finding(state, {
                "severity": finding.severity,
                "type": "security",
                "title": finding.title,
                "description": finding.description,
                "recommendation": finding.recommendation
            })

        state = update_metadata(
            state,
            cost_usd=security_analysis.cost_usd,
            tokens=security_analysis.input_tokens + security_analysis.output_tokens,
            model_call=True,
            stage="security_scan"
        )

        # Stage 2: Deep analysis with Pro model if critical issues found
        critical_found = any(
            f["severity"] == "CRITICAL"
            for f in state["review_results"]
        )

        if critical_found:
            state = update_state(state, current_step="deep_analysis")

            pro_client = GeminiClient(use_flash=False)  # Use Pro model
            detailed_analysis = await pro_client.analyze_code(diff, "security")

            for finding in detailed_analysis.findings:
                state = add_review_finding(state, {
                    "severity": finding.severity,
                    "type": "security_detailed",
                    "title": f"[Deep Analysis] {finding.title}",
                    "description": finding.description,
                    "recommendation": finding.recommendation,
                    "example_fix": finding.example_fix
                })

            state = update_metadata(
                state,
                cost_usd=detailed_analysis.cost_usd,
                tokens=detailed_analysis.input_tokens + detailed_analysis.output_tokens,
                model_call=True,
                stage="deep_analysis"
            )

        # Stage 3: Performance analysis
        state = update_state(state, current_step="performance_scan")

        perf_analysis = await flash_client.analyze_code(diff, "performance")

        for finding in perf_analysis.findings:
            state = add_review_finding(state, {
                "severity": finding.severity,
                "type": "performance",
                "title": finding.title,
                "description": finding.description,
                "recommendation": finding.recommendation
            })

        state = update_metadata(
            state,
            cost_usd=perf_analysis.cost_usd,
            tokens=perf_analysis.input_tokens + perf_analysis.output_tokens,
            model_call=True,
            stage="performance_scan"
        )

        # Complete
        state = update_state(state, current_step="completed")

        # Log results
        logger.info(
            f"Comprehensive review completed",
            extra={
                "repo": repo_name,
                "pr": pr_number,
                "findings": len(state["review_results"]),
                "stages": state["metadata"]["model_calls"],
                "total_cost": state["metadata"]["total_cost_usd"],
                "critical_issues": critical_found
            }
        )

    except Exception as e:
        state = set_error(state, f"Review failed: {str(e)}")

    return state
```

### Example 3: Error Recovery and Retry

```python
async def resilient_review_workflow(repo_name: str, pr_number: int, diff: str):
    """Workflow with error recovery and retry logic."""

    state = create_initial_workflow_state(repo_name, pr_number, diff=diff)
    max_retries = 3

    # Step 1: Analyze with retry
    for attempt in range(max_retries):
        try:
            state = update_state(
                state,
                current_step=f"analyzing_attempt_{attempt + 1}"
            )

            client = GeminiClient(use_flash=True)
            analysis = await client.analyze_code(diff, "general")

            # Success - process findings
            for finding in analysis.findings:
                state = add_review_finding(state, {
                    "severity": finding.severity,
                    "type": finding.type,
                    "title": finding.title,
                    "description": finding.description
                })

            state = update_metadata(
                state,
                cost_usd=analysis.cost_usd,
                tokens=analysis.input_tokens + analysis.output_tokens,
                model_call=True,
                attempts=attempt + 1
            )

            break  # Success, exit retry loop

        except Exception as e:
            logger.warning(f"Analysis attempt {attempt + 1} failed: {e}")

            if attempt == max_retries - 1:
                # Final attempt failed
                state = set_error(
                    state,
                    f"Analysis failed after {max_retries} attempts: {str(e)}"
                )
                return state

            # Wait before retry (exponential backoff)
            await asyncio.sleep(2 ** attempt)

    # Step 2: Post results with retry
    if state["error"] is None:
        for attempt in range(max_retries):
            try:
                state = update_state(state, current_step="posting_results")

                github = GitHubClient()
                summary = generate_review_summary(state)

                github.post_pr_comment(
                    repo_name=repo_name,
                    pr_number=pr_number,
                    body=summary,
                    installation_id=installation_id
                )

                state = update_state(state, current_step="completed")
                break

            except GithubException as e:
                logger.warning(f"GitHub posting attempt {attempt + 1} failed: {e}")

                if attempt == max_retries - 1:
                    state = set_error(
                        state,
                        f"Failed to post results: {str(e)}"
                    )

                await asyncio.sleep(2 ** attempt)

    return state
```

---

## Best Practices

### 1. Always Use Helper Functions

```python
# ✅ GOOD: Use helper functions
state = update_state(state, current_step="analyzing")
state = add_review_finding(state, finding)
state = update_metadata(state, cost_usd=0.001, tokens=500)

# ❌ BAD: Direct mutation
state["current_step"] = "analyzing"
state["review_results"].append(finding)
state["metadata"]["total_cost_usd"] += 0.001
```

### 2. Validate at Boundaries

```python
# ✅ GOOD: Validate when creating state from external data
pr_data = parse_webhook_payload(request.json)
is_valid, error = validate_pr_data(pr_data)
if not is_valid:
    raise ValueError(f"Invalid PR data: {error}")
state = create_initial_workflow_state(**pr_data)

# ❌ BAD: Skip validation
state = create_initial_workflow_state(**parse_webhook_payload(request.json))
```

### 3. Track Costs Consistently

```python
# ✅ GOOD: Always update metadata after AI calls
analysis = await gemini.analyze_code(diff, "security")
state = update_metadata(
    state,
    cost_usd=analysis.cost_usd,
    tokens=analysis.input_tokens + analysis.output_tokens,
    model_call=True
)

# ❌ BAD: Forget to track costs
analysis = await gemini.analyze_code(diff, "security")
# Missing: state = update_metadata(...)
```

### 4. Use current_step for Flow Control

```python
# ✅ GOOD: Track workflow progress
state = update_state(state, current_step="analyzing")
analysis = await analyze_code(diff)

state = update_state(state, current_step="posting")
post_results(analysis)

state = update_state(state, current_step="completed")

# ❌ BAD: No progress tracking
analysis = await analyze_code(diff)
post_results(analysis)
```

### 5. Handle Errors Gracefully

```python
# ✅ GOOD: Catch errors and set state
try:
    result = risky_operation()
    state = update_state(state, current_step="completed")
except Exception as e:
    state = set_error(state, f"Operation failed: {str(e)}")
    logger.error(f"Error: {e}", exc_info=True)

# ❌ BAD: Let errors propagate without updating state
result = risky_operation()
state = update_state(state, current_step="completed")
```

### 6. Log State Transitions

```python
# ✅ GOOD: Log important state changes
logger.info(f"State transition: {old_step} → {state['current_step']}")
logger.info(f"Added finding: {finding['severity']} - {finding['title']}")
logger.info(f"Cost update: +${cost_usd:.4f} (total: ${state['metadata']['total_cost_usd']:.4f})")

# ❌ BAD: Silent state changes
state = update_state(state, current_step="analyzing")
```

### 7. Keep State Focused

```python
# ✅ GOOD: Only store what's needed
state = create_initial_workflow_state(
    repo_name="owner/repo",
    pr_number=123,
    diff=diff,
    files=files
)

# ❌ BAD: Store entire webhook payload
state = create_initial_workflow_state(
    repo_name="owner/repo",
    pr_number=123,
    entire_webhook_payload=webhook_data,  # Too much data
    raw_github_response=github_response   # Unnecessary
)
```

### 8. Use Type Hints

```python
# ✅ GOOD: Type hints for clarity
def process_workflow(state: WorkflowState) -> WorkflowState:
    """Process workflow with type safety."""
    state = update_state(state, current_step="processing")
    return state

# ❌ BAD: No type hints
def process_workflow(state):
    state = update_state(state, current_step="processing")
    return state
```

---

## Common Patterns

### Pattern 1: Step-by-Step Workflow

```python
def execute_step_by_step(state: WorkflowState) -> WorkflowState:
    """Execute workflow one step at a time."""

    # Step 1
    state = update_state(state, current_step="step1")
    result1 = do_step1(state)

    # Step 2
    state = update_state(state, current_step="step2")
    result2 = do_step2(state, result1)

    # Step 3
    state = update_state(state, current_step="step3")
    result3 = do_step3(state, result2)

    # Complete
    state = update_state(state, current_step="completed")
    return state
```

### Pattern 2: Conditional Branching

```python
def conditional_workflow(state: WorkflowState) -> WorkflowState:
    """Branch based on state conditions."""

    state = update_state(state, current_step="analyzing")
    analysis = analyze_code(state["pr_data"]["diff"])

    # Check for critical issues
    has_critical = any(
        f["severity"] == "CRITICAL"
        for f in analysis.findings
    )

    if has_critical:
        # Deep analysis path
        state = update_state(state, current_step="deep_analysis")
        state = run_deep_analysis(state)
    else:
        # Quick review path
        state = update_state(state, current_step="quick_review")
        state = run_quick_review(state)

    state = update_state(state, current_step="completed")
    return state
```

### Pattern 3: Accumulating Results

```python
async def accumulate_analyses(state: WorkflowState) -> WorkflowState:
    """Run multiple analyses and accumulate results."""

    analysis_types = ["security", "performance", "best_practices"]

    for analysis_type in analysis_types:
        state = update_state(state, current_step=f"analyzing_{analysis_type}")

        client = GeminiClient(use_flash=True)
        analysis = await client.analyze_code(
            state["pr_data"]["diff"],
            analysis_type
        )

        # Add findings
        for finding in analysis.findings:
            state = add_review_finding(state, {
                "severity": finding.severity,
                "type": analysis_type,
                "title": finding.title,
                "description": finding.description
            })

        # Accumulate costs
        state = update_metadata(
            state,
            cost_usd=analysis.cost_usd,
            tokens=analysis.input_tokens + analysis.output_tokens,
            model_call=True
        )

    state = update_state(state, current_step="completed")
    return state
```

### Pattern 4: State Checkpointing

```python
def workflow_with_checkpoints(state: WorkflowState) -> WorkflowState:
    """Save state at checkpoints for recovery."""

    checkpoints = []

    try:
        # Checkpoint 1
        state = update_state(state, current_step="checkpoint1")
        checkpoints.append(deepcopy(state))
        state = do_risky_operation1(state)

        # Checkpoint 2
        state = update_state(state, current_step="checkpoint2")
        checkpoints.append(deepcopy(state))
        state = do_risky_operation2(state)

        # Checkpoint 3
        state = update_state(state, current_step="checkpoint3")
        checkpoints.append(deepcopy(state))
        state = do_risky_operation3(state)

        state = update_state(state, current_step="completed")

    except Exception as e:
        # Recover from last checkpoint
        logger.error(f"Error at {state['current_step']}: {e}")
        state = checkpoints[-1] if checkpoints else state
        state = set_error(state, f"Failed at {state['current_step']}: {str(e)}")

    return state
```

---

## Troubleshooting

### Issue 1: State Not Updating

**Symptom:**

```python
state = update_state(state, current_step="analyzing")
print(state["current_step"])  # Still shows "initialized"
```

**Cause:** Not reassigning the return value.

**Solution:**

```python
# WRONG
update_state(state, current_step="analyzing")  # Returns new state but not assigned

# CORRECT
state = update_state(state, current_step="analyzing")  # Reassign to variable
```

---

### Issue 2: Original State Modified

**Symptom:**

```python
state1 = create_initial_workflow_state("owner/repo", 123)
state2 = update_state(state1, current_step="analyzing")
print(state1["current_step"])  # Shows "analyzing" instead of "initialized"
```

**Cause:** Not using deep copy (shouldn't happen with our functions, but check if you're modifying manually).

**Solution:** Always use helper functions, never mutate directly.

---

### Issue 3: Metadata Not Accumulating

**Symptom:**

```python
state = update_metadata(state, cost_usd=0.001, tokens=100)
state = update_metadata(state, cost_usd=0.002, tokens=200)
print(state["metadata"]["total_cost_usd"])  # Shows 0.002 instead of 0.003
```

**Cause:** Reassigning metadata dict instead of accumulating.

**Solution:** Use `update_metadata()` which accumulates automatically.

---

### Issue 4: Validation Always Fails

**Symptom:**

```python
is_valid, error = validate_workflow_state(state)
print(is_valid)  # False
print(error)  # "Missing required keys: {'metadata'}"
```

**Cause:** State created manually without all required fields.

**Solution:** Always use `create_initial_workflow_state()` to ensure correct structure.

---

### Issue 5: Type Errors

**Symptom:**

```python
TypeError: 'WorkflowState' object does not support item assignment
```

**Cause:** TypedDict is for type hints only, not runtime enforcement.

**Solution:** This shouldn't happen. WorkflowState is just a typed dictionary. Check you're not using a different type.

---

# Part 2: Workflow Orchestration

---

## LangGraph Workflow Architecture

Now that we understand state management, let's dive into how LangGraph orchestrates the entire code review workflow using nodes, edges, and conditional routing.

### The Big Picture

RepoAuditor AI's code review workflow is implemented as a **directed graph** where:

- **Nodes** are functions that process state
- **Edges** connect nodes to define flow
- **Conditional Edges** enable dynamic routing based on state
- **State** flows through the graph immutably

```
GitHub Webhook → Initialize State → Workflow Execution → Final State → Response
```

### Files Structure

The workflow is split across three files for clarity:

```
app/workflows/
├── nodes.py                 # Node implementations (8 nodes)
├── code_review_workflow.py  # Graph definition & routing
└── executor.py              # Execution logic & utilities
```

**Why separate files?**

- **nodes.py**: Focus on business logic of each step
- **code_review_workflow.py**: Focus on workflow structure and routing
- **executor.py**: Focus on execution, testing, and monitoring

---

## Workflow Graph Structure

### Visual Representation

```
┌─────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH WORKFLOW                            │
└─────────────────────────────────────────────────────────────────┘

    ┌─────────┐
    │  START  │  Initialize state from webhook
    └────┬────┘
         │
         ▼
    ┌──────────┐
    │ FETCH_PR │  Get PR details & diff from GitHub API
    └────┬─────┘
         │
         ▼
    ┌────────────────┐
    │  Conditional   │  Has diff & files changed?
    └───┬────────┬───┘
        │ YES    │ NO
        ▼        └──────────────────────┐
    ┌──────────────┐                    │
    │ REVIEW_CODE  │  AI-powered analysis│
    └──────┬───────┘                    │
           │                            │
           ▼                            │
    ┌─────────────────┐                 │
    │ CLASSIFY_       │                 │
    │ SEVERITY        │  Categorize     │
    └────────┬────────┘                 │
             │                          │
             ▼                          │
    ┌────────────────┐                  │
    │  POST_REVIEW   │  Post to GitHub │
    └────────┬───────┘                  │
             │                          │
             ▼                          │
    ┌────────────────┐                  │
    │ CHECK_CRITICAL │                  │
    └───┬────────┬───┘                  │
        │ CRIT   │ OK                   │
        ▼        └──────┬───────────────┘
    ┌────────────────┐  │
    │ REQUEST_       │  │
    │ APPROVAL       │  │
    └────────┬───────┘  │
             │          │
             ▼          ▼
           ┌──────────────┐
           │     END      │  Finalize & log metrics
           └──────────────┘
                   │
                   ▼
                (DONE)
```

### Graph Components

#### 1. **Entry Point**

```python
workflow.set_entry_point("start")
```

- First node to execute
- Always the "start" node
- Initializes workflow state

#### 2. **Sequential Edges**

```python
workflow.add_edge("start", "fetch_pr")
workflow.add_edge("review_code", "classify_severity")
```

- Simple node-to-node connection
- Always follow this path
- No conditions

#### 3. **Conditional Edges**

```python
workflow.add_conditional_edges(
    "fetch_pr",
    should_skip_review,  # Routing function
    {
        "review_code": "review_code",
        "end": "end"
    }
)
```

- Dynamic routing based on state
- Routing function returns string key
- Key maps to target node

#### 4. **Terminal Node**

```python
workflow.add_edge("end", END)
```

- Marks workflow completion
- `END` is LangGraph's built-in terminal
- State becomes final result

---

## Workflow Nodes Explained

Let's examine each node in detail, looking at the actual code and understanding what it does.

### Node 1: start_node

**Location**: `app/workflows/nodes.py:27-56`

**Purpose**: Validate initial state and mark workflow as started.

**Code Breakdown**:

```python
def start_node(state: WorkflowState) -> WorkflowState:
    try:
        logger.info(f"Starting code review workflow for {state['pr_data']['repo_name']} PR #{state['pr_data']['pr_number']}")

        # Validate required fields
        required_fields = ["repo_name", "pr_number"]
        missing_fields = [
            field for field in required_fields
            if field not in state["pr_data"]
        ]

        if missing_fields:
            return set_error(state, f"Missing required PR data fields: {missing_fields}")

        # Update state to mark workflow as started
        state = update_state(
            state,
            current_step="started",
            metadata={
                **state["metadata"],
                "workflow_started_at": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Workflow started successfully")
        return state

    except Exception as e:
        logger.error(f"Error in start_node: {e}", exc_info=True)
        return set_error(state, f"Failed to start workflow: {str(e)}")
```

**What It Does**:

1. **Logs Start**: Records workflow initiation
2. **Validates Data**: Checks for required fields (repo_name, pr_number)
3. **Detects Errors**: Returns error state if validation fails
4. **Updates State**: Sets current_step to "started"
5. **Adds Timestamp**: Records workflow_started_at
6. **Error Handling**: Catches and logs any exceptions

**Why It's Important**:

- Fail fast if data is invalid
- Provides clear error messages
- Establishes baseline timestamp for duration calculation

---

### Node 2: fetch_pr_node

**Location**: `app/workflows/nodes.py:62-128`

**Purpose**: Fetch PR details and diff from GitHub API.

**Code Breakdown**:

```python
async def fetch_pr_node(state: WorkflowState) -> WorkflowState:
    try:
        state = update_state(state, current_step="fetching_pr")

        repo_name = state["pr_data"]["repo_name"]
        pr_number = state["pr_data"]["pr_number"]
        installation_id = state["pr_data"].get("installation_id")

        if not installation_id:
            return set_error(state, "Installation ID not found in PR data")

        logger.info(f"Fetching PR details for {repo_name}#{pr_number}")

        # Initialize GitHub client
        github_client = GitHubClient()

        # Fetch PR details
        pr_details = github_client.get_pr_details(
            repo_name=repo_name,
            pr_number=pr_number,
            installation_id=installation_id
        )

        # Fetch PR diff
        pr_diff = github_client.get_pr_diff(
            repo_name=repo_name,
            pr_number=pr_number,
            installation_id=installation_id
        )

        # Update pr_data with fetched information
        updated_pr_data = {
            **state["pr_data"],
            "title": pr_details.get("title", ""),
            "author": pr_details.get("user", {}).get("login", "unknown"),
            "description": pr_details.get("body", ""),
            "diff": pr_diff,
            "files": [
                {
                    "filename": f["filename"],
                    "status": f["status"],
                    "additions": f["additions"],
                    "deletions": f["deletions"],
                    "changes": f["changes"]
                }
                for f in pr_details.get("files", [])
            ],
            "changed_files_count": pr_details.get("changed_files", 0),
            "additions": pr_details.get("additions", 0),
            "deletions": pr_details.get("deletions", 0),
            "commit_sha": pr_details.get("head", {}).get("sha", ""),
        }

        state = update_state(
            state,
            pr_data=updated_pr_data,
            current_step="pr_fetched"
        )

        logger.info(f"Fetched PR details: {len(updated_pr_data['files'])} files changed")

        return state

    except Exception as e:
        logger.error(f"Error fetching PR: {e}", exc_info=True)
        return set_error(state, f"Failed to fetch PR details: {str(e)}")
```

**What It Does**:

1. **Updates Step**: current_step = "fetching_pr"
2. **Extracts Data**: Gets repo_name, pr_number, installation_id
3. **Creates Client**: Initializes GitHubClient
4. **Fetches Details**: Calls GitHub API for PR metadata
5. **Fetches Diff**: Gets unified diff of changes
6. **Enriches State**: Adds title, author, files, diff to pr_data
7. **Logs Progress**: Records files changed count
8. **Handles Errors**: Returns error state on API failure

**Key Points**:

- **Async**: Uses `async def` because GitHub API is I/O bound
- **Immutable Update**: Creates new pr_data dict with spread operator
- **Error Recovery**: Gracefully handles API failures
- **Complete Data**: Fetches everything needed for analysis

---

### Node 3: review_code_node

**Location**: `app/workflows/nodes.py:134-214`

**Purpose**: Analyze code using Gemini AI and extract findings.

**Code Breakdown**:

```python
async def review_code_node(state: WorkflowState) -> WorkflowState:
    try:
        state = update_state(state, current_step="reviewing_code")

        diff = state["pr_data"].get("diff", "")

        if not diff:
            logger.warning("No diff found, skipping code review")
            return update_state(state, current_step="review_skipped")

        logger.info(f"Starting AI code review")

        # Initialize Gemini client (use Flash model for cost efficiency)
        gemini_client = GeminiClient(use_flash=True)

        # Run comprehensive code analysis
        analysis = await gemini_client.analyze_code(
            code_diff=diff,
            analysis_type="general"  # Comprehensive review
        )

        # Add findings to state
        for finding in analysis.findings:
            state = add_review_finding(state, {
                "severity": finding.severity,
                "type": finding.type,
                "title": finding.title,
                "description": finding.description,
                "file_path": finding.location.file_path if finding.location else None,
                "line_start": finding.location.line_start if finding.location else None,
                "line_end": finding.location.line_end if finding.location else None,
                "code_snippet": finding.location.code_snippet if finding.location else None,
                "recommendation": finding.recommendation,
                "example_fix": finding.example_fix if hasattr(finding, 'example_fix') else None,
                "references": finding.references if hasattr(finding, 'references') else [],
            })

        # Update metadata with cost and usage
        state = update_metadata(
            state,
            cost_usd=analysis.cost_usd,
            tokens=analysis.input_tokens + analysis.output_tokens,
            model_call=True,
            model_name=gemini_client.model_name,
            input_tokens=analysis.input_tokens,
            output_tokens=analysis.output_tokens
        )

        state = update_state(state, current_step="code_reviewed")

        logger.info(f"Code review completed: {len(state['review_results'])} findings")

        return state

    except Exception as e:
        logger.error(f"Error during code review: {e}", exc_info=True)
        return set_error(state, f"Code review failed: {str(e)}")
```

**What It Does**:

1. **Gets Diff**: Extracts diff from state
2. **Checks Empty**: Skips review if no diff
3. **Creates Client**: Initializes GeminiClient with Flash model
4. **Runs Analysis**: Calls AI for comprehensive review
5. **Extracts Findings**: Converts Pydantic models to dicts
6. **Adds Each Finding**: Uses add_review_finding() immutably
7. **Tracks Costs**: Records USD cost and token usage
8. **Updates Metadata**: Stores model info and metrics

**Key Points**:

- **Cost Efficient**: Uses Flash model (cheaper than Pro)
- **Comprehensive**: Analyzes security, performance, bugs, style
- **Structured Data**: Findings have consistent format
- **Immutable Updates**: Uses helper functions for state changes
- **Error Handling**: Catches AI API failures

---

### Node 4: classify_severity_node

**Location**: `app/workflows/nodes.py:220-276`

**Purpose**: Count and categorize findings by severity and type.

**Code Breakdown**:

```python
def classify_severity_node(state: WorkflowState) -> WorkflowState:
    try:
        state = update_state(state, current_step="classifying_severity")

        findings = state["review_results"]

        # Count by severity
        severity_counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0
        }

        for finding in findings:
            severity = finding.get("severity", "INFO")
            if severity in severity_counts:
                severity_counts[severity] += 1

        # Count by type
        type_counts = {}
        for finding in findings:
            finding_type = finding.get("type", "unknown")
            type_counts[finding_type] = type_counts.get(finding_type, 0) + 1

        # Update metadata with classification
        state = update_metadata(
            state,
            severity_counts=severity_counts,
            type_counts=type_counts,
            total_findings=len(findings),
            has_critical=severity_counts["CRITICAL"] > 0,
            has_high=severity_counts["HIGH"] > 0
        )

        state = update_state(state, current_step="severity_classified")

        logger.info(f"Severity classification: Critical={severity_counts['CRITICAL']}, High={severity_counts['HIGH']}, ...")

        return state

    except Exception as e:
        logger.error(f"Error classifying severity: {e}", exc_info=True)
        return set_error(state, f"Severity classification failed: {str(e)}")
```

**What It Does**:

1. **Iterates Findings**: Loops through all findings
2. **Counts Severity**: Tallies each severity level
3. **Counts Types**: Tallies each finding type
4. **Sets Flags**: has_critical, has_high for routing
5. **Updates Metadata**: Stores all counts
6. **Logs Summary**: Records classification results

**Key Points**:

- **Simple Logic**: Just counting, no complex operations
- **Enables Routing**: has_critical flag used by conditional edge
- **Aggregation**: Provides summary for reporting
- **Sync Function**: No async needed (no I/O)

---

### Node 5: post_review_node

**Location**: `app/workflows/nodes.py:282-357`

**Purpose**: Post formatted review results to GitHub PR.

**Code Breakdown**:

```python
async def post_review_node(state: WorkflowState) -> WorkflowState:
    try:
        state = update_state(state, current_step="posting_review")

        repo_name = state["pr_data"]["repo_name"]
        pr_number = state["pr_data"]["pr_number"]
        installation_id = state["pr_data"].get("installation_id")

        if not installation_id:
            return set_error(state, "Installation ID not found")

        # Generate review comment
        comment = generate_review_comment(state)

        logger.info(f"Posting review comment to {repo_name}#{pr_number}")

        # Post comment to GitHub
        github_client = GitHubClient()
        github_client.post_pr_comment(
            repo_name=repo_name,
            pr_number=pr_number,
            body=comment,
            installation_id=installation_id
        )

        # Update commit status
        commit_sha = state["pr_data"].get("commit_sha")
        if commit_sha:
            try:
                has_critical = state["metadata"].get("has_critical", False)
                has_high = state["metadata"].get("has_high", False)

                if has_critical:
                    status_state = "failure"
                    description = "Critical issues found - review required"
                elif has_high:
                    status_state = "error"
                    description = "High severity issues found"
                else:
                    status_state = "success"
                    description = "Code review completed - no critical issues"

                github_client.update_commit_status(
                    repo_name=repo_name,
                    sha=commit_sha,
                    state=status_state,
                    description=description,
                    installation_id=installation_id,
                    context="RepoAuditor AI / Code Review"
                )
            except Exception as e:
                logger.warning(f"Failed to update commit status: {e}")

        state = update_state(state, current_step="review_posted")

        logger.info(f"Review posted successfully")

        return state

    except Exception as e:
        logger.error(f"Error posting review: {e}", exc_info=True)
        return set_error(state, f"Failed to post review: {str(e)}")
```

**What It Does**:

1. **Generates Comment**: Calls helper to format Markdown
2. **Posts Comment**: Uses GitHub API to add comment
3. **Updates Status**: Sets commit status check
   - failure: Critical issues found
   - error: High issues found
   - success: No critical/high issues
4. **Handles Errors**: Gracefully handles API failures
5. **Logs Success**: Records completion

**Key Points**:

- **Two API Calls**: Comment + status check
- **Status Check**: Visual indicator in GitHub UI
- **Error Resilience**: Status failure doesn't fail node
- **Formatted Output**: Uses generate_review_comment() helper

---

### Node 6: check_critical_node

**Location**: `app/workflows/nodes.py:363-392`

**Purpose**: Determine if critical/high issues require approval.

**Code Breakdown**:

```python
def check_critical_node(state: WorkflowState) -> WorkflowState:
    try:
        state = update_state(state, current_step="checking_critical")

        has_critical = state["metadata"].get("has_critical", False)
        has_high = state["metadata"].get("has_high", False)

        state = update_metadata(
            state,
            requires_approval=has_critical or has_high,
            approval_reason=(
                "Critical issues found" if has_critical
                else "High severity issues found" if has_high
                else None
            )
        )

        state = update_state(state, current_step="critical_checked")

        logger.info(f"Critical check: requires_approval={has_critical or has_high}")

        return state

    except Exception as e:
        logger.error(f"Error checking critical issues: {e}", exc_info=True)
        return set_error(state, f"Critical check failed: {str(e)}")
```

**What It Does**:

1. **Reads Flags**: Gets has_critical, has_high from metadata
2. **Sets Flag**: requires_approval = true if critical OR high
3. **Sets Reason**: Explains why approval needed
4. **Updates State**: Stores decision in metadata
5. **Logs Decision**: Records approval requirement

**Key Points**:

- **Decision Node**: Pure logic, no I/O
- **Enables Routing**: requires_approval used by conditional edge
- **Clear Reason**: Provides context for approval request
- **Fast Execution**: Simple boolean logic

---

### Node 7: request_approval_node

**Location**: `app/workflows/nodes.py:398-437`

**Purpose**: Post approval request comment for critical issues.

**Code Breakdown**:

```python
async def request_approval_node(state: WorkflowState) -> WorkflowState:
    try:
        state = update_state(state, current_step="requesting_approval")

        repo_name = state["pr_data"]["repo_name"]
        pr_number = state["pr_data"]["pr_number"]
        installation_id = state["pr_data"].get("installation_id")

        if not installation_id:
            return set_error(state, "Installation ID not found")

        # Generate approval request comment
        approval_comment = generate_approval_request_comment(state)

        logger.info(f"Posting approval request to {repo_name}#{pr_number}")

        # Post comment
        github_client = GitHubClient()
        github_client.post_pr_comment(
            repo_name=repo_name,
            pr_number=pr_number,
            body=approval_comment,
            installation_id=installation_id
        )

        state = update_state(state, current_step="approval_requested")

        logger.info(f"Approval request posted")

        return state

    except Exception as e:
        logger.error(f"Error requesting approval: {e}", exc_info=True)
        return set_error(state, f"Failed to request approval: {str(e)}")
```

**What It Does**:

1. **Generates Comment**: Creates prominent approval request
2. **Posts Comment**: Uses GitHub API
3. **Updates State**: Marks approval as requested
4. **Logs Action**: Records approval request

**Key Points**:

- **Optional Node**: Only executed if critical issues found
- **Separate Comment**: Distinct from review comment
- **Clear Action Items**: Tells developer what to do next
- **Async**: GitHub API call

---

### Node 8: end_node

**Location**: `app/workflows/nodes.py:443-494`

**Purpose**: Finalize workflow and log completion metrics.

**Code Breakdown**:

```python
def end_node(state: WorkflowState) -> WorkflowState:
    try:
        # Calculate workflow duration
        created_at = datetime.fromisoformat(state["metadata"]["created_at"])
        completed_at = datetime.utcnow()
        duration = (completed_at - created_at).total_seconds()

        # Update metadata
        state = update_metadata(
            state,
            workflow_completed_at=completed_at.isoformat(),
            workflow_duration_seconds=duration
        )

        state = update_state(state, current_step="completed")

        # Log completion metrics
        logger.info(
            f"Workflow completed for {state['pr_data']['repo_name']} PR #{state['pr_data']['pr_number']}",
            extra={
                "duration_seconds": duration,
                "total_findings": len(state["review_results"]),
                "critical_count": state["metadata"].get("severity_counts", {}).get("CRITICAL", 0),
                "high_count": state["metadata"].get("severity_counts", {}).get("HIGH", 0),
                "total_cost_usd": state["metadata"]["total_cost_usd"],
                "total_tokens": state["metadata"]["total_tokens"],
                "model_calls": state["metadata"]["model_calls"],
                "requires_approval": state["metadata"].get("requires_approval", False)
            }
        )

        return state

    except Exception as e:
        logger.error(f"Error in end_node: {e}", exc_info=True)
        return set_error(state, f"Failed to finalize workflow: {str(e)}")
```

**What It Does**:

1. **Calculates Duration**: created_at to completed_at
2. **Updates Metadata**: Stores completion time and duration
3. **Sets Final Step**: current_step = "completed"
4. **Logs Metrics**: Comprehensive structured logging
5. **Returns Final State**: Workflow complete

**Key Points**:

- **Analytics**: Provides complete workflow metrics
- **Structured Logging**: Easy to parse and analyze
- **Duration Tracking**: For performance monitoring
- **Terminal Node**: Last step before END

---

## Conditional Routing

Conditional routing is what makes the workflow intelligent. Instead of following a fixed path, the workflow adapts based on the state.

### Routing Function 1: should_skip_review

**Location**: `app/workflows/code_review_workflow.py:65-98`

**Purpose**: Determine if code review should be skipped.

**Code**:

```python
def should_skip_review(state: WorkflowState) -> Literal["review_code", "end"]:
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
```

**When It's Called**: After fetch_pr node

**Decision Logic**:

```
If error exists → "end" (skip review)
If no diff → "end" (nothing to review)
If no files → "end" (nothing changed)
Otherwise → "review_code" (proceed with review)
```

**Why It's Important**:

- Saves AI API costs (don't analyze empty diffs)
- Prevents errors (can't review nothing)
- Fast failure (no need to continue if error occurred)

**Graph Configuration**:

```python
workflow.add_conditional_edges(
    "fetch_pr",
    should_skip_review,
    {
        "review_code": "review_code",
        "end": "end"
    }
)
```

---

### Routing Function 2: should_request_approval

**Location**: `app/workflows/code_review_workflow.py:41-62`

**Purpose**: Determine if approval request is needed.

**Code**:

```python
def should_request_approval(state: WorkflowState) -> Literal["request_approval", "end"]:
    requires_approval = state["metadata"].get("requires_approval", False)

    if requires_approval:
        logger.info("Critical/high severity issues found - routing to approval request")
        return "request_approval"
    else:
        logger.info("No critical issues - routing to end")
        return "end"
```

**When It's Called**: After check_critical node

**Decision Logic**:

```
If requires_approval = True → "request_approval"
If requires_approval = False → "end"
```

**Why It's Important**:

- Only post approval request when needed
- Reduces noise (no unnecessary comments)
- Clear signal to developers (critical issues = approval needed)

**Graph Configuration**:

```python
workflow.add_conditional_edges(
    "check_critical",
    should_request_approval,
    {
        "request_approval": "request_approval",
        "end": "end"
    }
)
```

---

### How Conditional Edges Work

**Step 1**: LangGraph reaches a node with conditional edge

```python
# Current node: check_critical
state = check_critical_node(state)  # Sets requires_approval flag
```

**Step 2**: LangGraph calls routing function

```python
next_node = should_request_approval(state)  # Returns "request_approval" or "end"
```

**Step 3**: LangGraph looks up next node in mapping

```python
mapping = {
    "request_approval": "request_approval",
    "end": "end"
}
next_node_name = mapping[next_node]  # Get actual node
```

**Step 4**: LangGraph executes next node

```python
state = request_approval_node(state)  # If critical
# OR
state = end_node(state)  # If not critical
```

---

## Error Handling in Workflows

Every node has comprehensive error handling. Let's see how it works.

### Node-Level Error Handling

Each node follows this pattern:

```python
def some_node(state: WorkflowState) -> WorkflowState:
    try:
        # Update step
        state = update_state(state, current_step="doing_something")

        # Do work
        result = do_something_risky()

        # Update state with result
        state = update_state(state, current_step="something_done")

        return state

    except Exception as e:
        # Log error with full traceback
        logger.error(f"Error in some_node: {e}", exc_info=True)

        # Return error state (workflow continues to end)
        return set_error(state, f"Failed to do something: {str(e)}")
```

**What Happens**:

1. **Exception Caught**: Any error is caught
2. **Logged**: Full traceback logged for debugging
3. **Error State**: set_error() creates state with error message
4. **Workflow Continues**: Doesn't crash, continues to end node
5. **Final State**: Contains error information

### Workflow-Level Error Handling

The executor also handles errors:

```python
async def execute_code_review_workflow(...):
    try:
        # Create state
        state = create_initial_workflow_state(...)

        # Compile workflow
        workflow = compile_workflow()

        # Execute workflow
        final_state = await workflow.ainvoke(state)

        # Check for errors
        if final_state.get("error"):
            logger.error(f"Workflow completed with error: {final_state['error']}")
            return final_state

        logger.info(f"Workflow completed successfully")
        return final_state

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)

        # Create error state if needed
        if 'state' not in locals():
            state = create_initial_workflow_state(...)

        return set_error(state, f"Workflow execution failed: {str(e)}")
```

### Error State Structure

When an error occurs, the state looks like:

```python
{
    "pr_data": {...},
    "review_results": [...],  # May have partial results
    "current_step": "failed",  # Set by set_error()
    "error": "Failed to fetch PR details: API rate limit exceeded",
    "metadata": {
        "created_at": "2026-01-07T10:30:15",
        "updated_at": "2026-01-07T10:30:18",
        # ... partial metrics
    }
}
```

### Error Recovery

The workflow doesn't crash - it gracefully handles errors:

1. **Early Errors**: If fetch_pr fails, workflow skips review
2. **Partial Results**: If post_review fails, we still have findings
3. **Logged Details**: Every error is logged with full context
4. **User Notification**: Can check error field in final state

---

## Workflow Execution

### How to Execute the Workflow

**Method 1: From Webhook**

```python
from app.workflows.executor import execute_workflow_from_webhook

# In webhook handler
@app.post("/webhooks/github")
async def handle_webhook(event: PullRequestEvent):
    result = await execute_workflow_from_webhook(event)

    if result["success"]:
        return {"status": "completed", "findings": result["findings_count"]}
    else:
        return {"status": "failed", "error": result["error"]}
```

**Method 2: Programmatically**

```python
from app.workflows.executor import execute_code_review_workflow

state = await execute_code_review_workflow(
    repo_name="owner/repo",
    pr_number=123,
    installation_id=456789,
    pr_title="Fix security issue"
)

print(f"Findings: {len(state['review_results'])}")
print(f"Cost: ${state['metadata']['total_cost_usd']:.4f}")
```

**Method 3: Batch Processing**

```python
from app.workflows.executor import execute_multiple_reviews

reviews = [
    {"repo_name": "owner/repo1", "pr_number": 101, "installation_id": 456},
    {"repo_name": "owner/repo2", "pr_number": 102, "installation_id": 456},
]

results = await execute_multiple_reviews(reviews, max_concurrent=2)

for result in results:
    print(f"{result['pr_data']['repo_name']}: {len(result['review_results'])} findings")
```

### Execution Flow

```
1. Executor creates initial state
   ↓
2. Executor compiles workflow graph
   ↓
3. Executor calls workflow.ainvoke(state)
   ↓
4. LangGraph executes nodes in order:
   ├─ start_node(state) → state2
   ├─ fetch_pr_node(state2) → state3
   ├─ [conditional routing]
   ├─ review_code_node(state3) → state4
   ├─ classify_severity_node(state4) → state5
   ├─ post_review_node(state5) → state6
   ├─ check_critical_node(state6) → state7
   ├─ [conditional routing]
   ├─ request_approval_node(state7) → state8  [if critical]
   └─ end_node(state8) → final_state
   ↓
5. LangGraph returns final_state
   ↓
6. Executor checks for errors and logs results
```

### State Transitions

Each node transition looks like:

```python
# State before node
state_before = {
    "current_step": "pr_fetched",
    "pr_data": {"repo_name": "owner/repo", "pr_number": 123, "diff": "..."},
    "review_results": [],
    "error": None,
    "metadata": {"created_at": "...", "total_cost_usd": 0}
}

# Node execution
state_after = review_code_node(state_before)

# State after node
state_after = {
    "current_step": "code_reviewed",  # Changed
    "pr_data": {"repo_name": "owner/repo", "pr_number": 123, "diff": "..."},  # Same
    "review_results": [  # Added findings
        {"severity": "HIGH", "title": "SQL Injection", ...},
        {"severity": "MEDIUM", "title": "Missing validation", ...}
    ],
    "error": None,  # Still None
    "metadata": {  # Updated
        "created_at": "...",
        "updated_at": "...",  # New timestamp
        "total_cost_usd": 0.0023,  # Added cost
        "total_tokens": 1543,  # Added tokens
        "model_calls": 1  # Incremented
    }
}
```

---

## Testing Workflows

### Test Individual Nodes

```python
from app.workflows.nodes import classify_severity_node
from app.agents.state import create_initial_workflow_state

# Create test state
state = create_initial_workflow_state("test/repo", 123)
state['review_results'] = [
    {"severity": "CRITICAL", "type": "security", "title": "SQL Injection"},
    {"severity": "HIGH", "type": "security", "title": "XSS"},
]

# Test node
result = classify_severity_node(state)

# Check results
assert result['metadata']['severity_counts']['CRITICAL'] == 1
assert result['metadata']['has_critical'] == True
print("✓ classify_severity_node works!")
```

### Test Conditional Routing

```python
from app.workflows.code_review_workflow import should_request_approval
from app.agents.state import create_initial_workflow_state

# Test case 1: Critical issues
state1 = create_initial_workflow_state("test/repo", 123)
state1['metadata']['requires_approval'] = True

route = should_request_approval(state1)
assert route == "request_approval"
print("✓ Routes to approval when critical")

# Test case 2: No critical issues
state2 = create_initial_workflow_state("test/repo", 123)
state2['metadata']['requires_approval'] = False

route = should_request_approval(state2)
assert route == "end"
print("✓ Routes to end when no critical")
```

### Test Complete Workflow

```python
import asyncio
from app.workflows.executor import execute_code_review_workflow

async def test_workflow():
    state = await execute_code_review_workflow(
        repo_name="test/repo",
        pr_number=999,
        installation_id=0,  # Test mode
        diff="test diff content",
        pr_title="Test PR"
    )

    print(f"Workflow completed: {state['current_step']}")
    print(f"Error: {state['error']}")
    print(f"Findings: {len(state['review_results'])}")

asyncio.run(test_workflow())
```

### Visualize Workflow

```bash
# Print ASCII diagram
python -m app.workflows.code_review_workflow

# Output:
# Code Review Workflow Graph
# ═══════════════════════════
#
#     ┌─────────┐
#     │  START  │
#     └────┬────┘
#          │
#          ▼
#     ┌─────────┐
#     │ FETCH_PR│
#     └────┬────┘
#     ...
```

---

## Workflow Best Practices

### 1. Keep Nodes Pure and Focused

✅ **Good**: Node does one thing

```python
def classify_severity_node(state):
    # Only classifies - doesn't fetch, post, or analyze
    counts = count_findings_by_severity(state['review_results'])
    return update_metadata(state, severity_counts=counts)
```

❌ **Bad**: Node does multiple things

```python
def classify_and_post_node(state):
    # Too much responsibility
    counts = count_findings(state['review_results'])
    comment = generate_comment(state)
    post_to_github(comment)  # Side effect!
    return update_metadata(state, severity_counts=counts)
```

### 2. Use Conditional Routing for Decision Points

✅ **Good**: Conditional edge for routing

```python
workflow.add_conditional_edges(
    "check_critical",
    should_request_approval,
    {"request_approval": "request_approval", "end": "end"}
)
```

❌ **Bad**: Logic inside node

```python
def check_and_maybe_request_node(state):
    if has_critical:
        request_approval(state)  # Don't do this!
    return end_node(state)
```

### 3. Handle Errors Gracefully

✅ **Good**: Return error state

```python
def fetch_pr_node(state):
    try:
        data = fetch_from_github()
        return update_state(state, pr_data=data)
    except Exception as e:
        return set_error(state, f"Failed to fetch: {e}")
```

❌ **Bad**: Let exception propagate

```python
def fetch_pr_node(state):
    data = fetch_from_github()  # Might crash workflow
    return update_state(state, pr_data=data)
```

### 4. Log State Transitions

✅ **Good**: Log what's happening

```python
def review_code_node(state):
    logger.info(f"Starting review for {state['pr_data']['repo_name']}")
    result = analyze_code(state['pr_data']['diff'])
    logger.info(f"Review complete: {len(result.findings)} findings")
    return add_findings(state, result.findings)
```

❌ **Bad**: Silent execution

```python
def review_code_node(state):
    result = analyze_code(state['pr_data']['diff'])
    return add_findings(state, result.findings)
```

### 5. Use Immutable State Updates

✅ **Good**: Use helper functions

```python
state = update_state(state, current_step="analyzing")
state = add_review_finding(state, finding)
```

❌ **Bad**: Mutate state

```python
state['current_step'] = "analyzing"
state['review_results'].append(finding)
```

### 6. Validate State at Boundaries

✅ **Good**: Validate early

```python
def start_node(state):
    required = ["repo_name", "pr_number"]
    missing = [f for f in required if f not in state['pr_data']]
    if missing:
        return set_error(state, f"Missing fields: {missing}")
    # Continue...
```

❌ **Bad**: Assume valid

```python
def start_node(state):
    # Hope everything is there
    repo = state['pr_data']['repo_name']  # Might KeyError
```

### 7. Use Async for I/O Operations

✅ **Good**: Async for API calls

```python
async def fetch_pr_node(state):
    github = GitHubClient()
    pr_data = github.get_pr_details(...)  # I/O operation
    return update_state(state, pr_data=pr_data)
```

❌ **Bad**: Sync for I/O

```python
def fetch_pr_node(state):  # Should be async
    github = GitHubClient()
    pr_data = github.get_pr_details(...)  # Blocks event loop
    return update_state(state, pr_data=pr_data)
```

### 8. Track Metrics Consistently

✅ **Good**: Track all operations

```python
async def review_code_node(state):
    result = await gemini.analyze_code(diff)
    state = add_findings(state, result.findings)
    state = update_metadata(
        state,
        cost_usd=result.cost_usd,
        tokens=result.input_tokens + result.output_tokens,
        model_call=True
    )
    return state
```

❌ **Bad**: Forget to track

```python
async def review_code_node(state):
    result = await gemini.analyze_code(diff)
    state = add_findings(state, result.findings)
    return state  # Lost cost information!
```

---

## Summary

### Key Takeaways

1. **LangGraph + Immutability = Predictable Workflows**

   - State flows through workflow nodes
   - Each step creates new state
   - Original state never changes

2. **No Database Required**

   - State lives in memory during execution
   - Discarded after workflow completes
   - Event-driven, stateless design

3. **Type Safety**

   - TypedDict provides IDE autocomplete
   - Catch errors at development time
   - Self-documenting code

4. **Cost Tracking Built-In**

   - Automatic accumulation of API costs
   - Token usage monitoring
   - Model call counting

5. **Always Use Helper Functions**
   - `create_initial_workflow_state()`
   - `update_state()`
   - `add_review_finding()`
   - `set_error()`
   - `update_metadata()`

### Next Steps

1. Read the [FEATURES.md](FEATURES.md) for complete feature list
2. Check [Github Webhook.md](Github%20Webhook.md) for testing workflows
3. Review example workflows in this document
4. Start building your own LangGraph workflows!

---

**Questions? Issues?**

- See [TROUBLESHOOTING_WEBHOOK_ERRORS.md](TROUBLESHOOTING_WEBHOOK_ERRORS.md)
- Check [Setup Guide.md](Setup%20Guide.md)
- Review [README.md](README.md)
