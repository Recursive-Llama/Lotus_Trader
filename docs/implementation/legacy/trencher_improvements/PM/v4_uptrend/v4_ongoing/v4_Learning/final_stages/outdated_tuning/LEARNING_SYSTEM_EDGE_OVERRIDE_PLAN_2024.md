[Archived on 2025-11-20]

The full “Edge-Weighted Learning & Override Plan” has been moved here for historical reference. Please consult `PM_Learning_System.md` for the current implementation status.

---

## Edge-Weighted Learning & Override Plan

**Scope:** Complete plan for DM pattern learning and PM pattern-strength overrides (with exact math), plus current state + gaps for PM tuning. This is the “do-first” part of the v5 tightening.  
**Status:** Draft plan for implementation.

---

### 1. Reality Check – What Already Works

| Layer | What we have today | Notes |
|-------|--------------------|-------|
| **DM Coefficient Learning** | `learning_coefficients` via `coefficient_updater.py`. EWMA on curator/chain/cap/age/etc with explicit decay (`TAU_SHORT=14d`, `TAU_LONG=90d`) and clamps (`weight∈[0.5,2.0]`). | Baseline allocator. |
| **PM Pattern Strength** | `pattern_scope_stats` → `lesson_builder_v5` → capital levers (`size_mult`, `entry_aggression_mult`, `exit_aggression_mult`) with `learning_rate=0.02`, `edge_scale=20`, clamps (`size∈[0.7,1.3]`, aggression∈[0.8,1.2]`). | Already edge-based, but runtime picks only the most specific override. |
| **PM Tuning** | Counterfactual buckets `cf_entry_improvement_bucket` / `cf_exit_improvement_bucket` drive just five levers: `entry_delay_bars`, `phase1_frac_mult`, `trim_delay_mult`, `trail_mult`, and two fixed signal thresholds (`min_ts_for_add=0.55`, `min_ox_for_trim=0.40`). | Everything else in `PM_Learning_Lever_Map.md` is not wired yet. Buckets are based solely on missed R/R, no signal context. |

---

### 2. Goal

1. **DM pattern learning**: Add edge-based overrides on top of coefficient weights so allocation reacts to learned patterns, not just raw lever EWMA.
2. **PM pattern strength**: Replace “pick most specific override” with **edge-weighted composable overrides**. Make edge/confidence explicit in every override.
3. **PM tuning**: Document current state + precise gaps. (Implementation plan deferred until counterfactual detail is ready.)

---

### 3. Edge-Weighted Override Engine (applies to DM + PM strength)

**Override schema additions**

```json
{
  "type": "dm_alloc" | "pm_strength" | "pm_tuning",
  "pattern_key": "...",
  "action_category": "...",
  "scope": {...},
  "stats": {
    "edge_raw": 0.82,
    "n": 37,
    "variance": 0.45,
    "half_life_days": 18,
    "updated_at": "2025-01-11T00:00:00Z"
  },
  "levers": {
    "capital_levers": {...},
    "execution_levers": {...}
  }
}
```

**Weight calculation per override**

```
w_edge = tanh(|edge_raw| / edge_scale)              # edge_scale default = 1.0
w_n    = 1 - exp(-n / n_target)                     # n_target default = 25
w_var  = 1 / (1 + variance_penalty * variance)      # variance_penalty default = 1.0
w_decay= exp(-age_days / half_life_days)
w_spec = (num_scope_dims / max_scope_dims)^alpha    # alpha default = 1.5
w_total = w_edge * w_n * w_var * w_decay * w_spec
ignore override if w_total < 0.02
```

**Combining overrides for a lever**

- Multiplicative levers (size_mult, alloc_mult, entry/exit aggression, trail_mult): blend in log space.
- Additive levers (entry_delay_bars, thresholds): weighted average toward target.
- Each lever has a **max per-call movement** (e.g. ±0.02 in multiplier space, ±0.2 bars) to keep behavior smooth.
- Final value clamped to the safety bounds already defined in PM config.

---

### 4. DM Pattern Learning Plan

1. **Pattern stats**: Reuse `pattern_scope_stats` (module=`dm`). Ensure DM action logs already include pattern keys and scopes (they do; PM+DM share the schema).
2. **Lesson builder**: `lesson_builder_v5` already supports module arg. For DM:
   - `action_category = "allocation"` (single category for now).
   - Capital lever: `alloc_mult_target` (bounded 0.7–1.3, learning_rate=0.02, edge_scale=20).
   - Store in `learning_lessons` with `type="dm_alloc"`.
3. **Override materializer**: When `module='dm'`, write overrides into `learning_configs.dm.config_data.alloc_overrides`.
   - Include `stats` block (edge_raw, n, variance, half_life).
4. **Runtime**: Extend DM allocation pipeline to:
   - Load `alloc_overrides`.
   - For each position/universe, gather all overrides where `scope ⊆ current_scope`.
   - Combine into final `alloc_mult` using the weight formula.
   - Multiply DM coefficient-based allocation by this `alloc_mult` (before PM stage).

**Exact numbers**

| Parameter | Value |
|-----------|-------|
| `learning_rate` | 0.02 (max ±2% movement per lesson update) |
| `alloc_mult bounds` | 0.7 – 1.3 |
| `edge_scale` | 20 |
| `n_target` | 25 |
| `variance_penalty` | 1.0 |
| `alpha (specificity)` | 1.5 |
| `w_total min` | 0.02 |

---

### 5. PM Pattern Strength Plan

**Changes**

1. **Override storage**: add `stats` block, `type="pm_strength"`, `capital_levers` same as current.
2. **Runtime combiner** (`apply_pattern_strength_overrides`):
   - Instead of “pick most specific”, gather all matching overrides.
   - Compute `w_total` per override.
   - For each lever:
     - Use log-space blending with max ±0.02 movement per application.
     - Clamps: `size_mult ∈ [0.7, 1.3]`, `entry_aggression_mult ∈ [0.8, 1.2]`, `exit_aggression_mult ∈ [0.8, 1.2]`.
3. **Telemetry**: log the contributing overrides and weights each time we adjust an action. Store realized R/R for audit.

**Exact per-call movement**

| Lever | Base | Max step per combiner call | Bounds |
|-------|------|---------------------------|--------|
| `size_mult` | 1.0 | ±0.02 in multiplier space (i.e. log delta ≤ log(1.02)) | [0.7, 1.3] |
| `entry_aggression_mult` | 1.0 | ±0.02 | [0.8, 1.2] |
| `exit_aggression_mult` | 1.0 | ±0.02 | [0.8, 1.2] |

These match the existing lesson-level bounds, but now movement is caused by **aggregate edge** rather than a single override.

---

### 6. PM Tuning – Current State & Gaps

| Lever | Current input | Issue |
|-------|---------------|-------|
| `entry_delay_bars` | `cf_entry_improvement_bucket` (`none/small/medium/large`) | No signal context; bucket is just “missed R/R ≥ threshold”. |
| `phase1_frac_mult` | Same bucket | Same limitation; no knowledge of state/signal. |
| `trim_delay_mult` | `cf_exit_improvement_bucket` | Same. |
| `trail_mult` | `edge_raw` sign only | No tie to drawdown profile. |
| `signal_thresholds` (`min_ts_for_add`, `min_ox_for_trim`) | Hard-coded (0.55, 0.40) when `edge_raw > 0.3` | No pattern-specific values, no DX/EDX support. |
| All other levers in lever map (`min_dx_for_add`, `max_edx_for_add`, `panic_trigger_mult`, `wait_n_bars_after_trim`, `phase_scaling`, etc.) | **Not emitted at all.** | Need per-lever counterfactual stats. |

**Next steps for tuning (separate doc later)**

1. Expand counterfactual logging to include per-lever deltas (enter earlier/later by N bars, trim thresholds, trail behaviors).
2. Map each delta to the corresponding tuning lever with exact formulas (e.g. if `CF_trim_at_OX_0.5` beats actual by +0.4R consistently, set `min_ox_for_trim_target = 0.5`).
3. Extend lesson builder to output those targets with weights, then run them through the same edge-weighted combiner (separate channel).

For now, document in code/spec that tuning levers are limited to the five live ones and identified gaps are pending counterfactual detail.

---

### 7. Implementation Checklist

1. **Schema updates**
   - `learning_lessons`: add `type`, `stats` JSONB block.
   - `learning_configs`: add `alloc_overrides`, `override_stats`.
2. **Lesson builder**
   - Emit `type` per module.
   - Populate `stats` in lesson payload (edge_raw, n, variance, half_life_days).
3. **Override materializer**
   - Carry `stats`.
   - Separate DM vs PM sections.
4. **Runtime**
   - DM: edge-weighted combiner for allocation.
   - PM strength: new combiner described above.
   - PM tuning: no change yet (document current behavior + future plan).
5. **Telemetry**
   - Log override contributions and resulting levers for traceability.

---

### 8. Notes / Open Questions

1. **Counterfactual depth**: need dedicated work to expand beyond `could_enter/exit_better`.
2. **DM pattern_key coverage**: confirm DM action logs include the same v5 fields (they should, but verify).
3. **Feature flags**: keep ability to enable new combiners per module for phased rollout.

---

This plan keeps DM + PM strength outcome-first with explicit edge weighting, while acknowledging that PM tuning still needs deeper counterfactual signals before we can give it the same treatment.

