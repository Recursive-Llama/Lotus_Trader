# PM Strength: Multi-Outcome Design Analysis

**Date**: 2025-01-XX  
**Status**: Design Exploration - Multi-Outcome Learning for A/E Adjustment

---

## The Proposal

Instead of just using ROI to calculate a single `strength_mult` that affects sizing, use **multiple outcomes** to calculate **separate adjustments for A and E**:

### Outcomes to Track
1. **ROI** (current): `rpnl_pct` from trade
2. **Did it trim?** (boolean): Did the trade execute any trims?
3. **Did it reach S3?** (boolean): Did the trade reach S3 state before closing?

### Outcome → A/E Mapping

| ROI | Trimmed | Reached S3 | A Adjustment | E Adjustment | Reasoning |
|-----|---------|------------|-------------|--------------|-----------|
| ❌ Negative | ❌ No | ❌ No | **↓ Reduce** | **→ Keep** | Tuning issue, pattern not good, but no trim opportunity |
| ❌ Negative | ✅ Yes | ❌ No | **↓ Reduce** | **↑ Increase** | Pattern not great, but had opportunity to trim (should trim more aggressively) |
| ✅ Positive | ✅ Yes | ❌ No | **→ Keep** | **→ Keep** | Decent exit, multiple trims, but didn't complete full pattern |
| ✅ Positive | ✅ Yes | ✅ Yes | **↑ Increase** | **↓ Reduce** | Best outcome - full pattern completion, should be more aggressive, less urgent to exit |

---

## Part 1: Data Availability

### Current Data in `pattern_trade_events`

**What we have**:
- `rr`: R/R metric
- `pnl_usd`: Realized PnL
- `trade_id`: Links to parent trade
- `pattern_key`: Pattern identifier
- `action_category`: entry, add, trim, exit
- `scope`: Full context

**What we need to add**:
- `trimmed`: Boolean - did this trade have any trims?
- `reached_s3`: Boolean - did this trade reach S3 state?
- `roi`: `rpnl_pct` (we should switch from RR to ROI anyway)

### How to Capture This Data

**Option A: Add to `pattern_trade_events`** (per action)
- Add `trimmed` and `reached_s3` columns
- Populated from `trade_summary` or `completed_trades` when trade closes
- **Issue**: Multiple actions per trade share same outcome (already deduplicated by trade_id)

**Option B: Add to `position_closed` strand** (per trade)
- Add to `trade_summary`:
  ```json
  {
    "rr": 0.5,
    "pnl_usd": 100.0,
    "rpnl_pct": 0.05,
    "trimmed": true,
    "reached_s3": true,
    "max_state": "S3"  // Could also track max state reached
  }
  ```
- `pattern_scope_aggregator` reads this and adds to `pattern_trade_events`

**Option C: Query from execution history** (on-demand)
- When mining lessons, query `pm_execution_history` from position features
- Check if `last_trim` exists → `trimmed = true`
- Check if `max_state` or state history shows S3 → `reached_s3 = true`
- **Issue**: Need to join with position data, more complex

**Recommendation**: Option B - Add to `trade_summary` when trade closes, then propagate to `pattern_trade_events`.

---

## Part 2: Aggregation Strategy

### The Blending Problem

**Scenario**: 10 trades for pattern `uptrend.S1.entry`:
- 6 trades: Positive ROI + Reached S3 → Increase A, Reduce E
- 2 trades: Negative ROI + No Trim → Reduce A, Keep E
- 2 trades: Negative ROI + Trimmed → Reduce A, Increase E

**Question**: How do we calculate a single `a_multiplier` and `e_multiplier`?

### Option 1: Weighted Average by Outcome Count

```python
# Count outcomes
n_positive_s3 = 6  # Increase A, Reduce E
n_negative_no_trim = 2  # Reduce A, Keep E
n_negative_trimmed = 2  # Reduce A, Increase E

# Calculate adjustments (example values)
a_adjustments = {
    'positive_s3': +0.1,      # Increase A
    'negative_no_trim': -0.15, # Reduce A
    'negative_trimmed': -0.1,  # Reduce A
}

e_adjustments = {
    'positive_s3': -0.1,      # Reduce E
    'negative_no_trim': 0.0,   # Keep E
    'negative_trimmed': +0.15, # Increase E
}

# Weighted average
a_delta = (6 * 0.1 + 2 * -0.15 + 2 * -0.1) / 10 = 0.01  # Slight increase
e_delta = (6 * -0.1 + 2 * 0.0 + 2 * 0.15) / 10 = -0.03  # Slight decrease

# Convert to multipliers
a_multiplier = 1.0 + a_delta = 1.01
e_multiplier = 1.0 + e_delta = 0.97
```

**Pros**: Simple, handles mixed outcomes
**Cons**: Mixed signals might cancel out (6 positive vs 4 negative)

### Option 2: Majority Rule with Confidence

```python
# Determine dominant outcome
if n_positive_s3 > n_negative_no_trim + n_negative_trimmed:
    # Positive S3 is dominant
    a_multiplier = 1.1  # Increase A
    e_multiplier = 0.9  # Reduce E
    confidence = n_positive_s3 / total_trades  # 0.6
else:
    # Negative outcomes dominant
    if n_negative_no_trim > n_negative_trimmed:
        a_multiplier = 0.85  # Reduce A
        e_multiplier = 1.0   # Keep E
    else:
        a_multiplier = 0.9   # Reduce A
        e_multiplier = 1.15  # Increase E
    confidence = max(n_negative_no_trim, n_negative_trimmed) / total_trades
```

**Pros**: Clear signal, doesn't cancel out
**Cons**: Ignores minority outcomes, might be too binary

### Option 3: Separate A/E Calculations

```python
# Calculate A multiplier from A-relevant outcomes
a_relevant = {
    'positive_s3': 6,      # Increase A
    'negative_no_trim': 2, # Reduce A
    'negative_trimmed': 2, # Reduce A
}
# A: 6 positive vs 4 negative → slight increase
a_multiplier = 1.05

# Calculate E multiplier from E-relevant outcomes
e_relevant = {
    'positive_s3': 6,      # Reduce E
    'negative_trimmed': 2,  # Increase E
    'negative_no_trim': 2,  # Neutral (keep E)
}
# E: 6 reduce vs 2 increase → reduce
e_multiplier = 0.95
```

**Pros**: A and E can move independently
**Cons**: Still need to handle mixed signals

### Option 4: Score-Based System

```python
# Assign scores to each outcome
outcome_scores = {
    'positive_s3': {'a': +2, 'e': -2},      # Best outcome
    'positive_no_s3': {'a': 0, 'e': 0},    # Neutral
    'negative_trimmed': {'a': -1, 'e': +1}, # Reduce A, Increase E
    'negative_no_trim': {'a': -2, 'e': 0},  # Reduce A, Keep E
}

# Sum scores
a_score = (6 * 2 + 2 * -1 + 2 * -2) / 10 = 0.6
e_score = (6 * -2 + 2 * 1 + 2 * 0) / 10 = -1.0

# Convert to multipliers (with caps)
a_multiplier = 1.0 + clamp(a_score * 0.05, -0.2, +0.2) = 1.03
e_multiplier = 1.0 + clamp(e_score * 0.05, -0.2, +0.2) = 0.95
```

**Pros**: Flexible, handles mixed outcomes, can weight by confidence
**Cons**: More complex, need to tune score weights

**Recommendation**: Option 4 (Score-Based) - Most flexible, handles mixed outcomes well.

---

## Part 3: Integration with Current System

### Current Flow

1. **Lesson Builder**: Mines `pattern_trade_events`, calculates `edge_raw` from ROI
2. **Override Materializer**: Maps `edge_raw` → `multiplier` (single value)
3. **Runtime**: Applies `multiplier` to `position_size_frac`

### Proposed Flow

1. **Lesson Builder**: Mines `pattern_trade_events`, calculates:
   - `a_score`: From outcome distribution (positive_s3, negative_no_trim, etc.)
   - `e_score`: From outcome distribution
   - `a_multiplier`: `1.0 + clamp(a_score * scale, -0.2, +0.2)`
   - `e_multiplier`: `1.0 + clamp(e_score * scale, -0.2, +0.2)`

2. **Override Materializer**: Writes to `pm_overrides`:
   ```json
   {
     "pattern_key": "pm.uptrend.S1.entry",
     "action_category": "entry",
     "scope_subset": {"timeframe": "15m"},
     "a_multiplier": 1.05,
     "e_multiplier": 0.95,
     "confidence_score": 0.8
   }
   ```

3. **Runtime**: Applies to A/E scores:
   ```python
   # In _apply_v5_overrides_to_action() or earlier
   a_final = a_base * a_multiplier  # Apply strength to A
   e_final = e_base * e_multiplier  # Apply strength to E
   
   # Then calculate sizing from adjusted A/E
   position_size_frac = 0.10 + (a_final * 0.50)
   ```

### Blending Multiple Overrides

**Current**: Blends `multiplier` values using weighted average

**Proposed**: Blend `a_multiplier` and `e_multiplier` separately:

```python
# Find all matching overrides
matches = find_matching_overrides(pattern_key, scope)

# Blend A multipliers
a_mults = []
a_weights = []
for m in matches:
    a_mult = m.get('a_multiplier', 1.0)
    weight = confidence * specificity
    a_mults.append(a_mult * weight)
    a_weights.append(weight)

final_a_mult = sum(a_mults) / sum(a_weights) if sum(a_weights) > 0 else 1.0

# Blend E multipliers (same logic)
final_e_mult = ...
```

**Result**: A and E can be adjusted independently based on different outcome patterns.

---

## Part 4: Complexity Analysis

### Is This Worth It?

**Pros**:
- ✅ More granular control (A and E independent)
- ✅ Better signal (considers execution quality, not just ROI)
- ✅ Handles edge cases (negative ROI but trimmed = different signal)
- ✅ Aligns with your intuition (4 distinct outcomes)

**Cons**:
- ❌ More complex (need to track 3 outcomes, map to 2 adjustments)
- ❌ Need to add data capture (trimmed, reached_s3)
- ❌ Blending is more complex (2 multipliers vs 1)
- ❌ Need to tune score weights and scales

### Complexity Comparison

| Aspect | Current (ROI → Sizing) | Proposed (Multi-Outcome → A/E) |
|--------|------------------------|--------------------------------|
| **Data Points** | 1 (ROI) | 3 (ROI, trimmed, reached_s3) |
| **Calculations** | 1 multiplier | 2 multipliers (A, E) |
| **Blending** | Simple (weighted avg) | More complex (2 separate blends) |
| **Data Capture** | Already have | Need to add 2 booleans |
| **Tuning** | 1 threshold (0.05) | Multiple score weights |

**Verdict**: Moderate increase in complexity, but provides significantly more control.

---

## Part 5: Implementation Path

### Phase 1: Data Capture
1. Add `trimmed` and `reached_s3` to `trade_summary` when trade closes
2. Update `pattern_scope_aggregator` to include these in `pattern_trade_events`
3. Add migration to add columns to `pattern_trade_events`

### Phase 2: Lesson Builder Update
1. Update `compute_lesson_stats()` to:
   - Count outcomes by category (positive_s3, negative_no_trim, etc.)
   - Calculate `a_score` and `e_score` from outcome distribution
   - Calculate `a_multiplier` and `e_multiplier`
2. Update `learning_lessons` schema to store `a_multiplier` and `e_multiplier`

### Phase 3: Override Materializer Update
1. Update `materialize_pm_strength_overrides()` to write `a_multiplier` and `e_multiplier`
2. Update `pm_overrides` schema to store both multipliers

### Phase 4: Runtime Application
1. Update `apply_pattern_strength_overrides()` to return `(a_multiplier, e_multiplier)`
2. Update `_apply_v5_overrides_to_action()` to apply to A/E scores:
   ```python
   a_final = a_base * a_multiplier
   e_final = e_base * e_multiplier
   ```
3. Calculate sizing from adjusted A/E (already happens)

---

## Part 6: Open Questions

1. **Score Weights**: What should the score weights be for each outcome?
   - `positive_s3`: `{'a': +2, 'e': -2}`?
   - `negative_no_trim`: `{'a': -2, 'e': 0}`?
   - Need to tune based on desired sensitivity

2. **Multiplier Caps**: What should the caps be?
   - Current: `[0.3, 3.0]` for sizing
   - Proposed: `[0.8, 1.2]` for A/E? (more conservative)

3. **Confidence Threshold**: When is there enough data?
   - Current: `n >= 33` for lessons
   - Should we require more for multi-outcome?

4. **Blending**: Should A and E blend independently, or together?
   - Independent: More flexible
   - Together: More consistent

5. **Timing**: When to apply A/E adjustment?
   - Before action planning (affects decision thresholds)
   - After action planning (affects sizing only)
   - Both?

---

## Part 7: Recommendation

**Yes, this is worth implementing**, but with some simplifications:

1. **Start with 2 outcomes** (ROI + trimmed), add S3 later
2. **Use score-based system** (Option 4) for flexibility
3. **Apply to A/E scores** (not sizing) for more control
4. **Conservative caps** (`[0.9, 1.1]` initially) to avoid over-adjustment
5. **Keep blending simple** (weighted average per multiplier)

**Why this works**:
- More granular control (A and E independent)
- Better signal (considers execution quality)
- Fits naturally into current system (just change what strength affects)
- Not too complex (2 outcomes, 2 multipliers)

**Next Steps**:
1. Add data capture (trimmed, reached_s3)
2. Update lesson builder to calculate A/E scores
3. Update override materializer to write A/E multipliers
4. Update runtime to apply to A/E scores
5. Test and tune score weights

