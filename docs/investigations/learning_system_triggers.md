# Learning System Triggers - Complete Flow

## Overview

The learning system is triggered in **two ways**:
1. **Real-time (Event-Driven)**: When a position closes
2. **Periodic (Scheduled Jobs)**: Background jobs that process accumulated data

---

## 1. Real-Time Trigger: Position Closure

### The Complete Flow

```
PM Core Tick (scheduled) 
  ↓
Position State Check
  ↓
Position Closes (S0 transition)
  ↓
Calculate R/R Metrics
  ↓
Emit position_closed Strand
  ↓
Learning System Processes Strand
  ↓
Three Parallel Learning Paths
```

### Step-by-Step

#### Step 1: PM Core Tick Runs (Scheduled)

**When**: 
- **1m timeframe**: Every 1 minute
- **15m timeframe**: Every 15 minutes  
- **1h timeframe**: Every 1 hour (at :06)
- **4h timeframe**: Every 4 hours

**File**: `src/run_social_trading.py` (lines 578-610)

**Code**:
```python
def pm_core_1h_job():
    pm_core_main(timeframe="1h", learning_system=self.learning_system)

asyncio.create_task(schedule_hourly(6, pm_core_1h_job))
```

**What it does**:
- Processes all positions for that timeframe
- Checks state transitions
- Executes actions (add/trim/exit)
- Checks for position closure

---

#### Step 2: Position Closure Detection

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Method**: `run()` → `_check_position_closure()` (line 3072)

**Trigger Condition**:
- Position state transitions to **S0** (after emergency_exit or structural exit)
- Position `total_quantity = 0` (fully closed)

**Code**:
```python
# After all actions executed
self._check_position_closure(p, "", {}, {})
```

---

#### Step 3: Close Trade on S0 Transition

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Method**: `_close_trade_on_s0_transition()` (lines 2282-2623)

**What it does**:
1. **Calculates R/R metrics** from OHLCV data:
   - Entry price, exit price
   - Max drawdown, max gain
   - **RR = return_pct / max_drawdown** (bounded to -33 to 33)
   - Counterfactuals (could_enter_better, could_exit_better)

2. **Builds trade summary**:
   ```python
   trade_summary = {
       "entry_context": entry_context,
       "entry_price": entry_price,
       "exit_price": exit_price,
       "rr": rr,  # Bounded to -33 to 33
       "return": return_pct,
       "max_drawdown": max_drawdown,
       "max_gain": max_gain,
       "decision_type": decision_type,  # "emergency_exit", "trim", etc.
       "time_to_s3": time_to_s3,
       "pattern_key": ...,  # From pm_action strands
       "action_category": ...,  # From pm_action strands
       "scope": ...,  # From pm_action strands
   }
   ```

3. **Updates position**:
   - Sets `status = "watchlist"`
   - Sets `closed_at = exit_timestamp`
   - Appends to `completed_trades` array

4. **Emits position_closed strand**:
   ```python
   position_closed_strand = {
       "kind": "position_closed",
       "module": "pm",
       "position_id": position_id,
       "trade_id": trade_id,
       "content": {
           "entry_context": entry_context,
           "trade_summary": trade_summary,
           "completed_trades": completed_trades,  # Required by learning system
       },
       "target_agent": "learning_system",
   }
   ```

5. **Inserts strand into database**:
   ```python
   self.sb.table("ad_strands").insert(position_closed_strand).execute()
   ```

---

#### Step 4: Learning System Processes Strand

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` (lines 2607-2617)

**Code**:
```python
if self.learning_system:
    try:
        import asyncio
        asyncio.run(self.learning_system.process_strand_event(position_closed_strand))
        logger.info(f"Learning system processed position_closed strand: {position_id}")
    except Exception as e:
        logger.error(f"Error processing position_closed strand in learning system: {e}")
```

**Note**: This is a **synchronous call from async context** (blocking, but acceptable since position closures are rare - 1-2 per day)

---

#### Step 5: Universal Learning System Routes Strand

**File**: `src/intelligence/universal_learning/universal_learning_system.py`

**Method**: `process_strand_event()` (lines 75-130)

**What it does**:
```python
if strand_kind == 'position_closed':
    await self._process_position_closed_strand(strand)
    return strand
```

---

#### Step 6: Three Parallel Learning Paths

**File**: `src/intelligence/universal_learning/universal_learning_system.py`

**Method**: `_process_position_closed_strand()` (lines 210-297)

**Three paths execute in parallel**:

##### Path 1: Coefficient Updates
**What**: Updates timeframe weights and global R/R baseline

**Method**: `_update_coefficients_from_closed_trade()` (lines 299-361)

**Updates**:
1. **Timeframe weight** (EWMA with temporal decay):
   - Stored in `learning_configs.pm.timeframe_weights`
   - Used by Decision Maker for allocation split across timeframes
   - Formula: `weight = rr_short / global_rr_short` (clamped to 0.5-2.0)

2. **Global R/R baseline** (EWMA):
   - Stored in `learning_configs.pm.global_rr`
   - Used for normalizing timeframe weights
   - Two time constants: short (14 days) and long (90 days)

**Code**:
```python
await self._update_coefficients_from_closed_trade(
    entry_context=entry_context,
    completed_trade=completed_trade,
    timeframe=timeframe
)
```

---

##### Path 2: Pattern Scope Aggregation
**What**: Writes raw trade outcomes to `pattern_trade_events` (fact table)

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py`

**Method**: `process_position_closed_strand()` (lines 86-170)

**What it does**:
1. Extracts `completed_trades` from strand
2. Finds linked `pm_action` strands (by `trade_id`)
3. For each action, writes one row to `pattern_trade_events`:
   ```python
   {
       "pattern_key": "pm.uptrend.S1.buy_flag",
       "action_category": "entry",
       "scope": {"chain": "solana", "mcap_bucket": "<500k", ...},
       "rr": rr,  # From trade summary
       "pnl_usd": pnl_usd,
       "trade_id": trade_id,
       "timestamp": now_iso,
   }
   ```

**Code**:
```python
rows_updated = await process_position_closed_strand(
    sb_client=self.supabase_manager.client,
    strand=strand
)
```

**Output**: `pattern_trade_events` table (fact table for mining)

---

##### Path 3: LLM Research Layer
**What**: Generates hypotheses and reports (semantic intelligence)

**File**: `src/intelligence/lowcap_portfolio_manager/pm/llm_research_layer.py`

**Method**: `LLMResearchLayer.process()` (called from line 282)

**What it does**:
- Analyzes trade outcomes
- Generates hypotheses about patterns
- Stores in `llm_learning` table

**Code**:
```python
await self.llm_research_layer.process(
    position_closed_strand=strand,
    token_data=token_data,
    curator_message=curator_message
)
```

**Note**: This is optional (can be disabled)

---

## 2. Periodic Jobs (Background Processing)

### Job 1: Pattern Scope Aggregator

**When**: Every 5 minutes

**File**: `src/run_social_trading.py` (line 612)

**Code**:
```python
asyncio.create_task(schedule_5min(2, pattern_scope_aggregator_job))
```

**What it does**:
- Processes any `position_closed` strands that weren't processed in real-time
- Writes to `pattern_trade_events` table
- **Note**: This is a backup - real-time processing should handle most cases

---

### Job 2: Lesson Builder

**When**: Every 1 hour (at :08)

**File**: `src/run_social_trading.py` (line 613)

**Code**:
```python
asyncio.create_task(schedule_hourly(8, lambda: lesson_builder_job('pm')))
```

**What it does**:
1. **Mines patterns** from `pattern_trade_events`:
   - Scans for slices with N >= 33 (N_MIN_SLICE)
   - Recursively mines ALL valid scope combinations (Apriori algorithm)
   - Computes edge stats (avg_rr, decay, half-life)

2. **Fits decay curves**:
   - Exponential decay toward zero (handles both positive and negative RR)
   - Computes half-life
   - Detects state (decaying/improving/stable)

3. **Writes lessons** to `learning_lessons`:
   ```python
   {
       "pattern_key": "pm.uptrend.S1.buy_flag",
       "action_category": "entry",
       "scope_subset": {"chain": "solana", "mcap_bucket": "<500k"},
       "lesson_type": "pm_strength",
       "stats": {
           "avg_rr": 1.5,
           "delta_rr": 0.3,
           "edge_raw": 0.12,
           "decay_meta": {
               "state": "stable",
               "half_life_hours": 720,  # 30 days
               "multiplier": 1.0
           }
       },
       "decay_halflife_hours": 720,
       "status": "active"
   }
   ```

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py`

**Method**: `mine_lessons()` (lines 237-269)

---

### Job 3: Override Materializer

**When**: Every 1 hour (at :08, after lesson builder)

**File**: `src/run_trade.py` (or `run_social_trading.py`)

**What it does**:
1. Reads active lessons from `learning_lessons`
2. Filters by edge significance: `|edge_raw| >= 0.05`
3. Maps to multipliers:
   - Positive edge → increase sizing (multiplier = 1.0 + edge_raw, clamped to 0.3-3.0)
   - Negative edge → decrease sizing (multiplier = 1.0 + edge_raw, clamped to 0.3-3.0)
4. Writes to `pm_overrides` table

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py`

**Method**: `materialize_pm_strength_overrides()` (lines 39-104)

**Output**: `pm_overrides` table (used by PM runtime for sizing adjustments)

---

## Summary: Complete Trigger Flow

### Real-Time (Event-Driven)
```
Position Closes
  ↓
position_closed Strand Created
  ↓
Learning System.process_strand_event()
  ↓
┌─────────────────────────────────────┐
│ 1. Coefficient Updates              │ → learning_configs (timeframe weights)
│ 2. Pattern Scope Aggregation        │ → pattern_trade_events (fact table)
│ 3. LLM Research Layer               │ → llm_learning (hypotheses)
└─────────────────────────────────────┘
```

### Periodic (Scheduled)
```
Every 5 minutes:
  Pattern Scope Aggregator → pattern_trade_events (backup)

Every 1 hour:
  Lesson Builder → learning_lessons (mined patterns)
  Override Materializer → pm_overrides (actionable rules)
```

---

## Key Points

1. **Learning system is fully integrated**: Position closures trigger learning in real-time
2. **Three learning paths**: Coefficients, pattern mining, LLM research
3. **Periodic jobs**: Process accumulated data (lesson building, override materialization)
4. **Data flow**: 
   - `position_closed` strand → `pattern_trade_events` → `learning_lessons` → `pm_overrides`
5. **Decay is computed**: During lesson building, using exponential decay toward zero (handles both positive and negative RR)

---

## Files Involved

### Real-Time Trigger
- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` - Position closure
- `src/intelligence/universal_learning/universal_learning_system.py` - Learning system entry point
- `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py` - Pattern aggregation
- `src/intelligence/universal_learning/coefficient_updater.py` - Coefficient updates

### Periodic Jobs
- `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py` - Pattern mining
- `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py` - Override creation
- `src/run_social_trading.py` - Job scheduling

---

## Database Tables

1. **`ad_strands`**: `position_closed` strands (input)
2. **`pattern_trade_events`**: Raw trade outcomes (fact table)
3. **`learning_lessons`**: Mined patterns with edge stats
4. **`pm_overrides`**: Actionable rules for PM runtime
5. **`learning_configs`**: Timeframe weights, global R/R baseline
6. **`llm_learning`**: LLM-generated hypotheses (optional)

