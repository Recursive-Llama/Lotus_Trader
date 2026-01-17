# PM Tuning Data Capture Gaps

**Date**: 2025-01-XX  
**Purpose**: Identify what data we're capturing vs what we need for factor-specific tuning

---

## What We ARE Capturing

### In Window Samples (S1):
- ✅ `ts_score` - Trend strength score
- ✅ `ts_with_boost` - TS + SR boost
- ✅ `sr_boost` - Social/regime boost
- ✅ `entry_zone_ok` - **Gate pass/fail flag** (all gates passed)
- ✅ `slope_ok` - **Gate pass/fail flag** (slope gate passed)
- ✅ `ts_ok` - **Gate pass/fail flag** (TS gate passed)
- ✅ `halo_distance` - Distance from EMA in ATR units
- ✅ `halo` - Halo value
- ✅ `ema60_slope` - EMA60 slope
- ✅ `ema144_slope` - EMA144 slope
- ✅ `a_value` - A lever value
- ✅ `position_size_frac` - Position size fraction

### In Window Summary (becomes factors):
- The summary aggregates samples (median, min, max)
- But we need to check if gate flags are preserved

---

## What We're MISSING

### Critical Missing Data:

1. **Threshold Values** (the actual gates we compared against):
   - ❌ `ts_min` - The TS threshold (Constants.TS_THRESHOLD = 0.60)
   - ❌ `halo_max` or `halo_multiplier` - The halo limit (Constants.ENTRY_HALO_ATR_MULTIPLIER = 1.0)
   - ❌ `slope_min` - The slope requirement (typically 0.0)
   - ❌ `dx_min` - DX threshold (for S3, Constants.DX_BUY_THRESHOLD = 0.60)

2. **Gate-Specific Information**:
   - ⚠️ We have `entry_zone_ok`, `ts_ok`, `slope_ok` in samples
   - ⚠️ But need to verify these are in the summary/factors
   - ⚠️ Need to know which specific gate blocked us if we skipped

3. **Decision Context**:
   - ⚠️ Why did we skip? (TS too low? Halo too far? Slope too negative?)
   - ⚠️ Why did we act? (All gates passed? Which gates?)

---

## What We SHOULD Capture

### For Factor-Specific Tuning:

1. **Threshold Values at Decision Time**:
   ```python
   factors = {
       # Signal values
       "ts_score": 0.5,
       "halo_distance": 0.6,
       "ema60_slope": 0.0007,
       
       # THRESHOLDS (what we compared against)
       "ts_min": 0.60,  # ← MISSING
       "halo_max": 1.0,  # ← MISSING
       "slope_min": 0.0,  # ← MISSING
       
       # Gate pass/fail flags
       "entry_zone_ok": True,  # ← Need to verify this is captured
       "ts_ok": True,  # ← Need to verify this is captured
       "slope_ok": True,  # ← Need to verify this is captured
   }
   ```

2. **Gate-Specific Analysis**:
   - If we skipped and `ts_ok = False` → TS threshold too high
   - If we skipped and `slope_ok = False` → Slope requirement too strict
   - If we skipped and `entry_zone_ok = False` but `ts_ok = True` and `slope_ok = True` → Halo too tight
   - If we acted and failed → Compare signal values vs thresholds to see which gate was too loose

---

## Current System Limitations

### What We Can't Do Without This Data:

1. **Factor-Specific Pressure**:
   - Can't calculate TS-specific pressure (misses TS vs threshold)
   - Can't calculate Halo-specific pressure (misses halo vs limit)
   - Can't calculate Slope-specific pressure (misses slope vs requirement)

2. **Targeted Adjustments**:
   - Can't adjust only TS if TS is the problem
   - Can't adjust only halo if halo is the problem
   - Have to blanket-adjust everything (current system)

3. **Impact Analysis**:
   - Can't predict: "If we lower TS threshold by 0.05, how many misses would we catch?"
   - Can't predict: "How many extra failures would we take?"
   - Can't evaluate trade-offs

---

## What Needs to Change

### 1. Capture Threshold Values

**Location**: `pm_core_tick.py::_finalize_active_window()`

**Change**: Add threshold values to factors:
```python
factors = active.get("summary") or {}

# Add threshold values
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import Constants
factors["ts_min"] = Constants.TS_THRESHOLD
factors["halo_max"] = Constants.ENTRY_HALO_ATR_MULTIPLIER
factors["slope_min"] = 0.0  # Or from config

# For S2
factors["s2_halo_max"] = Constants.S2_RETEST_HALO_ATR_MULTIPLIER

# For S3
factors["dx_min"] = Constants.DX_BUY_THRESHOLD
```

### 2. Preserve Gate Flags in Summary

**Location**: `pm_core_tick.py::_summarize_window_samples()`

**Change**: Ensure gate flags are preserved (not just aggregated):
```python
# Gate flags should be boolean (not aggregated)
if samples:
    factors["entry_zone_ok"] = any(s.get("entry_zone_ok") for s in samples)
    factors["ts_ok"] = any(s.get("ts_ok") for s in samples)
    factors["slope_ok"] = any(s.get("slope_ok") for s in samples)
```

### 3. Capture Which Gate Blocked Us

**Location**: `pm_core_tick.py::_finalize_active_window()`

**Change**: If we skipped, capture why:
```python
if decision == "skipped":
    # Determine which gate blocked us
    last_sample = samples[-1] if samples else {}
    factors["blocked_by"] = []
    
    if not last_sample.get("ts_ok"):
        factors["blocked_by"].append("ts")
    if not last_sample.get("slope_ok"):
        factors["blocked_by"].append("slope")
    if not last_sample.get("entry_zone_ok") and last_sample.get("ts_ok") and last_sample.get("slope_ok"):
        factors["blocked_by"].append("halo")
```

---

## Additional Considerations

### 1. Override Application Context

**Question**: When we apply overrides, do we need to capture the override values too?

**Answer**: Probably not - overrides are applied at runtime, not at decision time. We want to learn from the base thresholds.

### 2. Scope-Specific Thresholds

**Question**: Are thresholds the same across all scopes, or do they vary?

**Answer**: Currently thresholds are global (Constants), but overrides can make them scope-specific. We should capture the **effective** threshold at decision time (base + overrides).

### 3. Historical Threshold Changes

**Question**: If thresholds change over time, should we track which threshold version was used?

**Answer**: Yes - we should capture the actual threshold value, not just reference Constants (which might change).

---

## Summary

**Current State**: We capture signal values and gate flags, but NOT threshold values.

**Impact**: Can't do factor-specific tuning - have to blanket-adjust everything.

**Fix**: Capture threshold values in factors when logging episode events.

**Priority**: HIGH - This is blocking factor-specific tuning.

