# Position Closure Trigger - Exact Conditions & Verification

## Critical: Without This, Learning System Doesn't Work

**If position closure doesn't trigger correctly, the learning system never gets data.**

---

## Exact Trigger Conditions

### Both Conditions Must Be True

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Method**: `_check_position_closure()` (lines 2223-2280)

**Conditions** (ALL must be true):
1. ✅ **State == "S0"** (line 2254)
2. ✅ **current_trade_id exists** (line 2276)
3. ✅ **status != "watchlist"** (line 2272) - not already closed
4. ✅ **total_quantity == 0** (line 2317) - position fully closed

**Code**:
```python
def _check_position_closure(...):
    # Condition 1: State must be S0
    if state != "S0":
        return False
    
    # Condition 2: Must have current_trade_id
    if not current_pos.get("current_trade_id"):
        return False
    
    # Condition 3: Must not already be closed
    if current_pos.get("status") == "watchlist":
        return False
    
    # Calls _close_trade_on_s0_transition() which checks:
    # Condition 4: total_quantity must be 0
    return self._close_trade_on_s0_transition(...)
```

**In `_close_trade_on_s0_transition()`** (line 2317):
```python
# Only close if position is empty (emergency_exit already sold everything)
if total_quantity > 0:
    return False
```

---

## How total_quantity Becomes 0

### Flow: Emergency Exit → total_quantity = 0 → State S0 → Position Closure

**Step 1: Emergency Exit Executes**
- **When**: `emergency_exit = True` (from uptrend engine)
- **Action**: `plan_actions_v4()` returns `emergency_exit` action with `size_frac = 1.0`
- **Execution**: `executor.execute()` sells 100% of position
- **Result**: `total_quantity = 0` (updated in `_update_position_after_execution()`)

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` (lines 1551-1563)

**Code**:
```python
# In _update_position_after_execution() for trim/emergency_exit
updates["total_quantity"] = max(0.0, current_quantity - tokens_sold)
# If tokens_sold == current_quantity, then total_quantity = 0
```

**Step 2: State Transitions to S0**
- **When**: Uptrend engine detects S0 conditions (all EMAs below EMA333, or full bearish order)
- **Action**: State changes from S1/S2/S3 → S0
- **Note**: This happens **separately** from emergency exit (can happen in same tick or different tick)

**Step 3: Position Closure Check**
- **When**: After all actions executed, `_check_position_closure()` is called (line 3072)
- **Checks**: State == S0 AND current_trade_id exists AND total_quantity == 0
- **If all pass**: Calls `_close_trade_on_s0_transition()` → triggers learning system

---

## The Critical Sequence

```
1. Emergency Exit Executes
   ↓
   total_quantity = 0 (position emptied)
   ↓
2. State Transitions to S0 (same tick or next tick)
   ↓
3. _check_position_closure() runs
   ↓
   Checks: state == S0 ✅ AND current_trade_id exists ✅ AND total_quantity == 0 ✅
   ↓
4. _close_trade_on_s0_transition() executes
   ↓
   Calculates R/R, emits position_closed strand, triggers learning system
```

---

## Potential Issues

### Issue 1: State S0 but total_quantity > 0

**Scenario**: State transitions to S0 but emergency exit hasn't executed yet (or failed)

**Result**: `_check_position_closure()` returns False (line 2317)

**Impact**: Position won't close, learning system won't trigger

**Fix**: Emergency exit should always execute before state S0, OR we need to handle this case

---

### Issue 2: total_quantity == 0 but State != S0

**Scenario**: Emergency exit executed but state hasn't transitioned to S0 yet

**Result**: `_check_position_closure()` returns False (line 2254)

**Impact**: Position won't close until state transitions to S0

**Note**: This is **expected behavior** - we wait for S0 confirmation before closing

---

### Issue 3: No current_trade_id

**Scenario**: Position has no current_trade_id (edge case)

**Result**: `_check_position_closure()` returns False (line 2276)

**Impact**: Position won't close

**Note**: This shouldn't happen in normal flow, but is a safety check

---

## Verification Steps

### 1. Check if Positions Are Closing

**SQL Query**:
```sql
-- Find positions that should have closed but didn't
SELECT 
    id,
    status,
    total_quantity,
    current_trade_id,
    features->'uptrend_engine_v4'->>'state' as state,
    closed_at
FROM lowcap_positions
WHERE 
    status != 'watchlist'
    AND (features->'uptrend_engine_v4'->>'state' = 'S0' OR total_quantity = 0)
ORDER BY updated_at DESC
LIMIT 20;
```

**What to look for**:
- Positions with `state = 'S0'` but `status != 'watchlist'` → **BUG**
- Positions with `total_quantity = 0` but `status != 'watchlist'` → **BUG**
- Positions with `state = 'S0'` AND `total_quantity = 0` but `status != 'watchlist'` → **CRITICAL BUG**

---

### 2. Check if position_closed Strands Are Created

**SQL Query**:
```sql
-- Count position_closed strands in last 24 hours
SELECT 
    COUNT(*) as count,
    DATE_TRUNC('hour', created_at) as hour
FROM ad_strands
WHERE 
    kind = 'position_closed'
    AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```

**What to look for**:
- If count = 0 but positions have closed → **BUG** (strands not being created)
- If count > 0 → Check if learning system processed them

---

### 3. Check if Learning System Processed Strands

**SQL Query**:
```sql
-- Check if pattern_trade_events were created (learning system worked)
SELECT 
    COUNT(*) as event_count,
    DATE_TRUNC('hour', timestamp) as hour
FROM pattern_trade_events
WHERE 
    timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```

**What to look for**:
- If `event_count = 0` but `position_closed` strands exist → **BUG** (learning system not processing)
- If `event_count > 0` → Learning system is working ✅

---

### 4. Check Logs

**File**: `logs/pm_core.log`

**Look for**:
```
Position {id} closed on S0 transition - emitted position_closed strand
Learning system processed position_closed strand: {id}
```

**If missing**: Learning system not being called

**File**: `logs/learning_system.log`

**Look for**:
```
Processing position_closed strand for learning updates
Successfully processed position_closed strand for pattern scope aggregation
```

**If missing**: Learning system not processing strands

---

## Test Cases

### Test Case 1: Normal Closure Flow

**Setup**:
1. Position in S3 with tokens
2. Emergency exit executes → `total_quantity = 0`
3. State transitions to S0

**Expected**:
- `_check_position_closure()` returns True
- `_close_trade_on_s0_transition()` executes
- `position_closed` strand created
- Learning system processes strand
- `pattern_trade_events` row created

---

### Test Case 2: State S0 but total_quantity > 0

**Setup**:
1. Position in S3 with tokens
2. State transitions to S0 (but emergency exit hasn't executed)

**Expected**:
- `_check_position_closure()` returns False (line 2317)
- Position doesn't close
- **Question**: Should we trigger emergency exit here?

---

### Test Case 3: total_quantity == 0 but State != S0

**Setup**:
1. Position in S3 with tokens
2. Emergency exit executes → `total_quantity = 0`
3. State still S3 (hasn't transitioned to S0 yet)

**Expected**:
- `_check_position_closure()` returns False (line 2254)
- Position doesn't close until state transitions to S0
- **This is expected** - we wait for S0 confirmation

---

## Recommendations

### 1. Add Logging

**Add to `_check_position_closure()`**:
```python
if state == "S0" and current_pos.get("current_trade_id"):
    total_quantity = float(current_pos.get("total_quantity", 0.0))
    if total_quantity > 0:
        logger.warning(
            f"Position {position_id} in S0 but total_quantity > 0: {total_quantity}. "
            f"Waiting for emergency exit to complete."
        )
    else:
        logger.info(
            f"Position {position_id} ready to close: state=S0, total_quantity=0, "
            f"current_trade_id={current_pos.get('current_trade_id')}"
        )
```

### 2. Add Metrics

Track:
- Positions in S0 with `total_quantity > 0` (should be 0 or very low)
- Positions with `total_quantity = 0` but `status != 'watchlist'` (should close quickly)
- Time between emergency exit and position closure (should be < 1 tick)

### 3. Add Safety Check

**In `_close_trade_on_s0_transition()`**:
```python
# Double-check total_quantity is 0
if total_quantity > 0:
    logger.error(
        f"CRITICAL: Attempting to close position {position_id} but "
        f"total_quantity = {total_quantity} > 0. This should not happen."
    )
    return False
```

---

## Summary

**Trigger Conditions** (ALL must be true):
1. ✅ State == "S0"
2. ✅ current_trade_id exists
3. ✅ status != "watchlist"
4. ✅ total_quantity == 0

**Flow**:
```
Emergency Exit → total_quantity = 0 → State S0 → Position Closure → Learning System
```

**Critical**: If any condition fails, learning system doesn't trigger.

**Verification**: Check logs, database queries, and metrics to ensure positions are closing correctly.

