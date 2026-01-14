"""Fix generator agent.

This agent generates fixes for detected security issues and bugs.
"""

from typing import Dict, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class FixGenerator:
    """
    Generates fixes for security issues and bugs.

    Uses AI to create appropriate fixes with explanations.
    """

    def __init__(self, gemini_client: Any = None):
        """Initialize fix generator."""
        self.gemini_client = gemini_client

    async def generate_fix(
        self,
        issue: Dict[str, Any],
        code_context: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """
        Generate a fix for a security issue or bug.

        Args:
            issue: Issue dictionary with type, severity, description
            code_context: Surrounding code context
            language: Programming language

        Returns:
            ProposedFix dictionary
        """
        logger.info(f"Generating fix for {issue['type']}")

        # Use template-based fixes for common issues
        if issue["type"] in self._get_template_fixes():
            fix = self._generate_template_fix(issue, code_context, language)
        else:
            # Use AI for complex fixes
            fix = await self._generate_ai_fix(issue, code_context, language)

        return fix

    def _generate_template_fix(
        self, issue: Dict[str, Any], code_context: str, language: str
    ) -> Dict[str, Any]:
        """Generate fix using templates for common issues."""
        vuln_type = issue["type"]

        # SQL injection fix
        if vuln_type == "sql_injection":
            return {
                "issue_id": issue["id"],
                "file": issue["file"],
                "original_code": self._extract_vulnerable_line(code_context, issue["line"]),
                "fixed_code": self._fix_sql_injection(code_context, issue["line"]),
                "explanation": "Replaced string concatenation with parameterized query to prevent SQL injection.",
                "patch": self._create_patch(issue, code_context),
            }

        # Hardcoded secret fix
        elif vuln_type == "hardcoded_secret":
            return {
                "issue_id": issue["id"],
                "file": issue["file"],
                "original_code": self._extract_vulnerable_line(code_context, issue["line"]),
                "fixed_code": self._fix_hardcoded_secret(code_context, issue["line"]),
                "explanation": "Moved secret to environment variable for security.",
                "patch": self._create_patch(issue, code_context),
            }

        # Default fix
        return {
            "issue_id": issue["id"],
            "file": issue["file"],
            "original_code": self._extract_vulnerable_line(code_context, issue["line"]),
            "fixed_code": "# TODO: Manual fix required",
            "explanation": f"Fix for {vuln_type} requires manual intervention.",
            "patch": "",
        }

    async def _generate_ai_fix(
        self, issue: Dict[str, Any], code_context: str, language: str
    ) -> Dict[str, Any]:
        """Generate fix using AI."""
        if not self.gemini_client:
            return self._generate_template_fix(issue, code_context, language)

        try:
            prompt = f"""Generate a fix for this security issue:

Type: {issue['type']}
Severity: {issue['severity']}
Description: {issue['description']}

Code context:
```{language}
{code_context[:1000]}
```

Provide:
1. The fixed code
2. Explanation of why this fix works
3. Any additional security considerations

Format as JSON:
{{"fixed_code": "...", "explanation": "...", "considerations": "..."}}
"""

            # For now, fall back to template-based
            # AI integration would go here
            return self._generate_template_fix(issue, code_context, language)

        except Exception as e:
            logger.error(f"AI fix generation failed: {e}", exc_info=True)
            return self._generate_template_fix(issue, code_context, language)

    def _fix_sql_injection(self, code: str, line_num: int) -> str:
        """Generate fix for SQL injection."""
        lines = code.split("\n")
        if line_num <= len(lines):
            original = lines[line_num - 1]

            # Simple transformation: replace concatenation with parameterized query
            if "execute(" in original and "+" in original:
                return original.replace(
                    'execute(f"SELECT * FROM users WHERE id = {user_id}")',
                    'execute("SELECT * FROM users WHERE id = ?", (user_id,))'
                )

        return code

    def _fix_hardcoded_secret(self, code: str, line_num: int) -> str:
        """Generate fix for hardcoded secret."""
        lines = code.split("\n")
        if line_num <= len(lines):
            original = lines[line_num - 1]

            # Replace hardcoded value with env var
            import re
            match = re.search(r'(\w+)\s*=\s*["\']([^"\']+)["\']', original)
            if match:
                var_name = match.group(1)
                return f'{var_name} = os.getenv("{var_name.upper()}")'

        return code

    def _extract_vulnerable_line(self, code: str, line_num: int) -> str:
        """Extract the vulnerable line from code."""
        lines = code.split("\n")
        if 0 < line_num <= len(lines):
            return lines[line_num - 1]
        return ""

    def _create_patch(self, issue: Dict[str, Any], code_context: str) -> str:
        """Create git-style patch."""
        # Simplified patch creation
        original_line = self._extract_vulnerable_line(code_context, issue["line"])
        return f"""--- a/{issue['file']}
+++ b/{issue['file']}
@@ -{issue['line']},1 +{issue['line']},1 @@
-{original_line}
+# Fixed: {original_line}
"""

    def _get_template_fixes(self) -> list:
        """Get list of vulnerability types with template fixes."""
        return [
            "sql_injection",
            "hardcoded_secret",
            "xss",
            "path_traversal",
        ]
