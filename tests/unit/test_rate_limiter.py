"""Unit tests for rate limiting system."""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
import tempfile

from app.utils.rate_limiter import RateLimiter, RateLimitExceeded


@pytest.fixture
def temp_rate_limiter():
    """Create a rate limiter with temporary file storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_file = Path(tmpdir) / "rate_limits.json"
        limiter = RateLimiter(data_file=data_file)
        yield limiter


@pytest.mark.asyncio
async def test_rate_limiter_initialization(temp_rate_limiter):
    """Test rate limiter initializes correctly."""
    assert temp_rate_limiter.data_file.exists()

    # Check initial data structure
    data = temp_rate_limiter._load_data()
    assert "version" in data
    assert "limits" in data
    assert "per_user" in data["limits"]
    assert "per_pr" in data["limits"]
    assert "per_repo" in data["limits"]


@pytest.mark.asyncio
async def test_user_rate_limit(temp_rate_limiter):
    """Test user rate limiting (5 commands per hour)."""
    user = "testuser"
    repo = "owner/repo"
    pr_number = 123

    # Should allow 5 commands
    for i in range(5):
        await temp_rate_limiter.check_and_record(
            user=user, repo=repo, pr_number=pr_number, command=f"command{i}"
        )

    # 6th command should raise exception
    with pytest.raises(RateLimitExceeded) as exc_info:
        await temp_rate_limiter.check_and_record(
            user=user, repo=repo, pr_number=pr_number, command="command6"
        )

    assert exc_info.value.limit_type == "User"
    assert exc_info.value.limit == 5
    assert exc_info.value.window == "hour"


@pytest.mark.asyncio
async def test_pr_rate_limit(temp_rate_limiter):
    """Test PR rate limiting (10 commands total)."""
    repo = "owner/repo"
    pr_number = 456

    # Should allow 10 commands from different users
    for i in range(10):
        await temp_rate_limiter.check_and_record(
            user=f"user{i}", repo=repo, pr_number=pr_number, command=f"command{i}"
        )

    # 11th command should raise exception
    with pytest.raises(RateLimitExceeded) as exc_info:
        await temp_rate_limiter.check_and_record(
            user="user11", repo=repo, pr_number=pr_number, command="command11"
        )

    assert exc_info.value.limit_type == "PR"
    assert exc_info.value.limit == 10
    assert exc_info.value.window == "total"


@pytest.mark.asyncio
async def test_repo_rate_limit(temp_rate_limiter):
    """Test repository rate limiting (50 commands per day)."""
    repo = "owner/repo"

    # Should allow 50 commands across different PRs
    for i in range(50):
        await temp_rate_limiter.check_and_record(
            user=f"user{i % 10}",  # 10 different users
            repo=repo,
            pr_number=i % 5,  # 5 different PRs
            command=f"command{i}",
        )

    # 51st command should raise exception
    with pytest.raises(RateLimitExceeded) as exc_info:
        await temp_rate_limiter.check_and_record(
            user="user51", repo=repo, pr_number=999, command="command51"
        )

    assert exc_info.value.limit_type == "Repository"
    assert exc_info.value.limit == 50
    assert exc_info.value.window == "day"


@pytest.mark.asyncio
async def test_different_users_independent_limits(temp_rate_limiter):
    """Test that different users have independent rate limits."""
    repo = "owner/repo"
    pr_number = 789

    # User 1: use 5 commands (at limit)
    for i in range(5):
        await temp_rate_limiter.check_and_record(
            user="user1", repo=repo, pr_number=pr_number, command=f"command{i}"
        )

    # User 1: should be rate limited
    with pytest.raises(RateLimitExceeded):
        await temp_rate_limiter.check_and_record(
            user="user1", repo=repo, pr_number=pr_number, command="command_fail"
        )

    # User 2: should still have full quota (independent limit)
    await temp_rate_limiter.check_and_record(
        user="user2", repo=repo, pr_number=pr_number, command="command_success"
    )


@pytest.mark.asyncio
async def test_get_limits_status(temp_rate_limiter):
    """Test getting current rate limit status."""
    user = "testuser"
    repo = "owner/repo"
    pr_number = 111

    # Record 3 commands
    for i in range(3):
        await temp_rate_limiter.check_and_record(
            user=user, repo=repo, pr_number=pr_number, command=f"command{i}"
        )

    # Get status
    status = await temp_rate_limiter.get_limits_status(user, repo, pr_number)

    # Verify user status
    assert status["user"]["count"] == 3
    assert status["user"]["limit"] == 5
    assert status["user"]["remaining"] == 2
    assert status["user"]["window"] == "hour"

    # Verify PR status
    assert status["pr"]["count"] == 3
    assert status["pr"]["limit"] == 10
    assert status["pr"]["remaining"] == 7
    assert status["pr"]["window"] == "total"

    # Verify repo status
    assert status["repo"]["count"] == 3
    assert status["repo"]["limit"] == 50
    assert status["repo"]["remaining"] == 47
    assert status["repo"]["window"] == "day"


@pytest.mark.asyncio
async def test_cleanup_old_entries(temp_rate_limiter):
    """Test automatic cleanup of old entries."""
    user = "olduser"
    repo = "owner/repo"
    pr_number = 222

    # Record a command
    await temp_rate_limiter.check_and_record(
        user=user, repo=repo, pr_number=pr_number, command="old_command"
    )

    # Load data and manually set old timestamp
    data = temp_rate_limiter._load_data()
    old_timestamp = (datetime.utcnow() - timedelta(hours=2)).isoformat()

    # Set old timestamp for user
    data["limits"]["per_user"][user]["commands"][0]["timestamp"] = old_timestamp

    # Set last_cleanup to trigger cleanup
    data["last_cleanup"] = (datetime.utcnow() - timedelta(hours=2)).isoformat()

    temp_rate_limiter._save_data(data)

    # Trigger cleanup by recording a new command
    await temp_rate_limiter.check_and_record(
        user="newuser", repo="owner/other", pr_number=333, command="new_command"
    )

    # Verify old user was cleaned up
    data = temp_rate_limiter._load_data()
    assert user not in data["limits"]["per_user"]


@pytest.mark.asyncio
async def test_repo_limit_resets_daily(temp_rate_limiter):
    """Test that repo limits reset on new day."""
    repo = "owner/repo"

    # Record a command today
    await temp_rate_limiter.check_and_record(
        user="user1", repo=repo, pr_number=444, command="today_command"
    )

    # Check count is 1
    data = temp_rate_limiter._load_data()
    assert data["limits"]["per_repo"][repo]["count_today"] == 1

    # Manually set date to yesterday
    yesterday = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    data["limits"]["per_repo"][repo]["date"] = yesterday
    temp_rate_limiter._save_data(data)

    # Record another command (should reset count)
    await temp_rate_limiter.check_and_record(
        user="user2", repo=repo, pr_number=445, command="new_day_command"
    )

    # Verify count reset to 1 (not 2)
    data = temp_rate_limiter._load_data()
    assert data["limits"]["per_repo"][repo]["count_today"] == 1
    assert data["limits"]["per_repo"][repo]["date"] == datetime.utcnow().date().isoformat()


@pytest.mark.asyncio
async def test_file_persistence(temp_rate_limiter):
    """Test that rate limit data persists to file."""
    user = "persistuser"
    repo = "owner/repo"
    pr_number = 555

    # Record a command
    await temp_rate_limiter.check_and_record(
        user=user, repo=repo, pr_number=pr_number, command="persist_command"
    )

    # Read file directly
    with open(temp_rate_limiter.data_file, "r") as f:
        data = json.load(f)

    # Verify data in file
    assert user in data["limits"]["per_user"]
    assert len(data["limits"]["per_user"][user]["commands"]) == 1
    assert data["limits"]["per_user"][user]["commands"][0]["command"] == "persist_command"


@pytest.mark.asyncio
async def test_concurrent_commands_same_user(temp_rate_limiter):
    """Test handling of concurrent commands from same user."""
    import asyncio

    user = "concurrentuser"
    repo = "owner/repo"
    pr_number = 666

    # Record 5 commands concurrently
    tasks = [
        temp_rate_limiter.check_and_record(
            user=user, repo=repo, pr_number=pr_number, command=f"command{i}"
        )
        for i in range(5)
    ]

    await asyncio.gather(*tasks)

    # 6th should fail
    with pytest.raises(RateLimitExceeded):
        await temp_rate_limiter.check_and_record(
            user=user, repo=repo, pr_number=pr_number, command="command6"
        )


@pytest.mark.asyncio
async def test_command_recording_accuracy(temp_rate_limiter):
    """Test that commands are recorded accurately."""
    user = "accuracyuser"
    repo = "owner/accurate-repo"
    pr_number = 777

    # Record multiple commands
    commands = ["fix-security", "review", "explain"]
    for cmd in commands:
        await temp_rate_limiter.check_and_record(
            user=user, repo=repo, pr_number=pr_number, command=cmd
        )

    # Load data and verify
    data = temp_rate_limiter._load_data()

    # Check user commands
    user_commands = data["limits"]["per_user"][user]["commands"]
    assert len(user_commands) == 3
    recorded_cmds = [c["command"] for c in user_commands]
    assert recorded_cmds == commands

    # Check PR commands
    pr_key = f"{repo}#{pr_number}"
    pr_commands = data["limits"]["per_pr"][pr_key]["commands"]
    assert len(pr_commands) == 3
    assert data["limits"]["per_pr"][pr_key]["total_count"] == 3

    # Check repo commands
    repo_commands = data["limits"]["per_repo"][repo]["commands"]
    assert len(repo_commands) == 3
    assert data["limits"]["per_repo"][repo]["count_today"] == 3
