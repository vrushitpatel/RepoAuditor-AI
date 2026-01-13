# GitHub App Setup Guide

Quick guide to set up your GitHub App for RepoAuditor AI.

---

## Step 1: Create a GitHub App

1. Go to **GitHub Settings** → **Developer settings** → **GitHub Apps**
   - Or visit: https://github.com/settings/apps

2. Click **New GitHub App**

3. Fill in basic information:
   - **App Name**: `YourName-RepoAuditor-AI` (must be unique)
   - **Homepage URL**: Your app URL or `https://github.com/yourusername/repoauditor-ai`
   - **Webhook URL**: `https://your-domain.com/webhooks/github`
   - **Webhook Secret**: Generate a secure random string (save this for `.env`)

4. Enable **Webhook Active** ✅

---

## Step 2: Set Repository Permissions

Under **Permissions** → **Repository permissions**, set:

| Permission | Access Level |
|------------|--------------|
| **Contents** | Read-only |
| **Issues** | Read and write |
| **Metadata** | Read-only |
| **Pull requests** | Read and write |

---

## Step 3: Subscribe to Webhook Events

Under **Subscribe to events**, enable:

- ✅ **Issue comment**
- ✅ **Pull request**
- ✅ **Pull request review**
- ✅ **Pull request review comment**

---

## Step 4: Set App Settings

1. **Where can this GitHub App be installed?**
   - Choose: **Any account** (for public use) or **Only on this account** (for private use)

2. Click **Create GitHub App**

---

## Step 5: Generate Private Key

1. After creation, scroll to **Private keys** section
2. Click **Generate a private key**
3. Save the downloaded `.pem` file securely
4. Move it to your project: `./github-app-private-key.pem`

---

## Step 6: Note Your App Credentials

From the app settings page, note down:

- **App ID** (displayed at the top)
- **Client ID**
- **Client Secret** (click Generate, then copy)

Update your `.env` file:
```env
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=./github-app-private-key.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret
```

---

## Step 7: Install App on Repository

1. Go to your GitHub App settings page
2. Click **Install App** (left sidebar)
3. Select the account/organization
4. Choose repositories:
   - **All repositories** or
   - **Only select repositories** → Choose your repo(s)
5. Click **Install**

---

## Step 8: Test Your Setup

1. Create or open a Pull Request in your repository
2. Post a comment: `/generate-ci`
3. The bot should respond with generated CI/CD workflows in a comment
4. Copy the workflows from the comment and add them to your repository

### Test Other Commands
- `/explain` - Get explanation of PR changes
- `/review` - Get code review
- `/help` - List all commands

### How CI/CD Generation Works
- The bot **analyzes your project** (language, framework, dependencies)
- **Generates customized workflows** (test, build, lint, deploy)
- **Posts them in a PR comment** with full YAML code
- **You copy and add them** to `.github/workflows/` directory
- This approach works for all repositories (no permission issues!)

---

## Troubleshooting

### Bot Not Responding to Comments
- **Issue**: Bot doesn't respond to commands
- **Fix**:
  - Check webhook URL is publicly accessible
  - Verify webhook secret matches `.env`
  - Check webhook delivery logs in App settings → Recent Deliveries
  - Ensure bot is installed on the repository (Step 7)

### Bot Can't Read Repository
- **Issue**: Bot says it can't access files
- **Fix**:
  - Verify Step 2 - Ensure **Contents** permission is set to **Read-only** (minimum)
  - Reinstall the app on your repository after changing permissions

### Workflows Not Showing
- **Issue**: `/generate-ci` doesn't post workflows
- **Fix**:
  - Check application logs for errors
  - Ensure Gemini API key is configured in `.env`
  - Verify the repository has a valid project structure

---

## Security Best Practices

1. **Keep private key secure** - Never commit `.pem` file to git
2. **Use environment variables** - Store secrets in `.env`, not in code
3. **Rotate secrets regularly** - Update webhook secret and private key periodically
4. **Minimal permissions** - Only grant permissions the app needs
5. **Monitor webhook logs** - Check for unauthorized access attempts

---

## Quick Reference

### Required Permissions
```
Contents: Read-only
Issues: Read and write
Metadata: Read-only
Pull requests: Read and write
```

**Note:** Only read-only access is needed since workflows are posted in comments, not committed directly.

### Required Webhook Events
```
- issue_comment
- pull_request
- pull_request_review
- pull_request_review_comment
```

### Environment Variables
```env
GITHUB_APP_ID=<your_app_id>
GITHUB_PRIVATE_KEY_PATH=./github-app-private-key.pem
GITHUB_WEBHOOK_SECRET=<your_webhook_secret>
```

---

## Need Help?

- **GitHub Apps Documentation**: https://docs.github.com/en/apps
- **Webhook Events**: https://docs.github.com/en/webhooks
- **RepoAuditor AI Issues**: https://github.com/yourusername/repoauditor-ai/issues

---

**Note**: After any permission changes, you may need to reinstall the app on your repositories for changes to take effect.
