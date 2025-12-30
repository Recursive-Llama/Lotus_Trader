# PM Strength: Counting Actions vs Trades - Deep Analysis

## Current Behavior

**What happens:**
1. Trade closes with final R/R = -0.88
2. Trade had 56 "add" actions during its lifetime
3. `pattern_scope_aggregator` writes 56 rows to `pattern_trade_events`:
   - All 56 rows have same `trade_id`
   - All 56 rows have same `rr = -0.88` (final trade R/R)
   - Each row has different `pattern_key` and `scope` (context at time of action)
4. `lesson_builder_v5` counts these 56 rows as `n=56` in `learning_lessons`
5. Edge calculation uses `n=56` for support_score and variance

## Statistical Analysis

### Problem 1: Violation of Independence

**The Issue:**
- All 56 actions share the **same outcome** (final trade R/R)
- They are **not independent observations**
- Statistical measures (variance, confidence intervals) assume independence

**Impact on Variance:**
```python
# Current code (lesson_builder_v5.py:227)
variance = statistics.variance(rrs) if n > 1 else 0.0
```

If all 56 actions have `rr = -0.88`:
- Variance = 0.0 (artificially low!)
- `reliability_score = 1.0 / (1.0 + 0.0) = 1.0` (artificially high!)
- `edge_raw` gets inflated by high reliability_score

**Example:**
- Trade 1: 56 actions, all with rr = -0.88 → variance = 0.0
- Trade 2: 1 action, rr = -0.88 → variance = 0.0 (but n=1)
- Trade 3: 1 action, rr = 2.0 → variance = 0.0 (but n=1)

If we group all together:
- 58 actions total
- But only 3 independent outcomes
- Variance calculation treats them as 58 independent observations

### Problem 2: Inflated Support Score

**The Issue:**
```python
# lesson_builder_v5.py:241
support_score = 1.0 - math.exp(-n / 50.0)
```

With `n=56`:
- `support_score = 1.0 - exp(-56/50) = 1.0 - 0.33 = 0.67`

If we counted trades instead (`n=1`):
- `support_score = 1.0 - exp(-1/50) = 1.0 - 0.98 = 0.02`

**Impact:**
- One trade with many actions dominates the statistics
- `edge_raw` gets inflated by high support_score
- System thinks it has strong evidence when it only has 1 trade

### Problem 3: RR Attribution

**The Issue:**
- All actions from a trade get the **same R/R** (final trade R/R)
- We're not learning "what was the outcome of this specific action"
- We're learning "what was the outcome of the trade that contained this action"

**Is this correct?**
- For **entry** actions: Makes sense - entry led to this trade outcome
- For **add** actions: Questionable - did this specific add contribute to the outcome?
- For **trim** actions: Questionable - did this trim affect the outcome?
- For **exit** actions: Makes sense - exit captured this outcome

**Current Design Intent:**
Looking at `pattern_scope_aggregator.py:152`:
```python
'rr': rr,  # Final trade R/R attributed to this action
```

The comment says "attributed" - so it's intentional that all actions get the same RR.

## Arguments FOR Counting Actions

### 1. Action-Specific Learning
**Claim:** Different actions (entry, add, trim, exit) have different patterns
- Entry might work well in one context
- Add might work well in another context
- Learning at action level captures these nuances

**Reality Check:**
- ✅ Actions DO have different contexts (different `scope` at time of action)
- ✅ Actions DO have different `pattern_key` values
- ❌ But they all share the same outcome (trade R/R)
- ❌ We can't learn "this add action was good" vs "this add action was bad" - they all have the same outcome

### 2. More Data Points = Better Statistical Power
**Claim:** 56 actions gives more statistical power than 1 trade

**Reality Check:**
- ❌ These are NOT independent data points
- ❌ They're 56 copies of the same outcome
- ❌ Statistical power comes from independent observations, not repeated measurements
- ✅ BUT: If actions have different contexts, we ARE learning "this context led to this outcome" - which is valuable

### 3. Context-Specific Learning
**Claim:** Each action has different context (scope), so we learn "this context → this outcome"

**Reality Check:**
- ✅ This is actually valid!
- ✅ If trade had 56 adds, and each add happened in different contexts (different scope values)
- ✅ We learn "add actions in context X led to outcome Y"
- ⚠️ BUT: We're still violating independence - all 56 contexts led to the SAME outcome

## Arguments AGAINST Counting Actions

### 1. Statistical Independence Violation
**The Core Problem:**
- All actions from one trade share the same outcome
- They are not independent observations
- Variance, confidence intervals, and statistical tests assume independence

**Impact:**
- Variance is artificially low (if all actions have same RR)
- Support score is artificially high (n=56 vs n=1)
- Edge calculation is inflated

### 2. One Trade Dominates Statistics
**The Problem:**
- One trade with 56 actions contributes 56x more to statistics than a trade with 1 action
- This is not fair - each trade should contribute equally

**Example:**
- Trade A: 1 entry action, rr = 2.0
- Trade B: 56 add actions, rr = -0.88
- Current system: n=57, avg_rr = (2.0 + 56*(-0.88)) / 57 = -0.85
- If counting trades: n=2, avg_rr = (2.0 + (-0.88)) / 2 = 0.56

### 3. Variance Calculation is Wrong
**The Problem:**
```python
variance = statistics.variance(rrs)  # Assumes independence
```

If we have:
- Trade 1: 10 actions, all rr = 1.0
- Trade 2: 5 actions, all rr = 2.0
- Trade 3: 1 action, rr = 0.5

Current calculation:
- 16 data points: [1.0, 1.0, ..., 1.0, 2.0, 2.0, ..., 2.0, 0.5]
- Variance = variance of these 16 values

Correct calculation (if counting trades):
- 3 data points: [1.0, 2.0, 0.5]
- Variance = variance of these 3 values

The current variance will be **much lower** than it should be, making the pattern look more reliable than it is.

## What Should We Do?

### Option 1: Count Distinct Trades (Conservative)
**Approach:**
- Group by `(pattern_key, action_category, scope_subset, trade_id)`
- Count distinct `trade_id` values
- Use average RR per trade (or just use the RR from one action per trade)

**Pros:**
- ✅ Statistically correct (independent observations)
- ✅ Each trade contributes equally
- ✅ Variance calculation is correct

**Cons:**
- ❌ Loses action-specific context learning
- ❌ Fewer data points (19 trades vs 197 events)
- ❌ May not reach N_MIN_SLICE (33) for many patterns

### Option 2: Weight by Trade (Hybrid)
**Approach:**
- Count actions, but weight them by `1 / actions_per_trade`
- So a trade with 56 actions contributes weight = 1/56 per action
- Total weight = 1.0 per trade

**Pros:**
- ✅ Maintains action-specific context learning
- ✅ Each trade contributes equally (weighted)
- ✅ More data points for learning

**Cons:**
- ⚠️ Variance calculation still needs adjustment
- ⚠️ More complex implementation

### Option 3: Keep Current (Action Counting) but Fix Statistics
**Approach:**
- Keep counting actions
- But adjust variance calculation to account for trade-level clustering
- Use cluster-robust standard errors or similar

**Pros:**
- ✅ Maintains action-specific context learning
- ✅ More data points
- ✅ Can fix statistical issues

**Cons:**
- ⚠️ Complex variance adjustment
- ⚠️ Still violates independence assumption

## Recommendation

**I recommend Option 1: Count Distinct Trades**

**Reasoning:**
1. **Statistical Correctness:** This is the most important. We can't make good decisions with bad statistics.
2. **Fairness:** Each trade should contribute equally to learning.
3. **Simplicity:** Easier to understand and debug.
4. **Action Context Still Preserved:** We still learn "this action in this context led to this outcome" - we just don't count it 56 times.

**Implementation:**
```python
# In lesson_builder_v5.py::mine_lessons()
# After grouping by (pattern_key, action_category, scope_subset):
# Deduplicate by trade_id, keeping one event per trade
df['trade_id'] = df['trade_id']  # Already have this
deduplicated = df.drop_duplicates(subset=['trade_id'], keep='first')
# Or: group by trade_id and take first, or average RR per trade

# Then proceed with deduplicated dataframe
n = len(deduplicated)  # Number of distinct trades
```

**Trade-off:**
- We'll have fewer data points (19 trades vs 197 events)
- But we'll have **correct** statistics
- And we can still learn action-specific patterns (just with fewer samples per pattern)

## Alternative: Action-Specific RR Attribution

**If we want to keep action counting, we need to fix RR attribution:**

Instead of attributing final trade R/R to all actions, we could:
- **Entry actions:** Get full trade R/R (makes sense)
- **Add actions:** Get partial R/R based on when they were added (complex)
- **Trim actions:** Get partial R/R based on what was trimmed (complex)
- **Exit actions:** Get full trade R/R (makes sense)

But this is much more complex and may not be worth it.

## Conclusion

**Current behavior is statistically incorrect** because:
1. It violates independence assumption
2. It inflates support scores
3. It understates variance
4. One trade can dominate statistics

**Recommendation:** Count distinct trades, not actions. This maintains action-specific context learning while ensuring statistical correctness.

