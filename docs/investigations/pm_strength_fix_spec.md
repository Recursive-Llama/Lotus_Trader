# PM Strength Fix: Specification

## Problem Statement

The current `lesson_builder_v5` treats action-level events as independent observations, but they are clustered by `trade_id` (all actions from one trade share the same outcome). This violates statistical independence assumptions and corrupts:
- `n` (support score)
- `variance` (reliability score)
- `edge_raw` (downstream calculations)

## Fix Specification

### Rule: Trade-Normalized Learning

> **For all lesson mining statistics, the effective sample unit is `trade_id`.**
> 
> Multiple action events within the same trade may enrich scope coverage, but must not increase `n`, reduce variance, or inflate confidence beyond the trade count.

### Implementation: Deduplicate by trade_id per slice

**Location:** `lesson_builder_v5.py::mine_lessons()`

**Change:**
Inside the recursive mining function, after filtering to a specific `(pattern_key, action_category, scope_subset)` slice, deduplicate by `trade_id` before computing statistics.

**Key Point:** Trade deduplication must happen **inside** each `(pattern_key, action_category, scope_subset)` slice, not at a higher level.

**Pseudocode:**
```python
# Current structure (lesson_builder_v5.py):
# 1. Group by (pattern_key, action_category) first
grouped = df.groupby('group_key')  # group_key = (pattern_key, action_category)

for (pk, cat), group_df in grouped:
    # 2. Recursive mining over scope_subset combinations
    def mine_recursive(slice_df: pd.DataFrame, current_mask: Dict, start_dim_idx: int):
        # slice_df is already filtered to (pk, cat, current_mask)
        
        # Current (WRONG):
        slice_events = slice_df[['rr', 'timestamp']].to_dict('records')
        stats = compute_lesson_stats(slice_events, global_baseline_rr)
        # n = len(slice_events)  # ← Counts all actions in this slice

# Fixed (CORRECT):
def mine_recursive(slice_df: pd.DataFrame, current_mask: Dict, start_dim_idx: int):
    # slice_df is filtered to (pattern_key=pk, action_category=cat, scope_subset=current_mask)
    
    # Deduplicate by trade_id within this slice (keep first action per trade)
    deduplicated = slice_df.drop_duplicates(subset=['trade_id'], keep='first')
    slice_events = deduplicated[['rr', 'timestamp']].to_dict('records')
    stats = compute_lesson_stats(slice_events, global_baseline_rr)
    # n = len(slice_events)  # ← Counts distinct trades in this slice
```

**Why `keep='first'`:**
- All actions from same trade have same `rr` anyway
- `first` is arbitrary but consistent
- Could also use `keep='last'` or average - doesn't matter since RR is identical per trade

### What This Preserves

✅ **Action-specific learning:**
- Still groups by `action_category` (entry vs add vs trim vs exit)
- Still groups by `scope_subset` (context at time of action)
- Different actions from same trade can still land in different slices

✅ **Scope coverage:**
- If 56 actions span 10 different scopes, they create 10 different lessons
- Each lesson gets `n = count of trades in that scope`
- Not `n = 56` (which would be wrong)

### What This Fixes

❌ **Before:**
- One trade with 56 actions in same scope → `n=56`, `support_score=0.67`
- All 56 have same RR → `variance=0.0`, `reliability_score=1.0`
- Inflated `edge_raw`

✅ **After:**
- Same trade → `n=1`, `support_score=0.02`
- `variance=0.0` (only one data point), but `reliability_score` is now correctly low-weighted by support
- Correct `edge_raw`

## Additional Fix: Small-N Reliability Correction

**Problem:** Even with trade deduplication, small `n` can still produce `variance=0.0` → `reliability_score=1.0`, over-trusting tiny samples.

**Important Note:** After dedup, this is **much less dangerous** because:
- `support_score` will be tiny at `n=1..3`
- Edge pipeline already multiplies several terms (including `support_score` in `integral`)

However, it's still worth fixing to prevent edge cases.

**Fix: Variance Shrinkage Prior**

Add a variance prior that shrinks with sample size. This avoids double-counting `support_score` (which is already in `integral`) while preventing over-trust of small samples.

```python
# Current (lesson_builder_v5.py:240):
reliability_score = 1.0 / (1.0 + variance)

# Fixed:
VAR_PRIOR = 0.25  # Tune based on expected RR variance (0.25 = reasonable default)
prior_variance = VAR_PRIOR / max(1, n)  # Shrinks as n grows
adjusted_variance = variance + prior_variance
reliability_score = 1.0 / (1.0 + adjusted_variance)
```

**Why this approach:**
- ✅ Keeps reliability purely "shape/dispersion" (doesn't mix with support)
- ✅ For `n=1`: `prior_variance = 0.25` → `reliability_score = 1/(1+0.25) = 0.8` (not 1.0)
- ✅ For `n=10`: `prior_variance = 0.025` → minimal impact
- ✅ For `n=33+`: `prior_variance ≈ 0.008` → negligible
- ✅ Avoids double-counting `support_score` (which is already in `integral`)

**Alternative framing:** This is a "variance shrinkage prior" that fades with `n`, ensuring reliability doesn't collapse to 1.0 for tiny samples.

## Testing

### Test Case 1: Single Trade with Many Actions
**Setup:**
- 1 trade with 56 "add" actions
- All actions have `rr = -0.88`
- All actions in same scope

**Expected:**
- `n = 1` (not 56)
- `support_score ≈ 0.02` (not 0.67)
- `variance = 0.0` (only one data point)
- `edge_raw` is correctly low

### Test Case 2: Multiple Trades, Same Scope
**Setup:**
- 3 trades, each with 10 "add" actions
- All actions in same scope
- Trade 1: `rr = 1.0`
- Trade 2: `rr = 2.0`
- Trade 3: `rr = 0.5`

**Expected:**
- `n = 3` (not 30)
- `avg_rr = (1.0 + 2.0 + 0.5) / 3 = 1.17`
- `variance = variance([1.0, 2.0, 0.5])` (not variance of 30 values)
- Correct `edge_raw`

### Test Case 3: Actions Span Multiple Scopes
**Setup:**
- 1 trade with 10 "add" actions
- 5 actions in scope A, 5 in scope B
- Trade `rr = 1.0`

**Expected:**
- Two lessons created (one per scope)
- Each lesson: `n = 1`
- Both lessons have same `rr = 1.0`
- Correct `edge_raw` for each

### Test Case 4: One Trade Dominates (Pathological Case)
**Setup:**
- Trade A: 1 trade_id, 100 "add" actions, all `rr = -0.5` (same scope)
- Trades B..K: 10 trade_ids, 1 "add" action each, `rr` distributed [0.5, 1.5, 2.0, ...] (same scope)

**Expected after fix:**
- `n = 11` (not 110)
- Trade A contributes exactly like one trade, not 100x
- `avg_rr` reflects all 11 trades equally
- `variance` reflects variance across 11 trades, not 110 actions
- Trade A cannot dominate the statistics

**This confirms the fix actually removes the pathological overweighting.**

## Migration

**No data migration needed:**
- This is a code fix only
- Existing `learning_lessons` will be recalculated on next run
- Old lessons will be overwritten with corrected statistics

**Backward compatibility:**
- Schema unchanged
- Downstream consumers (materializer, runtime) unchanged
- Only the statistics calculation changes

## Rollout

1. **Implement fix** in `lesson_builder_v5.py`:
   - Add trade_id deduplication inside `mine_recursive()` function
   - Apply to each `(pattern_key, action_category, scope_subset)` slice
2. **Add small-n reliability correction** (variance shrinkage prior)
3. **Test** with above test cases (especially Test Case 4 for domination)
4. **Run lesson builder** to regenerate all lessons
5. **Verify** `n` values are now trade counts, not action counts
6. **Monitor** edge_raw values for sanity (should be lower/more conservative)
7. **Verify** downstream materializer/runtime unchanged (only confidence math shifts, which is intended)

