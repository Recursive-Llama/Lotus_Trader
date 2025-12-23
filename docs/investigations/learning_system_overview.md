# Learning System Overview

## Executive Summary

The learning system is a multi-layered architecture that processes trading outcomes to improve future decisions. It operates in **real-time** (when positions close) and **periodically** (via scheduled jobs). The system is currently **active** but the log file is empty, which suggests either:
1. No positions have closed recently (no learning events to process)
2. Logging may not be properly configured for all components
3. The system is working but logging to a different location

---

## How the Learning System Works

### Architecture Overview

The learning system has **three main layers**:

1. **Event Collection** (Real-time) - When positions close
2. **Pattern Mining** (Periodic) - Discovers patterns from events
3. **Lesson Application** (Real-time) - Applies learned patterns to decisions

### Data Flow

```
Position Closes
    ↓
position_closed strand created (ad_strands table)
    ↓
UniversalLearningSystem.process_strand_event()
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
Periodic Jobs (v5_learning_scheduler.py)
    ↓
┌─────────────────────────────────────────┐
│  PATTERN MINING PIPELINE:               │
├─────────────────────────────────────────┤
│  pattern_trade_events                  │
│    ↓                                    │
│  Lesson Builder (every 6 hours)         │
│    → learning_lessons                   │
│    ↓                                    │
│  Override Materializer (every 2 hours) │
│    → pm_overrides                       │
└─────────────────────────────────────────┘
```

---

## Database Tables

### Core Learning Tables

#### 1. `ad_strands` (Input)
- **Purpose**: Stores all strand types including `position_closed` strands
- **Written by**: PM Core Tick (when positions close)
- **Read by**: UniversalLearningSystem (processes `position_closed` strands)
- **Key fields**: `kind`, `content` (contains `entry_context`, `completed_trades`)

#### 2. `learning_configs` (Coefficient Storage)
- **Purpose**: Stores learned coefficients and module configurations
- **Written by**: 
  - `CoefficientUpdater` (timeframe weights)
  - `UniversalLearningSystem` (global R/R baseline)
- **Structure**:
  ```json
  {
    "module_id": "decision_maker",
    "config_data": {
      "timeframe_weights": {
        "1h": {
          "weight": 1.15,
          "rr_short": 1.08,
          "rr_long": 1.05,
          "n": 42
        }
      },
      "global_rr": {
        "rr_short": 1.05,
        "rr_long": 0.98,
        "n": 150
      }
    }
  }
  ```
- **Updated when**: Every time a position closes (real-time)

#### 3. `pattern_trade_events` (Fact Table)
- **Purpose**: Raw fact table - one row per trade action (entry, add, trim, exit)
- **Written by**: `pattern_scope_aggregator.py` (called from UniversalLearningSystem)
- **Structure**:
  - `pattern_key`: "pm.uptrend.S1.buy_flag"
  - `action_category`: "entry", "add", "trim", "exit"
  - `scope`: Full context JSONB (chain, bucket, timeframe, regime, etc.)
  - `rr`: Realized R/R for this action
  - `pnl_usd`: Realized PnL
  - `trade_id`: Links to parent trade
- **Updated when**: Every time a position closes (real-time)

#### 4. `learning_lessons` (Mined Patterns)
- **Purpose**: Aggregated patterns discovered from `pattern_trade_events`
- **Written by**: `lesson_builder_v5.py` (scheduled job, every 6 hours)
- **Structure**:
  - `module`: "pm" or "dm"
  - `pattern_key`: "pm.uptrend.S1.buy_flag"
  - `action_category`: "entry", "add", "trim", "exit"
  - `scope_subset`: Scope slice (e.g., {"chain": "solana"})
  - `n`: Sample count
  - `stats`: Aggregated stats (avg_rr, edge_raw, decay_meta, etc.)
- **Updated when**: Periodic job runs (every 6 hours)

#### 5. `pm_overrides` (Actionable Rules)
- **Purpose**: Filtered lessons that are actionable (significant edge, acceptable decay)
- **Written by**: `override_materializer.py` (scheduled job, every 2 hours)
- **Read by**: PM Executor (applies overrides to action sizes)
- **Updated when**: Periodic job runs (every 2 hours)

#### 6. `learning_braids` (Pattern Statistics)
- **Purpose**: Raw pattern statistics aggregated across trades
- **Written by**: Braiding system (if enabled)
- **Structure**:
  - `pattern_key`: "big_win|state=S1|A=med|buy_flag=true"
  - `module`: "dm" or "pm"
  - `dimensions`: Pattern dimensions (JSONB)
  - `stats`: Aggregated stats (n, sum_rr, avg_rr, variance, win_rate)
- **Note**: May not be actively used in current v5 system

#### 7. `llm_learning` (LLM Research Outputs)
- **Purpose**: LLM-generated hypotheses, reports, semantic tags
- **Written by**: `LLMResearchLayer` (called from UniversalLearningSystem)
- **Structure**:
  - `kind`: "hypothesis", "report", "semantic_tag", "family_proposal", "semantic_pattern"
  - `level`: 1-5 (which LLM level generated this)
  - `module`: "dm", "pm", or "global"
  - `status`: "hypothesis", "validated", "rejected", "active", "deprecated"
  - `content`: Kind-specific structure (JSONB)
- **Updated when**: Every time a position closes (if LLM layer is enabled)

#### 8. `pattern_scope_stats` (Aggregated Edge Stats)
- **Purpose**: Aggregated edge stats per (pattern_key, action_category, scope_subset)
- **Written by**: Pattern scope aggregator (periodic)
- **Note**: May be superseded by `learning_lessons` in v5

---

## Real-Time Learning Flow

### When a Position Closes

1. **PM Core Tick** creates a `position_closed` strand in `ad_strands`:
   ```python
   # In pm_core_tick.py
   position_closed_strand = {
       'kind': 'position_closed',
       'content': {
           'entry_context': {...},  # Context at entry
           'completed_trades': [{...}]  # Trade outcomes with R/R
       }
   }
   ```

2. **UniversalLearningSystem.process_strand_event()** is called:
   ```python
   # In universal_learning_system.py
   if strand_kind == 'position_closed':
       await self._process_position_closed_strand(strand)
   ```

3. **Three parallel learning paths execute**:

   **Path 1: Coefficient Updates**
   - Updates timeframe weights in `learning_configs`
   - Uses EWMA (Exponentially Weighted Moving Average) with temporal decay
   - Only updates timeframe weights (controls DM allocation split)

   **Path 2: Pattern Scope Aggregation**
   - Calls `process_position_closed_strand()` from `pattern_scope_aggregator.py`
   - Writes one row per action to `pattern_trade_events`
   - Extracts pattern_key, action_category, scope, R/R, PnL

   **Path 3: LLM Research Layer**
   - Calls `LLMResearchLayer.process()` if enabled
   - Generates hypotheses/reports and stores in `llm_learning`

---

## Periodic Learning Jobs

### Scheduled Jobs (v5_learning_scheduler.py)

1. **Pattern Scope Aggregator** (Every 2 hours)
   - Reads `position_closed` strands
   - Writes to `pattern_trade_events`
   - **Note**: This may be redundant since real-time processing already does this

2. **Lesson Builder** (Every 6 hours)
   - Reads `pattern_trade_events`
   - Mines patterns with N ≥ 33 samples
   - Writes aggregated lessons to `learning_lessons`
   - Calculates edge stats, decay metadata, half-lives

3. **Override Materializer** (Every 2 hours)
   - Reads `learning_lessons`
   - Filters for actionable edges (significant edge, acceptable decay)
   - Writes to `pm_overrides`
   - PM Executor reads these at runtime

4. **Regime Weight Learner** (Daily at 01:00 UTC)
   - Learns regime-specific weights
   - Updates regime coefficients

5. **Half-Life Estimator** (Weekly on Monday at 02:00 UTC)
   - Estimates decay half-lives for patterns
   - Updates `learning_lessons.decay_halflife_hours`

6. **Latent Factor Clusterer** (Weekly on Monday at 03:00 UTC)
   - Clusters related lessons into latent factors
   - Updates `learning_lessons.latent_factor_id`

---

## How to Verify the System is Working

### 1. Check for Recent Position Closes

```sql
-- Check if position_closed strands exist
SELECT COUNT(*), MAX(created_at) 
FROM ad_strands 
WHERE kind = 'position_closed';
```

### 2. Check Learning Configs Updates

```sql
-- Check timeframe weights
SELECT 
    module_id,
    config_data->'timeframe_weights' as timeframe_weights,
    config_data->'global_rr' as global_rr,
    updated_at
FROM learning_configs
WHERE module_id = 'decision_maker';
```

### 3. Check Pattern Trade Events

```sql
-- Check if events are being written
SELECT COUNT(*), MAX(created_at)
FROM pattern_trade_events;
```

### 4. Check Learning Lessons

```sql
-- Check if lessons are being mined
SELECT 
    COUNT(*) as total_lessons,
    COUNT(DISTINCT pattern_key) as unique_patterns,
    MAX(updated_at) as last_update
FROM learning_lessons
WHERE status = 'active';
```

### 5. Check PM Overrides

```sql
-- Check if overrides are being materialized
SELECT COUNT(*), MAX(updated_at)
FROM pm_overrides
WHERE status = 'active';
```

### 6. Check Logs

```bash
# Check learning system log (currently empty)
tail -n 100 logs/learning_system.log

# Check PM core log for position_closed strand creation
grep "position_closed" logs/pm_core.log | tail -n 20

# Check for errors
grep -i "error\|exception" logs/learning_system.log
```

### 7. Check Scheduler Status

```bash
# Check if learning jobs are scheduled
grep "learning" logs/schedulers.log | tail -n 20
```

---

## Current Status Assessment

### ✅ What's Working

1. **Code Structure**: All learning components are properly structured
2. **Database Schemas**: All tables exist with correct schemas
3. **Integration**: Learning system is initialized in `run_trade.py`
4. **Real-time Processing**: `process_strand_event()` is called from:
   - Social Ingest (for social_lowcap strands)
   - Decision Maker (for decision_lowcap strands)
   - PM Core Tick (for position_closed strands)

### ⚠️ Potential Issues

1. **Empty Log File**: `logs/learning_system.log` is empty
   - May indicate no positions have closed recently
   - Or logging may not be configured correctly

2. **Scheduler Status**: Need to verify if `v5_learning_scheduler.py` is running
   - Check if it's integrated into main scheduler
   - Check if jobs are actually executing

3. **LLM Research Layer**: May be disabled by default
   - Check `DEFAULT_ENABLEMENT` in `llm_research_layer.py`
   - Only Level 1 and 2 are enabled by default

### 🔍 Investigation Needed

1. **Check if positions are closing**:
   ```sql
   SELECT COUNT(*) FROM ad_strands WHERE kind = 'position_closed';
   ```

2. **Check if learning system is being called**:
   - Add more logging to `process_strand_event()`
   - Check PM Core Tick logs for position_closed strand creation

3. **Check if scheduler is running**:
   - Verify `v5_learning_scheduler.py` is integrated
   - Check if jobs are scheduled in main scheduler

4. **Check database for learning data**:
   - Run all the SQL queries above
   - Verify data is flowing through the pipeline

---

## Recommendations

### Immediate Actions

1. **Add More Logging**:
   - Add INFO logs to `process_strand_event()` entry/exit
   - Add INFO logs to coefficient updates
   - Add INFO logs to pattern scope aggregation

2. **Verify Scheduler Integration**:
   - Check if `v5_learning_scheduler.py` is called from main scheduler
   - If not, integrate it

3. **Check for Position Closes**:
   - Verify positions are actually closing
   - Check PM Core Tick is creating position_closed strands

### Long-term Improvements

1. **Dashboard/Monitoring**:
   - Create a dashboard showing learning system health
   - Show counts of events, lessons, overrides
   - Show last update timestamps

2. **Alerting**:
   - Alert if no events processed in 24 hours
   - Alert if scheduler jobs fail
   - Alert if lesson count drops unexpectedly

3. **Testing**:
   - Add unit tests for learning components
   - Add integration tests for full pipeline
   - Add tests for edge cases (no data, errors, etc.)

---

## Key Files

- **Main Entry Point**: `src/intelligence/universal_learning/universal_learning_system.py`
- **Coefficient Updates**: `src/intelligence/universal_learning/coefficient_updater.py`
- **Pattern Aggregation**: `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py`
- **LLM Research**: `src/intelligence/lowcap_portfolio_manager/pm/llm_research_layer.py`
- **Scheduler**: `src/intelligence/lowcap_portfolio_manager/jobs/v5_learning_scheduler.py`
- **Lesson Builder**: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py`
- **Override Materializer**: `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py`

---

## Summary

The learning system is **architecturally complete** and **integrated** into the trading system. It processes position closes in real-time and runs periodic jobs to mine patterns and create actionable overrides. However, the empty log file suggests either:

1. No positions have closed recently (no learning events)
2. Logging needs to be enhanced
3. The system is working but needs verification

**Next Steps**: Run the verification queries above to confirm the system is processing data correctly.

