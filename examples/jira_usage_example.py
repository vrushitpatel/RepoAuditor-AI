"""Example usage of JIRA integration for RepoAuditor AI.

This script demonstrates how to:
1. Configure JIRA client
2. Create issues from code review findings
3. Add comments
4. Search issues
5. Handle errors

Prerequisites:
- Set JIRA environment variables in .env:
  - JIRA_BASE_URL
  - JIRA_EMAIL
  - JIRA_API_TOKEN
"""

import asyncio
from typing import List

from app.config import get_settings
from app.models.jira_models import JIRAConfig
from app.integrations.jira_client import (
    JIRAClient,
    JIRAError,
    JIRAAuthenticationError,
    JIRAValidationError,
    JIRARateLimitError,
)
from app.models.review_findings import Finding, CodeLocation, Severity, FindingType
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def example_1_basic_usage():
    """Example 1: Basic JIRA client usage."""
    print("\n" + "=" * 70)
    print("Example 1: Basic JIRA Client Usage")
    print("=" * 70)

    # Get settings
    settings = get_settings()

    # Check if JIRA is configured
    if not settings.jira.enabled:
        print("❌ JIRA integration not configured")
        print("Please set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in .env")
        return

    # Create config
    config = JIRAConfig(
        base_url=settings.jira.base_url,
        email=settings.jira.email,
        api_token=settings.jira.api_token,
    )

    # Initialize client
    async with JIRAClient(config) as jira:
        # Validate authentication
        try:
            await jira.validate_config()
            print("✅ JIRA authentication successful")
        except JIRAAuthenticationError as e:
            print(f"❌ Authentication failed: {e.message}")
            return

        # Create a simple issue
        try:
            issue = await jira.create_issue(
                project_key="TECH",  # Change to your project key
                summary="Test issue from RepoAuditor AI",
                description="This is a test issue created by the JIRA integration example.",
                issue_type="Task",
                priority="Medium",
                labels=["test", "automated"],
            )
            print(f"✅ Created issue: {issue.key}")
            print(f"   URL: {issue.url}")
        except JIRAValidationError as e:
            print(f"❌ Validation error: {e.message}")
            print("   Make sure the project key exists and you have permissions")


async def example_2_create_from_finding():
    """Example 2: Create JIRA issue from code review finding."""
    print("\n" + "=" * 70)
    print("Example 2: Create Issue from Finding")
    print("=" * 70)

    settings = get_settings()
    if not settings.jira.enabled:
        print("❌ JIRA integration not configured")
        return

    config = JIRAConfig(
        base_url=settings.jira.base_url,
        email=settings.jira.email,
        api_token=settings.jira.api_token,
    )

    # Create a sample finding
    finding = Finding(
        type=FindingType.SECURITY,
        severity=Severity.CRITICAL,
        title="SQL Injection Vulnerability",
        description="User input is directly concatenated to SQL query without sanitization, allowing SQL injection attacks.",
        recommendation="Use parameterized queries with prepared statements to safely handle user input.",
        location=CodeLocation(
            file_path="app/auth.py",
            line_start=42,
            line_end=42,
            code_snippet='query = "SELECT * FROM users WHERE id=" + user_id\ncursor.execute(query)',
        ),
        example_fix='query = "SELECT * FROM users WHERE id=?"\ncursor.execute(query, (user_id,))',
        references=["https://owasp.org/www-community/attacks/SQL_Injection"],
    )

    async with JIRAClient(config) as jira:
        try:
            issue = await jira.create_issue_from_finding(
                project_key="TECH",  # Change to your project key
                finding=finding,
                pr_url="https://github.com/user/repo/pull/123",
                repo_name="user/repo",
            )

            print(f"✅ Created issue from finding:")
            print(f"   Key: {issue.key}")
            print(f"   URL: {issue.url}")
            print(f"   Summary: {issue.fields.summary}")
            print(f"   Labels: {', '.join(issue.fields.labels)}")

        except JIRAError as e:
            print(f"❌ Failed to create issue: {e.message}")


async def example_3_search_and_comment():
    """Example 3: Search for issues and add comments."""
    print("\n" + "=" * 70)
    print("Example 3: Search and Comment")
    print("=" * 70)

    settings = get_settings()
    if not settings.jira.enabled:
        print("❌ JIRA integration not configured")
        return

    config = JIRAConfig(
        base_url=settings.jira.base_url,
        email=settings.jira.email,
        api_token=settings.jira.api_token,
    )

    async with JIRAClient(config) as jira:
        try:
            # Search for recent code review issues
            results = await jira.search_issues(
                jql_query='project = TECH AND labels = "code-review" ORDER BY created DESC',
                max_results=5,
            )

            print(f"Found {results.total} code review issues")
            print(f"Showing first {len(results.issues)} issues:\n")

            for i, issue in enumerate(results.issues, 1):
                print(f"{i}. {issue.key}: {issue.fields.summary}")
                print(f"   Status: {issue.fields.status.get('name', 'Unknown')}")
                print(f"   URL: {issue.url}\n")

            # Add comment to first issue (if any)
            if results.issues:
                first_issue = results.issues[0]
                comment = await jira.add_comment(
                    issue_key=first_issue.key,
                    comment="Automated comment from RepoAuditor AI: This issue has been reviewed.",
                )
                print(f"✅ Added comment to {first_issue.key}")

        except JIRAError as e:
            print(f"❌ Error: {e.message}")


async def example_4_bulk_create_with_error_handling():
    """Example 4: Bulk create issues with error handling."""
    print("\n" + "=" * 70)
    print("Example 4: Bulk Create with Error Handling")
    print("=" * 70)

    settings = get_settings()
    if not settings.jira.enabled:
        print("❌ JIRA integration not configured")
        return

    config = JIRAConfig(
        base_url=settings.jira.base_url,
        email=settings.jira.email,
        api_token=settings.jira.api_token,
    )

    # Create multiple sample findings
    findings: List[Finding] = [
        Finding(
            type=FindingType.SECURITY,
            severity=Severity.HIGH,
            title="Hardcoded API Key",
            description="Hardcoded API key detected",
            recommendation="Move API key to environment variable",
            location=CodeLocation(file_path="app/config.py", line_start=10),
        ),
        Finding(
            type=FindingType.PERFORMANCE,
            severity=Severity.MEDIUM,
            title="N+1 Query Problem",
            description="N+1 query detected in loop",
            recommendation="Use bulk query or eager loading",
            location=CodeLocation(file_path="app/models.py", line_start=55),
        ),
        Finding(
            type=FindingType.BEST_PRACTICE,
            severity=Severity.LOW,
            title="Unused Import",
            description="Unused import statement",
            recommendation="Remove unused import",
            location=CodeLocation(file_path="app/utils.py", line_start=5),
        ),
    ]

    async with JIRAClient(config) as jira:
        created_issues = []
        failed_findings = []

        for finding in findings:
            try:
                issue = await jira.create_issue_from_finding(
                    project_key="TECH",  # Change to your project key
                    finding=finding,
                    pr_url="https://github.com/user/repo/pull/456",
                )
                created_issues.append(issue)
                print(f"✅ Created {issue.key}: {finding.type}")

            except JIRARateLimitError:
                print("⏸️  Rate limited, waiting 60 seconds...")
                await asyncio.sleep(60)
                # Retry once
                try:
                    issue = await jira.create_issue_from_finding(
                        project_key="TECH",
                        finding=finding,
                        pr_url="https://github.com/user/repo/pull/456",
                    )
                    created_issues.append(issue)
                    print(f"✅ Created {issue.key} after retry: {finding.type}")
                except JIRAError as e:
                    print(f"❌ Failed after retry: {e.message}")
                    failed_findings.append(finding)

            except JIRAValidationError as e:
                print(f"❌ Validation error for {finding.type}: {e.message}")
                failed_findings.append(finding)

            except JIRAError as e:
                print(f"❌ Error creating issue for {finding.type}: {e.message}")
                failed_findings.append(finding)

        print(f"\n{'=' * 70}")
        print(f"Summary:")
        print(f"  ✅ Created: {len(created_issues)} issues")
        print(f"  ❌ Failed: {len(failed_findings)} issues")
        print(f"{'=' * 70}")


async def example_5_get_project_info():
    """Example 5: Get project information and issue types."""
    print("\n" + "=" * 70)
    print("Example 5: Get Project Information")
    print("=" * 70)

    settings = get_settings()
    if not settings.jira.enabled:
        print("❌ JIRA integration not configured")
        return

    config = JIRAConfig(
        base_url=settings.jira.base_url,
        email=settings.jira.email,
        api_token=settings.jira.api_token,
    )

    async with JIRAClient(config) as jira:
        try:
            # Get project details
            project = await jira.get_project("TECH")  # Change to your project key
            print(f"Project: {project.get('name')}")
            print(f"Key: {project.get('key')}")
            print(f"Description: {project.get('description', 'N/A')}")

            # Get available issue types
            issue_types = await jira.get_issue_types("TECH")
            print(f"\nAvailable Issue Types:")
            for issue_type in issue_types:
                print(f"  - {issue_type.get('name')}")

        except JIRAError as e:
            print(f"❌ Error: {e.message}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("RepoAuditor AI - JIRA Integration Examples")
    print("=" * 70)

    # Run examples
    await example_1_basic_usage()
    await example_2_create_from_finding()
    await example_3_search_and_comment()
    await example_4_bulk_create_with_error_handling()
    await example_5_get_project_info()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
