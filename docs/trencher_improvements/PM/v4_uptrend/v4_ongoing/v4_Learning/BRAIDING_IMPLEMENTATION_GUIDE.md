# Braiding System Implementation Guide

**Status**: Implementation Guide - Step-by-Step Instructions for Building Braiding System

**Purpose**: This document provides concrete implementation details for the braiding system, including schema, pseudo-code, and integration hooks.

**Related Documents**:
- [BRAIDING_SYSTEM_DESIGN.md](./BRAIDING_SYSTEM_DESIGN.md) - High-level design and architecture
- [LEARNING_SYSTEM_V4.md](./LEARNING_SYSTEM_V4.md) - Foundation (coefficients system)

---

## Table of Contents

1. [Database Schema](#database-schema)
2. [Dimension Definitions & Bucketing Rules](#dimension-definitions--bucketing-rules)
3. [Pattern Generation](#pattern-generation)
4. [Streaming Stats Update](#streaming-stats-update)
5. [Edge Score Calculation](#edge-score-calculation)
6. [Lesson Builder](#lesson-builder)
7. [Integration Hooks](#integration-hooks)

---

## Database Schema

### `learning_braids` Table

```sql
CREATE TABLE learning_braids (
    pattern_key TEXT PRIMARY KEY,  -- "big_win|state=S1|A=med|buy_flag=true"
    module TEXT NOT NULL,           -- 'dm' | 'pm' (explicit module, not just in family_id)
    dimensions JSONB NOT NULL,     -- { outcome_class: "big_win", state: "S1", a_bucket: "med", buy_flag: true }
    stats JSONB NOT NULL,          -- { n, sum_rr, sum_rr_squared, avg_rr, variance, win_rate, avg_hold_time_days }
    family_id TEXT NOT NULL,       -- "pm|add|S1|big_win" (computed from core dimensions)
    parent_keys TEXT[],            -- Array of parent pattern_keys for incremental edge calculation
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_learning_braids_module ON learning_braids(module);
CREATE INDEX idx_learning_braids_family ON learning_braids(family_id);
CREATE INDEX idx_learning_braids_pattern ON learning_braids(pattern_key);  -- Already PK, but explicit for clarity

COMMENT ON TABLE learning_braids IS 'Raw pattern statistics - aggregated across all trades matching each pattern';
COMMENT ON COLUMN learning_braids.pattern_key IS 'Unique pattern identifier (sorted, delimited dimensions)';
COMMENT ON COLUMN learning_braids.dimensions IS 'Dimension values that define this pattern (JSONB for flexible querying)';
COMMENT ON COLUMN learning_braids.stats IS 'Aggregated statistics: n, sum_rr, sum_rr_squared, avg_rr, variance, win_rate, avg_hold_time_days';
COMMENT ON COLUMN learning_braids.family_id IS 'Family core dimensions (module|action|state|outcome_class for PM, module|curator|chain|outcome_class for DM)';
COMMENT ON COLUMN learning_braids.parent_keys IS 'Array of parent pattern_keys (all (k-1) subsets) for incremental edge calculation';
```

**Stats JSONB Structure**:
```json
{
  "n": 23,                    // Sample size
  "sum_rr": 52.9,             // Sum of R/R values (for streaming avg)
  "sum_rr_squared": 125.3,    // Sum of R/R² (for streaming variance)
  "avg_rr": 2.3,              // Average R/R (computed: sum_rr / n)
  "variance": 0.5,             // Variance (computed: (sum_rr_squared / n) - avg_rr²)
  "win_rate": 0.87,            // Win rate (trades with R/R > 0)
  "avg_hold_time_days": 4.8   // Average hold time in days
}
```

### `learning_lessons` Table

```sql
CREATE TABLE learning_lessons (
    id SERIAL PRIMARY KEY,
    module TEXT NOT NULL,        -- 'dm' | 'pm'
    trigger JSONB NOT NULL,      -- { state: "S1", a_bucket: "med", buy_flag: true, ... }
    effect JSONB NOT NULL,       -- { size_multiplier: 1.08 } or { alloc_multiplier: 0.8 }
    stats JSONB NOT NULL,        -- { edge_raw, incremental_edge, n, avg_rr, family_id, ... }
    status TEXT NOT NULL,        -- 'candidate' | 'active' | 'deprecated'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_validated TIMESTAMPTZ,
    notes TEXT
);

CREATE INDEX idx_learning_lessons_module_status ON learning_lessons(module, status);
CREATE INDEX idx_learning_lessons_trigger ON learning_lessons USING GIN(trigger);  -- For subset matching

COMMENT ON TABLE learning_lessons IS 'Compressed, validated rules derived from braids - used at decision-time';
COMMENT ON COLUMN learning_lessons.trigger IS 'Dimension values that trigger this lesson (subset of context)';
COMMENT ON COLUMN learning_lessons.effect IS 'Behavioral adjustment: size_multiplier (PM) or alloc_multiplier (DM)';
COMMENT ON COLUMN learning_lessons.stats IS 'Evidence: edge_raw, incremental_edge, n, avg_rr, family_id';
COMMENT ON COLUMN learning_lessons.status IS 'Lifecycle: candidate (newly created), active (validated, in use), deprecated (no longer valid)';
```

**Effect JSONB Structure**:
```json
{
  "size_multiplier": 1.08  // For PM: multiply action size by this (clamped to [0.9, 1.1])
}
```

or

```json
{
  "alloc_multiplier": 0.8  // For DM: multiply allocation by this (clamped to [0.5, 1.5])
}
```

---

## Dimension Definitions & Bucketing Rules

### DM Dimensions (from `entry_context`)

All dimensions are captured **at entry time** (when DM creates position).

| Dimension | Type | Buckets | Source |
|-----------|------|---------|--------|
| `curator` | string | Raw curator ID | `entry_context.curator` |
| `chain` | string | solana, ethereum, base, bsc | `entry_context.chain` |
| `mcap_bucket` | string | <500k, 500k-1m, 1m-2m, 2m-5m, 5m-10m, 10m-50m, 50m+ | `entry_context.mcap_bucket` |
| `vol_bucket` | string | <10k, 10k-50k, 50k-100k, 100k-250k, 250k-500k, 500k-1m, 1m+ | `entry_context.vol_bucket` |
| `age_bucket` | string | <1d, 1-3d, 3-7d, 7-14d, 14-30d, 30-90d, 90d+ | `entry_context.age_bucket` |
| `intent` | string | hi_buy, med_buy, profit, sell, research_positive, etc. | `entry_context.intent` |
| `mapping_confidence` | string | high, med, low | `entry_context.mapping_confidence` |
| `mcap_vol_ratio_bucket` | string | <0.1, 0.1-0.5, 0.5-1.0, 1.0-2.0, 2.0-5.0, 5.0+ | `entry_context.mcap_vol_ratio_bucket` |
| `timeframe` | string | 1m, 15m, 1h, 4h | `position.timeframe` |

**Note**: These are already bucketed in `entry_context` (no additional bucketing needed).

**Action-Level vs Trade-Level Outcomes**:
- **In v1**: Braids are anchored on **trade-level** `outcome_class` (final R/R of the entire position)
- **`did_it_help` field**: Used only for reporting and LLM commentary. Not used as a braiding dimension in v1
- **Future enhancement**: May introduce `action_outcome` as a PM dimension (e.g., `did_help_bucket = helped | neutral | hurt`), allowing braids like `"trim_flag=true, state=S2, did_help=false"`

### PM Dimensions (from `action_context`)

All dimensions are captured **at action time** (when PM executes add/trim/exit).

| Dimension | Type | Buckets | Bucketing Function |
|-----------|------|---------|-------------------|
| `a_bucket` | string | low, med, high | `low: 0-0.3, med: 0.3-0.7, high: 0.7-1.0` |
| `e_bucket` | string | low, med, high | `low: 0-0.3, med: 0.3-0.7, high: 0.7-1.0` |
| `state` | string | S1, S2, S3 | Raw state value |
| `buy_signal` | boolean | true, false | Raw boolean |
| `buy_flag` | boolean | true, false | Raw boolean |
| `first_dip_buy_flag` | boolean | true, false | Raw boolean |
| `trim_flag` | boolean | true, false | Raw boolean |
| `emergency_exit` | boolean | true, false | Raw boolean |
| `reclaimed_ema333` | boolean | true, false | Raw boolean |
| `ts_score_bucket` | string | low, med, high | `low: <0.3, med: 0.3-0.7, high: >0.7` |
| `dx_score_bucket` | string | low, med, high | `low: <0.3, med: 0.3-0.7, high: >0.7` |
| `ox_score_bucket` | string | low, med, high | `low: <0.3, med: 0.3-0.7, high: >0.7` |
| `edx_score_bucket` | string | low, med, high | `low: <0.3, med: 0.3-0.7, high: >0.7` |
| `ema_slopes_bucket` | string | negative, flat, positive | `negative: < -0.001, flat: -0.001 to 0.001, positive: > 0.001` |
| `size_bucket` | string | small, med, large | `small: 0-0.2, med: 0.2-0.5, large: 0.5-1.0` |
| `bars_since_entry_bucket` | string | 0, 1-5, 6-20, 21+ | `0: 0, 1-5: 1-5, 6-20: 6-20, 21+: 21+` |
| `action_type` | string | add, trim, emergency_exit | Raw action type |

**Bucketing Functions** (Python pseudo-code):

```python
def bucket_a_e(score: float) -> str:
    """Bucket A/E score into low/med/high"""
    if score < 0.3:
        return "low"
    elif score < 0.7:
        return "med"
    else:
        return "high"

def bucket_score(score: float) -> str:
    """Bucket engine score (TS/DX/OX/EDX) into low/med/high"""
    if score < 0.3:
        return "low"
    elif score < 0.7:
        return "med"
    else:
        return "high"

def bucket_ema_slopes(slopes: Dict[str, float]) -> str:
    """Bucket EMA slopes into negative/flat/positive"""
    # Use average of all slopes, or check if majority are positive/negative
    avg_slope = sum(slopes.values()) / len(slopes)
    if avg_slope < -0.001:
        return "negative"
    elif avg_slope > 0.001:
        return "positive"
    else:
        return "flat"

def bucket_size(size_frac: float) -> str:
    """Bucket action size into small/med/large"""
    if size_frac < 0.2:
        return "small"
    elif size_frac < 0.5:
        return "med"
    else:
        return "large"

def bucket_bars_since_entry(bars: int) -> str:
    """Bucket bars since entry into timing buckets"""
    if bars == 0:
        return "0"
    elif bars <= 5:
        return "1-5"
    elif bars <= 20:
        return "6-20"
    else:
        return "21+"
```

### Outcome Dimensions (from `completed_trades`)

| Dimension | Type | Buckets | Classification Function |
|-----------|------|---------|------------------------|
| `outcome_class` | string | big_win, big_loss, small_win, small_loss, breakeven | `big_win: R/R > 2.0, big_loss: R/R < -1.0, small_win: 0.5 < R/R <= 2.0, small_loss: -1.0 <= R/R < 0, breakeven: -0.1 < R/R < 0.1` |
| `hold_time_class` | string | short, medium, long | `short: <7d, medium: 7-30d, long: >30d` |

**Classification Functions**:

```python
def classify_outcome(rr: float) -> str:
    """Classify trade outcome based on R/R"""
    if rr > 2.0:
        return "big_win"
    elif rr < -1.0:
        return "big_loss"
    elif rr > 0.5:
        return "small_win"
    elif rr < 0:
        return "small_loss"
    else:
        return "breakeven"

def classify_hold_time(hold_time_days: float) -> str:
    """Classify hold time into short/medium/long"""
    if hold_time_days < 7:
        return "short"
    elif hold_time_days <= 30:
        return "medium"
    else:
        return "long"
```

---

## Pattern Generation

### Dimension Policy (Incremental Edge Does the Filtering)

**Approach**: Start with broader whitelist, let incremental edge scores filter out redundant patterns.

**Why this works**:
- We don't know which dimensions matter until we test them
- Incremental edge check: if a pattern doesn't add value beyond its parents, it's naturally pruned
- Dimensions that never contribute to high-edge patterns will effectively be ignored
- Easier to include and filter than to discover we missed something important

**DM Dimensions** (allowed for braiding):
- `curator`
- `chain`
- `mcap_bucket`
- `age_bucket`
- `intent`
- `mapping_confidence`
- `timeframe` (core signal - 1m vs 4h are very different environments)
- `mcap_vol_ratio_bucket` (could be high signal - low ratio = illiquid = higher risk/reward)

**PM Dimensions** (allowed for braiding):
- `state`
- `a_bucket`
- `e_bucket`
- `buy_flag`
- `trim_flag`
- `action_type`
- `ts_score_bucket`
- `size_bucket`
- `bars_since_entry_bucket`
- `reclaimed_ema333` (could be high signal - "we always win after reclaiming EMA333")
- `first_dip_buy_flag` (could be high signal - "first dips are the best entries")
- `emergency_exit` (boolean flag)
- `dx_score_bucket`, `ox_score_bucket`, `edx_score_bucket` (engine scores)

**Controls** (not dimension exclusion):
- Max subset size: K=3 (patterns up to 3 dimensions)
- Outcome as required dimension: All patterns must include `outcome_class`
- Patterns are always of the form: "(context subset) + outcome_class"
- Incremental edge check: Patterns with `incremental_edge <= 0` are redundant
- Minimum sample size: Patterns need `n >= n_min` to be considered
- Edge score threshold: Patterns need `|edge_raw| >= edge_min` to become lessons

### Generate All Subsets Up to Size K

For a trade with context vector, generate all pattern keys (all subsets up to size K=3).

**Input**: Context dict with bucketed dimensions
**Output**: List of pattern keys

**Note**: Apply dimension whitelist before generating patterns.

# Dimension whitelists (broader - incremental edge will filter out what doesn't matter)
ALLOWED_DM_DIMS = {
    'curator', 'chain', 'mcap_bucket', 'age_bucket', 'intent', 
    'mapping_confidence', 'timeframe', 'mcap_vol_ratio_bucket'
}
ALLOWED_PM_DIMS = {
    'state', 'a_bucket', 'e_bucket', 'buy_flag', 'trim_flag', 'action_type', 
    'ts_score_bucket', 'size_bucket', 'bars_since_entry_bucket',
    'reclaimed_ema333', 'first_dip_buy_flag', 'emergency_exit',
    'dx_score_bucket', 'ox_score_bucket', 'edx_score_bucket'
}

def generate_pattern_keys(context: Dict[str, Any], module: str, k: int = 3) -> List[str]:
    """
    Generate all pattern keys (all subsets up to size K) from context.
    
    Args:
        context: Dict with bucketed dimension values
        module: 'dm' or 'pm' (determines which dimensions are allowed)
        k: Maximum subset size (default 3)
    
    Returns:
        List of pattern keys (sorted, delimited strings)
    """
    from itertools import combinations
    
    # Get allowed dimensions for this module
    allowed_dims = ALLOWED_DM_DIMS if module == 'dm' else ALLOWED_PM_DIMS
    
    # Filter: only allowed dimensions, non-None values, exclude outcome (added separately)
    outcome_dims = {'outcome_class', 'hold_time_class'}
    dims = {
        k: v for k, v in context.items() 
        if k in allowed_dims and v is not None and k not in outcome_dims
    }
    
    # Require outcome_class
    if 'outcome_class' not in context:
        return []  # No patterns without outcome
    
    outcome = context['outcome_class']
    pattern_keys = []
    
    # Generate all subsets of size 1, 2, ..., k
    for size in range(1, k + 1):
        for combo in combinations(dims.items(), size):
            # Sort by dimension name for consistency
            sorted_combo = sorted(combo, key=lambda x: x[0])
            # Create pattern key: "module=pm|dim1=val1|...|outcome_class=big_win"
            pattern_key = "|".join([f"{k}={v}" for k, v in sorted_combo])
            pattern_key = f"{pattern_key}|outcome_class={outcome}"  # Always include outcome
            pattern_keys.append(f"module={module}|{pattern_key}")
    
        # Also add outcome alone (still namespace with module)
        pattern_keys.append(f"module={module}|outcome_class={outcome}")
    
    return pattern_keys

# Example:
context = {
    'outcome_class': 'big_win',
    'state': 'S1',
    'a_bucket': 'med',
    'buy_flag': True
}

# Generates:
# 1D: "state=S1", "a_bucket=med", "buy_flag=True", "outcome_class=big_win"
# 2D: "state=S1|a_bucket=med", "state=S1|buy_flag=True", "a_bucket=med|buy_flag=True", ...
# 3D: "state=S1|a_bucket=med|buy_flag=True", ...
# Plus all with outcome_class appended
```

### Compute Family ID

```python
def compute_family_id(context: Dict[str, Any], module: str = 'pm') -> str:
    """
    Compute family_id from core dimensions.
    
    For PM: module|action_type|state|outcome_class
    For DM: module|curator|chain|outcome_class
    """
    if module == 'pm':
        core_dims = {
            'module': module,
            'action_type': context.get('action_type'),
            'state': context.get('state'),
            'outcome_class': context.get('outcome_class')
        }
    else:  # DM
        core_dims = {
            'module': module,
            'curator': context.get('curator'),
            'chain': context.get('chain'),
            'outcome_class': context.get('outcome_class')
        }
    
    # Sort keys for consistency
    sorted_items = sorted([(k, v) for k, v in core_dims.items() if v is not None])
    return '|'.join([f"{k}={v}" for k, v in sorted_items])
```

### Compute Parent Keys

```python
def compute_parent_keys(pattern_key: str) -> List[str]:
    """
    Compute all parent pattern keys (all (k-1) subsets).
    
    Args:
        pattern_key: Pattern key like "big_win|state=S1|A=med|buy_flag=true"
    
    Returns:
        List of parent pattern keys
    """
    from itertools import combinations
    
    # Parse pattern key into dimensions
    dims = pattern_key.split('|')
    
    if len(dims) <= 1:
        return []  # No parents for 1D patterns
    
    # Generate all (k-1) subsets
    parent_keys = []
    for combo in combinations(dims, len(dims) - 1):
        parent_key = "|".join(sorted(combo))  # Sort for consistency
        parent_keys.append(parent_key)
    
    return parent_keys

# Example:
pattern_key = "module=pm|outcome_class=big_win|state=S1|A=med|buy_flag=true"
# Parents:
# "module=pm|outcome_class=big_win|state=S1|A=med"
# "module=pm|outcome_class=big_win|state=S1|buy_flag=true"
# "big_win|A=med|buy_flag=true"
# "state=S1|A=med|buy_flag=true"
```

---

## Streaming Stats Update

### Update Braid Stats (ON CONFLICT DO UPDATE)

When a new trade closes, update all matching braids.

```python
def update_braid_stats(
    sb_client,
    pattern_key: str,
    module: str,
    dimensions: Dict[str, Any],
    rr: float,
    is_win: bool,
    hold_time_days: float,
    family_id: str,
    parent_keys: List[str]
):
    """
    Update braid stats using streaming aggregation (Welford's algorithm).
    
    Args:
        sb_client: Supabase client
        pattern_key: Pattern key (e.g., "big_win|state=S1|A=med")
        dimensions: Dimension values (JSONB)
        rr: R/R value for this trade
        is_win: Whether this trade was a win (R/R > 0)
        hold_time_days: Hold time in days
        family_id: Family ID
        parent_keys: List of parent pattern keys
    """
    # Compute new stats (using Welford's algorithm for streaming variance)
    # For first trade (n=0), we'll insert
    # For subsequent trades, we'll update
    
    # Get current stats (if exists)
    result = sb_client.table('learning_braids').select('stats').eq('pattern_key', pattern_key).execute()
    
    if result.data:
        # Update existing braid
        current_stats = result.data[0]['stats']
        n = current_stats.get('n', 0)
        sum_rr = current_stats.get('sum_rr', 0.0)
        sum_rr_squared = current_stats.get('sum_rr_squared', 0.0)
        sum_hold_time = current_stats.get('sum_hold_time_days', 0.0)
        wins = current_stats.get('wins', 0)
        
        # Update streaming stats
        n_new = n + 1
        sum_rr_new = sum_rr + rr
        sum_rr_squared_new = sum_rr_squared + (rr * rr)
        sum_hold_time_new = sum_hold_time + hold_time_days
        wins_new = wins + (1 if is_win else 0)
        
        # Compute new averages
        avg_rr_new = sum_rr_new / n_new
        avg_hold_time_new = sum_hold_time_new / n_new
        win_rate_new = wins_new / n_new
        
        # Compute variance (using Welford's algorithm)
        # variance = (sum_rr_squared / n) - avg_rr²
        variance_new = (sum_rr_squared_new / n_new) - (avg_rr_new * avg_rr_new)
        
        new_stats = {
            'n': n_new,
            'sum_rr': sum_rr_new,
            'sum_rr_squared': sum_rr_squared_new,
            'avg_rr': avg_rr_new,
            'variance': max(0.0, variance_new),  # Variance can't be negative (rounding errors)
            'win_rate': win_rate_new,
            'avg_hold_time_days': avg_hold_time_new,
            'wins': wins_new,
            'sum_hold_time_days': sum_hold_time_new
        }
        
        # Update row
        sb_client.table('learning_braids').update({
            'stats': new_stats,
            'last_updated': 'now()'
        }).eq('pattern_key', pattern_key).execute()
    else:
        # Insert new braid
        new_stats = {
            'n': 1,
            'sum_rr': rr,
            'sum_rr_squared': rr * rr,
            'avg_rr': rr,
            'variance': 0.0,
            'win_rate': 1.0 if is_win else 0.0,
            'avg_hold_time_days': hold_time_days,
            'wins': 1 if is_win else 0,
            'sum_hold_time_days': hold_time_days
        }
        
        sb_client.table('learning_braids').insert({
            'pattern_key': pattern_key,
            'module': module,  # Explicit module column
            'dimensions': dimensions,
            'stats': new_stats,
            'family_id': family_id,
            'parent_keys': parent_keys,
            'last_updated': 'now()',
            'created_at': 'now()'
        }).execute()
```

---

## Edge Score Calculation

### Segmented Baseline (Not Global R/R)

**Problem**: A 50k mcap, 1m token and BTC on 4h are different universes. Use segmented baselines.

**Solution**: Compare patterns against segment baseline by `(mcap_bucket, timeframe)`.

```python
def get_rr_baseline(
    sb_client,
    module: str,
    context: Dict[str, Any]
) -> float:
    """
    Get R/R baseline for a segment (mcap_bucket + timeframe).
    
    Falls back hierarchically: segment → mcap-only → timeframe-only → global
    
    Args:
        sb_client: Supabase client
        module: 'dm' or 'pm'
        context: Context with mcap_bucket and timeframe
    
    Returns:
        Baseline R/R for this segment
    """
    mcap_bucket = context.get('mcap_bucket')
    timeframe = context.get('timeframe')
    
    N_MIN_SEG = 10  # Minimum samples for segment baseline
    N_MIN_LOOSE = 5  # Minimum samples for fallback baselines
    
    # 1) Try segment baseline (mcap + timeframe)
    if mcap_bucket and timeframe:
        rr_seg, n_seg = lookup_baseline(sb_client, module, mcap_bucket, timeframe)
        if n_seg >= N_MIN_SEG:
            return rr_seg
    
    # 2) Fall back to looser segments
    candidates = []
    
    if mcap_bucket:
        rr_mcap, n_mcap = lookup_baseline_mcap(sb_client, module, mcap_bucket)
        if n_mcap >= N_MIN_LOOSE:
            candidates.append((rr_mcap, n_mcap))
    
    if timeframe:
        rr_tf, n_tf = lookup_baseline_timeframe(sb_client, module, timeframe)
        if n_tf >= N_MIN_LOOSE:
            candidates.append((rr_tf, n_tf))
    
    if candidates:
        # Weighted average of available fallbacks
        total_n = sum(n for _, n in candidates)
        rr_combined = sum(rr * n for rr, n in candidates) / total_n
        return rr_combined
    
    # 3) Fall back to global
    return get_global_rr(sb_client, module)
```

### Compute Edge Score

```python
def compute_edge_score(
    avg_rr: float,
    variance: float,
    n: int,
    rr_baseline: float  # Segment baseline, not global
) -> float:
    """
    Compute edge score for a braid pattern.
    
    Formula: edge_raw = (rr_p - rr_baseline) * coherence * log(1+n)
    where coherence = 1 / (1 + variance)
    
    Args:
        avg_rr: Average R/R for this pattern
        variance: Variance of R/R for this pattern
        n: Sample size
        rr_baseline: Segment baseline R/R (mcap_bucket + timeframe)
    
    Returns:
        Edge score (positive = good, negative = bad)
    """
    delta_rr = avg_rr - rr_baseline
    coherence = 1.0 / (1.0 + variance)  # Low variance = high coherence
    support = math.log(1 + n)  # Diminishing returns on sample size
    
    edge_raw = delta_rr * coherence * support
    return edge_raw
```

### Compute Incremental Edge

```python
def compute_incremental_edge(
    sb_client,
    pattern_key: str,
    edge_raw: float
) -> float:
    """
    Compute incremental edge vs parents.
    
    incremental_edge = edge_raw(child) - max(edge_raw(parents))
    
    If incremental_edge <= 0, the extra dimension doesn't add value.
    If incremental_edge > 0, the recombination is valuable.
    """
    # Get parent keys
    result = sb_client.table('learning_braids').select('parent_keys').eq('pattern_key', pattern_key).execute()
    if not result.data or not result.data[0].get('parent_keys'):
        return edge_raw  # No parents, so full edge is incremental
    
    parent_keys = result.data[0]['parent_keys']
    
    # Get edge scores for all parents
    parent_edges = []
    for parent_key in parent_keys:
        parent_result = sb_client.table('learning_braids').select('stats').eq('pattern_key', parent_key).execute()
        if parent_result.data:
            parent_stats = parent_result.data[0]['stats']
            # Get segment baseline for parent (same segment as child)
            parent_context = parent_result.data[0].get('dimensions', {})
            rr_baseline = get_rr_baseline(sb_client, module, {
                'mcap_bucket': parent_context.get('mcap_bucket'),
                'timeframe': parent_context.get('timeframe')
            })
            parent_edge = compute_edge_score(
                parent_stats['avg_rr'],
                parent_stats['variance'],
                parent_stats['n'],
                rr_baseline
            )
            parent_edges.append(parent_edge)
    
    if not parent_edges:
        return edge_raw  # No valid parents
    
    max_parent_edge = max(parent_edges)
    incremental_edge = edge_raw - max_parent_edge
    return incremental_edge
```

---

## Lesson Builder

### Lesson Lifecycle

**Status transitions**:

**Candidate → Active**:
- When `n >= N_promote` (e.g., 20) **and**
- `edge_raw > edge_promote` (e.g., 0.5) **and**
- Still positive over last `M` occurrences (e.g., last 10 trades)

**Active → Deprecated**:
- When over last `M_deprecate` trades (e.g., 20) where the lesson fired:
  - `edge_recent < 0` or `edge_recent < threshold` (e.g., 0.2)

**Deprecated → (archived/deleted)**:
- After some time period (e.g., 30 days) with no reactivation

### Build Lessons from Braids

```python
def build_lessons_from_braids(
    sb_client,
    module: str = 'pm',
    n_min: int = 10,
    edge_min: float = 0.5,
    incremental_min: float = 0.1,
    max_lessons_per_family: int = 3
):
    """
    Build lessons from braids by:
    1. Filtering candidates (n >= n_min, |edge_raw| >= edge_min)
    2. Grouping by family
    3. Choosing representative patterns (prefer simpler when possible)
    4. Creating lesson rows
    
    Args:
        sb_client: Supabase client
        module: 'pm' or 'dm'
        n_min: Minimum sample size
        edge_min: Minimum edge score
        incremental_min: Minimum incremental edge vs parents
        max_lessons_per_family: Maximum lessons per family
    """
    # Note: Edge scores use segment baselines (computed per pattern)
    
    # Get all braids for this module
    braids = sb_client.table('learning_braids').select('*').execute().data
    
    # Filter candidates
    candidates = []
    for braid in braids:
        stats = braid['stats']
        n = stats['n']
        avg_rr = stats['avg_rr']
        variance = stats['variance']
        
        # Get segment baseline (mcap_bucket + timeframe)
        rr_baseline = get_rr_baseline(sb_client, module, {
            'mcap_bucket': braid.get('mcap_bucket'),  # From dimensions or context
            'timeframe': braid.get('timeframe')
        })
        
        # Compute edge score
        edge_raw = compute_edge_score(avg_rr, variance, n, rr_baseline)
        
        # Filter
        if n >= n_min and abs(edge_raw) >= edge_min:
            incremental_edge = compute_incremental_edge(sb_client, braid['pattern_key'], edge_raw)
            candidates.append({
                'braid': braid,
                'edge_raw': edge_raw,
                'incremental_edge': incremental_edge
            })
    
    # Group by family
    families = {}
    for candidate in candidates:
        family_id = candidate['braid']['family_id']
        if family_id not in families:
            families[family_id] = []
        families[family_id].append(candidate)
    
    # Build lessons per family
    for family_id, family_candidates in families.items():
        # Sort by edge_raw (strongest first)
        family_candidates.sort(key=lambda x: abs(x['edge_raw']), reverse=True)
        
        selected_patterns = []
        
        for candidate in family_candidates:
            if len(selected_patterns) >= max_lessons_per_family:
                break
            
            braid = candidate['braid']
            edge_raw = candidate['edge_raw']
            incremental_edge = candidate['incremental_edge']
            
            # If incremental edge is too small, prefer parent
            if incremental_edge <= incremental_min:
                # Check if parent is in candidates
                parent_keys = braid.get('parent_keys', [])
                # Find best parent that's also a candidate
                best_parent = None
                for parent_key in parent_keys:
                    parent_candidate = next(
                        (c for c in candidates if c['braid']['pattern_key'] == parent_key),
                        None
                    )
                    if parent_candidate and parent_candidate not in selected_patterns:
                        if best_parent is None or abs(parent_candidate['edge_raw']) > abs(best_parent['edge_raw']):
                            best_parent = parent_candidate
                
                if best_parent:
                    if best_parent not in selected_patterns:
                        selected_patterns.append(best_parent)
                    continue
            
            # This pattern is valuable - add it
            if candidate not in selected_patterns:
                selected_patterns.append(candidate)
        
        # Create lesson rows
        for selected in selected_patterns:
            braid = selected['braid']
            edge_raw = selected['edge_raw']
            
            # Convert edge to multiplier
            edge_scale = 20.0  # Tuning parameter: edge_raw=20 → +10%
            mult = 1.0 + max(-0.10, min(0.10, edge_raw / edge_scale))
            
            # Check if should promote to active (lifecycle rules)
            n = braid['stats']['n']
            edge_promote = 0.5
            n_promote = 20
            
            status = 'active' if (n >= n_promote and edge_raw > edge_promote) else 'candidate'
            
            # Create lesson
            lesson = {
                'module': module,
                'trigger': braid['dimensions'],
                'effect': {
                    'size_multiplier' if module == 'pm' else 'alloc_multiplier': mult
                },
                'stats': {
                    'edge_raw': edge_raw,
                    'incremental_edge': selected['incremental_edge'],
                    'n': n,
                    'avg_rr': braid['stats']['avg_rr'],
                    'family_id': family_id
                },
                'status': status,
                'created_at': 'now()'
            }
            
            # Insert or update lesson
            # Check if lesson with same trigger exists
            existing = sb_client.table('learning_lessons').select('id').eq('module', module).eq('trigger', braid['dimensions']).execute()
            if existing.data:
                # Update
                sb_client.table('learning_lessons').update(lesson).eq('id', existing.data[0]['id']).execute()
            else:
                # Insert
                sb_client.table('learning_lessons').insert(lesson).execute()
```

---

## Integration Hooks

### PM Integration: Fetch and Apply Lessons

```python
def get_matching_lessons(
    sb_client,
    module: str,
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Get all active lessons that match the current context.
    
    Uses subset matching: lesson trigger must be subset of context.
    Returns most specific match (highest dimensional match).
    """
    # Get all active lessons for this module
    lessons = sb_client.table('learning_lessons').select('*').eq('module', module).eq('status', 'active').execute().data
    
    matching_lessons = []
    for lesson in lessons:
        trigger = lesson['trigger']
        # Check if trigger is subset of context
        if all(k in context and context[k] == v for k, v in trigger.items()):
            matching_lessons.append(lesson)
    
    # Sort by specificity (most dimensions first)
    matching_lessons.sort(key=lambda l: len(l['trigger']), reverse=True)
    
    return matching_lessons

def apply_lessons_to_action_size(
    sb_client,
    base_size_frac: float,
    context: Dict[str, Any]
) -> float:
    """
    Apply lessons to action size (PM).
    
    Uses most specific match (highest dimensional match).
    """
    lessons = get_matching_lessons(sb_client, 'pm', context)
    
    if not lessons:
        return base_size_frac
    
    # Use most specific match (first in sorted list)
    lesson = lessons[0]
    multiplier = lesson['effect'].get('size_multiplier', 1.0)
    
    # Apply multiplier (already clamped in lesson creation)
    final_size = base_size_frac * multiplier
    
    # Clamp to reasonable bounds (safety check)
    final_size = max(0.0, min(1.0, final_size))
    
    return final_size

# Usage in plan_actions_v4():
def plan_actions_v4_with_lessons(position, a_final, e_final, phase_meso, sb_client):
    # ... existing logic ...
    
    # Compute base size
    base_size_frac = compute_base_size(a_final, e_final, ...)
    
    # Build context for lesson matching
    context = {
        'state': uptrend.get('state'),
        'a_bucket': bucket_a_e(a_final),
        'e_bucket': bucket_a_e(e_final),
        'buy_flag': uptrend.get('buy_flag', False),
        'action_type': 'add',  # or 'trim', 'emergency_exit'
        # ... other dimensions ...
    }
    
    # Apply lessons
    final_size_frac = apply_lessons_to_action_size(sb_client, base_size_frac, context)
    
    # Use final_size_frac in action
    action = {
        'decision_type': 'add',
        'size_frac': final_size_frac,
        # ...
    }
```

### DM Integration: Fetch and Apply Lessons

```python
def apply_lessons_to_allocation(
    sb_client,
    base_allocation_pct: float,
    context: Dict[str, Any]
) -> float:
    """
    Apply lessons to allocation (DM).
    
    Uses most specific match (highest dimensional match).
    """
    lessons = get_matching_lessons(sb_client, 'dm', context)
    
    if not lessons:
        return base_allocation_pct
    
    # Use most specific match
    lesson = lessons[0]
    multiplier = lesson['effect'].get('alloc_multiplier', 1.0)
    
    # Apply multiplier
    final_allocation = base_allocation_pct * multiplier
    
    # Clamp to reasonable bounds
    final_allocation = max(0.0, min(100.0, final_allocation))
    
    return final_allocation

# Usage in _calculate_allocation():
def _calculate_allocation_with_lessons(self, curator_score, intent_analysis, token_data, sb_client):
    # ... existing logic ...
    
    # Compute base allocation
    base_allocation = compute_base_allocation(curator_score, ...)
    
    # Build context for lesson matching
    context = {
        'curator': token_data.get('curator'),
        'chain': token_data.get('chain'),
        'mcap_bucket': self.bucket_vocab.get_mcap_bucket(token_data.get('market_cap')),
        'intent': intent_analysis.get('intent_type'),
        # ... other dimensions ...
    }
    
    # Apply lessons
    final_allocation = apply_lessons_to_allocation(sb_client, base_allocation, context)
    
    return final_allocation
```

---

## 8. LLM Learning Layer (Build from Day 1, Phased Enablement)

### 8.1 Overview

**Strategy**: Build all infrastructure from Day 1, enable features gradually based on data availability.

**Enablement Flags**:
```python
LLM_ENABLEMENT = {
    'level_1_commentary': True,        # Enable from Day 1
    'level_2_semantic_features': True,  # Enable from Day 1
    'level_3_family_optimization': False,  # Enable after 50+ trades
    'level_4_semantic_compression': False,  # Enable after 100+ trades
    'level_5_hypothesis_generation': False  # Enable after 10+ trades
}
```

### 8.2 Database Schema

```sql
CREATE TABLE llm_learning (
    id SERIAL PRIMARY KEY,
    kind TEXT NOT NULL,  -- 'hypothesis' | 'report' | 'semantic_tag' | 'family_proposal' | 'semantic_pattern'
    level INTEGER NOT NULL,  -- 1-5 (which LLM level generated this)
    module TEXT,         -- 'dm' | 'pm' | 'global'
    status TEXT NOT NULL,  -- 'hypothesis' | 'validated' | 'rejected' | 'active' | 'deprecated'
    content JSONB NOT NULL,  -- Kind-specific structure
    test_results JSONB,     -- Auto-test results (if kind='hypothesis' or 'family_proposal')
    created_at TIMESTAMPTZ DEFAULT NOW(),
    validated_at TIMESTAMPTZ,
    notes TEXT
);

CREATE INDEX idx_llm_learning_kind_status ON llm_learning(kind, status);
CREATE INDEX idx_llm_learning_module ON llm_learning(module);
CREATE INDEX idx_llm_learning_level ON llm_learning(level);
```

### 8.3 Level 1: Commentary + Interpretation

**Status**: ✅ Enable from Day 1

**Implementation**:

```python
def generate_commentary_report(
    sb_client,
    module: str = 'pm',
    time_window_days: int = 30
) -> Dict[str, Any]:
    """
    Generate natural-language commentary on braids and lessons.
    
    Args:
        sb_client: Supabase client
        module: 'pm' or 'dm'
        time_window_days: How far back to analyze
    
    Returns:
        Report dict to store in llm_learning table
    """
    # Get recent braids and lessons
    braids = sb_client.table('learning_braids').select('*').execute().data
    lessons = sb_client.table('learning_lessons').select('*').eq('module', module).eq('status', 'active').execute().data
    
    # Build prompt for LLM
    prompt = f"""
    Analyze the following trading patterns and provide natural-language insights:
    
    Recent Braids (last {time_window_days} days):
    {format_braids_for_llm(braids)}
    
    Active Lessons:
    {format_lessons_for_llm(lessons)}
    
    Provide:
    1. Summary of strongest patterns
    2. Notable regime shifts
    3. Anomalies or contradictions
    4. Qualitative interpretation of what the system is learning
    """
    
    # Call LLM (using your LLM client)
    llm_response = llm_client.generate(prompt)
    
    # Store report
    report = {
        'kind': 'report',
        'level': 1,
        'module': module,
        'status': 'active',
        'content': {
            'type': 'commentary',
            'summary': llm_response,
            'time_window_days': time_window_days,
            'braids_analyzed': len(braids),
            'lessons_analyzed': len(lessons)
        }
    }
    
    sb_client.table('llm_learning').insert(report).execute()
    return report
```

### 8.4 Level 2: Semantic Dimension Extraction

**Status**: ✅ Enable from Day 1

**Implementation**:

```python
def extract_semantic_tags(
    sb_client,
    position_id: str,
    token_data: Dict[str, Any],
    curator_message: str
) -> List[Dict[str, Any]]:
    """
    Extract semantic tags from token/curator data.
    
    Args:
        sb_client: Supabase client
        position_id: Position ID
        token_data: Token information
        curator_message: Original curator message
    
    Returns:
        List of semantic tag dicts
    """
    # Build prompt for LLM
    prompt = f"""
    Extract semantic features from this token mention:
    
    Token: {token_data.get('token_name')}
    Curator Message: {curator_message}
    Chain: {token_data.get('chain')}
    
    Extract semantic tags such as:
    - Narrative tags: "AI narrative", "memecoin revival", "L2 rotation", "DEX meta"
    - Style tags: "insider-coded tweet", "urgent tone", "catalyst reference"
    - Project tags: "has roadmap", "no team", "trending on CT"
    
    Return JSON array of tags with confidence scores.
    """
    
    # Call LLM
    llm_response = llm_client.generate(prompt)
    tags = json.loads(llm_response)
    
    # Store each tag as hypothesis
    stored_tags = []
    for tag in tags:
        tag_record = {
            'kind': 'semantic_tag',
            'level': 2,
            'module': 'dm',  # Or 'pm' depending on context
            'status': 'hypothesis',
            'content': {
                'tag': tag['name'],
                'confidence': tag['confidence'],
                'extracted_from': ['curator_message', 'token_name'],
                'applies_to': [position_id],
                'reasoning': tag.get('reasoning', '')
            }
        }
        sb_client.table('llm_learning').insert(tag_record).execute()
        stored_tags.append(tag_record)
    
    return stored_tags
```

### 8.5 Level 3: Family Core Optimization

**Status**: ⏸️ Enable after 50+ closed trades

**Implementation**:

```python
def propose_family_optimization(
    sb_client,
    module: str = 'pm'
) -> List[Dict[str, Any]]:
    """
    Propose new family core definitions based on observed patterns.
    
    Args:
        sb_client: Supabase client
        module: 'pm' or 'dm'
    
    Returns:
        List of family proposal dicts
    """
    # Get all braids for this module
    braids = sb_client.table('learning_braids').select('*').execute().data
    
    # Group by current family_id
    families = {}
    for braid in braids:
        family_id = braid['family_id']
        if family_id not in families:
            families[family_id] = []
        families[family_id].append(braid)
    
    # Build prompt for LLM
    prompt = f"""
    Analyze these braid families and propose better groupings:
    
    Current Families:
    {format_families_for_llm(families)}
    
    Propose:
    1. Should any families be merged? (e.g., S1 and S2 behave similarly)
    2. Should any families be split? (e.g., state needs more granularity)
    3. Should new dimensions be added to family core? (e.g., timing, volatility regime)
    
    Return JSON array of proposals with reasoning.
    """
    
    # Call LLM
    llm_response = llm_client.generate(prompt)
    proposals = json.loads(llm_response)
    
    # Store proposals
    stored_proposals = []
    for proposal in proposals:
        proposal_record = {
            'kind': 'family_proposal',
            'level': 3,
            'module': module,
            'status': 'hypothesis',
            'content': {
                'current_family_core': proposal['current'],
                'proposed_family_core': proposal['proposed'],
                'reasoning': proposal['reasoning'],
                'affected_braids': proposal.get('affected_braid_keys', [])
            }
        }
        sb_client.table('llm_learning').insert(proposal_record).execute()
        stored_proposals.append(proposal_record)
    
    return stored_proposals

def validate_family_proposal(
    sb_client,
    proposal_id: int
) -> bool:
    """
    Math layer validates family proposal.
    
    Returns True if proposal should be accepted.
    """
    proposal = sb_client.table('llm_learning').select('*').eq('id', proposal_id).execute().data[0]
    content = proposal['content']
    
    # Test: Does merged/split family have better edge?
    # (Implementation details: query braids, compute edge scores, compare)
    
    # If validated → update family_id for affected braids
    if validated:
        # Update braids with new family_id
        # Update proposal status to 'validated'
        pass
    
    return validated
```

### 8.6 Level 4: Semantic Pattern Compression

**Status**: ⏸️ Enable after 100+ closed trades

**Implementation**:

```python
def propose_semantic_patterns(
    sb_client,
    family_id: str
) -> List[Dict[str, Any]]:
    """
    Propose semantic patterns that compress multiple braids.
    
    Args:
        sb_client: Supabase client
        family_id: Family to analyze
    
    Returns:
        List of semantic pattern proposals
    """
    # Get all braids in this family
    braids = sb_client.table('learning_braids').select('*').eq('family_id', family_id).execute().data
    
    # Build prompt for LLM
    prompt = f"""
    Analyze these braids in family {family_id} and propose semantic patterns:
    
    Braids:
    {format_braids_for_llm(braids)}
    
    Find conceptual patterns that span multiple dimensional combinations.
    For example: "momentum_reclaim", "early_entry_opportunity", "resistance_breakout"
    
    Return JSON array of semantic patterns with:
    - pattern_name
    - components (which braids it includes)
    - conceptual_summary
    - proposed_trigger (semantic dimension)
    """
    
    # Call LLM
    llm_response = llm_client.generate(prompt)
    patterns = json.loads(llm_response)
    
    # Store patterns
    stored_patterns = []
    for pattern in patterns:
        pattern_record = {
            'kind': 'semantic_pattern',
            'level': 4,
            'module': 'pm',  # Or 'dm'
            'status': 'hypothesis',
            'content': {
                'semantic_pattern': pattern['pattern_name'],
                'components': pattern['components'],
                'conceptual_summary': pattern['summary'],
                'proposed_trigger': pattern['trigger'],
                'family_id': family_id
            }
        }
        sb_client.table('llm_learning').insert(pattern_record).execute()
        stored_patterns.append(pattern_record)
    
    return stored_patterns
```

### 8.7 Level 5: Hypothesis Auto-Generation

**Status**: ✅ Enable after 10+ closed trades

**Implementation**:

```python
def generate_hypotheses(
    sb_client,
    module: str = 'pm'
) -> List[Dict[str, Any]]:
    """
    Generate hypotheses for new patterns, bucket boundaries, interactions.
    
    Args:
        sb_client: Supabase client
        module: 'pm' or 'dm'
    
    Returns:
        List of hypothesis dicts
    """
    # Get recent braids and lessons
    braids = sb_client.table('learning_braids').select('*').execute().data
    lessons = sb_client.table('learning_lessons').select('*').eq('module', module).execute().data
    
    # Build prompt for LLM
    prompt = f"""
    Analyze these patterns and propose new hypotheses to test:
    
    Recent Braids:
    {format_braids_for_llm(braids)}
    
    Current Lessons:
    {format_lessons_for_llm(lessons)}
    
    Propose:
    1. New interaction patterns to test (e.g., "Test rising OX + falling EDX")
    2. New bucket boundaries (e.g., "Test age<2d vs age<7d split")
    3. New semantic dimensions (e.g., "Test volatility regime")
    
    Return JSON array of hypotheses with test queries.
    """
    
    # Call LLM
    llm_response = llm_client.generate(prompt)
    hypotheses = json.loads(llm_response)
    
    # Store hypotheses
    stored_hypotheses = []
    for hypothesis in hypotheses:
        hypothesis_record = {
            'kind': 'hypothesis',
            'level': 5,
            'module': module,
            'status': 'hypothesis',
            'content': {
                'type': hypothesis['type'],  # 'interaction_pattern' | 'bucket_boundary' | 'semantic_dimension'
                'proposal': hypothesis['proposal'],
                'reasoning': hypothesis['reasoning'],
                'test_query': hypothesis.get('test_query', '')
            }
        }
        sb_client.table('llm_learning').insert(hypothesis_record).execute()
        stored_hypotheses.append(hypothesis_record)
    
    return stored_hypotheses

def auto_test_hypothesis(
    sb_client,
    hypothesis_id: int
) -> Dict[str, Any]:
    """
    Math layer auto-tests hypothesis against historical data.
    
    Returns test results dict.
    """
    hypothesis = sb_client.table('llm_learning').select('*').eq('id', hypothesis_id).execute().data[0]
    content = hypothesis['content']
    
    # Execute test query or pattern matching
    # Compute: avg_rr, n, p-value, etc.
    
    test_results = {
        'avg_rr': 1.9,
        'n': 8,
        'p_value': 0.03,
        'statistically_significant': True
    }
    
    # Update hypothesis with test results
    sb_client.table('llm_learning').update({
        'test_results': test_results,
        'status': 'validated' if test_results['statistically_significant'] else 'rejected'
    }).eq('id', hypothesis_id).execute()
    
    return test_results
```

### 8.8 LLM Execution Flow

```python
def process_llm_layer(
    sb_client,
    position_closed_strand: Dict[str, Any],
    enablement_flags: Dict[str, bool]
):
    """
    Main entry point for LLM layer processing.
    
    Args:
        sb_client: Supabase client
        position_closed_strand: Strand from PM when position closes
        enablement_flags: Which LLM levels are enabled
    """
    module = position_closed_strand.get('module', 'pm')
    
    # Level 1: Commentary (always enabled from Day 1)
    if enablement_flags.get('level_1_commentary', False):
        generate_commentary_report(sb_client, module)
    
    # Level 2: Semantic Features (always enabled from Day 1)
    if enablement_flags.get('level_2_semantic_features', False):
        # Extract semantic tags from position data
        position_id = position_closed_strand.get('position_id')
        token_data = position_closed_strand.get('token_data', {})
        curator_message = position_closed_strand.get('curator_message', '')
        extract_semantic_tags(sb_client, position_id, token_data, curator_message)
    
    # Level 5: Hypothesis Generation (enable after 10+ trades)
    if enablement_flags.get('level_5_hypothesis_generation', False):
        hypotheses = generate_hypotheses(sb_client, module)
        # Auto-test each hypothesis
        for hypothesis in hypotheses:
            auto_test_hypothesis(sb_client, hypothesis['id'])
    
    # Level 3: Family Optimization (enable after 50+ trades)
    if enablement_flags.get('level_3_family_optimization', False):
        proposals = propose_family_optimization(sb_client, module)
        # Validate each proposal
        for proposal in proposals:
            validate_family_proposal(sb_client, proposal['id'])
    
    # Level 4: Semantic Compression (enable after 100+ trades)
    if enablement_flags.get('level_4_semantic_compression', False):
        # Get all families
        families = sb_client.table('learning_braids').select('DISTINCT family_id').execute().data
        for family in families:
            propose_semantic_patterns(sb_client, family['family_id'])
```

---

## Implementation Status

### ✅ Completed

1. **✅ Database tables** - Created all schemas:
   - `learning_braids` - Pattern statistics
   - `learning_lessons` - Compressed rules
   - `llm_learning` - LLM layer outputs
   - `learning_baselines` - Segmented baselines
   - RLS policies configured

2. **✅ Data collection** - Enhanced `completed_trades`:
   - Full `action_context` captured for each action
   - Outcome classification (`outcome_class`, `hold_time_class`)
   - Bucketing functions implemented (`braiding_helpers.py`)

3. **✅ Pattern generation** - Implemented in `braiding_system.py`:
   - `generate_pattern_keys()` - Generates all subsets up to K=3
   - `compute_family_id()` - Computes family IDs
   - `compute_parent_keys()` - Computes parent pattern keys
   - Boolean values properly converted to strings

4. **✅ Streaming stats update** - Implemented:
   - `update_braid_stats()` - Uses Welford's algorithm for streaming aggregation
   - ON CONFLICT DO UPDATE pattern (insert or update)
   - Updates `n`, `sum_rr`, `sum_rr_squared`, `avg_rr`, `variance`, `win_rate`, `avg_hold_time_days`

5. **✅ Baseline updates** - Implemented:
   - `update_baseline_stats()` - Updates segmented baselines
   - Updates segment (mcap+timeframe), timeframe-only, and global baselines
   - Uses streaming aggregation

6. **✅ Edge score calculation** - Implemented:
   - `get_rr_baseline()` - Hierarchical fallback (segment → mcap → timeframe → global)
   - `compute_edge_score()` - Edge = (rr_p - rr_baseline) * coherence * log(1+n)
   - `compute_incremental_edge()` - Compares child vs parents

7. **✅ Integration** - Wired into learning system:
   - `process_position_closed_for_braiding()` called from `UniversalLearningSystem._process_position_closed_strand()`
   - Processes both PM and DM braiding
   - Handles errors gracefully (doesn't break coefficient updates)

8. **✅ Lesson builder** - Implemented:
   - `build_lessons_from_braids()` - Filters candidates, groups by family, creates lessons
   - Handles incremental edge vs parents
   - Promotes to 'active' based on lifecycle rules
   - Creates/updates lesson rows

9. **✅ Lesson matching** - Implemented:
   - `get_matching_lessons()` - Subset matching on triggers
   - `apply_lessons_to_action_size()` - PM integration (async)
   - `apply_lessons_to_allocation()` - DM integration (async)

### ⏸️ Next Steps

1. **✅ Periodic lesson builder job** - Created `braiding_lesson_builder.py`:
   - `run_lesson_builder()` - Runs for a single module
   - `run_all_modules()` - Runs for both PM and DM
   - Can be called standalone or scheduled
   - Returns count of lessons created/updated

2. **✅ Integrate lesson matching into PM** - Wired into `plan_actions_v4()`:
   - `_apply_lessons_sync()` - Synchronous wrapper for async lesson matching
   - Integrated into all action types (add, trim, reclaimed_ema333)
   - Builds context from position/uptrend data
   - Applies lesson multiplier to base size before finalizing
   - Full exits (emergency_exit) skip lesson matching (always 100%)

3. **✅ Integrate lesson matching into DM** - Wired into allocation calculation:
   - Integrated into `_calculate_allocation_with_curator()` and `_calculate_allocation()`
   - Builds context from `entry_context` (curator, chain, mcap_bucket, vol_bucket, age_bucket, intent, etc.)
   - Calls `apply_lessons_to_allocation()` after learned_multiplier is applied
   - Applies lesson multiplier to allocation before final clamping
   - Handles errors gracefully (falls back to allocation without lessons)

4. **✅ LLM layer infrastructure** - Built all 5 levels (phased enablement):
   - `LLMLearningLayer` class with all 5 levels implemented
   - Level 1: Commentary + Interpretation (Day 1) - `generate_commentary_report()`
   - Level 2: Semantic Dimension Extraction (Day 1) - `extract_semantic_tags()`
   - Level 3: Family Core Optimization (50+ trades) - `propose_family_optimization()` + `validate_family_proposal()`
   - Level 4: Semantic Pattern Compression (100+ trades) - `propose_semantic_patterns()`
   - Level 5: Hypothesis Auto-Generation (10+ trades) - `generate_hypotheses()` + `auto_test_hypothesis()`
   - Enablement flags system (defaults: Level 1 & 2 enabled, others disabled)
   - Integrated into `UniversalLearningSystem` (processes on position_closed strands)
   - All outputs stored in `llm_learning` table
   - Math layer validation for Level 3 and Level 5 proposals

5. **⏸️ Testing and validation**:
   - Test with real closed trades
   - Validate pattern generation
   - Validate edge scores
   - Monitor baseline updates
   - Test LLM layer outputs and validation

See [BRAIDING_SYSTEM_DESIGN.md](./BRAIDING_SYSTEM_DESIGN.md) for high-level design and priorities.

