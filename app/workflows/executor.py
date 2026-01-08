"""Workflow executor for running LangGraph code review workflows.

This module provides the execution logic for running code review workflows
triggered by GitHub webhooks. It handles state initialization, workflow execution,
error recovery, and result reporting.
"""

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

from app.agents.state import (
    WorkflowState,
    create_initial_workflow_state,
    validate_workflow_state,
    update_state,
    set_error,
)
from app.workflows.code_review_workflow import compile_workflow, visualize_workflow
from app.models.webhook_events import PullRequestEvent
from app.utils.logger import setup_logger
from app.utils.helpers import (
    mark_pr_as_reviewed,
    format_duration,
    format_cost,
    format_tokens,
    generate_execution_summary,
    extract_error_context,
)
from app.config import settings

logger = setup_logger(__name__)


# ============================================================================
# Workflow Executor
# ============================================================================

async def execute_code_review_workflow(
    repo_name: str,
    pr_number: int,
    installation_id: int,
    **pr_metadata
) -> WorkflowState:
    """
    Execute the complete code review workflow.

    This is the main entry point for running code reviews. It:
    1. Initializes workflow state
    2. Compiles and executes the LangGraph workflow
    3. Handles errors gracefully
    4. Caches successful reviews to prevent duplicates
    5. Returns final state with results

    Args:
        repo_name: Full repository name (owner/repo)
        pr_number: Pull request number
        installation_id: GitHub App installation ID
        **pr_metadata: Additional PR metadata (title, author, etc.)

    Returns:
        Final workflow state with results

    Example:
        ```python
        state = await execute_code_review_workflow(
            repo_name="owner/repo",
            pr_number=123,
            installation_id=456789,
            pr_title="Fix security issue",
            pr_author="developer"
        )

        if state["error"]:
            print(f"Workflow failed: {state['error']}")
        else:
            print(f"Found {len(state['review_results'])} issues")
            print(f"Cost: ${state['metadata']['total_cost_usd']:.4f}")
        ```
    """
    logger.info(
        f"Starting code review workflow for {repo_name}#{pr_number}",
        extra={
            "extra_fields": {
                "repo_name": repo_name,
                "pr_number": pr_number,
                "installation_id": installation_id,
            }
        }
    )

    try:
        # Step 1: Create initial workflow state
        state = create_initial_workflow_state(
            repo_name=repo_name,
            pr_number=pr_number,
            installation_id=installation_id,
            **pr_metadata
        )

        # Step 2: Validate initial state
        is_valid, error_msg = validate_workflow_state(state)
        if not is_valid:
            logger.error(
                f"Invalid initial state: {error_msg}",
                extra={
                    "extra_fields": {
                        "repo_name": repo_name,
                        "pr_number": pr_number,
                        "validation_error": error_msg,
                    }
                }
            )
            return set_error(state, f"State validation failed: {error_msg}")

        logger.info(
            f"Initial state created and validated",
            extra={
                "extra_fields": {
                    "repo_name": repo_name,
                    "pr_number": pr_number,
                    "state_keys": list(state.keys()),
                }
            }
        )

        # Step 3: Compile workflow
        logger.info("Compiling workflow graph...")
        workflow = compile_workflow()

        # Step 4: Execute workflow
        logger.info(
            "Executing workflow...",
            extra={
                "extra_fields": {
                    "repo_name": repo_name,
                    "pr_number": pr_number,
                }
            }
        )
        start_time = datetime.utcnow()

        final_state = await workflow.ainvoke(state)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # Step 5: Handle results and cache
        if final_state.get("error"):
            logger.error(
                f"Workflow completed with error: {final_state['error']}",
                extra={
                    "extra_fields": {
                        "repo_name": repo_name,
                        "pr_number": pr_number,
                        "duration_seconds": duration,
                        "duration_formatted": format_duration(duration),
                        "error": final_state["error"],
                    }
                }
            )
        else:
            # Log success with comprehensive metrics
            severity_counts = final_state["metadata"].get("severity_counts", {})
            total_cost = final_state["metadata"].get("total_cost_usd", 0)
            total_tokens = final_state["metadata"].get("total_tokens", 0)

            logger.info(
                f"Workflow completed successfully",
                extra={
                    "extra_fields": {
                        "repo_name": repo_name,
                        "pr_number": pr_number,
                        "duration_seconds": duration,
                        "duration_formatted": format_duration(duration),
                        "findings_count": len(final_state["review_results"]),
                        "critical_count": severity_counts.get("CRITICAL", 0),
                        "high_count": severity_counts.get("HIGH", 0),
                        "medium_count": severity_counts.get("MEDIUM", 0),
                        "low_count": severity_counts.get("LOW", 0),
                        "info_count": severity_counts.get("INFO", 0),
                        "cost_usd": total_cost,
                        "cost_formatted": format_cost(total_cost),
                        "tokens_used": total_tokens,
                        "tokens_formatted": format_tokens(total_tokens),
                        "model_calls": final_state["metadata"].get("model_calls", 0),
                        "requires_approval": final_state["metadata"].get("requires_approval", False),
                    }
                }
            )

            # Cache the successful review to prevent duplicates
            if settings.features.enable_caching:
                cache_metadata = {
                    "findings_count": len(final_state["review_results"]),
                    "cost_usd": total_cost,
                    "tokens": total_tokens,
                    "duration_seconds": duration,
                    "severity_counts": severity_counts,
                }

                mark_pr_as_reviewed(
                    repo_name=repo_name,
                    pr_number=pr_number,
                    ttl_seconds=settings.features.cache_ttl_seconds,
                    metadata=cache_metadata
                )

                logger.debug(
                    f"Cached successful review for {repo_name}#{pr_number}",
                    extra={
                        "extra_fields": {
                            "cache_ttl_seconds": settings.features.cache_ttl_seconds,
                        }
                    }
                )

        return final_state

    except Exception as e:
        error_context = extract_error_context(e, repo_name, pr_number)

        logger.error(
            f"Workflow execution failed: {e}",
            exc_info=True,
            extra={
                "extra_fields": error_context
            }
        )

        # Create error state if we don't have a state yet
        if 'state' not in locals():
            state = create_initial_workflow_state(
                repo_name=repo_name,
                pr_number=pr_number,
                installation_id=installation_id,
                **pr_metadata
            )

        return set_error(state, f"Workflow execution failed: {str(e)}")


async def execute_workflow_from_webhook(
    event: PullRequestEvent
) -> Dict[str, Any]:
    """
    Execute workflow from GitHub webhook event.

    Convenience function that extracts data from webhook event
    and executes the workflow. Includes comprehensive logging and
    error handling for webhook-triggered reviews.

    Args:
        event: Pull request webhook event

    Returns:
        Dictionary with execution results

    Example:
        ```python
        result = await execute_workflow_from_webhook(pr_event)

        if result["success"]:
            print(f"Review posted with {result['findings_count']} findings")
        else:
            print(f"Workflow failed: {result['error']}")
        ```
    """
    repo_name = event.repository.full_name if event.repository else "unknown"
    pr_number = event.number if hasattr(event, 'number') else 0

    logger.info(
        f"Processing webhook event for PR {repo_name}#{pr_number}",
        extra={
            "extra_fields": {
                "repo_name": repo_name,
                "pr_number": pr_number,
                "action": event.action if hasattr(event, 'action') else "unknown",
            }
        }
    )

    workflow_start = datetime.utcnow()

    try:
        # Extract PR data from webhook
        installation_id = event.installation.id

        logger.debug(
            f"Extracted webhook data for {repo_name}#{pr_number}",
            extra={
                "extra_fields": {
                    "installation_id": installation_id,
                    "pr_title": event.pull_request.title if hasattr(event.pull_request, 'title') else None,
                    "pr_author": event.pull_request.user.login if hasattr(event.pull_request, 'user') else None,
                }
            }
        )

        # Execute workflow
        final_state = await execute_code_review_workflow(
            repo_name=repo_name,
            pr_number=pr_number,
            installation_id=installation_id,
            pr_title=event.pull_request.title,
            pr_author=event.pull_request.user.login,
            pr_description=event.pull_request.body,
            commit_sha=event.pull_request.head["sha"]
        )

        workflow_end = datetime.utcnow()
        total_duration = (workflow_end - workflow_start).total_seconds()

        # Build result
        if final_state.get("error"):
            logger.error(
                f"Webhook workflow failed for {repo_name}#{pr_number}",
                extra={
                    "extra_fields": {
                        "repo_name": repo_name,
                        "pr_number": pr_number,
                        "error": final_state["error"],
                        "duration_seconds": total_duration,
                    }
                }
            )

            return {
                "success": False,
                "error": final_state["error"],
                "repo_name": repo_name,
                "pr_number": pr_number,
                "duration_seconds": total_duration,
            }

        # Success - log comprehensive results
        severity_counts = final_state["metadata"].get("severity_counts", {})
        total_cost = final_state["metadata"].get("total_cost_usd", 0)
        total_tokens = final_state["metadata"].get("total_tokens", 0)

        logger.info(
            f"Webhook workflow completed for {repo_name}#{pr_number}",
            extra={
                "extra_fields": {
                    "repo_name": repo_name,
                    "pr_number": pr_number,
                    "duration_seconds": total_duration,
                    "duration_formatted": format_duration(total_duration),
                    "findings_count": len(final_state["review_results"]),
                    "critical_count": severity_counts.get("CRITICAL", 0),
                    "high_count": severity_counts.get("HIGH", 0),
                    "medium_count": severity_counts.get("MEDIUM", 0),
                    "cost_usd": total_cost,
                    "cost_formatted": format_cost(total_cost),
                    "tokens_used": total_tokens,
                    "tokens_formatted": format_tokens(total_tokens),
                    "requires_approval": final_state["metadata"].get("requires_approval", False),
                }
            }
        )

        return {
            "success": True,
            "repo_name": repo_name,
            "pr_number": pr_number,
            "findings_count": len(final_state["review_results"]),
            "critical_count": severity_counts.get("CRITICAL", 0),
            "high_count": severity_counts.get("HIGH", 0),
            "medium_count": severity_counts.get("MEDIUM", 0),
            "low_count": severity_counts.get("LOW", 0),
            "info_count": severity_counts.get("INFO", 0),
            "cost_usd": total_cost,
            "cost_formatted": format_cost(total_cost),
            "tokens": total_tokens,
            "tokens_formatted": format_tokens(total_tokens),
            "duration_seconds": total_duration,
            "duration_formatted": format_duration(total_duration),
            "requires_approval": final_state["metadata"].get("requires_approval", False),
        }

    except Exception as e:
        workflow_end = datetime.utcnow()
        total_duration = (workflow_end - workflow_start).total_seconds()

        error_context = extract_error_context(e, repo_name, pr_number)
        error_context["duration_seconds"] = total_duration

        logger.error(
            f"Failed to process webhook for {repo_name}#{pr_number}: {e}",
            exc_info=True,
            extra={
                "extra_fields": error_context
            }
        )

        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "repo_name": repo_name,
            "pr_number": pr_number,
            "duration_seconds": total_duration,
        }


# ============================================================================
# Batch Execution
# ============================================================================

async def execute_multiple_reviews(
    reviews: list[Dict[str, Any]],
    max_concurrent: int = 3
) -> list[WorkflowState]:
    """
    Execute multiple code reviews concurrently.

    Useful for batch processing or catching up on multiple PRs.
    Limits concurrency to avoid overwhelming external APIs.

    Args:
        reviews: List of review requests, each with repo_name, pr_number, installation_id
        max_concurrent: Maximum number of concurrent executions

    Returns:
        List of final workflow states

    Example:
        ```python
        reviews = [
            {"repo_name": "owner/repo1", "pr_number": 123, "installation_id": 456},
            {"repo_name": "owner/repo2", "pr_number": 124, "installation_id": 456},
            {"repo_name": "owner/repo3", "pr_number": 125, "installation_id": 456},
        ]

        results = await execute_multiple_reviews(reviews, max_concurrent=2)

        for result in results:
            if result["error"]:
                print(f"Failed: {result['pr_data']['repo_name']}#{result['pr_data']['pr_number']}")
            else:
                print(f"Success: {len(result['review_results'])} findings")
        ```
    """
    logger.info(f"Starting batch execution of {len(reviews)} reviews")

    semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_with_limit(review: Dict[str, Any]) -> WorkflowState:
        """Execute single review with concurrency limit."""
        async with semaphore:
            return await execute_code_review_workflow(**review)

    # Execute all reviews concurrently (with limit)
    results = await asyncio.gather(
        *[execute_with_limit(review) for review in reviews],
        return_exceptions=True
    )

    # Handle any exceptions
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Review {i} failed with exception: {result}")
            # Create error state
            review = reviews[i]
            state = create_initial_workflow_state(
                repo_name=review.get("repo_name", "unknown"),
                pr_number=review.get("pr_number", 0),
                installation_id=review.get("installation_id", 0)
            )
            state = set_error(state, str(result))
            final_results.append(state)
        else:
            final_results.append(result)

    # Log summary
    successful = sum(1 for r in final_results if not r.get("error"))
    failed = len(final_results) - successful

    logger.info(
        f"Batch execution completed: {successful} successful, {failed} failed"
    )

    return final_results


# ============================================================================
# Workflow Testing & Debugging
# ============================================================================

async def test_workflow_execution(
    test_diff: str = None,
    test_files: list = None
) -> WorkflowState:
    """
    Test workflow execution with sample data.

    Useful for development and debugging without requiring actual GitHub webhooks.

    Args:
        test_diff: Sample git diff to analyze
        test_files: Sample file list

    Returns:
        Final workflow state

    Example:
        ```python
        test_diff = '''
        diff --git a/app/main.py b/app/main.py
        index 123..456 100644
        --- a/app/main.py
        +++ b/app/main.py
        @@ -10,7 +10,7 @@
         def login(username, password):
        -    query = f"SELECT * FROM users WHERE username = '{username}'"
        +    query = "SELECT * FROM users WHERE username = ?"
        '''

        result = await test_workflow_execution(test_diff=test_diff)
        print(f"Found {len(result['review_results'])} issues")
        ```
    """
    logger.info("Running test workflow execution")

    # Default test data
    if test_diff is None:
        test_diff = """
diff --git a/app/main.py b/app/main.py
index 1234567..abcdefg 100644
--- a/app/main.py
+++ b/app/main.py
@@ -10,7 +10,7 @@ def authenticate(username, password):
-    query = f"SELECT * FROM users WHERE username = '{username}'"
+    query = "SELECT * FROM users WHERE username = ?"
-    cursor.execute(query)
+    cursor.execute(query, (username,))
"""

    if test_files is None:
        test_files = [
            {
                "filename": "app/main.py",
                "status": "modified",
                "additions": 2,
                "deletions": 2,
                "changes": 4
            }
        ]

    # Create test state
    state = create_initial_workflow_state(
        repo_name="test/repo",
        pr_number=999,
        diff=test_diff,
        files=test_files,
        installation_id=0,  # Test mode - no actual GitHub API calls
        pr_title="Test PR - SQL injection fix",
        pr_author="test-user"
    )

    # Note: This will fail at GitHub API calls since we're using test data
    # You would need to mock the GitHub client for full testing
    logger.warning(
        "Test execution will fail at GitHub API calls. "
        "Mock GitHubClient for full testing."
    )

    try:
        workflow = compile_workflow()
        final_state = await workflow.ainvoke(state)
        return final_state
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return set_error(state, f"Test failed: {str(e)}")


def print_workflow_diagram():
    """
    Print workflow visualization to console.

    Useful for documentation and understanding the workflow structure.
    """
    print(visualize_workflow())


def get_execution_summary(state: WorkflowState) -> str:
    """
    Generate human-readable execution summary.

    Args:
        state: Final workflow state

    Returns:
        Formatted summary string
    """
    if state.get("error"):
        return f"""
Workflow Execution Summary
═══════════════════════════

Status: ❌ FAILED
Error: {state['error']}

Repository: {state['pr_data'].get('repo_name', 'Unknown')}
PR Number: #{state['pr_data'].get('pr_number', 0)}
"""

    metadata = state["metadata"]
    severity_counts = metadata.get("severity_counts", {})

    summary = f"""
Workflow Execution Summary
═══════════════════════════

Status: ✅ SUCCESS

Repository: {state['pr_data'].get('repo_name', 'Unknown')}
PR Number: #{state['pr_data'].get('pr_number', 0)}

Findings:
  Total: {len(state['review_results'])}
  Critical: {severity_counts.get('CRITICAL', 0)}
  High: {severity_counts.get('HIGH', 0)}
  Medium: {severity_counts.get('MEDIUM', 0)}
  Low: {severity_counts.get('LOW', 0)}
  Info: {severity_counts.get('INFO', 0)}

Analysis:
  Model: {metadata.get('model_name', 'Unknown')}
  Tokens: {metadata.get('total_tokens', 0):,}
  Cost: ${metadata.get('total_cost_usd', 0):.4f}
  API Calls: {metadata.get('model_calls', 0)}

Workflow:
  Duration: {metadata.get('workflow_duration_seconds', 0):.2f}s
  Requires Approval: {'Yes' if metadata.get('requires_approval') else 'No'}
  Final Step: {state.get('current_step', 'Unknown')}
"""

    return summary


# ============================================================================
# Main Entry Point (for testing)
# ============================================================================

if __name__ == "__main__":
    import sys

    # Print workflow diagram
    print_workflow_diagram()

    # Run test if requested
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("\n\nRunning test workflow...\n")

        async def run_test():
            state = await test_workflow_execution()
            print(get_execution_summary(state))

        asyncio.run(run_test())
