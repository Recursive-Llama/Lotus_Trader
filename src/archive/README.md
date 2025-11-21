# Archive Directory

This directory contains archived code that has been replaced by newer versions or is no longer in active use.

**Archive Date**: 2025-01-XX (Phase 1 cleanup before v4 implementation)

**Status**: ✅ Phase 1 Complete - Minimal cleanup done, ready for v4 implementation

## Archived Components

### Old Uptrend Engines

**Location**: `src/archive/intelligence/lowcap_portfolio_manager/jobs/`

- **`uptrend_engine.py`** (v1) - Original production engine
  - **Replaced by**: `uptrend_engine_v4.py`
  - **Status**: Archived - no longer used

- **`uptrend_engine_v2.py`** (v2) - Geometry-based S/R engine
  - **Replaced by**: `uptrend_engine_v4.py`
  - **Status**: Archived - no longer used

- **`uptrend_engine_v3.py`** (v3) - EMA Phase System attempt
  - **Location**: Still in `src/intelligence/lowcap_portfolio_manager/jobs/` (kept for reference)
  - **Status**: Deprecated but kept for reference during v4 implementation
  - **Note**: Will be archived after v4 is fully implemented and tested

### Old Social Ingest Modules

**Location**: `src/archive/intelligence/social_ingest/`

- **`social_ingest_module.py`** - Original social ingest with Playwright
  - **Replaced by**: `social_ingest_basic.py`
  - **Status**: Archived - no longer used
  - **Reason**: Replaced by simpler, more maintainable `social_ingest_basic.py`

### Old Backtesters

**Location**: `backtester/archive_v2/` and `backtester/archive_v3/`

- **`backtester/v2/`** → **`backtester/archive_v2/`**
  - **Replaced by**: `backtester/v4/`
  - **Status**: Archived - no longer used

- **`backtester/v3/`** → **`backtester/archive_v3/`**
  - **Replaced by**: `backtester/v4/`
  - **Status**: Archived - no longer used

## Active Components

### Current Active Versions

- **Uptrend Engine**: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`
- **Social Ingest**: `src/intelligence/social_ingest/social_ingest_basic.py`
- **Backtester**: `backtester/v4/`

## Restoration

If you need to reference archived code:
1. Check this README to understand what was archived and why
2. Files are preserved in archive directories
3. Do NOT restore archived files to active directories without discussion
4. If you need patterns from archived code, extract them to new files rather than restoring old ones

### Legacy Trader Service Methods

**Location**: `src/archive/trader_service_legacy_methods.py`

- **Old PositionMonitor-based methods** - Methods from `trader_service.py` that were part of the old system
  - **Replaced by**: v4 Portfolio Manager (PM handles all execution and position state)
  - **Status**: Archived - no longer used
  - **Methods archived**:
    - `execute_individual_entry()` - Old PositionMonitor entry execution
    - `spawn_trend_from_exit()` - Old trend batch system
    - `plan_buyback()` / `perform_buyback()` - Lotus buyback logic
    - Position aggregate update methods - PM handles this now
    - Exit recalculation helpers - PM handles this
    - Wallet reconciliation helpers - PM handles this
    - Position cap management - Should be in PM or separate module
    - Verification methods - PM handles this
    - Exit rules builders - PM handles this

## Future Cleanup

After v4 implementation is complete and tested:
- Archive `uptrend_engine_v3.py` (currently kept for reference)
- Archive any remaining old Decision Maker variants (if not already done)
- Final cleanup of any temporary code created during implementation

