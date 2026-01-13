# Command Router System

The command router provides a clean, extensible architecture for handling bot commands in GitHub PRs.

## Architecture

```
GitHub Webhook → Router → Agent → Response
```

### Components

1. **CommandRouter** (`app/commands/router.py`)
   - Routes commands to appropriate agents
   - Handles errors and unknown commands
   - Manages agent context

2. **BaseAgent** (`app/agents/base_agent.py`)
   - Abstract base class for all agents
   - Defines interface: `handle(context) -> response`
   - Provides logging and error handling

3. **Agent Wrappers**
   - `ExplainerAgentWrapper` - Explains code
   - `ReviewAgentWrapper` - Reviews code
   - `CICDAgentWrapper` - Generates CI/CD workflows
   - `HelpAgent` - Shows help message

---

## How It Works

### 1. Command Flow

```
User comments: "/explain app/main.py"
         ↓
Webhook Handler (github.py)
         ↓
Router.route(event)
         ↓
Router.match_command("/explain app/main.py")
         ↓
Router finds ExplainerAgentWrapper
         ↓
Create AgentContext (repo, PR, GitHub client, etc.)
         ↓
Agent.handle(context)
         ↓
Agent returns AgentResponse
         ↓
Router posts response to GitHub
```

### 2. Agent Context

Each agent receives an `AgentContext` with:

```python
- github_client: GitHubClient
- gemini_client: GeminiClient (optional)
- repo_name: str
- pr_number: int
- installation_id: int
- pr_title, pr_description, pr_author
- head_sha, base_sha
- command: str (e.g., "explain")
- command_args: str (e.g., "app/main.py")
- commenter: str
- metadata: Dict
```

### 3. Agent Response

Agents return an `AgentResponse` with:

```python
- success: bool
- message: str (markdown response)
- metadata: Dict (tokens, cost, etc.)
```

---

## Creating a New Agent

### Step 1: Create Agent Class

```python
# app/agents/my_agent.py
from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="MyAgent",
            description="Does something useful",
        )

    async def handle(self, context: AgentContext) -> AgentResponse:
        self.log_start(context)

        try:
            # Your logic here
            result = await do_something(context)

            message = f"## Result\n\n{result}"

            self.log_success(context)

            return AgentResponse(
                success=True,
                message=message,
                metadata={"some_stat": 42},
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)
```

### Step 2: Register Agent

```python
# app/commands/router_instance.py

from app.agents.my_agent import MyAgent

def initialize_router():
    # ... existing code ...

    # Register your agent
    router.register(
        command="mycommand",
        agent=MyAgent(),
        pattern=r"^/?mycommand\b",
    )

    return router
```

### Step 3: Test

Comment in a PR:
```
/mycommand some arguments
```

---

## Routing Patterns

### Simple Pattern

```python
router.register(
    command="help",
    agent=HelpAgent(),
    pattern=r"^/?help\b",  # Matches: /help or help at start
)
```

### Pattern with Variations

```python
router.register(
    command="explain",
    agent=ExplainerAgent(),
    pattern=r"^/?(explain|exp)\b",  # Matches: /explain or /exp
)
```

### Pattern with Arguments

The router automatically extracts arguments after the command:

```
"/explain app/main.py" → command="explain", args="app/main.py"
"/review --strict" → command="review", args="--strict"
```

---

## Error Handling

### Agent-Level Errors

```python
try:
    result = risky_operation()
except ValueError as e:
    # Agent handles specific error
    return AgentResponse(
        success=False,
        message="Invalid input: " + str(e),
    )
```

### Router-Level Errors

```python
# Unknown command → Router posts error message
# Agent not found → Router posts internal error
# Exception during execution → Router catches and posts error
```

---

## Example: Simple Agent

```python
# app/agents/ping_agent.py
from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse

class PingAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="PingAgent", description="Responds with pong")

    async def handle(self, context: AgentContext) -> AgentResponse:
        return AgentResponse(
            success=True,
            message=f"🏓 Pong! Hello @{context.commenter}!",
        )

# Register it
router.register("ping", PingAgent())
```

Usage:
```
/ping
```

Response:
```
🏓 Pong! Hello @vrushitpatel!
```

---

## Example: Agent with AI

```python
from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse

class SummarizeAgent(BaseAgent):
    async def handle(self, context: AgentContext) -> AgentResponse:
        self.log_start(context)

        try:
            # Get PR diff
            diff = context.github_client.get_pr_diff(
                repo_name=context.repo_name,
                pr_number=context.pr_number,
                installation_id=context.installation_id,
            )

            # Use AI to summarize
            prompt = f"Summarize this diff in 3 bullet points:\n\n{diff}"
            response = await context.gemini_client.generate_text(prompt)

            message = f"## Summary\n\n{response.text}"

            return AgentResponse(
                success=True,
                message=message,
                metadata={
                    "tokens_used": response.tokens_used,
                    "cost_usd": response.cost_usd,
                    "model_name": "gemini-2.5-flash-lite",
                },
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)
```

---

## Benefits

### 1. **Clean Separation**
- Each agent handles one command
- Easy to test in isolation
- Clear responsibilities

### 2. **Extensibility**
- Add new commands without touching existing code
- Just create agent + register

### 3. **Consistent Interface**
- All agents use same context/response pattern
- Predictable behavior

### 4. **Error Handling**
- Centralized error handling in router
- Agents can focus on logic

### 5. **Logging**
- Automatic logging at router and agent level
- Easy to track command execution

---

## Testing

### Unit Test an Agent

```python
import pytest
from app.agents.my_agent import MyAgent
from app.agents.base_agent import AgentContext

@pytest.mark.asyncio
async def test_my_agent():
    agent = MyAgent()

    context = AgentContext(
        github_client=mock_github_client,
        repo_name="owner/repo",
        pr_number=123,
        installation_id=456,
        command="mycommand",
        command_args="test",
    )

    response = await agent.handle(context)

    assert response.success == True
    assert "expected text" in response.message
```

### Integration Test

```python
from app.commands.router_instance import get_router

@pytest.mark.asyncio
async def test_router_integration():
    router = get_router()

    # Create mock event
    event = create_mock_issue_comment_event(
        comment_body="/mycommand test"
    )

    success = await router.route(event)

    assert success == True
```

---

## Migration Guide

### Old Way (command_handlers.py)

```python
async def handle_explain_command(event):
    # 100 lines of code
    pass

async def handle_review_command(event):
    # 150 lines of code
    pass

# Route manually
if command == "explain":
    await handle_explain_command(event)
elif command == "review":
    await handle_review_command(event)
```

### New Way (Router + Agents)

```python
# Each command is an agent
class ExplainerAgent(BaseAgent):
    async def handle(self, context):
        # 50 lines focused on explanation logic
        pass

# Router handles routing automatically
router.register("explain", ExplainerAgent())
await router.route(event)  # Automatically routes to correct agent
```

---

## Current Commands

| Command | Agent | Description |
|---------|-------|-------------|
| `/help` | HelpAgent | Show help message |
| `/explain [file]` | ExplainerAgentWrapper | Explain code changes |
| `/review` | ReviewAgentWrapper | Comprehensive code review |
| `/generate-ci [type]` | CICDAgentWrapper | Generate CI/CD workflows |

---

## Next Steps

1. **Add more agents**: Test analyzer, security scanner, etc.
2. **Add command aliases**: `/exp` → `/explain`
3. **Add command flags**: `/review --strict`
4. **Add interactive commands**: `/ask <question>`

---

## Files Structure

```
app/
├── agents/
│   ├── base_agent.py              # Abstract base class
│   ├── help_agent.py              # Help command
│   ├── explainer_agent_wrapper.py # Explain command
│   ├── review_agent_wrapper.py    # Review command
│   └── cicd_agent_wrapper.py      # CI/CD command
├── commands/
│   ├── router.py                  # Router implementation
│   ├── router_instance.py         # Global router instance
│   └── parser.py                  # Command parsing utilities
└── webhooks/
    └── github.py                  # Webhook handler (uses router)
```

---

**Questions?** Check the code or ask in issues!
