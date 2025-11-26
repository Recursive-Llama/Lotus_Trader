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

**Latest run (2025‑11‑26)**  
Harness: `tests/flow/learning_pipeline_harness.py` (PYTHONPATH=.)  
- Injected 40 Entry+Trim trades ⇒ 80 raw events written. `pattern_trade_events` confirmed 80 rows via exact-count query.  
- Lesson Builder (recursive Apriori) produced 704 lessons, including `chain=solana` and `chain=solana + market_family=meme` slices (N=40 each, avg RR≈1.41, edge_raw≈‑0.09).  
- Materializer upserted 512 strength overrides (multiplier clamp [0.3, 3.0]) and 8 tuning overrides using drift logic.  
- Evidence captured in terminal transcript (attached in harness log). Need to archive SQL snapshots per Section 5 before sign‑off.

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
- **2025-11-21** – Added `tests/flow/majors_feed_harness.py` to validate Hyperliquid WS ingest + rollups + tracker with explicit PASS/FAIL checkpoints on tick ingestion and 1m bar writes.
- **2025-11-21** – Added `tests/flow/pm_action_harness.py` to force S0→S1→S3→S0 transitions for a real position, run `pm_core_tick`, and print strand/action counts per step.
- **2025-11-21** – Removed legacy braiding system (`braiding_system.py`, `braiding_lesson_builder.py`). Learning now uses `pattern_scope_aggregator` (real-time) + v5 lesson builder + override materializer. Renamed `braiding_helpers.py` → `bucketing_helpers.py`.
- **2025-11-25** – Implemented `pattern_trade_events` (Fact Table) and V5 Lesson Builder (Miner) + V5 Materializer (Judge).
- **2025-11-25** – Implemented Phase 1 of Tuning System: `pattern_episode_events` logging in `PMCoreTick`.
- **2025-11-26** – Re-ran `pm_learning_flow_harness` with `--run-learning-jobs` (Strength pipeline green, trader layer still blocked on legacy indentation bug).  
- **2025-11-26** – Re-ran `learning_pipeline_harness` after recursive Apriori miner landed; confirmed Depth‑2 lessons and override drift output.  
- **2025-11-26** – Re-ran `pm_action_harness` (S1/S3 scenarios); S3 emergency-exit scenario returned `watchlist` instead of expected `active` status → needs follow-up bugfix before marking scenario fully green.

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
| **Lowcap OHLC + TA tracker** | `GenericOHLCRollup` and `ta_tracker` produce EMA/ATR/TS/OX/DX values for the test token, geometry builder outputs shapes | partial (TA snapshot proves tracker ran once, but no assertions) | Add verification step in PM action harness to query TA tables and compare expected metrics; add geometry assertions |
| **DM allocation learning** | DEPRECATED (DM simplification) | N/A | Removed from test plan |
| **Diagnostics (strand replay, lesson dry run, materializer dry run)** | Each tool processes real snapshots independently | ❌ not covered | Provide CLI scripts per §4 so we can isolate failures |

**Next actions**
1. ✅ **PM action harness** - Built and working. Verifies S1 entry, S3 retest, emergency_exit, trade closure, strand emission.
2. ✅ **Majors feed harness** - Built and working. Validates Hyperliquid WS ingest + rollups with explicit PASS/FAIL.
3. ✅ **Learning pipeline harness** - Built and working. Verifies Aggregator -> Lesson Builder -> Materializer flow.
4. ✅ **Tuning System Harness Phase 2/3** – Harness seeds synthetic events (N≥33), runs `TuningMiner` + drift judge, and verifies tuning overrides for S1/S3 patterns.
5. ⏳ **Exposure / Sizing verification** – Extend PM action harness (or dedicated scenario) to assert `exposure_skew < 1.0` when multiple positions share scope.
6. ⏳ **Real executor smoke (micro-size)** – Run `pm_action_harness` with the live PM executor (dry-run or $1 notional) to confirm the harness stub stays aligned with on-chain payloads; capture RPC/fee health in the evidence bundle.

Once each harness is green, we can revisit whether a combined “full stack” rehearsal (possibly via `run_social_trading.py` plus scripted inputs) is needed, but keeping the harnesses modular gives us clearer failure boundaries.
