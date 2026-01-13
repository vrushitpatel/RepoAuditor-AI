"""LangGraph workflow node implementations for code review process.

Each node is a pure function that takes WorkflowState and returns updated WorkflowState.
Nodes are designed to be composable, testable, and error-resilient.
"""

from typing import Dict, Any
import asyncio
from datetime import datetime

from app.agents.state import (
    WorkflowState,
    update_state,
    add_review_finding,
    set_error,
    update_metadata,
)
from app.integrations.github_client import GitHubClient
from app.integrations.gemini_client import GeminiClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# Node: start - Initialize State from Webhook
# ============================================================================

def start_node(state: WorkflowState) -> WorkflowState:
    """
    Initialize workflow state from webhook data.

    This is the entry point of the workflow. It validates the initial state
    and prepares it for processing.

    Args:
        state: Initial workflow state from webhook

    Returns:
        Updated state with current_step = "started"
    """
    try:
        logger.info(
            f"Starting code review workflow for {state['pr_data']['repo_name']} "
            f"PR #{state['pr_data']['pr_number']}"
        )

        # Validate required fields
        required_fields = ["repo_name", "pr_number"]
        missing_fields = [
            field for field in required_fields
            if field not in state["pr_data"]
        ]

        if missing_fields:
            return set_error(
                state,
                f"Missing required PR data fields: {missing_fields}"
            )

        # Update state to mark workflow as started
        state = update_state(
            state,
            current_step="started",
            metadata={
                **state["metadata"],
                "workflow_started_at": datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Workflow started successfully")
        return state

    except Exception as e:
        logger.error(f"Error in start_node: {e}", exc_info=True)
        return set_error(state, f"Failed to start workflow: {str(e)}")


# ============================================================================
# Node: fetch_pr - Get PR Details and Diff from GitHub
# ============================================================================

async def fetch_pr_node(state: WorkflowState) -> WorkflowState:
    """
    Fetch PR details and diff from GitHub API.

    Retrieves:
    - PR metadata (title, author, description)
    - PR diff (unified diff format)
    - List of changed files with stats

    Args:
        state: Current workflow state

    Returns:
        Updated state with PR data populated
    """
    try:
        state = update_state(state, current_step="fetching_pr")

        repo_name = state["pr_data"]["repo_name"]
        pr_number = state["pr_data"]["pr_number"]
        installation_id = state["pr_data"].get("installation_id")

        if not installation_id:
            return set_error(state, "Installation ID not found in PR data")

        logger.info(f"Fetching PR details for {repo_name}#{pr_number}")

        # Initialize GitHub client
        github_client = GitHubClient()

        # Fetch PR details
        pr_details = github_client.get_pr_details(
            repo_name=repo_name,
            pr_number=pr_number,
            installation_id=installation_id
        )

        # Fetch PR diff
        pr_diff = github_client.get_pr_diff(
            repo_name=repo_name,
            pr_number=pr_number,
            installation_id=installation_id
        )

        # Update pr_data with fetched information
        updated_pr_data = {
            **state["pr_data"],
            "title": pr_details.get("title", ""),
            "author": pr_details.get("user", {}).get("login", "unknown"),
            "description": pr_details.get("body", ""),
            "diff": pr_diff,
            "files": [
                {
                    "filename": f["filename"],
                    "status": f["status"],
                    "additions": f["additions"],
                    "deletions": f["deletions"],
                    "changes": f["changes"]
                }
                for f in pr_details.get("files", [])
            ],
            "changed_files_count": pr_details.get("changed_files", 0),
            "additions": pr_details.get("additions", 0),
            "deletions": pr_details.get("deletions", 0),
            "commit_sha": pr_details.get("head_sha", ""),
        }

        state = update_state(
            state,
            pr_data=updated_pr_data,
            current_step="pr_fetched"
        )

        logger.info(
            f"Fetched PR details: {len(updated_pr_data['files'])} files changed, "
            f"+{updated_pr_data['additions']}/-{updated_pr_data['deletions']}"
        )

        return state

    except Exception as e:
        logger.error(f"Error fetching PR: {e}", exc_info=True)
        return set_error(state, f"Failed to fetch PR details: {str(e)}")


# ============================================================================
# Node: review_code - Run Code Reviewer Agent
# ============================================================================

async def review_code_node(state: WorkflowState) -> WorkflowState:
    """
    Analyze code using Gemini AI and extract findings.

    Performs comprehensive code analysis including:
    - Security vulnerabilities
    - Performance issues
    - Best practices violations
    - Bug detection

    Args:
        state: Current workflow state with PR diff

    Returns:
        Updated state with review findings
    """
    try:
        state = update_state(state, current_step="reviewing_code")

        diff = state["pr_data"].get("diff", "")

        if not diff:
            logger.warning("No diff found, skipping code review")
            return update_state(state, current_step="review_skipped")

        logger.info(f"Starting AI code review")

        # Initialize Gemini client (use Flash model for cost efficiency)
        gemini_client = GeminiClient(use_flash=True)

        # Run comprehensive code analysis
        analysis = await gemini_client.analyze_code(
            code_diff=diff,
            analysis_type="general"  # Comprehensive review
        )

        # Add findings to state
        for finding in analysis.findings:
            state = add_review_finding(state, {
                "severity": finding.severity,
                "type": finding.type,
                "title": finding.title,
                "description": finding.description,
                "file_path": finding.location.file_path if finding.location else None,
                "line_start": finding.location.line_start if finding.location else None,
                "line_end": finding.location.line_end if finding.location else None,
                "code_snippet": finding.location.code_snippet if finding.location else None,
                "recommendation": finding.recommendation,
                "example_fix": finding.example_fix if hasattr(finding, 'example_fix') else None,
                "references": finding.references if hasattr(finding, 'references') else [],
            })

        # Update metadata with cost and usage
        state = update_metadata(
            state,
            cost_usd=analysis.cost_usd,
            tokens=analysis.tokens_used,
            model_call=True,
            model_name=gemini_client.model_config.model_name
        )

        state = update_state(state, current_step="code_reviewed")

        logger.info(
            f"Code review completed: {len(state['review_results'])} findings, "
            f"cost: ${state['metadata']['total_cost_usd']:.4f}"
        )

        return state

    except Exception as e:
        logger.error(f"Error during code review: {e}", exc_info=True)
        return set_error(state, f"Code review failed: {str(e)}")


# ============================================================================
# Node: classify_severity - Classify Findings by Severity
# ============================================================================

def classify_severity_node(state: WorkflowState) -> WorkflowState:
    """
    Classify and aggregate findings by severity level.

    Counts findings by severity and adds classification metadata.
    This helps with conditional routing and reporting.

    Args:
        state: Current workflow state with review findings

    Returns:
        Updated state with severity classification
    """
    try:
        state = update_state(state, current_step="classifying_severity")

        findings = state["review_results"]

        # Count by severity
        severity_counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0
        }

        for finding in findings:
            severity = finding.get("severity", "INFO")
            if severity in severity_counts:
                severity_counts[severity] += 1

        # Count by type
        type_counts = {}
        for finding in findings:
            finding_type = finding.get("type", "unknown")
            type_counts[finding_type] = type_counts.get(finding_type, 0) + 1

        # Update metadata with classification
        state = update_metadata(
            state,
            severity_counts=severity_counts,
            type_counts=type_counts,
            total_findings=len(findings),
            has_critical=severity_counts["CRITICAL"] > 0,
            has_high=severity_counts["HIGH"] > 0
        )

        state = update_state(state, current_step="severity_classified")

        logger.info(
            f"Severity classification: "
            f"Critical={severity_counts['CRITICAL']}, "
            f"High={severity_counts['HIGH']}, "
            f"Medium={severity_counts['MEDIUM']}, "
            f"Low={severity_counts['LOW']}, "
            f"Info={severity_counts['INFO']}"
        )

        return state

    except Exception as e:
        logger.error(f"Error classifying severity: {e}", exc_info=True)
        return set_error(state, f"Severity classification failed: {str(e)}")


# ============================================================================
# Node: post_review - Post Results to GitHub PR
# ============================================================================

async def post_review_node(state: WorkflowState) -> WorkflowState:
    """
    Post review results as a comment on the GitHub PR.

    Generates a formatted Markdown comment with:
    - Summary of findings
    - Detailed findings grouped by severity
    - Recommendations and fixes
    - Cost and metadata

    Args:
        state: Current workflow state with findings

    Returns:
        Updated state marking review as posted
    """
    try:
        state = update_state(state, current_step="posting_review")

        repo_name = state["pr_data"]["repo_name"]
        pr_number = state["pr_data"]["pr_number"]
        installation_id = state["pr_data"].get("installation_id")

        if not installation_id:
            return set_error(state, "Installation ID not found")

        # Generate review comment
        comment = generate_review_comment(state)

        logger.info(f"Posting review comment to {repo_name}#{pr_number}")

        # Post comment to GitHub
        github_client = GitHubClient()
        github_client.post_pr_comment(
            repo_name=repo_name,
            pr_number=pr_number,
            body=comment,
            installation_id=installation_id
        )

        # Update commit status
        commit_sha = state["pr_data"].get("commit_sha")
        if commit_sha:
            try:
                # Determine status based on findings
                has_critical = state["metadata"].get("has_critical", False)
                has_high = state["metadata"].get("has_high", False)

                if has_critical:
                    status_state = "failure"
                    description = "Critical issues found - review required"
                elif has_high:
                    status_state = "error"
                    description = "High severity issues found"
                else:
                    status_state = "success"
                    description = "Code review completed - no critical issues"

                github_client.update_commit_status(
                    repo_name=repo_name,
                    sha=commit_sha,
                    state=status_state,
                    description=description,
                    installation_id=installation_id,
                    context="RepoAuditor AI / Code Review"
                )
            except Exception as e:
                logger.warning(f"Failed to update commit status: {e}")

        state = update_state(state, current_step="review_posted")

        logger.info(f"Review posted successfully")

        return state

    except Exception as e:
        logger.error(f"Error posting review: {e}", exc_info=True)
        return set_error(state, f"Failed to post review: {str(e)}")


# ============================================================================
# Node: check_critical - Check if Critical Issues Found
# ============================================================================

def check_critical_node(state: WorkflowState) -> WorkflowState:
    """
    Check if any critical or high severity issues were found.

    This node is used for conditional routing - if critical issues exist,
    the workflow will route to request_approval_node.

    Args:
        state: Current workflow state

    Returns:
        Updated state with check results
    """
    try:
        state = update_state(state, current_step="checking_critical")

        has_critical = state["metadata"].get("has_critical", False)
        has_high = state["metadata"].get("has_high", False)

        state = update_metadata(
            state,
            requires_approval=has_critical or has_high,
            approval_reason=(
                "Critical issues found" if has_critical
                else "High severity issues found" if has_high
                else None
            )
        )

        state = update_state(state, current_step="critical_checked")

        logger.info(
            f"Critical check: requires_approval={has_critical or has_high}"
        )

        return state

    except Exception as e:
        logger.error(f"Error checking critical issues: {e}", exc_info=True)
        return set_error(state, f"Critical check failed: {str(e)}")


# ============================================================================
# Node: request_approval - Create Approval Request Comment
# ============================================================================

async def request_approval_node(state: WorkflowState) -> WorkflowState:
    """
    Post an approval request comment when critical issues are found.

    Creates a prominent comment requesting manual review and approval
    before the PR can be merged.

    Args:
        state: Current workflow state

    Returns:
        Updated state marking approval as requested
    """
    try:
        state = update_state(state, current_step="requesting_approval")

        repo_name = state["pr_data"]["repo_name"]
        pr_number = state["pr_data"]["pr_number"]
        installation_id = state["pr_data"].get("installation_id")

        if not installation_id:
            return set_error(state, "Installation ID not found")

        # Generate approval request comment
        approval_comment = generate_approval_request_comment(state)

        logger.info(f"Posting approval request to {repo_name}#{pr_number}")

        # Post comment
        github_client = GitHubClient()
        github_client.post_pr_comment(
            repo_name=repo_name,
            pr_number=pr_number,
            body=approval_comment,
            installation_id=installation_id
        )

        state = update_state(state, current_step="approval_requested")

        logger.info(f"Approval request posted")

        return state

    except Exception as e:
        logger.error(f"Error requesting approval: {e}", exc_info=True)
        return set_error(state, f"Failed to request approval: {str(e)}")


# ============================================================================
# Node: end - Finalize Workflow
# ============================================================================

def end_node(state: WorkflowState) -> WorkflowState:
    """
    Finalize the workflow and log completion metrics.

    This is the final node that marks the workflow as completed
    and logs all relevant metrics for monitoring and analytics.

    Args:
        state: Current workflow state

    Returns:
        Final state with current_step = "completed"
    """
    try:
        # Calculate workflow duration
        created_at = datetime.fromisoformat(state["metadata"]["created_at"])
        completed_at = datetime.utcnow()
        duration = (completed_at - created_at).total_seconds()

        # Update metadata
        state = update_metadata(
            state,
            workflow_completed_at=completed_at.isoformat(),
            workflow_duration_seconds=duration
        )

        state = update_state(state, current_step="completed")

        # Log completion metrics
        logger.info(
            f"Workflow completed for {state['pr_data']['repo_name']} "
            f"PR #{state['pr_data']['pr_number']}",
            extra={
                "duration_seconds": duration,
                "total_findings": len(state["review_results"]),
                "critical_count": state["metadata"].get("severity_counts", {}).get("CRITICAL", 0),
                "high_count": state["metadata"].get("severity_counts", {}).get("HIGH", 0),
                "total_cost_usd": state["metadata"]["total_cost_usd"],
                "total_tokens": state["metadata"]["total_tokens"],
                "model_calls": state["metadata"]["model_calls"],
                "requires_approval": state["metadata"].get("requires_approval", False)
            }
        )

        return state

    except Exception as e:
        logger.error(f"Error in end_node: {e}", exc_info=True)
        return set_error(state, f"Failed to finalize workflow: {str(e)}")


# ============================================================================
# Helper Functions
# ============================================================================

def generate_review_comment(state: WorkflowState) -> str:
    """
    Generate formatted Markdown review comment.

    Args:
        state: Workflow state with findings

    Returns:
        Formatted Markdown comment
    """
    findings = state["review_results"]
    metadata = state["metadata"]
    severity_counts = metadata.get("severity_counts", {})

    # Header
    comment = "# 🤖 RepoAuditor AI - Code Review\n\n"

    # Summary
    total = len(findings)
    if total == 0:
        comment += "✅ **No issues found!** Great job!\n\n"
        comment += "The code looks clean and follows best practices.\n\n"
    else:
        comment += f"**Found {total} issue{'s' if total != 1 else ''}:**\n\n"

        if severity_counts.get("CRITICAL", 0) > 0:
            comment += f"- ⛔ **{severity_counts['CRITICAL']} Critical**\n"
        if severity_counts.get("HIGH", 0) > 0:
            comment += f"- 🔴 **{severity_counts['HIGH']} High**\n"
        if severity_counts.get("MEDIUM", 0) > 0:
            comment += f"- 🟡 **{severity_counts['MEDIUM']} Medium**\n"
        if severity_counts.get("LOW", 0) > 0:
            comment += f"- 🔵 **{severity_counts['LOW']} Low**\n"
        if severity_counts.get("INFO", 0) > 0:
            comment += f"- ℹ️ **{severity_counts['INFO']} Info**\n"

        comment += "\n---\n\n"

        # Detailed findings
        comment += "## 📋 Detailed Findings\n\n"

        # Group by severity
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            severity_findings = [f for f in findings if f.get("severity") == severity]

            if not severity_findings:
                continue

            emoji = {
                "CRITICAL": "⛔",
                "HIGH": "🔴",
                "MEDIUM": "🟡",
                "LOW": "🔵",
                "INFO": "ℹ️"
            }[severity]

            comment += f"### {emoji} {severity} Severity\n\n"

            for i, finding in enumerate(severity_findings, 1):
                comment += f"#### {i}. {finding['title']}\n\n"
                comment += f"**Type:** {finding['type']}\n\n"

                if finding.get("file_path"):
                    location = f"`{finding['file_path']}"
                    if finding.get("line_start"):
                        location += f":{finding['line_start']}"
                        if finding.get("line_end") and finding['line_end'] != finding['line_start']:
                            location += f"-{finding['line_end']}"
                    location += "`"
                    comment += f"**Location:** {location}\n\n"

                comment += f"{finding['description']}\n\n"

                if finding.get("code_snippet"):
                    comment += "**Code:**\n```\n"
                    comment += finding['code_snippet']
                    comment += "\n```\n\n"

                if finding.get("recommendation"):
                    comment += f"**💡 Recommendation:** {finding['recommendation']}\n\n"

                if finding.get("example_fix"):
                    comment += "**✅ Example Fix:**\n```\n"
                    comment += finding['example_fix']
                    comment += "\n```\n\n"

                if finding.get("references"):
                    comment += "**📚 References:**\n"
                    for ref in finding['references']:
                        comment += f"- {ref}\n"
                    comment += "\n"

                comment += "---\n\n"

    # Footer with metadata
    comment += "\n---\n\n"
    comment += "<details>\n<summary>📊 Analysis Metadata</summary>\n\n"
    comment += f"- **Model:** {metadata.get('model_name', 'Unknown')}\n"
    comment += f"- **Tokens Used:** {metadata.get('total_tokens', 0):,}\n"
    comment += f"- **Cost:** ${metadata.get('total_cost_usd', 0):.4f}\n"
    comment += f"- **Analysis Time:** {metadata.get('workflow_duration_seconds', 0):.2f}s\n"
    comment += f"- **Files Analyzed:** {len(state['pr_data'].get('files', []))}\n"
    comment += "\n</details>\n\n"

    comment += "*Powered by RepoAuditor AI with Google Gemini 2.0*\n"

    return comment


def generate_approval_request_comment(state: WorkflowState) -> str:
    """
    Generate approval request comment for critical issues.

    Args:
        state: Workflow state

    Returns:
        Formatted approval request comment
    """
    severity_counts = state["metadata"].get("severity_counts", {})
    approval_reason = state["metadata"].get("approval_reason", "Critical issues found")

    comment = "# ⚠️ Manual Review Required\n\n"
    comment += f"**Reason:** {approval_reason}\n\n"

    if severity_counts.get("CRITICAL", 0) > 0:
        comment += f"🚨 **{severity_counts['CRITICAL']} Critical issue(s)** must be addressed before merging.\n\n"

    if severity_counts.get("HIGH", 0) > 0:
        comment += f"⚡ **{severity_counts['HIGH']} High severity issue(s)** require attention.\n\n"

    comment += "## 📝 Next Steps\n\n"
    comment += "1. Review the detailed findings in the main review comment above\n"
    comment += "2. Address critical and high severity issues\n"
    comment += "3. Request another review after fixes are applied\n"
    comment += "4. Obtain manual approval from a team lead or senior developer\n\n"

    comment += "---\n\n"
    comment += "*This PR requires manual approval due to the severity of issues found.*\n"

    return comment
