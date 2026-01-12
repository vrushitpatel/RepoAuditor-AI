# Explainer Agent - Friendly Code Explainer with Personality 🤖

The Explainer Agent is a friendly, witty, and educational AI assistant that explains code like a helpful senior developer at 2am. It uses personality-tuned prompts to make code explanations engaging, clear, and genuinely helpful.

## Features

✨ **Personality-Driven**: Acts like a friendly senior developer, not a boring documentation generator
📚 **Educational**: ELI5 (Explain Like I'm 5) approach to complex concepts
😄 **Witty**: Adds light humor and programming jokes when appropriate
🎯 **Focused**: Explains the "why" behind code, not just the "what"
💡 **Constructive**: Gently suggests improvements without being condescending
🎨 **Well-Formatted**: Uses emojis and markdown for visual appeal

## Usage

### 1. Explain Entire PR

Explains all changes in a pull request with narrative storytelling:

```
/explain
```

**Example Output:**
```markdown
## 📝 What Changed in This PR

**TL;DR:**
This PR adds a friendly code explainer agent that makes code reviews more fun!

**The Story:**
Imagine you're reviewing code at 2am (we've all been there). You want explanations that are:
- Clear enough that you don't need 3 coffees to understand
- Funny enough to keep you awake
- Helpful enough to actually teach you something

That's exactly what this PR adds! 🎉

...
```

### 2. Explain Specific File

Explains what a specific file does:

```
/explain app/main.py
```

**Example Output:**
```markdown
## 🔍 Code Explanation: app/main.py

**TL;DR:** This is the heart of your FastAPI application - like the engine room of a ship!

**What This Code Does:**
Think of this file as the conductor of an orchestra...

**Key Components:**
- **FastAPI App**: The main application instance (line 43)
- **CORS Middleware**: Lets your frontend talk to your backend (line 56)
- **Health Endpoint**: The "/health" endpoint that tells you everything is OK ✅

...
```

### 3. Explain Specific Class or Function

Explains a specific class or function in detail:

```
/explain app/main.py:ExplainerAgent
```

or

```
/explain app/utils/helpers.py:format_duration
```

**Example Output:**
```markdown
## 🎯 Explaining: `ExplainerAgent`

**What It Does:**
This is the friendly AI that explains code with personality. Think of it as your 2am code review buddy!

**How It Works:**
1. Takes your code (or PR diff)
2. Runs it through Gemini with special personality prompts
3. Returns explanations that are actually fun to read

**Why It Matters:**
Because code explanations don't have to be boring! This agent helps developers understand
code faster by making it relatable and entertaining.

...
```

## Supported Formats

The Explainer Agent handles various command formats:

| Command | What It Does |
|---------|--------------|
| `/explain` | Explains the entire PR diff |
| `/explain app/main.py` | Explains the specified file |
| `/explain app/main.py:MyClass` | Explains a specific class |
| `/explain app/utils/helpers.py:my_function` | Explains a specific function |

## Personality Traits

The Explainer Agent has these personality characteristics:

### 🎯 Helpful Senior Developer
- Assumes you're smart but might not know this specific codebase
- Explains things clearly without dumbing them down
- Shares insights from experience

### 🧠 Educational
- Uses ELI5 (Explain Like I'm 5) approach for complex concepts
- Provides analogies and metaphors
- Explains the "why" behind design decisions

### 😄 Witty & Entertaining
- Adds light programming humor when appropriate
- Uses relatable comparisons
- Makes dry code fun to read about

### 💡 Constructively Critical
- Celebrates good code patterns
- Gently suggests improvements
- Never condescending or harsh

### 🎨 Visually Engaging
- Uses emojis tastefully (5-8 per explanation)
- Well-structured with headers and bullet points
- Easy to scan and read

## Architecture

The Explainer Agent consists of several components:

### Core Components

```
app/agents/explainer.py          # Main Explainer Agent class
app/prompts/explainer_prompts.py # Personality-tuned prompts
app/utils/code_fetcher.py        # Utility for fetching code from GitHub
```

### How It Works

```
User posts /explain command
         ↓
Command handler parses the request
         ↓
Explainer Agent initialized
         ↓
Code fetched from GitHub
         ↓
Personality-tuned prompt created
         ↓
Gemini generates explanation
         ↓
Formatted response posted to PR
```

## Prompt Engineering

The Explainer Agent uses carefully crafted prompts with personality:

### System Prompt

```python
You are a helpful senior developer explaining code to a colleague at 2am.

- 🎯 Genuinely helpful and encouraging
- 🧠 Educational but never condescending
- 😄 Witty with occasional programming humor
- 🚀 Focused on making complex things simple
- 💡 Share insights about "why" not just "what"
```

### Example Patterns

**Before (Boring):**
```
This function returns a list of users from the database.
```

**After (With Personality):**
```
Think of this function as your personal database DJ 🎧 - it fetches all the users
from the database and returns them as a nice, organized list. It's like asking your
friend to grab everyone for a group photo!
```

## Configuration

The Explainer Agent is configured to use:

- **Model**: Gemini 2.5 Flash Lite (fast and cost-effective)
- **Temperature**: 0.2 (consistent but still creative)
- **System Prompt**: Personality-tuned for friendliness

You can customize the personality by editing:
- `app/prompts/explainer_prompts.py` - Update EXPLAINER_SYSTEM_PROMPT
- `app/agents/explainer.py` - Adjust agent behavior

## Examples

### Example 1: Explaining a Simple File

**Input**: `/explain test_security.py`

**Output**:
```markdown
## 🔍 Code Explanation: test_security.py

**TL;DR:** Security tests that make sure your app isn't accidentally welcoming hackers!

**What This Code Does:**
This file is like a bouncer at a club 🕴️ - it checks that only the right people (requests)
get in, and that your secrets stay secret. It tests things like:
- SQL injection protection
- XSS prevention
- Authentication checks

**Key Components:**
- **test_sql_injection()**: Makes sure Bobby Tables can't drop your database 😄
- **test_xss_protection()**: Keeps malicious scripts out of your HTML
- **test_auth_required()**: Ensures protected routes actually require auth

**Design Choices:**
These tests use pytest fixtures to set up test data, which is like having a stunt double -
you can break things without consequences!

**Things to Note:**
- Uses parametrized tests for multiple cases (DRY principle!)
- Mocks external dependencies so tests run fast
- Tests both positive and negative cases

**Pro Tip:** 💡
Add these tests to your CI/CD pipeline so they run on every PR. Security bugs caught
early are way cheaper than security bugs caught by hackers!
```

### Example 2: Explaining a PR Diff

**Input**: `/explain`

**Output**:
```markdown
## 📝 What Changed in This PR

**TL;DR:**
Added a witty AI agent that explains code like a friend, not a robot!

**The Story:**
You know how most code explanations are about as exciting as reading the phone book?
Yeah, we fixed that. This PR adds an "Explainer Agent" that:
- Talks like a real person (with occasional dad jokes)
- Uses analogies you actually understand
- Makes code reviews less painful

**File-by-File Breakdown:**
- **`app/agents/explainer.py`**: The main agent class - this is the brain 🧠
- **`app/prompts/explainer_prompts.py`**: Personality prompts that make it friendly
- **`app/utils/code_fetcher.py`**: Helper for grabbing code from GitHub
- **`app/workflows/command_handlers.py`**: Updated to use the new agent

**Impact:**
- Code explanations are now actually fun to read
- Developers understand code faster with relatable analogies
- Team morale improves (who doesn't like a good programming joke?)

**Technical Details:**
- Added: 3 new modules, ~800 lines of personality-tuned code
- Modified: Command handlers to use new agent
- Dependencies: None! Uses existing Gemini and GitHub clients

**Developer Notes:** 📌
- The agent uses Gemini Flash for speed and cost
- Prompts are modular - easy to tweak the personality
- Supports multiple command formats (/explain, /explain file, /explain file:class)
```

## Testing

### Manual Testing

1. **Test on a PR**:
   ```
   /explain
   ```

2. **Test on a file**:
   ```
   /explain app/main.py
   ```

3. **Test on a class**:
   ```
   /explain app/agents/explainer.py:ExplainerAgent
   ```

### What to Check

- ✅ Explanation is friendly and engaging
- ✅ Uses emojis but not excessively
- ✅ Has clear structure (headers, bullet points)
- ✅ Includes analogies or metaphors
- ✅ Explains "why" not just "what"
- ✅ Adds light humor when appropriate
- ✅ Is actually helpful and educational

## Troubleshooting

### Issue: Explanations are too long

**Solution**: The agent has built-in truncation (500 lines max, 50k chars max). If explanations are still too long, you can:
- Use file-specific commands instead of full PR
- Adjust truncation limits in `app/utils/code_fetcher.py`

### Issue: Not enough personality

**Solution**: The personality is defined in prompts. Make them more expressive:
- Edit `app/prompts/explainer_prompts.py`
- Add more examples of desired tone
- Increase temperature in Gemini config (currently 0.2)

### Issue: Too much humor/not professional enough

**Solution**: Tone down the personality:
- Edit `EXPLAINER_SYSTEM_PROMPT` in `explainer_prompts.py`
- Remove humor-related instructions
- Focus on educational aspects only

### Issue: File not found errors

**Solution**:
- Make sure file path is correct (case-sensitive)
- Check if file exists in the PR
- Verify file is not in `.gitignore`

## Best Practices

### For Users

1. **Be specific**: `/explain app/main.py` is better than `/explain`
2. **Use colon syntax**: `/explain file.py:ClassName` for focused explanations
3. **Read the whole response**: The best insights are often in the "Pro Tip" section

### For Developers

1. **Keep prompts modular**: Each prompt type is separate
2. **Test personality changes**: Small tweaks can have big impacts
3. **Monitor costs**: Gemini Flash is cheap, but watch token usage
4. **Gather feedback**: Ask users if explanations are helpful

## Future Enhancements

Potential improvements for the Explainer Agent:

- [ ] Compare before/after versions of files
- [ ] Explain architecture decisions across multiple files
- [ ] Generate diagrams (ASCII art or mermaid)
- [ ] Interactive Q&A mode (ask follow-up questions)
- [ ] Custom personality modes (serious, very casual, etc.)
- [ ] Support for more languages (currently Python-focused)
- [ ] Explain git diffs with visual highlights
- [ ] Integration with code review comments (explain specific lines)

## API Reference

### ExplainerAgent Class

```python
class ExplainerAgent:
    """Friendly code explainer with personality."""

    def __init__(self, gemini_client: GeminiClient, github_client: GitHubClient)

    async def explain_file(
        repo_name: str,
        file_path: str,
        installation_id: int,
        pr_number: Optional[int] = None,
        context: str = "",
        pr_title: str = "",
        ref: Optional[str] = None,
    ) -> ExplanationResponse

    async def explain_function_or_class(
        repo_name: str,
        file_path: str,
        target_name: str,
        installation_id: int,
        ref: Optional[str] = None,
    ) -> ExplanationResponse

    async def explain_pr_diff(
        repo_name: str,
        pr_number: int,
        installation_id: int,
        pr_title: str = "",
        pr_description: str = "",
        specific_file: Optional[str] = None,
    ) -> ExplanationResponse

    async def explain_from_reference(
        repo_name: str,
        reference: str,
        installation_id: int,
        pr_number: Optional[int] = None,
        context: str = "",
        pr_title: str = "",
    ) -> ExplanationResponse
```

### Convenience Function

```python
async def explain_code(
    reference: str,
    repo_name: str,
    installation_id: int,
    gemini_client: GeminiClient,
    github_client: GitHubClient,
    **kwargs,
) -> ExplanationResponse
```

## Credits

Built with:
- Google Gemini 2.5 Flash Lite for AI generation
- GitHub API for code fetching
- Lots of coffee and dad jokes ☕😄

---

**Remember**: Code explanations should be helpful AND enjoyable. That's what makes the Explainer Agent special! 🎉
