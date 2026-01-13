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
                metadata={"command_count": 5},  # Update this when adding commands
            )

        except Exception as e:
            self.log_error(context, e)
            return self.create_error_response(e)

    def _generate_help_message(self) -> str:
        """Generate the help message with all available commands."""
        return """## 🤖 RepoAuditor AI - Available Commands

I'm your AI code review assistant! Here's what I can do:

### 📝 Code Explanation

**`/explain`** - Explain the entire PR changes
- Shows what changed, why, and the impact
- Provides context and insights

**`/explain <file>`** - Explain a specific file
- Deep dive into a particular file
- Examples:
  - `/explain app/main.py`
  - `/explain src/components/Button.tsx`

**`/explain <file>:<target>`** - Explain a specific function or class
- Focus on a particular code element
- Examples:
  - `/explain app/main.py:health`
  - `/explain src/utils.py:calculate_metrics`

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
- Posts complete YAML in comment for you to copy

**Types:**
- `/generate-ci all` - All workflows (test, lint, build)
- `/generate-ci test` - Just testing workflow
- `/generate-ci lint` - Just linting workflow
- `/generate-ci build` - Just build workflow
- `/generate-ci deploy` - Deployment workflow

---

### ❓ Help

**`/help`** - Show this help message

---

### 💡 Tips

- Commands are case-insensitive
- File paths can use `./` prefix or not (both work)
- Commands work in PR comments and review comments
- Only repository collaborators can trigger commands

---

### 📊 How It Works

1. You comment with a command (e.g., `/explain`)
2. I analyze your PR using AI
3. I post a detailed response in a new comment
4. You can ask follow-up questions anytime!

---

### 🔗 Resources

- **Documentation:** Check the repository README
- **Issues:** Report bugs or request features on GitHub
- **Privacy:** I only access files in this PR, never store code

---

**Need more help?** Just mention specific files or areas you want me to focus on!

*Powered by Google Gemini AI 🤖*
"""
