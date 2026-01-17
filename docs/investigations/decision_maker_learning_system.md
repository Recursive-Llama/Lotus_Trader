# Decision Maker Learning System - Deep Dive

## Overview

The Decision Maker learning system adjusts **timeframe allocation** based on historical R/R performance. It uses **Exponentially Weighted Moving Average (EWMA)** with temporal decay to learn which timeframes perform better.

---

## How It Works

### 1. **What It Learns**

The system learns **timeframe weights** that control how capital is allocated across timeframes (1m, 15m, 1h, 4h) when creating new positions.

**Formula**:
```
timeframe_weight = timeframe_rr_short / global_rr_short
```

Where:
- `timeframe_rr_short` = EWMA of R/R for that timeframe (14-day decay)
- `global_rr_short` = EWMA of R/R across all timeframes (14-day decay)

**Weight Interpretation**:
- Weight = 1.0 → Performs at average
- Weight = 1.4 → Performs 40% better than average
- Weight = 0.8 → Performs 20% worse than average

### 2. **How It Updates**

**Update Trigger**: Every time a position closes (via `position_closed` strand)

**Update Process**:
1. Extract R/R from closed trade
2. Update timeframe's `rr_short` using EWMA with 14-day decay
3. Update global R/R baseline using EWMA
4. Calculate new weight: `weight = rr_short / global_rr_short`
5. Store in `learning_configs.config_data.timeframe_weights[timeframe]`

**EWMA Formula**:
```python
alpha = decay_weight / (decay_weight + 1.0)
new_rr_short = (1 - alpha) * old_rr_short + alpha * new_rr_value
```

Where `decay_weight = exp(-days_ago / 14)` (14-day time constant)

### 3. **How It's Applied**

**When**: Decision Maker creates new positions for a token

**Process**:
1. DM calculates `total_allocation_usd` (total for the token)
2. Gets learned timeframe weights from `learning_configs`
3. Normalizes weights to sum to 1.0
4. Splits allocation: `alloc_cap_usd[tf] = total_allocation_usd * normalized_weight[tf]`

**Example**:
```
Learned weights: {15m: 1.4, 1h: 1.1, 4h: 0.9}
Normalized: {15m: 0.41, 1h: 0.32, 4h: 0.27}
Total allocation: $1000
Result: 15m=$410, 1h=$320, 4h=$270
```

**Fallback**: If no learned data (all weights = 1.0), uses default splits:
- 1m: 10% of base (fixed, separate)
- 15m: 12.5%
- 1h: 70%
- 4h: 12.5%

---

## Current State

### Data from `learning_configs` (as of 2026-01-09):

**Timeframe Weights**:
- **1m**: weight=1.000, rr_short=-0.755, n=15
- **15m**: weight=1.000, rr_short=-0.864, n=14
- **1h**: weight=1.000, rr_short=0.041, n=1
- **4h**: No data yet

**Global R/R Baseline**:
- rr_short=-0.918, n=30

### Analysis

**Problem**: All weights are 1.0, meaning **no learning is being applied**!

**Why?**
- All timeframes have negative R/R (except 1h with only 1 trade)
- Global baseline is also negative (-0.918)
- When both numerator and denominator are negative, the ratio can be misleading
- With only 30 total trades, we don't have enough data yet

**Current Allocation**: System is using **default splits** (not learned weights)

---

## Minimum Sample Size

### **No Hard Minimum - But Practical Considerations**

The system **starts learning from trade #1**, but:

1. **EWMA is sensitive to early trades** - First few trades have high weight
2. **Weight calculation needs stable global baseline** - Need ~10-20 trades for stable global R/R
3. **Practical minimum**: ~5-10 trades per timeframe for meaningful weights
4. **Confidence threshold**: ~20-30 trades per timeframe for reliable weights

### Current Sample Sizes:
- 1m: 15 trades ✅ (enough)
- 15m: 14 trades ✅ (enough)
- 1h: 1 trade ❌ (not enough)
- 4h: 0 trades ❌ (no data)

**Conclusion**: We have enough trades for 1m and 15m, but weights are still 1.0 because:
1. All R/R values are negative
2. Global baseline is negative
3. The ratio calculation may not be working correctly with negative values

---

## Issues Identified

### 1. **Using R/R Instead of ROI**

**Problem**: 
- R/R can be negative even when trade is profitable (due to trims/re-entries)
- Current system uses raw R/R from `completed_trade.summary.rr`
- This leads to misleading weights

**Example**:
- Trade makes $1.39 profit (27% ROI)
- But R/R = -0.308 (negative!)
- System learns "this timeframe is bad" when it's actually good

**Solution**: Switch to ROI (`rpnl_pct`) instead of R/R

### 2. **Negative R/R Handling**

**Problem**:
- When both timeframe R/R and global R/R are negative, the weight calculation is problematic
- Weight = -0.755 / -0.918 = 0.82 (but this doesn't mean 1m is worse - it's actually better!)

**Solution**: Use ROI which is always positive when profitable

### 3. **Weight Bounds**

**Current**: Weights are bounded to [0.5, 2.0]

**Issue**: With negative R/R, weights might be getting clamped incorrectly

---

## Recommendations

### 1. **Switch to ROI-Based Learning**

**Change**:
```python
# Instead of:
rr_value = completed_trade.get('rr')

# Use:
roi_value = completed_trade.get('rpnl_pct') / 100.0  # Convert % to decimal
```

**Benefits**:
- ROI is positive when profitable, negative when losing
- Matches actual PnL
- No confusion with negative ratios

### 2. **Update Formula**

**New Formula**:
```python
timeframe_weight = timeframe_roi_short / global_roi_short
```

Where:
- `timeframe_roi_short` = EWMA of ROI for that timeframe
- `global_roi_short` = EWMA of ROI across all timeframes

### 3. **Add Minimum Sample Size Check**

**Recommendation**: Only apply learned weights if:
- `n >= 5` for that timeframe
- `n >= 10` for global baseline

Otherwise, use default splits.

### 4. **Handle Edge Cases**

- If global ROI is negative, use absolute values or different normalization
- If timeframe ROI is positive but global is negative, weight should be > 1.0
- Consider using median ROI instead of mean for robustness

---

## Code Locations

### Reading Weights
- **File**: `src/intelligence/universal_learning/coefficient_reader.py`
- **Method**: `get_timeframe_weights()`
- **Called by**: `decision_maker_lowcap_simple.py:_create_positions_for_token()`

### Updating Weights
- **File**: `src/intelligence/universal_learning/coefficient_updater.py`
- **Method**: `_update_timeframe_weight_ewma()`
- **Called by**: `universal_learning_system.py:_update_coefficients_from_closed_trade()`

### Applying Weights
- **File**: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`
- **Method**: `_create_positions_for_token()`
- **Lines**: 664-693

---

## Next Steps

1. **Switch to ROI-based learning** (instead of R/R)
2. **Test with current data** - See if weights change meaningfully
3. **Monitor allocation splits** - Verify they're being applied
4. **Add logging** - Track when learned weights are used vs defaults

