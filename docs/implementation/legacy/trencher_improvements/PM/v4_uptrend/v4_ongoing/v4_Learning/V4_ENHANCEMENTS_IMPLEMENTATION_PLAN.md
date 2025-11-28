# v4 Learning Enhancements - Implementation Plan & Deep Dive

**Status**: Investigation Complete - Ready for Implementation Planning

**Date**: 2024-01-XX

**Purpose**: This document provides a comprehensive analysis of the v4 learning enhancements, mapping them to the existing codebase, identifying what infrastructure exists, what needs to be built, and assessing implementation complexity.

---

## Executive Summary

**Assessment**: ✅ **The skeleton is already there.** The enhancements are **additive, not revolutionary**. The core infrastructure (braiding system, edge computation, stats aggregation, segment baselines) is solid and extensible.

**Key Findings**:
1. ✅ **Edge computation** (`compute_edge_score`) is already modular - easy to add multipliers
2. ✅ **Stats aggregation** (`update_braid_stats`) uses streaming aggregation - easy to add new fields
3. ✅ **Segment baselines** already exist - field coherence can build on this
4. ✅ **OHLCV data** is accessible - time_to_payback can be computed
5. ⚠️ **Counterfactual data** may need to be computed if not already in `completed_trades`
6. ⚠️ **Time series tracking** for recurrence needs to be added (but straightforward)

**Overall Complexity**: **Low to Medium** - Most enhancements are straightforward additions to existing functions.

---

## 1. Time Efficiency (Time to Payback)

### 1.1 Current State Analysis

**What Exists**:
- ✅ `update_braid_stats()` - Streaming aggregation system (lines 141-239 in `braiding_system.py`)
- ✅ `completed_trades` JSONB in `lowcap_positions` table - Can store time_to_payback
- ✅ OHLCV data access via `lowcap_price_data_ohlc` table
- ✅ Position timestamps: `first_entry_timestamp`, `closed_at` in positions table
- ✅ `avg_hold_time_days` already tracked in braid stats

**What's Missing**:
- ❌ `time_to_payback` calculation (first +1R touch)
- ❌ `time_efficiency` score computation
- ❌ `sum_time_to_payback_days` in braid stats
- ❌ `time_weight` multiplier in `compute_edge_score()`

### 1.2 Implementation Complexity: **LOW**

**Why it's easy**:
1. **OHLCV data is accessible**: We can query `lowcap_price_data_ohlc` between `first_entry_timestamp` and `closed_at`
2. **Calculation is straightforward**: Find first bar where `(price - entry_price) / entry_price >= 1.0` (or use R/R calculation)
3. **Stats aggregation is ready**: `update_braid_stats()` already tracks `sum_hold_time_days` - just add `sum_time_to_payback_days`
4. **Edge formula is modular**: `compute_edge_score()` can easily accept a `time_weight` parameter

**Implementation Steps**:
1. **Add calculation function** (new function):
   ```python
   async def compute_time_to_payback(
       sb_client,
       position_id: int,
       entry_timestamp: str,
       entry_price: float,
       closed_at: str,
       timeframe: str
   ) -> float:
       """Compute time_to_payback in days from OHLCV data"""
   ```

2. **Update `update_braid_stats()`** (modify existing):
   - Add `sum_time_to_payback_days` to stats
   - Compute `avg_time_to_payback_days = sum_time_to_payback_days / n`
   - Compute `time_efficiency = 1 / (1 + avg_time_to_payback_days)`

3. **Update `compute_edge_score()`** (modify existing):
   - Add optional `time_efficiency` parameter
   - Compute `time_weight = 0.5 + 0.5 * time_efficiency`
   - Multiply edge_raw by time_weight

4. **Update `process_position_closed_for_braiding()`** (modify existing):
   - Call `compute_time_to_payback()` when processing trade
   - Pass `time_to_payback` to `update_braid_stats()`

**Files to Modify**:
- `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py` (3 functions)
- `src/database/learning_braids_schema.sql` (no schema change needed - JSONB stats can hold new fields)

**Risk Level**: **LOW** - Additive only, doesn't change core logic

---

## 2. Counterfactual Learning

### 2.1 Current State Analysis

**What Exists**:
- ✅ `completed_trades` JSONB structure supports storing counterfactual data
- ✅ Trade summary structure (from `BRAIDING_SYSTEM_DESIGN.md`) mentions `could_enter_better` and `could_exit_better`
- ✅ `ALLOWED_PM_DIMS` in `braiding_system.py` (line 28-33) - can add new dimensions
- ✅ Pattern generation system (`generate_pattern_keys`) - can include counterfactual dimensions

**What's Missing**:
- ❌ **Counterfactual computation NOT implemented**: `could_enter_better` and `could_exit_better` are NOT currently computed (verified via code search)
- ❌ `cf_entry_improvement_bucket` and `cf_exit_improvement_bucket` bucketing function
- ❌ Counterfactual dimensions in `ALLOWED_PM_DIMS`
- ❌ Counterfactual-based lessons (delay lessons, hold lessons)

### 2.2 Implementation Complexity: **MEDIUM**

**Why it's medium**:
1. **Counterfactual computation needed**: `could_enter_better` and `could_exit_better` are NOT currently computed - need to add this
2. **New dimension types**: Adding counterfactual dimensions requires updating pattern generation
3. **New lesson types**: Counterfactual lessons (delay, hold) are different from size multiplier lessons

**Investigation Complete**:
- ✅ Verified: Counterfactual analysis is NOT computed in `pm_core_tick.py` (lines 923-939)
- ✅ Trade summary currently includes: entry/exit prices, R/R, max_drawdown, max_gain, but NOT counterfactuals
- ✅ Need to add counterfactual computation when position closes (use OHLCV data)

**Implementation Steps**:
1. **Add counterfactual computation** (new functionality):
   - When position closes, compute `could_enter_better` and `could_exit_better` from OHLCV
   - Query OHLCV data between `first_entry_timestamp` and `closed_at`
   - Find best entry price (lowest price) and best exit price (highest price)
   - Compute missed R/R for each
   - Store in `completed_trades` JSONB (add to trade_summary)

2. **Add bucketing function** (new function):
   ```python
   def bucket_cf_improvement(missed_rr: float) -> str:
       """Bucket counterfactual improvement: none/small/medium/large"""
   ```

3. **Update `ALLOWED_PM_DIMS`** (modify existing):
   - Add `'cf_entry_improvement_bucket'` and `'cf_exit_improvement_bucket'`

4. **Update `process_position_closed_for_braiding()`** (modify existing):
   - Extract counterfactual data from `completed_trades`
   - Bucket improvements
   - Add to context for pattern generation

5. **Update lesson builder** (modify existing):
   - Add logic to create counterfactual lessons (delay, hold, wait-for-confirmation)
   - Store in `learning_lessons` with different `effect` types

**Files to Modify**:
- `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py` (3-4 functions)
- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` (add counterfactual computation in `_check_position_closure()`)

**Risk Level**: **MEDIUM** - Adds new dimension types and lesson types, but doesn't break existing patterns

---

## 3. Field Coherence (Regime Stability)

### 3.1 Current State Analysis

**What Exists**:
- ✅ **Segment baselines already implemented**: `get_rr_baseline()` (lines 392-469) uses mcap_bucket + timeframe
- ✅ **Baseline storage**: `learning_baselines` table with segment baselines
- ✅ **Edge computation**: `compute_edge_score()` already uses segment baselines
- ✅ **Pattern dimensions**: `dimensions` JSONB in `learning_braids` includes `mcap_bucket` and `timeframe`
- ✅ **Query infrastructure**: Can query braids by module, filter by dimensions

**What's Missing**:
- ❌ Field coherence calculation (φ score)
- ❌ Query patterns across segments
- ❌ `field_coherence` and `segments_tested` in braid stats
- ❌ `field_coherence_multiplier` in edge formula

### 3.2 Implementation Complexity: **MEDIUM**

**Why it's medium**:
1. **Requires cross-segment queries**: Need to find same core pattern across different segments
2. **Pattern core extraction**: Need to separate "core dimensions" from "field dimensions"
3. **Aggregation logic**: Need to compute edge per segment, then aggregate into φ

**Key Insight**: The document notes that segment baselines already exist. Field coherence is a **meta-analysis** on top of this - it asks "does this pattern work across multiple segments?"

**Implementation Steps**:
1. **Add pattern core extraction** (new function):
   ```python
   def extract_core_dimensions(dimensions: Dict[str, Any]) -> Dict[str, Any]:
       """Extract core (behavioral) dimensions, excluding field (environment) dimensions"""
       # Core: state, a_bucket, buy_flag, etc.
       # Field: timeframe, mcap_bucket, age_bucket, chain
   ```

2. **Add field coherence calculation** (new function):
   ```python
   async def compute_field_coherence(
       sb_client,
       pattern_key: str,
       core_dimensions: Dict[str, Any],
       module: str
   ) -> Tuple[float, int]:
       """Compute φ (field coherence) and segments_tested"""
       # Query all braids with same core dimensions
       # For each segment, compute edge vs segment baseline
       # Aggregate into φ score
   ```

3. **Update `update_braid_stats()`** (modify existing):
   - Store `field_coherence` and `segments_tested` in stats

4. **Update `compute_edge_score()`** (modify existing):
   - Add optional `field_coherence` and `segments_tested` parameters
   - Compute `field_coherence_multiplier = (0.5 + 0.5 * φ) * (0.5 + 0.5 * tanh(segments_tested / 3))`
   - Multiply edge_raw by field_coherence_multiplier

5. **Update `build_lessons_from_braids()`** (modify existing):
   - Call `compute_field_coherence()` when building lessons
   - Use field_coherence_multiplier in edge calculation

**Files to Modify**:
- `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py` (3-4 functions)

**Risk Level**: **MEDIUM** - Requires new query patterns, but builds on existing baseline system

---

## 4. Recursive Depth (Pattern Recurrence)

### 4.1 Current State Analysis

**What Exists**:
- ✅ `edge_raw` computation - can track over time
- ✅ `last_updated` timestamp in `learning_braids` table
- ✅ `created_at` timestamp in `learning_braids` table
- ✅ Stats aggregation system

**What's Missing**:
- ❌ Time series tracking of `edge_raw` per pattern
- ❌ EWMA computation for recurrence
- ❌ `recurrence_score` in braid stats
- ❌ `recurrence_multiplier` in edge formula

### 4.2 Implementation Complexity: **MEDIUM**

**Why it's medium**:
1. **Time series storage**: Need to decide how to store edge_raw history (JSONB array? Separate table?)
2. **EWMA computation**: Need to implement exponential weighted moving average
3. **Update frequency**: Need to decide when to update recurrence (on each trade? Periodic job?)

**Implementation Options**:
- **Option A**: Store edge_raw history in `learning_braids.stats` as JSONB array: `{"edge_history": [{"timestamp": "...", "edge_raw": 2.3}, ...]}`
- **Option B**: Separate `pattern_recurrence` table with time series
- **Option C**: Compute on-demand from `last_updated` and current edge_raw (simpler but less accurate)

**Recommended**: **Option A** (JSONB array) - Simple, no schema change, sufficient for EWMA

**Implementation Steps**:
1. **Add EWMA computation** (new function):
   ```python
   def update_recurrence_score(
       current_recurrence: float,
       new_edge_raw: float,
       delta_t_days: float,
       tau_days: float = 30.0
   ) -> float:
       """Update recurrence score using EWMA"""
       alpha = 1 - math.exp(-delta_t_days / tau_days)
       return alpha * new_edge_raw + (1 - alpha) * current_recurrence
   ```

2. **Update `update_braid_stats()`** (modify existing):
   - Track `edge_raw` history in stats JSONB
   - Update `recurrence_score` using EWMA
   - Store `last_recurrence_update` timestamp

3. **Update `compute_edge_score()`** (modify existing):
   - Add optional `recurrence_score` parameter
   - Compute `recurrence_multiplier = 0.5 + 0.5 * tanh(recurrence_score)`
   - Multiply edge_raw by recurrence_multiplier

4. **Update `process_position_closed_for_braiding()`** (modify existing):
   - After computing edge_raw, update recurrence_score

**Files to Modify**:
- `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py` (3 functions)

**Risk Level**: **LOW-MEDIUM** - Additive, but requires careful EWMA implementation

---

## 5. Emergence Detection

### 5.1 Current State Analysis

**What Exists**:
- ✅ `incremental_edge` computation (lines 501-568 in `braiding_system.py`)
- ✅ `variance` tracking in braid stats
- ✅ `n` (sample size) tracking in braid stats
- ✅ Stats aggregation system

**What's Missing**:
- ❌ `emergence_score` calculation
- ❌ `emergence_score` in braid stats

### 5.2 Implementation Complexity: **LOW**

**Why it's easy**:
1. **All inputs exist**: incremental_edge, variance, n are already computed
2. **Simple formula**: `emergence_score = (incremental_edge / (1 + variance)) * (1 / sqrt(max(n, 3)))`
3. **No edge formula changes**: Emergence is tracking only, not used in decisions (yet)

**Implementation Steps**:
1. **Add emergence calculation** (new function or inline):
   ```python
   def compute_emergence_score(
       incremental_edge: float,
       variance: float,
       n: int
   ) -> float:
       """Compute emergence score for new but strong patterns"""
       return (incremental_edge / (1 + variance)) * (1 / math.sqrt(max(n, 3)))
   ```

2. **Update `compute_incremental_edge()`** (modify existing):
   - After computing incremental_edge, also compute emergence_score
   - Store in braid stats

3. **Update `update_braid_stats()`** (modify existing):
   - Store `emergence_score` in stats JSONB

**Files to Modify**:
- `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py` (2 functions)

**Risk Level**: **LOW** - Pure tracking, no impact on decisions

---

## 6. Integration Strategy

### 6.1 Combined Edge Formula

**Current Formula** (line 497 in `braiding_system.py`):
```python
edge_raw = delta_rr * coherence * support
```

**Enhanced Formula** (from V4_LEARNING_ENHANCEMENTS.md):
```python
edge_raw = delta_rr * coherence * support * time_weight * field_coherence_multiplier * recurrence_multiplier
```

**Implementation Approach**:
1. **Make multipliers optional**: Start with all multipliers = 1.0 (no change)
2. **Gradually enable**: Add each multiplier one at a time
3. **Backward compatible**: If multiplier data missing, default to 1.0

**Modified `compute_edge_score()` signature**:
```python
def compute_edge_score(
    avg_rr: float,
    variance: float,
    n: int,
    rr_baseline: float,
    time_efficiency: Optional[float] = None,
    field_coherence: Optional[float] = None,
    segments_tested: Optional[int] = None,
    recurrence_score: Optional[float] = None
) -> float:
```

### 6.2 Schema Changes

**Assessment**: **Minimal schema changes needed**

**Current `learning_braids.stats` JSONB structure**:
```json
{
  "n": 23,
  "sum_rr": 52.9,
  "avg_rr": 2.3,
  "variance": 0.5,
  "win_rate": 0.87,
  "avg_hold_time_days": 4.8
}
```

**Enhanced structure** (additions only):
```json
{
  // ... existing fields ...
  "avg_time_to_payback_days": 1.7,
  "time_efficiency": 0.42,
  "field_coherence": 0.67,
  "segments_tested": 3,
  "recurrence_score": 0.85,
  "last_recurrence_update": "2024-01-15T10:00:00Z",
  "emergence_score": 0.12,
  "edge_history": [{"timestamp": "...", "edge_raw": 2.3}, ...]
}
```

**No SQL migrations needed** - JSONB is flexible!

### 6.3 Testing Strategy

**For each enhancement**:
1. **Add computation** (don't use in decisions yet)
2. **Monitor values** (are they reasonable?)
3. **Validate against known patterns** (do high-quality patterns score well?)
4. **Gradually enable** (start with small multiplier weights, increase if beneficial)
5. **A/B test** (compare performance with/without enhancement)

---

## 7. Implementation Priority & Phases

### Phase 1 (v4.1): Time Efficiency ⭐ **START HERE**
- **Complexity**: LOW
- **Value**: HIGH (PM cares about speed)
- **Risk**: LOW (additive only)
- **Dependencies**: None
- **Estimated Effort**: 2-3 days
- **Status**: ✅ Implemented (`time_to_payback_days`, `time_efficiency`, `time_weight`)

### Phase 2 (v4.2): Counterfactual Learning
- **Complexity**: MEDIUM
- **Value**: HIGH (learns from mistakes)
- **Risk**: MEDIUM (new lesson types)
- **Dependencies**: Verify counterfactual data exists
- **Estimated Effort**: 4-5 days
- **Status**: ✅ Implemented (`could_enter_better`/`could_exit_better`, improvement buckets in braiding)

### Phase 3 (v4.3): Field Coherence
- **Complexity**: MEDIUM
- **Value**: HIGH (filters fragile patterns)
- **Risk**: LOW (just adds multiplier)
- **Dependencies**: None (builds on existing baselines)
- **Estimated Effort**: 3-4 days
- **Status**: ✅ Implemented (field_coherence metrics + multiplier in lesson builder)

### Phase 4 (v4.4): Recursive Depth
- **Complexity**: MEDIUM
- **Value**: HIGH (tracks pattern longevity)
- **Risk**: LOW (just adds multiplier/filter)
- **Dependencies**: None
- **Estimated Effort**: 3-4 days
- **Status**: ✅ Implemented (`recurrence_score` EWMA + multiplier in lesson builder)

### Phase 5 (v4.5): Emergence Detection
- **Complexity**: LOW
- **Value**: MEDIUM (predictive but not actionable yet)
- **Risk**: LOW (just tracking, not used in decisions)
- **Dependencies**: None
- **Estimated Effort**: 1-2 days
- **Status**: ✅ Implemented (emergence_score stored per braid, surfaced in lessons)

---

## 8. Code Impact Analysis

### 8.1 Files That Need Modification

**Primary File**:
- `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py`
  - `update_braid_stats()` - Add new stat fields
  - `compute_edge_score()` - Add multipliers
  - `compute_incremental_edge()` - Add emergence_score
  - `process_position_closed_for_braiding()` - Compute new metrics
  - `build_lessons_from_braids()` - Use enhanced edge formula

**Secondary Files** (may need changes):
- Position closing logic (wherever `completed_trades` is written) - Add time_to_payback, counterfactuals
- `src/intelligence/lowcap_portfolio_manager/pm/llm_research_layer.py` - May reference new stats

**No Schema Changes Needed**:
- ✅ `learning_braids` table - JSONB stats can hold new fields
- ✅ `learning_lessons` table - JSONB stats can hold new fields
- ✅ `learning_baselines` table - No changes needed

### 8.2 Backward Compatibility

**Assessment**: ✅ **Fully backward compatible**

**Why**:
1. **Optional parameters**: All new multipliers are optional, default to 1.0
2. **JSONB flexibility**: Missing fields in stats JSONB won't break existing code
3. **Gradual rollout**: Can enable features one at a time
4. **No breaking changes**: Existing patterns and lessons continue to work

**Migration Strategy**:
- Existing braids without new stats → multipliers default to 1.0 (no change)
- As new trades come in → new stats computed and stored
- Over time, all braids get enhanced stats

---

## 9. Key Risks & Mitigations

### Risk 1: Counterfactual Data Not Available
**Mitigation**: 
- Check if `could_enter_better`/`could_exit_better` are computed
- If not, add computation when position closes (use OHLCV data)

### Risk 2: Performance Impact from Cross-Segment Queries
**Mitigation**:
- Field coherence can be computed periodically (background job) rather than on every trade
- Cache results in braid stats

### Risk 3: EWMA Time Constant Tuning
**Mitigation**:
- Start with conservative tau (30 days)
- Make configurable via learning_configs table
- Monitor and adjust based on results

### Risk 4: Multiplier Weight Tuning
**Mitigation**:
- Start with conservative weights (0.5 + 0.5 * factor)
- Make configurable
- A/B test different weight combinations

### Risk 5: Hypothesis Validation Ownership
**Mitigation**:
- LLMResearchLayer now only emits hypotheses/reports; it no longer auto-validates outputs
- Ensure math-layer validators (cron or job) process `llm_learning` rows and update status/results
- Document ownership in LLM design notes so responsibilities stay separate

---

## 10. Conclusion

**Final Assessment**: ✅ **The skeleton is definitely there.** These enhancements are **additive and non-disruptive**. The core architecture (braiding, edge computation, stats aggregation) is solid and extensible.

**Key Strengths**:
1. ✅ Modular edge computation - easy to add multipliers
2. ✅ Flexible JSONB stats - no schema migrations needed
3. ✅ Streaming aggregation - easy to add new fields
4. ✅ Segment baselines exist - field coherence builds on this
5. ✅ OHLCV data accessible - time_to_payback can be computed

**Recommended Approach**:
1. **Start with Phase 1 (Time Efficiency)** - Lowest risk, high value
2. **Implement incrementally** - One phase at a time
3. **Monitor and validate** - Track metrics, adjust weights
4. **Gradually enable** - Start with multipliers = 1.0, then tune

**Estimated Total Effort**: 13-18 days for all v4 enhancements (v4.1-v4.5)

**Next Steps**:
1. Review this plan with team
2. Prioritize phases based on business needs
3. Start implementation with Phase 1 (Time Efficiency)
4. Set up monitoring/validation framework

---

## Appendix: Code Snippets for Reference

### Current Edge Computation
```python
# From braiding_system.py, line 472-498
def compute_edge_score(
    avg_rr: float,
    variance: float,
    n: int,
    rr_baseline: float
) -> float:
    delta_rr = avg_rr - rr_baseline
    coherence = 1.0 / (1.0 + variance)
    support = math.log(1 + n)
    edge_raw = delta_rr * coherence * support
    return edge_raw
```

### Enhanced Edge Computation (Target)
```python
def compute_edge_score(
    avg_rr: float,
    variance: float,
    n: int,
    rr_baseline: float,
    time_efficiency: Optional[float] = None,
    field_coherence: Optional[float] = None,
    segments_tested: Optional[int] = None,
    recurrence_score: Optional[float] = None
) -> float:
    delta_rr = avg_rr - rr_baseline
    coherence = 1.0 / (1.0 + variance)
    support = math.log(1 + n)
    
    # Enhancement multipliers (default to 1.0 if not provided)
    time_weight = 0.5 + 0.5 * (time_efficiency or 0.0)
    field_coherence_multiplier = 0.5 + 0.5 * (field_coherence or 0.0)
    if segments_tested:
        field_coherence_multiplier *= (0.5 + 0.5 * math.tanh(segments_tested / 3))
    recurrence_multiplier = 0.5 + 0.5 * math.tanh(recurrence_score or 0.0)
    
    edge_raw = delta_rr * coherence * support * time_weight * field_coherence_multiplier * recurrence_multiplier
    return edge_raw
```

---

**Document Status**: ✅ Complete - Ready for implementation

