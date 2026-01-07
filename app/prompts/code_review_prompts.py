"""Prompt templates for code review and analysis."""

from typing import Dict

# Base system prompt for code review
SYSTEM_PROMPT = """You are an expert code reviewer with deep knowledge of software engineering best practices, security vulnerabilities, and performance optimization. You provide clear, actionable feedback with specific examples and recommendations."""

# Analysis type prompts
SECURITY_ANALYSIS_PROMPT = """Analyze the following code diff for security vulnerabilities:

Focus on:
1. **SQL Injection**: Check for unsanitized user input in database queries
2. **XSS (Cross-Site Scripting)**: Look for unescaped user input in HTML/JavaScript
3. **Authentication/Authorization**: Verify proper access controls
4. **Secrets in Code**: Check for hardcoded passwords, API keys, tokens
5. **Path Traversal**: Look for file system access without validation
6. **Command Injection**: Check for user input in system commands
7. **Insecure Deserialization**: Look for unsafe object deserialization
8. **CSRF**: Check for missing CSRF tokens in forms
9. **Sensitive Data Exposure**: Look for logging/storing sensitive data
10. **Cryptography Issues**: Check for weak encryption or hashing

For each issue found, provide:
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Exact location (file and line numbers)
- Description of the vulnerability
- Example of how it could be exploited
- Recommended fix with code example
- References to OWASP or CVE if applicable

Code Diff:
{code_diff}

Return findings in JSON format:
{{
    "findings": [
        {{
            "severity": "HIGH",
            "type": "security",
            "title": "Brief title",
            "description": "Detailed description",
            "location": {{
                "file_path": "path/to/file.py",
                "line_start": 10,
                "line_end": 15,
                "code_snippet": "problematic code"
            }},
            "recommendation": "How to fix",
            "example_fix": "Fixed code example",
            "references": ["https://owasp.org/..."]
        }}
    ],
    "summary": "Overall security assessment"
}}"""

PERFORMANCE_ANALYSIS_PROMPT = """Analyze the following code diff for performance issues:

Focus on:
1. **N+1 Query Problem**: Check for repeated database queries in loops
2. **Inefficient Algorithms**: Look for O(n²) or worse complexity
3. **Missing Indexes**: Database queries without proper indexes
4. **Large Data Loading**: Loading entire datasets into memory
5. **Unnecessary I/O**: Redundant file reads/writes
6. **String Concatenation**: Using + instead of join() for strings
7. **Missing Caching**: Repeated expensive computations
8. **Synchronous Blocking**: Blocking I/O that could be async
9. **Memory Leaks**: Objects not being garbage collected
10. **Resource Management**: Missing connection pooling, file handles not closed

For each issue found, provide:
- Severity based on performance impact
- Location in code
- Description of the performance bottleneck
- Estimated performance impact
- Recommended optimization with code example
- Complexity analysis (Big O notation)

Code Diff:
{code_diff}

Return findings in JSON format with the same structure as security analysis."""

BEST_PRACTICES_PROMPT = """Analyze the following code diff for adherence to best practices:

Focus on:
1. **Naming Conventions**: Check for clear, descriptive names
2. **Code Structure**: Look for proper organization and modularity
3. **Error Handling**: Verify comprehensive try/except blocks
4. **Logging**: Check for appropriate logging statements
5. **Type Hints**: Verify presence and correctness of type annotations
6. **Function Length**: Check for overly long functions (>50 lines)
7. **Code Duplication**: Look for repeated code (DRY principle)
8. **Magic Numbers**: Check for hardcoded values without constants
9. **Comments**: Verify code is self-documenting or well-commented
10. **SOLID Principles**: Check for violations of SOLID principles
11. **Code Smells**: Look for common anti-patterns
12. **PEP 8 Compliance**: Check Python style guide adherence

For each issue found, provide:
- Severity (typically MEDIUM or LOW for style issues)
- Location in code
- Description of the violation
- Why it's a best practice
- Recommended improvement with example
- Reference to style guide or principle

Code Diff:
{code_diff}

Return findings in JSON format with the same structure."""

BUGS_ANALYSIS_PROMPT = """Analyze the following code diff for potential bugs and logic errors:

Focus on:
1. **Null/None Checks**: Missing null pointer checks
2. **Off-by-One Errors**: Array/list indexing issues
3. **Type Errors**: Incorrect type usage or conversions
4. **Edge Cases**: Missing handling of empty inputs, zeros, negatives
5. **Race Conditions**: Concurrency issues in threaded code
6. **Resource Leaks**: Files, connections, or memory not released
7. **Infinite Loops**: Loops without proper termination conditions
8. **Exception Handling**: Catching wrong exceptions or swallowing errors
9. **Logic Errors**: Incorrect boolean logic, wrong operators
10. **State Management**: Inconsistent object state
11. **Division by Zero**: Missing zero checks in division
12. **Integer Overflow**: Potential overflow in calculations

For each issue found, provide:
- Severity based on likelihood and impact
- Location in code
- Description of the bug
- How it could manifest
- Example input that triggers the bug
- Recommended fix with code example
- Test case to verify the fix

Code Diff:
{code_diff}

Return findings in JSON format with the same structure."""

EXPLANATION_PROMPT = """Explain the following code in detail:

Context: {context}

Code:
```
{code_snippet}
```

Provide:
1. **Overview**: High-level explanation of what this code does
2. **Step-by-Step**: Line-by-line breakdown of the logic
3. **Key Concepts**: Important programming concepts used
4. **Complexity**: Time and space complexity analysis
5. **Potential Issues**: Any concerns or edge cases
6. **Improvements**: Suggestions for making it better

Return response in JSON format:
{{
    "explanation": "Detailed explanation",
    "key_concepts": ["concept1", "concept2"],
    "complexity": "O(n) time, O(1) space",
    "suggestions": ["suggestion1", "suggestion2"]
}}"""

FIX_SUGGESTION_PROMPT = """Suggest a fix for the following issue:

Issue Description: {issue_description}

Current Code:
```
{code_context}
```

Provide:
1. **Root Cause**: What's causing the issue
2. **Fixed Code**: Complete corrected code
3. **Explanation**: Why this fix works
4. **Trade-offs**: Any trade-offs in this approach
5. **Alternatives**: Other possible solutions
6. **Testing**: How to test the fix

Return response in JSON format:
{{
    "original_code": "current code",
    "fixed_code": "corrected code",
    "explanation": "why this works",
    "trade_offs": ["trade-off1"],
    "alternatives": ["alternative1"]
}}"""

GENERAL_REVIEW_PROMPT = """Review the following code changes comprehensively:

Pull Request Title: {pr_title}
Description: {pr_description}

Analyze for:
- Security vulnerabilities
- Performance issues
- Best practices violations
- Potential bugs
- Code quality
- Maintainability
- Testing coverage

Code Diff:
{code_diff}

Provide a structured review with findings categorized by type and severity.

Return findings in JSON format with the same structure as specialized analyses."""

# Prompt templates dictionary
PROMPTS: Dict[str, str] = {
    "security": SECURITY_ANALYSIS_PROMPT,
    "performance": PERFORMANCE_ANALYSIS_PROMPT,
    "best_practices": BEST_PRACTICES_PROMPT,
    "bugs": BUGS_ANALYSIS_PROMPT,
    "explanation": EXPLANATION_PROMPT,
    "fix": FIX_SUGGESTION_PROMPT,
    "general": GENERAL_REVIEW_PROMPT,
}


def get_analysis_prompt(analysis_type: str) -> str:
    """
    Get prompt template for a specific analysis type.

    Args:
        analysis_type: Type of analysis (security, performance, best_practices, bugs, general)

    Returns:
        Prompt template string

    Raises:
        ValueError: If analysis_type is not supported
    """
    if analysis_type not in PROMPTS:
        valid_types = ", ".join(PROMPTS.keys())
        raise ValueError(
            f"Invalid analysis type: {analysis_type}. Valid types: {valid_types}"
        )
    return PROMPTS[analysis_type]


def format_security_prompt(code_diff: str) -> str:
    """Format security analysis prompt."""
    return SECURITY_ANALYSIS_PROMPT.format(code_diff=code_diff)


def format_performance_prompt(code_diff: str) -> str:
    """Format performance analysis prompt."""
    return PERFORMANCE_ANALYSIS_PROMPT.format(code_diff=code_diff)


def format_best_practices_prompt(code_diff: str) -> str:
    """Format best practices analysis prompt."""
    return BEST_PRACTICES_PROMPT.format(code_diff=code_diff)


def format_bugs_prompt(code_diff: str) -> str:
    """Format bugs analysis prompt."""
    return BUGS_ANALYSIS_PROMPT.format(code_diff=code_diff)


def format_explanation_prompt(code_snippet: str, context: str = "") -> str:
    """Format code explanation prompt."""
    return EXPLANATION_PROMPT.format(code_snippet=code_snippet, context=context)


def format_fix_prompt(issue_description: str, code_context: str) -> str:
    """Format fix suggestion prompt."""
    return FIX_SUGGESTION_PROMPT.format(
        issue_description=issue_description, code_context=code_context
    )


def format_general_prompt(
    code_diff: str, pr_title: str = "", pr_description: str = ""
) -> str:
    """Format general review prompt."""
    return GENERAL_REVIEW_PROMPT.format(
        code_diff=code_diff, pr_title=pr_title, pr_description=pr_description
    )
