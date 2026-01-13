"""Test logging to verify routing messages."""

from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Test different log messages
logger.info("Testing INFO level")
logger.info(
    "Processing command: test",
    extra={
        "extra_fields": {
            "command": "test",
            "pr_number": 123,
        }
    }
)
logger.debug("Testing DEBUG level")
logger.warning("Testing WARNING level")

print("\n✅ If you see messages above, logging is working!")
print("Your FastAPI logs should show similar messages when commands are processed.")
