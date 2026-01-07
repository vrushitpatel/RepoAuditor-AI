"""Pytest configuration and fixtures."""

import pytest
from typing import Generator

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Create a test client for FastAPI application.

    Yields:
        Test client instance
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_github_event() -> dict:
    """
    Create a mock GitHub pull request event.

    Returns:
        Mock webhook event data
    """
    return {
        "action": "opened",
        "number": 1,
        "pull_request": {
            "id": 1,
            "number": 1,
            "title": "Test PR",
            "body": "Test description",
            "state": "open",
            "user": {
                "login": "testuser",
                "id": 1,
                "type": "User",
            },
            "head": {
                "ref": "feature-branch",
                "sha": "abc123",
            },
            "base": {
                "ref": "main",
                "sha": "def456",
            },
            "html_url": "https://github.com/test/repo/pull/1",
            "diff_url": "https://github.com/test/repo/pull/1.diff",
            "commits": 1,
            "additions": 10,
            "deletions": 5,
            "changed_files": 2,
        },
        "repository": {
            "id": 1,
            "name": "repo",
            "full_name": "test/repo",
            "private": False,
            "owner": {
                "login": "test",
                "id": 1,
                "type": "Organization",
            },
            "html_url": "https://github.com/test/repo",
            "default_branch": "main",
        },
        "installation": {
            "id": 123456,
            "account": {
                "login": "test",
                "id": 1,
                "type": "Organization",
            },
        },
        "sender": {
            "login": "testuser",
            "id": 1,
            "type": "User",
        },
    }
