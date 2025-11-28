# ad_strands Schema Changes - Complete Plan

**Date**: 2025-11-15  
**Status**: Planning - Ready for Implementation  
**Focus**: Clean up schema for lowcap system, remove legacy CIL/RDI/CTP

---

## Summary of Changes

### 1. Remove Legacy Columns (CIL/RDI/CTP)
### 2. Remove Redundant Columns
### 3. Fix Column Usage Issues
### 4. Add Missing Data to signal_pack
### 5. Update Code to Use Correct Structure

---

## Part 1: Remove Legacy Columns

### CIL (Central Intelligence Layer) Columns - REMOVE
- `resonance_score` - Mathematical resonance score
- `strategic_meta_type` - Type of strategic meta-signal
- `team_member` - Team member that created this strand (redundant - we have `module` column)
- `agent_id` - Agent team identifier (redundant - we have `module` column)
- `experiment_id` - Experiment ID for tracking
- `doctrine_status` - Doctrine status
- `prediction_score` - How accurate was the prediction
- `outcome_score` - How well was it executed
- `telemetry` - Resonance metrics
- `resonance_updated_at` - Timestamp for resonance updates
- `autonomy_level` - Agent autonomy
- `directive_type` - CIL directive type

### RDI (Raw Data Intelligence) Columns - REMOVE
- `motif_id` - Motif identifier
- `motif_name` - Motif name
- `motif_family` - Motif family classification
- `pattern_type` - Pattern type classification

### Unused Learning System Columns - REMOVE
- `accumulated_score` - Accumulated performance score
- `lesson` - LLM-generated lesson
- `braid_level` - Learning hierarchy level (braids are in separate table)
- `persistence_score` - How reliable/consistent is this pattern
- `novelty_score` - How unique/new is this pattern
- `surprise_rating` - How unexpected was this outcome
- `cluster_key` - Clustering assignments
- `strength_range` - Pattern strength classification
- `rr_profile` - Risk/reward profile classification
- `market_conditions` - Market conditions classification
- `prediction_data` - Prediction tracking data
- `outcome_data` - Outcome analysis data
- `max_drawdown` - Maximum drawdown for trading strands
- `tracking_status` - Prediction tracking status
- `plan_version` - Plan version for evolution tracking
- `replaces_id` - ID of strand this replaces
- `replaced_by_id` - ID of strand that replaces this
- `context_vector` - Vector embedding for similarity search
- `resonance_scores` - Calculated resonance values
- `historical_metrics` - Historical accuracy, performance data
- `processed` - Learning system processing status
- `braid_candidate` - Candidate for braid creation
- `quality_score` - Overall quality score
- `feature_version` - Feature version for auditable clustering
- `derivation_spec_id` - Derivation spec ID for re-derivation

### Unused Data Columns - REMOVE
- `trading_plan` - Not used by lowcap system
- `dsi_evidence` - Not used
- `event_context` - Not used
- `curator_feedback` - Not used
- `regime` - Not used by lowcap (use `regime_context` JSONB instead)
- `metadata` - Not used (but keep for extensibility - see below)

---

## Part 2: Remove Redundant Columns

### `confidence` - REMOVE
- **Current**: Top-level column storing LLM extraction confidence (0.0-1.0)
- **Action**: Remove column - useful data should go in `signal_pack`, not top-level columns
- **Files to update**:
  - `src/intelligence/social_ingest/social_ingest_basic.py` (line 1150)
  - `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py` (lines 640, 731)

### `sig_confidence` - REMOVE
- **Current**: Used by social_ingest and decision_maker, but redundant
- **Action**: Remove column
- **Files to update**:
  - `src/intelligence/social_ingest/social_ingest_basic.py` (line 1149)
  - `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py` (lines 638, 729)

### `sig_sigma` - REMOVE
- **Current**: Used by social_ingest but redundant
- **Action**: Remove column
- **Files to update**:
  - `src/intelligence/social_ingest/social_ingest_basic.py` (line 1148)

### `sig_direction` - REMOVE
- **Current**: Direction from LLM trading signals ("buy", "sell") - stored but never actually used
- **Action**: Remove column - if needed in future, can be stored in `signal_pack.trading_signals.action`
- **Files to update**:
  - `src/intelligence/social_ingest/social_ingest_basic.py` (line 1151)
  - `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py` (lines 639, 730)

---

## Part 3: Fix Column Usage Issues

### `confidence` Column - MOVE TO signal_pack
- **Current**: Top-level column storing LLM extraction confidence (0.0-1.0 float)
- **Issue**: Token identification confidence (calculated at line 418) is NOT stored anywhere
- **Action**: 
  1. Store token identification confidence in `signal_pack.token_identification_confidence` (string: "highest", "high", "medium", "low")
  2. Keep top-level `confidence` for now (LLM extraction confidence), but consider moving to `signal_pack` too
- **Files to update**:
  - `src/intelligence/social_ingest/social_ingest_basic.py`:
    - Line 418: Store `confidence` in `token_details['token_identification_confidence']` before returning
    - Line 1189: Add `token_identification_confidence` to `signal_pack`

### `lifecycle_id` → RENAME TO `position_id`
- **Current**: Unused column named `lifecycle_id`
- **Action**: 
  1. **Rename column**: `lifecycle_id` → `position_id` in schema
  2. Set `position_id = position_id` for all PM strands (`pm_action`, `position_closed`) - only AFTER position is created
  3. **Backfill option**: Can backfill `social_lowcap` and `decision_lowcap` strands after position creation:
     - When position is created, we know which `decision_lowcap` strand created it
     - Trace back: `decision_lowcap` → `social_lowcap` (via `parent_id`)
     - Backfill `position_id` into both strands
  4. Update queries to use `.eq("position_id", position_id)` instead of `.eq("content->>'position_id'", position_id)`
- **Files to update**:
  - `src/database/ad_strands_schema.sql`: Rename `lifecycle_id` to `position_id`
  - `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`:
    - Line 909-926: Add `position_id = position_id` to `position_closed_strand`
    - Line 1017-1031: Add `position_id = position_id` to `pm_action` strands
  - `src/tests/flow/test_scenario_9_pm_executor.py`:
    - Line 714-723: Update query to use `position_id` instead of `content->>'position_id'`
  - `src/tests/flow/test_scenario_1b_v4_learning_verification.py`:
    - Line 88: Update query to use `position_id` instead of `position_id` (already correct column name)

### `pm_action` Strands - FIX STRUCTURE
- **Current**: Using non-column fields (`token`, `position_id`, `chain` as top-level)
- **Action**: Move all position-specific data to `content` JSONB
- **Discussion**: `content` JSONB is the right place for module-specific data. PM-specific fields like `position_id`, `token_contract`, `chain`, `action`, `size_frac`, etc. belong in `content`. `signal_pack` is for structured, LLM-ready data (token/venue/curator info), while `content` is for module-specific operational data.
- **Files to update**:
  - `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`:
    - Line 1017-1031: Fix `_write_strands` to use proper structure:
      ```python
      {
          "id": ...,
          "module": "pm",
          "kind": "pm_action",
          "symbol": token_ticker,
          "timeframe": timeframe,
          "position_id": position_id,  # Use position_id column (renamed from lifecycle_id)
          "content": {
              "position_id": position_id,  # Also in content for consistency
              "token_contract": token,
              "chain": chain,
              "action": action,
              "size_frac": ...,
              "a_value": ...,
              "e_value": ...,
              "execution_result": {...}
          },
          ...
      }
      ```

---

## Part 4: Add Missing Data to signal_pack

### Token Identification Source
- **Location**: `signal_pack.identification_source`
- **Type**: String ("contract_address", "ticker_exact", "ticker_approximate", "ticker_bare")
- **Source**: Based on how token was identified (contract address, exact ticker with Twitter match, exact ticker without match, bare ticker)
- **Action**: 
  1. Change `_calculate_token_confidence()` to return identification source instead of confidence level
  2. Store in `token_details['identification_source']` before returning from `_verify_token_with_dexscreener`
  3. Add to `signal_pack` in `_create_social_strand` (line 1189 area)
- **Files to update**:
  - `src/intelligence/social_ingest/social_ingest_basic.py`:
    - Line 921-942: Change `_calculate_token_confidence()` to return source: "contract_address", "ticker_exact", "ticker_approximate", "ticker_bare"
    - Line 500: Store `token_details['identification_source'] = identification_source` before `return token_details`
    - Line 1189: Add `"identification_source": token.get('identification_source')` to `signal_pack`

---

## Part 5: Keep These Columns (Decided)

### `regime_context` - KEEP
- **Current**: Not used by PM, but could be useful for regime-based learning
- **Decision**: Keep for future use

### `metadata` - KEEP
- **Current**: Not used, but might be useful for extensibility
- **Decision**: Keep for future extensibility

### `context_vector` - KEEP (for future use)
- **Current**: Vector embedding for similarity search - not currently used
- **Decision**: Keep for potential future vector similarity search use cases
- **Note**: Could be useful for finding similar strands/patterns, but not implemented yet

---

## Part 6: Remove Legacy Views/Triggers/Functions

### Views to Remove
- `rdi_strands` - Legacy RDI
- `cil_strands` - Legacy CIL
- `ctp_strands` - Legacy CTP
- `dm_strands` - Legacy DM (not decision_lowcap)
- `td_strands` - Legacy TD
- `braid_candidates` - Uses legacy columns

### Views to Keep
- `social_lowcap_strands` - Useful
- `decision_lowcap_strands` - Useful
- `pm_action_strands` - Useful

### Triggers/Functions to Remove
- `notify_ad_strands_update` - Not used
- `trigger_learning_system` - Not used
- `calculate_module_resonance_scores` - Not used

### Tables to Remove
- `module_resonance_scores` - Not used
- `pattern_evolution` - Not used (only legacy RDI reference)

---

## Part 7: Code Updates Required

### social_ingest_basic.py
1. **Line 921-942**: Change `_calculate_token_confidence()` to return identification source:
   ```python
   def _calculate_token_identification_source(self, token_info: Dict[str, Any], verified_token: Dict[str, Any]) -> str:
       """Return how token was identified"""
       if token_info.get('contract_address'):
           return "contract_address"
       ticker_source = token_info.get('ticker_source', '')
       is_exact_ticker = ticker_source.startswith('$')
       twitter_match = self._check_twitter_handle_match(...)
       if is_exact_ticker and twitter_match:
           return "ticker_exact"
       elif is_exact_ticker:
           return "ticker_approximate"
       else:
           return "ticker_bare"
   ```

2. **Line 418**: Change to use new function:
   ```python
   identification_source = self._calculate_token_identification_source(token_info, token_details)
   ```

3. **Line 500**: Store identification source:
   ```python
   token_details['identification_source'] = identification_source
   return token_details
   ```

4. **Line 1148**: Remove `sig_sigma`

5. **Line 1149**: Remove `sig_confidence`

6. **Line 1150**: Remove `confidence`

7. **Line 1151**: Remove `sig_direction`

8. **Line 1189**: Add identification source to `signal_pack`:
   ```python
   "identification_source": token.get('identification_source'),
   ```

### decision_maker_lowcap_simple.py
1. **Line 638**: Remove `sig_confidence` and `sig_direction`:
   ```python
   # Remove: "sig_confidence": social_signal.get('sig_confidence'),
   # Remove: "sig_direction": social_signal.get('sig_direction'),
   ```

2. **Line 640**: Remove `confidence`:
   ```python
   # Remove: "confidence": social_signal.get('confidence'),
   ```

3. **Line 729**: Remove `sig_confidence` and `sig_direction`:
   ```python
   # Remove: "sig_confidence": social_signal.get('sig_confidence'),
   # Remove: "sig_direction": social_signal.get('sig_direction'),
   ```

4. **Line 731**: Remove `confidence`:
   ```python
   # Remove: "confidence": social_signal.get('confidence'),
   ```

### pm_core_tick.py
1. **Line 909-926**: Add `position_id` to `position_closed_strand`:
   ```python
   position_closed_strand = {
       ...
       "position_id": position_id,  # Add this (column renamed from lifecycle_id)
       ...
   }
   ```

2. **Line 1017-1031**: Fix `pm_action` strand structure:
   ```python
   strand = {
       "id": ...,
       "module": "pm",
       "kind": "pm_action",
       "symbol": token_ticker,
       "timeframe": timeframe,
       "position_id": position_id,  # Add this (column renamed from lifecycle_id)
       "content": {
           "position_id": position_id,  # Also in content for consistency
           "token_contract": token,
           "chain": chain,
           "action": action,
           "size_frac": ...,
           "a_value": ...,
           "e_value": ...,
           "execution_result": {...}
       },
       ...
   }
   ```

### Test Files
1. **test_scenario_9_pm_executor.py** (line 714-723): Update query:
   ```python
   .eq("position_id", position_id)  # Column renamed from lifecycle_id
   ```

2. **test_scenario_1b_v4_learning_verification.py** (line 88): Update query:
   ```python
   .eq("position_id", position_id)  # Column renamed from lifecycle_id
   ```

### Schema Migration
1. **ad_strands_schema.sql**: 
   - Rename `lifecycle_id` to `position_id`
   - Remove `confidence`, `sig_confidence`, `sig_sigma`, `sig_direction` columns
   - Remove `team_member`, `agent_id` (redundant with `module`)

---

## Part 8: New Minimal Schema

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
    position_id TEXT,       -- Position ID (renamed from lifecycle_id) - for PM strands, can be backfilled to social/decision strands
    parent_id TEXT,         -- Link to parent strand
    
    -- DATA FIELDS
    signal_pack JSONB,      -- Structured token/venue/curator data + identification_source
    content JSONB,          -- Module-specific data (PM action details, position data, etc.)
    module_intelligence JSONB,  -- Module-specific intelligence
    regime_context JSONB,   -- Regime context (for future use)
    
    -- METADATA
    session_bucket TEXT,    -- Session identifier
    status VARCHAR(20) DEFAULT 'active',  -- Strand status
    metadata JSONB,         -- For future extensibility
    context_vector VECTOR(1536)  -- Vector embedding for similarity search (future use)
);
```

---

## Implementation Order

1. ✅ **Investigation** - Done
2. ⏳ **Plan** - This document
3. ⏳ **Code Updates** - Update social_ingest, decision_maker, PM code
4. ⏳ **Schema Migration** - Create new schema, migrate data
5. ⏳ **Test Updates** - Update test queries
6. ⏳ **Verification** - Run tests, verify no regressions

---

## Notes

- **Token Identification Source**: Changed from confidence levels ("highest", "high", etc.) to identification source ("contract_address", "ticker_exact", "ticker_approximate", "ticker_bare"). This tells us HOW the token was identified, not how confident we are. Used to relax volume/liquidity thresholds for health metrics (informational only, doesn't block).

- **`position_id` (renamed from `lifecycle_id`)**: 
  - Can only be set AFTER position is created (for PM strands)
  - Can be backfilled to `social_lowcap` and `decision_lowcap` strands after position creation by tracing: position → decision_lowcap → social_lowcap (via `parent_id`)

- **`content` JSONB**: 
  - **Purpose**: Module-specific operational data (PM action details, position data, decision reasoning, etc.)
  - **vs `signal_pack`**: `signal_pack` is for structured, LLM-ready data (token/venue/curator info), while `content` is for module-specific operational data
  - **For PM**: Position-specific fields like `position_id`, `token_contract`, `chain`, `action`, `size_frac`, etc. belong in `content`
  - **Yes, we have this column**: It exists in the schema (line 65 in `ad_strands_schema.sql`)

- **`team_member` and `agent_id`**: Redundant - we have `module` column which tells us where the strand came from

- **`context_vector`**: Kept for potential future vector similarity search use cases (finding similar strands/patterns), but not currently implemented

