# Agent Architecture Documentation

This document provides a comprehensive overview of the RepoAuditor AI multi-agent workflow system architecture, design patterns, and implementation details.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [LangGraph Workflow Patterns](#langgraph-workflow-patterns)
3. [State Management](#state-management)
4. [Specialized Agents](#specialized-agents)
5. [Command Routing](#command-routing)
6. [Adding New Commands](#adding-new-commands)
7. [Design Decisions](#design-decisions)

---

## 1. Architecture Overview

### 1.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Webhook                            │
│                  (FastAPI Endpoint)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Rate Limiter         │ <--- JSON File Storage
         │  (Middleware)         │      (data/rate_limits.json)
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Command Router       │
         │  (Pattern Matching)   │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  LangGraph Workflow   │
         │  Compiler/Executor    │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌────────────────┐      ┌────────────────┐
│ Simple         │      │ Complex        │
│ Workflows      │      │ Workflows      │
│                │      │                │
│ - /explain     │      │ - /fix-security│
│ - /help        │      │ - /comprehensive│
│ - /review      │      │ - /auto-fix    │
│                │      │ - /optimize    │
│                │      │ - /incremental │
└────────────────┘      └────────┬───────┘
                                 │
                     ┌───────────┴───────────┐
                     │                       │
                     ▼                       ▼
            ┌────────────────┐      ┌────────────────┐
            │ Specialized    │      │ State Managers │
            │ Agents         │      │                │
            │                │      │ - File-based   │
            │- SecurityAgent │      │ - Memory cache │
            │- TestGenAgent  │      │ - Incremental  │
            │- FixerAgent    │      │   tracking     │
            │- OptimizerAgent│      └────────────────┘
            └────────────────┘
```

### 1.2 Key Components

**1. Webhook Handler** (`app/webhooks/github.py`)
- Receives GitHub webhook events
- Verifies HMAC-SHA256 signatures
- Routes to background task processing

**2. Rate Limiter** (`app/utils/rate_limiter.py`)
- File-based JSON storage
- Three limit types: user, PR, repository
- Automatic cleanup of old entries

**3. Command Router** (`app/commands/router.py`)
- Pattern-based command matching
- Agent registration and routing
- Context creation for agents

**4. LangGraph Workflows** (`app/workflows/`)
- State graph orchestration
- Conditional routing
- Node execution
- Error handling

**5. Specialized Agents** (`app/agents/specialized/`)
- Task-specific agents
- AI-powered analysis
- Fix generation
- Test generation

---

## 2. LangGraph Workflow Patterns

### 2.1 Sequential Workflow Pattern

**Example:** `/fix-security-issues`

```python
from langgraph.graph import StateGraph, END

def create_security_fix_workflow():
    graph = StateGraph(SecurityFixState)

    # Define nodes
    graph.add_node("scan_security", scan_security_issues_node)
    graph.add_node("generate_fixes", generate_fixes_node)
    graph.add_node("run_tests", run_tests_node)
    graph.add_node("create_pr", create_pr_node)
    graph.add_node("rollback", rollback_changes_node)

    # Entry point
    graph.set_entry_point("scan_security")

    # Sequential edges
    graph.add_edge("scan_security", "generate_fixes")
    graph.add_edge("generate_fixes", "run_tests")

    # Conditional routing based on test results
    graph.add_conditional_edges(
        "run_tests",
        check_tests_passed,  # Routing function
        {
            "success": "create_pr",
            "failure": "rollback"
        }
    )

    # Terminal edges
    graph.add_edge("create_pr", END)
    graph.add_edge("rollback", END)

    return graph.compile()
```

**Flow Diagram:**
```
start
  ↓
scan_security_issues
  ↓
generate_fixes
  ↓
run_tests
  ├─→ [Tests Pass] → create_pr → END
  └─→ [Tests Fail] → rollback → END
```

### 2.2 Parallel Workflow Pattern

**Example:** `/comprehensive-review`

```python
from langgraph.graph import StateGraph, Send, END

def run_parallel_scans(state: ComprehensiveReviewState):
    """Fan-out to parallel scans."""
    return [
        Send("security_scan", state),
        Send("performance_scan", state),
        Send("quality_scan", state),
    ]

def create_comprehensive_review_workflow():
    graph = StateGraph(ComprehensiveReviewState)

    # Define nodes
    graph.add_node("fetch_pr_diff", fetch_pr_diff_node)
    graph.add_node("security_scan", security_scan_node)
    graph.add_node("performance_scan", performance_scan_node)
    graph.add_node("quality_scan", quality_scan_node)
    graph.add_node("aggregate_findings", aggregate_findings_node)
    graph.add_node("generate_report", generate_report_node)

    # Entry point
    graph.set_entry_point("fetch_pr_diff")

    # Parallel execution
    graph.add_conditional_edges(
        "fetch_pr_diff",
        run_parallel_scans
    )

    # All parallel branches converge to aggregation
    graph.add_edge("security_scan", "aggregate_findings")
    graph.add_edge("performance_scan", "aggregate_findings")
    graph.add_edge("quality_scan", "aggregate_findings")

    # Sequential after aggregation
    graph.add_edge("aggregate_findings", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()
```

**Flow Diagram:**
```
fetch_pr_diff
  ↓
[Fan-out to parallel execution]
  ├─→ security_scan ────┐
  ├─→ performance_scan ─┤
  └─→ quality_scan ─────┤
                        ↓
                [Join/Converge]
                        ↓
                aggregate_findings
                        ↓
                generate_report
                        ↓
                       END
```

### 2.3 Stateful Workflow Pattern

**Example:** `/incremental-review`

```python
def create_incremental_review_workflow():
    graph = StateGraph(IncrementalReviewState)

    # Nodes
    graph.add_node("load_history", load_review_history_node)
    graph.add_node("identify_new", identify_new_files_node)
    graph.add_node("review_new", review_new_files_node)
    graph.add_node("save_history", save_review_history_node)

    # Entry
    graph.set_entry_point("load_history")

    # Sequential flow with file persistence
    graph.add_edge("load_history", "identify_new")
    graph.add_conditional_edges(
        "identify_new",
        check_has_new_files,
        {
            "has_new": "review_new",
            "no_new": END
        }
    )
    graph.add_edge("review_new", "save_history")
    graph.add_edge("save_history", END)

    return graph.compile()
```

**State Persistence:**
- Loads from `data/incremental_reviews/{repo}/pr-{number}.json`
- Tracks reviewed files with SHA hashes
- Saves updated history after review

---

## 3. State Management

### 3.1 State Schema Design

All workflows use TypedDict for type-safe state management:

```python
from typing import TypedDict, List, Optional, Dict, Any

class SecurityFixState(TypedDict):
    # Input context
    repo_name: str
    pr_number: int
    installation_id: int

    # Workflow data
    security_issues: List[SecurityIssue]
    proposed_fixes: List[ProposedFix]
    test_results: Dict[str, Any]

    # Status flags
    scan_complete: bool
    fixes_generated: bool
    tests_passed: bool

    # Output
    pr_url: Optional[str]
    error: Optional[str]

    # Metadata
    metadata: Dict[str, Any]
```

**Key Principles:**
- **Immutability**: Always create new state objects
- **Type Safety**: Use TypedDict for schema validation
- **Completeness**: Include all needed fields upfront
- **Metadata**: Track costs, tokens, duration

### 3.2 State Updates

```python
# ❌ BAD: Mutating state directly
def bad_node(state: SecurityFixState) -> SecurityFixState:
    state["scan_complete"] = True  # Direct mutation
    return state

# ✅ GOOD: Creating new state
def good_node(state: SecurityFixState) -> SecurityFixState:
    return {
        **state,
        "scan_complete": True,
        "security_issues": found_issues,
        "metadata": {
            **state["metadata"],
            "scan_duration": 12.5
        }
    }
```

### 3.3 State Helper Functions

Located in `app/models/workflow_states.py`:

```python
# Create initial state
initial_state = create_security_fix_state(
    repo_name="owner/repo",
    pr_number=123,
    installation_id=456,
    github_client=client,
    gemini_client=gemini
)

# Update state immutably
updated_state = {
    **initial_state,
    "scan_complete": True,
    "security_issues": found_issues
}
```

---

## 4. Specialized Agents

### 4.1 Security Scanner Agent

**File:** `app/agents/specialized/security_scanner.py`

**Responsibilities:**
- Detect SQL injection vulnerabilities
- Find hardcoded secrets (API keys, passwords)
- Identify XSS vulnerabilities
- Detect path traversal risks
- Check for insecure deserialization

**Implementation Approach:**
1. **Pattern Matching**: Regex patterns for known vulnerabilities
2. **AI Analysis**: Gemini for context-aware detection
3. **Confidence Scoring**: Rate confidence (0.0-1.0)
4. **CWE Mapping**: Map to Common Weakness Enumeration IDs

**Example Usage:**
```python
from app.agents.specialized.security_scanner import SecurityScanner

scanner = SecurityScanner(gemini_client)

issues = await scanner.scan(
    code=pr_diff,
    language="python",
    context={"repo": "owner/repo", "pr": 123}
)

# Returns List[SecurityIssue]
for issue in issues:
    print(f"{issue['severity']}: {issue['type']} at {issue['file']}:{issue['line']}")
```

### 4.2 Fix Generator Agent

**File:** `app/agents/specialized/fix_generator.py`

**Responsibilities:**
- Generate fixes for security issues
- Provide explanations for each fix
- Validate fix syntax (AST parsing)
- Create git-style patches

**Example:**
```python
from app.agents.specialized.fix_generator import FixGenerator

generator = FixGenerator(gemini_client)

fix = await generator.generate_fix(
    issue=security_issue,
    code_context=surrounding_code,
    language="python"
)

# Returns ProposedFix with:
# - fixed_code: Corrected code
# - explanation: Why this works
# - patch: Git-style diff
```

### 4.3 Test Generator Agent

**File:** `app/agents/specialized/test_generator.py`

**Responsibilities:**
- Detect test framework (pytest, jest, go test)
- Generate test cases for fixes
- Create assertions
- Handle edge cases

**Example:**
```python
from app.agents.specialized.test_generator import TestGenerator

test_gen = TestGenerator(gemini_client)

tests = await test_gen.generate_tests(
    fix=proposed_fix,
    test_framework="pytest",
    coverage_target=0.8
)

# Returns List[GeneratedTest]
```

### 4.4 Language Detector Agent

**File:** `app/agents/specialized/language_detector.py`

**Responsibilities:**
- Count file extensions
- Determine primary language
- Return confidence score
- Map to tool configurations

**Example:**
```python
from app.agents.specialized.language_detector import LanguageDetector

detector = LanguageDetector()

result = detector.detect(files=pr_files)

# Returns:
# {
#   "language": "python",
#   "confidence": 0.95,
#   "formatter": "black",
#   "linter": "ruff"
# }
```

---

## 5. Command Routing

### 5.1 Command Router Architecture

**File:** `app/commands/router.py`

```python
class CommandRouter:
    def __init__(self, github_client, gemini_client):
        self.agents: Dict[str, BaseAgent] = {}
        self.patterns: Dict[Pattern, str] = {}

    def register(self, command: str, agent: BaseAgent, pattern: str):
        """Register an agent for a command."""
        self.agents[command] = agent
        self.patterns[re.compile(pattern)] = command

    def match_command(self, text: str) -> Optional[Tuple[str, str]]:
        """Match text against registered patterns."""
        for pattern, command in self.patterns.items():
            if match := pattern.match(text):
                return (command, remaining_text)
        return None

    async def route(self, event: IssueCommentEvent) -> bool:
        """Route event to appropriate agent."""
        command, args = self.match_command(event.comment.body)
        agent = self.agents[command]

        context = self._create_context(event, command, args)
        response = await agent.handle(context)

        await self._post_response(event, response.message)
```

### 5.2 Registering New Commands

**File:** `app/commands/router_instance.py`

```python
from app.commands.router import CommandRouter
from app.agents.specialized import MyNewAgent

def initialize_router() -> CommandRouter:
    router = CommandRouter(github_client, gemini_client)

    # Register existing commands
    router.register("help", HelpAgent(), r"^/?help\b")
    router.register("explain", ExplainerAgent(), r"^/?explain\b")

    # Register NEW command
    router.register(
        command="my-new-command",
        agent=MyNewAgent(),
        pattern=r"^/?my-new-command\b"
    )

    return router
```

---

## 6. Adding New Commands

### Step-by-Step Guide

#### Step 1: Define State Schema

`app/models/workflow_states.py`:
```python
class MyWorkflowState(TypedDict):
    repo_name: str
    pr_number: int
    # ... workflow-specific fields
    metadata: Dict[str, Any]
    error: Optional[str]
```

#### Step 2: Create Workflow Nodes

`app/workflows/nodes/my_nodes.py`:
```python
async def step1_node(state: MyWorkflowState) -> MyWorkflowState:
    """Execute step 1 of workflow."""
    # Workflow logic
    return {
        **state,
        "step1_complete": True
    }

async def step2_node(state: MyWorkflowState) -> MyWorkflowState:
    """Execute step 2 of workflow."""
    # Workflow logic
    return {
        **state,
        "step2_complete": True
    }
```

#### Step 3: Assemble Workflow

`app/workflows/my_workflow.py`:
```python
from langgraph.graph import StateGraph, END
from app.models.workflow_states import MyWorkflowState
from app.workflows.nodes.my_nodes import step1_node, step2_node

def create_my_workflow() -> StateGraph:
    """Create custom workflow."""
    graph = StateGraph(MyWorkflowState)

    # Add nodes
    graph.add_node("step1", step1_node)
    graph.add_node("step2", step2_node)

    # Set entry
    graph.set_entry_point("step1")

    # Add edges
    graph.add_edge("step1", "step2")
    graph.add_edge("step2", END)

    return graph.compile()
```

#### Step 4: Create Command Handler

`app/commands/handlers/my_handler.py`:
```python
from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse
from app.workflows.my_workflow import create_my_workflow
from app.models.workflow_states import create_my_workflow_state

class MyCommandHandler(BaseAgent):
    def __init__(self):
        super().__init__(
            name="MyCommandHandler",
            description="Handles my custom command"
        )

    async def handle(self, context: AgentContext) -> AgentResponse:
        """Handle command execution."""
        # Create initial state
        initial_state = create_my_workflow_state(
            repo_name=context.repo_name,
            pr_number=context.pr_number,
            installation_id=context.installation_id,
            github_client=context.github_client,
            gemini_client=context.gemini_client
        )

        # Execute workflow
        workflow = create_my_workflow()
        final_state = await workflow.ainvoke(initial_state)

        # Return response
        return AgentResponse(
            success=final_state["error"] is None,
            message=final_state.get("agent_result", "Workflow completed"),
            metadata=final_state["metadata"]
        )
```

#### Step 5: Register Command

`app/commands/router_instance.py`:
```python
from app.commands.handlers.my_handler import MyCommandHandler

router.register(
    command="my-command",
    agent=MyCommandHandler(),
    pattern=r"^/?my-command\b"
)
```

#### Step 6: Write Tests

`tests/unit/test_my_workflow.py`:
```python
import pytest
from app.workflows.my_workflow import create_my_workflow
from app.models.workflow_states import create_my_workflow_state

@pytest.mark.asyncio
async def test_my_workflow():
    """Test my workflow end-to-end."""
    initial_state = create_my_workflow_state(
        repo_name="test/repo",
        pr_number=123,
        installation_id=456
    )

    workflow = create_my_workflow()
    result = await workflow.ainvoke(initial_state)

    assert result["step1_complete"] == True
    assert result["step2_complete"] == True
    assert result["error"] is None
```

---

## 7. Design Decisions

### 7.1 File-Based Rate Limiting

**Decision:** Use JSON file storage instead of Redis/PostgreSQL

**Rationale:**
- ✅ Zero external dependencies
- ✅ Simple implementation
- ✅ Human-readable for debugging
- ✅ Sufficient for GitHub App scale (hundreds of requests/day)
- ✅ Aligns with stateless architecture

**Trade-offs:**
- ❌ Not suitable for extreme high traffic (10K+ req/sec)
- ❌ No distributed locking (but single instance assumed)
- ✅ Perfect for capstone project scale

### 7.2 Parallel vs Sequential Execution

**Decision:** Hybrid approach - use both patterns where appropriate

**Examples:**
- **Parallel:** `/comprehensive-review` (security + performance + quality)
- **Sequential:** `/fix-security-issues` (scan → fix → test → PR)

**Rationale:**
- Parallel reduces latency for independent tasks
- Sequential ensures proper ordering for dependencies
- LangGraph supports both patterns elegantly
- Each workflow uses the pattern that best fits its logic

### 7.3 Rollback Strategies

**Decision:** Different strategies per workflow

**Strategies:**
- **Snapshot-based** (`/optimize`): Store original file contents, restore if tests fail
- **Branch deletion** (`/fix-security`): Changes on separate branch, just delete if failed

**Rationale:**
- Different workflows have different failure recovery needs
- Optimize modifies main branch → needs reversion
- Security fix uses test branch → can just delete

### 7.4 Test Execution

**Decision:** Trigger GitHub Actions instead of local execution

**Rationale:**
- ✅ Uses repository's existing test configuration
- ✅ Runs in same environment as CI/CD
- ✅ No need to install dependencies locally
- ✅ Consistent with how developers test locally
- ❌ Slower than local execution (acceptable trade-off)

### 7.5 Agent Specialization

**Decision:** Specialized agents per task type

**Rationale:**
- ✅ Focused responsibility (Single Responsibility Principle)
- ✅ Easier to test and maintain
- ✅ Optimized prompts per task
- ✅ Better separation of concerns
- ✅ Demonstrates modularity for capstone project
- ❌ More files/code (acceptable for maintainability)

### 7.6 LangGraph State Management

**Decision:** TypedDict schemas with immutable updates

**Rationale:**
- ✅ Type safety with Python type hints
- ✅ IDE autocomplete support
- ✅ Runtime type checking (with typeguard)
- ✅ Clear schema documentation
- ✅ Prevents accidental mutations
- ✅ Enables LangGraph's proper state tracking

---

## 8. Performance Considerations

### 8.1 Workflow Optimization

**Token Usage:**
- Limit context sent to AI (use file diffs, not full files)
- Cache AI responses when possible
- Use `max_tokens` configuration appropriately

**Parallel Execution:**
- Use LangGraph's `Send()` for independent tasks
- Avoid parallel execution for dependent operations
- Monitor concurrency limits

**State Size:**
- Keep state minimal (only necessary fields)
- Use references instead of embedding large data
- Clean up intermediate results

### 8.2 Rate Limiter Performance

**File I/O Optimization:**
- Atomic writes (write to .tmp, then rename)
- Thread-safe locking
- Automatic cleanup every hour (not every request)

**Memory Usage:**
- In-memory cache for hot data
- Cleanup removes old entries
- Predictable memory footprint

---

## 9. Error Handling

### 9.1 Error Propagation

```python
async def workflow_node(state: WorkflowState) -> WorkflowState:
    """Example node with error handling."""
    try:
        # Node logic
        result = await risky_operation()
        return {...state, "result": result}

    except Exception as e:
        logger.error(f"Node failed: {e}", exc_info=True)
        return {
            **state,
            "error": f"Operation failed: {str(e)}",
            "current_step": "failed"
        }
```

### 9.2 User-Friendly Error Messages

```python
def create_error_message(error: Exception) -> str:
    """Create user-friendly error message."""
    if isinstance(error, RateLimitExceeded):
        return format_rate_limit_error(error)
    elif isinstance(error, GitHubAPIError):
        return format_github_error(error)
    else:
        return (
            "## ❌ Unexpected Error\n\n"
            f"An unexpected error occurred: {str(error)}\n\n"
            "Please try again or contact support if the issue persists."
        )
```

---

## 10. Monitoring & Observability

### 10.1 Structured Logging

```python
logger.info(
    "Workflow completed",
    extra={
        "extra_fields": {
            "workflow": "security-fix",
            "repo": "owner/repo",
            "pr_number": 123,
            "duration_seconds": 45.3,
            "total_cost_usd": 0.0234,
            "total_tokens": 12450,
            "success": True
        }
    }
)
```

### 10.2 Metrics Collection

Track:
- Workflow execution times
- Token usage per workflow
- Cost per workflow
- Success/failure rates
- Rate limit hits

### 10.3 Debugging Tips

1. **Enable Debug Logging:** `LOG_LEVEL=DEBUG`
2. **Inspect State Files:** Check `data/` directory
3. **Review GitHub Webhook Logs:** Check recent deliveries
4. **Test Locally:** Use ngrok for webhook debugging
5. **Validate State:** Use state validation functions

---

## Conclusion

This architecture provides a robust, scalable, and maintainable multi-agent system using LangGraph. The design emphasizes:

- **Type Safety**: TypedDict schemas
- **Modularity**: Specialized agents
- **Flexibility**: Multiple workflow patterns
- **Observability**: Structured logging and metrics
- **Production-Ready**: Error handling, rate limiting, testing

For hands-on testing and setup instructions, see [Testing_Github.md](./Testing_Github.md).

---

**Next Steps:**
1. Implement remaining workflows (Phase 2-6)
2. Write comprehensive tests
3. Deploy to production
4. Monitor and iterate based on feedback
