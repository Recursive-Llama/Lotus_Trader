# Learning System Update Plan

## Current State Analysis

### What We Have Now

**Decision Maker Learning System**:
- Updates timeframe weights using **R/R** (not ROI)
- Uses EWMA with 14-day decay for timeframe R/R
- Calculates weight: `weight = timeframe_rr_short / global_rr_short`
- Normalizes weights to sum to 1.0
- Applies weights when creating new positions

**Current Flow**:
1. Position closes → `position_closed` strand created
2. `UniversalLearningSystem` processes strand
3. `_update_coefficients_from_closed_trade()` extracts R/R
4. `CoefficientUpdater.update_coefficient_ewma()` updates timeframe R/R (EWMA)
5. Calculates new weight from R/R ratio
6. Stores in `learning_configs.config_data.timeframe_weights`
7. `DecisionMaker` reads weights and normalizes for allocation splits

**Current Issues**:
1. ❌ Uses R/R instead of ROI (R/R can be negative for profitable trades)
2. ❌ No gradual allocation changes (weights jump instantly)
3. ❌ No requirement for minimum 2 timeframes with trades
4. ❌ No per-trade cap on allocation changes
5. ❌ No min_trades discount
6. ❌ 1m timeframe still included (should be removed)

---

## New Requirements

### Starting Allocation
- **15m**: 15%
- **1h**: 50%
- **4h**: 35%
- **1m**: Remove (no longer used)

### Update Rules

1. **Only update when at least 2 timeframes have closed trades**
   - If only 1 timeframe has trades → no change
   - If 2+ timeframes have trades → can adjust between them

2. **Use ROI instead of R/R**
   - Extract `rpnl_pct` from completed trade
   - Track ROI using EWMA (14-day decay)
   - Calculate weights from ROI ratios

3. **Gradual allocation changes**
   - Max change per trade: **0.3%**
   - Capped by min_trades: `change * (min_trades / 5)`
   - Only adjust timeframes that have closed trades

4. **Store current allocation in learning_configs**
   - Track current allocation percentages
   - Update gradually toward desired allocation
   - Preserve allocation for timeframes without trades

---

## New Design

### Data Structure

**In `learning_configs.config_data`**:
```json
{
  "timeframe_allocation": {
    "15m": {
      "current_allocation": 0.15,  // Current allocation (15%)
      "roi_short": -0.0864,         // EWMA ROI (14-day)
      "roi_long": -0.0864,          // EWMA ROI (90-day)
      "n": 14,                      // Number of closed trades
      "updated_at": "2026-01-09T20:02:06Z"
    },
    "1h": {
      "current_allocation": 0.50,
      "roi_short": 0.041,
      "roi_long": 0.041,
      "n": 1,
      "updated_at": "2026-01-06T21:07:03Z"
    },
    "4h": {
      "current_allocation": 0.30,
      "roi_short": null,  // No trades yet
      "roi_long": null,
      "n": 0,
      "updated_at": null
    }
  },
  "global_roi": {
    "roi_short": -0.031,  // EWMA ROI across all timeframes
    "roi_long": -0.031,
    "n": 30,
    "updated_at": "2026-01-09T20:02:07Z"
  }
}
```

### Update Logic

**When a trade closes for timeframe X**:

```python
# 1. Update timeframe X ROI (EWMA)
timeframe_roi = update_roi_ewma(timeframe_x, new_roi_value, trade_timestamp)

# 2. Update global ROI (EWMA)
global_roi = update_global_roi_ewma(new_roi_value, trade_timestamp)

# 3. Get all timeframes that have at least 1 closed trade
timeframes_with_trades = [tf for tf in ['15m', '1h', '4h'] if n[tf] > 0]

# 4. If less than 2 timeframes have trades, no allocation change
if len(timeframes_with_trades) < 2:
    return  # No allocation adjustment

# 5. Calculate desired allocation from ROI ratios
desired_allocation = {}
total_roi = sum(timeframe_roi[tf] for tf in timeframes_with_trades)

for tf in timeframes_with_trades:
    if total_roi != 0:
        desired_allocation[tf] = timeframe_roi[tf] / total_roi
    else:
        desired_allocation[tf] = 1.0 / len(timeframes_with_trades)  # Equal split

# For timeframes without trades, keep current allocation
for tf in ['15m', '1h', '4h']:
    if tf not in timeframes_with_trades:
        desired_allocation[tf] = current_allocation[tf]

# 6. Normalize to sum to 1.0
total = sum(desired_allocation.values())
desired_allocation = {tf: val / total for tf, val in desired_allocation.items()}

# 7. Calculate changes needed
changes = {}
for tf in timeframes_with_trades:
    changes[tf] = desired_allocation[tf] - current_allocation[tf]

# 8. Apply caps
min_trades = min(n[tf] for tf in timeframes_with_trades)
max_change_per_trade = 0.003  # 0.3%
min_trades_discount = min(1.0, min_trades / 5.0)

capped_changes = {}
for tf in timeframes_with_trades:
    raw_change = changes[tf]
    capped_change = max(-max_change_per_trade, min(max_change_per_trade, raw_change))
    discounted_change = capped_change * min_trades_discount
    capped_changes[tf] = discounted_change

# 9. Apply changes (only to timeframes with trades)
new_allocation = {}
for tf in ['15m', '1h', '4h']:
    if tf in timeframes_with_trades:
        new_allocation[tf] = current_allocation[tf] + capped_changes[tf]
    else:
        new_allocation[tf] = current_allocation[tf]  # Unchanged

# 10. Renormalize to sum to 1.0
total = sum(new_allocation.values())
new_allocation = {tf: val / total for tf, val in new_allocation.items()}

# 11. Store new allocation
update_learning_configs(new_allocation)

# 12. Update existing positions' total_allocation_pct
update_existing_positions_allocation(new_allocation)
```

### Update Existing Positions

**When allocation changes, update `total_allocation_pct` for ALL positions (watchlist, active, and dormant)**:

```python
def update_existing_positions_allocation(new_allocation: Dict[str, float]) -> None:
    """
    Update total_allocation_pct for all existing positions based on new allocation splits.
    
    Updates watchlist, active, and dormant positions. For active positions, this doesn't force
    trades - it just updates the number. PM will recalculate usd_alloc_remaining automatically.
    
    For each token:
    1. Get all positions for that token
    2. Sum their total_allocation_pct to get token's total allocation
    3. Redistribute based on new timeframe splits
    4. Update each position's total_allocation_pct
    """
    # Get all watchlist, active, and dormant positions
    positions = sb.table("lowcap_positions").select(
        "id, token_contract, token_chain, timeframe, total_allocation_pct"
    ).in_("status", ["watchlist", "active", "dormant"]).execute()
    
    # Group by token
    by_token = {}
    for pos in positions.data:
        key = (pos["token_contract"], pos["token_chain"])
        by_token.setdefault(key, []).append(pos)
    
    # Redistribute for each token
    for token_positions in by_token.values():
        # Get token's total allocation
        total = sum(float(p.get("total_allocation_pct", 0) or 0) for p in token_positions)
        if total == 0:
            continue
        
        # Update each position
        for pos in token_positions:
            tf = pos.get("timeframe")
            if tf in new_allocation:
                new_pct = total * new_allocation[tf]
                sb.table("lowcap_positions").update({
                    "total_allocation_pct": new_pct
                }).eq("id", pos["id"]).execute()
```

### Example Walkthrough

**Starting**: 15m=15%, 1h=50%, 4h=35%

**Trade 1**: 15m closes, ROI = +5%
- Update: 15m ROI = +5% (EWMA), n=1
- Timeframes with trades: [15m] (only 1)
- **No allocation change** (need at least 2)

**Trade 2**: 1h closes, ROI = -2%
- Update: 1h ROI = -2% (EWMA), n=1
- Timeframes with trades: [15m, 1h] (2 timeframes ✓)
- Desired: 15m=71%, 1h=29% (based on ROI: +5% vs -2%)
- Current: 15m=15%, 1h=50%
- Change needed: 15m +56%, 1h -21%
- Capped: 0.3% max per trade
- Min trades: 1 → discount = 0.2 → actual change = 0.3% * 0.2 = **0.06%**
- New: 15m=15.06%, 1h=49.94%, 4h=30% (normalized)

**Trade 3**: 4h closes, ROI = +3%
- Update: 4h ROI = +3% (EWMA), n=1
- Timeframes with trades: [15m, 1h, 4h] (3 timeframes ✓)
- Desired: 15m=83%, 1h=17%, 4h=50% (based on ROI ratios)
- Current: 15m=15.06%, 1h=49.94%, 4h=30%
- Change needed: 15m +68%, 1h -33%, 4h +20%
- Capped: 0.3% max per trade
- Min trades: 1 → discount = 0.2 → actual change = **0.06%**
- New: 15m=15.12%, 1h=49.88%, 4h=30.00% (normalized)

**After 5 trades each**:
- Min trades: 5 → discount = 1.0 → full **0.3%** changes allowed

---

## Implementation Plan

### Phase 1: Switch to ROI

**Files to modify**:
1. `src/intelligence/universal_learning/universal_learning_system.py`
   - `_update_coefficients_from_closed_trade()`: Extract `rpnl_pct` instead of `rr`
   - Pass ROI to updater instead of R/R

2. `src/intelligence/universal_learning/coefficient_updater.py`
   - `_update_timeframe_weight_ewma()`: Rename to `_update_timeframe_roi_ewma()`
   - Track ROI instead of R/R
   - Store in `timeframe_allocation` instead of `timeframe_weights`

3. `src/intelligence/universal_learning/universal_learning_system.py`
   - `_update_global_rr_baseline_ewma()`: Rename to `_update_global_roi_baseline_ewma()`
   - Track global ROI instead of global R/R

### Phase 2: Add Allocation Tracking

**Files to modify**:
1. `src/intelligence/universal_learning/coefficient_updater.py`
   - Add `_update_timeframe_allocation()` method
   - Store `current_allocation` in config
   - Initialize with starting values: 15m=15%, 1h=50%, 4h=35%

2. `src/intelligence/universal_learning/coefficient_reader.py`
   - `get_timeframe_weights()`: Read `current_allocation` instead of `weight`
   - Return allocation percentages directly

### Phase 3: Implement Gradual Changes

**Files to modify**:
1. `src/intelligence/universal_learning/coefficient_updater.py`
   - Add allocation adjustment logic
   - Check: at least 2 timeframes with trades
   - Calculate desired allocation from ROI ratios
   - Apply 0.3% max change per trade
   - Apply min_trades discount
   - Only adjust timeframes with trades
   - **After updating allocation, call `_update_existing_positions_allocation()`**

2. `src/intelligence/universal_learning/coefficient_updater.py`
   - Add `_update_existing_positions_allocation()` method
   - Update `total_allocation_pct` for ALL positions (watchlist, active, and dormant)
   - Group by token, redistribute based on new splits
   - **Note**: Updating `total_allocation_pct` doesn't force trades - PM will recalculate `usd_alloc_remaining` automatically

### Phase 4: Remove 1m Timeframe

**Files to modify**:
1. `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`
   - Remove 1m from timeframe splits
   - Only use 15m, 1h, 4h

2. `src/intelligence/universal_learning/coefficient_updater.py`
   - Remove 1m from timeframe tracking

---

## Testing Plan

1. **Unit Tests**:
   - Test ROI EWMA calculation
   - Test allocation adjustment logic
   - Test min_trades discount
   - Test normalization

2. **Integration Tests**:
   - Test full flow: trade closes → allocation updates
   - Test with 1, 2, 3 timeframes having trades
   - Test gradual changes over multiple trades

3. **Validation**:
   - Verify allocations sum to 1.0
   - Verify max 0.3% change per trade
   - Verify min_trades discount works
   - Verify timeframes without trades don't change
   - Verify all positions' `total_allocation_pct` are updated (watchlist, active, and dormant)
   - Verify positions maintain correct total allocation per token

---

## Migration Notes

**Existing Data**:
- Current `timeframe_weights` in `learning_configs` will be ignored
- New `timeframe_allocation` structure will be created
- Starting allocation: 15m=15%, 1h=50%, 4h=35%

**Backward Compatibility**:
- Old code reading `timeframe_weights` will get defaults (1.0)
- New code reading `timeframe_allocation` will get actual allocations
- Gradual migration: both structures can coexist during transition

---

---

## PM Tuning System Improvements

### Current Issues

1. **TuningMiner Not Scheduled**: TuningMiner exists but is never run - no lessons are created
2. **Too Basic**: Calculates overall pressure (+3) and applies to ALL thresholds equally
3. **Missing Data**: Doesn't capture threshold values (ts_min, halo_max, slope_min)
4. **No Factor-Specific Tuning**: Can't tell which gate blocked us or which gate was too loose
5. **No Impact Analysis**: Can't predict trade-offs of threshold changes
6. **No Conservative Guardrails**: Doesn't consider dodge rate or success/failure ratios

### Required Data Capture

**What We Need to Capture in Episode Events**:

1. **Threshold Values** (the gates we compared against):
   - `ts_min` - TS threshold at decision time
   - `halo_max` - Halo limit at decision time
   - `slope_min` - Slope requirement at decision time
   - `dx_min` - DX threshold (for S3)

2. **Gate Flags** (preserved in summary, not aggregated):
   - `entry_zone_ok` - All gates passed
   - `ts_ok` - TS gate passed
   - `slope_ok` - Slope gate passed

3. **Which Gate Blocked Us** (if skipped):
   - `blocked_by` - Array of gate names that blocked entry (["ts"], ["slope"], ["halo"], etc.)

4. **Exact Scores for Acted Events**:
   - Keep representative sample (last sample or median) in factors
   - Already captured in samples, but need to preserve in summary

### Schedule TuningMiner

**File**: `src/run_social_trading.py` (or scheduler)

**Change**: Add TuningMiner to scheduler:
```python
# After lesson_builder_job at :08
asyncio.create_task(schedule_hourly(9, lambda: TuningMiner().run()))
```

**Note**: TuningMiner must run AFTER episode events have outcomes (which happens when episodes end).

### Implementation Changes

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

1. **Capture Threshold Values** (`_finalize_active_window()`):
   ```python
   factors = active.get("summary") or {}
   
   # Add threshold values at decision time
   from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import Constants
   factors["ts_min"] = Constants.TS_THRESHOLD
   factors["halo_max"] = Constants.ENTRY_HALO_ATR_MULTIPLIER
   factors["slope_min"] = 0.0
   
   # For S2/S3, add their specific thresholds
   ```

2. **Preserve Gate Flags** (`_summarize_window_samples()`):
   ```python
   # Gate flags should be boolean (not aggregated)
   if samples:
       summary["entry_zone_ok"] = any(s.get("entry_zone_ok") for s in samples)
       summary["ts_ok"] = any(s.get("ts_ok") for s in samples)
       summary["slope_ok"] = any(s.get("slope_ok") for s in samples)
   ```

3. **Capture Which Gate Blocked Us** (`_finalize_active_window()`):
   ```python
   if decision == "skipped":
       # Determine which gate blocked us from last sample
       last_sample = samples[-1] if samples else {}
       factors["blocked_by"] = []
       
       if not last_sample.get("ts_ok"):
           factors["blocked_by"].append("ts")
       if not last_sample.get("slope_ok"):
           factors["blocked_by"].append("slope")
       if not last_sample.get("entry_zone_ok") and last_sample.get("ts_ok") and last_sample.get("slope_ok"):
           factors["blocked_by"].append("halo")
   ```

4. **Preserve Representative Sample for Acted Events**:
   ```python
   if decision == "acted" and samples:
       # Keep last sample as representative
       last_sample = samples[-1]
       factors["ts_score_acted"] = last_sample.get("ts_score")
       factors["halo_distance_acted"] = last_sample.get("halo_distance")
       factors["slope_acted"] = last_sample.get("ema60_slope")
   ```

### Factor-Specific Tuning Logic

**Where This Happens**: `override_materializer.py::materialize_tuning_overrides()`

**Current Flow**:
1. TuningMiner runs → creates lessons with rates (WR, FPR, MR, DR)
2. Override Materializer runs → reads lessons, calculates pressure, creates overrides
3. **This is where we add the simulation logic**

**Minimal Changes**:
- TuningMiner stays the same (just calculates rates)
- Override Materializer gets enhanced with simulation logic
- No changes to episode event logging (except data capture improvements)

**When Simulation Runs**:
- Every time Override Materializer processes a tuning lesson
- For each lesson (pattern + scope combination)
- Uses the episode events that created that lesson

**Implementation Approach**:

**Full Simulation from Start**:
- For each lesson, test all lever adjustments:
  - **Individual levers**: TS, halo, slope (5 values each = 15 simulations)
  - **Pairs**: TS+halo, TS+slope, halo+slope (5×5 each = 75 simulations)
  - **Triples**: TS+halo+slope (5×5×5 = 125 simulations)
  - **Total: 215 simulations per lesson** (computationally manageable)
- **Optimization**: Use `blocked_by` data to narrow search
  - If no misses blocked by TS → skip TS adjustments
  - If no misses blocked by halo → skip halo adjustments
  - Only test combinations involving levers that address blockers
- **Select best option** (highest success/failure ratio ≥ 2.0x) from all simulations
- **Apply the selected adjustment(s)** - could be one lever or a combination

**Why This Works**:
- 215 simulations is computationally fine (runs in seconds)
- Can optimize by using `blocked_by` to skip irrelevant combinations
- Gets the best solution, not just "good enough"
- Not the most complex part of the learning system

**How It Fits Current System**:
- **TuningMiner** (runs periodically): Creates lessons with rates (WR, FPR, MR, DR) - **NO CHANGES**
- **Override Materializer** (runs hourly at :10): Reads lessons, creates overrides - **ADD SIMULATION HERE**
- **Episode Events**: Already being logged - **JUST ADD DATA CAPTURE** (thresholds, gate flags, blocked_by)

**Minimal Changes**:
1. Enhance data capture in `pm_core_tick.py::_finalize_active_window()` (add thresholds, gate flags, blocked_by)
2. Enhance `override_materializer.py::materialize_tuning_overrides()` (add simulation logic)
3. Schedule TuningMiner (currently not scheduled)

**When Simulation Runs**:
- Every time Override Materializer processes a tuning lesson (hourly at :10)
- For each lesson (pattern + scope combination)
- Uses the episode events that created that lesson (fetched from `pattern_episode_events` table)

3. **Impact Analysis - Full Simulation** (Override Materializer Enhancement):
   - **Input**: Lesson with rates (WR, FPR, MR, DR) + episode events that created the lesson
   - **Process**: Test all lever adjustments (individual + combinations):
     - **Individual levers**: TS, halo, slope (5 values each)
       - Example: TS [-0.1, -0.05, 0, +0.05, +0.1]
       - Example: Halo [-0.2, -0.1, 0, +0.1, +0.2]
       - Example: Slope [-0.002, -0.001, 0, +0.001, +0.002]
     - **Pairs**: TS+halo, TS+slope, halo+slope (5×5 each)
     - **Triples**: TS+halo+slope (5×5×5)
     - For each simulation:
       - Calculate: "If we make this adjustment, how many misses would we catch?"
       - Calculate: "How many failures would we add?"
       - Calculate success/failure ratio
     - **Optimization**: Use `blocked_by` data to skip irrelevant combinations
   - **Output**: Best adjustment (individual or combination) with highest ratio ≥ 2.0x
   - **If no adjustment has ratio ≥ 2.0x**: Do nothing (no override created)

5. **Conservative When Evidence is Mixed**:
   - **Success/Failure Ratio Threshold**: Only make changes if successes ≥ 2x failures
     - Example: 6 successes, 2 failures = 3.0x → OK to adjust
     - Example: 4 successes, 3 failures = 1.33x → NO adjustment (too risky)
   - **Dodge Rate Consideration**: If dodge rate is high (e.g., 91.8%) → be very conservative
     - High dodge rate means we're correctly avoiding failures
     - Don't loosen thresholds if it might break this
   - If pressure is small or conflicting → no adjustment
   - Don't force adjustments when evidence is weak

4. **Impact Analysis Process**:
   - Test all combinations (individual levers + pairs + triples)
   - For each simulation:
     - Predict: "If we make this adjustment, how many misses would we catch?"
     - Predict: "How many extra failures would we take?"
     - Calculate success/failure ratio
   - Use `blocked_by` data to optimize (skip irrelevant combinations)
   - Evaluate all options and select the best (highest ratio ≥ 2.0x)
   - **If no option has ratio ≥ 2.0x**: Do nothing (no override created)
   - Only proceed if best option has success/failure ratio ≥ 2.0x

---

## PM Strength Learning System Improvements

### Current State

**Current PM Strength Learning**:
- Uses R/R (not ROI) for edge calculation
- Applies `size_mult` directly to `position_size_frac`
- Does not consider outcome shape (trimmed? reached S3?)
- Single scalar multiplier (no A/E steering)

**Current Flow**:
1. Position closes → `position_closed` strand
2. Pattern Scope Aggregator → `pattern_trade_events` (one row per action)
3. Lesson Builder mines patterns, computes `edge_raw` (from R/R)
4. Override Materializer maps edge to `size_mult` (range [0.3, 3.0])
5. Runtime applies `size_mult` to `position_size_frac`

**Issues**:
1. ❌ Uses R/R instead of ROI (R/R can be negative for profitable trades)
2. ❌ No outcome-based steering (can't express "trim earlier" vs "press harder")
3. ❌ Single scalar doesn't allow A/E posture adjustments
4. ❌ `size_mult` applied after A/E → size conversion (double-counting risk)

---

### New Design: Multi-Outcome A/E Steering

**Core Concept**:
- **ROI** = magnitude signal ("how good was this pattern")
- **Outcomes** (trimmed? reached S3?) = direction signal ("how to improve")
- **Confidence** (support × reliability) = steering strength ("how much to trust this")

**Key Innovation**: Additive deltas with headroom scaling (not multiplication)
- Fits existing linear A/E model: `A = 0.5 + Σ(flag_deltas) + ΔA_learn`
- Headroom scaling prevents clamp waste: `apply_delta_with_headroom(x, delta)`
- Dynamic steering strength: `STEER_MAX_eff = STEER_BASE + STEER_GAIN * confidence`

---

### Data Capture Requirements

**Add to `pattern_trade_events`** (computed in Pattern Scope Aggregator):

```json
{
  "roi": rpnl_pct,           // Primary magnitude metric (replaces R/R)
  "did_trim": true,          // Was there at least one trim in this trade?
  "reached_s3": false,       // Did the trade reach S3 before closing?
  ...
}
```

**Where to compute**: Pattern Scope Aggregator already has:
- Full `completed_trades` list
- All linked `pm_action` strands
- Can compute `did_trim` and `reached_s3` per trade once, then copy to all action rows

**Still deduplicate by `trade_id`** in mining (same independence rule as today).

---

### Outcome Classification

**Four Scenarios** (map each trade to direction vector):

1. **ROI < 0, no trim**: `(dA=-1, dE=0)`
   - Lost money, didn't trim → reduce A (less aggressive)
   - No evidence about E (didn't trim)

2. **ROI < 0, trimmed**: `(dA=-1, dE=+1)`
   - Lost money, but trimmed → reduce A, increase E (trim earlier next time)

3. **ROI > 0, no S3**: `(dA=0, dE=0)`
   - Won, but didn't reach S3 → neutral (no posture change)
   - Base sizing can still increase, but no evidence posture change helps

4. **ROI > 0, reached S3**: `(dA=+1, dE=-1)`
   - Won and reached S3 → increase A, decrease E (press winners harder, trim less)

**Weight each trade by ROI magnitude**:
- `w = tanh(abs(roi) / roi_scale)` (saturating weight)
- Prevents one huge outlier from dominating

---

### Mining Changes (Lesson Builder)

**After deduplication by `trade_id`**, for each mined slice:

1. **Compute base edge from ROI**:
   - `edge_raw_roi` (signed; magnitude answers "bigger/smaller")
   - Replace current R/R-based `edge_raw`

2. **Compute outcome directions**:
   - `dirA = weighted_mean(dA, w)` (weighted by ROI magnitude)
   - `dirE = weighted_mean(dE, w)`
   - Both land in `[-1, +1]`
   - Mixed outcomes → naturally near 0 (conservative)

3. **Compute confidence**:
   - `support_score = 1 - exp(-n / 50)` (grows with n, saturates)
   - `reliability_score = 1 / (1 + adjusted_variance)` (penalizes noise)
   - `confidence = support_score * reliability_score`
   - Already computed in 6-D edge calculation

4. **Store in `learning_lessons.stats`**:
   ```json
   {
     "edge_raw_roi": 0.12,
     "dirA": 0.62,
     "dirE": -0.38,
     "confidence": 0.75,
     "p_trim": 0.67,
     "p_s3": 0.33,
     ...
   }
   ```

---

### Materialization Changes (Override Materializer)

**Store in `pm_overrides`** (not deltas - computed at runtime):

```json
{
  "pattern_key": "pm.uptrend.S1.entry",
  "action_category": "pm_strength",
  "scope_subset": {"timeframe": "15m"},
  "dirA": 0.62,
  "dirE": -0.38,
  "confidence_score": 0.75,
  "edge_raw_roi": 0.12,
  "multiplier": null,  // No longer used (replaced by dirA/dirE)
  ...
}
```

**Key Change**: Store `dirA`, `dirE`, `confidence_score` (not computed deltas)
- Deltas computed at runtime using blended confidence
- Allows dynamic `STEER_MAX_eff` based on blended confidence

---

### Runtime Application (PM Overrides)

**Location**: `src/intelligence/lowcap_portfolio_manager/pm/overrides.py::apply_pattern_strength_overrides()`

**Flow**:

1. **Fetch matching overrides** (same as today, by pattern + scope)

2. **Filter low-confidence overrides** (conditional):
   - If any matches have `confidence >= CONF_MIN` (0.40), ignore matches below CONF_MIN
   - If all matches are below CONF_MIN, keep them (better than no signal)
   - Prevents noise from polluting when good signals exist

3. **Blend dirA, dirE, confidence** (weighted by specificity × confidence):
   ```
   w_i = specificity_i * confidence_i
   dirA_final = Σ(w_i * dirA_i) / Σ(w_i)
   dirE_final = Σ(w_i * dirE_i) / Σ(w_i)
   conf_blended = Σ(w_i * confidence_i) / Σ(w_i)
   ```

4. **Compute dynamic steering strength**:
   ```
   STEER_MAX_eff = STEER_BASE + STEER_GAIN * conf_blended
   STEER_MAX_eff = min(STEER_MAX_eff, STEER_MAX_HARD)  // Optional cap
   ```

5. **Convert directions to deltas**:
   ```
   ΔA = STEER_MAX_eff * dirA_final
   ΔE = STEER_MAX_eff * dirE_final
   ```
   (Optionally add small base bias: `ΔA += BASE_BIAS * edge_raw_roi`)

6. **Apply with headroom scaling**:
   ```python
   def apply_delta_with_headroom(x, delta):
       if delta >= 0:
           return x + delta * (1 - x)   # Scales by remaining upward headroom
       else:
           return x + delta * x         # Scales by remaining downward headroom
   
   A_final = apply_delta_with_headroom(A_flags, ΔA)
   E_final = apply_delta_with_headroom(E_flags, ΔE)
   A_final = clamp(A_final, 0.0, 1.0)
   E_final = clamp(E_final, 0.0, 1.0)
   ```

7. **Derive sizing from A_final** (existing formula):
   ```python
   position_size_frac = 0.10 + (A_final * 0.50)
   ```

8. **No `size_mult`** (removed - posture now drives everything)

---

### Constants and Configuration

**Suggested Defaults**:

```python
# Steering strength
STEER_BASE = 0.03          # Always has voice (even at conf=0)
STEER_GAIN = 0.20          # Can grow to 0.23 total
STEER_MAX_HARD = 0.22      # Optional absolute safety cap

# Confidence filtering
CONF_MIN = 0.40            # For conditional filtering

# ROI weighting
ROI_SCALE = 0.10           # For tanh(abs(roi) / roi_scale)

# Optional base bias
BASE_BIAS = 0.01           # Small nudge from ROI edge (optional)
```

**Behavior Examples**:
- `conf=0.2` → `STEER_MAX_eff = 0.07` (weak, safe)
- `conf=0.6` → `STEER_MAX_eff = 0.15` (matches flags)
- `conf=0.9` → `STEER_MAX_eff = 0.21` (capped at 0.22)

**Why This Works**:
- Learning can match/exceed flags (0.15-0.20) when confident
- Starts weak when evidence is weak (safe)
- Headroom scaling prevents clamp waste
- Blending stays smooth and interpretable

---

### Implementation Plan

**Phase 1: Data Capture**
1. Add `did_trim`, `reached_s3` to Pattern Scope Aggregator
2. Compute per trade, copy to all `pattern_trade_events` rows
3. Switch from R/R to ROI in mining

**Phase 2: Mining Updates**
1. Compute `dirA`, `dirE` per slice (weighted averages)
2. Use existing `confidence = support × reliability`
3. Store in `learning_lessons.stats`

**Phase 3: Materialization Updates**
1. Store `dirA`, `dirE`, `confidence_score` in `pm_overrides`
2. Remove `size_mult` from materialization

**Phase 4: Runtime Updates**
1. Update `apply_pattern_strength_overrides()` to:
   - Filter low-confidence overrides (conditional)
   - Blend dirA/dirE/confidence
   - Compute `STEER_MAX_eff` from blended confidence
   - Convert to deltas
   - Apply with headroom scaling
2. Remove `size_mult` application
3. Ensure A/E adjustments affect downstream sizing/thresholds

**Phase 5: Testing**
1. Unit tests for headroom scaling
2. Unit tests for blending logic
3. Integration tests for full flow
4. Validate A/E adjustments affect behavior correctly

---

### Benefits of This Approach

1. **Outcomes drive direction**: Can express "trim earlier" vs "press harder"
2. **ROI drives magnitude**: Direct profitability signal (no R/R weirdness)
3. **Confidence-scaled steering**: Powerful when earned, weak when noisy
4. **Headroom scaling**: No clamp waste, preserves effect near boundaries
5. **Clean blending**: Self-consistent (same weights for direction and strength)
6. **Interpretable**: Can log "dirA=+0.62, conf=0.75 → ΔA=+0.12"
7. **Fits existing system**: Additive deltas match linear A/E model

---

## Next Steps

1. Review and approve this plan
2. Implement Phase 1 (ROI switch for Decision Maker)
3. Test Phase 1
4. Implement Phase 2 (Allocation tracking)
5. Test Phase 2
6. Implement Phase 3 (Gradual changes)
7. Test Phase 3
8. Implement Phase 4 (Remove 1m)
9. **Implement PM Tuning data capture improvements**
10. **Implement PM Strength multi-outcome learning** (see section below)
11. **Add comprehensive logging for learning system**
12. **Enable A/E v2 computation** (see section below)
13. Full integration testing
14. Deploy

---

## A/E v2 Enablement

### Current State
- **A/E v2 is NOT enabled** - system defaults to legacy `compute_levers()` method
- Code checks: `pm_cfg.get("feature_flags", {}).get("ae_v2_enabled", False)`
- Default is `False` when flag is missing
- No PM config entry in `learning_configs` table
- No `feature_flags` key in `pm_config.jsonc` file

### What Needs to Happen
Enable A/E v2 by adding `feature_flags.ae_v2_enabled = True` to PM config in database.

**SQL to enable**:
```sql
INSERT INTO learning_configs (module_id, config_data, updated_by) 
VALUES ('pm', '{"feature_flags": {"ae_v2_enabled": true}}', 'manual')
ON CONFLICT (module_id) DO UPDATE 
SET config_data = jsonb_set(
    COALESCE(config_data, '{}'::jsonb), 
    '{feature_flags,ae_v2_enabled}', 
    'true'
);
```

**Or if PM config already exists**:
```sql
UPDATE learning_configs 
SET config_data = jsonb_set(
    COALESCE(config_data, '{}'::jsonb),
    '{feature_flags}',
    COALESCE(config_data->'feature_flags', '{}'::jsonb) || '{"ae_v2_enabled": true}'::jsonb
)
WHERE module_id = 'pm';
```

### Verification
- Check logs for `"AE_V2: ..."` messages (v2 logs this, legacy doesn't)
- Verify A/E computation uses flag-driven method instead of regime-driven

### Impact
- Switches from complex regime-driven A/E (5 drivers × 3 timeframes) to simpler flag-driven method
- Both produce A/E in [0.0, 1.0] range, so PM Strength application works the same
- v2 is simpler and designed to work better with PM Strength learning

---

## Learning System Logging Plan

**New Log File**: `logs/learning_system.log`

### What to Log

#### 1. TuningMiner Execution
- **Start/Completion**: When TuningMiner runs, how many events processed, how many lessons created
- **Lesson Creation**: Each lesson created (pattern_key, scope_subset, n, rates)
- **Scope Slicing**: Which scope slices passed N_MIN threshold
- **Errors**: Failures in mining or lesson creation

**Example entries**:
```
2025-01-15 10:09:00,123 - learning_system - INFO - TuningMiner starting | events=104 | lookback_days=90
2025-01-15 10:09:02,456 - learning_system - INFO - TuningMiner: Created lesson | pattern=pm.uptrend.S1.entry | scope={} | n=104 | wr=0.286 fpr=0.714 mr=0.082 dr=0.918
2025-01-15 10:09:02,789 - learning_system - INFO - TuningMiner: Scope slice passed | pattern=pm.uptrend.S1.entry | scope={timeframe: 15m} | n=57
2025-01-15 10:09:03,012 - learning_system - INFO - TuningMiner completed | lessons_created=3 | duration=2.9s
```

#### 2. Override Materializer Execution
- **Start/Completion**: When Override Materializer runs, how many lessons processed
- **Simulation Results**: For each lesson, best adjustment found (lever, ratio, misses_caught, failures_added)
- **Override Creation**: Each override created (pattern_key, action_category, multiplier, scope)
- **No Override Reasons**: Why no override was created (ratio < 2.0x, no good solution, etc.)
- **Simulation Stats**: How many simulations run, how many skipped (optimization)

**Example entries**:
```
2025-01-15 10:10:00,123 - learning_system - INFO - Override Materializer starting | lessons=3
2025-01-15 10:10:01,456 - learning_system - INFO - SIMULATION: pattern=pm.uptrend.S1.entry scope={} | tested=215 skipped=150 | best=halo+0.1 ratio=5.0x (5 misses_caught, 1 failure_added)
2025-01-15 10:10:01,789 - learning_system - INFO - OVERRIDE CREATED: pattern=pm.uptrend.S1.entry | action=tuning_halo | multiplier=1.1 | scope={} | ratio=5.0x
2025-01-15 10:10:02,012 - learning_system - INFO - Override Materializer completed | overrides_created=1 | duration=1.9s
```

#### 3. Episode Event Logging
- **Event Logged**: When episode event is logged (pattern_key, decision, episode_id)
- **Outcome Updated**: When episode outcome is updated (episode_id, outcome, n_windows_updated)
- **Missing Data Warnings**: When required data is missing (thresholds, gate flags, etc.)

**Example entries**:
```
2025-01-15 10:30:31,234 - learning_system - INFO - EPISODE EVENT: pattern=pm.uptrend.S1.entry | decision=skipped | episode_id=s1_ep_abc123 | blocked_by=[ts]
2025-01-15 10:30:45,567 - learning_system - INFO - EPISODE OUTCOME: episode_id=s1_ep_abc123 | outcome=success | windows_updated=3
2025-01-15 10:30:31,890 - learning_system - WARNING - EPISODE EVENT: Missing threshold data | episode_id=s1_ep_abc123 | missing=[ts_min, halo_max]
```

#### 4. Decision Maker Learning (Timeframe Allocation)
- **Allocation Update**: When allocation changes (old allocation, new allocation, trigger trade)
- **ROI Updates**: When timeframe ROI is updated (timeframe, new_roi, n_trades)
- **No Change Reasons**: Why allocation didn't change (need 2+ timeframes, etc.)

**Example entries**:
```
2025-01-15 10:30:31,234 - learning_system - INFO - ALLOCATION UPDATE: trigger=15m trade closed | old={15m: 0.15, 1h: 0.50, 4h: 0.35} | new={15m: 0.1503, 1h: 0.4997, 4h: 0.35} | change=0.03%
2025-01-15 10:30:31,456 - learning_system - INFO - ROI UPDATE: timeframe=15m | roi_short=-0.0864 | n=14 | trade_roi=-0.022
2025-01-15 10:30:31,678 - learning_system - INFO - ALLOCATION SKIP: Only 1 timeframe has trades (need 2+) | timeframes_with_trades=[15m]
```

#### 5. PM Strength Learning
- **Strength Override Creation**: When PM strength override is created (pattern, multiplier, edge)
- **No Override Reasons**: Why no strength override (edge < threshold, etc.)

**Example entries**:
```
2025-01-15 10:10:02,234 - learning_system - INFO - STRENGTH OVERRIDE: pattern=pm.uptrend.S1.entry | multiplier=1.15 | edge_raw=0.12 | scope={chain: solana}
```

### Log File Configuration

**Add to `src/run_trade.py` loggers dictionary**:
```python
loggers = {
    # ... existing loggers ...
    'learning_system': 'logs/learning_system.log',
}
```

**Use in learning system code**:
```python
import logging
logger = logging.getLogger('learning_system')
logger.info("TuningMiner starting | events=%d | lookback_days=%d", n_events, lookback_days)
```

### Log Levels

- **INFO**: Normal operations (miner runs, overrides created, allocations updated)
- **WARNING**: Missing data, skipped operations, no good solutions found
- **ERROR**: Failures in mining, materialization, or allocation updates

### When to Check Learning System Logs

- **TuningMiner not creating lessons**: Check for errors or insufficient data
- **No overrides created**: Check simulation results and ratio calculations
- **Allocation not updating**: Check ROI updates and timeframe trade counts
- **Missing episode events**: Check event logging and outcome updates

---

## Override Selection Behavior

### How Overrides Are Applied

**With Simulation-Based Tuning**: Use **most specific override only** (per category), don't blend.

**Why**: Simulation already found the optimal adjustment for that scope. Blending would undo the optimization.

**Example**:
- S1 global override: `pattern=pm.uptrend.S1.entry`, `scope={}`, `tuning_halo` multiplier=1.1
- S1 15m override: `pattern=pm.uptrend.S1.entry`, `scope={timeframe: 15m}`, `tuning_halo` multiplier=1.05
- S1 15m micro override: `pattern=pm.uptrend.S1.entry`, `scope={timeframe: 15m, bucket: micro}`, `tuning_halo` multiplier=1.3

**When processing** `scope={timeframe: 15m, bucket: micro}`:
- All 3 overrides match (their scope_subset is a subset of current scope)
- System groups by `action_category` (e.g., `tuning_ts_min`, `tuning_halo`)
- For each category, selects **most specific override** (most scope dims):
  - `tuning_halo`: Uses S1 15m micro (2 dims) → multiplier=1.3
  - Ignores S1 15m (1 dim) and global (0 dims)
- Applies that exact multiplier (no blending)

**Result**: Most specific override wins completely. Simulation's optimization is preserved.

### Implementation Change Needed

**File**: `src/intelligence/lowcap_portfolio_manager/pm/overrides.py::apply_pattern_execution_overrides()`

**Current**: Blends all matching overrides using weighted average
**New**: Select most specific override per category, use exact multiplier

**Code Change**:
```python
# Group by category
by_cat: Dict[str, List[Dict]] = {}
for m in matches:
    cat = m['action_category']
    by_cat.setdefault(cat, []).append(m)

# For each category, select most specific (don't blend)
for cat, cat_matches in by_cat.items():
    # Sort by specificity (most scope dims = most specific)
    cat_matches.sort(key=lambda x: len(x.get('scope_subset', {})), reverse=True)
    most_specific = cat_matches[0]  # Most specific override
    
    multiplier = float(most_specific.get('multiplier', 1.0))
    # Apply exact multiplier (no blending)
    current_val = adjusted.get(target_key, 1.0)
    adjusted[target_key] = current_val * multiplier
```

### Implications for Tuning System

1. **Most specific wins completely**: If S1 15m micro has an override, it's used (not blended with global)
2. **Simulation optimization preserved**: The exact adjustment found by simulation is applied
3. **Fallback behavior**: If no exact match, use most specific match available
4. **This is correct**: Simulation already optimized - don't undo it by blending

### No Override Behavior

**If simulation finds no good solution** (best ratio < 2.0x):
- **No override created** → System uses base thresholds (Constants)
- **This is correct**: Don't make changes if evidence doesn't support it
- **Logging**: Should log why no override was created (ratio too low, etc.)

