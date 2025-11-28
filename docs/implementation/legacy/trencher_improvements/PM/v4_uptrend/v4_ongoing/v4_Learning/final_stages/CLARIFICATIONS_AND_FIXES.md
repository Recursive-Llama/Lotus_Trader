# Clarifications and Fixes - Learning System V5

**Date**: 2025-01-26  
**Status**: Summary of clarifications and code fixes

---

## 1. Tuning N_MIN Calculation

### Question
Is N_MIN based on total events (acted + skipped) or just `n_misses + n_fps`?

### Answer
**N_MIN is based on total events** (acted + skipped) for that `pattern_key` within that scope slice.

**Code Location**: `src/intelligence/lowcap_portfolio_manager/jobs/tuning_miner.py:142`
```python
if len(group) < self.N_MIN:  # group contains all events (acted + skipped)
    continue
```

**Example**: If you have 20 acted + 15 skipped = 35 total events, and N_MIN=33, the lesson qualifies.

**Status**: ✅ **Correct as-is**

---

## 2. DM Timeframe Weights

### Question
Is there an error with DM timeframe learning? Does it still work?

### Answer
**DM still reads timeframe weights from `learning_coefficients` table** via `coefficient_reader.get_timeframe_weights()`.

**Code Location**: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py:674-704`

**How it works**:
1. DM calls `coefficient_reader.get_timeframe_weights(module='dm')`
2. Reader queries `learning_coefficients` with `scope='lever', name='timeframe', key='1m'|'15m'|'1h'|'4h'`
3. If learned data exists (weights != 1.0), uses normalized weights
4. Otherwise falls back to defaults: `{1m: 0.05, 15m: 0.125, 1h: 0.70, 4h: 0.125}`

**Update Path**: ✅ **Confirmed working**

**Code Location**: `src/intelligence/universal_learning/universal_learning_system.py:593-606`

```python
# Update timeframe coefficient
if timeframe:
    levers_to_update.append(('timeframe', timeframe))

# Update each lever coefficient using EWMA
for lever_name, lever_key in levers_to_update:
    self.coefficient_updater.update_coefficient_ewma(
        module='dm',
        scope='lever',
        name=lever_name,  # 'timeframe'
        key=lever_key,    # '1m', '15m', '1h', or '4h'
        rr_value=rr,
        trade_timestamp=trade_timestamp
    )
```

**Flow**:
1. When a `position_closed` strand is processed, `_update_coefficients_from_closed_trade()` is called
2. It extracts the `timeframe` from the position
3. Adds `('timeframe', timeframe)` to `levers_to_update`
4. Calls `update_coefficient_ewma()` with `scope='lever', name='timeframe', key='1m'|'15m'|'1h'|'4h'`
5. This updates the `learning_coefficients` table
6. DM reads from the same table via `coefficient_reader.get_timeframe_weights()`

**Status**: ✅ **Working correctly** - Full cycle confirmed

---

## 3. Exposure Lookup Fallback Bug - FIXED

### Issue
When `_mask_keys_for_scope()` returns no matching masks (e.g., missing `intent` or `mcap_bucket` fields), the lookup returned `1.33` (max boost).

### Problem
This is wrong! If we can't match any mask, we have **no learning data**, so we should return `1.0` (neutral multiplier), not `1.33` (max boost).

### Fix
**File**: `src/intelligence/lowcap_portfolio_manager/pm/exposure.py:129`

**Before**:
```python
if not mask_keys or self.total_exposure <= 0:
    return 1.33  # ❌ Wrong - max boost with no data
```

**After**:
```python
if not mask_keys or self.total_exposure <= 0:
    return 1.0  # ✅ Correct - neutral when no learning data
```

**Status**: ✅ **Fixed**

---

## 4. Decay N_MIN Gate - REDUNDANT BUT HARMLESS

### Question
Is the N_MIN gate for decay redundant? Since decay is only computed on lessons, and lessons only exist when N >= 33, isn't the gate already enforced?

### Answer
**Yes, it's redundant but harmless.**

**Flow**:
1. `mine_lessons()` only processes slices with `N >= N_MIN_SLICE` (33)
2. `compute_lesson_stats()` is only called for those slices
3. So by the time we call `fit_decay_curve()`, we already have `N >= 33`

**Current Code**: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py:113`
```python
# Only fit decay if we have enough samples (N_MIN_SLICE)
if n >= N_MIN_SLICE:
    decay_meta = fit_decay_curve(events)
else:
    decay_meta = {"state": "insufficient", "multiplier": 1.0}
```

**Additional Gate**: `fit_decay_curve()` itself has a check for `len(events) < 5`, so there's a double gate.

**Recommendation**: 
- The gate is redundant but doesn't hurt
- Could remove it for clarity, but keeping it provides defense-in-depth
- **Status**: ✅ **Acceptable as-is** (redundant but safe)

---

## 5. Confidence Gate vs Edge Threshold - RESOLVED

### Decision
**Remove confidence gate** - Edge threshold alone is sufficient.

### Rationale
1. **Edge threshold is the primary filter**: `abs(edge_raw) >= 0.05` already filters out lessons with no meaningful edge
2. **Learn from both directions**: 
   - `edge_raw > 0.05`: Positive edge → increase sizing
   - `edge_raw < -0.05`: Negative edge → decrease sizing
   - `|edge_raw| < 0.05`: No edge → skip (no override)
3. **N_MIN already ensures quality**: Lessons only exist when `N >= 33`, so we already have minimum sample size
4. **Confidence gate was too conservative**: Could filter out valid lessons with real edge but high variance

### Implementation
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py`

**Before**:
```python
# Judge: Is edge significant?
if abs(edge_raw) < EDGE_SIGNIFICANCE_THRESHOLD:
    continue

# Confidence score
confidence = support_score * reliability_score
if confidence < MIN_CONFIDENCE_SCORE:  # ❌ Removed
    continue
```

**After**:
```python
# Judge: Is edge significant? (learns from both positive and negative edge)
# Positive edge (edge_raw > 0.05): Increase sizing
# Negative edge (edge_raw < -0.05): Decrease sizing
# No edge (|edge_raw| < 0.05): Skip (no override needed)
if abs(edge_raw) < EDGE_SIGNIFICANCE_THRESHOLD:
    continue

# Confidence still calculated for telemetry, but not used for filtering
confidence = support_score * reliability_score
```

### Edge Threshold Behavior
- **`edge_raw = 0.08`** → `multiplier = 1.08` (8% boost)
- **`edge_raw = -0.12`** → `multiplier = 0.88` (12% reduction)
- **`edge_raw = 0.03`** → Skipped (no override)

**Status**: ✅ **Fixed** - Confidence gate removed, edge threshold is the sole filter

---

## 6. Tuning Decay Removal - ALREADY CORRECT

### Question
Should tuning lessons have decay? If not, is it removed?

### Answer
**Tuning lessons do NOT use decay** - this is already correct.

**Code Location**: `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py:170`
```python
'decay_state': None,  # ✅ Tuning doesn't use decay
```

**Rationale**: Tuning is about adjusting thresholds based on miss rates, not about how those miss rates change over time. Decay is only relevant for `pm_strength` lessons (how edge changes over time).

**Status**: ✅ **Already correct** - No changes needed

---

## Summary of Actions

### ✅ Fixed
1. **Exposure lookup fallback**: Changed from `1.33` to `1.0` when no masks match

### ✅ Verified
1. **DM timeframe weight updates**: Confirmed - `_update_coefficients_from_closed_trade()` updates timeframe weights with `scope='lever', name='timeframe'` when trades close

### ✅ Resolved
1. **Confidence gate**: Removed - edge threshold alone is sufficient
2. **Decay N_MIN gate**: Kept (redundant but harmless, provides defense-in-depth)

### ✅ Confirmed Correct
1. **Tuning N_MIN**: Based on total events (acted + skipped)
2. **Tuning decay**: Already removed (set to `None`)
3. **DM timeframe learning**: Full cycle confirmed - updates on trade close, reads on position creation

---

## Next Steps

1. **Test edge threshold behavior**: Run materializer on real lessons and verify that both positive and negative edge lessons are materialized correctly
2. **Optional: Remove redundant decay N_MIN gate**: Since lessons only exist when N >= 33, the gate in `compute_lesson_stats()` is redundant (but harmless, so can stay for defense-in-depth)

