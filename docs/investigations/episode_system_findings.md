# Episode System Investigation - Critical Findings

**Date**: 2025-01-07  
**Status**: ⚠️ **CRITICAL ISSUES FOUND**

---

## Executive Summary

The episode system is **partially working** but has **critical bugs** that cause:
1. **Silent failures** in episode event logging
2. **Misclassification** of S2 episodes as S3 episodes
3. **Missing diagnostic information** when events fail to log

---

## Critical Issues

### 🚨 Issue #1: S2 Windows Misclassified as S3

**Location**: `pm_core_tick.py:976-978`

**Code**:
```python
window_type = active.get("window_type") # s1_buy_signal or None (s3)
is_s1 = window_type == "s1_buy_signal" or (episode.get("episode_id") or "").startswith("s1_")
state = "S1" if is_s1 else "S3"  # ❌ BUG: S2 windows fall through to S3
```

**Problem**:
- S2 windows have `window_type = "s2_buy_flag"` (line 1557)
- The check only looks for `"s1_buy_signal"` or episode_id starting with "s1_"
- S2 windows don't match either condition
- So `is_s1 = False`, and `state` is set to `"S3"` instead of `"S2"`

**Impact**:
- S2 episode events are logged with wrong `state` ("S3" instead of "S2")
- Pattern keys are generated incorrectly (e.g., "pm.s3_retest" instead of "pm.s2_entry")
- Learning system receives incorrect episode classifications
- S2 episodes appear as S3 retest episodes in database

**Evidence**:
- S2 window creation: `window_type = "s2_buy_flag"` (line 1557)
- No check for S2 in state detection (line 977)
- All non-S1 windows default to S3 (line 978)

**Fix Required**:
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

---

### 🚨 Issue #2: Silent Failure in Episode Event Logging

**Location**: `pm_core_tick.py:993`

**Code**:
```python
if pattern_key and scope:
    # Log event
    db_id = self._log_episode_event(...)
```

**Problem**:
- If `_build_pattern_scope()` throws an exception:
  - `pattern_key = None` (line 1082, caught exception)
  - `scope = {}` (line 1097, caught exception)
- The check `if pattern_key and scope:` fails (None is falsy)
- Event is **NOT logged**, but **NO warning** is generated
- This is a **silent failure**

**Impact**:
- Episode events silently fail to log when pattern key generation fails
- No diagnostic information about why events aren't being logged
- Learning system doesn't receive episode data
- Difficult to debug missing episodes

**Evidence**:
- Exception handling in `_build_pattern_scope()` (lines 1081-1097)
- No logging when pattern_key or scope are None/empty
- No logging when check fails

**Fix Required**:
```python
if not pattern_key:
    logger.warning(
        f"Failed to generate pattern_key for episode window: {active.get('window_id')} | "
        f"window_type={active.get('window_type')} | episode_id={episode.get('episode_id')}"
    )
if not scope:
    logger.warning(
        f"Failed to generate scope for episode window: {active.get('window_id')} | "
        f"position_id={position.get('id')}"
    )

if pattern_key and scope:
    # Log event
    db_id = self._log_episode_event(...)
    if not db_id:
        logger.warning(
            f"Failed to log episode event to database: window_id={active.get('window_id')}"
        )
else:
    logger.warning(
        f"Skipping episode event logging: pattern_key={pattern_key}, scope={bool(scope)} | "
        f"window_id={active.get('window_id')}"
    )
```

---

### ⚠️ Issue #3: Missing Context Validation

**Location**: `pm_core_tick.py:971`

**Code**:
```python
if position and uptrend_signals:
    # Log episode event
```

**Problem**:
- If `position` or `uptrend_signals` are missing, event logging is skipped
- No logging to indicate why events aren't being logged
- Could happen if called incorrectly or if data is missing

**Impact**:
- Silent skipping of episode events when context is missing
- No visibility into why episodes aren't being logged

**Fix Required**:
```python
if not position:
    logger.debug(f"Skipping episode event logging: position is None | window_id={active.get('window_id')}")
    return True  # Still finalize window, just don't log

if not uptrend_signals:
    logger.debug(f"Skipping episode event logging: uptrend_signals is None | window_id={active.get('window_id')}")
    return True  # Still finalize window, just don't log

# Continue with logging...
```

---

### ⚠️ Issue #4: No Logging When db_id is Missing

**Location**: `pm_core_tick.py:1001-1011`

**Code**:
```python
db_id = self._log_episode_event(...)
if db_id:
    active["db_id"] = db_id
```

**Problem**:
- If `_log_episode_event()` returns `None` (insert failed), no warning is logged
- The window is finalized but has no `db_id`
- Outcome updates will fail silently (no db_id to update)

**Impact**:
- Episode events may fail to insert but no error is logged
- Outcome updates will silently fail (no db_id to reference)
- Episodes appear in metadata but not in database

**Fix Required**:
```python
db_id = self._log_episode_event(...)
if db_id:
    active["db_id"] = db_id
else:
    logger.warning(
        f"Failed to get db_id from episode event insert: window_id={active.get('window_id')} | "
        f"episode_id={episode.get('episode_id')} | decision={decision}"
    )
```

---

## Verification Checklist

### Episode Creation
- [x] S1 episodes start on `S2 → S1` transition ✅ (line 1262)
- [x] S2 episodes start on `S1 → S2` transition ✅ (line 1276)
- [x] S3 episodes start on transition to `S3` ✅ (line 1287)

### Window Tracking
- [x] S1 windows open when `entry_zone_ok = True` ✅ (line 1524)
- [x] S2 windows open when `buy_flag = True` and `entry_zone_ok = True` ✅ (line 1552)
- [x] S3 windows track retest opportunities ✅ (line 1587)

### Event Logging
- [ ] Events logged to `pattern_episode_events` when windows close ⚠️ (has bugs)
- [ ] Events include correct `decision` (acted/skipped) ⚠️ (S2 misclassified)
- [ ] Events include `factors` (signal values) ✅
- [ ] Events linked to `trade_id` if acted ✅

### Outcome Updates
- [x] Outcomes updated to "success" when episode succeeds ✅ (line 1316, 1391)
- [x] Outcomes updated to "failure" when episode fails ✅ (line 1348, 1424)
- [x] Outcomes remain NULL if pending ✅

### Episode Summary Strands
- [x] Strands created when episodes end ✅ (line 1332, 1407, 1452)
- [x] Strands include episode metadata ✅
- [x] Strands include outcome information ✅

---

## Recommended Fixes (Priority Order)

### Priority 1: Fix S2 Window Classification
**Impact**: High - Affects all S2 episode data accuracy  
**Effort**: Low - Simple code change  
**Location**: `pm_core_tick.py:976-981`

### Priority 2: Add Diagnostic Logging
**Impact**: High - Enables debugging of missing episodes  
**Effort**: Low - Add logging statements  
**Location**: `pm_core_tick.py:970-1014`

### Priority 3: Validate Context Parameters
**Impact**: Medium - Prevents silent failures  
**Effort**: Low - Add validation checks  
**Location**: `pm_core_tick.py:971`

### Priority 4: Log Database Insert Failures
**Impact**: Medium - Identifies database issues  
**Effort**: Low - Add logging after insert  
**Location**: `pm_core_tick.py:1001-1011`

---

## Testing Recommendations

1. **Verify S2 Episode Classification**:
   - Check database for S2 episodes
   - Verify `pattern_key` contains "s2" not "s3"
   - Verify `state` in scope is "S2" not "S3"

2. **Check for Missing Events**:
   - Query `pattern_episode_events` table
   - Compare with episode metadata in position features
   - Identify episodes with windows but no events

3. **Verify Outcome Updates**:
   - Check for episodes with `outcome IS NULL` that should be updated
   - Verify `db_id` exists in window metadata before outcome update
   - Check for failed outcome updates in logs

4. **Monitor Diagnostic Logs**:
   - After fixes, monitor for pattern_key/scope generation failures
   - Track missing context warnings
   - Verify all episode events are being logged

---

## Conclusion

The episode system is **functionally working** but has **critical bugs** that cause:
- **Data quality issues**: S2 episodes misclassified as S3
- **Silent failures**: Events fail to log without warning
- **Debugging difficulties**: No diagnostic information

**Recommendation**: Fix Priority 1 and 2 issues immediately to ensure data accuracy and enable debugging.

