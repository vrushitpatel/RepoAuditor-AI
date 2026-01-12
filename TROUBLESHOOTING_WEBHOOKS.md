# Troubleshooting Webhook Issues - Not Receiving Responses

This guide helps diagnose and fix issues when GitHub comments (like `/help`) don't trigger responses from the bot.

## Quick Diagnosis Checklist

Run through these checks in order:

- [ ] FastAPI application is running
- [ ] ngrok tunnel is active and forwarding to correct port
- [ ] GitHub webhook is configured with ngrok URL
- [ ] GitHub App is installed on the repository
- [ ] Webhook secret matches in both GitHub and .env
- [ ] GitHub webhook is delivering events successfully

---

## Step 1: Verify FastAPI Application is Running

### Check if Application is Running

```bash
# Test health endpoint
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "github_app_configured": true,
  "gemini_configured": true,
  "jira_enabled": false,
  "caching_enabled": true
}
```

### If Application is NOT Running

```bash
# Start the application
cd "P:\[01] AI Application\AI Code Assistant + Reviewer\[02] Source Code\RepoAuditor AI\repoauditor-ai"

# Activate virtual environment (if using one)
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
# source venv/bin/activate

# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Check for Startup Errors

Look for these in the terminal output:
- ❌ `ModuleNotFoundError` → Missing dependencies, run `pip install -r requirements.txt`
- ❌ `GITHUB_APP_ID not found` → Missing environment variables in `.env`
- ❌ `FileNotFoundError: private-key.pem` → GitHub App private key not found
- ❌ `GEMINI_API_KEY not found` → Missing Gemini API key

### Verify Environment Variables

```bash
# Check .env file exists
ls .env

# Verify required variables are set
cat .env | grep GITHUB_APP_ID
cat .env | grep GITHUB_WEBHOOK_SECRET
cat .env | grep GITHUB_PRIVATE_KEY_PATH
cat .env | grep GEMINI_API_KEY
```

**Required Variables:**
- `GITHUB_APP_ID` - Your GitHub App ID (numeric)
- `GITHUB_WEBHOOK_SECRET` - Secret for verifying webhooks
- `GITHUB_PRIVATE_KEY_PATH` - Path to your `.pem` file
- `GEMINI_API_KEY` - Google Gemini API key

---

## Step 2: Verify ngrok Tunnel is Active

### Check ngrok Status

In your ngrok terminal, you should see:
```
Session Status                online
Account                       your-account
Region                        United States (us)
Forwarding                    https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:8000
```

### Test ngrok URL

```bash
# Replace with YOUR ngrok URL
curl https://your-ngrok-url.ngrok-free.app/health
```

**Expected:** Same response as localhost health check

**If Failed:**
- ❌ `Could not resolve host` → ngrok tunnel is down
- ❌ `Connection refused` → FastAPI app is not running
- ❌ `502 Bad Gateway` → Port mismatch between ngrok and FastAPI

### Start ngrok if Not Running

```bash
# Forward port 8000 to ngrok
ngrok http 8000
```

**Copy the HTTPS URL** (e.g., `https://abcd-1234-5678.ngrok-free.app`)

---

## Step 3: Verify GitHub Webhook Configuration

### Go to GitHub App Settings

1. Navigate to: `https://github.com/settings/apps`
2. Click on your app (RepoAuditor AI)
3. Scroll to **Webhook** section

### Check Webhook URL

**Should be:** `https://your-ngrok-url.ngrok-free.app/webhooks/github`

⚠️ **Common Mistakes:**
- Using `http://` instead of `https://`
- Missing `/webhooks/github` path
- Using an old ngrok URL (ngrok URLs change each restart)
- Using `localhost` instead of ngrok URL

### Check Webhook Secret

The **Webhook secret** in GitHub App settings **MUST MATCH** `GITHUB_WEBHOOK_SECRET` in your `.env` file.

**To Generate a New Secret:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

1. Copy the generated secret
2. Update GitHub App webhook secret
3. Update `.env` file with same secret
4. Restart FastAPI application

### Check SSL Verification

**Should be:** ✓ Enable SSL verification

### Check Content Type

**Should be:** `application/json`

### Check Active

**Should be:** ✓ Active checkbox is checked

### Save Changes

Click **"Save changes"** button at bottom of page.

---

## Step 4: Verify GitHub App Installation

### Check App is Installed on Repository

1. Go to your repository: `https://github.com/your-username/your-repo`
2. Navigate to **Settings** → **Integrations** → **GitHub Apps**
3. Verify your app (RepoAuditor AI) is listed

### If Not Installed

1. Go to: `https://github.com/settings/apps/your-app-name/installations`
2. Click **"Install App"**
3. Select your repository
4. Click **"Install"**

### Check App Permissions

Your app should have these permissions:

**Repository Permissions:**
- ✓ **Pull requests:** Read & Write
- ✓ **Issues:** Read & Write
- ✓ **Repository contents:** Read-only
- ✓ **Repository metadata:** Read-only

**Subscribe to Events:**
- ✓ Pull request
- ✓ Issue comment
- ✓ Pull request review comment

**If permissions are missing:**
1. Update permissions in GitHub App settings
2. Users will need to accept the permission update

---

## Step 5: Test Webhook Delivery in GitHub

### View Recent Deliveries

1. Go to GitHub App settings: `https://github.com/settings/apps/your-app-name`
2. Scroll to **Webhook** section
3. Click **"Recent Deliveries"**

### Check for Deliveries

**If NO deliveries appear:**
- GitHub is not sending webhooks
- Webhook might be disabled
- Events might not be subscribed

**If deliveries appear with red X (failed):**
Click on a delivery to see details:

#### Common Errors:

**❌ "Couldn't resolve host"**
- ngrok URL is invalid or expired
- Update webhook URL with current ngrok URL

**❌ "Connection refused"**
- FastAPI app is not running on specified port
- Start the application

**❌ "502 Bad Gateway"**
- Port mismatch between ngrok and FastAPI
- Verify both use port 8000

**❌ "401 Unauthorized"**
- Webhook signature verification failed
- Webhook secret mismatch between GitHub and .env
- Update secrets to match

**❌ "404 Not Found"**
- Webhook path is wrong
- Should be: `/webhooks/github`

### Redeliver a Webhook

1. Click on any delivery in Recent Deliveries
2. Click **"Redeliver"** button
3. Watch your FastAPI terminal and ngrok terminal for activity

---

## Step 6: Check Application Logs

### FastAPI Terminal

When a webhook arrives, you should see logs like:

```
INFO:     Received issue_comment event
INFO:     Comment on PR #3 by vrushitpatel
INFO:     Command detected: help
INFO:     Processing command: help
INFO:     Posted help message for PR #3
```

### ngrok Terminal

Should show HTTP requests:

```
POST /webhooks/github    200 OK
```

### If NO Logs Appear

Webhooks are not reaching your application. Go back to Steps 2-3.

### If Logs Show Errors

Common errors in logs:

**Error: "Missing X-GitHub-Event header"**
- Request is not coming from GitHub
- Test with a real PR comment, not curl

**Error: "Signature verification failed"**
- Webhook secret mismatch
- Check `.env` file `GITHUB_WEBHOOK_SECRET`
- Update GitHub App webhook secret
- Restart application

**Error: "Failed to parse issue comment event"**
- Payload structure doesn't match expected format
- Check GitHub webhook payload in Recent Deliveries

**Error: "401 Unauthorized" when posting comment**
- GitHub App authentication failed
- Check `GITHUB_APP_ID` in `.env`
- Check `GITHUB_PRIVATE_KEY_PATH` points to valid `.pem` file
- Check GitHub App is installed on repository

---

## Step 7: Test with a Simple Webhook Delivery

### Manually Trigger a Webhook

1. Go to GitHub App settings → Webhook → Recent Deliveries
2. Find any previous delivery (or create a test comment)
3. Click **"Redeliver"**

### Watch Three Places

1. **FastAPI Terminal** - Should show logs
2. **ngrok Terminal** - Should show POST request
3. **GitHub PR** - Should show bot response

### If Still No Response

Try this diagnostic endpoint:

```bash
# Test webhook endpoint directly
curl -X GET https://your-ngrok-url.ngrok-free.app/webhooks/github
```

**Expected Response:**
```json
{
  "endpoint": "/webhooks/github",
  "method": "POST",
  "description": "GitHub webhook receiver",
  "note": "Send POST requests with X-GitHub-Event and X-Hub-Signature-256 headers"
}
```

---

## Step 8: Test with Real PR Comment

### Create a Test Comment

1. Open any Pull Request
2. Add a comment: `/help`
3. Submit the comment
4. Wait 5-10 seconds

### What Should Happen

**In GitHub PR:**
- Bot should post a help message within 10 seconds
- Message should show available commands

**In FastAPI Terminal:**
```
INFO: Received issue_comment event
INFO: Comment on PR #X by username
INFO: Command detected: help
INFO: Handling /help command for repo#X
INFO: Posted help message for PR #X
```

**In ngrok Terminal:**
```
POST /webhooks/github    200 OK
```

---

## Common Issues and Solutions

### Issue: Bot Not Responding to Commands

**Possible Causes:**
1. Command not detected → Check command starts with `/` at beginning of comment
2. Webhook not delivered → Check GitHub Recent Deliveries
3. Application error → Check FastAPI logs for exceptions
4. Permission issue → Check GitHub App has "Issues: Write" permission

**Solution:**
```bash
# Check logs for the specific PR
# Look for: "Command detected: help"
# If not found, command extraction failed
```

### Issue: "Signature verification failed"

**Cause:** Webhook secret mismatch

**Solution:**
1. Generate new secret: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Update GitHub App webhook secret with new secret
3. Update `.env` file: `GITHUB_WEBHOOK_SECRET=new_secret_here`
4. Restart FastAPI application
5. Test again

### Issue: ngrok URL Changes Every Restart

**Cause:** Free ngrok accounts get new URLs on restart

**Solutions:**
1. **Use ngrok authtoken** (keeps URL longer):
   ```bash
   ngrok config add-authtoken YOUR_TOKEN
   ngrok http 8000
   ```

2. **Get ngrok paid plan** (static URLs)

3. **Update webhook URL** each time ngrok restarts:
   - Copy new ngrok URL
   - Update GitHub App webhook URL
   - Add `/webhooks/github` path

### Issue: "Failed to post PR comment" / 401 Error

**Cause:** GitHub App authentication failed

**Solution:**
1. Verify `GITHUB_APP_ID` in `.env` matches GitHub App ID
2. Verify `GITHUB_PRIVATE_KEY_PATH` points to correct `.pem` file
3. Verify `.pem` file is valid and not expired
4. Check GitHub App is installed on the repository
5. Check App has "Pull requests: Write" and "Issues: Write" permissions

**Test GitHub Authentication:**
```python
# Run this test script
from app.integrations.github_client import GitHubClient
client = GitHubClient()
# If this fails, authentication is broken
```

### Issue: Commands Work for Some Repos but Not Others

**Cause:** GitHub App not installed on all repositories

**Solution:**
1. Go to: `https://github.com/settings/installations`
2. Click on your app
3. Under "Repository access", select repositories
4. Click "Save"

---

## Testing Checklist

Use this checklist to verify everything works:

### Basic Connectivity
- [ ] `curl http://localhost:8000/health` returns 200 OK
- [ ] `curl https://your-ngrok-url.ngrok-free.app/health` returns 200 OK
- [ ] `curl https://your-ngrok-url.ngrok-free.app/webhooks/github` returns info

### GitHub Configuration
- [ ] GitHub App webhook URL is set to `https://your-ngrok-url.ngrok-free.app/webhooks/github`
- [ ] Webhook secret matches `.env` file
- [ ] Webhook is Active (checkbox checked)
- [ ] SSL verification is enabled

### GitHub App Installation
- [ ] App is installed on your repository
- [ ] App has "Pull requests: Read & Write" permission
- [ ] App has "Issues: Read & Write" permission
- [ ] App subscribes to "Pull request" events
- [ ] App subscribes to "Issue comment" events

### Webhook Delivery
- [ ] Recent Deliveries shows webhook attempts
- [ ] Recent delivery has green checkmark (200 OK)
- [ ] Delivery payload shows correct event type
- [ ] Response shows `{"status": "received"}`

### Application Logs
- [ ] FastAPI shows "Received issue_comment event"
- [ ] FastAPI shows "Command detected: help"
- [ ] FastAPI shows "Posted help message"
- [ ] ngrok shows "POST /webhooks/github 200 OK"

### End-to-End Test
- [ ] Posted `/help` comment on PR
- [ ] Bot responded within 10 seconds
- [ ] Bot response shows available commands
- [ ] Bot response is properly formatted markdown

---

## Advanced Debugging

### Enable Debug Logging

Update `.env`:
```
LOG_LEVEL=DEBUG
DEBUG=True
```

Restart application. Logs will show detailed information.

### Test Webhook Signature Manually

```python
import hmac
import hashlib

secret = "your_webhook_secret"
payload = b'{"test": "data"}'
signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
print(signature)
```

### Check Webhook Payload Structure

In GitHub Recent Deliveries:
1. Click on a delivery
2. View the **"Payload"** tab
3. Verify structure matches expected format

**For issue_comment event:**
```json
{
  "action": "created",
  "issue": {
    "number": 123,
    "pull_request": {}
  },
  "comment": {
    "body": "/help",
    "user": {"login": "username"}
  },
  "repository": {
    "full_name": "owner/repo"
  },
  "installation": {
    "id": 12345
  }
}
```

### Test Command Extraction

```python
from app.webhooks.github import extract_command

# Should return "help"
command = extract_command("/help")
print(command)

# Should return "explain"
command = extract_command("/explain")
print(command)

# Should return None (no slash at start)
command = extract_command("some text /help")
print(command)
```

---

## Still Not Working?

### Collect Debug Information

```bash
# Application info
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/webhooks/metrics

# Check environment
cat .env | grep -v API_KEY | grep -v SECRET
```

### Check GitHub App Logs

1. Go to: `https://github.com/settings/apps/your-app-name/advanced`
2. Check for any errors or warnings
3. Look at API request logs

### Verify Private Key

```bash
# Check private key file exists and is readable
ls -la private-key.pem

# Verify it's a valid PEM file
head -n 1 private-key.pem
# Should show: -----BEGIN RSA PRIVATE KEY-----
```

### Test Minimum Configuration

Create a test PR and try each command:
1. `/help` - Should respond immediately (no AI call)
2. `/explain` - Should call Gemini and respond with explanation
3. `/review` - Should trigger full review workflow

If `/help` works but others don't:
- Issue is with AI integration (Gemini)
- Check `GEMINI_API_KEY` in `.env`
- Check Gemini API quota/billing

---

## Quick Fix Summary

**Most Common Fix:**
```bash
# 1. Make sure app is running
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Make sure ngrok is running
ngrok http 8000

# 3. Update GitHub webhook URL with current ngrok URL
# Go to: https://github.com/settings/apps/your-app-name
# Update webhook URL to: https://your-new-ngrok-url.ngrok-free.app/webhooks/github

# 4. Verify webhook secret matches
# In GitHub and .env file

# 5. Test with /help command on a PR
```

---

## Success Criteria

You know it's working when:
- ✅ FastAPI terminal shows "Received issue_comment event"
- ✅ FastAPI terminal shows "Command detected: help"
- ✅ FastAPI terminal shows "Posted help message"
- ✅ ngrok terminal shows "POST /webhooks/github 200 OK"
- ✅ GitHub PR shows bot response with help text
- ✅ GitHub Recent Deliveries shows green checkmark

---

## Need More Help?

1. Check application logs in FastAPI terminal
2. Check GitHub webhook Recent Deliveries for errors
3. Check ngrok terminal for HTTP request logs
4. Enable DEBUG logging in `.env`
5. Review GitHub App permissions and installation
6. Verify all environment variables are set correctly

**Common Solutions:**
- 90% of issues: ngrok URL changed, update webhook URL
- 5% of issues: webhook secret mismatch
- 5% of issues: app not running or port mismatch
