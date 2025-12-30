# Episode Blocking System Failure Investigation

## Problem Statement

**Issue**: After an S1 entry failure for "NOTHING", an S2 entry was allowed, which should be blocked.

**Expected Behavior**: 
- S1 failure → blocks S1 + S2 entries
- S2 failure → blocks S2 entries only

**Actual Behavior**: 
- S1 entry failed (12:39:28)
- Position went S1 → S2 → S0 (failed attempt)
- S2 entry was allowed at 14:22:54 (should have been blocked)

---

## Root Cause Analysis

### Critical Finding: `record_attempt_failure` is NEVER Called

**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py::_process_episode_logging()`

**The Problem**:
1. ✅ Episode blocking functions exist (`episode_blocking.py`)
2. ✅ Blocking checks exist in `actions.py` (lines 827, 993)
3. ❌ **`record_attempt_failure` is NEVER called when episodes fail**

### Evidence from Code

**In `_process_episode_logging()` (lines 1240-1259)**:
```python
elif state == "S0" and prev_state in ("S1", "S2"):
    outcome = "failure"
    # Update DB outcomes for all windows in this episode
    self._update_episode_outcomes_from_meta(s1_episode, outcome)
    
    s1_episode.pop("active_window", None)
    strands.append(...)
    meta["s1_episode"] = None
    changed = True
    # ❌ MISSING: record_attempt_failure() call here!
```

**In `_process_episode_logging()` (lines 1285-1305)**:
```python
elif state == "S0":
    # S2 episode failed - attempt ended at S0
    outcome = "failure"
    self._update_episode_outcomes_from_meta(s2_episode, outcome)
    
    s2_episode.pop("active_window", None)
    strands.append(...)
    meta["s2_episode"] = None
    changed = True
    logger.debug("PHASE7: S2 episode failure for position")
    # ❌ MISSING: record_attempt_failure() call here!
```

**Missing Import**:
```python
# ❌ No import found in pm_core_tick.py:
# from .episode_blocking import record_attempt_failure, record_episode_success
```

---

## Evidence from Logs

### Log Analysis for "NOTHING"

**Timeline**:
1. **12:39:28** - S1 entry executed (from earlier logs, not shown in recent tail)
2. **14:11:45** - S1 entry blocked (reason: "already_bought_in_s1")
3. **14:13:18** - Position in S2 state (prev_state=S0) - **This is wrong! Should be S1→S2**
4. **14:22:54** - S2 entry executed successfully
5. **No EPISODE_BLOCK logs found** - `record_attempt_failure` was never called

**Key Log Entries**:
```
2025-12-30 14:11:45,082 - PLAN ACTIONS START: NOTHING/solana tf=1m | state=S1 prev_state=S0
2025-12-30 14:11:45,287 - PLAN ACTIONS: BLOCKED buy_signal (S1) | reason: already_bought_in_s1
2025-12-30 14:13:18,673 - PLAN ACTIONS START: NOTHING/solana tf=1m | state=S2 prev_state=S0
2025-12-30 14:22:54,172 - PLAN ACTIONS START: NOTHING/solana tf=1m | state=S2 prev_state=S0 | buy_flag=True
2025-12-30 14:22:54,272 - PLAN ACTIONS: S2 dip buy | NOTHING/solana tf=1m
2025-12-30 14:23:09,518 - EXECUTION RESULT: entry NOTHING/solana | status=success
```

**Missing Logs**:
- ❌ No "EPISODE_BLOCK: Recording S1 failure" log
- ❌ No "EPISODE_BLOCK: Entry blocked" log for S2
- ❌ No `record_attempt_failure` calls

---

## What Should Happen (Per Implementation Doc)

**From `docs/implementation/scaling_ae_v2_implementation.md` (lines 974-979)**:

| Callback | When to Call | Where in Code |
|----------|--------------|---------------|
| `record_attempt_failure(S1)` | Attempt ends at S0 AND `entered_s1 == True` | `pm_core_tick._process_episode_logging()` |
| `record_attempt_failure(S2)` | Attempt ends at S0 AND `entered_s2 == True` | `pm_core_tick._process_episode_logging()` |

**Expected Code** (what should be there):
```python
# When S1 episode ends at S0
elif state == "S0" and prev_state in ("S1", "S2"):
    outcome = "failure"
    self._update_episode_outcomes_from_meta(s1_episode, outcome)
    
    # ✅ MISSING: Record blocking failure
    if s1_episode.get("entered"):
        from .episode_blocking import record_attempt_failure
        record_attempt_failure(
            sb_client=self.sb,
            token_contract=position.get("token_contract"),
            token_chain=position.get("token_chain"),
            timeframe=position.get("timeframe"),
            entered_s1=s1_episode.get("entered", False),
            entered_s2=False,  # S2 episode handled separately
            book_id=position.get("book_id", "onchain_crypto")
        )
    
    s1_episode.pop("active_window", None)
    # ... rest of code
```

---

## Additional Issues Found

### Issue 1: State Transition Tracking

**Problem**: Logs show `prev_state=S0` when transitioning to S2, which suggests state tracking is broken:
```
2025-12-30 14:13:18,673 - state=S2 prev_state=S0
2025-12-30 14:22:54,172 - state=S2 prev_state=S0
```

**Expected**: Should show `prev_state=S1` if coming from S1, or proper state tracking.

**Impact**: May affect episode lifecycle detection.

### Issue 2: Episode Entry Flags

**Problem**: Need to verify that `s1_episode.get("entered")` and `s2_episode.get("entered")` are correctly set when entries happen.

**Location**: `_update_episode_entry_flags()` (line 1083)

**Need to Check**: 
- Are entry flags set when S1/S2 buys execute?
- Are they preserved through state transitions?

### Issue 3: Success Recording

**Problem**: `record_episode_success` is also likely not being called when episodes reach S3.

**Expected**: Should be called when:
- S1 episode reaches S3 (line 1220)
- S2 episode reaches S3 (line 1264)

---

## Verification Steps

### Step 1: Check Database

Query `token_timeframe_blocks` table:
```sql
SELECT * FROM token_timeframe_blocks 
WHERE token_contract LIKE '%NOTHING%' 
   OR token_contract = '<actual_contract>';
```

**Expected**: Should have a row with `blocked_s1=True, blocked_s2=True` after S1 failure.

**Actual**: Likely no row exists (failure never recorded).

### Step 2: Check Episode Meta

Query position features for episode entry flags:
```sql
SELECT 
    id,
    token_contract,
    features->'uptrend_episode_meta'->'s1_episode'->>'entered' as s1_entered,
    features->'uptrend_episode_meta'->'s2_episode'->>'entered' as s2_entered
FROM lowcap_positions
WHERE token_ticker = 'NOTHING';
```

**Expected**: `s1_entered` should be `true` if S1 entry happened.

### Step 3: Check Logs for Blocking Calls

```bash
grep -i "EPISODE_BLOCK" logs/pm_core.log
```

**Expected**: Should see "Recording S1 failure" and "Entry blocked" messages.

**Actual**: No messages found (functions never called).

---

## Summary

### What's Working
- ✅ Blocking functions exist and are correct (`episode_blocking.py`)
- ✅ Blocking checks exist in `actions.py` (lines 827, 993)
- ✅ Database schema exists (`token_timeframe_blocks`)

### What's Broken
- ❌ **`record_attempt_failure` is NEVER called** when episodes fail
- ❌ **`record_episode_success` is likely NEVER called** when episodes succeed
- ❌ **No import** of `episode_blocking` in `pm_core_tick.py`
- ❌ **State transition tracking** may be broken (prev_state=S0 when should be S1)

### Impact
- **Critical**: Blocking system is completely non-functional
- S1/S2 failures are not recorded
- Re-entries are allowed after failures
- System has no protection against repeated failures on same token

---

## Required Fixes

### Fix 1: Add Import
```python
# In pm_core_tick.py, add to imports:
from ..pm.episode_blocking import record_attempt_failure, record_episode_success
```

### Fix 2: Call `record_attempt_failure` on S1 Failure
```python
# In _process_episode_logging(), around line 1240:
elif state == "S0" and prev_state in ("S1", "S2"):
    outcome = "failure"
    self._update_episode_outcomes_from_meta(s1_episode, outcome)
    
    # Record blocking failure if we entered
    if s1_episode.get("entered"):
        record_attempt_failure(
            sb_client=self.sb,
            token_contract=position.get("token_contract"),
            token_chain=position.get("token_chain"),
            timeframe=position.get("timeframe"),
            entered_s1=True,
            entered_s2=False,
            book_id=position.get("book_id", "onchain_crypto")
        )
    
    # ... rest of existing code
```

### Fix 3: Call `record_attempt_failure` on S2 Failure
```python
# In _process_episode_logging(), around line 1285:
elif state == "S0":
    outcome = "failure"
    self._update_episode_outcomes_from_meta(s2_episode, outcome)
    
    # Record blocking failure if we entered
    if s2_episode.get("entered"):
        # Check if S1 also failed in this attempt
        s1_episode = meta.get("s1_episode")
        entered_s1 = s1_episode.get("entered", False) if s1_episode else False
        
        record_attempt_failure(
            sb_client=self.sb,
            token_contract=position.get("token_contract"),
            token_chain=position.get("token_chain"),
            timeframe=position.get("timeframe"),
            entered_s1=entered_s1,
            entered_s2=True,
            book_id=position.get("book_id", "onchain_crypto")
        )
    
    # ... rest of existing code
```

### Fix 4: Call `record_episode_success` on Success
```python
# When S1 episode reaches S3 (around line 1220):
if state == "S3":
    outcome = "success"
    self._update_episode_outcomes_from_meta(s1_episode, outcome)
    
    # Record success to unblock
    record_episode_success(
        sb_client=self.sb,
        token_contract=position.get("token_contract"),
        token_chain=position.get("token_chain"),
        timeframe=position.get("timeframe"),
        book_id=position.get("book_id", "onchain_crypto")
    )
    
    # ... rest of existing code
```

### Fix 5: Verify State Transition Tracking
- Check why `prev_state=S0` when transitioning to S2
- Ensure `meta["prev_state"]` is correctly updated
- May need to fix state transition detection logic

---

## Testing After Fix

1. **Create test position** in S1
2. **Execute S1 entry**
3. **Force S0 transition** (simulate failure)
4. **Verify** `token_timeframe_blocks` has `blocked_s1=True, blocked_s2=True`
5. **Try S2 entry** - should be blocked
6. **Check logs** for "EPISODE_BLOCK: Entry blocked" message

---

## Conclusion

**The blocking system was never integrated into the episode lifecycle.** The functions exist, the checks exist, but the failure recording is missing. This is a critical gap in the implementation - the system has no protection against repeated failures on the same token.

**Priority**: **CRITICAL** - This is a core risk control mechanism that is completely non-functional.

