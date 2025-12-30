# PM Strength: Final Verdict on Action Counting vs Trade Counting

## Executive Summary

**Current behavior is statistically incorrect and should be fixed.**

The system currently counts **actions** (events) instead of **trades**, which:
1. ✅ Provides more data points for learning
2. ❌ Violates statistical independence (all actions from one trade share the same outcome)
3. ❌ Artificially inflates support scores
4. ❌ Artificially deflates variance (making patterns look more reliable than they are)
5. ❌ Allows one trade to dominate statistics

## How It Affects the System

### 1. Edge Calculation (`edge_raw`)

```python
# lesson_builder_v5.py:248
edge_raw = delta_rr * reliability_score * integral * decay_meta.get('multiplier', 1.0)
```

Where:
- `reliability_score = 1.0 / (1.0 + variance)` ← **Affected by action counting**
- `integral = support_score + magnitude_score + time_score + stability_score`
- `support_score = 1.0 - exp(-n / 50.0)` ← **Affected by action counting**

**Impact:**
- One trade with 56 actions → `n=56` → `support_score = 0.67`
- If all 56 actions have same RR → `variance = 0.0` → `reliability_score = 1.0`
- This inflates `edge_raw`, making the pattern look stronger than it is

### 2. Runtime Override Application

```python
# overrides.py:77
weight = confidence * specificity
```

Where `confidence = support_score * reliability_score` (from materializer)

**Impact:**
- Inflated `support_score` and `reliability_score` → inflated `confidence`
- Runtime gives more weight to overrides that shouldn't have high confidence
- One trade with many actions gets disproportionate influence

### 3. Materializer Filtering

```python
# override_materializer.py:66
if abs(edge_raw) < EDGE_SIGNIFICANCE_THRESHOLD:
    continue
```

**Impact:**
- Inflated `edge_raw` from action counting can push lessons over the threshold
- Lessons that shouldn't be materialized get materialized
- System applies overrides based on incorrect statistics

## Real-World Example

**Your Data:**
- 19 closed trades
- 197 total events (actions)
- One trade has 56 "add" actions, all with `rr = -0.88`

**Current System:**
- Lesson for `uptrend.S3.add` with specific scope: `n=56`
- All 56 actions have `rr = -0.88`
- `variance = 0.0` (artificially low!)
- `support_score = 0.67` (artificially high!)
- `reliability_score = 1.0` (artificially high!)
- `edge_raw` is inflated

**If Counting Trades:**
- Same lesson: `n=1` (one trade)
- `variance = 0.0` (only one data point)
- `support_score = 0.02` (correctly low)
- `reliability_score = 1.0` (but with low support)
- `edge_raw` is much lower (correctly)

## Recommendation: Count Distinct Trades

### Why This Is Better

1. **Statistical Correctness**
   - Each trade is an independent observation
   - Variance calculation is correct
   - Support scores reflect actual evidence

2. **Fairness**
   - Each trade contributes equally
   - One trade can't dominate statistics

3. **Simplicity**
   - Easier to understand and debug
   - Clearer what `n` represents

4. **Action Context Still Preserved**
   - We still learn "this action in this context led to this outcome"
   - We just don't count it multiple times
   - Different actions from same trade can still have different contexts (scope)

### Implementation

```python
# In lesson_builder_v5.py::mine_lessons()
# After grouping by (pattern_key, action_category, scope_subset):

# Option 1: Deduplicate by trade_id (keep first action per trade)
deduplicated = group_df.drop_duplicates(subset=['trade_id'], keep='first')

# Option 2: Average RR per trade (more sophisticated)
trade_rrs = group_df.groupby('trade_id')['rr'].first()  # All same anyway
deduplicated = group_df.drop_duplicates(subset=['trade_id'], keep='first')

# Then proceed with deduplicated dataframe
slice_events = deduplicated[['rr', 'timestamp']].to_dict('records')
stats = compute_lesson_stats(slice_events, global_baseline_rr)
```

### Trade-offs

**Loss:**
- Fewer data points (19 trades vs 197 events)
- Some patterns may not reach `N_MIN_SLICE = 33`
- Less granular learning (but still action-specific)

**Gain:**
- ✅ Statistically correct
- ✅ Fair representation
- ✅ Correct variance and support scores
- ✅ Better decision-making

## Alternative: Weighted Approach (If We Need More Data)

If we need more data points but want statistical correctness:

```python
# Weight each action by 1 / actions_per_trade
group_df['trade_weight'] = 1.0 / group_df.groupby('trade_id')['trade_id'].transform('count')

# Use weighted statistics
weighted_avg_rr = (group_df['rr'] * group_df['trade_weight']).sum() / group_df['trade_weight'].sum()
weighted_n = group_df['trade_weight'].sum()  # Effective sample size
```

But this is more complex and may not be worth it.

## The Subtle Second Bug: Small-N Variance Collapse

Even after fixing action counting, there's a corner case:

```python
# lesson_builder_v5.py:240
reliability_score = 1.0 / (1.0 + variance)
```

**Problem:**
- If `n=2` and both trades have similar RR → `variance ≈ 0.0` → `reliability_score = 1.0`
- System over-trusts tiny samples
- Need to combine reliability with support to prevent "n=2 looks perfect"

**Fix needed:**
- Cap or shrink reliability for low `n`
- Or combine reliability with support: `effective_reliability = reliability_score * support_score`
- Or use a minimum variance floor based on sample size

## Conclusion

**The current behavior is a bug, not a feature.**

Counting actions instead of trades:
- Violates statistical independence (clustered observations treated as i.i.d.)
- Produces incorrect variance and support scores
- Inflates edge calculations
- Allows one trade to dominate

**Fix: Count distinct trades.**

This maintains action-specific context learning while ensuring statistical correctness. The trade-off of fewer data points is worth it for correct statistics.

### The Core Problem in One Sentence

> You're doing **clustered observations** (many rows per trade) but scoring them as if they were **i.i.d.** observations.

This specifically corrupts:
- `n` (support score)
- `variance` (reliability)
- Anything downstream that uses them (edge_raw thresholds, materialization weight)

### What the System Actually Wants

> "When we took action X under scope S, the eventual trade outcome tended to be Y."

That's **not** "56 independent outcomes."
That's "1 outcome with 56 contextual snapshots."

So the *unit of evidence* is the **trade**, not the action.

But you still want action-specific context (different scopes per action), which is preserved by the `scope_subset` grouping.

