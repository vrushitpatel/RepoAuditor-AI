"""FastAPI application for RepoAuditor AI."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

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

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    logger.info("Starting RepoAuditor AI application")
    logger.info(f"GitHub App ID: {settings.github_app_id}")
    logger.info(f"Gemini Model: {settings.gemini_model}")
    logger.info(f"Jira Enabled: {settings.jira_enabled}")

    yield

    logger.info("Shutting down RepoAuditor AI application")


# Create FastAPI application
app = FastAPI(
    title="RepoAuditor AI",
    description="AI-powered code review system using LangGraph and Gemini",
    version="0.1.0",
    lifespan=lifespan,
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
async def root() -> Dict[str, str]:
    """
    Root endpoint.

    Returns:
        Welcome message
    """
    return {
        "name": "RepoAuditor AI",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
