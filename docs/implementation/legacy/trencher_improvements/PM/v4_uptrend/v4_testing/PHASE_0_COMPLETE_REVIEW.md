# Phase 0 Complete - Next Steps Review

**Date**: 2025-01-XX  
**Status**: ✅ Phase 0 Complete - Ready for Phase 1

---

## Phase 0 Completion Summary

### ✅ Completed Tasks

1. **Database Schema Updates** ✅
   - `lowcap_positions_v4_schema.sql` - Added `entry_context` and `completed_trades` JSONB
   - `learning_configs_schema.sql` - Created
   - `learning_coefficients_schema.sql` - Created
   - `curators_schema.sql` - Added `chain_counts` JSONB
   - `pm_thresholds_schema.sql` - Created (Task 11)

2. **1m OHLC Conversion** ✅
   - Verified and implemented in `rollup_ohlc.py`
   - Handles Open=previous close, Close=current price, High/Low=max/min

3. **Decision Maker Updates** ✅
   - Creates 4 positions per token (1m, 15m, 1h, 4h)
   - Splits allocation: 1m=5%, 15m=12.5%, 1h=70%, 4h=12.5%
   - Sets status based on `bars_count` (dormant/watchlist)
   - Populates `entry_context` for learning system

4. **Backfill Updates** ✅
   - Supports all 4 timeframes (1m, 15m, 1h, 4h)
   - Fetches directly from GeckoTerminal API (no rollup)
   - Updates `bars_count` and auto-flips `dormant → watchlist`

5. **OHLC Conversion & Rollup** ✅
   - 1m OHLC conversion from price points
   - Rollup to 15m, 1h, 4h
   - All stored in `lowcap_price_data_ohlc` with `timeframe` column

6. **Uptrend Engine v4 Scheduling** ✅
   - Scheduled per timeframe (1m=1min, 15m=15min, 1h=1hr, 4h=4hr)
   - Timeframe-aware (processes positions by timeframe)
   - Bootstrap logic for watchlist positions

7. **State Bootstrap** ✅
   - Implemented in `uptrend_engine_v4.py`
   - Only bootstraps to S0 or S3 (clear trends)
   - Disables signals for watchlist positions (warmup mode)

8. **Trader Service Cleanup** ✅
   - Removed first buy execution
   - Simplified to validation + backfill trigger only
   - Archived legacy methods

9. **plan_actions_v4()** ✅
   - Created with correct payload structure
   - Signal execution tracking
   - Profit/allocation multipliers
   - Cooldown logic (3 bars or S/R level change)
   - All entry gates (S1, S2, S3, reclaimed EMA333)

10. **PM Frequency Updates** ✅
    - Timeframe-specific scheduling (1m=1min, 15m=15min, 1h=1hr, 4h=4hr)
    - Processes only watchlist + active (skips dormant)
    - Strands include position_id, timeframe, chain, token

11. **pm_thresholds Table** ✅
    - Schema created
    - 5-minute cache layer implemented
    - Fallback precedence: env → DB → code defaults

12. **PM Dormant Filtering** ✅
    - PM only processes watchlist + active positions
    - Dormant positions skipped entirely

---

## Current State Analysis

### ✅ What's Working

1. **Data Pipeline**:
   - ✅ 1m price collection → 1m OHLC conversion → rollup to 15m/1h/4h
   - ✅ Backfill for all 4 timeframes
   - ✅ `bars_count` updates and `dormant → watchlist` transitions

2. **Uptrend Engine v4**:
   - ✅ Scheduled per timeframe
   - ✅ Timeframe-aware data access
   - ✅ Bootstrap logic for watchlist positions
   - ✅ Writes signals to `features.uptrend_engine_v4`

3. **PM Core Tick**:
   - ✅ Timeframe-specific scheduling
   - ✅ Uses `plan_actions_v4()` (when `PM_USE_V4=1`)
   - ✅ Filters by timeframe and status (watchlist + active)
   - ✅ Writes strands with v4 structure

4. **Decision Maker**:
   - ✅ Creates 4 positions per token
   - ✅ Splits allocation correctly
   - ✅ Sets initial status based on data availability

### ❌ What's Missing (Phase 1 Critical)

1. **PM-Executor Integration** ❌ **CRITICAL**
   - **Current**: PM writes strands, executor subscribes to events (old system)
   - **Needed**: PM directly calls executor, executor returns results, PM updates database
   - **Location**: `pm_core_tick.py` - needs execution logic after `plan_actions_v4()`
   - **Impact**: No trades execute currently (only strands written)

2. **Position Table Updates** ❌ **CRITICAL**
   - **Current**: Executor doesn't update position table
   - **Needed**: PM updates `total_quantity`, `total_investment_native`, `total_extracted_native`, `total_tokens_bought`, `total_tokens_sold` after execution
   - **Location**: `pm_core_tick.py` - after executor returns results

3. **Execution History Tracking** ❌ **CRITICAL**
   - **Current**: `plan_actions_v4()` reads `pm_execution_history` but it's never updated
   - **Needed**: PM updates `features.pm_execution_history` after each execution
   - **Location**: `pm_core_tick.py` - after execution, before next tick

4. **Position Closure Detection** ❌ **CRITICAL**
   - **Current**: Not implemented
   - **Needed**: PM detects full exit (`emergency_exit` or `trim` with `size_frac=1.0`), computes R/R, writes `completed_trades` JSONB, emits `position_closed` strand
   - **Location**: `pm_core_tick.py` - after execution, check if position closed

5. **Executor Price Source** ❌ **CRITICAL**
   - **Current**: Executor reads from `lowcap_price_data_1m` (wrong)
   - **Needed**: Executor reads from `lowcap_price_data_ohlc` filtered by position's timeframe
   - **Location**: `pm/executor.py` - `_latest_price()` function

6. **Executor Direct Call Interface** ❌ **CRITICAL**
   - **Current**: Event-driven subscription model
   - **Needed**: Direct function call: `executor.execute(decision, position) -> result`
   - **Location**: `pm/executor.py` - needs new `execute()` function

---

## Phase 1: PM Integration (Next Steps)

### Priority 1: PM-Executor Direct Integration 🔴 **CRITICAL**

**Task 1.1: Create Direct Executor Interface**
- **File**: `src/intelligence/lowcap_portfolio_manager/pm/executor.py`
- **Action**: Create new `execute()` function that:
  - Takes `decision` dict and `position` dict
  - Gets latest price from `lowcap_price_data_ohlc` (filtered by position's timeframe)
  - Executes trade via chain executor
  - Returns execution result (status, tx_hash, tokens, price, slippage)
  - Does NOT write to database (PM does all writes)

**Task 1.2: Update PM Core Tick to Call Executor**
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- **Action**: After `plan_actions_v4()` returns actions:
  - For each non-hold action:
    - Call `executor.execute(decision, position)` directly
    - Update position table with execution results
    - Update `features.pm_execution_history`
    - Check if position closed → compute R/R, write `completed_trades`, emit `position_closed` strand
    - Write `pm_action` strand with execution results

**Task 1.3: Fix Executor Price Source**
- **File**: `src/intelligence/lowcap_portfolio_manager/pm/executor.py`
- **Action**: Update `_latest_price()` to:
  - Read from `lowcap_price_data_ohlc` (not `lowcap_price_data_1m`)
  - Filter by position's timeframe
  - Return latest close price for that timeframe

### Priority 2: Position State Management 🔴 **CRITICAL**

**Task 1.4: Update Position Table After Execution**
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- **Action**: After executor returns results:
  - Update `total_quantity` (add for buys, subtract for sells)
  - Update `total_investment_native` (add for buys)
  - Update `total_extracted_native` (add for sells)
  - Update `total_tokens_bought` / `total_tokens_sold`
  - Update `status` (watchlist → active on first buy, active → watchlist on full exit)

**Task 1.5: Update Execution History**
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- **Action**: After execution:
  - Read current `features.pm_execution_history`
  - Update `last_{state}_buy` or `last_trim` with timestamp, price, size_frac, signal
  - Update `prev_state` to current state
  - Store S/R level price for trims
  - Write back to `features.pm_execution_history`

**Task 1.6: Position Closure Detection & R/R Calculation**
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- **Action**: After full exit execution:
  - Detect: `decision_type == "emergency_exit"` OR (`decision_type == "trim"` AND `size_frac >= 1.0`)
  - Compute R/R from OHLCV data:
    - Entry price: from `entry_context` or first buy price
    - Exit price: from executor result
    - Min price: query OHLCV between entry and exit
    - Max price: query OHLCV between entry and exit
    - R/R = (exit_price - entry_price) / (entry_price - min_price)
  - Write to `completed_trades` JSONB array
  - Emit `position_closed` strand with all learning data
  - Update `status='watchlist'`, `closed_at=now()`

### Priority 3: Testing & Validation 🟠

**Task 1.7: Test Entry Gates**
- Test S1 one-time entry (only on S0 → S1 transition)
- Test S2/S3 entries reset on trim or state transition
- Test reclaimed EMA333 rebuy

**Task 1.8: Test Exit Gates**
- Test trim cooldown (3 bars per timeframe)
- Test trim on S/R level change
- Test emergency exit (full exit)

**Task 1.9: Test Position Sizing**
- Test profit/allocation multipliers
- Test S1 vs S2/S3 entry sizes
- Test trim sizes with multipliers

**Task 1.10: Parallel Run with Old System**
- Keep `PM_USE_V4=0` for old system
- Test with `PM_USE_V4=1` for new system
- Compare outputs and validate correctness

---

## Phase 2: Multi-Timeframe Foundation (Future)

1. Update TA Tracker to support all timeframes
2. Update Geometry Builder to support all timeframes
3. Test with single timeframe first, then multiple

---

## Phase 3: Uptrend Engine Multi-Timeframe (Future)

1. Already done (Task 6) ✅
2. Already done (Task 6) ✅
3. Already done (Task 6) ✅

---

## Phase 4: System Integration & Cleanup (Future)

1. Test end-to-end with multi-timeframe
2. Cleanup old components
3. Full migration
4. Documentation updates

---

## Critical Gaps Summary

### 🔴 Must Fix Before Production

1. **PM-Executor Integration**: No trades execute currently
2. **Position Updates**: Database not updated after execution
3. **Execution History**: Never updated, so signal tracking breaks
4. **Position Closure**: No R/R calculation or learning data collection
5. **Price Source**: Executor uses wrong table (1m instead of OHLC)

### 🟠 Should Fix Soon

1. **TA Tracker Multi-Timeframe**: Currently hardcoded to 1h
2. **Geometry Builder Multi-Timeframe**: Currently hardcoded to 1h
3. **Testing**: Need comprehensive test suite

### 🟡 Future Enhancements

1. **Tunable Thresholds**: Table created, but not used yet
2. **Learning System**: Schema ready, but not implemented
3. **LLM Learning Layer**: Designed but not implemented

---

## Recommended Next Steps

1. **Start with Task 1.1**: Create direct executor interface
2. **Then Task 1.2**: Wire executor into PM Core Tick
3. **Then Task 1.3**: Fix price source
4. **Then Task 1.4-1.6**: Position state management
5. **Then Task 1.7-1.9**: Testing

This will get the core execution flow working end-to-end.

