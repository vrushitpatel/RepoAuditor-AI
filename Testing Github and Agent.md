# Testing GitHub and Agent - Manual Testing Guide

This guide provides step-by-step instructions to manually test the RepoAuditor AI system with GitHub integration and the multi-agent workflow.

## Prerequisites

Before testing, ensure you have:

- ✅ Python 3.10+ installed
- ✅ Virtual environment activated
- ✅ All dependencies installed (`pip install -r requirements.txt`)
- ✅ GitHub App configured (see `GITHUB_APP_SETUP.md`)
- ✅ Environment variables configured (`.env` file)
- ✅ ngrok or similar tunneling tool for webhook testing
- ✅ Test GitHub repository with write access

---

## Part 1: Environment Setup

### Step 1: Verify Environment Configuration

```bash
# Navigate to project directory
cd "P:\[01] AI Application\AI Code Assistant + Reviewer\[02] Source Code\RepoAuditor AI\repoauditor-ai"

# Activate virtual environment
source venv/Scripts/activate  # Windows
# OR
source venv/bin/activate      # Linux/Mac

# Verify .env file exists and contains required variables
cat .env
```

Required environment variables:
- `GITHUB_APP_ID` - Your GitHub App ID
- `GITHUB_PRIVATE_KEY_PATH` - Path to private key file
- `GITHUB_WEBHOOK_SECRET` - Webhook secret for signature verification
- `GOOGLE_API_KEY` - Gemini API key

### Step 2: Start the Application

```bash
# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Verify Application Health

In a new terminal:

```bash
# Check health endpoint
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-13T..."
}
```

---

## Part 2: Webhook Testing with ngrok

### Step 4: Start ngrok Tunnel

```bash
# In a new terminal
ngrok http 8000
```

Expected output:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:8000
```

**Copy the https URL** - you'll need it for GitHub webhook configuration.

### Step 5: Configure GitHub Webhook

1. Go to your test repository on GitHub
2. Settings → Webhooks → Add webhook
3. Configure:
   - **Payload URL**: `https://abc123.ngrok.io/webhooks/github`
   - **Content type**: `application/json`
   - **Secret**: (value from `GITHUB_WEBHOOK_SECRET`)
   - **Events**: Select these:
     - ✅ Pull requests
     - ✅ Issue comments
     - ✅ Pull request review comments
4. Click "Add webhook"

### Step 6: Test Webhook Delivery

1. GitHub will send a "ping" event
2. Check ngrok terminal for incoming request
3. Check FastAPI logs for:
   ```
   INFO: Received ping event from GitHub
   ```
4. In GitHub, check webhook "Recent Deliveries" tab
5. Verify response is `200 OK`

---

## Part 3: Testing PR Code Review (Automatic)

### Step 7: Create a Test Pull Request

1. In your test repository, create a new branch:
   ```bash
   git checkout -b test-security-fix
   ```

2. Create a test file with a security issue:
   ```python
   # test_security.py
   def authenticate(username, password):
       # SQL injection vulnerability
       query = f"SELECT * FROM users WHERE username = '{username}'"
       cursor.execute(query)
       return cursor.fetchone()
   ```

3. Commit and push:
   ```bash
   git add test_security.py
   git commit -m "Add authentication function"
   git push origin test-security-fix
   ```

4. Create a Pull Request on GitHub

### Step 8: Verify Automatic Code Review

**Expected Behavior:**
1. Webhook is received by your server
2. FastAPI logs show:
   ```
   INFO: Received pull_request event
   INFO: Triggering code review for PR #1
   INFO: Starting code review workflow
   ```
3. Multi-agent workflow routes to code reviewer
4. AI analyzes the code
5. Review comment is posted on the PR

**What to Check:**
- ✅ PR has a comment from your bot
- ✅ Comment contains code review findings
- ✅ SQL injection vulnerability is identified
- ✅ Comment includes metadata (tokens, cost, duration)

**Example Expected Output:**
```markdown
## 🔍 Code Review Summary

Found 3 issues requiring attention.

### 🔴 Critical Issues (1)

**SQL Injection Vulnerability**
- File: `test_security.py`
- Line: 3
- Severity: CRITICAL

The SQL query construction uses string interpolation with user input...

---
*🔢 Tokens: 1,234 • 💰 Cost: $0.0012 • ⏱️ Duration: 4.5s*
```

---

## Part 4: Testing Commands

### Step 9: Test `/help` Command

1. Go to your test PR
2. Add a comment: `/help`
3. Wait for response

**Expected Output:**
```markdown
## 📚 Available Commands

- `/help` - Show this help message
- `/explain [file]` - Explain code changes
- `/review` - Trigger code review
- `/generate-ci [type]` - Generate CI/CD workflows

Examples:
- `/explain` - Explain all changes
- `/explain test_security.py` - Explain specific file
- `/generate-ci test` - Generate test workflow
```

### Step 10: Test `/explain` Command

**Test 10a: Explain entire PR**
1. Comment: `/explain`
2. Wait for response

**Expected Output:**
```markdown
## 📖 Code Explanation

This PR adds an authentication function...

### Changes Overview
- Added `test_security.py` with authentication logic
- Implements user login verification

### Key Implementation Details
...
```

**Test 10b: Explain specific file**
1. Comment: `/explain test_security.py`
2. Wait for response

**Expected Output:**
```markdown
## 📖 Explanation: test_security.py

This file contains authentication logic...
```

**Test 10c: Explain with invalid file**
1. Comment: `/explain nonexistent.py`
2. Wait for response

**Expected Output:**
```markdown
## ❌ Error

File not found: nonexistent.py
```

### Step 11: Test `/generate-ci` Command

**Test 11a: Generate all workflows**
1. Comment: `/generate-ci all`
2. Wait for response

**Expected Output:**
```markdown
## CI/CD Workflows Generated

### Test Workflow
```yaml
name: Run Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      ...
```

### Lint Workflow
...
```

**Test 11b: Generate specific workflow**
1. Comment: `/generate-ci test`
2. Wait for response

**Expected Output:**
- Only test workflow is generated

### Step 12: Test `/review` Command

1. Comment: `/review`
2. Wait for response

**Expected Output:**
- Same as automatic code review
- Fresh analysis performed
- New comment posted

### Step 13: Test Unknown Command

1. Comment: `/unknown-command`
2. Wait for response

**Expected Output:**
```markdown
## ❌ Unknown Command

Command not recognized: unknown-command

Available commands:
- /help
- /explain [file]
- /review
- /generate-ci [type]

Use `/help` for more information.
```

---

## Part 5: Testing Multi-Agent Workflow Routing

### Step 14: Verify Routing Logs

Check your FastAPI server logs to verify correct routing:

**For PR opened:**
```
INFO: Event type: pr_opened
INFO: Routing to code reviewer (PR event)
INFO: Executing code review
```

**For /explain command:**
```
INFO: Event type: command_created
INFO: Command detected: explain
INFO: Routing to explainer (command)
INFO: Executing explainer
```

**For /generate-ci command:**
```
INFO: Event type: command_created
INFO: Command detected: generate-ci
INFO: Routing to CI/CD generator (command)
INFO: Executing CI/CD generator
```

---

## Part 6: Error Handling Tests

### Step 15: Test Rate Limiting

1. Post 5 commands rapidly:
   ```
   /help
   /explain
   /review
   /generate-ci
   /help
   ```

2. Verify:
   - All commands are processed
   - Responses may be delayed
   - No crashes occur

### Step 16: Test Invalid PR Context

1. Delete the test branch
2. Try to comment `/explain`
3. Verify:
   - Error message is posted
   - Application doesn't crash

### Step 17: Test Large PR

1. Create a PR with 20+ files
2. Wait for automatic review
3. Verify:
   - Review completes (may take longer)
   - Response is posted
   - No timeout errors

---

## Part 7: Performance Testing

### Step 18: Measure Response Times

For each command, measure:
- **Webhook received** → **Processing started**: < 1s
- **Processing started** → **AI analysis complete**: 3-10s
- **AI analysis complete** → **Response posted**: < 2s
- **Total**: 5-15s depending on PR size

### Step 19: Verify Metadata

Check each response includes:
- ✅ Token count
- ✅ Cost (USD)
- ✅ Duration (seconds)
- ✅ Model name

---

## Part 8: Clean Up

### Step 20: Stop Services

```bash
# Stop FastAPI server
Ctrl+C

# Stop ngrok
Ctrl+C

# Deactivate virtual environment
deactivate
```

### Step 21: Review Logs

```bash
# Check for any errors
grep ERROR logs/app.log

# Check for warnings
grep WARNING logs/app.log
```

---

## Troubleshooting

### Issue: Webhook not received

**Check:**
1. ngrok is running
2. FastAPI server is running
3. Webhook URL in GitHub is correct
4. Webhook secret matches

**Solution:**
```bash
# Verify webhook secret
echo $GITHUB_WEBHOOK_SECRET

# Check ngrok status
curl http://localhost:4040/api/tunnels
```

### Issue: Commands not recognized

**Check:**
1. Command starts with `/`
2. Command is in PR comment (not review comment)
3. Bot has permissions

**Solution:**
- Try `/help` to verify bot is responding
- Check FastAPI logs for command detection

### Issue: Bot not responding

**Check:**
1. GitHub App installed on repository
2. `.env` file configured correctly
3. GitHub authentication working

**Solution:**
```bash
# Test GitHub authentication
python -c "from app.integrations.github_client import GitHubClient; client = GitHubClient(); print('Auth OK')"
```

### Issue: AI responses are slow

**Check:**
1. Internet connection
2. Gemini API rate limits
3. PR size (very large PRs take longer)

**Solution:**
- Check Gemini API quota
- Reduce PR size for testing
- Consider using flash model for faster responses

---

## Success Criteria

Your testing is successful if:

- ✅ PR opened triggers automatic code review
- ✅ All commands (`/help`, `/explain`, `/review`, `/generate-ci`) work
- ✅ Error handling works for invalid commands and files
- ✅ Responses include metadata (tokens, cost, duration)
- ✅ Multi-agent workflow routes correctly
- ✅ No crashes or unhandled exceptions
- ✅ Logs are clean (no ERROR entries)

---

## Next Steps

After successful testing:

1. **Deploy to Production**
   - Set up production webhook URL
   - Configure production secrets
   - Monitor logs and metrics

2. **Add More Agents**
   - Security scanner
   - Performance analyzer
   - Documentation generator

3. **Improve Responses**
   - Customize prompt templates
   - Add more code patterns
   - Enhance error messages

---

## Additional Resources

- **Documentation**: See `COMMAND_ROUTER.md` for router details
- **GitHub Setup**: See `GITHUB_APP_SETUP.md` for authentication
- **CI/CD**: See `HOW_CICD_WORKS.md` for workflow generation
- **Code**: See `Commands.md` for implementation details

---

**Happy Testing! 🎉**
