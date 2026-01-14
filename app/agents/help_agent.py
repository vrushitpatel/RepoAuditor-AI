"""Help agent for displaying available commands."""

from app.agents.base_agent import BaseAgent, AgentContext, AgentResponse


class HelpAgent(BaseAgent):
    """Agent that displays help information about available commands."""

    def __init__(self):
        """Initialize help agent."""
        super().__init__(
            name="HelpAgent",
            description="Provides help information about available commands",
        )

    async def handle(self, context: AgentContext) -> AgentResponse:
        """
        Display help information.

        Args:
            context: Agent context

        Returns:
            AgentResponse with help message
        """
        self.log_start(context)

        try:
            help_message = self._generate_help_message()
            self.log_success(context)

            return AgentResponse(
                success=True,
                message=help_message,
                metadata={"command_count": 10},  # Updated with new commands
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)

    def _generate_help_message(self) -> str:
        """Generate the help message with all available commands."""
        return """## 🤖 RepoAuditor AI - Available Commands

I'm your AI code review assistant with advanced LangGraph multi-agent workflows! Here's what I can do:

### 📝 Code Explanation

**`/explain`** - Explain the entire PR changes
- Shows what changed, why, and the impact
- Provides context and insights

**`/explain <file>`** - Explain a specific file
- Deep dive into a particular file
- Examples: `/explain app/main.py`

**`/explain <file>:<target>`** - Explain a specific function or class
- Focus on a particular code element
- Examples: `/explain app/main.py:health`

---

### 🔍 Code Review

**`/review`** - Get comprehensive code review
- Security vulnerabilities
- Performance issues
- Code quality suggestions
- Best practices
- Detailed findings with severity levels

---

### 🚀 CI/CD Generation

**`/generate-ci [type]`** - Generate CI/CD workflows
- Analyzes your project (language, framework, dependencies)
- Generates customized GitHub Actions workflows

**Types:** `all`, `test`, `lint`, `build`, `deploy`

---

### 🔒 Multi-Agent Workflows (NEW!)

**`/fix-security-issues`** - Automated security fix workflow
- 🔍 Scans code for security vulnerabilities
- 🛠️ Generates fixes for each issue
- ✅ Runs tests on fixes
- 🎯 Creates PR with fixes (or rolls back if tests fail)

**`/comprehensive-review`** - Multi-dimensional analysis
- 🔐 Security analysis (parallel)
- ⚡ Performance analysis (parallel)
- ✨ Code quality analysis (parallel)
- 📊 Aggregated report with severity breakdown
- 🎫 Optional Jira ticket creation

**`/auto-fix`** - Automated bug detection and fixing
- 🐛 Detects bugs using pattern matching + AI
- 🔧 Generates fixes for each bug
- 🧪 Generates test cases for fixes
- 📝 Creates PR with fixes AND tests

**`/optimize`** - Code optimization workflow
- 🌐 Detects primary language
- 💄 Applies formatter (black, prettier, etc.)
- 🔍 Applies linter (ruff, eslint, etc.)
- ✅ Runs tests
- ⏪ Rolls back if tests fail

**`/incremental-review`** - Smart incremental reviews
- 💾 Tracks previously reviewed files
- 🆕 Only reviews new/changed files
- 📝 Remembers previous feedback
- ⚡ Faster reviews on subsequent commits

---

### ⏱️ Rate Limits

To ensure fair usage:
- **Per user:** 5 commands/hour
- **Per PR:** 10 commands total
- **Per repository:** 50 commands/day

---

### ❓ Help

**`/help`** - Show this help message

---

### 💡 Tips

- All commands work with or without `/` prefix
- Multi-agent workflows use LangGraph orchestration
- Commands can be chained on subsequent commits
- Only repository collaborators can trigger commands

---

### 📊 How It Works

1. Comment with a command (e.g., `/fix-security-issues`)
2. Rate limiter checks your quota
3. LangGraph workflow orchestrates specialized agents
4. Results posted as comment on your PR
5. Metadata shows tokens used, cost, and duration

---

### 🔗 Resources

- **Setup Guide:** See `docs/Testing_Github.md`
- **Architecture:** See `docs/Agent.md`
- **Issues:** Report bugs on GitHub
- **Privacy:** Code analyzed in-memory, never stored

---

**Need more help?** Check our comprehensive documentation!

*Powered by LangGraph + Google Gemini AI 🤖*
"""
