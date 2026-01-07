# Dip Pool Rebuy Analysis - Log Investigation Results

## Summary

**Problem Found**: Pools ARE being created on trims, but they're NOT being found when S2 buy_flag fires later.

## Evidence from Logs

### ✅ Pools ARE Being Created

Multiple examples of successful pool creation:
```
2026-01-05 06:30:58 - TRIM_POOL: Updated pool with $11.85 trim | position=f7c8dc9f-7acc-4d6e-a441-665a67945995
2026-01-05 07:15:54 - TRIM_POOL: Updated pool with $6.52 trim | position=f7c8dc9f-7acc-4d6e-a441-665a67945995
2026-01-05 10:01:02 - TRIM_POOL: Updated pool with $2.41 trim | position=f7c8dc9f-7acc-4d6e-a441-665a67945995
```

### ❌ Pools NOT Found When S2 Buy Flag Fires

When S2 buy_flag fires, logs show:
```
PLAN ACTIONS: S2 buy_flag | MACARON/solana tf=1h | 
is_flat=False has_pool=False (basis=$0.00) recovery_started=False → can_s2_dip=False
PLAN ACTIONS: BLOCKED S2 dip buy | reason: no_pool_or_recovery_started | 
has_pool=False recovery_started=False
```

**Pattern**: Even positions that had trims (and should have pools) show `has_pool=False (basis=$0.00)` when S2 buy_flag fires.

### ✅ Only 2 Successful S2 Dip Buys from Pool

Only 2 instances found where S2 dip buy used a pool:
1. `2026-01-05 05:46:44 - TRIM_POOL: S2 dip buy $1.78 from pool, locked $1.45 profit | position=becdf881-27f0-4c6d-aa41-5132ea76bab1`
2. `2026-01-02 14:16:55 - TRIM_POOL: S2 dip buy $0.79 from pool, locked $0.81 profit | position=6829fb89-5b4e-49b9-b468-8dd13fc9b940`

But note: The second one shows `is_flat=True` in the planning log, so it wasn't actually using the pool - it was a flat entry.

## Root Cause Analysis

### Code Flow

1. **Trim Execution** (`pm_core_tick.py`):
   - Executor executes trim
   - `_update_execution_history()` is called
   - `_on_trim()` updates `exec_history["trim_pool"]`
   - Pool is saved to `position.features.pm_execution_history.trim_pool`

2. **S2 Buy Flag Planning** (`actions.py`):
   - `plan_actions_v4()` is called
   - Reads `exec_history = features.get("pm_execution_history") or {}`
   - Calls `pool = _get_pool(exec_history)`
   - Checks `has_pool = pool_basis > 0`

### The Problem

**Hypothesis**: The pool is being saved to the database, but when `plan_actions_v4()` reads the position from the database, the pool is missing or not being loaded correctly.

**Possible Causes**:

1. **Timing Issue**: `plan_actions_v4()` is called before the pool update is committed to the database
2. **Data Not Persisted**: Pool update is not being saved to database properly
3. **Stale Position Data**: Position is read from cache or stale database state
4. **Pool Cleared Prematurely**: Pool is being cleared somewhere between trim and S2 buy_flag
5. **Different Position Instance**: Pool is saved to one position instance but read from another (race condition)

### Where to Check

1. **`_update_execution_history()` in `pm_core_tick.py`** (line 1905):
   - Verify pool is being saved: `features["pm_execution_history"] = execution_history`
   - Verify database update includes features: `self.sb.table("lowcap_positions").update({"features": features})`

2. **Position Loading in `pm_core_tick.py`**:
   - Check where position is loaded before calling `plan_actions_v4()`
   - Verify it's reading fresh data from database, not cached

3. **Pool Clearing Logic**:
   - Check if pool is being cleared in `_on_s2_dip_buy()` correctly
   - Verify pool isn't being cleared elsewhere

## Logging Gaps

**Missing Logs That Would Help**:

1. **Pool State on Position Load**:
   - Log pool state when position is loaded from database
   - Log: `"LOADED POSITION: pool_basis=$X.XX from exec_history"`

2. **Pool Save Confirmation**:
   - Log after saving pool to database
   - Log: `"SAVED POOL: pool_basis=$X.XX to position.features"`

3. **Pool Retrieval in plan_actions_v4**:
   - Already logs `has_pool` but could log the actual pool structure
   - Log: `"POOL STATE: {pool}"` before checking `has_pool`

## Next Steps

1. **Add Diagnostic Logging**:
   - Log pool state when position is loaded
   - Log pool state when saved
   - Log full pool structure in `plan_actions_v4()` before checking

2. **Check Database**:
   - Query `lowcap_positions` table directly
   - Check `features->pm_execution_history->trim_pool` for positions with recent trims
   - Verify pools are actually in the database

3. **Check Timing**:
   - Verify `_update_execution_history()` completes before next PM tick
   - Check if there's a race condition between save and read

4. **Check Position Loading**:
   - Verify position is loaded fresh from database in each PM tick
   - Check if there's any caching that might return stale data

## Conclusion

The logs show a clear pattern:
- ✅ Pools ARE created on trims
- ❌ Pools are NOT found when S2 buy_flag fires
- This suggests a **data persistence or retrieval issue**, not a logic issue

The problem is likely in:
1. How the pool is saved to the database, OR
2. How the position is loaded from the database before planning

More diagnostic logging is needed to pinpoint exactly where the pool is being lost.

