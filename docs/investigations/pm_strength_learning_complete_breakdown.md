# PM Strength Learning System - Complete Breakdown

**Date**: 2025-01-XX  
**Purpose**: Full documentation of how PM Strength Learning works end-to-end

---

## Overview

PM Strength Learning learns from trade outcomes to adjust position sizing based on pattern performance. The system flows through 4 stages:

1. **Data Capture**: Trade closes → `position_closed` strand → `pattern_trade_events`
2. **Pattern Mining**: Lesson Builder mines `pattern_trade_events` → `learning_lessons`
3. **Override Creation**: Override Materializer converts lessons → `pm_overrides`
4. **Runtime Application**: PM applies overrides to position sizing

---

## Stage 1: Data Capture

### When: Trade Closes

**Trigger**: Position state transitions to `S0` (trade closed)

**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py::_close_trade_on_s0_transition()`

**What Happens**:
1. Calculates final R/R metrics from trade
2. Builds `trade_summary`:
   ```python
   trade_summary = {
       "rr": rr,                    # Risk/Reward ratio
       "pnl_usd": pnl_usd,          # Realized PnL in USD
       "rpnl_pct": rpnl_pct,        # Realized PnL percentage (ROI)
       "entry_price": avg_entry_price,
       "exit_price": avg_exit_price,
       "entry_timestamp": entry_timestamp,
       "exit_timestamp": exit_timestamp,
       # ... other metrics
   }
   ```
3. Emits `position_closed` strand:
   ```python
   position_closed_strand = {
       "kind": "position_closed",
       "module": "pm",
       "content": {
           "trade_id": current_trade_id,
           "entry_context": entry_context,  # Full context at entry
           "trade_summary": trade_summary,   # Final outcomes
           "completed_trades": completed_trades  # All trades for this position
       }
   }
   ```

### Pattern Scope Aggregator

**When**: 
- **Real-time**: Called immediately when `position_closed` strand is emitted
- **Periodic**: Every 5 minutes at :02 (backup for missed real-time processing)

**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py`

**Scheduling**: `src/run_social_trading.py:612`
```python
asyncio.create_task(schedule_5min(2, pattern_scope_aggregator_job))
```

**What It Does** (`process_position_closed_strand()`):

1. **Extracts trade data**:
   ```python
   trade_id = content.get('trade_id')
   trade_summary = content.get('trade_summary')
   rr = float(trade_summary.get('rr', 0.0))
   pnl_usd = float(trade_summary.get('pnl_usd', 0.0))
   ```

2. **Finds linked actions**:
   - Queries `ad_strands` for `pm_action` strands with matching `trade_id`
   - Each action has: `pattern_key`, `action_category`, `scope`

3. **Writes to `pattern_trade_events`** (one row per action):
   ```python
   {
       "pattern_key": "module=pm|pattern_key=uptrend.S1.buy_flag",
       "action_category": "entry",  # or "add", "trim", "exit"
       "scope": {
           "chain": "solana",
           "mcap_bucket": "500k-1m",
           "timeframe": "15m",
           "bucket": "micro",
           # ... full context from entry_context
       },
       "rr": rr,              # Final trade R/R (same for all actions in trade)
       "pnl_usd": pnl_usd,    # Final trade PnL (same for all actions)
       "trade_id": trade_id,   # Links all actions to same trade
       "timestamp": now_iso,
   }
   ```

**Key Point**: Multiple actions per trade (entry, add, trim, exit) all get the same `rr` and `pnl_usd` (final trade outcome). This is important for deduplication later.

**Output**: `pattern_trade_events` table (fact table for mining)

---

## Stage 2: Pattern Mining (Lesson Builder)

### When: Periodic Mining

**Schedule**: Every 1 hour at :08

**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py`

**Scheduling**: `src/run_social_trading.py:613`
```python
asyncio.create_task(schedule_hourly(8, lambda: lesson_builder_job('pm')))
```

### What It Does (`mine_lessons()`)

#### Step 1: Calculate Global Baseline

```python
baseline_res = sb_client.table('pattern_trade_events').select('rr').execute()
all_rrs = [r['rr'] for r in baseline_res.data or []]
global_baseline_rr = sum(all_rrs) / len(all_rrs)
```

**Purpose**: Compare pattern performance against global average

#### Step 2: Load Events

```python
res = sb_client.table('pattern_trade_events')\
    .select('*')\
    .order('timestamp', desc=True)\
    .limit(5000)\
    .execute()
events = res.data or []
```

**Limit**: 5000 events (safety limit)

#### Step 3: Recursive Apriori Mining

**Algorithm**: Recursively finds ALL valid scope combinations

**Process**:

1. **Group by Pattern + Action**:
   ```python
   df['group_key'] = list(zip(df['pattern_key'], df['action_category']))
   grouped = df.groupby('group_key')
   ```
   - Example: `("module=pm|pattern_key=uptrend.S1.buy_flag", "entry")`
   - **Key**: Don't mix different patterns or actions

2. **For each pattern group, recursively mine scope combinations**:
   ```python
   def mine_recursive(slice_df, current_mask, start_dim_idx):
       # Base case: Need at least N_MIN_SLICE trades
       if len(slice_df) < N_MIN_SLICE:  # N_MIN_SLICE = 33
           return
       
       # Deduplicate by trade_id (critical!)
       deduplicated = slice_df.drop_duplicates(subset=['trade_id'], keep='first')
       if len(deduplicated) < N_MIN_SLICE:
           return
       
       # Calculate stats for this scope slice
       stats = compute_lesson_stats(deduplicated, global_baseline_rr)
       
       # Write lesson
       lesson = {
           "module": "pm",
           "pattern_key": pattern_key,
           "action_category": action_category,
           "scope_subset": current_mask,  # e.g., {"timeframe": "15m", "bucket": "micro"}
           "lesson_type": "pm_strength",
           "n": stats['n'],
           "stats": stats,
           "status": "active"
       }
       
       # Recurse: Try adding each scope dimension
       for dim in valid_dims:
           for val in frequent_values:
               new_mask = current_mask.copy()
               new_mask[dim] = val
               mine_recursive(new_slice, new_mask, i + 1)
   ```

**Example Scope Mining**:
- Global: `{}` (all trades)
- By timeframe: `{"timeframe": "15m"}`
- By timeframe + bucket: `{"timeframe": "15m", "bucket": "micro"}`
- By timeframe + bucket + chain: `{"timeframe": "15m", "bucket": "micro", "chain": "solana"}`

**Key Point**: Creates lessons at **multiple specificity levels** (global, timeframe, timeframe+bucket, etc.)

#### Step 4: Calculate Edge (6-D Edge Math)

**Function**: `compute_lesson_stats()`

**Input**: List of events (deduplicated by trade_id), global baseline RR

**Calculations**:

```python
# 1. Basic stats
rrs = [float(e['rr']) for e in events]
n = len(rrs)
avg_rr = sum(rrs) / n
variance = statistics.variance(rrs) if n > 1 else 0.0

# 2. Delta RR (vs global baseline)
delta_rr = avg_rr - global_baseline_rr

# 3. Reliability Score (variance-adjusted)
prior_variance = VAR_PRIOR / max(1, n)  # VAR_PRIOR = 0.25
adjusted_variance = variance + prior_variance
reliability_score = 1.0 / (1.0 + adjusted_variance)

# 4. Support Score (sample size)
support_score = 1.0 - math.exp(-n / 50.0)

# 5. Magnitude Score
magnitude_score = sigmoid(avg_rr / 1.0)

# 6. Time Score (always 1.0 for now)
time_score = 1.0

# 7. Stability Score
stability_score = 1.0 / (1.0 + variance)

# 8. Decay Multiplier (if n >= N_MIN_SLICE)
decay_meta = fit_decay_curve(events)  # Exponential decay analysis
decay_multiplier = decay_meta.get('multiplier', 1.0)

# 9. Edge Raw (final calculation)
integral = support_score + magnitude_score + time_score + stability_score
edge_raw = delta_rr * reliability_score * integral * decay_multiplier
```

**Output Stats**:
```python
{
    "avg_rr": avg_rr,
    "delta_rr": delta_rr,
    "variance": variance,
    "n": n,
    "edge_raw": edge_raw,
    "reliability_score": reliability_score,
    "support_score": support_score,
    "magnitude_score": magnitude_score,
    "time_score": time_score,
    "stability_score": stability_score,
    "decay_meta": decay_meta
}
```

#### Step 5: Write Lessons

**Table**: `learning_lessons`

**Schema**:
```sql
{
    "module": "pm",
    "pattern_key": "module=pm|pattern_key=uptrend.S1.buy_flag",
    "action_category": "entry",
    "scope_subset": {"timeframe": "15m", "bucket": "micro"},
    "lesson_type": "pm_strength",
    "n": 45,
    "stats": {...},  # Full stats dict
    "decay_halflife_hours": 120.5,
    "status": "active",
    "updated_at": "2025-01-XX..."
}
```

**Upsert Key**: `(module, pattern_key, action_category, scope_subset)`

**Output**: `learning_lessons` table (one row per pattern+scope combination)

---

## Stage 3: Override Creation (Override Materializer)

### When: Periodic Materialization

**Schedule**: Every 1 hour at :10

**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py`

**Scheduling**: `src/run_social_trading.py:615`
```python
asyncio.create_task(schedule_hourly(10, override_materializer_job))
```

### What It Does (`materialize_pm_strength_overrides()`)

#### Step 1: Fetch Active Lessons

```python
res = sb_client.table('learning_lessons')\
    .select('*')\
    .eq('module', 'pm')\
    .eq('status', 'active')\
    .eq('lesson_type', 'pm_strength')\
    .execute()
lessons = res.data or []
```

#### Step 2: Filter by Edge Significance

```python
edge_raw = float(stats.get('edge_raw', 0.0))

# Only create override if |edge_raw| >= 0.05
if abs(edge_raw) < EDGE_SIGNIFICANCE_THRESHOLD:  # 0.05
    continue  # Skip this lesson
```

**Purpose**: Only create overrides for patterns with significant edge (positive or negative)

#### Step 3: Map Edge to Multiplier

```python
# Linear mapping: multiplier = 1.0 + edge_raw
multiplier = max(0.3, min(3.0, 1.0 + edge_raw))
```

**Examples**:
- `edge_raw = 0.5` → `multiplier = 1.5` (50% larger sizing)
- `edge_raw = -0.3` → `multiplier = 0.7` (30% smaller sizing)
- `edge_raw = 0.05` → `multiplier = 1.05` (5% larger sizing)
- `edge_raw = -0.05` → `multiplier = 0.95` (5% smaller sizing)

**Caps**: `[0.3, 3.0]` (30% to 300% of base sizing)

#### Step 4: Calculate Confidence

```python
support_score = float(stats.get('support_score', 0.0))
reliability_score = float(stats.get('reliability_score', 0.0))
confidence = support_score * reliability_score
```

**Purpose**: For telemetry/logging only, **not used for filtering or blending**

#### Step 5: Write Override

**Table**: `pm_overrides`

**Schema**:
```sql
{
    "pattern_key": "module=pm|pattern_key=uptrend.S1.buy_flag",
    "action_category": "entry",
    "scope_subset": {"timeframe": "15m", "bucket": "micro"},
    "multiplier": 1.15,
    "confidence_score": 0.85,
    "decay_state": "stable",
    "last_updated_at": "2025-01-XX..."
}
```

**Upsert Key**: `(pattern_key, action_category, scope_subset)`

**Output**: `pm_overrides` table (actionable overrides for runtime)

---

## Stage 4: Runtime Application

### When: Every PM Tick (when planning actions)

**Location**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py::_apply_v5_overrides_to_action()`

**Called From**: `plan_actions_v4()` after action type is determined

### What It Does

#### Step 1: Generate Pattern Key

```python
pattern_key, action_category = generate_canonical_pattern_key(
    module="pm",
    action_type=decision_type,  # "entry", "add", "trim", "exit"
    action_context=action_context,
    uptrend_signals=uptrend
)
```

**Example**: `"module=pm|pattern_key=uptrend.S1.buy_flag"`

#### Step 2: Build Scope

```python
scope = {
    "chain": "solana",
    "timeframe": "15m",
    "bucket": "micro",
    "mcap_bucket": "500k-1m",
    # ... full context
}
```

#### Step 3: Find Matching Overrides

```python
res = (
    sb_client.table('pm_overrides')
    .select('*')
    .eq('pattern_key', pattern_key)
    .eq('action_category', action_category)
    .filter('scope_subset', 'cd', scope_json)  # Contains operator
    .execute()
)
matches = res.data or []
```

**Matching Logic**: `scope_subset` must be **contained in** current `scope`

**Example Matches**:
- Override: `scope_subset = {"timeframe": "15m"}` → ✅ Matches (15m is in scope)
- Override: `scope_subset = {"timeframe": "15m", "bucket": "micro"}` → ✅ Matches (both in scope)
- Override: `scope_subset = {"timeframe": "1h"}` → ❌ Doesn't match (1h not in scope)

**Result**: Can have **multiple matches** (global, timeframe-specific, timeframe+bucket-specific, etc.)

#### Step 4: Blend Multipliers

```python
weighted_mults = []
total_weight = 0.0

for m in matches:
    scope_subset = m.get('scope_subset', {}) or {}
    specificity = (len(scope_subset) + 1.0) ** SPECIFICITY_ALPHA  # SPECIFICITY_ALPHA = 1.5
    confidence = float(m.get('confidence_score', 0.5))
    multiplier = float(m.get('multiplier', 1.0))
    
    weight = confidence * specificity
    weighted_mults.append(multiplier * weight)
    total_weight += weight

final_mult = sum(weighted_mults) / total_weight
final_mult = clamp(final_mult, 0.3, 3.0)
```

**Blending Logic**:
- **Specificity**: More scope dimensions = higher weight
  - Global `{}`: specificity = 1.0^1.5 = 1.0
  - `{"timeframe": "15m"}`: specificity = 2.0^1.5 = 2.83
  - `{"timeframe": "15m", "bucket": "micro"}`: specificity = 3.0^1.5 = 5.20
- **Confidence**: From lesson stats (support × reliability)
- **Weight**: `confidence × specificity`
- **Final**: Weighted average of all matching multipliers

**Example**:
- Global override: `multiplier = 1.1`, `specificity = 1.0`, `confidence = 0.8` → `weight = 0.8`
- 15m override: `multiplier = 1.15`, `specificity = 2.83`, `confidence = 0.9` → `weight = 2.55`
- Final: `(1.1 * 0.8 + 1.15 * 2.55) / (0.8 + 2.55) = 1.14`

#### Step 5: Apply to Sizing

```python
# Only applies to entries/adds, not trims or exits
if decision_type in ["entry", "add"]:
    # Get base sizing (calculated from A/E earlier)
    position_size_frac = 0.10 + (a_final * 0.50)  # Example
    
    # Apply strength multiplier
    action["size_frac"] = action.get("size_frac", 0.0) * final_mult
    
    # Also apply exposure_skew
    final_mult = strength_mult * exposure_skew
    action["size_frac"] = min(1.0, max(0.0, action.get("size_frac", 0.0) * final_mult))
```

**Key Point**: Strength multiplies `size_frac` (position sizing), **NOT** A/E scores

**Result**: Final position size is adjusted based on learned pattern performance

---

## Complete Flow Diagram

```
Trade Closes (S0 transition)
  ↓
position_closed strand emitted
  ↓
Pattern Scope Aggregator (real-time or every 5min)
  ↓
pattern_trade_events (one row per action)
  ↓
Lesson Builder (every 1 hour at :08)
  ↓
  ├─ Calculate global_baseline_rr
  ├─ Recursive Apriori mining (all scope combinations)
  ├─ Deduplicate by trade_id (maintain statistical independence)
  ├─ Calculate edge (6-D Edge Math)
  └─ Write learning_lessons
  ↓
Override Materializer (every 1 hour at :10)
  ↓
  ├─ Fetch active pm_strength lessons
  ├─ Filter: |edge_raw| >= 0.05
  ├─ Map: multiplier = 1.0 + edge_raw (clamped [0.3, 3.0])
  └─ Write pm_overrides
  ↓
Runtime (every PM tick)
  ↓
  ├─ Generate pattern_key from action context
  ├─ Build scope from position context
  ├─ Find matching overrides (scope_subset contained in scope)
  ├─ Blend multipliers (weighted by specificity + confidence)
  └─ Apply to position_size_frac
```

---

## Key Design Decisions

### 1. Why Deduplicate by trade_id?

**Problem**: Multiple actions per trade (entry, add, trim, exit) all share the same final outcome (trade R/R)

**Solution**: Count distinct trades, not actions

**Impact**: Maintains statistical independence (each trade is one observation)

### 2. Why Recursive Apriori Mining?

**Problem**: Need to find patterns at multiple specificity levels (global, timeframe, timeframe+bucket, etc.)

**Solution**: Recursively mine all valid scope combinations

**Impact**: Creates lessons at multiple levels, allowing blending at runtime

### 3. Why Blending Instead of Most Specific?

**Current**: Blends all matching overrides using weighted average

**Rationale**: 
- Sizing is less critical than threshold adjustments (Tuning system)
- Multiple lessons can inform sizing
- Smoother transitions
- More specific overrides have higher weight (but don't completely override)

**Alternative**: Use most specific only (like Tuning system)

### 4. Why Apply to Sizing, Not A/E?

**Current**: `strength_mult → position_size_frac`

**Rationale**:
- A/E calculated early (before pattern is known)
- Pattern determined later (when action is decided)
- Strength applied to sizing (derived from A/E)
- Mathematically equivalent for linear formulas

**Alternative**: Apply to A/E scores directly (would require earlier pattern determination)

---

## Current Limitations

1. **Using R/R instead of ROI**: R/R can be negative for profitable trades
2. **N_MIN = 33**: High threshold, few patterns meet it
3. **No outcome tracking**: Doesn't track trimmed/reached_s3
4. **Single multiplier**: One value for all adjustments (can't adjust A/E independently)

---

## Summary

**PM Strength Learning**:
1. Captures trade outcomes in `pattern_trade_events`
2. Mines patterns using recursive Apriori
3. Calculates edge using 6-D Edge Math
4. Converts edge to multiplier (1.0 + edge_raw)
5. Blends multiple overrides at runtime
6. Applies to position sizing (not A/E scores)

**Key Insight**: Strength affects sizing, which is derived from A/E, achieving the same goal through a different path.

