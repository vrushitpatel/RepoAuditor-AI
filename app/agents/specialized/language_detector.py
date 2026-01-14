"""Language detector agent.

Detects the primary programming language in a repository.
"""

from typing import Dict, Any, List
from collections import Counter
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class LanguageDetector:
    """Detects primary programming language from file extensions."""

    def __init__(self):
        """Initialize language detector."""
        self.extension_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "jsx": "javascript",
            "tsx": "typescript",
            "go": "go",
            "rs": "rust",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
            "rb": "ruby",
            "php": "php",
        }

        self.tool_map = {
            "python": {"formatter": "black", "linter": "ruff"},
            "javascript": {"formatter": "prettier", "linter": "eslint"},
            "typescript": {"formatter": "prettier", "linter": "eslint"},
            "go": {"formatter": "gofmt", "linter": "golangci-lint"},
            "rust": {"formatter": "rustfmt", "linter": "clippy"},
            "java": {"formatter": "google-java-format", "linter": "checkstyle"},
        }

    def detect(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect primary language from file list.

        Args:
            files: List of file dictionaries with 'filename' key

        Returns:
            Dictionary with language, confidence, formatter, linter
        """
        logger.info(f"Detecting language from {len(files)} files")

        # Count extensions
        extensions = []
        for file in files:
            filename = file.get("filename", "")
            if "." in filename:
                ext = filename.split(".")[-1].lower()
                extensions.append(ext)

        if not extensions:
            return self._default_result()

        # Find most common extension
        counter = Counter(extensions)
        most_common_ext, count = counter.most_common(1)[0]

        # Map to language
        language = self.extension_map.get(most_common_ext, "unknown")

        # Calculate confidence
        total_files = len(extensions)
        confidence = count / total_files if total_files > 0 else 0.0

        # Get tools
        tools = self.tool_map.get(language, {"formatter": "", "linter": ""})

        result = {
            "language": language,
            "confidence": confidence,
            "formatter": tools["formatter"],
            "linter": tools["linter"],
            "file_count": count,
            "total_files": total_files,
        }

        logger.info(
            f"Detected {language} with {confidence:.2%} confidence"
        )

        return result

    def _default_result(self) -> Dict[str, Any]:
        """Return default result when no files found."""
        return {
            "language": "unknown",
            "confidence": 0.0,
            "formatter": "",
            "linter": "",
            "file_count": 0,
            "total_files": 0,
        }
