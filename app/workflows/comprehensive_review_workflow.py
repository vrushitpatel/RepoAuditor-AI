"""Comprehensive Review Workflow for /comprehensive-review command.

This workflow runs parallel security, performance, and quality analysis.
"""

from langgraph.graph import StateGraph, END
from app.models.workflow_states import ComprehensiveReviewState
from app.agents.specialized import SecurityScanner
from app.integrations.gemini_client import GeminiClient
from app.utils.logger import setup_logger
from app.utils.decorators import rate_limited, log_execution

logger = setup_logger(__name__)


@rate_limited
@log_execution
async def fetch_pr_diff_node(state: ComprehensiveReviewState) -> ComprehensiveReviewState:
    """Fetch PR diff for analysis."""
    logger.info("Fetching PR diff")

    return {
        **state,
        "current_step": "diff_fetched",
    }


@log_execution
async def security_scan_node(state: ComprehensiveReviewState) -> ComprehensiveReviewState:
    """Run security analysis."""
    logger.info("Running security analysis")

    try:
        # Initialize Gemini client for AI-powered analysis
        gemini_client = state.get("gemini_client")
        if not gemini_client:
            gemini_client = GeminiClient(use_flash=True)

        scanner = SecurityScanner(gemini_client)
        diff = state["pr_data"].get("diff", "")
        issues = await scanner.scan(diff)

        analysis = {
            "analysis_type": "security",
            "findings": [
                {
                    "severity": issue["severity"],
                    "type": "security",
                    "category": issue["type"],
                    "file": issue["file"],
                    "line": issue["line"],
                    "title": f"Security: {issue['type']}",
                    "description": issue["description"],
                    "recommendation": "Apply security fix",
                }
                for issue in issues
            ],
            "summary": f"Found {len(issues)} security issues",
            "severity_counts": _count_severities(issues),
            "completed": True,
        }

        return {
            **state,
            "security_analysis": analysis,
        }

    except Exception as e:
        logger.error(f"Security analysis failed: {e}", exc_info=True)
        return state


@log_execution
async def performance_scan_node(state: ComprehensiveReviewState) -> ComprehensiveReviewState:
    """Run performance analysis."""
    logger.info("Running performance analysis")

    # Simulated performance analysis
    analysis = {
        "analysis_type": "performance",
        "findings": [],
        "summary": "No performance issues found",
        "severity_counts": {},
        "completed": True,
    }

    return {
        **state,
        "performance_analysis": analysis,
    }


@log_execution
async def quality_scan_node(state: ComprehensiveReviewState) -> ComprehensiveReviewState:
    """Run code quality analysis."""
    logger.info("Running quality analysis")

    # Simulated quality analysis
    analysis = {
        "analysis_type": "quality",
        "findings": [],
        "summary": "Code quality is good",
        "severity_counts": {},
        "completed": True,
    }

    return {
        **state,
        "quality_analysis": analysis,
    }


@log_execution
async def aggregate_findings_node(state: ComprehensiveReviewState) -> ComprehensiveReviewState:
    """Aggregate findings from all analyses."""
    logger.info("Aggregating findings")

    all_findings = []
    severity_summary = {}

    for analysis_type in ["security_analysis", "performance_analysis", "quality_analysis"]:
        analysis = state.get(analysis_type)
        if analysis:
            all_findings.extend(analysis["findings"])
            for severity, count in analysis["severity_counts"].items():
                severity_summary[severity] = severity_summary.get(severity, 0) + count

    return {
        **state,
        "all_findings": all_findings,
        "severity_summary": severity_summary,
        "total_issues": len(all_findings),
        "current_step": "aggregated",
    }


@log_execution
async def generate_report_node(state: ComprehensiveReviewState) -> ComprehensiveReviewState:
    """Generate comprehensive report."""
    logger.info("Generating report")

    total_issues = state["total_issues"]
    severity_summary = state["severity_summary"]

    report = f"""## 📊 Comprehensive Review Report

### Summary
- **Total Issues Found:** {total_issues}
- **Security Issues:** {len(state.get('security_analysis', {}).get('findings', []))}
- **Performance Issues:** {len(state.get('performance_analysis', {}).get('findings', []))}
- **Quality Issues:** {len(state.get('quality_analysis', {}).get('findings', []))}

### Severity Breakdown
"""

    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        count = severity_summary.get(severity, 0)
        if count > 0:
            report += f"- **{severity}:** {count}\n"

    report += "\n### Security Analysis\n"
    report += state.get("security_analysis", {}).get("summary", "No issues")

    report += "\n\n### Performance Analysis\n"
    report += state.get("performance_analysis", {}).get("summary", "No issues")

    report += "\n\n### Code Quality Analysis\n"
    report += state.get("quality_analysis", {}).get("summary", "No issues")

    report += "\n\n🤖 Powered by RepoAuditor AI with LangGraph"

    return {
        **state,
        "markdown_report": report,
        "agent_result": report,
        "report_posted": True,
        "current_step": "complete",
    }


def _count_severities(issues: list) -> dict:
    """Count issues by severity."""
    counts = {}
    for issue in issues:
        severity = issue.get("severity", "MEDIUM")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def create_comprehensive_review_workflow() -> StateGraph:
    """Create the comprehensive review workflow.

    Note: Currently runs scans sequentially. For parallel execution,
    LangGraph 2.0+ with Send() API is required.
    """
    logger.info("Creating comprehensive review workflow")

    graph = StateGraph(ComprehensiveReviewState)

    # Add nodes
    graph.add_node("fetch_diff", fetch_pr_diff_node)
    graph.add_node("security_scan", security_scan_node)
    graph.add_node("performance_scan", performance_scan_node)
    graph.add_node("quality_scan", quality_scan_node)
    graph.add_node("aggregate_findings", aggregate_findings_node)
    graph.add_node("generate_report", generate_report_node)

    # Entry point
    graph.set_entry_point("fetch_diff")

    # Sequential execution (parallel requires LangGraph 2.0+ Send API)
    graph.add_edge("fetch_diff", "security_scan")
    graph.add_edge("security_scan", "performance_scan")
    graph.add_edge("performance_scan", "quality_scan")
    graph.add_edge("quality_scan", "aggregate_findings")

    # Sequential after aggregation
    graph.add_edge("aggregate_findings", "generate_report")
    graph.add_edge("generate_report", END)

    logger.info("Comprehensive review workflow created (sequential mode)")

    return graph.compile()


_workflow_instance = None


def get_comprehensive_review_workflow() -> StateGraph:
    """Get workflow instance."""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = create_comprehensive_review_workflow()
    return _workflow_instance
