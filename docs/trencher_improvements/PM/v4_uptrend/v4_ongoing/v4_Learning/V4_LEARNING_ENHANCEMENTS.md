# v4 Learning System - Enhancement Ideas

**Status**: Design Document - Potential Enhancements for Future Versions

**Purpose**: This document captures enhancement ideas and concepts discussed for improving the v4 learning system. These are **not yet implemented** but represent valuable directions for future development.

**Related Documents**:
- [LEARNING_SYSTEM_V4.md](./LEARNING_SYSTEM_V4.md) - Current system implementation
- [BRAIDING_SYSTEM_DESIGN.md](./BRAIDING_SYSTEM_DESIGN.md) - Braiding system architecture
- [BRAIDING_IMPLEMENTATION_GUIDE.md](./BRAIDING_IMPLEMENTATION_GUIDE.md) - Implementation details

---

## Table of Contents

1. [Time Efficiency (Time to Payback)](#1-time-efficiency-time-to-payback)
2. [Counterfactual Learning](#2-counterfactual-learning)
3. [Field Coherence (Regime Stability)](#3-field-coherence-regime-stability)
4. [Recursive Depth (Pattern Recurrence)](#4-recursive-depth-pattern-recurrence)
5. [Emergence Detection](#5-emergence-detection)
6. [Integration Strategy](#6-integration-strategy)
7. [Meta-Learning Layers (Renaissance-Level Enhancements)](#7-meta-learning-layers-renaissance-level-enhancements)

---

## 1. Time Efficiency (Time to Payback)

### 1.1 The Problem

**Current state**: Edge scores only consider R/R vs baseline, not **how quickly** that edge materializes.

**Why it matters**:
- A 2R trade in 6 hours may be **better** than a 5R trade in 10 days
- Shorter trades reduce exposure to volatility, noise, liquidation cascades, narrative shifts
- PM tends to prefer fast patterns that prove themselves quickly

**What we care about**:
- **Time to payback**: How quickly did the trade de-risk and start paying us?
- **Not** entry→exit duration: Long-running trends with many adds/trims are often ideal (we've pulled principal, riding house money)

### 1.2 Definition: Time to Payback

**Time to payback** = Number of bars from **first meaningful allocation** → **first time trade hits +1R unrealized**

**Why this works**:
- If trend takes off fast → small number → **good**
- If trade grinds around, dips, faffs about before ever getting +1R → large number → **bad**
- If it never reaches +1R → set `time_to_payback = hold_time` (or a big cap)

**We don't care** about final RR or how long the whole story lasted in this metric. We care about:
> "How quickly did this behavior prove itself?"

### 1.3 Time Efficiency Score

From `time_to_payback`, derive a **bounded score** in [0, 1]:

```python
time_efficiency = 1 / (1 + time_to_payback_days)
```

**Definition of "first meaningful allocation"**: The first time cumulative `size_frac ≥ X%` (e.g., 20–30%), so we don't count tiny probe entries as the "start" for time_to_payback. This ensures we measure when we've actually committed meaningful capital, not just initial test positions.

**Properties**:
- Always between 0 and 1
- Strongly rewards fast payback
- Doesn't explode or require complex tuning

**Examples**:
- `time_to_payback = 0.2 days` → `time_efficiency ≈ 0.83`
- `time_to_payback = 3 days` → `time_efficiency ≈ 0.25`
- `time_to_payback = 10 days` → `time_efficiency ≈ 0.09`

### 1.4 Storage in Stats

Add to `learning_braids.stats`:

```json
{
  "n": 23,
  "sum_rr": 52.9,
  "avg_rr": 2.3,
  "variance": 0.5,
  "win_rate": 0.87,
  "avg_hold_time_days": 4.8,
  "avg_time_to_payback_days": 1.7,  // NEW
  "time_efficiency": 0.42             // NEW
}
```

### 1.5 Integration into Edge Formula

**Current edge formula**:
```python
edge_raw = (avg_rr - baseline_rr) * coherence * log(1 + n)
```

**Enhanced with time**:
```python
time_weight = 0.5 + 0.5 * time_efficiency
edge_raw = (avg_rr - baseline_rr) * coherence * log(1 + n) * time_weight
```

**Why this works**:
- Time can **halve** the perceived value of slow, sludgey patterns (`time_weight = 0.5`)
- Time can **fully credit** fast patterns (`time_weight = 1.0`)
- But it doesn't dominate R/R or variance - it's a **bias**, not the king

**Tuning**: If we want stronger preference for fast patterns:
```python
time_weight = 0.3 + 0.7 * time_efficiency  # More tilt toward speed
```

### 1.6 Implementation Notes

**Where to compute**:
- When position closes, compute `time_to_payback` from OHLCV data
- Track: first entry timestamp → first bar where unrealized R/R >= 1.0
- Store in `completed_trades` JSONB

**Where to aggregate**:
- In `update_braid_stats()`, track `sum_time_to_payback_days` and compute `avg_time_to_payback_days`
- Compute `time_efficiency` per braid (average across trades in pattern)

**Where to use**:
- In `compute_edge_score()`, multiply by `time_weight` derived from braid's `time_efficiency`

**Status**: ✅ Implemented in `pm/braiding_system.py` (time_to_payback_days, time_efficiency, time_weight)

---

## 2. Counterfactual Learning

### 2.1 Current State

**What we compute** (already in trade summary):
- `could_enter_better`: Best entry price, timestamp, signals, missed R/R
- `could_exit_better`: Best exit price, timestamp, signals, missed R/R

**What we're NOT doing**:
- Using counterfactuals as **pattern dimensions** in braiding
- Creating **counterfactual braids** (patterns that consistently show improvement opportunities)
- Using counterfactuals to create **action-sequence lessons** (delay add by N bars, reduce trimming, etc.)

### 2.2 Counterfactual Dimensions

Add new outcome dimensions to braiding:

**Entry improvement buckets**:
- `cf_entry_improvement_bucket`: `none` | `small` | `medium` | `large`
  - `none`: 0-0.5R improvement available
  - `small`: 0.5-1.0R improvement
  - `medium`: 1-2R improvement
  - `large`: 2R+ improvement

**Exit improvement buckets**:
- `cf_exit_improvement_bucket`: `none` | `small` | `medium` | `large` (same thresholds)

**Classification function**:
```python
def bucket_cf_improvement(missed_rr: float) -> str:
    """Bucket counterfactual improvement"""
    if missed_rr < 0.5:
        return "none"
    elif missed_rr < 1.0:
        return "small"
    elif missed_rr < 2.0:
        return "medium"
    else:
        return "large"
```

### 2.3 Counterfactual Braids

These become **dimensions** in braiding, same as `state`, `a_bucket`, etc.

**Example patterns**:
- `"S1|buy_flag=True|cf_entry_improvement=large"` → "We consistently enter too early in S1 with buy_flag"
- `"trim_flag=True|edx_score_bucket=high|cf_exit_improvement=large"` → "We trim too early when EDX is high"
- `"state=S1|a_bucket=med|cf_entry_improvement=medium"` → "Slight timing improvements available in this pattern"

**What this tells us**:
- "This action consistently leaves money on the table"
- "This trim is too early in these contexts"
- "This add is too early, and later the engine screamed to enter"

### 2.4 Counterfactual Lessons

Lesson builder can create lessons such as:

**Delay lessons**:
- **Trigger**: `{state: S1, a_bucket: med, buy_flag: true, cf_entry_improvement: large}`
- **Effect**: `{delay_bars: 3}` or `{size_multiplier: 0.95}` (slightly smaller initial add)

**Hold lessons**:
- **Trigger**: `{trim_flag: true, e_bucket: high, ox_score_bucket: high, cf_exit_improvement: large}`
- **Effect**: `{trim_multiplier: 0.9}` (reduce trimming in these contexts)

**Wait-for-confirmation lessons**:
- **Trigger**: `{state: S1, first_dip_buy_flag: false, cf_entry_improvement: medium}`
- **Effect**: `{wait_for_confirmation: true}` or threshold adjustments

### 2.5 Sequence Learning

From `action_sequence` with `did_it_help` flags, we can braid **sequences**:

**Sequence patterns**:
- `"add (bars_since_entry=0) → trim (E=high) → rebuy (DX high)"`
- `"add early + add early again"` → **always bad**
- `"trim late"` → **good for S1/S2 but bad for S3**

**Sequence braids**:
- `sequence_pattern`: `"add→trim→add"`
- `sequence_success`: `avg(rr_contribution)` across all trades with this sequence
- `sequence_consistency`: `variance / support`

**Implementation**:
- Store `sequence_pattern` as a dimension
- Braid sequences the same way we braid single-action dimensions
- Create lessons for optimal sequences

### 2.6 Implementation Notes

**Where to compute**:
- Already computed in trade summary (`could_enter_better`, `could_exit_better`)
- Add bucketing when trade closes
- Store in `completed_trades` JSONB

**Where to use**:
- Add `cf_entry_improvement_bucket` and `cf_exit_improvement_bucket` to allowed PM dimensions
- Generate patterns including these dimensions
- Create lessons that adjust timing/thresholds based on counterfactual patterns

**Status**: ✅ Implemented (`pm_core_tick.py` stores counterfactuals, braiding uses buckets)

**Future enhancement**:
- LLM layer can propose "what if we did X instead of Y" hypotheses
- Backtest engine can test those hypotheses
- Math validates and converts to lessons if significant

---

## 3. Field Coherence (Regime Stability)

### 3.1 The Concept

**Field coherence φ** = "How stable is this pattern across different environments?"

**The question**:
- Does the pattern work only on microcaps/1m?
- Does it also work on 4h majors?
- Does it work only in high-volatility markets?
- Does it disappear during chop?

**This is NOT variance** - variance is *within* a pattern. Field coherence is "does this pattern survive environment shifts?"

**Important context**: The system **already uses segment baselines** (mcap_bucket + timeframe) for edge calculation. Each pattern is compared against its segment baseline (e.g., a pattern in "microcap/1m" is compared to the average R/R for all trades in "microcap/1m"). Field coherence φ asks a **different question**: "If we look at the same *core behavior* pattern across *different* segments, does it consistently outperform its local baseline in multiple environments?"

### 3.2 Pattern vs Field Dimensions

**Split dimensions into two types**:

#### Core / Behavioral Dimensions (Pattern Core)
These describe **how we act** and what the internal engine sees:
- `state` (S1/S2/S3)
- `a_bucket`, `e_bucket`
- `buy_flag`, `first_dip_buy_flag`, `trim_flag`, `emergency_exit`
- `ts_score_bucket`, `dx_score_bucket`, `ox_score_bucket`, `edx_score_bucket`
- slopes bucket, size bucket, bars_since_entry bucket
- `action_type` (add / trim / emergency_exit)

These are **the "shape" of the behavior**.

#### Field / Environment Dimensions (Field φ)
These describe **where and when** it happens:
- `timeframe` (1m, 15m, 1h, 4h)
- `mcap_bucket` (micro / small / mid / large)
- `age_bucket` (<1d, 1-3d, 3-7d, …)
- `chain`
- macro / meso / micro regime (risk-on vs neutral vs risk-off, vol regime, etc.)

These are **the field the pattern lives in**.

### 3.3 Field Coherence Calculation

**Simple approach**:

1. **Define field segments**: For PM, e.g.:
   - 4 segments by timeframe (1m / 15m / 1h / 4h)
   - 3-4 segments by mcap_bucket (micro/small/mid/large)
   - Maybe 2-3 age buckets

2. **For a given core pattern**, look at all segments where it appears

3. **For each segment `s`** where we have enough data:
   ```python
   edge_s = rr_pattern_in_s - rr_segment_baseline_s
   ```
   
   **Note**: `rr_segment_baseline_s` is the EWMA R/R baseline for that specific segment (mcap_bucket + timeframe) for this module. This is already computed and stored in the `learning_baselines` table. The system uses `get_rr_baseline()` which falls back hierarchically: segment (mcap+timeframe) → mcap-only → timeframe-only → global.

4. **Define field coherence φ**:
   ```python
   φ = (# segments where edge_s has same sign and decent magnitude) / (# segments where pattern appears)
   ```
   
   Or smoothed version:
   ```python
   φ = average(tanh(edge_s / scale)) over segments
   ```

5. **Use φ as multiplier** on edge_raw when deciding which patterns to promote to lessons

**Result**:
- Pattern amazing in **one tiny slice** but never shows up elsewhere → **φ small** (even if edge is high in that one slice)
- Pattern modest but **consistently positive across slices** → **φ large** (more trustworthy)

**Support for φ (how many segments)**: Patterns with φ=1.0 but only tested in 1 segment should be downweighted. Consider:
```python
segments_tested = k  # Number of segments where pattern appears
field_coherence_multiplier = (0.5 + 0.5 * φ) * (0.5 + 0.5 * tanh(segments_tested / 3))
```

So:
- φ = 1.0, but `segments_tested = 1` → multiplier is still < 1.0 (less trustworthy)
- φ = 0.7, `segments_tested = 5` → multiplier close to full (more trustworthy)

### 3.4 Example

**Core pattern**: `state=S1, a_bucket=med, buy_flag=true`

**Field slices**:
- Slice A: `timeframe=15m, mcap_bucket≈$1m, age<3d` → `edge = +1.2`
- Slice B: `timeframe=1h, mcap_bucket≈$50m, age>30d` → `edge = +0.8`
- Slice C: `timeframe=4h, BTC, age>365d` → `edge = -0.3`

**Field coherence**: 2 out of 3 segments positive → `φ = 0.67`

**vs. another pattern**:
- Slice A: `edge = +2.5` (only appears here)
- No other segments → `φ = 1.0` (but only one segment, so less trustworthy)

### 3.5 Integration into Edge

**Current edge formula**:
```python
edge_raw = (avg_rr - baseline_rr) * coherence * log(1 + n)
```

**Enhanced with field coherence**:
```python
edge_raw = (avg_rr - baseline_rr) * coherence * log(1 + n) * field_coherence_multiplier
```

Where:
```python
field_coherence_multiplier = 0.5 + 0.5 * φ
```

**Properties**:
- Pattern only works in one segment → `multiplier = 0.5` (halved)
- Pattern works across all segments → `multiplier = 1.0` (full credit)

### 3.6 Implementation Notes

**Current baseline system**:
- ✅ **Already implemented**: `get_rr_baseline()` in `braiding_system.py` uses segment baselines (mcap_bucket + timeframe)
- ✅ **Already stored**: `learning_baselines` table tracks baselines by (module, mcap_bucket, timeframe)
- ✅ **Already used**: Edge scores are computed against segment baselines, not global

**Field coherence adds**:
- Query the **same core pattern** (e.g., `state=S1, a_bucket=med, buy_flag=true`) across **different segments**
- Compare edge scores across segments to compute φ
- This is a **meta-analysis** on top of the existing segment baseline system

**Storage**:
- Add `field_coherence` and `segments_tested` to `learning_braids.stats`
- Compute when building lessons (requires looking across segments)

**Computation**:
- For each braid, query all segments where core pattern appears
- For each segment, compute edge using existing `get_rr_baseline()` for that segment
- Aggregate edge scores across segments into φ score

**When to compute**:
- In `build_lessons_from_braids()`, after computing edge_raw
- Or as separate background job that updates field_coherence periodically

**Status**: ✅ Implemented (braiding system stores `field_coherence`/segment stats and applies multiplier)

---

## 4. Recursive Depth (Pattern Recurrence)

### 4.1 The Concept

**Recursive depth ρ** = "Does this pattern keep working over time?"

A pattern is more trustworthy if:
- It shows up in **braids**
- Then survives into **lessons**
- Then still performs well **AFTER being applied** in live trading

**The idea**: "A pattern that keeps ringing through time is more real."

### 4.2 Calculation: EWMA of Edge Over Time

**Not a simple recurrence count** - use EWMA of edge_raw over time:

```python
recurrence = EWMA(edge_raw) over time
```

**How it works**:
- Track `edge_raw` for each pattern/lesson over time
- Compute EWMA with time constant (e.g., 30 days)
- If edge_raw keeps being positive → ρ grows
- If it decays or flips sign → ρ falls

**Implementation note**: We'll probably track ρ **at the lesson level** first (not per raw braid), because:
- Lessons are what actually get applied in live trading
- It's easier to reason about "this rule kept working" at the lesson level
- We can track how well lessons perform after being promoted to active status

**Storage**:
- Add `recurrence_score` to `learning_lessons.stats` (primary) and optionally `learning_braids.stats`
- Update on each trade that matches the pattern/lesson

### 4.3 Usage

**As multiplier**:
```python
edge_raw = (avg_rr - baseline_rr) * coherence * log(1 + n) * recurrence_multiplier
```

Where:
```python
recurrence_multiplier = 0.5 + 0.5 * tanh(recurrence_score)
```

**As filter**:
- High recurrence → higher chance to become active lesson
- Low recurrence → deprecation candidate

**Lifecycle integration**:
- When promoting candidate → active: check `recurrence_score >= threshold`
- When deprecating active → deprecated: check `recurrence_score < threshold` over last M trades

### 4.4 Implementation Notes

**Storage**:
- Add `recurrence_score` and `last_recurrence_update` to `learning_braids` or `learning_lessons`
- Or track in separate `pattern_recurrence` table with time series

**Computation**:
- On each trade that matches pattern, update EWMA:
  ```python
  alpha = 1 - exp(-delta_t / tau)  # tau = 30 days
  recurrence_new = alpha * edge_raw + (1 - alpha) * recurrence_old
  ```

**When to compute**:
- In `update_braid_stats()`, after computing edge_raw for this trade
- Or in separate background job that processes all patterns

**Status**: ✅ Implemented (`recurrence_score` EWMA stored per braid, multiplier applied during lesson building)

---

## 5. Emergence Detection

### 5.1 The Concept

A pattern is "emergent" when it:
- Has **low sample size** (n small)
- BUT has **very high incremental edge**
- AND **low internal variance**

**This is a seed of a new idea** - not yet proven, but showing strong signal.

### 5.2 Emergence Score

```python
emergence_score = (incremental_edge / (1 + variance)) * (1 / sqrt(max(n, 3)))
```

**Why this works**:
- Strong signal (`incremental_edge` high)
- Low noise (`variance` low)
- Low sample size (`n` small) → `1/sqrt(n)` large

**Properties**:
- Rewards patterns that are:
  - Strong (high incremental edge)
  - Consistent (low variance)
  - New (low n)

**Robustness guard**: The `max(n, 3)` ensures we don't over-weight patterns with n=1 or n=2, which could be single lucky trades. This prevents emergence_score from being inflated by outliers.

### 5.3 Usage

**Do NOT give it full weight in lessons** (too risky), but **track it**.

**When many "emergence seeds" appear in the same region**, that's a powerful sign of:
- Trend changes
- New market regimes
- New token meta (AI coins, revivals, chain rotation)
- New PM behavior patterns

**This is a real predictive insight** - can alert to regime shifts before they're fully proven.

### 5.4 Implementation Notes

**Storage**:
- Add `emergence_score` to `learning_braids.stats`
- Compute when computing incremental_edge

**Computation**:
- In `compute_incremental_edge()`, also compute emergence_score
- Store in braid stats

**Usage**:
- Flag high-emergence patterns for LLM analysis
- Use in reports/commentary to highlight "seeds of new ideas"
- Don't use directly in lesson selection (too risky)

**Status**: ✅ Implemented (emergence_score computed per braid and recorded in lesson stats)

---

## 6. Integration Strategy

### 6.1 Combined Edge Formula

**v4 Enhanced edge formula (fixed weights)**:

```python
# Base components
delta_rr = avg_rr - rr_segment_baseline
coherence = 1 / (1 + variance)
support = log(1 + n)

# Enhancement multipliers (fixed weights)
time_weight = 0.5 + 0.5 * time_efficiency
field_coherence_multiplier = 0.5 + 0.5 * φ
recurrence_multiplier = 0.5 + 0.5 * tanh(recurrence_score)

# Combined edge
edge_raw = delta_rr * coherence * support * time_weight * field_coherence_multiplier * recurrence_multiplier
```

**Properties**:
- Each multiplier can **halve** edge (if pattern is slow, narrow, or decaying)
- Each multiplier can **fully credit** edge (if pattern is fast, broad, and recurring)
- No single multiplier dominates - they work together

**v5 Evolution (adaptive weights - see Section 7)**:
- Weights become **regime-adaptive** via meta-learning
- System learns which multipliers matter most in each market condition
- Formula structure remains the same, but weights are learned, not fixed

### 6.2 Implementation Priority

**Phase 1 (v4.1)**: Time Efficiency
- ✅ Easy to implement (just compute time_to_payback from OHLCV)
- ✅ High value (PM cares about speed)
- ✅ Low risk (just adds multiplier, doesn't change core logic)

**Phase 2 (v4.2)**: Counterfactual Learning
- ⚠️ Medium complexity (need to add dimensions, create new lesson types)
- ✅ High value (learns from mistakes)
- ⚠️ Medium risk (new lesson types need careful integration)

**Phase 3 (v4.3)**: Field Coherence
- ⚠️ Medium complexity (need to query across segments)
- ✅ High value (filters fragile patterns)
- ✅ Low risk (just adds multiplier)

**Phase 4 (v4.4)**: Recursive Depth
- ⚠️ Medium complexity (need EWMA tracking over time)
- ✅ High value (tracks pattern longevity)
- ✅ Low risk (just adds multiplier/filter)

**Phase 5 (v4.5)**: Emergence Detection
- ✅ Low complexity (just compute score)
- ⚠️ Medium value (predictive but not actionable yet)
- ✅ Low risk (just tracking, not used in decisions)

**Phase 6 (v5.1-v5.3)**: Meta-Learning Layers (Renaissance-Level)
- ⚠️ High complexity (requires v4 enhancements to be stable first)
- ✅ Very high value (completes the "learning how to learn" stack)
- ⚠️ Medium risk (meta-learning requires careful validation)
- **Prerequisites**: v4.1-v4.5 must be implemented and validated
- See [Section 7](#7-meta-learning-layers-renaissance-level-enhancements) for details

### 6.3 Data Requirements

**Time Efficiency**:
- Need: OHLCV data with timestamps
- Need: Track first +1R touch
- ✅ Already have: OHLCV data, timestamps

**Counterfactual Learning**:
- ✅ Already have: `could_enter_better`, `could_exit_better` in trade summary
- Need: Bucketing functions
- Need: Add to allowed dimensions

**Field Coherence**:
- ✅ Already have: Segment baselines (mcap_bucket + timeframe)
- Need: Query patterns across segments
- Need: Aggregate edge per segment

**Recursive Depth**:
- Need: Track edge_raw over time per pattern
- Need: EWMA computation
- Need: Time series storage (or periodic snapshots)

**Emergence Detection**:
- ✅ Already have: incremental_edge, variance, n
- Need: Compute emergence_score
- Need: Store in stats

**Meta-Factor Weight Learning (v5.1)**:
- Need: Regime detection system (volatility, trend, market phase, timeframe distribution)
- Need: Track pattern performance by regime
- Need: Compute correlation between meta-factors and outcomes per regime
- Need: Store regime weights in `learning_regime_weights` table

**Alpha Half-Life Modeling (v5.2)**:
- Need: Time series of `edge_raw` per pattern/lesson
- Need: Exponential decay curve fitting
- Need: Store half-life estimates in stats

**Pattern Orthogonalization (v5.3)**:
- Need: Compute correlation matrix of braid match sets
- Need: Clustering algorithm (hierarchical clustering or threshold-based)
- Need: Store latent factors in `learning_latent_factors` table

### 6.4 Schema Changes

**`learning_braids.stats` additions**:
```json
{
  "n": 23,
  "avg_rr": 2.3,
  "variance": 0.5,
  "win_rate": 0.87,
  "avg_hold_time_days": 4.8,
  
  // NEW: Time efficiency
  "avg_time_to_payback_days": 1.7,
  "time_efficiency": 0.42,
  
  // NEW: Field coherence
  "field_coherence": 0.67,
  "segments_tested": 3,
  "segments_positive": 2,
  
  // NEW: Recursive depth
  "recurrence_score": 0.85,
  "last_recurrence_update": "2024-01-15T10:00:00Z",
  
  // NEW: Emergence
  "emergence_score": 0.12,
  "incremental_edge": 0.6
}
```

**`learning_lessons.stats` additions**:
```json
{
  "edge_raw": 3.6,
  "incremental_edge": 0.6,
  "n": 10,
  "avg_rr": 3.2,
  "family_id": "pm|add|S1|big_win",
  
  // NEW: Recurrence (for lessons)
  "recurrence_score": 0.78,
  "last_validated": "2024-01-15T10:00:00Z",
  
  // NEW: Alpha half-life (v5.2)
  "half_life_days": 17.4,
  "decay_rate": 0.04,
  "edge_at_birth": 2.3,
  "edge_current": 1.8,
  "days_since_birth": 25
}
```

**New tables for v5 meta-layers**:

**`learning_regime_weights` table** (v5.1):
```sql
CREATE TABLE learning_regime_weights (
    regime_key TEXT PRIMARY KEY,  -- e.g., "high_vol|narrative_driven|fast_timeframes"
    module TEXT NOT NULL,          -- 'dm' | 'pm'
    meta_factor_weights JSONB NOT NULL,  -- {time_efficiency: 0.8, field_coherence: 0.3, recurrence: 0.5, variance: 0.7}
    n INTEGER DEFAULT 0,          -- Sample count for this regime
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**`learning_latent_factors` table** (v5.3):
```sql
CREATE TABLE learning_latent_factors (
    factor_id SERIAL PRIMARY KEY,
    module TEXT NOT NULL,         -- 'dm' | 'pm'
    pattern_keys TEXT[] NOT NULL,  -- Array of correlated pattern keys
    representative_pattern TEXT NOT NULL,  -- Best pattern in cluster
    correlation_matrix JSONB,     -- Correlation matrix of patterns in factor
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.5 Testing Strategy

**For each enhancement**:
1. **Add computation** (don't use in decisions yet)
2. **Monitor values** (are they reasonable?)
3. **Validate against known patterns** (do high-quality patterns score well?)
4. **Gradually enable** (start with small multiplier weights, increase if beneficial)
5. **A/B test** (compare performance with/without enhancement)

**Success criteria**:
- Patterns that should be good (high R/R, low variance, fast, broad, recurring) score higher
- Patterns that should be bad (low R/R, high variance, slow, narrow, decaying) score lower
- Lesson selection improves (better patterns become active)
- Trading performance improves (lessons are more effective)

---

## 7. Meta-Learning Layers (Renaissance-Level Enhancements)

**Status**: v5 Evolution - Requires v4 enhancements to be stable first

**Purpose**: These are **meta-learners** that learn how to weight the learners. They complete the "Renaissance stack" by making the learning system itself adaptive, not just the patterns.

**Key insight**: The v4 enhancements add multipliers to edge calculation. The v5 meta-layers learn **which multipliers to use** in each regime. This is the difference between pattern learning and learning how to learn patterns.

---

### 7.1 Meta-Factor Weight Learning (Regime-Adaptive Weights)

#### 7.1.1 The Concept

**The problem**: Current edge formula uses **fixed weights** for enhancement multipliers:
- `time_weight = 0.5 + 0.5 * time_efficiency` (always same formula)
- `field_coherence_multiplier = 0.5 + 0.5 * φ` (always same formula)
- `recurrence_multiplier = 0.5 + 0.5 * tanh(recurrence_score)` (always same formula)

**The Renaissance insight**: Different market regimes require different emphasis on different factors.

**Examples**:
- **Fast markets** (high volatility, narrative-driven) → `time_efficiency` should dominate
- **Stable macro** (low volatility, trend-following) → `recurrence` should dominate
- **Narrative-driven cycles** (AI coins, revivals) → `field_coherence` may collapse (micros behave nothing like majors)
- **Chop/consolidation** → `variance` and robustness matter more

**The solution**: Learn which meta-factors matter most **right now**, not always.

#### 7.1.2 Regime Classification

**Define regimes** (can start simple, expand later):

**Volatility regime**:
- `high_vol`: Recent volatility > 90th percentile
- `normal_vol`: 10th-90th percentile
- `low_vol`: < 10th percentile

**Trend regime**:
- `strong_trend`: Clear directional movement
- `chop`: Range-bound, no clear direction
- `transition`: Changing from one state to another

**Market phase**:
- `narrative_driven`: High social activity, new narratives emerging
- `technical_driven`: Price action following technical patterns
- `rotation`: Capital moving between sectors/chains

**Timeframe regime**:
- `fast_timeframes`: 1m, 15m dominant
- `slow_timeframes`: 1h, 4h dominant
- `mixed`: No clear dominance

#### 7.1.3 Learning Meta-Factor Weights

**For each regime**, track which meta-factors correlate with better outcomes:

```python
# For each regime R, track:
# - Which patterns performed best in R
# - What were their meta-factor values (time_efficiency, φ, recurrence, variance, n)
# - Learn: which meta-factors predict success in R

# Example: In "high_vol + narrative_driven" regime
# - Patterns with high time_efficiency → better outcomes
# - Patterns with high field_coherence → worse outcomes (micros vs majors diverge)
# - Patterns with high recurrence → neutral (recent patterns matter more)

# Result: Learned weights for this regime:
regime_weights = {
    'time_efficiency': 0.8,      # High weight
    'field_coherence': 0.3,      # Low weight (regime-specific)
    'recurrence': 0.5,           # Neutral
    'variance': 0.7              # High weight (robustness matters)
}
```

**Update mechanism**:
- Track pattern performance by regime
- Compute correlation between meta-factor values and outcomes per regime
- Update regime weights using EWMA
- Normalize weights so they sum to reasonable range

#### 7.1.4 Adaptive Edge Formula

**Current (v4) - fixed weights**:
```python
time_weight = 0.5 + 0.5 * time_efficiency
field_coherence_multiplier = 0.5 + 0.5 * φ
recurrence_multiplier = 0.5 + 0.5 * tanh(recurrence_score)
```

**Enhanced (v5) - regime-adaptive weights**:
```python
# Detect current regime
current_regime = detect_regime(volatility, trend, market_phase, timeframe_distribution)

# Get learned weights for this regime
regime_weights = get_regime_weights(current_regime)

# Apply regime-adaptive weights
time_weight = regime_weights['time_efficiency'] * time_efficiency
field_coherence_multiplier = regime_weights['field_coherence'] * φ
recurrence_multiplier = regime_weights['recurrence'] * tanh(recurrence_score)
variance_weight = regime_weights['variance'] * coherence  # Can also weight variance differently

# Combined edge (same structure, adaptive weights)
edge_raw = delta_rr * variance_weight * support * time_weight * field_coherence_multiplier * recurrence_multiplier
```

#### 7.1.5 Implementation Notes

**Storage**:
- New table: `learning_regime_weights`
  - Columns: `regime_key` (e.g., "high_vol|narrative_driven|fast_timeframes")
  - Columns: `meta_factor_weights` JSONB: `{time_efficiency: 0.8, field_coherence: 0.3, recurrence: 0.5, variance: 0.7}`
  - Columns: `n` (sample count), `last_updated`

**Computation**:
- On each closed trade, classify regime
- Update regime weights based on which meta-factors correlated with success
- Use EWMA to smooth weight updates

**When to compute**:
- Background job that processes recent trades
- Updates regime weights periodically (e.g., daily)
- Or real-time: update weights on each trade closure

**Fallback**:
- If regime has insufficient data → use default weights (current v4 formula)
- Gradually transition to learned weights as data accumulates

---

### 7.2 Alpha Half-Life Modeling (Decay Curves)

#### 7.2.1 The Concept

**The problem**: We track recurrence (ρ) - "does this pattern keep working?" - but not **how fast it decays**.

**The Renaissance insight**: Every alpha has a lifespan. A 2R pattern that dies immediately is less valuable than a 1R pattern that survives for years.

**What we need**:
- Track `edge_raw` over time for each pattern
- Fit exponential decay curve: `edge(t) = edge_0 * exp(-λ * t)`
- Calculate **half-life**: `t_half = ln(2) / λ`
- Use half-life as another quality signal

#### 7.2.2 Decay Curve Fitting

**Track edge_raw over time**:
- For each pattern/lesson, store time series: `[(timestamp, edge_raw), ...]`
- Fit exponential decay: `edge(t) = edge_0 * exp(-decay_rate * days_since_birth)`

**Calculate half-life**:
```python
half_life_days = ln(2) / decay_rate
```

**Properties**:
- High `decay_rate` → pattern dies fast → lower quality
- Low `decay_rate` → pattern survives long → higher quality
- `half_life_days` = how many days until edge drops to 50% of initial

#### 7.2.3 Integration into Edge

**Add half-life multiplier**:
```python
# Half-life quality score (normalized)
half_life_quality = tanh(half_life_days / 30)  # 30 days = good, 100+ days = excellent

# Add to edge formula
half_life_multiplier = 0.5 + 0.5 * half_life_quality
edge_raw = delta_rr * coherence * support * time_weight * field_coherence_multiplier * recurrence_multiplier * half_life_multiplier
```

**Or use in lesson selection**:
- Patterns with `half_life_days < threshold` → deprecate faster
- Patterns with `half_life_days > threshold` → promote to active faster

#### 7.2.4 Implementation Notes

**Storage**:
- Add to `learning_braids.stats` or `learning_lessons.stats`:
  ```json
  {
    "half_life_days": 17.4,
    "decay_rate": 0.04,
    "edge_at_birth": 2.3,
    "edge_current": 1.8,
    "days_since_birth": 25
  }
  ```

**Computation**:
- Track `edge_raw` time series per pattern
- Periodically fit decay curve (e.g., weekly)
- Update half-life estimates
- Use robust fitting (handle outliers, missing data)

**When to compute**:
- Background job that processes all patterns periodically
- Or on-demand when building lessons

---

### 7.3 Pattern Orthogonalization (Latent Factor Detection)

#### 7.3.1 The Concept

**The problem**: Many patterns are **not independent** - they are shadows of the same underlying phenomenon.

**Example**:
- Pattern A: `state=S1, a_bucket=med, buy_flag=true` → 2.1R
- Pattern B: `state=S1, a_bucket=med, ts_score_bucket=high` → 2.0R
- Pattern C: `state=S1, buy_flag=true, ts_score_bucket=high` → 2.2R

These might all be the **same underlying behavior** (early S1 momentum), just measured differently.

**The Renaissance insight**: Detect latent shared factors and avoid double-counting related patterns.

#### 7.3.2 Co-Occurrence Analysis

**Compute pattern correlation**:
- For each pair of braids, compute correlation of their **match sets** (which trades match each pattern)
- High correlation → patterns are likely measuring the same thing
- Low correlation → patterns are independent

**Clustering**:
- Group highly correlated patterns into **latent factors**
- Each latent factor represents a shared underlying behavior
- Patterns within a factor are redundant (use the best one)

#### 7.3.3 Orthogonalization

**After clustering**:
- Within each latent factor, keep the **best pattern** (highest edge, most samples)
- Mark others as **redundant** (don't create lessons for them)
- Or create a **composite pattern** that represents the latent factor

**Result**:
- Fewer, more independent patterns
- No double-counting of related signals
- Cleaner lesson set

#### 7.3.4 Implementation Notes

**Storage**:
- New table: `learning_latent_factors`
  - Columns: `factor_id`, `pattern_keys` (array of correlated patterns)
  - Columns: `representative_pattern` (best pattern in cluster)
  - Columns: `correlation_matrix` (JSONB)

**Computation**:
- Compute correlation matrix of all braids (which trades match which patterns)
- Apply clustering algorithm (e.g., hierarchical clustering, threshold-based)
- Identify latent factors
- Select representative patterns

**When to compute**:
- Periodic background job (e.g., weekly)
- Or when building lessons (check for redundancy before creating new lessons)

**Integration with lessons**:
- Before creating a lesson, check if pattern is redundant with existing lessons
- If redundant → don't create, or merge with existing lesson
- This prevents "lessons crowding each other out"

---

### 7.4 Integration with v4 Enhancements

**These meta-layers sit above the v4 edge formula**:

```
v4 Layer (Pattern Learning):
├── Compute time_efficiency, φ, recurrence, emergence
├── Apply fixed-weight multipliers
└── Generate edge_raw

v5 Layer (Meta-Learning):
├── Learn regime-adaptive weights (7.1)
├── Track alpha half-life & decay (7.2)
├── Detect latent factors & orthogonalize (7.3)
└── Adjust v4 formula based on meta-insights
```

**Key principle**: v5 doesn't replace v4 - it **learns how to use v4 better**.

---

### 7.5 Implementation Priority

**Phase 6.1 (v5.1)**: Meta-Factor Weight Learning
- ⚠️ High complexity (requires regime detection + correlation analysis)
- ✅ Very high value (adapts learning system to market conditions)
- ⚠️ Medium risk (requires careful validation)

**Phase 6.2 (v5.2)**: Alpha Half-Life Modeling
- ⚠️ Medium complexity (time series tracking + curve fitting)
- ✅ High value (identifies long-lived patterns)
- ✅ Low risk (additive, doesn't change core logic)

**Phase 6.3 (v5.3)**: Pattern Orthogonalization
- ⚠️ Medium complexity (correlation computation + clustering)
- ✅ High value (prevents double-counting, cleaner lessons)
- ✅ Low risk (filters redundant patterns, doesn't break existing)

**Prerequisites**:
- All v4 enhancements (v4.1-v4.5) must be implemented and stable
- Sufficient data (100+ closed trades minimum, ideally 200+)
- Regime detection system (can start simple)

---

## 8. Summary

### 8.1 Key Enhancements

**v4 Enhancements (Pattern Learning)**:
1. **Time Efficiency**: Reward fast payback, penalize slow sludge
2. **Counterfactual Learning**: Learn from "what could have been" to improve timing
3. **Field Coherence**: Filter fragile patterns that only work in one corner
4. **Recursive Depth**: Track pattern longevity, prefer patterns that keep working
5. **Emergence Detection**: Identify seeds of new ideas before they're fully proven

**v5 Meta-Learning Layers (Learning How to Learn)**:
6. **Meta-Factor Weight Learning**: Learn which multipliers matter most in each regime
7. **Alpha Half-Life Modeling**: Track decay curves, identify long-lived patterns
8. **Pattern Orthogonalization**: Detect latent factors, avoid double-counting

### 8.2 Design Principles

**All enhancements**:
- Add **multipliers** to edge, not replacements
- Keep core math (R/R, variance, sample size) as spine
- Each enhancement is a **bias**, not the king
- Easy to tune (adjust multiplier weights)
- Easy to disable (set multiplier to 1.0)

**Integration**:
- Build incrementally (one enhancement at a time)
- Test thoroughly before enabling
- Monitor performance
- Adjust weights based on results

### 8.3 Renaissance Alignment

**What we've built (v4)**:
- Pattern cluster representation (braids)
- Pattern decay tracking (ρ - recurrence)
- Regime segmentation (field coherence φ)
- Frequency and sample weighting (n, log(n))
- Variance suppression
- Outcome-first learning (R/R-based)
- Counterfactual alignment (timing model)
- Meta-structure preserved (families)
- Semantic model layered above structure (LLM)

**What v5 adds (Renaissance completion)**:
- Meta-learning that adapts the learning system itself
- Alpha half-life tracking (decay curves, not just recurrence)
- Pattern orthogonalization (latent factor detection)

**Assessment**: v4 captures ~80-85% of Renaissance's core structure. v5 completes the remaining 15-20% - the meta-learners that learn how to weight the learners.

**The system is designed to grow** - v4 enhancements fit cleanly into existing architecture, and v5 meta-layers sit above v4 without requiring redesign.

---

## 9. References

**Original conversation**: Internal discussion on v4 learning system enhancements

**Related concepts**:
- Resonance principles (field coherence, recursive depth, emergence)
- Time-weighted returns (finance literature)
- Counterfactual analysis (causal inference)
- Regime stability (quantitative finance)
- Renaissance Technologies meta-learning philosophy
- Alpha decay modeling (quantitative finance)
- Signal orthogonalization (factor models)

**Implementation guides**:
- See [BRAIDING_IMPLEMENTATION_GUIDE.md](./BRAIDING_IMPLEMENTATION_GUIDE.md) for current implementation
- See [BRAIDING_SYSTEM_DESIGN.md](./BRAIDING_SYSTEM_DESIGN.md) for architecture

=============

LLM redesign plan for - llm_research_layer.py:

"""
LLM Research Layer – Jim Simons Mode

Core principle:
    The math is the brainstem.
    The LLM is a research assistant that:
        - Reads what the math already knows
        - Names latent factors
        - Proposes re-groupings / hypotheses
        - NEVER overrides statistics
        - NEVER decides trades
        - NEVER validates its own outputs (math layer does that separately)

This file defines a narrow, testable interface for LLM-powered research
on top of the braiding + learning system.

Levels:

    L1 – Edge Landscape Commentary
         "Tell me what changed in the last X days."

    L2 – Semantic Factor Extraction
         "Name latent factors (narratives / styles) that might explain clusters."

    L3 – Family Core Optimization
         "Suggest alternative family cores that should increase out-of-sample robustness."

    L4 – Semantic Pattern Compression
         "Compress many concrete braids into a few conceptual patterns/factors."

    L5 – Hypothesis Auto-Generation
         "Propose strictly testable hypotheses, never conclusions."

All LLM outputs are stored as hypotheses in `llm_learning` and must be
validated by the math layer (edge stats, baselines, significance tests).
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime, timezone

from llm_integration.openrouter_client import OpenRouterClient
from llm_integration.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

ModuleName = Literal["pm", "dm"]

# --------------------------------------------------------------------------
# Configuration + Data Contracts
# --------------------------------------------------------------------------

DEFAULT_ENABLEMENT = {
    "level_1_commentary": True,          # day 1
    "level_2_semantic_factors": True,    # day 1
    "level_3_family_optimization": False,
    "level_4_semantic_compression": False,
    "level_5_hypothesis_generation": False,
}


@dataclass
class BraidStats:
    """Minimal stats the LLM is allowed to see for a braid/pattern."""
    pattern_key: str
    family_id: str
    module: ModuleName
    n: int
    avg_rr: float
    variance: float
    win_rate: float
    rr_baseline: float
    edge_raw: float
    time_efficiency: Optional[float] = None
    field_coherence: Optional[float] = None
    recurrence_score: Optional[float] = None
    emergence_score: Optional[float] = None


@dataclass
class LessonStats:
    """Minimal stats for a lesson (active rule) the LLM can see."""
    lesson_id: str
    module: ModuleName
    family_id: str
    n: int
    avg_rr: float
    edge_raw: float
    recurrence_score: Optional[float] = None


@dataclass
class EdgeLandscapeSnapshot:
    """
    Snapshot for L1 commentary:
    'Tell me how the edge landscape has shifted recently.'
    """
    module: ModuleName
    time_window_days: int
    top_braids: List[BraidStats]
    top_lessons: List[LessonStats]
    timestamp: str


@dataclass
class SemanticFactorTag:
    """
    Output for L2 semantic factor extraction.
    Stored as a hypothesis; math does correlation later.
    """
    name: str
    confidence: float
    reasoning: str
    applies_to_positions: List[str]
    source_fields: List[str]


@dataclass
class FamilyOptimizationProposal:
    """
    Output for L3: "maybe the family core should look like THIS instead."
    """
    current_family_core: str
    proposed_family_core: str
    reasoning: str
    affected_pattern_keys: List[str]


@dataclass
class SemanticPatternProposal:
    """
    Output for L4: conceptual patterns that compress multiple braids.
    """
    pattern_name: str
    components: List[str]  # pattern_keys
    conceptual_summary: str
    proposed_trigger: Dict[str, Any]
    family_id: str


@dataclass
class HypothesisProposal:
    """
    Output for L5: strictly testable hypotheses.
    """
    type: Literal["interaction_pattern", "bucket_boundary", "semantic_dimension", "other"]
    proposal: str
    reasoning: str
    test_query: str  # SQL-ish or pattern-query-ish; math layer interprets


# --------------------------------------------------------------------------
# LLM Research Layer – Jim Simons Style
# --------------------------------------------------------------------------


class LLMResearchLayer:
    """
    Jim-Simons-first LLM layer.

    - It ONLY consumes already-computed statistics.
    - It ONLY produces hypotheses, factors, commentary.
    - All proposals are written to `llm_learning` as 'hypothesis' / 'report'.
    - The math / backtest layer ALWAYS judges them.

    This class should stay thin:
        - Build small, focused prompts.
        - Parse strictly defined JSON schemas.
        - No trading logic lives here.
    """

    def __init__(
        self,
        sb_client,
        llm_client: Optional[OpenRouterClient] = None,
        enablement: Optional[Dict[str, bool]] = None,
    ):
        self.sb = sb_client
        self.llm = llm_client or OpenRouterClient()
        self.prompt_manager = PromptManager()
        self.enablement = {**DEFAULT_ENABLEMENT, **(enablement or {})}

        logger.info(f"LLMResearchLayer initialized with enablement={self.enablement}")

    # ------------------------------------------------------------------
    # Public orchestration
    # ------------------------------------------------------------------

    async def process(
        self,
        module: ModuleName = "pm",
        position_closed_strand: Optional[Dict[str, Any]] = None,
        token_data: Optional[Dict[str, Any]] = None,
        curator_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entrypoint for the LLM research layer.

        Called e.g. when:
          - a position closes, or
          - a periodic cron tick runs.

        It should be CHEAP: if a level is disabled, we do nothing.
        """
        results: Dict[str, Any] = {
            "level_1": None,
            "level_2": None,
            "level_3": None,
            "level_4": None,
            "level_5": None,
        }

        # L1 – commentary on edge landscape
        if self.enablement.get("level_1_commentary", False):
            try:
                results["level_1"] = await self._run_level_1_commentary(module)
            except Exception as e:
                logger.error(f"L1 commentary failed: {e}", exc_info=True)

        # L2 – semantic factors from token / curator data
        if self.enablement.get("level_2_semantic_factors", False) and token_data:
            try:
                position_id = position_closed_strand.get("position_id") if position_closed_strand else None
                results["level_2"] = await self._run_level_2_semantic_factors(
                    module=module,
                    position_id=position_id,
                    token_data=token_data,
                    curator_message=curator_message,
                )
            except Exception as e:
                logger.error(f"L2 semantic factors failed: {e}", exc_info=True)

        # L5 – hypotheses (we often want these earlier than 3/4)
        if self.enablement.get("level_5_hypothesis_generation", False):
            try:
                results["level_5"] = await self._run_level_5_hypotheses(module)
            except Exception as e:
                logger.error(f"L5 hypothesis generation failed: {e}", exc_info=True)

        # L3 – family optimization (heavier, run less often)
        if self.enablement.get("level_3_family_optimization", False):
            try:
                results["level_3"] = await self._run_level_3_family_optimization(module)
            except Exception as e:
                logger.error(f"L3 family optimization failed: {e}", exc_info=True)

        # L4 – semantic compression (heavier, run rarely)
        if self.enablement.get("level_4_semantic_compression", False):
            try:
                results["level_4"] = await self._run_level_4_semantic_compression(module)
            except Exception as e:
                logger.error(f"L4 semantic compression failed: {e}", exc_info=True)

        return results

    # ------------------------------------------------------------------
    # Level 1 – Edge Landscape Commentary
    # ------------------------------------------------------------------

    async def _run_level_1_commentary(self, module: ModuleName, time_window_days: int = 30) -> Dict[str, Any]:
        """
        L1: Given braid + lesson stats, describe how the edge landscape shifted.

        Input:   EdgeLandscapeSnapshot (built from DB).
        Output:  Structured natural-language report stored in `llm_learning`.
        """
        snapshot = await self._build_edge_landscape_snapshot(module, time_window_days)
        if not snapshot.top_braids and not snapshot.top_lessons:
            logger.debug("L1: no data for commentary")
            return {}

        prompt = self._build_l1_prompt(snapshot)
        raw = self.llm.generate_completion(
            prompt=prompt,
            temperature=0.4,
            max_tokens=1600,
        )
        content = raw.get("content", "").strip()

        report_record = {
            "kind": "report",
            "level": 1,
            "module": module,
            "status": "active",
            "content": {
                "type": "edge_landscape_commentary",
                "snapshot": {
                    "time_window_days": time_window_days,
                    "top_braids": [asdict(b) for b in snapshot.top_braids],
                    "top_lessons": [asdict(l) for l in snapshot.top_lessons],
                },
                "summary": content,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self.sb.table("llm_learning").insert(report_record).execute()
        return report_record

    async def _build_edge_landscape_snapshot(
        self,
        module: ModuleName,
        time_window_days: int,
    ) -> EdgeLandscapeSnapshot:
        """
        Pull top braids + lessons with their stats from DB and wrap in typed object.

        This is where we constrain the LLM's view:
          - Only a handful of numeric fields.
          - No raw trades.
          - No direct price series.
        """
        # TODO: filter by time_window_days when you have `updated_at`/`closed_at` in braids/lessons
        braids_res = (
            self.sb.table("learning_braids")
            .select("pattern_key,family_id,module,stats,rr_segment_baseline")
            .eq("module", module)
            .limit(30)
            .execute()
        )
        braids = braids_res.data or []

        lessons_res = (
            self.sb.table("learning_lessons")
            .select("id,family_id,module,stats")
            .eq("module", module)
            .eq("status", "active")
            .limit(20)
            .execute()
        )
        lessons = lessons_res.data or []

        top_braids: List[BraidStats] = []
        for row in braids:
            stats = row.get("stats") or {}
            try:
                top_braids.append(
                    BraidStats(
                        pattern_key=row.get("pattern_key"),
                        family_id=row.get("family_id", "unknown"),
                        module=row.get("module", module),
                        n=int(stats.get("n", 0)),
                        avg_rr=float(stats.get("avg_rr", 0.0)),
                        variance=float(stats.get("variance", 0.0)),
                        win_rate=float(stats.get("win_rate", 0.0)),
                        rr_baseline=float(row.get("rr_segment_baseline", 0.0)),
                        edge_raw=float(stats.get("edge_raw", 0.0)),
                        time_efficiency=stats.get("time_efficiency"),
                        field_coherence=stats.get("field_coherence"),
                        recurrence_score=stats.get("recurrence_score"),
                        emergence_score=stats.get("emergence_score"),
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping braid row in snapshot: {e}")

        top_lessons: List[LessonStats] = []
        for row in lessons:
            stats = row.get("stats") or {}
            try:
                top_lessons.append(
                    LessonStats(
                        lesson_id=str(row.get("id")),
                        module=row.get("module", module),
                        family_id=row.get("family_id", "unknown"),
                        n=int(stats.get("n", 0)),
                        avg_rr=float(stats.get("avg_rr", 0.0)),
                        edge_raw=float(stats.get("edge_raw", 0.0)),
                        recurrence_score=stats.get("recurrence_score"),
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping lesson row in snapshot: {e}")

        return EdgeLandscapeSnapshot(
            module=module,
            time_window_days=time_window_days,
            top_braids=top_braids,
            top_lessons=top_lessons,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _build_l1_prompt(self, snapshot: EdgeLandscapeSnapshot) -> str:
        """
        Jim-Simons-style commentary prompt:
        - Describe which patterns gained/lost edge.
        - Point out regime hints, but never assert certainty.
        """

        def format_b(b: BraidStats) -> str:
            return (
                f"- {b.pattern_key} | family={b.family_id} | "
                f"n={b.n}, avg_rr={b.avg_rr:.2f}, baseline={b.rr_baseline:.2f}, "
                f"edge={b.edge_raw:.2f}, var={b.variance:.2f}, win={b.win_rate:.2f}, "
                f"time_eff={b.time_efficiency}, φ={b.field_coherence}, ρ={b.recurrence_score}, "
                f"⚘={b.emergence_score}"
            )

        def format_l(l: LessonStats) -> str:
            return (
                f"- lesson={l.lesson_id} | family={l.family_id} | "
                f"n={l.n}, avg_rr={l.avg_rr:.2f}, edge={l.edge_raw:.2f}, ρ={l.recurrence_score}"
            )

        braids_block = "\n".join(format_b(b) for b in snapshot.top_braids) or "None."
        lessons_block = "\n".join(format_l(l) for l in snapshot.top_lessons) or "None."

        return f"""
You are an internal research assistant for a quantitative trading system.

You ONLY see statistics already computed by the math layer.
You MUST NOT invent numbers, parameters, or trades.

You are given an "edge landscape" snapshot:
- Each braid is a concrete pattern with:
  - avg_rr: average R/R
  - rr_baseline: baseline R/R for its segment
  - edge_raw: how much it beats baseline
  - variance, win_rate
  - time_efficiency: how fast it pays back
  - field_coherence φ: how broadly it works across regimes
  - recurrence_score ρ: how well it keeps working over time
  - emergence_score ⚘: new but strong/quiet patterns

Your task:
  1. Identify which patterns clearly gained edge vs baseline (strong, consistent, time-efficient, coherent).
  2. Identify which patterns lost edge or look fragile (high variance, low ρ, low φ).
  3. Comment on any hints of macro/meso regime shift (e.g. microcaps improving while majors worsen).
  4. Highlight any "emergent seeds" (high ⚘) that might deserve attention later.

Do NOT propose trades.
Do NOT change parameters.
Speak in cautious, precise language ("it suggests", "it may indicate").

Edge Landscape (module={snapshot.module}, window={snapshot.time_window_days}d):

Top Braids:
{braids_block}

Top Lessons:
{lessons_block}

Now, provide a structured commentary:

1. Strong patterns (with reasons)
2. Weakened patterns (with reasons)
3. Regime hints (if any)
4. Emergent seeds (if any)
5. Suggested questions to test mathematically (not answers)
""".strip()

    # ------------------------------------------------------------------
    # Level 2 – Semantic Factor Extraction
    # ------------------------------------------------------------------

    async def _run_level_2_semantic_factors(
        self,
        module: ModuleName,
        position_id: Optional[str],
        token_data: Dict[str, Any],
        curator_message: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        L2: Extract semantic narrative/style factors from token + curator.

        Output is a list of SemanticFactorTag, each stored as a row in `llm_learning`
        with kind='semantic_factor', status='hypothesis'.
        """
        prompt = self._build_l2_prompt(token_data, curator_message)
        raw = self.llm.generate_completion(
            prompt=prompt,
            temperature=0.4,
            max_tokens=900,
        )
        text = raw.get("content", "")

        tags = self._parse_json_array(text, fallback_key="tags")
        results: List[Dict[str, Any]] = []

        for tag in tags:
            try:
                factor = SemanticFactorTag(
                    name=str(tag.get("name", "unknown")).strip(),
                    confidence=float(tag.get("confidence", 0.5)),
                    reasoning=str(tag.get("reasoning", "")),
                    applies_to_positions=[position_id] if position_id else [],
                    source_fields=["token_data"] + (["curator_message"] if curator_message else []),
                )
            except Exception as e:
                logger.warning(f"Skipping malformed semantic factor tag: {e}")
                continue

            record = {
                "kind": "semantic_factor",
                "level": 2,
                "module": module,
                "status": "hypothesis",
                "content": asdict(factor),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            res = self.sb.table("llm_learning").insert(record).execute()
            if res.data:
                record["id"] = res.data[0].get("id")
            results.append(record)

        return results

    def _build_l2_prompt(self, token_data: Dict[str, Any], curator_message: Optional[str]) -> str:
        """
        Jim version: treat this like factor discovery, not vibe-tagging.
        """
        token_name = token_data.get("token_name") or token_data.get("symbol") or "Unknown"
        chain = token_data.get("chain", "Unknown")
        mcap = token_data.get("market_cap", "Unknown")
        age = token_data.get("age_days", "Unknown")
        extra = json.dumps({k: v for k, v in token_data.items() if k not in ["token_name", "symbol", "chain", "market_cap", "age_days"]}, default=str)  # noqa: E501

        curator_block = f"\nCurator Message:\n{curator_message}\n" if curator_message else ""

        return f"""
You are helping a quantitative trading system label *narrative and style factors*
for a single token mention.

Data:
- Token: {token_name}
- Chain: {chain}
- Market Cap: {mcap}
- Age (days): {age}
- Extra: {extra}{curator_block}

Your task:
  - Propose up to 5 semantic factors that might influence returns over time.
    Examples: "AI narrative", "L2 rotation", "memecoin revival",
              "serious infra project", "celebrity-backed memecoin".
  - Each factor must be:
      - A short name
      - A confidence 0–1
      - A brief reasoning

These factors are HYPOTHESES ONLY.
The math layer will later test if they correlate with edge or not.

Return STRICT JSON, no prose. Format:

[
  {{
    "name": "factor_name",
    "confidence": 0.0-1.0,
    "reasoning": "short explanation"
  }},
  ...
]
""".strip()

    # ------------------------------------------------------------------
    # Level 3 – Family Core Optimization
    # ------------------------------------------------------------------

    async def _run_level_3_family_optimization(self, module: ModuleName) -> List[Dict[str, Any]]:
        """
        L3: Ask the LLM to suggest better family cores (groupings of patterns).
        """
        braids_res = (
            self.sb.table("learning_braids")
            .select("pattern_key,family_id,module,stats,dimensions")
            .eq("module", module)
            .limit(300)
            .execute()
        )
        braids = braids_res.data or []
        if len(braids) < 10:
            logger.info("L3: not enough braids for family optimization")
            return []

        prompt = self._build_l3_prompt(braids)
        raw = self.llm.generate_completion(
            prompt=prompt,
            temperature=0.5,
            max_tokens=2000,
        )
        text = raw.get("content", "")

        proposals_json = self._parse_json_array(text, fallback_key="proposals")
        stored: List[Dict[str, Any]] = []

        for p in proposals_json:
            try:
                proposal = FamilyOptimizationProposal(
                    current_family_core=str(p.get("current_family_core", "")),
                    proposed_family_core=str(p.get("proposed_family_core", "")),
                    reasoning=str(p.get("reasoning", "")),
                    affected_pattern_keys=list(p.get("affected_pattern_keys", [])),
                )
            except Exception as e:
                logger.warning(f"Skipping malformed family proposal: {e}")
                continue

            record = {
                "kind": "family_proposal",
                "level": 3,
                "module": module,
                "status": "hypothesis",
                "content": asdict(proposal),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            res = self.sb.table("llm_learning").insert(record).execute()
            if res.data:
                record["id"] = res.data[0].get("id")
            stored.append(record)

        # math layer will later call a validator to test these proposals numerically
        return stored

    def _build_l3_prompt(self, braids: List[Dict[str, Any]]) -> str:
        """
        L3 prompt: see current families, propose merges/splits/cleaner cores.
        We only care about family core structure, NOT parameter values.
        """
        # very compact summary to avoid prompt bloat
        families: Dict[str, List[Dict[str, Any]]] = {}
        for b in braids:
            fid = b.get("family_id", "unknown")
            families.setdefault(fid, []).append(b)

        lines = []
        for fid, group in list(families.items())[:12]:
            lines.append(f"\nFamily: {fid} (braids={len(group)})")
            for b in group[:3]:
                stats = b.get("stats") or {}
                dims = b.get("dimensions") or {}
                lines.append(
                    f"  - {b.get('pattern_key')} | n={stats.get('n', 0)}, "
                    f"avg_rr={stats.get('avg_rr', 0.0):.2f}, edge={stats.get('edge_raw', 0.0):.2f}, "
                    f"dims={{{k: dims[k] for k in sorted(dims.keys())[:4]}}}"
                )

        families_block = "\n".join(lines)

        return f"""
You see families of trading patterns. Each "family" groups similar braids
(e.g., same state, similar action, similar context).

Goal:
  - Propose changes to the *family cores* that should make patterns more robust
    and easier for the math layer to generalize.
  - Think like a quant: you care about out-of-sample performance,
    not storytelling.

Current families (truncated view):
{families_block}

For each proposal:
  - current_family_core: a short description of what the current family is.
  - proposed_family_core: a short description of the new core (which dims matter).
  - reasoning: why this transformation might improve robustness.
  - affected_pattern_keys: list of pattern_keys that should move / be regrouped.

Return STRICT JSON:

[
  {{
    "current_family_core": "string",
    "proposed_family_core": "string",
    "reasoning": "short explanation",
    "affected_pattern_keys": ["pattern_key_1", "pattern_key_2", ...]
  }},
  ...
]
""".strip()

    # ------------------------------------------------------------------
    # Level 4 – Semantic Pattern Compression
    # ------------------------------------------------------------------

    async def _run_level_4_semantic_compression(self, module: ModuleName) -> List[Dict[str, Any]]:
        """
        L4: For each family, propose 1–3 semantic pattern names that compress multiple braids.
        """
        fam_res = (
            self.sb.table("learning_braids")
            .select("DISTINCT family_id")
            .eq("module", module)
            .execute()
        )
        fam_rows = fam_res.data or []
        family_ids = [r.get("family_id") for r in fam_rows if r.get("family_id")]

        stored: List[Dict[str, Any]] = []

        for fid in family_ids[:8]:
            braids_res = (
                self.sb.table("learning_braids")
                .select("pattern_key,family_id,module,stats,dimensions")
                .eq("family_id", fid)
                .eq("module", module)
                .limit(50)
                .execute()
            )
            braids = braids_res.data or []
            if len(braids) < 5:
                continue

            prompt = self._build_l4_prompt(fid, braids)
            raw = self.llm.generate_completion(
                prompt=prompt,
                temperature=0.5,
                max_tokens=2000,
            )
            text = raw.get("content", "")

            patterns_json = self._parse_json_array(text, fallback_key="patterns")

            for p in patterns_json:
                try:
                    proposal = SemanticPatternProposal(
                        pattern_name=str(p.get("pattern_name", "")),
                        components=list(p.get("components", [])),
                        conceptual_summary=str(p.get("conceptual_summary", "")),
                        proposed_trigger=p.get("proposed_trigger", {}),
                        family_id=fid,
                    )
                except Exception as e:
                    logger.warning(f"Skipping malformed semantic pattern: {e}")
                    continue

                record = {
                    "kind": "semantic_pattern",
                    "level": 4,
                    "module": module,
                    "status": "hypothesis",
                    "content": asdict(proposal),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                res = self.sb.table("llm_learning").insert(record).execute()
                if res.data:
                    record["id"] = res.data[0].get("id")
                stored.append(record)

        return stored

    def _build_l4_prompt(self, family_id: str, braids: List[Dict[str, Any]]) -> str:
        """
        L4: Turn many specific braids in a family into a smaller set of conceptual patterns.
        """
        lines = [f"Family {family_id} – sample braids:"]
        for b in braids[:12]:
            stats = b.get("stats") or {}
            dims = b.get("dimensions") or {}
            lines.append(
                f"- {b.get('pattern_key')} | n={stats.get('n', 0)}, avg_rr={stats.get('avg_rr', 0.0):.2f}, "
                f"edge={stats.get('edge_raw', 0.0):.2f}, dims={dims}"
            )
        braids_block = "\n".join(lines)

        return f"""
You are given multiple braids (concrete patterns) that belong to the same family.

Your task:
  - Identify 1–3 *semantic patterns* that conceptually group several braids.
    Examples: "momentum reclaim after flush", "late-stage parabolic extension",
              "early trend detection with tight invalidation".
  - For each semantic pattern:
      - Give it a short, descriptive name.
      - List which pattern_keys it includes.
      - Summarize what it represents.
      - Suggest a *candidate trigger* in terms of dimensions (a dict).

You are NOT changing any rules; you are naming structure.
The math layer will test these later.

Braids:
{braids_block}

Return STRICT JSON:

[
  {{
    "pattern_name": "string",
    "components": ["pattern_key_1", "pattern_key_2", ...],
    "conceptual_summary": "short explanation",
    "proposed_trigger": {{"dimension_name": "bucket_or_value", "...": "..."}}
  }},
  ...
]
""".strip()

    # ------------------------------------------------------------------
    # Level 5 – Hypothesis Auto-Generation
    # ------------------------------------------------------------------

    async def _run_level_5_hypotheses(self, module: ModuleName) -> List[Dict[str, Any]]:
        """
        L5: Use braids + lessons to generate NEW testable hypotheses.
        """
        braids_res = (
            self.sb.table("learning_braids")
            .select("pattern_key,family_id,module,stats,dimensions")
            .eq("module", module)
            .limit(200)
            .execute()
        )
        braids = braids_res.data or []

        lessons_res = (
            self.sb.table("learning_lessons")
            .select("id,family_id,module,stats,trigger,effect")
            .eq("module", module)
            .limit(50)
            .execute()
        )
        lessons = lessons_res.data or []

        if len(braids) < 5:
            logger.info("L5: not enough braids for hypothesis generation")
            return []

        prompt = self._build_l5_prompt(braids, lessons)
        raw = self.llm.generate_completion(
            prompt=prompt,
            temperature=0.6,
            max_tokens=2000,
        )
        text = raw.get("content", "")

        hyps_json = self._parse_json_array(text, fallback_key="hypotheses")
        stored: List[Dict[str, Any]] = []

        for h in hyps_json:
            try:
                proposal = HypothesisProposal(
                    type=h.get("type", "other"),
                    proposal=str(h.get("proposal", "")),
                    reasoning=str(h.get("reasoning", "")),
                    test_query=str(h.get("test_query", "")),
                )
            except Exception as e:
                logger.warning(f"Skipping malformed hypothesis: {e}")
                continue

            record = {
                "kind": "hypothesis",
                "level": 5,
                "module": module,
                "status": "hypothesis",
                "content": asdict(proposal),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            res = self.sb.table("llm_learning").insert(record).execute()
            if res.data:
                record["id"] = res.data[0].get("id")
            stored.append(record)

        return stored

    def _build_l5_prompt(self, braids: List[Dict[str, Any]], lessons: List[Dict[str, Any]]) -> str:
        """
        L5: generate strictly testable hypotheses; math layer will auto-test.
        """
        def fmt_b(b: Dict[str, Any]) -> str:
            s = b.get("stats") or {}
            d = b.get("dimensions") or {}
            return (
                f"- {b.get('pattern_key')} | family={b.get('family_id')} "
                f"| n={s.get('n', 0)}, avg_rr={s.get('avg_rr', 0.0):.2f}, edge={s.get('edge_raw', 0.0):.2f}, dims={d}"
            )

        def fmt_l(l: Dict[str, Any]) -> str:
            s = l.get("stats") or {}
            return (
                f"- lesson={l.get('id')} | family={l.get('family_id')} "
                f"| n={s.get('n', 0)}, edge={s.get('edge_raw', 0.0):.2f}, trigger={l.get('trigger')}, effect={l.get('effect')}"
            )

        braids_block = "\n".join(fmt_b(b) for b in braids[:25]) or "None."
        lessons_block = "\n".join(fmt_l(l) for l in lessons[:15]) or "None."

        return f"""
You are helping a quant system design new hypotheses to test.

You see:
- Braids: concrete patterns with stats and dimensions.
- Lessons: rules currently in use with their triggers/effects and edge.

Your job:
  - Propose new *testable* hypotheses.
  - Each hypothesis must be something the math layer can check using
    historical completed_trades and braids.

Types of hypotheses:
  - "interaction_pattern": relationship between dimensions
      e.g. "state=S1 AND age<3d AND high OX_score correlates with higher edge"
  - "bucket_boundary": suggestion to change a bucket split
      e.g. "age<2d vs age<7d"
  - "semantic_dimension": suggestion to correlate a semantic factor with edge
      e.g. "AI narrative tokens behave differently in high-vol regimes"
  - "other": anything else, but it must still be testable.

For EACH hypothesis:
  - type: one of the above
  - proposal: human-readable description
  - reasoning: why this might be true, based on patterns you see
  - test_query: pseudo-SQL or pattern query indicating how to test it
      (e.g. SELECT avg_rr FROM completed_trades WHERE state='S1' AND age_bucket='0-3d' ...)

Braids (sample):
{braids_block}

Lessons (sample):
{lessons_block}

Return STRICT JSON:

[
  {{
    "type": "interaction_pattern" | "bucket_boundary" | "semantic_dimension" | "other",
    "proposal": "string",
    "reasoning": "string",
    "test_query": "string"
  }},
  ...
]
""".strip()

    # ------------------------------------------------------------------
    # Helper: Parse JSON safely from LLM
    # ------------------------------------------------------------------

    def _parse_json_array(self, text: str, fallback_key: str) -> List[Dict[str, Any]]:
        """
        Extract a JSON array from an LLM response.

        Handles:
        - ```json ... ```
        - ``` ... ```
        - plain JSON
        - or a top-level dict with a given key pointing to a list.
        """
        if not text:
            return []

        try_strs = []

        # code fence variants
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            try_strs.append(text[start:end].strip())
        if "```" in text and not try_strs:
            start = text.find("```") + 3
            end = text.find("```", start)
            try_strs.append(text[start:end].strip())

        # whole text as fallback
        try_strs.append(text.strip())

        for candidate in try_strs:
            try:
                data = json.loads(candidate)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and fallback_key in data and isinstance(data[fallback_key], list):
                    return data[fallback_key]
            except Exception:
                continue

        logger.warning("Failed to parse LLM JSON array; returning empty list")
        return []
