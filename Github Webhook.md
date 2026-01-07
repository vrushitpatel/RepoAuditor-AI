# GitHub Webhook Setup Guide

This guide provides step-by-step instructions for manually setting up GitHub webhooks for RepoAuditor AI.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setting Up Your Application](#setting-up-your-application)
3. [Creating a GitHub App](#creating-a-github-app)
4. [Configuring Webhook Events](#configuring-webhook-events)
5. [Testing the Webhook](#testing-the-webhook)
6. [Monitoring and Debugging](#monitoring-and-debugging)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have:

- RepoAuditor AI application running (locally or deployed)
- GitHub account with repository or organization admin access
- A publicly accessible URL for webhook delivery (use ngrok for local testing)
- Webhook secret generated (min 16 characters)

## Setting Up Your Application

### Step 1: Start RepoAuditor AI

```bash
# Local development
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or with Docker
docker-compose up
```

### Step 2: Verify Application is Running

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "github_app_configured": true,
#   "gemini_configured": true,
#   "jira_enabled": false,
#   "caching_enabled": true
# }
```

### Step 3: Set Up Public URL (For Local Testing)

If testing locally, you need a public URL for GitHub to send webhooks to:

```bash
# Install ngrok (https://ngrok.com/)
# Run ngrok
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

**Note**: Keep ngrok running throughout your testing session.

## Creating a GitHub App

### Step 1: Navigate to GitHub App Settings

- **For organizations**: `https://github.com/organizations/YOUR_ORG/settings/apps`
- **For personal accounts**: `https://github.com/settings/apps`

### Step 2: Create New GitHub App

Click **"New GitHub App"** button.

### Step 3: Basic Information

Fill in the following fields:

| Field | Value | Example |
|-------|-------|---------|
| **GitHub App name** | Your app name | `RepoAuditor AI` |
| **Homepage URL** | Your project URL | `https://github.com/yourname/repoauditor-ai` |
| **Webhook URL** | Your webhook endpoint | `https://abc123.ngrok.io/webhooks/github` |
| **Webhook secret** | Generate a strong secret | See command below |

**Generate webhook secret:**

```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

**Save this secret!** You'll need it for your `.env` file.

### Step 4: Set Permissions

Configure the following **Repository permissions**:

| Permission | Access Level | Purpose |
|------------|-------------|---------|
| **Contents** | Read-only | Read repository code and files |
| **Pull requests** | Read & write | Read PR details and post comments |
| **Issues** | Read & write | Read and respond to issue comments |
| **Metadata** | Read-only | Required (automatically set) |

### Step 5: Subscribe to Events

Select the following webhook events:

- ✅ **Pull request**
  - Triggered when PRs are opened, synchronized, or reopened

- ✅ **Issue comment**
  - Triggered when comments are created on PRs
  - Used for commands like `/explain` or `/review`

- ✅ **Pull request review comment**
  - Triggered when comments are created on PR diffs
  - Used for inline code discussions

### Step 6: Installation Settings

**Where can this GitHub App be installed?**

Choose based on your needs:
- **Only on this account**: For private/testing use
- **Any account**: For public distribution

Click **"Create GitHub App"**.

## Configuring Webhook Events

### Step 1: Generate Private Key

After creating the app:

1. Scroll to **"Private keys"** section
2. Click **"Generate a private key"**
3. A `.pem` file will be downloaded automatically
4. Save this file securely in your project directory

```bash
# Move the private key to your project
mv ~/Downloads/your-app.private-key.pem ./private-key.pem

# Secure the file (Linux/Mac)
chmod 600 private-key.pem
```

### Step 2: Note Your App ID

1. On the GitHub App settings page, find the **App ID** (top of the page)
2. Copy this ID (e.g., `123456`)

### Step 3: Install the GitHub App

1. Go to **"Install App"** in the left sidebar
2. Click **"Install"** next to your account/organization
3. Choose repositories:
   - **All repositories**: App can access all current and future repos
   - **Only select repositories**: Choose specific repos to monitor
4. Click **"Install"**

### Step 4: Get Installation ID (Optional)

The installation ID is auto-detected, but you can find it manually:

```bash
# Visit your installation URL
https://github.com/settings/installations

# Click on the installed app
# The URL will contain the installation ID
# https://github.com/settings/installations/12345678
```

### Step 5: Update Your `.env` File

Add the credentials to your `.env` file:

```env
# GitHub App Configuration
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=./private-key.pem
GITHUB_WEBHOOK_SECRET=your_generated_secret_here
GITHUB_INSTALLATION_ID=  # Optional, auto-detected

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_NAME=gemini-2.0-flash-exp

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Feature Flags
ENABLE_CACHING=True
CACHE_TTL_SECONDS=3600
```

### Step 6: Restart Your Application

```bash
# If running locally
# Stop the server (Ctrl+C) and restart
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# If using Docker
docker-compose restart
```

## Testing the Webhook

### Step 1: Create a Test Pull Request

1. Create a new branch in one of your repositories
2. Make a small code change
3. Open a pull request

### Step 2: Verify Webhook Delivery

**In GitHub:**

1. Go to your GitHub App settings
2. Navigate to **"Advanced"** → **"Recent Deliveries"**
3. You should see webhook deliveries listed
4. Click on a delivery to see:
   - Request headers
   - Request payload
   - Response (should be `200 OK`)

**Example webhook delivery:**

```json
{
  "action": "opened",
  "number": 1,
  "pull_request": {
    "id": 123456789,
    "number": 1,
    "title": "Test PR",
    "state": "open"
  }
}
```

### Step 3: Check Application Logs

```bash
# Your application logs should show:
# INFO: Received pull_request event
# INFO: Pull request opened: owner/repo#1
# INFO: Triggering code review for PR #1
```

### Step 4: Monitor Metrics

Check the metrics endpoint to see webhook activity:

```bash
curl http://localhost:8000/webhooks/metrics

# Expected response:
# {
#   "total_webhooks": 1,
#   "pull_request_events": 1,
#   "issue_comment_events": 0,
#   "review_comment_events": 0,
#   "commands_processed": 0,
#   "reviews_triggered": 1
# }
```

### Step 5: Test Commands

**Test issue comment commands:**

1. Go to your test PR
2. Add a comment: `/explain`
3. Check logs and metrics

**Test review comment commands:**

1. Go to **"Files changed"** tab in your PR
2. Add a comment on a specific line: `/explain`
3. Check logs and metrics

## Monitoring and Debugging

### Available Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | API information and supported events |
| `/health` | GET | Health check and configuration status |
| `/webhooks/github` | POST | GitHub webhook receiver |
| `/webhooks/metrics` | GET | Simple webhook metrics |
| `/docs` | GET | Swagger API documentation |
| `/redoc` | GET | ReDoc API documentation |

### Check Application Status

```bash
# API info
curl http://localhost:8000/

# Health check
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/webhooks/metrics
```

### View Logs

```bash
# If running locally, logs appear in terminal

# If using Docker
docker-compose logs -f app

# If deployed, check your hosting platform's logs
```

### Enable Debug Logging

Edit `.env` to enable detailed logging:

```env
LOG_LEVEL=DEBUG
```

Restart the application to apply changes.

## Troubleshooting

### Issue 1: Webhook Not Received

**Symptoms**: No logs showing webhook events

**Solutions**:

1. **Verify webhook URL is correct**:
   - Check GitHub App settings
   - Ensure URL ends with `/webhooks/github`
   - For ngrok, verify tunnel is running: `ngrok http 8000`

2. **Check firewall rules**:
   - Ensure port 8000 is accessible
   - For production, ensure HTTPS is configured

3. **Verify app is installed**:
   - Go to repository **Settings** → **Integrations**
   - Confirm your GitHub App is listed

4. **Check webhook deliveries in GitHub**:
   - GitHub App settings → **Advanced** → **Recent Deliveries**
   - Look for error messages or failed deliveries

### Issue 2: Signature Verification Failed (401 Error)

**Symptoms**: Logs show "Invalid webhook signature"

**Solutions**:

1. **Verify webhook secret matches**:
   ```bash
   # Check .env file
   cat .env | grep GITHUB_WEBHOOK_SECRET

   # Compare with GitHub App settings
   # Settings → Webhook secret
   ```

2. **Regenerate webhook secret**:
   - Generate new secret: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Update GitHub App settings
   - Update `.env` file
   - Restart application

### Issue 3: Invalid JSON Payload Error

**Symptoms**: Logs show "Failed to parse webhook payload"

**Solutions**:

1. **Check webhook delivery details in GitHub**:
   - View the actual payload sent
   - Verify it's valid JSON

2. **Check for middleware interference**:
   - If using reverse proxy (nginx), ensure it's not modifying the payload
   - Verify `Content-Type` header is preserved

### Issue 4: Background Task Not Executing

**Symptoms**: Webhook received but code review not triggered

**Solutions**:

1. **Check logs for errors**:
   ```bash
   # Look for traceback or error messages
   docker-compose logs -f app | grep ERROR
   ```

2. **Verify Gemini API configuration**:
   ```bash
   curl http://localhost:8000/health
   # Check: "gemini_configured": true
   ```

3. **Check for rate limiting**:
   - Review metrics: `curl http://localhost:8000/webhooks/metrics`
   - Check if `reviews_triggered` is incrementing

### Issue 5: Commands Not Working

**Symptoms**: Comment commands like `/explain` are ignored

**Solutions**:

1. **Verify command format**:
   - Commands must start with `/`
   - Must be at the beginning of the comment
   - Valid: `/explain`
   - Invalid: `Can you /explain this?`

2. **Check event subscriptions**:
   - GitHub App settings → **Permissions & events**
   - Ensure "Issue comment" is subscribed

3. **Check comment location**:
   - Issue comments work on PR conversation
   - Review comments work on PR diffs

### Issue 6: Private Key Not Found

**Symptoms**: Error on startup: "Private key file not found"

**Solutions**:

```bash
# Verify file exists
ls -la private-key.pem

# Verify path in .env
cat .env | grep GITHUB_PRIVATE_KEY_PATH

# Update path if necessary (use absolute path if needed)
GITHUB_PRIVATE_KEY_PATH=/absolute/path/to/private-key.pem
```

### Getting Help

If issues persist:

1. **Enable debug logging**:
   ```env
   LOG_LEVEL=DEBUG
   ```

2. **Check GitHub webhook deliveries**:
   - Look for specific error messages
   - Check response codes and bodies

3. **Review application logs**:
   - Look for stack traces
   - Note any error messages

4. **Test connectivity**:
   ```bash
   # Test if webhook URL is accessible from outside
   curl -X POST https://your-url.com/webhooks/github
   # Should return 401 (signature verification failed) - this is expected
   ```

5. **Consult documentation**:
   - [GitHub Apps Documentation](https://docs.github.com/apps)
   - [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Security Best Practices

1. **Never commit secrets**:
   - Add `.env` and `*.pem` to `.gitignore`
   - Use environment variables in production

2. **Rotate credentials regularly**:
   - Generate new webhook secrets periodically
   - Update private keys if compromised

3. **Use HTTPS in production**:
   - Never use HTTP for webhook URLs
   - Use reverse proxy with SSL/TLS

4. **Implement rate limiting**:
   - Configure `RATE_LIMIT_PER_HOUR` in `.env`
   - Monitor metrics for abuse

5. **Monitor webhook deliveries**:
   - Regularly check GitHub's delivery logs
   - Set up alerts for failed deliveries

## Using the GitHub API Client

RepoAuditor AI includes a comprehensive GitHub API client wrapper with authentication, rate limiting, and error handling.

### Basic Usage

```python
from app.integrations.github_client import GitHubClient

# Create client instance
client = GitHubClient()

# Get PR details
pr_details = client.get_pr_details(
    repo_name="owner/repo",
    pr_number=123,
    installation_id=456
)
print(f"PR Title: {pr_details['title']}")
print(f"Changed files: {pr_details['changed_files']}")

# Get PR diff
diff = client.get_pr_diff(
    repo_name="owner/repo",
    pr_number=123,
    installation_id=456
)

# Post a comment
client.post_pr_comment(
    repo_name="owner/repo",
    pr_number=123,
    body="LGTM! :+1:",
    installation_id=456
)

# Add reaction to comment
client.add_reaction(
    repo_name="owner/repo",
    comment_id=98765,
    reaction="+1",
    installation_id=456
)

# Get file contents
content = client.get_file_contents(
    repo_name="owner/repo",
    path="src/main.py",
    ref="main",
    installation_id=456
)

# Update commit status
client.update_commit_status(
    repo_name="owner/repo",
    sha="abc123def",
    state="success",
    description="Code review completed!",
    installation_id=456,
    target_url="https://example.com/review/123"
)
```

### Features

- **Automatic token management**: Tokens are cached and automatically refreshed when expired
- **Rate limiting**: Exponential backoff retry on rate limits (3 attempts max)
- **Error handling**: Comprehensive logging and exception handling
- **Easy to mock**: Perfect for unit testing

### Authentication

The client uses GitHub App authentication with JWT tokens:

```python
from app.integrations.github_auth import GitHubAuth

# Authentication is handled automatically by GitHubClient
# But you can use it directly if needed:
auth = GitHubAuth()

# Generate JWT for app authentication
jwt_token = auth.generate_jwt()

# Get installation access token
token = auth.get_installation_token(installation_id=456)

# Check if token is valid
is_valid = auth.is_token_valid(installation_id=456)

# Force token refresh
auth.invalidate_token(installation_id=456)
token = auth.get_installation_token(installation_id=456)
```

### Rate Limiting

All API methods include automatic retry with exponential backoff:

- **Max attempts**: 3
- **Initial delay**: 1 second
- **Backoff multiplier**: 2.0

If a request fails due to rate limiting, it will automatically retry with increasing delays.

### Error Handling

The client raises `GithubException` for API errors:

```python
from github import GithubException

try:
    pr_details = client.get_pr_details("owner/repo", 999999, installation_id=456)
except GithubException as e:
    print(f"API error: {e}")
    # Handle error appropriately
```

## Using the Gemini API Client

RepoAuditor AI includes a powerful Gemini API client for AI-powered code analysis with structured responses and cost tracking.

### Basic Usage

```python
from app.integrations.gemini_client import GeminiClient
from app.models.review_findings import ModelConfig

# Initialize with default Flash model (fast, cost-effective)
client = GeminiClient(use_flash=True)

# Or initialize with Pro model (more capable)
client = GeminiClient(use_flash=False)

# Analyze code for security issues
analysis = await client.analyze_code(code_diff, "security")

# Check findings
for finding in analysis.findings:
    if finding.severity in ["CRITICAL", "HIGH"]:
        print(f"{finding.severity}: {finding.title}")
        print(f"Location: {finding.location.file_path}:{finding.location.line_start}")
        print(f"Fix: {finding.recommendation}")

# Generate code explanation
explanation = await client.generate_explanation(
    code_snippet="def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
    context="Recursive function for calculating factorial"
)
print(explanation.explanation)
print(f"Complexity: {explanation.complexity}")

# Suggest fix for an issue
fix = await client.suggest_fix(
    issue_description="SQL injection vulnerability",
    code_context='query = f"SELECT * FROM users WHERE id = {user_id}"'
)
print(f"Fixed code:\\n{fix.fixed_code}")
print(f"Explanation: {fix.explanation}")
```

### Analysis Types

The client supports multiple analysis types:

1. **security**: Focus on vulnerabilities (SQL injection, XSS, secrets, etc.)
2. **performance**: Find performance bottlenecks (N+1 queries, inefficient algorithms)
3. **best_practices**: Check code style, naming, error handling
4. **bugs**: Detect logic errors, null checks, edge cases
5. **general**: Comprehensive review covering all areas

```python
# Run security scan
security_analysis = await client.analyze_code(diff, "security")

# Check performance issues
perf_analysis = await client.analyze_code(diff, "performance")

# Review best practices
style_analysis = await client.analyze_code(diff, "best_practices")
```

### Model Switching

Switch between Flash (fast, cheap) and Pro (capable, expensive) models:

```python
# Start with Flash for initial analysis
client = GeminiClient(use_flash=True)
initial_analysis = await client.analyze_code(diff, "general")

# Switch to Pro for detailed security analysis
client.switch_model(use_flash=False)
detailed_analysis = await client.analyze_code(diff, "security")

# Switch back to Flash
client.switch_model(use_flash=True)
```

### Cost Tracking

Monitor token usage and costs:

```python
client = GeminiClient()

# Perform analyses
await client.analyze_code(diff1, "security")
await client.analyze_code(diff2, "performance")

# Check usage stats
stats = client.get_usage_stats()
print(f"Total tokens: {stats['total_tokens']}")
print(f"Input tokens: {stats['input_tokens']}")
print(f"Output tokens: {stats['output_tokens']}")
print(f"Total cost: ${stats['total_cost_usd']:.4f}")
print(f"Model: {stats['model']}")

# Reset stats for new batch
client.reset_usage_stats()
```

### Streaming Support

For real-time feedback (future use):

```python
# Stream analysis results as they arrive
async for chunk in client.analyze_code_stream(diff, "security"):
    print(chunk, end="", flush=True)
```

### Custom Model Configuration

Use custom model configurations:

```python
from app.models.review_findings import ModelConfig

# Create custom config
config = ModelConfig(
    model_name="gemini-2.0-flash-exp",
    temperature=0.1,  # Lower temperature for more deterministic output
    max_output_tokens=4096,
    input_cost_per_million=0.075,
    output_cost_per_million=0.30
)

client = GeminiClient(model_config=config)
```

### Structured Findings

The client returns structured findings with detailed information:

```python
analysis = await client.analyze_code(diff, "security")

for finding in analysis.findings:
    print(f"Severity: {finding.severity}")  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    print(f"Type: {finding.type}")  # security, bug, performance, etc.
    print(f"Title: {finding.title}")
    print(f"Description: {finding.description}")

    if finding.location:
        print(f"File: {finding.location.file_path}")
        print(f"Lines: {finding.location.line_start}-{finding.location.line_end}")
        print(f"Code: {finding.location.code_snippet}")

    print(f"Recommendation: {finding.recommendation}")
    print(f"Example fix: {finding.example_fix}")
    print(f"References: {finding.references}")

print(f"\\nSummary: {analysis.summary}")
print(f"Total issues: {analysis.total_issues}")
print(f"Critical: {analysis.critical_count}")
print(f"High: {analysis.high_count}")
print(f"Cost: ${analysis.cost_usd:.4f}")
```

### Model Comparison

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| **gemini-2.0-flash-exp** | Very Fast | $0.075/$0.30 per M tokens | General reviews, quick scans |
| **gemini-1.5-pro-latest** | Slower | $1.25/$5.00 per M tokens | Complex analysis, security audits |
| **gemini-2.0-pro-exp** | Slower | $1.25/$5.00 per M tokens | Latest features, experimental |

## Next Steps

After successfully setting up webhooks:

1. **Customize review logic**: Modify `app/agents/code_reviewer.py`
2. **Implement command handlers**: Enhance command processing in `app/webhooks/github.py`
3. **Use GitHub API client**: Integrate the client methods in your workflows
4. **Use Gemini API client**: Leverage AI-powered analysis in your reviews
5. **Add custom workflows**: Create new workflows in `app/workflows/`
6. **Set up monitoring**: Implement comprehensive logging and metrics
7. **Deploy to production**: Use Docker, cloud hosting, or Kubernetes

---

For more information, see:
- [Setup Guide.md](Setup%20Guide.md) - Full application setup
- [README.md](README.md) - Project overview
- [FEATURES.md](FEATURES.md) - Feature list
- [TROUBLESHOOTING_WEBHOOK_ERRORS.md](TROUBLESHOOTING_WEBHOOK_ERRORS.md) - Webhook troubleshooting
