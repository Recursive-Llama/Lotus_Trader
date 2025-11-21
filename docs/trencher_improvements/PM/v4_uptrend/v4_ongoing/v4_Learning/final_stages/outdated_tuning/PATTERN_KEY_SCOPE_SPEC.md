# Pattern Key, Scope & Controls Spec

**Status**: Draft – canonical definition for how PM/DM decisions, learning, and overrides refer to the same patterns.  
**Purpose**: Ensure raw action logs, learning aggregates, lessons, and runtime overrides all share one consistent schema.

---

## 1. Conceptual Layers

| Layer | Grain | Purpose | Stored Where |
|-------|-------|---------|--------------|
| **Action Events** | Per PM/DM action (`entry_immediate`, `E1`, `trim`, `panic_exit`, etc.) | Raw history for counterfactuals, execution tuning, and rebuilding aggregates | `completed_trades`/`action_sequence` |
| **Pattern Scope Stats** | `(pattern_key + scope subset)` | Aggregated edge stats (n, avg_rr, variance, edge_raw) used by braids/lessons | `pattern_scope_stats` (new) |
| **Lessons / Overrides** | Selected `(pattern_key + scope subset)` plus lever effects | What the learning system wants PM/DM to change | `learning_lessons`, `pm_config.pattern_*_overrides`, `dm_alloc_overrides` |
| **Runtime Hooks** | Current action context | Apply overrides before executing | PM/DM code (`apply_pattern_*_overrides`) |

---

## 2. Pattern Key

Represents the core **shape** of the behaviour, independent of environment or signals.

- **Canonical form**: `<family>.<state>.<motif>`
  - `family`: `uptrend`, `range`, `breakout`, `mean_revert`, etc.
  - `state`: `S0`…`S5` (Uptrend Engine state), `R1`… etc. (per module)
  - `motif`: `buy_flag`, `exhaustion`, `support_ret`, `panic_exit`, etc.
- **Module prefix**: stored as `module=<pm|dm>|pattern_key=...` when persisted (`generate_pattern_keys` already adds `module=...`).
- **Action-type** is **not** baked into the key; instead we store an `action_category` field (`entry`, `add`, `trim`, `exit`) alongside the scope so edge can be computed per `(pattern_key, action_category)` without fragmenting the behaviour identity.

Example:
```
module=pm|pattern_key=uptrend.S1.buy_flag
action_type=entry_immediate
```

---

## 3. Scope (Context)

Captures **where** the pattern was traded and **how** we configured A/E for that action. Scope dimensions are small in number (6 currently) but can be evaluated in combinations.

| Dim | Description | Example |
|-----|-------------|---------|
| `macro_phase` | Portfolio macro phase (`phase_state` macro stream) | `Good`, `Recover`, `Dip`, `Double-Dip`, `Oh-Shit`, `Euphoria`, `Chop`, `Unknown` |
| `meso_phase` | Portfolio meso phase | same list as macro |
| `micro_phase` | Portfolio micro phase | same list as macro |
| `bucket_leader` | Current top-ranked cap bucket from `bucket_rank[0]` | `micro`, `nano`, `mid`, ... |
| `bucket_rank_position` | Token’s bucket rank (1=leader) from `_get_regime_context().bucket_rank` | `1`, `2`, `3`, ... |
| `market_family` | Asset universe cluster | `lowcaps`, `perps`, `majors` |
| `bucket` | Absolute cap bucket from `token_cap_bucket` | `nano`, `micro`, `mid`, `big`, `large` |
| `timeframe` | Engine resolution | `1m`, `15m`, `1h`, `4h` |
| `A_mode` | Applied add-mode after overrides (`mode_sizes`) | `patient`, `normal`, `aggressive` |
| `E_mode` | Applied exit-mode after overrides (`mode_sizes`) | `patient`, `normal`, `aggressive` |
| `action_category` | Action class used for stats separation | `entry`, `add`, `trim`, `exit` |

- Scope (plus `action_category`) is stored as a JSON object on every action after the final plan is determined. We log `macro_phase`, `meso_phase`, `micro_phase`, `bucket_leader`, and `bucket_rank_position` as separate keys (phase vocab `{Good, Recover, Dip, Double-Dip, Oh-Shit, Euphoria, Chop, Unknown}`; rank vocab `1`–`6` or `Unknown`) and still derive the composite label `macro=<phase>|...|bucket_leader=<bucket>` for telemetry/LLM prompts. `bucket` references the latest `token_cap_bucket` assignment; `bucket_rank_position` lets lessons capture “top bucket vs laggard” behaviour without parsing strings.
- **Learning** can evaluate any subset of these dims (k=1…9). We enforce `n >= N_min` per subset to avoid overfitting.
- `action_category` is always included as a required grouping dimension in `pattern_scope_stats`; stats are computed per `(pattern_key, action_category, scope_subset)` so entry/add/trim/exit edges never bleed together.
- **Lessons/overrides** store the **chosen scope subset** that met edge/variance thresholds (e.g., `dims=["macro_phase","bucket","A_mode"]`) and always include `action_category`.
- **Runtime** matches overrides by finding the most specific subset whose values match the current action’s scope **and** the same `action_category`.
- Because the job only persists subset masks with sufficient support, splitting macro/meso/micro does **not** explode storage. Sparse combinations (e.g., `macro=Oh-Shit|meso=Recover|micro=Good|bucket=micro|A_mode=aggressive`) simply fail the `n` gate and are ignored, while common signatures (like `macro=Recover` alone) remain clean and discoverable.

---

## 4. Controls (Signals & Tunables)

Controls describe the **signals** and the **final execution knobs actually applied** when the action fired. They are the knobs the tuning layer learns to adjust and must reflect override-adjusted values.

| Category | Fields (examples) |
|----------|-------------------|
| Engine signals | `TS`, `OX`, `DX`, `EDX`, `volatility_bucket` |
| Entry sequencing | `entry_delay_bars`, `phase1_frac`, `phase_scaling` *(after overrides)* |
| Trim/exit timing | `trim_delay`, `wait_n_bars_after_trim`, `panic_trigger_level`, `trail_speed` *(after overrides)* |
| Signal thresholds | `min_ts_for_add`, `min_dx_for_add`, `max_edx_for_add`, `min_ox_for_trim`, `wait_for_signal_x` |

Controls live entirely in the action log and in the override/lesson payloads; they are **not** part of the pattern key or scope.

---

## 5. Data Flow

1. **Decision time (PM/DM)**  
   - Build `pattern_key` (family/state/motif).  
   - Capture `action_type`, `scope`, `controls`, base plan (size/A/E, timing).  
   - Apply any active overrides (Section 6) before executing.  
   - Log action with the final plan plus pattern/scope/controls.

2. **Action log → pattern scope stats**  
   - Learning job ingests action events per `(pattern_key, action_category)`.  
   - For each subset mask of the scope dims (now including `macro_phase`, `meso_phase`, `micro_phase`, `bucket_leader`) group events, compute `n`, `avg_rr`, `variance`, `edge_raw`.  
   - Upsert into `pattern_scope_stats(pattern_key, action_category, scope_mask, scope_values, stats)` (or compute on the fly if we keep it in-memory).  
   - Only trust rows with `n >= N_min` (configurable per subset size).

3. **Braids & lessons**  
   - Consume `pattern_scope_stats`, pick the **simplest** scope subset with sufficient edge/coherence/time efficiency.  
   - Emit lessons referencing `(pattern_key, scope_dims, scope_values)`.  
   - Attach capital levers (size/A/E) and tuning levers (controls) per `PM_Learning_Lever_Map`.

4. **Override materialization**  
   - Periodic job writes active lessons into `pm_config.pattern_strength_overrides` / `pattern_overrides` (and DM `alloc_multiplier_overrides`).  
   - Store `pattern_key`, `scope_signature`, lever values, lesson metadata, decay, feature flags.

5. **Runtime application**  
   - PM/DM call `apply_pattern_strength_overrides(pattern_key, scope, base_levers)` for capital multipliers.  
   - Before each action, call `apply_pattern_execution_overrides(pattern_key, scope, plan)` to adjust controls (entry delays, signal thresholds, etc.).  
   - Overrides match by selecting the most specific scope signature that is a subset of the current scope. Feature flags gate activation per regime/bucket.

---

## 6. Override Matching Algorithm (Runtime)

Given current action context `(pattern_key, scope)`:

1. Retrieve all overrides with matching `pattern_key`.  
2. For each override, check if its `scope_signature` (subset of dims) matches the current scope values.  
3. Sort matches by:
   1. Number of dimensions (more specific first).  
   2. Recency / lesson strength (optional).  
4. Apply the first match’s lever multipliers (capital or tuning), clamping to configured bounds.  
5. Telemetry: log pattern_key, scope_signature, lever changes, and feature flag state.

---

## 7. Control vs Scope Summary

| Type | Stored In | Used For | Examples |
|------|-----------|----------|----------|
| **Pattern key** | `pattern_key` field | Identity (braids, lessons, overrides) | `uptrend.S1.buy_flag` |
| **Scope** | JSON (`scope`) + `action_category` | Pattern strength learning, override applicability | `regime=trend_good`, `bucket=micro`, `A_mode=aggressive`, `action_category=entry` |
| **Controls** | JSON (`controls`), override levers | Execution tuning, counterfactual adjustments | `min_ts_for_add`, `entry_delay_bars`, `trail_mult` |

---

## 8. Open Items

- Schema for `pattern_scope_stats` (bitmask vs JSON dims) including `action_category`.  
- Minimum sample thresholds per subset size (k=1…9).  
- Feature flag strategy for enabling overrides per regime/bucket and category.  
- DM-specific scope dims (intent, curator tier, etc.) – follow same structure.  
- Telemetry dashboards tying overrides to observed ΔR/R and decay.

Once this spec is locked, we can wire the logging → learning → override → runtime loop without guessing or duplicating pattern definitions.

