# PM Tuning Simulation Feasibility Analysis

**Date**: 2025-01-XX  
**Purpose**: Analyze whether the proposed impact simulation approach is feasible

---

## The Challenge

**Goal**: Simulate "If we adjust TS by -0.05, how many misses would we catch? How many failures would we add?"

**Problem**: We need to know:
1. Which gate blocked each miss (we're capturing this ✅)
2. Which gate would have blocked each dodge if we lower thresholds (we need this)
3. Whether adjusting one gate would cause us to act on events that failed OTHER gates

---

## What We Can Do With Current Data

### For Misses (Skipped Successes):

**We have**:
- `blocked_by` array: ["ts"], ["slope"], ["halo"], etc.
- Signal values: `ts_score`, `halo_distance`, `slope`
- Threshold values: `ts_min`, `halo_max`, `slope_min`

**Simulation**:
```python
# If we lower TS by 0.05
misses_caught = 0
for miss in misses:
    if "ts" in miss["blocked_by"]:  # TS was the blocker
        if miss["ts_score"] >= (miss["ts_min"] - 0.05):  # Would pass new threshold
            # Check other gates still pass
            if miss["slope_ok"] and miss["halo_distance"] <= miss["halo_max"]:
                misses_caught += 1
```

**This works!** ✅ We can simulate TS adjustments for misses blocked by TS.

### For Dodges (Skipped Failures):

**We have**:
- Signal values: `ts_score`, `halo_distance`, `slope`
- Threshold values: `ts_min`, `halo_max`, `slope_min`
- Gate flags: `ts_ok`, `slope_ok`, `entry_zone_ok`

**Problem**: We don't know which gate blocked us from acting on a dodge.

**Simulation**:
```python
# If we lower TS by 0.05
failures_added = 0
for dodge in dodges:
    # Would we have acted with lower TS?
    if not dodge["ts_ok"]:  # TS was blocking
        if dodge["ts_score"] >= (dodge["ts_min"] - 0.05):  # Would pass new threshold
            # Check other gates
            if dodge["slope_ok"] and dodge["halo_distance"] <= dodge["halo_max"]:
                failures_added += 1  # We would have acted on this failure
```

**This works IF** we have gate flags! ✅ We can infer which gate blocked from `ts_ok`, `slope_ok`, `entry_zone_ok`.

---

## The Real Challenge: Multi-Gate Logic

**Problem**: An event might fail multiple gates. If we adjust one gate, we might catch events that fail OTHER gates.

**Example**:
- Miss has `blocked_by = ["ts"]` (TS blocked it)
- But if we lower TS, we catch it
- But what if it ALSO fails slope? We'd act on it, but it would still fail!

**Solution**: We need to check ALL gates pass:
```python
if miss["ts_score"] >= (miss["ts_min"] - 0.05):  # TS would pass
    if miss["slope_ok"] and miss["halo_distance"] <= miss["halo_max"]:  # Other gates pass
        misses_caught += 1
```

**This works IF** we have gate flags for all gates! ✅

---

## Testing Many Combinations

**Question**: Can we test halo 0.1 to 0.5 increase? That's 5 values × 3 levers = 15 combinations, plus all pairs = many more.

**Answer**: Yes, but we need to be smart:

1. **Narrow the search space**:
   - Only test reasonable ranges (e.g., TS: -0.1 to +0.1, Halo: -0.2 to +0.2)
   - Use step sizes (e.g., 0.05 increments)
   - Example: TS [-0.1, -0.05, 0, +0.05, +0.1] = 5 values
   - Halo [-0.2, -0.1, 0, +0.1, +0.2] = 5 values
   - Slope [-0.002, -0.001, 0, +0.001, +0.002] = 5 values

2. **Total combinations**:
   - Individual levers: 5 + 5 + 5 = 15
   - Pairs: 5×5 + 5×5 + 5×5 = 75
   - Triples: 5×5×5 = 125
   - **Total: 215 combinations** (manageable!)

3. **Optimization**:
   - Only test combinations where at least one lever addresses a blocker
   - If no misses blocked by TS, don't test TS adjustments
   - Use `blocked_by` data to narrow search

---

## Does It Actually Work?

### ✅ What Works:

1. **Simulating misses caught**: 
   - We know which gate blocked (`blocked_by`)
   - We can check if adjustment would unblock
   - We can verify other gates still pass

2. **Simulating failures added**:
   - We have gate flags (`ts_ok`, `slope_ok`, `entry_zone_ok`)
   - We can infer which gate blocked
   - We can check if adjustment would cause us to act

3. **Testing combinations**:
   - Computationally feasible (215 combinations is fine)
   - Can optimize by using `blocked_by` to narrow search

### ⚠️ Potential Issues:

1. **Gate interactions**:
   - Adjusting TS might change which events pass, but we still need to check other gates
   - This is handled by checking all gates pass

2. **Sample size**:
   - With n=104, we have enough data
   - But with smaller scope slices (e.g., n=32), simulation might be noisy
   - Need minimum samples for reliable simulation

3. **Overfitting**:
   - Testing many combinations might find spurious patterns
   - Solution: Only apply if success/failure ratio ≥ 2.0x AND sample size is sufficient

---

## Recommended Approach

### Phase 1: Simple Simulation (Start Here)

1. **For each lever independently**:
   - Test 3-5 adjustment values (e.g., TS: -0.1, -0.05, 0, +0.05, +0.1)
   - Calculate misses caught and failures added
   - Calculate success/failure ratio
   - Only consider adjustments where ratio ≥ 2.0x

2. **Select best individual lever**:
   - Pick the lever with highest ratio ≥ 2.0x
   - If none meet threshold, no adjustment

### Phase 2: Combination Testing (If Needed)

1. **If best individual lever has ratio ≥ 2.5x**:
   - Test combinations with that lever + one other
   - See if combination improves ratio further
   - Only if combination ratio > individual ratio

2. **Limit search**:
   - Only test combinations involving levers that address blockers
   - Use `blocked_by` data to narrow search

### Phase 3: Full Optimization (Future)

1. **Grid search** over reasonable ranges
2. **Gradient-based optimization** (if we have enough data)
3. **Bayesian optimization** (if we want to be fancy)

---

## Conclusion

**Yes, this approach works!** ✅

**Requirements**:
1. ✅ Capture `blocked_by` for misses (we're adding this)
2. ✅ Capture gate flags (`ts_ok`, `slope_ok`, `entry_zone_ok`) - need to verify in summary
3. ✅ Capture threshold values (`ts_min`, `halo_max`, `slope_min`) - we're adding this
4. ✅ Capture signal values (`ts_score`, `halo_distance`, `slope`) - already have

**Feasibility**:
- Testing 215 combinations is computationally fine
- Can optimize by using `blocked_by` to narrow search
- Start simple (individual levers), expand to combinations if needed

**Recommendation**: Start with Phase 1 (individual levers), validate it works, then expand to combinations if beneficial.

