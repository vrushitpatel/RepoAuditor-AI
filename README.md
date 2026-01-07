# RepoAuditor AI

An AI-powered code review system that automatically reviews pull requests using LangGraph multi-agent orchestration and Google's Gemini 2.5 Pro API.

## Features

- **Automated Code Review**: Intelligent analysis of pull requests using AI
- **Multi-Agent Architecture**: Built with LangGraph for sophisticated orchestration
- **GitHub Integration**: Seamless integration via GitHub App webhooks
- **Stateless Design**: No database required - fully stateless architecture
- **Jira Integration**: Optional ticket creation and tracking
- **Production Ready**: Containerized with Docker, type-safe with full type hints

## Architecture

RepoAuditor AI uses a stateless, event-driven architecture:

1. **Webhook Receiver**: FastAPI endpoint receives GitHub webhook events
2. **Multi-Agent Orchestration**: LangGraph coordinates specialized AI agents
3. **Code Analysis**: Gemini 2.5 Pro analyzes code changes and provides feedback
4. **Review Posting**: Automated comments posted back to GitHub PRs

### Technology Stack

- **Python 3.11+**: Modern Python with full type hints
- **LangGraph**: Multi-agent orchestration framework
- **Gemini 2.5 Pro**: Google's advanced AI model for code intelligence
- **FastAPI**: High-performance async web framework
- **PyGithub**: GitHub API integration
- **Docker**: Containerization for easy deployment

## Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for containerized deployment)
- GitHub App credentials
- Google Gemini API key
- (Optional) Jira account for issue tracking

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd repoauditor-ai
```

### 2. Environment Setup

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:

```env
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=./private-key.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Install Dependencies

#### Using pip

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

#### Using Docker

```bash
docker-compose up --build
```

### 4. Run the Application

#### Local Development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Docker

```bash
docker-compose up
```

The API will be available at `http://localhost:8000`

## GitHub App Setup

1. Create a new GitHub App in your organization settings
2. Set the webhook URL to `https://your-domain.com/webhooks/github`
3. Enable webhook events: `pull_request`, `pull_request_review_comment`
4. Generate and download a private key
5. Install the app on your repositories

## Project Structure

```
repoauditor-ai/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── agents/                 # LangGraph agents
│   │   ├── state.py           # Shared state definitions
│   │   └── code_reviewer.py   # Code review agent
│   ├── workflows/             # LangGraph workflows
│   │   └── code_review_workflow.py
│   ├── integrations/          # External service clients
│   │   ├── github_client.py
│   │   ├── gemini_client.py
│   │   └── jira_client.py
│   ├── webhooks/              # Webhook handlers
│   │   ├── github.py
│   │   └── signature.py
│   ├── models/                # Pydantic models
│   │   └── webhook_events.py
│   └── utils/                 # Utility functions
│       ├── cache.py
│       ├── retry.py
│       └── logger.py
├── tests/                     # Test suite
├── scripts/                   # Utility scripts
├── Dockerfile                 # Container definition
├── docker-compose.yml        # Docker orchestration
└── pyproject.toml            # Project dependencies
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy app/
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

### Required Variables

- `GITHUB_APP_ID`: Your GitHub App ID
- `GITHUB_PRIVATE_KEY_PATH`: Path to your GitHub App private key
- `GITHUB_WEBHOOK_SECRET`: Secret for webhook verification
- `GEMINI_API_KEY`: Your Google Gemini API key

### Optional Variables

- `JIRA_BASE_URL`: Jira instance URL
- `JIRA_EMAIL`: Jira account email
- `JIRA_API_TOKEN`: Jira API token
- `LOG_LEVEL`: Logging level (default: INFO)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)

## Deployment

### Docker Deployment

1. Build the image:
```bash
docker build -t repoauditor-ai .
```

2. Run the container:
```bash
docker run -p 8000:8000 --env-file .env repoauditor-ai
```

### Production Considerations

- Use a reverse proxy (nginx, Traefik) for HTTPS
- Set up proper logging and monitoring
- Configure rate limiting
- Use secrets management for sensitive credentials
- Set appropriate resource limits in docker-compose.yml

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass and code is formatted
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [Report bugs or request features]
- Documentation: See `Guide.md` for detailed setup instructions

## Roadmap

- [ ] Advanced code analysis patterns
- [ ] Multi-language support optimization
- [ ] Custom review rules configuration
- [ ] Performance metrics dashboard
- [ ] Slack/Teams integration
