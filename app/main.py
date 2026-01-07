"""FastAPI application for RepoAuditor AI."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logger import setup_logger
from app.webhooks.github import router as github_router

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles application startup and shutdown events.
    Logs configuration information on startup.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    logger.info("Starting RepoAuditor AI application")
    logger.info(f"GitHub App ID: {settings.github.app_id}")
    logger.info(f"Gemini Model: {settings.gemini.model_name}")
    logger.info(f"JIRA Enabled: {settings.jira.enabled}")
    logger.info(f"Caching Enabled: {settings.features.enable_caching}")
    logger.info(f"Log Level: {settings.server.log_level}")

    yield

    logger.info("Shutting down RepoAuditor AI application")


# Create FastAPI application
app = FastAPI(
    title="RepoAuditor AI",
    description=(
        "AI-powered code review system using LangGraph and Google Gemini. "
        "Automatically reviews pull requests via GitHub webhooks."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(github_router)


@app.get("/")
async def root() -> Dict[str, Any]:
    """
    Root endpoint providing API information.

    Returns:
        API metadata including name, version, status, and available endpoints
    """
    return {
        "name": "RepoAuditor AI",
        "version": "1.0.0",
        "status": "running",
        "description": "AI-powered code review system",
        "endpoints": {
            "health": "/health",
            "metrics": "/webhooks/metrics",
            "github_webhook": "/webhooks/github",
            "docs": "/docs",
            "redoc": "/redoc",
        },
        "supported_events": [
            "pull_request (opened, synchronize, reopened)",
            "issue_comment (created)",
            "pull_request_review_comment (created)",
        ],
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns comprehensive health status including configuration info.

    Returns:
        Health status and configuration summary
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "github_app_configured": bool(settings.github.app_id),
        "gemini_configured": bool(settings.gemini.api_key),
        "jira_enabled": settings.jira.enabled,
        "caching_enabled": settings.features.enable_caching,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
        log_level=settings.server.log_level.lower(),
    )
