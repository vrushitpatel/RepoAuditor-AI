"""Logging configuration and utilities."""

import logging
import sys
from typing import Any

from app.config import settings


def setup_logger(name: str) -> logging.Logger:
    """
    Set up and configure a logger instance.

    Args:
        name: Name of the logger (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Avoid duplicate handlers
    if not logger.handlers:
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, settings.log_level.upper()))

        # Formatter
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


def log_function_call(logger: logging.Logger, func_name: str, **kwargs: Any) -> None:
    """
    Log a function call with arguments.

    Args:
        logger: Logger instance
        func_name: Name of the function being called
        **kwargs: Function arguments to log
    """
    args_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.debug(f"Calling {func_name}({args_str})")
