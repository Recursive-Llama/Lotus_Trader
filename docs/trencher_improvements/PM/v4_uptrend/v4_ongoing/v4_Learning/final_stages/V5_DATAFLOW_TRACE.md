# v5 Learning System Dataflow Trace

**Purpose**: Verify end-to-end dataflow from action logging → aggregation → lessons → overrides → runtime application

**Date**: 2025-01-XX

---

## Dataflow Overview

```
1. PM Action → ad_strands (pm_action) with v5 fields
2. Position Close → ad_strands (position_closed) with completed_trades
3. Aggregator → Reads position_closed, extracts v5 fields → pattern_scope_stats
4. Lesson Builder → Reads pattern_scope_stats → learning_lessons
5. Override Materializer → Reads learning_lessons → learning_configs.pm.config_data
6. Runtime → PM reads config, applies overrides in plan_actions_v4
```

---

## Step 1: Action Logging ✅

**Location**: `pm_core_tick.py:_write_strands()`

**What happens**:
1. PM executes action (add/trim/exit)
2. Generates `pattern_key` via `generate_canonical_pattern_key()`
3. Extracts `action_category` from decision_type
4. Extracts `scope` via `extract_scope_from_context()`
5. Extracts `controls` (signals + applied_knobs) via `extract_controls_from_action()`
6. Writes to `ad_strands` with:
   - `kind = "pm_action"`
   - `content.pattern_key`
   - `content.action_category`
   - `content.scope`
   - `content.controls`

**Status**: ✅ **WORKING** - v5 fields are logged correctly

**Code Reference**:
- Lines 1163-1211: Pattern key generation and scope extraction
- Lines 1234-1241: v5 fields added to content_data
- Lines 1256-1271: Strand written to ad_strands

---

## Step 2: Position Closure ✅

**Location**: `pm_core_tick.py:_check_position_closure()`

**What happens**:
1. PM detects full exit (total_quantity == 0)
2. Calculates R/R metrics from OHLCV
3. Creates `trade_summary` with R/R, outcome_class, etc.
4. Appends to `completed_trades` array
5. Writes `position_closed` strand to `ad_strands` with:
   - `kind = "position_closed"`
   - `content.completed_trades` (array of trade entries)
   - `content.entry_context`
   - `regime_context` (macro/meso/micro phases)

**Status**: ✅ **WORKING** - Position closure is logged

**Issue**: ⚠️ `completed_trades` entries don't include v5 fields (pattern_key, action_category, scope)

**Code Reference**:
- Lines 1010-1033: trade_summary creation
- Lines 1047-1068: position_closed strand creation

---

## Step 3: Aggregation ⚠️

**Location**: `pattern_scope_aggregator.py`

**What happens**:
1. Reads `position_closed` strands from `ad_strands`
2. Extracts `completed_trades` array
3. For each trade entry:
   - **Tries to read v5 fields** (`pattern_key`, `action_category`, `scope`)
   - **If missing, reconstructs** from `action_context` (fallback logic)
   - Generates all scope subset masks (k=1 to k=10)
   - Computes stats (n, avg_rr, variance, edge_raw) per subset
   - Upserts to `pattern_scope_stats`

**Status**: ⚠️ **PARTIALLY WORKING** - Has fallback logic but fragile

**Issues**:
1. `completed_trades` entries don't have v5 fields directly
2. Fallback reconstruction from `action_context` may fail if context is incomplete
3. Better approach: Link `pm_action` strands to `position_closed` by position_id

**Code Reference**:
- Lines 334-620: `process_position_closed_strand()`
- Lines 388-426: v5 field extraction with fallback
- Lines 432-565: Scope subset generation and stats computation

**Recommendation**: 
- Option A: Include v5 fields in `completed_trades` entries when PM creates them
- Option B: Aggregator reads `pm_action` strands and matches to `position_closed` by position_id

---

## Step 4: Lesson Building ✅

**Location**: `lesson_builder_v5.py`

**What happens**:
1. Reads `pattern_scope_stats` for candidates (n >= N_min, |edge_raw| >= edge_min)
2. Groups by `(pattern_key, action_category)`
3. Finds simplest scope subset with sufficient edge
4. Computes incremental edge vs parent subsets
5. Estimates half-life (v5.2) from `learning_edge_history`
6. Checks latent factor (v5.3) to avoid duplicates
7. Maps edge → capital + execution levers
8. Writes to `learning_lessons` with full payload

**Status**: ✅ **WORKING** - Correctly reads from pattern_scope_stats

**Code Reference**:
- Lines 328-583: `build_lessons_from_pattern_scope_stats()`
- Lines 167-274: `map_edge_to_levers()` - maps edge to lever payloads

---

## Step 5: Override Materialization ✅

**Location**: `override_materializer.py`

**What happens**:
1. Reads active lessons from `learning_lessons` (status='active')
2. Groups by `latent_factor_id` (v5.3) to merge duplicates
3. Applies decay (v5.2) based on half-life and lesson age
4. Merges levers from duplicate patterns
5. Writes to `learning_configs.pm.config_data`:
   - `pattern_strength_overrides` (capital levers)
   - `pattern_overrides` (execution levers)

**Status**: ✅ **WORKING** - Correctly materializes lessons to config

**Code Reference**:
- Lines 134-350: `materialize_overrides()`
- Lines 21-50: `apply_decay()` - v5.2 decay logic
- Lines 52-131: `merge_latent_factor_levers()` - v5.3 merging

---

## Step 6: Runtime Application ✅

**Location**: `pm/actions.py` and `pm/overrides.py`

**What happens**:
1. `plan_actions_v4()` creates action
2. Calls `_apply_v5_overrides_to_action()` helper
3. Generates `pattern_key` and extracts `scope` (same as logging)
4. Calls `apply_pattern_strength_overrides()` - adjusts size_frac
5. Calls `apply_pattern_execution_overrides()` - adjusts controls
6. Override functions:
   - Load config from `learning_configs.pm.config_data`
   - Match by `pattern_key` + `action_category` + scope subset
   - Apply levers with bounds checking
   - Return adjusted values

**Status**: ✅ **WORKING** - Overrides are applied at runtime

**Code Reference**:
- `pm/actions.py` Lines 44-162: `_apply_v5_overrides_to_action()`
- `pm/overrides.py` Lines 133-220: `apply_pattern_strength_overrides()`
- `pm/overrides.py` Lines 223-320: `apply_pattern_execution_overrides()`

---

## Critical Gap Identified ⚠️

**Issue**: Step 3 (Aggregation) has a data quality issue

**Problem**: 
- `completed_trades` entries in `position_closed` strands don't include v5 fields
- Aggregator relies on fallback reconstruction from `action_context`
- This is fragile and may fail if `action_context` is incomplete

**Impact**: 
- Some trades may not be aggregated correctly
- Pattern scope stats may be incomplete
- Lessons may miss some patterns

**Solution Options**:

### Option A: Include v5 Fields in completed_trades (Recommended)
When PM creates `completed_trades` entries, include the v5 fields from the original `pm_action` strands.

**Changes needed**:
- In `pm_core_tick.py:_check_position_closure()`, when creating `trade_summary`, include:
  - `pattern_key` (from original pm_action strands)
  - `action_category` (from original pm_action strands)
  - `scope` (from original pm_action strands)
  - `controls` (from original pm_action strands)

**How to get v5 fields**:
- Query `ad_strands` for `pm_action` strands with same `position_id`
- Extract v5 fields from those strands
- Include in `trade_summary`

### Option B: Aggregator Reads pm_action Strands
Modify aggregator to:
1. Read `position_closed` strand for R/R
2. Query `pm_action` strands for same `position_id`
3. Match actions to trades
4. Use v5 fields from `pm_action` strands directly

**Pros**: More robust, direct access to v5 fields
**Cons**: More complex matching logic

---

## Verification Checklist

- [x] Step 1: Action logging emits v5 fields
- [x] Step 2: Position closure creates position_closed strands
- [⚠️] Step 3: Aggregator can extract v5 fields (has fallback)
- [x] Step 4: Lesson builder reads pattern_scope_stats
- [x] Step 5: Override materializer writes to config
- [x] Step 6: Runtime applies overrides

**Overall Status**: ✅ **MOSTLY WORKING** - One gap in Step 3 that should be fixed

---

## Next Steps

1. **Fix Step 3**: Implement Option A (include v5 fields in completed_trades)
2. **Test end-to-end**: Run validator and check data flows correctly
3. **Monitor**: Watch for missing v5 fields in aggregator logs

