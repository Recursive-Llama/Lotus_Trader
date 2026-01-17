
**Status**: Draft  
**Date**: 2025-01-XX  
**Purpose**: Complete rewrite of learning system based on shadow positions and trajectory-based learning

---

## Core Principle

> **We are not inventing a new learning paradigm.**
> **We are upgrading episodes into full counterfactual positions so outcomes become continuous (ROI) instead of binary.**

Every buy-flag opportunity becomes either:
- **Active position** (if tuning gates pass)
- **Shadow position** (if tuning gates block)

Both run the same PM lifecycle, producing measurable ROI and trajectory outcomes.

---

## 1. The Core Loop

### 1.1 Entry Events

**Entry Event A: S2 Entry (Primary)**
- Trigger: First time in S2 and `entry_zone_ok = True`
- Pattern key: `pm.uptrend.S2.entry`
- Decision: Tuning gates decide → Active or Shadow

**Entry Event B: S1 Retest Entry (Secondary)**
- Trigger: After reaching S2, dips back to S1 (breakout/retest) and retest entry condition fires
- Pattern key: `pm.uptrend.S1.retest_entry`
- Decision: Tuning gates decide → Active or Shadow
- **Constraint**: S1 entry only possible if position has touched S2 previously

### 1.2 Position Semantics

**Shadow positions are normal positions with `status = 'shadow'`:**
- Same table: `lowcap_positions`
- Same lifecycle, same bookkeeping, same ROI computation
- Only difference: `status = 'shadow'` instead of `status = 'active'`

> **Note**: `is_shadow` in `position_trajectories` is derived from the position's status at creation (shadow vs active) and does not drift. It is not a separate source of truth.

**Shadow → Active Conversion:**
- If shadow opened at S2, then later a valid entry fires (S1 retest or re-entry) and gates pass:
  - Open **ACTIVE position**
  - Close/cancel the **SHADOW position**
  - One position per token×timeframe constraint

**Shadow Position Lifecycle (Deterministic Rule):**
- Shadow closes on its own if it reaches terminal exit **before** any active position opens
- Otherwise, shadow is closed/canceled at the moment an active position opens for the same token×timeframe
- This prevents "shadow and active both running" edge cases

### 1.3 Lifecycle Milestones

Once in a position (active or shadow), the attempt can:
- **Fail early**: Hit S0 before any trim
- **Reach initial trim**: Hit S2 trim at least once
- **Reach multiple trims**
- **Reach S3**
- **Fail after trims**: Trend break to S0 after some trims
- **Close for other reasons**: Timeouts, manual risk, etc.

---

## 2. Scope System v2

> **Scopes are the indexing system for all learning.** Every entry, trim, add, and dip-buy has a scope. All overrides match via `scope_subset ⊆ scope`.

### 2.1 Core Rules

- Every entry opportunity has a `scope_at_entry`
- Every action (trim/add/dip-buy) has a `scope_at_action`
- Every learning update is indexed by `(pattern_key, entry_event, scope_subset)`
- Override application uses: **`scope_subset ⊆ scope`** (Supabase JSONB `cd` operator)

### 2.2 Scope Changes vs Current System

**Removed (leaky):**
- `A_mode` — derived from A, self-referential
- `E_mode` — derived from E, self-referential

**Added:**
- `ticker` — token symbol or contract; learnable once evidence exists

**Regime: Compress for scope, preserve everything in storage:**
- Scope uses meso-primary **bins**: `opp_meso_bin`, `conf_meso_bin`, `riskoff_meso_bin`, `bucket_rank_meso`
- Raw numeric coordinates are stored alongside for analysis

**Numeric regime fields stored in scope (for analysis, not matching):**
- `opp_meso`, `conf_meso`, `riskoff_meso` (floats)
- Plus micro/macro equivalents: `opp_micro`, `riskoff_micro`, `opp_macro`, etc.
- Bins are derived from these numeric fields

### 2.3 Scope Keys (Same for Tuning and Strength)

| Category | Keys |
|----------|------|
| **Token-specific** | `timeframe`, `chain`, `ticker`, `mcap_bucket`, `age_bucket`, `vol_bucket`, `mcap_vol_ratio_bucket`, `curator`, `intent` |
| **Regime (meso primary)** | `opp_meso_bin`, `conf_meso_bin`, `riskoff_meso_bin`, `bucket_rank_meso_bin` |
| **Regime (secondary)** | `*_micro_bin` (timing), `*_macro_bin` (never gates tuning) |

> **Binning Rule**: Regime coordinates are stored as numeric fields **and** as discrete bins for scope matching (e.g., `opp_meso_bin ∈ {low, mid, high}`). Bins are used for scope keys; raw numeric values are stored for analysis. JSONB containment requires discrete values.

**Binning Cardinality:**
- Default binning uses **3 bins** (`low`/`mid`/`high`) for opp/conf/riskoff
- May be upgraded to 5 bins later only if sample volume supports it

**`bucket_rank_meso`:**
- Stored both as raw rank (1..N) and as discrete bin (`top`/`mid`/`bottom`)
- Scope key uses the **bin** (`bucket_rank_meso_bin`), not raw rank

### 2.4 Dimension Weights (Numeric Priors)

> Dimension weights apply to **discrete scope keys (bins)**, not raw numeric regime values.

**Strength Weights v0:**
| Dim | Weight | | Dim | Weight |
|-----|--------|---|-----|--------|
| `timeframe` | 3.0 | | `opp_meso_bin` | 1.8 |
| `ticker` | 3.0 | | `curator` | 1.8 |
| `mcap_bucket` | 2.2 | | `vol_bucket` | 1.5 |
| `bucket_rank_meso` | 2.0 | | `riskoff_meso_bin` | 1.4 |
| `age_bucket` | 2.0 | | `chain` | 1.2 |
| | | | `mcap_vol_ratio_bucket` | 1.2 |
| | | | `conf_meso_bin` | 1.0 |
| | | | `*_micro_bin` | 0.7 |
| | | | `*_macro_bin` | 0.0–0.3 |

**Tuning Weights v0:**
| Dim | Weight | | Dim | Weight |
|-----|--------|---|-----|--------|
| `timeframe` | 3.0 | | `conf_meso_bin` | 1.8 |
| `ticker` | 2.6 | | `age_bucket` | 1.6 |
| `riskoff_meso_bin` | 2.2 | | `bucket_rank_meso` | 1.6 |
| `mcap_bucket` | 2.0 | | `chain` | 1.2 |
| | | | `vol_bucket` | 1.2 |
| | | | `opp_meso_bin` | 1.0 |
| | | | `mcap_vol_ratio_bucket` | 1.0 |
| | | | `riskoff_micro_bin` | 1.0 |
| | | | `curator` | 0.6 |
| | | | `*_macro_bin` | 0.0 |

### 2.5 Selection Rules

**Strength: Blended overrides**
```
spec_mass = Σ weight[d] for d in scope_subset
specificity = (spec_mass + 1.0) ^ SPECIFICITY_ALPHA
total_weight = confidence_eff * specificity
final_dirA = weighted_average(dirA, total_weight)
```

**Tuning: Most-specific with confidence fallback (no blending)**
- Pick most-specific override that meets confidence threshold
- If none qualify, use base constants
- No blending (overrides are optimized solutions)

### 2.6 N_MIN and Confidence System

**Two separate questions:**
1. **N_MIN** → "May this slice speak at all?" (eligibility)
2. **Confidence** → "How loudly should it speak?" (influence weight)

**N_MIN (Eligibility Threshold):**
- `N_MIN_START = 12`
- If `n < 12`: ❌ No override created, no learning signal emitted
- `n = 12` does NOT mean "trusted" — it means "allowed to exist in the learning system"

**Confidence Ramp g(n):**

| n range | g(n) | Interpretation |
|---------|------|----------------|
| `< 12` | 0 | No signal (noise only) |
| `12 → 33` | 0.2 → 0.5 | "This *might* be real" |
| `33 → 69` | 0.5 → 0.9 | "This is probably real" |
| `69 → 124` | 0.9 → 1.0 | "We trust this, refining magnitude" |
| `≥ 124` | 1.0 | "Very stable, hard to move" |

**Confidence Formula:**
```
confidence_eff = reliability × g(n)
```
- `reliability` = outcome consistency (variance-aware, ∈ (0, 1))
- `g(n)` = sample ramp (from table above)

**Usage:**
- **Strength**: `confidence_eff` weights blending
- **Tuning**: override must meet confidence threshold to be selected

---

## 3. Trajectory Classification (The Spine)

> **Key Rule**: Trajectories are defined *independently* of whether the position was active or shadow.
> **Active vs shadow only changes how the outcome is interpreted**, not how it is classified.

### Trajectory Dimensions

Every attempt is classified by:
- `is_shadow`: `true` or `false` (derived from `status` at creation)
- `did_trim`: `true` or `false`
- `n_trims`: Count of trims
- `reached_s3`: `true` or `false`
- `roi`: Final ROI (continuous value)
- `entry_event`: `S2.entry` or `S1.retest_entry`
- `blocked_by`: Array of gate names that blocked entry (shadow only)
- `near_miss_gates`: Gates that were close to blocking (active failures only)
- `gate_margins`: Dict of margin values at decision tick (see below)

### Gate Margins (Authoritative Definition)

**`gate_margins`**: Stored at decision tick for all positions.
```
gate_margins = {
    "ts_margin": ts_score - ts_min,       // positive = passed
    "halo_margin": halo_max - halo_dist,  // positive = passed
    "slope_margin": slope - slope_min,    // positive = passed
    ...
}
```

**`blocked_by`** (shadow): Gates with **negative margin** at decision tick.

**`near_miss_gates`** (active): Gates with **smallest positive margin** at decision tick.
- Defaults to **top 2 closest-to-fail** gates
- Full margins stored in `gate_margins` for analysis

### ROI Handling (Authoritative)

- `roi > 0` = **winner**
- `roi <= 0` = **non-winner** (includes breakeven as managed loss)

### Strength Learning Rule

> Strength consumes **all Active trajectories**, but posture deltas are scaled by ROI magnitude and confidence. Losing actives contribute weakly unless the pattern is consistently losing.
>
> Strength consumes shadow trajectories **only if roi > 0**.

---

## 4. Unified Trajectory Table

### Legend
- **Active** = Position was opened
- **Shadow** = Position was blocked by tuning gates
- **Tuning learns** = Entry / trim gates (when to act)
- **Strength learns** = A / E posture (how hard to press)
- **Blocked_by** = Exact gates that prevented entry (shadow only)
- **Near_miss_gates** = Gates that were close to blocking (active failures)

---

### Trajectory 1: Immediate Failure (No Trim, Negative ROI)

| Dimension | Active | Shadow |
|-----------|--------|--------|
| **Observed outcome** | Entered → failed → exited at S0 | Skipped → would have failed |
| **ROI** | `< 0` | `< 0` |
| **Reached S2 trim** | ❌ | ❌ |
| **Reached S3** | ❌ | ❌ |
| **Meaning** | Bad entry | Correctly blocked |
| **Tuning action** | **Tighten specific entry gates** that allowed this | **No change** (block was correct under current gates) |
| **Strength action** | Mild A↓ (optional) | ❌ None |
| **Notes** | This is a *tuning failure* | This is a *tuning success* |

**Gate-specific tuning:**
- Active: `Δts_min = +0.05`, `Δhalo_max = -0.1`, etc. (based on `near_miss_gates`)
- Shadow: No change (gates worked)

---

### Trajectory 2: Trim-but-Loss (Managed Loser)

| Dimension | Active | Shadow |
|-----------|--------|--------|
| **Observed outcome** | Entered → trimmed → still failed | Skipped → would have trimmed then failed |
| **ROI** | `≤ 0` | `≤ 0` |
| **Reached S2 trim** | ✅ | ✅ |
| **Reached S3** | ❌ | ❌ |
| **Meaning** | Entry borderline, trims insufficient | Borderline setup |
| **Tuning action** | Tighten **entry OR trim gates** (scope-specific diagnosis) | Usually none |
| **Strength action** | **E↑** (trim more aggressively) | ❌ None |
| **Notes** | Important diagnostic for trim tuning | Shadow confirms it wasn't a missed opportunity |

**Gate-specific tuning:**
- Active: 
  - If entry was borderline: `Δts_min = +0.02`, `Δhalo_max = -0.05`
  - If trim was too late/weak: `Δtrim_trigger = -0.01`, `Δtrim_fraction = +0.05`
- Shadow: Usually none (correctly blocked)

**Strength action:**
- Active: `ΔE = +0.05` (increase trim aggressiveness)
- Shadow: None

**Note on E vs Trim Gates:**
- **E (Strength)**: Controls trim *aggressiveness* (how much to trim)
- **Trim Gates (Tuning)**: Control trim *timing* (when to trim)
- If we trim but still lose → **E↑** (trim more aggressively)
- If we trim too late → **Trim gates** (tune timing)

---

### Trajectory 3: Trimmed Winner (Messy Winner)

| Dimension | Active | Shadow |
|-----------|--------|--------|
| **Observed outcome** | Entered → trimmed → profitable exit | Skipped → would have been profitable |
| **ROI** | `> 0` | `> 0` |
| **Reached S2 trim** | ✅ | ✅ |
| **Reached S3** | ❌ | ❌ |
| **Meaning** | Entry OK, trend weak | Missed but not ideal |
| **Tuning action** | **No change by default** | **Evaluate loosening** of `blocked_by` gates |
| **Strength action** | Mild A↑ | **Strength learns (pattern works)** |
| **Notes** | Acceptable outcome | Missed EV — tuning too strict |

**Gate-specific tuning:**
- Active: Usually none (acceptable outcome)
- Shadow: Evaluate loosening `blocked_by` gates, scaled by margin-to-pass and EV tradeoff

**Strength action:**
- Active: `ΔA = +0.02` (mild increase)
- Shadow: `ΔA = +0.03`, `ΔE = -0.01` (pattern works, missed opportunity)

---

### Trajectory 4: Clean Winner (Reached S3, Profitable)

| Dimension | Active | Shadow |
|-----------|--------|--------|
| **Observed outcome** | Entered → rode → S3 → big win | Skipped → would have been big win |
| **ROI** | `> 0` (often large) | `> 0` |
| **Reached S2 trim** | Usually | Usually |
| **Reached S3** | ✅ | ✅ |
| **Meaning** | Ideal trade | Serious miss |
| **Tuning action** | **No change by default** | **Evaluate loosening** of `blocked_by` gates (strong signal) |
| **Strength action** | **A↑↑, E↓↓** | **A↑↑, E↓↓ (shadow winner)** |
| **Notes** | This defines what "good" looks like | Shadow winner is gold for learning |

**Gate-specific tuning:**
- Active: **No change by default** (active winner is not evidence tuning was too strict)
- Shadow: Evaluate loosening `blocked_by` gates, scaled by margin-to-pass and EV tradeoff (strong signal)

**Strength action:**
- Active: `ΔA = +0.10`, `ΔE = -0.05` (strong increase in aggressiveness)
- Shadow: `ΔA = +0.12`, `ΔE = -0.06` (even stronger — missed big opportunity)

---

### Trajectory 5: Rare / Edge Cases

| Case | Classification | Notes |
|------|----------------|-------|
| Reached S3 but ROI ≈ 0 | `trimmed_winner` | Trend existed but execution weak |
| No trim but ROI > 0 | `trimmed_winner` with `did_trim=false` | Rare; same category, different flag |
| Trim improves loss but still negative | `trim_but_loss` | Trim tuning signal |
| Shadow + near-trim then fail | `trim_but_loss` (shadow) | Useful for trim-gate tuning |

> **Determinism rule**: All edge cases map to existing trajectory types; no "configurable" classification.

---

## 5. Who Owns What (Clean Division)

### Tuning Owns

**Goal**: Don't lose money. Ideally break even or better.

**Controls:**
- Entry gates (S2 entry, S1 retest entry)
  - `ts_min`, `halo_max`, `slope_min`, `dx_min`
- Trim gates (when to trim)
  - `trim_trigger_threshold`, `trim_fraction` (timing only)
- Add / dip-buy gates
- **Note**: Trim *amount* is controlled by E (strength), but trim *timing* is tuning

**Learns from:**
- Active failures → "we were too loose" → tighten based on `near_miss_gates`
- Shadow winners → "we were too strict" → evaluate loosening based on `blocked_by`
- Shadow failures → "we were right to block" → no change
- Trim-but-loss → "trim timing was wrong" OR "entry was borderline"

**EV Tradeoff for Loosening (Critical):**

When considering loosening gates, we simulate the **marginal effect** on positions whose gate outcome would flip:

> "If we had loosened these specific gates, what would the net ROI change have been for **newly-admitted** attempts?"

**Rule**: Only loosen if:
```
EV_delta = Σ_{i ∈ newly_admitted, roi_i > 0} roi_i  -  1.69 × Σ_{i ∈ newly_admitted, roi_i < 0} |roi_i|  >  0
```

- **newly_admitted** = attempts that were blocked but would pass under the candidate gate change
- Uses **actual continuous ROI** from each position (not binary +1/-1)
- `|roi_i|` ensures we sum absolute loss magnitudes, not net (prevents sign errors)
- Computed over **both active and shadow** positions in scope
- This is the core value of shadow positions: **continuous ROI for counterfactual analysis**

This prevents loosening gates that would have net negative EV on the marginal set.

**Key point**: Tuning is *not* about how big the trade was. It's about whether we should have participated *at all* and whether we exited/trimmed at the right time.

---

### Strength Owns

**Goal**: When we *do* trade, how hard should we press?

**Controls:**
- A (aggressiveness) → affects position sizing
- E (trim pressure) → affects trim *amount/aggressiveness*
- **Note**: E affects trim amount, but trim *timing* is still tuning

**Learns from:**
- Active outcomes (all trajectories)
- Shadow outcomes **only when they are good** (missed strength, not missed tuning)
- ROI magnitude
- S3 attainment

**Does NOT learn from:**
- Shadow failures → those are tuning wins

**Key point**: Strength never tightens entry gates. Strength only affects A/E posture once we are in.

---

## 6. Summary Rules (Authoritative)

1. **Every entry opportunity has an active OR shadow trajectory**
   - Same taxonomy, same buckets
   - Active vs shadow only changes interpretation

2. **Shadow failures are good for tuning**
   - They confirm gates are working
   - No strength learning from shadow failures

3. **Shadow winners are bad for tuning, good for strength**
   - Tuning: gates were too strict
   - Strength: pattern itself is strong

4. **Tuning always adjusts specific gates**
   - Never "loosen overall"
   - Always: `Δts_min`, `Δhalo_max`, `Δslope_min`, `Δdx_min`, `Δtrim_trigger`, etc.

5. **Strength never tightens entry gates**
   - Strength only affects **A / E posture**
   - Uses: active winners, shadow winners

6. **Primary tuning goal**
   - Get to **break-even or better** (via entry + first trims)

7. **Primary strength goal**
   - Maximize **S3 reach + ROI magnitude**

8. **E vs Trim Gates distinction**
   - **E (Strength)**: Controls trim *amount* (how much to trim)
   - **Trim Gates (Tuning)**: Controls trim *timing* (when to trim)
   - If trim but still lose → **E↑** (trim more aggressively)
   - If trim too late → **Trim gates** (tune timing)

9. **Strength posture learning**
   - Strength posture deltas (dirA, dirE) are learned from trajectory outcomes
   - Losing active trajectories contribute weakly (scaled by ROI magnitude)
   - Shadow failures do not contribute to strength learning

10. **EV tradeoff for tuning loosening**
    - Uses **actual continuous ROI** (not binary win/loss)
    - Only loosen if: `EV_delta = Σ(ROI newly-admitted winners) - 1.69 × |Σ(ROI newly-admitted losers)| > 0`
    - Computed over **marginal set** (positions whose gate outcome would flip)

---

## 7. Data Model

### 7.1 Core Principle: ROI as Shared Currency

> **All learning uses ROI (realized P&L %) as the outcome metric, not R/R.**

- ROI is already tracked in `lowcap_positions.rpnl_pct`
- ROI is continuous, comparable across scopes, and directly measures profitability
- R/R is deprecated for learning purposes

### 7.2 Position Table Changes

Shadow positions use `status = 'shadow'` (not a separate flag):

```sql
-- Status enum now includes 'shadow'
-- Existing values: 'watchlist', 'active', 'dormant'
-- New value: 'shadow'

ALTER TABLE lowcap_positions ADD COLUMN entry_event TEXT;  -- 'S2.entry' or 'S1.retest_entry'
```

**Shadow positions are normal positions** with `status = 'shadow'`. They run the same PM lifecycle, same state machine, same ROI computation.

### 7.3 Trajectory Table (Unified Learning Fact Table)

**New table**: `position_trajectories`

Replaces and deprecates:
- `pattern_trade_events` (deprecated)
- `pattern_episode_events` (deprecated)

```sql
CREATE TABLE position_trajectories (
    id BIGSERIAL PRIMARY KEY,
    
    -- Link to position
    position_id TEXT NOT NULL,            -- lowcap_positions.id
    trade_id TEXT,                        -- If position had a trade
    
    -- Entry context
    entry_event TEXT NOT NULL,            -- 'S2.entry' or 'S1.retest_entry'
    pattern_key TEXT NOT NULL,            -- 'pm.uptrend.S2.entry'
    scope JSONB NOT NULL,                 -- Full scope at entry time
    entry_time TIMESTAMPTZ NOT NULL,
    
    -- Shadow vs Active
    is_shadow BOOLEAN NOT NULL,           -- Derived from status at creation (entry decision), not at close
    blocked_by TEXT[],                    -- Shadow only: gates that blocked entry (negative margins)
    near_miss_gates TEXT[],               -- Active failures: gates with smallest positive margin
    gate_margins JSONB,                   -- All gate margins at decision tick
    
    -- Outcome dimensions
    trajectory_type TEXT NOT NULL,        -- 'immediate_failure', 'trim_but_loss', 'trimmed_winner', 'clean_winner'
    roi FLOAT NOT NULL,                   -- Final ROI (continuous, from rpnl_pct)
    did_trim BOOLEAN NOT NULL,
    n_trims INTEGER DEFAULT 0,
    reached_s3 BOOLEAN NOT NULL,
    
    -- Timestamps
    closed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for mining
CREATE INDEX idx_pt_scope_gin ON position_trajectories USING GIN(scope);
CREATE INDEX idx_pt_pattern ON position_trajectories(pattern_key, trajectory_type);
CREATE INDEX idx_pt_shadow ON position_trajectories(is_shadow);
CREATE INDEX idx_pt_closed_at ON position_trajectories(closed_at DESC);
```

**Flow:**
1. Entry opportunity → creates position (`status = 'active'` or `status = 'shadow'`)
2. Position runs PM lifecycle (same for both)
3. Position closes → compute trajectory → write to `position_trajectories`
4. Mining reads from `position_trajectories`

### 7.4 Override Table Changes

Extend existing `pm_overrides` table (no new table):

```sql
-- Add strength steering columns
ALTER TABLE pm_overrides ADD COLUMN dirA FLOAT;  -- Direction for A: -1 to +1
ALTER TABLE pm_overrides ADD COLUMN dirE FLOAT;  -- Direction for E: -1 to +1

-- 'multiplier' column is deprecated but kept for backward compat during transition
```

**Usage:**
- **Strength writes**: `dirA`, `dirE`, `confidence_score`
- **Tuning writes**: `tuning_params` (gate adjustments like `{"ts_min": 1.1, "halo_max": 0.9}`)
- **`multiplier`**: Deprecated, use `dirA`/`dirE` for strength

### 7.5 Table Changes Summary

| Table | Status | Notes |
|-------|--------|-------|
| `pattern_trade_events` | **Deprecated** | Replaced by `position_trajectories` |
| `pattern_episode_events` | **Deprecated** | Replaced by `position_trajectories` |
| `learning_lessons` | **Optional telemetry** | Useful for audit/debugging during rollout; not required at runtime |

### 7.6 Future: Action-Level Trajectories

> S3 dip-add learning retains current episode semantics, but events will be stored as `action_trajectories` records for unified mining.

**Future table** (not needed v1): `action_trajectories`
- Captures S3 dip-add episodes, S2 dip-buys, and other action-level learning
- `position_trajectories` stays attempt-level (entry→exit)
- `action_trajectories` captures mid-position action decisions

---

## 8. Implementation Phases

### Phase 1: Shadow Position Infrastructure
- [ ] Add `status = 'shadow'` to positions (extend status enum)
- [ ] Add `entry_event` column to positions
- [ ] Shadow positions run same PM lifecycle
- [ ] Shadow→Active conversion logic
- [ ] Shadow position ROI computation (same as active)

### Phase 2: Trajectory Classification
- [ ] Create `position_trajectories` table
- [ ] Compute trajectory on position close: `did_trim`, `n_trims`, `reached_s3`, `roi`
- [ ] Record `blocked_by` for shadow positions
- [ ] Record `near_miss_gates` for active failures
- [ ] Classify into: `immediate_failure`, `trim_but_loss`, `trimmed_winner`, `clean_winner`

### Phase 3: Learning Updates
- [ ] Add `dirA`, `dirE` columns to `pm_overrides`
- [ ] Mining reads from `position_trajectories` (not legacy tables)
- [ ] Tuning updates driven by **active failures** and **shadow winners**; shadow failures recorded as confirmed correct blocks
- [ ] Strength learns from **all Active** + **positive Shadow** (ROI > 0)
- [ ] Gate-specific tuning actions (not general loosen/tighten)
- [ ] Implement EV tradeoff simulation for loosening (marginal set, 1.69:1 ratio)
- [ ] Migrate DX ladder tuning to use `position_trajectories` instead of `pattern_episode_events`

### Phase 4: Trim Tuning
- [ ] Add trim gates to tuning system
- [ ] Learn from `trim_but_loss` trajectories
- [ ] Adjust trim thresholds per scope
- [ ] Distinguish trim timing (tuning) from trim amount (E/strength)

### Phase 5: Decision Maker Updates
- [ ] Switch from R/R to ROI (`rpnl_pct`)
- [ ] Remove 1m timeframe (use only 15m, 1h, 4h)
- [ ] Starting allocation: 15m=15%, 1h=50%, 4h=35%
- [ ] Gradual allocation changes (max 0.3% per trade)
- [ ] Enable A/E v2 (prerequisite)

### Phase 6: Dip-Buy Integration
- [ ] Integrate S3 dip-buy with trajectory classification
- [ ] Learn from dip-buy outcomes

---

## 9. Decision Maker Learning (Separate System)

> **Status**: Not part of unified PM learning — handled separately by `UniversalLearningSystem`

### 9.1 Changes Required

**Current Issues (from `universal_learning_system.py`):**
1. ❌ Uses R/R instead of ROI
2. ❌ 1m timeframe still included
3. ❌ No gradual allocation changes

**New Requirements:**
- **ROI**: Extract `rpnl_pct` instead of R/R
- **Allocations**: 15m=15%, 1h=50%, 4h=35%
- **Gradual changes**: Max 0.3% change per trade
- **Remove 1m**: Only use 15m, 1h, 4h

### 9.2 A/E v2 Enablement (Prerequisite)

Enable A/E v2 before deploying learning updates:

```sql
INSERT INTO learning_configs (module_id, config_data, updated_by) 
VALUES ('pm', '{"feature_flags": {"ae_v2_enabled": true}}', 'manual')
ON CONFLICT (module_id) DO UPDATE 
SET config_data = jsonb_set(
    COALESCE(config_data, '{}'::jsonb), 
    '{feature_flags,ae_v2_enabled}', 
    'true'
);
```

## 10. Open Questions / Future Work

1. **Trim tuning gates**: Exact gates to tune (timing vs amount)
2. **E vs Trim gates interaction**: How to coordinate E (strength) and trim gates (tuning)
3. **Shadow position performance**: Computational cost of running shadow positions
4. **Migration**: How to migrate existing episode data to trajectory data?

---

## 11. Relationship to Current System

### What Stays the Same
- PM state machine (S0 → S1 → S2 → S3)
- A/E computation
- Trim logic
- Exit logic
- ROI computation

### What Changes
- Episodes → Shadow positions (upgrade, not replacement)
- Binary outcomes → Continuous ROI + trajectory classification
- Episode events → Trajectory records
- Learning from episodes → Learning from trajectories

### What's New
- Shadow positions (full lifecycle)
- Trajectory classification
- Gate-specific tuning actions
- Trim tuning (timing gates)

---

## 12. Next Steps

1. **Review and approve this spec**
2. **Design shadow position data model** (Phase 1)
3. **Implement trajectory classifier** (Phase 2)
4. **Update learning systems** (Phase 3)
5. **Add trim tuning** (Phase 4)
6. **Test with production data**
7. **Migrate existing episode data**

---

**End of Specification**
