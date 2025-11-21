# ad_strands: Columns Actually Needed

**Date**: 2025-11-15  
**Status**: Analysis - No Changes Yet  
**Focus**: Lowcap trading system only (social_ingest, decision_maker, PM)

---

## What Lowcap System Actually Uses

### ✅ Required Columns (Keep)

| Column | Used By | Purpose |
|--------|---------|---------|
| `id` | All | Primary key |
| `module` | All | Module identifier |
| `kind` | All | Strand type (`social_lowcap`, `decision_lowcap`, `pm_action`, `position_closed`) |
| `symbol` | All | Token symbol/ticker |
| `timeframe` | All | Timeframe (`1m`, `15m`, `1h`, `4h`) |
| `tags` | All | Communication tags (JSONB array) |
| `target_agent` | All | Target module for communication |
| `created_at` | All | Timestamp |
| `updated_at` | All | Last update timestamp |
| `content` | All | Module-specific data (JSONB) |
| `parent_id` | decision_maker | Links to parent strand (social_lowcap → decision_lowcap) |
| `signal_pack` | social_ingest, decision_maker | Structured token/venue/curator data (JSONB) |
| `session_bucket` | social_ingest, decision_maker | Session identifier |
| `confidence` | social_ingest, decision_maker | Generic confidence score (0-1) |
| `sig_direction` | social_ingest, decision_maker | Direction (`buy`, `sell`, `long`, `short`) |
| `module_intelligence` | decision_maker | Module-specific intelligence (JSONB) |
| `status` | decision_maker | Strand status (`active`, `inactive`, etc.) |
| `lifecycle_id` | **PM (planned)** | Use as `position_id` for PM strands |

### ❌ Remove (Legacy/Unused)

**Legacy CIL/RDI/CTP Columns:**
- `resonance_score` - CIL resonance
- `strategic_meta_type` - CIL meta-signals
- `team_member` - CIL team structure
- `agent_id` - CIL agent identifier
- `experiment_id` - CIL experiments
- `doctrine_status` - CIL doctrine
- `prediction_score` - CIL predictions
- `outcome_score` - CIL outcomes
- `telemetry` - CIL resonance metrics
- `resonance_updated_at` - CIL timestamp
- `motif_id`, `motif_name`, `motif_family` - RDI motifs
- `pattern_type` - RDI patterns
- `autonomy_level` - CIL autonomy
- `directive_type` - CIL directives

**Redundant/Unused Columns:**
- `sig_sigma` - Signal strength (used but redundant - can use `confidence`)
- `sig_confidence` - Signal confidence (redundant with `confidence` - **REMOVE**)
- `trading_plan` - Not used
- `dsi_evidence` - Not used
- `event_context` - Not used
- `curator_feedback` - Not used
- `regime` - Not used by lowcap
- `accumulated_score` - Not used
- `lesson` - Not used
- `braid_level` - Not used (braids are in separate table)
- `resonance_scores` - Not used (legacy)
- `historical_metrics` - Not used (legacy)
- `processed` - Not used
- `braid_candidate` - Not used (legacy)
- `quality_score` - Not used (legacy)
- `persistence_score` - Not used (legacy)
- `novelty_score` - Not used (legacy)
- `surprise_rating` - Not used (legacy)
- `cluster_key` - Not used (legacy)
- `strength_range` - Not used (legacy)
- `rr_profile` - Not used (legacy)
- `market_conditions` - Not used (legacy)
- `prediction_data` - Not used (legacy)
- `outcome_data` - Not used (legacy)
- `max_drawdown` - Not used (legacy)
- `tracking_status` - Not used (legacy)
- `plan_version` - Not used (legacy)
- `replaces_id` - Not used (legacy)
- `replaced_by_id` - Not used (legacy)
- `context_vector` - Not used (legacy)
- `feature_version` - Not used (legacy)
- `derivation_spec_id` - Not used (legacy)
- `metadata` - Not used

**Legacy Tables to Remove:**
- `module_resonance_scores` - Not used
- `pattern_evolution` - Not used (only legacy RDI reference)

**Legacy Views to Remove:**
- `rdi_strands` - Not used
- `cil_strands` - Not used
- `ctp_strands` - Not used
- `dm_strands` - Not used (legacy, not decision_lowcap)
- `td_strands` - Not used
- `braid_candidates` - Not used (uses legacy columns)

**Legacy Triggers/Functions to Remove:**
- `notify_ad_strands_update` - Not used
- `trigger_learning_system` - Not used
- `calculate_module_resonance_scores` - Not used

**Keep These Views (Lowcap):**
- `social_lowcap_strands` - Useful
- `decision_lowcap_strands` - Useful
- `pm_action_strands` - Useful

---

## Questions to Resolve

1. **`sig_sigma`** - Used by social_ingest but seems redundant with `confidence`. Remove or keep?
2. **`regime_context`** - Not currently used by PM, but could be useful for regime-based learning. Keep for future use?
3. **`metadata`** - Not used, but might be useful for future extensibility. Keep or remove?

---

## Minimal Schema (What We Actually Need)

```sql
CREATE TABLE ad_strands (
    -- REQUIRED FIELDS
    id TEXT PRIMARY KEY,
    module TEXT DEFAULT 'alpha',
    kind TEXT,  -- 'social_lowcap'|'decision_lowcap'|'pm_action'|'position_closed'
    symbol TEXT,
    timeframe TEXT,  -- '1m'|'5m'|'15m'|'1h'|'4h'|'1d'
    tags JSONB,
    target_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- HIERARCHY
    lifecycle_id TEXT,  -- Use as position_id for PM strands
    parent_id TEXT,     -- Link to parent strand
    
    -- SIGNAL DATA
    confidence FLOAT8,      -- Generic confidence (0-1)
    sig_direction TEXT,     -- 'buy'|'sell'|'long'|'short'
    
    -- DATA FIELDS
    signal_pack JSONB,      -- Structured token/venue/curator data
    content JSONB,          -- Module-specific data
    module_intelligence JSONB,  -- Module-specific intelligence
    regime_context JSONB,   -- Regime context (for future use)
    
    -- METADATA
    session_bucket TEXT,    -- Session identifier
    status VARCHAR(20) DEFAULT 'active'  -- Strand status
);
```

---

## Current Issues

1. **PM `pm_action` strands** - Using non-column fields (`token`, `position_id`, `chain` as top-level)
2. **PM `position_closed` strands** - Missing `lifecycle_id = position_id`
3. **Code using `sig_confidence`** - Need to update to use `confidence` only

---

## Next Steps

1. ✅ Verify what's actually used (done)
2. ⏳ Decide on `sig_sigma` and `regime_context`
3. ⏳ Create cleaned schema
4. ⏳ Update PM code to use proper structure
5. ⏳ Update social_ingest/decision_maker to remove `sig_confidence`

