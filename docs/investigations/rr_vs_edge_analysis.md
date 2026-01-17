# RR vs Edge Analysis - Learning System Issues

## Problem Summary

The learning system is using **raw RR** for timeframe weights, but it should be using **edge** (delta_rr relative to baseline). This causes:

1. **Outlier inflation**: 1m timeframe has one trade with RR=12.793, inflating the average to 5.915
2. **Incorrect comparisons**: 1h shows rr_short=0.041 but actual avg RR is -0.613
3. **Missing edge calculation**: System should use `edge_raw = delta_rr * reliability * integral` instead of raw RR

---

## Current State

### Learning Configs (What's Stored)
```
1m:  weight=1.000, rr_short=5.915, n=10  ❌ WAY TOO HIGH
15m: weight=0.500, rr_short=-0.723, n=10 ✅ Reasonable
1h:  weight=1.000, rr_short=0.041, n=1   ❌ Wrong (should be negative)
```

### Actual RR Values (From Closed Trades)
```
1m:  Avg RR = 0.204 (but with outlier RR=12.793)
     - Without outlier: Avg RR ≈ -0.5 to -0.6
     - Individual RRs: [12.793, -1.000, -0.907, -1.000, ...]

15m: Avg RR = -0.747 ✅ Matches learning_configs (-0.723)

1h:  Avg RR = -0.613 ❌ Doesn't match learning_configs (0.041)
```

---

## Root Cause

### 1. Outlier Problem (1m RR=12.793)

**The Trade**: DREAM token, PnL=$0.56 (6.9%), RR=12.793

**Why it's an outlier**:
- All other 1m trades have RR between -1.0 and 0.2
- This one trade has RR=12.793 (64x higher than next highest)
- With only n=10 trades, EWMA gives this outlier heavy weight

**Impact**:
- Inflates 1m rr_short from ~-0.5 to 5.915
- Makes 1m look like the best timeframe (when it's actually worst)

### 2. Using Raw RR Instead of Edge

**Current Code** (`coefficient_updater.py`):
```python
# Line 162: Uses raw RR value
new_rr_short = (1 - alpha_short) * current_rr_short + alpha_short * rr_value
```

**Problem**: 
- Raw RR doesn't account for baseline
- Should use `delta_rr = avg_rr - global_baseline_rr`
- Or better: use `edge_raw` which accounts for variance, support, etc.

**Lesson Builder** (`lesson_builder_v5.py`) already calculates edge correctly:
```python
# Line 238: Calculates delta_rr
delta_rr = avg_rr - global_baseline_rr

# Line 256: Calculates edge_raw
edge_raw = delta_rr * reliability_score * integral * decay_meta.get('multiplier', 1.0)
```

**But**: Coefficient updater doesn't use this - it uses raw RR!

---

## Recommendations

### 1. Use Edge Instead of Raw RR

**Change**: Update `coefficient_updater.py` to use edge (delta_rr) instead of raw RR

**Benefits**:
- Normalized against baseline (accounts for market conditions)
- More robust to outliers
- Consistent with lesson builder logic

**Implementation**:
```python
# Instead of:
new_rr_short = (1 - alpha_short) * current_rr_short + alpha_short * rr_value

# Use:
global_baseline = self._get_global_rr_short()
delta_rr = rr_value - global_baseline
new_delta_rr_short = (1 - alpha_short) * current_delta_rr_short + alpha_short * delta_rr
new_rr_short = global_baseline + new_delta_rr_short
```

### 2. Outlier Handling

**Option A: Cap Outliers**
```python
# Cap RR values to reasonable range
rr_value = max(-2.0, min(2.0, rr_value))  # Cap at ±2.0
```

**Option B: Use Median Instead of Mean**
```python
# Store median RR instead of mean (more robust to outliers)
# Requires storing all RR values or using approximate median
```

**Option C: Use Robust Statistics**
```python
# Use trimmed mean (remove top/bottom 10%)
# Or use IQR-based outlier detection
```

### 3. Use Edge from Lesson Builder

**Best Solution**: When lessons are mined, use the `edge_raw` from lessons instead of calculating from raw RR

**Flow**:
1. Lesson builder mines patterns → calculates `edge_raw` for each pattern
2. Aggregate edge by timeframe from lessons
3. Use aggregated edge for timeframe weights

**Benefits**:
- Already accounts for variance, support, decay
- Consistent with lesson mining logic
- More statistically sound

---

## Immediate Fix

### Quick Fix: Cap Outliers in Coefficient Updater

```python
# In coefficient_updater.py, _update_timeframe_weight_ewma()
# Add outlier capping:
rr_value = max(-2.0, min(2.0, rr_value))  # Cap at ±2.0
```

This will prevent the 12.793 outlier from inflating 1m RR.

---

## Long-term Solution

1. **Switch to Edge**: Use `delta_rr` or `edge_raw` instead of raw RR
2. **Use Lesson Data**: When lessons exist, aggregate edge by timeframe from lessons
3. **Robust Statistics**: Use median or trimmed mean for small samples
4. **Validation**: Add checks to detect and flag outliers

---

## Verification

After fixes, verify:
- 1m rr_short should be negative (around -0.5 to -0.6)
- 1h rr_short should match actual avg RR (-0.613)
- Timeframe weights should reflect actual performance

