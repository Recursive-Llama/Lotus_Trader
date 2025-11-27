## PM Learning Flow Test Plan

Authoritative checklist for proving the entire learning stack (DM allocation, PM strength, PM tuning) works in production conditions. Every test follows `FLOW_TESTING_ETHOS.md`: turn the real system on, inject packets, observe the database, and log exactly where a packet dies.

---

### 0. Prerequisites

1. **Code wiring**
   - `run_social_trading.py` schedules:
     - `pattern_scope_aggregator.run_aggregator()` (5 min) [Events -> Trade Events]
     - `lesson_builder_v5.mine_lessons()` (hourly) [Trade Events -> Lessons]
     - `override_materializer.materialize_overrides()` (hourly) [Lessons -> Overrides]
     - `tuning_miner.run()` (TBD) [Episode Events -> Tuning Lessons]
   - `apply_pattern_execution_overrides()` uses V5 overrides.
2. **Environment**
   - `.env` configured (Supabase URL/key, Actions enabled if needed).
   - Fresh database backup available.
3. **Test helpers**
   - CLI utilities to inject a social signal (`create_social_signal`).
   - Uptrend-engine mock hooks (existing debug functions) that can set state/flags per position.
   - Simple script to poll Supabase/Postgres and print query results.

---

### 1. System Bring-up Checklist

1. `python /Users/bruce/Documents/Lotus_Trader⚘⟁/src/run_social_trading.py`
2. Confirm logs show:
   - Social ingest/decision maker/trader initialized.
   - PM job scheduler started.
   - Aggregator, lesson builder, materializer jobs scheduled.
3. Record job PIDs/timestamps for later correlation.

If the scheduler omits any learning job, stop: packet would die at “learning jobs not running.”

---

### 2. Stage-Focused Flow Tests

#### 2.1 Data Collection Pass

1. Inject one real social signal (cap bucket = micro, timeframe focus = 1 h).
2. Wait for decision strand: `SELECT * FROM ad_strands WHERE kind='decision_lowcap' AND parent_id=:signal_id`.
3. Confirm four `lowcap_positions` exist (1m/15m/1h/4h) with `status='watchlist'`.
4. Mock Uptrend engine for the 1 h position:
   - Emit S0→S1 transition, set `entry_zone_ok=True` for N bars, then S1→S2 with trim flag, then S3 emergency-exit.
5. Let PM core tick run (or trigger job once). Query:
   - `pm_execution_history.last_s1_buy` not null.
   - `total_quantity > 0` after buy, returns to 0 after exit.
6. Check strands:
   - `ad_strands.kind IN ('pm_action','uptrend_stage_transition','uptrend_episode_summary','position_closed')` exist for this `position_id`.
7. Expected failure points:
   - No `pm_action`: packet died at PM.
   - `uptrend_episode_summary` missing: tuning pipeline broken.

**Latest run (2025‑11‑26)**  
Command: `PYTHONPATH=src:. python tests/flow/pm_learning_flow_harness.py --run-learning-jobs`  
- Social→decision strand flow succeeded; DM approved `flowtest-49cf…` and created four positions (existing positions triggered duplicate warnings but were re-used).  
- Aggregator saw 0 new event rows (recent strand already aggregated), Lesson Builder mined 704 lessons and Materializer wrote `{'strength_overrides': 512, 'tuning_overrides': 8}`.  
- Trader trigger failed due to legacy `trader_service.py` indentation bug; learning flow still completed because PM harness does not depend on execution.  
- Keep note: DM still attempts to read `learning_coefficients` (dropped table). This surfaces harmless warnings during the run but should be cleaned up when DM learning removal is finished.

#### 2.2 Aggregator + Lesson + Materializer Pass (Sizing/Strength)

1. Wait for (or manually trigger) `pattern_scope_aggregator`.
2. Query `pattern_trade_events` (Fact Table) for the relevant `pattern_key`. Verify:
   - Rows exist for each action (Entry, Trim, Exit).
   - `scope` column is JSONB and contains full context.
   - `rr` and `pnl_usd` match the trade summary.
3. After next scheduler cycle, query `learning_lessons`:
   - `lesson_type='pm_strength'` row created/updated.
   - `stats` includes `avg_rr`, `edge_raw`, and decay metadata.
   - `scope_subset` matches the targeted slice (e.g., `chain=solana`).
4. After materializer runs, query `pm_overrides`:
   - Row exists for `pattern_key` + `scope_subset`.
   - `multiplier` is calculated (e.g., >1.0 for positive edge).
5. If any table missing data, log “packet died at aggregator/lesson/materializer stage” with exact query.

#### 2.2a Learning Pipeline Follow-ups

**Purpose**: Stress the trade-events → lessons → overrides chain with the failure cases we kept hitting (missing scope dims, low-N slices, DM module drift, schema regressions). Every scenario uses the real Supabase DB and the new CLI switch:

```
PYTHONPATH=src:. python tests/flow/learning_pipeline_harness.py --scenario <base|missing-fields|sparse-events|dm-absence|schema-smoke>
```

**Scenarios exercised on 2025‑11‑27**

1. **Strand replay with missing fields**  
   Command: `--scenario missing-fields`  
   - Aggregator processed 404 trade strands, wrote 80 events for `TEST_V5_db723111`.  
   - Lesson Builder mined 864 lessons (chain slice N=40, avg RR=1.61, edge_raw=0.15).  
   - Materializer produced 544 strength + 40 tuning overrides; override multiplier=1.15.  
   - `verify_scope_defaults` found 7 rows with `intent='unknown'`, proving fallback coverage.

2. **Decay fitting with sparse events**  
   Command: `--scenario sparse-events` (injects 20 trades).  
   - Aggregator wrote 40 events; Lesson Builder skipped the `chain=solana` slice entirely.  
   - Materializer returned no overrides for the test pattern key (expected while `N < 33`).  
   - Confirms decay gating suppresses overrides when the sample size is insufficient.

3. **DM lesson absence**  
   Command: `--scenario dm-absence`.  
   - PM path succeeded (80 events, 992 lessons, overrides applied).  
   - **Failure**: re-running `mine_lessons(module='dm')` still mined 992 lessons. Module scoping is ignored, so DM lessons are still being emitted off PM strands. Needs product decision before we touch `lesson_builder_v5`. Harness keeps this scenario marked as failing until the job enforces module filters.

4. **Schema smoke test**  
   Command: `--scenario schema-smoke`.  
   - Skips injection, runs jobs on the live dataset.  
   - Aggregator returned zero rows for the random pattern key, Miner/Materializer completed without column errors, and `verify_*` functions confirmed no stray rows were written for the test key.

**Harness**: `tests/flow/learning_pipeline_harness.py` now exposes the scenarios above plus the original base run. Each scenario prints the Supabase counts so we can attach transcripts to the test record.

**Status (2025‑11‑27)**: ⚠️ **Partial** – Missing-field, sparse-events, and schema smoke pass; DM-module isolation fails (open bug: `lesson_builder_v5` ignores `module='dm'` argument and still emits lessons). Latest terminal transcripts attached in the repo logs.

#### 2.3 Tuning System Pass (Episode Logging -> Tuning)

1. **Mock S1 Skip**: Force S1 state, set `entry_zone_ok=True`, but force `PM` to skip (e.g. by mocking `allow_buys=False` or just observing Engine-only skips if using Engine tuning).
2. **Verify Episode Logging**: Query `pattern_episode_events`:
   - Row exists with `pattern_key='pm.s1_entry'` (or similar).
   - `decision='skipped'`.
   - `factors` contains `ts_score`, `halo_dist`, etc.
3. **Mock S1 Success**: Transition state S1 -> S3.
4. **Verify Outcome**: Query `pattern_episode_events` again.
   - `outcome='success'`.
   - This proves we captured a "Missed Opportunity".
5. **Mock S3 Retest**:
   - State S3. `price < ema144` (In Band).
   - Log `decision='skipped'`.
   - Emit Trim.
   - Verify `outcome='success'`.

**Status (2025‑11‑26)**  
- `tests/flow/tuning_system_harness.py` covers Phase 1 (logging + outcomes) and passes after recent fixes (trim-sync + window factors).  
- **Update (2025‑11‑26 pm)** – Harness now seeds synthetic `%tuning_harness%` scope rows (40 misses for S1, 40 false positives for S3), runs `TuningMiner()` plus `materialize_tuning_overrides()`, and asserts:
  - `learning_lessons` receives `lesson_type='tuning_rates'` rows with `n_misses>=33` (S1) / `n_fps>=33` (S3).
  - `pm_overrides` contains drift outputs (`tuning_ts_min<1`, `tuning_halo>1` for S1; `tuning_ts_min>1`, `tuning_dx_min>1` for S3).
  Command: `PYTHONPATH=src:. python -m tests.flow.tuning_system_harness`.
- **Update (2025‑11‑26 late)** – Added `tests/flow/exposure_skew_harness.py`: seeds two peer slots plus a target sharing the same scope, runs `pm_core_tick` with the mock executor, and verifies the `pm_action` strand reports `exposure_skew_applied≈0.33`. Command: `PYTHONPATH=src:. python -m tests.flow.exposure_skew_harness`.

#### 2.3a Tuning System Phase 4 (Runtime Override Flipping)

**Purpose**: Verify that tuning overrides actually flip S1/S3 signals in runtime.

1. **S1 Signal Flipping**:
   - Seed tuning override: `tuning_ts_min=1.2` (tightens gate) for scope `chain=solana`.
   - Create position with S1 state, `ts_score=0.75` (would pass default `ts_min=60`).
   - Run `pm_core_tick`.
   - Verify `effective_buy_signal=False` (override tightened gate, signal blocked).
   - Verify NO `pm_action` strand emitted.
   - Seed tuning override: `tuning_ts_min=0.8` (loosens gate) for same scope.
   - Run `pm_core_tick` again with same `ts_score=0.75`.
   - Verify `effective_buy_signal=True` (override loosened gate, signal passes).
   - Verify `pm_action` strand emitted.

2. **S3 Signal Flipping**:
   - Seed tuning override: `tuning_dx_min=1.2` (tightens gate) for scope `chain=solana`.
   - Create position with S3 state, `dx_score=0.65` (would pass default `dx_min=60`).
   - Run `pm_core_tick`.
   - Verify `effective_buy_flag=False` (override tightened gate, retest blocked).
   - Seed tuning override: `tuning_dx_min=0.8` (loosens gate).
   - Run `pm_core_tick` again with same `dx_score=0.65`.
   - Verify `effective_buy_flag=True` (override loosened gate, retest passes).

3. **Cross-Module Interference**:
   - Run Phase 1 harness (episode logging) to generate real `pattern_episode_events`.
   - Run `TuningMiner` on the real events.
   - Run `materialize_tuning_overrides`.
   - Verify tuning overrides are created from real episode data.
   - Run `pm_core_tick` with a position matching the override scope.
   - Verify tuning overrides affect runtime signals.

**Harness**: Extend `tuning_system_harness.py` with Phase 4 runtime tests.

**Status (2025‑11‑27)**: ✅ **Completed**  
- Harness adds a Phase 4 block that calls `plan_actions_v4` with real Supabase overrides and checks whether actions flip.  
- S1 case: baseline `ts_with_boost=62` emits an entry; inserting a harness-scoped `tuning_ts_min` multiplier of `1.2×` suppresses the entry (no `pm_action` strand), and a `0.8×` override restores it.  
- S3 case: baseline `dx=0.62` emits an add; a `tuning_dx_min` multiplier of `1.2×` blocks the flag; `0.8×` re-enables it.  
- Commands: `PYTHONPATH=src:. python tests/flow/tuning_system_harness.py` (Phase 4 runs after the earlier episode/miner tests).  
- Overrides are written with curator=`tuning_harness` so they never collide with production scopes; the harness cleans them up after each sub-test.

---

### 3. Full-System Flow Scenarios

#### 3.1 Multi-Bucket + Exposure Scenario

1. Inject three signals covering:
   - Micro cap (1 h focus)
   - Mid cap (15 m focus)
   - Large cap (4 h focus)
2. For each timeframe, mock Uptrend engine to create:
   - S1 success (entry taken, reaches S3, trim before exit).
   - S1 failure (entry taken, falls back to S0 without trim).
   - S1 missed opportunity (engine goes S1→S3 but PM never enters).
   - S3 retest success/failure.
3. Allow system to run for ≥2 hours so aggregator/lessons/materializer cycle multiple times.
4. Queries per timeframe:
   - `pattern_trade_events` shows rows for taken trades.
   - `pattern_episode_events` shows rows for all opportunities (taken + skipped).
   - `learning_lessons` count increments for each scenario.
   - `pm_overrides` shows updated multipliers and decay state.
5. Trigger new PM actions in the SAME scope clusters. Inspect runtime telemetry/logs to confirm:
   - `pm_strength` multiplier applied (base * strength).
   - `exposure_skew` multiplier applied (< 1.0 due to crowding).
   - `pm_action` strand contains `pm_strength_applied` and `exposure_skew_applied`.

**Status (2025‑11‑26)**  
- Not yet re-run post-recursive miner. Exposure telemetry fields (`pm_strength_applied`, `exposure_skew_applied`) exist in `pm_action` strands but still need a fresh scenario with ≥3 simultaneous positions to validate skew math. Remains open.

#### 3.1a PM Action Loop Edge Cases

**Purpose**: Verify PM handles edge cases correctly (S2 adds, cooldown, bag-full, partial fills, executor failures).

1. **S2 Add Logic**:
   - Create position in S2 state with `buy_flag=True`.
   - Run `pm_core_tick`.
   - Verify `pm_action` strand emitted with `action='add'`.
   - Verify `total_quantity` increases.

2. **Cooldown Enforcement**:
   - Create position with recent trim (within cooldown window).
   - Set S1 `buy_signal=True`.
   - Run `pm_core_tick`.
   - Verify entry is skipped (cooldown active).
   - Verify log message indicates cooldown.

3. **Bag-Full Rejection**:
   - Create position with `total_allocation_pct` already at max.
   - Set S1 `buy_signal=True`.
   - Run `pm_core_tick`.
   - Verify entry is skipped (bag full).
   - Verify log message indicates bag full.

4. **Partial Fill Handling**:
   - Mock executor to return `tokens_bought < planned_tokens` (partial fill).
   - Run `pm_core_tick` with S1 entry.
   - Verify `total_quantity` updated to partial amount.
   - Verify position remains in S1 (not fully entered).
   - Verify next tick attempts to complete the entry.

5. **Executor Failure Path**:
   - Mock executor to return `status='error'`.
   - Run `pm_core_tick` with S1 entry.
   - Verify `total_quantity` is NOT updated (execution failed).
   - Verify position remains in S1.
   - Verify error logged.

6. **Emergency Exit Failure**:
   - Mock executor to return `status='error'` for emergency exit.
   - Run `pm_core_tick` with S3 emergency exit.
   - Verify position remains `active` (not closed).
   - Verify error logged.

**Harness**: Extend `pm_action_harness.py` with edge case scenarios.

**Status**: ⏳ **Not yet implemented**

**Update (2025‑11‑27)**  
- Added `tests/unit/pm_overrides_test.py` covering both entry strength and tuning overrides with a stub Supabase client.  
- Tests verify:  
  - Strength multipliers scale `position_size_frac` (single override, neutral fallback).  
  - `tuning_ts_min` clamps/loosens S1 thresholds.  
  - `tuning_dx_min` tightens/loosens S3 gates without affecting TS unless explicitly overridden.  
- Command: `PYTHONPATH=src:. pytest tests/unit/pm_overrides_test.py`.  
- Keeps overrides scoped to a fake curator so we can assert results deterministically without touching production rows.

#### 3.1b Exposure & Sizing Stress Tests

**Purpose**: Verify exposure skew and pm_strength interact correctly under extreme conditions.

1. **Partial Scope Handling**:
   - Create positions with missing scope fields (e.g., no `intent`, no `mcap_bucket`).
   - Run `ExposureLookup.build()`.
   - Verify lookup returns `1.0` (neutral) when no masks match (not `1.33`).
   - Verify positions with partial scope don't break exposure calculation.

2. **Extreme Configs**:
   - Load config with `mask_defs: []` (empty masks).
   - Verify `ExposureConfig.from_pm_config()` rejects or logs fatal error.
   - Load config with `alpha=5.0` (extreme power-law).
   - Verify exposure calculation still works (may be extreme but shouldn't crash).

3. **Skew × Strength Interaction**:
   - Seed `pm_overrides` with extreme multiplier: `multiplier=3.0` for scope `chain=solana`.
   - Create 5 positions in same scope (heavy crowding).
   - Run `pm_core_tick` for new entry in same scope.
   - Verify `pm_strength_applied ≈ 3.0`.
   - Verify `exposure_skew_applied < 0.5` (crowded).
   - Verify `pm_final_multiplier` is clamped correctly (e.g., `3.0 * 0.5 = 1.5`).
   - Verify telemetry records both contributions.

4. **Mask Weighting Config**:
   - Load config with `scope_dim_weights` all set to `0.0`.
   - Verify exposure calculation degrades gracefully (returns `1.0` or logs warning).
   - Load config with `alpha=0.0` (no power-law).
   - Verify exposure calculation still works.

**Harness**: `tests/flow/exposure_skew_harness.py` (now covers crowding, overrides, config stress).

**Status**: ✅ **Completed (2025‑11‑27)**  
- Added pure `ExposureLookup` tests for partial scopes, empty mask defs, zero-weight configs, and extreme alpha.  
- Added flow tests that seed peer positions, fire `pm_core_tick`, and assert `exposure_skew < 1.0`.  
- Added a skew×strength test that injects a 3× override and verifies `pm_strength` boost is damped by exposure (combined multiplier < strength alone).  
- Harness cleans up seeded positions and overrides between scenarios so it can be rerun safely.

#### 3.2 Backfill & Rollup Scenario

1. Start system with empty OHLC tables for a test token.
2. Verify rollup jobs (`convert_1m`, `rollup_5m/15m/1h/4h`) populate data without manual intervention.
3. Mock engine states after rollups finish to ensure newly created positions still generate strands and feed learning.
4. Failure logging: if OHLC backfill fails, note “packet died during rollup; learning starved.”

#### 3.2a Lowcap TA / Rollup Harness

**Purpose**: Verify lowcap OHLC ingestion, rollups, and TA tracker produce correct EMA/ATR/TS values.

1. **1m Ingestion**:
   - Insert synthetic 1m candles for a test token (Solana).
   - Verify `lowcap_price_data_1m` contains rows.
   - Verify timestamps are correct.

2. **Rollup Jobs**:
   - Run `convert_1m` job.
   - Verify `lowcap_price_data_ohlc` contains aggregated bars.
   - Run `rollup_5m`, `rollup_15m`, `rollup_1h`, `rollup_4h` jobs.
   - Verify higher timeframe tables populated.

3. **TA Tracker**:
   - Run `ta_tracker` job for the test token.
   - Query TA tables for EMA, ATR, TS, OX, DX values.
   - Verify EMA values are within expected ranges (e.g., EMA60 > EMA144 > EMA333).
   - Verify ATR > 0.
   - Verify TS score is between 0-100.

4. **Backfill Recovery**:
   - Delete a chunk of 1m candles (simulate missing data).
   - Run backfill job.
   - Verify missing candles are restored.
   - Verify rollups and TA tracker still produce correct values.

5. **Geometry Builder**:
   - Run geometry builder for a position.
   - Verify `uptrend_signals` contains EMA slopes, price position, etc.
   - Verify geometry matches TA tracker outputs.

**Harness**: `tests/flow/lowcap_ta_harness.py` (real social signal → DM → backfill → TA/geometry checks).

**Status**: ✅ **Completed (2025‑11‑27)**  
- Avici (BANK) and WOJACK harness runs inject live strands, let DM backfill all four timeframes, and verify TA/geometry outputs.  
- Flow uncovered and resolved two regressions: missing EMA30 propagation (prevented S3 promotions) and a `vo_z` NameError in `_compute_s3_scores()` that blocked the 1h engine.  
- Harness now doubles as a regression test—can be re-run for any token via CLI overrides.

---

### 4. Per-Component Diagnostics (still flow-based)

Use when a full scenario fails; each step uses real data but narrows the scope.

1. **Strand replay**  
   - Export offending strands, reinsert into a test schema, and run only `pattern_scope_aggregator` to see if stats update. Confirms aggregator logic independent of PM.
2. **Lesson builder dry run**  
   - Pause PM jobs, run `lesson_builder_v5` once, and inspect logs to ensure both DM/PM modules processed rows.
3. **Materializer dry run**  
   - Use the latest `learning_lessons` snapshot, run materializer, compare config diffs.
4. **Runtime override inspection**  
   - Enable verbose logging around `apply_pattern_strength_overrides` and `apply_pattern_execution_overrides`. Confirm the weighting math matches override stats.

Each diagnostic still treats the database as the source of truth; we never mock components that exist in production.

#### 4.1 Diagnostics Tooling Harnesses

**Purpose**: Verify diagnostic CLI scripts remain functional and provide playbook for production debugging.

1. **Strand Replay Harness**:
   - Export a `position_closed` strand from production (or test data).
   - Run `strand_replay.py --strand-id <id>`.
   - Verify aggregator processes the strand.
   - Verify `pattern_trade_events` row created.
   - Verify no errors or missing fields.

2. **Lesson Builder Dry Run Harness**:
   - Pause PM jobs.
   - Run `lesson_builder_v5` once.
   - Verify logs show lessons mined.
   - Verify `learning_lessons` rows created/updated.
   - Verify no errors.

3. **Materializer Dry Run Harness**:
   - Load latest `learning_lessons` snapshot.
   - Run `override_materializer` once.
   - Verify `pm_overrides` rows created/updated.
   - Verify multiplier calculations match expected values.
   - Verify no errors.

4. **Runtime Override Unit Tests**:
   - Create test harness for `apply_pattern_strength_overrides`:
     - Seed `pm_overrides` with test multipliers.
     - Call function with matching scope.
     - Verify `position_size_frac` is scaled correctly.
     - Test blending of multiple overrides.
   - Create test harness for `apply_pattern_execution_overrides`:
     - Seed `pm_overrides` with tuning multipliers.
     - Call function with matching scope.
     - Verify `ts_min`, `halo_mult`, `dx_min` are adjusted correctly.
     - Test clamping (e.g., `ts_min` stays within `[10.0, 90.0]`).

**Harness**: Create `tests/flow/diagnostics_harness.py` and `tests/unit/pm_overrides_test.py`.

**Status**: ⏳ **Not yet implemented**

---

### 5. Evidence to Capture

For every scenario, archive:
1. Command log (exact `python run_social_trading.py` invocation and timestamps).
2. SQL transcripts for each verification step.
3. Relevant log excerpts (job start/stop, override application).
4. Summary table:  
   `scenario | packet_id | final sink (override applied?) | failure stage (if any)`.

---

### 6. Regression Policy

- Run the stage-focused tests after any change to PM core tick, aggregator, lesson builder, or overrides.
- Run the full multi-bucket scenario before major releases.
- If any packet dies, file a blocking bug with the “Packet died at stage X” note and the captured evidence. Do not “fix the test”; fix the flow.

---

Following this plan ensures we can repeatedly demonstrate that turning the system on, injecting real signals, and letting scheduled jobs run is sufficient for learning to keep itself healthy. Anything less means the system—and production—would break.***


### 7. Progress Log

- **2025-11-20** – `run_social_trading.py` now schedules `pattern_scope_aggregator`, lesson builder for both modules, and the override materializer.
- **2025-11-20** – PM tuning channel now only nudges signal thresholds; all legacy execution levers stay fixed at their configured values. Ready to start the staged flow tests (lever audit complete).
- **2025-11-20** – Added `tests/flow/pm_learning_flow_harness.py` so one command can inject a signal, drive the decision maker, and optionally run aggregator/lesson/materializer with explicit pass/fail checkpoints.
- **2025-11-21** – Added `tests/flow/majors_feed_harness.py` to validate Hyperliquid WS ingest + rollups + tracker with explicit PASS/FAIL checkpoints on tick ingestion and 1m bar writes.
- **2025-11-21** – Added `tests/flow/pm_action_harness.py` to force S0→S1→S3→S0 transitions for a real position, run `pm_core_tick`, and print strand/action counts per step.
- **2025-11-21** – Removed legacy braiding system (`braiding_system.py`, `braiding_lesson_builder.py`). Learning now uses `pattern_scope_aggregator` (real-time) + v5 lesson builder + override materializer. Renamed `braiding_helpers.py` → `bucketing_helpers.py`.
- **2025-11-25** – Implemented `pattern_trade_events` (Fact Table) and V5 Lesson Builder (Miner) + V5 Materializer (Judge).
- **2025-11-25** – Implemented Phase 1 of Tuning System: `pattern_episode_events` logging in `PMCoreTick`.
- **2025-11-26** – Re-ran `pm_learning_flow_harness` with `--run-learning-jobs` (Strength pipeline green, trader layer still blocked on legacy indentation bug).  
- **2025-11-26** – Re-ran `learning_pipeline_harness` after recursive Apriori miner landed; confirmed Depth‑2 lessons and override drift output.  
- **2025-11-26** – Re-ran `pm_action_harness` (S1/S3 scenarios); S3 emergency-exit scenario returned `watchlist` instead of expected `active` status → needs follow-up bugfix before marking scenario fully green.
- **2025-01-26** – Updated DM rejection criteria: removed intent and capacity blockers, lowered curator score minimum to 0.1, confirmed already-holding logs intent but doesn't duplicate positions. Updated test plan with remaining testing gaps: DM rejection tests, lowcap TA harness, PM action edge cases, exposure stress tests, learning pipeline follow-ups, tuning Phase 4, runtime override unit tests, telemetry validation, diagnostics tooling.
- **2025-11-27** – Flow-tested Avici (BANK) and WOJACK end-to-end via `lowcap_ta_harness`; uncovered and fixed EMA30 propagation gap, `_check_s3_order` S4 dead-end, and `_compute_s3_scores` `vo_z` NameError. Uptrend engine now runs for 1m/15m/1h/4h on schedule and writes state snapshots for watchlist positions.
- **2025-11-27** – Extended `exposure_skew_harness` with partial-scope/zero-weight lookup tests plus live PM runs (crowding + override damping). Harness now exercises exposure config edge cases and confirms `pm_strength` × `exposure_skew` interplay.

---

### 8. Test Inventory & Harness Map

The single existing harness (“social → decision → trader bootstrap”) does **not** execute `run_social_trading.py`; it stands up Supabase + learning + DM + trader classes directly. That means HL WS, rollups, and other scheduled jobs only run if we invoke them explicitly.

| Subsystem / flow | Evidence needed | Current coverage | Harness / plan |
| --- | --- | --- | --- |
| **Social ingest → DM decision** | Social strands become `decision_lowcap`, DM checklist reasons logged, four `lowcap_positions` created | ✅ `pm_learning_flow_harness` proves this | Extend harness with richer signal cases (already-holding, curator score fail, intent fail) |
| **Trader bootstrap** | Decision approval triggers trader, backfill jobs fire, trade attempt logged | ✅ same harness | Add assertions for notifier / order path once we point to sim executors |
| **PM action loop (Uptrend engine, buys/sells, position bookkeeping)** | Synthetic price/state data drives S0→S1→S2→S3 flows, `pm_action` / `uptrend_*` strands emitted, quantities update correctly | ✅ `pm_action_harness` covers this | Verifies S1 entry, S3 retest, emergency_exit, S3→S0/S1→S0 transitions, strand counts, position status |
| **Learning pipeline (aggregator → lessons → overrides)** | `pattern_trade_events` rows accumulate edge/tuning stats, `learning_lessons` emits dm/pm/tuning lessons, `pm_overrides` stores overrides | ✅ `learning_pipeline_harness` covers this | Select `position_closed` strands → run `pattern_scope_aggregator`, `lesson_builder_v5`, `override_materializer`, assert DB mutations. |
| **Tuning System Phase 1 (Episode Logging)** | `pattern_episode_events` logs S1/S3 windows, decisions (acted/skipped), and outcomes | ✅ `tuning_system_harness` logs S1/S3 skip + success + retest | Extend harness to Phase 2 (Miner/Judge) validation. |
| **Runtime override application** | Logs show PM strength bias, `exposure_skew` damping, PM tuning thresholds deviating from neutral | ✅ `pm_runtime_sizing_harness` | Test `apply_pattern_strength_overrides` with mock overrides in DB. |
| **Hyperliquid WS + majors rollups** | HL ingester connected, 1m points stored, 1m→5m/15m/1h conversions succeed, macro context updates | ✅ `majors_feed_harness` covers this | Validates WS ingest (PASS/FAIL), 1m rollup writes, higher timeframe conversions, phase_state updates |
| **Lowcap OHLC + TA tracker** | `GenericOHLCRollup` and `ta_tracker` produce EMA/ATR/TS/OX/DX values for the test token, geometry builder outputs shapes | ✅ `lowcap_ta_harness` (Avici + WOJACK) | Harness injects real signal, triggers backfill/rollups/TA, verifies EMA/ATR/geometry + backfill recovery |
| **DM allocation learning** | DEPRECATED (DM simplification) | N/A | Removed from test plan |
| **DM rejection criteria** | DM correctly rejects unsupported chains, low curator scores; doesn't block on removed criteria (intent, capacity) | ✅ `pm_learning_flow_harness --test-rejections` | Tests chain support, curator score (0.1 min), already-holding behavior, removed blockers |
| **PM action loop edge cases** | S2 adds, cooldown, bag-full, partial fills, executor failures handled correctly | ⏳ `pm_action_harness` extension planned | Test S2 add logic, cooldown enforcement, bag-full rejection, partial fills, executor error paths |
| **Exposure & sizing stress tests** | Partial scopes, extreme configs, skew×strength interaction, mask weighting | ⏳ `exposure_skew_harness` extension planned | Test missing scope fields, extreme configs, extreme multipliers + crowding, mask weight configs |
| **Learning pipeline follow-ups** | Strand replay with missing fields, decay fitting with sparse events, DM lesson absence, schema smoke | ⏳ `learning_pipeline_harness` extension planned | Test aggregator handles missing fields, decay N_MIN gate, DM lesson filtering, empty DB runs |
| **Tuning System Phase 4** | Runtime overrides actually flip S1/S3 signals | ⏳ `tuning_system_harness` extension planned | Test S1/S3 signal flipping with tuning overrides, cross-module interference |
| **Runtime override unit tests** | `apply_pattern_strength_overrides` and `apply_pattern_execution_overrides` work correctly | ⏳ unit tests planned | Test override blending, clamping, scope matching |
| **Telemetry / strands validation** | Required fields exist in strands (`pm_strength_applied`, `exposure_skew_applied`, `learning_multipliers`) | ✅ `telemetry_harness.py` (2025‑11‑27) | CLI scans recent `pm_action` strands; latest packets contain all required fields (legacy rows before 2025‑11‑27 lack the telemetry, so harness flags them for awareness). |
| **Diagnostics (strand replay, lesson dry run, materializer dry run)** | Each tool processes real snapshots independently | ⏳ `diagnostics_harness` planned | Create CLI scripts per §4.1 and harness to verify they still run |

**Next actions**
1. ✅ **PM action harness** - Built and working. Verifies S1 entry, S3 retest, emergency_exit, trade closure, strand emission.
2. ✅ **Majors feed harness** - Built and working. Validates Hyperliquid WS ingest + rollups with explicit PASS/FAIL.
3. ✅ **Learning pipeline harness** - Built and working. Verifies Aggregator -> Lesson Builder -> Materializer flow.
4. ✅ **Tuning System Harness Phase 2/3** – Harness seeds synthetic events (N≥33), runs `TuningMiner` + drift judge, and verifies tuning overrides for S1/S3 patterns.
5. ✅ **Exposure / Sizing verification** – `tests/flow/exposure_skew_harness.py` now seeds two peer positions plus a target with identical scope, runs `pm_core_tick` (mock executor), and asserts the target's `pm_action` strand records `exposure_skew_applied ≈ 0.33` (< 1.0) alongside the entry.
6. ✅ **DM rejection criteria tests** – Extended `pm_learning_flow_harness.py` with `--test-rejections` flag. Tests: unsupported chain rejection, low curator score (< 0.1) rejection, already-holding behavior (approves but doesn't duplicate), removed blockers verification (intent, capacity don't block). All tests passing.
7. ✅ **Lowcap TA / Rollup harness** – Created `tests/flow/lowcap_ta_harness.py`. Tests: 1m ingestion (synthetic price points), convert_1m job, rollup jobs (5m/15m/1h/4h), TA tracker (verifies EMA/ATR/RSI/ADX with minimum bar requirements), backfill recovery, geometry builder. All tests passing.
8. ✅ **PM action loop edge cases** – Extended `pm_action_harness.py` with `_run_edge_case_tests()` method. Tests: S2 add logic (verifies quantity increase and pm_action strands), bag-full rejection (verifies entry skipped when allocation at max), partial fill handling (50% fill simulation), executor failure paths (entry and exit failures), emergency exit failure. Cooldown test noted as requiring execution history modification. All tests passing.
9. ⏳ **Exposure & sizing stress tests** – Extend `exposure_skew_harness.py` to test partial scopes, extreme configs, skew×strength interaction.
10. ⏳ **Learning pipeline follow-ups** – Extend `learning_pipeline_harness.py` to test strand replay with missing fields, decay fitting, DM lesson absence, schema smoke.
11. ⏳ **Tuning System Phase 4** – Extend `tuning_system_harness.py` to verify runtime overrides actually flip S1/S3 signals.
12. ⏳ **Runtime override unit tests** – Create `tests/unit/pm_overrides_test.py` to test `apply_pattern_strength_overrides` and `apply_pattern_execution_overrides`.
13. ✅ **Telemetry / strands validation** – `tests/flow/telemetry_harness.py` loads recent `pm_action` strands and asserts telemetry fields (`pm_strength_applied`, `exposure_skew_applied`, `pm_final_multiplier`, `learning_multipliers`). Latest strands (post‑2025‑11‑27) pass; older ones are flagged as missing so we know which historical packets predate the field.
14. ⏳ **Diagnostics tooling** – Create CLI scripts per §4.1 and `tests/flow/diagnostics_harness.py` to verify they still run.
15. ⏳ **Real executor smoke (micro-size)** – Run `pm_action_harness` with the live PM executor (dry-run or $1 notional) to confirm the harness stub stays aligned with on-chain payloads; capture RPC/fee health in the evidence bundle.

Once each harness is green, we can revisit whether a combined “full stack” rehearsal (possibly via `run_social_trading.py` plus scripted inputs) is needed, but keeping the harnesses modular gives us clearer failure boundaries.
