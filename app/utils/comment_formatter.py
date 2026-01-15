"""Enhanced comment formatter for code review results with JIRA integration.

This module provides utilities for formatting review comments with:
- Clear finding IDs (#1, #2, #3)
- Action buttons for JIRA, explain, test
- Emoji severity indicators
- Code snippets with syntax highlighting
- Collapsible details
- Professional and actionable tone
"""

from typing import List, Dict, Any, Optional
from app.config import get_settings


class ReviewCommentFormatter:
    """Format code review findings into professional, actionable comments."""

    # Emoji mappings
    SEVERITY_EMOJI = {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🔵",
        "INFO": "ℹ️",
    }

    SEVERITY_LABELS = {
        "CRITICAL": "CRITICAL",
        "HIGH": "HIGH",
        "MEDIUM": "MEDIUM",
        "LOW": "LOW",
        "INFO": "INFO",
    }

    @classmethod
    def format_review_comment(
        cls,
        findings: List[Dict[str, Any]],
        severity_counts: Dict[str, int],
        metadata: Dict[str, Any],
        repo_name: str = "",
        pr_number: int = 0,
    ) -> str:
        """
        Format complete review comment with findings.

        Args:
            findings: List of finding dictionaries
            severity_counts: Count of findings by severity
            metadata: Analysis metadata (cost, time, model, etc.)
            repo_name: Repository name
            pr_number: PR number

        Returns:
            Formatted markdown comment
        """
        settings = get_settings()
        total = len(findings)

        # Choose template based on severity
        if total == 0:
            return cls._format_no_issues_comment(metadata)
        elif severity_counts.get("CRITICAL", 0) > 0:
            return cls._format_critical_issues_comment(
                findings, severity_counts, metadata, repo_name, pr_number, settings
            )
        elif severity_counts.get("HIGH", 0) > 0:
            return cls._format_high_priority_comment(
                findings, severity_counts, metadata, repo_name, pr_number, settings
            )
        else:
            return cls._format_minor_issues_comment(
                findings, severity_counts, metadata, repo_name, pr_number, settings
            )

    @classmethod
    def _format_no_issues_comment(cls, metadata: Dict[str, Any]) -> str:
        """Format comment when no issues found."""
        comment = "# 🎉 Code Review - No Issues Found!\n\n"
        comment += "## ✅ All Checks Passed\n\n"
        comment += "Your code looks great! No issues were detected during the analysis.\n\n"
        comment += "### What We Checked\n"
        comment += "- ✅ Security vulnerabilities\n"
        comment += "- ✅ Performance issues\n"
        comment += "- ✅ Code quality problems\n"
        comment += "- ✅ Best practice violations\n"
        comment += "- ✅ Potential bugs\n\n"
        comment += "---\n\n"
        comment += cls._format_metadata(metadata)
        comment += "\n*Powered by RepoAuditor AI with Google Gemini 2.0*\n"
        return comment

    @classmethod
    def _format_critical_issues_comment(
        cls,
        findings: List[Dict[str, Any]],
        severity_counts: Dict[str, int],
        metadata: Dict[str, Any],
        repo_name: str,
        pr_number: int,
        settings: Any,
    ) -> str:
        """Format comment for critical issues (urgent tone)."""
        total = len(findings)
        critical = severity_counts.get("CRITICAL", 0)
        high = severity_counts.get("HIGH", 0)

        comment = "# 🚨 Code Review - Critical Issues Found\n\n"
        comment += "## 🔍 Summary\n\n"
        comment += f"Found **{total} issue{'s' if total != 1 else ''}** that require immediate attention:\n\n"
        comment += cls._format_severity_summary(severity_counts)
        comment += "\n"

        # Quick actions
        comment += "### ⚡ Quick Actions\n\n"
        if settings.jira.enabled:
            comment += f"- 🎫 **Create JIRA tickets:** `/jira` (creates tickets for critical/high issues)\n"
        comment += f"- 💬 **Get explanation:** `/explain` (detailed analysis)\n"
        comment += f"- 🔧 **Auto-fix:** `/fix-security-issues` (automated fixes for security issues)\n\n"
        comment += "---\n\n"

        # Detailed findings
        comment += "## 📋 Detailed Findings\n\n"
        comment += cls._format_findings_by_severity(findings, repo_name, pr_number, settings)

        # Footer
        comment += cls._format_footer(total, settings, metadata)

        return comment

    @classmethod
    def _format_high_priority_comment(
        cls,
        findings: List[Dict[str, Any]],
        severity_counts: Dict[str, int],
        metadata: Dict[str, Any],
        repo_name: str,
        pr_number: int,
        settings: Any,
    ) -> str:
        """Format comment for high priority issues (balanced tone)."""
        total = len(findings)

        comment = "# 🟠 Code Review - High Priority Issues Found\n\n"
        comment += "## 🔍 Summary\n\n"
        comment += f"Found **{total} issue{'s' if total != 1 else ''}** that should be addressed:\n\n"
        comment += cls._format_severity_summary(severity_counts)
        comment += "\n"

        # Quick actions
        comment += "### ⚡ Quick Actions\n\n"
        if settings.jira.enabled:
            comment += f"- 🎫 **Create JIRA tickets:** `/jira` (for high priority issues)\n"
        comment += f"- 💬 **Get explanation:** `/explain` (detailed analysis)\n"
        comment += f"- 🔍 **Incremental review:** `/incremental-review` (review only changed files)\n\n"
        comment += "---\n\n"

        # Detailed findings
        comment += "## 📋 Detailed Findings\n\n"
        comment += cls._format_findings_by_severity(findings, repo_name, pr_number, settings)

        # Footer
        comment += cls._format_footer(total, settings, metadata)

        return comment

    @classmethod
    def _format_minor_issues_comment(
        cls,
        findings: List[Dict[str, Any]],
        severity_counts: Dict[str, int],
        metadata: Dict[str, Any],
        repo_name: str,
        pr_number: int,
        settings: Any,
    ) -> str:
        """Format comment for minor issues (encouraging tone)."""
        total = len(findings)

        comment = "# 🟡 Code Review - Minor Issues Found\n\n"
        comment += "## 🔍 Summary\n\n"
        comment += f"Good work! Found **{total} minor issue{'s' if total != 1 else ''}** to consider:\n\n"
        comment += cls._format_severity_summary(severity_counts)
        comment += "\n"
        comment += "*These are optional improvements that would enhance code quality.*\n\n"

        # Quick actions
        comment += "### ⚡ Quick Actions\n\n"
        comment += f"- 💬 **Get explanation:** `/explain` (detailed analysis)\n"
        comment += f"- 📊 **Comprehensive review:** `/comprehensive-review` (full analysis)\n\n"
        comment += "---\n\n"

        # Detailed findings
        comment += "## 📋 Detailed Findings\n\n"
        comment += cls._format_findings_by_severity(findings, repo_name, pr_number, settings)

        # Footer
        comment += cls._format_footer(total, settings, metadata)

        return comment

    @classmethod
    def _format_severity_summary(cls, severity_counts: Dict[str, int]) -> str:
        """Format severity breakdown."""
        summary = ""
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                emoji = cls.SEVERITY_EMOJI[severity]
                label = cls.SEVERITY_LABELS[severity]
                summary += f"- {emoji} **{count} {label}**\n"
        return summary

    @classmethod
    def _format_findings_by_severity(
        cls,
        findings: List[Dict[str, Any]],
        repo_name: str,
        pr_number: int,
        settings: Any,
    ) -> str:
        """Format findings grouped by severity."""
        comment = ""
        global_finding_id = 1

        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            severity_findings = [f for f in findings if f.get("severity") == severity]

            if not severity_findings:
                continue

            emoji = cls.SEVERITY_EMOJI[severity]
            label = cls.SEVERITY_LABELS[severity]

            comment += f"### {emoji} {label} Severity\n\n"

            for finding in severity_findings:
                comment += cls._format_single_finding(
                    finding, global_finding_id, repo_name, pr_number, settings
                )
                global_finding_id += 1

        return comment

    @classmethod
    def _format_single_finding(
        cls,
        finding: Dict[str, Any],
        finding_id: int,
        repo_name: str,
        pr_number: int,
        settings: Any,
    ) -> str:
        """Format a single finding."""
        comment = f"#### **#{finding_id}** - {finding.get('title', 'Issue')}\n\n"

        # Metadata line
        metadata_parts = []

        # File location with link
        if finding.get("file_path"):
            file_path = finding["file_path"]
            if finding.get("line_start"):
                line_start = finding["line_start"]
                # Create GitHub PR file link
                if repo_name and pr_number:
                    file_link = f"https://github.com/{repo_name}/pull/{pr_number}/files#diff-{hash(file_path)}R{line_start}"
                    metadata_parts.append(f"**File:** [`{file_path}:{line_start}`]({file_link})")
                else:
                    metadata_parts.append(f"**File:** `{file_path}:{line_start}`")
            else:
                metadata_parts.append(f"**File:** `{file_path}`")

        # Severity
        severity = finding.get("severity", "INFO")
        severity_emoji = cls.SEVERITY_EMOJI.get(severity, "")
        metadata_parts.append(f"**Severity:** {severity} {severity_emoji}")

        # Category/Type
        if finding.get("type"):
            metadata_parts.append(f"**Category:** {finding['type']}")

        comment += " | ".join(metadata_parts) + "\n\n"

        # Issue description
        if finding.get("description"):
            comment += "**Issue:**\n"
            comment += f"{finding['description']}\n\n"

        # Impact (if present)
        if finding.get("impact"):
            comment += "**Impact:**\n"
            comment += f"{finding['impact']}\n\n"

        # Code snippet (if present)
        if finding.get("code_snippet"):
            comment += "<details>\n"
            comment += "<summary><b>📄 View Code</b></summary>\n\n"
            comment += "```python\n"  # Default to Python, could detect language
            comment += finding["code_snippet"]
            comment += "\n```\n"
            comment += "</details>\n\n"

        # Recommendation
        if finding.get("recommendation"):
            comment += "**💡 Recommended Fix:**\n"
            comment += f"{finding['recommendation']}\n\n"

        # Example fix (if present)
        if finding.get("example_fix"):
            comment += "**✅ Suggested Code:**\n"
            comment += "```python\n"
            comment += finding["example_fix"]
            comment += "\n```\n\n"

        # Action buttons
        comment += "**Actions:**\n"
        if settings.jira.enabled:
            comment += f"- 🎫 `/jira #{finding_id}` - Create JIRA ticket for this issue\n"

        if finding.get("file_path") and finding.get("line_start"):
            comment += f"- 💡 `/explain {finding['file_path']}:{finding['line_start']}` - Get detailed explanation\n"

        comment += "\n---\n\n"

        return comment

    @classmethod
    def _format_footer(
        cls,
        total_issues: int,
        settings: Any,
        metadata: Dict[str, Any],
    ) -> str:
        """Format comment footer with actions and metadata."""
        comment = ""

        # JIRA helper section
        if total_issues > 0 and settings.jira.enabled:
            comment += "## 🎟️ JIRA Integration\n\n"
            comment += "Create JIRA tickets directly from findings:\n\n"
            comment += "```\n"
            comment += "/jira          # Create ticket for latest CRITICAL/HIGH finding\n"
            comment += "/jira #2       # Create ticket for finding #2\n"
            comment += "/jira #1 TECH  # Create ticket in specific project\n"
            comment += "```\n\n"
            comment += "---\n\n"

        # Metadata
        comment += cls._format_metadata(metadata)

        # Powered by
        comment += "\n*Powered by RepoAuditor AI with Google Gemini 2.0*\n"

        return comment

    @classmethod
    def _format_metadata(cls, metadata: Dict[str, Any]) -> str:
        """Format analysis metadata."""
        comment = "<details>\n"
        comment += "<summary><b>📊 Analysis Metadata</b></summary>\n\n"
        comment += f"- **Model:** {metadata.get('model_name', 'Unknown')}\n"
        comment += f"- **Tokens Used:** {metadata.get('total_tokens', 0):,}\n"
        comment += f"- **Cost:** ${metadata.get('total_cost_usd', 0):.4f}\n"
        comment += f"- **Analysis Time:** {metadata.get('workflow_duration_seconds', 0):.2f}s\n"
        comment += f"- **Files Analyzed:** {metadata.get('files_analyzed', 0)}\n"
        comment += "\n</details>\n"
        return comment
