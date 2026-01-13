# CI/CD Generator - Technical Documentation

## 📋 Overview

This document provides technical details about the CI/CD Generator implementation, architecture, and code structure for developers who need to maintain, extend, or debug the system.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub PR Comment                        │
│                    "/generate-ci test"                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Webhook Handler                            │
│              (app/webhooks/webhook_handler.py)               │
│   - Receives issue_comment event                            │
│   - Extracts command from comment                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Command Parser                             │
│              (app/commands/parser.py)                        │
│   - Parses "/generate-ci test"                              │
│   - Validates command syntax                                │
│   - Extracts arguments                                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Command Router                             │
│           (app/workflows/command_handlers.py)                │
│   - Routes to handle_generate_ci_command()                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              handle_generate_ci_command()                    │
│           (app/workflows/command_handlers.py)                │
│   1. Post acknowledgment comment                            │
│   2. Initialize CICDGenerator                               │
│   3. Call generate_workflows()                              │
│   4. Format and post results                                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  CICDGenerator                               │
│              (app/agents/cicd_generator.py)                  │
│                                                              │
│   generate_workflows()                                       │
│   ├── ProjectDetector.detect_project()  ◄───────────┐      │
│   │   └── Returns ProjectInfo                       │      │
│   │                                                  │      │
│   ├── For each workflow type:                       │      │
│   │   ├── _select_template()                        │      │
│   │   ├── _load_template()                          │      │
│   │   └── _customize_template()                     │      │
│   │       ├── _customize_python()                   │      │
│   │       ├── _customize_nodejs()                   │      │
│   │       ├── _customize_docker()                   │      │
│   │       └── _customize_deploy()                   │      │
│   │                                                  │      │
│   └── Returns Dict[filename, yaml_content]          │      │
│                                                      │      │
└──────────────────────────────────────────────────────┼──────┘
                                                       │
        ┌──────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                 ProjectDetector                              │
│           (app/utils/project_detector.py)                    │
│                                                              │
│   detect_project()                                           │
│   ├── _detect_python_project()                              │
│   │   ├── Check requirements.txt                            │
│   │   ├── Check pyproject.toml (Poetry)                     │
│   │   ├── Check Pipfile (Pipenv)                            │
│   │   ├── Detect framework (FastAPI, Flask, Django)         │
│   │   ├── Detect test framework (pytest, unittest)          │
│   │   └── Detect linter (black, ruff, flake8)               │
│   │                                                          │
│   ├── _detect_nodejs_project()                              │
│   │   ├── Check package.json                                │
│   │   ├── Detect framework (Express, React, Next.js)        │
│   │   ├── Detect test framework (jest, mocha)               │
│   │   └── Detect linter (eslint, prettier)                  │
│   │                                                          │
│   ├── _check_docker()                                       │
│   │   └── Look for Dockerfile                               │
│   │                                                          │
│   └── Returns ProjectInfo dataclass                         │
│       ├── project_type: str                                 │
│       ├── framework: Optional[str]                          │
│       ├── test_framework: Optional[str]                     │
│       ├── linter: Optional[str]                             │
│       ├── package_manager: Optional[str]                    │
│       └── dependencies: List[str]                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
repoauditor-ai/
├── app/
│   ├── agents/
│   │   └── cicd_generator.py          # Main CI/CD generator agent
│   │
│   ├── commands/
│   │   ├── parser.py                  # Command parsing logic
│   │   └── registry.py                # Command registration
│   │
│   ├── templates/
│   │   └── cicd_templates/            # YAML workflow templates
│   │       ├── python_test.yml        # Python testing workflow
│   │       ├── python_lint.yml        # Python linting workflow
│   │       ├── nodejs_test.yml        # Node.js testing workflow
│   │       ├── nodejs_lint.yml        # Node.js linting workflow
│   │       ├── docker_build.yml       # Docker build workflow
│   │       ├── deploy_railway.yml     # Railway deployment
│   │       └── deploy_render.yml      # Render deployment
│   │
│   ├── utils/
│   │   └── project_detector.py        # Project type detection
│   │
│   ├── workflows/
│   │   └── command_handlers.py        # Command handler functions
│   │
│   └── webhooks/
│       └── webhook_handler.py         # GitHub webhook handler
│
├── HOW_CICD_WORKS.md                  # User-facing documentation
├── TESTING_CICD_GENERATOR.md          # Manual testing guide
└── CICD_GENERATOR.md                  # This file (technical docs)
```

---

## 🔧 Core Components

### 1. CICDGenerator (app/agents/cicd_generator.py)

**Purpose:** Main orchestrator for generating customized CI/CD workflows.

**Key Methods:**

#### `generate_workflows()`
```python
async def generate_workflows(
    self,
    repo_name: str,
    installation_id: int,
    workflow_types: List[str],
    pr_number: Optional[int] = None,
) -> Dict[str, str]:
```

**Flow:**
1. Calls `ProjectDetector.detect_project()` to analyze repository
2. Expands "all" to specific workflow types based on project
3. For each workflow type, calls `_generate_workflow()`
4. Returns dict of `{filename: yaml_content}`

**Example:**
```python
workflows = await generator.generate_workflows(
    repo_name="user/repo",
    installation_id=12345,
    workflow_types=["test", "lint"],
    pr_number=42,
)
# Returns:
# {
#     "test.yml": "name: Python Tests\n...",
#     "lint.yml": "name: Code Quality\n..."
# }
```

---

#### `_select_template()`
```python
def _select_template(
    self, workflow_type: str, project_info: ProjectInfo
) -> str:
```

**Logic:**
- For `test`: Returns `python_test.yml` or `nodejs_test.yml` based on project type
- For `lint`: Returns `python_lint.yml` or `nodejs_lint.yml`
- For `build`: Returns `docker_build.yml`
- For `deploy`: Returns `deploy_railway.yml` (default)

**Template Selection Matrix:**

| Workflow Type | Project Type | Template File |
|---------------|--------------|---------------|
| test | python | python_test.yml |
| test | nodejs | nodejs_test.yml |
| lint | python | python_lint.yml |
| lint | nodejs | nodejs_lint.yml |
| build | any | docker_build.yml |
| deploy | any | deploy_railway.yml |

---

#### `_customize_template()`
```python
def _customize_template(
    self,
    template_content: str,
    workflow_type: str,
    project_info: ProjectInfo,
    repo_name: str,
) -> str:
```

**Customization Process:**
1. Starts with template content (with `{{PLACEHOLDERS}}`)
2. Calls project-specific customizer based on `project_info.project_type`
3. Calls workflow-specific customizer based on `workflow_type`
4. Returns customized YAML with all placeholders replaced

---

#### `_customize_python()`

**Placeholders Replaced:**

| Placeholder | Replacement Logic | Example |
|-------------|-------------------|---------|
| `{{PYTHON_VERSION}}` | `project_info.language_version` or `"3.11"` | `3.11` |
| `{{REQUIREMENTS_FILE}}` | Based on package manager | `requirements.txt`, `pyproject.toml`, `Pipfile` |
| `{{INSTALL_COMMAND}}` | Based on package manager | `pip install -r requirements.txt`, `poetry install` |
| `{{TEST_COMMAND}}` | Based on test framework | `pytest tests/ -v`, `python -m unittest` |
| `{{LINTER}}` | Based on linter | `Black`, `Ruff`, `Flake8` |
| `{{LINTER_INSTALL}}` | Install commands for linter | `pip install black ruff` |
| `{{LINTER_COMMAND}}` | Run commands for linter | `black . --check && ruff check .` |
| `{{COVERAGE_STEP}}` | Coverage upload step (if pytest-cov) | Codecov action |
| `{{TYPE_CHECK_STEP}}` | Type checking step (if mypy) | `mypy .` |

**Example:**
```yaml
# Template:
- name: Install dependencies
  run: {{INSTALL_COMMAND}}

# After customization (Poetry detected):
- name: Install dependencies
  run: pip install poetry && poetry install
```

---

#### `_customize_nodejs()`

**Placeholders Replaced:**

| Placeholder | Replacement Logic | Example |
|-------------|-------------------|---------|
| `{{NODE_VERSION}}` | `project_info.language_version` or `"18.x"` | `18.x` |
| `{{INSTALL_COMMAND}}` | Based on package manager | `npm ci`, `yarn install --frozen-lockfile` |
| `{{TEST_COMMAND}}` | Based on scripts in package.json | `npm test`, `yarn test` |
| `{{LINTER_COMMAND}}` | Based on linter | `npm run lint`, `npm run format:check` |
| `{{COVERAGE_STEP}}` | Coverage upload (if jest) | Codecov action |
| `{{TYPE_CHECK_STEP}}` | Type checking (if TypeScript) | `npm run type-check` |

---

### 2. ProjectDetector (app/utils/project_detector.py)

**Purpose:** Analyze repository to detect project type, framework, dependencies.

**Key Method:**

#### `detect_project()`
```python
async def detect_project(
    self,
    repo_name: str,
    installation_id: int,
    pr_number: Optional[int] = None,
) -> ProjectInfo:
```

**Detection Flow:**

```
1. Fetch repository files
   ├── Get tree from GitHub API
   └── Get file list

2. Check for Python indicators
   ├── requirements.txt?
   ├── pyproject.toml?
   ├── Pipfile?
   └── *.py files?

3. Check for Node.js indicators
   ├── package.json?
   └── *.js files?

4. If Python detected:
   └── _detect_python_project()
       ├── Parse requirements.txt
       ├── Detect framework (fastapi, flask, django)
       ├── Detect test framework (pytest, unittest)
       ├── Detect linter (black, ruff, flake8)
       └── Detect package manager (pip, poetry, pipenv)

5. If Node.js detected:
   └── _detect_nodejs_project()
       ├── Parse package.json
       ├── Detect framework (express, react, next.js)
       ├── Detect test framework (jest, mocha)
       ├── Detect linter (eslint, prettier)
       └── Detect package manager (npm, yarn, pnpm)

6. Check for Docker
   └── _check_docker()
       └── Look for Dockerfile

7. Return ProjectInfo
```

**ProjectInfo Dataclass:**
```python
@dataclass
class ProjectInfo:
    project_type: str  # "python", "nodejs", "unknown"
    framework: Optional[str] = None  # "fastapi", "express", etc.
    language_version: Optional[str] = None  # "3.11", "18.x"
    test_framework: Optional[str] = None  # "pytest", "jest"
    linter: Optional[str] = None  # "black", "eslint"
    package_manager: Optional[str] = None  # "pip", "npm", "yarn"
    has_docker: bool = False
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    scripts: Dict[str, str] = field(default_factory=dict)
```

---

### 3. Command Handler (app/workflows/command_handlers.py)

**Function:** `handle_generate_ci_command()`

**Location:** app/workflows/command_handlers.py:349-528

**Flow:**

```python
async def handle_generate_ci_command(event: IssueCommentEvent) -> None:
    # 1. Parse command arguments
    workflow_types = parse_workflow_types(event.comment.body)

    # 2. Post acknowledgment
    post_ack_comment()

    # 3. Initialize generator
    cicd_generator = CICDGenerator(gemini_client, github_client)

    # 4. Generate workflows
    workflows = await cicd_generator.generate_workflows(...)

    # 5. Get project info for formatting
    project_info = await detector.detect_project(...)

    # 6. Format workflows
    formatted_comment = cicd_generator.format_workflows_for_comment(...)

    # 7. Post results
    post_workflows_comment()
```

**Error Handling:**
- Catches all exceptions
- Posts helpful error message with troubleshooting tips
- Logs error with context

---

## 🎨 Template System

### Template Structure

Templates use `{{PLACEHOLDER}}` syntax for dynamic values.

**Example Template (python_test.yml):**
```yaml
name: Python Tests

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '{{PYTHON_VERSION}}'

    - name: Install dependencies
      run: {{INSTALL_COMMAND}}

    - name: Run tests
      run: {{TEST_COMMAND}}

{{COVERAGE_STEP}}

{{TYPE_CHECK_STEP}}
```

### Adding New Templates

**Steps to add a new template:**

1. **Create template file:**
   ```bash
   touch app/templates/cicd_templates/my_new_template.yml
   ```

2. **Add placeholders:**
   ```yaml
   name: My Workflow

   on:
     push:
       branches: [ main ]

   jobs:
     my-job:
       runs-on: ubuntu-latest
       steps:
         - name: Do something
           run: {{MY_PLACEHOLDER}}
   ```

3. **Update `_select_template()` in cicd_generator.py:**
   ```python
   def _select_template(self, workflow_type: str, project_info: ProjectInfo) -> str:
       if workflow_type == "my-new-type":
           return "my_new_template.yml"
       # ... existing code
   ```

4. **Add customization logic:**
   ```python
   def _customize_my_new_type(self, content: str, project_info: ProjectInfo) -> str:
       content = content.replace("{{MY_PLACEHOLDER}}", "my value")
       return content
   ```

5. **Call customizer in `_customize_template()`:**
   ```python
   def _customize_template(self, ...):
       # ... existing code
       if workflow_type == "my-new-type":
           content = self._customize_my_new_type(content, project_info)
       return content
   ```

6. **Update registry in app/commands/registry.py:**
   ```python
   # Already includes "generate-ci" with flexible args
   # No changes needed unless you want to restrict args
   ```

---

## 🔄 Data Flow

### Complete Request Flow

```
1. GitHub Webhook
   POST /webhooks/github
   Body: { "action": "created", "comment": { "body": "/generate-ci test" } }

2. Webhook Handler
   - Verifies signature
   - Parses event
   - Extracts command

3. Command Parser
   - Matches "/generate-ci test"
   - Extracts command: "generate-ci"
   - Extracts args: ["test"]

4. Command Router
   - Routes to handle_generate_ci_command()

5. Command Handler
   - Posts acknowledgment: "🚀 CI/CD Generator Started"
   - Initializes CICDGenerator
   - Calls generate_workflows()

6. CICDGenerator
   - Calls ProjectDetector.detect_project()

7. ProjectDetector
   - Fetches repo files via GitHub API
   - Analyzes files
   - Returns ProjectInfo(project_type="python", test_framework="pytest", ...)

8. CICDGenerator (continued)
   - Selects template: "python_test.yml"
   - Loads template content
   - Customizes template:
     - Replaces {{PYTHON_VERSION}} → "3.11"
     - Replaces {{TEST_COMMAND}} → "pytest tests/ -v"
   - Returns: {"test.yml": "name: Python Tests\n..."}

9. Command Handler (continued)
   - Formats workflows with format_workflows_for_comment()
   - Posts formatted comment to PR

10. GitHub
    - Comment appears on PR with workflows
```

---

## 🧪 Testing

### Unit Testing

**Test ProjectDetector:**
```python
# tests/test_project_detector.py

async def test_detect_python_project():
    detector = ProjectDetector(github_client)

    # Mock GitHub API to return files
    github_client.get_repo_tree = Mock(return_value=[
        {"path": "requirements.txt"},
        {"path": "app/main.py"},
    ])

    github_client.get_file_content = Mock(return_value="pytest\nblack\n")

    project_info = await detector.detect_project(
        repo_name="user/repo",
        installation_id=12345,
    )

    assert project_info.project_type == "python"
    assert project_info.test_framework == "pytest"
    assert project_info.linter == "black"
```

**Test CICDGenerator:**
```python
# tests/test_cicd_generator.py

async def test_generate_python_test_workflow():
    generator = CICDGenerator(gemini_client, github_client)

    project_info = ProjectInfo(
        project_type="python",
        test_framework="pytest",
        package_manager="pip",
    )

    workflows = await generator.generate_workflows(
        repo_name="user/repo",
        installation_id=12345,
        workflow_types=["test"],
    )

    assert "test.yml" in workflows
    assert "pytest" in workflows["test.yml"]
    assert "{{" not in workflows["test.yml"]  # No placeholders
```

### Integration Testing

See `TESTING_CICD_GENERATOR.md` for complete manual testing guide.

---

## 🐛 Debugging

### Common Issues

#### Issue 1: Placeholder Not Replaced

**Symptom:** Generated YAML contains `{{PLACEHOLDER}}`

**Debug Steps:**
1. Check if placeholder exists in template
2. Verify customization function is called
3. Add logging:
   ```python
   logger.info(f"Before customization: {content}")
   content = content.replace("{{PLACEHOLDER}}", value)
   logger.info(f"After customization: {content}")
   ```

#### Issue 2: Wrong Template Selected

**Symptom:** Node.js workflow for Python project

**Debug Steps:**
1. Check ProjectDetector output:
   ```python
   logger.info(f"Detected project: {project_info}")
   ```
2. Verify template selection logic in `_select_template()`
3. Check file detection in `_detect_python_project()`

#### Issue 3: File Not Found Error

**Symptom:** `FileNotFoundError: Template not found: python_test.yml`

**Debug Steps:**
1. Verify template file exists:
   ```bash
   ls app/templates/cicd_templates/python_test.yml
   ```
2. Check TEMPLATE_DIR constant:
   ```python
   logger.info(f"Template dir: {self.TEMPLATE_DIR}")
   logger.info(f"Template path: {template_path}")
   ```
3. Verify path resolution is correct

---

## 🚀 Extending the System

### Adding Support for New Language

**Example: Adding Go support**

1. **Update ProjectDetector:**
   ```python
   # app/utils/project_detector.py

   async def _detect_go_project(self, files: List[str]) -> Optional[ProjectInfo]:
       """Detect Go project and extract info."""
       if not any(f.endswith(".go") for f in files):
           return None

       # Look for go.mod
       if "go.mod" in files:
           go_mod = await self._get_file_content("go.mod")
           # Parse go.mod for dependencies

       return ProjectInfo(
           project_type="go",
           test_framework="testing",  # Go's built-in testing
           package_manager="go",
       )
   ```

2. **Create Go templates:**
   ```yaml
   # app/templates/cicd_templates/go_test.yml

   name: Go Tests

   on: [push, pull_request]

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-go@v4
           with:
             go-version: '{{GO_VERSION}}'
         - run: go test ./...
   ```

3. **Add customization:**
   ```python
   # app/agents/cicd_generator.py

   def _customize_go(self, content: str, project_info: ProjectInfo) -> str:
       content = content.replace(
           "{{GO_VERSION}}",
           project_info.language_version or "1.21"
       )
       return content
   ```

4. **Update template selection:**
   ```python
   def _select_template(self, workflow_type: str, project_info: ProjectInfo) -> str:
       if workflow_type == "test":
           if project_info.project_type == "go":
               return "go_test.yml"
           # ... existing code
   ```

### Adding New Workflow Type

**Example: Adding "security" workflow**

1. **Create template:**
   ```yaml
   # app/templates/cicd_templates/security_scan.yml

   name: Security Scan

   on: [push, pull_request]

   jobs:
     security:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - name: Run security scan
           run: {{SECURITY_COMMAND}}
   ```

2. **Update `_select_template()`:**
   ```python
   def _select_template(self, workflow_type: str, project_info: ProjectInfo) -> str:
       if workflow_type == "security":
           return "security_scan.yml"
       # ... existing code
   ```

3. **Add customization:**
   ```python
   def _customize_security(self, content: str, project_info: ProjectInfo) -> str:
       if project_info.project_type == "python":
           command = "bandit -r ."
       elif project_info.project_type == "nodejs":
           command = "npm audit"
       else:
           command = "echo 'No security scan available'"

       content = content.replace("{{SECURITY_COMMAND}}", command)
       return content
   ```

4. **Call customizer:**
   ```python
   def _customize_template(self, ...):
       # ... existing code
       if workflow_type == "security":
           content = self._customize_security(content, project_info)
       return content
   ```

5. **Update `_get_all_workflow_types()`:**
   ```python
   def _get_all_workflow_types(self, project_info: ProjectInfo) -> List[str]:
       types = ["test", "security"]  # Add security
       # ... existing code
       return types
   ```

---

## 📊 Performance Considerations

### Optimization Strategies

1. **Caching**
   - Cache project detection results for same repo/commit
   - Cache template contents (already in memory)
   - Cache GitHub API responses

2. **Parallel Processing**
   - Generate multiple workflows concurrently
   - Use `asyncio.gather()` for parallel API calls

3. **Rate Limiting**
   - GitHub API has rate limits
   - Use conditional requests (ETags)
   - Implement exponential backoff

**Example Parallel Generation:**
```python
async def generate_workflows(self, ...):
    # ... detection code

    # Generate workflows in parallel
    tasks = [
        self._generate_workflow(wf_type, project_info, repo_name)
        for wf_type in workflow_types
    ]

    results = await asyncio.gather(*tasks)

    workflows = {filename: content for filename, content in results}
    return workflows
```

---

## 🔒 Security Considerations

1. **Input Validation**
   - Validate workflow type arguments
   - Sanitize file paths
   - Validate YAML syntax

2. **Secret Handling**
   - Never log secrets or tokens
   - Use GitHub's secret storage
   - Don't include secrets in workflows

3. **GitHub API Security**
   - Use installation tokens (not personal access tokens)
   - Scope tokens to minimum permissions
   - Verify webhook signatures

4. **YAML Injection**
   - Sanitize user inputs before template insertion
   - Validate generated YAML
   - Don't allow arbitrary code execution

---

## 📚 Additional Resources

- **GitHub Actions Documentation:** https://docs.github.com/en/actions
- **YAML Specification:** https://yaml.org/spec/
- **GitHub App Documentation:** https://docs.github.com/en/developers/apps
- **Project Documentation:**
  - `HOW_CICD_WORKS.md` - User-facing explanation
  - `TESTING_CICD_GENERATOR.md` - Manual testing guide
  - `TROUBLESHOOTING_WEBHOOKS.md` - Webhook debugging

---

## 🤝 Contributing

When contributing to the CI/CD Generator:

1. **Follow existing patterns**
   - Use async/await consistently
   - Add type hints to all functions
   - Include docstrings

2. **Add tests**
   - Unit tests for new functions
   - Integration tests for workflows
   - Manual testing checklist

3. **Update documentation**
   - Update this file for code changes
   - Update HOW_CICD_WORKS.md for user-facing changes
   - Update TESTING_CICD_GENERATOR.md for new test cases

4. **Code style**
   - Follow PEP 8 for Python
   - Use Black for formatting
   - Run linters before committing

---

## 📞 Support

For issues or questions:

1. Check logs in FastAPI terminal
2. Review this documentation
3. Check TROUBLESHOOTING_WEBHOOKS.md
4. Review GitHub Actions logs
5. Open an issue on GitHub

---

**Last Updated:** 2026-01-12

**Maintainers:** RepoAuditor AI Team
