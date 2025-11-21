# Phase 3: Learning System - Decision Maker Integration

**Status**: ✅ **COMPLETE**  
**Date**: 2025-11-07

---

## Summary

Phase 3 of the Learning System implementation is complete. The Decision Maker now uses learned coefficients to calculate allocations, replacing static multipliers with data-driven weights.

---

## What Was Implemented

### 1. Coefficient Reader (`coefficient_reader.py`)

**New File**: `src/intelligence/universal_learning/coefficient_reader.py`

Reads learned coefficients from database and applies weight calibration and importance bleed:

**Key Methods**:
- `get_lever_weights(entry_context, module)` - Get weights for all levers
- `get_interaction_weight(entry_context, module)` - Get interaction pattern weight
- `apply_importance_bleed(lever_weights, interaction_weight)` - Apply anti-double-counting
- `calculate_allocation_multiplier(entry_context, module)` - Calculate total multiplier
- `get_timeframe_weights(module)` - Get learned timeframe weights
- `normalize_timeframe_weights(timeframe_weights)` - Normalize to sum to 1.0

### 2. Updated Decision Maker

**File**: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`

**Changes**:
- Added `CoefficientReader` and `BucketVocabulary` initialization
- Updated `_calculate_allocation()` to use learned coefficients:
  - Builds entry context with buckets
  - Gets learned multiplier from coefficients
  - Applies multiplier to base allocation
  - Falls back to static multipliers if learning system unavailable
- Added `_build_entry_context_for_learning()` to create entry context with buckets:
  - Calculates mcap_bucket, vol_bucket, age_bucket, mcap_vol_ratio_bucket
  - Includes curator, chain, intent, mapping_confidence
- Updated `_create_positions_for_token()` to use learned timeframe weights:
  - Gets learned timeframe weights from coefficients
  - Normalizes weights to sum to 1.0
  - Falls back to default splits if no learned data
- Added `_calculate_allocation_static_fallback()` for backward compatibility

---

## Allocation Formula (Phase 3)

### Before (Static Multipliers)
```
allocation = base_allocation × intent_multiplier × mcap_multiplier × age_multiplier × chain_multiplier
```

### After (Learned Coefficients)
```
allocation = base_allocation × learned_multiplier

Where:
learned_multiplier = ∏(lever_weight) × interaction_weight

And:
lever_weight = learned coefficient for each lever (curator, chain, cap, vol, age, intent, confidence)
interaction_weight = learned coefficient for interaction pattern (if exists)
```

**With importance bleed applied**:
- If interaction pattern is significant (weight ≠ 1.0)
- Single-factor weights are downweighted toward 1.0 by α = 0.2
- Prevents double-counting

---

## Timeframe Splits (Phase 3)

### Before (Fixed Splits)
```
1m: 5%
15m: 12.5%
1h: 70%
4h: 12.5%
```

### After (Learned Weights)
```
1. Get learned timeframe weights from learning_coefficients
2. Normalize weights to sum to 1.0
3. Apply normalized weights to total_allocation_usd
4. Fallback to defaults if no learned data
```

**Example**:
- Learned weights: `{'1m': 0.8, '15m': 1.4, '1h': 1.1, '4h': 0.9}`
- Normalized: `{'1m': 0.19, '15m': 0.33, '1h': 0.26, '4h': 0.22}`
- Applied to $1000 total: `1m=$190, 15m=$330, 1h=$260, 4h=$220`

---

## Data Flow (Phase 3)

```
Social signal → Decision Maker
  ↓
Build entry_context with buckets (mcap_bucket, vol_bucket, age_bucket, etc.)
  ↓
Get learned multiplier from CoefficientReader
  - Read single-factor weights (curator, chain, cap, vol, age, intent, confidence)
  - Read interaction pattern weight (if exists)
  - Apply importance bleed
  - Calculate: multiplier = ∏(lever_weight) × interaction_weight
  ↓
Calculate allocation: base_allocation × learned_multiplier
  ↓
Get learned timeframe weights
  - Normalize to sum to 1.0
  - Apply to total_allocation_usd
  ↓
Create 4 positions with learned allocation splits
  ↓
Store entry_context in positions table for learning
```

---

## Fallback Behavior

**If learning system unavailable or no coefficients found**:
1. **Allocation calculation**: Falls back to static multipliers (old behavior)
2. **Timeframe splits**: Falls back to default splits (5%, 12.5%, 70%, 12.5%)

**This ensures**:
- System works even when learning system is empty (cold start)
- Gradual transition as coefficients accumulate
- No breaking changes if learning system has issues

---

## Entry Context Structure

**Now includes buckets** (for learning system):
```json
{
  "curator": "0xdetweiler",
  "chain": "base",
  "mcap_bucket": "1m-2m",
  "vol_bucket": "250k-500k",
  "age_bucket": "3-7d",
  "intent": "research_positive",
  "mapping_confidence": "high",
  "mcap_vol_ratio_bucket": "0.5-1.0",
  "mcap_at_entry": 1500000,
  "vol_at_entry": 350000,
  "age_at_entry": 5,
  "curator_score": 0.85,
  "token_contract": "0x123...",
  "token_ticker": "TOKEN",
  "allocation_pct": 6.5,
  "total_allocation_usd": 650.0,
  "created_at": "2024-01-15T10:00:00Z"
}
```

---

## Example Allocation Calculation

**Scenario**:
- Base allocation: 4% (from AllocationManager, curator_score=0.8)
- Learned coefficients:
  - curator=0xdetweiler: 1.3×
  - chain=base: 1.4×
  - cap=1m-2m: 1.5×
  - vol=250k-500k: 1.1×
  - age=3-7d: 1.3×
  - intent=research_positive: 1.2×
  - mapping_confidence=high: 1.0×
  - interaction pattern: 1.8× (curator=detweiler|chain=base|age<7d|vol>250k)

**Calculation**:
1. **Single-factor product**: 1.3 × 1.4 × 1.5 × 1.1 × 1.3 × 1.2 × 1.0 = 4.68
2. **Apply importance bleed** (interaction=1.8, significant):
   - Adjusted single-factor: 4.68 → ~4.2 (downweighted by α=0.2)
3. **Apply interaction**: 4.2 × 1.8 = 7.56
4. **Final allocation**: 4% × 7.56 = 30.24%
5. **Clamp to bounds**: min(20.0, 30.24) = 20.0%

**Result**: 20% allocation (clamped to max)

---

## Files Created/Modified

### New Files
- `src/intelligence/universal_learning/coefficient_reader.py` - Coefficient reading and application

### Modified Files
- `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`
  - Added `CoefficientReader` and `BucketVocabulary` initialization
  - Updated `_calculate_allocation()` to use learned coefficients
  - Added `_build_entry_context_for_learning()` for bucket calculation
  - Added `_calculate_allocation_with_curator()` wrapper
  - Added `_calculate_allocation_from_context()` for coefficient-based calculation
  - Added `_calculate_allocation_static_fallback()` for backward compatibility
  - Updated `_create_positions_for_token()` to use learned timeframe weights
  - Updated entry_context building to include buckets

---

## Testing

### Manual Testing Steps

1. **Test with no learned data** (cold start):
   - Decision Maker should fallback to static multipliers
   - Timeframe splits should use defaults
   - System should work normally

2. **Test with learned coefficients**:
   - Create test coefficients in `learning_coefficients` table
   - Process a social signal
   - Verify allocation uses learned coefficients
   - Verify timeframe splits use learned weights

3. **Test importance bleed**:
   - Create interaction pattern with significant weight (e.g., 1.5)
   - Create matching single-factor coefficients
   - Verify single-factor weights are downweighted

---

## Status

✅ **Phase 3 Complete** - Decision Maker now uses learned coefficients for allocation calculation.

**The complete learning loop is now closed!**

```
PM closes position → Emits position_closed strand → Learning system processes → 
Updates coefficients → Decision Maker uses coefficients → Better allocations → 
Better outcomes → More learning data → Continuous improvement
```

---

## Next Steps

1. **Monitor and validate**:
   - Watch allocation calculations in logs
   - Verify coefficients are being used correctly
   - Check that fallback works when needed

2. **Future enhancements**:
   - PM dynamic recalculation (recalculate allocations for existing positions)
   - Per-timeframe learning refinement
   - Interaction pattern discovery improvements

---

## Summary of All Phases

| Phase | Status | What It Does |
|-------|--------|--------------|
| **Phase 1** | ✅ Complete | Process `position_closed` strands, update coefficients (simple averaging) |
| **Phase 2** | ✅ Complete | EWMA with temporal decay, interaction patterns, importance bleed |
| **Phase 3** | ✅ Complete | Decision Maker uses learned coefficients for allocations |

**The Learning System v4 is now fully operational!** 🎉

