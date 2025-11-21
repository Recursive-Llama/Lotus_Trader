# ad_strands Schema Analysis & Recommendations

**Date**: 2025-11-15  
**Status**: Investigation Complete - No Changes Made  
**Purpose**: Understand current usage patterns and identify gaps/misalignments

---

## Executive Summary

The `ad_strands` table is a unified communication table for all modules. This analysis focuses on the **lowcap trading system** (social_ingest, decision_maker, PM) and ignores legacy CIL/RDI/CTP systems.

**Key Finding**: The test query `.eq("position_id", position_id)` fails because `position_id` is not a column. 

**Solution**: Use `lifecycle_id` column (currently unused) and set it to `position_id` for all PM strands. This enables direct querying: `.eq("lifecycle_id", position_id)`.

---

## 1. Position ID Query Issue

### Current Problem

**Test Code** (`test_scenario_1b_v4_learning_verification.py:88`):
```python
.eq("position_id", position_id)  # ❌ This fails - position_id is not a column
```

**PM Code** (`pm_core_tick.py:915-923`):
```python
"content": {
    "position_id": position_id,  # ✅ Correct - in content JSONB
    ...
}
```

**Other Code Examples** (CIL, RDI):
```python
.eq("content->>'position_id'", position_id)  # ✅ Correct JSONB query syntax
```

### Root Cause

The `ad_strands` schema does NOT have a `position_id` column. It's a JSONB field in `content`. The test is using incorrect query syntax.

### Impact

- **Test fails** when trying to find `position_closed` strands
- **Learning system** may not be able to query by position_id if it uses similar syntax
- **PM `pm_action` strands** also use top-level `position_id` (line 1020) which would fail

### Recommendation

1. **Fix test query**: Use `content->>'position_id'` or filter in Python after fetching
2. **Fix PM `pm_action` strands**: Move `position_id` to `content` JSONB (currently at line 1020)
3. **Document query patterns**: Create examples for JSONB field queries

---

## 2. Column Usage Analysis

### ✅ Columns Used Effectively

| Column | Used By | Purpose | Status |
|--------|---------|---------|--------|
| `id` | All | Primary key | ✅ Required |
| `module` | All | Module identifier | ✅ Used |
| `kind` | All | Strand type | ✅ Used |
| `symbol` | All | Trading symbol | ✅ Used |
| `timeframe` | All | Timeframe | ✅ Used |
| `tags` | All | Communication tags | ✅ Used well |
| `target_agent` | All | Target module | ✅ Used |
| `signal_pack` | social_ingest, decision_maker | Token/venue/curator data | ✅ **Used well - important** |
| `content` | All | Module-specific data | ✅ Used (but inconsistently) |
| `parent_id` | decision_maker | Links to social_lowcap | ✅ Used correctly |
| `created_at` | All | Timestamp | ✅ Used |

### ⚠️ Columns That Should Be Used But Aren't

| Column | Should Be Used By | Why | Current Status |
|--------|-------------------|-----|----------------|
| `regime_context` | PM | Should contain micro/meso/macro state | ❌ Not used by PM |
| `module_intelligence` | PM | Could store PM-specific intelligence | ⚠️ Used by decision_maker, not PM |
| `lifecycle_id` | PM | Could link position_closed to pm_action strands | ❌ Not used by PM |
| `parent_id` | PM | Could link position_closed to decision_lowcap | ❌ Not used by PM |

### ❌ Columns Not Used (Potentially Outdated)

| Column | Original Purpose | Current Status | Recommendation |
|--------|------------------|----------------|----------------|
| `sig_sigma` | Signal strength (RDI) | ⚠️ Used by social_ingest, but redundant with `confidence` | **Review** - seems redundant |
| `sig_confidence` | Signal confidence (RDI) | ⚠️ Used by social_ingest, but redundant with `confidence` | **Review** - seems redundant |
| `confidence` | Generic confidence | ⚠️ Used by social_ingest | **Keep** - generic is better |
| `sig_direction` | Direction (long/short) | ⚠️ Used by social_ingest | **Keep** - useful |
| `trading_plan` | Trading plan data | ❌ Not used | **Remove or repurpose** |
| `dsi_evidence` | DSI evidence | ❌ Not used | **Remove or repurpose** |
| `event_context` | Event context | ❌ Not used | **Remove or repurpose** |
| `curator_feedback` | Curator evaluation | ❌ Not used | **Remove or repurpose** |

### ❌ Legacy System Columns (CIL/RDI/CTP - To Be Archived)

These columns are for legacy systems (CIL, RDI, CTP) that should be archived:

- `resonance_score` - CIL resonance
- `strategic_meta_type` - CIL meta-signals
- `team_member` - CIL team structure
- `agent_id` - CIL agent identifier
- `experiment_id` - CIL experiments
- `doctrine_status` - CIL doctrine
- `prediction_score` - CIL predictions
- `outcome_score` - CIL outcomes
- `telemetry` - CIL resonance metrics
- `motif_id`, `motif_name`, `motif_family` - RDI motifs
- `pattern_type` - RDI patterns
- `autonomy_level` - CIL autonomy
- `directive_type` - CIL directives

**Recommendation**: Archive these legacy systems. They're creating confusion and not used by lowcap trading modules.

---

## 3. Module-Specific Strand Patterns

### social_lowcap Strands

**Structure**:
```python
{
    "id": "...",
    "module": "social_ingest",
    "kind": "social_lowcap",
    "symbol": token['ticker'],
    "timeframe": None,
    "session_bucket": "...",
    "tags": ["curated", "social_signal", "dm_candidate"],
    "target_agent": "decision_maker_lowcap",
    "sig_confidence": trading_confidence,  # ⚠️ Redundant?
    "confidence": token_confidence,
    "sig_direction": trading_action,
    "signal_pack": {  # ✅ Used well
        "token": {...},
        "venue": {...},
        "curator": {...},
        "intent_analysis": {...}
    },
    "content": {  # ✅ Also used
        "curator_id": "...",
        "message": {...},
        ...
    }
}
```

**Assessment**: ✅ **Good structure** - uses `signal_pack` for structured data, `content` for additional context.

### decision_lowcap Strands

**Structure**:
```python
{
    "id": "...",
    "module": "decision_maker",
    "kind": "decision_lowcap",
    "symbol": "...",
    "parent_id": social_signal.get('id'),  # ✅ Links to social_lowcap
    "signal_pack": social_signal.get('signal_pack'),  # ✅ Inherits from social
    "module_intelligence": social_signal.get('module_intelligence'),
    "content": {  # ✅ Decision-specific data
        "source_kind": "social_lowcap",
        "source_strand_id": "...",
        "action": "approve" | "reject",
        "allocation_pct": ...,
        "reasoning": "..."
    },
    "tags": ["decision", "social_lowcap", "approved"]
}
```

**Assessment**: ✅ **Good structure** - uses `parent_id` for hierarchy, inherits `signal_pack`, adds decision data to `content`.

### pm_action Strands

**Structure** (Current - **PROBLEMATIC**):
```python
{
    "kind": "pm_action",
    "token": token,  # ❌ Not a column!
    "position_id": position_id,  # ❌ Not a column!
    "timeframe": timeframe,
    "chain": chain,  # ❌ Not a column!
    "ts": now.isoformat(),
    "decision_type": ...,
    "size_frac": ...,
    ...
}
```

**Assessment**: ❌ **BAD** - Uses top-level fields that don't exist in schema. This will fail or be ignored.

**Should Be**:
```python
{
    "id": "...",
    "module": "pm",
    "kind": "pm_action",
    "symbol": token_ticker,
    "timeframe": timeframe,
    "parent_id": decision_strand_id,  # ✅ Link to decision_lowcap
    "lifecycle_id": position_id,  # ✅ Use lifecycle_id as position_id for querying
    "content": {  # ✅ All PM-specific data here
        "position_id": position_id,
        "token_contract": token,
        "chain": chain,
        "ts": now.isoformat(),
        "decision_type": ...,
        "size_frac": ...,
        "a_value": ...,
        "e_value": ...,
        "execution_result": {...}
    },
    "tags": ["pm_action", "execution"],
    "target_agent": "learning_system"
}
```

### position_closed Strands

**Structure** (Current):
```python
{
    "id": "...",
    "module": "pm",
    "kind": "position_closed",
    "symbol": token_ticker,
    "timeframe": timeframe,
    "content": {  # ✅ Correct - in content
        "position_id": position_id,
        "token_contract": ...,
        "chain": ...,
        "entry_context": {...},
        "completed_trades": [...],
        "decision_type": ...
    },
    "tags": ["position_closed", "pm", "learning"],
    "target_agent": "learning_system"
}
```

**Assessment**: ✅ **Good structure** - but could be improved:
- Add `parent_id` to link to last `pm_action` strand
- Add `lifecycle_id = position_id` to enable direct querying
- Consider using `signal_pack` for structured trade data (like social uses it for token data)

---

## 4. Recommendations

### Immediate Fixes (Critical)

1. **Fix PM `pm_action` strands** (`pm_core_tick.py:1018-1045`):
   - Move `position_id`, `chain`, `token` to `content` JSONB
   - Add proper `id`, `module`, `symbol` fields
   - Add `parent_id` to link to `decision_lowcap` strand
   - Add `lifecycle_id` to group all PM actions for a position

2. **Fix test queries**:
   - Change `.eq("position_id", ...)` to `.eq("content->>'position_id'", ...)`
   - Or fetch all `position_closed` strands and filter in Python

3. **Fix learning system queries**:
   - Check if learning system queries `position_id` - update to use JSONB syntax

### Short-Term Improvements

1. **Use `lifecycle_id` as `position_id` for PM strands**:
   - Set `lifecycle_id = position_id` for all PM strands related to a position
   - Enables easy querying: `.eq("lifecycle_id", position_id)`
   - **Note**: `lifecycle_id` is currently unused, so this is safe to repurpose

2. **Use `parent_id` for strand hierarchy**:
   - `position_closed` → `parent_id` = last `pm_action` strand
   - `pm_action` → `parent_id` = `decision_lowcap` strand
   - `decision_lowcap` → `parent_id` = `social_lowcap` strand

3. **Use `regime_context` for PM state**:
   - Store micro/meso/macro phase state in `regime_context` JSONB
   - Enables regime-based learning

4. **Consider `signal_pack` for structured trade data**:
   - Similar to how social uses it for token/venue data
   - Could contain: entry_context, completed_trades summary, etc.

### Long-Term Schema Cleanup

1. **Review redundant columns**:
   - `sig_sigma` vs `confidence` - consolidate
   - `sig_confidence` vs `confidence` - consolidate
   - Keep generic `confidence`, remove signal-specific ones

2. **Remove unused columns** (after confirming no usage):
   - `trading_plan` - not used
   - `dsi_evidence` - not used
   - `event_context` - not used
   - `curator_feedback` - not used

3. **Document column purposes**:
   - Create clear documentation on which columns are for which modules
   - CIL columns vs Lowcap columns vs Generic columns

---

## 5. Query Patterns

### Current (Incorrect)
```python
# ❌ Fails - position_id is not a column
.eq("position_id", position_id)
```

### Correct JSONB Query
```python
# ✅ Correct - queries JSONB field
.eq("content->>'position_id'", position_id)
```

### Recommended: Use lifecycle_id
```python
# ✅ Best - use lifecycle_id = position_id for all PM strands
.eq("lifecycle_id", position_id)
```

### Filter in Python (Simple but less efficient)
```python
# ✅ Works but less efficient
strands = sb.table("ad_strands").select("*").eq("kind", "position_closed").execute()
matching = [s for s in strands.data if s.get("content", {}).get("position_id") == position_id]
```

---

## 6. Questions to Resolve

1. **Should `position_id` be queryable directly?**
   - ✅ **DECIDED**: Use `lifecycle_id = position_id` for all PM strands
   - This enables direct querying: `.eq("lifecycle_id", position_id)`
   - `lifecycle_id` is currently unused, so safe to repurpose
   - Also keep `position_id` in `content` JSONB for reference

2. **Should PM use `signal_pack`?**
   - Social uses it for token/venue/curator data
   - PM could use it for entry_context/completed_trades
   - Would provide consistency across modules

3. **Should PM use `regime_context`?**
   - Currently unused by PM
   - Could store micro/meso/macro phase state
   - Would enable regime-based learning

4. **Should we clean up redundant columns?**
   - `sig_sigma`, `sig_confidence` vs `confidence`
   - Need to check if any code depends on these

---

## 7. Action Plan

### Phase 1: Critical Fixes (Do First)
- [ ] Fix PM `pm_action` strand structure (move fields to `content`)
- [ ] Fix test query to use JSONB syntax
- [ ] Verify learning system can find `position_closed` strands

### Phase 2: Improvements (Do Next)
- [ ] Add `lifecycle_id` to PM strands for position tracking
- [ ] Add `parent_id` to PM strands for hierarchy
- [ ] Document proper strand structure patterns

### Phase 3: Schema Cleanup (Do Later)
- [ ] Review and consolidate redundant columns
- [ ] Remove truly unused columns
- [ ] Add indexes for JSONB queries if needed

---

## Conclusion

The main issue is **inconsistent usage** of the schema. Some modules (social, decision) use it correctly with JSONB fields, while PM is trying to use non-existent top-level columns. The fix is straightforward: move PM-specific data to `content` JSONB and use proper query syntax.

The schema itself is mostly fine - it's a unified table for all modules, which is good. The issue is that different modules have different needs, and we need to use the schema consistently.

