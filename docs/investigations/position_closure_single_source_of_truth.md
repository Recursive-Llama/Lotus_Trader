# Position Closure - Single Source of Truth

## The ONE Place That Defines Trade Closure

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Method**: `_close_trade_on_s0_transition()` (lines 2282-2623)

**This is THE place** where:
- ✅ Trade is marked as closed
- ✅ `current_trade_id = None` (wipes trade data)
- ✅ `status = "watchlist"` (marks position as closed)
- ✅ `completed_trades.append()` (saves trade data)
- ✅ `position_closed` strand emitted
- ✅ Learning system triggered

**There is NO other place** that does this.

---

## Exact Conditions to Reach This Place

### Step 1: Position Must Be Processed

**Method**: `_active_positions()` (line 449-464)

**Conditions**:
- ✅ `timeframe` matches PM Core Tick timeframe
- ✅ `status IN ["watchlist", "active"]` (line 460)
- ❌ Skips `dormant` positions

**So**: Both `watchlist` and `active` positions are processed.

---

### Step 2: `_check_position_closure()` Must Return True

**Method**: `_check_position_closure()` (line 2223-2280)

**Called from**: `run()` after all actions executed (line 3072)

**Conditions** (ALL must be true):
1. ✅ **State == "S0"** (line 2254)
2. ✅ **status != "watchlist"** (line 2272) - not already closed
3. ✅ **current_trade_id exists** (line 2276) - has an open trade

**If all pass**: Calls `_close_trade_on_s0_transition()`

---

### Step 3: `_close_trade_on_s0_transition()` Must Complete

**Method**: `_close_trade_on_s0_transition()` (line 2282-2623)

**Current Conditions** (line 2317):
- ❌ **total_quantity == 0** (blocks if > 0) ← **PROBLEM**

**What it does**:
1. Calculates R/R metrics
2. Builds `trade_summary`
3. **Wipes trade data** (lines 2525-2532):
   - `current_trade_id = None`
   - `status = "watchlist"`
   - `completed_trades.append(trade_cycle_entry)`
   - `closed_at = exit_timestamp`
4. Emits `position_closed` strand (line 2601)
5. Triggers learning system (line 2610)

---

## The Complete Condition Chain

```
Position Processed (watchlist OR active)
  ↓
State == S0 ✅
  ↓
status != "watchlist" ✅ (not already closed)
  ↓
current_trade_id exists ✅ (has open trade)
  ↓
_close_trade_on_s0_transition() called
  ↓
total_quantity == 0 ❌ (BLOCKS if > 0) ← PROBLEM
  ↓
Trade Closed (wipe + learning)
```

---

## Is This The Perfect Place?

### ✅ YES - This IS the perfect place because:

1. **Single Source of Truth**: Only place that defines trade closure
2. **Complete Logic**: Does everything (wipe, save, learn)
3. **State-Based**: Uses S0 (trade ended signal), not action-based
4. **Called After Actions**: Runs after all actions executed (line 3072)

### ❌ BUT - The conditions are wrong:

**Problem 1**: `total_quantity == 0` check (line 2317)
- Blocks closure if 0.001 tokens left (rounding error)
- Blocks closure if emergency exit partially failed
- **Should be**: Remove check OR use threshold (0.01)

**Problem 2**: Position doesn't need to be "active"
- Processes both `watchlist` and `active` positions
- But checks `status != "watchlist"` (line 2272)
- **So**: Only `active` positions can close (watchlist already closed)
- **This is correct**: Only active positions should close

---

## The Real Question

**When should a trade close?**

**Answer**: **When state == S0 AND current_trade_id exists**

That's it. The `total_quantity == 0` check is defensive but wrong.

---

## Recommended Fix

### Remove total_quantity Check (Simplest)

**Change** (line 2316-2318):
```python
# REMOVE THIS:
# if total_quantity > 0:
#     return False

# REPLACE WITH:
# Log warning if we have tokens left, but still close
if total_quantity > 0.01:
    logger.warning(
        f"Position {position_id} closing in S0 but has {total_quantity} tokens left. "
        f"S0 means trade ended - closing anyway."
    )
# Continue with closure...
```

**Rationale**: 
- S0 = trade ended (that's the signal)
- If state is S0, close it regardless of tiny amounts
- Log warning for debugging

---

## Verification: Is This The Only Place?

### Check 1: Search for `current_trade_id = None`

**Result**: Only in `_close_trade_on_s0_transition()` (line 2529)

### Check 2: Search for `completed_trades.append`

**Result**: Only in `_close_trade_on_s0_transition()` (line 2522)

### Check 3: Search for `status = "watchlist"` updates

**Result**: 
- `_close_trade_on_s0_transition()` (line 2527) - closure
- `_update_position_after_execution()` (line 1532) - entry (watchlist → active)
- Test harnesses (not production)

**Conclusion**: ✅ **This IS the only place** that closes trades.

---

## Summary

**Single Source of Truth**: ✅ `_close_trade_on_s0_transition()`

**Conditions**:
1. ✅ Position processed (watchlist OR active)
2. ✅ State == S0
3. ✅ status != "watchlist" (not already closed)
4. ✅ current_trade_id exists
5. ❌ total_quantity == 0 (WRONG - should remove or use threshold)

**Is this the perfect place?**: ✅ **YES** - but fix condition #5

**Recommendation**: Remove `total_quantity > 0` check. S0 means trade ended - close it.

