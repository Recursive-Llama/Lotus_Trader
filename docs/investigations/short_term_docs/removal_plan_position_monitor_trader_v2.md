# Removal Plan: PositionMonitor & TraderLowcapSimpleV2

## Overview

This plan outlines the safe removal of legacy systems (PositionMonitor and TraderLowcapSimpleV2) that are incompatible with the v4 architecture.

## Prerequisites

- [x] Analysis complete: `docs/analysis_position_monitor_vs_pm.md`
- [x] Confirmed: v4 schema doesn't have `entries[]`, `exits[]`, `trend_entries[]`, `trend_exits[]`
- [x] Confirmed: PM handles all position management
- [ ] PriceOracle extraction (in progress)

---

## Phase 1: Extract PriceOracle ✅ (In Progress)

### Step 1.1: Create Standalone PriceOracle Factory
- [x] Create `src/trading/price_oracle_factory.py`
- [ ] Move PriceOracle initialization logic
- [ ] Make it independent of TraderLowcapSimpleV2

### Step 1.2: Update ScheduledPriceCollector Dependencies
- [ ] Update `run_trade.py` to use factory
- [ ] Update `run_social_trading.py` to use factory
- [ ] Test price collection still works

### Step 1.3: Verify PriceOracle Usage
- [ ] Check `trader_service.py` usage (may need update)
- [ ] Check `trader_views.py` usage (may need update)
- [ ] Check `fix_existing_positions.py` (tool, can update later)

**Status**: ✅ In Progress

---

## Phase 2: Remove PositionMonitor ❌

### Step 2.1: Verify PM Handles Everything
- [ ] Confirm PM executes all entries/exits
- [ ] Confirm PM handles position closure
- [ ] Confirm no code depends on `entries[]`, `exits[]`, `trend_entries[]`, `trend_exits[]`

### Step 2.2: Remove PositionMonitor Initialization
- [ ] Remove from `run_trade.py` (line 285-289)
- [ ] Remove from `run_social_trading.py` (line 209-212)
- [ ] Remove `start_monitoring()` calls (line 591 in run_trade.py, line 259 in run_social_trading.py)

### Step 2.3: Remove PositionMonitor File
- [ ] Delete `src/trading/position_monitor.py`
- [ ] Remove import statements

### Step 2.4: Update Documentation
- [ ] Remove PositionMonitor from `docs/run_trade_requirements.md`
- [ ] Update architecture docs

**Status**: ⏸️ Waiting for Phase 1

---

## Phase 3: Remove TraderLowcapSimpleV2 Dependencies ❌

### Step 3.1: Check Remaining Dependencies
- [ ] `learning_system.trader` - Check if needed
- [ ] `wallet_manager.trader` - Check if needed
- [ ] `register_pm_executor(trader, sb_client)` - Check if trader param needed

### Step 3.2: Update Learning System
- [ ] Check if `learning_system.trader` is actually used
- [ ] Remove if not needed, or replace with minimal interface

### Step 3.3: Update Wallet Manager
- [ ] Check if `wallet_manager.trader` is actually used
- [ ] Remove if not needed, or replace with minimal interface

### Step 3.4: Update PM Executor Registration
- [ ] Check `register_pm_executor()` signature
- [ ] Update to not require trader instance if possible

**Status**: ⏸️ Waiting for Phase 2

---

## Phase 4: Remove TraderLowcapSimpleV2 ❌

### Step 4.1: Remove Initialization
- [ ] Remove from `run_trade.py` (line 262-270)
- [ ] Remove from `run_social_trading.py` (line 177-187)
- [ ] Remove all `self.trader = TraderLowcapSimpleV2(...)` calls

### Step 4.2: Remove File
- [ ] Delete `src/intelligence/trader_lowcap/trader_lowcap_simple_v2.py`
- [ ] Remove import statements

### Step 4.3: Update Manual Tools
- [ ] Update `trigger_exit.py` (if still needed)
- [ ] Update `fix_existing_positions.py` (if still needed)
- [ ] Update `fix_specific_contracts.py` (if still needed)
- [ ] Update `trader_evm_decision_smoke.py` (if still needed)

### Step 4.4: Clean Up
- [ ] Remove unused imports
- [ ] Update documentation
- [ ] Run tests

**Status**: ⏸️ Waiting for Phase 3

---

## Phase 5: Verification ✅

### Step 5.1: Test PM Execution
- [ ] Verify PM executes entries correctly
- [ ] Verify PM executes exits correctly
- [ ] Verify PM handles position closure

### Step 5.2: Test Price Collection
- [ ] Verify ScheduledPriceCollector works with extracted PriceOracle
- [ ] Verify price data is collected correctly

### Step 5.3: Test System Startup
- [ ] Verify `run_trade.py` starts without errors
- [ ] Verify `run_social_trading.py` starts without errors
- [ ] Verify all components initialize correctly

### Step 5.4: Integration Tests
- [ ] Run test harnesses
- [ ] Verify no broken dependencies
- [ ] Verify PM handles all position management

**Status**: ⏸️ Waiting for Phase 4

---

## Rollback Plan

If issues arise:

1. **Phase 1 Rollback**: Revert PriceOracle factory, restore TraderLowcapSimpleV2 initialization
2. **Phase 2 Rollback**: Restore PositionMonitor initialization and file
3. **Phase 3 Rollback**: Restore TraderLowcapSimpleV2 dependencies
4. **Phase 4 Rollback**: Restore TraderLowcapSimpleV2 file

All changes should be in separate commits for easy rollback.

---

## Notes

- PositionMonitor reads columns that don't exist in v4 schema - it will fail silently or error
- TraderLowcapSimpleV2 sets `status='closed'` which is invalid in v4 (should be `'watchlist'`)
- PM is the single source of truth for position management in v4
- All execution goes through PMExecutor (Li.Fi SDK)

---

## Progress Tracking

- [x] Phase 1: Extract PriceOracle (In Progress)
- [ ] Phase 2: Remove PositionMonitor
- [ ] Phase 3: Remove TraderLowcapSimpleV2 Dependencies
- [ ] Phase 4: Remove TraderLowcapSimpleV2
- [ ] Phase 5: Verification

