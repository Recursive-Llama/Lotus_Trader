# Learning System v4 Implementation Plan

**Status**: Ready to implement  
**Priority**: HIGH - PM is already emitting `position_closed` strands, but learning system isn't processing them yet

---

## Current State Assessment

### ✅ Already Implemented

1. **Database Schemas**:
   - ✅ `learning_configs` table exists (`src/database/learning_configs_schema.sql`)
   - ✅ `learning_coefficients` table exists (`src/database/learning_coefficients_schema.sql`)
   - ✅ `lowcap_positions.entry_context` JSONB (Decision Maker populates it)
   - ✅ `lowcap_positions.completed_trades` JSONB (PM populates it)

2. **PM Position Closure**:
   - ✅ `_check_position_closure()` implemented in `pm_core_tick.py`
   - ✅ `_calculate_rr_metrics()` implemented (queries OHLCV, computes R/R)
   - ✅ PM writes `completed_trades` JSONB when position closes
   - ✅ PM emits `position_closed` strands with full context

3. **Decision Maker**:
   - ✅ Creates `entry_context` JSONB when creating positions
   - ✅ Includes all lever values (curator, chain, mcap_bucket, vol_bucket, etc.)

### ❌ Missing (Critical Gap)

1. **Learning System Processing**:
   - ❌ `UniversalLearningSystem.process_strand_event()` doesn't handle `kind='position_closed'` strands
   - ❌ No coefficient update logic (EWMA, weight calculation)
   - ❌ No global R/R baseline tracking
   - ❌ Decision Maker doesn't use learned coefficients yet (still uses static multipliers)

---

## Implementation Order

### Phase 1: Wire Up Learning System (CRITICAL - Closes Feedback Loop)

**Why first**: PM is already emitting `position_closed` strands, but they're not being processed. Without this, we're losing learning data.

**Tasks**:
1. Update `UniversalLearningSystem.process_strand_event()` to detect `kind='position_closed'` strands
2. Create `_process_position_closed_strand()` method:
   - Extract `completed_trade` data from strand
   - Extract `entry_context` from strand
   - Call coefficient update logic
3. Create `_update_coefficients_from_closed_trade()` method:
   - Update single-factor coefficients (curator, chain, mcap, vol, age, intent, confidence)
   - Update interaction patterns (if any match)
   - Update global R/R baseline
   - Recalculate weights

**Files to modify**:
- `src/intelligence/universal_learning/universal_learning_system.py`

**Estimated effort**: 2-3 hours

---

### Phase 2: Implement Coefficient Update Logic

**Why second**: Need the math layer to actually update coefficients from closed trades.

**Tasks**:
1. Create `CoefficientUpdater` class:
   - EWMA with temporal decay (τ₁ = 14 days, τ₂ = 90 days)
   - Weight calculation: `weight = clamp((rr_short / rr_global_short), 0.5, 2.0)`
   - Bucket vocabulary (standardize mcap, vol, age buckets)
   - Interaction pattern matching (hash combinations)

2. Implement bucket vocabulary:
   - Market Cap: `<500k`, `500k-1m`, `1m-2m`, `2m-5m`, `5m-10m`, `10m-50m`, `50m+`
   - Volume: `<10k`, `10k-50k`, `50k-100k`, `100k-250k`, `250k-500k`, `500k-1m`, `1m+`
   - Age: `<1d`, `1-3d`, `3-7d`, `7-14d`, `14-30d`, `30-90d`, `90d+`
   - Mcap/Vol Ratio: `<0.1`, `0.1-0.5`, `0.5-1.0`, `1.0-2.0`, `2.0-5.0`, `5.0+`

3. Implement global R/R baseline:
   - Store in `learning_configs.dm.global_rr` JSONB
   - Update on every closed trade
   - Use for weight normalization

**Files to create**:
- `src/intelligence/universal_learning/coefficient_updater.py`

**Files to modify**:
- `src/intelligence/universal_learning/universal_learning_system.py` (use CoefficientUpdater)

**Estimated effort**: 4-6 hours

---

### Phase 3: Update Decision Maker to Use Learned Coefficients

**Why third**: Once coefficients are being updated, DM should use them for allocation.

**Tasks**:
1. Create `CoefficientReader` class:
   - Read coefficients from `learning_coefficients` table
   - Apply weight calibration (clamp to [0.5, 2.0])
   - Apply importance bleed (downweight overlapping single-factor weights when interaction pattern active)
   - Return normalized weights

2. Update Decision Maker allocation formula:
   - Read learned coefficients
   - Calculate: `allocation = base_allocation × ∏(factor_weight[lever])`
   - Normalize to portfolio constraints
   - Fallback to static multipliers if no learned data yet

3. Enable PM to recalculate (future):
   - Same formula, updated token data
   - For now, just document the approach

**Files to create**:
- `src/intelligence/universal_learning/coefficient_reader.py`

**Files to modify**:
- `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`

**Estimated effort**: 3-4 hours

---

### Phase 4: Social Ingest Changes (Lower Priority)

**Why last**: These are infrastructure improvements, not critical for learning loop.

**Tasks**:
1. Migrate `ignored_tokens` to `learning_configs.social_ingest.ambiguous_terms`
2. Add `chain_counts` to `curators` table
3. Update `_detect_chain()` to use curator chain_counts as small weight
4. Remove volume/liquidity BLOCK logic (change to NOTE)
5. Add metadata to strands (`mapping_reason`, `confidence_grade`, health metrics)

**Files to modify**:
- `src/intelligence/social_ingest/social_ingest_basic.py`
- `src/database/curators_schema.sql` (add `chain_counts` column)

**Estimated effort**: 2-3 hours

---

## Critical Path

**The feedback loop must be closed first**:

```
PM closes position → Emits position_closed strand → Learning system processes → Updates coefficients → DM uses coefficients → Better allocations
```

**Without Phase 1, the loop is broken** - PM emits strands, but nothing processes them.

---

## Implementation Strategy

### Option A: Minimal Viable Learning (Recommended)

**Start with Phase 1 only** - just wire up the processing:
- Process `position_closed` strands
- Update single-factor coefficients (curator, chain, mcap, vol, age, intent, confidence)
- Store in `learning_coefficients` table
- **Don't use coefficients yet** (Phase 3 comes later)

**Benefits**:
- Closes feedback loop immediately
- Starts collecting learning data
- Can verify data is being stored correctly
- Low risk (doesn't change allocation logic yet)

**Then add Phase 2** (coefficient math), then Phase 3 (use coefficients).

### Option B: Full Implementation

**Implement all phases at once** - complete learning system in one go.

**Benefits**:
- Complete system from day one
- No intermediate states

**Risks**:
- More complex to test
- Harder to debug if something breaks
- Longer development cycle

---

## Recommendation

**Start with Option A (Minimal Viable Learning)**:
1. Wire up Phase 1 (process `position_closed` strands, update coefficients)
2. Verify data is being stored correctly (query `learning_coefficients` table)
3. Then add Phase 2 (coefficient math)
4. Then add Phase 3 (use coefficients in DM)

**Why**: Lower risk, incremental progress, can verify each step works before moving to the next.

---

## Testing Strategy

### Phase 1 Testing:
1. Create test `position_closed` strand
2. Call `process_strand_event()` with test strand
3. Verify `learning_coefficients` table has new rows
4. Verify coefficients have correct values

### Phase 2 Testing:
1. Create multiple test closed trades with known R/R
2. Process them through learning system
3. Verify EWMA calculations are correct
4. Verify weight clamping works

### Phase 3 Testing:
1. Create test position with known lever values
2. Query coefficients for those levers
3. Verify allocation formula uses coefficients correctly
4. Verify fallback to static multipliers when no data

---

## Next Steps

1. **Start with Phase 1** - Wire up `position_closed` strand processing
2. **Verify** - Check that coefficients are being stored correctly
3. **Iterate** - Add Phase 2, then Phase 3

**Ready to proceed?** Let's start with Phase 1 implementation.

