"""Personality-tuned prompts for the Explainer Agent."""

# Base system prompt for the Explainer Agent
EXPLAINER_SYSTEM_PROMPT = """
You are a helpful senior developer explaining code to a colleague at 2am during a code review session.

**Your Personality:**
- 🎯 Genuinely helpful and encouraging
- 🧠 Educational but never condescending
- 😄 Witty with occasional light programming humor
- 🚀 Focused on making complex things simple (ELI5 approach)
- 💡 Share insights about "why" not just "what"

**Your Style:**
- Use analogies and metaphors to explain complex concepts
- Break down intimidating code into digestible pieces
- Celebrate good code patterns when you see them
- Gently suggest improvements (like a friendly mentor)
- Use emojis to make explanations engaging (but not overwhelming)
- Keep explanations concise and well-structured

**Important Guidelines:**
- If code has issues, mention them constructively
- Focus on what the code does RIGHT before suggesting improvements
- Use simple language - avoid jargon when possible
- When you must use technical terms, explain them briefly
- Add relevant programming jokes or fun facts when appropriate
- Always be encouraging - writing code is hard!

Remember: Your goal is to help developers understand code in a way that makes them feel smart, not stupid.
"""


def get_file_explanation_prompt(
    file_path: str,
    file_content: str,
    context: str = "",
    pr_title: str = "",
) -> str:
    """
    Generate prompt for explaining an entire file.

    Args:
        file_path: Path to the file
        file_content: Content of the file
        context: Additional context about the PR or request
        pr_title: PR title for additional context

    Returns:
        Formatted prompt string
    """
    prompt = f"""
I need you to explain this code file in a friendly, educational way.

**File:** `{file_path}`
"""

    if pr_title:
        prompt += f"**PR Context:** {pr_title}\n"

    if context:
        prompt += f"**Additional Context:** {context}\n"

    prompt += f"""
**Code:**
```
{file_content}
```

**Your Task:**
Explain this file in a way that's both informative and enjoyable to read. Follow this structure:

## 🔍 Code Explanation: {file_path}

**TL;DR:** [One sentence that captures the essence of this file]

**What This Code Does:**
[2-3 paragraphs explaining the main functionality in simple terms. Use analogies if helpful!]

**Key Components:**
[Bullet points highlighting the important parts - functions, classes, patterns]
- **Component Name**: What it does and why it matters

**Design Choices:**
[Explain WHY the code is structured this way. What problem does this design solve?]

**Things to Note:**
[Important patterns, potential gotchas, best practices demonstrated]
- Point 1
- Point 2

**Pro Tip:** 💡
[One helpful insight or gentle suggestion for improvement]

---
**Remember:**
- Use emojis to make it engaging (but not excessive - 5-8 emojis total)
- Add a programming joke or fun fact if relevant
- Be encouraging - celebrate good code!
- Keep it concise - developers are busy
- If code has issues, mention them gently and constructively
"""

    return prompt


def get_function_explanation_prompt(
    file_path: str,
    function_name: str,
    function_code: str,
    surrounding_context: str = "",
) -> str:
    """
    Generate prompt for explaining a specific function or class.

    Args:
        file_path: Path to the file
        function_name: Name of the function/class
        function_code: Code of the specific function/class
        surrounding_context: Code around the function for context

    Returns:
        Formatted prompt string
    """
    prompt = f"""
I need you to explain this specific function/class in a friendly, educational way.

**File:** `{file_path}`
**Function/Class:** `{function_name}`

**Code to Explain:**
```
{function_code}
```
"""

    if surrounding_context:
        prompt += f"""
**Surrounding Context:**
```
{surrounding_context}
```
"""

    prompt += f"""
**Your Task:**
Explain this function/class in a focused, helpful way. Follow this structure:

## 🎯 Explaining: `{function_name}`

**What It Does:**
[1-2 sentences in plain English - imagine explaining to a friend]

**How It Works:**
[Step-by-step walkthrough in simple terms]
1. Step one...
2. Step two...

**Why It Matters:**
[Explain the purpose - what problem does this solve?]

**Notable Details:**
- Important parameters or variables
- Edge cases handled
- Patterns used (if any)

**Quick Take:** 💭
[One sentence summary + any gentle suggestions]

---
**Remember:**
- Focus on this specific function/class
- Use analogies if the logic is complex
- Add humor if appropriate
- Keep it short and sweet - 2-3 paragraphs max
- Celebrate clever solutions
"""

    return prompt


def get_pr_diff_explanation_prompt(
    pr_title: str,
    pr_description: str,
    diff_content: str,
    file_path: str = "",
) -> str:
    """
    Generate prompt for explaining PR changes.

    Args:
        pr_title: Title of the PR
        pr_description: Description of the PR
        diff_content: Diff content showing changes
        file_path: Optional specific file to focus on

    Returns:
        Formatted prompt string
    """
    prompt = f"""
I need you to explain what changed in this pull request in a friendly, clear way.

**PR Title:** {pr_title}
**PR Description:** {pr_description or "No description provided"}
"""

    if file_path:
        prompt += f"**Specific File:** `{file_path}`\n"

    prompt += f"""
**Changes (Diff):**
```diff
{diff_content}
```

**Your Task:**
Explain these changes in a way that makes sense to someone who hasn't seen the code before.

## 📝 What Changed in This PR

**TL;DR:**
[One sentence: what's the main change and why?]

**The Story:**
[2-3 paragraphs explaining what changed and why it matters. Make it narrative - tell a story!]

**File-by-File Breakdown:**
[If multiple files, break it down]
- **`filename.py`**: What changed here and why
- **`another.py`**: ...

**Impact:**
[What's different now? What problems does this solve?]

**Technical Details:**
- What was added: [brief list]
- What was removed: [brief list]
- What was modified: [brief list]

**Before vs After:**
[If helpful, show a simple comparison of the old vs new behavior]

**Developer Notes:** 📌
[Anything developers reviewing this PR should pay attention to]

---
**Remember:**
- Focus on the "why" behind changes
- Use emojis for visual breaks
- Be encouraging about good changes
- Gently note any concerns if you see them
- Keep it scannable - use formatting
- Add a fun comparison or analogy if appropriate
"""

    return prompt


def get_comparison_explanation_prompt(
    old_code: str,
    new_code: str,
    file_path: str,
    context: str = "",
) -> str:
    """
    Generate prompt for comparing before/after code.

    Args:
        old_code: Original code
        new_code: Updated code
        file_path: Path to the file
        context: Additional context

    Returns:
        Formatted prompt string
    """
    prompt = f"""
I need you to explain the difference between two versions of this code.

**File:** `{file_path}`
"""

    if context:
        prompt += f"**Context:** {context}\n"

    prompt += f"""
**Original Code (Before):**
```
{old_code}
```

**Updated Code (After):**
```
{new_code}
```

**Your Task:**
Explain what changed and why it's better (or different).

## 🔄 Before & After: `{file_path}`

**What Changed:**
[Plain English explanation of the differences]

**Why This Change:**
[What problem does this solve? What's improved?]

**Side-by-Side Comparison:**
| Before 👈 | After 👉 |
|-----------|----------|
| [Key aspect 1] | [How it changed] |
| [Key aspect 2] | [How it changed] |

**Impact:**
[What's the real-world effect of this change?]
- Performance: [Better/Worse/Same]
- Readability: [Better/Worse/Same]
- Maintainability: [Better/Worse/Same]

**Bottom Line:**
[Is this change good? Why or why not?]

---
**Remember:**
- Be objective but friendly
- Celebrate improvements
- Gently point out any concerns
- Use emojis for visual cues
- Keep it concise
"""

    return prompt


def get_architecture_explanation_prompt(
    file_paths: list,
    code_samples: dict,
    question: str = "",
) -> str:
    """
    Generate prompt for explaining architecture decisions.

    Args:
        file_paths: List of relevant file paths
        code_samples: Dict of file_path -> code_content
        question: Specific architecture question

    Returns:
        Formatted prompt string
    """
    prompt = f"""
I need you to explain the architecture/design decisions in this codebase.

**Files Involved:** {', '.join(f'`{fp}`' for fp in file_paths)}
"""

    if question:
        prompt += f"**Specific Question:** {question}\n"

    prompt += "\n**Code Samples:**\n"
    for file_path, code in code_samples.items():
        prompt += f"\n**{file_path}:**\n```\n{code}\n```\n"

    prompt += """
**Your Task:**
Explain the architectural decisions and patterns used.

## 🏗️ Architecture Deep Dive

**Overview:**
[High-level view of how these pieces fit together]

**Key Design Patterns:**
- **Pattern Name**: Why it's used here and what problem it solves

**Architecture Decisions:**
[Explain the big choices made]
1. **Decision 1**: Why this approach was chosen
2. **Decision 2**: Trade-offs and benefits

**How It All Fits Together:**
[Explain the flow/connections between components]
```
Component A → Component B → Component C
```

**Why This Design:**
[The reasoning behind the architecture]

**Trade-offs:**
- ✅ Benefits: [What this design does well]
- ⚠️ Considerations: [Potential limitations]

**Real-World Analogy:**
[Compare to something familiar - like a restaurant, factory, library, etc.]

---
**Remember:**
- Focus on the "why" more than the "what"
- Use diagrams/ASCII art if helpful
- Be honest about trade-offs
- Make it relatable with analogies
- Encourage good architecture
"""

    return prompt
