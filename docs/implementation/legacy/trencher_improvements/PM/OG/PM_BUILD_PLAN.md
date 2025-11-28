# PM Build Plan Overview (Enhanced v2.0)

## 1. Prerequisites & Database Schema
- **curator_signals fields**: intent_type, confidence, token/chain, ts, intent_divergence, temporal_sync
- **positions.features**: JSONB field with cached PM inputs (rsi_div, vo_z, sr_break, intent_metrics, residual_vs_majors, breadth_z, age_h, pnl_pct, usd_value, liquidity_usd, market_cap, weakness_ema, weakness_days, dead_score, dead_score_final, obv_ema, obv_z, obv_slope, obv_tf, sr_break, sr_conf, sr_age, sr_tf)
 - **positions.features (additions)**: lens diagnostics and dominance metrics (S_btcusd, S_rotation, S_port_btc, S_port_alt, btc_dom_delta, usdt_dom_delta, btc_dom_slope_z, btc_dom_curv_z, btc_dom_level_z, usdt_dom_slope_z, usdt_dom_curv_z, usdt_dom_level_z)
- **positions.cooldown_until**: Time gates for position re-evaluation
- **positions.last_review_at**: PM decision tracking
- **positions.time_patience_h**: Min hours to hold before re-evaluation gates (36/72/168)
- **positions.reentry_lock_until**: Cooldown before re-entry (36h default)
- **positions.trend_entry_count**: Track trend entries for learning
- **positions.new_token_mode**: Boolean flag for new token entry mode (is_new_token, flip_conditions_met, observation_start_time, probe_size_frac)
- **ad_strands** (existing): Table used for PM decisions/strands (decision_type, size_frac, A_value, E_value, reasons[], phase_state, forward_pnl_24h/72h, eps_score, trend_redeploy_frac, new_token_mode)
- **phase_state**: Store macro/meso/micro phase detection results with confidence, dwell_remaining, pending_label
 - **phase_state (additions)**: persist lens sub-scores per horizon (S_btcusd, S_rotation, S_port_btc, S_port_alt) to mirror SPIRAL Section 9
- **portfolio_bands**: Core count tracking and cut_pressure state (includes core_count, core_pressure, delta_core)
  - Also stores dominance diagnostics and raw levels (`btc_dom_level`, `usdt_dom_level`, nullable)
 - **majors_price_data_1m**: Canonical 1m OHLCV for majors (BTC, ETH, BNB, SOL, HYPE) from Hyperliquid WS (schema mirrors lowcap_price_data_1m)
 - **majors_trades_ticks**: Raw Hyperliquid trade ticks for majors (used to roll up to 1m)

## 2. Data & Feature Workers
- **lowcap_price_data_1m ingest**: Continuous price data pipeline (UTC-aligned bars)
- **OHLCV backfill**: One-shot backfill for new tokens
- **Features pipeline**: Compute and cache r_btc, r_alt (EW SOL/ETH/BNB/HYPE), r_port; residual_major (port−BTC), residual_alt (port−Alt), rotation_spread (Alt−BTC); lens sub-scores (S_btcusd, S_rotation, S_port_btc, S_port_alt) per horizon; rsi_div, vo_z, sr_break, intent_metrics, breadth_z, phase_state, obv_ema, obv_z, obv_slope, sr_break, sr_conf, sr_age, sr_tf to positions.features
- **Real-time updates**: Keep cached features current for PM consumption
- **EMA calculation**: As per SPIRAL Appendix A defaults (Micro EMA_60 1m, Meso EMA_55 15m, Macro EMA_200 4h) or document PM-specific 15m/1h pair; ensure consistency
- **RSI divergence detection**: Price vs RSI slope comparison for signal generation
- **OBV computation**: On-Balance Volume calculation with multi-timeframe smoothing (EMA 3-5 periods, slope over 5 bars, z-score over 7-14 lookback)
- **Volume analysis**: VO_z calculation vs 7-day mean, volume climax detection, blended vol_state (0.6*VO_z + 0.4*OBV_z)
- **Price-action geometry**: Support/resistance detection with prominence ≥0.5·ATR(14), Theil–Sen trendlines through last 3–5 highs/lows, bull/bear breaks with (vo_z>0.5 OR OBV_z>0) confirmation, sr_conf scoring, validity M=20 bars or re-entry ≥3 bars
- **Intent aggregation**: Multi-channel intent processing with synchrony detection

## 3. SPIRAL Engine (Phase Detector) - Mathematical Implementation
- **Four-lens inputs** (USD log returns): r_btc, r_alt = EW(SOL, ETH, BNB, HYPE), r_port; residual_major = r_port − r_btc; residual_alt = r_port − r_alt; rotation_spread = r_alt − r_btc
- **Multi-horizon analysis**: Macro {1d, 3d, 1w}, Meso {4h, 12h, 1d}, Micro {30m, 2h, 4h}
- **Feature extraction per window**:
  - Smooth streams: `R_tf = EMA(stream_tf, n_tf≈2–3)`
  - Slope computation: regression slope over last k bars of R_tf
  - Curvature: slope-of-slope (second derivative)
  - ΔResidual: `R_tf(now) - R_tf(prev_window)`
- **Lens sub-scores**: S_btcusd (on r_btc), S_rotation (on rotation_spread), S_port_btc (on residual_major), S_port_alt (on residual_alt) using `0.5×Slope_H + 0.3×Curvature_H + 0.2×ΔRes_H + 0.1×Level_H`
- **Horizon blends**: Macro = 0.55·S_btcusd + 0.35·S_rotation + 0.05·S_port_btc + 0.05·S_port_alt; Meso = 0.50·S_port_btc + 0.30·S_port_alt + 0.15·S_rotation + 0.05·S_btcusd (adaptive rotation tilt ±0.10 to S_port_alt/S_port_btc); Micro = 0.70·S_port_btc + 0.30·S_port_alt
- **Phase band mapping**: Euphoria ≥+1.20, Good +0.40–+1.20, Recover −0.20–+0.40, Dip −0.90–−0.20, Double-Dip −1.30–−0.90, Oh‑Shit < −1.30; skip rules reaffirmed (no Recover→Double‑Dip)
- **Hysteresis & dwell logic**: Enter at threshold A, exit at B (±0.2 gap), min dwell times (Macro≥3d, Meso≥12h, Micro≥60-90m)
- **Context nudges**: Breadth_z, Vol_z, RSI_bias, EMA_cross_bias, IntentBreadthBias (±0.2 max)
- **Cross-horizon coherence**: Macro anchors (1.0), Meso drives (0.6-0.8), Micro timing (0-0.4 adaptive)
- **Output generation**: {macro, meso, micro, A/E/readiness} phase states with confidence and dwell_remaining
- **Phase storage**: Persist phase states for PM consumption with sequence sanity checks

## 4. PM Core Engine
- **Hourly tick**: Main PM decision loop (60s price data, 1h PM cadence)
- **Event triggers**: decision_approved, price_dips, exit_created, mention_update, band_breach, time_gates
- **Input processing**: Read positions.features, phase_state, compute A/E modes per position
- **Output generation**: Write pm_decision_strands, update position states

## 5. PM Lever Computation - Complete Signal Processing
- **Phase → Policy Templates**: Meso sets behavior, Macro scales amplitude, Micro times spikes
- **A/E computation with signal weights**:
  - RSI divergence: ±0.25 (primary lead signal)
  - OBV divergence: ±0.10 (confirms/denies RSI)
  - RSI+OBV combo kicker: +0.05 (when both agree)
  - Price-action geometry: ±0.15 A, ±0.20 E (bull/bear breaks, S/R retests)
  - EMA trend: ±0.05 (confirmation only)
  - Volume+OBV state: ±0.10 (0.6*VO_z + 0.4*OBV_z)
  - Intent channels: ±0.30 (vector sum of sub-scores)
  - Residual Δ vs Majors: ±0.10 (rising→strength, rolling→E↑)
  - Breadth bias: ±0.05 (contrarian flip at z<-2)
- **Signal clamping**: Total weights clamped to ±0.4 per lever
- **Intent channel processing**:
  - High-Confidence Buy: +0.25 A, -0.10 E
  - Medium Buy: +0.15 A, -0.05 E
  - Profit Intent: -0.15 A, +0.15 E
  - Sell/Negative: -0.25 A, +0.35 E
  - Mocking/Derision: -0.10 A, +0.10 E
- **Intent synchrony detection**: ≥3 curators, spread>1d (+0.05 A, -0.05 E), spread<0.5d (-0.10 A, +0.10 E)
- **Cut-pressure coupling**: single stage; `cut_pressure` already folds core-count seesaw.
  `A_final = A_policy × (1 − 0.33 × cut_pressure)`, `E_final = E_policy × (1 + 0.33 × cut_pressure)`
- **DeadScore computation**: `0.4*(PnL < -30%) + 0.2*(VO < 0.5) + 0.2*(intent_strength < 0.2) + 0.2*(residual_pnl < -0.5)`
- **DeadScore adjustments**: Dual weakness +0.2, intent divergence hold, macro context trim/replace
- **DeadScore coupling**: `DeadScore_final = DeadScore × (1 + 0.3 × cut_pressure)`
- **Time gates**: 36/72/168h patience gates, 36h re-entry lock logic
- **F_now targets**: immediate on-book targets = 0.10 / 0.33 / 0.50 (Patient / Normal / Aggressive)
  - On A increase: immediate top-up to F_now × max_alloc (reserves left for ladders/trend)
  - On A decrease: no forced sells; freeze adds and soft-trim via exits/trails toward F_now
- **Portfolio breathing**: cut_pressure based on 12-26-36 core bands with phase sensitivity and dominance modulators (BTC.D early-rise/peak-roll light; USDT.D heavier, antisymmetric)

## 6. PM Action Mapping (Zones) - Complete Entry/Exit Logic
- **Entry modes**: Patient (10%), Normal (33%), Aggressive (50%) with −23.6/−38.2/−61.8% ladders
- **Entry ladder access**: −23.6% (VO>1), −38.2% (structure+VO≥1), −61.8% (retest+RSI slope>0)
- **Exit logic**: Base ladder +38.2%, +61.8%, +161.8%, +261.8%, +423.6%, +685.4%, +1089%
- **Exit slice sizing by E_mode**: Patient 10-15%, Normal 20-25%, Aggressive 30-40% (of remaining bag)
- **EMA trail stops**: 15 consecutive 1-min closes below EMA_long → queue exit on bounce
- **Trail stop logic**: If no reclaim within 6 bars → demote to Moon Bag (protect profit only)
- **Trend-redeploy system**: 10/15/25% fractions by A_mode with phase gates
- **Trend entry triggers**: Partial harvest (+23.6/+38.2/+61.8), pre-checks (sr_break≠bear, RSI_slope>0 OR obv_trend>0 OR sr_break=="bull", VO_z>0.5 OR OBV_z>0 OR sr_conf>=0.5)
- **Trend entry phase gates**: Blocked in Meso Euphoria, allowed in Double-Dip→Oh-Shit→Recover→Good
- **Re-entry lock logic**: 36h cooldown unless price < 0.7× last_exit + fresh trigger
- **Action types**: add/trim/cut/hold/trail based on computed modes with EPS scoring

## 6.1. New Token Entry Mode - Specialized Discovery Pathway
- **Activation trigger**: is_new_token=true at first DM signal
- **Initial probe sizing**: 10% of DM max_alloc with A=0.20 (Patient), E=0.80 (Aggressive)
- **Observation window**: 5-15 minutes with 60s bar updates monitoring VO_z, RSI_1m/5m, EMA trends, micro stability, slippage/spread
- **Flip conditions**: Escalate Probe→Build if ≥2 of 4 conditions hold for ≥3 consecutive minutes:
  - VO_z ≥ +1.0 OR sr_break == "bull" (sustained expansion or structure break)
  - RSI > 50 and rising OR obv_trend > 0 (positive momentum)
  - Trend confirm: close above EMA_long OR diagonal reclaim OR sr_break == "bull" (structure confirmation)
  - Micro stability: |price - entry| ≤ 5% after initial thrust
- **Build phase**: A→0.8 (Aggressive), E→0.4 (Moderate), execute build adds on controlled pullbacks (-23.6%, -38.2%)
- **Failure handling**: Remain in probe state, exit on structure break (15 consecutive 1-min closes below EMA_long), queue trim on bounce
- **Safety rails**: Liquidity guard (spread>3%), herd burst detection (≥3 curators <30min), macro hostility checks
- **Deactivation**: new_token_mode=false after first build add, 60min timeout, or +61.8% harvest with E_mode≥Normal
- **Integration**: Works with existing trend-add rules, DeadScore coupling, and portfolio state (cut_pressure, underexposure)

## 7. Portfolio Bands & Rotation
- **Core-count seesaw (folded into cut_pressure)**: ideal 12; compute `delta_core = k·tanh((core_count − 12)/τ)` and `core_pressure = 0.5 + 0.5·tanh((core_count − 12)/τ)`; persist to `portfolio_bands` and include in cut_target per SPIRAL §6.3.
- **Phase-sensitive trimming**: Dip/Double-Dip cut overperformers, Recover/Good/Euphoria cut laggards
- Remove EPS from scope: trim selection remains local (A/E + geometry). No portfolio-level ranking.
- **Weakness tracking**: WeaknessEMA = EMA(residual_vs_majors, 7d), weakness_days counter
- **Laggard vs Weak Coin classification**: ≤2 cycles (laggard), ≥3 cycles + rising DeadScore (weak coin)
- **Core↔Moon lifecycle**:
  - Demotion triggers: DeadScore_final > 0.6 OR EMA trend break confirmed
  - Demotion action: Sell 70-90%, convert to Moon Bag
  - Promotion triggers: Price > EMA_long + VO↑ + RSI > 50 + intent > 0.5 + phase ∈ {Recover, Good}
  - Moon bag rules: 0.3-0.5% each, no adds, harvest only on major pumps
- **Moon bag sizing**: On demotion, sell down to min(10% of current position size, 0.9% of portfolio)

## 8. Event Bus & Triggers - Enhanced Event Processing
- **Event types**: decision_approved, price_dips, exit_created, mention_update, band_breach, time_gates, phase_transition, ema_trail_breach, intent_surge, new_token_signal, flip_conditions_met, probe_timeout, structure_break, sr_break_detected, sr_retest, sr_reject, dominance_early_rise, dominance_peak_roll, rotation_tilt_on, rotation_tilt_off
- **PM tick cadence**: Hourly + event-driven triggers
- **Event processing**: Convert events to PM decision triggers with priority queuing
- **Phase transition events**: Trigger immediate A/E recomputation when phase changes
- **EMA trail breach events**: Immediate trail stop evaluation and bounce detection
- **Intent surge events**: Rapid intent aggregation and synchrony detection
- **New token events**: Trigger new token entry mode activation and observation window monitoring
- **Flip condition events**: Monitor and trigger Probe→Build escalation when conditions met
- **Probe timeout events**: Handle 60-minute observation window expiration and structure break detection
- **Structure break events**: Monitor diagonal breaks, S/R retests, and rejections for immediate A/E adjustments
- **Time gate events**: Automatic position re-evaluation when patience periods expire
- No band breach events; core-count acts only via cut_pressure.

## 9. Strands & Logging - Comprehensive Decision Tracking
- **pm_decision schemas**: decision_type, size_frac, A_value, E_value, reasons[], phase_state, eps_score, trend_redeploy_frac, dead_score_final
- **pm_log schemas**: Forward PnL 24h/72h backfill with context snapshots
- **Context capture**: reasons[], phase_state, forward_pnl tracking, signal weights, intent_aggregation, obv_div_bull/bear, obv_confirm, obv_z_up/down, sr_break_bull/bear, sr_retest, sr_reject
- **Decision types**: add/trim/cut/hold/trail/trend_add/demote/promote/add_probe/flip_build/hold_probe/trim_on_bounce with full reasoning chains
- **Learning preparation**: Every PM decision becomes a strand for future learning with complete feature vectors
- **Performance tracking**: A/E mode effectiveness, phase transition success, EPS accuracy, trend entry performance
- **Audit trail**: Complete decision history with forward PnL for learning system feedback

## 10. Integration Points - Complete System Architecture
- **DM → PM**: max_alloc caps, decision context, intent_metrics, archetype_tags
- **PM → Trader**: size_frac commands for execution, trend_entry flags, moon_bag conversions
- **PM → Learning**: pm_decision_strands for future learning with complete feature vectors
- **Social → PM**: intent signals via positions.features, synchrony detection, divergence analysis
- **Market → PM**: price/volume data via positions.features, EMA calculations, RSI divergence
- **SPIRAL → PM**: phase states (macro/meso/micro), confidence levels, dwell tracking
- **PM → Portfolio**: Core/Moon lifecycle management, cut_pressure modulation, band enforcement
- **PM → Risk**: DeadScore monitoring, weakness tracking, trail stop management

## 11. Ops & Dashboards - Enhanced Monitoring & Safeguards
- **Live status**: A/E modes, cut_pressure, phase states, DeadScore distributions, EPS rankings
- **Core count bands**: Portfolio structure monitoring with phase-sensitive thresholds
- **Decision audit trail**: PM decision history and reasoning with forward PnL tracking
- **Performance metrics**: PM effectiveness tracking, A/E mode performance, phase transition success
- **SPIRAL monitoring**: Phase confidence levels, dwell tracking, sequence sanity checks
- **Intent monitoring**: Synchrony detection, divergence alerts, channel weight distributions
- **Risk monitoring**: DeadScore trends, weakness tracking, trail stop effectiveness
- **Operational safeguards**: 
  - Backfill fallbacks for new tokens with historical data reconstruction
  - Stale-feature detection (skip decisions if features >2h old)
  - Idempotent event handling and ordered processing
  - Circuit breakers for extreme market conditions
  - Feature validation and outlier detection
  - Graceful degradation when external data sources fail

## 12. Testing & Rollout - Comprehensive Validation Strategy
- **Backtest replay**: Historical PM decision testing with full SPIRAL phase detection
- **Shadow mode**: PM decisions without execution, complete strand logging
- **Guarded enablement**: Gradual rollout with safety checks and circuit breakers
- **Phase transition testing**: Validate SPIRAL mathematical accuracy across market cycles
- **A/E mode testing**: Verify signal weight accuracy and coupling formulas
- **DeadScore validation**: Test weakness tracking and demotion logic
- **EPS system testing**: Validate trim selection accuracy and phase bias
- **Trend entry testing**: Verify redeploy logic and phase gates with OBV confirmation
- **New token entry testing**: Validate probe→build escalation, flip conditions, safety rails, and timeout handling
- **OBV integration testing**: Verify OBV computation accuracy, divergence detection, and signal weight integration
- **Price-action geometry testing**: Validate S/R detection, diagonal break accuracy, and structure confirmation logic
- **Intent processing testing**: Validate synchrony detection and divergence analysis
- **Metrics**: PM performance and learning system feedback with forward PnL analysis

## 13. Learning Hooks (Future) - Advanced Optimization
- **Weight tuning**: Optimize A/E computation weights based on forward PnL analysis
- **Band optimization**: Refine 12-26-36 core count bands using portfolio performance data
- **Selection rules**: Improve trim selection heuristics with EPS component optimization
- **Archetype presets**: Position-specific lever configurations based on behavioral patterns
- **Phase detection refinement**: Optimize SPIRAL mathematical parameters using market cycle data
- **Intent processing optimization**: Improve synchrony detection and divergence analysis accuracy
- **DeadScore calibration**: Refine weakness tracking thresholds and adjustment rules
- **Trend entry optimization**: Optimize redeploy fractions and phase gate effectiveness with OBV confirmation
- **New token entry optimization**: Optimize probe sizing, flip conditions, and safety rail thresholds
- **OBV parameter optimization**: Refine OBV computation parameters, divergence thresholds, and signal weights
- **Price-action geometry optimization**: Refine S/R detection thresholds, diagonal break parameters, and structure confirmation logic
- **EMA trail optimization**: Refine trail stop parameters and bounce detection logic
- **Cut-pressure calibration**: Optimize portfolio breathing parameters across market regimes

## 14. Implementation Priority Matrix
**Phase 1 (Core Foundation)**:
- Database schema updates and feature caching
- Basic SPIRAL mathematical engine
- Simple A/E computation with signal weights
- Basic entry/exit logic and portfolio bands

**Phase 2 (Advanced Logic)**:
- Complete DeadScore system with adjustments
- EPS-based trim selection with phase bias
- Trend entry and recycle logic with OBV and structure confirmation
- New token entry mode with probe→build escalation
- Price-action geometry integration with S/R and diagonal breaks
- EMA trail stops with bounce detection

**Phase 3 (Sophistication)**:
- Intent synchrony detection and divergence analysis
- Advanced Core↔Moon lifecycle management
- Comprehensive event processing and monitoring
- Learning system integration and optimization

The PM is a sophisticated database entity that reads cached features, computes breathing parameters through mathematical phase detection, and writes comprehensive decision strands. It's triggered hourly and by events, integrating seamlessly with the existing strand flow while providing the mathematical rigor and operational sophistication described in the detailed specifications.

===========

Section by Section Build Plan


### 1) Prerequisites & Database Schema — Detailed Build Plan

Goal

- Create the exact tables/columns/indexes required by SPIRAL and PM to store phase states, decisions, and portfolio breathing, aligned with UTC and the lens diagnostics.

Scope

- In: schema changes, indices, constraints, retention, verification queries, and safe rollout.
- Out: business logic (computed by workers) — covered in later sections.

Migrations (SQL)

- positions table:
  - add column features JSONB (if not present)
  - add columns: cooldown_until TIMESTAMPTZ, last_review_at TIMESTAMPTZ, time_patience_h INT, reentry_lock_until TIMESTAMPTZ, trend_entry_count INT DEFAULT 0, new_token_mode BOOLEAN DEFAULT FALSE
- phase_state table:
  - id (PK), token TEXT, ts TIMESTAMPTZ (UTC), horizon TEXT CHECK (horizon IN ('macro','meso','micro')),
    phase TEXT, score DOUBLE PRECISION, slope DOUBLE PRECISION, curvature DOUBLE PRECISION, delta_res DOUBLE PRECISION,
    confidence DOUBLE PRECISION, dwell_remaining DOUBLE PRECISION, pending_label TEXT NULL,
    s_btcusd DOUBLE PRECISION, s_rotation DOUBLE PRECISION, s_port_btc DOUBLE PRECISION, s_port_alt DOUBLE PRECISION
- pm_decision_strands table:
  - id (PK), token TEXT, ts TIMESTAMPTZ, decision_type TEXT, size_frac DOUBLE PRECISION,
    a_value DOUBLE PRECISION, e_value DOUBLE PRECISION, reasons JSONB, phase_state JSONB,
    forward_pnl_24h DOUBLE PRECISION NULL, forward_pnl_72h DOUBLE PRECISION NULL,
    eps_score DOUBLE PRECISION NULL, trend_redeploy_frac DOUBLE PRECISION NULL, new_token_mode BOOLEAN DEFAULT FALSE
- portfolio_bands table:
  - ts TIMESTAMPTZ, core_count INT, cut_pressure DOUBLE PRECISION, cut_pressure_raw DOUBLE PRECISION,
    phase_tension DOUBLE PRECISION, core_congestion DOUBLE PRECISION, liquidity_stress DOUBLE PRECISION, intent_skew DOUBLE PRECISION,
    btc_dom_delta DOUBLE PRECISION, usdt_dom_delta DOUBLE PRECISION, dominance_delta DOUBLE PRECISION,
    btc_dom_slope_z DOUBLE PRECISION, btc_dom_curv_z DOUBLE PRECISION, btc_dom_level_z DOUBLE PRECISION,
    usdt_dom_slope_z DOUBLE PRECISION, usdt_dom_curv_z DOUBLE PRECISION, usdt_dom_level_z DOUBLE PRECISION,
    nav_usd DOUBLE PRECISION NULL

Price tables (DDL — reference; MVP must-haves only)
Canonical note: 1m is the canonical ingest for both lowcaps and majors. Higher TFs (5m/1h/1d) should be implemented as SQL views/materialized views later (optional), not new base tables.

```sql
-- Raw ticks from Hyperliquid WS
CREATE TABLE IF NOT EXISTS public.majors_trades_ticks (
  token      text        NOT NULL,   -- BTC, ETH, BNB, SOL, HYPE
  ts         timestamptz NOT NULL,   -- trade timestamp (UTC)
  price      numeric     NOT NULL,
  size       numeric     NOT NULL,   -- base size; quote can be derived
  side       text        NULL,       -- 'buy' | 'sell' if available
  trade_id   text        NULL,
  source     text        NOT NULL DEFAULT 'hyperliquid',
  inserted_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (token, ts, trade_id)
);

-- 1m OHLCV rolled up from ticks; mirrors lowcap_price_data_1m
CREATE TABLE IF NOT EXISTS public.majors_price_data_1m (
  token      text        NOT NULL,
  ts         timestamptz NOT NULL,   -- minute start UTC
  open       numeric     NOT NULL,
  high       numeric     NOT NULL,
  low        numeric     NOT NULL,
  close      numeric     NOT NULL,
  volume     numeric     NOT NULL,   -- quote or base per convention (USD preferred)
  source     text        NOT NULL DEFAULT 'hyperliquid',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (token, ts)
);

-- Optional later: materialized views over both 1m tables (lowcaps/majors)
-- v_price_5m / v_price_1h / v_price_1d can be added and refreshed by a job
```

Indexes & constraints

- positions(token), phase_state(token, ts, horizon), pm_decision_strands(token, ts), portfolio_bands(ts)
- UNIQUE (token, ts, horizon) on phase_state to prevent duplicate writes
- CHECK (horizon IN ('macro','meso','micro')) on phase_state.horizon
- GIN on positions.features and pm_decision_strands.reasons for flexible querying

Backfill tasks

- Initialize features for existing positions with placeholders and current metrics
- Seed phase_state with latest macro/meso/micro per token

Verification queries

- Ensure UTC alignment: SELECT date_part('timezone', ts) FROM phase_state LIMIT 10;
- Validate recent strands exist after PM tick: SELECT count(*) FROM ad_strands WHERE ts > now() - interval '1 hour';
- Check cut_pressure fields populated: SELECT * FROM portfolio_bands ORDER BY ts DESC LIMIT 5;

Acceptance criteria

- All tables/columns created; NOT NULL applied where specified; diagnostics nullable.
- phase_state enforces UNIQUE (token, ts, horizon) and horizon CHECK constraint.
- Sample write from a dry-run SPIRAL job inserts macro/meso/micro rows with s_btcusd/s_rotation/s_port_btc/s_port_alt populated.
- Verification queries return expected counts; no duplicate rows on (token, ts, horizon).

Rollout plan

- Apply migrations in a transaction; add columns as NULLable first; backfill; then tighten constraints where safe.
- Run 90‑day backfill for phase_state and portfolio_bands; verify row counts per token×horizon and hourly cadence.
- Enable writers; monitor insert error rate and flip/dwell metrics for 24–48 h.

Rollback

- If needed, disable writers, drop UNIQUE/constraints first, then drop added columns/tables; retain archived copies.

Operational notes

- Enforce NOT NULL where safe; keep diagnostics nullable to allow gradual rollout
- Add pruning/retention policies: e.g., keep phase_state 90d hot, archive beyond
=============


=============

### 2) Data & Feature Workers — Executable Build Plan

Goal

- Produce all inputs required by SPIRAL and PM on schedule (UTC), and persist them to `positions.features` and `phase_state` exactly as specified in `SPIRAL_DECISION_ENGINE.md` (Sections 2, 3.1/3.2, 6.2, 6.3, Appendices A/B).

Scope

- In: OHLCV ingestion/aggregation; portfolio NAV; dominance series; feature computation (returns, residuals, lenses, geometry, diagnostics); persistence; data-quality gates.
- Out: A/E computation and cut-pressure math (handled in PM/Section 5 and SPIRAL §6.3 runtime).

Inputs (per Appendix A/B of SPIRAL)

- Prices & volume (USD): 1m canonical ingest → `lowcap_price_data_1m` (lowcaps), `majors_price_data_1m` (majors). Downsample to 5m/1h/1d via views/materialized views.
- Portfolio NAV snapshots (hourly) to compute r_port.
- Dominance series: BTC.D, USDT.D levels (hourly); used to compute 7 d deltas and z-scores; diagnostics stored in portfolio_bands (no new table).

Outputs

- positions.features additions per token: r_btc, r_alt (EW SOL/ETH/BNB/HYPE), r_port; residual_major, residual_alt, rotation_spread; OBV metrics; geometry `{sr_break, sr_conf, sr_age, sr_tf}`; breadth_z, vol_z, vo_z, rsi_bias, ema_cross_bias; dominance diagnostics (btc_dom_* and usdt_dom_* z-components and deltas).
- phase_state rows per token×horizon: `phase, score, slope, curvature, delta_res, confidence, dwell_remaining, pending_label, s_btcusd, s_rotation, s_port_btc, s_port_alt`.

Tasks (ordered)

1) Ingest ticks & rollup (UTC)
- Worker: `hyperliquid_ws_ticks` → current implementation aggregates directly to 1m OHLCV in-memory and upserts to `majors_price_data_1m`. Optional ticks persistence to `majors_trades_ticks` via `SAVE_TICKS=1`.
- Worker: `ticks_to_1m_rollup` remains as a utility/backfill path when ticks are stored; otherwise not required in the main pipeline.
- Worker: `price_ingest_1m_lowcaps` → write to `lowcap_price_data_1m` (unchanged).
- Aggregation: refresh materialized views `v_price_5m`, `v_price_1h`, `v_price_1d` over union of `lowcap_price_data_1m` and `majors_price_data_1m`.
- Snap to exact UTC boundaries; forward-fill ≤ 1 bar; else mark horizon confidence down.

2) NAV compute
- Worker: `nav_compute_1h` → compute r_port from portfolio NAV (USD log return) hourly.

3) Dominance fetch
- Worker: `dominance_ingest_1h` → fetch BTC.D, USDT.D; compute 7 d Δ; z-score over 90 d; derive `slope_z, curv_z, level_z` per SPIRAL §6.3; persist diagnostics for cut-pressure.

4) Feature computation (hourly)
- Worker: `features_compute_1h` implementing SPIRAL §2 and Appendix A (geometry runtime disabled here; handled by monitor):
  - Returns (USD log): r_btc, r_alt = EW(SOL, ETH, BNB, HYPE), r_port.
  - Streams: residual_major = r_port − r_btc; residual_alt = r_port − r_alt; rotation_spread = r_alt − r_btc.
  - Per horizon windows {Micro 30m/2h/4h; Meso 4h/12h/1d; Macro 1d/3d/1w} with n_tf={3,5,7}, k_tf={30,24,20}, Δ windows {2h,1d,1w}, L_H={14,30,60}:
    - Compute Slope_H, Curvature_H, ΔRes_H, Level_H (weights 0.2/0.6/0.2).
    - Lens sub-scores (SPIRAL §3.1): S_btcusd on r_btc; S_rotation on rotation_spread; S_port_btc on residual_major; S_port_alt on residual_alt.
    - PhaseScore per horizon (SPIRAL §3.2): Macro 0.55/0.35/0.05/0.05; Meso 0.50/0.30/0.15/0.05 with adaptive tilt; Micro 0.70/0.30.
    - Map to bands with hysteresis ±0.2 and dwell (Macro ≥3d, Meso ≥12h, Micro ≥60–90m). Enforce skip rules (no Recover→Double‑Dip).
  - Geometry (SPIRAL §6.2): daily builder computes levels/diagonals; per-minute tracking in `trading/position_monitor.py` updates `sr_break/diag_break/conf` using latest bars (hourly tracker disabled by default).
  - Context nudges: breadth_z, vol_z, vo_z, rsi_bias, ema_cross_bias per Appendix A (apply only where specified).

5) Persistence
- Update `positions.features` fields per token.
- Append `phase_state` per token×horizon with diagnostics `s_btcusd/s_rotation/s_port_btc/s_port_alt`.

6) Events (for Section 8)
- Emit: `phase_transition` (per horizon), `rotation_tilt_on/off`, `dominance_early_rise/peak_roll`, `sr_break_detected/retest/reject`.

Interfaces (modules/functions)

- `ingest/hyperliquid_ws.py`: `run_ws_ingest(symbols: list[str]) -> None` (writes majors_trades_ticks)
- `ingest/rollup.py`: `rollup_ticks_to_1m(now: datetime) -> int` (writes majors_price_data_1m)
- `spiral/returns.py`: `compute_returns(prices) -> dict[r_btc, r_alt, r_port]`
- `spiral/lenses.py`: `compute_lens_scores(streams, params) -> dict[S_btcusd, S_rotation, S_port_btc, S_port_alt]`
- `spiral/phase.py`: `compute_phase_scores(lens_scores, params) -> dict[macro, meso, micro]`
- `spiral/geometry.py`: `detect_geometry(ohlcv, vo_z, obv_z) -> dict[sr_break, sr_conf, sr_age, sr_tf]`
- `spiral/dominance.py`: `compute_dom_diagnostics(btc_d, usdt_d) -> dict[slope_z, curv_z, level_z]`
- `spiral/persist.py`: `write_phase_state(rows); write_features(token, features_dict)`

Tests

- Unit: derivatives (slope/curvature), z-scoring windows, hysteresis/dwell enforcement, skip rules.
- Fixture: canned scenarios validating Recover→Good and Euphoria→Dip transitions; geometry sr_conf near 0.6–0.8 on typical breaks.
- Integration: 7d backtest replay producing stable dwell and no invalid flips; phase outputs match doc examples.

Acceptance criteria

- Fresh features (< 2 h); populated `phase_state` rows for all tokens×horizons with diagnostics.
- Deterministic outputs on fixed seed input; band transitions obey hysteresis/dwell and skip rules.
- Geometry and dominance diagnostics present; events emitted.

Telemetry

- Log decision snapshots on phase flips (phase, score, diagnostics); counters for flip rate, avg dwell, rotation_tilt state.
======================


### 3) SPIRAL Engine — Executable Build Plan

Goal

- Compute Macro/Meso/Micro phases per token using the four-lens method, write per-horizon rows to `phase_state`, and emit phase events. All math and parameters come from `SPIRAL_DECISION_ENGINE.md` (Sections 2, 3.1/3.2, 4, 6.2, 8, 9; Appendices A/B).

Scope

- In: 1m OHLCV (majors/lowcaps), dominance diagnostics (read-only), positions (for r_port), OBV/VO/breadth inputs.
- Out: `phase_state` rows with diagnostics; events: `phase_transition`, `rotation_tilt_on/off`, `sr_break_*`.

Inputs

- Prices: `lowcap_price_data_1m`, `majors_price_data_1m` (USD), aligned to UTC. Note: geometry consumed from `positions.features.geometry` (built daily + tracked per-minute), not recomputed in the SPIRAL job.
- Alt basket: EW(SOL, ETH, BNB, HYPE) from `majors_price_data_1m`.
- r_port: computed hourly from `positions` (Σ qty × last_price from 1m close), no separate NAV table; last NAV cached or read from latest `portfolio_bands.nav_usd`.
- Breadth universe: tokens in `lowcap_positions`.
- Dominance: BTC.D/USDT.D z-diags (read from `portfolio_bands`, not written here).

Outputs (per token×horizon×ts)

- `phase_state`: phase, score, slope, curvature, delta_res, confidence, dwell_remaining, pending_label, s_btcusd, s_rotation, s_port_btc, s_port_alt.
- Events on label flips with prior/new phase and diagnostics.

Tasks (ordered)

1) Returns & streams (hourly driver, reads 1m windows)
- Compute USD log returns r_btc (BTC), r_alt (EW SOL/ETH/BNB/HYPE), r_port.
- Streams: residual_major = r_port − r_btc; residual_alt = r_port − r_alt; rotation_spread = r_alt − r_btc.

2) Feature extraction per horizon (Appendix A)
- Windows: Micro {30m,2h,4h}, Meso {4h,12h,1d}, Macro {1d,3d,1w} over 1m series.
- For each stream: EMA smoothing (n_tf={3,5,7}); slope (k_tf={30,24,20}); curvature; Δ vs window_len {2h,1d,1w}; z-score with L_H {14,30,60}; winzorize 1%.
- Aggregate: Slope_H/Curvature_H/ΔRes_H/Level_H using {0.2,0.6,0.2} weights.

3) Lens sub-scores & blends (Sections 3.1/3.2)
- S_btcusd on r_btc; S_rotation on rotation_spread; S_port_btc on residual_major; S_port_alt on residual_alt with 0.5/0.3/0.2/0.1 mix.
- PhaseScore_macro = 0.55·S_btcusd + 0.35·S_rotation + 0.05·S_port_btc + 0.05·S_port_alt.
- PhaseScore_meso = 0.50·S_port_btc + 0.30·S_port_alt + 0.15·S_rotation + 0.05·S_btcusd with adaptive tilt: if S_rotation > +0.8 (6–12h dwell) → 0.40/0.40; if < −0.8 → 0.60/0.20.
- PhaseScore_micro = 0.70·S_port_btc + 0.30·S_port_alt.

4) Labeling & guards
- Map to bands; hysteresis ±0.2; dwell: Macro ≥3d, Meso ≥12h, Micro ≥60–90m.
- Skip rules: no Recover → Double‑Dip; allowed skips per spec.
- Confidence: distance to band edge × dwell fraction.

5) Geometry overlay (Section 6.2)
- Swings N=10 with prominence ≥0.5·ATR(14); Theil–Sen trendlines; bull/bear breaks.
- Confirmation: (vo_z > 0.5) OR (OBV_z > 0); sr_conf = 0.6·sigmoid(distance) + 0.4·sigmoid(vol_term); validity M=20 or channel re-entry ≥3.
- Emit sr_break events; log geometry outputs to features for PM use.

6) Persistence & events
- Upsert/append `phase_state` per token×horizon×ts with diagnostics s_*.
- On label change per horizon: emit `phase_transition` with {prev, next, score, diagnostics}; emit `rotation_tilt_on/off` when tilt gates pass/fail.

Interfaces (modules)
- `spiral/returns.py`: compute r_btc/r_alt/r_port.
- `spiral/lenses.py`: compute S_btcusd/S_rotation/S_port_btc/S_port_alt.
- `spiral/phase.py`: label phases per horizon with hysteresis/dwell/skip.
- `spiral/geometry.py`: detect S/R and diagonal breaks, compute sr_conf.
- `spiral/persist.py`: write `phase_state` and emit events.

Tests & acceptance
- Unit: derivative/z-scoring math; banding/hysteresis/dwell; skip rules.
- Fixture: Recover→Good and Euphoria→Dip cases; rotation tilt on/off; geometry sr_conf ≈ 0.6–0.8 on typical breaks.
- Integration: 7d replay yields stable dwell and no invalid flips; outputs match spec thresholds.

Operational notes
- Job cadence: hourly driver with on-event triggers (sr_break, rotation tilt, dominance early-rise/peak-roll).
- Breadth_z computed from `lowcap_positions` universe; OBV/VO per Section 6.1 if enabled.

### 4) PM Core Engine — Executable Build Plan

Goal

- On an hourly tick (plus on-events), compute A/E modes and actions per position using Meso/Macro/Micro phases and signal weights, then write decisions to `ad_strands` and update position state.

Scope

- In: `phase_state` (latest per horizon), `portfolio_bands` (cut_pressure), `positions` (+ features), DM caps, intent metrics.
- Out: `ad_strands` decision strands; updated `positions` state fields (cooldowns/locks/counters).

Inputs

- Phases: latest Macro/Meso/Micro per token from `phase_state` with confidence/dwell.
- Portfolio tone: `portfolio_bands.cut_pressure` (+ components for logging).
- Position context: `positions` (qty, avg_entry, usd_value, age, new_token_mode, trend_entry_count, cooldowns, locks).
- Features (from positions.features): rsi_div, vo_z, obv_ema/obv_z/obv_slope, sr_break/sr_conf/sr_age/sr_tf, breadth_z, residual deltas, intent_metrics (+ synchrony), ema trend.
- DM caps: max_alloc per token.

Outputs

- Strand records in `ad_strands` with: decision_type, size_frac (fraction of DM cap), A_value, E_value, reasons[], phase_state snapshot, trend_redeploy_frac when applicable, forward_pnl_24h/72h placeholders.
- Updated `positions` fields: last_review_at, cooldown_until, reentry_lock_until, time_patience_h, trend_entry_count, new_token_mode flag (unchanged unless Section 6.1 triggers), and any readiness gates.

Tasks (ordered)

1) Snapshot load (per token)
- Read latest Meso/Macro/Micro from `phase_state`; read `cut_pressure` from `portfolio_bands`.
- Read `positions` row + features; fetch DM.max_alloc.

2) Base A/E from phase templates (PM_LEVER_SPEC.md & PM_CHEAT_SHEET.md)
- Map Meso label → (A_policy, E_policy) per behaviour templates.
- Apply Macro multipliers from the policy table to modulate amplitude (never invert direction).
- Micro affects pacing only (not posture); keep its weight to drive readiness timing and ladder cadence.

3) Cut-pressure coupling (canonical 0.33)
- A_pre = A_policy × (1 − 0.33 × cut_pressure)
- E_pre = E_policy × (1 + 0.33 × cut_pressure)

4) TA/structure/volume and intent deltas (clamped)
- Sum per-lever deltas with caps ±0.4:
  - RSI divergence: ±0.25; OBV divergence: ±0.10; combo kicker +0.05 when both agree.
  - Geometry: ±0.15 A, ±0.20 E (bull/bear diagonal breaks; S/R retests per sr_conf).
  - EMA trend (confirm only): ±0.05.
  - Volume+OBV state: ±0.10 (0.6·VO_z + 0.4·OBV_z).
  - Residual Δ vs Majors: ±0.10; Breadth bias: ±0.05.
  - Intent channels (sum): ±0.30 with synchrony modifiers.
- Apply deltas to A_pre/E_pre → A_tmp/E_tmp.

5) Clamp, discretize for UI, size now
- Clamp A_final/E_final to [0,1].
- Derive display modes only: patient [0–0.3), normal [0.3–0.7), aggressive [0.7–1].
- Compute immediate size target F_now (0.10/0.33/0.50 of DM cap for Patient/Normal/Aggressive), scaled by A_final (continuous):
  - size_now = min(DM.max_alloc × F_mode × A_final, remaining_cap)

6) Readiness & action planning
- New entry readiness per phase: Dip/Double-Dip = Wait; Recover/Good/Euphoria = Active (with rotation nuances).
- Trend-entry gate (Section 6.2/Doc 4): sr_break!=bear AND (RSI_slope>0 OR obv_trend>0 OR sr_break==bull) AND (VO_z>0.5 OR OBV_z>0 OR sr_conf≥0.5) AND phase_meso ∈ {Double-Dip, Oh‑Shit, Recover, Good} AND DeadScore<0.4.
- Re-entry lock: freeze trend adds for lock_h after EMA trail breaches.
- Time patience: enforce 36/72/168h gates before re-evaluation where configured.

7) Trim selection (EPS) when cutting exposure
- If cut_pressure > 0.2, compute EPS with phase bias and choose highest scores: OverextensionZ (0.45), ResidualWeakness (0.25), 1−intent (0.15), StaleAgeZ (0.10), LowVO (0.05).

8) Create decision and write strand
- decision_type: add / trim / cut / hold / trail / trend_add.
- size_frac: fraction of DM cap used now (not % of portfolio); for trims use slice sizing by E-mode.
- reasons[]: include active signals (e.g., rsi_div, obv_confirm, sr_break_bull, phase_recover, cut_pressure_up).
- Include phase_state snapshot {macro, meso, micro} and cut_pressure.
- Write to `ad_strands` and update `positions.last_review_at` etc.

9) Events
- Emit events for external systems: `decision_approved` (after persistence), `band_breach` (if core count crosses thresholds), and any trail/lock events.

Interfaces (modules)
- `pm/core/context.py`: load snapshot {phase_state, cut_pressure, positions, features, DM cap}.
- `pm/core/modes.py`: compute (A_policy, E_policy) from phase + macro.
- `pm/core/apply_signals.py`: apply TA/intent deltas with clamps → A/E.
- `pm/core/actions.py`: readiness gates, trend-entry logic, EPS trims, size_now.
- `pm/core/strand.py`: write `ad_strands` and update `positions` fields.

Tests & acceptance
- Unit: A/E coupling and clamp order; per-signal delta effects; EPS ranking.
- Fixture: scenarios for each phase transition; verify decisions match templates; ensure no decisions when feature staleness > 2 h.
- Integration: end-to-end hourly tick producing strands; verify size_now respects DM cap and locks.

Operational notes
- Cadence: hourly tick + on-event triggers (phase flip, sr_break, band breach).
- Safety: skip decisions if features stale (>2h) or confidence low; log reasons.

### 5) PM Lever Computation — Executable Build Plan

Goal

- Transform phase context + TA/intent signals into continuous A/E levers in [0,1], with deterministic ordering, clamping, and logging. Follow `PM_LEVER_SPEC.md` and `PM_CHEAT_SHEET.md` exactly.

Scope

- In: phase labels/scores (Meso, Macro, Micro), cut_pressure, TA/structure/volume features, intent channels, DM caps.
- Out: `(A_final, E_final)` and display modes, plus structured reasons[] suitable for `ad_strands`.

Inputs

- Phase templates: from SPIRAL Part 2 (Meso behaviour templates; Macro multipliers; Micro pacing guidance).
- Cut-pressure: `portfolio_bands.cut_pressure` (already computed per SPIRAL §6.3; use 0.33 coupling).
- TA/Structure/Volume: rsi_div, obv signals (obv_ema/obv_z/obv_slope), geometry `{sr_break, sr_conf}`, EMA trend, `vol_state = 0.6*VO_z + 0.4*OBV_z`.
- Market context nudges: residual Δ vs majors; breadth bias.
- Intent channels: high/medium buy, profit, sell/negative, mocking/derision; synchrony modifiers (count + time spread).

Outputs

- `(A_final, E_final)` in [0,1].
- `mode_display`: patient|normal|aggressive (for UI only, derived from A_final/E_final bins).
- `reasons[]`: ordered list of applied signals with magnitudes and before/after snapshots.

Computation order (deterministic)

1) Phase → base policy
- Map Meso label to (A_policy, E_policy) per behaviour table:
  - Dip: A≈0.2, E≈0.8
  - Double‑Dip: A≈0.4, E≈0.7
  - Oh‑Shit: A≈0.9, E≈0.8
  - Recover: A≈1.0, E≈0.5
  - Good: A≈0.5, E≈0.3
  - Euphoria: A mixed (0.3–0.4 for existing, 0.8 for new/laggards), E≈0.5

2) Macro multipliers (tone)
- Multiply A and E by Macro table multipliers from SPIRAL Part 2 §5; never invert direction.

3) Micro pacing (timing)
- Micro only affects pacing (readiness cadence), not lever direction; no arithmetic change to A/E beyond cadence flags.

4) Cut‑pressure coupling (canonical)
- A_tmp = A × (1 − 0.33 × cut_pressure)
- E_tmp = E × (1 + 0.33 × cut_pressure)

5) TA / Structure / Volume deltas (apply with caps)
- Start from A_tmp/E_tmp, sum deltas per lever then clamp the total per lever to ±0.4:
  - RSI divergence: ±0.25
  - OBV divergence: ±0.10; combo kicker +0.05 when RSI and OBV agree
  - Geometry: ±0.15 to A, ±0.20 to E (bull/bear diagonal breaks; S/R retests by sr_conf)
  - EMA trend (confirm only): ±0.05
  - Volume+OBV state: ±0.10 using `vol_state = 0.6·VO_z + 0.4·OBV_z`
  - Residual Δ vs Majors: ±0.10
  - Breadth bias: ±0.05

6) Intent channel deltas (aggregate with caps)
- Channel weights (from LEVER_SPEC/CHEAT_SHEET):
  - High‑Confidence Buy: A +0.25, E −0.10
  - Medium Buy: A +0.15, E −0.05
  - Profit Intent: A −0.15, E +0.15
  - Sell / Negative: A −0.25, E +0.35 (LEVER_SPEC) or stronger variant if configured
  - Mocking / Derision: A −0.10, E +0.10
- Synchrony modifiers:
  - ≥3 curators, spread > 1 d → A +0.05, E −0.05
  - ≥3 curators, spread < 0.5 d → A −0.10, E +0.10
- Clamp TA+intent combined impact per lever to ±0.4.

7) Clamp and discretize
- Clamp A_final/E_final ∈ [0,1].
- mode_display (UI only): patient [0–0.3), normal [0.3–0.7), aggressive [0.7–1].

8) Size now (advice to Trader)
- Immediate target F_now by display mode: 0.10 / 0.33 / 0.50 of DM cap; scale by A_final. Trader converts to actual quantities.

Logging

- reasons[] includes: phase_meso, macro_mult, cut_pressure, rsi_div, obv_div, obv_confirm, sr_break_bull/bear, sr_conf, ema_trend, vol_state, residual_delta, breadth_bias, intent_channels, synchrony.
- Store before/after snapshots for A/E at each major step for audit.

Interfaces (module signatures)

- `pm/lever/policy.py`: `map_phase_to_policy(phase_meso: str, is_new_token: bool) -> tuple[float, float]`
- `pm/lever/macro.py`: `apply_macro_multipliers(a: float, e: float, phase_macro: str) -> tuple[float, float]`
- `pm/lever/cut_pressure.py`: `apply_cut_pressure(a: float, e: float, cut_pressure: float) -> tuple[float, float]`
- `pm/lever/deltas_ta.py`: `apply_ta_deltas(a: float, e: float, features: dict) -> tuple[float, float, list]`
- `pm/lever/deltas_intent.py`: `apply_intent_deltas(a: float, e: float, intent: dict) -> tuple[float, float, list]`
- `pm/lever/finalize.py`: `finalize_levers(a: float, e: float) -> dict{A_final, E_final, mode_display}`

Tests & acceptance

- Unit: verify ordering (policy → macro → cut_pressure → TA → intent → clamp); per‑signal deltas; clamp at ±0.4; invariants (A/E in [0,1]).
- Fixture: phase transitions for each label; intent surge scenarios; geometry break cases; ensure decisions replicate CHEAT_SHEET examples.
- Integration: with Section 4 core engine loop to ensure strands contain expected A/E and reasons[].

Operational notes

- Run at hourly cadence within the PM core loop, with on‑event recompute when phase flips or structure events fire.

### 6) PM Action Mapping (Zones) — Executable Build Plan

Goal

- Convert `(A_final, E_final)` and phase context into concrete add/trim/cut/hold/trail/trend_add actions with precise sizes, ladders, and guards, then emit strands for the Trader.

Scope

- In: `(A_final, E_final, mode_display)`, DM.max_alloc, position state (qty, avg_entry, usd_value, age, cooldown/locks, new_token_mode), features (sr_break/sr_conf, VO_z, RSI_slope), phase labels.
- Out: `ad_strands` entries and position state updates (moon/core, locks, counters).

Inputs (policy constants from specs)

- Entry modes (initial deploy of DM cap): Patient 10%, Normal 33%, Aggressive 50%.
- Dip-add ladders (percent retrace from anchor):
  - Patient: −23.6% / −38.2% / −61.8% with add fractions 23/33/34 of the remaining allocation bucket.
  - Normal: −23.6% / −38.2% with add fractions 33/33.
  - Aggressive: −23.6% / −38.2% with add fractions 23/27 (front‑loaded).
- Exit ladders (percent from average entry): +38.2%, +61.8%, +161.8%, +261.8%, +423.6%, +685.4%, +1089%.
- Exit slice sizing by E_mode (of remaining bag): Patient 10–15%, Normal 20–25%, Aggressive 30–40%.
- Trail stops (profit only): if 15 consecutive 1‑min closes below EMA_long → queue partial exit on first bounce; if no reclaim within 6 bars → demote to Moon.
- Trend‑redeploy fractions (from realized proceeds): Patient 0.10, Normal 0.15, Aggressive 0.25; pre‑checks per Trend Entry spec (Doc Part 4).

Tasks (ordered)

1) Determine action window per tick
- If in cooldown/reentry_lock → only manage exits/trails; suppress new adds.
- If `new_token_mode` → defer to Section 6.1 logic (probe/flip rules), else follow standard mapping below.

2) Compute allowed initial deploy (A‑based)
- target_now = DM.max_alloc × F_mode(A) where F_mode ∈ {0.10, 0.33, 0.50}.
- allowed_size = max(0, target_now − deployed_from_DM_cap) × A_final.
- Create `add` decision if allowed_size ≥ min_order and readiness gates are met for the phase (Dip/Double‑Dip → Wait; others → Active).

3) Manage dip‑add ladders
- Anchor = current average entry or most recent local high/anchor per policy when rebuilding; compute retrace % from anchor.
- If price retrace crosses next ladder and readiness true, schedule `add` with configured ladder fraction; update ladder cursor.

4) Manage exit ladders
- For each unhit exit level above avg_entry: if reached, emit `trim` of slice per E_mode on remaining qty; log level hit and update cursor.
- Maintain FIFO of hit levels to avoid duplicate trims within a bar.

5) Trail logic (profit‑only)
- Track consecutive closes below EMA_long (1m for trail guard, or horizon‑specific if configured).
- On threshold (15 closes): set `trail_pending=true`; when price bounces to EMA zone, emit `trim` and clear pending.
- If no reclaim for 6 bars: demote to Moon (sell 70–90%; keep residual per Moon rules).

6) Trend‑redeploy on harvest events
- On any `trim` from exits/trails: run Trend Entry pre‑checks (sr_break!=bear AND (RSI_slope>0 OR obv_trend>0 OR sr_break==bull) AND (VO_z>0.5 OR OBV_z>0 OR sr_conf≥0.5) AND phase_meso ∈ {Double‑Dip, Oh‑Shit, Recover, Good} AND DeadScore<0.4).
- If pass: size = trend_redeploy_frac(A_mode) × realized_proceeds → emit `trend_add` (re‑add) and merge into position (recompute avg_entry).
- Else: log `no_trend_add`.

7) Core↔Moon lifecycle rules
- Demote → Moon when DeadScore_final > 0.6 OR EMA trend break confirmed with profit.
- Promote → Core when price > EMA_long AND VO↑ AND RSI > 50 AND phase_meso ∈ {Recover, Good} (any two‑of‑three TA + intent acceptable).
- Enforce Moon rules: cap per‑token Moon bag; no adds; only harvest on major pumps.

8) Strand persistence
- Write decisions to `ad_strands` with size_frac relative to DM.max_alloc and reasons[] (signals + phase + cut_pressure + cursors).
- Update position fields: avg_entry on merge, trend_entry_count, cooldowns/locks, last_review_at.

Interfaces (modules)
- `pm/actions/entry.py`: compute initial deploy and dip‑adds; return list[add_decision].
- `pm/actions/exit.py`: manage exit ladders; return list[trim_decision].
- `pm/actions/trail.py`: track consecutive closes, bounce detection, and demotion.
- `pm/actions/trend_redeploy.py`: pre‑checks and redeploy sizing.
- `pm/actions/lifecycle.py`: core↔moon transitions.
- `pm/actions/emit.py`: persist `ad_strands`, update `positions`.

Tests & acceptance
- Unit: ladder crossing correctness; slice sizing per E_mode; trail pending/clear; redeploy gate logic.
- Fixture: scenarios covering Dip→Recover adds, Good/Euphoria exits, trail breach + bounce, demotion/promotion.
- Integration: verify that cumulative size respects DM cap; avg_entry recomputes correctly; decisions match templates across phases.

Operational notes
- Minimum order sizes handled by Trader; Actions layer supplies fractional `size_frac` only.
- All strands include phase snapshot and `cut_pressure` for audit/learning.

### 6.1) New Token Entry Mode — Executable Build Plan

Goal

- Safely discover tape quality for brand‑new tickers with a small probe, then flip fast to build sizing when structure/volume confirm, or exit on strength if structure breaks.

Scope

- In: DM signal with `is_new_token=true`, live features (VO_z, RSI, sr_break/sr_conf, EMA trend, micro stability), phase context, cut_pressure.
- Out: probe/add/trim/trail/demotion strands; `positions.new_token_mode` state updates.

Activation

- Trigger: `is_new_token=true` from DM.
- Set mode state: `new_token_mode=true` and start `observation_start_time`.

Probe sizing & levers

- Initial probe: `size_frac = 0.10 × DM.max_alloc`.
- Levers: A=0.20 (Patient), E=0.80 (Aggressive) on a probe sleeve only (avoid scalping build move).

Observation window

- Duration: 5–15 minutes on 1m bars; evaluate once per minute.
- Required inputs per bar: VO_z, RSI_1m/5m, EMA_short/long, `sr_break`/`sr_conf`, price stability, slippage/spread estimate.

Flip to Build (escalation)

- Condition: any 2 of 4 sustained for ≥3 consecutive minutes:
  1) Volume/structure: `VO_z ≥ +1.0` OR `sr_break == 'bull'`.
  2) Momentum: `RSI > 50 and rising` OR `obv_trend > 0`.
  3) Trend confirm: `close > EMA_long` OR diagonal reclaim OR `sr_break == 'bull'`.
  4) Micro stability: `|price − entry| ≤ 5%` after initial thrust.
- Action on flip:
  - Set levers for build sleeve: `A → 0.8`, `E → 0.4`.
  - Execute build adds on first controlled pullback: −23.6%, then −38.2% from local high/anchor.
  - Set `new_token_mode=false` after first build add.

Failure path (no confirmation)

- Stay in probe; protective exit only on structure break:
  - Mark `trend_break=true` after 15 consecutive 1m closes below EMA_long.
  - Do not dump into flush; queue a trim on first bounce to EMA zone.
  - If no reclaim within 6 bars, demote to Moon (sell 70–90%).

Trend‑add rules (while mode active)

- Allow when flip conditions met OR (Recover/Good and diagonal reclaim).
- Ladder gating by volume/structure:
  - −23.6%: `VO_z > 1.0` (Normal/Aggressive only)
  - −38.2%: Structure intact + `VO ≥ 1.0` (all modes)
  - Never average down in pure chop (EMA_short < EMA_long AND RSI slope < 0).

Guards

- Liquidity: if average spread > 3% OR effective slippage > 3% → keep probe size and do not flip.
- Herd burst: if ≥3 curators mention within <30 min and VO not confirming → pause flip.
- Macro hostility: if Macro rolling over sharply, require trend confirm + VO_z.

Persistence & logging

- Update `positions.new_token_mode` flag and `observation_start_time`.
- Emit strands: `add_probe`, `flip_build`, `hold_probe`, `trim_on_bounce`, `demote_moon` with reasons[].

Interfaces (modules)

- `pm/new_token/mode.py`: state machine for probe/flip/failure.
- `pm/new_token/observe.py`: compute window tests each minute.
- `pm/new_token/actions.py`: flip/build adds and failure exits; write strands and update state.

Tests & acceptance

- Unit: 2/4 sustained tests logic; 15‑close trend break; flip demotion rules.
- Fixture: (a) Confirmed flip: meets 2/4 for 3 min → adds −23.6/−38.2; (b) Failed structure: 15 closes below EMA_long → trim on bounce → demote in 6 bars; (c) Liquidity guard blocks flip.
- Integration: 60‑minute replay with mode transitions; strands reflect reasons and state changes; no duplicate flips.

### 7) Portfolio Bands & Rotation — Executable Build Plan

Goal

- Keep the portfolio around the healthy core range (~33) by selecting trims intelligently when crowded and unlocking expansion when underexposed, while respecting phase bias and rotation.

Scope

- In: `positions` (core/moon flags, usd_value, pnl, age), latest `phase_state` (meso), `portfolio_bands` (cut_pressure), features (breadth_z, residual_vs_majors, VO_z, intent metrics), rotation signals (S_rotation, S_port_alt).
- Out: updated `portfolio_bands` (core_count), ranked trim recommendations and EPS diagnostics for learning.

Inputs

- Core band thresholds: Underexposed < 12, Target 12–26, Soft Over 26–36, Hard Over > 36.
- EPS components and weights:
  - Overextension Z: 0.45 (phase bias +0.3 in Dip/Double‑Dip)
  - Residual Weakness: 0.25 (phase bias +0.3 in Recover/Good/Euphoria)
  - (1 − Intent Strength): 0.15
  - Stale Age Z: 0.10
  - Low VO: 0.05

Outputs

- Ranked list of positions with EPS scores and suggested trim slices (per E_mode rules).
- Updated `portfolio_bands.core_count` each evaluation.

Tasks (ordered)

1) Compute portfolio structure & state
- Count current Core bags; write `core_count` into `portfolio_bands`.
- Determine band: under, target, soft over, hard over.

2) Build EPS for each Core position
- Compute components per position using cached features in `positions.features` and recent price stats (z-standardize where relevant per Appendix A).
- Apply phase biases:
  - If meso ∈ {Dip, Double‑Dip}: increase weight on OverextensionZ by +0.3.
  - If meso ∈ {Recover, Good, Euphoria}: increase weight on Residual Weakness by +0.3.
- EPS = 0.45·OverextensionZ + 0.25·ResidualWeakness + 0.15·(1−intent_strength) + 0.10·StaleAgeZ + 0.05·LowVO + phase_bias.

3) Select trims when crowded (cut_pressure > 0.2 or band ≥ Soft Over)
- Sort Core positions by EPS descending.
- Compute required notional to trim: target toward ~33 cores; if EPS ties, prefer profitable and smaller USD first.
- Emit trim recommendations using Section 6 sizing (E_mode slice of remaining bag); stop when target achieved.

4) Expansion when underexposed (band < 12)
- No forced trims; mark readiness to expand: allow adds via Section 6 based on A_mode with priority to positions showing S_port_btc/S_port_alt > 0 and intent up.

5) Rotation nuance (when S_rotation > +0.8 and S_port_alt strong)
- If rotation_on and residual_alt < 0: raise selection priority of alt‑cohort positions meeting VO/RSI gates; deprioritize trims on those unless Meso Euphoria.

6) Emit plan to Actions
- Provide the ranked trim list with suggested slice sizes to Section 6; include EPS diagnostics in reasons[].

Interfaces (modules)
- `pm/bands/eps.py`: compute EPS per position and return sorted list.
- `pm/bands/select.py`: choose trims based on band, cut_pressure, and target core count.
- `pm/bands/emit.py`: pass recommendations to Actions layer.

Tests & acceptance
- Unit: EPS component correctness, phase bias application, deterministic ranking.
- Fixture: crowded portfolio (e.g., 38 cores) → trims chosen from overextended/stale first; underexposed (e.g., 10 cores) → no trims.
- Integration: tick with cut_pressure > 0.2 produces trim recommendations; Section 6 executes; core_count trends toward target.

Operational notes
- This section recommends; Section 6 executes and persists.
- Log EPS components alongside decisions to enable learning analysis later.

### 8) Event Bus & Triggers — Executable Build Plan

Goal

- Deliver low-latency, idempotent signals to PM components on key state changes without introducing new durable tables. Durability is provided by existing state tables (`phase_state`, `portfolio_bands`, `ad_strands`).

Scope

- In-process event dispatcher with typed payloads; no external broker required. Emission happens alongside writes to existing tables.
- Subscribers: PM Core (Section 4), Actions (Section 6), SPIRAL writer (Section 3).

Event types (sources → subscribers)

- phase_transition {token, horizon, prev, next, score, diagnostics}  (SPIRAL → PM Core)
- rotation_tilt_on/off {token, meso_score, S_rotation}               (SPIRAL → PM Core)
- dominance_early_rise/peak_roll {btc/usdt diagnostics}               (SPIRAL cut-pressure → PM Core)
- sr_break_detected/retest/reject {token, tf, sr_conf, side}          (Geometry → PM Core/Actions)
- ema_trail_breach {token, consec_closes}                              (Trail monitor → Actions)
- band_breach {core_count, band}                                       (Bands calc → Actions)
- decision_approved {strand_id}                                        (Actions → external listeners)
- new_token_signal / flip_conditions_met / probe_timeout               (New token mode → Actions)
- time_gate_expired {position_id, gate}                                (Patience/reentry locks → Actions)

No new tables

- phase transitions are durable via appended rows in `phase_state`.
- dominance/rotation diagnostics are durable via `portfolio_bands` writes.
- decisions are durable via `ad_strands`.

Dispatcher design

- Synchronous in-process publish/subscribe with simple topic registry.
- Each emit returns an idempotency key (event_type + primary keys + ts bucket) to prevent duplicate handling in the same tick.
- Debounce window: 1–2 seconds to collapse noisy micro-events (e.g., repeated structure checks).

Interfaces (modules)

- `pm/events/bus.py`
  - `subscribe(event_type: str, handler: Callable) -> None`
  - `emit(event_type: str, payload: dict, idem_key: str | None = None) -> None`
  - `with_debounce(event_type: str, key_fn: Callable, ms: int)` (decorator)
- `pm/events/types.py`: Typed payload dataclasses for each event.

Emit points (integration)

- Section 3 (SPIRAL writer): after writing a new phase label different from prior → emit `phase_transition`; on tilt gate flip → emit `rotation_tilt_on/off`; on dominance inflection → emit `dominance_*`.
- Section 6 (Actions): on trail threshold → emit `ema_trail_breach`; after writing a strand → emit `decision_approved`.
- Bands calc: when `core_count` crosses thresholds → emit `band_breach`.
- New token mode: emit `new_token_signal`, `flip_conditions_met`, `probe_timeout` as the state machine advances.
- Time gates: when patience/lock timers expire → emit `time_gate_expired`.

Ordering & idempotency

- Handlers must be pure and idempotent. Use idem_key to skip duplicates within the same tick.
- Ordering rule of thumb: phase_transition → (bands/rotation) → actions; the PM Core loop coalesces multiple events into a single recompute if they land within the same second.

Tests & acceptance

- Unit: bus subscribe/emit/debounce/idempotency; typed payload validation.
- Integration: simulate rapid `phase_transition` + `sr_break_detected` and assert a single PM recompute; verify `decision_approved` fires once per strand.

Operational notes

- Heartbeat: 1m data acts as the base cadence; events can trigger immediate recompute outside the hour.
- Observability: counters per event_type, last_emit_ts, dropped_duplicates, debounce_hits.

### 9) Strands & Logging — Executable Build Plan

Goal

- Persist every PM decision with full causal trace for audit and learning; backfill forward PnL; keep volume manageable while retaining critical context.

Scope

- In: computed `(A_final, E_final)`, decision type and size, reasons[], phase snapshot, cut_pressure, EPS (when applicable).
- Out: strand rows in `ad_strands`, plus forward PnL backfill fields; lightweight metrics.

Schema (reuse `ad_strands`)

- Columns (ensure exist):
  - token TEXT, ts TIMESTAMPTZ
  - decision_type TEXT  -- add | trim | cut | hold | trail | trend_add | demote | promote | add_probe | flip_build | hold_probe | trim_on_bounce
  - size_frac DOUBLE PRECISION  -- fraction of DM.max_alloc used (+ for adds; for trims a fraction of remaining bag per E_mode)
  - a_value DOUBLE PRECISION, e_value DOUBLE PRECISION
  - reasons JSONB  -- ordered list of {name, value, before, after} and any diagnostics
  - phase_state JSONB  -- {macro, meso, micro, scores, confidence, dwell_remaining}
  - forward_pnl_24h DOUBLE PRECISION NULL, forward_pnl_72h DOUBLE PRECISION NULL
  - eps_score DOUBLE PRECISION NULL
  - trend_redeploy_frac DOUBLE PRECISION NULL
  - new_token_mode BOOLEAN DEFAULT FALSE

Reasons[] contents (by source)

- Phase: phase_meso, macro_mult, cut_pressure, rotation_tilt_state
- TA/structure/volume: rsi_div, obv_div, obv_confirm, ema_trend, vol_state, sr_break_bull/bear, sr_conf, sr_retest/sr_reject, residual_delta, breadth_bias
- Intent: channel hits (hi_buy/med_buy/profit/sell/mock), synchrony modifiers
- EPS: components for trimmed positions (overextension_z, residual_weakness, 1−intent, stale_age_z, low_vo)

Forward PnL backfill

- Job: `strands_backfill_pnl` runs hourly; for strands with NULL pnl fields and age ≥ 24h/72h, compute realized/mark-to-market PnL from price data and fill.
- For adds, compute mark-to-market; for trims/trail/trend_add, compute realized component where applicable.

Tasks (ordered)

1) Strand writer (Section 6 integration)
- Build the reasons[] deterministically in the order of operations; include before/after snapshots for A/E at each major step.
- Attach phase snapshot and cut_pressure.
- Write to `ad_strands`; emit `decision_approved`.

2) PnL backfill job
- Query strands with NULL forward_pnl_24h/72h and ts < now()−24h/72h; compute pnl using 1m close-to-close over the horizon; write back.

3) Metrics
- Counters: strands_written, pct_with_pnl24/pnl72, avg_reasons_len, avg_A/E, add_vs_trim_ratio.
- Timing: median write latency.

Interfaces (modules)
- `pm/strands/write.py`: `write_strand(token, decision, a_value, e_value, size_frac, reasons, phase_snapshot, extras) -> id`
- `pm/strands/pnl_backfill.py`: `backfill_pnl(now: datetime) -> int`

Tests & acceptance
- Unit: reasons[] canonical order and required keys present; strand serializer.
- Fixture: craft decisions across all types; verify reasons and snapshots; ensure backfill computes non-null pnl when data present.
- Integration: hourly loop writes strands; backfill fills pnl; metrics updated.

Operational notes
- Storage: reasons and phase_state can be pruned to only include keys listed above to control payload size.
- Retention: keep `ad_strands` indefinitely; optionally archive older strands if size becomes an issue.

### 10) Integration Points — Executable Build Plan

Goal

- Wire all subsystems end‑to‑end with clear data flow, schedules, and contracts; ensure idempotent operation and observability.

Scope

- In: running jobs/modules from Sections 1–9.
- Out: reliable 1m heartbeat, hourly compute, on‑event recompute, and strands with forward PnL.

Runtime components (processes)

- Ingest
  - `hyperliquid_ws_ticks` (continuous 1m heartbeat via ticks) → `majors_trades_ticks`
  - `ticks_to_1m_rollup` (each minute :00–:02) → `majors_price_data_1m`
  - `price_ingest_1m_lowcaps` (existing) → `lowcap_price_data_1m`
- SPIRAL
  - `features_compute_1h` (hourly on the hour; on‑event allowed)
- PM Core
  - `pm_core_tick` (hourly + on `phase_transition`/`sr_break`/`band_breach`)
  - `pm_actions` (called by core) → strands
- Bands & rotation
  - `bands_calc` (hourly; computes core_count, EPS list)
- Backfill/maintenance
  - `strands_backfill_pnl` (hourly)
  - optional: MV refresh jobs for `v_price_{5m,1h,1d}` if enabled
- Event bus
  - in‑process dispatcher in PM process; Section 8 API

Data flow (happy path)

1) Ticks → 1m majors bars; lowcaps already 1m
2) `features_compute_1h` reads 1m bars + positions → r_btc, r_alt, r_port → streams → lens scores → phase scores → writes `phase_state` and emits `phase_transition/rotation_tilt_*`
3) `bands_calc` updates `portfolio_bands.core_count` and prepares EPS ranking
4) `pm_core_tick` reads latest `phase_state` + `portfolio_bands.cut_pressure` + positions/features → computes `(A_final,E_final)` (Section 5) → `pm_actions` (Section 6) emits `ad_strands`
5) `strands_backfill_pnl` fills forward PnL; dashboards consume strands/metrics

Schedules (UTC)

- 1m: ticks ingest, rollup to 1m, trail monitors
- Hourly at :00: features_compute_1h, bands_calc, pm_core_tick, strands_backfill_pnl
- On‑event: immediate pm_core_tick coalesced within 1–2 s via bus debounce

Configuration (env)

- SUPABASE_URL, SUPABASE_KEY, SUPABASE_DB_PASSWORD
- HL_WS_URL (and/or REST backfill URL); HL_SYMBOLS="BTC,ETH,BNB,SOL,HYPE"
- JOB_CONCURRENCY, BACKOFF_BASE_MS, MAX_RETRIES
- LOG_LEVEL, METRICS_PUSH (if applicable)

Idempotency & retries

- Upserts with PKs on `(token, ts)` for 1m bars and `(token, ts, trade_id)` for ticks
- Event bus emits with idem_key; PM coalesces recompute per second
- Jobs retry with exponential backoff; skip duplicate strands by (token, ts, decision_type, idem_key)

Observability

- Metrics: ingest_lag_s, bars_written/updated, phase_flip_rate, avg_dwell_h, cut_pressure, strands_written, pct_with_pnl24/72
- Logs: snapshot objects on flips and decisions with reasons[]; warn on stale features > 2 h

Tests & acceptance (E2E)

- Dry‑run 24 h replay: phases stable, no invalid skips; strands produced with correct A/E and reasons[]
- Live smoke: verify 1m heartbeat, hourly jobs fire, events coalesce, and strands PnL backfill fills within 1 hour windows

### 11) Ops & Dashboards — Executable Build Plan

Goal

- Expose live operational status, risk posture, and decision traces to operators; surface alerts on lag, instability, or rule violations.

Scope

- In: metrics/logs/events from Sections 1–10; selected DB views.
- Out: dashboards (status, risk, phases, strands), alerts, and runbooks.

Dashboards (widgets)

- Live status: current Macro/Meso/Micro per token, scores, confidence, dwell_remaining, pending_label.
- Portfolio posture: cut_pressure (with components), core_count bands, EPS top‑N candidates, A/E distributions.
- Ingest & stability: ingest_lag_s, bars_written/updated, phase_flip_rate, avg_dwell_h, invalid_skip_count (=0 target).
- Decisions: last 50 strands with reasons[], A/E before/after, mode_display, size_frac; forward_pnl placeholders.
- Rotation: S_rotation and S_port_alt summaries; rotation_on status.

Alerts (thresholds)

- ingest_lag_s > 120s (critical), > 60s (warning)
- phase_flip_rate > 2× baseline over 24h (warning)
- avg_dwell_h < 50% of spec (warning)
- dominance early‑rise (USDT.D) for > 2 hours (info → tighten ops focus)

Views/queries

- v_phase_latest: per token latest phase rows joined (macro/meso/micro) with scores.
- v_strands_recent: last 24h strands with reasons size.
- v_posture: current cut_pressure + components + core_count.

Runbooks

- Ingest lag: check WS connectivity, backfill windows; escalate if lag > 10 min.
- Flip storm: verify data sanity, skip rules, dominance inputs; consider raising hysteresis temporarily.
- Strand write errors: retry queue, reduce batch size, disable nonessential events.

### 12) Testing & Rollout — Executable Build Plan

Goal

- Validate correctness and stability across units, integration, and live canary; ship safely with rollback gates.

Scope

- In: code from Sections 1–11; test data; replay harness.
- Out: pass/fail signals, rollout plan, and rollback procedures.

Tests

- Unit: math kernels (EMA/slope/curvature/z), labeler (bands/hysteresis/dwell/skip), lever ordering and clamping, actions ladders/trail, event bus idempotency, strand writer.
- Fixtures: curated scenarios—Recover→Good, Euphoria→Dip, rotation tilt on/off, trend_add gates, new_token flip/failure, EPS trimming.
- Integration replay: 7 days of 1m bars; assert dwell targets, zero invalid skips, and stable outputs.

Rollout

- Stage 1: shadow mode (no trades), full strands logging, alerts on; 48h.
- Stage 2: canary subset of tokens (e.g., 5 cores) with reduced size caps; 48–72h.
- Stage 3: expand to full set; monitor metrics and flip/dwell for 1 week.

Gates & rollback

- Gate: ingest_lag_s < 60s; invalid_skip_count = 0; flip_rate within ±50% of baseline; no strand write errors > 0.1%.
- Rollback: disable PM core tick and actions; keep strands in shadow; revert parameters to prior set.

### 13) Learning Hooks (Future) — Executable Build Plan

Goal

- Prepare artifacts and signals for future weight tuning and behavioural optimization without changing live logic now.

Scope

- In: strands with reasons and forward PnL; phase_state history; EPS outcomes.
- Out: datasets and knobs ranges for a separate offline learner.

Artifacts & features

- Dataset 1: phase snapshot → forward PnL attribution of A/E decisions; per‑lever deltas and outcomes.
- Dataset 2: rotation states (S_rotation, S_port_alt, residual_alt) → success of rotation‑aligned adds/exits.
- Dataset 3: EPS recommendations → realized trims and subsequent PnL.

Knob ranges (bounded as per Appendix C)

- Lens weights: Macro {S_btcusd 0.4–0.7, S_rotation 0.2–0.5}; Meso {S_port_btc 0.4–0.6, S_port_alt 0.2–0.5}.
- Rotation tilt thresholds: z ∈ [0.6, 1.0], dwell ∈ [6h, 12h].
- Dominance deltas: BTC.D ±[0.03,0.08]; USDT.D ±[0.08,0.15]; clamp ±[0.15,0.20].
- Hysteresis gap: ±[0.15,0.30]; n_tf/k_tf/L_H per Appendix A.

Evaluation metrics

- Stability: dwell length vs spec; invalid skip count; flip variance.
- Performance: forward PnL (24h/72h) conditioned on phase and lever changes.
- Interpretability: weight ranges stay within bounds; label distribution sanity.

Deployment of learned params

- Monthly update cadence; log param diffs with checksum and training window.
- Auto‑rollback to prior params if flip rate > 2× baseline over 7 days.

### 14) Implementation Roadmap & Folder Layout

Folder layout (new top-level module)

```
src/pm/
  ingest/           # HL WS + rollup
    hyperliquid_ws.py
    rollup.py
  spiral/           # SPIRAL math
    returns.py
    lenses.py
    phase.py
    geometry.py
    dominance.py
    persist.py
  core/             # PM core compute
    context.py
    modes.py
    apply_signals.py
  actions/          # mapping to decisions
    entry.py
    exit.py
    trail.py
    trend_redeploy.py
    lifecycle.py
    emit.py
  bands/            # EPS & selection
    eps.py
    select.py
    emit.py
  events/
    bus.py
    types.py
  strands/
    write.py
    pnl_backfill.py
  jobs/             # schedulable entrypoints
    features_compute_1h.py
    bands_calc.py
    pm_core_tick.py
  tests/
    unit/
    fixtures/
    integration/
```

Feature flags (env)

- PM_SHADOW=true|false (default true)
- PM_CANARY_SYMBOLS="BTC,ETH" (empty = none)
- EVENTS_ENABLED=true|false (default true)
- ACTIONS_ENABLED=true|false (default false)
- TREND_REDEPLOY_ENABLED=true|false (default false)

Rollout steps (execute sequentially)

1) Migrations — DONE
- Created: `majors_trades_ticks`, `majors_price_data_1m`, `phase_state`, `portfolio_bands` (incl. nav_usd and dominance diagnostics). Apply DDL to Supabase next.

2) Ingest heartbeat — DONE
- `hyperliquid_ws.py` writes direct 1m majors bars to `majors_price_data_1m` (ticks optional via SAVE_TICKS). Quote volume validated.

3) SPIRAL (shadow)
- Run `jobs/features_compute_1h.py`; write `phase_state`; emit `phase_transition`.

4) PM Core (shadow)
- Run `jobs/pm_core_tick.py`; compute `(A_final,E_final)`; write `ad_strands` only.

5) Actions (canary)
- Enable `ACTIONS_ENABLED=true` and `PM_CANARY_SYMBOLS` for 3–5 tokens; execute adds/trims/trails.

6) Expand to all
- Lift canary; enable trend redeploy if desired; monitor dashboards.

7) Ops & dashboards
- Deploy widgets, alerts; review metrics weekly; plug into Learning (Section 13) later.

\

### Appendix — Implementation Checklist (to date)

- Database & schema
  - Created `majors_trades_ticks` (raw HL ticks) [optional use]
  - Created `majors_price_data_1m` (canonical 1m majors OHLCV)
  - Created `phase_state` (per horizon with lens diagnostics)
  - Extended `portfolio_bands` with dominance diagnostics and raw levels `btc_dom_level`, `usdt_dom_level`
  - Extended `lowcap_positions` with PM fields: `features` JSONB + indexes; cooldown/locks/counters/new_token_mode

- Ingest & data cadence
  - Implemented Hyperliquid WS ingester with direct 1m aggregation; optional tick persistence via `SAVE_TICKS=1`
  - Standardized on 1m canonical; higher TFs to use SQL views/MVs later (optional)

- Jobs (wired into run_social_trading scheduler)
  - `nav_compute_1h`: computes and upserts `portfolio_bands.nav_usd`
  - `dominance_ingest_1h`: fetches BTC.D/USDT.D, computes diagnostics, writes to `portfolio_bands`
  - `features_compute_1h`: SPIRAL features and phase writes (portfolio-level for now), context features to positions
  - `geometry_build_daily`: builds S/R levels and diagonals per token daily
  - Scheduler offsets: :02 NAV, :03 Dominance, :04 Features, :05 PM core, :10 Daily geometry

- Geometry
  - Daily builder persists levels/diagonals under `positions.features.geometry`
  - Per-minute tracking moved to `trading/position_monitor.py` (sr_break/diag_break/conf updates)
  - Hourly geometry tracker disabled by default

- SPIRAL (v1.1/1.2 alignment)
  - Four-lens computation and horizon blends implemented (portfolio-level: token='PORTFOLIO')
  - Band mapping, hysteresis, dwell, skip rules (no Recover→Double-Dip)
  - Phase state persistence with lens diagnostics

- Event bus
  - In-process emitter (`events/bus.py`) available; `phase_transition` emitted on flips

- PM Core & Actions
  - `pm_core_tick` added and scheduled; currently computes A/E from Meso policy and cut_pressure (shadow/guarded)
  - Actions mapper v1 implemented (gated by `ACTIONS_ENABLED`):
    - Adds require phase readiness (Recover/Good/Euphoria) + confirmation (sr/diag bull or confidence)
    - Trims on structure breaks (sr/diag bear); E scales slice size
  - Hourly price fetch removed; ladder/trail detection is per-minute in the monitor

- Docs updates
  - Clarified 1m canonical ingest, HL direct 1m aggregation, optional ticks, and geometry split (daily build + monitor)
  - Noted portfolio-level SPIRAL scope with geometry consumed from features

- Status gates
  - ACTIONS are disabled by default (`ACTIONS_ENABLED=0`) pending lever engine completion and canary enablement
