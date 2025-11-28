# Learning System v5 Implementation Roadmap

**Status**: Implementation-ready spec for integrating final_stages specs into the live system.  
**Purpose**: Complete end-to-end plan for building the v5 learning stack with pattern keys, scope stats, lessons, overrides, and meta-learning layers all wired from day one.

---

## Overview

This roadmap implements the learning system defined in:
- `PATTERN_KEY_SCOPE_SPEC.md` - Pattern identity, scope dimensions, controls
- `PM_Learning_Lever_Map.md` - Capital and execution lever mappings
- `CAP_BUCKET_REGIME_SPEC.md` - Bucket-aware regime context
- `V5_META_LEARNING_IMPLEMENTATION_PLAN.md` - Meta-learning layers (v5.1-v5.3)

**Key principle**: When v5 learning is activated, the **full stack** is live:
- Pattern key + scope + controls logging
- `pattern_scope_stats` aggregation with v5.1 regime weights
- Lessons with capital + tuning levers + v5.2 decay + v5.3 latent factors
- Runtime overrides for both strength and execution tuning
- All meta-learning layers present from day one (with small effects until data accumulates)

Safety comes from **tight bounds and learning rates**, not from disabling features.

---

## 1. Data Contract & Schema Changes

### 1.1 Action Logging Format

Every PM/DM action must log:

```json
{
  "pattern_key": "pm.uptrend.S1.buy_flag",
  "action_category": "entry",  // see mapping below
  "scope": {
    "macro_phase": "Recover",
    "meso_phase": "Dip",
    "micro_phase": "Good",
    "bucket_leader": "micro",
    "bucket_rank_position": 1,
    "market_family": "lowcaps",
    "bucket": "micro",
    "timeframe": "1h",
    "A_mode": "normal",
    "E_mode": "aggressive"
  },
  "controls": {
    "signals": {
      "TS": 0.65,
      "OX": 0.42,
      "DX": 0.78,
      "EDX": 0.15,
      "OBV_z": 1.2
    },
    "applied_knobs": {
      "entry_delay_bars": 1,
      "phase1_frac": 0.15,
      "trim_delay": 3,
      "trail_mult": 1.0,
      "min_ts_for_add": 0.5
    }
  }
}
```

**Action category mapping** (must be consistent across codebase):

| Action Types | Category | Notes |
|-------------|----------|-------|
| `entry_immediate`, `E1`, `E2` | `entry` | All entry behavior patterns |
| `add`, `scale_up` (if distinct) | `add` | Additional position scaling |
| `trim`, `partial_exit` | `trim` | Profit-taking / position reduction |
| `cut`, `emergency_exit`, `panic_exit` | `exit` | Full exits / loss-cutting |

**Source files to update**:
- `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py` - Pattern key generation
- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` - Action logging
- DM equivalent action loggers (if separate)

### 1.2 New Table: `pattern_scope_stats`

**Purpose**: Aggregated edge stats per `(pattern_key, action_category, scope_subset)`.

**Schema**:
```sql
CREATE TABLE pattern_scope_stats (
  id BIGSERIAL PRIMARY KEY,
  pattern_key TEXT NOT NULL,
  action_category TEXT NOT NULL CHECK (action_category IN ('entry', 'add', 'trim', 'exit')),
  scope_mask SMALLINT NOT NULL,  -- bitmask over 10 scope dims
  scope_values JSONB NOT NULL,   -- only dims indicated by mask
  scope_values_hash TEXT NOT NULL,  -- deterministic hash for uniqueness
  n INT NOT NULL,                -- sample count (also in stats for convenience)
  stats JSONB NOT NULL,           -- { avg_rr, variance, edge_raw, time_efficiency, ... }
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (pattern_key, action_category, scope_mask, scope_values_hash)
);

CREATE INDEX idx_pattern_scope_stats_lookup 
  ON pattern_scope_stats(pattern_key, action_category, scope_mask);
CREATE INDEX idx_pattern_scope_stats_n 
  ON pattern_scope_stats(n DESC) WHERE n >= 10;
```

**Scope dimension bitmask** (10 dims total):
- Bit 0: `macro_phase`
- Bit 1: `meso_phase`
- Bit 2: `micro_phase`
- Bit 3: `bucket_leader`
- Bit 4: `bucket_rank_position`
- Bit 5: `market_family`
- Bit 6: `bucket`
- Bit 7: `timeframe`
- Bit 8: `A_mode`
- Bit 9: `E_mode`

**Stats JSONB shape**:
```json
{
  "n": 42,
  "avg_rr": 1.85,
  "variance": 0.32,
  "edge_raw": 0.68,
  "time_efficiency": 0.75,
  "field_coherence": 0.82,
  "recurrence_score": 0.45,
  "segments_tested": 5,
  "segments_positive": 4
}
```

**N_min thresholds per subset size** (configurable, example defaults):
- k = 1-2 dims → `N_min = 10`
- k = 3-4 dims → `N_min = 20`
- k = 5-6 dims → `N_min = 30`
- k = 7+ dims → `N_min = 50` (or skip if too sparse)

### 1.3 Extended `learning_lessons` Table

**New columns**:
```sql
ALTER TABLE learning_lessons 
  ADD COLUMN action_category TEXT CHECK (action_category IN ('entry', 'add', 'trim', 'exit')),
  ADD COLUMN scope_dims TEXT[],  -- e.g. ['macro_phase', 'bucket', 'A_mode']
  ADD COLUMN scope_values JSONB,  -- e.g. {"macro_phase": "Recover", "bucket": "micro"}
  ADD COLUMN lesson_strength FLOAT,  -- 0.0-1.0, for decay weighting
  ADD COLUMN decay_halflife_hours INT,  -- from v5.2
  ADD COLUMN latent_factor_id TEXT;  -- from v5.3
```

**Effect payload shape** (extends existing `effect` JSONB):
```json
{
  "capital_levers": {
    "size_mult": 1.12,
    "entry_aggression_mult": 1.08,
    "exit_aggression_mult": 0.95
  },
  "execution_levers": {
    "entry_delay_bars": 1,
    "phase1_frac_mult": 0.85,
    "trim_delay_mult": 1.1,
    "trail_mult": 0.95,
    "signal_thresholds": {
      "min_ts_for_add": 0.55,
      "min_ox_for_trim": 0.40
    }
  }
}
```

### 1.4 Meta-Learning Tables (v5.1-v5.3)

**`learning_regime_weights`** (v5.1):
```sql
CREATE TABLE learning_regime_weights (
  id BIGSERIAL PRIMARY KEY,
  pattern_key TEXT NOT NULL,
  action_category TEXT NOT NULL,
  regime_signature TEXT NOT NULL,  -- e.g. "macro=Recover|meso=Dip|bucket_rank=1"
  weights JSONB NOT NULL,  -- { time_efficiency: 0.6, field_coherence: 0.8, recurrence: 0.5, variance: 0.3 }
  n_samples INT NOT NULL,
  confidence FLOAT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (pattern_key, action_category, regime_signature)
);
```

**`learning_edge_history`** (v5.2):
```sql
CREATE TABLE learning_edge_history (
  id BIGSERIAL PRIMARY KEY,
  pattern_key TEXT NOT NULL,
  action_category TEXT NOT NULL,
  scope_signature TEXT NOT NULL,  -- hash or sorted JSON string
  edge_raw FLOAT NOT NULL,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  n INT NOT NULL  -- sample count at this snapshot
);

CREATE INDEX idx_edge_history_pattern 
  ON learning_edge_history(pattern_key, action_category, scope_signature, ts DESC);
```

**`learning_latent_factors`** (v5.3):
```sql
CREATE TABLE learning_latent_factors (
  id BIGSERIAL PRIMARY KEY,
  factor_id TEXT NOT NULL UNIQUE,
  pattern_keys TEXT[] NOT NULL,  -- patterns in this cluster
  representative_pattern TEXT,  -- canonical pattern for this factor
  correlation_matrix JSONB,  -- pairwise correlations
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 1.5 Override Config Structure

**In Supabase `learning_configs` table or `pm_config.jsonc`**:
```jsonc
{
  "pattern_strength_overrides": [
    {
      "pattern_key": "pm.uptrend.S1.buy_flag",
      "action_category": "entry",
      "scope": {
        "macro_phase": "Recover",
        "bucket": "micro"
      },
      "levers": {
        "size_mult": 1.12,
        "entry_aggression_mult": 1.08,
        "exit_aggression_mult": 0.95
      },
      "lesson": {
        "id": "ls_abc123",
        "strength": 0.34,
        "decay_halflife_hours": 720,
        "enabled": true
      }
    }
  ],
  "pattern_overrides": [
    {
      "pattern_key": "pm.uptrend.S1.buy_flag",
      "action_category": "entry",
      "scope": {
        "macro_phase": "Recover",
        "bucket_rank_position": 1,
        "A_mode": "normal"
      },
      "levers": {
        "entry_delay_bars": 1,
        "phase1_frac_mult": 0.85,
        "phase_scaling": {"S1": 0.9, "S2": 1.05, "S3": 1.1},
        "trim_delay_mult": 1.1,
        "trail_mult": 0.95,
        "panic_trigger_mult": 1.05,
        "signal_thresholds": {
          "min_ts_for_add": 0.55,
          "min_ox_for_trim": 0.40
        }
      },
      "lesson": {
        "id": "ls_def456",
        "strength": 0.28,
        "decay_halflife_hours": 480,
        "enabled": true
      }
    }
  ]
}
```

---

## 2. Core Implementation Components

### 2.1 Pattern Scope Stats Aggregation Job

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py`

**Responsibilities**:
1. Ingest action logs / `completed_trades` with pattern_key + action_category + scope + controls
2. For each `(pattern_key, action_category)` pair:
   - Generate all non-empty subset masks (1-10 dims)
   - Group events by scope subset
   - Compute stats (n, avg_rr, variance, edge_raw) per subset
   - Only upsert rows where `n >= N_min` for that subset size
3. Update `pattern_scope_stats` table

**Note on R/R attribution**: Use **closed trades** as the unit of outcome. For pattern strength, assign the trade-level R/R (and time_efficiency, etc.) to the relevant action events (e.g., entry-category actions) when aggregating. We're not trying to estimate per-action R/R mid-trade — only after we know the final outcome. This locks in the "learning happens on close, logging happens per action" model.

**Edge computation** (with v5.1 regime weights baked in):
```python
def compute_edge_with_regime_weights(
    avg_rr: float,
    variance: float,
    n: int,
    rr_baseline: float,
    time_efficiency: float,
    field_coherence: float,
    recurrence_score: float,
    regime_signature: str,
    regime_weights: Dict[str, float]  # from learning_regime_weights
) -> float:
    """
    Compute edge_raw using regime-specific weights (v5.1).
    Falls back to defaults if weights not yet learned.
    """
    delta_rr = avg_rr - rr_baseline
    coherence = 1.0 / (1.0 + variance)
    support = math.log(1 + n)
    
    # Apply regime-specific weights (default 1.0 if not learned)
    time_weight = regime_weights.get('time_efficiency', 1.0) * time_efficiency
    field_weight = regime_weights.get('field_coherence', 1.0) * field_coherence
    recur_weight = regime_weights.get('recurrence', 1.0) * recurrence_score
    var_penalty = regime_weights.get('variance', 1.0) * (1.0 / (1.0 + variance))
    
    edge_raw = delta_rr * coherence * support * (
        0.5 + 0.5 * (time_weight + field_weight + recur_weight) / 3.0
    ) * var_penalty
    
    return edge_raw
```

**Cron schedule**: Run every 1-4 hours (configurable), or triggered by position_closed events.

### 2.2 Lesson Builder (with v5.2 + v5.3)

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/braiding_lesson_builder.py` (extend existing)

**Responsibilities**:
1. Query `pattern_scope_stats` for candidates (n >= N_min, |edge_raw| >= edge_min)
2. For each `(pattern_key, action_category)`:
   - Find simplest scope subset with sufficient edge
   - Compute incremental edge vs parent subsets
   - Estimate half-life (v5.2) from `learning_edge_history`
   - Check latent factor (v5.3) to avoid duplicate patterns
   - Map edge → capital levers + execution levers
   - Write to `learning_lessons` with full payload

**Half-life estimation** (v5.2):
```python
def estimate_half_life(
    pattern_key: str,
    action_category: str,
    scope_signature: str,
    edge_history: List[Tuple[float, datetime]]
) -> Optional[float]:
    """
    Fit exponential decay: edge(t) = edge_0 * exp(-lambda * t)
    Return half_life_days = ln(2) / lambda
    """
    if len(edge_history) < 5:
        return None  # insufficient data
    
    # Fit exponential decay curve
    # Return half_life_days
    ...
```

**Latent factor check** (v5.3):
```python
def get_latent_factor(
    pattern_key: str,
    latent_factors: Dict[str, List[str]]
) -> Optional[str]:
    """
    Check if pattern_key belongs to an existing latent factor cluster.
    Return factor_id if found, None if unique.
    """
    for factor_id, patterns in latent_factors.items():
        if pattern_key in patterns:
            return factor_id
    return None
```

**Lever mapping**:
```python
def map_edge_to_levers(
    edge_raw: float,
    action_category: str,
    counterfactual_signals: Dict[str, float]
) -> Dict[str, Any]:
    """
    Map edge_raw + counterfactuals to capital + execution levers.
    Apply tight bounds and small learning rate.
    """
    learning_rate = 0.02  # max ±2% per epoch
    edge_scale = 20.0
    
    # Capital levers
    size_mult = clamp(1.0 + (edge_raw / edge_scale) * learning_rate, 0.7, 1.3)
    entry_aggression_mult = clamp(1.0 + (edge_raw / edge_scale) * learning_rate, 0.8, 1.2)
    exit_aggression_mult = clamp(1.0 - (edge_raw / edge_scale) * learning_rate, 0.8, 1.2)
    
    # Execution levers (from counterfactual signals)
    entry_delay_bars = adjust_if_needed(counterfactual_signals.get('could_enter_better'), ...)
    trim_delay_mult = adjust_if_needed(counterfactual_signals.get('could_exit_better'), ...)
    # ... etc
    
    return {
        "capital_levers": {...},
        "execution_levers": {...}
    }
```

### 2.3 Override Materialization Job

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py`

**Responsibilities**:
1. Query active lessons from `learning_lessons` (status='active', enabled=true)
2. Group by `(pattern_key, action_category)`
3. Apply decay multipliers (v5.2) based on `decay_halflife_hours` and lesson age
4. Check latent factors (v5.3) - merge or deduplicate if needed
5. Write to `learning_configs.pattern_strength_overrides` + `pattern_overrides`
6. Hot-reload config (or trigger PM/DM reload)

**Decay application**:
```python
def apply_decay(
    lever_value: float,
    lesson_strength: float,
    decay_halflife_hours: int,
    lesson_age_hours: float
) -> float:
    """
    Decay lever strength toward 1.0 (neutral) based on half-life.
    """
    if decay_halflife_hours <= 0:
        return lever_value
    
    decay_factor = math.exp(-0.693 * lesson_age_hours / decay_halflife_hours)
    neutral = 1.0
    return neutral + (lever_value - neutral) * decay_factor * lesson_strength
```

### 2.4 Runtime Override Application

**File**: `src/intelligence/lowcap_portfolio_manager/pm/overrides.py` (new)

**Functions**:
```python
def apply_pattern_strength_overrides(
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any],
    base_levers: Dict[str, float]  # { A_value, E_value, position_size_frac }
) -> Dict[str, float]:
    """
    Apply capital lever overrides (size_mult, entry_aggression_mult, exit_aggression_mult).
    Returns adjusted levers.
    """
    overrides = load_pattern_strength_overrides()  # from config
    matches = find_matching_overrides(overrides, pattern_key, action_category, scope)
    
    if not matches:
        return base_levers
    
    # Use most specific match (highest # of scope dims)
    best_match = sorted(matches, key=lambda m: len(m['scope']), reverse=True)[0]
    
    adjusted = {
        "A_value": base_levers["A_value"] * best_match["levers"].get("entry_aggression_mult", 1.0),
        "E_value": base_levers["E_value"] * best_match["levers"].get("exit_aggression_mult", 1.0),
        "position_size_frac": base_levers["position_size_frac"] * best_match["levers"].get("size_mult", 1.0)
    }
    
    # Clamp to safety bounds
    adjusted["A_value"] = clamp(adjusted["A_value"], 0.0, 1.0)
    adjusted["E_value"] = clamp(adjusted["E_value"], 0.0, 1.0)
    adjusted["position_size_frac"] = clamp(adjusted["position_size_frac"], 0.0, 1.0)
    
    # Log telemetry
    log_override_application(pattern_key, action_category, best_match, adjusted)
    
    return adjusted


def apply_pattern_execution_overrides(
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any],
    plan_controls: Dict[str, Any]  # base plan's controls
) -> Dict[str, Any]:
    """
    Apply execution lever overrides (entry_delay_bars, thresholds, trail_mult, etc.).
    Returns adjusted controls.
    """
    overrides = load_pattern_overrides()  # from config
    matches = find_matching_overrides(overrides, pattern_key, action_category, scope)
    
    if not matches:
        return plan_controls
    
    best_match = sorted(matches, key=lambda m: len(m['scope']), reverse=True)[0]
    levers = best_match["levers"]
    
    adjusted = dict(plan_controls)
    
    # Apply multipliers
    if "entry_delay_bars" in levers:
        adjusted["entry_delay_bars"] = levers["entry_delay_bars"]
    if "phase1_frac_mult" in levers:
        adjusted["phase1_frac"] *= levers["phase1_frac_mult"]
    if "trim_delay_mult" in levers:
        adjusted["trim_delay"] *= levers["trim_delay_mult"]
    if "trail_mult" in levers:
        adjusted["trail_speed"] *= levers["trail_mult"]
    
    # Apply signal thresholds
    if "signal_thresholds" in levers:
        thresholds = levers["signal_thresholds"]
        for key, value in thresholds.items():
            adjusted[key] = value
    
    log_override_application(pattern_key, action_category, best_match, adjusted)
    
    return adjusted
```

**Integration points**:
- `pm_core_tick.py`: Call `apply_pattern_strength_overrides` before `compute_levers()`, call `apply_pattern_execution_overrides` before action planning
- DM equivalent: Apply `alloc_multiplier` overrides at allocation time

### 2.5 Meta-Learning Jobs (v5.1-v5.3)

**v5.1 Regime Weight Learning** (`jobs/regime_weight_learner.py`):
- Daily cron
- Group `pattern_scope_stats` by regime signature
- Measure which multipliers (time_efficiency, field_coherence, etc.) correlate with edge improvements
- Update `learning_regime_weights` table
- Initially weights are neutral (1.0), become meaningful as data accumulates

**v5.2 Half-Life Estimation** (`jobs/half_life_estimator.py`):
- Weekly cron
- For each `(pattern_key, action_category, scope_signature)`:
  - Query `learning_edge_history` for time series
  - Fit exponential decay curve
  - Update `learning_lessons.decay_halflife_hours`
- Early on, fits are crude → decay multipliers near 1.0

**v5.3 Latent Factor Clustering** (`jobs/latent_factor_clusterer.py`):
- Weekly cron
- Extract match sets per pattern (which trades matched each pattern)
- Compute pairwise correlation matrix
- Run hierarchical clustering
- Update `learning_latent_factors` table
- Early on, clusters may degenerate to "each pattern in own factor" → becomes meaningful as history grows

---

## 3. CAP Bucket Regime Integration

### 3.1 Prerequisites

- `phase_state_bucket` table exists and is being written by tracker job
- `_get_regime_context()` returns `bucket_phases`, `bucket_rank`, `bucket_population`
- `token_cap_bucket` table has current bucket per token

### 3.2 Scope Logging

When logging action scope:
1. Read `macro_phase`, `meso_phase`, `micro_phase` from `_get_regime_context()`
2. Read `bucket_leader` = `bucket_rank[0]`
3. Read token's bucket from `token_cap_bucket`
4. Compute `bucket_rank_position` = index of token's bucket in `bucket_rank` (1-indexed)
5. Log all of these in the `scope` JSON

### 3.3 DM Path

DM must log the same structure:
- `pattern_key` (DM family/curator/chain patterns)
- `action_category` (same mapping: entry/add/trim/exit)
- `scope` (DM-specific dims: `curator_tier`, `intent`, `chain`, plus regime/bucket if applicable)
- `controls` (DM-specific signals)

DM can share `pattern_scope_stats` table (with different pattern_key namespace) or have its own table with identical schema.

---

## 4. Implementation Sequence

**Important**: These phases are **implementation order**, not separate public rollouts. v5 learning is only considered "ON" once Phases 1–5 are complete and all components are enabled together. We build sequentially for practical engineering reasons, but the full system (including v5.1/v5.2/v5.3) must be present before activation.

### Phase 1: Schema & Logging Foundation

1. **Create new tables**:
   - `pattern_scope_stats`
   - `learning_regime_weights`
   - `learning_edge_history`
   - `learning_latent_factors`
   - Extend `learning_lessons` with new columns

2. **Update action logging**:
   - Modify `pm_core_tick.py` to emit pattern_key + action_category + scope + controls
   - Ensure `_get_regime_context()` populates macro/meso/micro + bucket fields
   - Test logging output matches spec

3. **DM logging** (if separate):
   - Mirror PM logging structure
   - Ensure DM pattern_key generation follows same canonical format

**Validation**: Logs contain all required fields, scope values are valid, action_category mapping is consistent.

### Phase 2: Aggregation & Stats

1. **Build `pattern_scope_aggregator` job**:
   - Ingest action logs
   - Generate subset masks
   - Compute stats with v5.1 regime weights (initially default/neutral)
   - Upsert to `pattern_scope_stats`

2. **Test aggregation**:
   - Run on historical data if available
   - Verify N_min thresholds work correctly
   - Check edge_raw values are reasonable

**Validation**: `pattern_scope_stats` has rows, stats are computed correctly, subset masks are valid.

### Phase 3: Lesson Builder + Meta-Learning ✅

1. **Extend lesson builder** ✅:
   - ✅ Created `lesson_builder_v5.py` that queries `pattern_scope_stats` instead of raw braids
   - ✅ Implemented half-life estimation (v5.2) with fallback for missing scipy
   - ✅ Implemented latent factor check (v5.3) to avoid duplicate patterns
   - ✅ Maps edge → full lever payload (capital + execution levers)
   - ✅ Writes to `learning_lessons` with v5 fields (pattern_key, action_category, scope_dims, scope_values, lesson_strength, decay_halflife_hours, latent_factor_id)

2. **Build meta-learning jobs** ✅:
   - ✅ `regime_weight_learner.py` (v5.1) - learns regime-specific weights daily
   - ✅ `half_life_estimator.py` (v5.2) - estimates decay half-lives weekly, also snapshots edge history
   - ✅ `latent_factor_clusterer.py` (v5.3) - clusters overlapping patterns weekly

3. **Test lesson generation**:
   - Verify lessons have action_category
   - Check lever payloads are within bounds
   - Confirm meta-learning fields are populated (even if neutral early)

**Validation**: Lessons are created, payloads are valid, meta-learning jobs run without errors.

**Files created**:
- `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py`
- `src/intelligence/lowcap_portfolio_manager/jobs/regime_weight_learner.py`
- `src/intelligence/lowcap_portfolio_manager/jobs/half_life_estimator.py`
- `src/intelligence/lowcap_portfolio_manager/jobs/latent_factor_clusterer.py`
- Updated `src/database/learning_lessons_v5_alter.sql` to include pattern_key column

### Phase 4: Override System ✅

1. **Build override materializer** ✅:
   - ✅ Created `override_materializer.py` that reads active lessons
   - ✅ Applies decay (v5.2) based on half-life and lesson age
   - ✅ Handles latent factors (v5.3) by merging levers from duplicate patterns
   - ✅ Writes to `learning_configs` table with `pattern_strength_overrides` and `pattern_overrides`

2. **Build runtime override functions** ✅:
   - ✅ Created `pm/overrides.py` with `apply_pattern_strength_overrides()` for capital levers
   - ✅ Created `apply_pattern_execution_overrides()` for execution levers
   - ✅ Integrated into `plan_actions_v4()` via `_apply_v5_overrides_to_action()` helper
   - ✅ Updated `pm_core_tick.py` to pass regime_context, token_bucket, and feature_flags

3. **Integrate into PM/DM** ✅:
   - ✅ Wired override calls into action planning (all action types)
   - ✅ Added telemetry logging in override functions
   - ✅ Feature flag support for gradual rollout

**Validation**: Overrides are written to config, runtime functions match correctly, telemetry logs are created.

**Files created**:
- `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py`
- `src/intelligence/lowcap_portfolio_manager/pm/overrides.py`
- Updated `src/intelligence/lowcap_portfolio_manager/pm/actions.py` to apply overrides
- Updated `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` to pass override context

### Phase 5: Full System Integration ✅

1. **Enable all components** ✅:
   - ✅ Created `v5_learning_scheduler.py` to orchestrate all learning jobs
   - ✅ Pattern scope aggregator: Every 2 hours
   - ✅ Lesson builder: Every 6 hours
   - ✅ Override materializer: Every 2 hours
   - ✅ Regime weight learner (v5.1): Daily at 01:00 UTC
   - ✅ Half-life estimator (v5.2): Weekly on Monday at 02:00 UTC
   - ✅ Latent factor clusterer (v5.3): Weekly on Monday at 03:00 UTC
   - ✅ Runtime overrides: Enabled via feature flags in config

2. **Monitor & validate** ✅:
   - ✅ Created `v5_learning_validator.py` to check system health
   - ✅ Validates tables exist and have data
   - ✅ Checks action logging emits v5 fields
   - ✅ Verifies stats aggregation has multiple subset sizes
   - ✅ Confirms lessons have v5 fields and lever payloads
   - ✅ Checks overrides are materialized in config
   - ✅ Monitors meta-learning table populations

3. **Gradual rollout**:
   - Start with small learning rates (0.01-0.02) - configured in lesson_builder_v5.py
   - Monitor for 1-2 weeks using validator
   - Gradually increase if stable

**Validation**: Full loop is working, no errors, overrides are being applied, meta-learning is active.

**Files created**:
- `src/intelligence/lowcap_portfolio_manager/jobs/v5_learning_scheduler.py` - Orchestrates all learning jobs
- `src/intelligence/lowcap_portfolio_manager/jobs/v5_learning_validator.py` - System health validation

**Integration**:
- Scheduler can be run standalone or integrated into `run_social_trading.py`
- Feature flags stored in `learning_configs.pm_config.feature_flags`
- All jobs respect feature flags for gradual rollout

---

## 5. Safety & Bounds

### 5.1 Lever Bounds

All levers have explicit min/max:

| Lever | Min | Max | Notes |
|-------|-----|-----|-------|
| `size_mult` | 0.7 | 1.3 | ±30% max deviation |
| `entry_aggression_mult` | 0.8 | 1.2 | ±20% max deviation |
| `exit_aggression_mult` | 0.8 | 1.2 | ±20% max deviation |
| `entry_delay_bars` | 0 | 5 | Hard limit |
| `phase1_frac_mult` | 0.5 | 1.5 | ±50% max deviation |
| `trim_delay_mult` | 0.5 | 2.0 | ±100% max deviation |
| `trail_mult` | 0.5 | 2.0 | ±100% max deviation |
| Signal thresholds | config-dependent | | Per-threshold bounds |

### 5.2 Learning Rate

Global learning rate cap: **±2% per epoch** (configurable).

```python
max_step = 0.02  # 2% max change per learning cycle
delta_mult = clamp(delta_mult, -max_step, max_step)
```

### 5.3 Feature Flags

- `learning_overrides_enabled` - Master switch for runtime overrides
- `learning_overrides_enabled_regimes` - List of regimes where overrides are active (e.g., `["Recover", "Good"]`)
- `learning_overrides_enabled_buckets` - List of buckets where overrides are active
- `v5_meta_learning_enabled` - Enable v5.1/v5.2/v5.3 jobs

---

## 6. Open Questions / Risks

1. **Performance**: `pattern_scope_stats` aggregation over large action logs - may need batching/streaming
2. **Storage**: Edge history table could grow large - consider retention policy or archiving
3. **DM scope dims**: Finalize DM-specific scope dimensions (curator, intent, etc.)
4. **Telemetry**: Dashboard/alerting for override effectiveness (ΔR/R per override)
5. **Migration**: If any existing braids/lessons need to be migrated to new schema

---

## 7. Success Criteria

v5 learning system is "live" when:

- ✅ All tables exist and are being populated
- ✅ Action logging emits pattern_key + action_category + scope + controls
- ✅ `pattern_scope_stats` has rows with valid stats
- ✅ `pattern_scope_stats` rows exist for multiple subset sizes (k=1–4 at least), not just the full scope
- ✅ Lessons are being created with full lever payloads
- ✅ Overrides are materialized in config
- ✅ Runtime override functions are called and applying changes
- ✅ Meta-learning jobs (v5.1/v5.2/v5.3) are running
- ✅ Telemetry shows override application rates
- ✅ No errors in logs
- ✅ Lever bounds are respected

**Note**: Early effects may be small (neutral weights, crude half-life fits, degenerate clusters), but the **full machinery is present** from day one.

---

## 8. Next Steps

1. Review this roadmap with team
2. Create DDL scripts for all new tables
3. Implement Phase 1 (schema + logging)
4. Test with sample data
5. Proceed through phases sequentially
6. Document any deviations or learnings

---

*This roadmap implements the complete v5 learning stack as defined in the final_stages specs. All components are built and wired from day one, with safety coming from bounds and learning rates rather than feature disabling.*

