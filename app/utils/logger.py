"""Structured logging configuration and utilities.

This module provides structured logging capabilities with context
information, performance tracking, and standardized log formatting.
"""

import json
import logging
import sys
import time
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

from app.config import get_settings

# Context variable for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging.

    This formatter outputs logs as JSON objects with consistent fields
    for easier parsing and analysis in log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields from extra
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StandardFormatter(logging.Formatter):
    """Standard human-readable formatter for console output."""

    def __init__(self) -> None:
        """Initialize with a standard format."""
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logger(
    name: str,
    *,
    structured: bool = False,
    level: Optional[str] = None,
) -> logging.Logger:
    """Set up and configure a logger instance.

    Args:
        name: Name of the logger (typically __name__)
        structured: If True, use structured JSON logging
        level: Optional log level override (defaults to config setting)

    Returns:
        Configured logger instance

    Example:
        ```python
        from app.utils.logger import setup_logger

        logger = setup_logger(__name__)
        logger.info("Application started")

        # With structured logging
        logger_json = setup_logger(__name__, structured=True)
        logger_json.info("Processing request", extra={"extra_fields": {"user_id": 123}})
        ```
    """
    settings = get_settings()
    logger = logging.getLogger(name)

    # Set log level
    log_level = level or settings.server.log_level
    logger.setLevel(getattr(logging, log_level.upper()))

    # Avoid duplicate handlers
    if not logger.handlers:
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, log_level.upper()))

        # Choose formatter based on structured flag
        if structured:
            formatter = StructuredFormatter()
        else:
            formatter = StandardFormatter()

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

    return logger


def log_function_call(
    logger: logging.Logger,
    level: int = logging.DEBUG,
) -> Callable:
    """Decorator to log function calls with arguments and execution time.

    Args:
        logger: Logger instance to use
        level: Logging level (default: DEBUG)

    Returns:
        Decorator function

    Example:
        ```python
        from app.utils.logger import setup_logger, log_function_call

        logger = setup_logger(__name__)

        @log_function_call(logger)
        def process_data(data: dict) -> dict:
            return data

        result = process_data({"key": "value"})
        ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__qualname__
            start_time = time.time()

            # Log function entry
            logger.log(
                level,
                f"Calling {func_name}",
                extra={
                    "extra_fields": {
                        "function": func_name,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    }
                },
            )

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Log successful completion
                duration = time.time() - start_time
                logger.log(
                    level,
                    f"Completed {func_name}",
                    extra={
                        "extra_fields": {
                            "function": func_name,
                            "duration_seconds": round(duration, 3),
                            "status": "success",
                        }
                    },
                )

                return result

            except Exception as e:
                # Log error
                duration = time.time() - start_time
                logger.error(
                    f"Error in {func_name}: {str(e)}",
                    exc_info=True,
                    extra={
                        "extra_fields": {
                            "function": func_name,
                            "duration_seconds": round(duration, 3),
                            "status": "error",
                            "error_type": type(e).__name__,
                        }
                    },
                )
                raise

        return wrapper

    return decorator


def log_performance(
    logger: logging.Logger,
    operation: str,
    threshold_seconds: float = 1.0,
) -> Callable:
    """Decorator to log slow operations that exceed a time threshold.

    Args:
        logger: Logger instance to use
        operation: Name of the operation being monitored
        threshold_seconds: Time threshold in seconds (default: 1.0)

    Returns:
        Decorator function

    Example:
        ```python
        from app.utils.logger import setup_logger, log_performance

        logger = setup_logger(__name__)

        @log_performance(logger, "database_query", threshold_seconds=0.5)
        def fetch_data():
            # ... database operation ...
            pass
        ```
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            if duration >= threshold_seconds:
                logger.warning(
                    f"Slow operation detected: {operation}",
                    extra={
                        "extra_fields": {
                            "operation": operation,
                            "duration_seconds": round(duration, 3),
                            "threshold_seconds": threshold_seconds,
                            "function": func.__qualname__,
                        }
                    },
                )

            return result

        return wrapper

    return decorator


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context.

    Args:
        request_id: Unique identifier for the request

    Example:
        ```python
        from app.utils.logger import set_request_id

        set_request_id("req-12345")
        # All subsequent log messages will include this request_id
        ```
    """
    request_id_var.set(request_id)


def clear_request_id() -> None:
    """Clear the request ID from the current context."""
    request_id_var.set(None)


def get_request_id() -> Optional[str]:
    """Get the current request ID.

    Returns:
        Current request ID or None if not set
    """
    return request_id_var.get()


class LogContext:
    """Context manager for temporarily setting log context variables.

    Example:
        ```python
        from app.utils.logger import LogContext, setup_logger

        logger = setup_logger(__name__)

        with LogContext(request_id="req-123"):
            logger.info("Processing request")
            # Logs will include request_id
        ```
    """

    def __init__(self, request_id: Optional[str] = None):
        """Initialize log context.

        Args:
            request_id: Request ID to set for this context
        """
        self.request_id = request_id
        self.previous_request_id: Optional[str] = None

    def __enter__(self) -> "LogContext":
        """Enter the context."""
        self.previous_request_id = get_request_id()
        if self.request_id:
            set_request_id(self.request_id)
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit the context and restore previous state."""
        if self.previous_request_id:
            set_request_id(self.previous_request_id)
        else:
            clear_request_id()


# Create default application logger
app_logger = setup_logger("repoauditor_ai")
