# Learning Scheduler Options - Detailed Explanation

## Current State

### What's Currently Running (Main Scheduler)

**Hourly Jobs** (in `run_trade.py`):
- **:08** - Lesson Builder (PM) - `_wrap_lesson_builder('pm')`
- **:09** - Lesson Builder (DM) - `_wrap_lesson_builder('dm')`
- **:10** - Override Materializer - `_wrap_override_materializer()`

**What these do**:
- **Lesson Builder**: Mines patterns from `pattern_trade_events` → writes to `learning_lessons`
- **Override Materializer**: Reads `learning_lessons` → filters actionable ones → writes to `pm_overrides`

**These are NOT legacy code** - they're using the correct v5 functions, just scheduled more frequently than v5 recommends.

### What's NOT Running (v5 Scheduler)

**v5 Scheduler** (in `v5_learning_scheduler.py`) - **Fixed but not integrated**:
- Pattern Scope Aggregator: Every 2 hours
- Lesson Builder: Every 6 hours (both PM and DM)
- Override Materializer: Every 2 hours
- **Regime Weight Learner**: Daily at 01:00 UTC ❌ **Missing**
- **Half-Life Estimator**: Weekly Mon 02:00 UTC ❌ **Missing**
- **Latent Factor Clusterer**: Weekly Mon 03:00 UTC ❌ **Missing**

---

## Option A: Replace with v5 Scheduler (Complete Replacement)

### What Gets Replaced

**Remove from main scheduler**:
```python
# Lines 793-795 in run_trade.py - REMOVE THESE
tasks.append(asyncio.create_task(self._schedule_hourly(8, lambda: self._wrap_lesson_builder('pm'), "Lesson PM")))
tasks.append(asyncio.create_task(self._schedule_hourly(9, lambda: self._wrap_lesson_builder('dm'), "Lesson DM")))
tasks.append(asyncio.create_task(self._schedule_hourly(10, self._wrap_override_materializer, "Override Mat")))
```

**Add to main scheduler**:
```python
# Add v5 scheduler integration
from intelligence.lowcap_portfolio_manager.jobs.v5_learning_scheduler import schedule_v5_learning_jobs

# In start_schedulers():
sb_client = self._create_service_client()
tasks.append(asyncio.create_task(schedule_v5_learning_jobs(sb_client)))
```

### What Changes

| Job | Current (Main) | Option A (v5) | Change |
|-----|----------------|---------------|--------|
| Lesson Builder | Hourly (:08, :09) | Every 6 hours | Less frequent |
| Override Materializer | Hourly (:10) | Every 2 hours | Less frequent |
| Pattern Aggregator | Every 5m (separate) | Every 2 hours | Different job |
| Regime Weight Learner | ❌ Not scheduled | Daily 01:00 UTC | **NEW** |
| Half-Life Estimator | ❌ Not scheduled | Weekly Mon 02:00 | **NEW** |
| Latent Factor Clusterer | ❌ Not scheduled | Weekly Mon 03:00 | **NEW** |

### Pros of Option A

1. **Complete v5 System**: All v5 features enabled
2. **Optimal Scheduling**: v5 intervals (6h/2h) are based on data volume analysis
3. **Meta-Learning**: Gets all three meta-learning jobs
4. **Single Source of Truth**: One scheduler for all learning jobs
5. **Future-Proof**: Easy to add new v5 features

### Cons of Option A

1. **Less Frequent Updates**: Lessons update every 6h instead of hourly
   - **Impact**: New patterns take longer to appear in overrides
   - **Mitigation**: Real-time processing still happens (position closures → events)
2. **More Complex**: Adds another scheduler system to manage
3. **Breaking Change**: Removes existing hourly jobs (need to verify nothing depends on them)
4. **Testing Needed**: Need to verify v5 scheduler works correctly in production

---

## Option C: Hybrid (Keep Main + Add Meta-Learning)

### What Gets Added

**Keep existing** (lines 793-795):
- Hourly lesson builder (PM and DM)
- Hourly override materializer

**Add new** (meta-learning jobs only):
```python
# Add meta-learning jobs to main scheduler
from intelligence.lowcap_portfolio_manager.jobs.regime_weight_learner import run_regime_weight_learner
from intelligence.lowcap_portfolio_manager.jobs.half_life_estimator import run_half_life_estimator
from intelligence.lowcap_portfolio_manager.jobs.latent_factor_clusterer import run_latent_factor_clusterer

# In start_schedulers():
# Regime weight learner: Daily at 01:00 UTC
tasks.append(asyncio.create_task(schedule_daily(1, 0, 
    lambda: asyncio.run(run_regime_weight_learner()), "Regime Weight Learner")))

# Half-life estimator: Weekly Monday at 02:00 UTC
tasks.append(asyncio.create_task(schedule_weekly(0, 2, 0,
    lambda: asyncio.run(run_half_life_estimator()), "Half-Life Estimator")))

# Latent factor clusterer: Weekly Monday at 03:00 UTC
tasks.append(asyncio.create_task(schedule_weekly(0, 3, 0,
    lambda: asyncio.run(run_latent_factor_clusterer()), "Latent Factor Clusterer")))
```

### What Changes

| Job | Current | Option C | Change |
|-----|---------|----------|--------|
| Lesson Builder | Hourly | Hourly | **No change** |
| Override Materializer | Hourly | Hourly | **No change** |
| Regime Weight Learner | ❌ Missing | Daily 01:00 UTC | **NEW** |
| Half-Life Estimator | ❌ Missing | Weekly Mon 02:00 | **NEW** |
| Latent Factor Clusterer | ❌ Missing | Weekly Mon 03:00 | **NEW** |

### Pros of Option C

1. **Non-Breaking**: Keeps existing working jobs
2. **More Frequent Updates**: Lessons still update hourly (faster feedback)
3. **Adds Missing Features**: Gets all meta-learning jobs
4. **Lower Risk**: Less change = less chance of breaking things
5. **Easy Rollback**: Can disable meta-learning jobs if issues arise

### Cons of Option C

1. **Not "Pure" v5**: Still using hourly instead of 6h/2h intervals
2. **More Frequent = More Load**: Hourly lesson building uses more CPU/database
3. **Potential Over-Mining**: Mining every hour might create noise if data hasn't changed
4. **Two Systems**: Main scheduler + v5 scheduler both exist (though v5 not used)

---

## Meta-Learning Jobs Explained

### 1. Regime Weight Learner (v5.1)

**What it does**:
- Analyzes which **regime conditions** (BTC macro/meso/micro, alt macro/meso/micro, etc.) make patterns stronger/weaker
- Learns **regime-specific weights** for multipliers like:
  - `time_efficiency` (how time-sensitive is this pattern?)
  - `field_coherence` (how consistent is this pattern across contexts?)
  - `recurrence_score` (how often does this pattern repeat?)
  - `variance` (how stable is the edge?)

**Example**:
```
Pattern: "pm.uptrend.S1.buy_flag" with scope {"chain": "solana", "mcap_bucket": "micro"}

Regime: "btc_macro=S1|alt_macro=S2|bucket_macro=S1"

Learned weights:
- time_efficiency: 1.15 (pattern is 15% more time-sensitive in this regime)
- field_coherence: 0.92 (pattern is 8% less consistent in this regime)
```

**Why it matters**:
- Patterns behave differently in different market regimes
- A pattern that works in bull markets might fail in bear markets
- Regime weights help the system adapt to changing market conditions

**When it runs**: Daily at 01:00 UTC (needs enough data to learn from)

---

### 2. Half-Life Estimator (v5.2)

**What it does**:
- Estimates **decay half-life** for each pattern (how long until edge drops by 50%)
- Fits exponential decay curves to edge history
- Updates `learning_lessons.decay_halflife_hours` field
- Also snapshots edge history to `learning_edge_history` table

**Example**:
```
Pattern: "pm.uptrend.S1.buy_flag" with scope {"chain": "solana"}

Edge history over time:
- Week 1: edge_raw = 0.85
- Week 2: edge_raw = 0.78
- Week 3: edge_raw = 0.72
- Week 4: edge_raw = 0.68

Fitted decay: half_life = 168 hours (7 days)
→ Pattern edge decays by 50% every 7 days
```

**Why it matters**:
- Patterns can "wear out" over time (market adapts, conditions change)
- Half-life tells us when to deprecate old patterns
- Override materializer uses half-life to decay lesson strength over time
- Prevents using stale patterns that no longer work

**When it runs**: Weekly on Monday at 02:00 UTC (needs weeks of data to fit curves)

---

### 3. Latent Factor Clusterer (v5.3)

**What it does**:
- Detects **overlapping patterns** that match the same trades
- Clusters them into **latent factors** (underlying market forces)
- Prevents **double-counting** when multiple patterns match the same trade
- Updates `learning_lessons.latent_factor_id` to group related patterns

**Example**:
```
Pattern A: "pm.uptrend.S1.buy_flag" + {"chain": "solana"}
Pattern B: "pm.uptrend.S1.buy_flag" + {"chain": "solana", "mcap_bucket": "micro"}

Analysis:
- Pattern A matches trades: {T1, T2, T3, T4, T5}
- Pattern B matches trades: {T2, T3, T4}
- Overlap: 3/5 = 60% (high overlap)

Result:
- Both patterns assigned to latent_factor_id: "lf_solana_micro_uptrend_s1"
- Override materializer merges levers from both patterns to avoid double-counting
```

**Why it matters**:
- Multiple patterns can match the same trade (e.g., "solana" pattern + "micro" pattern)
- Without clustering, we'd apply both patterns' overrides = double adjustment
- Latent factors identify the underlying market force (e.g., "Solana micro-cap uptrends")
- Prevents over-adjusting action sizes

**When it runs**: Weekly on Monday at 03:00 UTC (needs enough patterns to cluster)

---

## Recommendation

**I recommend Option C (Hybrid)** because:

1. **Lower Risk**: Keeps working system, adds new features
2. **Faster Feedback**: Hourly lesson updates mean faster learning
3. **Complete Feature Set**: Gets all meta-learning jobs
4. **Easy to Change Later**: Can switch to Option A later if hourly proves unnecessary

**When to Consider Option A**:
- If hourly lesson building causes performance issues
- If you find that hourly updates don't add value (patterns don't change that fast)
- If you want to align with v5 design philosophy (less frequent, more thoughtful)

---

## Implementation Notes

### Option A Implementation
- Remove 3 lines from main scheduler
- Add 1 line to start v5 scheduler
- Test that v5 scheduler works correctly
- Monitor that 6h/2h intervals are sufficient

### Option C Implementation
- Keep existing 3 lines
- Add 3 new meta-learning job schedules
- Test that meta-learning jobs run correctly
- Monitor that they produce useful results

Both options require the same meta-learning job code (already exists and is fixed).

