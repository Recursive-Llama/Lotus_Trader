# Dip Pool Diagnostic Logging - Implementation Summary

## Overview

Added comprehensive diagnostic logging to track dip pool state throughout the system lifecycle. This will help identify where pools are being lost between trim execution and S2/S3 buy planning.

## Logging Points Added

### 1. Position Load for Planning (`pm_core_tick.py`)

**Location**: Before `plan_actions_v4()` is called (line ~3603)

**Log**: `POOL_DIAG: Position loaded for planning`
- Shows pool state when position is loaded from database
- Logs full pool structure if present
- Logs exec_history keys if pool is missing

**Example**:
```
POOL_DIAG: Position loaded for planning | TOKEN/solana tf=1h position_id=xxx | pool={'usd_basis': 11.85, 'recovery_started': False, ...}
```

### 2. S2 Buy Flag Pool Check (`actions.py`)

**Location**: In `plan_actions_v4()` when S2 buy_flag is detected (line ~1013)

**Log**: `POOL_DIAG: S2 buy_flag pool check`
- Shows exec_history keys
- Shows full pool structure
- Shows pool_basis, has_pool, recovery_started

**Example**:
```
POOL_DIAG: S2 buy_flag pool check | TOKEN/solana tf=1h | exec_history_keys=['last_trim', 'trim_pool'] | pool={'usd_basis': 11.85, ...} | pool_basis=$11.85 has_pool=True recovery_started=False
```

### 3. S3 DX Buy Pool Check (`actions.py`)

**Location**: In `plan_actions_v4()` when S3 buy_flag is detected (line ~1118)

**Log**: `POOL_DIAG: S3 buy_flag pool check`
- Shows exec_history keys
- Shows full pool structure
- Shows pool_basis, has_pool, dx_count

**Example**:
```
POOL_DIAG: S3 buy_flag pool check | TOKEN/solana tf=1h | exec_history_keys=['last_trim', 'trim_pool'] | pool={'usd_basis': 11.85, 'dx_count': 0, ...} | pool_basis=$11.85 has_pool=True dx_count=0
```

### 4. Pool Loaded from Database (`pm_core_tick.py`)

**Location**: In `_update_execution_history()` when loading current features (line ~1937)

**Log**: `POOL_DIAG: Loaded pool from DB` or `POOL_DIAG: No pool in exec_history`
- Shows pool state when loading from database before update
- Helps identify if pool was already missing

**Example**:
```
POOL_DIAG: Loaded pool from DB | position=xxx | pool={'usd_basis': 11.85, ...}
```

### 5. Pool Updated on Trim (`pm_core_tick.py`)

**Location**: In `_update_execution_history()` after `_on_trim()` is called (line ~2093)

**Log**: `TRIM_POOL: Updated pool with $X.XX trim` (enhanced)
- Now shows pool_before and pool_after states
- Helps verify pool accumulation is working

**Example**:
```
TRIM_POOL: Updated pool with $11.85 trim | position=xxx | pool_before={'usd_basis': 0.0, ...} pool_after={'usd_basis': 11.85, ...}
```

### 6. Pool Saved to Database (`pm_core_tick.py`)

**Location**: In `_update_execution_history()` before and after database update (line ~2105)

**Log**: `POOL_DIAG: Saving pool to DB` and `POOL_DIAG: Pool save completed`
- Shows pool state before saving
- Confirms save operation succeeded

**Example**:
```
POOL_DIAG: Saving pool to DB | position=xxx | pool={'usd_basis': 11.85, ...}
POOL_DIAG: Pool save completed | position=xxx | update_success=True
```

## Log Search Queries

To track pool lifecycle:

1. **Find all pool diagnostics**:
   ```bash
   grep "POOL_DIAG" logs/pm_core.log
   ```

2. **Track a specific position's pool**:
   ```bash
   grep "position_id=xxx\|position=xxx" logs/pm_core.log | grep -E "POOL_DIAG|TRIM_POOL"
   ```

3. **Find S2 buy attempts with pool state**:
   ```bash
   grep "POOL_DIAG: S2 buy_flag pool check" logs/pm_core.log
   ```

4. **Find S3 DX buy attempts with pool state**:
   ```bash
   grep "POOL_DIAG: S3 buy_flag pool check" logs/pm_core.log
   ```

5. **Find pool saves**:
   ```bash
   grep "POOL_DIAG: Saving pool to DB\|POOL_DIAG: Pool save completed" logs/pm_core.log
   ```

## What This Will Reveal

These logs will help identify:

1. **Pool Persistence**: Is the pool actually being saved to the database?
2. **Pool Retrieval**: Is the pool being loaded correctly when planning actions?
3. **Timing Issues**: Is there a race condition between save and read?
4. **Data Loss**: Is the pool being cleared somewhere unexpectedly?
5. **State Mismatch**: Is the pool in exec_history but not being found by `_get_pool()`?

## Next Steps

After these logs are in place and running:

1. Monitor logs for a few trim → S2 buy_flag cycles
2. Look for patterns:
   - Pool saved but not loaded?
   - Pool loaded but empty?
   - Pool present in one log but missing in next?
3. Identify the exact point where pool is lost
4. Fix the root cause

## Files Modified

1. `src/intelligence/lowcap_portfolio_manager/pm/actions.py`
   - Added pool diagnostic logging in S2 buy_flag check
   - Added pool diagnostic logging in S3 DX buy check

2. `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
   - Added pool diagnostic logging when position loaded for planning
   - Added pool diagnostic logging when loading from DB
   - Enhanced trim pool update logging
   - Added pool diagnostic logging when saving to DB

