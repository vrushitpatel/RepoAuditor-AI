# Commands - Multi-Agent Workflow Implementation

Brief explanation of the multi-agent workflow implementation.

---

## Architecture Overview

```
GitHub Webhook → Initialize → Route → Agent → Post Result → End
                                ↓
                    ┌───────────┴───────────┐
                    ↓           ↓           ↓
              Code Review   Explainer   CI/CD Gen
```

---

## Core Components

### 1. State Management (`app/agents/state.py`)

**Purpose**: Define state that flows through the workflow.

**Key Types:**

```python
class Command(TypedDict):
    """Command from user comment"""
    name: str        # "explain", "review", etc.
    args: str        # Command arguments
    commenter: str   # Who issued it
    comment_id: int  # GitHub comment ID

class AgentState(TypedDict):
    """State flowing through workflow"""
    event_type: str          # "pr_opened", "command_created"
    command: Optional[Command]
    pr_data: Dict            # PR details
    agent_result: str        # Agent's output
    error: Optional[str]     # Error message
    metadata: Dict           # Tokens, cost, duration
    target_agent: str        # Which agent to route to
    # ... GitHub context ...
```

**Why**: Provides structure for passing data between workflow nodes.

---

### 2. Multi-Agent Workflow (`app/workflows/multi_agent_workflow.py`)

**Purpose**: Unified workflow that routes to different agents.

**Key Nodes:**

```python
# 1. Initialize State
def initialize_state_node(state):
    """Set up metadata, validate state"""
    state["metadata"] = {
        "started_at": ...,
        "total_cost_usd": 0.0,
        "total_tokens": 0,
    }
    return state

# 2. Route to Agent
def route_to_agent_node(state):
    """Determine which agent to use"""
    if state["event_type"] == "pr_opened":
        state["target_agent"] = "code_review"
    elif state["command"]["name"] == "explain":
        state["target_agent"] = "explain"
    # ... etc ...
    return state

# 3. Agent Nodes
async def code_review_node(state):
    """Execute code review"""
    result = await execute_workflow_from_state(state)
    state["agent_result"] = result["summary"]
    return state

async def explainer_node(state):
    """Explain code changes"""
    explainer = ExplainerAgent(...)
    response = await explainer.explain_pr_diff(...)
    state["agent_result"] = response.explanation
    return state

async def cicd_generator_node(state):
    """Generate CI/CD workflows"""
    generator = CICDGenerator(...)
    workflows = await generator.generate_workflows(...)
    state["agent_result"] = format_workflows(workflows)
    return state

# 4. Post Result
async def post_result_node(state):
    """Post result to GitHub"""
    github_client.post_pr_comment(
        repo_name=state["repo_name"],
        pr_number=state["pr_number"],
        comment_body=state["agent_result"],
    )
    return state
```

**Workflow Graph:**

```python
def create_multi_agent_workflow():
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

    # Entry point
    graph.set_entry_point("initialize")

    # Flow
    graph.add_edge("initialize", "route")

    # Conditional routing
    graph.add_conditional_edges(
        "route",
        determine_agent,  # Returns "code_review", "explain", etc.
        {
            "code_review": "code_reviewer",
            "explain": "explainer",
            "test": "test_analyst",
            "cicd": "cicd_generator",
            "error": "error",
        }
    )

    # All agents → post_result
    graph.add_edge("code_reviewer", "post_result")
    graph.add_edge("explainer", "post_result")
    graph.add_edge("test_analyst", "post_result")
    graph.add_edge("cicd_generator", "post_result")

    # End
    graph.add_edge("post_result", END)
    graph.add_edge("error", END)

    return graph.compile()
```

**Why**: Single workflow handles all events, easier to maintain.

---

### 3. Workflow Executor (`app/workflows/executor.py`)

**Purpose**: Execute workflow from webhook events.

**Key Function:**

```python
async def execute_multi_agent_workflow_from_webhook(
    event_type: str,
    pr_data: Dict[str, Any],
    installation_id: int,
    command: Optional[Dict[str, Any]] = None,
):
    """Execute unified workflow"""

    # 1. Create initial state
    state = {
        "event_type": event_type,
        "command": command,
        "pr_data": pr_data,
        "installation_id": installation_id,
        # ... other fields ...
    }

    # 2. Get workflow
    workflow = get_multi_agent_workflow()

    # 3. Execute
    final_state = await workflow.ainvoke(state)

    # 4. Return result
    return {
        "success": not final_state["error"],
        "result": final_state["agent_result"],
    }
```

---

### 4. Webhook Integration (`app/webhooks/github.py`)

**Purpose**: Receive webhooks and trigger workflow.

**Flow:**

```python
@router.post("/webhooks/github")
async def handle_github_webhook():
    # 1. Verify signature
    # 2. Parse payload
    # 3. Route to handler

async def handle_pull_request_event():
    # Execute in background
    background_tasks.add_task(
        execute_multi_agent_workflow_from_webhook,
        event_type="pr_opened",
        pr_data={...},
    )

async def handle_issue_comment_event():
    # Extract command
    command = extract_command(comment_body)

    # Execute in background
    background_tasks.add_task(
        execute_multi_agent_workflow_from_webhook,
        event_type="command_created",
        pr_data={...},
        command={
            "name": command,
            "args": extract_args(comment_body),
        }
    )
```

---

## Routing Logic

### Event → Agent Mapping

| Event Type | Command | Agent | Description |
|------------|---------|-------|-------------|
| `pr_opened` | - | `code_review` | Auto review |
| `pr_synchronized` | - | `code_review` | Review commits |
| `command_created` | `/explain` | `explain` | Explain changes |
| `command_created` | `/review` | `code_review` | Manual review |
| `command_created` | `/test` | `test_analyst` | Analyze tests |
| `command_created` | `/generate-ci` | `cicd_generator` | Generate workflows |

---

## Key Design Decisions

### 1. Single Workflow

**Why**: Easier to maintain, shared error handling, consistent state.

### 2. Flat State

**Why**: Easy to pass between nodes, clear context.

### 3. Background Tasks

**Why**: GitHub requires <10s response, AI takes 10-30s.

### 4. Agent as Nodes

**Why**: Clean separation, easy to add, testable.

### 5. Dedicated Post Node

**Why**: Centralized posting, consistent formatting.

---

## Usage Examples

### PR Opened

```python
result = await execute_multi_agent_workflow_from_webhook(
    event_type="pr_opened",
    pr_data={"repo_name": "owner/repo", "pr_number": 123},
    installation_id=456,
)
```

**Flow**: Initialize → Route → Code Review → Post Result

### Explain Command

```python
result = await execute_multi_agent_workflow_from_webhook(
    event_type="command_created",
    pr_data={...},
    installation_id=456,
    command={"name": "explain", "args": "app/main.py"},
)
```

**Flow**: Initialize → Route → Explainer → Post Result

### Generate CI/CD

```python
result = await execute_multi_agent_workflow_from_webhook(
    event_type="command_created",
    pr_data={...},
    installation_id=456,
    command={"name": "generate-ci", "args": "test lint"},
)
```

**Flow**: Initialize → Route → CI/CD Generator → Post Result

---

## Summary

**Built:**
- ✅ Unified multi-agent workflow
- ✅ State management with TypedDict
- ✅ Routing for different events
- ✅ Integration with existing agents
- ✅ Error handling
- ✅ Background execution

**Benefits:**
- Single workflow for all events
- Easy to add new agents
- Consistent error handling
- Clean separation
- Testable components

---

For testing, see `Testing Github and Agent.md`.
