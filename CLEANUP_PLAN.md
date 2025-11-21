# Repository Cleanup Plan

**Created**: 2025-01-XX  
**Status**: 📋 Planning Phase - Safe to execute after testing completes

---

## Overview

This document outlines a phased cleanup plan to remove old, unused, and temporary files from the repository without interfering with active testing work.

---

## Phase 1: Safe to Clean Now (Non-Interfering)

These files can be removed immediately without affecting tests or active development.

### 1.1 Log Files (7 files)
**Location**: Root directory and `logs/` directory
- `jupiter_debug.log`
- `llm_test_results.log`
- `pump_large_amount_test.log`
- `pump_real_config_test.log`
- `pump_simple_debug.log`
- `social_trading.log`
- `src/social_trading.log`
- `logs/*.log` (all log files in logs directory)

**Action**: Delete all `.log` files (they're regenerated on runtime)

### 1.2 Temporary JSON/Text Files (6 files)
**Location**: Root directory
- `llm_trendline_analysis.json`
- `llm_trendline_prompt.txt`
- `llm_trendline_response.txt`
- `llm_trendlines_clean.json`
- `polytale_swing_points.json`
- `token_registry_backup.json`

**Action**: Review and delete if not needed for reference

### 1.3 Temporary PNG Files (2 files)
**Location**: Root directory
- `adaptive_trend_segmentation_POLYTALE_solana_1760223624.png`
- `percentage_swing_highs_POLYTALE_solana_1760223624.png`

**Action**: Delete (appear to be temporary analysis outputs)

---

## Phase 2: Archive Directories (Review & Consolidate)

These are clearly archived but should be reviewed before deletion.

### 2.1 Backtester Archives
**Location**: `backtester/`
- `backtester/archive_v2/` (58 files: 27 JSON, 26 PNG, 4 Python, 1 other)
- `backtester/archive_v3/` (85 files: 43 JSON, 42 PNG)

**Action**: 
- Option A: Move to external storage/backup, then delete
- Option B: Keep if needed for historical reference
- Option C: Compress into single archive file

**Recommendation**: Archive externally, then remove from repo

### 2.2 Source Code Archives
**Location**: `src/archive/`
- `src/archive/` (35 files: 30 SQL, 4 Python, 1 MD)

**Action**: Review if any SQL schemas are still referenced, then archive externally

---

## Phase 3: Standalone Analysis/Debug Scripts (Review Dependencies)

These scripts appear to be one-off analysis tools. Review before deletion.

### 3.1 Analysis Scripts (6 files)
**Location**: Root directory
- `analyze_batch_1.py`
- `analyze_batch_2.py`
- `analyze_batch_3.py`
- `analyze_batch_4.py`
- `analyze_dlmm.py`
- `analyze_zfi.py`

**Action**: 
- Check if referenced in documentation
- If not, move to `scripts/archive/` or delete

### 3.2 Check/Diagnostic Scripts (8 files)
**Location**: Root directory
- `check_dreams.py`
- `check_executed_exits.py`
- `check_position_entry_proximity.py`
- `check_s1_conditions.py`
- `check_slopes_debug.py`
- `check_token.py`
- `diagnose_bloxwap.py`
- `list_below_entry_positions.py`

**Action**: 
- Review if any are still useful
- Move useful ones to `scripts/` directory
- Delete one-off diagnostic scripts

### 3.3 Debug Scripts (4 files)
**Location**: Root directory
- `debug_curator_structure.py`
- `debug_execution_flow.py`
- `debug_meta_data.py`
- `calculate_facy.py`

**Action**: 
- Review if still needed for debugging
- Move to `scripts/debug/` if useful
- Delete if obsolete

### 3.4 Extract/Utility Scripts (3 files)
**Location**: Root directory
- `extract_llm_trendlines.py`
- `extract_token_registry.py`
- `get_current_prices.py`

**Action**: 
- Move to `scripts/` if still useful
- Delete if one-off utility

### 3.5 Test Scripts in Root (9 files)
**Location**: Root directory
- `test_exact_amount.py`
- `test_jupiter_debug.py`
- `test_production_params.py`
- `test_pump_large_amount.py`
- `test_pump_sell_debug.py`
- `test_pump_simple_debug.py`
- `test_pump_simple.py`
- `test_pump_transaction_debug.js`
- `test_pump_with_real_config.py`

**Action**: 
- Review if these are still needed
- If obsolete, delete
- If useful, move to `src/tests/` or `tests/` directory

---

## Phase 4: Old Test Directory (Consolidate)

### 4.1 Root `tests/` Directory
**Location**: `tests/` (23 Python files)

**Status**: Partially referenced in `pytest.ini`:
- `tests/test_v2_trader.py`
- `tests/test_trader_isolated.py`

**Action**: 
1. Review which tests in `tests/` are still active
2. Move active tests to `src/tests/` if they belong to new test suite
3. Archive or delete obsolete tests
4. Update `pytest.ini` to remove old paths if tests are moved

**Files to Review**:
- `test_v2_trader.py` (referenced in pytest.ini)
- `test_trader_isolated.py` (referenced in pytest.ini)
- All other files in `tests/` directory

---

## Phase 5: Backtester Results (Large Files)

### 5.1 Backtest Result Images
**Location**: `backtester/v4/backests/` (40 PNG files)

**Action**: 
- These are likely generated outputs
- Consider moving to `.gitignore` if regeneratable
- Or archive externally if needed for reference

### 5.2 Backtest Result JSON
**Location**: `backtester/v4/backests/` (28 JSON files)

**Action**: Same as above - review if needed or archive

---

## Phase 6: Empty/Unused Directories

### 6.1 Empty Directories
- `Module_Design/` (appears empty in project layout)

**Action**: Check if truly empty, then delete

---

## Execution Plan

### Immediate (Safe - Can do now):
1. ✅ Delete all `.log` files
2. ✅ Delete temporary JSON/text files (after review)
3. ✅ Delete temporary PNG files in root

### After Testing Completes:
1. Review and consolidate archive directories
2. Review standalone scripts and organize/delete
3. Consolidate test directories
4. Clean up backtest result files
5. Update `pytest.ini` if test paths change

### Recommended Order:
1. **Phase 1** (Safe now) - Execute immediately
2. **Phase 4** (Test consolidation) - After testing, consolidate test directories
3. **Phase 3** (Scripts) - Review and organize scripts
4. **Phase 2 & 5** (Archives) - Archive externally, then remove
5. **Phase 6** (Empty dirs) - Final cleanup

---

## Safety Checklist

Before deleting anything:
- [ ] Ensure no imports reference the files
- [ ] Check git history if unsure about importance
- [ ] Archive externally before deleting (for safety)
- [ ] Update `.gitignore` for regeneratable files
- [ ] Test that pytest still works after test directory changes

---

## Estimated Impact

- **Files to delete**: ~150-200 files
- **Directories to clean**: 3-4 archive directories
- **Repository size reduction**: Significant (especially PNG/JSON backtest results)
- **Risk level**: Low (with proper review)

---

## Notes

- All active testing is in `src/tests/` directory
- Main code is in `src/` directory
- Scripts should be organized in `scripts/` directory
- Keep all documentation in `docs/` directory

