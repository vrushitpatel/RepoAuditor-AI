# Troubleshooting Webhook Errors

## "Method Not Allowed" Error (405)

If you're seeing a "Method not allowed" error when GitHub sends webhooks, follow these steps to diagnose and fix the issue.

### Step 1: Verify Webhook URL in GitHub

The most common cause is an **incorrect webhook URL** in your GitHub App settings.

**Correct URL format:**
```
https://your-domain.com/webhooks/github
```

**Common mistakes:**
- ❌ `https://your-domain.com/github` (missing `/webhooks/`)
- ❌ `https://your-domain.com/webhook/github` (singular instead of plural)
- ❌ `https://your-domain.com/` (missing entire path)

**How to check:**
1. Go to your GitHub App settings
2. Look for the "Webhook URL" field
3. Verify it ends with `/webhooks/github`
4. For local testing with ngrok: `https://abc123.ngrok.io/webhooks/github`

### Step 2: Check Application is Running

```bash
# Test if the application is accessible
curl http://localhost:8000/

# Should return:
# {
#   "name": "RepoAuditor AI",
#   "version": "1.0.0",
#   "status": "running",
#   ...
# }
```

### Step 3: Test the Webhook Endpoint Directly

```bash
# Test GET (should return endpoint info)
curl http://localhost:8000/webhooks/github

# Expected response:
# {
#   "endpoint": "/webhooks/github",
#   "method": "POST",
#   "description": "GitHub webhook receiver",
#   ...
# }
```

### Step 4: Check GitHub Webhook Deliveries

1. Go to your GitHub App settings
2. Navigate to **"Advanced" → "Recent Deliveries"**
3. Click on the failed delivery
4. Look at the **Response** tab

**What to look for:**
- **Status Code 405**: Wrong URL or HTTP method
- **Status Code 401**: Signature verification failed
- **Status Code 404**: Endpoint not found (wrong URL)
- **Status Code 500**: Application error
- **Connection refused**: Application not running

### Step 5: Enable Debug Logging

Edit your `.env` file:

```env
LOG_LEVEL=DEBUG
```

Restart the application and check the logs for detailed error messages.

### Step 6: Verify Application Configuration

```bash
# Check health endpoint
curl http://localhost:8000/health

# Should show:
# {
#   "status": "healthy",
#   "github_app_configured": true,
#   "gemini_configured": true,
#   ...
# }
```

### Step 7: Test with the Test Script

Use the provided `test_webhook.py` script to simulate GitHub webhooks locally:

```bash
python test_webhook.py
```

**Expected output if working:**
```
=== Testing Ping Event ===
Status: 200
Response: {'status': 'received', 'message': 'pong', ...}
```

**If you see "Signature verification failed":**
- Check that your `.env` file has the correct `GITHUB_WEBHOOK_SECRET`
- Make sure the secret in `.env` matches the secret in GitHub App settings
- The secret must be identical (case-sensitive)

## Common Issues and Solutions

### Issue: "Signature verification failed"

**Cause:** The webhook secret in your `.env` doesn't match the secret configured in GitHub.

**Solution:**
1. Generate a new secret:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. Update GitHub App settings with the new secret
3. Update `.env` file:
   ```env
   GITHUB_WEBHOOK_SECRET=your_new_secret_here
   ```

4. Restart the application

### Issue: "Missing X-GitHub-Event header"

**Cause:** The request is not coming from GitHub or is malformed.

**Solution:**
- Verify you're testing with the correct endpoint: `POST /webhooks/github`
- If using curl/Postman, make sure to include the header:
  ```bash
  curl -X POST http://localhost:8000/webhooks/github \
    -H "X-GitHub-Event: ping" \
    -H "X-Hub-Signature-256: sha256=..." \
    -H "Content-Type: application/json" \
    -d '{"zen": "test"}'
  ```

### Issue: Application receives webhook but doesn't process it

**Cause:** Event type might not be supported or an error occurred in processing.

**Check logs for:**
```
INFO: Received pull_request event
INFO: Pull request opened: owner/repo#1
INFO: Triggering code review for PR #1
```

**If you see:**
```
INFO: Ignoring unsupported event type: <event>
```

The event type is not implemented yet. Supported events:
- `pull_request` (opened, synchronize, reopened)
- `issue_comment` (created)
- `pull_request_review_comment` (created)
- `ping`

### Issue: Commands (/explain, /review) not working

**Cause 1:** Command must be at the start of the comment.

**Correct:**
```
/explain
```

**Incorrect:**
```
Can you /explain this?
```

**Cause 2:** GitHub App doesn't have permission to receive issue comments.

**Solution:**
1. Go to GitHub App settings → **Permissions & events**
2. Under **Repository permissions**, verify:
   - **Issues**: Read & write
   - **Pull requests**: Read & write
3. Under **Subscribe to events**, verify:
   - ✅ Pull request
   - ✅ Issue comment
   - ✅ Pull request review comment

### Issue: Webhook delivers but review doesn't post

**Possible causes:**
1. **Background task failed** - Check application logs for errors
2. **GitHub API authentication failed** - Verify `GITHUB_APP_ID` and `GITHUB_PRIVATE_KEY_PATH`
3. **Gemini API failed** - Verify `GEMINI_API_KEY` is valid
4. **Rate limiting** - Check metrics: `curl http://localhost:8000/webhooks/metrics`

**Debug steps:**
```bash
# 1. Check if webhooks are being received
curl http://localhost:8000/webhooks/metrics

# Should show increments in counters

# 2. Check health status
curl http://localhost:8000/health

# 3. Check application logs
docker-compose logs -f app  # if using Docker
# or check console output if running locally
```

## Quick Checklist

Before asking for help, verify:

- [ ] Application is running: `curl http://localhost:8000/health`
- [ ] Webhook URL is correct: `https://your-domain.com/webhooks/github`
- [ ] Webhook secret matches between GitHub App and `.env`
- [ ] GitHub App is installed on the repository
- [ ] GitHub App has required permissions (Pull requests, Issues)
- [ ] GitHub App is subscribed to correct events
- [ ] For local testing: ngrok tunnel is active
- [ ] Logs show webhook being received
- [ ] Metrics show event counters incrementing

## Still Having Issues?

1. **Enable debug logging** in `.env`:
   ```env
   LOG_LEVEL=DEBUG
   ```

2. **Check GitHub webhook delivery logs** in GitHub App settings

3. **Run the test script** to isolate issues:
   ```bash
   python test_webhook.py
   ```

4. **Check application logs** for stack traces

5. **Test each component individually**:
   - Health check: `curl http://localhost:8000/health`
   - Webhook endpoint: `curl http://localhost:8000/webhooks/github`
   - Metrics: `curl http://localhost:8000/webhooks/metrics`

## Contact

If you've tried all the above and still have issues:

1. Include the following information:
   - Error message from GitHub webhook delivery
   - Application logs (with DEBUG level)
   - Output from `curl http://localhost:8000/health`
   - Output from `python test_webhook.py`

2. Check the GitHub repository issues for similar problems

3. Create a new issue with the template above
