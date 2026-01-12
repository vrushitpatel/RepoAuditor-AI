# Testing GitHub Command Parser - Manual Testing Guide

This guide provides step-by-step instructions for manually testing the slash command parser in GitHub PR comments.

## Prerequisites

1. **GitHub Repository**: You need a GitHub repository with the RepoAuditor AI GitHub App installed
2. **Running Application**: The RepoAuditor AI application must be running and accessible
3. **Webhook Configuration**: GitHub webhooks must be configured to point to your application
4. **Pull Request**: An active pull request to test commands on

## Setup Steps

### 1. Verify Application is Running

```bash
# Check if the application is running
curl http://localhost:8000/health

# Expected response: {"status": "ok"}
```

### 2. Verify GitHub App Installation

1. Go to your GitHub repository
2. Navigate to **Settings** → **GitHub Apps**
3. Verify that RepoAuditor AI is installed
4. Check permissions:
   - **Pull requests**: Read & Write
   - **Issues**: Read & Write
   - **Repository contents**: Read-only

### 3. Verify Webhook Configuration

1. Go to **Settings** → **Webhooks**
2. Check webhook URL points to your application (e.g., `https://your-domain.com/webhooks/github`)
3. Verify these events are enabled:
   - Pull requests
   - Issue comments
   - Pull request review comments

## Testing Commands

### Test 1: `/help` Command

**Purpose**: Verify help command displays available commands

**Steps**:
1. Open any pull request in your repository
2. Add a new comment with the text: `/help`
3. Submit the comment
4. Wait for bot response (should be within 5-10 seconds)

**Expected Result**:
- Bot posts a comment with a list of all available commands
- Comment includes command descriptions and usage examples
- Formatted in markdown with clear sections

**Validation**:
```
✓ Bot responded within 10 seconds
✓ Response includes all commands: explain, explain-diff, test, generate-ci, review, help
✓ Each command has description and usage example
✓ Markdown formatting is correct
```

---

### Test 2: `/explain` Command with File Path

**Purpose**: Verify explain command can analyze a specific file

**Steps**:
1. In the same or different PR, add a comment: `/explain app/main.py`
2. Submit the comment
3. Wait for bot response

**Expected Result**:
- Bot posts explanation of `app/main.py`
- Explanation includes:
  - Overview of file purpose
  - Key functions/classes
  - Dependencies and imports
  - Code structure analysis

**Validation**:
```
✓ Bot identified the correct file
✓ Explanation is comprehensive and accurate
✓ Includes metadata (model used, tokens, cost, time)
✓ Markdown formatting is readable
```

---

### Test 3: `/explain` Command with Class/Function Specifier

**Purpose**: Verify explain command with specific class or function

**Steps**:
1. Add comment: `/explain app/integrations/github_client.py:GitHubClient`
2. Submit the comment
3. Wait for response

**Expected Result**:
- Bot explains the `GitHubClient` class specifically
- Explanation focuses on:
  - Class purpose and responsibilities
  - Methods and their purposes
  - Usage examples
  - Dependencies

**Validation**:
```
✓ Bot correctly parsed file:ClassName syntax
✓ Explanation is focused on GitHubClient class only
✓ Includes class methods and attributes
✓ Response is relevant and accurate
```

---

### Test 4: `/explain-diff` Command (Full PR)

**Purpose**: Verify explain-diff explains all PR changes

**Steps**:
1. Ensure PR has at least 2-3 modified files
2. Add comment: `/explain-diff`
3. Submit and wait for response

**Expected Result**:
- Bot analyzes all files changed in the PR
- Explanation includes:
  - Summary of what changed
  - Purpose of changes
  - Impact on codebase
  - File-by-file breakdown (if multiple files)

**Validation**:
```
✓ All changed files are mentioned
✓ Summary is accurate and comprehensive
✓ Explains why changes were made
✓ Includes before/after context
```

---

### Test 5: `/explain-diff` Command (Specific File)

**Purpose**: Verify explain-diff with specific file filter

**Steps**:
1. Add comment: `/explain-diff app/main.py`
2. Submit and wait for response

**Expected Result**:
- Bot explains only changes to `app/main.py` in the PR
- Focuses on diff/changes, not entire file
- Explains impact of specific changes

**Validation**:
```
✓ Only app/main.py changes are explained
✓ Other files are ignored
✓ Diff-based explanation (additions/deletions)
✓ Context is provided for changes
```

---

### Test 6: `/test` Command (Default Framework)

**Purpose**: Verify test generation without specifying framework

**Steps**:
1. Add comment: `/test`
2. Submit and wait for response

**Expected Result**:
- Bot generates tests for PR changes
- Uses default framework (pytest)
- Includes:
  - Test file suggestions
  - Test cases for new/modified functions
  - Assertions and expected outcomes

**Validation**:
```
✓ Test code is generated
✓ Tests are relevant to PR changes
✓ Uses pytest syntax by default
✓ Includes proper imports and fixtures
```

---

### Test 7: `/test` Command (Specific Framework)

**Purpose**: Verify test generation with specific framework

**Steps**:
1. Add comment: `/test unittest`
2. Submit and wait for response

**Expected Result**:
- Bot generates tests using unittest framework
- Syntax matches unittest (not pytest)
- Uses unittest.TestCase classes

**Validation**:
```
✓ Tests use unittest syntax
✓ Contains TestCase classes
✓ Uses self.assertEqual, self.assertTrue, etc.
✓ No pytest-specific features
```

---

### Test 8: `/generate-ci` Command (Default)

**Purpose**: Verify CI/CD workflow generation without type

**Steps**:
1. Add comment: `/generate-ci`
2. Submit and wait for response

**Expected Result**:
- Bot generates complete CI/CD workflow
- Includes all types: build, test, deploy
- Provides GitHub Actions YAML configuration

**Validation**:
```
✓ Valid GitHub Actions YAML syntax
✓ Includes build, test, and deploy jobs
✓ Proper job dependencies
✓ Uses appropriate actions (checkout, setup-python, etc.)
```

---

### Test 9: `/generate-ci` Command (Specific Type)

**Purpose**: Verify CI/CD generation for specific type

**Steps**:
1. Add comment: `/generate-ci test`
2. Submit and wait for response

**Expected Result**:
- Bot generates test-only CI workflow
- Focuses on running tests (pytest, coverage, linting)
- Excludes build and deploy steps

**Validation**:
```
✓ Only test-related jobs included
✓ Includes pytest, coverage, linting
✓ No build or deployment steps
✓ Valid YAML configuration
```

---

### Test 10: `/review` Command

**Purpose**: Verify full PR review trigger

**Steps**:
1. Add comment: `/review`
2. Submit and wait for response

**Expected Result**:
- Bot acknowledges review request immediately
- Performs full code review (may take longer)
- Posts detailed review feedback
- Includes:
  - Code quality issues
  - Potential bugs
  - Best practice suggestions
  - Security concerns (if any)

**Validation**:
```
✓ Immediate acknowledgment comment
✓ Full review completes within reasonable time
✓ Review covers all changed files
✓ Feedback is actionable and specific
```

---

### Test 11: Invalid Command

**Purpose**: Verify error handling for unknown commands

**Steps**:
1. Add comment: `/invalid-command`
2. Submit and wait for response

**Expected Result**:
- Bot responds with error message
- Suggests similar valid command or /help
- Error message is friendly and helpful

**Validation**:
```
✓ Error message posted
✓ Indicates command is unknown
✓ Suggests /help command
✓ May suggest similar valid command
```

---

### Test 12: Command with Wrong Arguments

**Purpose**: Verify argument validation

**Steps**:
1. Add comment: `/help extra arguments here`
2. Submit and wait (help takes no arguments)

**Expected Result**:
- Bot responds with validation error
- Indicates too many arguments
- Shows correct usage

**Validation**:
```
✓ Validation error is clear
✓ Mentions argument count issue
✓ Provides correct usage example
✓ Helpful error message
```

---

### Test 13: Command with Quoted Arguments

**Purpose**: Verify quoted argument parsing

**Steps**:
1. Add comment: `/explain "app/utils/cache.py"`
2. Submit and wait for response

**Expected Result**:
- Bot correctly parses quoted file path
- Treats entire quoted string as single argument
- Executes command normally

**Validation**:
```
✓ Quoted argument parsed correctly
✓ Command executes successfully
✓ File path handled properly
✓ No parsing errors
```

---

### Test 14: Multiple Commands in One Comment

**Purpose**: Verify behavior with multiple commands

**Steps**:
1. Add comment with multiple lines:
   ```
   /help
   /review
   ```
2. Submit and wait for response

**Expected Result**:
- Bot processes the first command found
- Ignores or processes remaining commands based on implementation

**Validation**:
```
✓ At least first command is processed
✓ No parsing errors
✓ Response is coherent
```

---

### Test 15: Command in Middle of Comment

**Purpose**: Verify command extraction from comment text

**Steps**:
1. Add comment:
   ```
   Hey team, can you help?
   /explain app/main.py
   Thanks!
   ```
2. Submit and wait

**Expected Result**:
- Bot finds and executes the `/explain` command
- Ignores surrounding text
- Processes command normally

**Validation**:
```
✓ Command extracted from comment body
✓ Surrounding text ignored
✓ Command executes correctly
✓ Response is relevant to command
```

---

## Troubleshooting

### Bot Not Responding

**Check**:
1. Application is running: `curl http://localhost:8000/health`
2. Webhook delivery in GitHub Settings → Webhooks → Recent Deliveries
3. Application logs for errors
4. GitHub App permissions are correct

### Wrong Command Behavior

**Check**:
1. Command spelling is correct (case-sensitive)
2. Arguments are properly formatted
3. Application logs for parsing errors
4. Command registry is properly initialized

### Parsing Errors

**Check**:
1. Quotes are properly closed
2. No special characters causing issues
3. Arguments are space-separated
4. Check application logs for detailed error

## Test Results Template

Use this template to record test results:

```
## Test Session: [Date]

| Test # | Command | Status | Notes |
|--------|---------|--------|-------|
| 1 | /help | ✓ Pass | All commands listed |
| 2 | /explain app/main.py | ✓ Pass | Accurate explanation |
| 3 | /explain file:Class | ✓ Pass | Class-specific |
| 4 | /explain-diff | ✓ Pass | All files covered |
| 5 | /explain-diff file | ✓ Pass | Single file diff |
| 6 | /test | ✓ Pass | Pytest tests generated |
| 7 | /test unittest | ✓ Pass | Unittest syntax |
| 8 | /generate-ci | ✓ Pass | Full workflow |
| 9 | /generate-ci test | ✓ Pass | Test-only workflow |
| 10 | /review | ✓ Pass | Full review completed |
| 11 | /invalid-command | ✓ Pass | Error handled |
| 12 | /help extra args | ✓ Pass | Validation error |
| 13 | /explain "quoted" | ✓ Pass | Quotes parsed |
| 14 | Multiple commands | ✓ Pass | First processed |
| 15 | Command in text | ✓ Pass | Extracted correctly |

**Overall**: 15/15 tests passed

**Issues Found**: None

**Recommendations**: None
```

## Next Steps

After completing manual testing:

1. **Document Issues**: Record any bugs or unexpected behavior
2. **Create Unit Tests**: Write automated tests for parser logic
3. **Performance Testing**: Test with high volume of commands
4. **Edge Cases**: Test with unusual input (unicode, very long arguments, etc.)
5. **Security Testing**: Test with injection attempts or malicious input
