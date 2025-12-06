# Phase State Investigation - Can We Remove It?

## Summary

**Current Status**: The system is in transition between old and new regime systems:
- **Old System**: Uses `phase_state` table with string labels ("Dip", "Recover", "Oh-Shit", "Good", "Euphoria")
- **New System**: Uses `lowcap_positions` table with `status='regime_driver'` and Uptrend Engine states ("S0", "S1", "S2", "S3")

## What Still Writes to `phase_state`

### 1. `tracker.py` (SPIRAL Tracker)
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py`
- **Lines**: 218-261
- **What it does**: 
  - Computes phase scores using SPIRAL lens system
  - Converts scores to labels using `label_from_score()` function
  - Writes to `phase_state` table with token="PORTFOLIO" and horizons (macro/meso/micro)
  - Also writes to `phase_state_bucket` for bucket-level phases
- **Schedule**: Runs every 5 minutes (aligned to :00, :05, :10, etc.)
- **Labels used**: "Dip", "Double-Dip", "Oh-Shit", "Recover", "Good", "Euphoria"

### 2. `spiral/persist.py`
- **File**: `src/intelligence/lowcap_portfolio_manager/spiral/persist.py`
- **Methods**: `write_phase_state()`, `write_phase_state_bucket()`
- **What it does**: Helper functions to write phase state data

## What Still Reads from `phase_state`

### 1. `pm_core_tick.py` (PM Core Tick)
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- **Lines**: 103-115 (`_latest_phase()`), 117-162 (`_get_regime_context()`)
- **What it reads**: 
  - Portfolio-level meso phase for `_latest_phase()`
  - All horizons (macro/meso/micro) for `_get_regime_context()`
- **How it's used**:
  - `_latest_phase()` → Used by `_map_meso_to_policy()` (lines 42-56) to map phase to policy values
  - `_get_regime_context()` → Passed to `compute_levers()` as `regime_context`
- **Critical**: `_map_meso_to_policy()` maps old phase labels to policy values:
  ```python
  def _map_meso_to_policy(phase: str) -> tuple[float, float]:
      p = (phase or "").lower()
      if p == "dip": return 0.2, 0.8
      if p == "double-dip": return 0.4, 0.7
      if p == "oh-shit": return 0.9, 0.8
      if p == "recover": return 1.0, 0.5
      if p == "good": return 0.5, 0.3
      if p == "euphoria": return 0.4, 0.5
      return 0.5, 0.5
  ```

### 2. `decision_maker_lowcap_simple.py` (Decision Maker)
- **File**: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`
- **Lines**: 76-100
- **What it reads**: All horizons (macro/meso/micro) for regime context
- **How it's used**: Passed to `compute_levers()` as `regime_context`

### 3. `social_ingest_basic.py` (Social Ingest)
- **File**: `src/intelligence/social_ingest/social_ingest_basic.py`
- **Lines**: 1451-1470
- **What it reads**: All horizons (macro/meso/micro) for regime context
- **How it's used**: Passed to `compute_levers()` as `regime_context`

### 4. `bootstrap_system.py` (Bootstrap System)
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/bootstrap_system.py`
- **Line**: 596
- **What it reads**: Just checks if table exists (diagnostic)

### 5. `pm_shadow_diag.py` (PM Shadow Diagnostics)
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_shadow_diag.py`
- **Line**: 66
- **What it reads**: Summary of phase states (diagnostic)

## What the New System Uses Instead

### Regime Engine (`regime_ae_calculator.py`)
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/regime_ae_calculator.py`
- **What it reads**: `lowcap_positions` table with `status='regime_driver'`
- **States**: "S0", "S1", "S2", "S3" (stored in `features.uptrend_engine_v4.state`)
- **How it works**: 
  - Reads regime driver states from `lowcap_positions`
  - Computes ΔA/ΔE deltas from state/flag tables
  - Applies timeframe weights and driver weights
  - Returns regime-based A/E scores

### Regime Runner (`regime_runner.py`)
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/regime_runner.py`
- **What it does**: Orchestrates regime pipeline (price collection → TA → Uptrend Engine → Regime A/E calculation)

## Key Question: Is `phase_state` Still Used for Decisions?

### Current State:
1. **`tracker.py`** still writes old phase labels to `phase_state`
2. **`pm_core_tick.py`** reads `phase_state` and uses `_map_meso_to_policy()` to convert phase to policy values
3. **`compute_levers()`** receives `regime_context` which includes old phase labels
4. **BUT**: The new regime engine (`regime_ae_calculator.py`) computes A/E from regime driver states, not from phase labels

### Critical Code Path:
```
pm_core_tick.py → _get_regime_context() → reads phase_state → passes to compute_levers()
```

But `compute_levers()` might be using the new regime engine instead. Need to check `levers.py`.

## Investigation Results

### ✅ `compute_levers()` Does NOT Use Phase Labels

**File**: `src/intelligence/lowcap_portfolio_manager/pm/levers.py`
- **Lines 7-8**: Comment says "Replaces old phase-based system (phase_macro, phase_meso, cut_pressure)"
- **Line 91**: Comment says "Removed: Phase-based A/E"
- **Lines 95-97**: Uses `RegimeAECalculator` which reads from `lowcap_positions` with regime drivers
- **Conclusion**: `compute_levers()` does NOT use phase labels from `regime_context`

### ✅ `_map_meso_to_policy()` Is NOT Called

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- **Line 42**: Function is defined but **never called**
- **Conclusion**: This function is dead code and can be removed

### ✅ Phase Labels Replaced with Regime States for Logging

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- **Replaced**: `_latest_phase()` with `_get_bucket_regime_state()` which gets regime states (S0, S1, S2, S3) for all three timeframes
- **Returns**: Dict with `{"macro": "S0", "meso": "S1", "micro": "S3"}` from bucket driver positions
- **Formatted**: As string `"Macro S0, Meso S1, Micro S3"` for logging and backward compatibility
- **Line 2602**: Regime state string is added to strand reasons as `"regime_state": phase` for **audit/logging only**
- **Conclusion**: Regime states are NOT used for decision making, only for logging in strands. Decision making uses `RegimeAECalculator` which reads from `lowcap_positions` with `status='regime_driver'`

### ✅ `regime_context` Phase Fields Are NOT Used for Decisions

- `regime_context` includes phase fields from `phase_state`
- But `compute_levers()` doesn't use them - it uses `RegimeAECalculator` instead
- Phase fields are only passed through for potential future use or logging

## Recommendation: Safe to Remove

**✅ `phase_state` is safe to remove** because:

1. **Decision making**: Uses new regime engine (`RegimeAECalculator`) which reads from `lowcap_positions`
2. **No active usage**: Phase labels are only used for logging in strands
3. **Dead code**: `_map_meso_to_policy()` is never called

## Removal Plan

### Step 1: Stop Writing to `phase_state`
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py`
- **Action**: Comment out or remove lines 218-261 (phase state writing)
- **Risk**: Low - only affects logging

### Step 2: Stop Reading from `phase_state` in PM Core
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- **Actions**:
  - Remove `_latest_phase()` method (lines 103-115)
  - Remove `_map_meso_to_policy()` function (lines 42-56)
  - Update `_get_regime_context()` to not read from `phase_state` (lines 126-156)
  - Update `run()` to not call `_latest_phase()` (line 2779)
  - Update `_write_strands()` to accept empty string for phase (line 2962)
- **Risk**: Low - phase is only used for logging

### Step 3: Stop Reading from `phase_state` in Decision Maker
- **File**: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`
- **Action**: Update `_get_regime_context()` to not read from `phase_state` (lines 76-100)
- **Risk**: Low - phase fields are not used

### Step 4: Stop Reading from `phase_state` in Social Ingest
- **File**: `src/intelligence/social_ingest/social_ingest_basic.py`
- **Action**: Update regime context fetching to not read from `phase_state` (lines 1451-1470)
- **Risk**: Low - phase fields are not used

### Step 5: Database Cleanup (Optional)
- **Action**: Drop `phase_state` and `phase_state_bucket` tables
- **Risk**: Low - but keep for historical data if needed

## Notes

- **Backward compatibility**: Strands currently include `"phase_meso"` field - we can either:
  - Keep it as empty string (backward compatible)
  - Remove it (cleaner, but breaks backward compatibility)
- **Historical data**: Consider keeping `phase_state` table for historical analysis, but stop writing to it

