# Episode Failure Blocking - Log Investigation Results

## Summary

**Problem Found**: Episode blocking IS working in some cases (S2 entries are being blocked), but failure recording appears to be missing or not triggering correctly.

## Evidence from Logs

### ✅ Episode Blocking IS Working (Some Cases)

Found multiple instances of successful blocking:
```
2026-01-04 15:31:18 - PLAN ACTIONS: BLOCKED S2 entry (episode block) | SOAR/solana tf=15m | reason: token blocked until success observed
2026-01-04 18:16:35 - PLAN ACTIONS: BLOCKED S2 entry (episode block) | SOAR/solana tf=15m | reason: token blocked until success observed
```

This shows that `is_entry_blocked()` is working and blocking entries.

### ❌ Failure Recording NOT Found

**Critical Finding**: No logs found for:
- `"EPISODE_BLOCK: Recording S1 failure"`
- `"EPISODE_BLOCK: Recording S2 failure"`
- `"EPISODE_BLOCK: Recording attempt failure"`

This suggests `record_attempt_failure()` is **NEVER being called**, even though failures are happening.

### ✅ S0 Transitions Found

Found multiple S0 transitions from S1 and S2:
```
2026-01-05 06:54:02 - state=S0 prev_state=S2 | TRAX/solana tf=1m
2026-01-04 17:00:21 - state=S0 prev_state=S1 | TRAX/solana tf=1m
2026-01-03 21:15:30 - state=S0 prev_state=S1 | SOAR/solana tf=15m
```

These are the exact conditions where `record_attempt_failure()` should be called.

### ❌ No "Failed to record attempt failure" Warnings

No logs found for:
- `"Failed to record attempt failure for blocking"`
- `"Failed to record episode success for blocking"`

This suggests the try/except blocks are not even being entered, meaning the conditions are not being met.

## Root Cause Analysis

### Code Flow for Failure Recording

**Location**: `pm_core_tick.py` lines 1279-1301 (S1) and 1355-1380 (S2)

**S1 Failure Recording** (lines 1279-1301):
```python
elif state == "S0" and prev_state in ("S1", "S2"):
    outcome = "failure"
    self._update_episode_outcomes_from_meta(s1_episode, outcome)
    
    # Record blocking failure if we entered S1
    if s1_episode.get("entered"):  # ← KEY CONDITION
        try:
            record_attempt_failure(...)
        except Exception as e:
            logger.warning(f"Failed to record attempt failure for blocking: {e}")
```

**S2 Failure Recording** (lines 1355-1380):
```python
elif state == "S0":
    outcome = "failure"
    self._update_episode_outcomes_from_meta(s2_episode, outcome)
    
    # Record blocking failure if we entered S2
    if s2_episode.get("entered"):  # ← KEY CONDITION
        try:
            record_attempt_failure(...)
        except Exception as e:
            logger.warning(f"Failed to record attempt failure for blocking: {e}")
```

### The Problem

**Hypothesis**: `s1_episode.get("entered")` or `s2_episode.get("entered")` is **False** when failures happen, so `record_attempt_failure()` is never called.

**Why `entered` might be False**:

1. **Episode Not Created**: Episode might not exist when failure happens
2. **Entry Not Recorded**: `last_s1_buy` or `last_s2_buy` might not be in execution_history
3. **Entry Flag Not Updated**: `_update_episode_entry_flags()` might not be setting `entered=True`
4. **Timing Issue**: Entry happens but episode fails before `entered` flag is updated

### How `entered` Flag is Set

**Location**: `pm_core_tick.py` `_update_episode_entry_flags()` (lines 1087-1155)

**S1 Entry Flag** (lines 1090-1106):
```python
last_s1_buy = execution_history.get("last_s1_buy") or {}
last_ts = last_s1_buy.get("timestamp")
if last_ts:
    episode = meta.get("s1_episode")
    consumed = meta.get("last_consumed_s1_buy_ts")
    if episode and consumed != last_ts:
        started_at = episode.get("started_at")
        started_dt = self._iso_to_datetime(started_at)
        ts_dt = self._iso_to_datetime(last_ts)
        if started_dt and ts_dt and ts_dt >= started_at:  # ← Must be after episode start
            episode["entered"] = True
```

**S2 Entry Flag** (lines 1108-1124):
```python
last_s2_buy = execution_history.get("last_s2_buy") or {}
last_s2_ts = last_s2_buy.get("timestamp")
if last_s2_ts:
    s2_episode = meta.get("s2_episode")
    consumed = meta.get("last_consumed_s2_buy_ts")
    if s2_episode and consumed != last_s2_ts:
        started_at = s2_episode.get("started_at")
        started_dt = self._iso_to_datetime(started_at)
        ts_dt = self._iso_to_datetime(last_s2_ts)
        if started_dt and ts_dt and ts_dt >= started_at:  # ← Must be after episode start
            s2_episode["entered"] = True
```

### Potential Issues

1. **Episode Start Timing**: Episode might start AFTER entry happens
   - S1 episode starts: `S2 → S1` (retest phase)
   - But entry might have happened in initial `S0 → S1` transition
   - So `entered` never gets set to True

2. **Entry Not in Execution History**: `last_s1_buy` or `last_s2_buy` might not be set
   - Check if `_update_execution_history()` is setting these correctly
   - Check if entries are actually happening

3. **Episode Not Created**: Episode might not exist when failure happens
   - S1 episode only created on `S2 → S1` transition (retest)
   - If failure happens before retest, no episode exists

4. **Timing Issue**: Entry happens but episode fails in same tick
   - `_update_episode_entry_flags()` might run after failure check
   - Or episode might be cleared before `entered` is set

## Specific Case Analysis: SOAR/solana tf=15m

**Timeline from logs**:
- `2026-01-03 21:15:30` - `state=S0 prev_state=S1` (failure)
- `2026-01-04 15:31:18` - `BLOCKED S2 entry (episode block)` (blocking working)

**Questions**:
1. Was there an S1 entry before the failure?
2. Was an S1 episode created?
3. Was `entered=True` set?
4. Why wasn't `record_attempt_failure()` called?

## Missing Logs

**What We Need to See**:
1. Episode creation: `"PHASE7: Started S1 episode"` or `"PHASE7: Started S2 episode"`
2. Entry flag update: Log when `entered=True` is set
3. Failure recording: `"EPISODE_BLOCK: Recording S1 failure"` or `"EPISODE_BLOCK: Recording S2 failure"`
4. Episode state on failure: Log episode state when S0 transition happens

## Next Steps

1. **Add Diagnostic Logging**:
   - Log when episodes are created
   - Log when `entered=True` is set
   - Log episode state when S0 transition happens
   - Log why `record_attempt_failure()` is not called (if `entered=False`)

2. **Check Entry Recording**:
   - Verify `last_s1_buy` and `last_s2_buy` are being set in execution_history
   - Check if entries are actually happening before failures

3. **Check Episode Creation**:
   - Verify episodes are being created at the right time
   - Check if episodes exist when failures happen

4. **Check Timing**:
   - Verify `_update_episode_entry_flags()` is called before failure check
   - Check if there's a race condition

## Conclusion

The blocking mechanism IS working (entries are being blocked), but failure recording is NOT happening. This suggests:

1. **Either**: Episodes don't have `entered=True` when failures happen
2. **Or**: Episodes don't exist when failures happen
3. **Or**: There's a logic issue preventing `record_attempt_failure()` from being called

The most likely issue is that `entered` is False because:
- Episodes are created after entries happen (S1 retest phase)
- Or entries aren't being recorded in execution_history
- Or `_update_episode_entry_flags()` isn't setting `entered=True`

More diagnostic logging is needed to pinpoint the exact issue.

