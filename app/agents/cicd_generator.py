"""CI/CD Generator Agent - Generate GitHub Actions workflows with AI customization."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.integrations.gemini_client import GeminiClient
from app.integrations.github_client import GitHubClient
from app.utils.logger import setup_logger
from app.utils.project_detector import ProjectDetector, ProjectInfo

logger = setup_logger(__name__)


class CICDGenerator:
    """Generate customized CI/CD workflows for projects."""

    # Template directory
    TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "cicd_templates"

    def __init__(
        self,
        gemini_client: GeminiClient,
        github_client: GitHubClient,
    ):
        """
        Initialize CI/CD Generator.

        Args:
            gemini_client: Gemini AI client for customization
            github_client: GitHub client for repo access
        """
        self.gemini = gemini_client
        self.github = github_client
        self.detector = ProjectDetector(github_client)

        logger.info("CI/CD Generator initialized")

    async def generate_workflows(
        self,
        repo_name: str,
        installation_id: int,
        workflow_types: List[str],
        pr_number: Optional[int] = None,
    ) -> Dict[str, str]:
        """
        Generate CI/CD workflow files.

        Args:
            repo_name: Repository name (owner/repo)
            installation_id: GitHub App installation ID
            workflow_types: List of workflow types to generate
                           ["test", "lint", "build", "deploy", "all"]
            pr_number: Optional PR number for context

        Returns:
            Dict of {filename: yaml_content}

        Raises:
            Exception: If generation fails
        """
        logger.info(
            f"Generating CI/CD workflows for {repo_name}",
            extra={
                "extra_fields": {
                    "repo": repo_name,
                    "workflow_types": workflow_types,
                    "pr_number": pr_number,
                }
            },
        )

        # Detect project type and configuration
        project_info = await self.detector.detect_project(
            repo_name=repo_name,
            installation_id=installation_id,
            pr_number=pr_number,
        )

        # Expand "all" to specific types
        if "all" in workflow_types:
            workflow_types = self._get_all_workflow_types(project_info)

        # Generate each workflow
        workflows = {}
        for workflow_type in workflow_types:
            try:
                filename, content = await self._generate_workflow(
                    workflow_type=workflow_type,
                    project_info=project_info,
                    repo_name=repo_name,
                )
                workflows[filename] = content
                logger.info(f"Generated {filename}")

            except Exception as e:
                logger.error(
                    f"Failed to generate {workflow_type} workflow: {e}",
                    exc_info=True,
                )
                # Continue with other workflows
                workflows[f"{workflow_type}.yml"] = f"# Error generating: {e}"

        logger.info(
            f"Generated {len(workflows)} workflows",
            extra={"extra_fields": {"count": len(workflows)}},
        )

        return workflows

    def _get_all_workflow_types(self, project_info: ProjectInfo) -> List[str]:
        """
        Get all applicable workflow types for project.

        Args:
            project_info: Detected project information

        Returns:
            List of workflow types to generate
        """
        types = ["test"]

        # Add lint if linter detected
        if project_info.linter:
            types.append("lint")

        # Add build if Docker detected
        if project_info.has_docker:
            types.append("build")

        return types

    async def _generate_workflow(
        self,
        workflow_type: str,
        project_info: ProjectInfo,
        repo_name: str,
    ) -> tuple[str, str]:
        """
        Generate a single workflow file.

        Args:
            workflow_type: Type of workflow (test, lint, build, deploy)
            project_info: Project information
            repo_name: Repository name

        Returns:
            Tuple of (filename, yaml_content)
        """
        # Select template
        template_file = self._select_template(workflow_type, project_info)

        # Load template
        template_content = self._load_template(template_file)

        # Customize template
        customized_content = self._customize_template(
            template_content=template_content,
            workflow_type=workflow_type,
            project_info=project_info,
            repo_name=repo_name,
        )

        # Generate filename
        filename = f"{workflow_type}.yml"

        return filename, customized_content

    def _select_template(
        self, workflow_type: str, project_info: ProjectInfo
    ) -> str:
        """
        Select appropriate template file.

        Args:
            workflow_type: Type of workflow
            project_info: Project information

        Returns:
            Template filename
        """
        if workflow_type == "test":
            if project_info.project_type == "python":
                return "python_test.yml"
            elif project_info.project_type == "nodejs":
                return "nodejs_test.yml"

        elif workflow_type == "lint":
            if project_info.project_type == "python":
                return "python_lint.yml"
            elif project_info.project_type == "nodejs":
                return "nodejs_lint.yml"

        elif workflow_type == "build":
            return "docker_build.yml"

        elif workflow_type == "deploy":
            return "deploy_railway.yml"

        # Default
        return f"{workflow_type}.yml"

    def _load_template(self, template_file: str) -> str:
        """
        Load template content from file.

        Args:
            template_file: Template filename

        Returns:
            Template content

        Raises:
            FileNotFoundError: If template not found
        """
        template_path = self.TEMPLATE_DIR / template_file

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_file}")

        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    def _customize_template(
        self,
        template_content: str,
        workflow_type: str,
        project_info: ProjectInfo,
        repo_name: str,
    ) -> str:
        """
        Customize template with project-specific values.

        Args:
            template_content: Template YAML content
            workflow_type: Type of workflow
            project_info: Project information
            repo_name: Repository name

        Returns:
            Customized YAML content
        """
        content = template_content

        # Python-specific customization
        if project_info.project_type == "python":
            content = self._customize_python(content, project_info)

        # Node.js-specific customization
        elif project_info.project_type == "nodejs":
            content = self._customize_nodejs(content, project_info)

        # Docker-specific customization
        if workflow_type == "build":
            content = self._customize_docker(content, repo_name)

        # Deployment-specific customization
        if workflow_type == "deploy":
            content = self._customize_deploy(content, project_info, repo_name)

        return content

    def _customize_python(
        self, content: str, project_info: ProjectInfo
    ) -> str:
        """Customize Python workflow."""
        # Python version
        content = content.replace(
            "{{PYTHON_VERSION}}",
            project_info.language_version or "3.11",
        )

        # Requirements file
        if project_info.package_manager == "poetry":
            content = content.replace(
                "{{REQUIREMENTS_FILE}}", "pyproject.toml"
            )
            content = content.replace(
                "{{INSTALL_COMMAND}}",
                "pip install poetry && poetry install",
            )
        elif project_info.package_manager == "pipenv":
            content = content.replace("{{REQUIREMENTS_FILE}}", "Pipfile")
            content = content.replace(
                "{{INSTALL_COMMAND}}", "pip install pipenv && pipenv install"
            )
        else:
            content = content.replace(
                "{{REQUIREMENTS_FILE}}", "requirements.txt"
            )
            content = content.replace(
                "{{INSTALL_COMMAND}}", "pip install -r requirements.txt"
            )

        # Test command
        if project_info.test_framework == "pytest":
            test_cmd = "pytest tests/ -v"
            if "pytest-cov" in project_info.dependencies:
                test_cmd += " --cov --cov-report=xml"
                coverage_step = """
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml"""
            else:
                coverage_step = ""
        else:
            test_cmd = "python -m unittest discover tests"
            coverage_step = ""

        content = content.replace("{{TEST_COMMAND}}", test_cmd)
        content = content.replace("{{COVERAGE_STEP}}", coverage_step)

        # Linter
        if project_info.linter == "black":
            content = content.replace("{{LINTER}}", "Black")
            content = content.replace(
                "{{LINTER_INSTALL}}", "pip install black ruff"
            )
            content = content.replace(
                "{{LINTER_COMMAND}}", "black . --check && ruff check ."
            )
        elif project_info.linter == "ruff":
            content = content.replace("{{LINTER}}", "Ruff")
            content = content.replace("{{LINTER_INSTALL}}", "pip install ruff")
            content = content.replace("{{LINTER_COMMAND}}", "ruff check .")
        else:
            content = content.replace("{{LINTER}}", "Flake8")
            content = content.replace(
                "{{LINTER_INSTALL}}", "pip install flake8"
            )
            content = content.replace("{{LINTER_COMMAND}}", "flake8 .")

        # Type checking
        if "mypy" in project_info.dependencies:
            type_check = """
    - name: Type checking with mypy
      run: mypy ."""
        else:
            type_check = ""

        content = content.replace("{{TYPE_CHECK_STEP}}", type_check)

        return content

    def _customize_nodejs(
        self, content: str, project_info: ProjectInfo
    ) -> str:
        """Customize Node.js workflow."""
        # Node version
        content = content.replace(
            "{{NODE_VERSION}}",
            project_info.language_version or "18.x",
        )

        # Install command
        if project_info.package_manager == "yarn":
            install_cmd = "yarn install --frozen-lockfile"
        elif project_info.package_manager == "pnpm":
            install_cmd = "pnpm install --frozen-lockfile"
        else:
            install_cmd = "npm ci"

        content = content.replace("{{INSTALL_COMMAND}}", install_cmd)

        # Test command
        if "test" in project_info.scripts:
            test_cmd = f"{project_info.package_manager} test"
        else:
            if project_info.test_framework == "jest":
                test_cmd = "npx jest"
            else:
                test_cmd = f"{project_info.package_manager} test"

        content = content.replace("{{TEST_COMMAND}}", test_cmd)

        # Coverage
        if project_info.test_framework == "jest":
            coverage_step = """
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage/coverage-final.json"""
        else:
            coverage_step = ""

        content = content.replace("{{COVERAGE_STEP}}", coverage_step)

        # Linter
        if project_info.linter == "eslint":
            content = content.replace("{{LINTER}}", "ESLint")
            content = content.replace(
                "{{LINTER_COMMAND}}",
                f"{project_info.package_manager} run lint",
            )
        else:
            content = content.replace("{{LINTER}}", "Prettier")
            content = content.replace(
                "{{LINTER_COMMAND}}",
                f"{project_info.package_manager} run format:check",
            )

        # Type checking
        if "typescript" in project_info.dev_dependencies:
            type_check = f"""
    - name: Type checking
      run: {project_info.package_manager} run type-check"""
        else:
            type_check = ""

        content = content.replace("{{TYPE_CHECK_STEP}}", type_check)

        return content

    def _customize_docker(self, content: str, repo_name: str) -> str:
        """Customize Docker workflow."""
        # Repository name for image tagging
        content = content.replace("{{REPO_NAME}}", repo_name)
        return content

    def _customize_deploy(
        self, content: str, project_info: ProjectInfo, repo_name: str
    ) -> str:
        """Customize deployment workflow."""
        # Service name (use repo name without owner)
        service_name = repo_name.split("/")[-1]
        content = content.replace("{{SERVICE_NAME}}", service_name)

        return content

    def format_workflows_for_comment(
        self, workflows: Dict[str, str], project_info: ProjectInfo
    ) -> str:
        """
        Format generated workflows for GitHub comment.

        Args:
            workflows: Dict of {filename: yaml_content}
            project_info: Project information

        Returns:
            Formatted markdown comment
        """
        comment = f"""## 🚀 CI/CD Workflows Generated!

I've analyzed your **{project_info.project_type}** project"""

        if project_info.framework:
            comment += f" using **{project_info.framework}**"

        comment += " and created the following workflows:\n\n"

        # Add summary
        for filename in sorted(workflows.keys()):
            workflow_type = filename.replace(".yml", "")
            emoji = self._get_workflow_emoji(workflow_type)
            description = self._get_workflow_description(
                workflow_type, project_info
            )

            comment += f"### {emoji} `{filename}`\n{description}\n\n"

        # Add instructions
        comment += """---

### 📋 How to Use These Workflows

**Option 1: Manual Setup**
1. Create directory: `.github/workflows/`
2. Copy each workflow file below to that directory
3. Commit and push to your repository
4. Workflows will run automatically!

**Option 2: Copy from Comment**
Expand each workflow below, copy the content, and save to `.github/workflows/[filename]`

---

### 📁 Workflow Files

"""

        # Add each workflow with code blocks
        for filename, content in sorted(workflows.items()):
            comment += f"""<details>
<summary><b>{filename}</b> (click to expand)</summary>

```yaml
{content}
```

</details>

"""

        # Add tips
        comment += """---

### 💡 Pro Tips

- **Secrets**: Add required secrets in Settings → Secrets → Actions
  - `RAILWAY_TOKEN` for deployments
  - `CODECOV_TOKEN` for code coverage

- **Customize**: Feel free to modify these workflows for your needs

- **Test First**: Create a test PR to see workflows in action

- **Need Help?**: Type `/help` to see other available commands

---

### 🎯 What Happens Next?

**On Every Pull Request:**
"""

        if "test.yml" in workflows:
            comment += f"\n- ✅ Tests run with {project_info.test_framework or 'your test framework'}"
        if "lint.yml" in workflows:
            comment += f"\n- ✅ Code quality checked with {project_info.linter or 'linter'}"
        if "build.yml" in workflows:
            comment += "\n- ✅ Docker image built (not pushed)"

        comment += "\n\n**On Merge to Main:**\n"

        if "test.yml" in workflows:
            comment += "\n- ✅ Final tests run"
        if "build.yml" in workflows:
            comment += "\n- ✅ Docker image built and pushed to registry"
        if "deploy.yml" in workflows:
            comment += "\n- ✅ Automatically deployed to production"

        comment += "\n\n*Generated by RepoAuditor AI's CI/CD Generator 🤖*"

        return comment

    def _get_workflow_emoji(self, workflow_type: str) -> str:
        """Get emoji for workflow type."""
        emojis = {
            "test": "🧪",
            "lint": "✨",
            "build": "🐳",
            "deploy": "🚀",
        }
        return emojis.get(workflow_type, "📝")

    def _get_workflow_description(
        self, workflow_type: str, project_info: ProjectInfo
    ) -> str:
        """Get description for workflow type."""
        if workflow_type == "test":
            test_fw = project_info.test_framework or "your test framework"
            return f"Runs tests with **{test_fw}** on every push and PR"

        elif workflow_type == "lint":
            linter = project_info.linter or "linter"
            return f"Checks code quality with **{linter}** and enforces style"

        elif workflow_type == "build":
            return "Builds Docker image and pushes to GitHub Container Registry"

        elif workflow_type == "deploy":
            return "Automatically deploys to production on merge to main"

        return "Custom workflow"
