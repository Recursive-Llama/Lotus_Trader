# Testing Plan Update - After ad_strands Schema Changes

**Date**: 2025-11-15  
**Status**: Update Required  
**Changes Since Original Plan**: Major schema cleanup and structure changes

---

## Summary of Changes

### 1. ad_strands Schema Cleanup ✅ **COMPLETE**
- **Removed**: 40+ legacy columns (CIL/RDI/CTP related)
- **Renamed**: `lifecycle_id` → `position_id`
- **Removed**: Top-level `confidence`, `sig_confidence`, `sig_sigma`, `sig_direction`
- **Removed**: Legacy views, triggers, functions
- **Result**: Clean, focused schema for lowcap system only

### 2. Strand Structure Changes ✅ **COMPLETE**

#### position_closed Strands
**OLD Structure** (from original plan):
```python
{
    "kind": "position_closed",
    "position_id": position_id,  # Top-level
    "token": token,  # Top-level
    "chain": chain,  # Top-level
    "timeframe": timeframe,  # Top-level
    "entry_context": entry_context,  # Top-level
    "completed_trades": completed_trades,  # Top-level
    "decision_type": decision_type,  # Top-level
}
```

**NEW Structure** (current implementation):
```python
{
    "id": f"position_closed_{position_id}_{timestamp}",
    "module": "pm",
    "kind": "position_closed",
    "symbol": token_ticker,  # Top-level (renamed from "token")
    "timeframe": timeframe,  # Top-level
    "position_id": position_id,  # Top-level column for querying
    "content": {
        "position_id": position_id,  # Also in content for consistency
        "token_contract": token_contract,
        "chain": chain,
        "ts": timestamp,
        "entry_context": entry_context,  # MOVED TO content
        "completed_trades": completed_trades,  # MOVED TO content
        "decision_type": decision_type,
    },
    "regime_context": {  # NEW: Macro/meso/micro phases
        "macro": {"phase": "...", "score": 0.0, "ts": "..."},
        "meso": {"phase": "...", "score": 0.0, "ts": "..."},
        "micro": {"phase": "...", "score": 0.0, "ts": "..."}
    },
    "tags": ["position_closed", "pm", "learning"],
    "target_agent": "learning_system",
    "created_at": timestamp,
    "updated_at": timestamp
}
```

**⚠️ CRITICAL**: Learning system code reads `entry_context` and `completed_trades` from **top-level** of strand dict, but they're now in `content` JSONB!

**Fix Required**: Update learning system to read from `content`:
```python
# OLD (current code):
entry_context = strand.get('entry_context', {})
completed_trades = strand.get('completed_trades', [])

# NEW (should be):
content = strand.get('content', {})
entry_context = content.get('entry_context', {})
completed_trades = content.get('completed_trades', [])
```

#### pm_action Strands
**OLD Structure**: Used non-column fields (`token`, `position_id`, `chain` as top-level)

**NEW Structure**:
```python
{
    "id": f"pm_action_{position_id}_{decision_type}_{timestamp}",
    "module": "pm",
    "kind": "pm_action",
    "symbol": token_ticker,
    "timeframe": timeframe,
    "position_id": position_id,  # Top-level column
    "content": {
        "position_id": position_id,  # Also in content
        "token_contract": token_contract,
        "chain": chain,
        "ts": timestamp,
        "decision_type": decision_type,
        "size_frac": size_frac,
        "a_value": a_val,
        "e_value": e_val,
        "reasons": {...},
        "execution_result": {...}  # If available
    },
    "regime_context": {...},  # NEW: Macro/meso/micro phases
    "tags": ["pm_action", "execution", decision_type],
    "target_agent": "learning_system",
    "created_at": timestamp,
    "updated_at": timestamp
}
```

#### social_lowcap Strands
**NEW Additions**:
- `regime_context`: Macro/meso/micro phases (NEW)
- `signal_pack.identification_source`: How token was identified (NEW)
- Removed: Top-level `confidence`, `sig_confidence`, `sig_direction`, `sig_sigma`

#### decision_lowcap Strands
**NEW Additions**:
- `regime_context`: Macro/meso/micro phases (NEW)
- `position_id`: Backfilled after position creation (NEW)
- `content.position_ids`: Array of all 4 position IDs (NEW)
- `content.primary_position_id`: Primary position ID (NEW)
- Removed: Top-level `confidence`, `sig_confidence`, `sig_direction`

### 3. Learning System Code Updates Required ⚠️ **NEEDS FIX**

#### Issue: Reading from Wrong Location
**Files Affected**:
1. `src/intelligence/universal_learning/universal_learning_system.py`:
   - Line 536: `entry_context = strand.get('entry_context', {})` → Should read from `content`
   - Line 537: `completed_trades = strand.get('completed_trades', [])` → Should read from `content`

2. `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py`:
   - Line 260: `entry_context = strand.get('entry_context', {})` → Should read from `content`
   - Line 261: `completed_trades = strand.get('completed_trades', [])` → Should read from `content`

**Fix**:
```python
# In _process_position_closed_strand():
content = strand.get('content', {})
entry_context = content.get('entry_context', {})
completed_trades = content.get('completed_trades', [])

# In process_position_closed_for_braiding():
content = strand.get('content', {})
entry_context = content.get('entry_context', {})
completed_trades = content.get('completed_trades', [])
```

### 4. Legacy Code Removal ✅ **COMPLETE**
- Removed `_is_braid_candidate()` method (checked removed `confidence` column)
- Removed `_mark_as_braid_candidate()` method
- Removed call to these methods in `process_strand_event()`

---

## Updated Testing Plan Checklist

### 1.1 Database Schema Verification

#### ✅ Schema Files Exist
- [x] `ad_strands_schema.sql` - **UPDATED**: Cleaned schema, removed legacy columns
- [x] `ad_strands_schema.sql` - **UPDATED**: Renamed `lifecycle_id` → `position_id`
- [x] `ad_strands_schema.sql` - **UPDATED**: Removed legacy views/triggers/functions
- [ ] All other schemas unchanged

#### ✅ Schema Alignment
- [ ] `position_closed` strands use `content` JSONB for `entry_context` and `completed_trades`
- [ ] `position_closed` strands have `position_id` in top-level column AND in `content`
- [ ] `position_closed` strands have `regime_context` with macro/meso/micro phases
- [ ] `pm_action` strands use `content` JSONB for all PM-specific data
- [ ] `pm_action` strands have `position_id` in top-level column AND in `content`
- [ ] `pm_action` strands have `regime_context` with macro/meso/micro phases
- [ ] `decision_lowcap` strands have `position_id` backfilled after position creation
- [ ] `decision_lowcap` strands have `regime_context` with macro/meso/micro phases
- [ ] `social_lowcap` strands have `regime_context` with macro/meso/micro phases
- [ ] `social_lowcap` strands have `signal_pack.identification_source`

### 1.2 Learning System Implementation

#### ✅ Phase 1: Basic Strand Processing
- [ ] `UniversalLearningSystem.process_strand_event()` handles `kind='position_closed'`
- [ ] **FIX REQUIRED**: `_process_position_closed_strand()` reads `entry_context` and `completed_trades` from `content` JSONB (not top-level)
- [ ] `_update_coefficients_from_closed_trade()` calls coefficient updater
- [ ] Global R/R baseline updates correctly

#### ✅ Braiding System
- [ ] **FIX REQUIRED**: `process_position_closed_for_braiding()` reads `entry_context` and `completed_trades` from `content` JSONB (not top-level)
- [ ] Pattern keys generated correctly
- [ ] Braid stats updated correctly

### 1.4 Portfolio Manager Implementation

#### ✅ Position Closed Strand Emission
- [x] Emits strand with `kind='position_closed'`
- [x] Includes `position_id` in top-level column AND in `content`
- [x] Includes `entry_context` in `content` JSONB (for learning)
- [x] Includes `completed_trades` array in `content` JSONB (for learning)
- [x] Includes `regime_context` with macro/meso/micro phases
- [x] Strand is inserted into `ad_strands` table
- [x] **FIXED**: Learning system processes strand via direct call (not queue)

#### ✅ PM Action Strands
- [x] Emits strands with `kind='pm_action'`
- [x] All PM-specific data in `content` JSONB
- [x] `position_id` in top-level column AND in `content`
- [x] `regime_context` with macro/meso/micro phases
- [x] Proper `id`, `module`, `symbol`, `tags`, `target_agent` fields

### 1.5 Data Flow Verification

#### ✅ Complete Learning Loop
1. [x] **Decision Maker** creates positions with `entry_context` populated
2. [x] **Decision Maker** backfills `position_id` to `decision_lowcap` strand after position creation
3. [x] **PM** executes trades, tracks execution history
4. [x] **PM** detects position closure, computes R/R, writes `completed_trades`
5. [x] **PM** emits `position_closed` strand with proper structure (`content` JSONB)
6. [x] **PM** calls `learning_system.process_strand_event()` directly
7. [ ] **FIX REQUIRED**: **Learning System** reads `entry_context` and `completed_trades` from `content` JSONB
8. [ ] **Learning System** updates coefficients (single-factor + interaction)
9. [ ] **Learning System** updates global R/R baseline
10. [ ] **Decision Maker** uses updated coefficients for next allocation

---

## Updated Test Scenarios

### Test Scenario 1B: Complete Learning Loop Flow Test

**Updated Step 7: Follow to Position Closure**

**OLD Query**:
```sql
SELECT * FROM ad_strands 
WHERE kind = 'position_closed' 
AND position_id = [1h_position_id]
```

**NEW Query** (position_id is now a top-level column):
```sql
SELECT * FROM ad_strands 
WHERE kind = 'position_closed' 
AND position_id = [1h_position_id]
-- OR query by content if needed:
-- WHERE kind = 'position_closed' 
-- AND content->>'position_id' = [1h_position_id]
```

**OLD Assert**:
- `entry_context` (matches position's `entry_context`)
- `completed_trades` (matches position's `completed_trades`)
- `position_id`, `token`, `chain`, `timeframe`

**NEW Assert**:
- `position_id` in top-level column (matches position ID)
- `content->>'entry_context'` (matches position's `entry_context`)
- `content->>'completed_trades'` (matches position's `completed_trades`)
- `content->>'token_contract'` (matches position's token_contract)
- `content->>'chain'` (matches position's token_chain)
- `timeframe` (matches position's timeframe)
- `regime_context` (contains macro/meso/micro phases)

**Updated Step 8: Follow to Learning**

**NEW Verification**:
- Verify learning system can read `entry_context` from `content` JSONB
- Verify learning system can read `completed_trades` from `content` JSONB
- Verify coefficients updated correctly
- Verify global R/R baseline updated correctly

---

## Critical Fixes Applied ✅

### Fix 1: Learning System Reads from content JSONB ✅ **COMPLETE**

**Files Updated**:
1. ✅ `src/intelligence/universal_learning/universal_learning_system.py`:
   - Lines 535-538: Now reads `entry_context` and `completed_trades` from `content` JSONB

2. ✅ `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py`:
   - Lines 259-262: Now reads `entry_context` and `completed_trades` from `content` JSONB

**Code Change Applied**:
```python
# OLD:
entry_context = strand.get('entry_context', {})
completed_trades = strand.get('completed_trades', [])

# NEW (applied):
content = strand.get('content', {})
entry_context = content.get('entry_context', {})
completed_trades = content.get('completed_trades', [])
```

**Status**: ✅ Fixed - Learning system and braiding system now correctly read from `content` JSONB.

---

## Test Data Updates

### Test Scenario 1B: Complete Learning Loop

**Updated Assertions**:

**Step 3: Follow to Positions**
- Verify `decision_lowcap` strand has `position_id` backfilled (after positions created)
- Verify `decision_lowcap.content.position_ids` contains all 4 position IDs
- Verify `decision_lowcap.content.primary_position_id` matches first position ID

**Step 7: Follow to Position Closure**
- Verify `position_closed` strand structure:
  - `position_id` in top-level column
  - `content.entry_context` exists
  - `content.completed_trades` exists
  - `regime_context` exists with macro/meso/micro phases
  - `symbol` (not `token`) in top-level column

**Step 8: Follow to Learning**
- Verify learning system can read from `content` JSONB
- Verify coefficients updated correctly
- Verify braiding system can read from `content` JSONB

---

## Summary

### ✅ Completed
- Schema cleanup (removed legacy columns)
- Strand structure updates (content JSONB, regime_context)
- Position ID backfilling to decision_lowcap strands
- Legacy code removal (braid candidate methods)
- PM → Learning System direct call (not queue)

### ✅ Critical Fix Applied
- [x] **Learning system now reads `entry_context` and `completed_trades` from `content` JSONB** (fixed in `universal_learning_system.py`)
- [x] **Braiding system now reads `entry_context` and `completed_trades` from `content` JSONB** (fixed in `braiding_system.py`)

### 📝 Test Plan Updates
- Update test queries to use `content` JSONB for `entry_context` and `completed_trades`
- Update test assertions to verify `regime_context` exists
- Update test assertions to verify `position_id` backfilling to decision_lowcap strands
- Update test assertions to verify proper strand structure (id, module, symbol, tags, etc.)

---

## Next Steps

1. ✅ **Fix learning system code** to read from `content` JSONB (COMPLETE)
2. ✅ **Fix braiding system code** to read from `content` JSONB (COMPLETE)
3. **Update test queries** to match new strand structure (see updated test scenarios above)
4. **Run Test Scenario 1B** to verify complete learning loop works
5. **Verify regime_context** is populated correctly in all strands
6. **Verify position_id backfilling** works correctly for decision_lowcap strands

---

**Status**: ✅ **READY FOR TESTING** - All critical fixes applied. Learning system and braiding system now correctly read from `content` JSONB.

