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

| Field               | Value                    | Example                                      |
| ------------------- | ------------------------ | -------------------------------------------- |
| **GitHub App name** | Your app name            | `RepoAuditor AI`                             |
| **Homepage URL**    | Your project URL         | `https://github.com/yourname/repoauditor-ai` |
| **Webhook URL**     | Your webhook endpoint    | `https://abc123.ngrok.io/webhooks/github`    |
| **Webhook secret**  | Generate a strong secret | See command below                            |

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

| Permission        | Access Level | Purpose                            |
| ----------------- | ------------ | ---------------------------------- |
| **Contents**      | Read-only    | Read repository code and files     |
| **Pull requests** | Read & write | Read PR details and post comments  |
| **Issues**        | Read & write | Read and respond to issue comments |
| **Metadata**      | Read-only    | Required (automatically set)       |

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
GEMINI_MODEL_NAME=gemini-2.5-flash-lite

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

| Endpoint            | Method | Purpose                               |
| ------------------- | ------ | ------------------------------------- |
| `/`                 | GET    | API information and supported events  |
| `/health`           | GET    | Health check and configuration status |
| `/webhooks/github`  | POST   | GitHub webhook receiver               |
| `/webhooks/metrics` | GET    | Simple webhook metrics                |
| `/docs`             | GET    | Swagger API documentation             |
| `/redoc`            | GET    | ReDoc API documentation               |

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
    model_name="gemini-2.5-flash-lite",
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

| Model                     | Speed     | Cost                      | Best For                          |
| ------------------------- | --------- | ------------------------- | --------------------------------- |
| **gemini-2.5-flash-lite** | Very Fast | $0.075/$0.30 per M tokens | General reviews, quick scans      |
| **gemini-1.5-pro-latest** | Slower    | $1.25/$5.00 per M tokens  | Complex analysis, security audits |
| **gemini-2.0-pro-exp**    | Slower    | $1.25/$5.00 per M tokens  | Latest features, experimental     |

## Manual Testing Without Webhooks

For development and testing, you can manually trigger the code review workflow without setting up webhooks. This is useful for:

- Testing the LangGraph workflow locally
- Developing new features without GitHub integration
- Debugging issues in isolation

### Method 1: Using Python Script

Create a test script to manually invoke the workflow:

```python
# test_workflow_manual.py
import asyncio
from app.agents.state import create_initial_workflow_state, validate_workflow_state
from app.integrations.gemini_client import GeminiClient
from app.integrations.github_client import GitHubClient

async def test_code_review_workflow():
    """Manually test the code review workflow."""

    # Step 1: Create initial state
    state = create_initial_workflow_state(
        repo_name="owner/repo",
        pr_number=123,
        diff="""
diff --git a/app/main.py b/app/main.py
index 1234567..abcdefg 100644
--- a/app/main.py
+++ b/app/main.py
@@ -10,7 +10,7 @@ def login(username, password):
-    query = f"SELECT * FROM users WHERE username = '{username}'"
+    query = "SELECT * FROM users WHERE username = ?"
        """,
        files=[
            {"filename": "app/main.py", "status": "modified", "additions": 1, "deletions": 1}
        ],
        pr_title="Fix SQL injection vulnerability",
        pr_author="developer123"
    )

    # Step 2: Validate state
    is_valid, error = validate_workflow_state(state)
    print(f"State valid: {is_valid}")
    if error:
        print(f"Validation error: {error}")
        return

    print(f"\nInitial state:")
    print(f"  Repo: {state['pr_data']['repo_name']}")
    print(f"  PR #: {state['pr_data']['pr_number']}")
    print(f"  Current step: {state['current_step']}")
    print(f"  Files changed: {len(state['pr_data']['files'])}")

    # Step 3: Run code analysis with Gemini
    gemini_client = GeminiClient(use_flash=True)

    print("\n[Step 1] Analyzing code for security issues...")
    analysis = await gemini_client.analyze_code(
        state['pr_data']['diff'],
        analysis_type="security"
    )

    # Step 4: Update state with findings
    from app.agents.state import update_state, add_review_finding, update_metadata

    state = update_state(state, current_step="analyzing")

    for finding in analysis.findings:
        state = add_review_finding(state, {
            "severity": finding.severity,
            "type": finding.type,
            "title": finding.title,
            "description": finding.description,
            "file_path": finding.location.file_path if finding.location else None,
            "line_start": finding.location.line_start if finding.location else None,
            "recommendation": finding.recommendation
        })

    # Update metadata with costs
    state = update_metadata(
        state,
        cost_usd=analysis.cost_usd,
        tokens=analysis.input_tokens + analysis.output_tokens,
        model_call=True,
        model_name=gemini_client.model_name
    )

    state = update_state(state, current_step="analysis_complete")

    print(f"\n[Step 2] Analysis complete!")
    print(f"  Findings: {len(state['review_results'])}")
    print(f"  Total cost: ${state['metadata']['total_cost_usd']:.4f}")
    print(f"  Total tokens: {state['metadata']['total_tokens']}")

    # Step 5: Display findings
    print(f"\n[Step 3] Review Results:")
    for i, finding in enumerate(state['review_results'], 1):
        print(f"\n  Finding #{i}:")
        print(f"    Severity: {finding['severity']}")
        print(f"    Type: {finding['type']}")
        print(f"    Title: {finding['title']}")
        print(f"    Description: {finding['description']}")
        if finding.get('file_path'):
            print(f"    Location: {finding['file_path']}:{finding['line_start']}")
        print(f"    Recommendation: {finding['recommendation']}")

    # Step 6: Generate summary
    print(f"\n[Step 4] Generating summary...")
    state = update_state(state, current_step="generating_summary")

    summary = f"""
Code Review Summary for PR #{state['pr_data']['pr_number']}

Total Issues Found: {len(state['review_results'])}
- Critical: {sum(1 for f in state['review_results'] if f['severity'] == 'CRITICAL')}
- High: {sum(1 for f in state['review_results'] if f['severity'] == 'HIGH')}
- Medium: {sum(1 for f in state['review_results'] if f['severity'] == 'MEDIUM')}
- Low: {sum(1 for f in state['review_results'] if f['severity'] == 'LOW')}

Analysis Cost: ${state['metadata']['total_cost_usd']:.4f}
Tokens Used: {state['metadata']['total_tokens']}
Model: {state['metadata'].get('model_name', 'Unknown')}
"""

    print(summary)

    # Step 7: Mark workflow as complete
    state = update_state(state, current_step="completed")

    print(f"\n[Step 5] Workflow completed!")
    print(f"  Final state: {state['current_step']}")
    print(f"  Duration: {state['metadata']['created_at']} -> {state['metadata']['updated_at']}")

    return state

# Run the test
if __name__ == "__main__":
    asyncio.run(test_code_review_workflow())
```

Run the test:

```bash
python test_workflow_manual.py
```

### Method 2: Using curl to Simulate Webhook

Create a sample webhook payload and send it to your local server:

```bash
# Create payload file
cat > webhook_payload.json << 'EOF'
{
  "action": "opened",
  "number": 123,
  "pull_request": {
    "id": 1234567890,
    "number": 123,
    "state": "open",
    "title": "Fix SQL injection vulnerability",
    "body": "This PR fixes a SQL injection vulnerability in the login function",
    "user": {
      "login": "developer123"
    },
    "head": {
      "ref": "fix/sql-injection",
      "sha": "abc123def456"
    },
    "base": {
      "ref": "main",
      "repo": {
        "full_name": "owner/repo",
        "name": "repo",
        "owner": {
          "login": "owner"
        }
      }
    },
    "changed_files": 1,
    "additions": 1,
    "deletions": 1
  },
  "repository": {
    "full_name": "owner/repo",
    "name": "repo",
    "owner": {
      "login": "owner"
    }
  },
  "installation": {
    "id": 12345678
  }
}
EOF

# Calculate signature (replace YOUR_WEBHOOK_SECRET)
WEBHOOK_SECRET="your_webhook_secret_here"
SIGNATURE=$(echo -n "$(cat webhook_payload.json)" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //')

# Send the webhook
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-GitHub-Delivery: $(uuidgen)" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d @webhook_payload.json
```

### Method 3: Using Interactive Python Console

Test individual components interactively:

```python
# Start Python console
python

# Import necessary modules
from app.agents.state import *
from app.integrations.gemini_client import GeminiClient
from app.integrations.github_client import GitHubClient
import asyncio

# Create a test state
state = create_initial_workflow_state(
    repo_name="test/repo",
    pr_number=1,
    diff="your diff here",
    files=[{"filename": "test.py", "status": "modified"}]
)

# Validate it
is_valid, error = validate_workflow_state(state)
print(f"Valid: {is_valid}, Error: {error}")

# Update state
state = update_state(state, current_step="testing")
print(f"Current step: {state['current_step']}")

# Add a finding
state = add_review_finding(state, {
    "severity": "HIGH",
    "type": "security",
    "title": "Test finding",
    "description": "This is a test"
})
print(f"Findings count: {len(state['review_results'])}")

# Update metadata
state = update_metadata(state, cost_usd=0.001, tokens=100, model_call=True)
print(f"Total cost: ${state['metadata']['total_cost_usd']}")

# Test Gemini client
async def test_gemini():
    client = GeminiClient(use_flash=True)
    result = await client.analyze_code(
        "print('hello')",
        "general"
    )
    return result

# Run async test
result = asyncio.run(test_gemini())
print(f"Analysis complete: {len(result.findings)} findings")
```

### Method 4: Create Unit Tests

Create proper unit tests for the workflow:

```python
# tests/test_workflow_state.py
import pytest
from app.agents.state import (
    create_initial_workflow_state,
    update_state,
    add_review_finding,
    set_error,
    update_metadata,
    validate_workflow_state,
    validate_pr_data,
    validate_finding
)

def test_create_initial_state():
    """Test creating initial workflow state."""
    state = create_initial_workflow_state(
        repo_name="owner/repo",
        pr_number=123,
        diff="test diff",
        files=[{"name": "test.py"}]
    )

    assert state["pr_data"]["repo_name"] == "owner/repo"
    assert state["pr_data"]["pr_number"] == 123
    assert state["current_step"] == "initialized"
    assert state["error"] is None
    assert len(state["review_results"]) == 0
    assert "created_at" in state["metadata"]

def test_update_state_immutable():
    """Test that update_state doesn't mutate original."""
    state1 = create_initial_workflow_state("owner/repo", 123)
    state2 = update_state(state1, current_step="analyzing")

    assert state1["current_step"] == "initialized"
    assert state2["current_step"] == "analyzing"
    assert state1 is not state2

def test_add_review_finding():
    """Test adding findings to state."""
    state = create_initial_workflow_state("owner/repo", 123)

    finding = {
        "severity": "HIGH",
        "type": "security",
        "title": "SQL Injection",
        "description": "Potential SQL injection vulnerability"
    }

    new_state = add_review_finding(state, finding)

    assert len(state["review_results"]) == 0
    assert len(new_state["review_results"]) == 1
    assert new_state["review_results"][0]["title"] == "SQL Injection"

def test_set_error():
    """Test setting error on state."""
    state = create_initial_workflow_state("owner/repo", 123)
    error_state = set_error(state, "API call failed")

    assert error_state["error"] == "API call failed"
    assert error_state["current_step"] == "failed"

def test_update_metadata():
    """Test updating metadata."""
    state = create_initial_workflow_state("owner/repo", 123)

    # Add costs from multiple API calls
    state = update_metadata(state, cost_usd=0.001, tokens=100, model_call=True)
    state = update_metadata(state, cost_usd=0.002, tokens=200, model_call=True)

    assert state["metadata"]["total_cost_usd"] == 0.003
    assert state["metadata"]["total_tokens"] == 300
    assert state["metadata"]["model_calls"] == 2

def test_validate_workflow_state():
    """Test workflow state validation."""
    # Valid state
    state = create_initial_workflow_state("owner/repo", 123)
    is_valid, error = validate_workflow_state(state)
    assert is_valid is True
    assert error is None

    # Invalid state - missing keys
    invalid_state = {"pr_data": {}}
    is_valid, error = validate_workflow_state(invalid_state)
    assert is_valid is False
    assert "Missing required keys" in error

def test_validate_pr_data():
    """Test PR data validation."""
    # Valid PR data
    valid_data = {"repo_name": "owner/repo", "pr_number": 123}
    is_valid, error = validate_pr_data(valid_data)
    assert is_valid is True

    # Invalid repo name
    invalid_data = {"repo_name": "invalid", "pr_number": 123}
    is_valid, error = validate_pr_data(invalid_data)
    assert is_valid is False
    assert "owner/repo" in error

def test_validate_finding():
    """Test finding validation."""
    # Valid finding
    valid_finding = {
        "severity": "HIGH",
        "type": "security",
        "title": "Test",
        "description": "Test finding"
    }
    is_valid, error = validate_finding(valid_finding)
    assert is_valid is True

    # Invalid severity
    invalid_finding = {"severity": "INVALID"}
    is_valid, error = validate_finding(invalid_finding)
    assert is_valid is False
```

Run the tests:

```bash
# Install pytest if needed
pip install pytest

# Run tests
pytest tests/test_workflow_state.py -v
```

### Method 5: Manual Workflow Execution Steps

To manually replicate the webhook workflow:

1. **Fetch PR data from GitHub**:

```bash
# Set your GitHub token
export GITHUB_TOKEN="your_personal_access_token"

# Get PR details
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER

# Get PR diff
curl -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3.diff" \
  https://api.github.com/repos/OWNER/REPO/pulls/PR_NUMBER \
  > pr_diff.txt
```

2. **Create workflow state from PR data**:

```python
import json

# Load PR data from GitHub API response
with open('pr_response.json', 'r') as f:
    pr_data = json.load(f)

# Load diff
with open('pr_diff.txt', 'r') as f:
    diff = f.read()

# Create state
from app.agents.state import create_initial_workflow_state

state = create_initial_workflow_state(
    repo_name=pr_data['base']['repo']['full_name'],
    pr_number=pr_data['number'],
    diff=diff,
    files=[{
        'filename': f['filename'],
        'status': f['status'],
        'additions': f['additions'],
        'deletions': f['deletions']
    } for f in pr_data.get('files', [])]
)
```

3. **Execute analysis workflow**:

```python
from app.integrations.gemini_client import GeminiClient
from app.agents.state import update_state, add_review_finding, update_metadata

# Initialize client
client = GeminiClient(use_flash=True)

# Run analysis
analysis = await client.analyze_code(state['pr_data']['diff'], "security")

# Update state with results
for finding in analysis.findings:
    state = add_review_finding(state, {
        "severity": finding.severity,
        "type": finding.type,
        "title": finding.title,
        "description": finding.description
    })

state = update_metadata(
    state,
    cost_usd=analysis.cost_usd,
    tokens=analysis.input_tokens + analysis.output_tokens
)
```

4. **Post results back to GitHub**:

```python
from app.integrations.github_client import GitHubClient

github_client = GitHubClient()

# Format review comment
comment = f"## Code Review Results\n\n"
comment += f"Found {len(state['review_results'])} issues:\n\n"

for finding in state['review_results']:
    comment += f"### {finding['severity']}: {finding['title']}\n"
    comment += f"{finding['description']}\n\n"

# Post comment
github_client.post_pr_comment(
    repo_name=state['pr_data']['repo_name'],
    pr_number=state['pr_data']['pr_number'],
    body=comment,
    installation_id=YOUR_INSTALLATION_ID
)
```

### Expected Output

When running manual tests, you should see output like:

```
Initial state:
  Repo: owner/repo
  PR #: 123
  Current step: initialized
  Files changed: 1

[Step 1] Analyzing code for security issues...

[Step 2] Analysis complete!
  Findings: 3
  Total cost: $0.0023
  Total tokens: 1543

[Step 3] Review Results:

  Finding #1:
    Severity: HIGH
    Type: security
    Title: SQL Injection Vulnerability
    Description: Direct string interpolation in SQL query
    Location: app/main.py:13
    Recommendation: Use parameterized queries

  Finding #2:
    Severity: MEDIUM
    Type: best_practices
    Title: Missing Error Handling
    Description: No exception handling for database operations
    Location: app/main.py:10
    Recommendation: Add try-except block

  Finding #3:
    Severity: LOW
    Type: style
    Title: Missing Type Hints
    Description: Function parameters lack type annotations
    Location: app/main.py:10
    Recommendation: Add type hints

[Step 4] Generating summary...

Code Review Summary for PR #123

Total Issues Found: 3
- Critical: 0
- High: 1
- Medium: 1
- Low: 1

Analysis Cost: $0.0023
Tokens Used: 1543
Model: gemini-2.5-flash-lite

[Step 5] Workflow completed!
  Final state: completed
  Duration: 2026-01-07T10:30:15.123456 -> 2026-01-07T10:30:18.789012
```

## Testing LangGraph Workflow

The LangGraph workflow orchestrates the entire code review process with conditional routing and error handling. Here's how to test it:

### Understanding the Workflow

The workflow consists of 8 nodes with conditional routing:

```
START → FETCH_PR → REVIEW_CODE → CLASSIFY_SEVERITY → POST_REVIEW → CHECK_CRITICAL
                                                                            ↓
                                                          [Has Critical Issues?]
                                                           ↙            ↘
                                                   REQUEST_APPROVAL      END
                                                          ↓
                                                         END
```

### Method 1: Visualize Workflow

View the complete workflow structure:

```bash
# Visualize workflow graph
python -m app.workflows.code_review_workflow

# Output shows ASCII diagram and workflow metadata
```

### Method 2: Execute Workflow with Test Data

Test the complete workflow without GitHub webhooks:

```python
# test_langgraph_workflow.py
import asyncio
from app.workflows.executor import execute_code_review_workflow
from app.agents.state import create_initial_workflow_state

async def test_full_workflow():
    """Test complete LangGraph workflow execution."""

    # Create test diff with intentional security issue
    test_diff = """
diff --git a/app/auth.py b/app/auth.py
index 123..456 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -10,7 +10,7 @@ def authenticate(username, password):
     # Authenticate user
-    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
-    cursor.execute(query)
+    query = "SELECT * FROM users WHERE username = ? AND password = ?"
+    cursor.execute(query, (username, password))

     user = cursor.fetchone()
     return user
"""

    print("=" * 70)
    print("Testing LangGraph Code Review Workflow")
    print("=" * 70)
    print()

    # Execute workflow
    # Note: This will fail at GitHub API calls without proper credentials
    # For full testing, mock the GitHub client
    final_state = await execute_code_review_workflow(
        repo_name="test/security-fixes",
        pr_number=42,
        installation_id=0,  # Test mode
        diff=test_diff,
        pr_title="Fix SQL injection vulnerability",
        pr_author="security-bot"
    )

    # Print results
    print("\n" + "=" * 70)
    print("Workflow Execution Results")
    print("=" * 70)

    if final_state.get("error"):
        print(f"\n❌ Workflow Failed: {final_state['error']}")
    else:
        print(f"\n✅ Workflow Completed Successfully!")
        print(f"\nCurrent Step: {final_state['current_step']}")
        print(f"Findings: {len(final_state['review_results'])}")

        # Show severity breakdown
        severity_counts = final_state['metadata'].get('severity_counts', {})
        print(f"\nSeverity Breakdown:")
        print(f"  Critical: {severity_counts.get('CRITICAL', 0)}")
        print(f"  High: {severity_counts.get('HIGH', 0)}")
        print(f"  Medium: {severity_counts.get('MEDIUM', 0)}")
        print(f"  Low: {severity_counts.get('LOW', 0)}")
        print(f"  Info: {severity_counts.get('INFO', 0)}")

        # Show cost metrics
        print(f"\nCost Metrics:")
        print(f"  Total Cost: ${final_state['metadata']['total_cost_usd']:.4f}")
        print(f"  Total Tokens: {final_state['metadata']['total_tokens']:,}")
        print(f"  Model Calls: {final_state['metadata']['model_calls']}")

        # Show workflow timing
        print(f"\nWorkflow Timing:")
        print(f"  Duration: {final_state['metadata'].get('workflow_duration_seconds', 0):.2f}s")

        # Show if approval required
        requires_approval = final_state['metadata'].get('requires_approval', False)
        print(f"\nApproval Required: {'Yes' if requires_approval else 'No'}")

        # Show individual findings
        if final_state['review_results']:
            print(f"\n" + "-" * 70)
            print("Detailed Findings:")
            print("-" * 70)

            for i, finding in enumerate(final_state['review_results'], 1):
                print(f"\n{i}. [{finding['severity']}] {finding['title']}")
                print(f"   Type: {finding['type']}")
                if finding.get('file_path'):
                    print(f"   Location: {finding['file_path']}:{finding.get('line_start', '?')}")
                print(f"   Description: {finding['description'][:100]}...")
                if finding.get('recommendation'):
                    print(f"   Fix: {finding['recommendation'][:80]}...")

# Run test
if __name__ == "__main__":
    asyncio.run(test_full_workflow())
```

Run the test:

```bash
python test_langgraph_workflow.py
```

### Method 3: Test Individual Nodes

Test each workflow node independently:

```python
# test_workflow_nodes.py
import asyncio
from app.agents.state import create_initial_workflow_state
from app.workflows.nodes import (
    start_node,
    classify_severity_node,
    check_critical_node,
)

async def test_individual_nodes():
    """Test workflow nodes independently."""

    # Create test state
    state = create_initial_workflow_state(
        repo_name="test/repo",
        pr_number=123,
        installation_id=456
    )

    # Test start node
    print("Testing start_node...")
    state = start_node(state)
    print(f"  Current step: {state['current_step']}")
    print(f"  Error: {state['error']}")
    assert state['current_step'] == 'started'
    print("  ✓ start_node passed\n")

    # Add mock findings for classification test
    state['review_results'] = [
        {"severity": "CRITICAL", "type": "security", "title": "SQL Injection"},
        {"severity": "HIGH", "type": "security", "title": "XSS Vulnerability"},
        {"severity": "MEDIUM", "type": "performance", "title": "N+1 Query"},
        {"severity": "LOW", "type": "style", "title": "Missing docstring"},
    ]

    # Test classify_severity node
    print("Testing classify_severity_node...")
    state = classify_severity_node(state)
    severity_counts = state['metadata']['severity_counts']
    print(f"  Severity counts: {severity_counts}")
    assert severity_counts['CRITICAL'] == 1
    assert severity_counts['HIGH'] == 1
    print("  ✓ classify_severity_node passed\n")

    # Test check_critical node
    print("Testing check_critical_node...")
    state = check_critical_node(state)
    requires_approval = state['metadata']['requires_approval']
    print(f"  Requires approval: {requires_approval}")
    assert requires_approval == True  # Has critical issue
    print("  ✓ check_critical_node passed\n")

    print("All node tests passed! ✅")

if __name__ == "__main__":
    asyncio.run(test_individual_nodes())
```

### Method 4: Test Conditional Routing

Test the workflow's conditional routing logic:

```python
# test_conditional_routing.py
from app.workflows.code_review_workflow import (
    should_request_approval,
    should_skip_review
)
from app.agents.state import create_initial_workflow_state

def test_routing_logic():
    """Test conditional routing functions."""

    print("Testing Conditional Routing")
    print("=" * 50)

    # Test 1: Should request approval (has critical)
    state1 = create_initial_workflow_state("test/repo", 123)
    state1['metadata']['requires_approval'] = True
    state1['metadata']['has_critical'] = True

    route = should_request_approval(state1)
    print(f"\nTest 1: Critical issues found")
    print(f"  Route: {route}")
    assert route == "request_approval"
    print("  ✓ Correctly routes to approval request\n")

    # Test 2: Should not request approval (no critical)
    state2 = create_initial_workflow_state("test/repo", 123)
    state2['metadata']['requires_approval'] = False
    state2['metadata']['has_critical'] = False

    route = should_request_approval(state2)
    print(f"Test 2: No critical issues")
    print(f"  Route: {route}")
    assert route == "end"
    print("  ✓ Correctly routes to end\n")

    # Test 3: Should skip review (no diff)
    state3 = create_initial_workflow_state("test/repo", 123)
    state3['pr_data']['diff'] = ""

    route = should_skip_review(state3)
    print(f"Test 3: No diff available")
    print(f"  Route: {route}")
    assert route == "end"
    print("  ✓ Correctly skips review\n")

    # Test 4: Should proceed with review
    state4 = create_initial_workflow_state("test/repo", 123)
    state4['pr_data']['diff'] = "some diff content"
    state4['pr_data']['files'] = [{"filename": "test.py"}]

    route = should_skip_review(state4)
    print(f"Test 4: Diff and files available")
    print(f"  Route: {route}")
    assert route == "review_code"
    print("  ✓ Correctly proceeds with review\n")

    print("All routing tests passed! ✅")

if __name__ == "__main__":
    test_routing_logic()
```

### Method 5: Test Batch Execution

Test processing multiple PRs concurrently:

```python
# test_batch_execution.py
import asyncio
from app.workflows.executor import execute_multiple_reviews

async def test_batch_processing():
    """Test batch workflow execution."""

    reviews = [
        {
            "repo_name": "test/repo1",
            "pr_number": 101,
            "installation_id": 0,
            "pr_title": "Fix security issue",
        },
        {
            "repo_name": "test/repo2",
            "pr_number": 102,
            "installation_id": 0,
            "pr_title": "Performance optimization",
        },
        {
            "repo_name": "test/repo3",
            "pr_number": 103,
            "installation_id": 0,
            "pr_title": "Code cleanup",
        },
    ]

    print("Testing Batch Execution")
    print("=" * 50)
    print(f"Processing {len(reviews)} PRs concurrently\n")

    # Execute batch with max 2 concurrent
    results = await execute_multiple_reviews(reviews, max_concurrent=2)

    print(f"\nResults:")
    successful = 0
    failed = 0

    for i, result in enumerate(results, 1):
        repo = result['pr_data']['repo_name']
        pr = result['pr_data']['pr_number']

        if result.get('error'):
            print(f"{i}. ❌ {repo}#{pr} - Failed: {result['error'][:50]}...")
            failed += 1
        else:
            findings = len(result['review_results'])
            cost = result['metadata']['total_cost_usd']
            print(f"{i}. ✅ {repo}#{pr} - {findings} findings, ${cost:.4f}")
            successful += 1

    print(f"\nSummary: {successful} successful, {failed} failed")

if __name__ == "__main__":
    asyncio.run(test_batch_processing())
```

### Method 6: Monitor Workflow Execution

Add logging to see workflow progress in real-time:

```python
# test_with_logging.py
import asyncio
import logging
from app.workflows.executor import execute_code_review_workflow, get_execution_summary

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_with_logging():
    """Test workflow with detailed logging."""

    state = await execute_code_review_workflow(
        repo_name="test/logging-demo",
        pr_number=999,
        installation_id=0,
        pr_title="Test PR with logging"
    )

    # Print execution summary
    print("\n" + get_execution_summary(state))

if __name__ == "__main__":
    asyncio.run(test_with_logging())
```

### Expected Output

When testing the workflow, you should see output like:

```
======================================================================
Testing LangGraph Code Review Workflow
======================================================================

INFO: Starting code review workflow for test/security-fixes#42
INFO: Initial state created and validated
INFO: Compiling workflow graph...
INFO: Workflow compiled and ready for execution
INFO: Executing workflow...
INFO: Starting code review workflow for test/security-fixes PR #42
INFO: Workflow started successfully
INFO: Fetching PR details for test/security-fixes#42
INFO: Starting AI code review
INFO: Code review completed: 3 findings, cost: $0.0023
INFO: Severity classification: Critical=1, High=0, Medium=2, Low=0, Info=0
INFO: Posting review comment to test/security-fixes#42
INFO: Review posted successfully
INFO: Critical check: requires_approval=True
INFO: Critical/high severity issues found - routing to approval request
INFO: Posting approval request to test/security-fixes#42
INFO: Approval request posted
INFO: Workflow completed for test/security-fixes PR #42

======================================================================
Workflow Execution Results
======================================================================

✅ Workflow Completed Successfully!

Current Step: completed
Findings: 3

Severity Breakdown:
  Critical: 1
  High: 0
  Medium: 2
  Low: 0
  Info: 0

Cost Metrics:
  Total Cost: $0.0023
  Total Tokens: 1,543
  Model Calls: 1

Workflow Timing:
  Duration: 3.45s

Approval Required: Yes

----------------------------------------------------------------------
Detailed Findings:
----------------------------------------------------------------------

1. [CRITICAL] SQL Injection Vulnerability
   Type: security
   Location: app/auth.py:13
   Description: Direct string interpolation in SQL query allows SQL injection attacks...
   Fix: Use parameterized queries with placeholders...

2. [MEDIUM] Missing Error Handling
   Type: best_practices
   Location: app/auth.py:10
   Description: Database operations lack proper error handling...
   Fix: Wrap database calls in try-except blocks...

3. [MEDIUM] Plaintext Password Storage
   Type: security
   Location: app/auth.py:13
   Description: Password appears to be compared in plaintext...
   Fix: Use password hashing with bcrypt or argon2...
```

### Troubleshooting Workflow Tests

#### Issue: GitHub API Errors

If you see GitHub API errors during testing:

```python
# Mock the GitHub client for testing
from unittest.mock import Mock, patch

@patch('app.workflows.nodes.GitHubClient')
async def test_with_mocked_github(mock_client):
    # Mock GitHub client responses
    mock_instance = Mock()
    mock_instance.get_pr_details.return_value = {
        "title": "Test PR",
        "user": {"login": "testuser"},
        "body": "Test description",
        "files": [],
        "changed_files": 0,
        "additions": 0,
        "deletions": 0,
        "head": {"sha": "abc123"}
    }
    mock_instance.get_pr_diff.return_value = test_diff
    mock_client.return_value = mock_instance

    # Now test workflow
    state = await execute_code_review_workflow(...)
```

#### Issue: Gemini API Rate Limits

If you hit rate limits:

```python
# Add delay between tests
import time

for test in tests:
    await run_test(test)
    time.sleep(2)  # Wait 2 seconds between tests
```

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
