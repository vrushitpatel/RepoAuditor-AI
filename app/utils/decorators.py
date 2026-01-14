"""Decorators for workflow and command handling.

This module provides decorators for common cross-cutting concerns
like rate limiting, error handling, and logging.
"""

from functools import wraps
from typing import TypeVar, Callable, Any

from app.utils.rate_limiter import get_rate_limiter, RateLimitExceeded
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Type variable for state
StateT = TypeVar("StateT")


def rate_limited(func: Callable[[StateT], StateT]) -> Callable[[StateT], StateT]:
    """
    Decorator to apply rate limiting to workflow nodes or command handlers.

    This decorator extracts rate limiting parameters from the workflow state
    and checks limits before allowing execution. If rate limit is exceeded,
    it updates the state with an appropriate error message.

    The decorated function should accept a state dictionary/TypedDict with:
    - repo_name: Repository name (owner/repo)
    - pr_number: Pull request number
    - command (optional dict with 'commenter' and 'name' keys)

    Args:
        func: Function to decorate (should accept and return state)

    Returns:
        Decorated function with rate limiting

    Example:
        ```python
        @rate_limited
        async def initialize_workflow_node(state: SecurityFixState) -> SecurityFixState:
            # Workflow logic here
            return state
        ```

    Note:
        If rate limit is exceeded, the function is NOT executed and state
        is updated with error message. The workflow should handle this
        error state appropriately.
    """

    @wraps(func)
    async def wrapper(state: StateT, *args: Any, **kwargs: Any) -> StateT:
        # Extract rate limiting parameters from state
        # Support both direct state fields and nested command structure
        user = "unknown"
        command_name = "unknown"

        # Try to get user from command structure
        if "command" in state and isinstance(state["command"], dict):
            user = state["command"].get("commenter", "unknown")
            command_name = state["command"].get("name", "unknown")
        # Fallback to direct state fields
        elif "commenter" in state:
            user = state.get("commenter", "unknown")
            command_name = state.get("command_name", "unknown")

        repo = state.get("repo_name", "unknown")
        pr_number = state.get("pr_number", 0)

        # Check rate limits
        limiter = get_rate_limiter()

        try:
            await limiter.check_and_record(user, repo, pr_number, command_name)
        except RateLimitExceeded as e:
            logger.warning(
                f"Rate limit exceeded: {e}",
                extra={
                    "extra_fields": {
                        "user": user,
                        "repo": repo,
                        "pr_number": pr_number,
                        "command": command_name,
                        "limit_type": e.limit_type,
                        "limit": e.limit,
                        "window": e.window,
                    }
                },
            )

            # Get current status for detailed message
            status = await limiter.get_limits_status(user, repo, pr_number)

            # Build user-friendly error message
            error_message = f"""## ⏱️ Rate Limit Exceeded

You've hit the **{e.limit_type.lower()} rate limit** of **{e.limit} commands per {e.window}**.

### Current Usage
- **User ({user}):** {status['user']['count']}/{status['user']['limit']} commands this hour (remaining: {status['user']['remaining']})
- **PR (#{pr_number}):** {status['pr']['count']}/{status['pr']['limit']} commands total (remaining: {status['pr']['remaining']})
- **Repository ({repo}):** {status['repo']['count']}/{status['repo']['limit']} commands today (remaining: {status['repo']['remaining']})

### What You Can Do
- ⏳ **Wait before trying again** - User limits reset every hour
- 📧 **Contact repository administrators** if you need higher limits
- 💡 **Batch your requests** to stay within limits

### Why Rate Limits?
Rate limits ensure fair usage and system stability for all users.

---
*Rate limit exceeded at workflow initialization. Please try again later.*
"""

            # Update state with error
            state["error"] = str(e)

            # Add formatted message to agent_result if present
            if "agent_result" in state:
                state["agent_result"] = error_message

            # Don't execute the wrapped function
            return state

        # Rate limit check passed - execute original function
        return await func(state, *args, **kwargs)

    return wrapper


def log_execution(func: Callable) -> Callable:
    """
    Decorator to log function execution with timing.

    Args:
        func: Function to decorate

    Returns:
        Decorated function with execution logging

    Example:
        ```python
        @log_execution
        async def my_workflow_node(state: WorkflowState) -> WorkflowState:
            # Node logic
            return state
        ```
    """
    import time

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = func.__name__
        start_time = time.time()

        logger.info(
            f"Executing {func_name}",
            extra={"extra_fields": {"function": func_name, "started_at": start_time}},
        )

        try:
            result = await func(*args, **kwargs)

            duration = time.time() - start_time
            logger.info(
                f"Completed {func_name}",
                extra={
                    "extra_fields": {
                        "function": func_name,
                        "duration_seconds": round(duration, 3),
                        "success": True,
                    }
                },
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Failed {func_name}: {e}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "function": func_name,
                        "duration_seconds": round(duration, 3),
                        "success": False,
                        "error": str(e),
                    }
                },
            )
            raise

    return wrapper


def handle_errors(error_field: str = "error") -> Callable:
    """
    Decorator to handle errors and update state error field.

    Args:
        error_field: Name of the error field in state (default: "error")

    Returns:
        Decorator function

    Example:
        ```python
        @handle_errors(error_field="error")
        async def risky_node(state: WorkflowState) -> WorkflowState:
            # Node logic that might fail
            return state
        ```
    """

    def decorator(func: Callable[[StateT], StateT]) -> Callable[[StateT], StateT]:
        @wraps(func)
        async def wrapper(state: StateT, *args: Any, **kwargs: Any) -> StateT:
            try:
                return await func(state, *args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {e}",
                    exc_info=True,
                    extra={
                        "extra_fields": {
                            "function": func.__name__,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    },
                )

                # Update state with error
                state[error_field] = f"Error in {func.__name__}: {str(e)}"
                return state

        return wrapper

    return decorator
