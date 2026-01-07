# Episode System Investigation

**Date**: 2025-01-XX  
**Purpose**: Comprehensive investigation of episode system functionality

---

## Overview

The episode system tracks trading opportunities (S1 entry, S2 entry, S3 retest) and logs:
1. **Decisions**: Acted vs Skipped
2. **Outcomes**: Success vs Failure vs Neutral
3. **Factors**: Signal values at decision time (TS scores, DX values, A values, etc.)

Episodes are logged to `pattern_episode_events` table and create `uptrend_episode_summary` strands.

---

## Episode Types

### 1. S1 Entry Episodes
- **Start**: State transition `S2 → S1` (retest phase, after S2 breakout)
- **End**: 
  - **Success**: Reaches `S3`
  - **Failure**: Returns to `S0`
- **Windows**: Tracked when `entry_zone_ok = True` (TS/halo/slope gates satisfied)
- **Logging**: `logger.debug("PHASE7: Started S1 episode (retest phase) %s for position", episode_id)`

### 2. S2 Entry Episodes
- **Start**: State transition `S1 → S2` (first time in attempt)
- **End**:
  - **Success**: Reaches `S3`
  - **Failure**: Returns to `S0`
- **Windows**: Tracked when `buy_flag = True` and `entry_zone_ok = True` in S2 state
- **Logging**: `logger.debug("PHASE7: Started S2 episode %s for position", episode_id)`

### 3. S3 Retest Episodes
- **Start**: State transition to `S3` (from any state)
- **End**: 
  - **Success**: Trim occurs (virtual success if episode trimmed)
  - **Failure**: Returns to `S0`
- **Windows**: Tracked during S3 state (retest opportunities)
- **Logging**: No explicit start log (episode created silently)

---

## Code Flow

### Episode Processing Entry Point
**Location**: `pm_core_tick.py:3622`
```python
episode_strands, meta_changed = self._process_episode_logging(
    position=p,
    regime_context=regime_context,
    token_bucket=token_bucket,
    now=now,
    levers=le, # Pass levers for factor logging
)
```

**Called from**: `_update_position()` method during position updates

### Episode Event Logging
**Location**: `pm_core_tick.py:620-647`
```python
def _log_episode_event(
    self,
    window: Dict[str, Any],
    scope: Dict[str, Any],
    pattern_key: str,
    decision: str,
    factors: Dict[str, Any],
    episode_id: str,
    trade_id: Optional[str] = None,
) -> Optional[int]:
    """Log an episode event to pattern_episode_events table."""
    try:
        payload = {
            "scope": scope,
            "pattern_key": pattern_key,
            "episode_id": episode_id,
            "decision": decision,
            "factors": factors,
            "outcome": None, # Pending
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trade_id": trade_id
        }
        res = self.sb.table("pattern_episode_events").insert(payload).execute()
        if res.data:
            return res.data[0].get("id")
    except Exception as e:
        logger.warning(f"Failed to log episode event: {e}")
    return None
```

### Episode Outcome Updates
**Location**: `pm_core_tick.py:649-656`
```python
def _update_episode_outcome(self, db_ids: List[int], outcome: str) -> None:
    """Update outcome for a list of episode event IDs."""
    if not db_ids:
        return
    try:
        self.sb.table("pattern_episode_events").update({"outcome": outcome}).in_("id", db_ids).execute()
    except Exception as e:
        logger.warning(f"Failed to update episode outcomes: {e}")
```

---

## Key Log Messages to Check

### Episode Start Logs
- `"PHASE7: Started S1 episode (retest phase) %s for position"` - S1 episode start
- `"PHASE7: Started S2 episode %s for position"` - S2 episode start
- `"PHASE7: Opened S2 window for position"` - S2 window opened

### Episode Outcome Logs
- `"PHASE7: S2 episode success for position"` - S2 episode succeeded
- `"PHASE7: S2 episode failure for position"` - S2 episode failed
- `"PHASE7: Updated %d DX episodes to success"` - DX episode outcomes
- `"PHASE7: Updated %d DX episodes to failure"` - DX episode outcomes

### Error Logs
- `"Failed to log episode event: {e}"` - Episode event logging failed
- `"Failed to update episode outcomes: {e}"` - Outcome update failed
- `"Error finalizing active window logging: {e}"` - Window finalization error

### Episode Summary Strand Creation
- Episode summary strands are created via `_build_episode_summary_strand()` but no explicit log message

---

## Potential Issues to Investigate

### 1. Episode Event Logging Failures
**Check for**: `"Failed to log episode event"` warnings
**Impact**: Events not recorded in `pattern_episode_events` table
**Possible Causes**:
- Database connection issues
- Schema mismatch
- Missing required fields (scope, pattern_key, etc.)

### 2. Episode Outcome Update Failures
**Check for**: `"Failed to update episode outcomes"` warnings
**Impact**: Outcomes remain `NULL` in database
**Possible Causes**:
- Invalid `db_id` values
- Database connection issues
- Race conditions

### 3. Episode Not Starting
**Check for**: Missing `"PHASE7: Started S1/S2 episode"` logs
**Possible Causes**:
- State transitions not happening
- `uptrend_engine_v4` signals missing
- Episode meta not initialized

### 4. Windows Not Being Finalized
**Check for**: Missing episode events for windows that should have closed
**Possible Causes**:
- `_finalize_active_window()` not being called
- Missing position/uptrend_signals context
- Exception in window finalization

### 5. Episode Summary Strands Not Created
**Check for**: Missing `uptrend_episode_summary` strands in `ad_strands` table
**Possible Causes**:
- Episode outcome not determined
- `_build_episode_summary_strand()` not called
- Strand insertion failed silently

---

## Database Queries to Verify

### Check Episode Events Exist
```sql
SELECT 
    COUNT(*) as total_events,
    COUNT(DISTINCT episode_id) as unique_episodes,
    COUNT(DISTINCT pattern_key) as unique_patterns,
    COUNT(*) FILTER (WHERE outcome IS NULL) as pending_outcomes,
    COUNT(*) FILTER (WHERE outcome = 'success') as successes,
    COUNT(*) FILTER (WHERE outcome = 'failure') as failures,
    MIN(timestamp) as earliest_event,
    MAX(timestamp) as latest_event
FROM pattern_episode_events;
```

### Check Episode Events by Pattern
```sql
SELECT 
    pattern_key,
    decision,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE outcome = 'success') as successes,
    COUNT(*) FILTER (WHERE outcome = 'failure') as failures,
    COUNT(*) FILTER (WHERE outcome IS NULL) as pending
FROM pattern_episode_events
GROUP BY pattern_key, decision
ORDER BY pattern_key, decision;
```

### Check Episode Summary Strands
```sql
SELECT 
    COUNT(*) as total_strands,
    COUNT(DISTINCT content->>'episode_id') as unique_episodes,
    COUNT(*) FILTER (WHERE content->>'outcome' = 'success') as successes,
    COUNT(*) FILTER (WHERE content->>'outcome' = 'failure') as failures,
    MIN(created_at) as earliest_strand,
    MAX(created_at) as latest_strand
FROM ad_strands
WHERE kind = 'uptrend_episode_summary';
```

### Check Recent Episode Activity
```sql
SELECT 
    episode_id,
    pattern_key,
    decision,
    outcome,
    timestamp,
    trade_id
FROM pattern_episode_events
ORDER BY timestamp DESC
LIMIT 50;
```

---

## Log Search Queries

### Episode Start Logs
```bash
grep -i "PHASE7: Started.*episode" logs/pm_core.log
```

### Episode Outcome Logs
```bash
grep -i "PHASE7:.*episode.*success\|failure" logs/pm_core.log
```

### Episode Event Logging Errors
```bash
grep -i "Failed to log episode event" logs/pm_core.log
```

### Episode Outcome Update Errors
```bash
grep -i "Failed to update episode outcomes" logs/pm_core.log
```

### Window Finalization Errors
```bash
grep -i "Error finalizing active window" logs/pm_core.log
```

---

## Expected Behavior Checklist

### ✅ Episode Creation
- [ ] S1 episodes start on `S2 → S1` transition (after S2 breakout)
- [ ] S2 episodes start on `S1 → S2` transition (first time)
- [ ] S3 episodes start on transition to `S3`

### ✅ Window Tracking
- [ ] S1 windows open when `entry_zone_ok = True` in S1
- [ ] S2 windows open when `buy_flag = True` and `entry_zone_ok = True` in S2
- [ ] S3 windows track retest opportunities
- [ ] Windows close when conditions no longer met or episode ends

### ✅ Event Logging
- [ ] Events logged to `pattern_episode_events` when windows close
- [ ] Events include correct `decision` (acted/skipped)
- [ ] Events include `factors` (signal values)
- [ ] Events linked to `trade_id` if acted

### ✅ Outcome Updates
- [ ] Outcomes updated to "success" when episode succeeds
- [ ] Outcomes updated to "failure" when episode fails
- [ ] Outcomes remain NULL if pending

### ✅ Episode Summary Strands
- [ ] Strands created when episodes end
- [ ] Strands include episode metadata
- [ ] Strands include outcome information

---

## Critical Issues Found

### 🚨 Issue #1: Silent Failure in Episode Event Logging

**Location**: `pm_core_tick.py:993`

**Problem**: Episode events are only logged if `pattern_key and scope` are both truthy. If `_build_pattern_scope()` throws an exception:
- `pattern_key` becomes `None` (line 1082)
- `scope` becomes `{}` (empty dict, line 1097)
- The check `if pattern_key and scope:` fails (None is falsy)
- Event is NOT logged, but NO warning is generated

**Impact**: 
- Episode events silently fail to log if pattern key generation fails
- No diagnostic information about why events aren't being logged
- Learning system doesn't receive episode data

**Fix Needed**: Add logging when pattern_key or scope generation fails:
```python
if not pattern_key:
    logger.warning(f"Failed to generate pattern_key for episode window: {active.get('window_id')}")
if not scope:
    logger.warning(f"Failed to generate scope for episode window: {active.get('window_id')}")
```

### 🚨 Issue #2: S2 Window Type Detection

**Location**: `pm_core_tick.py:976-978`

**Problem**: The code checks for S1 windows like this:
```python
window_type = active.get("window_type") # s1_buy_signal or None (s3)
is_s1 = window_type == "s1_buy_signal" or (episode.get("episode_id") or "").startswith("s1_")
```

But S2 windows have `window_type = "s2_buy_flag"` (line 1557), so:
- S2 windows won't match `window_type == "s1_buy_signal"`
- S2 episodes have IDs starting with "s2_", not "s1_"
- So `is_s1` will be `False` for S2 windows
- State will be set to "S3" instead of "S2" (line 978)
- This causes incorrect pattern_key generation for S2 episodes

**Impact**:
- S2 episode events may be logged with wrong pattern_key
- S2 episodes may be classified as S3 retest episodes
- Learning system receives incorrect episode data

**Fix Needed**: Add S2 window detection:
```python
window_type = active.get("window_type")
is_s1 = window_type == "s1_buy_signal" or (episode.get("episode_id") or "").startswith("s1_")
is_s2 = window_type == "s2_buy_flag" or (episode.get("episode_id") or "").startswith("s2_")
if is_s1:
    state = "S1"
    action_type = "entry"
elif is_s2:
    state = "S2"
    action_type = "entry"  # S2 is also an entry opportunity
else:
    state = "S3"
    action_type = "add"
```

### 🚨 Issue #3: Missing Diagnostic Logging

**Location**: `pm_core_tick.py:970-1014`

**Problem**: When episode events fail to log, there's no diagnostic information:
- No log when `position` or `uptrend_signals` are missing
- No log when `pattern_key` or `scope` are None/empty
- No log when `_log_episode_event()` returns None (insert failed)

**Impact**: 
- Difficult to diagnose why episodes aren't being logged
- No visibility into silent failures

**Fix Needed**: Add diagnostic logging at each failure point

### ⚠️ Issue #4: S2 Episode State Detection

**Location**: `pm_core_tick.py:977-978`

**Problem**: For S2 windows, the code incorrectly infers state:
- S2 windows have `window_type = "s2_buy_flag"`
- But the check only looks for "s1_buy_signal"
- So S2 windows fall through to `state = "S3"` (line 978)
- This causes S2 episodes to be logged as S3 retest episodes

**Impact**: S2 episode data is misclassified in the database

---

## Next Steps

1. **Check Logs**: Search for episode-related log messages
2. **Query Database**: Verify episode events exist and outcomes are updated
3. **Check Strands**: Verify episode summary strands are created
4. **Identify Gaps**: Find missing episodes or events
5. **Fix Issues**: Address the critical issues found above

---

## Related Documentation

- `docs/investigations/episode_blocking_final_analysis.md` - Episode blocking investigation
- `docs/investigations/episode_based_learning_tuning_deep_dive.md` - Episode system deep dive
- `docs/investigations/learning_system_deep_dive.md` - Learning system integration
- `docs/implementation/phase7_tuning_implementation_notes.md` - Phase 7 implementation status

