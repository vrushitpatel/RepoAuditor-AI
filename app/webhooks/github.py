"""GitHub webhook handlers."""

import json
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Header, Request

from app.models.webhook_events import PullRequestEvent
from app.webhooks.signature import verify_github_signature
from app.workflows.code_review_workflow import process_pull_request_review
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
) -> Dict[str, str]:
    """
    Handle incoming GitHub webhook events.

    Args:
        request: FastAPI request object
        background_tasks: FastAPI background tasks
        x_github_event: GitHub event type
        x_hub_signature_256: GitHub signature for verification

    Returns:
        Response indicating webhook received
    """
    # Verify webhook signature
    body = await verify_github_signature(request, x_hub_signature_256)

    # Parse JSON payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return {"status": "error", "message": "Invalid JSON payload"}

    logger.info(f"Received {x_github_event} event")

    # Handle pull request events
    if x_github_event == "pull_request":
        await handle_pull_request_event(payload, background_tasks)
    else:
        logger.info(f"Ignoring {x_github_event} event")

    return {"status": "received"}


async def handle_pull_request_event(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
) -> None:
    """
    Handle pull request webhook events.

    Args:
        payload: Webhook payload
        background_tasks: FastAPI background tasks
    """
    try:
        event = PullRequestEvent(**payload)
    except Exception as e:
        logger.error(f"Failed to parse pull request event: {e}")
        return

    action = event.action
    pr_number = event.number
    repo_name = event.repository.full_name

    logger.info(f"Pull request {action}: {repo_name}#{pr_number}")

    # Trigger review for opened or synchronize (new commits) actions
    if action in ["opened", "synchronize", "reopened"]:
        logger.info(f"Triggering code review for PR #{pr_number}")

        # Process review in background to avoid blocking webhook response
        background_tasks.add_task(
            process_pull_request_review,
            event=event,
        )
    else:
        logger.info(f"Skipping review for action: {action}")
