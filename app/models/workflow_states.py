"""State schemas for LangGraph workflows.

This module defines TypedDict schemas for all multi-agent workflows.
Each state schema represents the data structure that flows through
a LangGraph workflow.
"""

from typing import Any, Dict, List, Optional, Set, TypedDict


# ============================================================================
# Security Fix Workflow State
# ============================================================================


class SecurityIssue(TypedDict):
    """Represents a security vulnerability found in code."""

    id: str  # Unique identifier
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    type: str  # SQL injection, XSS, hardcoded secret, etc.
    file: str  # File path
    line: int  # Line number
    description: str  # Human-readable description
    confidence: float  # Confidence score (0.0 - 1.0)
    cwe_id: Optional[str]  # Common Weakness Enumeration ID


class ProposedFix(TypedDict):
    """Represents a proposed fix for a security issue."""

    issue_id: str  # Links to SecurityIssue.id
    file: str  # File to modify
    original_code: str  # Code before fix
    fixed_code: str  # Code after fix
    explanation: str  # Why this fix works
    patch: str  # Git-style patch


class SecurityFixState(TypedDict):
    """State for /fix-security-issues workflow.

    Flow: Scan → Generate Fixes → Test → Create PR
    """

    # Input context
    repo_name: str
    pr_number: int
    installation_id: int
    command: Optional[Dict[str, Any]]  # Command details

    # GitHub clients
    github_client: Optional[Any]
    gemini_client: Optional[Any]

    # PR data
    pr_data: Dict[str, Any]  # PR details, diff, files

    # Scanning phase
    security_issues: List[SecurityIssue]
    scan_complete: bool

    # Fix generation phase
    proposed_fixes: List[ProposedFix]
    fixes_generated: bool

    # Testing phase
    test_branch_name: Optional[str]
    test_results: Dict[str, Any]  # status, passed, failed, errors
    tests_passed: bool

    # PR creation phase
    pr_url: Optional[str]
    pr_created: bool

    # Error handling
    error: Optional[str]
    rollback_needed: bool
    rollback_complete: bool

    # Workflow tracking
    current_step: str

    # Metadata
    metadata: Dict[str, Any]  # tokens, cost, duration, timestamps
    agent_result: Optional[str]  # Final result message


# ============================================================================
# Comprehensive Review Workflow State
# ============================================================================


class AnalysisResult(TypedDict):
    """Result from a single analysis (security/performance/quality)."""

    analysis_type: str  # security, performance, quality
    findings: List[Dict[str, Any]]  # List of findings
    summary: str  # Markdown summary
    severity_counts: Dict[str, int]  # CRITICAL: 2, HIGH: 5, etc.
    completed: bool


class Finding(TypedDict):
    """A single finding from comprehensive review."""

    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    type: str  # security, performance, quality
    category: str  # SQL injection, N+1 query, code smell, etc.
    file: str
    line: Optional[int]
    title: str
    description: str
    recommendation: str


class ComprehensiveReviewState(TypedDict):
    """State for /comprehensive-review workflow.

    Flow: [Security | Performance | Quality] (parallel) → Aggregate → Report → Jira
    """

    # Input context
    repo_name: str
    pr_number: int
    installation_id: int
    command: Optional[Dict[str, Any]]

    # Clients
    github_client: Optional[Any]
    gemini_client: Optional[Any]

    # PR data
    pr_data: Dict[str, Any]

    # Analysis results (from parallel execution)
    security_analysis: Optional[AnalysisResult]
    performance_analysis: Optional[AnalysisResult]
    quality_analysis: Optional[AnalysisResult]

    # Aggregation
    all_findings: List[Finding]
    severity_summary: Dict[str, int]
    total_issues: int

    # Report generation
    markdown_report: str
    report_posted: bool

    # Jira integration (optional)
    jira_enabled: bool
    jira_tickets: List[Dict[str, str]]  # ticket_key, url, summary
    jira_tickets_created: bool

    # Workflow tracking
    current_step: str
    error: Optional[str]

    # Metadata
    metadata: Dict[str, Any]
    agent_result: Optional[str]


# ============================================================================
# Auto-Fix Workflow State
# ============================================================================


class Bug(TypedDict):
    """Represents a detected bug."""

    id: str
    type: str  # Type error, logic error, null pointer, etc.
    severity: str  # HIGH, MEDIUM, LOW
    file: str
    line: int
    description: str
    confidence: float  # 0.0 - 1.0


class Fix(TypedDict):
    """Represents a bug fix."""

    bug_id: str
    file: str
    original_code: str
    fixed_code: str
    explanation: str
    patch: str


class GeneratedTest(TypedDict):
    """Represents a generated test case."""

    fix_id: str
    test_file: str  # Where to put the test
    test_code: str  # Test code
    test_framework: str  # pytest, jest, go test, etc.
    description: str  # What the test verifies


class AutoFixState(TypedDict):
    """State for /auto-fix workflow.

    Flow: Detect Bugs → Generate Fixes → Generate Tests → Create PR
    """

    # Input context
    repo_name: str
    pr_number: int
    installation_id: int
    command: Optional[Dict[str, Any]]

    # Clients
    github_client: Optional[Any]
    gemini_client: Optional[Any]

    # PR data
    pr_data: Dict[str, Any]

    # Bug detection
    detected_bugs: List[Bug]
    bugs_detected: bool

    # Fix generation
    fixes: List[Fix]
    fixes_generated: bool

    # Test generation
    generated_tests: List[GeneratedTest]
    tests_generated: bool

    # Validation
    fix_validation: Dict[str, bool]  # fix_id → is_valid
    test_validation: Dict[str, bool]  # test_id → is_valid

    # PR creation
    branch_name: str
    pr_url: Optional[str]
    pr_created: bool

    # Workflow tracking
    current_step: str
    error: Optional[str]

    # Metadata
    metadata: Dict[str, Any]
    agent_result: Optional[str]


# ============================================================================
# Optimize Workflow State
# ============================================================================


class OptimizeState(TypedDict):
    """State for /optimize workflow.

    Flow: Detect Language → Apply Formatter → Apply Linter → Test → Rollback if Failed
    """

    # Input context
    repo_name: str
    pr_number: int
    installation_id: int
    command: Optional[Dict[str, Any]]

    # Clients
    github_client: Optional[Any]
    gemini_client: Optional[Any]

    # PR data
    pr_data: Dict[str, Any]

    # Language detection
    primary_language: str  # python, javascript, typescript, go, rust, etc.
    language_confidence: float  # 0.0 - 1.0
    language_detected: bool

    # Optimization tools
    formatter_tool: str  # black, prettier, gofmt, rustfmt, etc.
    linter_tool: str  # ruff, eslint, golangci-lint, clippy, etc.

    # Optimization changes
    formatted_files: List[str]
    optimization_diff: str
    optimizations_applied: bool

    # Testing
    test_command: str  # Command to run tests
    test_output: str
    test_passed: bool
    tests_run: bool

    # Rollback
    original_state_snapshot: Dict[str, str]  # file → original content
    snapshot_created: bool
    rollback_performed: bool

    # Workflow tracking
    current_step: str
    error: Optional[str]

    # Metadata
    metadata: Dict[str, Any]
    agent_result: Optional[str]


# ============================================================================
# Incremental Review Workflow State
# ============================================================================


class FileReviewHistory(TypedDict):
    """History of reviews for a single file."""

    last_reviewed_sha: str
    last_reviewed_at: str  # ISO format timestamp
    findings_count: int
    feedback: List[str]  # Previous feedback/findings


class IncrementalReviewState(TypedDict):
    """State for /incremental-review workflow.

    Flow: Load History → Identify New Files → Review New → Merge → Save History
    """

    # Input context
    repo_name: str
    pr_number: int
    installation_id: int
    command: Optional[Dict[str, Any]]

    # Clients
    github_client: Optional[Any]
    gemini_client: Optional[Any]

    # PR data
    pr_data: Dict[str, Any]

    # File tracking
    all_files: List[str]  # All files in current PR
    previously_reviewed_files: Set[str]  # Files already reviewed
    new_files_to_review: List[str]  # Files that need review
    history_loaded: bool

    # Review results
    new_findings: List[Finding]
    previous_feedback: Dict[str, List[str]]  # file → feedback list
    review_complete: bool

    # Storage
    tracking_file_path: str  # Path to JSON file for this PR
    history_saved: bool

    # Workflow tracking
    current_step: str
    error: Optional[str]

    # Metadata
    metadata: Dict[str, Any]
    agent_result: Optional[str]


# ============================================================================
# State Helper Functions
# ============================================================================


def create_security_fix_state(
    repo_name: str,
    pr_number: int,
    installation_id: int,
    github_client: Any = None,
    gemini_client: Any = None,
    command: Optional[Dict[str, Any]] = None,
    pr_data: Optional[Dict[str, Any]] = None,
) -> SecurityFixState:
    """
    Create initial state for security fix workflow.

    Args:
        repo_name: Repository name (owner/repo)
        pr_number: Pull request number
        installation_id: GitHub App installation ID
        github_client: GitHub client instance
        gemini_client: Gemini client instance
        command: Command details
        pr_data: PR data dictionary

    Returns:
        Initialized SecurityFixState
    """
    from datetime import datetime

    return SecurityFixState(
        repo_name=repo_name,
        pr_number=pr_number,
        installation_id=installation_id,
        command=command,
        github_client=github_client,
        gemini_client=gemini_client,
        pr_data=pr_data or {},
        security_issues=[],
        scan_complete=False,
        proposed_fixes=[],
        fixes_generated=False,
        test_branch_name=None,
        test_results={},
        tests_passed=False,
        pr_url=None,
        pr_created=False,
        error=None,
        rollback_needed=False,
        rollback_complete=False,
        current_step="initialized",
        metadata={
            "created_at": datetime.utcnow().isoformat(),
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "workflow_duration_seconds": 0.0,
        },
        agent_result=None,
    )


def create_comprehensive_review_state(
    repo_name: str,
    pr_number: int,
    installation_id: int,
    github_client: Any = None,
    gemini_client: Any = None,
    command: Optional[Dict[str, Any]] = None,
    pr_data: Optional[Dict[str, Any]] = None,
) -> ComprehensiveReviewState:
    """Create initial state for comprehensive review workflow."""
    from datetime import datetime

    return ComprehensiveReviewState(
        repo_name=repo_name,
        pr_number=pr_number,
        installation_id=installation_id,
        command=command,
        github_client=github_client,
        gemini_client=gemini_client,
        pr_data=pr_data or {},
        security_analysis=None,
        performance_analysis=None,
        quality_analysis=None,
        all_findings=[],
        severity_summary={},
        total_issues=0,
        markdown_report="",
        report_posted=False,
        jira_enabled=False,
        jira_tickets=[],
        jira_tickets_created=False,
        current_step="initialized",
        error=None,
        metadata={
            "created_at": datetime.utcnow().isoformat(),
            "total_cost_usd": 0.0,
            "total_tokens": 0,
        },
        agent_result=None,
    )


def create_auto_fix_state(
    repo_name: str,
    pr_number: int,
    installation_id: int,
    github_client: Any = None,
    gemini_client: Any = None,
    command: Optional[Dict[str, Any]] = None,
    pr_data: Optional[Dict[str, Any]] = None,
) -> AutoFixState:
    """Create initial state for auto-fix workflow."""
    from datetime import datetime

    return AutoFixState(
        repo_name=repo_name,
        pr_number=pr_number,
        installation_id=installation_id,
        command=command,
        github_client=github_client,
        gemini_client=gemini_client,
        pr_data=pr_data or {},
        detected_bugs=[],
        bugs_detected=False,
        fixes=[],
        fixes_generated=False,
        generated_tests=[],
        tests_generated=False,
        fix_validation={},
        test_validation={},
        branch_name="",
        pr_url=None,
        pr_created=False,
        current_step="initialized",
        error=None,
        metadata={
            "created_at": datetime.utcnow().isoformat(),
            "total_cost_usd": 0.0,
            "total_tokens": 0,
        },
        agent_result=None,
    )


def create_optimize_state(
    repo_name: str,
    pr_number: int,
    installation_id: int,
    github_client: Any = None,
    gemini_client: Any = None,
    command: Optional[Dict[str, Any]] = None,
    pr_data: Optional[Dict[str, Any]] = None,
) -> OptimizeState:
    """Create initial state for optimize workflow."""
    from datetime import datetime

    return OptimizeState(
        repo_name=repo_name,
        pr_number=pr_number,
        installation_id=installation_id,
        command=command,
        github_client=github_client,
        gemini_client=gemini_client,
        pr_data=pr_data or {},
        primary_language="",
        language_confidence=0.0,
        language_detected=False,
        formatter_tool="",
        linter_tool="",
        formatted_files=[],
        optimization_diff="",
        optimizations_applied=False,
        test_command="",
        test_output="",
        test_passed=False,
        tests_run=False,
        original_state_snapshot={},
        snapshot_created=False,
        rollback_performed=False,
        current_step="initialized",
        error=None,
        metadata={
            "created_at": datetime.utcnow().isoformat(),
            "total_cost_usd": 0.0,
            "total_tokens": 0,
        },
        agent_result=None,
    )


def create_incremental_review_state(
    repo_name: str,
    pr_number: int,
    installation_id: int,
    github_client: Any = None,
    gemini_client: Any = None,
    command: Optional[Dict[str, Any]] = None,
    pr_data: Optional[Dict[str, Any]] = None,
) -> IncrementalReviewState:
    """Create initial state for incremental review workflow."""
    from datetime import datetime

    # Generate tracking file path
    repo_safe = repo_name.replace("/", "-")
    tracking_file = f"data/incremental_reviews/{repo_safe}/pr-{pr_number}.json"

    return IncrementalReviewState(
        repo_name=repo_name,
        pr_number=pr_number,
        installation_id=installation_id,
        command=command,
        github_client=github_client,
        gemini_client=gemini_client,
        pr_data=pr_data or {},
        all_files=[],
        previously_reviewed_files=set(),
        new_files_to_review=[],
        history_loaded=False,
        new_findings=[],
        previous_feedback={},
        review_complete=False,
        tracking_file_path=tracking_file,
        history_saved=False,
        current_step="initialized",
        error=None,
        metadata={
            "created_at": datetime.utcnow().isoformat(),
            "total_cost_usd": 0.0,
            "total_tokens": 0,
        },
        agent_result=None,
    )
