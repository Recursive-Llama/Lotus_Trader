# Edge Decay Analysis & Implementation Plan

## Current State Summary

### 1. Edge History Storage

**What we have:**
- `learning_edge_history` table: stores snapshots of `edge_raw` over time
- Written by `pattern_scope_aggregator.py` on each stats update (line 627)
- Schema: `(pattern_key, action_category, scope_signature, edge_raw, ts, n)`
- Indexed for efficient queries by pattern+category+signature

**What we DON'T have:**
- `edge_history` array in `pattern_scope_stats.stats` JSONB
- Direct access to recent edge values without querying separate table

**Recommendation:**
❓ **Keep using `learning_edge_history` table - no array needed**

**Rationale:**
- Table is already indexed and efficient for queries
- We're already querying it for decay calculations
- Adding array would duplicate data without clear benefit
- Table supports long-term analysis better than capped JSONB array

**Alternative (if we want faster access):**
- Add small `edge_history` array (last 10-20 snapshots) to stats JSONB for quick slope calculation
- Still use table for half-life estimation (needs more history)
- Trade-off: slight duplication vs faster runtime access

**Implementation:**
```json
{
  "stats": {
    "edge_raw": 0.68,
    "n": 42,
    "avg_rr": 1.85,
    "variance": 0.32,
    "edge_history": [
      {"ts": "2024-01-15T10:00:00Z", "edge_raw": 0.72, "n": 40},
      {"ts": "2024-01-15T11:00:00Z", "edge_raw": 0.70, "n": 41},
      {"ts": "2024-01-15T12:00:00Z", "edge_raw": 0.68, "n": 42}
    ]
  }
}
```

**Rolling window size:** Keep last 30-50 snapshots in array, cap at reasonable size.

---

### 2. Decay Calculation

**What we have:**
- `half_life_estimator.py`: fits exponential decay curves `edge(t) = a * exp(-b * t)`
- `estimate_half_life()`: uses last 20-30 snapshots from `learning_edge_history` table
- Rolling window: **trade-based** (last N snapshots, not time-based)
- Half-life stored in `learning_lessons.decay_halflife_hours`

**Current approach:**
- Queries `learning_edge_history` table with `.limit(20-30)`
- Fits exponential decay curve using scipy or fallback linear regression
- Returns half-life in hours

**Questions:**
1. **Rolling window size?** Currently 20-30 snapshots
2. **How to select window?** Use all recent data points with timestamps

**Recommendation:**
✅ **Use recent data points (last N snapshots) - no artificial trade/time distinction**

**Rationale:**
- We're fitting a curve: `edge(t) = edge_0 * exp(-λ * t)`
- The curve doesn't care if data points are "trade-based" or "time-based" - it just needs `(edge, timestamp)` pairs
- If we have sparse data (few trades), use what we have - the curve fitting handles it


**What Renaissance Tech actually did:**
- Tracked alpha over time with timestamps
- Fit exponential decay curves to the time series
- Used half-life to determine when to reduce sizing
- **No artificial distinction between "trade-based" and "time-based"** - just time series data

**Implementation:**
```python
def compute_edge_slope(
    edge_history: List[Tuple[float, datetime]],
    min_points: int = 5
) -> Optional[float]:
    """
    Compute slope of edge over time using linear regression.
    
    Simple approach: fit line to (time, edge) points.
    Returns slope (negative = decaying, positive = improving, no pattern = no pattern).
    
    Args:
        edge_history: List of (edge_raw, timestamp) tuples
        min_points: Minimum points needed
    
    Returns:
        Slope (edge per hour), or None if insufficient data
    """
    if len(edge_history) < min_points:
        return None
    
    # Sort by timestamp
    edge_history = sorted(edge_history, key=lambda x: x[1])
    
    # Convert to hours since first observation
    first_ts = edge_history[0][1]
    times = [(ts - first_ts).total_seconds() / 3600.0 for _, ts in edge_history]
    edges = [edge for edge, _ in edge_history]
    
    # Simple linear regression: edge = a + b*t
    # slope = b
    n = len(times)
    sum_t = sum(times)
    sum_e = sum(edges)
    sum_t2 = sum(t * t for t in times)
    sum_te = sum(t * e for t, e in zip(times, edges))
    
    denom = n * sum_t2 - sum_t * sum_t
    if abs(denom) < 1e-10:
        return None
    
    slope = (n * sum_te - sum_t * sum_e) / denom
    return slope
```

**Note:** Stability is NOT part of decay. Stability is a separate dimension of edge (Stability-of-Edge from 6-D definition). Don't mix them.

**Are we using time series data?** ✅ **YES**
- We query `learning_edge_history` table with `(edge_raw, ts)` pairs
- We sort by timestamp: `sorted(edge_history, key=lambda x: x[1])`
- We convert to time deltas: `times = [(ts - first_ts).total_seconds() / 3600.0 ...]`
- We fit curves to `(time, edge)` pairs
- This is exactly what Renaissance Tech did - time series data with timestamps

---

### 3. PM/DM Sizing Multiplier

**What we have:**
- `apply_decay()` in `override_materializer.py`: exponential decay toward neutral (1.0)
- Formula: `value(t) = neutral + (value_0 - neutral) * exp(-lambda * t) * lesson_strength`
- Applied to both PM (`size_mult`, `entry_aggression_mult`, `exit_aggression_mult`) and DM (`alloc_mult`)
- Uses `decay_halflife_hours` from lessons

**Current approach:**
- Fixed exponential decay based on lesson age
- Decays toward neutral (1.0) regardless of current edge direction
- Uses half-life from historical curve fitting

**Renaissance Tech Insight:**
> "Alpha decays predictably, but the decay rate itself is learnable. More importantly, **decay direction matters more than decay rate**."

**Key insight:**
- If edge is **increasing** (slope > 0), we should **size up** (multiplier > 1.0)
- If edge is **decreasing** (slope < 0), we should **size down** (multiplier < 1.0)
- If edge is **stable** (slope ≈ 0), use neutral sizing

**Recommendation:**
✅ **Replace fixed exponential decay with adaptive decay based on edge slope**

**Implementation:**
```python
def adjust_multiplier_for_edge_direction(
    base_multiplier: float,
    edge_slope: Optional[float],
    max_adjustment: float = 0.1  # Max ±10% adjustment
) -> float:
    """
    Adjust multiplier based on edge direction (slope).
    
    Simple rule:
    - If edge is improving (slope > 0) → increase multiplier
    - If edge is decaying (slope < 0) → decrease multiplier
    - If edge is stable (slope ≈ 0) → no change
    
    Args:
        base_multiplier: Base multiplier from lesson
        edge_slope: Slope from compute_edge_slope() (edge per hour)
        max_adjustment: Maximum adjustment factor (0.1 = ±10%)
    
    Returns:
        Adjusted multiplier (clamped to bounds)
    """
    if edge_slope is None:
        return base_multiplier  # No data, use base
    
    # Normalize slope: convert to adjustment factor
    # Slope is in "edge per hour" - we need to scale it
    # Use tanh to bound the adjustment smoothly
    # 
    # Example: if slope = -0.01 edge/hour (decaying)
    #   tanh(-0.01 / 0.01) = tanh(-1.0) ≈ -0.76
    #   adjustment = -0.76 * 0.1 = -0.076 (7.6% decrease)
    #
    # Example: if slope = +0.02 edge/hour (improving fast)
    #   tanh(0.02 / 0.01) = tanh(2.0) ≈ 0.96
    #   adjustment = 0.96 * 0.1 = 0.096 (9.6% increase)
    #
    # The normalization factor (0.01) determines what counts as "significant":
    # - 0.01 edge/hour = moderate change → ~76% of max adjustment
    # - 0.02 edge/hour = fast change → ~96% of max adjustment
    # - Very steep slopes are capped at ±1.0 by tanh
    #
    # Question: Is 0.01 edge/hour the right threshold? This needs calibration.
    slope_normalized = np.tanh(edge_slope / 0.01)  # 0.01 edge/hour = significant change
    adjustment = slope_normalized * max_adjustment
    
    adjusted = base_multiplier * (1.0 + adjustment)
    
    # Clamp to bounds (0.7-1.3 for PM/DM)
    return max(0.7, min(1.3, adjusted))
```

**For PM:**
```python
# In apply_pattern_strength_overrides()
# Get edge history from table
edge_history = query_edge_history(pattern_key, action_category, scope_signature, limit=30)
edge_slope = compute_edge_slope(edge_history)

# Adjust multiplier based on edge direction
size_mult = adjust_multiplier_for_edge_direction(
    base_multiplier=size_mult_from_lesson,
    edge_slope=edge_slope,
    max_adjustment=0.1  # ±10% max adjustment
)
```

**For DM:**
```python
# In apply_allocation_overrides()
# Same approach
edge_history = query_edge_history(pattern_key, action_category, scope_signature, limit=30)
edge_slope = compute_edge_slope(edge_history)

alloc_mult = adjust_multiplier_for_edge_direction(
    base_multiplier=alloc_mult_from_lesson,
    edge_slope=edge_slope,
    max_adjustment=0.1  # Same ±10% max adjustment
)
```

**Key simplification:**
- No "sensitivity" parameter (arbitrary)
- No "stability_score" in decay (separate dimension)
- Just: edge slope → multiplier adjustment
- Simple, clear, based on actual edge direction

**Key differences from current approach:**
1. **Not just age-based**: Uses actual edge slope, not just time since lesson creation
2. **Directional**: Can size up if edge is improving, not just decay down
3. **Simple**: Just slope → adjustment, no arbitrary parameters
4. **Continuous**: Not fixed buckets, smooth function of edge direction

---

## Implementation Plan

### Phase 1: Edge Slope Calculation

1. **Add `compute_edge_slope()` function**:
   - Takes edge history from `learning_edge_history` table
   - Fits linear regression: `edge = a + b*t`
   - Returns slope (edge per hour)

2. **Query helper**:
   - Add function to query `learning_edge_history` table
   - Get last 20-30 snapshots for a pattern+category+scope
   - Return as list of `(edge_raw, timestamp)` tuples

### Phase 2: Adaptive Multiplier Adjustment

1. **Add `adjust_multiplier_for_edge_direction()` function**:
   - Takes base multiplier and edge slope
   - Returns adjusted multiplier based on direction
   - Simple: slope > 0 → increase, slope < 0 → decrease

2. **Update `apply_pattern_strength_overrides()`**:
   - Query edge history from table
   - Compute edge slope
   - Adjust `size_mult`, `entry_aggression_mult`, `exit_aggression_mult` based on slope

3. **Update `apply_allocation_overrides()`**:
   - Same approach for `alloc_mult`

4. **Keep existing `apply_decay()`**:
   - Still use for age-based decay (half-life from lessons)
   - New slope-based adjustment is additional signal
   - Can combine both: age decay + direction adjustment

---

## Questions for User

1. **Edge history storage**: 
   - Use table only (simpler, already works)?
   - Or add small array to stats JSONB for faster access (last 10-20 snapshots)?

2. **Rolling window size**: 
   - How many snapshots to use for slope calculation?
   - Current: 20-30 snapshots
   - More = smoother but slower to react, Less = faster reaction but noisier

3. **Max adjustment**: 
   - How much should edge slope affect multiplier?
   - Proposed: ±10% max adjustment
   - Too conservative? Too aggressive?

4. **Combining signals**:
   - Use slope-based adjustment only?
   - Or combine with existing age-based decay (half-life)?
   - If combine: how to weight each?

---

## Renaissance Tech Principles Applied

1. **Decay is predictable but learnable**: We fit curves to estimate half-life (already doing this)
2. **Direction matters more than rate**: We use slope to determine sizing direction
3. **Simple is better**: No arbitrary parameters, just edge direction → multiplier adjustment
4. **Continuous, not discrete**: Smooth functions, not fixed buckets
5. **Adaptive sizing**: Size up on improving edge, down on decaying edge

**What we're NOT doing (and why):**
- ❌ No "sensitivity" parameter (arbitrary, unclear meaning)
- ❌ No "stability_score" in decay (stability is separate dimension of edge)
- ❌ No artificial trade-based vs time-based distinction (just use time series data)
- ❌ No complex hybrid windows (just use recent data points)

