# Episode-Based Learning Tuning System - Deep Dive

## Overview

The episode-based learning tuning system evaluates trading opportunities (episodes) by tracking:
1. **What we decided** (Acted vs Skipped)
2. **What happened** (Success vs Failure)
3. **Why we decided** (Signal values at decision time)

This creates a feedback loop that tunes entry gates (TS thresholds, halo distances, DX thresholds) based on actual outcomes.

---

## Core Philosophy: The 4 Quadrants

Every episode is evaluated as a binary experiment with 4 possible outcomes:

| Decision | Outcome | Interpretation | Tuning Action |
|----------|---------|-----------------|---------------|
| **Acted** | **Success** | "Good call" | **Reinforce**: Keep gates as-is or slightly loosen |
| **Acted** | **Failure** | "False positive" | **Tighten**: Raise thresholds, lower halo |
| **Skipped** | **Success** | "Missed opportunity" | **Loosen**: Lower thresholds, widen halo |
| **Skipped** | **Failure** | "Good dodge" | **Reinforce**: Keep gates tight or tighten further |

---

## Episode Types

### S1 Entry Episodes

**Purpose**: Learn when to enter positions during the primer phase (S1 state).

**Lifecycle**:
- **Start**: State transition `S0 → S1`
- **End**: 
  - **Success**: Reaches `S3` (via `S1 → S2 → S3`)
  - **Failure**: Returns to `S0` without reaching S3
- **Outcome Classification**:
  - `success`: Entered AND reached S3
  - `failure`: Entered BUT returned to S0 before S3
  - `missed`: Did NOT enter BUT episode reached S3 anyway
  - `correct_skip`: Did NOT enter AND episode collapsed to S0

**Windows Within Episode**:
- An S1 episode contains one or more **buy windows**
- A window opens when `entry_zone_ok = True` (TS/halo/slope gates satisfied)
- Window closes when `entry_zone_ok = False` or episode ends
- Each window captures samples (signal values) while active

**Signals Captured** (per sample):
- `ts_score`: Trend Strength score
- `ts_with_boost`: TS + SR boost
- `sr_boost`: Social/Regime boost
- `ema60_slope`, `ema144_slope`: EMA slope values
- `halo_distance`: Distance from EMA60 in ATR units
- `entry_zone_ok`, `slope_ok`, `ts_ok`: Gate pass/fail flags
- `a_value`: Aggressiveness score at decision time
- `position_size_frac`: Position sizing fraction

**Levers Tuned**:
- `ts_min`: Trend Strength threshold
- `sr_boost_max`: SR boost ceiling
- `ema60_slope_min`, `ema144_slope_min`: Slope guard thresholds
- `halo_multiplier`: Halo distance multiplier

---

### S3 Retest Episodes (S3DX)

**Purpose**: Learn when to add to positions during S3 retests (dip buys).

**Lifecycle**:
- **Start**: State transition to `S3` (from S2)
- **End**: State transition `S3 → S0` (trend broken)
- **Outcome Classification**:
  - `success`: Entered AND a trim occurred before S0
  - `failure`: Entered BUT trend broke (S0) before any trim
  - `missed`: Did NOT enter BUT a trim occurred anyway
  - `correct_skip`: Did NOT enter AND trend broke to S0

**Windows Within Episode**:
- An S3 episode contains **multiple retest windows**
- A window opens when price dips into the band (`price < ema144`)
- Window closes when price moves above EMA144 or episode ends
- Each window is a potential retest opportunity

**Signals Captured** (per sample):
- `ts_score`: Trend Strength (anchored to EMA333)
- `dx_score`: Dip buy signal strength
- `edx_score`: Extended dip signal (suppression factor)
- `price_pos`: Normalized position in EMA144-EMA333 band (0.0 = EMA144, 1.0 = EMA333)
- `ema250_slope`, `ema333_slope`: Slow-band slope values
- `a_value`: Aggressiveness score
- `position_size_frac`: Position sizing fraction

**Levers Tuned**:
- `dx_min`: DX threshold for retest buys
- `edx_supp_mult`: EDX suppression multiplier
- `ts_min`: TS threshold (same as S1 but anchored differently)
- `ema250_slope_min`, `ema333_slope_min`: Slow-band slope guards
- `price_band_bias`: Price position weighting (future)

---

## Data Flow: Episode Lifecycle

### Phase 1: Episode Creation & Window Tracking

**Location**: `pm_core_tick.py::_process_episode_logging()`

1. **State Transition Detection**:
   ```python
   # S1 Episode starts
   if state == "S1" and prev_state == "S0":
       episode_id = generate_episode_id("s1")
       meta["s1_episode"] = {
           "episode_id": episode_id,
           "started_at": now,
           "entered": False,
           "windows": [],
           "active_window": None
       }
   
   # S3 Episode starts
   elif state == "S3" and prev_state != "S3":
       episode_id = generate_episode_id("s3")
       meta["s3_episode"] = {
           "episode_id": episode_id,
           "started_at": now,
           "windows": [],
           "retest_index": 0,
           "entered": False,
           "active_window": None
       }
   ```

2. **Window Opening** (S1):
   ```python
   if state == "S1" and entry_zone_ok:
       if not active_window:
           active_window = {
               "window_id": generate_episode_id("s1win"),
               "window_type": "s1_buy_signal",
               "started_at": now,
               "samples": [],
               "entered": False
           }
       # Capture sample
       sample = _capture_s1_window_sample(uptrend, now, levers)
       _append_window_sample(active_window, sample)
   ```

3. **Window Opening** (S3):
   ```python
   if state == "S3" and price < ema144:  # In retest band
       if not active_window:
           retest_index += 1
           active_window = {
               "window_id": generate_episode_id("s3win"),
               "retest_index": retest_index,
               "started_at": now,
               "samples": [],
               "entered": False
           }
       # Capture sample
       sample = _capture_s3_window_sample(uptrend, now, levers)
       _append_window_sample(active_window, sample)
   ```

4. **Window Closing**:
   - Window closes when conditions no longer met OR episode ends
   - On close: `_finalize_active_window()` is called
   - This function:
     - Summarizes samples (min/max/median for each signal)
     - Logs to `pattern_episode_events` table
     - Marks window as entered/skipped based on execution history

### Phase 2: Decision Tracking

**Location**: `pm_core_tick.py::_update_episode_entry_flags()`

The system tracks whether we actually entered during a window:

**S1 Entry Detection**:
```python
# Check execution history for S1 buy
last_s1_buy = execution_history.get("last_s1_buy")
if last_s1_buy and episode exists:
    buy_timestamp = last_s1_buy["timestamp"]
    if buy_timestamp >= episode["started_at"]:
        episode["entered"] = True
        active_window["entered"] = True
        active_window["entry_timestamp"] = buy_timestamp
```

**S3 Entry Detection**:
```python
# Check execution history for S3 buy
last_s3_buy = execution_history.get("last_s3_buy")
if last_s3_buy and active_window exists:
    buy_timestamp = last_s3_buy["timestamp"]
    if buy_timestamp >= active_window["started_at"]:
        active_window["entered"] = True
        active_window["entry_timestamp"] = buy_timestamp
```

**S3 Trim Detection** (for virtual success):
```python
# Check if trim occurred after episode start
last_trim = execution_history.get("last_trim")
if last_trim and trim_timestamp > episode["started_at"]:
    episode["trimmed"] = True  # Virtual success marker
```

### Phase 3: Outcome Determination

**Location**: `pm_core_tick.py::_process_episode_logging()`

**S1 Episode Outcomes**:
```python
if state == "S3" and prev_state in ("S1", "S2"):
    # Success: Reached S3
    outcome = "success" if episode["entered"] else "missed"
    
elif state == "S0" and prev_state in ("S1", "S2"):
    # Failure: Returned to S0
    outcome = "failure" if episode["entered"] else "correct_skip"
```

**S3 Episode Outcomes**:
```python
def _compute_s3_episode_outcome(episode):
    windows = episode.get("windows", [])
    entered_windows = [w for w in windows if w.get("entered")]
    
    if entered_windows:
        # Did any entered window succeed?
        if any(w.get("outcome") == "success" for w in entered_windows):
            return "success"
        return "failure"
    
    # No entries
    if any(w.get("samples") or w.get("summary") for w in windows):
        return "missed"  # Had opportunity but skipped
    return "correct_skip"  # No opportunity
```

**S3 Window Outcomes** (individual windows):
```python
def _compute_s3_window_outcomes(episode):
    windows = episode.get("windows", [])
    trimmed = episode.get("trimmed")  # Virtual success marker
    
    for win in windows:
        if win.get("outcome"):
            continue  # Already set
        
        # Success if: entered and got trim, OR episode got trim (virtual)
        if (win.get("entered") and win.get("trim_timestamp")) or trimmed:
            win["outcome"] = "success"
        # Failure set on S3 -> S0 transition
```

### Phase 4: Event Logging

**Location**: `pm_core_tick.py::_finalize_active_window()`

When a window closes, an event is logged to `pattern_episode_events`:

```python
decision = "acted" if active.get("entered") else "skipped"

# Build pattern key and scope
pattern_key, _, scope = _build_pattern_scope(
    position, uptrend_signals, action_type, 
    regime_context, token_bucket, state
)

# Extract factors (signal values at decision)
factors = active.get("summary") or {}
factors["a_value"] = levers.get("A_value")
factors["position_size_frac"] = levers.get("position_size_frac")

# Log to database
db_id = _log_episode_event(
    window=active,
    scope=scope,
    pattern_key=pattern_key,
    decision=decision,
    factors=factors,
    episode_id=active.get("window_id"),
    trade_id=position.get("current_trade_id") if decision == "acted" else None
)
```

**Database Schema** (`pattern_episode_events`):
```sql
CREATE TABLE pattern_episode_events (
    id BIGSERIAL PRIMARY KEY,
    scope JSONB NOT NULL,              -- {"chain": "solana", "bucket": "micro", ...}
    pattern_key TEXT NOT NULL,         -- "pm.s1_entry" or "pm.s3_retest"
    episode_id TEXT NOT NULL,          -- Unique episode ID
    trade_id TEXT,                     -- Linked trade if acted
    decision TEXT NOT NULL,            -- 'acted' or 'skipped'
    outcome TEXT,                      -- 'success', 'failure', 'missed', 'correct_skip' (or NULL if pending)
    factors JSONB NOT NULL,            -- Signal values at decision time
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

### Phase 5: Outcome Backfill

**Location**: `pm_core_tick.py::_update_episode_outcomes_from_meta()`

When an episode ends, outcomes are backfilled to all related events:

```python
def _update_episode_outcomes_from_meta(episode, outcome):
    windows = episode.get("windows", [])
    db_ids = [w.get("db_id") for w in windows if w.get("db_id")]
    if db_ids:
        _update_episode_outcome(db_ids, outcome)
```

This updates all `pattern_episode_events` rows for windows in the episode.

---

## Learning Pipeline: From Episodes to Overrides

### Step 1: The Miner (TuningMiner)

**Location**: `tuning_miner.py`

**Purpose**: Aggregate episode events into tuning rates (Win Rate, Miss Rate, False Positive Rate, Dodge Rate).

**Process**:

1. **Fetch Events**:
   ```python
   events = fetch_raw_events()  # Last 90 days, with outcomes
   ```

2. **Mine Lessons** (Recursive Apriori-like search):
   ```python
   # Group by scope dimensions (chain, mcap, timeframe, etc.)
   # For each scope slice with N >= 33 samples:
   for pattern_key in ["pm.s1_entry", "pm.s3_retest"]:
       group = events[events.pattern_key == pattern_key]
       
       acted = group[group.decision == "acted"]
       skipped = group[group.decision == "skipped"]
       
       # Calculate rates
       wr = len(acted[acted.outcome == "success"]) / len(acted)  # Win Rate
       fpr = len(acted[acted.outcome == "failure"]) / len(acted)  # False Positive Rate
       mr = len(skipped[skipped.outcome == "success"]) / len(skipped)  # Miss Rate
       dr = len(skipped[skipped.outcome == "failure"]) / len(skipped)  # Dodge Rate
       
       # Store lesson
       lesson = {
           "module": "pm",
           "pattern_key": pattern_key,
           "action_category": "tuning",
           "scope_subset": scope_slice,
           "lesson_type": "tuning_rates",
           "stats": {
               "wr": wr,
               "fpr": fpr,
               "mr": mr,
               "dr": dr,
               "n_acted": len(acted),
               "n_skipped": len(skipped),
               "n_misses": len(skipped[skipped.outcome == "success"]),
               "n_fps": len(acted[acted.outcome == "failure"])
           }
       }
   ```

3. **Write Lessons**:
   - Upsert to `learning_lessons` table
   - Key: `(module, pattern_key, action_category, scope_subset)`

### Step 2: The Judge (Override Materializer)

**Location**: `override_materializer.py::materialize_tuning_overrides()`

**Purpose**: Convert tuning rates into actionable overrides.

**Logic**:

```python
for lesson in tuning_lessons:
    stats = lesson["stats"]
    n_misses = stats["n_misses"]  # Skipped but succeeded
    n_fps = stats["n_fps"]         # Acted but failed
    
    # Pressure: Positive = Too many misses (loosen), Negative = Too many FPs (tighten)
    pressure = n_misses - n_fps
    
    if pressure == 0:
        continue  # No action needed
    
    # Calculate multipliers using drift formula
    ETA = 0.005  # Learning rate
    mult_threshold = exp(-ETA * pressure)  # Lower threshold = Looser
    mult_halo = exp(ETA * pressure)          # Higher halo = Looser
    
    # Clamp [0.5, 2.0]
    mult_threshold = max(0.5, min(2.0, mult_threshold))
    mult_halo = max(0.5, min(2.0, mult_halo))
    
    # Write overrides
    if "S1" in pattern_key:
        write_override("tuning_ts_min", mult_threshold)
        write_override("tuning_halo", mult_halo)
    elif "S3" in pattern_key:
        write_override("tuning_ts_min", mult_threshold)
        write_override("tuning_dx_min", mult_threshold)
```

**Override Storage** (`pm_overrides` table):
```sql
CREATE TABLE pm_overrides (
    pattern_key TEXT,
    action_category TEXT,  -- "tuning_ts_min", "tuning_halo", "tuning_dx_min"
    scope_subset JSONB,
    multiplier FLOAT,      -- Applied to base threshold/halo
    confidence_score FLOAT,
    last_updated_at TIMESTAMPTZ
);
```

### Step 3: Runtime Application

**Location**: `overrides.py::apply_pattern_execution_overrides()`

**Purpose**: Apply tuning overrides at decision time.

**Process**:

```python
def apply_pattern_execution_overrides(pattern_key, scope, plan_controls):
    # Query pm_overrides for this pattern + scope
    overrides = query_overrides(pattern_key, scope, 
                                ["tuning_ts_min", "tuning_halo", "tuning_dx_min"])
    
    adjusted = plan_controls.copy()
    
    # Apply multipliers
    if "tuning_ts_min" in overrides:
        base_ts = adjusted["signal_thresholds"]["ts_min"]
        mult = overrides["tuning_ts_min"]["multiplier"]
        adjusted["signal_thresholds"]["ts_min"] = base_ts * mult
    
    if "tuning_halo" in overrides:
        base_halo = adjusted["signal_thresholds"]["halo_mult"]
        mult = overrides["tuning_halo"]["multiplier"]
        adjusted["signal_thresholds"]["halo_mult"] = base_halo * mult
    
    if "tuning_dx_min" in overrides:
        base_dx = adjusted["signal_thresholds"]["dx_min"]
        mult = overrides["tuning_dx_min"]["multiplier"]
        adjusted["signal_thresholds"]["dx_min"] = base_dx * mult
    
    return adjusted
```

---

## Detailed Example: S1 Entry Episode

### Scenario: S1 Entry Opportunity

1. **State Transition**: `S0 → S1`
   - Episode created: `s1_epi_abc123`
   - `meta["s1_episode"]` initialized

2. **Window Opens**: `entry_zone_ok = True`
   - Window created: `s1win_xyz789`
   - Active window starts capturing samples

3. **Sample Capture** (every tick while window open):
   ```python
   sample = {
       "ts": "2025-01-15T10:00:00Z",
       "ts_score": 0.58,
       "ts_with_boost": 0.62,
       "sr_boost": 0.04,
       "ema60_slope": 0.01,
       "ema144_slope": 0.02,
       "halo_distance": 0.8,
       "entry_zone_ok": True,
       "ts_ok": True,
       "slope_ok": True,
       "a_value": 0.45
   }
   ```

4. **Decision Point**: PM evaluates entry
   - TS = 0.58, threshold = 0.60 → **Skipped** (TS too low)
   - OR: TS = 0.62, threshold = 0.60 → **Acted** (entered position)

5. **Window Closes**: `entry_zone_ok = False`
   - Window finalized
   - Summary computed: `{ts_score: {min: 0.56, max: 0.62, median: 0.59}, ...}`
   - Event logged:
     ```json
     {
       "pattern_key": "pm.s1_entry",
       "scope": {"chain": "solana", "bucket": "micro"},
       "episode_id": "s1win_xyz789",
       "decision": "skipped",
       "factors": {
         "ts_score": {"median": 0.59},
         "ts_min": 0.60,
         "halo_distance": {"median": 0.8},
         "a_value": 0.45
       },
       "outcome": null  // Pending
     }
     ```

6. **Episode Continues**: More windows may open/close

7. **Episode Ends**: `S1 → S3` (Success) or `S1 → S0` (Failure)
   - Outcome determined
   - All window events updated with outcome:
     ```json
     {
       "outcome": "missed"  // Skipped but reached S3
     }
     ```

8. **Learning**:
   - Miner aggregates: "For Solana micro, S1 entries: MR = 0.65 (65% of skips reached S3)"
   - Materializer: `pressure = 65 - 20 = 45` → `mult_ts = exp(-0.005 * 45) = 0.80`
   - Override created: `ts_min_mult = 0.80` (loosen by 20%)

9. **Next Time**: Same scope uses `ts_min = 0.60 * 0.80 = 0.48` (looser gate)

---

## Detailed Example: S3 Retest Episode

### Scenario: S3 DX Retest Opportunity

1. **State Transition**: `S2 → S3`
   - Episode created: `s3_epi_def456`
   - `meta["s3_episode"]` initialized

2. **Retest Window Opens**: `price < ema144` (dip into band)
   - Window created: `s3win_retest1`
   - Active window starts capturing samples

3. **Sample Capture**:
   ```python
   sample = {
       "ts": "2025-01-15T11:00:00Z",
       "ts_score": 0.55,
       "dx_score": 0.68,
       "edx_score": 0.35,
       "price_pos": 0.7,  // 70% down the band (closer to EMA333)
       "ema250_slope": 0.005,
       "ema333_slope": 0.003,
       "a_value": 0.50
   }
   ```

4. **Decision Point**: PM evaluates retest buy
   - DX = 0.68, threshold = 0.65 → **Acted** (added to position)
   - OR: DX = 0.63, threshold = 0.65 → **Skipped**

5. **Window Closes**: `price > ema144` (moved out of band)
   - Window finalized
   - Event logged with decision

6. **More Retests**: Episode may have multiple retest windows

7. **Episode Ends**: `S3 → S0` (trend broken)
   - Window outcomes computed:
     - Entered window + trim occurred → `outcome = "success"`
     - Entered window + no trim → `outcome = "failure"`
     - Skipped window + trim occurred → `outcome = "missed"`
     - Skipped window + no trim → `outcome = "correct_skip"`
   - Episode outcome: `success` if any entered window succeeded

8. **Learning**:
   - Miner: "For Solana micro, S3 retests: FPR = 0.55 (55% of entries failed)"
   - Materializer: `pressure = 10 - 55 = -45` → `mult_dx = exp(-0.005 * -45) = 1.25`
   - Override: `dx_min_mult = 1.25` (tighten by 25%)

9. **Next Time**: Same scope uses `dx_min = 0.65 * 1.25 = 0.8125` (tighter gate)

---

## Key Design Decisions

### 1. Window-Based Sampling

- **Why**: Captures signal evolution during opportunity window
- **How**: Samples capped at 12 (first + last + closest-to-threshold)
- **Benefit**: Can reconstruct decision context later

### 2. Virtual Success (S3)

- **Why**: Even if we skip, if a trim occurs, it's a missed opportunity
- **How**: `episode["trimmed"]` flag tracks trim after episode start
- **Benefit**: Learning from "what could have been"

### 3. Scope-Based Learning

- **Why**: Different markets/conditions need different gates
- **How**: Lessons grouped by `(pattern_key, scope_subset)`
- **Benefit**: Contextual tuning (e.g., Solana vs Base, Micro vs Small)

### 4. Drift Formula

- **Why**: Gradual, cumulative learning (not binary on/off)
- **How**: `mult = exp(ETA * pressure)` with small ETA (0.005)
- **Benefit**: Smooth convergence, avoids over-reaction

### 5. Minimum Sample Size

- **Why**: Avoid noise from small samples
- **How**: N_MIN = 33 episodes per scope slice
- **Benefit**: Statistically meaningful lessons

---

## Current Limitations & Future Work

1. **S2 Episodes**: Currently only S1 and S3 are tracked. S2 dip buys could be added.

2. **Lever Severity**: System captures lever deltas but doesn't weight by severity yet (planned).

3. **Decay**: Tuning lessons don't decay (unlike PM strength lessons). May need time-based decay.

4. **Multi-Lever Coordination**: Currently tunes TS/halo/DX independently. Could coordinate adjustments.

5. **Episode Token Gating**: Planned feature to block re-entry after failures until success observed.

---

## Summary

The episode-based learning tuning system creates a complete feedback loop:

1. **Track**: Every opportunity (episode) with decision and outcome
2. **Learn**: Aggregate into rates (WR, MR, FPR, DR) per scope
3. **Judge**: Convert rates into pressure → multipliers
4. **Apply**: Adjust entry gates at runtime
5. **Iterate**: System continuously improves entry quality

This enables the system to learn from both successes and failures, tightening gates when too many false positives occur, and loosening them when too many opportunities are missed.



