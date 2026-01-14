# Bug Fix: Timezone-Aware Datetime Handling

## Issue

**Error:** `TypeError: can't subtract offset-naive and offset-aware datetimes`

**Location:** `app/utils/rate_limiter.py:392`

**Root Cause:** The rate limiter was mixing timezone-naive and timezone-aware datetime objects, causing comparison errors during runtime.

## The Problem

1. **Mixed Datetime Types:**
   - `datetime.utcnow()` returns timezone-naive datetimes
   - `datetime.fromisoformat()` could return either naive or aware datetimes depending on the input format
   - When comparing naive vs aware datetimes, Python raises `TypeError`

2. **Where It Failed:**
   ```python
   # Line 392 - Original code
   return datetime.utcnow() - last_cleanup > self.CLEANUP_INTERVAL
   #      ^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^
   #      naive datetime      could be aware (from ISO with 'Z')
   ```

## The Solution

### 1. Use Timezone-Aware Datetimes Throughout

**Changed:** All `datetime.utcnow()` to `datetime.now(timezone.utc)`

```python
# Before
datetime.utcnow()

# After
datetime.now(timezone.utc)
```

**Locations Updated:**
- Line 108: File initialization
- Line 274: User command counting
- Line 314: Repository date checking
- Line 341: User command recording
- Line 362: Repository command recording
- Line 392: Cleanup time checking
- Line 401: Cleanup execution
- Line 420: Repository date setting

### 2. Added Datetime Parsing Helper

Created `_parse_datetime()` method to safely parse ISO format strings:

```python
@staticmethod
def _parse_datetime(dt_str: str) -> datetime:
    """
    Parse ISO format datetime string and ensure it's timezone-aware.

    Handles both formats:
    - "2026-01-14T13:04:57Z" (with Z suffix)
    - "2026-01-14T13:04:57.123456" (without timezone)

    Returns:
        Timezone-aware datetime in UTC
    """
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        # If naive, treat as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
```

**Locations Updated:**
- Line 301: User command timestamp parsing
- Line 408: Last cleanup timestamp parsing
- Line 427: Command timestamp filtering

### 3. Added Import

```python
from datetime import datetime, timedelta, timezone  # Added 'timezone'
```

## Testing

### Unit Tests
All 11 rate limiter tests pass:
```
tests/unit/test_rate_limiter.py::test_rate_limiter_initialization PASSED
tests/unit/test_rate_limiter.py::test_user_rate_limit PASSED
tests/unit/test_rate_limiter.py::test_pr_rate_limit PASSED
tests/unit/test_rate_limiter.py::test_repo_rate_limit PASSED
tests/unit/test_rate_limiter.py::test_different_users_independent_limits PASSED
tests/unit/test_rate_limiter.py::test_get_limits_status PASSED
tests/unit/test_rate_limiter.py::test_cleanup_old_entries PASSED
tests/unit/test_rate_limiter.py::test_repo_limit_resets_daily PASSED
tests/unit/test_rate_limiter.py::test_file_persistence PASSED
tests/unit/test_rate_limiter.py::test_concurrent_commands_same_user PASSED
tests/unit/test_rate_limiter.py::test_command_recording_accuracy PASSED

====================== 11 passed, 5 warnings ======================
```

### Production Testing
- Tested with `/fix-security-issues` command on GitHub PR
- Tested with `/comprehensive-review` command on GitHub PR
- Both commands now execute without datetime errors

## Impact

**Before:** Commands would fail with `TypeError` during rate limit checking
**After:** Commands execute successfully with proper timezone-aware datetime handling

## Files Modified

1. **`app/utils/rate_limiter.py`**
   - Added `timezone` import
   - Added `_parse_datetime()` static method
   - Replaced all `datetime.utcnow()` with `datetime.now(timezone.utc)`
   - Replaced all `datetime.fromisoformat()` with `self._parse_datetime()`

## Remaining Warnings

Minor deprecation warnings remain in test files using `datetime.utcnow()`. These are non-critical and can be updated separately:

```python
# In tests/unit/test_rate_limiter.py
old_timestamp = (datetime.utcnow() - timedelta(hours=2)).isoformat()
# Should be updated to:
old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
```

## Prevention

Going forward:
1. **Always use timezone-aware datetimes** for any datetime operations
2. **Use `datetime.now(timezone.utc)`** instead of `datetime.utcnow()`
3. **Always parse ISO strings** through the `_parse_datetime()` helper
4. **Store timestamps with timezone info** (ISO format with 'Z' suffix or '+00:00')

---

**Fixed:** January 14, 2026
**Status:** ✅ Complete and tested
**Impact:** All new multi-agent workflows now working in production
