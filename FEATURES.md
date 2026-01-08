# RepoAuditor AI - Features

## Core Features

### AI Code Review

- **Automated PR Analysis**: AI-powered code review using Google Gemini 2.0 Flash
- **Intelligent Feedback**: Context-aware suggestions and code quality recommendations
- **Multi-file Analysis**: Analyzes all changed files in a pull request
- **Review Summarization**: Generates concise summaries of code reviews

### GitHub Integration

- **GitHub App**: Seamless integration via GitHub App webhooks
- **Real-time Processing**: Automatic review on PR creation and updates
- **PR Comments**: Posts review feedback directly as PR comments
- **Webhook Security**: HMAC SHA256 signature verification for webhooks
- **Multi-repository Support**: Works across multiple repositories
- **Event Handling**: Processes pull_request, issue_comment, and pull_request_review_comment events
- **Background Processing**: Async task processing with FastAPI BackgroundTasks
- **Immediate Response**: Returns 200 OK to GitHub immediately to prevent timeouts
- **Command Support**: Recognizes slash commands in comments (/explain, /review, /help)
- **Comment Types**: Handles both PR conversation comments and inline code review comments

### GitHub API Client

- **PyGithub Wrapper**: Comprehensive GitHub API client with enhanced functionality
- **JWT Authentication**: Automatic JWT generation for GitHub App authentication
- **Token Management**: Automatic token caching and refresh (1-hour TTL)
- **Installation Tokens**: Secure installation access token retrieval
- **Exponential Backoff**: Automatic retry with exponential backoff (3 attempts, 2.0x multiplier)
- **Rate Limit Handling**: Intelligent rate limit detection and retry
- **PR Operations**:
  - Get PR details (title, body, author, stats, URLs)
  - Get PR diff (unified diff format)
  - Post PR comments (Markdown supported)
  - Add reactions to comments (+1, -1, heart, rocket, etc.)
- **File Operations**: Get file contents from any branch/commit
- **Commit Status**: Update commit status checks (pending, success, error, failure)
- **Error Handling**: Comprehensive logging with GithubException handling
- **Easy Mocking**: Design optimized for unit testing
- **Client Caching**: Caches GitHub client instances per installation

### Gemini API Client

- **LangChain Integration**: Uses langchain-google-genai for AI-powered analysis
- **Multiple Analysis Types**:
  - Security analysis (SQL injection, XSS, secrets, CSRF, etc.)
  - Performance analysis (N+1 queries, inefficient algorithms)
  - Best practices review (naming, error handling, SOLID principles)
  - Bug detection (null checks, edge cases, logic errors)
  - General comprehensive review
- **Structured Responses**: Pydantic models for type-safe findings
- **Detailed Findings**: Severity levels, code locations, recommendations, example fixes
- **Code Explanation**: Generate detailed explanations with complexity analysis
- **Fix Suggestions**: AI-powered fix recommendations with trade-offs
- **Text Generation**: General-purpose text generation with token/cost tracking
- **Model Flexibility**: Easy switching between Flash (fast/cheap) and Pro (capable/expensive)
- **Cost Tracking**: Token counting and USD cost estimation
- **Streaming Support**: Real-time response streaming (for future use)
- **Retry Logic**: Exponential backoff for API failures (3 attempts, 2.0x multiplier)
- **JSON Extraction**: Smart parsing of JSON from markdown code blocks
- **Usage Statistics**: Track input/output tokens and cumulative costs
- **Prompt Templates**: Pre-built templates for different analysis types
- **Custom Configuration**: Configurable temperature, max tokens, top-p, top-k

### Command Handlers

- **Slash Command Processing**: Dedicated handlers for interactive PR commands
- **Command Routing**: Intelligent routing based on comment type (PR vs review comment)
- **Background Execution**: All commands run asynchronously without blocking webhooks
- **Error Recovery**: Graceful error handling with user-friendly error messages
- **Cost Tracking**: Comprehensive tracking of tokens and costs for each command
- **Supported Commands**:
  - `/explain` - Generate AI explanation of PR changes
  - `/review` - Trigger on-demand code review
  - `/help` - Display command documentation
- **Context-Aware**: Different behavior for PR comments vs line-specific review comments
- **Metadata Logging**: All command executions logged with full context
- **Reply Threading**: Responses posted in appropriate comment threads

### Architecture & Performance

- **Multi-Agent Orchestration**: Built with LangGraph for sophisticated workflow management
- **Stateless Design**: No database required - fully event-driven architecture
- **In-Memory Caching**: Thread-safe cache to prevent duplicate PR reviews
  - Automatic cache expiration with configurable TTL
  - Duplicate review prevention (default: 5 minutes)
  - Background cleanup thread for expired entries
  - Cache metadata tracking (cost, tokens, duration, severity counts)
- **Rate Limiting**: Configurable API request limits per repository
- **Timeout Protection**: Configurable review timeout to prevent hanging operations
- **Automatic Retries**: Built-in retry logic with exponential backoff
- **Helper Utilities**: Comprehensive helper functions for common tasks
  - Cache key generation for PRs and commits
  - Duplicate review detection and prevention
  - Formatting utilities (duration, cost, tokens)
  - Error context extraction for debugging
  - Webhook payload validation
  - Execution summary generation

### LangGraph State Management

RepoAuditor AI uses LangGraph for sophisticated workflow orchestration with a powerful state management system:

#### Workflow State Schema
- **WorkflowState TypedDict**: Comprehensive state container for PR review workflows
  - `pr_data`: Dict containing repo_name, pr_number, diff, files, and metadata
  - `review_results`: List of findings from AI code analysis
  - `current_step`: Tracks current workflow step (initialized, analyzing, reviewing, posting, completed, failed)
  - `error`: Optional error message for failure handling
  - `metadata`: Timestamps, costs, token usage, model information, and analytics

#### Immutable State Management
- **Deep Copy Updates**: All state updates use deep copy to ensure LangGraph can track changes properly
- **Pure Functions**: State helper functions are pure and side-effect free
- **Predictable Workflow**: Immutability ensures consistent and reproducible workflow execution
- **Easy Debugging**: State history can be tracked and inspected at any point

#### State Helper Functions
- **create_initial_workflow_state()**: Initialize new workflow with default values
  - Sets up initial PR data structure
  - Creates empty review results list
  - Initializes metadata with timestamps and cost tracking
- **update_state()**: Update state immutably with automatic timestamp tracking
  - Creates deep copy of state
  - Applies updates without mutating original
  - Automatically updates `updated_at` timestamp
- **add_review_finding()**: Append findings to state immutably
  - Adds AI-generated findings to review results
  - Maintains immutability of original state
- **set_error()**: Mark workflow as failed with error message
  - Sets error message
  - Updates current_step to "failed"
- **update_metadata()**: Track costs, tokens, and model usage
  - Accumulates API costs across multiple calls
  - Counts total tokens (input + output)
  - Tracks number of model API calls

#### State Validation
- **validate_workflow_state()**: Comprehensive state structure validation
  - Checks all required top-level keys
  - Validates data types
  - Ensures structural integrity
- **validate_pr_data()**: PR data format validation
  - Validates repo_name format (owner/repo)
  - Checks pr_number is positive integer
  - Validates files structure if present
- **validate_finding()**: Finding structure validation
  - Validates severity levels (CRITICAL, HIGH, MEDIUM, LOW, INFO)
  - Checks required fields
  - Ensures type safety

#### Cost and Analytics Tracking
- **Automatic Cost Calculation**: Tracks USD costs for each AI API call
- **Token Usage**: Monitors input and output tokens across all operations
- **Model Call Counter**: Counts total number of AI model invocations
- **Timestamp Tracking**: Records created_at and updated_at for all state changes
- **Cumulative Metrics**: Aggregates costs and usage across entire workflow

#### In-Memory Execution
- **No Database Required**: State lives entirely in memory during workflow execution
- **No PostgreSQL/Redis**: Zero external dependencies for state management
- **No SQLAlchemy/Alembic**: No database models or migrations needed
- **Event-Driven**: State is created per webhook event and discarded after completion
- **Stateless Design**: Each workflow execution is independent and isolated

### LangGraph Workflow Orchestration

RepoAuditor AI implements a sophisticated code review workflow using LangGraph with conditional routing and error handling:

#### Workflow Nodes
- **start**: Initialize workflow state from webhook data
  - Validates required fields
  - Sets up initial metadata and timestamps
- **fetch_pr**: Fetch PR details and diff from GitHub API
  - Retrieves PR metadata (title, author, description)
  - Fetches unified diff and file change list
  - Updates state with complete PR information
- **review_code**: AI-powered code analysis with Gemini
  - Runs comprehensive code review (security, performance, bugs, best practices)
  - Extracts structured findings with severity levels
  - Tracks token usage and API costs
- **classify_severity**: Categorize findings by severity
  - Counts issues by severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)
  - Groups by type (security, performance, bug, style)
  - Prepares data for conditional routing
- **post_review**: Post formatted results to GitHub PR
  - Generates Markdown comment with detailed findings
  - Updates commit status check
  - Includes recommendations and example fixes
- **check_critical**: Determine if manual approval needed
  - Checks for critical or high severity issues
  - Sets approval requirement flag
  - Routes to appropriate next step
- **request_approval**: Request manual review (if critical issues found)
  - Posts prominent approval request comment
  - Summarizes critical issues requiring attention
  - Provides next steps for developers
- **end**: Finalize workflow and log metrics
  - Calculates total duration
  - Logs comprehensive metrics
  - Marks workflow as completed

#### Conditional Routing
- **After fetch_pr**: Skip review if no diff or files changed
- **After check_critical**: Route to approval request if critical/high issues found
  - Critical or High issues → request_approval → end
  - No critical issues → end
- **Error Handling**: Automatic routing to end node on any error

#### Workflow Features
- **Pure Functions**: All nodes are pure functions taking and returning WorkflowState
- **Error Recovery**: Each node has comprehensive error handling
- **Logging**: Detailed logging at each step for debugging
- **Testability**: Nodes can be tested independently
- **Composability**: Easy to add, remove, or modify nodes
- **Visualization**: Built-in ASCII diagram of workflow structure
- **Metadata Tracking**: Complete workflow metadata (duration, costs, tokens, API calls)

#### Execution Modes
- **Single Execution**: Execute workflow for one PR
- **Batch Execution**: Process multiple PRs concurrently with rate limiting
- **Webhook Execution**: Triggered by GitHub webhook events (with duplicate prevention)
- **Command Execution**: On-demand execution via slash commands
- **Manual Testing**: Test workflow with sample data without webhooks
- **Async Support**: Fully async/await for high performance

#### Workflow Metrics
Every workflow execution tracks:
- **Duration**: Total workflow execution time (formatted: "2m 45s", "1h 5m 30s")
- **Findings**: Count and breakdown by severity/type
- **Costs**: Total USD cost of AI API calls (formatted: "$0.0125", "$1.50")
- **Tokens**: Input and output token counts (formatted: "15,234 tokens")
- **API Calls**: Number of model invocations
- **Approval Status**: Whether manual approval is required
- **Cache Status**: Whether review was cached to prevent duplicates

#### Enhanced Logging
All workflow executions include comprehensive logging:
- **Workflow start/end**: With full PR context
- **Node execution**: Each workflow step logged
- **API calls**: GitHub and Gemini API calls tracked
- **Execution time**: Formatted duration for readability
- **Cost tracking**: Formatted costs with proper precision
- **Token usage**: Formatted with thousands separators
- **Severity breakdown**: Counts by CRITICAL, HIGH, MEDIUM, LOW, INFO
- **Error context**: Detailed error information with stack traces

See [app/workflows/code_review_workflow.py](app/workflows/code_review_workflow.py) for complete workflow definition.

### Configuration & Management

- **Type-Safe Configuration**: Pydantic-based configuration with validation
- **Environment Variables**: Full configuration via .env files
- **Feature Flags**: Enable/disable caching, set limits, and control behavior
- **Structured Logging**: JSON logging support with contextual information
- **Log Levels**: Configurable logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Integration Capabilities

- **JIRA Integration**: Optional ticket creation and tracking (configurable)
- **RESTful API**: FastAPI-based REST endpoints
- **Health Checks**: Built-in health monitoring endpoints
- **API Documentation**: Auto-generated Swagger/ReDoc documentation

### Deployment & DevOps

- **Docker Support**: Fully containerized with Docker and Docker Compose
- **Production Ready**: Type hints, error handling, and security best practices
- **CORS Support**: Configurable cross-origin resource sharing
- **Scalable**: Async/await architecture for high concurrency

### Security

- **Webhook Verification**: GitHub webhook signature validation
- **Private Key Authentication**: Secure GitHub App authentication
- **Secret Management**: Environment-based credential management
- **File Size Limits**: Configurable max files per review

## Technical Capabilities

### Processing Limits (Configurable)

- **Max Files per Review**: Default 50 files
- **Review Timeout**: Default 300 seconds (5 minutes)
- **Cache TTL**: Default 3600 seconds (1 hour)
- **Rate Limit**: Default 100 requests per hour per repository

### Slash Commands

RepoAuditor AI supports interactive slash commands that can be triggered by commenting on pull requests:

#### `/explain` - Explain PR Changes
**Usage**: Comment `/explain` on a pull request

**Features**:
- Generates AI-powered explanation of what the PR does
- Provides high-level summary (2-3 sentences)
- Lists key changes by file with bullet points
- Identifies potential impact and areas of concern
- Suggests related changes or dependencies needed
- Uses Gemini Flash for cost-effective generation
- Displays metadata: tokens used, cost, generation time

**Example Response**:
```markdown
## 📝 PR Explanation

This PR refactors the authentication system to use JWT tokens instead of
session cookies. The changes improve security and enable stateless authentication.

Key changes by file:
- auth/login.py: Added JWT token generation on successful login
- middleware/auth.py: Updated to validate JWT tokens instead of sessions
- models/user.py: Added token refresh mechanism

Potential impact: All existing sessions will be invalidated after deployment.
```

**Line-Specific Explanation**: Comment `/explain` on a specific line in a code review to get an explanation of that particular change.

---

#### `/review` - Trigger On-Demand Review
**Usage**: Comment `/review` on a pull request

**Features**:
- Triggers a full code review on demand
- Same comprehensive analysis as automatic reviews
- Analyzes security, performance, bugs, and best practices
- Posts detailed findings with severity levels
- Updates commit status check
- Tracks costs and token usage
- Runs in background without blocking

**Example Response**:
```markdown
🤖 Code Review Initiated

@username requested a code review. Starting analysis now...

*This may take a minute or two depending on the size of the PR.*
```

Followed by the complete review results (same format as automatic reviews).

**Use Cases**:
- Re-run review after making changes
- Request review on older PRs that weren't auto-reviewed
- Bypass cache to get fresh analysis
- Manual review for PRs that were skipped

---

#### `/help` - Show Available Commands
**Usage**: Comment `/help` on a pull request

**Features**:
- Displays comprehensive help documentation
- Lists all available commands with descriptions
- Shows usage examples and tips
- Includes configuration information
- Links to documentation

**Example Response**:
```markdown
## 🤖 RepoAuditor AI - Available Commands

### 📝 `/explain`
Get a detailed explanation of what this PR does...

### 🔍 `/review`
Trigger a comprehensive code review...

### ❓ `/help`
Show this help message...
```

---

#### Command Features
- **Case Insensitive**: Commands work with any case (`/Review`, `/EXPLAIN`, etc.)
- **Must Start Comment**: Commands must be at the beginning of the comment
- **Background Processing**: Commands run asynchronously without blocking
- **Error Handling**: Graceful error messages if command fails
- **Cost Tracking**: All AI operations track tokens and costs
- **Comprehensive Logging**: All command executions are logged with metadata

---

### Supported Events

- **Pull Request Events**:
  - `opened` - New PR created (triggers automatic review)
  - `synchronize` - New commits pushed to PR (triggers automatic review)
  - `reopened` - Closed PR reopened (triggers automatic review)
- **Issue Comment Events**:
  - `created` - Comment added to PR conversation
  - Command detection for `/explain`, `/review`, `/help`
- **Pull Request Review Comment Events**:
  - `created` - Inline comment on PR diff
  - Command detection for `/explain` on specific code lines

### API Endpoints

- `GET /` - Application info and supported events
- `GET /health` - Health check with configuration status
- `POST /webhooks/github` - GitHub webhook receiver (main endpoint)
- `GET /webhooks/metrics` - Simple webhook metrics and counters
- `GET /docs` - Swagger UI API documentation
- `GET /redoc` - ReDoc API documentation

### Webhook Metrics

- **Total Webhooks**: Count of all webhooks received
- **Pull Request Events**: Count of PR events processed
- **Issue Comment Events**: Count of issue comment events processed
- **Review Comment Events**: Count of review comment events processed
- **Commands Processed**: Count of slash commands detected and processed
- **Reviews Triggered**: Count of code reviews initiated

## Technology Stack

- **Python 3.11+**: Modern Python with full type hints
- **LangGraph**: Multi-agent workflow orchestration
- **Google Gemini 2.0**: Advanced AI model for code intelligence
- **FastAPI**: High-performance async web framework
- **PyGithub**: GitHub API integration
- **Pydantic**: Data validation and settings management
- **Docker**: Containerization for deployment

## Developer Experience

### Manual Testing Without Webhooks

RepoAuditor AI supports manual testing and development without requiring GitHub webhook setup:

#### Testing Methods
1. **Python Script**: Complete workflow testing script with step-by-step execution
2. **curl Simulation**: Send webhook payloads directly to local server
3. **Interactive Console**: Test individual components in Python REPL
4. **Unit Tests**: Comprehensive pytest test suite for state management
5. **Manual Workflow**: Step-by-step execution using GitHub API directly

#### Benefits
- **Rapid Development**: Test changes without webhook setup
- **Isolated Debugging**: Test components independently
- **CI/CD Friendly**: Run tests in any environment
- **Cost Control**: Test locally before making expensive API calls
- **Learning Tool**: Understand workflow execution step-by-step

See [Github Webhook.md](Github%20Webhook.md#manual-testing-without-webhooks) for detailed testing documentation.
