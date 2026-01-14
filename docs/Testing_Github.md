# Testing Guide for RepoAuditor AI

This guide provides comprehensive instructions for setting up, testing, and validating the RepoAuditor AI LangGraph multi-agent workflow system.

## Table of Contents

1. [GitHub App Setup](#github-app-setup)
2. [Local Development Setup](#local-development-setup)
3. [Testing Commands](#testing-commands)
4. [Automated Testing](#automated-testing)
5. [Rate Limiting Tests](#rate-limiting-tests)
6. [Troubleshooting](#troubleshooting)

---

## 1. GitHub App Setup

### 1.1 Create GitHub App

1. **Navigate to GitHub App Settings**
   - Go to: https://github.com/settings/apps
   - Click **"New GitHub App"**

2. **Configure Basic Information**
   - **GitHub App name:** `RepoAuditor AI` (or your preferred name)
   - **Homepage URL:** Your app URL or repository URL
   - **Webhook URL:** `https://your-domain.com/webhooks/github` (or ngrok URL for local testing)
   - **Webhook secret:** Generate a secure secret (save this for `.env` file)

3. **Set Permissions**

   **Repository permissions:**
   - Contents: **Read & write** (to create branches, commit fixes)
   - Pull requests: **Read & write** (to comment, create PRs)
   - Issues: **Read & write** (to handle PR comments)
   - Metadata: **Read-only** (required)

   **Subscribe to events:**
   - Pull request
   - Pull request review
   - Pull request review comment
   - Issue comment

4. **Generate Private Key**
   - Scroll to bottom of page
   - Click **"Generate a private key"**
   - Save the downloaded `.pem` file securely
   - Place it in your project root as `github-app-private-key.pem`

5. **Note Your App ID**
   - Found at the top of the app settings page
   - Save this for the `.env` file

### 1.2 Install GitHub App on Repository

1. Go to app settings page
2. Click **"Install App"** in left sidebar
3. Select the repository to install on
4. Choose **"All repositories"** or **"Only select repositories"**
5. Click **"Install"**
6. Note the **Installation ID** from the URL (e.g., `/settings/installations/12345`)

---

## 2. Local Development Setup

### 2.1 Environment Variables

Create a `.env` file in the project root:

```env
# GitHub App Configuration
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_PATH=github-app-private-key.pem
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here

# Gemini API Configuration
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.0-flash-exp

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Feature Flags
ENABLE_CACHING=true
CACHE_TTL_SECONDS=3600
USE_MULTI_AGENT_WORKFLOW=false

# Jira Integration (Optional)
JIRA_BASE_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
```

### 2.2 Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2.3 Running Locally with ngrok

For local development, use ngrok to expose your local server to GitHub webhooks:

1. **Install ngrok**
   ```bash
   # Download from https://ngrok.com/download
   # Or use package manager
   ```

2. **Start ngrok**
   ```bash
   ngrok http 8000
   ```

3. **Copy the HTTPS URL**
   - Example: `https://abc123.ngrok.io`

4. **Update GitHub App Webhook URL**
   - Go to GitHub App settings
   - Update **Webhook URL** to: `https://abc123.ngrok.io/webhooks/github`
   - Save changes

5. **Start the Application**
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```

6. **Verify Setup**
   - Visit: http://localhost:8000/health
   - Should return: `{"status": "healthy"}`

---

## 3. Testing Commands

### 3.1 Create Test Repository

1. **Create a new repository** or use an existing one
2. **Add test code with intentional issues:**

#### Example: Security Vulnerabilities (`test_security.py`)

```python
import sqlite3

def get_user_by_id(user_id):
    # SQL Injection vulnerability
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"  # VULNERABLE
    cursor.execute(query)
    return cursor.fetchone()

# Hardcoded secret
API_KEY = "sk-1234567890abcdef"  # VULNERABLE

def fetch_data(url):
    import requests
    # No input validation
    response = requests.get(url)  # Path traversal risk
    return response.text
```

#### Example: Code Quality Issues (`messy_code.py`)

```python
def calculate(a,b,c):  # Poor formatting
    result=a+b*c-a/b  # No spaces
    if result>100:
        print("Big")
    else:
        print("Small")
    return result

# Unused imports
import os
import sys
import json
```

### 3.2 Test Each Command

#### `/fix-security-issues`

**Purpose:** Scan for security vulnerabilities, generate fixes, test, and create PR.

**Steps:**
1. Create a PR with `test_security.py`
2. Comment on the PR: `/fix-security-issues`
3. **Expected behavior:**
   - Bot scans code for security issues
   - Generates fixes for SQL injection, hardcoded secrets
   - Creates test branch
   - Runs tests
   - Creates new PR with fixes (if tests pass)
4. **Verify:**
   - Bot comment lists found issues
   - New PR created with fixed code
   - Tests passed

#### `/comprehensive-review`

**Purpose:** Multi-dimensional analysis (security + performance + quality).

**Steps:**
1. Create a PR with multiple issues
2. Comment: `/comprehensive-review`
3. **Expected behavior:**
   - Parallel analysis: security, performance, quality
   - Comprehensive markdown report posted
   - Optionally creates Jira tickets
4. **Verify:**
   - Report has 3 sections (security, performance, quality)
   - Severity summary included
   - Jira tickets created (if enabled)

#### `/auto-fix`

**Purpose:** Detect bugs, generate fixes AND tests, create PR.

**Steps:**
1. Create a PR with buggy code
2. Comment: `/auto-fix`
3. **Expected behavior:**
   - Detects bugs (type errors, logic errors, etc.)
   - Generates fixes for each bug
   - Generates test cases for fixes
   - Creates PR with fixes + tests
4. **Verify:**
   - Bot lists detected bugs
   - New PR includes both fixes and tests
   - Tests are runnable

#### `/optimize`

**Purpose:** Auto-format and lint code, rollback if tests fail.

**Steps:**
1. Create a PR with unformatted code
2. Comment: `/optimize`
3. **Expected behavior:**
   - Detects primary language
   - Applies formatter (black, prettier, etc.)
   - Applies linter
   - Runs tests
   - Rolls back if tests fail
4. **Verify:**
   - Code is formatted correctly
   - Linter issues fixed
   - Tests pass (or rollback occurred)

#### `/incremental-review`

**Purpose:** Track reviewed files, only review new/changed files.

**Steps:**
1. Create PR, comment: `/incremental-review`
2. Bot reviews all files
3. Add more commits to the same PR
4. Comment: `/incremental-review` again
5. **Expected behavior:**
   - Bot only reviews new/changed files
   - References previous feedback
6. **Verify:**
   - Bot message says "Reviewing X new files"
   - Previous files skipped
   - Review history saved to `data/incremental_reviews/`

---

## 4. Automated Testing

### 4.1 Running Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_rate_limiter.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

### 4.2 Running Integration Tests

```bash
# Run integration tests (requires mocked clients)
pytest tests/integration/ -v

# Run end-to-end workflow tests
pytest tests/integration/test_workflows_e2e.py -v
```

### 4.3 Test Coverage Goals

- **Overall coverage:** >80%
- **Critical modules:**
  - `rate_limiter.py`: >95%
  - Workflow nodes: >85%
  - Specialized agents: >80%

---

## 5. Rate Limiting Tests

### 5.1 Test User Limit (5 commands/hour)

**Steps:**
1. Create a PR
2. Comment with any command 5 times in a row
3. On the 6th attempt, expect rate limit error

**Expected Response:**
```markdown
## ⏱️ Rate Limit Exceeded

You've hit the **user rate limit** of **5 commands per hour**.

### Current Usage
- **User (your-username):** 5/5 commands this hour (remaining: 0)
- **PR (#123):** 5/10 commands total (remaining: 5)
- **Repository (owner/repo):** 5/50 commands today (remaining: 45)
```

### 5.2 Test PR Limit (10 commands total)

**Steps:**
1. Create a PR
2. Have 10 different users comment commands
3. 11th user should get rate limit error

### 5.3 Test Repository Limit (50 commands/day)

**Steps:**
1. Across multiple PRs, issue 50 commands
2. 51st command should trigger repo rate limit

### 5.4 Verify Rate Limit Cleanup

**Check:**
1. Inspect `data/rate_limits.json`
2. Verify old entries (>1 hour for users) are removed
3. Verify cleanup runs automatically

---

## 6. Troubleshooting

### 6.1 Common Errors

#### **Error: GitHub API returns 403 Forbidden**

**Cause:** Insufficient permissions or installation issues

**Solution:**
- Verify GitHub App has correct permissions
- Check installation is active
- Ensure private key is correct
- Verify `GITHUB_APP_ID` matches app settings

#### **Error: Webhook signature verification failed**

**Cause:** Webhook secret mismatch

**Solution:**
- Verify `GITHUB_WEBHOOK_SECRET` matches GitHub App settings
- Check secret has no extra whitespace
- Try regenerating secret

#### **Error: Gemini API key invalid**

**Cause:** API key incorrect or missing

**Solution:**
- Verify `GEMINI_API_KEY` starts with correct prefix
- Check API key has required permissions
- Generate new key from Google AI Studio

#### **Error: Rate limit file corruption**

**Cause:** Concurrent writes or JSON errors

**Solution:**
- Delete `data/rate_limits.json`
- Restart application (will recreate file)
- Check file permissions

#### **Error: Workflow state validation failed**

**Cause:** Missing required state fields

**Solution:**
- Check state initialization in command handlers
- Verify all required fields present
- Review workflow_states.py schemas

### 6.2 Debugging Tips

1. **Enable Debug Logging**
   ```env
   LOG_LEVEL=DEBUG
   ```

2. **Check Application Logs**
   - Look for ERROR or WARNING messages
   - Check timestamps to correlate with webhook events

3. **Inspect State Files**
   - Check `data/rate_limits.json` for rate limit state
   - Check `data/incremental_reviews/` for review history

4. **Test Webhook Delivery**
   - Go to GitHub App → Advanced → Recent Deliveries
   - Click on failed delivery to see error details
   - Use "Redeliver" to retry

5. **Validate JSON Files**
   ```bash
   # Check JSON syntax
   python -m json.tool data/rate_limits.json
   ```

6. **Test GitHub Authentication**
   ```python
   from app.integrations.github_client import GitHubClient

   client = GitHubClient()
   # Test authentication
   info = client.get_installation_info(installation_id)
   print(info)
   ```

### 6.3 Performance Issues

**If workflows are slow:**
- Check Gemini API response times
- Monitor token usage (large diffs take longer)
- Consider increasing `max_tokens` in config
- Check network latency to GitHub/Gemini

**If rate limits are hit frequently:**
- Review per-user limits (may need adjustment)
- Check for duplicate webhook events
- Verify cleanup is running

### 6.4 Getting Help

1. **Check Logs:** Review application logs for detailed error messages
2. **Inspect State:** Check state files in `data/` directory
3. **GitHub Webhook Logs:** Check recent deliveries in GitHub App settings
4. **Test Locally:** Use ngrok to debug webhook processing
5. **Report Issues:** Create issue in repository with:
   - Error message
   - Steps to reproduce
   - Relevant logs
   - Configuration (redact secrets!)

---

## 7. Testing Checklist

Use this checklist to ensure complete testing coverage:

### Setup
- [ ] GitHub App created and configured
- [ ] Private key generated and saved
- [ ] Webhook URL configured (ngrok for local)
- [ ] Environment variables set in `.env`
- [ ] Dependencies installed
- [ ] Application starts without errors
- [ ] Health endpoint returns 200 OK

### Commands
- [ ] `/fix-security-issues` - Scans, fixes, tests, creates PR
- [ ] `/comprehensive-review` - Parallel analysis, report posted
- [ ] `/auto-fix` - Detects bugs, generates fixes + tests
- [ ] `/optimize` - Formats, lints, tests, rolls back on failure
- [ ] `/incremental-review` - Tracks files, skips reviewed

### Rate Limiting
- [ ] User limit (5/hour) enforced
- [ ] PR limit (10 total) enforced
- [ ] Repo limit (50/day) enforced
- [ ] Rate limit error messages clear
- [ ] Cleanup removes old entries
- [ ] Different users have independent limits

### Error Handling
- [ ] Invalid commands show helpful error
- [ ] GitHub API failures handled gracefully
- [ ] Gemini API failures handled gracefully
- [ ] Webhook signature failures rejected
- [ ] State validation errors logged

### Automated Tests
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Test coverage >80%
- [ ] No flaky tests
- [ ] Tests run in CI/CD

### Documentation
- [ ] README updated with new commands
- [ ] This testing guide is accurate
- [ ] Agent.md architecture doc complete
- [ ] Code has inline comments
- [ ] All APIs have docstrings

---

## Congratulations!

If you've completed this testing guide, your RepoAuditor AI system is fully tested and ready for production use. For architecture details and extending the system, see [Agent.md](./Agent.md).

## Next Steps

1. Deploy to production (Cloud Run, AWS, etc.)
2. Monitor rate limits and adjust as needed
3. Collect feedback from users
4. Add more specialized agents as needed
5. Integrate with additional tools (Jira, Slack, etc.)

---

**Questions or Issues?** Check the troubleshooting section or create an issue in the repository.
