# PM Strength Learning - Deep Dive Analysis

**Date**: 2025-01-XX  
**Status**: Investigation Complete - Findings Documented

---

## Executive Summary

**Current State**:
- ✅ Data collection working: 103 `pattern_trade_events` exist
- ⚠️  No lessons exist: Lesson Builder may not have run or encountered issues
- ⚠️  No overrides exist: No lessons to materialize
- ⚠️  Using R/R instead of ROI: Same issue as Tuning system
- ⚠️  Blending vs Most Specific: Inconsistent with Tuning system approach

**Key Findings**:
1. Only 1 pattern meets N_MIN=33 threshold (S2.trim with n=52, 21 unique trades)
2. Pattern keys stored correctly: `module=pm|pattern_key=uptrend.S2.trim`
3. Lesson Builder is scheduled (hourly at :08) but no lessons exist
4. Edge calculation is sophisticated (6-D Edge Math) but uses R/R
5. Multiplier mapping is linear: `multiplier = 1.0 + edge_raw`
6. Blending approach differs from Tuning system (which uses most specific)

---

## Part 1: System Flow

### Data Flow

```
1. Position closes
   ↓
2. Pattern Scope Aggregator (pattern_scope_aggregator.py)
   - Reads position_closed strand
   - Extracts pm_action strands (by trade_id)
   - Writes to pattern_trade_events (one row per action)
   ↓
3. Lesson Builder (lesson_builder_v5.py) - Runs hourly at :08
   - Reads pattern_trade_events
   - Mines patterns with N >= 33 (recursive Apriori)
   - Calculates edge using 6-D Edge Math
   - Writes to learning_lessons (lesson_type='pm_strength')
   ↓
4. Override Materializer (override_materializer.py) - Runs periodically
   - Reads learning_lessons (pm_strength)
   - Filters: |edge_raw| >= 0.05
   - Maps: multiplier = 1.0 + edge_raw (clamped [0.3, 3.0])
   - Writes to pm_overrides
   ↓
5. Runtime (PM Executor)
   - Calls apply_pattern_strength_overrides()
   - Finds matching overrides (scope_subset contained in current scope)
   - Blends multipliers using weighted average (specificity + confidence)
   - Applies to position_size_frac
```

### Key Components

**Pattern Trade Events** (`pattern_trade_events`):
- One row per action (entry, add, trim, exit)
- Stores: `pattern_key`, `action_category`, `scope`, `rr`, `pnl_usd`, `trade_id`
- Pattern key format: `module=pm|pattern_key=uptrend.S2.trim`

**Lesson Builder** (`lesson_builder_v5.py`):
- Groups by `(pattern_key, action_category)`
- Recursive Apriori mining (finds all valid scope combinations)
- Deduplicates by `trade_id` (multiple actions per trade share same outcome)
- Calculates 6-D Edge Math
- N_MIN_SLICE = 33

**Override Materializer** (`override_materializer.py`):
- Filters lessons: `|edge_raw| >= 0.05`
- Maps edge to multiplier: `multiplier = 1.0 + edge_raw`
- Clamps to [0.3, 3.0]

**Runtime Override Application** (`overrides.py::apply_pattern_strength_overrides()`):
- Finds all matching overrides (scope_subset contained in current scope)
- Blends using weighted average: `weight = confidence * specificity`
- Applies to `position_size_frac`

---

## Part 2: Current Data State

### Pattern Trade Events

**Total Events**: 103  
**Global Baseline RR**: -0.616 (from 103 events)

**Pattern Breakdown**:

| Pattern | Action | n | Unique Trades | Avg RR | Delta RR | Status |
|---------|--------|---|---------------|--------|----------|--------|
| uptrend.S2.trim | trim | 52 | 21 | -0.725 | -0.110 | ✅ Ready (n>=33) |
| uptrend.S2.buy_flag | entry | 18 | 18 | -0.788 | -0.173 | ⚠️  Need 15 more |
| uptrend.S1.entry | entry | 17 | 17 | 0.059 | 0.675 | ⚠️  Need 16 more |
| uptrend.S1.add | add | 9 | 9 | -0.799 | -0.183 | ⚠️  Need 24 more |
| uptrend.S0.exit | exit | 6 | 6 | -0.719 | -0.104 | ⚠️  Need 27 more |
| uptrend.S2.entry | entry | 1 | 1 | -1.000 | -0.384 | ⚠️  Need 32 more |

**Key Observations**:
1. Only S2.trim meets N_MIN threshold
2. Most patterns have negative R/R (but this may be misleading - see R/R vs ROI issue)
3. S1.entry has positive avg_rr (0.059) but high variance (10.863) → low reliability

### Lessons and Overrides

**PM Strength Lessons**: 0  
**PM Strength Overrides**: 0

**Why No Lessons?**
- Lesson Builder is scheduled (hourly at :08)
- Pattern keys are stored correctly
- S2.trim has n=52 (after deduplication: 21 unique trades)
- **Issue**: After deduplication, n=21 < 33, so lesson not created

**Deduplication Impact**:
- S2.trim: 52 events → 21 unique trades
- After deduplication: n=21 < N_MIN=33
- **Result**: No lesson created despite 52 events

---

## Part 3: Edge Calculation (6-D Edge Math)

### Formula

```python
delta_rr = avg_rr - global_baseline_rr

reliability_score = 1.0 / (1.0 + adjusted_variance)
  where adjusted_variance = variance + VAR_PRIOR / max(1, n)
  VAR_PRIOR = 0.25 (variance shrinkage prior)

support_score = 1.0 - exp(-n / 50.0)

magnitude_score = sigmoid(avg_rr / 1.0)

time_score = 1.0

stability_score = 1.0 / (1.0 + variance)

integral = support_score + magnitude_score + time_score + stability_score

edge_raw = delta_rr * reliability_score * integral * decay_multiplier
```

### Example: S2.trim

- n = 52 (21 unique trades after deduplication)
- avg_rr = -0.725
- delta_rr = -0.110
- variance = 0.076
- reliability_score = 0.925
- support_score = 0.65 (approx)
- magnitude_score = 0.33 (approx)
- stability_score = 0.93
- integral = 2.91 (approx)
- edge_raw = -0.110 * 0.925 * 2.91 * 1.0 = **-0.295**
- multiplier = 1.0 + (-0.295) = **0.705** (70.5% sizing)

**Issue**: After deduplication, n=21 < 33, so lesson not created.

---

## Part 4: Analysis - What's Working, What's Not

### ✅ What's Working

1. **Data Collection**: `pattern_trade_events` are being created correctly
2. **Edge Calculation**: 6-D Edge Math is sophisticated and well-designed
3. **Scope Mining**: Recursive Apriori finds all valid scope combinations
4. **Trade Deduplication**: Correctly deduplicates by `trade_id` (maintains statistical independence)
5. **Pattern Key Format**: Stored correctly as `module=pm|pattern_key=uptrend.S2.trim`

### ⚠️  Potential Issues

#### 1. Using R/R Instead of ROI

**Problem**: R/R can be negative for profitable trades (if `exit_price < entry_price` due to trims/re-entries). R/R doesn't directly reflect profitability.

**Example**: A profitable trade with R/R = -0.5 would get `edge_raw = -0.5` → `multiplier = 0.5` (reduces sizing), even though it's profitable.

**Recommendation**: Switch to ROI (`rpnl_pct`) for edge calculation, same as Tuning system.

**Impact**: High - affects all edge calculations and multiplier mappings.

#### 2. Edge Threshold (0.05)

**Current**: Only creates overrides if `|edge_raw| >= 0.05`

**Issue**: With negative R/R values, `edge_raw` is often negative. Negative `edge_raw` → `multiplier < 1.0` → reduces sizing. But is this correct? Or should we use ROI?

**Recommendation**: Re-evaluate threshold after switching to ROI.

#### 3. Multiplier Mapping

**Current**: `multiplier = 1.0 + edge_raw` (linear mapping)

**Example**:
- `edge_raw = -0.5` → `multiplier = 0.5` (50% sizing)
- `edge_raw = +0.5` → `multiplier = 1.5` (150% sizing)

**Question**: Is linear mapping appropriate? Should it be sigmoid or exponential?

**Recommendation**: Keep linear for now, but consider sigmoid if we see extreme multipliers.

#### 4. Blending vs Most Specific

**Current**: Blends all matching overrides using weighted average (specificity + confidence)

**Tuning System**: Uses most specific override only (no blending)

**Inconsistency**: Two different approaches for similar systems.

**Question**: Should PM Strength also use most specific? Or is blending OK here?

**Arguments for Blending**:
- Sizing is less critical than threshold adjustments
- Blending provides smoother transitions
- Multiple lessons can inform sizing

**Arguments for Most Specific**:
- Consistency with Tuning system
- Simulation already found optimal solution (if we had simulation)
- Simpler logic

**Recommendation**: Consider switching to most specific for consistency, but this is lower priority than R/R → ROI.

#### 5. N_MIN = 33

**Current**: Only 1 pattern meets threshold (S2.trim with n=52, but 21 unique trades after deduplication)

**Issue**: After deduplication, n=21 < 33, so no lesson created.

**Question**: Should we:
- Lower N_MIN? (risky - less reliable)
- Wait for more data? (conservative)
- Use different N_MIN for different patterns? (complex)

**Recommendation**: Keep N_MIN=33 for now, but monitor. Consider lowering to 20-25 if we need faster learning.

#### 6. No Lessons Exist

**Problem**: Despite S2.trim having n=52 events, no lessons exist.

**Root Cause**: After deduplication by `trade_id`, n=21 < N_MIN=33, so lesson not created.

**Impact**: System cannot learn from existing data.

**Recommendation**: 
- Option 1: Lower N_MIN to 20-25
- Option 2: Wait for more data
- Option 3: Use different deduplication strategy (but this would break statistical independence)

---

## Part 5: Comparison with Tuning System

| Aspect | Tuning System | PM Strength System |
|--------|---------------|-------------------|
| **Data Source** | `pattern_episode_events` (opportunities) | `pattern_trade_events` (outcomes) |
| **Metric** | Rates (WR, FPR, MR, DR) | Edge (delta_rr * reliability * ...) |
| **Adjustment Method** | Simulation (finds optimal) | Direct mapping (edge → multiplier) |
| **Override Selection** | Most specific wins | Blends all matching |
| **Current Issue** | Using R/R (should use ROI) | Using R/R (should use ROI) |
| **Status** | Not running (TuningMiner not scheduled) | Not creating lessons (N_MIN too high) |

**Key Differences**:
1. **Tuning**: Simulates to find optimal adjustment
   **Strength**: Direct mapping (edge → multiplier)
2. **Tuning**: Most specific override wins
   **Strength**: Blends all matching overrides
3. **Tuning**: Uses rates (WR, FPR, MR, DR)
   **Strength**: Uses edge (delta_rr * reliability * ...)

**Common Issues**:
- Both use R/R instead of ROI
- Both have data/execution issues preventing lessons from being created

---

## Part 6: Recommendations

### High Priority

1. **Switch to ROI for Edge Calculation**
   - Change `pattern_trade_events` to store `roi` (rpnl_pct) instead of (or in addition to) `rr`
   - Update `compute_lesson_stats()` to use ROI
   - Update `materialize_pm_strength_overrides()` to use ROI-based edge
   - **Impact**: Fixes misleading negative R/R for profitable trades

2. **Lower N_MIN or Adjust Deduplication**
   - Option A: Lower N_MIN to 20-25 (allows faster learning)
   - Option B: Keep N_MIN=33 but adjust deduplication (risky - breaks statistical independence)
   - **Impact**: Allows lessons to be created from existing data

### Medium Priority

3. **Consider Most Specific Override (Consistency)**
   - Switch from blending to most specific override
   - Aligns with Tuning system approach
   - **Impact**: Consistency, simpler logic

4. **Re-evaluate Edge Threshold**
   - After switching to ROI, re-evaluate if 0.05 is appropriate
   - **Impact**: Affects how many overrides are created

### Low Priority

5. **Consider Non-Linear Multiplier Mapping**
   - Evaluate if sigmoid or exponential mapping is better
   - **Impact**: Affects how edge translates to sizing

6. **Add Logging**
   - Log when lessons are created/updated
   - Log when overrides are applied
   - **Impact**: Better observability

---

## Part 7: Questions for Discussion

1. **R/R vs ROI**: Should we switch to ROI for PM Strength? (Same issue as Tuning)
2. **N_MIN**: Should we lower N_MIN to 20-25 to allow faster learning?
3. **Blending vs Most Specific**: Should PM Strength use most specific override (like Tuning)?
4. **Multiplier Mapping**: Is linear mapping (`1.0 + edge_raw`) appropriate?
5. **Edge Threshold**: Is 0.05 the right threshold? Should it be different for positive vs negative edge?

---

## Part 8: Next Steps

1. ✅ **Investigation Complete**: Deep dive into PM Strength learning system
2. ⏳ **Decision Needed**: R/R vs ROI, N_MIN, blending vs most specific
3. ⏳ **Implementation**: Apply recommendations after decisions
4. ⏳ **Testing**: Validate changes with existing data
5. ⏳ **Monitoring**: Track lesson creation and override application

---

## Appendix: Code References

- **Pattern Scope Aggregator**: `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py`
- **Lesson Builder**: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py`
- **Override Materializer**: `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py`
- **Runtime Override Application**: `src/intelligence/lowcap_portfolio_manager/pm/overrides.py::apply_pattern_strength_overrides()`
- **Scheduling**: `src/run_social_trading.py` (hourly at :08)

