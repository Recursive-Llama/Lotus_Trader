# Learning System Deep Dive Investigation

## Critical Findings

### 🚨 BUG #1: Learning System Never Called for Position Closures

**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:2571-2625`

**Problem**: The learning system call is **unreachable dead code**.

**Current Code Structure**:
```python
try:
    # ... create position_closed strand ...
    self.sb.table("ad_strands").insert(position_closed_strand).execute()
    logger.info(f"Position {position_id} closed on S0 transition - emitted position_closed strand")
    return True  # ← EXITS HERE
    
except Exception as e:
    logger.error(f"Error closing trade on S0 transition for position {position_id}: {e}")
    return False  # ← OR EXITS HERE
    if self.learning_system:  # ← UNREACHABLE CODE!
        try:
            asyncio.run(self.learning_system.process_strand_event(position_closed_strand))
            logger.info(f"Learning system processed position_closed strand: {position_id}")
        except Exception as e:
            logger.error(f"Error processing position_closed strand in learning system: {e}")
```

**Impact**: 
- Position closed strands ARE created and inserted into database ✅
- Learning system is NEVER called to process them ❌
- No coefficient updates happen ❌
- No pattern_trade_events are written ❌
- No LLM research layer processing ❌

**Fix Required**: Move learning system call BEFORE the return statement, inside the try block.

---

### 🔍 Finding #2: Episodes vs Position Closures

**What are Episodes?**
- Episodes are **opportunity windows** (S1 entry opportunities, S3 retest opportunities)
- They track whether we **acted** or **skipped** an opportunity
- They are logged to `pattern_episode_events` table
- They create `uptrend_episode_summary` strands (NOT `position_closed` strands)

**Episode Strands**:
- `kind = "uptrend_episode_summary"`
- Created in `_build_episode_summary_strand()` (line 1252)
- Contains episode metadata, outcomes, windows, levers considered
- **NOT processed by learning system** (learning system only processes `position_closed` strands)

**Position Closed Strands**:
- `kind = "position_closed"`
- Created when position fully closes (total_quantity == 0)
- Contains `entry_context` and `completed_trades` with R/R metrics
- **SHOULD be processed by learning system** but currently isn't (due to bug #1)

**Why Episodes Don't Trigger Learning**:
- Episodes are **tuning system** inputs (for S1/S3 gating improvements)
- They're separate from the **learning system** (which learns from completed trades)
- Episodes track "should we have entered?" while learning tracks "how did our trades perform?"

**Conclusion**: Episodes are working as designed - they're for tuning, not learning. The issue is that position closures aren't triggering learning.

---

### 🔍 Finding #3: Scheduler Integration Status

**v5 Learning Scheduler** (`v5_learning_scheduler.py`):
- ✅ Exists and is complete
- ❌ **NOT integrated** into main scheduler
- Has its own scheduling logic (every 2h, 6h, daily, weekly)

**Main Scheduler** (`run_trade.py`):
- ✅ Has learning jobs scheduled (lines 793-795)
- Uses **different functions**:
  - `_wrap_lesson_builder()` → calls `build_lessons_from_pattern_scope_stats()` (NOT `run_lesson_builder()`)
  - `_wrap_override_materializer()` → calls `run_override_materializer()` ✅ (correct)
- Runs hourly (not every 2h/6h as v5 scheduler would)

**Comparison**:

| Job | v5 Scheduler | Main Scheduler | Status |
|-----|--------------|----------------|--------|
| Pattern Scope Aggregator | Every 2h | Every 5m (pattern aggregator) | ✅ Different but working |
| Lesson Builder | Every 6h (`run_lesson_builder`) | Hourly (`build_lessons_from_pattern_scope_stats`) | ⚠️ Different functions |
| Override Materializer | Every 2h | Hourly | ✅ Same function, different schedule |
| Regime Weight Learner | Daily 01:00 UTC | ❌ Not scheduled | ❌ Missing |
| Half-Life Estimator | Weekly Mon 02:00 UTC | ❌ Not scheduled | ❌ Missing |
| Latent Factor Clusterer | Weekly Mon 03:00 UTC | ❌ Not scheduled | ❌ Missing |

**Conclusion**: 
- Main scheduler has **partial integration** (override materializer works)
- Lesson builder uses **different function** (may be legacy vs v5)
- Meta-learning jobs (regime weights, half-life, latent factors) are **completely missing**

---

## Data Flow Analysis

### Current Flow (Broken)

```
Position Closes
    ↓
position_closed strand created ✅
    ↓
Inserted into ad_strands ✅
    ↓
Learning system called? ❌ (BUG - unreachable code)
    ↓
No coefficient updates ❌
No pattern_trade_events ❌
No LLM research ❌
```

### Expected Flow (After Fix)

```
Position Closes
    ↓
position_closed strand created ✅
    ↓
Inserted into ad_strands ✅
    ↓
Learning system.process_strand_event() called ✅
    ↓
┌─────────────────────────────────────────┐
│  THREE PARALLEL LEARNING PATHS:         │
├─────────────────────────────────────────┤
│  1. Coefficient Updates                 │
│     → learning_configs (timeframe weights)│
│                                          │
│  2. Pattern Scope Aggregation           │
│     → pattern_trade_events (fact table) │
│                                          │
│  3. LLM Research Layer                  │
│     → llm_learning (hypotheses/reports) │
└─────────────────────────────────────────┘
    ↓
Periodic Jobs (scheduler)
    ↓
pattern_trade_events → learning_lessons → pm_overrides
```

---

## Verification Queries

### Check Position Closures
```sql
-- Count position_closed strands
SELECT COUNT(*), MAX(created_at) 
FROM ad_strands 
WHERE kind = 'position_closed';

-- Check if they have learning data
SELECT 
    a.id,
    a.created_at,
    a.content->>'trade_id' as trade_id,
    (SELECT COUNT(*) FROM pattern_trade_events WHERE trade_id::text = a.content->>'trade_id') as events_count
FROM ad_strands a
WHERE a.kind = 'position_closed'
ORDER BY a.created_at DESC
LIMIT 10;
```

### Check Episodes
```sql
-- Count episode events
SELECT COUNT(*), MAX(timestamp)
FROM pattern_episode_events;

-- Count episode summary strands
SELECT COUNT(*), MAX(created_at)
FROM ad_strands
WHERE kind = 'uptrend_episode_summary';
```

### Check Learning Data
```sql
-- Check learning configs
SELECT 
    module_id,
    config_data->'timeframe_weights' as timeframe_weights,
    config_data->'global_rr' as global_rr,
    updated_at
FROM learning_configs
WHERE module_id = 'decision_maker';

-- Check pattern trade events
SELECT COUNT(*), MAX(created_at)
FROM pattern_trade_events;

-- Check learning lessons
SELECT 
    COUNT(*) as total,
    COUNT(DISTINCT pattern_key) as unique_patterns,
    MAX(updated_at) as last_update
FROM learning_lessons
WHERE status = 'active';
```

---

## Required Fixes

### Fix #1: Make Learning System Call Reachable (CRITICAL)

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Current** (lines 2571-2625):
```python
try:
    # ... create strand ...
    self.sb.table("ad_strands").insert(position_closed_strand).execute()
    logger.info(f"Position {position_id} closed on S0 transition - emitted position_closed strand")
    return True
    
except Exception as e:
    logger.error(f"Error closing trade on S0 transition for position {position_id}: {e}")
    return False
    if self.learning_system:  # UNREACHABLE
        # ... process strand ...
```

**Fixed**:
```python
try:
    # ... create strand ...
    self.sb.table("ad_strands").insert(position_closed_strand).execute()
    logger.info(f"Position {position_id} closed on S0 transition - emitted position_closed strand")
    
    # Process strand in learning system (async call from sync context)
    if self.learning_system:
        try:
            import asyncio
            asyncio.run(self.learning_system.process_strand_event(position_closed_strand))
            logger.info(f"Learning system processed position_closed strand: {position_id}")
        except Exception as e:
            logger.error(f"Error processing position_closed strand in learning system: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    else:
        logger.warning(f"Learning system not available - position_closed strand not processed: {position_id}")
    
    return True
    
except Exception as e:
    logger.error(f"Error closing trade on S0 transition for position {position_id}: {e}")
    return False
```

### Fix #2: Integrate v5 Learning Scheduler (OPTIONAL but Recommended)

**Option A**: Replace main scheduler jobs with v5 scheduler
- Remove `_wrap_lesson_builder` and `_wrap_override_materializer` from main scheduler
- Add `schedule_v5_learning_jobs()` call in `start_schedulers()`

**Option B**: Keep main scheduler, add missing meta-learning jobs
- Add regime weight learner (daily 01:00 UTC)
- Add half-life estimator (weekly Mon 02:00 UTC)
- Add latent factor clusterer (weekly Mon 03:00 UTC)

**Recommendation**: Fix #1 is critical. Fix #2 can be done later.

---

## Summary

### What's Working ✅
1. Position closed strands ARE created
2. Episodes ARE being logged (for tuning system)
3. Override materializer IS running (hourly)
4. Database schemas are correct

### What's Broken ❌
1. **CRITICAL**: Learning system never called for position closures (dead code)
2. Lesson builder may be using legacy function (needs verification)
3. Meta-learning jobs not scheduled (regime weights, half-life, latent factors)

### What Needs Investigation 🔍
1. Are there any position_closed strands in database? (Check with SQL)
2. Is `build_lessons_from_pattern_scope_stats` the same as `run_lesson_builder`?
3. Are episodes supposed to trigger learning? (Answer: No, they're for tuning)

---

## Next Steps

1. **IMMEDIATE**: Fix the unreachable code bug (Fix #1)
2. **VERIFY**: Run SQL queries to check current state
3. **TEST**: Close a test position and verify learning system is called
4. **OPTIONAL**: Integrate v5 scheduler or add missing meta-learning jobs

