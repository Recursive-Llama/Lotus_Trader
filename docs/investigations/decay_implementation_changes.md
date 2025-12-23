# Decay Implementation Changes

## Changes Made

### 1. RR Bounds Updated: -10 to 10 → -33 to 33

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Change**:
```python
# Before
rr = max(-10.0, min(10.0, rr))

# After
rr = max(-33.0, min(33.0, rr))
```

**Rationale**:
- Captures extreme but realistic trades (RR = 20-30 is possible)
- Most trades will still be within -10 to 10
- Still prevents infinite values
- Simple change with minimal risk

---

### 2. Exponential Decay Now Handles Negative Values

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py`

**Function**: `estimate_half_life()`

**What Changed**:
- **Before**: Only worked on positive values (filtered out negative/zero)
- **After**: Works on both positive and negative values using exponential decay toward zero

**Implementation**:
1. **Uses absolute values for fitting**: `|y| = |y_0| * exp(-λt)`
2. **Preserves sign**: Model is `y(t) = sign(y_0) * |y_0| * exp(-λt)` (decays toward zero)
3. **Handles zero-crossing**: If values cross zero, uses the more recent segment (after zero-crossing) if enough data, otherwise uses segment before zero-crossing

**How It Works**:
- **Positive values**: `[2.0, 1.5, 1.0, 0.5]` → fits exponential decay toward 0
- **Negative values**: `[-0.5, -0.3, -0.1, -0.05]` → fits exponential decay toward 0
- **Crossing zero**: `[2.0, 1.0, 0.0, -0.5]` → uses segment after zero-crossing (if enough data)

**Benefits**:
- ✅ Handles all RR values (positive, negative, zero-crossing)
- ✅ Models decay toward zero naturally
- ✅ No information loss (uses all trades)
- ✅ Mathematically sound (exponential decay model)

---

## Technical Details

### Exponential Decay Model

**Formula**: `y(t) = sign(y_0) * |y_0| * exp(-λt)`

**Fitting Process**:
1. Take absolute values: `|y| = |y_0| * exp(-λt)`
2. Take log: `ln(|y|) = ln(|y_0|) - λt`
3. Linear regression on `(t, ln(|y|))` → get `λ`
4. Half-life: `t_half = ln(2) / λ`

**Zero-Crossing Handling**:
- If values cross zero, find the crossing point
- Use the segment with more data (prefer recent segment if both have enough data)
- Fit exponential decay on that segment

---

## Testing Recommendations

1. **Test with positive values**: `[2.0, 1.5, 1.0, 0.5]` → should fit exponential decay
2. **Test with negative values**: `[-0.5, -0.3, -0.1, -0.05]` → should fit exponential decay
3. **Test with zero-crossing**: `[2.0, 1.0, 0.0, -0.5]` → should use recent segment
4. **Test with all zeros**: `[0.0, 0.0, 0.0]` → should return None (insufficient data)
5. **Test with mixed signs (no crossing)**: `[2.0, 1.5, -0.5, -0.3]` → should use absolute values

---

## Impact

### What This Fixes
- ✅ Can now fit decay on patterns with negative RR values
- ✅ Can now fit decay on patterns that cross zero
- ✅ No longer loses information from negative trades
- ✅ More accurate decay modeling

### What Stays the Same
- ✅ Decay multiplier still ranges from 0.5 to 1.5
- ✅ Decay multiplier still multiplied into edge_raw
- ✅ State detection (decaying/improving/stable) still works
- ✅ Half-life calculation still works (just handles more cases)

---

## Files Changed

1. `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
   - Updated RR bounds from -10 to 10 → -33 to 33

2. `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py`
   - Rewrote `estimate_half_life()` to handle negative values
   - Added zero-crossing detection and handling
   - Uses absolute values for fitting, preserves sign

---

## Next Steps

1. **Monitor**: Watch for any issues with decay fitting on negative values
2. **Validate**: Check that half-life values make sense for both positive and negative patterns
3. **Consider**: May want to add logging for zero-crossing cases to understand how often it happens

