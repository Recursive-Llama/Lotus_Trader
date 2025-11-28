 Everything is going eating## Overview

The PM learning stack has three independent but complementary channels. Each channel observes a different slice of reality, emits its own lessons, and tunes a specific family of controls. Everything flows through the same infrastructure: strands → `pattern_scope_stats` → `lesson_builder_v5` → `learning_configs` → runtime override combiners.

1. **DM Allocation Learning** – adjusts how much capital each strategy deserves before the PM ever looks at a token.
2. **PM Pattern-Strength Learning** – biases size and A/E aggression for patterns that repeatedly outperform (or underperform) once we are in a trade.
3. **PM Tuning Learning (S1 + S3)** – adjusts the engine gates (TS/SR/halo/slope/DX/EDX) so buy/trim signals only fire in contexts that historically succeed.

The sections below summarize the data sources, lesson logic, and runtime hooks for each channel.

---

## 1. DM Allocation Learning (channel 1)

| Aspect | Details |
| --- | --- |
| **Data source** | `ad_strands.kind = 'position_closed'` + DM action strands. All trades already log `pattern_key`, `action_category="allocation"`, and full scope (curator/chain/cap/intent + regime context). |
| **Aggregation** | `pattern_scope_aggregator` groups trades by `(pattern_key, scope subset)` and stores `stats.edge_raw`, `n`, variance, time efficiency, etc. |
| **Lesson builder** | `lesson_builder_v5` (module=`dm`) emits `lesson_type='dm_alloc'` with `effect.alloc_mult`. Edge → lever scaling uses `learning_rate=0.02`, `edge_scale=20`, bounds [0.7, 1.3]. |
| **Materializer** | Writes lessons into `learning_configs.dm.config_data.alloc_overrides`, including `stats` metadata (edge, n, variance, half-life). |
| **Runtime** | Allocation pipeline loads all overrides where `scope ⊆ current_scope`, computes weights via the edge formula, and blends them multiplicatively (log space, ±0.02 step). Final `alloc_mult` multiplies the coefficient/EWMA baseline. |

Result: DM can lean into or away from strategy families before PM takes any action.

---

## 2. PM Pattern-Strength Learning (channel 2)

| Aspect | Details |
| --- | --- |
| **Data source** | Same `position_closed` strands but filtered to PM trades. Each trade stores the entry context, R/R, counterfactual buckets, and the list of `pm_action` strands (pattern key + scope). |
| **Aggregation** | `pattern_scope_aggregator` updates `pattern_scope_stats` for every scope subset, including edge history for decay tracking. |
| **Lesson builder** | `lesson_builder_v5` (module=`pm`, `lesson_type='pm_strength'`) maps `edge_raw` to capital levers:<br>• `size_mult` (0.5–1.5)<br>• `entry_aggression_mult` (0.8–1.2 for entry/add)<br>• `exit_aggression_mult` (0.8–1.2 for trim/exit)<br>Lessons carry `stats` (edge, n, variance, time_efficiency), half-life, and latent factor ids. |
| **Materializer** | Lessons land in `learning_configs.pm.config_data.pattern_strength_overrides`. Each override stores `levers`, `stats`, and lesson metadata (strength, decay). |
| **Runtime** | `apply_pattern_strength_overrides()` now gathers **all** matching overrides, weights them (edge/n/variance/half-life/scope), blends the multipliers with ±0.02 per call, and clamps to safety bounds. No more “most specific wins.” |

Result: position size/A/E bias evolves smoothly with edge evidence, while conflicting lessons cancel proportionally to their confidence.

---

## 3. PM Tuning Learning (channel 3 – S1/S3 episodes)

| Aspect | Details |
| --- | --- |
| **Stage logging** | `pm_core_tick` tracks `S0→S1` and `S2→S3` transitions. When state enters S1 or S3, it opens an `episode_id`, records every bar where the engine’s **buy signal** (S1) or **DX buy flag** (S3) stays true, and captures capped samples (TS, SR boost, slopes, halo, DX, EDX, price-band position). Episodes close when we reach S3 (success) or fall back to S0 (failure/correct skip). Each episode emits an `uptrend_episode_summary` strand with windows, outcome, and `levers_considered` (delta, severity, confidence for each gate). |
| **Aggregation** | `pattern_scope_aggregator` ingests these episode summaries and stores tuning stats under `pattern_scope_stats.stats['tuning']`, broken out by `episode_type='s1_entry'` or `s3_retest`. We track outcome counts plus severity/confidence totals per lever. |
| **Lesson builder** | When `lesson_builder_v5` creates or updates a PM strength lesson, it now looks at `stats['tuning']` and, if there’s enough evidence, emits a companion `lesson_type='pm_tuning'` with entries such as:<br>• `signal_thresholds.ts_min`<br>• `signal_thresholds.sr_boost`<br>• `signal_thresholds.dx_min` / `edx_supp_mult`<br>• (future) slope/halo adjustments.<br>These payloads include the same `stats` metadata and decay settings as strength lessons. |
| **Runtime** | `apply_pattern_execution_overrides()` mirrors the capital combiner. It loads all tuning overrides, weights them, and nudges each lever a tiny step toward its target (±0.05 for thresholds, ±0.02 for multipliers, ±1 bar for delays). Signal thresholds live in `plan_controls['signal_thresholds']`, so raising TS/DX gates literally changes when the engine’s `buy_signal/buy_flag` fires. |

For full episode details see `S1_S3_Tuning_Episode_Spec.md`. First-dip buys still log through the S3 path and can become their own episode type later if needed.

---

## 4. Data Flow Summary

```
Uptrend / PM strands  ─┐
                       │
position_closed strands│         ┌─────────────┐         ┌──────────────┐
                       ├─> pattern_scope_stats ├─> lesson_builder_v5 ──> learning_configs
episode_summary strands│         └─────────────┘         └──────────────┘
                       │                                  │
                       │                                  └─ DM alloc overrides
                       │
                       └───────────────────────────────────── PM strength overrides
                                                             PM tuning overrides
```

- **Strand layer** supplies both trade outcomes (channel 1 & 2) and stage episodes (channel 3).
- **Aggregator** updates shared stats (`edge_raw`, variance, n, time efficiency) plus the tuning block.
- **Lesson builder** emits three lesson types (`dm_alloc`, `pm_strength`, `pm_tuning`) using the same decay/half-life machinery.
- **Materializer** writes overrides into `learning_configs` for hot reload.
- **Runtime** (DM allocation + PM overrides) combines all matches edge-weighted, guaranteeing smooth, auditable adjustments.

This single doc is now the canonical description of the learning system. The detailed S1/S3 episode spec and pattern-key/scope spec remain referenced appendices, while older tuning drafts have been archived under `final_stages/outdated_tuning/`.

---

## 5. Immediate Wiring Tasks

1. **Launch every learning job inside `run_social_trading.py`**  
   `start_pm_jobs()` must schedule three more loops so “run the system” == “learning is live”:  
   - `pattern_scope_aggregator.run_aggregator()` (5 min cadence)  
   - `lesson_builder_v5.build_lessons_from_pattern_scope_stats()` for both `module='dm'` and `module='pm'` (hourly)  
   - `override_materializer.run()` (hourly)  
   No CLI stand-ins or manual invocations in tests—if the scheduler isn’t running it, the system is broken.

2. **Clamp unused tuning levers to neutral**  
   We only tune signal gates right now (TS, SR, halo, slope guards for S1; DX, EDX suppression, SR boost, slopes for S3). `lesson_builder_v5` must emit nothing else, and `apply_pattern_execution_overrides()` should hardcode legacy knobs (`entry_delay_bars`, `phase1_frac_mult`, `trim_delay_mult`, `trail_mult`, `panic_trigger`, `wait_n_after_trim`) to their neutral defaults until we design new signals for them. That prevents drift from stale lessons while keeping the code paths intact.

3. **Verify DM labeling end-to-end**  
   - `pattern_keys_v5.generate_canonical_pattern_key()` already tags module/action. Double-check DM strands populate `module='dm'` in `pattern_scope_stats`.  
   - Ensure `lesson_builder_v5` emits `lesson_type='dm_alloc'` only for `module='dm'` rows, and PM lessons never leak DM dimensions.  
   - Confirm materializer writes DM overrides into `learning_configs.dm` and runtime allocation loader actually reads them.

---

## 6. Flow Testing Plan (Flow Ethos Applied)

We stay true to `FLOW_TESTING_ETHOS.md`: turn the real system on, inject packets, query the DB, observe where they die. We just scope scenarios so debugging stays surgical.

### 6.1 Stage-Focused Flow Tests
- **Data-collection pass**:  
  1. Start the full system.  
  2. Inject one social signal (real curator + token).  
  3. Mock Uptrend engine signals so the 1 h position goes through S0→S1→S3 → trims → exit.  
  4. Verify strands exist for `pm_action`, `uptrend_buy_window`, `uptrend_episode_summary`, `position_closed`.  
  If anything is missing, the failure is in PM/engine wiring.
- **Aggregator+lesson+materializer pass** (still with system running):  
  1. After strands exist, watch the scheduler fire `pattern_scope_aggregator`.  
  2. Query `pattern_scope_stats` to confirm `edge_raw` and `stats['tuning']` updated for each scope subset.  
  3. When the lesson-builder job runs, confirm new rows in `learning_lessons` for `dm_alloc`, `pm_strength`, and `pm_tuning`.  
  4. After materializer executes, confirm `learning_configs` contains fresh overrides.  
  This isolates learning infrastructure without stopping the system or mocking databases.

### 6.2 Full-System Flow Test
1. Start `run_social_trading.py` (all schedulers enabled).  
2. Inject multiple signals spanning cap buckets and timeframes so all four positions per token become active.  
3. Mock Uptrend engine per timeframe to produce: S1 successes, S1 failures, missed S1 entries, S3 retest successes/failures.  
4. Let the system run long enough for aggregator → lessons → materializer to cycle.  
5. Trigger another set of PM actions and verify runtime logs show tuning overrides adjusting the TS/DX gates.  
6. Document every drop-off point as “packet died at stage X,” never “test failed.”

### 6.3 Why Layered Flow Tests
- Keeps every component real (no unit harnesses), but narrows investigation when something fails.  
- Mirrors production deploy: if the per-stage flow test fails, prod would fail too.  
- Scaling up to the multi-scenario test guarantees cross-bucket/timeframe behaviour, not just a single happy path.

Deliverables from the flow campaign:
- Query transcripts showing each job’s outputs.  
- A checklist per scenario so we can rerun whenever we touch learning code.  
- Logged evidence that runtime thresholds actually shift after lessons materialize.

Once these steps pass, we can be confident “turn the system on → learning works” is literally true.

