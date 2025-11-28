# Simplified Allocation & Global Edge Plan

**Status**: Draft proposal  
**Author**: ChatGPT  
**Date**: 2025-11-24  

---

## 1. Goals

1. Remove the Decision Maker (DM) learning layer and collapse allocation logic down to a single `base → strength → exposure` pipeline.
2. Make "edge" a single, global measurement shared by every stage of the pipeline, so we no longer run separate coefficient flows.
3. Keep PM sizing responsive to two signals only:
   - **Observed performance** (`pm_strength`, learned edge by pattern + scope masks).
   - **Current crowding** (`exposure_skew`, new logic that mirrors the same mask language).
4. Ensure the entire plan is easy to reason about, easy to inspect, and compatible with future extensions.

---

## 2. Allocation Formula (Single Path)

```
base_alloc = config.default_allocation_pct      # e.g. 10%
pm_strength = clamp(edge_lookup(pattern_key, scope), 0.3, 3.0)
exposure_skew = clamp(exposure_lookup(pattern_key, scope), 0.33, 1.33)

max_alloc = base_alloc * (pm_strength * exposure_skew)
```

Key points:

- **DM** no longer applies learned coefficients. It simply approves a token with `base_alloc` (today: 10%). That knob lives in config and can be A/B tested later.
- **DM** still splits that `base_alloc` across the four timeframes using the existing learned timeframe weights (fallback: current defaults). This is the only surviving use of the coefficient reader; everything else (alloc multipliers, crowding, etc.) is removed.
- **PM** handles all dynamic sizing via `pm_strength` and `exposure_skew`.
- There is no special-case multiplier stacking. Everything flows through the same formula.

---

## 3. pm_strength (Existing Logic, Now Global)

### 3.1 What stays the same

- The `pattern_scope_aggregator` continues to read every `position_closed` strand and compute edge statistics by `(pattern_key, action_category, scope_mask)`.
- `pm_strength` looks up the best matching masks (coarse → specific) and blends them to produce a multiplier `[0.3, 3.0]`.
- Lessons/overrides still come from `pattern_scope_stats`. Nothing fundamental changes here.

### 3.1.1 Runtime wiring

- We keep the existing override pipeline (`pattern_scope_stats` → `lesson_builder_v5` → `learning_configs.pattern_strength_overrides`) so we do not need to reinvent storage. The only change is semantic: the `size_mult` lever is renamed to `pm_strength`, and downstream callers treat it as “the” multiplier in the `base × strength × exposure` formula.
- `plan_actions_v4` and the A/E lever stack remain untouched. They still emit a raw `size_frac` based on A/E + geometry. Immediately before execution we multiply that `size_frac` by the resolved `pm_strength` (with decay already baked in) and later by `exposure_skew`.
- Because we are still using the override infrastructure, the override materializer simply writes `pm_strength` entries instead of `size_mult`. No new Supabase tables are required. The only override category the DM continues to care about is the timeframe-weight helper; `dm_alloc` overrides are retired with the coefficient stack.

### 3.2 What changes

1. **Scope Dimensions**: We now use the full union of entry-context, action-context, and regime dimensions. (See Section 5.)
2. **Bitmask**: `scope_mask` becomes `INTEGER` (max 32 dims) instead of `SMALLINT` (max 16). This lets us include all dims.
3. **Global Edge Definition**:
   - Every closed trade updates the same `pattern_scope_stats` table.
   - We compare `avg_rr`/`edge_raw` for a candidate scope against **all historical trades** that share the same mask (never against a module-specific subset). The baselines are also global.
4. **Per-mask Decay**:
   - For each mask we already use in the strength ladder, we will also compute a decay multiplier (see §6.2) and apply it to that mask’s edge before blending.
5. **Fallbacks**:
   - If no mask meets `N_min` for a candidate scope, we return a neutral `pm_strength = 1.0`. The trade therefore falls back to the DM’s base allocation percentage (10% today) with no strength boost.

Practically: once a trade closes it is indistinguishable from any other trade for learning purposes; scope alignment is the only filter that determines the comparison set, and both edge magnitude + decay are evaluated per mask before we blend the ladder into `pm_strength`.

---

## 4. exposure_skew (New Logic)

### 4.1 Motivation

- We want to **de-prioritize** patterns/scope clusters where we already have a lot of capital deployed.
- We want to **favor** novel clusters where we currently have little or no exposure.
- We need to respect the same mask structure as pm_strength so "similarity" is measured in the same language.

### 4.2 Precomputation (per PM tick or as a cached service)

For every active position `j`:

1. Retrieve `(pattern_key_j, full_scope_j, exposure_pct_j)`.
2. For every mask `m` in our mask set:
   - If `full_scope_j` has all dims in `m`, accumulate exposure:
     - `scope_exposure[m] += w_mask(m) * exposure_pct_j`
     - `pk_scope_exposure[(pattern_key_j, m)] += w_mask(m) * exposure_pct_j`
   - `w_mask(m)` favors more specific masks (same weighting config we use for `pm_strength` resolution: `weight = (Σ present_dim_weights / Σ all_dim_weights)^α` with per-dimension weights defaulting to 1.0 and `α ≈ 0.5`, all stored in the PM config).
   - Exposure percentages come directly from each position’s `total_allocation_pct` (or the remaining USD allocation for partially filled entries). Dormant positions contribute 0; watchlist/active positions contribute their configured percentage regardless of current fill, so crowding reflects intended capital rather than executed fills.
   - We recompute the exposure maps once per PM tick and cache them for the duration of that tick; cache invalidation is as simple as “run the precompute step again” whenever the PM loop starts.

This gives us two maps:

- `scope_exposure`: how crowded each scope mask is.
- `pk_scope_exposure`: same but keyed by pattern+mask (lower importance).

### 4.3 Lookup for a candidate

For candidate `(pattern_key*, scope*)`:

1. For each mask `m` that matches `scope*`, read:
   - `scope_exposure[m]`
   - `pk_scope_exposure[(pattern_key*, m)]`
2. Combine into a concentration metric:
   ```
   conc_total = α * Σ scope_exposure[m] + β * Σ pk_scope_exposure[(pattern_key*, m)]
   ```
   where `α > β` (scope similarity matters more than exact pattern_key).
3. Normalize `conc_total` against the engine’s total exposure (or a configurable cap) to produce `conc_norm ∈ [0, 1]`.
4. Map to skew multiplier:
   ```
   exposure_skew = 1.33 - conc_norm
   ```
   - `conc_norm = 1` ⇒ `0.33x` (very crowded)
   - `conc_norm = 0` ⇒ `1.33x` (completely empty neighborhood)

This matches the spec:
- If 100% of exposure sits in the exact same mask combination, a new trade there gets minimum sizing.
- If no existing position overlaps on any mask, the trade gets the maximum boost.

### 4.4 Telemetry / strands

- Every `pm_action` strand already carries a `reasons` dict (flag, state, scores, etc.). We add two explicit fields: `pm_strength_applied` and `exposure_skew_applied`. They live both in the strand payload and in the telemetry dashboards so we can audit how the combined multiplier evolved over time.

---

## 5. Scope Dimensions (Unified)

We now treat **all** dimensions as first-class for both edge and exposure:

| Source        | Dimensions |
|---------------|------------|
| Entry context (captured when the trade is approved) | `curator`, `chain`, `mcap_bucket`, `vol_bucket`, `age_bucket`, `intent`, `mapping_confidence`, `mcap_vol_ratio_bucket` |
| Action context (captured when PM plans/executes) | `market_family`, `timeframe`, `A_mode`, `E_mode` |
| Regime / Shared | `macro_phase`, `meso_phase`, `micro_phase`, `bucket_leader`, `bucket_rank_position`, `bucket` (alias for `mcap_bucket`) |

Notes:

- **Action item**: unify `bucket` vs `mcap_bucket`. They refer to the same cap bucket; we currently store both in different places. We should pick a single canonical key (likely `mcap_bucket`) and remove the duplicate. DM will continue to populate `mcap_bucket`, `vol_bucket`, `intent`, `mapping_confidence`, and `mcap_vol_ratio_bucket` when it approves the trade, so PM simply carries that entry context forward.
- Additional dims  can be added later; our bitmask now has room.
- `entry_context` + `action_context` + `regime_context` are merged into a unified scope before aggregation or exposure calculations.

---

## 6. Edge Calculation (Global Definition)

1. **Data**: Every closed trade writes its `trade_summary` plus the unified scope (entry context + action context + regime context) into `pattern_scope_stats`.
2. **Aggregation**:
   - For each `(pattern_key, action_category, mask)` subset, we track:
     - `sum_rr`, `sum_rr_squared`, `n`, `avg_rr`, `variance`, `edge_raw`, etc.
   - Incremental updates happen whenever a trade closes.
3. **Baseline**: `get_rr_baseline()` uses a single global baseline (all trades) so rr and edge are measured against the entire population, not a bucket/timeframe subset.
4. **Edge Raw**: `compute_edge_with_regime_weights(...)` compares `avg_rr` vs baseline, adjusts for variance, time efficiency, etc.
5. **Global**: Edge calculations and comparisons happen against *all* trades that share the same mask.
6. **Lesson Builder**: Still runs the same pipeline; it now has richer scopes but the logic (N_MIN, edge_min, incremental edge) stays unchanged.

> **Note:** We keep the existing `learning_baselines` table around for telemetry/backfill purposes, but it is considered legacy and no longer participates in runtime strength calculations once the global baseline is in place.

### 6.1 Edge Components (6-D definition)

We now store each dimension of edge explicitly inside `pattern_scope_stats.stats` so downstream consumers can inspect the full vector, not just the scalar `edge_raw`.

- `ev_score` — expected value advantage (`EV`)
- `reliability_score` — reliability (`rel`)
- `support_score`
- `magnitude_score`
- `time_score`
- `stability_score`
- `edge_raw` — final scalar edge (`EV × rel × integral`)

#### Normalization formulas

| Dimension | Formula (0–1) |
|-----------|---------------|
| `ev_score` | `sigmoid(delta_rr / 1.0)` |
| `reliability_score` | `1 / (1 + variance_rr)` |
| `support_score` | `1 - exp(-n / k)` (k ≈ 10–15) |
| `magnitude_score` | `sigmoid(median_rr / 1.0)` |
| `time_score` | `1 / (1 + log(1 + duration_hours))` (using time-to-S3 metric) |
| `stability_score` | `1 / (1 + edge_volatility)` (edge volatility = std of recent edge values) |

#### Final edge scalar

```
EV = delta_rr
rel = 1 / (1 + variance_rr)
integral = support_score + magnitude_score + time_score + stability_score  # summed in natural units
edge_raw = EV × rel × integral
```

These scalars will be stored inside `pattern_scope_stats.stats` (the aggregator will compute and persist them for every mask). That way any consumer (pm_strength, telemetry, overrides, LLM layers) can reason about per-dimension behavior, not just the composite. The same stats JSON will also house the decay metadata (see §6.2) so there’s a single place to read edge + decay.

### 6.2 Edge Decay (per-mask, slope + exponential)

We compute decay directly from the per-mask time series stored in `learning_edge_history`. The idea is identical to the strength ladder: every mask gets its own decay multiplier before blending.

1. For each mask we care about (bucket-only, bucket+timeframe, full scope, etc.):
   - Build the exact signature for that mask (same key/value subset we stored in `pattern_scope_stats`).
   - Query **all available** `(edge_raw, ts)` snapshots for that mask (optionally time-bounded, but not an arbitrary “last N” trade count).
   - Require at least **18** snapshots before attempting any decay classification. If the history is shorter, we skip decay and default the multiplier to `1.0`.
2. Sort by timestamp, convert to elapsed hours since the first observation.
3. Fit two curves:
   - **Linear** `edge = a + b * time` → slope `b` (edge/hour) for quick direction/speed.
   - **Exponential** `edge = A * exp(B * time)` → growth/decay rate `B` and half-life `half_life_hours = ln(2) / |B|`.
4. Classify the mask:
   - Improving (B > 0 / slope > +ε)
   - Decaying (B < 0 / slope < −ε)
   - No clear pattern (|B| small and slope ≈ 0)
   - Speed determined by |B| (if exponential fit is good) or |slope|.
5. Map to a **decay multiplier per mask**:
   - `decay_mult ∈ [0.33, 1.33]`
   - Fast decays (short half-life) pull toward 0.33x.
   - Fast improvements push toward 1.33x.
   - Stable/no pattern ⇒ multiplier ≈ 1.0.
   - We treat improving vs decaying asymmetrically: strong positive slope can get a larger boost, while rapid decay shrinks more aggressively.
6. Apply this `decay_mult` to the mask’s edge before the weight/blend step, so `pm_strength` already reflects decay when it comes out of the ladder.

Storage:

- We will add decay metadata (linear slope, exponential rate, half-life, decay_state) into `pattern_scope_stats.stats` so the latest values are persisted alongside the edge dimension scores. This lets pm_strength, telemetry, exposure skew, or future modules inspect decay without re-querying raw history.

Implementation detail:

- The legacy helper `adjust_multiplier_for_edge_direction()` in the overrides layer will be retired once decay lives inside the mask loop. All decay adjustments happen before blending, so the final `pm_strength` already includes decay. Overrides no longer need to post-process the multiplier.

---

## 7. Implementation Checklist

1. **Remove DM allocation learning**
   - Delete all coefficient reader usage from DM except the timeframe-weight helper (the only learner we keep).
   - Remove DM allocation overrides/materializer entries.
   - DM config now only needs `default_allocation_pct` plus the timeframe-weight tuning hook.
2. **Update Scope Mask**
   - Change `pattern_scope_stats.scope_mask` to `INTEGER`.
   - Update SQL schema comments + docs.
   - Expand `SCOPE_DIMS` in `pattern_scope_aggregator`.
3. **Unified Scope Extraction**
   - Build helper to merge `entry_context` + `action_context` + `regime_context` into a single scope dict.
   - Ensure `pattern_scope_aggregator` uses this unified scope when inserting stats.
4. **Exposure service**
   - New helper to compute `scope_exposure` and `pk_scope_exposure` maps from active positions.
   - Integrate into PM sizing (likely inside `pm_core_tick`).
5. **Sizing update**
   - Replace existing position sizing multipliers with `base * pm_strength * exposure_skew`.
   - Keep clamps and logging so we can audit final numbers.
6. **Override rename**
   - Update `lesson_builder_v5` + `override_materializer` so the `size_mult` lever is now stored/emitted as `pm_strength`.
   - Ensure PM runtime multiplies the existing `size_frac` by the renamed lever before applying `exposure_skew`.
7. **Docs & telemetry**
   - Update `PM_Learning_Flow_Test_Plan.md` and telemetry dashboards to reflect the simplified pipeline.
   - Add metrics/strand fields for both `pm_strength` and `exposure_skew` so we can audit final multipliers end-to-end.

---

## 8. Open Questions / Next Steps

1. **Mask weights**: `pattern_key` is always required (not part of the weighting map), but we still need a config for how much extra weight the scope dimensions add (e.g., bucket-only vs bucket+timeframe vs full scope). Plan: use a configurable power-law curve `weight = (Σ scope_dim_weights / Σ all_scope_dim_weights)^α` with `α < 1` (e.g., 0.5) so more dims matter but with diminishing returns. Expose both `α` and the per-scope-dimension weights (default 1.0) in config so we can tune them later.
2. **Edge clamps**: keep an eye on whether the `[0.3, 3.0]` pm_strength clamp still feels right after the decay + exposure work. For now we’re keeping it as-is.
3. **Telemetry**: log both `pm_strength` and `exposure_skew` into every `pm_action` strand so we can inspect trades without extra tooling. (Add to strand payload + dashboards.)

---

This plan keeps PM flexible, removes the DM-specific learning maintenance burden, and exploits the same mask machinery for both strength and exposure. Let me know where you’d like deeper detail or prototypes next.

