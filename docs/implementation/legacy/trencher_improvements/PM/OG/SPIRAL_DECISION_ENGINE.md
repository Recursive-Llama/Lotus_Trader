SPIRAL_DECISION_ENGINE v1:

Phase Detection Spec (v1.1) Part 1

Goal:
Label Macro / Meso / Micro market phases from raw performance data, using math—not rules.
Detect the rhythm of market acceleration and deceleration, not just direction.

0. Core Idea

Phases describe how fast our portfolio’s performance is changing relative to the majors, not simply whether it’s up or down.

𝑅
𝑒
𝑠
𝑖
𝑑
𝑢
𝑎
𝑙
(
𝑡
)
=
𝑃
𝑜
𝑟
𝑡
𝑓
𝑜
𝑙
𝑖
𝑜
𝑅
𝑒
𝑡
𝑢
𝑟
𝑛
(
𝑡
)
−
𝑀
𝑎
𝑗
𝑜
𝑟
𝑠
𝐼
𝑛
𝑑
𝑒
𝑥
𝑅
𝑒
𝑡
𝑢
𝑟
𝑛
(
𝑡
)
Residual(t)=PortfolioReturn(t)−MajorsIndexReturn(t)

We smooth this, measure its slope, curvature, and change vs the last window (ΔResidual).
Phases shift when the shape of this residual curve changes.

Four-lens residual framework (expanded inputs)

- S_btcusd: BTC vs USD (market tone)
- S_rotation: Alt basket vs BTC (rotation tone), where Alt basket = equal-weight of {SOL, ETH, BNB, HYPE}
- S_port_btc: Portfolio vs BTC (beta outperformance)
- S_port_alt: Portfolio vs Alt basket (rotation participation)

We compute a standard SPIRAL sub-score (slope/curvature/Δ/level → z) for each lens and blend them per horizon to produce the Macro/Meso/Micro PhaseScores. Banding, hysteresis, dwell, and skip rules are unchanged.

1. Horizons & Windows
Horizon	Windows	Typical dwell
Macro	{1 d, 3 d, 1 w}	3 d – 3 w
Meso	{4 h, 12 h, 1 d}	12 h – 5 d
Micro	{30 m, 2 h, 4 h}	60 – 180 m

Each window gives an independent view; we later combine them.

2. Feature Extraction

Streams & return conventions

- All returns are USD log returns.
- r_btc = ln(BTC_t) − ln(BTC_{t−1})
- r_alt = mean_EW( ln(SOL_t/SOL_{t−1}), ln(ETH_t/ETH_{t−1}), ln(BNB_t/BNB_{t−1}), ln(HYPE_t/HYPE_{t−1}) )
- r_port = portfolio’s USD log return over the bar (value-weighted across positions)
- residual_major = r_port − r_btc
- residual_alt = r_port − r_alt
- rotation_spread = r_alt − r_btc

For each window tf in horizon H (apply the same steps to each stream: r_btc, residual_major, residual_alt, rotation_spread):

Smooth residuals

R_tf = EMA(stream_tf, n_tf≈2–3)


Compute slope and curvature

Slope_tf: regression slope over last k bars of R_tf

Curvature_tf: slope-of-slope (second derivative)

Compute ΔResidual

ΔResidual_tf = R_tf(now) − R_tf(prev_window)


Standardize (z-score) over rolling lookback L to remove scale bias.

Aggregate per horizon:

Slope_H     = Σ w_tf * z(Slope_tf)
Curvature_H = Σ w_tf * z(Curvature_tf)
ΔRes_H      = Σ w_tf * z(ΔResidual_tf)
Level_H     = Σ w_tf * z(R_tf)


Default weights emphasize the middle window (e.g., 0.2 / 0.6 / 0.2).

3. Phase Score Computation

Hybrid dynamic anchor formula:

𝑃
ℎ
𝑎
𝑠
𝑒
𝑆
𝑐
𝑜
𝑟
𝑒
𝐻
=
0.5
⋅
𝑆
𝑙
𝑜
𝑝
𝑒
𝐻
+
0.3
⋅
𝐶
𝑢
𝑟
𝑣
𝑎
𝑡
𝑢
𝑟
𝑒
𝐻
+
0.2
⋅
Δ
𝑅
𝑒
𝑠
𝐻
+
0.1
⋅
𝐿
𝑒
𝑣
𝑒
𝑙
𝐻
PhaseScore
H
	​

=0.5⋅Slope
H
	​

+0.3⋅Curvature
H
	​

+0.2⋅ΔRes
H
	​

+0.1⋅Level
H
	​


Slope → direction

Curvature → acceleration

ΔResidual → responsiveness (flow vs previous window)

Level → context anchoring

3.1 Lens sub-scores

For each of the four lenses we form a SPIRAL sub-score using the above mix:

- S_btcusd = 0.5·Slope_H(r_btc) + 0.3·Curvature_H(r_btc) + 0.2·ΔRes_H(r_btc) + 0.1·Level_H(r_btc)
- S_rotation = same, computed on rotation_spread
- S_port_btc = same, computed on residual_major
- S_port_alt = same, computed on residual_alt

3.2 Horizon blends (weights)

- Macro (tone):
  PhaseScore_macro = 0.55·S_btcusd + 0.35·S_rotation + 0.05·S_port_btc + 0.05·S_port_alt

- Meso (behaviour):
  PhaseScore_meso = 0.50·S_port_btc + 0.30·S_port_alt + 0.15·S_rotation + 0.05·S_btcusd
  Adaptive rotation tilt (dwell ≥ 6–12 h):
    if S_rotation > +0.8 → 0.40·S_port_btc + 0.40·S_port_alt + 0.15·S_rotation + 0.05·S_btcusd
    if S_rotation < −0.8 → 0.60·S_port_btc + 0.20·S_port_alt + 0.15·S_rotation + 0.05·S_btcusd

- Micro (timing):
  PhaseScore_micro = 0.70·S_port_btc + 0.30·S_port_alt  (Micro remains a spike sensor per Section 7.)

4. Band Mapping → Phase Label
Phase	PhaseScore Range (z)	Qualitative meaning
Euphoria	≥ +1.20	accelerating outperformance
Good	+0.40 – +1.20	steady outperformance
Recover	−0.20 – +0.40	rebound forming
Dip	−0.90 – −0.20	mild underperformance
Double-Dip	−1.30 – −0.90	renewed weakness
Oh-Shit	< −1.30	capitulation
Hysteresis

To prevent flicker:

enter phase at threshold A

exit only after crossing B (≈ ±0.2 gap)

Dwell (min time in phase)
Horizon	Dwell Min
Macro	≥ 3 days
Meso	≥ 12 h
Micro	≥ 60 – 90 min
Allowed skips

{Dip → Oh-Shit, Double-Dip → Recover, Good → Euphoria, Euphoria → Dip}

5. Context Nudges (± 0.2 max)

These refine but never override the score.

Breadth_z = % tokens > EMA(1h)

Vol_z = volatility of majors returns

RSI_bias = avg RSI of majors + low-cap index

EMA_cross_bias = sign & persistence of EMA(15 m) – EMA(1 h)

IntentBreadthBias = buy vs profit-taking intent breadth

PhaseScore_H += small_weight * (Breadth_z - Vol_z + RSI_bias + EMA_cross_bias + IntentBreadthBias)

6. Output per Horizon
{
  "phase": "Dip|Double-Dip|Oh-Shit|Recover|Good|Euphoria",
  "score": float,
  "slope": float,
  "curvature": float,
  "ΔResidual": float,
  "confidence": 0.0-1.0,
  "dwell_remaining": float,
  "pending_label": null|"...",
  "diagnostics": {
    "S_btcusd": float,
    "S_rotation": float,
    "S_port_btc": float,
    "S_port_alt": float
  }
}


Confidence = distance to band edge × dwell fraction achieved.

7. Cross-Horizon Coherence

Macro anchors context (baseline weight 1.0)

Meso drives decisions (weight 0.6–0.8)

Micro adds timing nuance (adaptive 0 – 0.4)

Adaptive Micro Weighting
Micro phase	Weight into A/E modulation	Rationale
Dip → Good	0 – 0.1	mostly noise
Oh-Shit	0.3 – 0.4	panic detector
Euphoria	0.3 – 0.4	blow-off detector

Micro is a spike sensor, not a driver.

8. Sequence Sanity Check

Ensure each horizon’s label sequence broadly follows the cycle.
If labels violate dwell and skip rules across three consecutive windows → flag horizon as unstable; no punishment for valid fast micro spirals.

Skip rules (reaffirmed):

- Recover cannot jump to Double-Dip. Down-path is Recover → Dip → (Oh-Shit if acceleration).
- Allowed skips remain: {Dip → Oh-Shit, Double-Dip → Recover, Good → Euphoria, Euphoria → Dip}.

9. Storage

Persist per horizon in phase_state:

Field	Type	Description
phase	str	current label
score	float	PhaseScore_H
slope	float	normalized
curvature	float	normalized
ΔResidual	float	normalized
confidence	float	0–1
dwell_remaining	float	hours / days
pending_label	str | null	awaiting dwell confirmation
S_btcusd	float	lens sub-score (diagnostic)
S_rotation	float	lens sub-score (diagnostic)
S_port_btc	float	lens sub-score (diagnostic)
S_port_alt	float	lens sub-score (diagnostic)
Summary

Baseline residual keeps orientation vs the market.

ΔResidual term adds smooth, time-responsive flow between phases.

Micro acts only at emotional extremes.

Hysteresis + dwell ensure stable, interpretable progression.

Parameters & Conventions (concise)

- Alt basket (rotation lens): equal-weight of {SOL, ETH, BNB, HYPE}.
- Returns: USD log returns for BTC, Alt constituents, and portfolio.
- Streams per horizon: r_btc, rotation_spread (Alt−BTC), residual_major (Port−BTC), residual_alt (Port−Alt).
- Lens sub-scores: S_btcusd, S_rotation, S_port_btc, S_port_alt computed with the standard SPIRAL mix.
- Horizon blends: Macro = 0.55/0.35/0.05/0.05; Meso = 0.50/0.30/0.15/0.05 with adaptive rotation tilt; Micro = 0.70/0.30 (Port vs BTC / Port vs Alt).
- Bands, hysteresis (±0.2), dwell (Macro ≥3d, Meso ≥12h, Micro ≥60–90m) unchanged.

Appendix A — Numeric Defaults & Data Conventions (v1 seeds)

Time & bars

- All timestamps aligned to UTC.
- Base bars per horizon: Micro = 5 m, Meso = 1 h, Macro = 1 d.
- Windows (as in Section 1) are applied on the base bars and aggregated with weights {0.2, 0.6, 0.2}.

Returns

- USD log returns: r_t = ln(P_t) − ln(P_{t−1}).
- Portfolio return r_port computed from value-weighted portfolio NAV on the bar.

Smoothing & derivatives (per horizon H)

- EMA smoothing length n_tf: Micro 3, Meso 5, Macro 7.
- Regression window k_tf (bars of the window tf): Micro 30, Meso 24, Macro 20.
- Δ window length (absolute time): Micro 2 h, Meso 1 d, Macro 1 w.

Standardization

- Z-score each feature with rolling lookback L_H: Micro 14 windows, Meso 30, Macro 60.
- Winsorize input features at 1%/99% tails before z-scoring.

Aggregation

- Horizon aggregates: Slope_H, Curvature_H, ΔRes_H, Level_H = Σ w_tf · z(feature_tf) with w_tf = {0.2, 0.6, 0.2}.
- PhaseScore_H = 0.5·Slope_H + 0.3·Curvature_H + 0.2·ΔRes_H + 0.1·Level_H.

Context nudges (formal)

- breadth_z: fraction of tracked tokens with close > EMA_1h (computed on 5 m bars, evaluated hourly), z-scored over 30 d, winsorize 5–95%.
- vol_z: z-score of rolling stdev of BTC 1 h USD returns over 30 d.
- vo_z: z-score of log(volume) on a token’s 1 h bars with 7 d lookback (EWMA variance).
- rsi_bias: average RSI(14) of BTC + Alt basket (1 h), standardized.
- ema_cross_bias: signed persistence of EMA(15 m) − EMA(1 h) (standardized streak length).
- intent_breadth_bias: buy vs profit-taking share across curators (standardized).
- Apply: PhaseScore_H += 0.05 × (breadth_z − vol_z + rsi_bias + ema_cross_bias + intent_breadth_bias), clamp total nudge to ±0.2 per horizon.

Calibration notes

- ATR convention: Wilder’s ATR(14) on the tf used when needed.
- Sigmoid(x) = 1 / (1 + e^{−x}); scale inputs so typical structure breaks yield sr_conf ≈ 0.6–0.8 (if geometry module is enabled).
- Backtest: tune {n_tf, k_tf, L_H, hysteresis} via walk-forward on 6–12 months; objective = stability (fewer invalid flips) and forward PnL on PM actions.

Appendix B — Data Ingestion Checklist

Feeds (all UTC):

- Prices & volume (USD) for BTC, SOL, ETH, BNB, HYPE at 5 m / 1 h / 1 d bars.
- Portfolio NAV or per-position valuations to compute r_port on each bar.
- Dominance series: BTC.D, USDT.D (level; compute 7 d deltas for z-scores).
- Universe prices (for breadth_z and vol_z): tracked token set at 5 m/1 h.

Derived signals computed on ingest:

- r_btc, r_alt (EW of SOL/ETH/BNB/HYPE), r_port; residual_major, residual_alt, rotation_spread.
- OBV and VO metrics per Section 6.1 (if TA nudges enabled).
- Breadth_z, vol_z, vo_z, rsi_bias, ema_cross_bias (per Appendix A).

Cadence & persistence:

- Re-sample/align bars strictly to UTC boundaries; fill small gaps with forward-fill up to one bar; larger gaps → mark horizon confidence down.
- Persist per-horizon PhaseScore inputs/outputs and diagnostics listed in Section 9, plus dominance diagnostics.
- Logging cadence: hourly tick and on-event (phase flip, dominance early-rise/peak-roll, geometry break).

Appendix C — Evaluation & Calibration

Objective

- Let the Learning system tune lens weights, dominance coefficients, and hysteresis/lookbacks to maximize stability and forward PnL of PM actions while preserving interpretability.

Method (walk-forward)

- Split data into rolling windows (e.g., 3 m train → 1 m test, advance monthly) across multiple market regimes.
- Optimize over:
  - Lens weights (within bounds): Macro {S_btcusd 0.4–0.7, S_rotation 0.2–0.5}, Meso {S_port_btc 0.4–0.6, S_port_alt 0.2–0.5}, Micro fixed.
  - Rotation tilt thresholds (±0.6–±1.0 z with 6–12 h dwell).
  - Dominance deltas (BTC.D ±0.03–0.08; USDT.D ±0.08–0.15) and clamps (±0.15–±0.20).
  - n_tf, k_tf, L_H, and hysteresis gap (±0.15–±0.30).

Targets & guards

- Targets: (1) minimize invalid flips (band violations vs dwell/skip); (2) maximize forward 24 h / 72 h PnL attribution of PM decisions conditioned on phase; (3) stability score (avg dwell length >= spec).
- Guards: keep interpretability — weights must stay within ranges; do not remove skip rules; keep label distributions within historical priors.

Deployment

- Update parameters at most monthly; log diffs with checksum and training window.
- Roll back to prior set automatically if real-time flip rate exceeds 2× baseline over 7 days.

This v1.1 detector yields continuous, self-correcting phase states that downstream modules (Policy, A/E, etc.) can trust for context and timing.

=========

=========

Phase → Part 2 Policy Templates (v1.2)

Purpose
Translate detected market phases into concrete Portfolio Manager posture:
how aggressively to enter (A_mode), exit (E_mode), and act (readiness) — with full flexibility to adapt as the market and position context evolve.

This layer does not predict; it defines the state of aggression and timing rhythm for the PM.
The learning and TA systems modulate within these behavioural envelopes.

0. Core Principles

Meso phase sets behaviour.
Macro defines tone (confidence / defensiveness).
Micro defines pacing (timing of spikes and exhaustion).

A (entry) and E (exit) share the same numeric range (0–1) but behave as dynamic opposites most of the time:

In weakness → patient entries, aggressive exits.

In strength → aggressive entries, patient exits.

In panic or mania → both can be aggressive.

Modes are continuous and fluid — not discrete.
An open position automatically scales size and exit aggressiveness as the market state changes.

The objective: Buy fear, sell euphoria, let strength breathe.

1. Mode Scale
Mode	Range	Description
Patient	0.0 – 0.3	Minimal risk-taking; slow exits
Normal	0.3 – 0.7	Balanced posture
Aggressive	0.7 – 1.0	Max conviction / fast rotations
2. Meso Phase Behaviour Templates
Meso Phase	Market Feel	A_mode	E_mode	Readiness (New)	Readiness (Trend)	Behaviour
Dip	First pullback after strength	0.2 (Patient)	0.8 (Aggressive)	Wait	Wait	Market starts to weaken. Exit trend breaks in profit and overperformers (they top early). Don’t sell laggards — they’ll mean-revert later. Avoid early entries; prepare watchlist.
Double-Dip	Second leg down, fear building	0.4 (Normal)	0.7 (Aggressive)	Wait / Light	Active	Take profits on remaining strong names; trim trend breaks aggressively. Begin scaling small into laggards showing RSI/price divergence; they often lead the next bounce.
Oh-Shit	Capitulation and panic	0.9 (Aggressive)	0.8 (Aggressive)	Active	Active	Deploy hard into prior leaders now flushed; buy fear. Trim aggressively on mean reversion rebounds to recycle capital. Repeat buy–trim–buy cycle. Risk high but payoffs large.
Recover	First sustained rebound	1.0 (Max Aggressive)	0.5 (Medium)	Active	Active	Add aggressively on trend confirmations and diagonal breaks. Take medium partials on flash pops; re-enter on retests. Manage position rotation actively.
Good	Stable healthy uptrend	0.5 (Normal)	0.3 (Patient)	Active	Active	Smooth trending market. Build and hold core positions. Trim minimal; recycle only on extreme extensions. Let winners run.
Euphoria	Blow-off / mania	0.3–0.4 (Patient) for existing coins, 0.8 (Aggressive) for new/laggards	0.5 (Medium)	Active (selective)	Wait	Main profit zone. Trade new launches and laggards aggressively; hold mature winners. Reduce re-entry frequency. Micro Euphoria spikes trigger temporary aggressive exits when mania peaks.
3. A/E Coupling Rules
Phase Group	A/E Relationship	Behaviour
Dip, Double-Dip	Opposed: E = 1 − A	Protect capital; trim aggressively, build patience
Oh-Shit	Aligned: A ≈ E ≈ 0.8–1.0	Both aggressive — rapid deploy + scalp cycle
Recover, Good, Euphoria	Aligned: A ≈ E	Ride momentum; fast in/out rotation as needed

This coupling maintains natural polarity between accumulation and distribution depending on emotional regime.

4. Continuous Mode Updating

Positions evolve automatically with context:

Target_alloc
=
Entry_size
×
𝐴
_
𝑐
𝑢
𝑟
𝑟
𝑒
𝑛
𝑡
𝐴
_
𝑒
𝑛
𝑡
𝑟
𝑦
Target_alloc=Entry_size×
A_entry
A_current
	​


If A rises from 0.2 → 0.6, exposure scales ×3 (subject to caps).
If E rises, harvest frequency increases and trailing stops tighten.
Modes flow smoothly — no stepwise flips.

5. Macro Modulation (Tone)

Macro phase controls conviction amplitude — how confident or defensive we are globally.

Macro Phase	A multiplier	E multiplier	Portfolio Tone
Dip	× 0.6	× 1.4	Defensive; protect gains
Double-Dip	× 0.8	× 1.2	Guarded but probing
Oh-Shit	× 1.2	× 0.8	Begin deploying capital
Recover	× 1.3	× 1.0	Confidence returning
Good	× 1.1	× 1.1	Normalised environment
Euphoria	× 1.0	× 1.4	Full harvest bias / quick rotations

This modulation is multiplicative on the 0–1 scale before discretisation; it changes amplitude, never reverses direction.

6. Micro Modulation (Timing)

Micro only influences pacing, not posture.

Micro Phase	Weight	Effect
Dip → Good	0–0.1	Ignored (noise floor)
Oh-Shit	0.3–0.4	Accelerate entry pace — “pulse buys”
Euphoria	0.3–0.4	Accelerate exits — “flash profit-taking”

Micro = timing overlay, particularly valuable for managing short-term rotations and blow-off tops.

7. Readiness Logic
Phase	New Entry Readiness	Trend Entry Readiness	Explanation
Dip	Wait	Wait	Structure forming; no new adds
Double-Dip	Wait / Light	Active	Fear building but still opportunity forming
Oh-Shit	Active	Active	Deploy and rotate aggressively
Recover	Active	Active	Momentum confirmed; trend adds resume
Good	Active	Active	Normal trending participation
Euphoria	Active (selective)	Wait	Focus on new/laggards; established winners held

“Active” = eligible if Intent + TA confirm.
“Wait” = queued to watchlist until conditions align.

8. Behavioural Overview (Condensed Logic)
Regime	A/E Pair	What we do
Dip	Patient / Aggressive	Cut trend breaks + overperformers; avoid adds
Double-Dip	Patient / Aggressive	Take profits, prepare laggard buys
Oh-Shit	Aggressive / Aggressive	Deploy heavily; trim rebounds fast
Recover	Aggressive / Medium	Grow exposure, take partials on pops
Good	Normal / Patient	Ride trends; minimal trimming
Euphoria	Mixed (Aggressive new, Patient old) / Medium	Trade rotations; let core winners run; micro spikes drive exits
9. Example Combinations
Macro	Meso	Micro	Result
Macro Dip + Meso Double-Dip		A = 0.4×0.8 = 0.32 → Patient–Normal, E = 0.7×1.2 = 0.84 → Aggressive	Defensive profit-taking; small probes in laggards.
Macro Recover + Meso Oh-Shit	Micro Dip	A = 0.9×1.3 = 1.17 (capped 1.0); E = 0.8×0.8 = 0.64	Deploy hard; trim on bounce; re-buy dips.
Macro Euphoria + Meso Good	Micro Euphoria	A = 0.5×1.0 = 0.5; E = 0.3×1.4 + 0.3 micro = ~0.72	Strong-in/strong-out; rotate laggards; harvest micro peaks.
10. Output Schema
{
  "A_mode": "patient|normal|aggressive",
  "E_mode": "patient|normal|aggressive",
  "A_value": 0.0–1.0,
  "E_value": 0.0–1.0,
  "readiness_new": "wait|active",
  "readiness_trend": "wait|active",
  "macro_mult": float,
  "micro_weight": float,
  "source": {
    "phase_macro": "...",
    "phase_meso": "...",
    "phase_micro": "..."
  }
}

11. Summary

Meso defines, Macro scales, Micro times.

Entries and exits adapt dynamically to context — opposites in fear, aligned in conviction.

Trend breaks and RSI divergences define capital flow, not arbitrary profit rules.

Oh-Shit = Deploy hard, scalp fast.

Euphoria = Hold core, rotate laggards, let micro peaks dictate trims.

The PM’s state updates continuously, not through switches — ensuring consistent behaviour across changing conditions.

This is now the canonical Phase → Policy Templates v1.2.
It’s aligned with your cycle logic, mean-reversion principles, and trading reality.

==============

==============

Position Manager — Part 3: Policy Integration  (v1.1)

Note: A_final is continuous (0–1) and selects the mode; the first slice is the mode’s fixed % (10 / 33 / 50). The remaining DM cap is reserved for dip ladders and trend adds.

1. Purpose

Convert real-time context (price + intent + phase + volume) into two continuous levers:

A = Entry Aggressiveness

E = Exit Aggressiveness

The PM doesn’t predict; it biases how much and how fast we act inside the guard-rails defined by the Decision Maker (DM).

2. Hierarchical Roles
Layer	Responsibility
DM	Defines max allocation per token (e.g. 9 % of portfolio).
PM	Decides what fraction of that allocation to deploy now (A) and how tightly to harvest (E).
Trader/Executor	Converts the PM’s relative orders into absolute trade sizes and executions.

Example:
DM = 9 % cap → PM 
If A_final ≈ 0.5 (Normal) → initial deploy = 33% of 9% = 2.97%, remainder reserved for dip/trend adds.
If A_final ≈ 0.8 (Aggressive) → initial deploy = 50% of 9% = 4.5%, remainder reserved.
PM chooses how much now based on mode; Trader sizes orders off DM’s cap.

3. Core Banding
Mode	Numeric Range	Description
Patient	0 – 0.3	Minimal risk-taking / slow exits
Normal	0.3 – 0.7	Default steady operation
Aggressive	0.7 – 1.0	Max size / fast rotations

Usually A and E move inversely (weak markets → patient A + aggressive E); but they can diverge dynamically.
 (euphoric → aggressive A + aggressive E),

Macro phase modulates amplitude of Meso signals (≈ ±25 %).

4. Entry Policy
Mode	Initial Deployment	Adds (−23.6 / −38.2 / −61.8 %)	Behaviour
Patient	10 % of max_alloc	23 % / 33 % / 34 % remaining adds	Wait for confirmation; slow dip buy.
Normal	33 %	33 % / 33 %	Balanced ladder adds.
Aggressive	50 %	23 % / 27 %	Front-loaded; trend biased.

A_final = fraction of DM max_alloc deployed initially.
Remaining reserve is for dip adds or trend re-entries.

5. Exit Policy

Base exit levels: +38.2 %, +61.8 %, +161.8 %, +261.8 %, +423.6 %, +685.4 %, +1089 %.
Slice size scales with E-mode:

Mode	Slice per Level (of remaining bag)	Trailing Stop
Patient	10–15 %	Loose; EMA × 1.5
Normal	20–25 %	Normal trail (N)
Aggressive	30–40 %	Tighter; EMA × 0.7

Trailing stop applies only to positions in profit.
Trail width = base × (1 / (1 + E)) → higher E = tighter.

If close < ema_long for N bars and PnL > 0 → demote to Moon Bag.
Re-add eligibility = (price > ema_long + VO ↑ + RSI > 50 + phase ∈ {Recover, Good}).
Re-add opens trend-entry path (handled in Doc 4).

6. Signal Weights (A/E Modulators) – updated
Signal	ΔA (max)	ΔE (max)	Notes
RSI divergence	±0.25	±0.25	Primary timing lead
OBV divergence	±0.10	±0.10	Confirms/denies RSI
RSI+OBV combo kicker	+0.05	+0.05	Only when both agree
Price-action geometry	±0.15	±0.20	Bull/bear breaks, S/R retests
EMA trend (confirm only)	±0.05	±0.05	Secondary
Volume+OBV state	±0.10	±0.10	0.6VO_z + 0.4OBV_z
Intent channels (aggregate)	±0.30	±0.25	Unchanged
Residual Δ vs Majors	±0.10	±0.10	Unchanged
Breadth bias	±0.05	±0.05	Unchanged

Weights clamped to ±0.4 total per lever.

6.1. TA Integration: OBV (On-Balance Volume)

6.1.1. Computation (per stream)

Inputs: your existing OHLCV.

For each bar i:

if close[i] > close[i-1]:   OBV[i] = OBV[i-1] + volume[i]
elif close[i] < close[i-1]: OBV[i] = OBV[i-1] - volume[i]
else:                       OBV[i] = OBV[i-1]

Smoothing (recommended):

OBV_ema = EMA(OBV, n=3 to 5)             # dampen micro noise
OBV_slope = slope(OBV_ema, k=5 bars)     # linear-reg slope
OBV_z = zscore(OBV_slope, lookback=7–14) # standardize per token

Multi-TF:

Micro: 1m → aggregate 5m for OBV_ema, slope over 5×5m bars

Meso: 15m/1h

Macro: 4h/1d

Store in features:

positions.features: { obv_ema, obv_z, obv_slope, obv_tf }  # per horizon cache

6.1.2. Signals we derive

OBV Trend: obv_trend = sign(OBV_slope) (−1/0/+1)

OBV Divergence vs Price:

Bullish: OBV_z > +0.5 while price making equal/lower lows → obv_div_bull = True

Bearish: OBV_z < −0.5 while price making equal/higher highs → obv_div_bear = True

OBV Confirmation: obv_confirm = (obv_trend == price_trend) (trend add confidence)

6.1.3. How it slots into existing TA terms

Replace "Volume state" with Volume+OBV state:

Current: Volume state (VO_z) ± 0.10 to A/E

New blended metric: vol_state = 0.6 * VO_z + 0.4 * OBV_z

Weights for A/E (keep total clamp the same):

ΔA += clamp( +0.10 * vol_state, -0.10, +0.10 )

ΔE += clamp( -0.10 * vol_state, -0.10, +0.10 )

Intuition: rising OBV/volume → easier entries, lazier exits; falling → harder entries, tighter exits.

Add OBV divergence alongside RSI divergence:

Keep RSI as the primary timing lead; OBV acts as a confirmer/denier:

Bull divergence pair (RSI_div_bull OR obv_div_bull):

ΔA += +0.10 (on top of RSI's own weight)

ΔE += −0.10

Bear divergence pair (RSI_div_bear OR obv_div_bear):

ΔA += −0.10

ΔE += +0.10

If both RSI and OBV show the same divergence:

Add a combo kicker: ΔA += +0.05 (bull) or ΔE += +0.05 (bear)

Trend adds confirmation gate:

In Trend Entry logic (Doc 4), extend pre-check:

Allow trend_add if:
  (sr_break != bear) AND
  (RSI_slope > 0 OR obv_trend > 0) AND
  (VO_z > 0 OR OBV_z > 0)

This lets OBV carry the confirmation when RSI is late (common in low caps).

6.1.4. Phase interaction (light touch)

In Oh-Shit / Recover, OBV_z > 0 reduces the need for perfect RSI timing: ΔA += +0.05

In Meso Euphoria, OBV_z < 0 increases exit urgency: ΔE += +0.05 (on top of policy)

6.1.5. Edge-case guards (low liquidity)

If median spread > 3% or effective slippage > 3% over last 10 trades, halve OBV's influence:

OBV_z_scaled = 0.5 * OBV_z

If average volume per bar < threshold (token-specific), ignore OBV divergence flags (set to False).

6.1.6. Logging additions

Add these keys to reasons[] where applicable:

obv_div_bull, obv_div_bear, obv_confirm, obv_z_up, obv_z_down

And persist:

positions.features.obv_ema, obv_z, obv_slope

6.2. Price-Action Geometry Layer (Support/Resistance + Diagonal Break Integration)

6.2.1. Purpose

Reintroduce pure structure awareness into the PM's decision loop.
RSI, OBV, and EMA describe energy; diagonal breaks and S/R describe form.
Together they define when momentum shifts and where to act.

6.2.2. Core Concepts

Term	Meaning	Interpretation
Support	Horizontal zone formed by clustered lows (≥3 local minima)	Buy zone; structural demand.
Resistance	Horizontal zone formed by clustered highs (≥3 local maxima)	Sell zone; structural supply.
Diagonal trendline	Regression line through last 3–5 swing highs/lows	Defines short-term directional structure.
Break	Close above/below trendline with volume confirmation	Structural momentum shift.

6.2.3. Computation (formal defaults)

For each timeframe (micro / meso):

Swing detection:

- Identify local extrema over a rolling window N = 10 bars (Micro on 5 m bars; Meso on 1 h bars).
- Require prominence ≥ 0.5 × ATR(14) on that tf to filter noise.

Trendline fit (robust):

- Use Theil–Sen regression through the last 3–5 swing highs (resistance) and last 3–5 swing lows (support).
- This yields upper_trendline(t) and lower_trendline(t) with slope/intercept robust to outliers.

Break detection:

- Bull: close > upper_trendline(t)
- Bear: close < lower_trendline(t)

Volume confirmation:

- Require (vo_z > 0.5) OR (OBV_z > 0) to mark a confirmed break.

Outputs (stored in positions.features):

{
  "sr_break": "bull" | "bear" | "none",
  "sr_conf":  float,     // volume confirmation strength 0–1
  "sr_age":   int,       // bars since break occurred
  "sr_tf":    "micro"|"meso"
}

Break signals remain active for up to M bars (default = 20) or until invalidated (price re-enters trend channel).

6.2.3.1. Confidence scoring (sr_conf)

Let distance = |close − trendline| / ATR(14) (dimensionless), where trendline is the broken line (upper for bull, lower for bear).

Let vol_term = max(0, 0.5·vo_z + 0.5·OBV_z).

sr_conf = clamp( 0.6·sigmoid(distance) + 0.4·sigmoid(vol_term), 0, 1 ).

Signal validity:

- A break remains active for M = 20 bars or until price re-enters the trend channel for ≥ 3 consecutive bars.

6.2.4. Integration Points

6.2.4.1. Entry & Exit Bias

Event	ΔA	ΔE	Logic
Bull diagonal break	+0.15	−0.10	Early breakout; enter strength.
Bear diagonal break	−0.15	+0.20	Early rollover; tighten exits.
Support retest (hold)	+0.10	−0.05	Price defended key zone; re-entry confirmation.
Resistance reject	−0.10	+0.10	Supply confirmed; take partials.

Weights clamp within existing ±0.4 total per lever.

6.2.4.2. Phase Interplay

Dip / Double-Dip:
Bull break upgrades readiness → Wait → Active (early recovery tell).

Oh-Shit:
Bull break + volume → "panic bottom" signal → A↑ 0.1; E↑ 0.1 (deploy & recycle).

Recover / Good:
Bull break = trend confirmation; increase A.
Bear break = exit warning before EMA trails trigger.

Euphoria:
Bear break + OBV↓ → exit acceleration (micro blow-off detector).

6.2.4.3. Trend Entry Gate

In Trend Entry Logic, extend the pre-check:

Allow trend_add if:
    sr_break == "bull"
    and sr_conf ≥ 0.5
    and (RSI_slope > 0 or OBV_z > 0)

This lets price-action geometry open re-entries even when indicators lag.

6.2.4.4. Stop & Demotion Sync

If sr_break == "bear" and VO_z > 0.5, trigger an early demotion (Core → Moon) even before EMA stop.

If later sr_break == "bull" and RSI > 50, unlock re-add eligibility sooner (trend-reclaim logic).

6.2.5. Behavioural Summary

Structure Event	Market Context	PM Reaction
Bull break + VO↑	Any non-Euphoria phase	Promote readiness; favour early adds.
Bear break + VO↑	Any strong phase	Tighten exits, trail close to EMA.
Support hold (OBV↑)	Dip / Double-Dip	Validate continuation; scale cautiously.
Resistance reject (OBV↓)	Good / Euphoria	Secure profits, flag potential reversal.

6.2.6. Logging

Each detection adds sr_break_bull, sr_break_bear, sr_retest, or sr_reject to pm_decision.reasons[].
These feed learning correlations with forward PnL.

6.2.7. Summary

Diagonal breaks and S/R geometry restore contextual intelligence to the TA stack:

EMAs describe trend state,

RSI/OBV describe internal energy,

Geometry describes structure shift.

The PM now knows what changed, where, and how confidently—turning the technical layer from reactive indicators into a unified market-structure sensor.

6.3. Cut-Pressure System - Antisymmetric Risk Management

6.3.1. Purpose & Intuition

High when risk of buying tops / overtrading is highest → Meso Good → Euphoria, especially when momentum starts rolling over.

Medium in Dip / Double-Dip (we still want to trim leaders and avoid early adds).

Low in Oh-Shit (deploy on fear; don't strangle entries).

It's anticipatory: uses level and turning (slope/curvature) of phase to tighten at tops and loosen at bottoms.

6.3.2. Component Breakdown (all 0–1; we log each for transparency)

6.3.2.1. Phase Tension (anti-cyclical core)

Let S = PhaseScore_meso (z-scored), C = Curvature_meso (slope-of-slope), both from SPIRAL.

We want:

High tension when S is high (Good/Euphoria) and C ≤ 0 (topping).

Low tension when S is very low (Oh-Shit) and C ≥ 0 (bottoming).

A compact mapping:

phase_tension = clip01(
    0.6 * sigmoid(+S)         # high in Good/Euphoria
  + 0.4 * sigmoid(+S) * sigmoid(-C)  # extra if turning down
  - 0.6 * sigmoid(-S) * sigmoid(+C)  # relief if bottoming & turning up
)

Where sigmoid(x) = 1 / (1 + e^{-k x}), k≈1.2 (gentle).

6.3.2.2. Core Count (seesaw around 12)

Single smooth term that adds pressure when crowded and removes when under‑exposed.

Let d = core_count − 12; τ≈4 (spread), k≈0.25 (max swing for A/E after coupling).

delta_core = k · tanh(d / τ)            # antisymmetric, in [−k, +k]

Normalized component for cut_target mixing (0–1):

core_pressure = clip01( 0.5 + 0.5 · tanh(d / τ) )   # 0 at far under, 1 at far over; 0.5 at 12

6.3.2.3. Liquidity / Cash Stress (optional, small)

Avoids tightening if we're already cash-rich, and avoids loosening if cash is nearly zero.

liquidity_stress = clip01( 1 - free_cash_ratio )   # 0 = plenty cash, 1 = none

6.3.2.4. Sentiment Skew (intent polarity)

We don't want to loosen if social is euphoric, nor tighten if social is capitulating.

intent_skew = clip01( pos_intent_share - neg_intent_share )  # 0–1
# We use it contrarian: more euphoric -> more pressure

6.3.3. Computation Methodology

6.3.3.1. Raw target & smoothing

Weighted blend (no lookahead, all observable):

Dominance modulators (front-run inflections; stronger for USDT.D)

Inputs (computed on 7d changes with 90d z-scores):

- For BTC.D and USDT.D, compute slope_z (first derivative), curv_z (turning), level_z (current extremeness).
- early_rise = (slope_z > 0.6 and curv_z > 0)
- peak_roll = (level_z > 1.0 and curv_z < 0)

Nudges (per signal):

- btc_dom_delta =
    +0.06 if early_rise_btc else 0
    −0.05 if peak_roll_btc else 0
  # context tweaks from rotation
  btc_dom_delta +=
    (−0.02) if (rotation_spread_z > +0.8 and slope_btcusd > 0) else 0
  btc_dom_delta +=
    (+0.02) if (rotation_spread_z < −0.8 and slope_btcusd < 0) else 0

- usdt_dom_delta =
    +0.12 if early_rise_usdt else 0
    −0.12 if peak_roll_usdt else 0

dominance_delta = clamp(btc_dom_delta + usdt_dom_delta, -0.18, +0.18)

cut_target = clip01(
    0.55 * phase_tension      # main driver (anti-cyclical)
  + 0.25 * core_pressure      # folded core-count seesaw (around 12)
  + 0.10 * liquidity_stress
  + 0.10 * intent_skew        # contrarian: euphoric → higher pressure
  + dominance_delta           # dominance-based anticipatory nudge
)

Smooth to avoid lurching:

cut_pressure[t] = cut_pressure[t-1]
                + α * (cut_target - cut_pressure[t-1])

α = 0.25 on phase transitions; else 0.15
Δcut_pressure per hour capped at ±0.20

We persist: cut_pressure_raw, cut_pressure, and components for audit, including core_count, core_pressure, and delta_core.

Additional persistence (dominance audit):

- btc_dom_delta, usdt_dom_delta, dominance_delta
- btc_dom_slope_z, btc_dom_curv_z, btc_dom_level_z
- usdt_dom_slope_z, usdt_dom_curv_z, usdt_dom_level_z

6.3.4. Phase-Specific Behavior (sanity check)

(Assuming typical S/C signs from SPIRAL; exact value comes from formula.)

Meso phase	Expected cut_pressure	Rationale
Euphoria	0.70–0.95	Top risk; tighten exits, slow new adds.
Good	0.50–0.75	Strong trend; take profits into strength, don't bloat.
Recover	0.30–0.50	Let adds through; still prune weak.
Double-Dip	0.35–0.55	Avoid early adds; trim overperformers/early trend breaks.
Dip	0.40–0.60	First pullback; stay selective; don't rush.
Oh-Shit	0.10–0.30	Panic bottom; loosen to deploy and recycle.

Macro modulates amplitude (±0.15), Micro briefly nudges (+0.1 on micro-Euphoria, −0.1 on micro-Oh-Shit) for 30–60 min only.

6.3.5. Integration with A/E System

A_final = A_policy * (1 - 0.33 * cut_pressure)

E_final = E_policy * (1 + 0.33 * cut_pressure)

DeadScore_final = DeadScore * (1 + 0.3 * cut_pressure)

So in Euphoria, A compresses and E expands (exactly what you want); in Oh-Shit, A breathes wider and E relaxes.

6.3.6. Examples (quick numbers)

Meso Euphoria, crowded (core=34), euphoric intent, low cash
phase_tension≈0.9, core≈0.92, liq≈0.7, intent≈0.8 → cut_target≈0.87 → cut_pressure≈0.8–0.9
→ A_final ~ 73–80% of policy; E_final ~ 126–133% of policy.

Meso Oh-Shit, under-exposed (core=10), intent fearful, some cash
phase_tension≈0.15, core≈0, liq≈0.3, intent≈0.1 → cut_target≈0.18 → cut_pressure≈0.15–0.25
→ A_final ~ 92–95% of policy; E_final ~ 105–108% (slightly up, not tight).

6.3.7. Why this matches your intent

It tightens late, where tops form (Good→Euphoria), and loosens late where bottoms form (Double-Dip→Oh-Shit→early Recover).

It doesn't overreact to Micro chop (only small, transient nudge).

It's self-documenting: each component logged so we can see why pressure rose.

6.3.8. Logging & Audit Trail

Persist for each PM decision:
- cut_pressure_raw (target before smoothing)
- cut_pressure (final smoothed value)
- phase_tension, core_congestion, liquidity_stress, intent_skew (components)
- phase_meso, curvature_meso (SPIRAL inputs)

7. Intent Channel Weights
Channel	Examples	ΔA	ΔE	Notes
High-Confidence Buy	adding_to_position, technical_breakout, fundamental_positive	+0.25	−0.10	Strong immediate entry bias.
Medium-Confidence Buy	new_discovery, comparison_listed	+0.15	−0.05	Soft adds.
Profit Intent	“taking profit on 3×,” “trimmed half”	−0.15	+0.15	Momentum cooling; allow trend re-adds only.
Sell / Negative	“sold all,” “team shady,” “avoid this”	−0.25	+0.35	Capital protection; adds to DeadScore if PnL < 0.
Mocking / Derision	“dead coin,” “L project”	−0.10	+0.10	Early warning for decay.
Neutral / Educational	research_neutral, market_analysis	± 0	± 0	Ignored.

Sub-scores are summed and clamped; no single composite intent_score.

8. DeadScore Computation
DeadScore = 0.4*(PnL < -30%)
           + 0.2*(VO < 0.5)
           + 0.2*(intent_strength < 0.2)
           + 0.2*(residual_pnl < -0.5)


Adjustments:
If a token underperforms during both upswings and selloffs (negative residual on green days and worse-than-breadth on red days) → DeadScore +0.2 (persistent structural weakness).
If intent divergence > 0.5 (price flat but mentions ↑) → hold (sleeper override).
If macro negative and residual_pnl < −1.0 → trim.
If macro positive and residual_pnl < −1.0 → replace with stronger idea.
Convert to Moon Bag if DeadScore > 0.6 and no positive intent reversal.
(Moon Bag converstion = sell 69% to 90%)

9. Core vs Moon Bags
Type	Allocation Cap	Rules
Core Bag	≤ DM max alloc (e.g. 9 %)	Actively managed by A/E policy.
Moon Bag	≤ 0.9–0.3 % each (soft cap)	Small leftovers from trim / demotion; no averaging down; only sold on major pumps.

Promotion / Demotion logic:

Demote → Moon when (DeadScore > 0.6) OR EMA-long trail stop hits (and PnL > 0). Sell 69–90%, keep residual Moon Bag; free capital.

Promote → Core when price > EMA-long, VO rising (VO_z > 0.5), RSI > 50, and intent high-confidence > 0.5 (any two-of-three TA + intent suffice).

Moon bags don’t count toward position limit (> 30 rule).

10. Summary Flow

DM assigns max allocation & intent context.

PM computes A/E from signals → deploys A_final × max_alloc initially.

Dip adds / trend adds unlock via Fib levels or EMA reclaim.

E controls harvest size & trailing tightness.

DeadScore / Intent changes update Core↔Moon status.

Logs feed Learning for future refinement.

========

========

Position Manager — Part 4 Trend Entry & Recycle Logic (v1.1)
1. Purpose

Convert realised profits and prior exits into controlled continuation entries when a trend still has strength.
Avoid “exit → missed pump” while preventing over-re-risking.

2. Trigger Conditions

Trend-entry evaluation occurs on every exit strand logged.

Category	Trigger	Description
Partial Harvest	+23.6 / +38.2 / +61.8 exit	Evaluate redeploy of a fraction of realised proceeds.
Demotion Exit	Core → Moon sell	Lock re-adds until EMA reclaim.
Stop Exit	EMA trail breach	No immediate trend entry; wait for new structure.
3. Pre-Check Filters

A trend entry may fire only if:

sr_break != bear
(RSI_slope > 0 OR obv_trend > 0 OR sr_break == "bull")    # RSI, OBV, or structure confirmation
(VO_z > 0.5 OR OBV_z > 0 OR sr_conf >= 0.5)              # volume, OBV, or structure confirmation
phase_meso ∈ {Double-Dip, Oh-Shit, Recover, Good}
DeadScore < 0.4


Optional override:
if intent_divergence > 0.5 and price flat → allow “sleeper” re-add.

4. Phase-Based Trend Entry Table
Meso Phase	Default A Mode	Trend Entry Behaviour	Ladder Levels Active	Notes
Dip	Patient	None (structure breaking)	—	Wait for reset.
Double-Dip	Patient → Normal	Yes (cautious adds)	−38.2 %, −61.8 %	Leaders only with VO confirmation.
Oh-Shit	Aggressive	Yes (heavy redeploys)	−23.6 %, −38.2 %, −61.8 %	Deploy into fear; highest pay-offs.
Recover	Aggressive	Yes (full rotation)	−23.6 %, −38.2 %	Trend continuation sweet spot.
Good	Normal	Moderate adds	−23.6 %	Ride strength but rotate slowly.
Euphoria (Meso)	Patient	No adds	—	Freeze trend entries completely.
Euphoria (Macro)	Normal	Small continuations only	−23.6 %	Permitted only on ATH breaks + VO↑ + intent↑.

Macro context modulates size (±25 %), but cannot override the “no trend entries in Meso Euphoria” rule.

5. Ladder Level Access
Level	Conditions	Mode Access
−23.6 %	VO > 1	Normal, Aggressive
−38.2 %	Structure intact + VO ≥ 1	All
−61.8 %	Confirmed retest + RSI slope > 0	Patient only
6. Redeploy Fraction

Redeploy uses realised proceeds, not free capital.

A Mode	trend_redeploy_frac	Notes
Patient	0.10	Tiny pulse; confirmation first.
Normal	0.15	Standard rotation.
Aggressive	0.25	Momentum continuation; quick reload.

New entries tagged trend_entry=True for traceability.

7. Stop & Lock-Out

After redeploy:

if close < ema_long for N bars:
    freeze trend adds for lock_h (default = 36 h)


→ prevents over-compounding into rolling tops.

8. Recycling Flow
Harvest event →
    if prechecks pass:
        size = trend_redeploy_frac × proceeds
        create new entry_plan(trend_entry=True)
        position.size += size
        log pm_decision {type: "trend_add", reasons[]}
    else:
        log "no_trend_add" for Learning


Forward PnL (24 h / 72 h) is logged to train future redeploy rules.

9. Interaction with Core / Moon

Trend adds allowed only on Core Bags.

Once demoted to Moon → no trend entries until re-promotion.

Trend adds merge into existing position (no mini-harvests).

Weighted average entry price recalculates after each add:

avg_entry_new =
    (size_prev * avg_entry_prev + size_add * add_price)
    / (size_prev + size_add)


→ all future Fib exit levels and PnL use this updated base.

10. Learning Signals

Learning later optimises:

Typical VO / RSI thresholds that yield positive redeploy PnL.

Ideal trend_redeploy_frac per archetype.

EMA vs diagonal break efficacy.

Mean dwell between harvest → redeploy cycles.

Summary

Trend Entry Logic v1.1 = disciplined profit recycling:

Never new capital — only re-deployed gains.

Redeploys allowed in Double-Dip → Oh-Shit → Recover → Good.

Blocked in Meso Euphoria or early Dip.

Size and ladder access depend on A mode and volume confirmation.

Trend adds update average entry and fold into normal position lifecycle.

=======

========

Position Manager — Part 5: New Token Entry Mode (v1.1)

1. Purpose

Scope: Applies only to brand-new tokens / first-time tickers (no prior Lotus trade history, VO baseline, or residual curve).
Goal: Discover tape quality with minimal risk, then flip fast to full sizing as soon as the market confirms.

2. Activation

Trigger: is_new_token = true at first signal from DM.

Preset: A=0.20 (Patient), E=0.80 (Aggressive) on a probe sleeve only.

Initial size: size_frac = 0.10 × DM.max_alloc (i.e., 10% of the cap).

Lock: reentry_lock_h = 36 still applies to any closes; trend-adds are allowed per rules below.

Rationale: start small to learn liquidity/spread/response without paying full exposure risk.

3. Observation Window (5–15 minutes, Micro frame)

Data to monitor (updated per 60s bar):

VO_z (volume z-score vs emerging baseline)

RSI_1m/5m (over 50 and rising)

Trend state: EMA_short > EMA_long or diagonal reclaim

Micro stability: price not whipsawing >5% around entry

Slippage & spread: <2–3% effective cost on test orders (internal metric)

4. Flip Conditions (escalate within minutes)

Escalate from Probe → Build if ≥ 2 of the following hold for ≥ 3 consecutive minutes:

VO_z ≥ +1.0 OR sr_break == "bull" (sustained expansion or structure break)

RSI > 50 and rising OR obv_trend > 0 (positive momentum)

Trend confirm: close above EMA_long OR diagonal reclaim OR sr_break == "bull" (structure confirmation)

Micro stability: |price − entry| ≤ 5% after initial thrust

On flip:

A → 0.8 (Aggressive/Normal) for the build sleeve

E → 0.4 (Moderate) (avoid scalping the move we are joining)

Execute build adds on first controlled pullback:

−23.6%, then −38.2% from local high or anchor

Tag position new_token_mode=false after first build add (token now "known")

Design: the probe sleeve keeps E tight; the build sleeve inherits live A/E from policy so we don't auto-trim the very move we sized into.

5. If Flip Fails (no confirmation)

Remain in probe state and apply protective exit only on structure break:

EMA break test: require 15 consecutive 1-minute closes below EMA_long to mark trend_break=true.

Action: do not dump into the red; queue a trim on first bounce to EMA zone.

If no reclaim within 6 bars, demote to Moon (sell 70–90%) and end mode.

We exit on strength (the bounce), not into the flush.

6. Trend-Add Rules (while New Token Mode is active)

Allowed once flip conditions met or when Recover/Good and price reclaims diagonal.

Levels gated by volume/structure:

−23.6%: VO_z > 1.0 (Normal/Aggressive only)

−38.2%: structure intact + VO ≥ 1.0 (all modes)

Never average down in pure chop (EMA_short < EMA_long and RSI slope < 0).

7. Interaction with Portfolio State

cut_pressure high (overcrowded/late-cycle): keep probe longer; require 3/4 flip tests instead of 2/4.

Underexposed (<12 cores): allow fast-track (flip on 2/4 tests promptly).

DeadScore coupling: unchanged; DeadScore_final applies normally to demotion if weakness persists.

8. Logging (for learning)

Each minute during the window (or on events) emit a pm_decision strand:

Field	Example
decision_type	add_probe / flip_build / hold_probe / trim_on_bounce
size_frac	0.10 (probe), then 0.23/0.27 adds
A_value / E_value	0.20 / 0.80 → 0.80 / 0.40
reasons[]	[new_token, VO_z_up, RSI_up, EMA_reclaim]
phase_state	{macro, meso, micro}
forward_pnl_24h / 72h	placeholders for backfill

9. Deactivation

new_token_mode=false when any of:

First build add executed, or

60 minutes have elapsed with no flip and structure broke + demotion executed, or

Token achieves +61.8% from initial entry (harvested) and E_mode ≥ Normal.

10. Safety Rails & Edge Cases

Liquidity guard: if average spread > 3% or effective slippage > 3% on probes → do not flip, keep size minimal until resolved.

Herd burst: if ≥3 curators mention within <30 min (temporal sync high) and VO not confirming → pause flip (avoid exit-liquidity traps).

Macro hostility: if Macro = Euphoria rolling over (PhaseScore ↓ sharply), require trend confirm and VO_z for flip.

Summary

Start every brand-new token with 10% probe (A low, E high).

Flip fast (minutes) to full sizing only when the market confirms (volume, RSI, trend, stability).

Exit on bounce if structure breaks; never dump at lows.

Mode auto-disables after first build add or failed structure.

=======


======



















======

J) Data & Schema — “Where do these numbers live?”

Add to positions (or positions_features) so PM has state:

phase_macro/meso/micro, confidences

A_mode, E_mode, readiness_new, readiness_trend

RSI/EMA/Volume derived fields (rsi_div_strength, ema_trend_strength, vo_state, obv_ema, obv_z, obv_slope, sr_break, sr_conf, sr_age, sr_tf)

Intent fields (intent_confidence, intent_direction, intent_divergence)

Behavioural profile (lead_score, dip_strength, trend_strength, recovery_speed, intent_coherence, archetype_tag)

Core/Moon + demotion metadata (core_moon_tag, core_size_frac, moon_retention_frac)

Health guards (dead_score, cycle_response)

K) Evaluation hooks — “Does it behave how we intended?”

Forward PnL (6h/24h/72h) per decision with context snapshot.

Outcome by A/E mode & phase.

“Phase sanity” (did labels follow cycle; if not, dampen horizon weight).

Exposure drift monitor (system’s bias to too-much exposure).