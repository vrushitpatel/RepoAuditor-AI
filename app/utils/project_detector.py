"""Project type and framework detector for CI/CD generation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from app.integrations.github_client import GitHubClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ProjectInfo:
    """Information about detected project type and configuration."""

    project_type: str  # "python", "nodejs", "docker", "unknown"
    framework: Optional[str] = None  # "fastapi", "flask", "express", etc.
    language_version: Optional[str] = None  # "3.11", "18.x", etc.
    package_manager: Optional[str] = None  # "pip", "npm", "yarn", "poetry"
    test_framework: Optional[str] = None  # "pytest", "jest", "mocha"
    linter: Optional[str] = None  # "black", "eslint", "ruff"
    has_docker: bool = False
    has_tests: bool = False
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    scripts: Dict[str, str] = field(default_factory=dict)
    entry_point: Optional[str] = None


class ProjectDetector:
    """Detect project type, framework, and configuration from repository."""

    def __init__(self, github_client: GitHubClient):
        """
        Initialize project detector.

        Args:
            github_client: GitHub client for API calls
        """
        self.github = github_client

    async def detect_project(
        self,
        repo_name: str,
        installation_id: int,
        pr_number: Optional[int] = None,
    ) -> ProjectInfo:
        """
        Detect project type and configuration.

        Args:
            repo_name: Repository name (owner/repo)
            installation_id: GitHub App installation ID
            pr_number: Optional PR number for context

        Returns:
            ProjectInfo with detected configuration
        """
        logger.info(
            f"Detecting project type for {repo_name}",
            extra={"extra_fields": {"repo": repo_name, "pr_number": pr_number}},
        )

        # Get repository files
        files = self._list_repo_files(repo_name, installation_id)

        # Initialize project info
        info = ProjectInfo(project_type="unknown")

        # Detect Python project
        if self._is_python_project(files):
            info = await self._detect_python_project(
                repo_name, installation_id, files
            )

        # Detect Node.js project
        elif self._is_nodejs_project(files):
            info = await self._detect_nodejs_project(
                repo_name, installation_id, files
            )

        # Detect Docker project
        if "Dockerfile" in files or "docker-compose.yml" in files:
            info.has_docker = True

        # Detect tests
        info.has_tests = self._has_tests(files)

        logger.info(
            f"Detected {info.project_type} project with {info.framework or 'no'} framework",
            extra={
                "extra_fields": {
                    "repo": repo_name,
                    "project_type": info.project_type,
                    "framework": info.framework,
                    "has_docker": info.has_docker,
                    "has_tests": info.has_tests,
                }
            },
        )

        return info

    def _list_repo_files(
        self, repo_name: str, installation_id: int
    ) -> Set[str]:
        """
        Get list of files in repository root.

        Args:
            repo_name: Repository name
            installation_id: GitHub App installation ID

        Returns:
            Set of filenames in repo root
        """
        try:
            # Get repository root contents
            client = self.github._get_installation_client(installation_id)
            repo = client.get_repo(repo_name)
            contents = repo.get_contents("")

            files = set()
            if isinstance(contents, list):
                for item in contents:
                    files.add(item.name)
            else:
                files.add(contents.name)

            logger.debug(f"Found {len(files)} files in repo root")
            return files

        except Exception as e:
            logger.error(f"Failed to list repo files: {e}")
            return set()

    def _is_python_project(self, files: Set[str]) -> bool:
        """Check if project is Python."""
        python_indicators = {
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "Pipfile",
            "poetry.lock",
        }
        return bool(python_indicators & files)

    def _is_nodejs_project(self, files: Set[str]) -> bool:
        """Check if project is Node.js."""
        nodejs_indicators = {"package.json", "yarn.lock", "package-lock.json"}
        return bool(nodejs_indicators & files)

    def _has_tests(self, files: Set[str]) -> bool:
        """Check if project has tests directory."""
        test_indicators = {
            "tests",
            "test",
            "__tests__",
            "spec",
            "pytest.ini",
            "jest.config.js",
        }
        return bool(test_indicators & files)

    async def _detect_python_project(
        self, repo_name: str, installation_id: int, files: Set[str]
    ) -> ProjectInfo:
        """Detect Python project details."""
        info = ProjectInfo(project_type="python")

        # Detect package manager
        if "poetry.lock" in files:
            info.package_manager = "poetry"
        elif "Pipfile" in files:
            info.package_manager = "pipenv"
        else:
            info.package_manager = "pip"

        # Try to read requirements.txt or pyproject.toml
        dependencies = []
        try:
            if "requirements.txt" in files:
                content = self.github.get_file_content(
                    installation_id=installation_id,
                    repo_full_name=repo_name,
                    file_path="requirements.txt",
                    ref="HEAD",
                )
                dependencies = self._parse_requirements(content)

            elif "pyproject.toml" in files:
                content = self.github.get_file_content(
                    installation_id=installation_id,
                    repo_full_name=repo_name,
                    file_path="pyproject.toml",
                    ref="HEAD",
                )
                dependencies = self._parse_pyproject(content)

        except Exception as e:
            logger.warning(f"Failed to read dependencies: {e}")

        info.dependencies = dependencies

        # Detect framework
        dep_lower = [d.lower() for d in dependencies]
        if any("fastapi" in d for d in dep_lower):
            info.framework = "fastapi"
        elif any("flask" in d for d in dep_lower):
            info.framework = "flask"
        elif any("django" in d for d in dep_lower):
            info.framework = "django"

        # Detect test framework
        if any("pytest" in d for d in dep_lower):
            info.test_framework = "pytest"
        elif any("unittest" in d for d in dep_lower):
            info.test_framework = "unittest"

        # Detect linter
        if any("black" in d for d in dep_lower):
            info.linter = "black"
        elif any("ruff" in d for d in dep_lower):
            info.linter = "ruff"
        elif any("flake8" in d for d in dep_lower):
            info.linter = "flake8"

        # Default Python version
        info.language_version = "3.11"

        return info

    async def _detect_nodejs_project(
        self, repo_name: str, installation_id: int, files: Set[str]
    ) -> ProjectInfo:
        """Detect Node.js project details."""
        info = ProjectInfo(project_type="nodejs")

        # Detect package manager
        if "yarn.lock" in files:
            info.package_manager = "yarn"
        elif "pnpm-lock.yaml" in files:
            info.package_manager = "pnpm"
        else:
            info.package_manager = "npm"

        # Try to read package.json
        try:
            if "package.json" in files:
                content = self.github.get_file_content(
                    installation_id=installation_id,
                    repo_full_name=repo_name,
                    file_path="package.json",
                    ref="HEAD",
                )
                package_info = self._parse_package_json(content)

                info.dependencies = package_info.get("dependencies", [])
                info.dev_dependencies = package_info.get("devDependencies", [])
                info.scripts = package_info.get("scripts", {})

                # Detect framework
                deps = info.dependencies + info.dev_dependencies
                deps_lower = [d.lower() for d in deps]

                if any("express" in d for d in deps_lower):
                    info.framework = "express"
                elif any("next" in d for d in deps_lower):
                    info.framework = "nextjs"
                elif any("react" in d for d in deps_lower):
                    info.framework = "react"
                elif any("vue" in d for d in deps_lower):
                    info.framework = "vue"

                # Detect test framework
                if any("jest" in d for d in deps_lower):
                    info.test_framework = "jest"
                elif any("mocha" in d for d in deps_lower):
                    info.test_framework = "mocha"
                elif any("vitest" in d for d in deps_lower):
                    info.test_framework = "vitest"

                # Detect linter
                if any("eslint" in d for d in deps_lower):
                    info.linter = "eslint"
                elif any("prettier" in d for d in deps_lower):
                    info.linter = "prettier"

        except Exception as e:
            logger.warning(f"Failed to read package.json: {e}")

        # Default Node version
        info.language_version = "18.x"

        return info

    def _parse_requirements(self, content: str) -> List[str]:
        """Parse requirements.txt content."""
        deps = []
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove version specifiers
                dep = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                if dep:
                    deps.append(dep)
        return deps

    def _parse_pyproject(self, content: str) -> List[str]:
        """Parse pyproject.toml content (simplified)."""
        deps = []
        in_deps = False

        for line in content.split("\n"):
            line = line.strip()

            if "[tool.poetry.dependencies]" in line or "[project.dependencies]" in line:
                in_deps = True
                continue

            if in_deps:
                if line.startswith("["):
                    break
                if "=" in line:
                    dep = line.split("=")[0].strip().strip('"')
                    if dep and dep != "python":
                        deps.append(dep)

        return deps

    def _parse_package_json(self, content: str) -> Dict:
        """Parse package.json content."""
        import json

        try:
            data = json.loads(content)

            result = {
                "dependencies": list(data.get("dependencies", {}).keys()),
                "devDependencies": list(data.get("devDependencies", {}).keys()),
                "scripts": data.get("scripts", {}),
            }

            return result

        except Exception as e:
            logger.error(f"Failed to parse package.json: {e}")
            return {}
