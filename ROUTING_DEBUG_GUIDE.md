# Routing Debug Guide

How to check which routing system is active and see routing logs.

---

## Quick Check: Which System Am I Using?

### Method 1: Check Logs When Command is Posted

Post `/help` in a GitHub PR and look for one of these in your FastAPI terminal:

**Option A: Command Router (Default)**
```
INFO: Processing command: help
INFO: 🔀 Using command router
INFO: Routing command from comment
```

**Option B: Multi-Agent Workflow**
```
INFO: Processing command: help
INFO: 🔀 Using multi-agent workflow
INFO: Executing multi-agent workflow: command_created
INFO: Initializing workflow for command_created
INFO: Routing event: command_created
INFO: Routing to explainer (command)
```

---

## System Comparison

### Command Router (Currently Active)

**Flow:**
```
Webhook → process_command → CommandRouter → AgentWrapper → GitHub
```

**Key Log Messages:**
```
"🔀 Using command router"
"Routing command from comment"
"Executing agent: HelpAgent"
```

**Location:** `app/commands/router.py`

---

### Multi-Agent Workflow (Optional)

**Flow:**
```
Webhook → execute_multi_agent_workflow → LangGraph → Agent Node → GitHub
```

**Key Log Messages:**
```
"🔀 Using multi-agent workflow"
"Initializing workflow for command_created"
"Routing event: command_created"
"Routing to explainer (command)"
"Executing explainer"
```

**Location:** `app/workflows/multi_agent_workflow.py`

---

## How to Switch Systems

### Enable Multi-Agent Workflow

**Option 1: Environment Variable**

Add to your `.env` file:
```bash
USE_MULTI_AGENT_WORKFLOW=true
```

**Option 2: Direct Config**

Edit `app/config.py`:
```python
use_multi_agent_workflow: bool = Field(
    default=True,  # Changed from False
    ...
)
```

**Restart FastAPI:**
```bash
# Stop server (Ctrl+C)
# Start again
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Troubleshooting: No Routing Logs

### Problem: Can't see ANY routing messages

**Possible Causes:**

1. **Webhook not reaching server**
   - Check ngrok is running
   - Check FastAPI is running
   - Verify webhook URL in GitHub

2. **Command not recognized**
   - Try `/help` first (simplest command)
   - Check command starts with `/`
   - Check comment is on PR (not issue)

3. **Logs not visible**
   - Check correct terminal window
   - Logs appear in FastAPI terminal, not ngrok

---

## Debug Checklist

### Step 1: Verify FastAPI is Running

```bash
curl http://localhost:8000/health
```

Expected: `{"status": "healthy"}`

### Step 2: Verify Webhook Received

Post `/help` in PR and check terminal for:
```
INFO: Received issue_comment event
INFO: Comment on PR #X by username
INFO: Command detected: help
```

✅ **If you see these:** Webhook is working, routing happens next

❌ **If you don't see these:** Webhook not reaching server

### Step 3: Check Routing

Continue reading logs after "Command detected":

**Should see:**
```
INFO: Processing command: help
INFO: 🔀 Using command router
```

✅ **If you see this:** Routing is working with command router

### Step 4: Check Agent Execution

Continue reading:

```
INFO: Routing command from comment
INFO: Matched command: help
INFO: Executing agent: HelpAgent
```

✅ **If you see this:** Agent is executing

---

## Example: Full Log Flow

### Command Router Mode (Current)

```
INFO: Received issue_comment event
INFO: Comment on PR #1 by vrushitpatel
INFO: Command detected: help
INFO: Processing command: help
INFO: 🔀 Using command router        ← ROUTING START
INFO: Routing command from comment
INFO: Matched command: help
INFO: Executing agent: HelpAgent     ← AGENT EXECUTION
INFO: Agent executed successfully
INFO: Posted response to PR #1
```

### Multi-Agent Workflow Mode (After Enabling)

```
INFO: Received issue_comment event
INFO: Comment on PR #1 by vrushitpatel
INFO: Command detected: help
INFO: Processing command: help
INFO: 🔀 Using multi-agent workflow              ← ROUTING START
INFO: Executing multi-agent workflow: command_created
INFO: Initializing workflow for command_created
INFO: Routing event: command_created
INFO: Routing to explainer (command)            ← ROUTING DECISION
INFO: Executing explainer                       ← AGENT EXECUTION
INFO: Explainer completed successfully
INFO: Posting result to GitHub
INFO: Result posted to GitHub successfully
```

---

## Common Issues

### Issue: "No routing messages at all"

**Check:**
```bash
# In your .env or app/config.py
# Logging level might be too high
```

**Fix:**
Ensure logging is set to INFO level (default)

---

### Issue: "Using command router but want multi-agent"

**Fix:**
```bash
# Add to .env
USE_MULTI_AGENT_WORKFLOW=true

# Restart server
```

---

### Issue: "Can't find log files"

**Answer:**
Logs are in **stdout** (FastAPI terminal), not files by default.

To save to file:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee app.log
```

Now logs go to both terminal AND `app.log` file.

---

## Quick Test Script

Run this to verify logging works:

```bash
python test_logging.py
```

Expected output:
```
INFO: Testing INFO level
INFO: Processing command: test
✅ If you see messages above, logging is working!
```

---

## Summary

**To see routing logs:**
1. ✅ Post `/help` in a PR
2. ✅ Watch FastAPI terminal
3. ✅ Look for `🔀 Using command router` or `🔀 Using multi-agent workflow`
4. ✅ Then look for routing-specific messages below that

**Currently active:** Command Router (default)
**To switch:** Set `USE_MULTI_AGENT_WORKFLOW=true` in `.env`

---

**Pro Tip:** Keep your FastAPI terminal visible when testing commands. All routing logs appear there in real-time!
