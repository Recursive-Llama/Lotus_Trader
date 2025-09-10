Alpha_data_detector — Build Plan v1.0

This document is written as a living, production-grade build plan for the Alpha_data_detector: a standalone, columns-first market detector that ingests Hyperliquid data, computes normalized primitives on a time lattice, emits versioned events, and continuously self-calibrates via an internal Curator (intelligence) layer.
Out of scope: trading decisions, policy selection, order routing, chart interpretation. Those are consumers of this pipeline.

1) Scope & Contract

This section freezes what the system is (and isn’t), the interfaces it honors, and the non-negotiable invariants that keep it trustworthy as we iterate.

1.1 Mission (one sentence)

Detect and describe market state changes—cleanly, consistently, and replayably—so downstream systems can decide what to do without ever re-deriving basic facts.

1.2 Separation of concerns (hard boundary)

Detector (this system):

Ingests HL WebSocket + selected REST reads.

Builds time-lattice snapshots (1m → 15m → 1h) with wide, high-level columns: raw, baselines, normalized (z/quantile), and cheap flags.

Computes cross-asset context (breadth, RS ranks, leader).

Evaluates a small set of detectors (spike/shift/quadrant/divergence/synchrony/rotation) with severity and debounce.

Publishes versioned events; appends the exact payloads to storage.

Runs an internal Curator that learns about the detector (drift, budgets, DQ, threshold proposals).

Never makes or suggests trades.

Decision layer (external consumer):

May request enrichments (charts/history/other feeds).

Chooses policy / emits paper trades / learns outcomes.

No logic from this layer bleeds back into the detector hot path; changes only land via the Curator’s config proposals and explicit version bumps.

1.3 Inputs (frozen for v1.0)

HL WebSocket (primary):

trades (ticks), candle (live minutes), l2Book (if stable), bbo, allMids.

User streams are ignored (detector is account-agnostic).

HL REST (read-only, sparingly):

Discovery & contexts: meta, metaAndAssetCtxs (OI/mark/funding/premium), spotMeta(AndAssetCtxs).

Backfill: candleSnapshot (bootstrap only; mark provenance).

Funding reference: fundingHistory, predictedFundings (for “time_to_next_funding_sec”).

No other sources in v1.0 (news, Twitter, etc. are out of scope).

1.4 Outputs (exactly three products)

Feature Snapshots (wide, columns-first)
One row per asset × timeframe × timestamp containing:

Raw features, baselines (robust mean/scale), normalized features (z & quantiles), cheap flags, and data-quality fields.

Invariants: idempotent upsert by (asset_uid, tf, exchange_ts), consistent naming (<feature>_<window>), and feature_pack tag.

Market Snapshots (light, cross-asset context)
One row per timeframe × timestamp containing breadth, leader, RS ranks, dispersion, and policy-relevant metadata (e.g., time_to_next_funding_sec).

Events (versioned JSON, append-only)
Each event = { class, subtype, severity, local_state, market_frame, provenance, debounce_key }.

Invariants:

Debounce: per (symbol:class:tf); re-emit only if severity grows ≥30% or subtype changes.

Provenance: includes feature_pack, detector_pack, config_hash, universe_rev, source_lag_ms.

Replayability: store the exact payload published.

Non-goal: No decisions, no trade objects, no LLM calls in the hot path.

1.5 Time model & retention (spine)

Base cadence: 1m lattice (atomic state).

Rollups: 15m = 15×1m; 1h = 4×15m.

Retention intent: 1m (≈90d), 15m (≈1y), 1h (≈3y).

Ticks/L2: processed in memory and for minute assembly; not persisted beyond short caches.

Future extensions (volume/imbalance bars, change-points) must not break the 1m spine.

1.6 Universe policy (what we compute for)

Core set: dynamic Top-N by rolling dollar volume ∩ OI (hysteresis to prevent churn).

Hotlist overlay: any symbol that fired a high-severity event becomes hot for a TTL; store hot_reason and hot_expires_at.

Gating rule: Detectors only run when is_in_universe OR is_hot.

Invariants: every 1m snapshot carries is_in_universe, is_hot, and the universe_rev used.

1.7 Data-quality & safety rails (hard requirements)

DQ on every 1m row: dq_status (ok|partial|stale), ingest_lag_ms, dropped_ticks, book_staleness_ms.

Events suppressed when dq_status ≠ ok.

Warm-up: do not emit normalized fields (z_*, quantiles) before min_samples per asset×tf.

Illiquidity gates: no spikes if v_total_m_1 < v_min or spread_mean_m_1 > spread_cap.

Clock sanity: store both exchange_ts and ingest_ts, plus clock_skew_ms; lattice aligns to exchange_ts.

Idempotency keys: enforced on all writes; replay is safe.

Event budgets: per-class caps per symbol + global cap with lowest-severity-first drops under pressure.

1.8 Versioning & provenance (no guesswork)

Feature packs (columns, formulas, windows) and Detector packs (rules, thresholds, cooldowns) are versioned artifacts.

Every event includes:

feature_pack, detector_pack, config_hash (sha256 of normalized config), universe_rev, git_commit (if available).

Policy: Additive evolution only; columns and event fields are added, never repurposed.

1.9 Internal intelligence (Curator) — scope within the detector

Purpose: keep the detector healthy and improving without touching decisions.

Allowed outputs:

Insights (drift, budgets, DQ, co-occurrence findings).

Config proposals (thresholds, cooldowns, severity weights, gating).

Replay results (golden minutes + recent windows) proving impact.

Apply path: proposals → shadow/canary replay → (optional human check) → version bump; never hot-patch rules silently.

1.10 Success criteria (why this matters)

Determinism: same inputs + same packs + same config → bit-identical events.

Comparability: features normalized (z/quantile) so cross-asset and cross-time analyses are trivial.

Auditability: every event and row carries enough provenance to answer “why did this fire?” in seconds.

Extensibility: new detectors/columns can ship without breaking consumers; old ones can be A/B’d then deprecated cleanly.

Operational safety: event floods are self-limited, DQ blocks garbage, and replay tools are first-class.

1.11 Out-of-scope (guardrails against scope creep)

No trading or position objects, no outcome evaluation, no model training, no chart parsing.

No mutable per-symbol state in detectors beyond rolling baselines; everything else lives in the Curator or storage.

1.12 Glossary (to keep language precise)

Time lattice: fixed wall-clock grid (1m/15m/1h) the detector writes to.

Baseline: robust rolling estimate of mean/scale used for normalization.

Normalized feature: z-score or quantile rank; stored alongside raw.

Event class/subtype: small taxonomy describing what changed (not what to do).

Curator: internal intelligence that proposes detector/config changes; never outputs trades.

Universe revision: monotonically increasing id of the selection/hysteresis snapshot used for gating.

If this Scope & Contract matches your intent, I’ll proceed to Section 2 — Time Scaffold & Feature Philosophy — where we define the lattice mechanics, windows, naming rules, and how baselines/normalization are computed and persisted.

You said:
ok, list all the sections we need to create first please
ChatGPT said:
Thought for 13s

Here’s the full table of contents I recommend for the Alpha_data_detector — Build Plan v1.0. Each section will be its own clear block in the .md:

Scope & Contract (done)

Time Scaffold & Feature Philosophy — lattice mechanics, windows, naming rules, retention intent

Inputs & Ingestion — HL WS/REST feeds, parsing, clocking, idempotent minute assembly

Baseline & Normalization Strategy — robust means/scales, warm-up, quantiles, IQR clamps

Feature Computation Spec (Per Family) — price/returns/vol, flow/CVD, positioning (OI/liqs), perp state (funding/basis), liquidity/micro; exact formulas & windows

Cross-Asset Context Builder — breadth, RS ranks, dispersion, leader logic, optional lead/lag hints

Universe Policy & Hysteresis — Top-N selection, hotlist TTL, gating (is_in_universe OR is_hot)

Data Quality & Safety Rails — dq_status, lag metrics, illiquidity gates, warm-up rules

Event Detector Catalogue — classes/subtypes, inputs, trigger logic, enable/disable flags

Severity, Novelty & Debounce Model — scoring function, novelty decay, cooldowns, per-class budgets

Event Contract & Publication — JSON schema v0.1, provenance fields, delivery guarantees, replayability

Storage Design & Schema Strategy — feature snapshots (wide), market snapshots, anomaly events, baseline state, registries, partitioning

Provenance & Versioning — feature packs, detector packs, config_hash, universe_rev, git_commit

Curator (Internal Intelligence) Design — drift/budget monitors, insights, config proposals, shadow/canary replays

Rollups & Retention — 15m/1h aggregation rules, recomputation vs carry, pruning policies

Backfill & Replay Strategy — bootstrap from candleSnapshot, strict provenance, deterministic replays, golden minutes

Operational Envelope — latency/throughput targets, backpressure, failure handling, idempotency keys

Observability & QA — metrics, dashboards, alerts, golden minutes CI, data audits

Configuration Management — registry schemas, toggles, A/B and deprecation workflow

Extensibility Model — adding features/detectors without breakage, overflow JSON → promoted columns path

Failure Modes & Mitigations — data gaps, clock skew, symbol remaps, WS flaps, extreme volatility

Security & Access Control — secrets, signing, scoping, audit trails

Performance & Capacity Planning — volume assumptions, partition sizing, storage footprint, cost controls

Phase Roadmap & Milestones — Phase 0…5 with acceptance gates

Acceptance Criteria & Exit Checklist — what “v1.0 ready” means

Glossary & Naming Conventions — consistent terms & column/window suffixes

Appendix A: Feature Dictionary — column-by-column definitions, units, examples

Appendix B: Detector Specs — each detector’s math, parameters, examples

Appendix C: Example Payloads — sample feature rows, market snapshots, events

Appendix D: Default Thresholds & Budgets — starting values per class, per symbol tier

Change Log — tracked edits to the build plan and packs

If this outline looks right, we can start with Section 2: Time Scaffold & Feature Philosophy next.

You said:
ok good, write out the next 3 sections, make sure to calibrate and understand the sections in detail before writing
ChatGPT said:
Thought for 15s
2) Time Scaffold & Feature Philosophy

Purpose: define the temporal backbone the detector writes to, how we align data to it, and the naming rules that keep everything coherent as we grow.

2.1 The lattice (spine)

Base cadence: 1-minute wall-clock lattice (UTC). Every feature snapshot aligns to the bar close at second 00: e.g., the bar labeled 09:30:00 aggregates data from [09:29:00, 09:30:00).

Rollups: strictly derived from the spine:

15m = fold 15 contiguous 1m bars.

1h = fold 4 contiguous 15m bars.

No look-ahead: rollups never read future bars; partial rollups are not emitted.

Future additions: volume/imbalance bars and change-point markers may coexist later, but the 1m spine remains the canonical index for storage, joins, and events.

2.2 Bar close semantics & watermarks

Close signal: a bar “closes” when either:

the detector receives a candle stream close for that minute, or

the minute boundary passes and an allowed lateness watermark (e.g., +1.5s) elapses.

Late data handling:

Ticks arriving within a grace window (e.g., +3s) are merged and the 1m row is idempotently upserted (same PK).

Beyond the grace window, they are counted in DQ (see §8) but do not rewrite the bar.

Dual timestamps: every row carries:

exchange_ts (bar label; lattice key), and

ingest_ts (first write time), plus clock_skew_ms.

2.3 Assembly order (per minute)

Accumulate raw minute state (price/volume, OI/basis snapshots, order-book metrics, flow/CVD).

Compute raw features for the minute (OHLC, spread means, etc.).

Update baselines (robust means/scales), then compute normalized features (z, quantiles).

Apply guards (warm-up, illiquidity, DQ).

Write feature snapshot (idempotent).

Emit/refresh market snapshot (breadth, RS, dispersion).

Evaluate detectors (severity/novelty/debounce), publish events.

Ordering guarantees: normalization/flags are computed from finalized raw features of that minute; detectors read the same finalized set.

2.4 Windows & naming rules

Window suffixes:

seconds: s_XX (e.g., ret_s_30)

minutes: m_XX (e.g., z_vol_m_1, oi_roc_m_5)

hours: h_XX (e.g., funding_h_1)

Feature packs: we ship v1.0 with a fixed set of windows (30s, 1m, 5m, 15m, 1h). New windows → v1.x (additive only).

Consistency: a feature computed at different granularities has consistent semantics; e.g., z_vol_m_1 and z_vol_m_15 are z-scores against their own time-frame baselines (no cross-tf mixing).

2.5 Retention & recomputation intent

Retention intent: 1m ≈90d, 15m ≈1y, 1h ≈3y.

Recompute policy:

1m bars are authoritative; 15m/1h are recomputed from stored 1m (never from candles directly).

If a 1m bar is amended within the grace window, rollups are re-folded deterministically (same lattice keys).

Historical rebuilds (rare) are done from raw backfills with provenance marked (see §16).

3) Inputs & Ingestion

Purpose: enumerate the feeds we rely on, how we parse/merge them, and how we make minute assembly deterministic, idempotent, and low-latency.

3.1 Feeds we subscribe/poll (v1.0)

WebSocket (primary):

trades per asset: tick prints with time, px, sz, taker_side.

candle per asset: live 1m candle state (close signal & sanity check).

bbo per asset: best bid/ask updates (spread & microprice).

l2Book (optional if stable): top-N levels; used for imbalance/depth once DQ is “ok”.

allMids: backup for midprice sanity when bbo is stale.

REST (periodic, read-only, rate-aware):

meta / spotMeta: discovery (universe, tick/lot, decimals).

metaAndAssetCtxs / spotMetaAndAssetCtxs: contexts (OI, mark/index, funding snapshot, 24h stats).

candleSnapshot: bootstrap/backfill recent 1m if we need to seed history.

fundingHistory / predictedFundings: reference for basis/funding and time_to_next_funding_sec.

Note on OI: if no public WS stream provides OI deltas, we maintain a REST poll cadence (e.g., 5–10s) with smoothing; provenance will tag OI source and staleness.

3.2 Stable asset identity & discovery

Build and maintain:

asset_uid (canonical int64), and

an alias map { symbol, ws_symbol, spot_pair/@index, ui_symbol }.

On startup: pull meta/spotMeta, construct active universe, assign asset_uids, and take universe_rev snapshot.

Hysteresis: a symbol must meet criteria K times to enter and M times to exit (avoid churn). Hotlist overlay may force inclusion (with TTL and hot_reason).

3.3 Ingestion topology

Dedicated WS sessions:

One public stream shard for price/flow (trades, candle, bbo),

One optional shard for order book (l2Book) if enabled.

Reconnect with exponential backoff; resume subscriptions deterministically from the alias map.

Message validation:

Monotonic time per asset; drop/flag regressions.

Type/field checks; out-of-range guards (e.g., negative sizes) increment DQ.

Per-asset accumulators (ring buffers):

Trades accumulator → minute volume, v_buy/v_sell, trade_count, last price, returns (30s), CVD (delta/level/slope).

BBO accumulator → time-weighted spread, microprice, book_staleness_ms.

Order-book accumulator (when enabled) → top-N depth, OBI, convexity (later).

Context poller (REST):

Pulls OI, mark/index, funding snapshot on a fixed cadence; tags each minute with latest known values and staleness in ms.

3.4 Minute assembly & idempotency

At minute boundary:

Seal accumulators; compute raw features for the minute.

Attach latest context (OI, mark/index, funding), plus provenance of their age.

Compute normalized features (post-baseline update)—see §4.

Materialize DQ: dq_status, ingest_lag_ms, dropped_ticks, book_staleness_ms.

Upsert the feature snapshot keyed by (asset_uid, tf='1m', exchange_ts).

If another write for the same key arrives within grace → overwrite.

Outside grace → ignore raw fields, log late arrival, update DQ counters only.

Clocking: use exchange timestamps from the messages to bucket to minutes; use local wall-clock only for latency and skew metrics.

3.5 Backpressure & budgets

Per-symbol rate caps for event emission (detector output), not for ingestion.

Processing budgets: ensure minute assembly completes within < 300–500 ms of bar close at typical loads (Top-N + hotlist).

Drop strategy under stress:

Prioritize finalizing 1m feature snapshots.

Temporarily defer detectors for lowest-tier symbols; emit a “detectors_deferred” metric.

3.6 Reconnects, gaps, and recovery

WS reconnect: on disconnect, record gap start; on resume, do not attempt to re-synthesize missed ticks—fill the minute using whatever arrived plus REST/candle sanity; escalate dq_status.

Cold start: optionally seed last K minutes (e.g., 120) from candleSnapshot (raw OHLCV only), mark provenance source='candle_snapshot', and do not backfill normalized features until baselines warm (see §4).

Consistency: rollups are rebuilt after any 1m amendment within grace; otherwise left untouched.

4) Baseline & Normalization Strategy

Purpose: make features comparable across assets and time, robust to outliers, with clear warm-up rules and persisted state for fast restarts.

4.1 What we normalize (v1.0)

Magnitude-varying features per asset×timeframe:

Volume: v_total_m_1 (and variants)

Absolute returns: ret_abs_m_1 (and 5m)

OI change rates: oi_roc_m_5

Spread: spread_mean_m_1

Basis: basis_bp_m_5

Outputs stored alongside raw:

z-scores: z_* (zero-mean, unit-scale target).

quantiles: q_* in [0,1] (robust, easy to threshold across assets).

4.2 Robust baselines (per asset × tf)

For each normalized feature X_t on lattice t:

Maintain robust mean/scale using exponentially weighted median/MAD approximations, e.g.:

Location: μ_t = (1−α)·μ_{t−1} + α·x̂_t where x̂_t is a robust location estimate (online median approximation).

Scale: σ_t = (1−α)·σ_{t−1} + α·ŝ_t where ŝ_t ≈ MAD×1.4826 (online).

Choose α to reflect half-life (e.g., HL ≈ 1d of minutes for 1m features; longer for 15m/1h).

Warm-up: until min_samples (e.g., 200) are observed for a feature, set its z-score to NULL and mark warmup=true in DQ; quantiles may still be emitted with q_confidence=low.

4.3 Z-scores & quantiles

Z: z_t = (X_t − μ_t) / max(σ_t, ε) with ε small (e.g., 1e−9).

We store this raw z_t.

For severity (event scoring), we may apply an IQR clamp (below) without altering stored z_t.

Quantiles (q_t ∈ [0,1]): maintain an online estimator (e.g., t-digest or P²) per feature;

Persist its state periodically (hourly), recover on restart.

Emit q_t and optionally q_confidence if the digest has <N effective samples.

4.4 Outlier control (for alerts, not storage)

IQR clamp per asset×tf per feature, updated daily:

Compute rolling Q1, Q3, IQR = Q3−Q1; define bounds [Q1−k·IQR, Q3+k·IQR] (start k=3).

Severity inputs use clamp(z_t); the stored z_t remains unclamped (truthful for analysis).

4.5 Time-of-day effects (optional v1.1)

If daily seasonality is strong (session opens), maintain two baseline tracks per feature (e.g., “active hours” vs “rest”) selected by hour-of-day; provenance marks which track powered normalization.

v1.0 keeps a single track for simplicity; Curator will propose splitting if drift monitors trigger.

4.6 Baseline state persistence

For each (asset_uid, tf, feature) store:

μ_t, σ_t (robust EW stats), n_samples, last updated ts.

Quantile sketch state (digest or P² parameters).

On restart: reload states; the first bar uses reloaded baselines (no re-warm-up).

4.7 Integrity & DQ interplay

If a minute’s dq_status ≠ ok, do not update baselines with that observation; still write raw features and DQ to the snapshot.

If a feature is NULL (e.g., no book data), skip normalization for that feature for the minute; mark a null counter for drift monitoring.

4.8 Cross-timeframe independence

Never share baselines between timeframes: z_vol_m_1 uses 1m baseline; z_vol_m_15 uses 15m baseline (even though 15m is derived). This prevents leakage and keeps semantics clean.

4.9 Curator hooks (learning about baselines)

Drift monitors: rolling mean/std of each z_* should sit near (0,1). If |mean|>0.2 or std∉[0.8,1.2] for >K bars, Curator proposes:

tweak α (decay),

adjust IQR clamp k, or

split baselines by time-of-day.

Budget monitors: Curator checks event frequency vs severity distribution; proposes threshold/cooldown changes rather than altering normalization.

If this matches what you had in mind, I’ll proceed with Section 5: Feature Computation Spec (Per Family), Section 6: Cross-Asset Context Builder, and Section 7: Universe Policy & Hysteresis next.

You said:
yes, next 3 please
ChatGPT said:
Thought for 1m 2s
5) Feature Computation Spec (Per Family)

Purpose: define the exact signals we compute each minute (and roll up), with names, windows, units, and edge-case handling. These are the high-level columns the entire system stands on.

Notation:
mid_t = minute-close midprice; mid_{t-Δ} = mid at Δ before close;
B_t = best bid; A_t = best ask; spr_t = A_t − B_t;
Vol_buy/Vol_sell by taker side; OI_t = open interest snapshot nearest minute close;
Suffixes: _s_30 = 30 seconds, _m_1 = 1 minute, _m_5 = 5 minutes, _m_15 = 15 minutes, _h_1 = 1 hour.
Every normalized variant (z_*, q_*) is produced per §4 with robust baselines; do not recompute here.

5.1 Price / Returns / Volatility

Columns (1m unless stated):

open, high, low, close — from trade prints within the minute; if no trades, fall back to mid from bbo snapshots (flag dq_status='partial').

mid_close — minute-close (best_bid_close + best_ask_close)/2 (preferred mid for returns).

ret_s_30 — (mid_close − mid_{t-30s}) / mid_{t-30s} using rolling mid from BBO accumulator.

ret_m_1, ret_m_5, ret_m_15 — analogous minute-difference returns.

ret_abs_m_1 — abs(ret_m_1).

rv_m_1 — realized vol proxy within minute: sqrt( sum_i ( Δlog(mid_i) )^2 ) over BBO mid snapshots in the minute (unscaled).
If BBO missing → compute from trades’ mid prints; else NULL and DQ increments.

atr_proxy_m_1 — (high − low) / mid_close.

Notes & edge cases

If mid_{t-Δ} is NULL (startup/warmup), ret_* = NULL.

Use exchange timestamps to align 30s lookbacks accurately (do not assume fixed tick spacing).

Rollups recompute from 1m (do not average returns; re-difference at the higher tf).

5.2 Flow / CVD (Cumulative Volume Delta)

Columns:

v_buy_m_1, v_sell_m_1, v_total_m_1 — sum of taker-buy/sell/total size in quote currency.

trade_count_m_1 — number of prints.

cvd_delta_m_1 — v_buy_m_1 − v_sell_m_1.

cvd_level — running total of cvd_delta_m_1, anchored at UTC 00:00 (resets daily).

cvd_slope_m_5 — the OLS slope of cvd_level over the last 5 bars (units: quote/min).

Notes

If anchor reset occurs intra-run, set cvd_level to 0 at first minute after 00:00 UTC for that asset.

For 15m/1h, recompute cvd_slope over that tf’s bars (do not reuse 1m slope).

5.3 Positioning (Open Interest & Liquidations)

Columns:

oi_open, oi_close, oi_min, oi_max — OI samples observed within minute (from REST poll cadence); choose nearest to bar open/close; min/max across minute.

oi_delta_m_5 — oi_close(t) − oi_close(t−5m).

oi_roc_m_5 — oi_delta_m_5 / max(oi_close(t−5m), ε).

liq_count_m_5, liq_notional_m_5 — count & total notional of liquidations in last 5m if exposed; else NULL.

oi_staleness_ms — ms since last OI sample at bar close (for DQ).

Notes

If OI not updated within staleness cap (e.g., 20s), flag dq_status='partial' for positioning features.

No synthetic OI: do not infer OI from prints; keep honest NULL when missing.

5.4 Perp State (Funding & Basis)

Columns:

funding_h_1 — most recent predicted or current funding rate (per hour). If multiple venues exposed, prefer HL; else store HL predicted.

basis_bp_m_5 — rolling mean of ((mark − index) / index) * 10_000 over last 5 minutes (basis in bps).

time_to_next_funding_sec — seconds to next funding event (if available).

Notes

If index is missing or ≤0, set basis_bp_m_5 = NULL and bump DQ.

For rollups, recompute the 5m rolling mean within the larger tf window (not a simple carry).

5.5 Liquidity / Microstructure

(Enable L2-derived fields only when dq_status='ok' for the order-book stream; otherwise NULL.)

Columns:

spread_mean_m_1 — time-weighted average spread across BBO updates in minute.

spread_p95_m_1 — 95th percentile spread for the minute.

obi_top5_mean_m_1 — mean order-book imbalance over the minute, computed on top-5 levels:
OBI = bid_depth / (bid_depth + ask_depth); aggregate by time-weight.

depth_top5_quote_median_m_1 — median of (sum of top-5 bid+ask in quote).

microprice_drift_s_30 (optional v1.1) — (microprice_close − microprice_{t−30s}) / microprice_{t−30s}, where
microprice = (A*BidDepth + B*AskDepth) / (BidDepth + AskDepth).

Notes

If only BBO is available (no L2), compute spread metrics; set OBI/depth to NULL.

5.6 Cheap Flags (detector-friendly bits)

These are columns (booleans) produced from normalized features and class LUT defaults; detectors will still compute severity independently.

is_vol_spike_m_1 — z_vol_m_1 ≥ τ_vol (default τ to be set in detector pack).

is_price_spike_up_m_1, is_price_spike_down_m_1 — z_ret_abs_m_1 ≥ τ_ret ∧ sign of ret_m_1.

is_oi_spike_up_m_5, is_oi_spike_down_m_5 — threshold on oi_roc_m_5.

is_spread_stress_m_1 — z_spread_m_1 ≥ τ_spread.

is_liq_cluster_m_5 — liq_count_m_5 ≥ L (only if liq feed present).

Guardrails

Apply warm-up: any flag that depends on a z_* is NULL until baseline ready.

Apply illiquidity gates before setting flags.

5.7 Normalized Variants (produced per §4)

For each family’s normalizable inputs, include:

z_vol_m_1, z_ret_abs_m_1, z_oi_roc_m_5, z_spread_m_1, z_basis_m_5

q_vol_m_1, q_ret_abs_m_1, q_oi_roc_m_5

(Stored alongside raw; severity will use IQR-clamped copies without altering z_*.)

6) Cross-Asset Context Builder

Purpose: produce a lightweight, deterministic market frame on each lattice tick so events can be contextualized without heavy recomputation downstream.

6.1 Inputs & scope

Consume the just-finalized 1m feature snapshots for symbols where is_in_universe OR is_hot.

Ignore assets with dq_status≠ok for the context aggregates (but keep counts of excluded names for observability).

6.2 Core outputs (per tf × ts row)

leader — symbol acting as flow leader for the last 5 minutes.

shock_count_5s — #symbols that fired any spike-class flag within the last 5 seconds of exchange time
(derived from emitted events; if unavailable, approximate using current minute flags with a 1m granularity and mark approx=true).

rs_top / rs_bottom — arrays (e.g., length 5) of strongest/weakest names by RS score (below).

return_dispersion_m_5 — cross-sectional standard deviation of ret_m_5.

vol_dispersion_m_5 — cross-sectional standard deviation of z_vol_m_1 (or rv_m_1).

dominance_share — fraction of total dollar volume (last 5m) explained by the leader (0–1).

time_to_next_funding_sec — minimum across covered perps (or BTC if present).

6.3 Relative Strength (RS) score

Goal: rank assets intraday with a simple, robust scalar.

Definition (defaults):

RS = w1 * z_ret_abs_m_1 * sign(ret_m_5)
   + w2 * z_vol_m_1
   + w3 * sign(oi_roc_m_5) * min(|z_oi_roc_m_5|, z_cap)


Defaults: w1=0.5, w2=0.3, w3=0.2, z_cap=3.0.

If oi_roc missing → set the last term to 0.

If any z is NULL (warm-up), treat as 0 and record rs_incomplete=true.

Outputs:

rs_score_m_5 per asset (store scalar in features_snapshot for convenience).

rs_top, rs_bottom are the arg-sorts of rs_score_m_5.

6.4 Leader logic

Candidates: majors (BTC, ETH) plus any asset in the top decile of RS for the last 5m.

Leader selection:

Compute lead index per candidate:
lead = |ret_m_5| * max(z_vol_m_1, 0) * (1 + 0.5 * max(0, sign(ret_m_5)*sign(oi_roc_m_5)))

Pick symbol with max lead.

If tie or low activity (lead below small epsilon), default to BTC if present.

Dominance:

dominance_share = leader’s dollar volume (5m) / total dollar volume across covered assets (5m).

6.5 Synchrony / breadth

Event-driven method (preferred): read last 5 seconds of emitted events (spike class). Count unique symbols → shock_count_5s.

Fallback: use current minute’s cheap flags; count is_price_spike_* OR is_vol_spike_m_1 OR is_oi_spike_* → store and mark approx=true.

6.6 Dispersion metrics

return_dispersion_m_5 — stddev across assets of ret_m_5.

vol_dispersion_m_5 — stddev across assets of z_vol_m_1.

Optional: rs_dispersion_m_5 — stddev of rs_score_m_5 (add if Curator deems helpful).

6.7 Optional lead-lag hint (v1.1+)

Two cheap hints without heavy modeling:

First-trigger map: among assets that triggered spike events in last 30s, record first arrival time; compute lead_ms_to_btc = time_diff(asset vs BTC).

Event co-occurrence graph: exponentially-weighted counts of (leader, follower) pairs when follower spikes within Δt after leader. Expose top edges periodically to Curator.

(Do not block v1.0; store only if trivial to compute.)

6.8 DQ & gating

Exclude assets with dq_status≠ok from aggregates; add excluded_count to market_snapshot.

If fewer than min_assets_for_context (e.g., 5) are eligible, mark market_snapshot dq='partial'.

7) Universe Policy & Hysteresis

Purpose: define which symbols the detector actively maintains features for each minute, and how we prevent churn while still reacting to “hot” names.

7.1 Objectives

Keep compute bounded and stable (no symbol churn every minute).

Always cover liquid leaders and recently hot assets.

Make membership changes auditable (reason codes, revisions).

7.2 Scores & lookbacks

Compute per asset on a rolling basis (using 1m snapshots):

Dollar volume (lookback L1): dv_L1 = sum_{last L1}( v_total_m_1 * mid_close ).
Default L1 = 60m.

Open interest (lookback L2): oi_L2 = median_{last L2}( oi_close ).
Default L2 = 60m.

Composite rank score:
U = wv * rank_desc(dv_L1) + wo * rank_desc(oi_L2) with wv=0.7, wo=0.3.
Missing OI → use wv=1.0, wo=0.0 for that asset (and log DQ).

7.3 Membership rules

Let N_base be the target universe size (default 25). Define entry and exit bands with hysteresis:

Entry condition: rank(U) ≤ N_entry for K_entry consecutive minutes.
Defaults: N_entry = N_base − 3, K_entry = 3.

Exit condition: rank(U) > N_exit for K_exit consecutive minutes.
Defaults: N_exit = N_base + 5, K_exit = 5.

Stability hints

Freeze window after each change: do not re-evaluate membership again for T_freeze minutes (default 5) to avoid thrash.

Min dwell time: once in, stay ≥ min_dwell (default 30m) unless hard-exit (see below).

7.4 Hotlist overlay

Trigger: any event with severity ≥ S_hot (default 70) or specific subtypes (e.g., basis_jolt, liq_cluster).

Behavior:

Add asset to hotlist with:

hot_reason (enum),

hot_started_at,

ttl_min derived from severity: ttl = ttl_base + k * severity (e.g., base 15m, k=0.3m/pt → sev=80 ⇒ +24m → 39m total).

While hot, the asset bypasses universe membership checks for detector gating.

When TTL expires, remove unless it also qualifies by universe score.

7.5 Gating

At 1m assembly, set per asset:

is_in_universe (bool),

is_hot (bool),

universe_rev (int).

Detectors only run if: is_in_universe OR is_hot.
Feature snapshots are still written for tracked assets; if you choose to not compute for out-of-universe names, at minimum write a thin row with DQ and membership bits so joins remain simple.

7.6 Hard exits & safety valves

Hard exit: if dq_status='stale' for T_stale minutes (e.g., 10) and dv_L1 falls below a dead threshold, drop asset immediately despite dwell.

Cap universe churn: no more than C changes per hour (default 5). If exceeded, defer entries (except hotlist) to the next hour boundary.

7.7 Auditing & revisions

On every membership change, bump universe_rev and append an audit record:
{rev, ts, added[], removed[], reasons{symbol: 'entry|exit|hard_exit|hotlist'}}.

Store current N_base, N_entry, N_exit, K_entry, K_exit, ttl_base, k in config; include universe_policy_rev in event provenance.

7.8 Curator hooks

Churn monitor: if hourly churn > C for 3 consecutive hours, propose wider hysteresis or bigger N_base.

Coverage monitor: ensure top 95% of total dollar volume (last 24h) is captured by the union of is_in_universe ∪ is_hot; if not, propose N_base++ or lower S_hot.

Liquidity tiers: propose tiered budgets/thresholds by volume decile to reduce false spikes on thin names.

7.9 Pseudocode (reference)
def update_universe(now, assets):
    # compute scores
    for a in assets:
        a.dv_L1 = rolling_sum(a.v_total_m_1 * a.mid_close, lookback=60)
        a.oi_L2 = rolling_median(a.oi_close, lookback=60)
    rankU = rank_desc([
        (a.uid, 0.7*rank_desc(a.dv_L1) + 0.3*rank_desc_or_zero(a.oi_L2))
        for a in assets
    ])

    # hysteresis
    for a in assets:
        if rankU[a.uid] <= N_entry and a.entry_streak >= K_entry:
            enter(a)
        elif rankU[a.uid] > N_exit and a.exit_streak >= K_exit:
            exit(a)

    # apply freeze/dwell & cap churn
    enforce_freeze_and_dwell()
    limit_hourly_churn()

    # hotlist TTL
    for a in hotlist:
        if now >= a.hot_expires_at:
            hotlist.remove(a)


If this level of detail works, I’ll continue with Section 8: Data Quality & Safety Rails, Section 9: Event Detector Catalogue, and Section 10: Severity, Novelty & Debounce Model next.

You said:
ok good - next 3 please
ChatGPT said:
Thought for 28s
8) Data Quality & Safety Rails

Purpose: make the detector trustworthy under stress. These rules determine when we compute, normalize, and emit—and when we hold fire.

8.1 DQ fields (on every 1m row)

dq_status ENUM('ok','partial','stale')

ok: all required feeds fresh & consistent

partial: core (trades/BBO) ok but secondary (OI/L2) stale/missing

stale: core late/missing or severe inconsistencies

ingest_lag_ms: time from bar close (exchange_ts) to first persisted write

dropped_ticks: count of invalid/duplicate/out-of-order trade records in minute

book_staleness_ms: ms since last BBO update at bar close

oi_staleness_ms: ms since last OI sample at bar close (if tracking OI)

warmup BOOL: true until min_samples reached for all normalized features used by detectors

is_in_universe BOOL, is_hot BOOL, universe_rev INT (from §7)

Computation thresholds (starters; Curator may tune):

dq_status='partial' if oi_staleness_ms > 20000 or l2Book missing while enabled

dq_status='stale' if book_staleness_ms > 3000 or no trades & no BBO in minute

8.2 Warm-up & baseline hygiene

No z/quantile emission for features until min_samples ≥ 200 per asset×tf.

Store raw features; set z_* = NULL. Cheap flags that depend on z_* are also NULL.

Baselines do not update on minutes with dq_status!='ok'.

8.3 Illiquidity & dead-book guards

Define per-asset dynamic thresholds:

v_min = max(1e4, 0.5% * median(dollar_vol_m_1, 7d))

spread_cap = 15 * median(spread_mean_m_1, 7d)

Block spike-class flags if v_total_m_1 < v_min or spread_mean_m_1 > spread_cap.

Mark illiquidity_hit=TRUE in snapshot for Curator tracking.

8.4 OI / Funding / Basis staleness

If oi_staleness_ms > 20000: set positioning features that rely on fresh OI to NULL and zero-out their contributions in RS/severity.

If index missing/zero: basis_* = NULL and suppress basis/funding detectors.

Always attach time_to_next_funding_sec if available; else NULL.

8.5 Gaps & late data

Grace window: up to +3s after bar close; we upsert the row and re-fold rollups.

After grace: do not rewrite the bar. Increment DQ counters and log late-series metrics.

WS reconnects: mark affected minutes dq_status='stale'; detectors do not fire on those minutes.

8.6 Integrity checks (minute-level)

Price sanity: low ≤ min(trade_px) ≤ max(trade_px) ≤ high, open/close inside [low, high]. Else flag stale.

Return bounds: clamp raw return magnitude to ≤ 20% per minute; beyond that, mark stale and drop from normalization.

Clock skew: if |clock_skew_ms| > 1000, raise partial; if > 3000, raise to stale.

8.7 Event gating by DQ

Never emit events if dq_status!='ok', warmup==TRUE, or illiquidity guard tripped.

Suppressed emissions increment per-class suppression counters (observability).

8.8 Degraded modes (safety valves)

Detector deferral: if bar finalization time exceeds 500ms p95, defer detectors for tail symbols for that minute (write a metric).

Budget pressure: under global event surge, drop lowest-severity events first (per §10.5), but never skip feature snapshot writes.

8.9 Metrics & alerts (ops)

Lag: p50/p95 ingest_lag_ms

Quality: % ok/partial/stale, null rates per feature family

Suppression: counts by (class, reason), per symbol and system-wide

Baseline drift: mean/std of z_* by asset×tf vs targets (0,1)

Illiquidity: hit-rate trend by symbol tier (top/mid/long tail)

8.10 Curator hooks

Propose asset-specific v_min/spread_cap from empirical 7d distributions

Suggest time-of-day baseline splits if drift recurs at session opens

Auto-tighten clock_skew alarms if repeated near-threshold incidents occur

9) Event Detector Catalogue (v0.1)

Purpose: a small, composable set of detectors that cover 95% of what we need. All are deterministic, read only from the 1m snapshots + market snapshot, and respect §8 gating.

Format per detector: What/Why, Inputs, Preconditions, Trigger, Local state payload, Notes.

9.1 General rules

Run on 1m lattice (unless subtype names encode 5m/15m horizons).

Gated by: dq_status=='ok' ∧ (is_in_universe ∨ is_hot) ∧ warmup==FALSE.

Severity & debounce come from §10 (detector emits a candidate with primary_z, secondary_z, breadth, which the scorer maps to 0–100).

Each detector has a cooldown and half-life (novelty decay) maintained in the registry.

9.2 SPIKE class
a) spike.vol_spike_m_1

What/Why: sudden flow intensity → potential impulse or unwind.

Inputs: z_vol_m_1, ret_m_1, trade_count_m_1, v_total_m_1

Preconditions: illiquidity guard passes; trade_count_m_1 ≥ 5

Trigger: z_vol_m_1 ≥ τ_vol (default 3.0)

Local state payload: z_vol_m_1 (primary), ret_m_1, z_ret_abs_m_1, v_total_m_1

Notes: secondary confirms include z_ret_abs_m_1 > 1.5

b) spike.price_spike_up_m_1 / spike.price_spike_down_m_1

Inputs: ret_m_1, z_ret_abs_m_1, spread_mean_m_1

Trigger: z_ret_abs_m_1 ≥ τ_ret (2.5), sign of ret_m_1 determines subtype

Payload: ret_m_1 (primary z proxy = z_ret_abs_m_1), spread_mean_m_1, rv_m_1

c) spike.oi_spike_up_m_5 / spike.oi_spike_down_m_5

Inputs: oi_roc_m_5, z_oi_roc_m_5, ret_m_5

Pre: oi_staleness_ms ≤ 20000

Trigger: |oi_roc_m_5| ≥ 1.5% and z_oi_roc_m_5 ≥ 2.0

Payload: oi_roc_m_5 (primary), ret_m_5, z_vol_m_1

d) spike.liq_cluster_m_5 (if feed available; else inferred)

Inputs: liq_count_m_5, liq_notional_m_5 or inference proxy: (z_ret_abs_m_1 + spread_p95_m_1 z + OI↓)

Trigger: liq_count_m_5 ≥ L (e.g., 3) or proxy score ≥ threshold

Payload: counts/notional, ret_m_1, z_vol_m_1, oi_roc_m_5

9.3 SHIFT class
a) shift.spread_stress_m_1

Why: liquidity regime change → worse fills, higher slippage; also signal of stress.

Inputs: z_spread_m_1, spread_p95_m_1, trade_count_m_1

Trigger: z_spread_m_1 ≥ 2.0

Payload: z_spread_m_1 (primary), spread_p95_m_1, v_total_m_1

b) shift.basis_jolt_m_5

Why: perp–spot dislocation; potential arb/mean-revert or crowded carry unwind.

Inputs: basis_bp_m_5, z_basis_m_5, ret_m_5, oi_roc_m_5

Trigger: |z_basis_m_5| ≥ 2.5

Payload: basis_bp_m_5 (primary), z_basis_m_5, oi_roc_m_5, ret_m_5

c) shift.funding_jolt_h_1

Inputs: funding_h_1 (change vs last hour), time_to_next_funding_sec

Trigger: |Δ funding_h_1| ≥ 10 bps (starter) or predicted flip within ≤ 1h

Payload: funding now/prev, time_to_next_funding_sec

9.4 QUADRANT class

(Positioning vs price: commitment vs squeeze framing)

a) quadrant.price_up_oi_up_m_5 (trend build)
b) quadrant.price_up_oi_down_m_5 (short squeeze)
c) quadrant.price_down_oi_up_m_5 (trend down build)
d) quadrant.price_down_oi_down_m_5 (long squeeze)

Inputs: ret_m_5, oi_roc_m_5

Pre: fresh OI

Trigger: |ret_m_5| ≥ 0.3% and |oi_roc_m_5| ≥ 1.0% with signs per subtype

Payload: ret_m_5 (primary), oi_roc_m_5 (secondary), z_vol_m_1

9.5 DIVERGENCE class
a) div.price_up_cvd_down_m_5

Why: absorption; price lifts but net flow sells—fragile move or large passive buyer

Inputs: ret_m_5 > 0, cvd_delta_m_1 rolling sum over 5 bars < 0

Trigger: ret_m_5 ≥ 0.3% and Σ_5(cvd_delta_m_1) ≤ −q

Payload: ret_m_5 (primary), Σ_5(cvd_delta), z_vol_m_1, z_spread_m_1

b) div.price_flat_cvd_trend_m_5

Why: accumulation/distribution without price change

Inputs: |ret_m_5| ≤ 0.1%, cvd_slope_m_5 ≠ 0

Trigger: |cvd_slope_m_5| ≥ θ_cvd

Payload: slope, ret_m_5, spread_mean_m_1

c) div.premium_no_oi_m_5

Why: basis premium spike without OI confirmation → likely to mean-revert

Inputs: z_basis_m_5, oi_roc_m_5

Trigger: z_basis_m_5 ≥ 2.0 and oi_roc_m_5 ≤ 0

Payload: basis, oi_roc_m_5, ret_m_5

9.6 SYNCHRONY class
a) sync.basket_shock_Δt_5s

Why: market-wide shock/news; momentum continuation or liquidity vacuum

Inputs: event bus (spike-class) over last 5s; shock_count_5s

Trigger: shock_count_5s ≥ max(4, ceil(0.15 * universe_size))

Payload: shock_count_5s (primary), current leader, dominance_share, return_dispersion_m_5

9.7 ROTATION class
a) rot.rs_flip_sector_m_15 (if sectors tagged)

Why: leadership change; rotation opportunities

Inputs: sector-wise average rs_score_m_5 over last 15m

Trigger: former top sector falls out of top-2 and a new sector leads by ≥ δ

Payload: old/new sector, delta in sector RS

b) rot.leader_cooling_followers_hot_m_15

Why: BTC/ETH cool off while alts heat up—classic rotation

Inputs: leader’s z_vol_m_1/ret_m_5 trending down; median of followers’ RS trending up

Trigger: 2-bar trend divergence on these aggregates

Payload: leader metrics vs follower median deltas

9.8 Local state payload (what to include)

For every event, include:

Features (subset): primary & secondary inputs, plus a small panel for context
e.g., ret_s_30, ret_m_1, z_ret_abs_m_1, z_vol_m_1, oi_roc_m_5, z_oi_roc_m_5, spread_mean_m_1, z_spread_m_1, cvd_slope_m_5, basis_bp_m_5, z_basis_m_5

Flags: any relevant cheap flags that are TRUE

DQ echoes: dq_status, ingest_lag_ms, oi_staleness_ms (so consumers can trust/ignore)

Market frame: leader, shock_count_5s, rs_top, rs_bottom, dominance_share, time_to_next_funding_sec

(Exact JSON shape in §11; detectors just provide the fields.)

9.9 Detector registry entry (example)
{
  "detector_id": "spike.vol_spike_m_1",
  "version": "0.1.3",
  "inputs": ["z_vol_m_1","ret_m_1","dq_status","v_total_m_1"],
  "preconditions": ["dq_status=='ok'","v_total_m_1 >= v_min","trade_count_m_1 >= 5"],
  "trigger": "z_vol_m_1 >= 3.0",
  "cooldown_sec": 45,
  "half_life_sec": 120,
  "severity_weights": {"primary":1.0,"secondary":0.5,"breadth":0.4,"novelty":0.2,"dq_penalty":-0.6},
  "enabled": true
}

10) Severity, Novelty & Debounce Model

Purpose: standardize how raw triggers become a 0–100 severity, avoid spam, and keep signals meaningful as conditions persist.

10.1 Inputs to the scorer

Per candidate trigger, the detector passes:

primary_z (e.g., z_vol_m_1, z_ret_abs_m_1, z_basis_m_5)

secondary_z+ (0–N supporting z/metrics: z_oi_roc_m_5, z_spread_m_1, etc.)

breadth (e.g., shock_count_5s scaled to [0,1])

novelty_state (first seen? time since last?)

dq_penalties (0 or >0 if any soft issues)

illiquidity_penalty (0 or >0 if near guard thresholds)

10.2 IQR clamp (only for scoring)

Compute primarŷ = clamp(primary_z) using per-asset IQR bounds (§4.4).

Apply the same for secondary metrics that can explode (optional).

10.3 Map to 0–100

We use a smooth saturating function:

core = w1*primarŷ + w2*max(0, secondarŷ) + w3*breadth
pen  = w_dq*dq_penalty + w_liq*illiquidity_penalty
raw  = core + novelty_boost - pen

severity = round( 100 * sigmoid( a * raw ) )


Defaults:

w1=1.0, w2=0.5, w3=0.4, w_dq=0.6, w_liq=0.3

a=0.6 (controls steepness)

Class LUT overrides weights per class:

spike: higher w1, moderate w3

shift: lower w1, higher w2 (secondary confirmation)

synchrony: w3 dominates

Curator calibrates a and weights to keep severity histograms stable.

10.4 Novelty & half-life

Each (symbol:class:tf) keeps a small novelty state:

if first_time:
    novelty_boost = β0                      # e.g., +0.8
else:
    dt = now - last_emit_time
    novelty_boost = β0 * exp(- dt / half_life_sec)


Half-life per class: spike=120s, shift=300s, synchrony=60s, quadrant=180s, divergence=240s, rotation=900s

Novelty is additive (pre-sigmoid), capped to prevent dominating.

10.5 Debounce & re-emission rules

Debounce key: symbol:class:tf

Cooldown: per registry (e.g., 45s for spikes, 90s for shifts)

Emit when:

No active cooldown and severity ≥ class threshold; or

Within cooldown but severity ≥ last_severity × (1 + δ), with δ=0.3 (≥ +30%)

Subtype change within same class (e.g., price_spike_up→price_spike_down) — emit immediately with novelty_boost reset

Coalescing: if multiple subtypes in same class trigger within 1s, keep the higher-severity one and add a coalesced=[subtypes...] note to payload.

10.6 Per-class budgets & backpressure

Caps per symbol per minute (starters): spike:4, shift:2, quadrant:2, divergence:2, sync:2, rotation:1

Global cap (system-wide): e.g., 800 events/min; if exceeded, drop lowest severity events first, preserving class diversity (don’t drop all of one class).

Dropped events still increment suppression metrics with reason=budget.

10.7 Quality penalties

If dq_status='ok' but near limits (e.g., book_staleness_ms ∈ (1500,3000]), set dq_penalty=1.

If v_total_m_1 just above v_min or spread_mean_m_1 just below spread_cap, set illiquidity_penalty=1.

Both penalties subtract via w_dq/w_liq in the score.

10.8 Calibration workflow (offline, Curator-led)

Collect last 14 days of candidate triggers with their raw z’s & breadth.

Grid-search small sets of weights & a to keep:

class-wise severity distributions stable (median in [55,70], p90 in [80,95])

per-class event rate within budgets

Replay golden minutes & most recent day; ensure bit-identical emissions across environments.

Propose a config (weights, thresholds, half-lives) → config_hash changes → canary → apply.

10.9 Example (worked)

Inputs: spike.vol_spike_m_1

primary_z = 3.6 (clamped to 3.2)

secondarŷ = z_ret_abs_m_1 = 2.1

breadth = min(1, shock_count_5s/6) = 4/6 ≈ 0.67

dq_penalty=0, illiquidity_penalty=0

First occurrence (novelty_boost=0.8)

Core: 1.0*3.2 + 0.5*2.1 + 0.4*0.67 ≈ 3.2 + 1.05 + 0.27 = 4.52

Raw: 4.52 + 0.8 = 5.32

Severity: ≈ 100 * sigmoid(0.6 * 5.32) ≈ 100 * sigmoid(3.19) ≈ 96

Emit, set cooldown=45s, store last_severity=96.

With these three sections, the detector now knows when it can trust data (§8), what to detect (§9), and how to score & throttle signals (§10).
Ready for the next set: §11 Event Contract & Publication, §12 Storage Design & Schema Strategy, §13 Provenance & Versioning.

You said:
good, next 3
ChatGPT said:
Thought for 39s
11) Event Contract & Publication

Purpose: define the canonical JSON we publish, delivery guarantees, and how consumers reliably dedupe and replay.

11.1 Event schema (v0.1)

Principles

Small, stable core. No decisions, no PII, no user state.

Self-describing. Includes provenance to reproduce bit-for-bit.

Dedupe-friendly. Strong IDs and debounce keys.

{
  "v": "0.1",
  "event_id": "uuid-v7",                 // time-ordered; unique per emission
  "emitted_at": "2025-09-03T09:30:00Z",
  "exchange_ts": "2025-09-03T09:30:00Z", // lattice label (bar close)
  "ingest_ts": "2025-09-03T09:30:00.142Z",
  "symbol": "BTC",
  "asset_uid": 101,                       // canonical numeric ID
  "tf": "1m",                             // 1m|15m|1h (producer: 1m)
  "class": "spike",                       // spike|shift|quadrant|divergence|synchrony|rotation
  "subtype": "vol_spike_m_1",
  "window_sec": 60,
  "severity": 74,                         // 0..100 (rounded int)
  "novelty": { "first_seen_at": "2025-09-03T09:29:00Z" },
  "debounce_key": "BTC:spike:1m",
  "coalesced": ["price_spike_up_m_1"],    // optional; present when coalesced
  "local_state": {
    "features": {
      "ret_s_30": 0.0042,
      "ret_m_1": 0.0031,
      "z_ret_abs_m_1": 2.9,
      "v_total_m_1": 18000000,
      "z_vol_m_1": 3.6,
      "oi_roc_m_5": 0.012,
      "z_oi_roc_m_5": 2.1,
      "spread_mean_m_1": 0.75,
      "z_spread_m_1": 0.9,
      "cvd_slope_m_5": 0.7,
      "basis_bp_m_5": 18.4,
      "z_basis_m_5": 1.3
    },
    "flags": {
      "is_price_spike_up_m_1": true,
      "is_oi_spike_up_m_5": true
    },
    "dq": {
      "status": "ok",
      "ingest_lag_ms": 142,
      "book_staleness_ms": 41,
      "oi_staleness_ms": 1800
    }
  },
  "market_frame": {
    "leader": "BTC",
    "dominance_share": 0.42,
    "shock_count_5s": 4,
    "rs_top": ["SOL","HYPE","APT","SEI","ENA"],
    "rs_bottom": ["XRP","ADA","ARB","DOGE","DOT"],
    "return_dispersion_m_5": 0.006,
    "vol_dispersion_m_5": 0.92,
    "time_to_next_funding_sec": 2143
  },
  "membership": { "is_in_universe": true, "is_hot": true, "universe_rev": 3127 },
  "provenance": {
    "producer": "alpha-detector@v1.0.0",
    "feature_pack": "v1.0",
    "detector_pack": "v0.1",
    "config_hash": "sha256:…",
    "git_commit": "…",
    "universe_policy_rev": 17,
    "source_lag_ms": 128,
    "clock_skew_ms": 73
  },
  "attachments": {
    "bar_refs": { "1m": ["BTC/1m/2025-09-03T09:26:00Z", "…", "…"] }
  }
}


Required fields: v,event_id,emitted_at,exchange_ts,symbol,asset_uid,tf,class,subtype,severity,debounce_key,local_state.dq.status,market_frame.leader,membership.*,provenance.*
Optional: coalesced,attachments,market_frame.rs_top/rs_bottom

11.2 Types & bounds

severity: integer 0–100.

Floats: finite, non-NaN. Use decimal strings if consumer requires exactness (we keep JSON numbers).

Arrays: max 16 elements (e.g., rs_top).

Strings: ASCII or UTF-8; subtype/class/tf enumerations only.

11.3 Publication channel & delivery

Topic: alpha.events.v0 (versioned by contract).

Partitioning key: asset_uid (keeps per-asset order).

Semantics: at-least-once delivery; consumers must dedupe on event_id.

Retention: 7–14 days on the bus; authoritative archive is the anomaly_event table (§12).

DLQ: alpha.events.dlq for schema or size violations.

11.4 Ordering & dedupe

We use UUIDv7 (time-ordered) for event_id.

Per partition we preserve publish order, but consumers must ignore older emitted_at for the same debounce_key within a window.

Dedupe key in storage: (event_id); additional unique index (asset_uid, class, tf, emitted_at, subtype) for fast queries.

11.5 Backfill & replay emission

Replays publish to alpha.events.replay.v0 to avoid confusing live consumers.

Replay payloads must carry original event_id and emitted_at; add "provenance": { "replay_of": true }.

11.6 Contract evolution

Backward-compatible fields are add-only.

Breaking changes → new topic alpha.events.v1.

Consumers are expected to ignore unknown fields.

12) Storage Design & Schema Strategy

Purpose: store snapshots and events so they’re fast to query, cheap to retain, and easy to evolve.

We describe structure and constraints. Exact DDL can be generated from this spec.

12.1 Core tables
A) features_snapshot

Grain: (asset_uid, tf, exchange_ts); PK on these three.

Columns (wide):

Identity: asset_uid INT8, symbol TEXT, tf ENUM, exchange_ts TIMESTAMPTZ, ingest_ts TIMESTAMPTZ

Price/Returns/Vol: open,high,low,close,mid_close,ret_s_30,ret_m_1,ret_m_5,ret_m_15,ret_abs_m_1,rv_m_1,atr_proxy_m_1 (DECIMAL)

Flow/CVD: v_buy_m_1,v_sell_m_1,v_total_m_1,trade_count_m_1,cvd_delta_m_1,cvd_level,cvd_slope_m_5

Positioning: oi_open,oi_close,oi_min,oi_max,oi_delta_m_5,oi_roc_m_5,liq_count_m_5,liq_notional_m_5,oi_staleness_ms

Perp: funding_h_1,basis_bp_m_5,time_to_next_funding_sec

Micro: spread_mean_m_1,spread_p95_m_1,obi_top5_mean_m_1,depth_top5_quote_median_m_1

Baselines (robust): b_mean_* , b_scale_* (per §4)

Normalized: z_vol_m_1,z_ret_abs_m_1,z_oi_roc_m_5,z_spread_m_1,z_basis_m_5,q_vol_m_1,q_ret_abs_m_1,q_oi_roc_m_5

Cheap flags: is_vol_spike_m_1,is_price_spike_up_m_1,is_price_spike_down_m_1,is_oi_spike_up_m_5,is_oi_spike_down_m_5,is_spread_stress_m_1,is_liq_cluster_m_5

RS scalar: rs_score_m_5 (shortcut for §6; optional but useful)

DQ: dq_status ENUM, ingest_lag_ms INT2, dropped_ticks INT2, book_staleness_ms INT2, warmup BOOL

Membership: is_in_universe BOOL, is_hot BOOL, universe_rev INT4

Provenance: feature_pack TEXT, pack_rev INT2, source TEXT (e.g., ws|candle_snapshot)

Extras: extras_json JSONB (for experimental fields)

Partitioning: by (tf, month); e.g., Timescale hypertables or native partitions.

Indexes:

PK as above;

(asset_uid, exchange_ts DESC);

partial indexes on (dq_status!='ok'), (is_hot=true).

B) market_snapshot

Grain: (tf, exchange_ts); PK on both.

Columns: leader TEXT, dominance_share DECIMAL, shock_count_5s INT2, rs_top JSONB, rs_bottom JSONB, return_dispersion_m_5 DECIMAL, vol_dispersion_m_5 DECIMAL, excluded_count INT2, approx BOOL, time_to_next_funding_sec INT4, dq_status ENUM, universe_rev INT4.

C) anomaly_event

Grain: append-only; PK: (event_id UUID).

Columns:

Identity: event_id, emitted_at, exchange_ts, asset_uid, symbol, tf, class, subtype, severity INT2

Membership echo: is_in_universe BOOL, is_hot BOOL, universe_rev INT4

Provenance: feature_pack, detector_pack, config_hash, git_commit, universe_policy_rev INT4, source_lag_ms INT4, clock_skew_ms INT4, replay_of BOOL

Payload: payload JSONB (exact event JSON)

Indexes: (asset_uid, exchange_ts DESC), (class, subtype, emitted_at DESC), GIN on payload.

12.2 State & registry tables

baseline_state
(asset_uid, tf, feature_name) → mu, sigma, n_samples, updated_at, quantile_state BYTEA/JSONB.
Used to resume normalization instantly.

feature_registry
feature_name, window, formula, inputs, units, pack, added_at, deprecated_at, notes.
Living dictionary; drives DDL generation.

detector_registry
detector_id, version, inputs[], preconditions, trigger, cooldown_sec, half_life_sec, severity_weights JSONB, enabled BOOL, added_at, deprecated_at.

universe_audit
rev, ts, added[], removed[], params JSONB.

hotlist_state
(asset_uid) → hot_reason ENUM, hot_started_at, hot_expires_at.

Curator tables (summarized)

curator_runs(run_id, started_at, finished_at, inputs_hash, config_hash, notes)

insights(insight_id, ts, scope, kind, evidence JSONB, recommendation JSONB, author, status)

config_proposals(proposal_id, created_at, target, diff JSONB, rationale, status, applied_at)

replay_results(proposal_id, window, metrics JSONB, passed BOOL)

12.3 Data types & precision

Prices/ratios: DECIMAL(38, 12) (or DOUBLE with care if storage pressure is high).

Counts: INT4/INT2.

Timestamps: TIMESTAMPTZ (UTC).

Enums for tf, dq_status, class, subtype keep data clean; add values carefully.

12.4 Retention & pruning

features_snapshot: keep 1m ≈90d, 15m ≈1y, 1h ≈3y (drop partitions by date).

anomaly_event: keep ≥1y (events are compact).

market_snapshot: 1y+.

Compression: enable chunk compression (Timescale) after 7d.

12.5 Idempotency & conflict policy

features_snapshot: UPSERT on (asset_uid, tf, exchange_ts); last-write-wins within grace (≤+3s). After grace: ignore raw field changes; allow DQ counters to update via side-channel if needed.

market_snapshot: UPSERT on (tf, exchange_ts) same as above.

anomaly_event: INSERT ONLY; duplicates rejected by event_id PK.

12.6 Overflow & promotion

Experimental fields land in extras_json.

Once stable, they are promoted to typed columns in the next feature_pack minor version; backfill forward only (no historical retrofits unless trivial).

12.7 Query patterns (design for them)

Recent state per asset: SELECT … FROM features_snapshot WHERE asset_uid=? AND tf='1m' ORDER BY exchange_ts DESC LIMIT 120;

Event search: by (class, subtype) and time window; use GIN on payload for ad-hoc.

Cross-section: join latest features_snapshot on exchange_ts = now_floor for RS ranks, dispersion.

13) Provenance & Versioning

Purpose: guarantee that we can explain exactly why an event fired, reproduce it, and evolve without breaking consumers.

13.1 Packs & policy

Feature Pack (FP): defines columns + formulas + windows.

Semantic versioning: vMAJOR.MINOR (e.g., v1.0).

MINOR adds columns/windows (backward-compatible).

MAJOR reserved for breaking renames/removals (avoid if at all possible).

Detector Pack (DP): defines detectors + thresholds + cooldowns + class LUT.

Semantic versioning vMAJOR.MINOR.

MINOR adjusts thresholds/weights/cooldowns; MAJOR changes taxonomy or scoring model.

Universe Policy Rev: monotonically increasing integer; captures hysteresis & N_base, TTL rules.

13.2 Config hash (what it covers)

config_hash = sha256( canonical_json({ FP, DP, thresholds, weights, budgets, cooldowns, novelty_half_lives, universe_policy_rev }) )

Canonicalization: sort keys, stringify numbers with fixed precision, strip whitespace.

Stored in: every event (provenance.config_hash), anomaly_event, and curator_runs.

13.3 Producer provenance

Every event also includes:

producer (binary and version),

git_commit (short hash of repo at build),

source_lag_ms, clock_skew_ms (runtime),

universe_policy_rev (selection rules),

environment tag (env=prod|stg if desired).

13.4 Evolution workflow

Proposal (Curator) — changes to DP (thresholds, weights) or FP (new columns) with rationale + replay results.

Canary — enable for a small symbol set or to a shadow topic; compare event counts/severities and DQ impacts.

Apply — bump FP/DP versions, recompute config_hash, deploy.

Archive — write change log entry; store diffs in config_proposals with status=applied.

Contracts

Events: add fields only; breaking changes → new topic alpha.events.vX.

Tables: add columns only; deprecations marked in feature_registry/detector_registry with deprecated_at, kept nullable until a major version.

13.5 Reproducibility recipe

To reproduce an event E:

Read E.payload and E.provenance (FP, DP, config_hash, git_commit).

Check out git_commit; load FP/DP that match the versions.

Rehydrate baseline_state and features_snapshot rows for the asset at exchange_ts and preceding warm-up window.

Run detector with the specified config; confirm severity and payload match.

If not: compare baseline_state or feature values for drift; root-cause via curator_runs logs.

13.6 Deprecation lifecycle

Shadow a detector first (emit to internal table, not events).

When replaced: mark deprecated_at in detector_registry; keep code path for ≥30 days to support replays.

Remove only on next MAJOR DP, and only when replays for the affected window are no longer required.

13.7 Backward compatibility expectations

Consumers must ignore unknown fields in events.

Consumers must not rely on array lengths (e.g., rs_top) or on ordering beyond specification.

Severity is comparable within class, not across classes.

13.8 Change log discipline

Maintain a human-readable Change Log section at the end of this .md (also stored in DB) that tracks:

FP/DP version bumps,

Added/removed detectors/features,

Threshold/weight changes,

Universe policy rev increments (with reason),

Backfills and replays.

With these three sections, the pipeline has a clear event contract, durable storage, and provable lineage/versioning—so downstream systems can trust, replay, and evolve against it.
Ready for the next set: §14 Curator (Internal Intelligence) Design, §15 Rollups & Retention, §16 Backfill & Replay Strategy.

You said:
ok, next 3
ChatGPT said:
14) Curator (Internal Intelligence) Design

Purpose: keep the detector sharp without ever making trades. The Curator observes, measures, and proposes—it does not alter the hot path directly.

14.1 Role & boundaries

Reads: feature snapshots, market snapshots, anomaly events, registries, and DQ metrics.

Writes: insights, config proposals, replay results, its own run logs.

May trigger: shadow/canary replays of detectors with proposed configs.

May not: publish live events, change code at runtime, or emit decisions/trades.

14.2 Operating cadence

Every minute: lightweight monitors (event budgets, suppression counts, DQ spikes).

Hourly: baseline drift checks, severity histogram calibration, universe churn review.

Daily: golden-minute replays, threshold sweeps, quantile sketch compaction, weekly report draft.

On-trigger: immediate run when flood/drought, drift, or DQ incident detected.

14.3 Monitors (always-on, statistical)

Baseline drift

Target: mean(z_*) ≈ 0, std(z_*) ≈ 1 per asset×tf.

Trigger: |mean| > 0.2 or std ∉ [0.8,1.2] for K bars → propose decay/HL tweak or split by time-of-day.

Event health

Keep per-class event rates within bands and with healthy tail (p90 severity not collapsing).

Trigger: sustained flood/drought → propose threshold/cooldown adjustments.

Suppression audit

Track suppressed events by reason (DQ, budget, illiquidity, warm-up).

Trigger: >10% suppressions for a class over 6h → investigate guardrails or budgets.

Universe churn & coverage

Churn ≤ C/hour; coverage ≥ 95% of dollar volume last 24h via (universe ∪ hotlist).

Trigger: violations → hysteresis/TTL/size proposals.

DQ posture

Assets with frequent partial/stale, rising book_staleness_ms, or oi_staleness_ms.

Trigger: propose relaxed reliance (disable micro detectors) or REST cadence tuning.

Performance monitoring (Phase 6 Addition)

Detector accuracy drift

Target: accuracy ≥ 0.60 for top detectors, f1_score ≥ 0.50 for active detectors.

Trigger: accuracy < 0.55 for 24h OR accuracy dropping > 0.05/week → propose threshold adjustments or detector disable.

Regime-specific performance

Target: detectors perform well in their intended market regimes.

Trigger: accuracy < 0.45 in intended regime for 48h → propose regime-specific threshold adjustments.

Signal quality degradation

Target: f1_score ≥ 0.50 for active detectors, win_rate ≥ 0.55 for pattern detectors.

Trigger: f1_score < 0.45 for 12h OR win_rate < 0.45 for 24h → propose cooldown increases or feature adjustments.

Drawdown protection

Target: max_drawdown < 0.20 for any detector over 7-day rolling window.

Trigger: max_drawdown > 0.25 for 24h → propose detector disable or threshold increases.

Market regime adaptation

Target: detector performance adapts to changing market conditions.

Trigger: performance drops > 0.15 when regime changes → propose regime-specific configurations.

14.4 Proposals (structured diffs, not code)

Detector tuning: thresholds, cooldowns, half-life per class (asset-tier aware).

Severity weights: per-class (w1,w2,w3,a) nudges based on histogram fit.

Gates: asset-specific v_min/spread_cap from empirical distributions.

Universe policy: N_base, entry/exit bands, K_entry/K_exit, TTL schedule.

Feature pack minor: enabling a new normalized column or cheap flag (already computed in extras_json).

Performance-based proposals (Phase 6 Addition)

Detector performance tuning: thresholds, cooldowns based on real trading results.

Regime-specific configurations: different thresholds for different market conditions.

Detector enable/disable: based on performance degradation or drawdown limits.

Feature importance weighting: adjust detector inputs based on performance correlation.

Format (example):

{
  "proposal_id": "perf_20250103_001",
  "target": "detector_pack",
  "type": "performance_based_tuning",
  "diff": {
    "pattern.diagonal_support_break": { 
      "threshold": { "old": 0.75, "new": 0.82 },
      "cooldown_sec": { "old": 300, "new": 450 }
    }
  },
  "rationale": "Accuracy dropped to 0.52 in ranging markets; increasing threshold and cooldown",
  "evidence": {
    "performance_data": {
      "accuracy_trending": 0.78,
      "accuracy_ranging": 0.52,
      "total_signals": 156,
      "time_window": "2025-01-01 to 2025-01-03"
    },
    "market_regime_analysis": "Ranging markets show 26% accuracy drop"
  },
  "status": "proposed"
}

Regime-specific proposal example:

{
  "proposal_id": "regime_20250103_002",
  "target": "detector_pack",
  "type": "regime_specific_config",
  "diff": {
    "div.price_rsi_bear_m_5": {
      "regime_configs": {
        "trending_up": { "threshold": 0.65, "cooldown_sec": 180 },
        "trending_down": { "threshold": 0.55, "cooldown_sec": 120 },
        "ranging": { "threshold": 0.80, "cooldown_sec": 300 }
      }
    }
  },
  "rationale": "RSI divergence performs differently across market regimes",
  "evidence": {
    "regime_performance": {
      "trending_up": { "accuracy": 0.72, "signals": 45 },
      "trending_down": { "accuracy": 0.68, "signals": 38 },
      "ranging": { "accuracy": 0.45, "signals": 23 }
    }
  },
  "status": "proposed"
}

14.5 Replay harness (gatekeeper)

Inputs: exact FP/DP versions, config_diff, golden minutes pack, last N days slice.

Execution: re-run detectors against stored feature snapshots; never touch live bus.

Outputs: replay_results with event counts by class, severity distributions, suppression deltas, runtime budgets.

Pass criteria: within configured deltas (e.g., −20%..+10% events), p90 severity ≥ baseline−5, no DQ-induced side effects.

Only after pass (and optional manual approval) does Curator flip status → applied, bump pack version, and roll to prod.

14.6 LLM-assisted analyses (offline, bounded)

Weekly summaries: human-readable briefs (“BTC-led impulses fell 37% WoW; spread-stress spikes doubled during US open.”).

Pattern mining drafts: co-occurrence/ordering hypotheses (e.g., “basis_jolt → price_up_cvd_down within 5m, support 28%”).

Root-cause notes: narratives for recurring DQ or flood incidents.

Constraints: capped tokens/run; structured prompts; outputs are insights, not automatic changes.

14.7 Artifacts (tables)

curator_runs (who/when/what), insights (append-only), config_proposals (diffs), replay_results (metrics), weekly_reports (optional).

14.8 Failure containment

If Curator crashes: detector hot path continues unaffected.

If Curator proposes a bad config: replay harness vetoes. No hot changes allowed.

If replays drift (non-determinism): block apply, open incident, enumerate provenance mismatches.

15) Rollups & Retention

Purpose: define exactly how 15m and 1h rows are derived, what carries vs recomputes, and how we keep storage lean without losing analysis power.

15.1 Philosophy

1m is authoritative. All aggregates derive from it.

Recompute, don’t average: higher-tf features must have the same semantics at that tf.

Independent baselines per tf. z_* at 15m uses 15m baselines.

15.2 Aggregation map (1m → 15m → 1h)

OHLC

open = first minute’s open

close = last minute’s close

high = max of minute high

low = min of minute low

mid_close = last minute’s mid_close

Volume & counts

v_buy_*, v_sell_*, v_total_* = sum over minutes

trade_count_* = sum

Returns

For tf T:

ret_T = (mid_close(t) − mid_close(t−T)) / mid_close(t−T) using tf-aligned previous close.

ret_abs_T = abs(ret_T)

Do not average 1m returns; recompute from mid_close.

Realized vol / ATR

rv_T = sqrt( Σ within T of (Δlog(mid_close_minute))^2 ) or recomputed from BBO if available at that tf window.

atr_proxy_T = (high − low) / mid_close at the tf.

Flow / CVD

cvd_delta_T = sum of cvd_delta_m_1 over the window.

cvd_level retains end-of-window level (daily-anchored).

cvd_slope_T*k = slope over last k tf bars (e.g., for 15m tf, slope over 5×15m = 75m window) — name as cvd_slope_m_75 to preserve absolute units.

Positioning

oi_open/close = first/last minute values available in window (prefer freshest near boundaries).

oi_min/max = min/max within window.

oi_delta_T = oi_close − oi_close(t−T); oi_roc_T = oi_delta_T / oi_close(t−T).

liq_count_T/liq_notional_T = sum (if feed exists).

Perp state

funding_h_1 at 15m/1h rows = last known funding rate at window end (not averaged).

basis_bp_T = rolling mean of (mark−index)/index * 10_000 over the last T minutes, recomputed at tf.

Microstructure

spread_mean_T = time-weighted mean of 1m spread_mean_m_1, weighted by minute activity (e.g., v_total_m_1 or time if neutral).

spread_p95_T = 95th percentile of minute spreads (use TDigest merge).

obi_top5_mean_T, depth_top5_quote_median_T = recompute via TDigest/weighted average over minutes with valid L2; if insufficient L2 coverage, set NULL and bump DQ at tf.

Normalized & baselines

For tf row, produce z_* and q_* at that tf (e.g., z_vol_m_15, z_spread_m_15, z_oi_roc_m_15, z_basis_m_15). Do not transform 1m z to 15m z.

Cheap flags at higher tf

Re-evaluate with tf-appropriate z/thresholds (e.g., is_vol_spike_m_15).

15.3 Rollup mechanics

Trigger: when last constituent minute closes and grace windows have elapsed.

Idempotent: recompute and UPSERT the tf row. If any 1m bar inside the window was amended within grace, refold.

Missing data: if ≥X% of constituent minutes have dq_status!='ok', mark tf row dq='partial'; with ≥Y% missing, dq='stale' and suppress detectors at that tf.

Defaults: X=10%, Y=30%.

15.4 Retention & pruning

Drop oldest partitions by tf according to policy:

1m: keep ≈90d

15m: keep ≈1y

1h: keep ≈3y

Compression: compress chunks older than 7d; keep anomaly_event ≥1y uncompressed indices for search speed.

15.5 Rollup validation

Periodic checks compare:

Σ v_total_m_1 vs v_total_m_15 (exact equality)

Boundary conditions: open/close consistency, high/low enclosure

Derived metrics (e.g., oi_delta_T) match recomputation from edges

Alerts on deviations → Curator insight.

16) Backfill & Replay Strategy

Purpose: bootstrap cold starts, repair gaps, and prove determinism via replays—without contaminating provenance or mixing sources.

16.1 Cold start (bootstrap)

Seed 1m OHLCV with candleSnapshot for last K minutes (e.g., 120):

Populate open/high/low/close, v_total_m_1, trade_count_m_1 (if provided).

Set source='candle_snapshot' in features_snapshot.provenance.

Leave micro/positioning fields NULL.

Normalization:

Do not emit z_* until baselines warm per §4 (min_samples).

Quantiles may start with low confidence; set q_confidence='low' (if you add this flag).

Events: disabled during bootstrap window (configurable), or gated by warmup==FALSE.

16.2 Historical backfill (repairs)

Source of truth: backfills must come from one source per field:

Use candleSnapshot only for OHLCV.

Use stored anomaly_event if reconstructing context is required (do not recalc from candles).

Scope: prefer forward-only backfills (fill recent past), avoid rewriting old months unless legal/compliance requires.

Provenance: mark rows source='backfill', attach backfill_job_id, and write an audit entry.

16.3 Replay (determinism proof)

Golden minutes pack: 10 curated windows (squeeze, cascade, rug, dead book, basis jolt, spread stress, low-liquidity false spike, etc.). Stored as frozen feature snapshots + market snapshots + prior baseline state.

Config seal: replays run with specified FP/DP and config_hash; results must be bit-identical event payloads.

Publication: replays publish to alpha.events.replay.v0 with provenance.replay_of=true.

CI gate: any change to detector code or pack must pass all golden minutes, then a “most recent day” replay slice with tolerances (counts/severity deltas under bounds).

16.4 Late data and re-emission

Within grace: it’s not a replay—normal upsert and (if severity materially changes) event re-emit is allowed by debounce rules.

After grace: do not alter historical tf rows; instead:

Append a late_data_note to Curator insights.

Optionally run a reconciliation replay tagged as repair to quantify impact (no live event corrections).

16.5 What we never do

Mix candles and minute-built ticks for the same bar (choose one; provenance enforces).

Backfill normalized fields from candles (no baselines there).

Rewrite anomaly_event rows (append-only); if truly wrong, write a follow-up correction record referencing event_id.

16.6 Operational runbook (backfill/replay)

Backfill

Define window & fields; compute job id/hash.

Ingest with provenance marks; do not emit events during backfill.

Recompute rollups strictly within window; DQ set to partial.

Log audit & diff basic aggregates vs existing data.

Replay

Select FP/DP/config; freeze baseline_state snapshot at start.

Load feature/market snapshots for window; run detectors.

Compare to reference: counts, severities, payload hashes.

Publish to replay topic; store replay_results.

16.7 Curator hooks

If replays routinely fail bit-identical checks, open incident and pin root cause (non-deterministic clocks, floating-point drift, nondeterministic JSON ordering). Propose fixes (decimal quantization, canonical JSON serializer).

With §§14–16, the detector gains a self-improving brain (Curator), precise aggregation/retention rules, and a disciplined backfill/replay practice—the three pillars that prevent entropy as we scale. Ready for the next trio: §17 Operational Envelope, §18 Observability & QA, §19 Configuration Management when you are.

You said:
Next 3
ChatGPT said:
Thought for 17s
17) Operational Envelope

Purpose: define latency/throughput targets, degradation paths, failure handling, and idempotency so the detector is predictable under load.

17.1 Latency & throughput targets (Top-N ≈ 25 + hotlist ≈ 10)

Minute close → 1m row persisted: p95 < 300 ms, p99 < 500 ms
(assemble features, baselines, z/quantiles, DQ)

Market snapshot compute: p95 < 50 ms

Detector pass + event publish: p95 < 150 ms (after snapshot write)

Total end-to-end (bar close → events on bus): p95 < 450 ms

WS ingest headroom: sustain ≥ 5× average trade rate for Top-N (burst tolerance)

If any minute exceeds 500 ms, auto-defer detectors for lowest-tier names (log detectors_deferred=1) and recover next minute.

17.2 Concurrency model (shard by asset)

Ingest shards: 1 WS client per feed group (trades+candle+bbo; optional l2Book).

Per-asset accumulators: lock-free ring buffers.

Minute close workers: a bounded work-queue keyed by asset_uid; each task runs the 7-step assembly (Section 2.3).

Detector worker: runs after a bar’s snapshot is persisted (reads that row + current market snapshot).

Backpressure: if the minute queue > threshold, pause detector worker for tail assets first.

17.3 Degradation paths (graceful, explicit)

Microstructure degrade: if l2Book stale or missing → set micro features NULL, mark DQ partial, auto-disable micro detectors.

Positioning degrade: if oi_staleness_ms > 20 s → set OI-dependent features NULL; suppress OI detectors.

Compute pressure: if snapshot p95 > 300 ms → skip detector pass for bottom-ranked 20% assets for that minute.

Event surge: enforce per-class budgets (Section 10.6); drop lowest severity first; never drop snapshot writes.

Cold start: run with warmup=TRUE; events suppressed until baselines ready.

17.4 Failure handling (hot path)

WS disconnect: exponential backoff; mark affected minutes stale; never retro-synthesize ticks.

Clock drift: if |clock_skew_ms|>1 s, escalate DQ to partial; if >3 s, stale and suppress events.

Malformed messages: drop, increment dropped_ticks, include in DQ; never crash workers.

Disk full / DB write errors:

First failure: switch to write-ahead NDJSON log on disk, raise storage_degraded=1, alert.

Recovery: batch-ingest the log to DB; guarantee idempotent UPSERTs.

REST rate-limit: backoff + jitter; skip non-critical polls (e.g., funding history) before OI/contexts.

17.5 Idempotency & state

Snapshots: UPSERT by (asset_uid, tf, exchange_ts); “last write within grace wins”.

Debounce state: per (symbol:class:tf), stored in memory + checkpointed every minute; on restart, restore from last N anomaly_event rows.

Baselines & quantiles: persisted every minute; on restart, reload before first compute.

Event bus: at-least-once; dedupe by event_id (UUIDv7) downstream.

17.6 Deployment topology

Processes:

ingest (WS & accumulators),

builder (assembly + rollups),

detector (events),

curator (out-of-band),

publisher (bus/DB writers).

Scaling: horizontal by asset shards (hash(asset_uid)%S).

Upgrades: blue/green or canary (10% assets) → observe metrics → roll.

17.7 SLAs / SLOs (starter)

Availability (hot path): 99.9%/30d

Minute completion p95: ≤ 300 ms

Event suppression (budget): ≤ 5% of attempted

DQ ok-rate: ≥ 95% of minutes for top-tier assets

18) Observability & QA

Purpose: ensure we can see liveness/quality in real time and prove correctness offline.

18.1 Metrics (Prometheus-style names)

Ingest

hl_ws_messages_total{feed,type}

hl_ws_disconnects_total{feed} / hl_ws_reconnect_seconds{feed}

alpha_ingest_book_staleness_ms{symbol} (gauge)

Assembly

alpha_bar_finalize_latency_ms{tf} (histogram)

alpha_snapshot_writes_total{tf,status}

alpha_baseline_updates_total{feature,tf}

Quality

alpha_dq_status_count{status}

alpha_null_rate{feature}

alpha_clock_skew_ms (histogram)

Detectors & Events

alpha_detector_triggers_total{class,subtype}

alpha_event_published_total{class}

alpha_event_suppressed_total{reason}

alpha_severity_histogram{class}

Budgets & Backpressure

alpha_budget_utilization{class} (0–1)

alpha_deferred_detectors_total{tier}

Curator

alpha_curator_proposals_total{status}

alpha_replay_pass_rate{window}

18.2 Dashboards (four panes)

Ingest Health: WS rates, reconnects, book staleness, OI staleness.

Minute Pipeline: finalize latency, write errors, DQ split, null rates by feature.

Events: triggers vs published vs suppressed, severity distributions, class mix, budgets.

Curator & Drift: z-mean/std by feature, replay pass/fail, proposal queue.

18.3 Alerts (examples)

WS flap: hl_ws_disconnects_total rate > 3/5m.

Latency breach: alpha_bar_finalize_latency_ms_p95 > 500 for 5m.

DQ deterioration: alpha_dq_status_count{status="stale"} > 1% for 15m.

Event flood: alpha_event_published_total > global cap for 1m OR suppression > 10%.

Drift: |mean(z_vol_m_1)| > 0.2 or std outside [0.8,1.2] for 60m on any top-tier asset.

Curator stalled: no replay_pass in 48h.

18.4 Logging & tracing

Structured logs with asset_uid, tf, exchange_ts, event_id, debounce_key, universe_rev, config_hash.

Trace IDs: every minute assembly attaches a trace; detector logs link to the same trace.

Audit logs: all config changes (packs, thresholds, budgets) with approver & diff.

18.5 QA layers

Unit tests: formula correctness for each feature (edge cases: no trades, spreads zero, negative sizes).

Property tests: invariants (OHLC enclosure, return recomputation, rollup equalities).

Fuzz tests: malformed WS payloads, timestamp regressions, out-of-order trades.

Golden minutes CI: run detectors on 10 frozen windows; assert bit-identical event payloads.

Replay CI (daily): last 24h slice; assert event counts & severity histograms within tolerances.

18.6 Synthetic generators (optional but useful)

Stress scenarios: programmed squeezes, cascade selloffs, spread blowouts.

Use to validate detector sensitivity and suppression behavior.

19) Configuration Management

Purpose: make detector behavior declarative, reviewable, and reversible—without runtime surprises.

19.1 Sources of truth

Feature Pack (FP): columns, formulas, windows (YAML/JSON in repo + feature_registry).

Detector Pack (DP): detectors, thresholds, weights, cooldowns, half-lives, budgets (YAML/JSON in repo + detector_registry).

Universe Policy: N_base, entry/exit bands, streaks, TTL mapping (YAML/JSON + DB).

Runtime Config: environment knobs (URLs, partitions, grace windows).

Secrets: managed outside packs (vault), never embedded.

All configs validated by JSON-Schema (or Pydantic) and stamped with config_hash used in events.

19.2 Loading & update model

Boot: load FP/DP/Universe from DB (latest active) or from files pinned by env; compute config_hash.

Runtime update: hot-reload only DP/universe via atomic swap:

New config → validate (schema, bounds).

Canary enablement flag: {enable_for: [asset_uids…]} or % of assets.

Start a config_epoch with start time; both epochs may run in parallel for canary vs control.

On promote: set active=true, bump detector_pack.version, persist; store diff and new config_hash.

Rollback: flip to previous epoch (stored), publish rollback notice in audit.

Feature packs (columns) require code & DB migration → deploy gates (cannot hot-reload).

19.3 Feature flags & kill-switches

Per-detector flags: enabled=true/false, cooldown_override, threshold_override.

Per-class budgets: adjustable at runtime (bounded ranges).

Per-asset tier overrides: e.g., looser thresholds for top decile liquidity.

Global kill: emit_events=false (snapshots still written).

All flags live in DP and are hashed into config_hash.

19.4 Environments & promotion

dev → stg → prod pipeline:

dev uses synthetic feeds; stg replays last 24h; prod is live.

Promotion requires: green unit/property tests, golden minutes equal, replay deltas within bounds, SRE approval.

Time-boxed freezes: restrict config changes during known high-vol windows (e.g., CPI prints) unless emergency.

19.5 Schema & example snippets

Detector pack (excerpt):

detector_pack: v0.1.7
class_defaults:
  spike: { cooldown_sec: 45, half_life_sec: 120, weights: { w1: 1.0, w2: 0.5, w3: 0.4, a: 0.6 } }
  shift: { cooldown_sec: 90, half_life_sec: 300, weights: { w1: 0.7, w2: 0.8, w3: 0.2, a: 0.55 } }
detectors:
  - id: spike.vol_spike_m_1
    enabled: true
    threshold: 3.0
    inputs: [z_vol_m_1, ret_m_1, v_total_m_1]
    preconditions: [dq_ok, not_illiquid, trade_count_ge_5]
  - id: shift.basis_jolt_m_5
    enabled: true
    threshold_z: 2.5
budgets:
  per_symbol_per_minute: { spike: 4, shift: 2, quadrant: 2, divergence: 2, sync: 2, rotation: 1 }
overrides:
  tiers:
    top: { spike: { threshold: 3.2 } }
    tail: { spike: { threshold: 3.8 }, budgets: { spike: 2 } }


Universe policy (excerpt):

universe_policy_rev: 17
n_base: 25
entry_band: { n_entry: 22, k_entry: 3 }
exit_band:  { n_exit: 30, k_exit: 5 }
freeze_min: 5
min_dwell_min: 30
hotlist:
  s_hot: 70
  ttl_base_min: 15
  ttl_k_min_per_point: 0.3

19.6 Auditing & approvals

Every change writes an audit row with {who, when, diff, rationale, env, proposal_id?}.

Optional two-man rule for prod: SRE + Quant must approve DP changes.

Weekly Curator report summarizes config churn & impact.

19.7 Failure-safe defaults

On config load failure: keep last good packs; raise alert; do not halt pipeline.

On partial apply: revert entire epoch; configs are all-or-nothing.

19.8 What not to configure

Schema/columns via DP—those belong to FP and code migrations.

Secrets/keys inside packs—managed via vaults and env-specific secret stores.

With §§17–19, the detector is operationally bounded, observable, and controllable.
If you’re happy with this, I’ll continue to §20 Extensibility Model, §21 Failure Modes & Mitigations, and §22 Security & Access Control next.

You said:
Next three
ChatGPT said:
20) Extensibility Model

Purpose: let us add features, detectors, and context logic without breaking consumers, slowing the hot path, or causing schema churn.

20.1 Principles

Additive evolution: we only add columns/fields; never repurpose.

Registries, not rewrites: new things are declared in feature_registry / detector_registry, then promoted.

Hot path is boring: detectors consume already-computed columns; they never compute expensive transforms inline.

Shadow → Canary → Promote: every addition runs dark first.

20.2 Adding a new feature (column)

Step 0 — Proposal (Curator or Engineer)

Provide: name, window, formula, inputs (existing columns only), units, expected null behavior, compute budget (µs per row).

Step 1 — Prototype (extras_json)

Implement compute in the 1m builder; write into extras_json only.

Add a feature_registry row with pack_proposed=v1.x-proto, status='shadow'.

Step 2 — QA

Unit/property tests for formula and edge cases (no trades, partial DQ).

Latency budget check (p95 ≤ 10 µs / asset-minute unless justified).

Step 3 — Promote

Add a typed column in next Feature Pack minor (e.g., v1.1).

Backfill forward only (no historical rewrite).

Update detectors that may use it (still optional).

Naming rules

<family>_<window> (e.g., microprice_drift_s_30).

Normalized/quantile variants are automatic in §4; do not add those manually.

20.3 Adding a new detector

Step 0 — Spec

What/Why (one sentence), class/subtype, inputs (columns), preconditions, trigger math, cooldown, half-life, severity weights.

Step 1 — Registry

Insert into detector_registry with enabled=false, status='shadow'.

Step 2 — Shadow mode

Run detector and write candidate outputs to an internal table (not the bus).

Verify budgets, latency, and suppression reasons.

Step 3 — Canary

Enable on ≤ 10% of assets (by tier) with live event publication to a replay topic.

Compare counts/severity distributions vs expectation.

Step 4 — Promote

Flip enabled=true, point to live topic, bump Detector Pack minor version.

Design constraints

Must read only from features_snapshot + market_snapshot.

No cross-asset scans inside a single detector (cross-asset context comes from §6).

Compute budget: ≤ 50 µs per asset-minute on average.

20.4 Extending market context

New scalar (e.g., rs_dispersion_m_5): add to market_snapshot as a typed column; fill with NULL until ready.

New arrays/maps (e.g., sector leaders): add JSONB fields with fixed caps (≤ 16 items).

Promotion path: shadow → canary → promote; update event payload optionally to include it.

20.5 Version & compatibility guardrails

Feature Pack (FP) bumps on column adds; Detector Pack (DP) bumps on detector changes.

Events: add fields only; breaking change → new topic.

Consumers must ignore unknown fields; we enforce in consumer contract tests.

20.6 Code structure (plugin-like)

/packs/feature/: declarative YAML + code-gen for columns & formulas.

/packs/detector/: registry YAML → auto-wires detector functions.

/curator/: monitors and proposal generators.

/replay/: deterministic runner used by CI and Curator.

20.7 Performance safety nets

Per-detector microbench (CI gate).

Build-time “cost map” (µs per feature) surfaced in docs; Curator flags regressions.

Backoff switches: per-detector enabled=false feature flag; class budgets adjustable at runtime (bounded).

21) Failure Modes & Mitigations

Purpose: enumerate realistic ways the detector can fail and the pre-baked responses that keep it safe and explainable.

21.1 Data-plane failures

WS disconnect / packet loss

Symptom: gaps; book_staleness_ms spikes; no trades in minute.

Mitigation: mark minute dq='stale', suppress detectors, attempt reconnect with backoff; never synthesize missing ticks.

Clock skew (exchange vs local)

Symptom: negative/duplicated minute binning; out-of-order “close” signals.

Mitigation: use exchange ts for lattice; escalate DQ per §8; if |skew|>3s, suppress; raise alert.

REST staleness / rate-limit

Symptom: OI or funding stale; 429s.

Mitigation: backoff w/ jitter; preserve last good snapshot; suppress OI/funding detectors; Curator may lower cadence or change schedule.

Symbol remap / delist / listing

Symptom: symbol disappears or changes id; spot/perp mapping breaks.

Mitigation: alias map table; freeze old asset_uid and create new one; never reuse IDs; hotlist & universe recalc; Curator raises “remap” insight.

Candle vs tick divergence

Symptom: bootstrap candles disagree with tick-built bars.

Mitigation: provenance separates sources; 1m tick-built is authoritative once live; no merging.

Extreme volatility / outlier prints

Symptom: z-scores explode; event floods.

Mitigation: IQR clamp for scoring, per-class budgets, debounce, illiquidity gates; Curator may propose temporary thresholds.

L2 instability

Symptom: l2Book feed stalls or flaps.

Mitigation: set micro features NULL, DQ=partial, auto-disable micro detectors; re-enable after grace.

21.2 Compute/storage failures

Minute finalize over budget

Mitigation: detector deferral for tail assets; log detectors_deferred; Curator investigates hot spots.

DB outage / disk full

Mitigation: switch to write-ahead NDJSON spool; alert; on recovery, batch import with UPSERT; gaps are marked in DQ.

Baseline/quantile state corruption

Mitigation: checksums; if invalid, discard and require warm-up; Curator logs “baseline_reset”.

Partition bloat / slow queries

Mitigation: time-partition by (tf, month), compress ≥7d; VACUUM/ANALYZE jobs; index hygiene; cap extras_json size.

Non-determinism in replays

Symptom: payload hashes drift across environments.

Mitigation: canonical JSON serializer, decimal quantization, fixed RNG seeds (if any), pinned library versions.

21.3 Config/process failures

Bad detector config change

Mitigation: Curator replay gate; canary; fast rollback to prior config_epoch; events carry config_hash for forensics.

Budget misconfiguration

Mitigation: guard bounds in schema; Curator alerts when suppression > 10%; auto-revert to last known-good.

Universe thrash

Mitigation: hysteresis, freeze windows, churn caps; Curator can widen bands.

Curator runaway

Mitigation: proposals only; no hot-path writes; manual approval for DP/FP changes; replay must pass.

21.4 Black swans / market halts

No prints, spreads blow out → DQ=stale, event emission paused; metrics show flood of suppressions with reason=dq.

Exchange maintenance → stop ingest, write heartbeat; do not fabricate bars.

21.5 Incident runbooks (abbrev.)

WS flap: rotate endpoints, reduce subscription set to Top-10, increase backoff; after stable 10m, restore.

Sev flood: raise class thresholds via runtime override, widen cooldowns; note config_epoch in audit.

Baseline drift: freeze baseline updates, re-seed from last good snapshot; warm-up again; Curator documents.

22) Security & Access Control

Purpose: protect credentials, data, and change paths; ensure auditable, least-privilege operation.

22.1 Identities & roles

Service roles

ingest-svc: WS/REST read, no DB schema changes.

builder-svc: DB write to snapshots, read registries, no events bus admin.

detector-svc: read snapshots/market, publish to events, write anomaly_event.

curator-svc: read everything; write insights/proposals/replay_results; no event publishing.

ops-admin: approve config, run replays in prod; audited.

RBAC at DB/topic level; principle of least privilege.

22.2 Secrets & keys

Storage: Vault/KMS; never in repo or logs.

Rotation: at least quarterly or on incident.

Scope: separate keys per env (dev/stg/prod), per service.

Access: short-lived tokens; mTLS between services if internal mesh supports it.

22.3 Network & transport

All WS/REST over TLS.

Egress allow-list to HL endpoints only; deny-all baseline.

Internal service-to-DB connections via mTLS or IAM auth (cloud-native).

No inbound ports from the public internet to detector nodes.

22.4 Data protection

At rest: DB encryption (cloud-managed) + disk encryption for spools.

In transit: TLS everywhere.

Backups/DR: daily full + hourly WAL/incremental; restore tested monthly; RPO ≤ 1h, RTO ≤ 2h for snapshots; events re-playable from bus.

22.5 Audit & change control

Every config change (DP/FP/Universe) writes an audit row {who, when, diff, rationale, env} and links to proposal_id.

Two-man rule (optional, prod): Quant + SRE for Detector Pack changes.

Event provenance includes git_commit, config_hash, universe_policy_rev.

22.6 Supply-chain hygiene

Pinned deps with checksums; dependabot or equivalent review.

Build in hermetic containers; sign images; verify signatures at deploy.

Ban network during build to avoid supply-chain injection.

22.7 Logging hygiene

No secrets in logs.

Redact WS/REST headers (if any).

Structured logs only; capped field sizes; PII not applicable (but still treat symbols/IDs as sensitive metadata in shared environments).

22.8 Environment isolation

dev/stg/prod isolated projects/accounts; no cross-read of prod from dev.

Replay uses replay topics; prod bus is write-only for detector.

Test data never exported to prod; prod snapshots never copied to dev without sanitization.

22.9 Hardening & runtime

Read-only root filesystems for stateless services.

Seccomp/AppArmor (or cloud equivalent) profiles applied.

Resource limits (CPU/mem) enforce predictability; OOM killer policies tested.

22.10 Incident response

Security incident runbook: rotate secrets, revoke tokens, freeze configs (lock DP), enable verbose audit, snapshot DB, open ticket with severity.

Postmortem template includes: indicators, blast radius, data exfil risk, recovery actions, preventive controls.

These three sections make the detector easy to extend, hard to break, and safe to operate in production. If you want, I can continue with the final trio—§23 Performance & Capacity Planning, §24 Phase Roadmap & Milestones, §25 Acceptance Criteria & Exit Checklist—plus the appendices.

You said:
Next 3 
ChatGPT said:
Thought for 7s
23) Performance & Capacity Planning

Purpose: size the system with concrete budgets and formulae so we can predict cost, scale safely, and spot regressions early.

23.1 Baseline assumptions (tunable)

Active symbols: Top-N 25 + hotlist 10 (peak 35 concurrently “on”).

Cadence: 1-minute lattice; 15m/1h rollups derived from 1m.

Event rate envelope: per §10.6 caps → ≤ 11 events/symbol/hour worst-case (spike 4 + others 7); typical 2–4.

Event payload size: ~1.2–2.0 KB JSON (depends on arrays included).

Feature snapshot width: ~240–320 typed columns + DQ + membership + provenance.
Encoded row (binary/columnar DB): 2.0–3.5 KB (post compression 0.7–1.4 KB).

Market snapshot: ~1–3 KB per minute per tf.

We size to p95 traffic bursts 2–3× typical.

23.2 Storage footprint (order-of-magnitude)

Per symbol, per day:

1m features: 1440 rows/day × 2.5 KB ≈ 3.6 MB (uncompressed)
With compression 2:1 → ~1.8 MB/day

15m features: 96 rows × 2.5 KB ≈ 0.24 MB → ~0.12 MB/day compressed

1h features: 24 rows × 2.5 KB ≈ 0.06 MB → ~0.03 MB/day compressed

Events: assume 3 events/hour avg → 72/day × 1.6 KB ≈ 115 KB/day

Market snapshots (1m): 1440 × 1.5 KB ≈ 2.1 MB/day (shared across all assets)

For 35 symbols:

1m features: 35 × 1.8 MB ≈ 63 MB/day

15m + 1h: 35 × (0.12 + 0.03) ≈ 5.25 MB/day

Events: 35 × 0.115 ≈ 4 MB/day

Market snapshots: ~2.1 MB/day (shared)

Total daily (compressed, 35 symbols): ~74–80 MB/day
Retention target (1m 90d, 15m 1y, 1h 3y): ~7–9 GB steady-state, plus indices (~30–50%).

Scale linearly: for 100 symbols, ~210–230 MB/day compressed.

23.3 Throughput & CPU budgets

Per minute, per symbol (steady):

1m assembly + normalization + write: ~50–120 µs CPU (no L2)
Add L2 microstructure: +50–150 µs

Detector evaluation (all classes, gated): ≤ 50 µs

Rollups amortized: negligible per symbol compared to 1m path.

Node sizing (illustrative):

1 vCPU can comfortably process 10–20 symbols end-to-end at p95 < 300 ms with headroom.

For 35 symbols, allocate 3–4 vCPU for builder/detector combined (plus 1 vCPU for ingest IO & publisher).

23.4 Bus capacity (events)

Worst-case spike: global cap 800 events/min (§10.6) ⇒ ~13 events/s.

With 1.6 KB payloads → ~20 KB/s egress; trivial for Kafka/NATS.

Partitioning: ≥ 8 partitions (hash by asset_uid) for smooth consumer scaling.

23.5 DB capacity & indexes

Write QPS: 35 symbols × 1 row/min (1m tf) + rollups + market rows ⇒ ~40–50 writes/min; with occasional upserts within grace.
Plenty of headroom on a single medium instance (e.g., Postgres/Timescale).

Indexes:

PK on (asset_uid, tf, exchange_ts)

Secondary (asset_uid, exchange_ts DESC)

Partial on (is_hot = true)

GIN on anomaly_event.payload

23.6 Latency SLO checks (from §17)

Bar close → snapshot persisted: p95 < 300 ms, p99 < 500 ms.

Snapshot → event published: p95 < 150 ms.

Total end-to-end: p95 < 450 ms.

Load test recipe: synthetic bursts at 3× average trade rate for 10 minutes; SLOs must hold and degraded modes engage predictably (detector deferrals, budget drops).

23.7 Cost control levers

Tighten Top-N sizing; tiered thresholds for tails reduce event volume.

Compression on partitions >7 days; drop 1m beyond 90d.

Push heavy enrichment (e.g., chart/LLM) to consumers on demand.

Curator can auto-tune budgets to stay within per-day event envelopes.

23.8 Capacity headroom plan

50% headroom CPU at typical; scale builder/detector horizontally via asset shards.

Backpressure policy triggers before p95 > 500 ms (defer tail detectors).

Quarterly re-size using actual metrics: row sizes, event rates, compression ratios.

24) Phase Roadmap & Milestones

Purpose: deliver value incrementally without compromising quality. Each phase has acceptance gates and rolls forward only when green.

Phase 0 — Bootstrap (Weeks 1–2)

Scope

WS ingest (trades, candle, bbo).

1m assembly for price/volume + DQ fields.

Minimal normalization (vol/ret_abs) with warm-up.

Basic spike detectors: spike.vol_spike_m_1, spike.price_spike_*.

Event publication to staging topic only.

Metrics: latency, DQ, trigger counts.

Milestones

M0.1: First snapshots written, p95 < 300 ms on 10 symbols.

M0.2: Events visible in stg; golden minutes pack defined.

Gate

Golden minutes CI passes (bit-identical), SLOs met on 10 symbols.

Phase 1 — Core v1.0 (Weeks 3–5)

Scope

Full feature pack v1.0 (Sections 5.1–5.6).

Baselines & quantiles per §4; IQR clamp for severity only.

Event catalogue v0.1 (Sections 9.2–9.7).

Severity/novelty/debounce per §10, budgets enforced.

Market snapshot builder (§6 core).

Universe policy & hotlist (Section 7).

Storage schemas (Section 12) live.

Milestones

M1.1: All detectors shadowed; severity histograms stable.

M1.2: Live events to alpha.events.v0 (prod) for Top-10.

Gate

Replay CI (last 24h) within tolerances; suppression < 5%; DQ ok-rate ≥ 95% on Top-10.

Phase 2 — Rollups & Retention (Weeks 6–7)

Scope

15m & 1h rollups (recompute, not average).

Retention/pruning jobs (1m 90d, 15m 1y, 1h 3y).

Partitioning & compression; index hygiene.

Milestones

M2.1: Rollups validated (Σ volume equalities, OHLC enclosure).

M2.2: Storage footprint matches plan ±15%.

Gate

Rollup validation suite green; query latency (recent cross-section) < 100 ms p95.

Phase 3 — Microstructure & Positioning (Weeks 8–10)

Scope

L2-based features (spread_p95, OBI, depth) guarded by DQ.

OI polling cadence; positioning detectors (oi_spike_*, quadrant.*).

Basis/funding (basis_jolt, funding_jolt) with staleness rules.

Milestones

M3.1: L2-guarded detectors produce stable signals (low false positives on thin books).

M3.2: OI freshness ≥ 95% within 20s.

Gate

Suppression due to DQ < 10% for micro detectors; severity distributions healthy.

Phase 4 — Curator & Replays (Weeks 11–13)

Scope

Curator v0.1 (statistical monitors, proposals, budget/threshold diffs).

Replay harness (golden minutes + recent day).

Config epochs, canary & rollback workflows.

Milestones

M4.1: First proposals generated & applied via canary.

M4.2: Weekly Curator report produced automatically.

Gate

Zero hot-path mutations; proposals only via replay-approved packs.

Phase 5 — Hardening & Extensibility (Weeks 14–16)

Scope

Failure runbooks exercised (WS flap, DB outage, flood).

Shadow new detectors (divergence/synchrony/rotation refinements).

Extensibility plumbing (extras_json → promotion path).

Security posture (RBAC, secrets, audit).

Milestones

M5.1: Incident game-day pass.

M5.2: New feature promoted from extras_json to column via FP minor bump.

Gate

All SLOs met at 35 symbols; ops dashboard complete; audit trail validated.

25) Acceptance Criteria & Exit Checklist

Purpose: define “done” for v1.0 so we don’t ship an ambiguous prototype.

25.1 Functional acceptance (v1.0)

Ingest & Assembly

WS ingest stable across trades, candle, bbo (optionally l2Book).

1m snapshots contain all v1.0 columns with correct naming & units.

DQ fields present and accurate; warm-up honored.

Normalization

Baselines persist & restore; z-means in [−0.2, +0.2] and z-std in [0.8, 1.2] for top assets (7-day window).

Quantile digests restored after restart with continuity.

Detectors

All v0.1 detectors enabled; triggers match spec; no cross-asset scans inside detectors.

Severity/novelty/debounce behavior exactly per §10.

Events

Event payloads conform to §11; UUIDv7, provenance filled, config_hash correct.

Budgets enforced; suppression metrics populated.

Market Context

Market snapshots written per minute with leader, RS arrays, dispersion; approx flag set when applicable.

25.2 Non-functional acceptance

Latency: end-to-end (bar close → bus) p95 < 450 ms, p99 < 800 ms at 35 symbols.

Reliability: Availability 99.9%/30d of hot path; graceful degrade paths verified.

Determinism: Golden minutes replay produces bit-identical payloads; last-day replay within tolerance bands.

Storage: Daily growth within ±20% of plan; retention/pruning jobs healthy.

25.3 Operational acceptance

Dashboards: ingest, pipeline, events, curator; all panels populated.

Alerts: WS flap, latency breach, DQ deterioration, event flood, drift, curator stalled.

Runbooks: WS reconnect, latency spike, DB outage, event flood; tested once.

RBAC: least-privilege service roles active; audit logs on config changes.

25.4 Security acceptance

Secrets in vault; no secrets in logs or repos.

TLS enforced; egress allow-list to HL endpoints.

Backups/DR tested (restore dry-run).

Image signing/verification configured; deps pinned.

25.5 Data & schema acceptance

Registries: feature_registry, detector_registry populated & in sync with repo packs.

Schema evolution: extras_json path exercised at least once; promotion to typed column via FP minor bump validated.

Provenance: events include feature_pack, detector_pack, config_hash, git_commit, universe_policy_rev, source_lag_ms.

25.6 Handoff artifacts

Build Plan .md (this doc) checked into repo.

Packs (feature, detector, universe) in versioned directories with JSON-Schema validators.

Golden minutes dataset & replay harness usage guide.

Ops runbook and on-call cheat-sheet.

Curator weekly report template & first report.

25.7 Exit checklist (one page)

 SLOs hit at 35 symbols; degraded modes verified

 v1.0 feature columns present; names & units validated

 Event payload contract v0.1 validated by consumer tests

 Budgets & debounce functioning; suppression < 5%

 Registries populated; packs versioned; config_hash stable

 Golden minutes: bit-identical; last-day replay within bounds

 Retention/pruning running; storage growth within plan

 Dashboards/alerts live; runbooks tested

 RBAC, secrets, TLS, backups, image signing verified

 Change log updated; go-live decision recorded (date/time, owners)

With §§23–25, the plan is fully “ship-able”: you have concrete sizing, a staged path to production, and crisp gate criteria to declare v1.0 done. If you want, I can round out the Appendices (feature dictionary, detector specs, example payloads, default thresholds) next.

You said:
Yes pls
ChatGPT said:
Thought for 36s
Appendix A — Feature Dictionary (v1.0)

Columns are per asset × timeframe × exchange_ts unless noted. Normalized (z_*) and quantiles (q_*) are produced per §4. Units are in quote currency unless specified. When NULL rules apply, DQ is incremented.

A.1 Identity, Membership, Provenance, DQ

asset_uid INT8 — canonical ID.

symbol TEXT — display symbol.

tf ENUM('1m','15m','1h')

exchange_ts TIMESTAMPTZ — lattice label (bar close).

ingest_ts TIMESTAMPTZ

feature_pack TEXT, pack_rev INT2, source TEXT('ws'|'candle_snapshot'|'backfill')

is_in_universe BOOL, is_hot BOOL, universe_rev INT4

dq_status ENUM('ok','partial','stale'), ingest_lag_ms INT2, dropped_ticks INT2, book_staleness_ms INT2, oi_staleness_ms INT4, warmup BOOL

A.2 Price / Returns / Vol

open, high, low, close DECIMAL — trade OHLC; NULL if no trades and no BBO → stale.

mid_close DECIMAL — (best_bid_close + best_ask_close)/2; NULL if BBO missing at close.

ret_s_30 DECIMAL — (mid_close − mid_{t−30s}) / mid_{t−30s}; NULL if lookback missing.

ret_m_1, ret_m_5, ret_m_15 DECIMAL — as above with minute lookbacks.

ret_abs_m_1 DECIMAL — abs(ret_m_1).

rv_m_1 DECIMAL — sqrt(Σ (Δlog(mid_i))^2) over intra-minute mid updates; fallback to trade mids; NULL if neither.

atr_proxy_m_1 DECIMAL — (high − low)/mid_close; NULL if any component is NULL.

Normalized: z_ret_abs_m_1; Quantiles: q_ret_abs_m_1.

A.3 Flow / CVD

v_buy_m_1, v_sell_m_1, v_total_m_1 DECIMAL — taker-labeled sums.

trade_count_m_1 INT4

cvd_delta_m_1 DECIMAL — v_buy_m_1 − v_sell_m_1.

cvd_level DECIMAL — running sum since 00:00 UTC; resets daily.

cvd_slope_m_5 DECIMAL — OLS slope of cvd_level over last 5 minutes.

Normalized: z_vol_m_1; Quantiles: q_vol_m_1.

A.4 Positioning (OI, Liqs)

oi_open, oi_close, oi_min, oi_max DECIMAL — freshest samples within minute; NULL if oi_staleness_ms>20_000.

oi_delta_m_5 DECIMAL — oi_close(t) − oi_close(t−5m); NULL if edges missing.

oi_roc_m_5 DECIMAL — oi_delta_m_5 / max(oi_close(t−5m), ε); NULL as above.

liq_count_m_5 INT4, liq_notional_m_5 DECIMAL — NULL if feed unavailable.

Normalized: z_oi_roc_m_5; Quantiles: q_oi_roc_m_5.

A.5 Perp State (Funding & Basis)

funding_h_1 DECIMAL — current/predicted hourly rate (HL venue preferred).

basis_bp_m_5 DECIMAL — mean of ((mark−index)/index)*10_000 over last 5m; NULL if index≤0 or missing.

time_to_next_funding_sec INT4 NULLABLE

Normalized: z_basis_m_5.

A.6 Liquidity / Microstructure

spread_mean_m_1 DECIMAL — time-weighted mean spread; NULL if BBO missing.

spread_p95_m_1 DECIMAL — 95th percentile spread; NULL if insufficient samples.

obi_top5_mean_m_1 DECIMAL — time-weighted mean of bid_depth/(bid_depth+ask_depth) over top-5 levels; NULL if L2 disabled/stale.

depth_top5_quote_median_m_1 DECIMAL — median top-5 sum depth (quote); NULL if L2 disabled/stale.

Normalized: z_spread_m_1.

A.7 Cheap Flags (booleans)

is_vol_spike_m_1, is_price_spike_up_m_1, is_price_spike_down_m_1,

is_oi_spike_up_m_5, is_oi_spike_down_m_5,

is_spread_stress_m_1, is_liq_cluster_m_5
NULL during warm-up; obey illiquidity & DQ gates.

A.8 RS Convenience

rs_score_m_5 DECIMAL — scalar per §6.3 (stored for easy ranking).

A.9 Baseline (robust) snapshots (subset)

b_mean_vol DECIMAL, b_scale_vol DECIMAL

b_mean_ret_abs DECIMAL, b_scale_ret_abs DECIMAL

b_mean_oi_roc DECIMAL, b_scale_oi_roc DECIMAL

b_mean_spread DECIMAL, b_scale_spread DECIMAL

b_mean_basis DECIMAL, b_scale_basis DECIMAL
(Used for audits; true state lives in baseline_state.)

A.10 Market Snapshot (per tf×exchange_ts)

leader TEXT, dominance_share DECIMAL(0..1)

shock_count_5s INT2, approx BOOL

rs_top JSONB(≤5), rs_bottom JSONB(≤5)

return_dispersion_m_5 DECIMAL, vol_dispersion_m_5 DECIMAL

time_to_next_funding_sec INT4 NULLABLE

excluded_count INT2

dq_status ENUM, universe_rev INT4

Appendix B — Detector Specs (v0.1, exact)

All detectors enforce: dq_status='ok' ∧ (is_in_universe ∨ is_hot) ∧ warmup=FALSE ∧ illiquidity guard. Severity, novelty, debounce per §10.

B.1 SPIKE

spike.vol_spike_m_1

Inputs: z_vol_m_1 (primary), z_ret_abs_m_1, ret_m_1, v_total_m_1, trade_count_m_1

Preconditions: trade_count_m_1 ≥ 5

Trigger: z_vol_m_1 ≥ 3.0

Cooldown: 45s · Half-life: 120s

Severity weights (class default): {w1:1.0,w2:0.5,w3:0.4,a:0.6}

Emit threshold: class T_spike = 65

spike.price_spike_up_m_1 / spike.price_spike_down_m_1

Inputs: z_ret_abs_m_1 (primary), ret_m_1, spread_mean_m_1

Trigger: z_ret_abs_m_1 ≥ 2.5 and sign defines subtype

Cooldown: 45s · Half-life: 120s

Weights: same as spike

Emit threshold: T_spike

spike.oi_spike_up_m_5 / spike.oi_spike_down_m_5

Inputs: z_oi_roc_m_5 (primary), oi_roc_m_5, ret_m_5, oi_staleness_ms

Preconditions: oi_staleness_ms ≤ 20_000

Trigger: z_oi_roc_m_5 ≥ 2.0 ∧ |oi_roc_m_5| ≥ 0.015

Cooldown: 60s · Half-life: 180s

Weights: {w1:0.9,w2:0.6,w3:0.3,a:0.58}

Emit threshold: T_spike

spike.liq_cluster_m_5 (if liq feed)

Inputs: liq_count_m_5 (primary), liq_notional_m_5, z_ret_abs_m_1, z_vol_m_1

Trigger: liq_count_m_5 ≥ 3 or proxy-score ≥ θ

Cooldown: 60s · Half-life: 240s

Weights: spike defaults

Emit threshold: T_spike

B.2 SHIFT

shift.spread_stress_m_1

Inputs: z_spread_m_1 (primary), spread_p95_m_1, trade_count_m_1

Trigger: z_spread_m_1 ≥ 2.0

Cooldown: 90s · Half-life: 300s

Weights: {w1:0.7,w2:0.8,w3:0.2,a:0.55}

Emit threshold: T_shift = 60

shift.basis_jolt_m_5

Inputs: z_basis_m_5 (primary), basis_bp_m_5, ret_m_5, oi_roc_m_5

Trigger: |z_basis_m_5| ≥ 2.5

Cooldown: 90s · Half-life: 300s

Weights: shift defaults

Emit threshold: T_shift

shift.funding_jolt_h_1

Inputs: funding_h_1 (primary as Δ), time_to_next_funding_sec

Trigger: |Δ funding_h_1| ≥ 10 bps or predicted flip ≤ 1h

Cooldown: 300s · Half-life: 600s

Weights: shift defaults

Emit threshold: T_shift

B.3 QUADRANT

quadrant.price_up_oi_up_m_5 (trend build)
quadrant.price_up_oi_down_m_5 (short squeeze)
quadrant.price_down_oi_up_m_5 (trend down build)
quadrant.price_down_oi_down_m_5 (long squeeze)

Inputs: ret_m_5 (primary as |ret|), oi_roc_m_5 (secondary), z_vol_m_1

Preconditions: fresh OI

Trigger: |ret_m_5| ≥ 0.003 ∧ |oi_roc_m_5| ≥ 0.01 with sign matrix

Cooldown: 90s · Half-life: 180s

Weights: {w1:0.8,w2:0.6,w3:0.2,a:0.58}

Emit threshold: T_quad = 55

B.4 DIVERGENCE

div.price_up_cvd_down_m_5

Inputs: ret_m_5 (primary as |ret|), Σ_5(cvd_delta_m_1) (secondary), z_vol_m_1, z_spread_m_1

Trigger: ret_m_5 ≥ 0.003 ∧ Σ_5(cvd_delta) ≤ −q (q tuned by Curator)

Cooldown: 90s · Half-life: 240s

Weights: {w1:0.8,w2:0.7,w3:0.2,a:0.58}

Emit threshold: T_div = 55

div.price_flat_cvd_trend_m_5

Inputs: |ret_m_5| ≤ 0.001, cvd_slope_m_5 (primary as |slope|)

Trigger: |cvd_slope_m_5| ≥ θ_cvd

Cooldown: 90s · Half-life: 240s

Emit threshold: T_div

div.premium_no_oi_m_5

Inputs: z_basis_m_5 (primary), oi_roc_m_5

Trigger: z_basis_m_5 ≥ 2.0 ∧ oi_roc_m_5 ≤ 0

Cooldown: 90s · Half-life: 240s

Emit threshold: T_div

B.5 SYNCHRONY

sync.basket_shock_Δt_5s

Inputs: shock_count_5s (primary), leader, dominance_share, return_dispersion_m_5

Trigger: shock_count_5s ≥ max(4, ceil(0.15 * universe_size))

Cooldown: 60s · Half-life: 60s

Weights: {w1:0.4,w2:0.3,w3:1.0,a:0.55} (breadth-heavy)

Emit threshold: T_sync = 60

B.6 ROTATION

rot.leader_cooling_followers_hot_m_15

Inputs: leader’s z_vol_m_1, ret_m_5 trend down; follower median RS trend up

Trigger: 2-bar divergence (15m) beyond δ

Cooldown: 300s · Half-life: 900s

Emit threshold: T_rot = 55

rot.rs_flip_sector_m_15 (if sectors)

Inputs: sector mean rs_score_m_5 over 15m

Trigger: lead-sector flip with margin ≥ δ

Cooldown: 300s · Half-life: 900s

Emit threshold: T_rot

Appendix C — Example Payloads (concrete)
C.1 Feature Snapshot (1m) — abbreviated
{
  "asset_uid": 101,
  "symbol": "BTC",
  "tf": "1m",
  "exchange_ts": "2025-09-03T09:30:00Z",
  "ingest_ts": "2025-09-03T09:30:00.142Z",
  "open": 64231.5, "high": 64320.0, "low": 64188.0, "close": 64295.0,
  "mid_close": 64294.6,
  "ret_s_30": 0.0007, "ret_m_1": 0.0010, "ret_abs_m_1": 0.0010,
  "v_buy_m_1": 9.8e6, "v_sell_m_1": 7.9e6, "v_total_m_1": 1.77e7,
  "trade_count_m_1": 412, "cvd_delta_m_1": 1.9e6, "cvd_level": 2.3e8,
  "oi_close": 1.23e9, "oi_roc_m_5": 0.011, "oi_staleness_ms": 1800,
  "funding_h_1": 0.00018, "basis_bp_m_5": 22.4, "time_to_next_funding_sec": 2143,
  "spread_mean_m_1": 0.75, "spread_p95_m_1": 1.8,
  "z_vol_m_1": 3.6, "z_ret_abs_m_1": 2.9, "z_oi_roc_m_5": 2.1, "z_spread_m_1": 0.9, "z_basis_m_5": 1.3,
  "q_vol_m_1": 0.992, "q_ret_abs_m_1": 0.973, "q_oi_roc_m_5": 0.955,
  "is_price_spike_up_m_1": true, "is_vol_spike_m_1": true, "is_oi_spike_up_m_5": true,
  "rs_score_m_5": 1.87,
  "dq_status": "ok", "ingest_lag_ms": 142, "dropped_ticks": 0, "book_staleness_ms": 41, "warmup": false,
  "is_in_universe": true, "is_hot": true, "universe_rev": 3127,
  "feature_pack": "v1.0", "pack_rev": 1, "source": "ws"
}

C.2 Market Snapshot (1m)
{
  "tf": "1m",
  "exchange_ts": "2025-09-03T09:30:00Z",
  "leader": "BTC",
  "dominance_share": 0.42,
  "shock_count_5s": 4,
  "rs_top": ["SOL","HYPE","APT","SEI","ENA"],
  "rs_bottom": ["XRP","ADA","ARB","DOGE","DOT"],
  "return_dispersion_m_5": 0.0062,
  "vol_dispersion_m_5": 0.94,
  "time_to_next_funding_sec": 2143,
  "excluded_count": 3,
  "approx": false,
  "dq_status": "ok",
  "universe_rev": 3127
}

C.3 Event (as published) — spike.vol_spike_m_1
{
  "v": "0.1",
  "event_id": "018f3b3a-ef2f-7b61-bc1e-3f0f1b0c0b8d",
  "emitted_at": "2025-09-03T09:30:00Z",
  "exchange_ts": "2025-09-03T09:30:00Z",
  "ingest_ts": "2025-09-03T09:30:00.144Z",
  "symbol": "BTC",
  "asset_uid": 101,
  "tf": "1m",
  "class": "spike",
  "subtype": "vol_spike_m_1",
  "window_sec": 60,
  "severity": 96,
  "novelty": { "first_seen_at": "2025-09-03T09:29:00Z" },
  "debounce_key": "BTC:spike:1m",
  "local_state": {
    "features": {
      "ret_s_30": 0.0042,
      "ret_m_1": 0.0031,
      "z_ret_abs_m_1": 2.9,
      "v_total_m_1": 1.8e7,
      "z_vol_m_1": 3.6,
      "oi_roc_m_5": 0.012,
      "z_oi_roc_m_5": 2.1,
      "spread_mean_m_1": 0.75,
      "z_spread_m_1": 0.9,
      "cvd_slope_m_5": 0.7,
      "basis_bp_m_5": 18.4,
      "z_basis_m_5": 1.3
    },
    "flags": { "is_price_spike_up_m_1": true, "is_oi_spike_up_m_5": true },
    "dq": { "status": "ok", "ingest_lag_ms": 144, "book_staleness_ms": 41, "oi_staleness_ms": 1800 }
  },
  "market_frame": {
    "leader": "BTC",
    "dominance_share": 0.42,
    "shock_count_5s": 4,
    "rs_top": ["SOL","HYPE","APT","SEI","ENA"],
    "rs_bottom": ["XRP","ADA","ARB","DOGE","DOT"],
    "return_dispersion_m_5": 0.006,
    "vol_dispersion_m_5": 0.92,
    "time_to_next_funding_sec": 2143
  },
  "membership": { "is_in_universe": true, "is_hot": true, "universe_rev": 3127 },
  "provenance": {
    "producer": "alpha-detector@v1.0.0",
    "feature_pack": "v1.0",
    "detector_pack": "v0.1",
    "config_hash": "sha256:…",
    "git_commit": "…",
    "universe_policy_rev": 17,
    "source_lag_ms": 128,
    "clock_skew_ms": 73
  }
}

Appendix D — Default Thresholds, Budgets & Gates (starter values)

These ship with DP v0.1 and are expected to be Curator-tuned after 1–2 weeks of live data.

D.1 Class publish thresholds (severity ≥ T_class)

spike: 65

shift: 60

quadrant: 55

divergence: 55

synchrony: 60

rotation: 55

D.2 Cooldowns & half-lives (class defaults)

spike: cooldown 45s, half-life 120s

shift: cooldown 90s, half-life 300s

quadrant: cooldown 90s, half-life 180s

divergence: cooldown 90s, half-life 240s

synchrony: cooldown 60s, half-life 60s

rotation: cooldown 300s, half-life 900s

D.3 Severity weights (class defaults)

spike: { w1:1.0, w2:0.5, w3:0.4, a:0.6 }

shift: { w1:0.7, w2:0.8, w3:0.2, a:0.55 }

quadrant: { w1:0.8, w2:0.6, w3:0.2, a:0.58 }

divergence: { w1:0.8, w2:0.7, w3:0.2, a:0.58 }

synchrony: { w1:0.4, w2:0.3, w3:1.0, a:0.55 }

rotation: { w1:0.7, w2:0.5, w3:0.4, a:0.52 }

w1 → primary z (clamped), w2 → secondary support, w3 → breadth, a → sigmoid steepness.

D.4 Detector-specific triggers (restate)

spike.vol_spike_m_1: z_vol_m_1 ≥ 3.0, trade_count_m_1 ≥ 5

spike.price_spike_*: z_ret_abs_m_1 ≥ 2.5

spike.oi_spike_*: z_oi_roc_m_5 ≥ 2.0 ∧ |oi_roc_m_5| ≥ 0.015

shift.spread_stress_m_1: z_spread_m_1 ≥ 2.0

shift.basis_jolt_m_5: |z_basis_m_5| ≥ 2.5

shift.funding_jolt_h_1: |Δ funding_h_1| ≥ 10 bps or flip ≤ 1h

quadrant.*: |ret_m_5| ≥ 0.003 ∧ |oi_roc_m_5| ≥ 0.01

div.price_up_cvd_down_m_5: ret_m_5 ≥ 0.003 ∧ Σ_5(cvd_delta) ≤ −q

div.price_flat_cvd_trend_m_5: |cvd_slope_m_5| ≥ θ_cvd

div.premium_no_oi_m_5: z_basis_m_5 ≥ 2.0 ∧ oi_roc_m_5 ≤ 0

sync.basket_shock_Δt_5s: shock_count_5s ≥ max(4, ceil(0.15 * universe_size))

rot.*: per §9.7

D.5 Per-class budgets (per symbol per minute)

spike: 4, shift: 2, quadrant: 2, divergence: 2, synchrony: 2, rotation: 1
Global cap: 800 events/min (drop lowest severity first, preserve class mix).

D.6 Illiquidity & quality gates

v_min = max(1e4, 0.005 * median(dollar_vol_m_1, 7d))

spread_cap = 15 * median(spread_mean_m_1, 7d)

OI freshness: oi_staleness_ms ≤ 20_000 for OI-dependent detectors

Book freshness: book_staleness_ms ≤ 3_000 to use micro features

Warm-up: min_samples ≥ 200 before any z_* (flags NULL until then)

D.7 Tiered overrides (by liquidity decile)

Top decile: spike.vol_spike_m_1 threshold → 3.2; budgets unchanged.

Mid tiers: defaults.

Tail decile: spike.vol_spike_m_1 threshold → 3.8; spike budget → 2/min.

D.8 Hotlist TTL map (severity → minutes)

ttl = ttl_base + k * severity with ttl_base=15, k=0.3 → sev=70 ⇒ 36 min, sev=90 ⇒ 42 min.
Reasons: vol_spike|oi_spike|basis_jolt|manual.

If you want a single compiled .md file with everything (Sections 1–25 + Appendices A–D) as deliverable docs, say the word and I’ll output it ready to drop into your repo.

You said:
Thank you this is good. It’s very detailed and I think very in-depth. I guess my question is moron. How do we use this now? Like can we physically spill this out and then hit play and it’s gonna work kind of thing what do we need to do what do we need to think about like? There’s some pretty complex stuff in here like if it doesn’t work what do we do? Can I think? Like? I don’t know whether it’s a bad question but like how do I get to work? I guess it’s a question. How does it operate? Do you see what I’m asking?

Less like an implementation checklist and more of an understanding of how this works for you and find out what we need to be looking at what we need to think about I guess that kind of implementation checklist just think about this
ChatGPT said:
Thought for 14s

Totally get what you’re asking: “Can I actually turn this on and reason about it without getting lost—what happens when I hit play, what should I look at, and what do I do when something’s off?”

Here’s the pragmatic, operator-level guide—how it behaves in motion, how you bring it up, what signals tell you it’s healthy, and what to do when it isn’t.

Alpha_data_detector — Operator’s Guide (How it actually runs)
1) Mental model: life of a minute

Think of the system as a conveyor belt that ticks once per minute.

WS ingest (trades, candle, bbo; optionally L2) streams into per-asset accumulators.

Minute boundary hits. We close the bar with a small lateness watermark (~1–1.5s).

Build the 1m snapshot. Compute raw features → update baselines → compute z/quantiles → set DQ.

Write it. One UPSERT row keyed by (asset_uid, '1m', exchange_ts).

Market snapshot. Build breadth/leader/RS for that timestamp.

Detectors pass. Evaluate rules on that finished 1m row (+ market snapshot).

Events publish. Anything above class thresholds gets scored, debounced, and sent.

If something degrades (book stale, OI stale, time over budget), it keeps the belt moving but suppresses events for the affected parts.

2) Run modes (how you “press play” safely)

You don’t jump straight to live events; you walk through modes:

Dry-run: ingest + build + write snapshots; detectors compute but don’t publish (they log candidates).
Goal: prove bars are correct and fast enough.

Shadow: detectors write would-have-fired events to an internal table/topic (not the real bus).
Goal: sanity-check counts, severities, and suppression without audience.

Canary: enable real publications for a few high-liquidity symbols (e.g., BTC, ETH, SOL).
Goal: confirm behavior against budgets and latency under real flow.

Prod: full Top-N (+ hotlist). Budgets, cooldowns, gates active.

Replay: offline, deterministic; used by the Curator to validate config changes.
Goal: guarantee we can reproduce events bit-for-bit.

You can move forward or roll back a mode quickly; the core belt (1m snapshots) keeps running.

3) “Turn it on” — the first hour, concretely

0–10 min

Start WS ingest for 3–5 symbols (BTC/ETH/SOL).

Verify proof of life: a 1m row appears for each symbol ~150–300ms after each minute close.

DQ should be ok ≥95% (no trades? BBO still gives you mid_close).

10–20 min

Watch baselines warm (z_* = NULL until ~200 samples).

Confirm ingest_lag_ms p95 < 300ms; book_staleness_ms typically < 1000ms on majors.

20–40 min (still dry-run)

Enable 3 spike detectors in shadow (vol_spike, price_spike_up/down).

You should see some shadowed candidates on the active names; suppression = 0 (since we’re not publishing).

40–60 min (canary)

Flip canary on BTC/ETH to publish spikes only.

Confirm:

Events show up within <150ms after the snapshot write.

Budget utilization < 0.5 for spike class.

No events during minutes with dq_status != ok.

If those are green, widen to Top-10 with spikes only; add other classes later (shift/quadrant/divergence).

4) What to look at while it runs (four gauges)

Pipeline latency

Green: bar finalize p95 < 300ms; end-to-end (close→event) p95 < 450ms.

Amber: p95 300–500ms → detector deferrals may kick in for tail symbols.

Red: p95 > 500ms → fix before widening scope.

Data quality

Green: ≥95% 1m rows dq=ok on majors; few nulls outside L2 columns.

Amber: growing book_staleness_ms, OI staleness >20s.

Red: frequent stale → events will be sparse; check WS and clock skew.

Event health

Green: class mix close to defaults, suppression <5%, severities p50 ~60–70 for spikes.

Amber: floods (budgets hit) or droughts (almost nothing) → thresholds/cooldowns likely need tuning.

Red: everything suppressed for DQ/illiquidity → guardrails too tight or feeds stale.

Baseline drift (z_*)

Green: |mean| ≤ 0.2, std in [0.8,1.2].

Amber/Red: drift means your normalizer is off; Curator will propose decay tweaks.

5) “It’s not working”—quick triage
Symptom	Likely cause	Do this now
No 1m rows	WS not subscribed, wrong symbol alias, clocking issue	Check subscriptions; verify alias map and exchange timestamps; ensure watermark fired
Rows exist but dq=stale	No BBO/trades, WS gap	Reconnect WS; don’t backfill ticks; accept partial minutes and recover
z_* are NULL forever	Warm-up never completes, DQ not ok, baseline not persisted	Confirm min_samples ~200; ensure baseline_state updates only on dq=ok; check persistence on restart
Events flood	Thresholds too low, IQR clamp off, budgets mis-set	Raise class thresholds/cooldowns (runtime override), ensure clamp is applied in scoring
Events drought	Gates too tight (illiquidity), warm-up, DQ partial	Lower v_min/spread_cap for top tiers; confirm warm-up complete; loosen OI/basis reliance if stale
Latency > 500ms	Too many symbols, L2 heavy, slow DB	Disable L2 features; reduce universe to Top-10; profile DB writes; enable detector deferral
OI/basis NULL often	REST cadence too slow, rate-limited	Shorten cadence with jitter; tag staleness; suppress OI/basis detectors until freshness returns
6) How it learns without trading (what improves over week 1)

Baselines settle. z-scores become comparable across assets; fewer false spikes.

Curator calibrates. It watches severity histograms and proposes small threshold/cooldown/weight nudges; you replay → apply.

Universe stabilizes. Hysteresis + hotlist cut churn; detector budgets distribute better.

Guardrails specialize. Per-asset v_min / spread_cap learned from 7d medians reduce noise on thin names.

You’re not optimizing PnL here; you’re optimizing signal quality: healthy severity distributions, low suppression for the right reasons, and latency within SLO.

7) What to add when the basics are green

More detectors: add shift.*, then quadrant.*, then divergence.*. Do each in shadow → canary → prod.

OI & basis: bring those in once REST freshness is consistently ≤ 20s.

L2 microstructure: only after you see stable BBO/L2; otherwise keep those columns NULL (DQ partial).

15m/1h rollups: flip on once 1m is rock-solid; they’re recomputed from 1m so it’s low risk.

8) How to reason about an emitted event

Every event carries enough state to judge it in isolation:

Severity (0–100) and class/subtype tell you what fired and how strong.

local_state.features gives the exact z’s/metrics that drove it.

market_frame tells you if it was alone or part of a basket shock + who the leader was.

provenance.config_hash/pack versions let you reproduce it later with the replay harness.

Downstream (decision layer) can safely act without asking the detector for more context—by design.

9) When something changes (configs/packs)

Detector Pack tweaks (thresholds/cooldowns/weights) are hot-reloadable via an epoch flag.

Use canary (10% assets) before promote; Curator replays golden minutes + last day.

Feature Pack changes add columns; those require a deploy & DB migration (additive).

You’ll always see the active feature_pack, detector_pack, and config_hash in each event for traceability.

10) Minimal scaffolding (what must exist before “play”)

WS client (trades/candle/bbo) with reconnect & per-asset accumulators.

Minute builder writing features_snapshot (a subset is okay to start: price/volume + DQ).

Baselines with persistence + warm-up rules (even for two features: vol, ret_abs).

Detector runner executing 2–3 spike detectors, scoring, debounce, budgets (shadow first).

Publisher to emit to a staging topic; and metrics: finalize latency, DQ split, trigger counts.

Curator can be a stub at first: just severity histograms + a console report.

That’s the minimal engine. Everything else (OI, basis, L2, cross-asset doodads) is bolt-on once the belt is healthy.

11) What “healthy” looks like (quick heuristics)

Latency: bar finalize p95 ~200–300ms; event publish p95 ~100–150ms.

DQ: ok ≥ 95% on majors; partial mainly due to OI/L2; stale ≪ 1%.

Events: per-class counts within budgets; suppression < 5%; severities bell-curvy around 60–70 for spikes.

Drift: z-means ≈ 0, z-std ≈ 1; no large, persistent bias on any top symbol.

Stability: universe churn ≤ 5/hour; hotlist TTLs expiring as expected.

12) If you had to start today (the pragmatic path)

Run dry-run for BTC/ETH/SOL → verify bar finalize latency + DQ.

Shadow spike detectors for 30–60 min → sanity-check candidate counts.

Canary spikes to real bus for BTC/ETH → watch budgets and severity histos.

Expand to Top-10; add price_spike_* and vol_spike only.

Next day, enable shift.spread_stress in shadow; quadrant.* when OI freshness is good.

Let Curator do the first small threshold/cooldown nudge via replay.

You’ll end up with a live, trustworthy detector emitting clean signals—ready for the decision layer to consume—without having to “finish everything” first.

If you want, I can package this Operator’s Guide into a RUNBOOK.md alongside the Build Plan, with a tiny “Day-1 checklist” section at the top so whoever’s on the keyboard knows exactly what “green” looks like before widening scope.

You said:
OK good so would we build this neck as its own repo in isolation? And then somehow it fires events into our system? Like how’s that work? What do we need to think about that?
ChatGPT said:
Thought for 20s

Totally—treat Alpha_data_detector as its own repo + service. It publishes a clean, versioned event stream your existing system consumes. Keep data + runtime isolated, and agree on a tiny public contract. Here’s the practical way to wire it up.

How to structure it (repo → services → integration)
1) Own repo, clear public interface

Repo name: alpha-data-detector/

Deliberate boundary: it does not trade or call LLMs. It only:

writes its own DB tables (snapshots, events archive), and

publishes events to a bus topic.

Consumers (your decision layer, UI, backtests) subscribe to the topic and/or read a read-only API for snapshots/market frames.

2) Minimal interfaces (pick 1–2, not all)

Primary (recommended):

Event bus (Kafka/NATS/Redis Streams): topic alpha.events.v0 (plus alpha.events.replay.v0).

Key by asset_uid for order.

At-least-once delivery; dedupe on event_id (UUIDv7).

Optional:

Read API (HTTP/gRPC) for pulling context:

GET /snapshots/latest?asset=BTC&tf=1m

GET /market/frame?tf=1m&ts=...

GET /events?symbol=...&since=... (read-from-archive)

Status API (for ops only): health, lag, version, pack hashes.

Not recommended: sharing the detector’s DB directly with other apps (tight coupling). If you must, expose a read replica.

3) How your system consumes it

Real-time: decision layer subscribes to alpha.events.v0.

Dedupe on event_id, also respect debounce_key if you want to suppress local spam.

Use severity, class/subtype, and market_frame to route logic.

On demand: when you need extra context, call the Read API for the exact 1m/15m rows referenced by the event’s exchange_ts.

What to think about (integration “gotchas”)
Contract & versioning

Pin to event schema v0.1. Consumers ignore unknown fields (forward-compatible).

When detector breaks schema → it publishes to a new topic (alpha.events.v1). Your consumer opts in when ready.

Delivery semantics

At-least-once on the bus. Your consumer must dedupe via event_id.

Ordering is per asset (keyed partitions). Do not assume global order.

Backpressure

Detector enforces per-class budgets; still, your consumer should:

apply its own per-class rate caps, and

drop lowest severity first under pressure.

Provenance / reproducibility

Every event includes feature_pack, detector_pack, config_hash, git_commit.

If you store the event as-is, you can always replay the exact minute later.

Security

Separate service accounts/keys per env (dev/stg/prod).

Read-only tokens for your consumer.

No direct DB writes from outside.

Suggested repo layout (keeps roles clean)
alpha-data-detector/
  /cmd/
    ingest/          # WS clients, accumulators
    builder/         # 1m assembly + rollups
    detector/        # rule eval + scoring + publish
    curator/         # monitors, proposals, replays (offline)
    publisher/       # bus + DB writers
    api/             # optional read/status API
  /internal/
    feeds/           # HL WS/REST adapters
    features/        # feature calculators (1m core)
    baselines/       # robust stats, quantiles
    detectors/       # catalog implementations (pure, deterministic)
    market/          # cross-asset context builder
    storage/         # DB models, migrations
    bus/             # Kafka/NATS client
    config/          # loaders, schema validation
    dq/              # gates & guards
  /packs/
    feature/         # FP YAML + codegen
    detector/        # DP YAML (thresholds/cooldowns/weights/budgets)
    universe/        # policy YAML (N_base, bands, TTLs)
  /deploy/
    docker/          # images per component
    helm/compose/    # local + cluster manifests
  /ops/
    RUNBOOK.md       # the operator’s guide
    BUILD_PLAN.md    # the big spec you and I wrote
  /tests/
    golden_minutes/  # frozen fixtures for replay CI
    replay/          # deterministic runner


Tech picks (pragmatic):

Go/Rust for ingest/builder/detector (latency, concurrency).

Python for Curator & replays (stats, plots); it’s out of the hot path.

Postgres/Timescale for storage; Kafka or NATS for events.

Environments & wiring (dev → stg → prod)
Dev (local + CI)

docker compose up: Postgres, Kafka/NATS, detector services.

Feed recorded PCAPs to ingest for deterministic tests.

CI runs golden-minute replays; blocks merges on diffs.

Staging

Connect to HL testnet or prod in read-only.

Publish to alpha.events.v0.stg.

Decision layer can point a canary consumer at staging to test parser/logic.

Prod

Real HL feeds.

Publish to alpha.events.v0 (and to ...replay.v0 for replays).

Decision layer’s prod consumer reads from v0 only.

How the pieces talk at runtime (dataflow recap)

Ingest subscribes to HL WS (trades, bbo; optionally l2Book).

Builder rolls 1m → computes features → updates baselines → writes features_snapshot.

Market creates the market_snapshot row for that minute.

Detector reads the just-written rows → evaluates detectors → publishes events.

Publisher writes event archive (anomaly_event) and pushes JSON to the event bus.

Your decision layer consumes the bus:

acts on the event (or calls a Read API for more context),

and logs decisions/outcomes elsewhere (separate system).

No reverse calls from decision layer back into detector (keeps it pure and safe).

Two integration patterns (choose 1 + optional 1)

(A) Firehose-first (recommended): your system consumes alpha.events.v0.

Pro: lowest coupling, near-zero latency.

Use case: LLM decision-maker, alerting, auto/sim trading.

(B) Thin Read API (optional): your system fetches snapshots/frames by exchange_ts.

Pro: easy ad-hoc context, less DB exposure.

Use case: dashboards, backtest scrapes, post-hoc analysis.

You can start with A only; add B if you want UI/analytics later.

What to implement first for integration (short, real list)

Event consumer in your system (Python/TS/Go), with:

JSON model for the event schema v0.1 (strict parsing, unknown-field tolerant),

dedupe by event_id,

basic filters (min severity per class),

a dead-letter path when parsing fails.

Config pinning in the consumer:

Log feature_pack, detector_pack, config_hash per message,

Alert if packs change unexpectedly (helps you correlate behavior shifts).

Safe defaults in consumer:

If dq.status != ok in local_state → ignore or downweight the event,

If class not recognized → drop (until you upgrade to v1).

Optional: a /context call in the detector for “give me the 1m row & market frame for event.exchange_ts”.

How to expand later without breaking you

New columns → Feature Pack minor bump; events may include new fields you can ignore.

New detectors → Detector Pack minor; they appear as new subtypes under existing classes (your parser just treats them as strings).

Breaking schema → new topic alpha.events.v1. We run v0 and v1 in parallel during migration.

“What if it doesn’t work?” (playbook)

No events: check DQ (dq='ok'?), warm-up (z_* ready?), budgets (class threshold too high?).

Too many events: raise thresholds/cooldowns with a runtime override (detector pack flag) and log config epoch.

Latency spikes: disable L2 (microstructure) and reduce universe to Top-10; detector deferral will help immediately.

Consumer crashes on message: fall back to DLQ; inspect the payload; ensure your parser ignores unknown fields.

If you want, I can drop a skeletal repo scaffold (folders, RUNBOOK.md, BUILD_PLAN.md, sample detector_pack.yaml, and a tiny event consumer example in Python/TypeScript) so your team can clone and start wiring to your bus right away.

You said:
So I guess my next question is yeah it separates out each of the events where there’s different event types that it could be correct like different signals what are we kind of? So I guess my question when it comes down we’re starting with some basic signals right so just say oh up and volume up maybe that means something maybe it doesn’t just say that’s one of our signals. Do we have some basic signals? We’re looking at? How do we add new signalsand two so we have the different signal? We also have like a strength of signal rating kind of thing, yeah make sense.
ChatGPT said:
Thought for 15s

Yep, makes total sense. Think of “signals” as detectors that fire events with a strength score (severity 0–100). You start with a tiny, dependable set, then add more via the registry → shadow → canary → promote flow.

Here’s the crisp playbook.

1) Starter signal set (v0 “basic but useful”)

Each detector is deterministic, reads from the 1-minute feature row (+ market frame), and emits one event with a severity.

A. Spikes (pure anomaly checks)

Volume spike (1m) — z_vol_m_1 ≥ 3.0, trade_count_m_1 ≥ 5.

Price spike up/down (1m) — z_ret_abs_m_1 ≥ 2.5, sign of ret_m_1 picks subtype.

B. Simple combos (two-dimensional)

Price up + Volume up (1m) — ret_m_1 > 0, z_ret_abs_m_1 ≥ 1.5, z_vol_m_1 ≥ 2.5.
(Your “price up & volume up” example. Good continuation candidate.)

Price up + OI up (5m) — ret_m_5 ≥ 0.3% AND z_oi_roc_m_5 ≥ 2.0 AND oi_roc_m_5 ≥ 1.0%.
(“Trend build”.)

Price up + OI down (5m) — ret_m_5 ≥ 0.3% AND oi_roc_m_5 ≤ −1.0%.
(“Short squeeze” signature.)

C. Micro & market conditions (sanity/context)

Spread stress (1m) — z_spread_m_1 ≥ 2.0. (Slippage regime change; caution.)

Basket shock (Δt≈5s) — shock_count_5s ≥ max(4, ceil(0.15*universe)). (Market-wide impulse.)

D. Basis/funding (perp state)

Basis jolt (5m) — |z_basis_m_5| ≥ 2.5. (Perp–spot dislocation.)

That’s 8 detectors. Ship these first—low code, high signal.

2) Strength of signal (severity)

Every event carries severity: 0..100. For v0 you can keep it simple:

primary = clamp_IQR(primary_z)              # e.g., z_vol or z_ret_abs
secondary = max(0, clamp_IQR(secondary_z))  # optional confirm (e.g., z_oi_roc)
breadth = min(1, shock_count_5s / 6)        # market synchrony 0..1
raw = 1.0*primary + 0.5*secondary + 0.4*breadth + novelty_boost
severity = round(100 * sigmoid(0.6 * raw))


Primary z gives most of the score.

Secondary and breadth nudge it up/down.

Novelty gives a perk to first fires, then decays.

Thresholds by class (publish if severity ≥ 65 for spikes, ≥ 60 for shifts, etc.).

If you want extra simple for v0: severity ≈ min(100, round(15 * primary_z + 5 * secondary_z + 10 * breadth)) and iterate later.

3) How to add a new signal (zero drama)

Step 0 — Spec it (one page)

Name/class/subtype: e.g., spike.price_up_volume_confirmed_m_1

Inputs: z_ret_abs_m_1, ret_m_1, z_vol_m_1

Trigger: ret_m_1 > 0 ∧ z_ret_abs_m_1 ≥ 1.5 ∧ z_vol_m_1 ≥ 2.5

Cooldown/half-life: 45s / 120s

Weights: {w1:1.0, w2:0.5, w3:0.4, a:0.6}

DQ gates: require dq_status='ok', pass illiquidity guards.

Step 1 — Register it

Add to detector_registry with enabled=false (shadow).

Step 2 — Shadow

Run live, write candidates to an internal table/topic. Check counts, severity distribution, suppression reasons.

Step 3 — Canary

Enable for BTC/ETH/SOL only, publish to real topic. Watch budgets/latency.

Step 4 — Promote

Flip enabled=true globally, bump Detector Pack minor version.

You don’t touch schemas; detectors consume existing columns.

4) Example: your “Price↑ + Volume↑” detector

ID: combo.price_up_volume_up_m_1 (class spike, subtype price_vol_combo_m_1)

Trigger (AND):

ret_m_1 > 0

z_ret_abs_m_1 ≥ 1.5

z_vol_m_1 ≥ 2.5

trade_count_m_1 ≥ 5

DQ/illiquidity gates pass

Severity inputs:

primary_z = z_ret_abs_m_1

secondary_z = z_vol_m_1

breadth = min(1, shock_count_5s/6)

Cooldown / Half-life: 45s / 120s
Publish threshold: class spike default (e.g., severity ≥ 65)

Payload fields to include (local_state.features):

ret_m_1, z_ret_abs_m_1, v_total_m_1, z_vol_m_1, trade_count_m_1, spread_mean_m_1

Done. This is literally a dozen lines in the detector runner once the features exist.

5) Quick menu of “next signals” you can add later

Divergence: price_up with Σ_5(cvd_delta) < 0 → absorption.

Price flat + CVD trend: accumulation/distribution in ranges.

Price down + OI up (5m): trend-down build.

Price up + OI down + Spread stress: squeeze in illiquid book (high risk/high reward).

Leader cooling, followers heating (15m): rotation into alts.

All of these use columns you already compute.

6) Tuning knobs (per detector)

Thresholds: z cutoffs (2.5 vs 3.0 changes fire rate a lot).

Cooldowns: fewer repeats during persistent regimes.

Weights: how much secondary/breadth matter.

Budgets: per-class max events/min, plus global cap.

The Curator will propose small tweaks after a few days based on severity histograms and flood/drought patterns.

7) Common pitfalls & how to dodge them

False spikes on thin books: keep illiquidity gates on (v_min, spread_cap).

OI/funding flakiness: require freshness (oi_staleness_ms ≤ 20s) else zero out their contribution.

Warm-up noise: don’t use z_* until baselines ready (min_samples).

Severity runaway: keep the IQR clamp inside the scorer.

If you want, I can draft a tiny detector pack snippet (YAML) containing the three starters (vol_spike, price_spike_*, and your price_up_volume_up) so your team can plug it into the runner and see events immediately.

You said:
OK so do we have any of these built-in in our plan or or we just have the primitive to start building this?
ChatGPT said:
Thought for 8s

Short answer: we already have a built-in starter set in the plan—not just primitives.

The primitives (features & z-scores) are defined in Feature Pack v1.0 (prices, volume, OI, basis, spread, CVD, etc.).

The signals (detectors) and strength scoring are defined in §9 (Detector Catalogue) + §10 (Severity/Novelty/Debounce) and spelled out again in Appendix B. That’s your “built-in” set: volume spike, price spike up/down, price+OI quadrants, spread stress, basis jolt, basket shock, divergences, rotations.

What this means practically:

You don’t need new design to get signals—just implement the runner according to the spec.

Start with the basic trio and the combo you asked for:

spike.vol_spike_m_1

spike.price_spike_up_m_1 / spike.price_spike_down_m_1

combo.price_up_volume_up_m_1 (the “price↑ & volume↑” check)

If it helps, here’s a minimal detector_pack.yaml slice you can drop in today:

detector_pack: v0.1.0
class_defaults:
  spike: { cooldown_sec: 45, half_life_sec: 120, weights: { w1: 1.0, w2: 0.5, w3: 0.4, a: 0.6 }, publish_threshold: 65 }
detectors:
  - id: spike.vol_spike_m_1
    enabled: true
    inputs: [z_vol_m_1, ret_m_1, v_total_m_1, trade_count_m_1]
    preconditions: [dq_ok, not_illiquid, trade_count_ge_5]
    trigger: "z_vol_m_1 >= 3.0"
  - id: spike.price_spike_up_m_1
    enabled: true
    inputs: [z_ret_abs_m_1, ret_m_1, spread_mean_m_1]
    preconditions: [dq_ok, not_illiquid]
    trigger: "z_ret_abs_m_1 >= 2.5 && ret_m_1 > 0"
  - id: spike.price_spike_down_m_1
    enabled: true
    inputs: [z_ret_abs_m_1, ret_m_1, spread_mean_m_1]
    preconditions: [dq_ok, not_illiquid]
    trigger: "z_ret_abs_m_1 >= 2.5 && ret_m_1 < 0"
  - id: combo.price_up_volume_up_m_1
    enabled: true
    inputs: [ret_m_1, z_ret_abs_m_1, z_vol_m_1, trade_count_m_1]
    preconditions: [dq_ok, not_illiquid, trade_count_ge_5]
    trigger: "ret_m_1 > 0 && z_ret_abs_m_1 >= 1.5 && z_vol_m_1 >= 2.5"
budgets:
  per_symbol_per_minute: { spike: 4 }


And if you want OI/basis later, enable these (once freshness gates are green):

  - id: spike.oi_spike_up_m_5
    enabled: false
    inputs: [z_oi_roc_m_5, oi_roc_m_5, ret_m_5, oi_staleness_ms]
    preconditions: [dq_ok, not_illiquid, oi_fresh_20s]
    trigger: "z_oi_roc_m_5 >= 2.0 && abs(oi_roc_m_5) >= 0.015"
  - id: shift.basis_jolt_m_5
    enabled: false
    inputs: [z_basis_m_5, basis_bp_m_5, ret_m_5]
    preconditions: [dq_ok, basis_valid]
    trigger: "abs(z_basis_m_5) >= 2.5"


So: yes, we have basic signals defined and ready—plus the machinery for strength scoring. You implement the feature builder, drop this pack in the registry, run in shadow → canary, and you’ll see real events immediately.