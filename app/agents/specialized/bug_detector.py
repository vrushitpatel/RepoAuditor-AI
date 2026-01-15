"""Bug detector agent.

Detects common bugs and code issues.
"""

import re
from typing import List, Dict, Any
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class BugDetector:
    """Detects bugs and code issues."""

    def __init__(self, gemini_client: Any = None):
        """Initialize bug detector."""
        self.gemini_client = gemini_client

        # Common bug patterns
        self.patterns = {
            "null_pointer": [
                r"\.(\w+)\s*\(",  # Method call without null check
                r"\[\w+\]",  # Array access without bounds check
            ],
            "logic_error": [
                r"if.*==.*True",  # Comparing to True/False
                r"while\s+True:",  # Infinite loop
            ],
            "type_error": [
                r"\+\s*['\"]",  # String concatenation with non-string
            ],
        }

    async def detect(
        self, code: str, language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Detect bugs in code.

        Args:
            code: Code to analyze
            language: Programming language

        Returns:
            List of Bug dictionaries
        """
        logger.info(f"Detecting bugs in {language} code")

        bugs = []
        lines = code.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # Check patterns
            for bug_type, patterns in self.patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line):
                        bug = {
                            "id": f"bug_{bug_type}_{line_num}",
                            "type": bug_type,
                            "severity": "MEDIUM",
                            "file": "unknown",
                            "line": line_num,
                            "description": f"Potential {bug_type} detected",
                            "confidence": 0.6,
                        }
                        bugs.append(bug)
                        break

        logger.info(f"Detected {len(bugs)} potential bugs")

        return bugs
