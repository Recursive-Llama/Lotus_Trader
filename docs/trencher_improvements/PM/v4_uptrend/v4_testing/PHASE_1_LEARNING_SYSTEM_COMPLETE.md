# Phase 1: Learning System - Position Closed Strand Processing

**Status**: ✅ **COMPLETE**  
**Date**: 2025-11-07

---

## Summary

Phase 1 of the Learning System implementation is complete. The learning system now processes `position_closed` strands emitted by the Portfolio Manager and updates learning coefficients in the database.

## What Was Implemented

### 1. Strand Detection (`process_strand_event()`)

**File**: `src/intelligence/universal_learning/universal_learning_system.py`

- Updated `process_strand_event()` to detect `kind='position_closed'` strands
- Routes `position_closed` strands to dedicated processing method
- Skips scoring/clustering for `position_closed` strands (they're learning events, not signals)

### 2. Position Closed Processing (`_process_position_closed_strand()`)

**Method**: `_process_position_closed_strand(strand: Dict[str, Any])`

- Extracts `entry_context` and `completed_trades` from strand
- Gets the most recent completed trade (last in array)
- Validates R/R metric exists
- Calls coefficient update logic

### 3. Coefficient Updates (`_update_coefficients_from_closed_trade()`)

**Method**: `_update_coefficients_from_closed_trade(entry_context, completed_trade, timeframe)`

- Extracts lever values from `entry_context`:
  - `curator`, `chain`, `mcap_bucket`, `vol_bucket`, `age_bucket`
  - `intent`, `mapping_confidence`, `mcap_vol_ratio_bucket`
  - `timeframe` (1m, 15m, 1h, 4h)
- Updates single-factor coefficients for each lever
- Updates global R/R baseline

### 4. Single Coefficient Update (`_update_single_coefficient()`)

**Method**: `_update_single_coefficient(module, scope, name, key, rr_value, timeframe)`

- Reads existing coefficient from `learning_coefficients` table
- Uses simple averaging for Phase 1: `new_rr = (old_rr * n + new_rr) / (n + 1)`
- Calculates weight: `weight = clamp((rr_short / rr_global_short), 0.5, 2.0)`
- Creates new coefficient if doesn't exist
- Updates or inserts into `learning_coefficients` table

### 5. Global R/R Baseline (`_update_global_rr_baseline()`)

**Method**: `_update_global_rr_baseline(rr_value)`

- Updates global R/R baseline in `learning_configs.dm.global_rr`
- Uses simple averaging for Phase 1
- Stores `rr_short`, `rr_long`, `n` (sample count), `updated_at`

### 6. Global R/R Retrieval (`_get_global_rr_short()`)

**Method**: `_get_global_rr_short() -> Optional[float]`

- Retrieves global R/R short-term baseline from `learning_configs`
- Used for weight normalization

---

## Data Flow

```
PM closes position
  ↓
PM emits position_closed strand (with entry_context, completed_trades, R/R metrics)
  ↓
UniversalLearningSystem.process_strand_event() detects kind='position_closed'
  ↓
_process_position_closed_strand() extracts data
  ↓
_update_coefficients_from_closed_trade() updates all matching levers
  ↓
_update_single_coefficient() for each lever (curator, chain, mcap, vol, age, intent, confidence, timeframe)
  ↓
_update_global_rr_baseline() updates global R/R
  ↓
Coefficients stored in learning_coefficients table
```

---

## Database Tables Used

### `learning_coefficients`
- Stores learned performance coefficients
- Columns: `module`, `scope`, `name`, `key`, `weight`, `rr_short`, `rr_long`, `n`, `updated_at`
- Example rows created:
  - `('dm', 'lever', 'curator', '0xdetweiler', 1.3, 1.35, 1.2, 5, ...)`
  - `('dm', 'lever', 'chain', 'base', 1.4, 1.45, 1.3, 8, ...)`
  - `('dm', 'lever', 'cap', '1m-2m', 1.5, 1.55, 1.4, 12, ...)`

### `learning_configs`
- Stores global R/R baseline
- Module: `decision_maker`
- Config structure:
  ```json
  {
    "global_rr": {
      "rr_short": 1.05,
      "rr_long": 0.98,
      "n": 150,
      "updated_at": "2024-01-15T10:00:00Z"
    }
  }
  ```

---

## Phase 1 Limitations (To Be Addressed in Phase 2)

1. **Simple Averaging**: Uses `(old_rr * n + new_rr) / (n + 1)` instead of EWMA with temporal decay
2. **No Interaction Patterns**: Only updates single-factor coefficients, not combinations
3. **No Importance Bleed**: Doesn't downweight overlapping single-factor weights when interaction patterns are active
4. **No Time Decay**: All trades weighted equally, regardless of age

---

## Testing

### Manual Testing Steps

1. **Create a test position_closed strand**:
   ```python
   test_strand = {
       "kind": "position_closed",
       "position_id": 123,
       "token": "0x123...",
       "timeframe": "1h",
       "chain": "base",
       "entry_context": {
           "curator": "0xdetweiler",
           "chain": "base",
           "mcap_bucket": "1m-2m",
           "vol_bucket": "250k-500k",
           "age_bucket": "3-7d",
           "intent": "research_positive",
           "mapping_confidence": "high"
       },
       "completed_trades": [{
           "rr": 1.42,
           "return": 1.13,
           "max_drawdown": 0.20,
           "max_gain": 2.0
       }]
   }
   ```

2. **Process the strand**:
   ```python
   await learning_system.process_strand_event(test_strand)
   ```

3. **Verify coefficients were created/updated**:
   ```sql
   SELECT * FROM learning_coefficients 
   WHERE module = 'dm' AND scope = 'lever';
   ```

4. **Verify global R/R baseline was updated**:
   ```sql
   SELECT config_data->'global_rr' FROM learning_configs 
   WHERE module_id = 'decision_maker';
   ```

---

## Next Steps (Phase 2)

1. **Implement EWMA with Temporal Decay**:
   - Short-term τ₁ = 14 days
   - Long-term τ₂ = 90 days
   - Weight trades by `e^(-Δt / τ)`

2. **Implement Interaction Patterns**:
   - Hash combinations like `curator=detweiler|chain=base|age<7d|vol>250k`
   - Store in `learning_coefficients` with `scope='interaction'`

3. **Implement Importance Bleed**:
   - Downweight overlapping single-factor weights when interaction pattern is active

4. **Implement Bucket Vocabulary**:
   - Standardize buckets for mcap, vol, age, mcap/vol ratio
   - Ensure consistent bucketing across all trades

---

## Files Modified

- `src/intelligence/universal_learning/universal_learning_system.py`
  - Added `_process_position_closed_strand()` method
  - Added `_update_coefficients_from_closed_trade()` method
  - Added `_update_single_coefficient()` method
  - Added `_update_global_rr_baseline()` method
  - Added `_get_global_rr_short()` method
  - Updated `process_strand_event()` to detect and route `position_closed` strands

---

## Status

✅ **Phase 1 Complete** - Learning system now processes `position_closed` strands and updates coefficients.

**The feedback loop is now closed!** When PM closes a position, the learning system automatically processes it and updates coefficients.

