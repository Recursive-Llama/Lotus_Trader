# Archived Draft

The active learning architecture now lives in **`PM_Learning_System.md`**.  
This file is only a pointer to the historical lever-map draft (kept under `outdated_tuning/PM_Learning_Lever_Map_2024.md`).
# PM Learning Lever Map

**Status**: Draft – alignment doc for how learning outputs drive PM controls.  
**Purpose**: Keep the learning→control loop simple and explicit. Everything the learning system emits should map to (1) capital allocation levers or (2) execution tuning levers. Decision Maker lessons use the same pattern-strength concept but only need an `alloc_multiplier`.

---

## 1. Pattern Strength → Capital Allocation

**Signal**: `edge_raw` (average R/R vs segment baseline, coherence, support, time efficiency, regime multipliers). Stored per braid/lesson.

**Goal**: Increase capital where repeatable edge is proven; reduce where it is not.  
**DM variant**: If a lesson lives entirely in DM dimension space (curator/chain/mcap/intent/etc.), we emit `effect.alloc_multiplier` (bounded 0.7–1.3) and apply it at the end of the DM coefficient pipeline.

**Authorized levers (per `(pattern_key, action_category, scope subset)`):**

| Lever | Config Slot (target) | Bounds | Notes |
|-------|----------------------|--------|-------|
| `size_mult` | `pattern_strength_overrides[].levers.size_mult` | 0.5 – 1.5 | Scales final position size fraction |
| `entry_aggression_mult` | `pattern_strength_overrides[].levers.entry_aggression_mult` | 0.7 – 1.3 | Biases add appetite / mode selection (entry/add categories only) |
| `exit_aggression_mult` | `pattern_strength_overrides[].levers.exit_aggression_mult` | 0.7 – 1.3 | Biases exit assertiveness / trims (trim/exit categories only) |

**Update rule (conceptual)**:
```
mult_new = clamp(
  mult_old * (1 + k * sign(edge_raw) * f(|edge_raw|, confidence)),
  min,
  max
)
```
*Small, slow nudges; edge_raw already bakes in ΔR/R, coherence, support, and time weighting. Values decay back toward 1.0 when no fresh evidence arrives.*

---

## 2. Pattern Execution → Tuning Levers

**Signal**: Counterfactual R/R deltas (`could_enter_better`, `could_exit_better`, action sequence analysis) plus outcome stats (hold time, drawdown, time efficiency).

**Goal**: Trade the proven pattern more effectively: better timing, scaling, trims, trails, panic management.

### 2.1 Lever Inventory

| Lever | Effect | Config Target |
|-------|--------|---------------|
| `entry_delay_bars` | Wait N bars before first/next add | `pattern_overrides[].levers.entry_delay_bars` |
| `phase1_frac_mult` | Scale first allocation fraction | `pattern_overrides[].levers.phase1_frac_mult` |
| `phase_scaling.S{1,2,3}_mult` | Bias adds per Uptrend state | `pattern_overrides[].levers.phase_scaling` |
| `wait_for_signal_x` | Require stronger TS/OX/etc before acting | `pattern_overrides[].levers.signal_thresholds` |
| `min_ts_for_add` | Raise/lower TS threshold before adding | same block |
| `min_dx_for_add` | Raise/lower DX threshold before adding | same block |
| `trim_delay_mult` | Shift trim timing windows | `pattern_overrides[].levers.trim_delay_mult` |
| `min_ox_for_trim` | Raise/lower trim trigger strength | same block |
| `max_edx_for_add` | Cap adds when EDX signals exhaustion | same block |
| `trail_mult` | Tighten/loosen trailing stop | `pattern_overrides[].levers.trail_mult` |
| `panic_trigger_mult` | Adjust emergency-exit sensitivity | same block |
| `wait_n_bars_after_trim` | Sequence control (trim→rebuy delay) | same block |
| `lesson_strength / decay_halflife / enabled` | Ensure slow, auditable adjustments | `pattern_overrides[].lesson` |

All values are stored per `(pattern_key, action_category, scope subset)` with explicit min/max bounds. That keeps entry/add lessons separated from trim/exit lessons while still sharing the same behaviour key.

### 2.2 Storage Shape (proposed)

```jsonc
"pattern_overrides": [
  {
    "pattern_key": "pm.uptrend.S1.buy_flag",
    "action_category": "entry",
    "scope": {"regime": "recover|dip|micro_leads", "bucket": "micro", "A_mode": "normal"},
    "levers": {
      "entry_delay_bars": 1,
      "phase1_frac_mult": 0.85,
      "phase_scaling": {"S1": 0.9, "S2": 1.05, "S3": 1.1},
      "trim_delay_mult": 1.1,
      "trail_mult": 0.95,
      "panic_trigger_mult": 1.05
    },
    "lesson": {
      "id": "ls_12345",
      "strength": 0.32,
      "decay_halflife_hours": 720,
      "enabled": true
    }
  }
]
```

---

## 3. Lessons Today vs Target

| Area | Current State | Gap |
|------|---------------|-----|
| Lesson effect payload | Only `size_multiplier` (PM) / `alloc_multiplier` (DM) | Need structured lever map (size/A/E for strength, tuning levers for execution) |
| Config bridge | Lessons stored in Supabase, but no hot path into `pm_config` | Introduce `pattern_strength_overrides` + `pattern_overrides` sections, hot-reload |
| Runtime hook | `apply_lessons_to_action_size` multiplies size only | Need `apply_pattern_overrides(action, context)` middleware before entries/adds/trims/trails; PM stays dumb, learning stays smart |
| Feedback loop | Lesson stats tracked (edge_raw, n) but no decay/QA | Add per-lever strength, decay, and monitoring hooks |

---

## 4. Next Steps

1. **Config schema**  
   - Add `pattern_strength_overrides` and `pattern_overrides` blocks to `pm_config` (or Supabase `learning_configs` entry).  
   - Define bounds + defaults per lever.

2. **Lesson writer**  
   - When a lesson graduates, map `edge_raw` → capital levers; map counterfactual signals → tuning levers.  
   - Store lever values + metadata (strength, decay).

3. **Runtime integration**  
   - Entry/add/trim/tail logic calls `apply_pattern_overrides(action, context, action_category)` before executing.  
   - Add feature flags (`learning_overrides_enabled`, `learning_overrides_enabled_regimes`) for gradual rollout.  
   - Ensure safety clamps and telemetry on every override usage.

4. **Monitoring**  
   - Track performance of each lever override (ΔR/R vs baseline).  
   - Decay or disable overrides that stop adding value.

---

## 5. How v5 Meta-Learning Feeds the Lever System

The v4/v5 roadmap provides the inputs that drive this lever map:

| v5 Phase | What it learns | How it feeds the lever rule |
|----------|----------------|-----------------------------|
| **v5.1 Meta-factor weights** | Regime-specific weights for time efficiency, field coherence, recurrence, variance | Produces `edge_raw_regime` + confidence per action_category; lever updates use this instead of static weights so nudges reflect the current regime |
| **v5.2 Alpha half-life** | Decay rate / half-life of each pattern’s edge | Drives `decay_halflife` in overrides and modulates `f(|edge_raw|, confidence)`—patterns that keep working earn stronger nudges and decay slower |
| **v5.3 Orthogonalization** | De-duplicates overlapping patterns into latent factors | Ensures each `pattern_key` represents unique edge, preventing double-counted lever updates |

Implementation plan:

1. Finish lever plumbing (sections 1–4 above) keyed by `(pattern_key, action_category, scope subset)`.  
2. Build v5.1 so `edge_raw` is regime-aware before the first overrides go live.  
3. Layer v5.2 to power the decay/strength metadata in `pattern_overrides`.  
4. Layer v5.3 once enough history exists, keeping pattern keys clean and auditable.

That sequence gives us a closed loop: v5 keeps improving the quality of `edge_raw`, and the lever map translates that edge into bounded PM/DM behaviour changes.

This keeps the control system minimal: the learning layer only ever adjusts these explicit levers, and PM behavior changes are auditable, bounded, and directly tied to measured edge.

