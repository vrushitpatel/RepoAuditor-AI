"""GitHub webhook handlers."""

import json
import re
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Header, Request

from app.models.webhook_events import (
    IssueCommentEvent,
    PullRequestEvent,
    PullRequestReviewCommentEvent,
)
from app.webhooks.signature import verify_github_signature
from app.workflows.executor import execute_workflow_from_webhook
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Simple metrics counter
metrics_data = {
    "total_webhooks": 0,
    "pull_request_events": 0,
    "issue_comment_events": 0,
    "review_comment_events": 0,
    "commands_processed": 0,
    "reviews_triggered": 0,
}


@router.get("/github")
async def webhook_info() -> Dict[str, str]:
    """
    GET endpoint for webhook information and testing.

    GitHub webhooks use POST, but this GET endpoint is useful
    for verifying the webhook URL is accessible.

    Returns:
        Information about the webhook endpoint
    """
    return {
        "endpoint": "/webhooks/github",
        "method": "POST",
        "description": "GitHub webhook receiver",
        "note": "Send POST requests with X-GitHub-Event and X-Hub-Signature-256 headers",
    }


@router.post("/github")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
) -> Dict[str, str]:
    """
    Handle incoming GitHub webhook events.

    This endpoint receives GitHub webhook events, verifies the signature,
    and dispatches them to appropriate handlers. Processing is done in
    background tasks to ensure immediate 200 OK response to GitHub.

    Supported events:
    - pull_request: PR opened, synchronized, reopened
    - issue_comment: Comments on PRs (for commands like /explain)
    - pull_request_review_comment: Comments on PR diffs

    Args:
        request: FastAPI request object
        background_tasks: FastAPI background tasks for async processing
        x_github_event: GitHub event type from webhook header
        x_hub_signature_256: HMAC SHA256 signature for verification

    Returns:
        Immediate response with status "received" (200 OK)

    Raises:
        HTTPException: If signature verification fails (401)
    """
    # Increment total webhooks counter
    metrics_data["total_webhooks"] += 1

    # Check required headers
    if not x_github_event:
        logger.error("Missing X-GitHub-Event header")
        return {
            "status": "error",
            "message": "Missing X-GitHub-Event header",
            "note": "This endpoint expects GitHub webhook requests with proper headers",
        }

    if not x_hub_signature_256:
        logger.error("Missing X-Hub-Signature-256 header")
        return {
            "status": "error",
            "message": "Missing X-Hub-Signature-256 header",
            "note": "Webhook signature is required for security",
        }

    # Verify webhook signature (raises HTTPException if invalid)
    try:
        body = await verify_github_signature(request, x_hub_signature_256)
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return {"status": "error", "message": "Signature verification failed"}

    # Parse JSON payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return {"status": "error", "message": "Invalid JSON payload"}

    logger.info(
        f"Received {x_github_event} event",
        extra={
            "extra_fields": {
                "event_type": x_github_event,
                "action": payload.get("action"),
                "repo": payload.get("repository", {}).get("full_name"),
            }
        },
    )

    # Handle ping event (sent when webhook is first created)
    if x_github_event == "ping":
        logger.info("Received ping event from GitHub")
        return {
            "status": "received",
            "message": "pong",
            "webhook_id": payload.get("hook_id"),
        }

    # Route to appropriate event handler
    try:
        if x_github_event == "pull_request":
            metrics_data["pull_request_events"] += 1
            await handle_pull_request_event(payload, background_tasks)
        elif x_github_event == "issue_comment":
            metrics_data["issue_comment_events"] += 1
            await handle_issue_comment_event(payload, background_tasks)
        elif x_github_event == "pull_request_review_comment":
            metrics_data["review_comment_events"] += 1
            await handle_review_comment_event(payload, background_tasks)
        else:
            logger.info(f"Ignoring unsupported event type: {x_github_event}")
    except Exception as e:
        logger.error(
            f"Error handling {x_github_event} event: {e}",
            exc_info=True,
            extra={
                "extra_fields": {
                    "event_type": x_github_event,
                    "error": str(e),
                }
            },
        )
        # Still return 200 OK to GitHub to prevent retries
        return {"status": "received", "note": "Processing error logged"}

    # Always return 200 OK immediately to GitHub
    return {"status": "received"}


async def handle_pull_request_event(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
) -> None:
    """
    Handle pull request webhook events.

    Triggers code review for PR opened, synchronized (new commits), or reopened.

    Args:
        payload: Webhook payload dictionary
        background_tasks: FastAPI background tasks for async processing
    """
    try:
        event = PullRequestEvent(**payload)
    except Exception as e:
        logger.error(
            f"Failed to parse pull request event: {e}",
            exc_info=True,
            extra={"extra_fields": {"error": str(e)}},
        )
        return

    action = event.action
    pr_number = event.number
    repo_name = event.repository.full_name

    logger.info(
        f"Pull request {action}: {repo_name}#{pr_number}",
        extra={
            "extra_fields": {
                "action": action,
                "pr_number": pr_number,
                "repo": repo_name,
            }
        },
    )

    # Trigger review for opened, synchronize (new commits), or reopened actions
    if action in ["opened", "synchronize", "reopened"]:
        logger.info(f"Triggering code review for PR #{pr_number}")
        metrics_data["reviews_triggered"] += 1

        # Process review in background to avoid blocking webhook response
        background_tasks.add_task(
            execute_workflow_from_webhook,
            event=event,
        )
    else:
        logger.debug(f"Skipping review for action: {action}")


async def handle_issue_comment_event(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
) -> None:
    """
    Handle issue comment webhook events.

    Processes comments on PRs that may contain commands like /explain, /review.
    Only processes comments on pull requests (not regular issues).

    Supported commands:
    - /explain: Explain the changes in the PR
    - /review: Trigger a new code review

    Args:
        payload: Webhook payload dictionary
        background_tasks: FastAPI background tasks for async processing
    """
    try:
        event = IssueCommentEvent(**payload)
    except Exception as e:
        logger.error(
            f"Failed to parse issue comment event: {e}",
            exc_info=True,
            extra={"extra_fields": {"error": str(e)}},
        )
        return

    # Only process "created" comments, not edited or deleted
    if event.action != "created":
        logger.debug(f"Ignoring comment action: {event.action}")
        return

    # Only process comments on pull requests, not regular issues
    if not event.issue.pull_request:
        logger.debug("Ignoring comment on regular issue (not a PR)")
        return

    comment_body = event.comment.body.strip()
    issue_number = event.issue.number
    repo_name = event.repository.full_name
    commenter = event.comment.user.login

    logger.info(
        f"Comment on PR #{issue_number} by {commenter}",
        extra={
            "extra_fields": {
                "pr_number": issue_number,
                "repo": repo_name,
                "commenter": commenter,
            }
        },
    )

    # Check for commands in the comment
    command = extract_command(comment_body)

    if command:
        logger.info(f"Command detected: {command}")
        metrics_data["commands_processed"] += 1

        # Process the command in background
        background_tasks.add_task(
            process_command,
            command=command,
            event=event,
        )
    else:
        logger.debug("No commands found in comment")


async def handle_review_comment_event(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
) -> None:
    """
    Handle pull request review comment webhook events.

    Processes comments made on specific lines in PR diffs.
    Can be used to respond to questions or provide additional context.

    Args:
        payload: Webhook payload dictionary
        background_tasks: FastAPI background tasks for async processing
    """
    try:
        event = PullRequestReviewCommentEvent(**payload)
    except Exception as e:
        logger.error(
            f"Failed to parse review comment event: {e}",
            exc_info=True,
            extra={"extra_fields": {"error": str(e)}},
        )
        return

    # Only process "created" comments
    if event.action != "created":
        logger.debug(f"Ignoring review comment action: {event.action}")
        return

    pr_number = event.pull_request.number
    repo_name = event.repository.full_name
    commenter = event.comment.user.login
    file_path = event.comment.path
    comment_body = event.comment.body.strip()

    logger.info(
        f"Review comment on PR #{pr_number} by {commenter} on {file_path}",
        extra={
            "extra_fields": {
                "pr_number": pr_number,
                "repo": repo_name,
                "commenter": commenter,
                "file": file_path,
            }
        },
    )

    # Check for commands in the review comment
    command = extract_command(comment_body)

    if command:
        logger.info(f"Command detected in review comment: {command}")
        metrics_data["commands_processed"] += 1

        # Process the command in background
        background_tasks.add_task(
            process_review_comment_command,
            command=command,
            event=event,
        )
    else:
        logger.debug("No commands found in review comment")


def extract_command(text: str) -> str | None:
    """
    Extract command from comment text.

    Commands start with / and are at the beginning of a line.
    Supported commands: /explain, /review, /help

    Args:
        text: Comment text to parse

    Returns:
        Command name without the / prefix, or None if no command found

    Examples:
        >>> extract_command("/explain")
        'explain'
        >>> extract_command("Some text /explain")
        None
        >>> extract_command("/review\\nWith description")
        'review'
    """
    # Match commands at the start of the text or after newline
    pattern = r"^/(\w+)"
    match = re.match(pattern, text.strip())

    if match:
        return match.group(1).lower()

    return None


async def process_command(command: str, event: IssueCommentEvent) -> None:
    """
    Process commands from issue comments.

    Args:
        command: Command name (without / prefix)
        event: Issue comment event data
    """
    logger.info(f"Processing command: {command}")

    # TODO: Implement command handlers
    if command == "explain":
        logger.info(f"Would explain PR #{event.issue.number}")
        # Future: Generate explanation of PR changes
    elif command == "review":
        logger.info(f"Would trigger review for PR #{event.issue.number}")
        # Future: Trigger full code review
    elif command == "help":
        logger.info("Would show help message")
        # Future: Post help comment
    else:
        logger.warning(f"Unknown command: {command}")


async def process_review_comment_command(
    command: str,
    event: PullRequestReviewCommentEvent,
) -> None:
    """
    Process commands from pull request review comments.

    Args:
        command: Command name (without / prefix)
        event: Review comment event data
    """
    logger.info(f"Processing review comment command: {command}")

    # TODO: Implement command handlers
    if command == "explain":
        logger.info(f"Would explain code at {event.comment.path}:{event.comment.line}")
        # Future: Explain specific code section
    else:
        logger.warning(f"Unknown command: {command}")


@router.get("/metrics")
async def get_metrics() -> Dict[str, int]:
    """
    Get simple webhook metrics.

    Returns a dictionary with counters for various webhook events
    and processing activities.

    Returns:
        Dictionary with metric counters:
        - total_webhooks: Total webhooks received
        - pull_request_events: PR events processed
        - issue_comment_events: Issue comment events processed
        - review_comment_events: Review comment events processed
        - commands_processed: Commands extracted from comments
        - reviews_triggered: Code reviews triggered
    """
    return metrics_data
