# Testing CI/CD Generator - Complete Manual Testing Guide

## 📋 Overview

This guide provides comprehensive manual testing procedures for the CI/CD Generator feature. Follow these test cases to ensure everything works correctly.

---

## 🎯 Prerequisites

Before testing, ensure:

1. **Application is Running**
   ```bash
   python main.py
   ```
   - FastAPI should be running
   - ngrok should be active (if testing locally)

2. **GitHub App is Configured**
   - Webhooks are subscribed to "Issue comments"
   - App is installed on test repository

3. **Environment Variables Set**
   ```bash
   # Check these are configured
   GITHUB_APP_ID
   GITHUB_PRIVATE_KEY
   GEMINI_API_KEY
   ```

4. **Test Repository Requirements**
   - Create or use a test repository
   - Repository should have one of:
     - Python project (with `requirements.txt` or `pyproject.toml`)
     - Node.js project (with `package.json`)
     - Docker project (with `Dockerfile`)

---

## 🧪 Test Cases

### Test Case 1: Generate All Workflows (Python Project)

**Setup:**
- Repository: Python project with `requirements.txt`
- File structure:
  ```
  my-python-app/
  ├── app/
  │   └── main.py
  ├── tests/
  │   └── test_main.py
  ├── requirements.txt  (with pytest, black)
  └── Dockerfile
  ```

**Steps:**
1. Create a Pull Request in the repository
2. In PR comments, post: `/generate-ci all`
3. Wait 5-10 seconds

**Expected Results:**
✅ **Acknowledgment Comment:**
```
🚀 CI/CD Generator Started

@username I'm analyzing your project and generating customized CI/CD workflows...

Requested workflows: all
```

✅ **Generated Workflows Comment:**
- Should include:
  - 🧪 `test.yml` - Python test workflow with pytest
  - ✨ `lint.yml` - Code quality with black
  - 🐳 `build.yml` - Docker build workflow (if Dockerfile present)
- Each workflow expandable with full YAML content
- Instructions for manual setup
- Pro Tips section
- Generation metadata

✅ **FastAPI Logs:**
```
INFO - Handling /generate-ci command for username/repo#123
INFO - Generating workflows: ['all']
INFO - Detected project type: python
INFO - Posted CI/CD workflows for PR #123
```

**Validation:**
- [ ] Acknowledgment posted within 2 seconds
- [ ] Full workflows comment posted within 10 seconds
- [ ] Python-specific workflows generated (pytest, black)
- [ ] YAML syntax is valid
- [ ] Placeholders replaced correctly (no {{}} remaining)
- [ ] Generation metadata shows correct project type

---

### Test Case 2: Generate Specific Workflow (test only)

**Setup:**
- Same Python project as Test Case 1

**Steps:**
1. In the same or new PR, comment: `/generate-ci test`

**Expected Results:**
✅ Only `test.yml` generated
✅ No `lint.yml` or `build.yml`
✅ Test workflow customized for pytest

**Validation:**
- [ ] Only test workflow generated
- [ ] Workflow includes pytest commands
- [ ] Python version detected correctly
- [ ] Requirements file detection correct

---

### Test Case 3: Generate Multiple Workflows

**Setup:**
- Same Python project

**Steps:**
1. Comment: `/generate-ci test lint`

**Expected Results:**
✅ Both `test.yml` and `lint.yml` generated
✅ No `build.yml` or `deploy.yml`

**Validation:**
- [ ] Both workflows present
- [ ] Each workflow properly customized
- [ ] No duplicate workflows

---

### Test Case 4: Node.js Project

**Setup:**
- Repository: Node.js project with `package.json`
- File structure:
  ```
  my-node-app/
  ├── src/
  │   └── index.js
  ├── tests/
  │   └── index.test.js
  └── package.json
  ```

**package.json:**
```json
{
  "name": "my-app",
  "scripts": {
    "test": "jest",
    "lint": "eslint ."
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "eslint": "^8.0.0"
  }
}
```

**Steps:**
1. Create PR
2. Comment: `/generate-ci all`

**Expected Results:**
✅ Node.js-specific workflows:
- `test.yml` with `npm ci` and `npm test`
- `lint.yml` with `npm run lint`

✅ Detection:
- Project type: nodejs
- Package manager: npm
- Test framework: jest
- Linter: eslint

**Validation:**
- [ ] Node.js workflows generated (not Python)
- [ ] npm commands used
- [ ] jest detected
- [ ] eslint detected

---

### Test Case 5: Docker Project

**Setup:**
- Repository with `Dockerfile`

**Steps:**
1. Create PR
2. Comment: `/generate-ci build`

**Expected Results:**
✅ Docker build workflow generated
✅ Workflow includes:
- Docker buildx setup
- GitHub Container Registry login
- Build and push configuration
- Only pushes on main branch (not PRs)

**Validation:**
- [ ] Docker workflow generated
- [ ] ghcr.io registry configured
- [ ] Push only on main branch
- [ ] Pull request builds but doesn't push

---

### Test Case 6: Project with Poetry

**Setup:**
- Python project with `pyproject.toml` (Poetry)

**Steps:**
1. Comment: `/generate-ci test`

**Expected Results:**
✅ Test workflow uses Poetry:
```yaml
- run: pip install poetry
- run: poetry install
- run: poetry run pytest
```

**Validation:**
- [ ] Poetry detected
- [ ] Poetry commands in workflow
- [ ] No pip install -r requirements.txt

---

### Test Case 7: No Project Files (Error Case)

**Setup:**
- Empty repository or repository without project files

**Steps:**
1. Create PR
2. Comment: `/generate-ci all`

**Expected Results:**
✅ Error comment posted:
```
❌ CI/CD Generation Failed

Sorry @username, I encountered an error...

Troubleshooting Tips:
- Make sure your repository has a valid project structure
- For Python: Ensure requirements.txt...
```

**Validation:**
- [ ] Error message posted
- [ ] Helpful troubleshooting tips included
- [ ] No Python traceback visible to user

---

### Test Case 8: Multiple Workflow Types

**Setup:**
- Python project with Docker

**Steps:**
1. Comment: `/generate-ci test lint build`

**Expected Results:**
✅ Three workflows generated:
- `test.yml`
- `lint.yml`
- `build.yml`

**Validation:**
- [ ] All three workflows present
- [ ] Each properly customized
- [ ] No duplicates

---

### Test Case 9: Case Insensitive Command

**Setup:**
- Any project

**Steps:**
1. Comment: `/Generate-CI all` (mixed case)
2. Comment: `/GENERATE-CI test` (uppercase)

**Expected Results:**
✅ Both commands work correctly
✅ Same results as lowercase

**Validation:**
- [ ] Mixed case works
- [ ] Uppercase works
- [ ] Same output as lowercase

---

### Test Case 10: Help Command Shows CI/CD

**Steps:**
1. Comment: `/help`

**Expected Results:**
✅ Help message includes:
```
### 🚀 /generate-ci
Generate customized CI/CD workflows for your project:
- /generate-ci or /generate-ci all - Generate all workflows
- /generate-ci test - Generate test workflow only
...
```

**Validation:**
- [ ] CI/CD section present in help
- [ ] Examples included
- [ ] Usage explained

---

## 🔍 Validation Checklist

After running all test cases, verify:

### Functionality
- [ ] All workflow types generate correctly (test, lint, build, deploy)
- [ ] Python projects detected and customized
- [ ] Node.js projects detected and customized
- [ ] Docker projects detected and customized
- [ ] Multiple package managers supported (pip, poetry, pipenv, npm, yarn, pnpm)
- [ ] Multiple test frameworks supported (pytest, unittest, jest)
- [ ] Multiple linters supported (black, ruff, eslint)

### YAML Quality
- [ ] All generated YAML is valid (no syntax errors)
- [ ] No {{PLACEHOLDER}} text remaining
- [ ] Proper indentation
- [ ] Correct GitHub Actions syntax
- [ ] Secrets referenced correctly

### User Experience
- [ ] Acknowledgment posted quickly
- [ ] Final results posted within reasonable time
- [ ] Error messages are helpful
- [ ] Instructions are clear
- [ ] Examples are provided
- [ ] Metadata is accurate

### Error Handling
- [ ] Invalid project types handled gracefully
- [ ] Missing files handled correctly
- [ ] GitHub API errors handled
- [ ] Helpful error messages provided

---

## 📊 Test Results Template

Use this template to document your test results:

```
## Test Run: [Date]

**Environment:**
- FastAPI Version:
- Python Version:
- Test Repository:

### Test Results:

| Test Case | Status | Notes |
|-----------|--------|-------|
| TC1: Generate All (Python) | ✅/❌ | |
| TC2: Generate Specific | ✅/❌ | |
| TC3: Multiple Workflows | ✅/❌ | |
| TC4: Node.js Project | ✅/❌ | |
| TC5: Docker Project | ✅/❌ | |
| TC6: Poetry Project | ✅/❌ | |
| TC7: Error Case | ✅/❌ | |
| TC8: Multiple Types | ✅/❌ | |
| TC9: Case Insensitive | ✅/❌ | |
| TC10: Help Command | ✅/❌ | |

### Issues Found:
1.
2.

### Performance:
- Average generation time:
- Acknowledgment latency:
- Comment posting latency:
```

---

## 🐛 Common Issues & Solutions

### Issue 1: No Workflows Generated

**Symptoms:**
- Acknowledgment posted but no workflows comment
- Error in logs: "Template not found"

**Solution:**
- Check template files exist in `app/templates/cicd_templates/`
- Verify template file names match code

### Issue 2: Placeholders Not Replaced

**Symptoms:**
- Generated YAML contains `{{PYTHON_VERSION}}`

**Solution:**
- Check customization functions are called
- Verify project detection works
- Check placeholder names match template

### Issue 3: Wrong Workflow Type Generated

**Symptoms:**
- Python workflows for Node.js project

**Solution:**
- Check project detection logic
- Verify `requirements.txt` or `package.json` detection
- Test ProjectDetector separately

### Issue 4: GitHub API Rate Limit

**Symptoms:**
- Error: "API rate limit exceeded"

**Solution:**
- Wait for rate limit reset
- Use authenticated requests (should be automatic)
- Check installation token generation

---

## 🎓 Manual Testing Tips

1. **Use Test Repositories**
   - Don't test on production repositories
   - Create dedicated test repos for each project type

2. **Check Logs**
   - Always monitor FastAPI terminal
   - Look for errors in workflow generation
   - Verify detection logic works

3. **Validate YAML**
   - Copy generated YAML to a validator
   - Paste into `.github/workflows/` and check GitHub Actions UI
   - Ensure no syntax errors

4. **Test Edge Cases**
   - Empty repositories
   - Repositories with unusual structures
   - Very large repositories
   - Repositories with multiple languages

5. **Document Issues**
   - Screenshot errors
   - Copy log outputs
   - Note exact steps to reproduce

---

## ✅ Success Criteria

The CI/CD Generator is working correctly if:

1. ✅ **All test cases pass** (10/10)
2. ✅ **Generated YAML is valid** (no syntax errors)
3. ✅ **Project detection is accurate** (Python vs Node.js)
4. ✅ **Customization works** (correct commands, versions)
5. ✅ **Error handling is graceful** (helpful messages)
6. ✅ **Performance is acceptable** (<10s generation time)
7. ✅ **User experience is smooth** (clear instructions)

---

## 📞 Need Help?

If tests fail or you encounter issues:

1. Check logs in FastAPI terminal
2. Review `TROUBLESHOOTING_WEBHOOKS.md` for webhook issues
3. Review `HOW_CICD_WORKS.md` for feature explanation
4. Check GitHub App configuration
5. Verify environment variables

---

**Happy Testing! 🚀**
