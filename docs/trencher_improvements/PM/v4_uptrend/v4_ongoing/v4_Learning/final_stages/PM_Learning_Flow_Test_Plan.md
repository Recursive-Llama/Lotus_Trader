## PM Learning Flow Test Plan

Authoritative checklist for proving the entire learning stack (DM allocation, PM strength, PM tuning) works in production conditions. Every test follows `FLOW_TESTING_ETHOS.md`: turn the real system on, inject packets, observe the database, and log exactly where a packet dies.

---

### 0. Prerequisites

1. **Code wiring**
   - `run_social_trading.py` schedules:
     - `pattern_scope_aggregator.run_aggregator()` (5 min)
     - `lesson_builder_v5.build_lessons_from_pattern_scope_stats()` for `module='dm'` and `module='pm'` (hourly)
     - `override_materializer.run()` (hourly)
   - `apply_pattern_execution_overrides()` clamps legacy levers to neutral.
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
   - Emit S0→S1 transition, set `buy_signal=True` for N bars, then S1→S2 with trim flag, then S3 emergency-exit.
5. Let PM core tick run (or trigger job once). Query:
   - `pm_execution_history.last_s1_buy` not null.
   - `total_quantity > 0` after buy, returns to 0 after exit.
6. Check strands:
   - `ad_strands.kind IN ('pm_action','uptrend_stage_transition','uptrend_buy_window','uptrend_episode_summary','position_closed')` exist for this `position_id`.
7. Expected failure points:
   - No `pm_action`: packet died at PM.
   - `uptrend_episode_summary` missing: tuning pipeline broken.

#### 2.2 Aggregator + Lesson + Materializer Pass

1. Wait for (or manually trigger) `pattern_scope_aggregator`.
2. Query `pattern_scope_stats` for the relevant `pattern_key` and scope subsets. Verify:
   - `stats.edge_raw` updated (DM & PM channels).
   - `stats.tuning` contains counts for `s1_entry` / `s3_retest`.
3. After next scheduler cycle, query `learning_lessons`:
   - `lesson_type='dm_alloc'` row appended.
   - `lesson_type='pm_strength'` row appended.
   - `lesson_type='pm_tuning'` row appended with only signal-threshold levers.
4. After materializer runs, query `learning_configs`:
   - `config_data.alloc_overrides` contains new DM override with stats metadata.
   - `config_data.pattern_strength_overrides` updated.
   - `config_data.pattern_tuning_overrides` updated.
5. If any table missing data, log “packet died at aggregator/lesson/materializer stage” with exact query.

---

### 3. Full-System Flow Scenarios

#### 3.1 Multi-Bucket Scenario

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
   - `pattern_scope_stats` shows separate rows per scope subset (macro phase, cap bucket, timeframe).
   - `learning_lessons` count increments for each scenario.
   - `learning_configs` overrides show decay metadata updating (`age_hours`).
5. Trigger new PM actions after overrides exist; inspect runtime telemetry/logs to confirm:
   - DM allocation multipliers applied (log shows alloc_mult ≠ 1.0).
   - PM strength multipliers applied (A/E biases).
   - PM tuning thresholds shifted (TS/DX gates different from neutral). Use `plan_controls` debug output.

#### 3.2 Backfill & Rollup Scenario

1. Start system with empty OHLC tables for a test token.
2. Verify rollup jobs (`convert_1m`, `rollup_5m/15m/1h/4h`) populate data without manual intervention.
3. Mock engine states after rollups finish to ensure newly created positions still generate strands and feed learning.
4. Failure logging: if OHLC backfill fails, note “packet died during rollup; learning starved.”

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
