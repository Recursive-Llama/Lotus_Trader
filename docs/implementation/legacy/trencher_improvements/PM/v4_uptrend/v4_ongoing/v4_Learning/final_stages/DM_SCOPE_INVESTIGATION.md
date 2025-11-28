# DM Scope Investigation - Deep Dive

**Date**: 2025-01-XX  
**Status**: Issue identified - aggregator ignores DM dimensions from entry_context

---

## Executive Summary

**The aggregator reads `entry_context` from `position_closed` strands (which contains all DM dimensions), but then only uses `extract_scope_from_context()` which only knows the 10 PM dimensions. DM dimensions (curator, chain, intent, etc.) are ignored. The fix is to merge `entry_context` (DM dimensions) with PM-specific dimensions to create ONE unified scope.**

---

## The Unified Scope Architecture (Correct Understanding)

**There should be ONE complete list of dimensions. Some apply only to DM, some apply only to PM, and all apply to both when present.**

### Complete Dimension List

**DM Dimensions** (from `entry_context`, set by DM):
- `curator` - Curator identifier
- `chain` - Blockchain (base, solana, ethereum, etc.)
- `mcap_bucket` - Market cap bucket at entry
- `vol_bucket` - Volume bucket at entry
- `age_bucket` - Token age bucket at entry
- `intent` - Intent type (research_positive, etc.)
- `mapping_confidence` - Confidence in token mapping
- `mcap_vol_ratio_bucket` - Market cap to volume ratio bucket

**PM Dimensions** (from `action_context`, set by PM):
- `market_family` - Market family (lowcaps, etc.)
- `timeframe` - Timeframe (1m, 15m, 1h, 4h)
- `A_mode` - Aggressiveness mode (patient, normal, aggressive)
- `E_mode` - Exit assertiveness mode (patient, normal, aggressive)

**Shared Dimensions** (from both `entry_context` and `regime_context`):
- `macro_phase` - Macro regime phase
- `meso_phase` - Meso regime phase
- `micro_phase` - Micro regime phase
- `bucket_leader` - Leading bucket in regime
- `bucket_rank_position` - Position in bucket rank
- `bucket` - Token bucket (should be same as `mcap_bucket` for consistency)

### Current Problem

**The aggregator's `SCOPE_DIMS` only has 10 dimensions:**
```python
SCOPE_DIMS = [
    "macro_phase", "meso_phase", "micro_phase",
    "bucket_leader", "bucket_rank_position",
    "market_family", "bucket", "timeframe",
    "A_mode", "E_mode"
]
```

**Missing DM dimensions:**
- `curator`, `chain`, `mcap_bucket`, `vol_bucket`, `age_bucket`, `intent`, `mapping_confidence`, `mcap_vol_ratio_bucket`

**The aggregator reads `entry_context` from `position_closed` strands (which has all DM dimensions), but then only uses `extract_scope_from_context()` which only extracts the 10 PM dimensions. DM dimensions are ignored.**

---

## The Critical Problem

### The Aggregator Ignores DM Dimensions from `entry_context`

**Current Flow:**
1. ✅ DM creates `entry_context` with DM dimensions (curator, chain, intent, etc.) and stores it in `lowcap_positions.entry_context`
2. ✅ PM reads `entry_context` from position and includes it in `position_closed` strand `content.entry_context`
3. ✅ Aggregator reads `entry_context` from `position_closed` strand (line 397)
4. ❌ **BUT** - Aggregator only uses `entry_context` to get `bucket` (line 486)
5. ❌ Aggregator calls `extract_scope_from_context()` which only extracts 10 PM dimensions (line 489)
6. ❌ **DM dimensions (curator, chain, intent, etc.) are completely ignored**

**Code Evidence:**
```python
# pattern_scope_aggregator.py:397
entry_context = content.get('entry_context', {})  # ✅ Has curator, chain, intent, etc.

# pattern_scope_aggregator.py:486
position_bucket = entry_context.get('bucket') or action_context.get('bucket')  # Only uses bucket!

# pattern_scope_aggregator.py:489
scope = extract_scope_from_context(...)  # ❌ Only extracts 10 PM dimensions, ignores entry_context!
```

**The Fix:**
1. Start with `entry_context` as base scope (has all DM dimensions)
2. Merge PM-specific dimensions from `action_context` (A_mode, E_mode, timeframe, market_family)
3. Merge regime phases from `regime_context`
4. Create ONE unified scope with ALL dimensions
5. Update `SCOPE_DIMS` to include ALL dimensions (DM + PM)

---

## The `_augment_dm_context()` Question

**Should DM scope include regime phases?**

**Current behavior:**
- `_augment_dm_context()` adds regime phases to DM scope
- These are the **only** DM scope dimensions that would be recognized by the aggregator
- But DM doesn't create `position_closed` strands, so even these don't get aggregated

**Options:**

### Option A: Keep `_augment_dm_context()` (Current)
**Pros:**
- DM and PM share some dimensions (regime phases)
- Could enable cross-module learning (if we fix aggregation)

**Cons:**
- DM-specific dimensions (curator, chain, intent) are still ignored
- Creates confusion - DM scope has both DM and PM dimensions

### Option B: Remove `_augment_dm_context()` (Separate DM/PM)
**Pros:**
- Clear separation: DM scope = DM dimensions only
- PM scope = PM dimensions only
- No confusion about which dimensions belong to which module

**Cons:**
- Lose shared regime context
- Can't learn regime effects on DM decisions

### Option C: Fix Aggregation to Handle Both (Recommended)
**Pros:**
- DM scope gets aggregated properly
- PM scope gets aggregated properly
- Both modules can learn from their own dimensions

**Cons:**
- Requires architectural changes:
  1. DM needs to create `position_closed` strands (or PM needs to include DM scope)
  2. Aggregator needs to handle DM dimensions
  3. `pattern_scope_stats` needs to support DM dimensions

---

## Root Cause Analysis

### Why This Happened

1. **PM was designed first** - aggregator built for PM's 10 dimensions
2. **DM was added later** - uses different dimensions but same override system
3. **Override system works** - `apply_allocation_overrides()` matches on any scope dimensions
4. **But aggregation is broken** - only processes PM dimensions

### The Mismatch

| Component | DM Scope | PM Scope | Aggregator |
|-----------|----------|----------|------------|
| **Dimensions** | curator, chain, intent, mcap_bucket, vol_bucket, age_bucket, mapping_confidence, mcap_vol_ratio_bucket, + regime phases | macro_phase, meso_phase, micro_phase, bucket_leader, bucket_rank_position, market_family, bucket, timeframe, A_mode, E_mode | Only PM dimensions |
| **Used for** | Runtime overrides ✅ | Runtime overrides ✅ | Aggregation ❌ |
| **Gets aggregated?** | ❌ NO | ✅ YES | N/A |

---

## Recommended Solution

### Phase 1: Create Unified Scope Extraction

1. **Create `extract_unified_scope_from_strand()` function:**
   ```python
   def extract_unified_scope_from_strand(
       entry_context: Dict[str, Any],  # Has DM dimensions
       action_context: Dict[str, Any],  # Has PM dimensions
       regime_context: Dict[str, Any]   # Has regime phases
   ) -> Dict[str, Any]:
       # Start with entry_context (DM dimensions)
       scope = entry_context.copy()
       
       # Add PM-specific dimensions from action_context
       scope['market_family'] = action_context.get('market_family', 'lowcaps')
       scope['timeframe'] = action_context.get('timeframe', '1h')
       scope['A_mode'] = action_context.get('A_mode') or derive_a_mode(action_context)
       scope['E_mode'] = action_context.get('E_mode') or derive_e_mode(action_context)
       
       # Add/override regime phases from regime_context
       macro = regime_context.get('macro', {})
       meso = regime_context.get('meso', {})
       micro = regime_context.get('micro', {})
       scope['macro_phase'] = macro.get('phase') or scope.get('macro_phase', 'Unknown')
       scope['meso_phase'] = meso.get('phase') or scope.get('meso_phase', 'Unknown')
       scope['micro_phase'] = micro.get('phase') or scope.get('micro_phase', 'Unknown')
       
       # Add bucket_leader and bucket_rank_position from regime_context
       bucket_rank = regime_context.get('bucket_rank', [])
       if bucket_rank:
           scope['bucket_leader'] = bucket_rank[0]
           bucket = scope.get('bucket') or scope.get('mcap_bucket')
           if bucket and bucket in bucket_rank:
               scope['bucket_rank_position'] = bucket_rank.index(bucket) + 1
       
       # Normalize bucket (use mcap_bucket if bucket not set)
       if not scope.get('bucket') and scope.get('mcap_bucket'):
           scope['bucket'] = scope['mcap_bucket']
       
       return scope
   ```

2. **Update `SCOPE_DIMS` to include ALL dimensions:**
   ```python
   SCOPE_DIMS = [
       # DM dimensions
       "curator", "chain", "mcap_bucket", "vol_bucket", "age_bucket",
       "intent", "mapping_confidence", "mcap_vol_ratio_bucket",
       # Shared dimensions
       "macro_phase", "meso_phase", "micro_phase",
       "bucket_leader", "bucket_rank_position", "bucket",
       # PM dimensions
       "market_family", "timeframe", "A_mode", "E_mode"
   ]
   ```

3. **Update aggregator to use unified scope:**
   - Replace `extract_scope_from_context()` call with `extract_unified_scope_from_strand()`
   - Use `entry_context` from `position_closed` strand as base
   - Merge with `action_context` from `pm_action` strands
   - Merge with `regime_context` from strand

4. **Update `pattern_scope_stats` schema:**
   - Extend bitmask to support all dimensions (currently 10 bits, need ~18 bits)
   - Or use separate `scope_values` JSONB column (already exists) and compute hash

### Phase 2: Clarify `_augment_dm_context()`

**Current behavior:**
- `_augment_dm_context()` adds regime phases to DM scope
- This is correct - regime phases should be part of unified scope
- **Keep it** - regime phases are useful for both DM and PM learning

---

## Immediate Actions

1. ✅ **Document the issue** (this document)
2. ⏳ **Decide on `_augment_dm_context()`** - keep or remove?
3. ⏳ **Design DM aggregation path** - how should DM scope be aggregated?
4. ⏳ **Update aggregator** - support DM dimensions
5. ⏳ **Update `position_closed` strands** - include DM scope from `entry_context`

---

## Questions for Discussion

1. **Should DM and PM share scope dimensions?** (Current: partially - regime phases)
2. **Should DM create its own `position_closed` strands?** (Current: NO - only PM does)
3. **Should aggregator process both DM and PM dimensions?** (Current: NO - only PM)
4. **Should `pattern_scope_stats` have separate tables for DM vs PM?** (Current: single table)
5. **What is the "local" baseline for DM?** (Current: unclear - same as PM?)

