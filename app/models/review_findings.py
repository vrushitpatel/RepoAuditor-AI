"""Pydantic models for code review findings."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for code review findings."""

    CRITICAL = "CRITICAL"  # Security vulnerabilities, data loss risks
    HIGH = "HIGH"  # Bugs, major performance issues
    MEDIUM = "MEDIUM"  # Code quality, minor bugs
    LOW = "LOW"  # Style issues, suggestions
    INFO = "INFO"  # Informational notes


class FindingType(str, Enum):
    """Types of code review findings."""

    SECURITY = "security"  # Security vulnerabilities
    BUG = "bug"  # Logic errors, bugs
    PERFORMANCE = "performance"  # Performance issues
    BEST_PRACTICE = "best_practice"  # Code style, best practices
    MAINTAINABILITY = "maintainability"  # Code organization, readability
    DOCUMENTATION = "documentation"  # Missing or poor documentation
    TESTING = "testing"  # Missing or inadequate tests


class CodeLocation(BaseModel):
    """Location of code in a file."""

    file_path: str = Field(..., description="Path to the file")
    line_start: Optional[int] = Field(None, description="Starting line number")
    line_end: Optional[int] = Field(None, description="Ending line number")
    code_snippet: Optional[str] = Field(None, description="Relevant code snippet")


class Finding(BaseModel):
    """A single code review finding."""

    severity: Severity = Field(..., description="Severity of the finding")
    type: FindingType = Field(..., description="Type of finding")
    title: str = Field(..., description="Short title/summary of the finding")
    description: str = Field(..., description="Detailed description of the issue")
    location: Optional[CodeLocation] = Field(None, description="Code location")
    recommendation: Optional[str] = Field(
        None, description="Recommended fix or improvement"
    )
    example_fix: Optional[str] = Field(
        None, description="Example code showing the fix"
    )
    references: List[str] = Field(
        default_factory=list, description="References to documentation, CVEs, etc."
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "severity": "HIGH",
                "type": "security",
                "title": "SQL Injection Vulnerability",
                "description": "User input is directly concatenated into SQL query without sanitization",
                "location": {
                    "file_path": "app/database.py",
                    "line_start": 42,
                    "line_end": 45,
                    "code_snippet": 'query = f"SELECT * FROM users WHERE id = {user_id}"',
                },
                "recommendation": "Use parameterized queries or an ORM to prevent SQL injection",
                "example_fix": 'query = "SELECT * FROM users WHERE id = ?"\\nresult = db.execute(query, (user_id,))',
                "references": [
                    "https://owasp.org/www-community/attacks/SQL_Injection"
                ],
            }
        }


class ReviewAnalysis(BaseModel):
    """Complete code review analysis."""

    findings: List[Finding] = Field(
        default_factory=list, description="List of findings"
    )
    summary: str = Field(..., description="Overall review summary")
    total_issues: int = Field(0, description="Total number of issues found")
    critical_count: int = Field(0, description="Number of critical issues")
    high_count: int = Field(0, description="Number of high severity issues")
    medium_count: int = Field(0, description="Number of medium severity issues")
    low_count: int = Field(0, description="Number of low severity issues")
    files_analyzed: int = Field(0, description="Number of files analyzed")
    tokens_used: int = Field(0, description="Number of tokens used")
    cost_usd: float = Field(0.0, description="Estimated cost in USD")

    def count_by_severity(self) -> None:
        """Update severity counts from findings."""
        self.total_issues = len(self.findings)
        self.critical_count = sum(
            1 for f in self.findings if f.severity == Severity.CRITICAL
        )
        self.high_count = sum(1 for f in self.findings if f.severity == Severity.HIGH)
        self.medium_count = sum(
            1 for f in self.findings if f.severity == Severity.MEDIUM
        )
        self.low_count = sum(1 for f in self.findings if f.severity == Severity.LOW)


class ExplanationResponse(BaseModel):
    """Response from code explanation request."""

    explanation: str = Field(..., description="Detailed explanation of the code")
    key_concepts: List[str] = Field(
        default_factory=list, description="Key concepts used in the code"
    )
    complexity: Optional[str] = Field(
        None, description="Complexity assessment (low/medium/high)"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Suggestions for improvement"
    )
    tokens_used: int = Field(0, description="Number of tokens used")
    cost_usd: float = Field(0.0, description="Estimated cost in USD")


class FixSuggestion(BaseModel):
    """Suggestion for fixing an issue."""

    original_code: str = Field(..., description="Original problematic code")
    fixed_code: str = Field(..., description="Suggested fixed code")
    explanation: str = Field(..., description="Explanation of the fix")
    trade_offs: List[str] = Field(
        default_factory=list, description="Trade-offs to consider"
    )
    alternatives: List[str] = Field(
        default_factory=list, description="Alternative approaches"
    )
    tokens_used: int = Field(0, description="Number of tokens used")
    cost_usd: float = Field(0.0, description="Estimated cost in USD")


class ModelConfig(BaseModel):
    """Configuration for Gemini models."""

    model_name: str = Field(..., description="Model name (e.g., gemini-2.5-flash)")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="Response randomness")
    max_output_tokens: int = Field(8192, gt=0, description="Maximum output tokens")
    top_p: float = Field(0.95, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    top_k: int = Field(40, gt=0, description="Top-k sampling parameter")

    # Cost per million tokens (approximate, update with actual pricing)
    input_cost_per_million: float = Field(
        0.075, description="Input token cost per million"
    )
    output_cost_per_million: float = Field(
        0.30, description="Output token cost per million"
    )

    @classmethod
    def flash(cls) -> "ModelConfig":
        """Get config for Gemini 2.0 Flash (fast, cost-effective)."""
        return cls(
            model_name="gemini-2.5-flash",
            temperature=0.2,
            max_output_tokens=8192,
            input_cost_per_million=0.075,
            output_cost_per_million=0.30,
        )

    @classmethod
    def pro(cls) -> "ModelConfig":
        """Get config for Gemini 1.5 Pro (more capable)."""
        return cls(
            model_name="gemini-1.5-pro-latest",
            temperature=0.2,
            max_output_tokens=8192,
            input_cost_per_million=1.25,
            output_cost_per_million=5.00,
        )

    @classmethod
    def pro_experimental(cls) -> "ModelConfig":
        """Get config for Gemini 2.0 Pro Experimental (latest)."""
        return cls(
            model_name="gemini-2.0-pro-exp",
            temperature=0.2,
            max_output_tokens=8192,
            input_cost_per_million=1.25,
            output_cost_per_million=5.00,
        )

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million
        return input_cost + output_cost
