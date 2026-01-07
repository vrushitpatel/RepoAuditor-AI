"""GitHub webhook signature verification."""

import hmac
import hashlib
from typing import Optional

from fastapi import HTTPException, Header, Request

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def verify_github_signature(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
) -> bytes:
    """
    Verify GitHub webhook signature.

    Args:
        request: FastAPI request object
        x_hub_signature_256: GitHub signature header

    Returns:
        Request body as bytes

    Raises:
        HTTPException: If signature verification fails
    """
    if not x_hub_signature_256:
        logger.error("Missing X-Hub-Signature-256 header")
        raise HTTPException(status_code=401, detail="Missing signature header")

    # Read request body
    body = await request.body()

    # Calculate expected signature
    secret = settings.github_webhook_secret.encode("utf-8")
    expected_signature = (
        "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    )

    # Compare signatures securely
    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.debug("Webhook signature verified successfully")
    return body
