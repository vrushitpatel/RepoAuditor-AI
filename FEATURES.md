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
- **Model Flexibility**: Easy switching between Flash (fast/cheap) and Pro (capable/expensive)
- **Cost Tracking**: Token counting and USD cost estimation
- **Streaming Support**: Real-time response streaming (for future use)
- **Retry Logic**: Exponential backoff for API failures (3 attempts, 2.0x multiplier)
- **JSON Extraction**: Smart parsing of JSON from markdown code blocks
- **Usage Statistics**: Track input/output tokens and cumulative costs
- **Prompt Templates**: Pre-built templates for different analysis types
- **Custom Configuration**: Configurable temperature, max tokens, top-p, top-k

### Architecture & Performance
- **Multi-Agent Orchestration**: Built with LangGraph for sophisticated workflow management
- **Stateless Design**: No database required - fully event-driven architecture
- **In-Memory Caching**: Thread-safe cache to prevent duplicate PR reviews
- **Rate Limiting**: Configurable API request limits per repository
- **Timeout Protection**: Configurable review timeout to prevent hanging operations
- **Automatic Retries**: Built-in retry logic with exponential backoff

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

### Supported Events
- **Pull Request Events**:
  - `opened` - New PR created
  - `synchronize` - New commits pushed to PR
  - `reopened` - Closed PR reopened
- **Issue Comment Events**:
  - `created` - Comment added to PR conversation
  - Command detection for `/explain`, `/review`, `/help`
- **Pull Request Review Comment Events**:
  - `created` - Inline comment on PR diff
  - Command detection for code-specific explanations

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
