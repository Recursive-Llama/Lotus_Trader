# ad_strands Schema Implementation Summary

**Date**: 2025-11-15  
**Status**: Implementation Complete - Ready for Testing  
**Changes**: Schema cleaned, code updated, redundant columns removed

---

## ✅ Changes Implemented

### 1. Schema Updates
- ✅ Created cleaned `ad_strands` schema (removed 40+ legacy columns)
- ✅ Renamed `lifecycle_id` → `position_id`
- ✅ Removed: `sig_sigma`, `sig_confidence`, `confidence`, `sig_direction` (top-level)
- ✅ Removed: All CIL/RDI/CTP legacy columns
- ✅ Removed: Legacy views, triggers, functions

### 2. PM Code Updates
- ✅ Fixed `pm_action` strands to use proper schema structure
- ✅ All PM-specific data now in `content` JSONB (including `position_id`)
- ✅ `position_id` also in top-level column for querying
- ✅ Added `_get_regime_context()` method to fetch macro/meso/micro phases
- ✅ All PM strands now include `regime_context` with macro/meso/micro
- ✅ Fixed `position_closed` strands to include `position_id` and `regime_context`

### 3. Social Ingest Updates
- ✅ Removed: `sig_sigma`, `sig_confidence`, `confidence`, `sig_direction` (top-level)
- ✅ Changed `_calculate_token_confidence()` → `_calculate_token_identification_source()`
- ✅ Returns identification source: "contract_address", "ticker_exact", "ticker_approximate", "ticker_bare"
- ✅ Added `identification_source` to `signal_pack`
- ✅ Removed `confidence` from `content` JSONB

### 4. Decision Maker Updates
- ✅ Removed: `sig_confidence`, `sig_direction`, `confidence` (top-level)
- ✅ Cleaned up approval and rejection decision strands

---

## 📊 Column Usage Review & Suggestions

### social_ingest (social_lowcap strands)

**Current Usage:**
- ✅ `id`, `module`, `kind`, `symbol` - Used correctly
- ✅ `timeframe` - Set to `None` (not applicable) - **Correct**
- ✅ `session_bucket` - Used for hourly sessions - **Good**
- ✅ `tags` - Used for communication - **Good**
- ✅ `target_agent` - Set to "decision_maker_lowcap" - **Good**
- ✅ `parent_id` - Not set (no parent) - **Correct**
- ✅ `signal_pack` - **Excellent usage**:
  - Token data (ticker, contract, chain, price, volume, market_cap, liquidity, dex)
  - Venue data (dex, chain, liq_usd, vol24h_usd)
  - Curator data (id, name, platform, handle, weight, priority, tags)
  - Trading signals (action, timing, confidence)
  - Intent analysis
  - **NEW**: `identification_source` (how token was identified)
  - Health metrics (volume_health, liquidity_health, liq_mcap_ratio)
  - Mapping metadata (mapping_reason, confidence_grade, mapping_status)
- ✅ `content` - Minimal (summary, curator_id, platform, token_ticker) - **Appropriate**
- ✅ `module_intelligence` - Stores social signal metadata (message, context_slices) - **Good**
- ⚠️ `regime_context` - **NOT SET** - Could be useful for regime-based filtering
- ⚠️ `position_id` - **NOT SET** - Could be backfilled after position creation
- ✅ `status` - Set to "active" - **Good**

**Suggestions:**
1. **`regime_context`**: Consider adding macro/meso/micro phases to social signals for regime-based filtering in decision_maker. This would allow DM to consider market regime when making allocation decisions.
2. **`position_id`**: Can be backfilled after position creation (via decision_lowcap → position link)

**Verdict**: ✅ **Excellent usage** - `signal_pack` is well-structured, `content` is minimal and appropriate. Only minor enhancement would be adding `regime_context` for regime-based filtering.

---

### decision_maker_lowcap (decision_lowcap strands)

**Current Usage:**
- ✅ `id`, `module`, `kind`, `symbol` - Used correctly
- ✅ `session_bucket` - Inherited from social_signal - **Good**
- ✅ `tags` - Used for communication - **Good**
- ✅ `parent_id` - Links to `social_lowcap` strand - **Perfect**
- ✅ `signal_pack` - Inherited from social_signal - **Good** (keeps all token/venue/curator data)
- ✅ `module_intelligence` - Inherited from social_signal - **Good**
- ✅ `content` - **Well-structured**:
  - Decision-specific data (action, allocation_pct, allocation_usd, curator_confidence, reasoning)
  - Source tracking (source_kind, source_strand_id, curator_id)
  - Token/venue data (for backward compatibility)
  - Portfolio context (available_capacity_pct, planned_positions, current_exposure_pct, book_nav)
- ⚠️ `regime_context` - **NOT SET** - Could be useful for regime-based learning
- ⚠️ `position_id` - **NOT SET** - Could be set after position creation
- ✅ `status` - Set to "active" - **Good**

**Suggestions:**
1. **`regime_context`**: Add macro/meso/micro phases when making decisions. This would enable regime-based learning (e.g., "curator X performs better in euphoria phase").
2. **`position_id`**: Can be backfilled after position creation (decision_lowcap → position link exists)

**Verdict**: ✅ **Very good usage** - `content` is well-structured with decision-specific data. `signal_pack` inheritance is clean. Only enhancement would be adding `regime_context` for regime-based learning.

---

### PM (pm_action and position_closed strands)

**Current Usage:**
- ✅ `id`, `module`, `kind`, `symbol` - Used correctly
- ✅ `timeframe` - Set correctly - **Good**
- ✅ `tags` - Used for communication - **Good**
- ✅ `target_agent` - Set to "learning_system" - **Good**
- ✅ `position_id` - **NOW SET** in top-level column AND in `content` - **Perfect**
- ✅ `content` - **Well-structured**:
  - All PM-specific operational data (position_id, token_contract, chain, ts, decision_type, size_frac, a_value, e_value, reasons, execution_result)
- ✅ `regime_context` - **NOW INCLUDED** with macro/meso/micro phases - **Perfect**
- ✅ `status` - Not explicitly set (defaults to "active") - **Fine**

**Suggestions:**
1. **`parent_id`**: Could link `pm_action` strands to `decision_lowcap` strand for full traceability (social_lowcap → decision_lowcap → pm_action → position_closed)
2. **`position_closed` strands**: Already have `parent_id`? Check if we should link to the decision_lowcap strand that created the position

**Verdict**: ✅ **Excellent usage** - All PM-specific data in `content`, `regime_context` now included, `position_id` properly set. Structure is clean and queryable.

---

## 🔍 Issues Found

### 1. Legacy Code References
- `universal_learning_system.py` line 867: Checks `strand.get('confidence')` for braid candidates
- This is legacy code for old CIL/RDI system
- **Action**: Update `_is_braid_candidate()` to not rely on removed columns, or remove if unused by lowcap system

### 2. Missing Fields
- `decision_maker_lowcap` strands don't have `created_at`/`updated_at` explicitly set (may default)
- **Action**: Add explicit timestamps for consistency

---

## 📝 Recommendations

### High Value Additions

1. **Add `regime_context` to social_ingest strands**:
   - Would enable regime-based filtering in decision_maker
   - Low effort, high value for learning

2. **Add `regime_context` to decision_maker strands**:
   - Would enable regime-based learning (e.g., "curator X performs better in euphoria")
   - Low effort, high value for learning

3. **Link `pm_action` strands to `decision_lowcap` via `parent_id`**:
   - Would create full traceability chain: social_lowcap → decision_lowcap → pm_action → position_closed
   - Medium effort, high value for debugging and learning

### Low Priority

4. **Add explicit `created_at`/`updated_at` to decision_maker strands**:
   - Currently may rely on database defaults
   - Low effort, minor value

---

## ✅ Summary

**Overall Assessment**: The modules are using the columns **very well**. The structure is clean and appropriate:

- **social_ingest**: Excellent use of `signal_pack` for structured data, minimal `content` for operational data
- **decision_maker**: Good inheritance of `signal_pack`, well-structured `content` for decision data
- **PM**: Perfect use of `content` for operational data, now includes `regime_context`

**Main Enhancement Opportunity**: Add `regime_context` to social_ingest and decision_maker strands for regime-based learning. This is the only significant improvement I'd suggest.

**Everything else is working well** - no changes needed for the sake of it.

