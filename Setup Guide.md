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

Edit `.env` file with your actual credentials:

```env
# GitHub App Configuration
GITHUB_APP_ID=123456  # Replace with your App ID
GITHUB_PRIVATE_KEY_PATH=./private-key.pem  # Path to your downloaded .pem file
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here  # The secret you generated

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here  # Your Gemini API key

# Jira Integration (Optional - leave blank if not using)
JIRA_BASE_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=

# Application Configuration
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

### Step 3: Add Private Key File

```bash
# Copy your downloaded GitHub App private key to the project root
cp ~/Downloads/your-app-name.2024-01-01.private-key.pem ./private-key.pem

# Ensure it's not tracked by git (should be in .gitignore)
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
