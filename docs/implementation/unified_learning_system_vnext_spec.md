
**Date**: 2025-01-XX  
**Status**: Implementation-Ready  
**Last Updated**: Clarifications from code review  
**Purpose**: Complete specification for the unified learning system redesign

---

## Executive Summary

This document defines the **Unified Learning System vNext**, which replaces the current dual-system approach (tuning vs strength) with a single, outcome-first learning framework.

**Core Principle**: Every opportunity becomes a **Trade Attempt** that ends in a **Trajectory Class** with an ROI outcome. We learn by asking: "In what contexts (scopes) do we get each trajectory, and what changes improve EV?"

**Key Innovations**:
- **Unified Attempt Model**: Real + shadow attempts (counterfactual learning)
- **Trajectory Classes**: Diagnostic signals that map directly to actuators
- **Compressed Regime Dimensions**: 15 regime dims → 9 compressed dims (3 per horizon)
- **Attempt-Level Learning**: Entry → full lifecycle → outcome (not per-action)
- **Selective Shadow Usage**: Tuning uses all shadows, strength uses shadow winners only

---

## 1. Core Concepts

### 1.1 Trade Attempt (Atomic Unit)

A **Trade Attempt** is the atomic unit for learning. It represents:

- **Entry** → full lifecycle → **final outcome**

Every attempt produces:
- `trajectory_class` (diagnostic signal)
- `roi` (shared currency)
- `scope` (explanatory context)
- `confidence_contribution` (sample quality)

**Attempt Types**:
- **Real attempt**: Actually entered by PM
- **Shadow attempt**: Counterfactual entry (tuning blocked, but we simulate as if entry was allowed)

### 1.2 Trajectory Classes (Diagnostic Signals)

Every attempt maps to exactly one trajectory class. These are **not labels**—they are **diagnostic signals** that map directly to actuators:

| Class | Criteria | Signal | Actuator |
|-------|----------|--------|----------|
| **clean_winner** | `reached_s3 = true` AND `roi > 0` | Press harder | A↑, E↓ |
| **messy_winner** | `did_trim = true` AND `roi > 0` AND `reached_s3 = false` | Entry OK, trend weak | Mostly tuning + mild strength |
| **managed_loser** | `did_trim = true` AND `roi <= 0` | Entry borderline, trim too weak | E↑, trim tuning, A↓ |
| **immediate_failure** | `did_trim = false` AND `roi <= 0` | Bad entry | Tighten entry gates |

**Edge Cases**:
- `reached_s3 = true`, `roi > 0`, `did_trim = false` → `clean_winner` (never trimmed, rode to S3)
- `did_trim = true`, `roi = 0` → `managed_loser` (breakeven treated as managed loss)

### 1.3 Shadow Attempts (Counterfactual Learning)

**When Created**:
- Pattern was in "entry-eligible zone"
- Entry did not occur **only because of tuning gates**
- Create at most **one shadow attempt per market attempt / entry opportunity cluster** (avoid per-candle explosion)

**How It Runs**:
- Uses **exact same PM logic** as real attempt:
  - Initial size determined by A (from flags at that time)
  - Trims/exits determined by E and PM state machine
  - Position state maintained (remaining size, realized pnl, etc.)
  - Closes when PM would have closed it
- Result: Full attempt record with ROI + trajectory class

**Selective Usage**:
- **Tuning**: Uses all real + all shadow attempts (winners + losers)
  - Question: "Should we enter at all?"
- **Strength**: Uses real attempts + shadow winners only
  - Default: Include shadow attempts where `roi > 0`
  - Optional stricter: Require `reached_s2` or `reached_s3`
  - Question: "When we do enter, how hard should we press?"

**Rationale**: This keeps strength from being polluted by hypothetical losers that tuning should block.

**Shadow Attempt Spawn Rules** (Deterministic Policy):
- **Trigger**: First time `entry_zone_ok` becomes `true` and tuning blocks entry
- **Alternative**: Spawn at max desirability score within a window (if multiple opportunities)
- **Cap**: Maximum 1 shadow attempt per token per timeframe per day
- **Rationale**: Avoid explosion and make runs reproducible

---

## 2. Data Model

### 2.1 Attempt Events (Primary Fact Table)

**Table**: `attempt_events` (or adapt `pattern_trade_events` to be per-attempt, not per-action)

**Fields** (minimum):
```sql
attempt_id TEXT NOT NULL,              -- real: trade_id, shadow: shadow:<episode_id>
is_shadow BOOLEAN NOT NULL,
entry_time TIMESTAMPTZ NOT NULL,
entry_price FLOAT NOT NULL,
exit_time TIMESTAMPTZ,
exit_price FLOAT,
roi FLOAT,                              -- Consolidated from rpnl_pct at close time
did_trim BOOLEAN,                       -- Consolidated from exec_history at close time
reached_s2 BOOLEAN,                     -- Consolidated from state tracking at close time
reached_s3 BOOLEAN,                     -- Consolidated from time_to_s3 at close time
trajectory_class TEXT NOT NULL,        -- Computed at close time: clean_winner, messy_winner, managed_loser, immediate_failure
entry_pattern_key TEXT NOT NULL,       -- Entry pattern key (to distinguish from action pattern keys)
scope JSONB NOT NULL,                   -- Compressed regime dims + other dims
blocked_by TEXT[],                      -- Shadow only: ["ts", "halo", "slope"]
tuning_version TEXT,                    -- Optional: which tuning version was active
timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

> [!IMPORTANT]
> **Consolidation at Write Time**: All trajectory fields (`roi`, `did_trim`, `reached_s3`, `trajectory_class`) are computed **once** when the attempt closes and stored directly in `attempt_events`. Do NOT derive these at query time from scattered sources.

**Why Consolidate**:
- Single source of truth for mining queries
- Faster queries (no joins across positions/features/episodes)
- Immutable once written (closed attempts don't change)

**Implementation** (in `pm_core_tick.py` at trade close):
```python
# Consolidate attempt fields at close time
reached_s3 = time_to_s3 is not None
did_trim = bool(exec_history.get("last_trim"))
roi = rpnl_pct
trajectory_class = compute_trajectory_class(reached_s3, did_trim, roi)

# Write all fields to attempt_events in one insert
```

**Key Point**: 
- **Attempt is the unit of outcome** (trajectory class + ROI)
- **Strength learns per action type**, but each sample is labeled by its parent attempt outcome
- This is "attempt-labeled action learning", not "attempt-only learning"

### 2.2 Action Events (Diagnostic Only)

**Purpose**: Store individual actions (entry, add, trim, exit) for diagnostics and action-level strength learning.

**Fields**:
```sql
action_id TEXT NOT NULL,
attempt_id TEXT NOT NULL,              -- Links to attempt
action_category TEXT NOT NULL,        -- entry, add, trim, exit
action_time TIMESTAMPTZ NOT NULL,
scope_at_action JSONB NOT NULL,        -- Scope at action time (may differ from entry scope)
pattern_key TEXT NOT NULL,             -- Action-specific pattern key
size_frac FLOAT,
a_value FLOAT,
e_value FLOAT,
timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

**Usage**: Action events are labeled by their attempt's final `(trajectory_class, roi)` for strength learning.

---

## 3. Scope System v2

> [!IMPORTANT]
> Scopes are the **indexing system** for all learning. Every entry, trim, add, and dip-buy has a scope. All overrides match via `scope_subset ⊆ scope`.

### 3.1 Everything is Scope-Based

- Every entry opportunity has a `scope_at_entry`
- Every action (trim/add/dip-buy) has a `scope_at_action`
- Every learning update is indexed by `(pattern_key, action_category, scope_subset)`
- Override application uses: **`scope_subset ⊆ scope`** (Supabase JSONB `cd` operator)

### 3.2 Scope Changes vs Current System

#### Removed Dimensions (Leaky)
- `A_mode` — derived from A, self-referential
- `E_mode` — derived from E, self-referential

#### Added Dimensions
- `ticker` — token symbol or contract; learnable once evidence exists

#### Regime: Compress for Scope, Preserve Everything in Storage

We do **not** use all 15 raw regime states as scope dimensions. Instead:

**Scope uses a small set of regime coordinates (meso-primary):**
- `effective_opp_meso` — opportunity score (favors S1/S2)
- `effective_conf_meso` — confidence score (favors S2/S3)
- `riskoff_meso` — risk-off pressure (from USDT.d + BTC.d)
- `bucket_rank_meso` — relative bucket performance (separate dimension, not multiplied into opp)

**Secondary (stored, optionally used later):**
- `*_micro` equivalents (timing/friction)
- `*_macro` equivalents (**macro never gates tuning**)

**Storage preserves full detail** — even if scope only matches on meso coordinates, we store all raw S-states and derived scores per horizon for future learning.

### 3.3 Scope Dictionary (Same Keys for Tuning and Strength)

Both systems query the same `scope` dict. The difference is in **dimension weights** and **selection rules**.

#### Token-Specific / Structural Keys
| Key | Description |
|-----|-------------|
| `timeframe` | Position timeframe (15m, 1h, 4h) |
| `chain` | Blockchain (solana, base, ethereum) |
| `ticker` | Token symbol or contract |
| `mcap_bucket` | Market cap bucket (micro, small, mid) |
| `age_bucket` | Token age bucket |
| `vol_bucket` | Volume bucket |
| `mcap_vol_ratio_bucket` | Market cap to volume ratio |
| `curator` | Signal source (optional) |
| `intent` | Trade intent (optional) |

#### Regime Coordinate Keys (Meso Primary)
| Key | Description |
|-----|-------------|
| `effective_opp_meso` | Opportunity score at meso horizon |
| `effective_conf_meso` | Confidence score at meso horizon |
| `riskoff_meso` | Risk-off pressure at meso horizon |
| `bucket_rank_meso` | Bucket rank (1-6, separate from opp) |

#### Secondary Regime Keys (Stored, Lower Weight)
| Key | Description |
|-----|-------------|
| `riskoff_micro` | Micro timing/friction guardrail |
| `effective_opp_micro` | Micro opportunity |
| `*_macro` | Macro context (very low weight, never gates tuning) |

### 3.4 Dimension Weights (Numeric Priors)

These are **starting priors**, not truth. They're updated via weight learning (Section 5.5).

#### Strength Weights v0 (A/E Posture)

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| `timeframe` | 3.0 | Primary structural |
| `ticker` | 3.0 | Token-specific behavior |
| `mcap_bucket` | 2.2 | Size matters for strength |
| `bucket_rank_meso` | 2.0 | Relative performance |
| `age_bucket` | 2.0 | Young tokens behave differently |
| `effective_opp_meso` | 1.8 | Opportunity drives posture |
| `curator` | 1.8 | Source quality |
| `vol_bucket` | 1.5 | Liquidity context |
| `riskoff_meso` | 1.4 | Risk context |
| `chain` | 1.2 | Chain differences |
| `mcap_vol_ratio_bucket` | 1.2 | Structural |
| `effective_conf_meso` | 1.0 | Lower for strength |
| `riskoff_micro` | 0.7 | Timing/friction |
| `effective_opp_micro` | 0.7 | Timing/friction |
| `*_macro` | 0.0–0.3 | Never strong for strength |

#### Tuning Weights v0 (Entry Gates)

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| `timeframe` | 3.0 | Primary structural |
| `ticker` | 2.6 | Token-specific gates |
| `riskoff_meso` | 2.2 | Risk gates entries |
| `mcap_bucket` | 2.0 | Size affects gate thresholds |
| `effective_conf_meso` | 1.8 | Confirmation for tuning |
| `age_bucket` | 1.6 | Young tokens need different gates |
| `bucket_rank_meso` | 1.6 | Relative performance |
| `chain` | 1.2 | Chain differences |
| `vol_bucket` | 1.2 | Liquidity |
| `effective_opp_meso` | 1.0 | Lower for tuning |
| `riskoff_micro` | 1.0 | Timing guardrail |
| `mcap_vol_ratio_bucket` | 1.0 | Structural |
| `curator` | 0.6 | Lower for tuning |
| `*_macro` | 0.0 | **Macro never gates tuning** |

### 3.5 Selection Rules (Different Per Subsystem)

#### Strength: Blended Overrides

Strength blends all matching overrides using weighted specificity:

```
spec_mass = Σ weight[d] for d in scope_subset
specificity = (spec_mass + 1.0) ** SPECIFICITY_ALPHA
total_weight = confidence_eff * specificity
final_dirA = weighted_average(dirA, total_weight)
final_dirE = weighted_average(dirE, total_weight)
```

**Rationale**: Posture is continuous, blending makes sense.

#### Tuning: Most-Specific with Confidence Fallback (No Blending)

For each gate category (`ts_min`, `halo_max`, `slope_min`, `dx_min`):

1. Collect matching overrides, sort by `spec_mass` descending
2. Pick most-specific that meets `confidence_eff >= CONF_MIN_TUNE`
3. If none meet threshold, fall back to next most-specific
4. If none qualify, use base constants

**No blending** because tuning overrides are optimized solutions.

### 3.6 Regime Compression Formulas (Reference)

#### Opportunity Score (for strength)
Favors *early-to-mid trend* (S1/S2 peak):
```
opp(state): S0=0, S1=3, S2=4, S3=2
opp_h = 3*opp(bucket_h) + 1*opp(alt_h) + 0.5*opp(btc_h)
```

#### Confidence Score (for tuning)
Favors *confirmation* (S2/S3 preferred):
```
conf(state): S0=0, S1=1, S2=3, S3=4
conf_h = 3*conf(bucket_h) + 1*conf(alt_h) + 0.5*conf(btc_h)
```

#### Risk-Off Pressure
```
dom(state): S0=0, S1=1, S2=2, S3=3
riskoff_h = 3*dom(usdtd_h) + 1*dom(btcd_h)
```
Range: 0–12. Classification: 0–2=risk_on, 3–7=mixed, 8–12=risk_off.

#### Bucket Rank (Separate Dimension)
| Rank | Multiplier (for runtime, not scope) |
|------|-------------------------------------|
| 1 | 1.9 |
| 2 | 1.6 |
| 3 | 1.3 |
| 4 | 1.0 |
| 5 | 0.7 |
| 6 | 0.5 |

**Note**: `bucket_rank_meso` is stored as the raw rank (1-6) for scope matching. The multiplier is applied at runtime to opp/conf if desired.

### 3.7 Regime Hierarchy

| Horizon | Role | For Tuning | For Strength |
|---------|------|------------|--------------|
| **Macro** | Wind direction (bull/bear climate) | Never gates | Light multiplier (0.0–0.3) |
| **Meso** | Sea state (where you trade) | **Primary signal** | **Primary signal** |
| **Micro** | Waves & chop (timing) | Secondary guardrail | Timing/friction (0.7) |

**Key Rule**: You sail on meso. Macro doesn't tell you *when* to sail.

### 3.8 Data Preservation

**Critical**: Store **all** raw + derived scores, not just scope-matching keys.

**Per Attempt / Scope, Store:**
- All raw S-states (S0–S3) for each driver × horizon
- All derived scores: `opp_*`, `conf_*`, `riskoff_*` per horizon
- Bucket rank (raw 1-6 + multiplier)

**Rationale**: Learning can later ask "Was it opp_meso or bucket_rank that mattered?" without re-running history.

---

## 4. Actuator Mapping

**Explicit mapping from trajectory classes to allowed actuators**:

| Trajectory Class | Strength A/E | Tuning Gates | Trim Tuning | Notes |
|------------------|--------------|--------------|-------------|-------|
| **clean_winner** | A↑, E↓ | Slightly loosen (scope-specific) | N/A | Press harder, allow more entries |
| **messy_winner** | A neutral/slight↑, E neutral | Mostly no change, or mild tweak | Optional mild tweak | Entry OK, trend weak |
| **managed_loser** | A↓, E↑ | Tighten slightly (scope-specific) | Increase aggressiveness | Entry borderline, trim too weak |
| **immediate_failure** | A↓ (optional), E neutral | Tighten significantly | N/A | Bad entry, tuning should handle |

**Key Rules**:
- **Tuning** primarily responds to `immediate_failure` and `managed_loser` (entry quality issues)
- **Strength** primarily responds to `clean_winner` and `managed_loser` (posture adjustments)
- **Trim tuning** (future) primarily responds to `managed_loser` (trim aggressiveness)
- Scope-specific overrides allow fine-grained adjustments per context

---

## 5. Learning Mechanisms

### 4.1 Attempt vs Action Granularity

**Rule**: Keep attempt as the outcome label, but learn strength per action type.

**Why**:
- Entry and add decisions are triggered at different times, with different scopes (regime can change)
- If you collapse them, you'll blur the signal and miss "good add / bad entry" cases

**The Correct Shape**:
- Every **attempt** gets one trajectory class + ROI
- Each **action event** inside the attempt (entry/add/trim/exit) becomes a learning sample, labeled by the attempt outcome

**What We Learn**:
- **`entry_strength`** lessons: "When we entered under this scope, attempts tended to end as clean winners vs failures"
- **`add_strength`** lessons: Same but with add-time scope
- **(Later) `trim_strength`** lessons: "When we trimmed under this scope, attempts tended to recover vs fail"

**Scope for Adds**:
- Use **add-time context**, not entry context:
  - timeframe, chain, ticker, curator, compressed regime dims at add time, bucket rank, etc.

**Trajectory Class vs ROI for Adds**:
- Use both:
  - ROI = magnitude
  - Trajectory class = direction / actuator mapping

**Result**: Learn separate lessons for `action_category ∈ {entry, add}`. Label each event with the attempt's final `(trajectory_class, roi)`.

### 4.2 Strength Learning (A/E Steering)

**What It Learns**: Posture deltas from attempts.

**Per-Attempt Posture Target**:
Each attempt produces a posture "vote":

| Trajectory Class | ΔA Vote | ΔE Vote | Notes |
|------------------|---------|---------|-------|
| clean_winner | +1 | -1 | Press harder |
| messy_winner | +0.3 (or neutral) | 0 | Entry OK, trend weak |
| managed_loser | -1 | +1 | Entry borderline, trim too weak |
| immediate_failure | -1 | 0 | Entry bad, tuning should handle |

**Per Action Type**: These deltas are **identical** for entry and add actions at v0. (Future: may allow different deltas per action type if evidence supports it.)

**Magnitude** (ROI-weighted):
```
mag = tanh(|roi| / roi_scale)
```

Each attempt contributes `(ΔA_vote * mag, ΔE_vote * mag)`.

**Mining Result Per Slice**:
For each `(pattern_key, action_category, scope_subset)`:
- Compute mean `ΔA_vote`, mean `ΔE_vote`
- Compute confidence
- Store override: `dirA`, `dirE`, `confidence`, etc.

**Runtime Application**:
1. Fetch matching overrides
2. Filter low-confidence if higher-confidence exists
3. Blend `dirA`, `dirE`, and blended confidence
4. Compute dynamic steering strength:
   ```
   STEER_MAX_eff = STEER_BASE + STEER_GAIN * conf_blended
   ```
5. Convert to deltas:
   ```
   ΔA = STEER_MAX_eff * dirA_final
   ΔE = STEER_MAX_eff * dirE_final
   ```
6. Apply with headroom scaling and clamp A/E in [0,1]
7. Sizing derives from A_final (no separate size_mult)

### 4.3 Tuning Learning (Entry Gate Tuning)

**What It Learns**: Optimizes **delta EV** when changing gates.

**Process**:
Using attempts (real + shadow), for each scope slice:
1. Estimate EV of allowing entries under current gates
2. Simulate gate adjustments (ts_min, halo_max, slope_min, dx_min)
3. Compute:
   - Downside avoided
   - Upside lost
4. Accept if tradeoff meets ratio:
   - Accept if `UpsideLost / DownsideAvoided <= 1.69` (configurable)
   - Or use weighted objective: `Score = DownsideAvoided - (1/1.69)*UpsideLost`

**Override Selection**: Most-specific only (do not blend)

**Rationale**: Overrides are optimized solutions. Blending would undo the optimization.

### 4.4 Confidence and N_MIN

#### N_MIN Eligibility

**Minimum attempts per slice to create a lesson/override**:
- **N_MIN_START = 12**
- Below 12: no lesson

#### Confidence Ramps

**Confidence Calculation** (v0, simplified):
```
reliability = 1 / (1 + adjusted_variance)
g(n) = ramp_factor(n)  // Defined below
confidence_eff = reliability * g(n)
```

**Ramp Factor `g(n)`**:
- `n < 12`: `g(n) = 0` (below N_MIN_START, no lesson)
- `12 ≤ n < 33`: `g(n) = 0.2 + 0.3 * (n - 12) / 21` (linear ramp: 0.2 → 0.5)
- `33 ≤ n < 69`: `g(n) = 0.5 + 0.4 * (n - 33) / 36` (steep ramp: 0.5 → 0.9)
- `69 ≤ n < 124`: `g(n) = 0.9 + 0.1 * (n - 69) / 55` (taper: 0.9 → 1.0)
- `n ≥ 124`: `g(n) = 1.0` (asymptote)

**Rationale**: 
- Most growth between 33 and 69
- Taper after 69
- Asymptote near "full" closer to 124–333
- `reliability` captures variance-aware quality (no separate support_score needed)

**Applies to**: Both tuning and strength when weighting lessons.

### 4.5 Scope Weight Learning (MVP Algorithm)

**Goal**: Learn which dimensions matter, starting with priors, evolving over time.

**MVP: "EV Separation Usefulness" + Time-Split Stability + Slow EWMA**

For each actuator type separately (`tuning`, `strength_entry`, `strength_add`), and for each dim `d`:

1. **Take a dataset of labeled samples**:
   - For tuning: attempts (real+shadow)
   - For strength: action events labeled by attempt outcome (real + shadow winners only)

2. **Split by time**:
   - Train window (older)
   - Test window (recent)

3. **Compute usefulness in each window**:
   ```
   EV_global = mean(roi)
   For each value v of dim d:
       EV(v) = mean(roi | d=v)
   U_d = Σ_v p(v) * |EV(v) - EV_global|
   ```
   This answers: "Does this dim meaningfully move EV when you condition on it?"

4. **Stability check**:
   ```
   U_d* = min(U_train, U_test)  // Conservative
   ```

5. **Update weight**:
   ```
   w_d ← clamp((1-α)*w_d + α*(w0 + k*U_d*), w_min, w_max)
   ```
   Where:
   - α is small (0.02 weekly, or 0.01 daily)
   - w0 is baseline (around 1.0)
   - k sets sensitivity

**When to Update**: Daily or weekly (not hourly—too noisy)

**Bounds**:
- w_min ~ 0.3
- w_max ~ 3.0

**Pairs/Triples Later**:
- Only for promoted dims
- Only once singles stabilize

### 4.6 Dimension Weights (Starting Priors)

These weights affect specificity mass (not mining eligibility).

#### Strength Weights (v0)

**High**:
- timeframe
- opportunity_meso, opportunity_macro
- bucket_rank_meso, bucket_rank_macro
- curator
- ticker

**Medium**:
- risk_posture_meso, risk_posture_macro
- chain
- mcap_bucket
- vol_bucket

#### Tuning Weights (v0)

**High**:
- timeframe
- risk_posture_macro, risk_posture_meso
- bucket_rank_macro, bucket_rank_meso
- ticker

**Medium**:
- opportunity_macro, opportunity_meso
- chain
- mcap_bucket

---

## 6. Scope Matching and Selection

### 5.1 Matching Logic

**Matching stays the same**:
- `scope_subset ⊆ scope` (JSONB contains operator)

**Supabase `cd` operator**: Checks if `scope_subset` is **contained in** current `scope`

**Example**:
- Current scope: `{"chain": "solana", "timeframe": "15m", "bucket": "micro"}`
- Override 1: `scope_subset = {}` → ✅ Matches (global)
- Override 2: `scope_subset = {"timeframe": "15m"}` → ✅ Matches
- Override 3: `scope_subset = {"timeframe": "15m", "bucket": "micro"}` → ✅ Matches
- Override 4: `scope_subset = {"timeframe": "1h"}` → ❌ Doesn't match

### 5.2 Strength Selection: Blended

Strength aggregates multiple matching overrides using weighted blending.

**Formula**:
```
specificity = (sum of dimension_weights for dims in scope_subset + 1.0) ** SPECIFICITY_ALPHA
weight = confidence * specificity
final_dirA = weighted_average(dirA, weights)
final_dirE = weighted_average(dirE, weights)
```

**Rationale**: Posture is continuous, blending makes sense.

### 5.3 Tuning Selection: Most-Specific with Confidence Fallback

**Rule**: Most-specific with confidence-based fallback. **No blending**.

**Process**:
For each tuning category (ts_min, halo_max, slope_min, dx_min):

1. Collect all matching overrides for the current scope
2. Sort by specificity mass (not just count) descending
3. Walk from most specific → less specific and pick the first that satisfies:
   - `confidence_eff >= CONF_MIN_TUNE`
   - and `n >= N_MIN_START` (should already be true)
4. If none satisfy, use base constants

**CONF_MIN_TUNE**:
- Small but non-trivial, aligned with ramp
- e.g., `CONF_MIN_TUNE = 0.25` initially
- OR: require `g(n) >= 0.4` (meaning n is at least in the "starting to be real" region)

**Rationale**: Gives specificity when it's earned, fallback to robust general overrides when it isn't. No blending, because tuning overrides are optimized.

---

## 7. Dip-Buys (Trim Pool Redeploy)

### 6.1 Integration into Unified System

**Bring dip-buys into the unified Attempt/Trajectory language**, but treat dip-buys as a **separate "sub-attempt class"** inside an attempt.

**Not**: "Leave it as old episodes forever" (loses unified language)

**Not**: "Force it into the same entry trajectory classes" (dip-buy success criteria are different)

### 6.2 Clean Unified Model

**Layers**:

#### A) Attempt-Level Trajectory (The Full Trade)
The overall attempt still ends as:
- clean_winner / messy_winner / managed_loser / immediate_failure
- Based on final ROI and whether it hit S3 / trimmed / etc.

#### B) Dip-Buy Episode as a "Micro-Attempt" (Tuning-Only Actuator)
Each dip-buy decision becomes its own labeled event:

- **Event type**: `dip_buy_s2` or `dip_buy_s3`
- **Entry**: time of dip buy, redeployed size
- **Outcome label**:
  - success = "this redeploy led to a beneficial outcome" (it trims again / improves outcome)
  - failure = "it went to S0 / forced exit / worsened attempt"

**Tuning learns**:
- Tighten/loosen the dip-buy gating conditions
- By scope at dip-buy time (not entry time)

**Dip-Buy Success/Failure Definition** (v0, deterministic):

**Dip-Buy S2 Success**:
- Within 24 hours after dip-buy, price reaches next trim threshold again
- OR: Attempt's final ROI improves by ≥5% vs same attempt without dip-buy (if counterfactual available)

**Dip-Buy S2 Failure**:
- Attempt hits S0/end before any next trim event occurs
- OR: Attempt's final ROI worsens by ≥5% vs same attempt without dip-buy

**Dip-Buy S3 Success**:
- Within 48 hours after dip-buy, price reaches next trim threshold again
- OR: Attempt's final ROI improves by ≥5% vs same attempt without dip-buy

**Dip-Buy S3 Failure**:
- Attempt hits S0/end before any next trim event occurs
- OR: Attempt's final ROI worsens by ≥5% vs same attempt without dip-buy

**ROI for Dip-Buys**:
- Store `roi_after_dip_buy` (incremental contribution)
- Store `delta_to_next_trim` (time to next trim, if any)

**Result**:
- ✅ Unify it structurally
- ✅ Keep it tuning semantics
- ✅ Don't shove it into strength

### 6.3 Scope Divergence

**They diverge in the correct way**:
- **Entry tuning scope**: entry-time scope
- **Dip-buy tuning scope**: dip-buy-time scope (later regime state)
- **Strength entry sizing**: entry-time scope
- **Strength add sizing**: add-time scope

**Key**: Don't treat them as one scope. Treat them as **scope-at-decision-time** for each decision.

**Rationale**: Otherwise you'll learn nonsense like "this entry scope was good for dip buys" (when the dip buy happened under different market conditions).

**Scope Storage**:
- Both `scope` (attempt-level) and `scope_at_action` (action-level) must contain **raw states + derived composites**
- Store all regime states (S0–S3) for each driver
- Store all derived scores (opp, conf, riskoff per horizon)
- Store bucket rank (raw + multiplier)

---

## 8. Windows and Decay

### 7.1 All-Time First

**Rule**: Use **all-time** aggregates at first.

**Rationale**:
- Won't have enough samples for fancy train/test splits per scope
- All-time is simplest and most stable early on

### 7.2 Decay Later (If Needed)

**Optionally keep**:
- "Short" EWMA (14d) and "long" EWMA (90d) later, once volume exists
- If you add decay, do it as a **single multiplier** on sample weight, not as extra complexity everywhere

**Start**: All-time  
**Add decay**: Only when you actually see drift

---

## 9. Current State Analysis

### 9.1 What We Have Now

**Decision Maker Learning System** (Separate System):
- Updates timeframe weights using **R/R** (not ROI)
- Uses EWMA with 14-day decay for timeframe R/R
- Calculates weight: `weight = timeframe_rr_short / global_rr_short`
- Normalizes weights to sum to 1.0
- Applies weights when creating new positions

**Current Flow**:
1. Position closes → `position_closed` strand created
2. `UniversalLearningSystem` processes strand
3. `_update_coefficients_from_closed_trade()` extracts R/R
4. `CoefficientUpdater.update_coefficient_ewma()` updates timeframe R/R (EWMA)
5. Calculates new weight from R/R ratio
6. Stores in `learning_configs.config_data.timeframe_weights`
7. `DecisionMaker` reads weights and normalizes for allocation splits

**Current Issues**:
1. ❌ Uses R/R instead of ROI (R/R can be negative for profitable trades)
2. ❌ No gradual allocation changes (weights jump instantly)
3. ❌ No requirement for minimum 2 timeframes with trades
4. ❌ No per-trade cap on allocation changes
5. ❌ No min_trades discount
6. ❌ 1m timeframe still included (should be removed)

**PM Tuning System**:
- TuningMiner exists but is not scheduled
- Uses episode-based approach (not attempt-based)
- Calculates overall pressure and applies to all thresholds equally
- Missing threshold values in episode events
- No factor-specific tuning

**PM Strength System**:
- Uses R/R (not ROI) for edge calculation
- Applies `size_mult` directly to `position_size_frac`
- Does not consider outcome shape (trimmed? reached S3?)
- Single scalar multiplier (no A/E steering)

### 9.2 A/E v2 Enablement (Prerequisite)

**Current State**:
- **A/E v2 is NOT enabled** - system defaults to legacy `compute_levers()` method
- Code checks: `pm_cfg.get("feature_flags", {}).get("ae_v2_enabled", False)`
- Default is `False` when flag is missing
- No PM config entry in `learning_configs` table

**What Needs to Happen**:
Enable A/E v2 by adding `feature_flags.ae_v2_enabled = True` to PM config in database.

**SQL to enable**:
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

**Or if PM config already exists**:
```sql
UPDATE learning_configs 
SET config_data = jsonb_set(
    COALESCE(config_data, '{}'::jsonb),
    '{feature_flags}',
    COALESCE(config_data->'feature_flags', '{}'::jsonb) || '{"ae_v2_enabled": true}'::jsonb
)
WHERE module_id = 'pm';
```

**Verification**:
- Check logs for `"AE_V2: ..."` messages (v2 logs this, legacy doesn't)
- Verify A/E computation uses flag-driven method instead of regime-driven

**Impact**:
- Switches from complex regime-driven A/E (5 drivers × 3 timeframes) to simpler flag-driven method
- Both produce A/E in [0.0, 1.0] range, so PM Strength application works the same
- v2 is simpler and designed to work better with PM Strength learning

---

## 10. Implementation Checklist

### Phase 0: Prerequisites
- [ ] Enable A/E v2 computation (see Section 9.2)
- [ ] Verify A/E v2 is working correctly

### Phase 1: Core Infrastructure
- [ ] Create `attempt_events` table (or adapt `pattern_trade_events`)
- [ ] Implement trajectory class computation
- [ ] Implement shadow attempt simulation (counterfactual entry)
- [ ] Implement regime compression mapping (deterministic v0)
- [ ] Store all raw + derived regime scores

### Phase 2: Mining
- [ ] Implement attempt-level mining (trajectory classes + ROI)
- [ ] Implement action-level strength mining (entry, add)
- [ ] Implement tuning mining (with shadow attempts)
- [ ] Implement confidence ramp `g(n)`

### Phase 3: Override Materialization
- [ ] Materialize strength overrides (dirA, dirE, confidence)
- [ ] Materialize tuning overrides (most-specific only)
- [ ] Implement scope weight learning (MVP algorithm)

### Phase 4: Runtime Application
- [ ] Implement strength blending (weighted average of dirA/dirE)
- [ ] Implement tuning selection (most-specific with confidence fallback)
- [ ] Implement dynamic STEER_MAX_eff
- [ ] Apply headroom scaling to A/E deltas

### Phase 5: Dip-Buys
- [ ] Integrate dip-buys as tuning-labeled micro-attempts
- [ ] Implement dip-buy success/failure labeling
- [ ] Scope dip-buys at dip-buy time

---

## 10. Authoritative Decisions (Locked)

### 9.1 Attempt vs Action Granularity
- ✅ Attempt = outcome label (trajectory class + ROI)
- ✅ Strength learns per action type (entry, add, trim)
- ✅ Each action event labeled by attempt outcome
- ✅ Scope for adds = add-time context

### 9.2 Regime Compression
- ✅ Deterministic v0 mapping (explicit polarity)
- ✅ S1 = positive (ignition), not weak
- ✅ USDT.d / BTC.d inverted (S3 = risk-off)
- ✅ Bucket rank = multiplier on opportunity, not standalone
- ✅ Store all raw + derived scores

### 9.3 Confidence and N_MIN
- ✅ N_MIN_START = 12
- ✅ Confidence ramp: most growth 33–69, asymptote 124–333
- ✅ `confidence_eff = confidence_base * g(n)`

### 9.4 Tuning Selection
- ✅ Most-specific with confidence threshold fallback
- ✅ No blending (overrides are optimized)
- ✅ CONF_MIN_TUNE = 0.25 (or g(n) >= 0.4)

### 9.5 Strength Selection
- ✅ Blended (weighted average of dirA/dirE)
- ✅ Uses specificity (dimension-weighted) + confidence

### 9.6 Shadow Attempts
- ✅ Tuning: all real + all shadow attempts
- ✅ Strength: real attempts + shadow winners only
- ✅ Counterfactual entry using deterministic PM logic

### 9.7 Regime Hierarchy
- ✅ Meso = primary signal
- ✅ Macro = context (never gates)
- ✅ Micro = timing/friction (secondary guardrail)

### 9.8 Windows
- ✅ All-time first
- ✅ Decay later if needed (single multiplier on sample weight)

---

## 11. Decision Maker Learning (Separate System)

**Status**: Not part of unified learning system - handled separately

**Purpose**: Adjusts timeframe allocation based on ROI performance

**Key Difference**: Decision Maker Learning is about **allocation** (which timeframes get capital), not about **pattern strength** or **entry tuning**.

### 11.1 Current State

**Current System**:
- Updates timeframe weights using **R/R** (not ROI)
- Uses EWMA with 14-day decay for timeframe R/R
- Calculates weight: `weight = timeframe_rr_short / global_rr_short`
- Normalizes weights to sum to 1.0
- Applies weights when creating new positions

**Current Issues**:
1. ❌ Uses R/R instead of ROI (R/R can be negative for profitable trades)
2. ❌ No gradual allocation changes (weights jump instantly)
3. ❌ No requirement for minimum 2 timeframes with trades
4. ❌ No per-trade cap on allocation changes
5. ❌ No min_trades discount
6. ❌ 1m timeframe still included (should be removed)

### 11.2 New Requirements

**Starting Allocation**:
- **15m**: 15%
- **1h**: 50%
- **4h**: 35%
- **1m**: Remove (no longer used)

**Update Rules**:
1. Only update when at least 2 timeframes have closed trades
2. Use ROI instead of R/R
3. Gradual allocation changes (max 0.3% per trade, capped by min_trades)
4. Store current allocation in `learning_configs`

### 11.3 Implementation Plan

**Files to modify**:
1. `src/intelligence/universal_learning/universal_learning_system.py`
   - `_update_coefficients_from_closed_trade()`: Extract `rpnl_pct` instead of `rr`
   - `_update_global_rr_baseline_ewma()`: Rename to `_update_global_roi_baseline_ewma()`

2. `src/intelligence/universal_learning/coefficient_updater.py`
   - `_update_timeframe_weight_ewma()`: Rename to `_update_timeframe_roi_ewma()`
   - Add `_update_timeframe_allocation()` method
   - Add `_update_existing_positions_allocation()` method

3. `src/intelligence/universal_learning/coefficient_reader.py`
   - `get_timeframe_weights()`: Read `current_allocation` instead of `weight`

4. `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`
   - Remove 1m from timeframe splits

---

## 12. Open Questions (Future Work)

1. **Trim Tuning**: How to integrate trim aggressiveness learning?
2. **Pair/Triple Interactions**: When to add dimension interaction bonuses?
3. **Shadow Attempt Validation**: How to validate shadow attempt accuracy?
4. ~~**Ticker Dimension**: How to handle scope explosion with 1000+ tickers?~~ **RESOLVED**: N_MIN handles this naturally—lessons are only created when sufficient volume exists for a ticker. No clustering needed.
5. **Regime Compression Learning**: When to make compression mapping learnable?

---

## Appendix: Regime State Semantics

### Legacy Note

**Critical**: Any "recover/dip" labels referenced elsewhere are **legacy** and must **not** be used in vNext logic.

**Current regime language**: **S0–S3** (not "Recover/Dip")

**Examples of legacy references to ignore**:
- `btc_macro=Recover`
- `alt_macro=Dip`
- Any recovery/dip labels in old documentation or IDE responses

### State Meanings

**Risk-On Assets** (BTC, ALT, BUCKET):
- **S0**: Bearish / dead
- **S1**: Transition / ignition (positive, not weak)
- **S2**: Early trend
- **S3**: Strong trend

**Dominance Metrics** (USDT.d, BTC.d, **inverted**):
- **S0**: Risk-on (bullish for dominance)
- **S1**: Low risk-off pressure
- **S2**: Moderate risk-off pressure
- **S3**: Max risk-off pressure (bearish for dominance)

**Key Point**: USDT.d and BTC.d are **inverted** relative to risk-on assets. S3 = bearish/risk-off, S0 = bullish/risk-on.

---

## 13. Learning System Logging Plan

**New Log File**: `logs/learning_system.log`

### 13.1 What to Log

#### TuningMiner Execution
- Start/Completion: When TuningMiner runs, how many events processed, how many lessons created
- Lesson Creation: Each lesson created (pattern_key, scope_subset, n, rates)
- Scope Slicing: Which scope slices passed N_MIN threshold
- Errors: Failures in mining or lesson creation

#### Override Materializer Execution
- Start/Completion: When Override Materializer runs, how many lessons processed
- Simulation Results: For each lesson, best adjustment found (lever, ratio, misses_caught, failures_added)
- Override Creation: Each override created (pattern_key, action_category, multiplier, scope)
- No Override Reasons: Why no override was created (ratio < 2.0x, no good solution, etc.)

#### Attempt Event Logging
- Event Logged: When attempt event is logged (pattern_key, attempt_id, is_shadow)
- Outcome Updated: When attempt outcome is updated (attempt_id, trajectory_class, roi)
- Missing Data Warnings: When required data is missing

#### Decision Maker Learning (Timeframe Allocation)
- Allocation Update: When allocation changes (old allocation, new allocation, trigger trade)
- ROI Updates: When timeframe ROI is updated (timeframe, new_roi, n_trades)
- No Change Reasons: Why allocation didn't change (need 2+ timeframes, etc.)

#### PM Strength Learning
- Strength Override Creation: When PM strength override is created (pattern, dirA, dirE, confidence)
- No Override Reasons: Why no strength override (edge < threshold, etc.)

### 13.2 Log File Configuration

**Add to `src/run_trade.py` loggers dictionary**:
```python
loggers = {
    # ... existing loggers ...
    'learning_system': 'logs/learning_system.log',
}
```

**Use in learning system code**:
```python
import logging
logger = logging.getLogger('learning_system')
logger.info("TuningMiner starting | events=%d | lookback_days=%d", n_events, lookback_days)
```

### 13.3 Log Levels

- **INFO**: Normal operations (miner runs, overrides created, allocations updated)
- **WARNING**: Missing data, skipped operations, no good solutions found
- **ERROR**: Failures in mining, materialization, or allocation updates

---

## 14. Implementation Details

### 14.1 File Paths

**Core Infrastructure**:
- `src/database/attempt_events_schema.sql` (or adapt `pattern_trade_events_schema.sql`)
- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` (trajectory class computation)
- `src/intelligence/lowcap_portfolio_manager/jobs/shadow_attempt_simulator.py` (new file)

**Mining**:
- `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py` (adapt for attempt-level)
- `src/intelligence/lowcap_portfolio_manager/jobs/tuning_miner.py` (adapt for attempt-level)
- `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py` (adapt for new format)

**Runtime**:
- `src/intelligence/lowcap_portfolio_manager/pm/overrides.py` (strength blending, tuning selection)
- `src/intelligence/lowcap_portfolio_manager/pm/actions.py` (apply overrides)

**Regime Compression**:
- `src/intelligence/lowcap_portfolio_manager/pm/regime_compression.py` (new file)

### 14.2 Data Capture Requirements

**For Attempt Events**:
- Threshold values at entry time (ts_min, halo_max, slope_min, dx_min)
- Gate flags (entry_zone_ok, ts_ok, slope_ok)
- Blocked_by array (for shadow attempts)
- All raw regime states (S0–S3) for each driver
- All derived scores (opp, conf, riskoff per horizon)
- Bucket rank (raw + multiplier)

**For Action Events**:
- Scope at action time (may differ from entry scope)
- A/E values at action time
- Size fraction

### 14.3 Migration Notes

> [!IMPORTANT]
> **Starting Fresh**: There are no existing lessons to migrate. The `learning_lessons` table is deprecated and will not be used by vNext.

**Deprecated Tables**:
- `learning_lessons` → **Deprecated** (starting fresh, no migration needed)
- `pattern_episode_events` → **Retained** for reference, but vNext uses `attempt_events`

**New Tables**:

#### `pm_strength_overrides` (New Table for Strength Learning)

```sql
CREATE TABLE pm_strength_overrides (
    id BIGSERIAL PRIMARY KEY,
    pattern_key TEXT NOT NULL,                      -- e.g., "pm.uptrend.S1.entry"
    action_category TEXT NOT NULL,                  -- "entry" | "add"
    scope_subset JSONB NOT NULL,                    -- Scope slice: {"chain": "solana", "timeframe": "1h"}
    
    -- Strength Steering
    dirA FLOAT NOT NULL DEFAULT 0.0,                -- Direction for A: -1 to +1
    dirE FLOAT NOT NULL DEFAULT 0.0,                -- Direction for E: -1 to +1
    confidence FLOAT NOT NULL DEFAULT 0.0,          -- Blended confidence (0-1)
    
    -- Mining Stats
    n INT NOT NULL DEFAULT 0,                       -- Sample count
    mean_roi FLOAT,                                 -- Mean ROI of samples
    trajectory_counts JSONB,                        -- {"clean_winner": 5, "immediate_failure": 2, ...}
    
    -- Metadata
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (pattern_key, action_category, scope_subset)
);

CREATE INDEX idx_pm_strength_overrides_lookup ON pm_strength_overrides(pattern_key, action_category);
CREATE INDEX idx_pm_strength_overrides_scope ON pm_strength_overrides USING GIN(scope_subset);
```

**Existing Tables (Adapted)**:
- `pm_overrides` → **Retained** for tuning overrides (ts_min, halo, dx_min multipliers)
- `pattern_trade_events` → **Adapt** to `attempt_events` format (add trajectory_class, reached_s3 columns)

---

## 15. Related Documents

- **`scope_system_deep_dive.md`**: Deep dive into scope dimensions and matching
- **`learning_system_update_plan.md`**: ⚠️ **Deprecated** - All content has been consolidated into this document
