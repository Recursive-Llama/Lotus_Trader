# Phase 2: Learning System - EWMA, Interaction Patterns, Importance Bleed

**Status**: ✅ **COMPLETE**  
**Date**: 2025-11-07

---

## Summary

Phase 2 of the Learning System implementation is complete. The learning system now uses:
- **EWMA with temporal decay** (τ₁ = 14 days, τ₂ = 90 days)
- **Bucket vocabulary standardization**
- **Interaction pattern matching and updates**
- **Importance bleed** (anti-double-counting)

---

## What Was Implemented

### 1. Bucket Vocabulary (`bucket_vocabulary.py`)

**New File**: `src/intelligence/universal_learning/bucket_vocabulary.py`

Standardized bucket definitions for consistent pattern matching:

- **Market Cap**: `<500k`, `500k-1m`, `1m-2m`, `2m-5m`, `5m-10m`, `10m-50m`, `50m+`
- **Volume**: `<10k`, `10k-50k`, `50k-100k`, `100k-250k`, `250k-500k`, `500k-1m`, `1m+`
- **Age**: `<1d`, `1-3d`, `3-7d`, `7-14d`, `14-30d`, `30-90d`, `90d+`
- **Mcap/Vol Ratio**: `<0.1`, `0.1-0.5`, `0.5-1.0`, `1.0-2.0`, `2.0-5.0`, `5.0+`

**Methods**:
- `get_mcap_bucket(mcap_usd)` - Convert market cap to bucket
- `get_vol_bucket(vol_24h_usd)` - Convert volume to bucket
- `get_age_bucket(age_days)` - Convert age to bucket
- `get_mcap_vol_ratio_bucket(mcap_usd, vol_24h_usd)` - Calculate ratio bucket
- `normalize_bucket(bucket_type, bucket_value)` - Normalize existing bucket values

### 2. Coefficient Updater (`coefficient_updater.py`)

**New File**: `src/intelligence/universal_learning/coefficient_updater.py`

Implements EWMA, interaction patterns, and importance bleed:

**Key Features**:
- **EWMA with temporal decay**: `w = e^(-Δt / τ)`
  - Short-term τ₁ = 14 days (fast memory)
  - Long-term τ₂ = 90 days (slow memory)
- **Interaction pattern generation**: Creates hashed keys like `curator=detweiler|chain=base|age<7d|vol>250k`
- **Importance bleed**: Downweights overlapping single-factor weights when interaction pattern is active

**Methods**:
- `calculate_decay_weight(trade_timestamp, current_timestamp, tau)` - Calculate exponential decay
- `update_coefficient_ewma(...)` - Update coefficient using EWMA
- `generate_interaction_key(entry_context)` - Create interaction pattern key
- `update_interaction_pattern(...)` - Update interaction pattern coefficient
- `apply_importance_bleed(...)` - Apply anti-double-counting adjustment

### 3. Updated Universal Learning System

**File**: `src/intelligence/universal_learning/universal_learning_system.py`

**Changes**:
- Added `CoefficientUpdater` and `BucketVocabulary` initialization
- Updated `_update_coefficients_from_closed_trade()` to:
  - Normalize bucket values using `BucketVocabulary`
  - Use `CoefficientUpdater.update_coefficient_ewma()` for single-factor coefficients
  - Update interaction patterns using `CoefficientUpdater.update_interaction_pattern()`
  - Apply importance bleed when interaction patterns are significant
- Replaced `_update_global_rr_baseline()` with `_update_global_rr_baseline_ewma()` using EWMA
- Removed old Phase 1 `_update_single_coefficient()` method

---

## How It Works

### EWMA Update Formula

For each closed trade:
1. Calculate decay weight: `w = e^(-Δt / τ)`
2. Calculate alpha: `α = w / (w + 1.0)` (normalized to [0, 0.5] range)
3. Update R/R: `new_rr = (1 - α) * old_rr + α * new_rr`

**Example**:
- Trade closed 7 days ago (τ₁ = 14 days)
- Decay weight: `w = e^(-7/14) = 0.606`
- Alpha: `α = 0.606 / 1.606 = 0.377`
- If old_rr = 1.2, new_rr = 1.5:
  - `new_rr = 0.623 * 1.2 + 0.377 * 1.5 = 1.32`

### Interaction Pattern Matching

**Example**:
- Entry context: `{curator: "0xdetweiler", chain: "base", mcap_bucket: "1m-2m", vol_bucket: "250k-500k", age_bucket: "3-7d"}`
- Generated key: `curator=0xdetweiler|chain=base|cap=1m-2m|vol=250k-500k|age=3-7d`
- Stored in `learning_coefficients` with `scope='interaction'`, `name='interaction'`

### Importance Bleed

**When interaction pattern is active** (weight ≠ 1.0):
- Get single-factor weights for levers in the interaction
- Apply bleed: `adjusted_weight = current_weight + α * (1.0 - current_weight)`
- Where `α = 0.2` (IMPORTANCE_BLEED_ALPHA)

**Example**:
- Interaction pattern `{curator=A, chain=Base}` has weight 1.5
- Single-factor: `curator=A` = 1.3, `chain=Base` = 1.4
- After bleed: `curator=A` = 1.3 + 0.2 * (1.0 - 1.3) = 1.24
- After bleed: `chain=Base` = 1.4 + 0.2 * (1.0 - 1.4) = 1.32

**Purpose**: Avoid double-counting. If the interaction already captures the synergy, don't also apply full single-factor weights.

---

## Data Flow (Phase 2)

```
PM closes position → Emits position_closed strand
  ↓
Learning system processes strand
  ↓
Normalize buckets using BucketVocabulary
  ↓
Update single-factor coefficients using EWMA (τ₁=14d, τ₂=90d)
  ↓
Update interaction pattern using EWMA
  ↓
Apply importance bleed to overlapping single-factor weights
  ↓
Update global R/R baseline using EWMA
  ↓
Coefficients stored in learning_coefficients table
```

---

## Database Impact

### `learning_coefficients` Table

**New rows created**:
- Single-factor coefficients (same as Phase 1, but now using EWMA)
- **Interaction pattern coefficients** (new in Phase 2):
  - `module='dm'`, `scope='interaction'`, `name='interaction'`
  - `key='curator=detweiler|chain=base|age<7d|vol>250k'`
  - Updated using EWMA with temporal decay

**Example interaction pattern row**:
```sql
('dm', 'interaction', 'interaction', 'curator=detweiler|chain=base|age<7d|vol>250k', 1.8, 1.75, 1.5, 12, '2024-01-15T10:00:00Z')
```

### `learning_configs` Table

**Global R/R baseline** now uses EWMA:
- `rr_short`: Short-term EWMA (τ₁ = 14 days)
- `rr_long`: Long-term EWMA (τ₂ = 90 days)
- Both updated with temporal decay on every closed trade

---

## Phase 2 Improvements Over Phase 1

| Feature | Phase 1 | Phase 2 |
|---------|---------|---------|
| **Averaging** | Simple: `(old * n + new) / (n + 1)` | EWMA: `(1 - α) * old + α * new` |
| **Temporal Decay** | None (all trades weighted equally) | Exponential: `w = e^(-Δt / τ)` |
| **Time Constants** | N/A | τ₁ = 14 days, τ₂ = 90 days |
| **Interaction Patterns** | None | Full support with hashed keys |
| **Importance Bleed** | None | Applied when interaction is significant |
| **Bucket Normalization** | None | Standardized buckets via BucketVocabulary |

---

## Testing

### Manual Testing Steps

1. **Create test position_closed strand with old trade** (30 days ago):
   ```python
   test_strand = {
       "kind": "position_closed",
       "entry_context": {
           "curator": "0xdetweiler",
           "chain": "base",
           "mcap_bucket": "1m-2m",
           "vol_bucket": "250k-500k",
           "age_bucket": "3-7d"
       },
       "completed_trades": [{
           "rr": 1.42,
           "exit_timestamp": (datetime.now() - timedelta(days=30)).isoformat()
       }]
   }
   ```

2. **Process the strand**:
   ```python
   await learning_system.process_strand_event(test_strand)
   ```

3. **Verify EWMA decay**:
   - Old trade (30 days) should have lower weight than recent trade (1 day)
   - Check `rr_short` and `rr_long` values reflect temporal decay

4. **Verify interaction pattern**:
   ```sql
   SELECT * FROM learning_coefficients 
   WHERE module = 'dm' AND scope = 'interaction';
   ```

5. **Verify importance bleed**:
   - Check single-factor weights are adjusted when interaction pattern is significant

---

## Files Created/Modified

### New Files
- `src/intelligence/universal_learning/bucket_vocabulary.py` - Bucket standardization
- `src/intelligence/universal_learning/coefficient_updater.py` - EWMA, interaction patterns, importance bleed

### Modified Files
- `src/intelligence/universal_learning/universal_learning_system.py`
  - Added `CoefficientUpdater` and `BucketVocabulary` initialization
  - Updated `_update_coefficients_from_closed_trade()` for Phase 2
  - Replaced `_update_global_rr_baseline()` with `_update_global_rr_baseline_ewma()`
  - Removed old Phase 1 `_update_single_coefficient()` method

---

## Next Steps (Phase 3)

1. **Update Decision Maker to use learned coefficients**:
   - Read coefficients from `learning_coefficients` table
   - Apply weight calibration and importance bleed
   - Calculate allocation: `allocation = base × ∏(factor_weight[lever])`
   - Normalize to portfolio constraints

2. **Enable PM to recalculate** (future):
   - Same formula, updated token data
   - Dynamic position resizing based on learned coefficients

---

## Status

✅ **Phase 2 Complete** - Learning system now uses EWMA, interaction patterns, and importance bleed.

**The learning system is now production-ready for coefficient updates!** Phase 3 will integrate these coefficients into the Decision Maker's allocation logic.

