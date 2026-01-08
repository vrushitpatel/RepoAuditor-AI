# RepoAuditor AI - Setup Guide

This guide provides step-by-step instructions to manually replicate and set up RepoAuditor AI from scratch.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GitHub App Setup](#github-app-setup)
3. [Google Gemini API Setup](#google-gemini-api-setup)
4. [Project Setup](#project-setup)
5. [Configuration](#configuration)
6. [Running the Application](#running-the-application)
7. [Testing the Integration](#testing-the-integration)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have:

- Python 3.11 or higher installed
- Git installed
- Docker and Docker Compose (optional, for containerized deployment)
- A GitHub account with organization admin access (or personal account)
- A Google Cloud account for Gemini API access
- Basic knowledge of Python, REST APIs, and webhooks

## GitHub App Setup

### Step 1: Create a GitHub App

1. Navigate to your GitHub account settings:

   - For organizations: `https://github.com/organizations/YOUR_ORG/settings/apps`
   - For personal: `https://github.com/settings/apps`

2. Click **"New GitHub App"**

3. Fill in the basic information:

   - **GitHub App name**: `RepoAuditor AI` (or your preferred name)
   - **Homepage URL**: `https://github.com/YOUR_USERNAME/repoauditor-ai`
   - **Webhook URL**: `https://your-domain.com/webhooks/github`
     - For local testing: Use ngrok or similar tunnel service
     - Example: `https://abc123.ngrok.io/webhooks/github`
   - **Webhook secret**: Generate a strong random string (save this for later)
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```

4. Set **Permissions**:

   - Repository permissions:
     - **Contents**: Read-only (to read code)
     - **Pull requests**: Read & write (to comment on PRs)
     - **Metadata**: Read-only (required)

5. Subscribe to **Events**:

   - ✓ Pull request
   - ✓ Pull request review comment

6. **Where can this GitHub App be installed?**

   - Select "Only on this account" (for testing)
   - Or "Any account" (for public distribution)

7. Click **"Create GitHub App"**

### Step 2: Generate and Download Private Key

1. After creating the app, scroll to **"Private keys"** section
2. Click **"Generate a private key"**
3. A `.pem` file will be downloaded automatically
4. Save this file securely (you'll reference it in configuration)

### Step 3: Note Your App ID

1. On the GitHub App settings page, note the **App ID** (you'll need this for configuration)

### Step 4: Install the GitHub App

1. Go to **"Install App"** in the left sidebar
2. Click **"Install"** next to your account/organization
3. Choose **"All repositories"** or **"Only select repositories"**
4. Click **"Install"**

## JIRA API Token:

1. Visit: https://id.atlassian.com/manage-profile/security/api-tokens
2. Create API Key here

## Google Gemini API Setup

### Step 1: Access Google AI Studio

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account

### Step 2: Get API Key

1. Click **"Get API Key"** in the top navigation
2. Click **"Create API Key"**
3. Select or create a Google Cloud project
4. Click **"Create API key in new project"** (or use existing project)
5. Copy the API key (save this for configuration)

### Step 3: Enable Gemini API

1. Ensure the Gemini API is enabled for your project
2. Set up billing if required (Gemini has a free tier)

## Project Setup

### Step 1: Create Project Directory

```bash
# Create main project directory
mkdir repoauditor-ai
cd repoauditor-ai

# Create application structure
mkdir -p app/{agents,workflows,integrations,webhooks,models,utils}
mkdir -p tests/{unit,integration}
mkdir -p scripts
```

### Step 2: Create Python Package Files

```bash
# Create __init__.py files
touch app/__init__.py
touch app/agents/__init__.py
touch app/workflows/__init__.py
touch app/integrations/__init__.py
touch app/webhooks/__init__.py
touch app/models/__init__.py
touch app/utils/__init__.py
touch tests/__init__.py
```

### Step 3: Create Configuration Files

Create `pyproject.toml`:

```bash
# See the pyproject.toml file in the repository
```

Create `.gitignore`:

```bash
# See the .gitignore file in the repository
```

### Step 4: Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install project in editable mode
pip install -e .
```

## Configuration

### Step 1: Create Environment File

```bash
# Copy example environment file
cp .env.example .env
```

### Step 2: Configure Environment Variables

Edit `.env` file with your actual credentials. The configuration is organized into logical groups:

#### GitHub App Configuration

```env
# GitHub App Configuration
GITHUB_APP_ID=123456  # Replace with your App ID
GITHUB_PRIVATE_KEY_PATH=./private-key.pem  # Path to your downloaded .pem file
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here  # The secret you generated (min 16 chars)
GITHUB_INSTALLATION_ID=  # Optional, auto-detected if not set
```

#### Gemini AI Configuration

```env
# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here  # Your Gemini API key (starts with AIza)
GEMINI_MODEL_NAME=gemini-2.5-flash-lite  # Model to use
GEMINI_TEMPERATURE=0.2  # Response randomness (0.0-1.0)
GEMINI_MAX_TOKENS=8192  # Maximum response tokens
```

#### JIRA Integration (Optional)

```env
# Jira Integration (Optional - leave blank if not using)
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
```

#### Server Configuration

```env
# Server Configuration
HOST=0.0.0.0  # Server bind address
PORT=8000  # Server port
DEBUG=False  # Debug mode (development only)
LOG_LEVEL=INFO  # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

#### Feature Flags and Performance

```env
# Feature Flags
ENABLE_CACHING=True  # Enable response caching
CACHE_TTL_SECONDS=3600  # Cache TTL (1 hour)
RATE_LIMIT_PER_HOUR=100  # API requests per hour per repo
MAX_FILES_PER_REVIEW=50  # Max files per PR review
REVIEW_TIMEOUT_SECONDS=300  # Review timeout (5 minutes)
```

### Step 3: Add Private Key File

```bash
# Copy your downloaded GitHub App private key to the project root
cp ~/Downloads/your-app-name.2024-01-01.private-key.pem ./private-key.pem

# Ensure it's not tracked by git (should be in .gitignore)
```

### Step 4: Understanding the Configuration System

RepoAuditor AI uses **Pydantic Settings** for type-safe configuration management with validation. The configuration is organized into logical groups for better maintainability.

#### Configuration Structure

The configuration system is divided into the following groups:

1. **GitHubAppSettings**: GitHub App credentials and settings
2. **GeminiAPISettings**: Google Gemini API configuration
3. **JIRASettings**: JIRA integration settings (optional)
4. **ServerSettings**: Server and logging configuration
5. **FeaturesSettings**: Feature flags and performance settings

#### Accessing Configuration in Code

Use the `get_settings()` function to access configuration throughout your application:

```python
from app.config import get_settings

# Get settings instance (cached)
settings = get_settings()

# Access grouped settings
print(f"GitHub App ID: {settings.github.app_id}")
print(f"Gemini Model: {settings.gemini.model_name}")
print(f"Server Port: {settings.server.port}")
print(f"JIRA Enabled: {settings.jira.enabled}")
print(f"Caching Enabled: {settings.features.enable_caching}")
```

#### Configuration Validation

The system automatically validates:

- **Type checking**: All values are validated against their types
- **Required fields**: Missing required fields will raise errors
- **Value ranges**: Numeric values are validated (e.g., port: 1-65535)
- **Format validation**: API keys, URLs, and paths are validated
- **File existence**: Private key file existence is checked

#### Example Configuration Validation

```python
# This will fail validation:
# - GitHub App ID must be an integer
# - Gemini API key must start with "AIza"
# - Private key file must exist
# - Temperature must be between 0.0 and 1.0

# Valid configuration:
GITHUB_APP_ID=123456
GEMINI_API_KEY=AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ
GEMINI_TEMPERATURE=0.2
```

#### Using Structured Logging

The logging system supports both standard and structured JSON logging:

```python
from app.utils.logger import setup_logger, LogContext, log_function_call

# Create a logger
logger = setup_logger(__name__)

# Basic logging
logger.info("Application started")

# Structured logging with JSON output
logger_json = setup_logger(__name__, structured=True)
logger_json.info("Processing request", extra={"extra_fields": {"user_id": 123}})

# Using log context for request tracking
with LogContext(request_id="req-12345"):
    logger.info("Processing request")  # Includes request_id in logs

# Decorator for function call logging
@log_function_call(logger)
def process_data(data: dict) -> dict:
    return data
```

#### Using the In-Memory Cache System

RepoAuditor AI includes a simple, thread-safe in-memory cache to prevent duplicate operations (like reviewing the same PR multiple times):

##### Basic Cache Usage

```python
from app.utils.cache import get_cache

# Get the global cache instance
cache = get_cache()

# Set a value with 5 minute TTL
cache.set("repo/pr/123", "reviewed", ttl_seconds=300)

# Get the value
value = cache.get("repo/pr/123")
if value:
    print(f"Already reviewed: {value}")

# Delete a specific entry
cache.delete("repo/pr/123")

# Clear all entries
cache.clear()
```

##### Preventing Duplicate PR Reviews

```python
from app.utils.cache import get_cache

def should_review_pr(repo: str, pr_number: int) -> bool:
    """Check if a PR should be reviewed (not recently reviewed)."""
    cache = get_cache()
    cache_key = f"{repo}/pr/{pr_number}"

    # Check if already reviewed recently
    if cache.get(cache_key):
        return False

    # Mark as reviewed for 1 hour
    cache.set(cache_key, "reviewed", ttl_seconds=3600)
    return True

# Usage
if should_review_pr("owner/repo", 123):
    # Proceed with review
    pass
else:
    # Skip - already reviewed recently
    pass
```

##### Cache Features

- **Thread-Safe**: All operations use locks for concurrent access
- **TTL Support**: Automatic expiration of entries
- **Automatic Cleanup**: Background thread removes expired entries every 60 seconds
- **Simple API**: Easy-to-use get/set/delete/clear methods
- **No External Dependencies**: Pure Python, no Redis or database needed

##### Cache Configuration

The cache respects the `ENABLE_CACHING` setting from your `.env` file:

```env
# Enable or disable caching
ENABLE_CACHING=True

# Cache TTL (used as default if not specified in set())
CACHE_TTL_SECONDS=3600
```

##### Advanced Cache Operations

```python
from app.utils.cache import SimpleCache, get_cache

# Create a custom cache instance with different cleanup interval
custom_cache = SimpleCache(cleanup_interval_seconds=30)

# Get cache size
cache = get_cache()
print(f"Cache has {cache.size()} entries")
print(f"Cache has {len(cache)} entries")  # Alternative syntax

# Check if key exists (without retrieving value)
if "repo/pr/123" in cache:
    print("Key exists in cache")

# Manual cleanup of expired entries
removed = cache.cleanup_expired()
print(f"Removed {removed} expired entries")

# Stop automatic cleanup (useful for testing or shutdown)
cache.stop_cleanup()
```

##### Cache Use Cases

1. **Duplicate PR Review Prevention**:

   ```python
   cache_key = f"{owner}/{repo}/pr/{pr_number}"
   if not cache.get(cache_key):
       # Review the PR
       perform_review()
       cache.set(cache_key, "reviewed", ttl_seconds=3600)
   ```

2. **Rate Limiting**:

   ```python
   cache_key = f"rate_limit/{repo}/{hour}"
   count = cache.get(cache_key) or 0
   if count < max_requests:
       cache.set(cache_key, count + 1, ttl_seconds=3600)
       # Process request
   else:
       # Rate limit exceeded
       pass
   ```

3. **Temporary Data Storage**:

   ```python
   # Store API response for 5 minutes
   cache.set("api_response/repo_info", data, ttl_seconds=300)

   # Retrieve cached response
   cached_data = cache.get("api_response/repo_info")
   ```

#### Environment-Specific Configuration

For different environments (development, staging, production), you can create environment-specific files:

```bash
# Development
.env.development

# Staging
.env.staging

# Production
.env.production
```

Then load the appropriate file:

```bash
# Development
cp .env.development .env

# Production
cp .env.production .env
```

## Running the Application

### Option 1: Run Locally (Development)

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at `http://localhost:8000`

### Option 2: Run with Docker

```bash
# Build the Docker image
docker build -t repoauditor-ai .

# Run the container
docker run -p 8000:8000 --env-file .env \
  -v $(pwd)/private-key.pem:/app/private-key.pem:ro \
  repoauditor-ai
```

### Option 3: Run with Docker Compose

```bash
# Build and start services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Testing the Integration

### Step 1: Set Up Local Tunnel (for Development)

If testing locally, you need to expose your local server to the internet:

```bash
# Install ngrok (https://ngrok.com/)
# Run ngrok
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update your GitHub App webhook URL to: https://abc123.ngrok.io/webhooks/github
```

### Step 2: Test Webhook Reception

1. Check application logs to ensure it's running:

```bash
# If running locally:
# You should see: "Application startup complete"

# If using Docker Compose:
docker-compose logs -f app
```

2. Create a test pull request in a repository where the app is installed

3. Monitor the logs for webhook reception:

```bash
# You should see webhook events being received and processed
```

### Step 3: Verify Code Review

1. Create or update a pull request
2. Wait for the AI review (check application logs for processing)
3. Verify that review comments appear on the PR

### Step 4: Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# API documentation
# Open browser to: http://localhost:8000/docs
```

## Deployment

### Production Deployment Checklist

#### 1. Security

- [ ] Use environment variables for all secrets (never commit secrets)
- [ ] Store private key securely (use secrets manager in production)
- [ ] Enable HTTPS (use reverse proxy like nginx or Traefik)
- [ ] Set up firewall rules
- [ ] Use webhook signature verification
- [ ] Implement rate limiting

#### 2. Infrastructure

```bash
# Example: Deploy to a cloud server

# 1. SSH into your server
ssh user@your-server.com

# 2. Clone the repository
git clone https://github.com/your-username/repoauditor-ai.git
cd repoauditor-ai

# 3. Set up environment
cp .env.example .env
# Edit .env with production values
nano .env

# 4. Add private key
nano private-key.pem
# Paste your private key content

# 5. Run with Docker Compose
docker-compose up -d

# 6. Check logs
docker-compose logs -f
```

#### 3. Reverse Proxy (nginx example)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable HTTPS with Let's Encrypt:

```bash
sudo certbot --nginx -d your-domain.com
```

#### 4. Monitoring

Set up monitoring for:

- Application health (`/health` endpoint)
- Error logs
- Response times
- Webhook processing success rate

#### 5. Update GitHub App Webhook URL

Update your GitHub App settings with the production URL:

```
https://your-domain.com/webhooks/github
```

## Troubleshooting

### Common Issues

#### 1. Webhook Not Received

**Symptoms**: No logs showing webhook events

**Solutions**:

- Verify webhook URL is correct in GitHub App settings
- Check that the application is running and accessible
- Verify ngrok tunnel is active (for local testing)
- Check firewall rules
- Review GitHub App installation (ensure it's installed on the repository)

#### 2. Authentication Errors

**Symptoms**: `401 Unauthorized` or authentication failures

**Solutions**:

- Verify `GITHUB_APP_ID` is correct
- Check that private key file path is correct
- Ensure private key file has correct permissions
- Verify the private key matches the GitHub App

#### 3. Gemini API Errors

**Symptoms**: AI review fails or returns errors

**Solutions**:

- Verify `GEMINI_API_KEY` is valid
- Check API quota/billing in Google Cloud Console
- Review API error messages in logs
- Ensure internet connectivity from the application

#### 4. Import Errors

**Symptoms**: `ModuleNotFoundError` or import failures

**Solutions**:

```bash
# Reinstall dependencies
pip install -e .

# Or with Docker:
docker-compose build --no-cache
```

#### 5. Port Already in Use

**Symptoms**: `Address already in use` error

**Solutions**:

```bash
# Find process using port 8000
# On Linux/macOS:
lsof -i :8000
# On Windows:
netstat -ano | findstr :8000

# Kill the process or change PORT in .env
```

### Debugging Tips

1. **Enable Debug Logging**:

```env
LOG_LEVEL=DEBUG
```

2. **Check Application Logs**:

```bash
# Local:
# Logs printed to console

# Docker Compose:
docker-compose logs -f app
```

3. **Test GitHub Authentication**:

```python
# Create a test script to verify GitHub App authentication
from app.integrations.github_client import GitHubClient

client = GitHubClient()
# Test authentication
```

4. **Verify Webhook Signature**:

- Check that `GITHUB_WEBHOOK_SECRET` matches GitHub App settings
- Review signature verification logic in `app/webhooks/signature.py`

5. **Test Gemini API Connection**:

```python
# Test script
from app.integrations.gemini_client import GeminiClient

client = GeminiClient()
# Test API call
```

### Getting Help

1. Check application logs for detailed error messages
2. Review API documentation:
   - FastAPI docs: `http://localhost:8000/docs`
   - GitHub Apps: https://docs.github.com/apps
   - Gemini API: https://ai.google.dev/docs
3. Enable debug logging for more detailed information
4. Check GitHub webhook delivery logs in App settings

## Next Steps

After successful setup:

1. **Customize Review Logic**: Modify `app/agents/code_reviewer.py` to adjust review criteria
2. **Add Custom Workflows**: Create new workflows in `app/workflows/`
3. **Integrate with Jira**: Configure Jira integration for ticket management
4. **Scale**: Consider horizontal scaling for high-traffic scenarios
5. **Monitor**: Set up comprehensive monitoring and alerting

## Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [GitHub Apps Documentation](https://docs.github.com/apps)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)

---

For questions or issues, please refer to the project's issue tracker or documentation.
