# Timeframe Allocation Learning - Design Analysis

## ROI vs Edge: Which Should We Use?

### Option 1: ROI (Simple)

**Pros**:
- ✅ Directly reflects PnL (what we care about)
- ✅ Simple to understand and implement
- ✅ Works from trade #1 (no minimum sample size)
- ✅ Positive when profitable, negative when losing
- ✅ No complex calculations

**Cons**:
- ❌ Doesn't account for variance (one big win vs consistent small wins)
- ❌ Doesn't account for sample size (2 trades vs 20 trades)
- ❌ Doesn't normalize against market conditions

**Formula**:
```python
timeframe_weight = timeframe_roi_short / global_roi_short
```

### Option 2: Edge (Sophisticated)

**Pros**:
- ✅ Accounts for variance (reliability)
- ✅ Accounts for sample size (support)
- ✅ Normalizes against baseline (delta_rr)
- ✅ Accounts for magnitude, time, stability
- ✅ More statistically sound

**Cons**:
- ❌ Requires N>=33 for lessons (too high for timeframes)
- ❌ Complex calculation (6-D edge)
- ❌ Harder to understand
- ❌ Might be overkill for allocation splits

**Formula**:
```python
edge_raw = delta_rr * reliability_score * (support + magnitude + time + stability) * decay
timeframe_weight = timeframe_edge / global_edge
```

### Recommendation: **Hybrid Approach**

Use **ROI with confidence weighting**:

```python
# Simple ROI for the value
timeframe_roi = EWMA(roi_values)

# Confidence based on sample size
confidence = min(1.0, n / 20.0)  # Full confidence at 20 trades

# Weighted allocation
if confidence < 0.5:
    # Low confidence: use default splits
    weight = 1.0
else:
    # High confidence: use learned ROI
    weight = timeframe_roi / global_roi
```

**Why**:
- Simple like ROI
- Accounts for sample size (the 4h problem)
- Works from trade #1 but doesn't over-trust early data
- Easy to understand and debug

---

## How Many Trades Do We Need?

### The 4h Problem

**Issue**: 4h trades are slower, so they'll have fewer trades and look less profitable early on.

**Example**:
- After 1 week: 1m has 15 trades, 4h has 2 trades
- 1m avg ROI: -6.6% (15 trades)
- 4h avg ROI: +5.0% (2 trades)
- System thinks: "1m is better" (more data) ❌

### Solutions

#### Option A: Confidence-Weighted (Recommended)

```python
# Weight by confidence (sample size)
confidence_1m = min(1.0, 15 / 20.0) = 0.75
confidence_4h = min(1.0, 2 / 20.0) = 0.10

# Blend learned weight with default
final_weight_1m = 0.75 * learned_weight_1m + 0.25 * default_weight_1m
final_weight_4h = 0.10 * learned_weight_4h + 0.90 * default_weight_4h
```

**Benefits**:
- Doesn't over-trust low-sample timeframes
- Gradually increases confidence as more trades come in
- 4h starts with defaults, slowly learns

#### Option B: Time-Normalized

```python
# Normalize by trades per week
trades_per_week_1m = 15 / 1.0 = 15
trades_per_week_4h = 2 / 1.0 = 2

# Weight by expected frequency
expected_ratio = trades_per_week_4h / trades_per_week_1m = 0.13
# 4h should have ~13% as many trades as 1m

# Adjust weight by frequency
adjusted_weight_4h = weight_4h * (1.0 / expected_ratio)  # Boost 4h
```

**Benefits**:
- Accounts for natural frequency differences
- Doesn't penalize slower timeframes

**Drawbacks**:
- More complex
- Assumes frequency ratios are constant

#### Option C: Minimum Sample Size

```python
# Only use learned weights if n >= threshold
if n_4h < 5:
    weight_4h = 1.0  # Use default
else:
    weight_4h = learned_weight_4h
```

**Benefits**:
- Simple
- Prevents over-trusting early data

**Drawbacks**:
- Hard cutoff (binary)
- 4h might take weeks to reach threshold

### Recommendation: **Confidence-Weighted (Option A)**

**Why**:
- Smooth transition (not binary)
- Accounts for sample size naturally
- Works from trade #1
- Easy to understand

**Implementation**:
```python
def get_timeframe_weight_with_confidence(timeframe, n, learned_roi, global_roi, default_weight=1.0):
    # Calculate confidence (0.0 to 1.0)
    confidence = min(1.0, n / 20.0)  # Full confidence at 20 trades
    
    # Calculate learned weight
    if global_roi != 0:
        learned_weight = learned_roi / global_roi
    else:
        learned_weight = 1.0
    
    # Blend learned with default based on confidence
    final_weight = confidence * learned_weight + (1 - confidence) * default_weight
    
    return final_weight
```

---

## Gradual vs Instant Updates

### How EWMA Works (It's Gradual!)

**Current System**: Uses EWMA with temporal decay

**Update Formula**:
```python
# Decay weight based on trade age
decay_weight = exp(-days_ago / 14)  # 14-day time constant

# Alpha (learning rate) depends on decay
alpha = decay_weight / (decay_weight + 1.0)

# Update with weighted average
new_roi = (1 - alpha) * old_roi + alpha * new_roi_value
```

### Examples

**Trade from today** (0 days old):
- `decay_weight = exp(0 / 14) = 1.0`
- `alpha = 1.0 / (1.0 + 1.0) = 0.5`
- **Impact**: 50% of new value, 50% of old value
- **Result**: Moderate update

**Trade from 7 days ago**:
- `decay_weight = exp(-7 / 14) = 0.61`
- `alpha = 0.61 / (0.61 + 1.0) = 0.38`
- **Impact**: 38% of new value, 62% of old value
- **Result**: Smaller update

**Trade from 14 days ago**:
- `decay_weight = exp(-14 / 14) = 0.37`
- `alpha = 0.37 / (0.37 + 1.0) = 0.27`
- **Impact**: 27% of new value, 73% of old value
- **Result**: Small update

**Trade from 28 days ago**:
- `decay_weight = exp(-28 / 14) = 0.14`
- `alpha = 0.14 / (0.14 + 1.0) = 0.12`
- **Impact**: 12% of new value, 88% of old value
- **Result**: Very small update

### Key Insights

1. **It's gradual, not instant** - Each trade updates by ~50% max (for today's trade)
2. **Recent trades matter more** - Today's trade has 5x more impact than 14-day-old trade
3. **Old trades fade away** - 28-day-old trade has minimal impact
4. **14-day half-life** - After 14 days, a trade's weight is ~37% of original

### Visual Example

**Starting state**: 15m ROI = -0.864 (from 14 trades)

**New trade**: 15m trade closes with ROI = +0.10

**Update**:
- `alpha = 0.5` (today's trade)
- `new_roi = 0.5 * (-0.864) + 0.5 * (0.10) = -0.382`
- **Change**: -0.864 → -0.382 (moved 56% toward new value)

**Next trade** (if also +0.10):
- `new_roi = 0.5 * (-0.382) + 0.5 * (0.10) = -0.141`
- **Change**: -0.382 → -0.141 (moved 63% toward new value)

**After 5 good trades** (+0.10 each):
- `new_roi ≈ +0.05` (gradually moved from negative to positive)

### Why This Is Good

1. **Resistant to outliers** - One bad trade doesn't destroy everything
2. **Adapts to trends** - If performance improves, weights gradually adjust
3. **Forgets old data** - Old bad performance fades away
4. **Smooth transitions** - No sudden jumps

---

## Complete Recommendation

### Use ROI with Confidence Weighting

**Formula**:
```python
# 1. Calculate ROI with EWMA (gradual updates)
timeframe_roi = EWMA(roi_values, tau=14 days)

# 2. Calculate confidence (sample size)
confidence = min(1.0, n / 20.0)

# 3. Calculate learned weight
if global_roi != 0:
    learned_weight = timeframe_roi / global_roi
else:
    learned_weight = 1.0

# 4. Blend with default based on confidence
final_weight = confidence * learned_weight + (1 - confidence) * default_weight

# 5. Normalize across timeframes
normalized_weight = final_weight / sum(all_final_weights)
```

**Benefits**:
- ✅ Simple (ROI, not complex edge)
- ✅ Gradual updates (EWMA)
- ✅ Accounts for sample size (confidence)
- ✅ Works from trade #1
- ✅ Handles 4h problem (low confidence = defaults)

**Minimum Trades**:
- **Starts learning**: Trade #1 (but with low confidence)
- **Meaningful learning**: ~5 trades per timeframe
- **Confident learning**: ~20 trades per timeframe
- **4h will be slow**: But that's OK - it uses defaults until it has enough data

---

## Implementation Plan

1. **Switch from R/R to ROI** in `coefficient_updater.py`
2. **Add confidence weighting** in `coefficient_reader.py`
3. **Update weight calculation** to blend learned + default
4. **Test with current data** - See how weights change
5. **Monitor allocation splits** - Verify they're being applied correctly

