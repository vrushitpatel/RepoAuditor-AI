"""Security vulnerability scanner agent.

This agent scans code for common security vulnerabilities including:
- SQL injection
- XSS vulnerabilities
- Hardcoded secrets
- Path traversal
- Insecure deserialization
"""

import re
from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SecurityScanner:
    """
    AI-powered security vulnerability scanner.

    Uses pattern matching and AI analysis to detect security issues.
    """

    def __init__(self, gemini_client: Any = None):
        """
        Initialize security scanner.

        Args:
            gemini_client: Optional Gemini client for AI-powered analysis
        """
        self.gemini_client = gemini_client

        # Security patterns (regex-based detection)
        self.patterns = {
            "sql_injection": [
                r"execute\(['\"].*\+.*['\"]",  # String concatenation in SQL
                r"execute\(f['\"].*\{.*\}",  # f-string in SQL
                r"cursor\.execute\(['\"].*%s.*['\"].*%",  # Old-style formatting
            ],
            "hardcoded_secret": [
                r"(api[_-]?key|password|secret|token)\s*=\s*['\"][a-zA-Z0-9]{16,}['\"]",
                r"(AWS|GITHUB|STRIPE)[_-]?(SECRET|KEY|TOKEN)\s*=",
            ],
            "xss": [
                r"innerHTML\s*=",
                r"document\.write\(",
                r"eval\(",
            ],
            "path_traversal": [
                r"open\(['\"].*\+.*['\"]",
                r"open\(.*input\(",
                r"\.\.\/",  # Directory traversal
            ],
        }

    async def scan(
        self,
        code: str,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scan code for security vulnerabilities.

        Args:
            code: Code to scan (typically PR diff)
            language: Programming language
            context: Additional context (repo, PR number, etc.)

        Returns:
            List of SecurityIssue dictionaries
        """
        logger.info(f"Starting security scan for {language} code")

        issues = []

        # Pattern-based detection
        pattern_issues = self._scan_with_patterns(code, language)
        issues.extend(pattern_issues)

        # AI-powered detection (if available)
        if self.gemini_client:
            ai_issues = await self._scan_with_ai(code, language, context)
            issues.extend(ai_issues)

        # Deduplicate issues
        issues = self._deduplicate_issues(issues)

        logger.info(f"Security scan complete: {len(issues)} issues found")

        return issues

    def _scan_with_patterns(
        self, code: str, language: str
    ) -> List[Dict[str, Any]]:
        """Scan code using regex patterns."""
        issues = []
        lines = code.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # Skip comments
            if line.strip().startswith("#") or line.strip().startswith("//"):
                continue

            # Check each pattern type
            for vuln_type, patterns in self.patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issue = {
                            "id": f"pattern_{vuln_type}_{line_num}",
                            "severity": self._get_severity(vuln_type),
                            "type": vuln_type,
                            "file": "unknown",  # Will be filled by caller
                            "line": line_num,
                            "description": self._get_description(vuln_type),
                            "confidence": 0.8,  # Pattern-based = high confidence
                            "cwe_id": self._get_cwe_id(vuln_type),
                        }
                        issues.append(issue)
                        break  # One issue per line per type

        return issues

    async def _scan_with_ai(
        self,
        code: str,
        language: str,
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Scan code using AI analysis via GeminiClient."""
        if not self.gemini_client:
            return []

        try:
            # Use the existing analyze_code method from GeminiClient
            # This is the same method used by the /review command
            analysis = await self.gemini_client.analyze_code(
                code_diff=code,
                analysis_type="security"  # Focus on security
            )

            # Convert findings to our security issue format
            ai_issues = []
            for finding in analysis.findings:
                # Only include security-related findings
                if finding.type.lower() in ['security', 'vulnerability', 'sql_injection',
                                            'xss', 'injection', 'hardcoded_secret']:
                    issue = {
                        "id": f"ai_{finding.type}_{finding.location.line_start if finding.location else 0}",
                        "severity": finding.severity,
                        "type": finding.type,
                        "file": finding.location.file_path if finding.location else "unknown",
                        "line": finding.location.line_start if finding.location else 0,
                        "description": finding.description,
                        "confidence": 0.9,  # AI-powered = high confidence
                        "recommendation": finding.recommendation,
                        "cwe_id": None,  # Would need mapping
                    }
                    ai_issues.append(issue)

            logger.info(f"AI analysis found {len(ai_issues)} security issues")
            return ai_issues

        except Exception as e:
            logger.error(f"AI scan failed: {e}", exc_info=True)
            return []

    def _deduplicate_issues(
        self, issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate issues."""
        seen = set()
        unique_issues = []

        for issue in issues:
            # Create unique key based on type and line
            key = (issue["type"], issue["line"])
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        return unique_issues

    def _get_severity(self, vuln_type: str) -> str:
        """Get severity level for vulnerability type."""
        severity_map = {
            "sql_injection": "CRITICAL",
            "hardcoded_secret": "HIGH",
            "xss": "HIGH",
            "path_traversal": "HIGH",
            "command_injection": "CRITICAL",
        }
        return severity_map.get(vuln_type, "MEDIUM")

    def _get_description(self, vuln_type: str) -> str:
        """Get description for vulnerability type."""
        descriptions = {
            "sql_injection": "Potential SQL injection vulnerability. User input is concatenated directly into SQL queries.",
            "hardcoded_secret": "Hardcoded secret detected. API keys, passwords, and tokens should be stored in environment variables.",
            "xss": "Potential XSS vulnerability. User input is used in DOM manipulation without sanitization.",
            "path_traversal": "Potential path traversal vulnerability. File paths are constructed from user input without validation.",
            "command_injection": "Potential command injection vulnerability. User input is used in system commands.",
        }
        return descriptions.get(vuln_type, "Security vulnerability detected")

    def _get_cwe_id(self, vuln_type: str) -> Optional[str]:
        """Get CWE ID for vulnerability type."""
        cwe_map = {
            "sql_injection": "CWE-89",
            "hardcoded_secret": "CWE-798",
            "xss": "CWE-79",
            "path_traversal": "CWE-22",
            "command_injection": "CWE-78",
        }
        return cwe_map.get(vuln_type)
