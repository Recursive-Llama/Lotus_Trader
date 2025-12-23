# RR Bounds and Decay Analysis

## 1. RR Bounds: -10 to 10

### Current Implementation
```python
# Line 2196-2198 in pm_core_tick.py
# Bound R/R to reasonable range (e.g., -10 to 10)
if rr != float('inf') and rr != float('-inf'):
    rr = max(-10.0, min(10.0, rr))
```

### Why It Exists
1. **Prevents infinite values**: When `max_drawdown = 0`, RR becomes infinite
2. **Prevents extreme outliers**: RR = return_pct / max_drawdown can be very large if drawdown is tiny
3. **Keeps values manageable**: For learning calculations (averages, EWMA, etc.)

### The Math
- **RR = return_pct / max_drawdown**
- If return = 5% and max_drawdown = 0.1%, then RR = 50
- If return = -5% and max_drawdown = 0.1%, then RR = -50
- **Extreme values are possible** when drawdown is very small

### Should We Keep/Increase/Remove?

**Option A: Keep -10 to 10**
- ✅ Prevents outliers from skewing calculations
- ✅ Keeps learning system stable
- ❌ Loses information about truly exceptional trades
- ❌ Arbitrary cutoff

**Option B: Increase to -50 to 50 (or -100 to 100)**
- ✅ Captures more extreme values
- ✅ Still prevents infinite values
- ❌ Still arbitrary
- ❌ May still lose information on truly exceptional trades

**Option C: Remove bounds entirely**
- ✅ No information loss
- ✅ Captures all trades accurately
- ❌ Risk of extreme outliers skewing averages
- ❌ Need robust statistics (median, trimmed mean, etc.)

**Option D: Use robust statistics instead of bounds**
- ✅ No information loss
- ✅ Handles outliers naturally
- ✅ More statistically sound
- ❌ More complex implementation

### Recommendation
**Keep bounds but increase to -50 to 50**:
- Most trades will be within -10 to 10 anyway
- Captures extreme but realistic trades (RR = 20-30 is possible)
- Still prevents infinite values
- Simple to implement

**Alternative: Use trimmed mean** (remove top/bottom 5% of values when computing averages)
- More statistically sound
- No arbitrary bounds
- Handles outliers naturally

---

## 2. How Decay Is Used

### Current Usage
```python
# Line 219 in lesson_builder_v5.py
edge_raw = delta_rr * reliability_score * integral * decay_meta.get('multiplier', 1.0)
```

**Key Points:**
1. **Decay multiplier is multiplied into edge_raw**
2. **edge_raw can be positive or negative** (delta_rr can be negative)
3. **Decay multiplier ranges from 0.5 to 1.5**:
   - Short half-life (< 7 days): 0.5 to 0.9
   - Long half-life (≥ 7 days): 1.0
   - Improving pattern: up to 1.5
4. **Decay state is stored but not used** (only for telemetry)

### What This Means
- **Positive edge with decay**: `edge_raw = 0.1 * 0.8 = 0.08` (reduced by 20%)
- **Negative edge with decay**: `edge_raw = -0.1 * 0.8 = -0.08` (less negative, but still negative)
- **Decay reduces the magnitude** of edge (both positive and negative)

### The Problem
**Current decay fitting only works on positive RR values**:
- If RR goes from `[2.0, 1.5, 1.0]` → fits exponential decay ✅
- If RR goes from `[-0.5, -0.3, -0.1]` → can't fit (all filtered out) ❌
- If RR goes from `[2.0, 1.0, -0.5]` → only uses `[2.0, 1.0]` (loses negative) ❌

---

## 3. What Happens If Decay Goes Below 0?

### Option 1: Use Absolute Value, Preserve Sign

**The Approach:**
```python
# Fit exponential on absolute value
abs_values = [abs(v) for v in values]
# Fit: |y| = a * e^(-λt)
# Then apply sign: y = sign(y) * |y|
```

**Example: RR = [2.0, 1.0, 0.0, -0.5]**
1. Take absolute: `[2.0, 1.0, 0.0, 0.5]`
2. Fit exponential: `|y| = 2.0 * e^(-λt)`
3. Apply sign: `y = sign(y) * |y|`
   - `y(0) = +1 * 2.0 = 2.0` ✅
   - `y(1) = +1 * 1.0 = 1.0` ✅
   - `y(2) = +1 * 0.0 = 0.0` ✅
   - `y(3) = -1 * 0.5 = -0.5` ✅

**Problem:**
- **Sign is preserved from original data**, not from the fit
- If pattern crosses zero, we're fitting decay on `[2.0, 1.0, 0.0, 0.5]` (absolute values)
- But the actual pattern is `[2.0, 1.0, 0.0, -0.5]` (crossing zero)
- **We lose the information that it crossed zero**

**Better Approach:**
- Fit exponential decay **toward zero** (not toward a baseline)
- Model: `y = sign(y0) * |y0| * e^(-λt)`
- This naturally handles crossing zero:
  - Positive values decay toward 0: `2.0 → 1.0 → 0.5 → 0.0`
  - Negative values decay toward 0: `-0.5 → -0.3 → -0.1 → 0.0`
  - If it crosses zero, we fit two separate curves (before and after zero)

---

## 4. Recommended Solution

### Exponential Decay Toward Zero

**Model:**
```python
# For positive values: y = y0 * e^(-λt)  (decays toward 0)
# For negative values: y = y0 * e^(-λt)  (decays toward 0, but y0 is negative)
# If values cross zero: fit two separate curves
```

**Implementation:**
1. **Check if values cross zero**:
   - If all positive or all negative → fit single exponential
   - If crosses zero → fit two curves (before and after)

2. **For single curve (all positive or all negative)**:
   ```python
   # Take absolute value for fitting
   abs_values = [abs(v) for v in values]
   # Fit: |y| = |y0| * e^(-λt)
   # Result: y = sign(y0) * |y0| * e^(-λt)
   ```

3. **For crossing zero**:
   ```python
   # Split into two segments
   before_zero = [v for v in values if v >= 0]  # or v <= 0
   after_zero = [v for v in values if v < 0]     # or v > 0
   # Fit each separately
   # Use the more recent segment for half-life
   ```

**Benefits:**
- ✅ Handles both positive and negative values
- ✅ Naturally models decay toward zero
- ✅ Works for patterns that cross zero
- ✅ Simple and intuitive

---

## 5. RR Bounds Recommendation

### Keep Bounds, Increase to -50 to 50

**Rationale:**
1. **Prevents infinite values** (still needed)
2. **Captures extreme but realistic trades** (RR = 20-30 is possible)
3. **Most trades will be within -10 to 10 anyway** (bounds only affect outliers)
4. **Simple to implement** (just change the numbers)

**Alternative: Use trimmed statistics**
- Remove top/bottom 5% when computing averages
- No bounds needed
- More statistically sound
- But more complex

**My Recommendation: Increase to -50 to 50**
- Simple change
- Captures realistic extremes
- Still prevents infinite values
- Can always increase later if needed

---

## 6. Summary

### RR Bounds
- **Current**: -10 to 10
- **Recommendation**: Increase to -50 to 50
- **Reason**: Captures extreme but realistic trades, still prevents infinite values

### Decay Fitting
- **Current**: Only works on positive values
- **Recommendation**: Fit exponential decay toward zero (handles both positive and negative)
- **Implementation**: Use absolute value for fitting, preserve sign, handle zero-crossing

### Decay Usage
- **Current**: Multiplier (0.5 to 1.5) multiplied into edge_raw
- **Works correctly**: Reduces magnitude of edge (both positive and negative)
- **No changes needed**: The usage is correct, just need to fix the fitting

