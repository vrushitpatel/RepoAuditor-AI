"""Utility for fetching code from GitHub repositories."""

import re
from typing import Optional, Tuple

from app.integrations.github_client import GitHubClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CodeFetcher:
    """Fetch code from GitHub repositories."""

    def __init__(self, github_client: GitHubClient):
        """
        Initialize code fetcher.

        Args:
            github_client: GitHub client for API calls
        """
        self.github_client = github_client

    async def fetch_file_content(
        self,
        repo_name: str,
        file_path: str,
        installation_id: int,
        ref: Optional[str] = None,
    ) -> Optional[str]:
        """
        Fetch content of a specific file from GitHub.

        Args:
            repo_name: Repository name (owner/repo)
            file_path: Path to the file
            installation_id: GitHub App installation ID
            ref: Branch/commit ref (optional, defaults to default branch)

        Returns:
            File content as string, or None if not found
        """
        try:
            logger.debug(
                f"Fetching file content: {repo_name}/{file_path}",
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "file_path": file_path,
                        "ref": ref,
                    }
                },
            )

            # If no ref specified, use default branch (will be handled by GitHub API)
            if ref is None:
                ref = "HEAD"

            # Try to fetch file
            try:
                content = self.github_client.get_file_content(
                    installation_id=installation_id,
                    repo_full_name=repo_name,
                    file_path=file_path,
                    ref=ref,
                )

                if content:
                    logger.info(
                        f"Fetched {len(content)} bytes from {file_path}",
                        extra={
                            "extra_fields": {
                                "repo": repo_name,
                                "file_path": file_path,
                                "size": len(content),
                                "ref": ref,
                            }
                        },
                    )
                    return content

            except Exception as e:
                # If file not found at specific ref, try default branch
                if "404" in str(e) and ref != "HEAD":
                    logger.warning(
                        f"File not found at ref {ref}, trying default branch",
                        extra={
                            "extra_fields": {
                                "repo": repo_name,
                                "file_path": file_path,
                                "original_ref": ref,
                            }
                        },
                    )

                    # Try default branch
                    content = self.github_client.get_file_content(
                        installation_id=installation_id,
                        repo_full_name=repo_name,
                        file_path=file_path,
                        ref="HEAD",
                    )

                    if content:
                        logger.info(
                            f"Fetched {len(content)} bytes from {file_path} (from default branch)",
                            extra={
                                "extra_fields": {
                                    "repo": repo_name,
                                    "file_path": file_path,
                                    "size": len(content),
                                }
                            },
                        )
                        return content
                else:
                    raise

            logger.warning(f"File not found: {file_path}")
            return None

        except Exception as e:
            logger.error(
                f"Failed to fetch file {file_path}: {e}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "file_path": file_path,
                        "ref": ref,
                        "error": str(e),
                    }
                },
            )
            return None

    def extract_function_or_class(
        self,
        file_content: str,
        target_name: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract a specific function or class from file content.

        Args:
            file_content: Full content of the file
            target_name: Name of function or class to extract

        Returns:
            Tuple of (extracted_code, surrounding_context)
            Returns (None, None) if not found
        """
        try:
            lines = file_content.split("\n")

            # Try to find class definition first
            class_pattern = rf"^class\s+{re.escape(target_name)}\s*[\(:]"
            func_pattern = rf"^def\s+{re.escape(target_name)}\s*\("

            start_idx = None
            is_class = False

            for idx, line in enumerate(lines):
                if re.search(class_pattern, line.strip()):
                    start_idx = idx
                    is_class = True
                    break
                elif re.search(func_pattern, line.strip()):
                    start_idx = idx
                    is_class = False
                    break

            if start_idx is None:
                logger.warning(f"Could not find {target_name} in file")
                return None, None

            # Find the end of the function/class by tracking indentation
            base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
            end_idx = start_idx + 1

            # Find next line with same or less indentation (or empty line followed by such)
            while end_idx < len(lines):
                line = lines[end_idx]
                stripped = line.strip()

                # Skip empty lines and comments
                if not stripped or stripped.startswith("#"):
                    end_idx += 1
                    continue

                # Check indentation
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= base_indent:
                    # Found end of function/class
                    break

                end_idx += 1

            # Extract the code
            extracted_code = "\n".join(lines[start_idx:end_idx])

            # Get surrounding context (10 lines before and after)
            context_start = max(0, start_idx - 10)
            context_end = min(len(lines), end_idx + 10)
            surrounding_context = "\n".join(lines[context_start:context_start + 10])

            logger.info(
                f"Extracted {target_name} ({end_idx - start_idx} lines)",
                extra={
                    "extra_fields": {
                        "target": target_name,
                        "is_class": is_class,
                        "lines": end_idx - start_idx,
                    }
                },
            )

            return extracted_code, surrounding_context

        except Exception as e:
            logger.error(
                f"Failed to extract {target_name}: {e}",
                exc_info=True,
                extra={"extra_fields": {"target": target_name, "error": str(e)}},
            )
            return None, None

    def parse_file_reference(self, reference: str) -> Tuple[str, Optional[str]]:
        """
        Parse file reference that might include class/function specifier.

        Handles formats like:
        - "app/main.py" -> ("app/main.py", None)
        - "./app/main.py" -> ("app/main.py", None)
        - "app/main.py:MyClass" -> ("app/main.py", "MyClass")
        - "app/main.py:my_function" -> ("app/main.py", "my_function")

        Args:
            reference: File reference string

        Returns:
            Tuple of (file_path, target_name)
        """
        if ":" in reference:
            parts = reference.split(":", 1)
            file_path = parts[0].strip()
            target_name = parts[1].strip()
        else:
            file_path = reference.strip()
            target_name = None

        # Normalize file path - remove leading ./
        file_path = file_path.lstrip("./")

        # Also handle Windows-style paths
        file_path = file_path.lstrip(".\\")

        return file_path, target_name

    async def fetch_pr_file_content(
        self,
        repo_name: str,
        file_path: str,
        pr_number: int,
        installation_id: int,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetch both base and head versions of a file from a PR.

        Args:
            repo_name: Repository name (owner/repo)
            file_path: Path to the file
            pr_number: Pull request number
            installation_id: GitHub App installation ID

        Returns:
            Tuple of (base_content, head_content)
            Either can be None if file doesn't exist in that version
        """
        try:
            # Get PR details to find base and head refs
            pr_details = self.github_client.get_pr_details(
                repo_name=repo_name,
                pr_number=pr_number,
                installation_id=installation_id,
            )

            base_ref = pr_details.get("base_sha")
            head_ref = pr_details.get("head_sha")

            if not base_ref or not head_ref:
                logger.error("Could not get base/head refs from PR")
                return None, None

            # Fetch both versions
            logger.debug(f"Fetching base version from {base_ref}")
            base_content = await self.fetch_file_content(
                repo_name=repo_name,
                file_path=file_path,
                installation_id=installation_id,
                ref=base_ref,
            )

            logger.debug(f"Fetching head version from {head_ref}")
            head_content = await self.fetch_file_content(
                repo_name=repo_name,
                file_path=file_path,
                installation_id=installation_id,
                ref=head_ref,
            )

            return base_content, head_content

        except Exception as e:
            logger.error(
                f"Failed to fetch PR file versions: {e}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "repo": repo_name,
                        "pr_number": pr_number,
                        "file_path": file_path,
                        "error": str(e),
                    }
                },
            )
            return None, None

    def extract_changed_files_from_diff(self, diff_content: str) -> list[str]:
        """
        Extract list of changed file paths from diff content.

        Args:
            diff_content: Git diff content

        Returns:
            List of file paths that were changed
        """
        file_paths = []
        lines = diff_content.split("\n")

        for line in lines:
            # Look for diff headers like: diff --git a/path/to/file.py b/path/to/file.py
            if line.startswith("diff --git"):
                # Extract file path (after b/)
                parts = line.split(" b/")
                if len(parts) > 1:
                    file_path = parts[1].strip()
                    file_paths.append(file_path)

            # Also look for +++ headers
            elif line.startswith("+++") and not line.startswith("+++ /dev/null"):
                # Format: +++ b/path/to/file.py
                file_path = line.replace("+++ b/", "").strip()
                if file_path and file_path not in file_paths:
                    file_paths.append(file_path)

        logger.info(
            f"Extracted {len(file_paths)} changed files from diff",
            extra={"extra_fields": {"file_count": len(file_paths)}},
        )

        return file_paths

    def truncate_content(
        self,
        content: str,
        max_lines: int = 500,
        max_chars: int = 50000,
    ) -> str:
        """
        Truncate content if it's too large.

        Args:
            content: Content to truncate
            max_lines: Maximum number of lines
            max_chars: Maximum number of characters

        Returns:
            Truncated content with notice if truncated
        """
        # Check character limit first
        if len(content) > max_chars:
            content = content[:max_chars]
            content += "\n\n... [Content truncated - file too large] ..."
            logger.warning(f"Content truncated (exceeded {max_chars} chars)")

        # Check line limit
        lines = content.split("\n")
        if len(lines) > max_lines:
            content = "\n".join(lines[:max_lines])
            content += f"\n\n... [Content truncated - showing first {max_lines} lines] ..."
            logger.warning(f"Content truncated (exceeded {max_lines} lines)")

        return content
