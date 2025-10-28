Position Manager — Dynamic State & Divergence Playbook

Scope: Low-cap coins (thin liquidity, fat tails).
Goal: Simple surface, deep internals. PM exposes levers; Learning tunes them.
Core idea: Don’t classify coins; track motion (state probabilities) and act on transitions using RSI–price divergence + diagonal breakouts with volume context.

0) Design Principles

Levers, not rules: PM defines an instrument panel; Learning pulls the knobs.

State over labels: A coin expresses a mix of behaviors that evolve over time.

Scale, don’t snipe: Signals drive laddered adds/trims, not binary buys/sells.

Evidence checkpoints: Time gates (e.g., 36/72h) trigger re-evaluation, not forced exits.

Portfolio senses: Entries on fear, harvest on euphoria; respect divergence vs SOL/ETH/BNB.

1) Behavior Archetypes (for intuition & learning targets)
#	Archetype	Description	Default PM Bias
1	Strong Trender	Up → consolidate → up	Scale-in, trail, slice profits
2	Early Hype → Dip → Second Wave	Social burst → pullback → reaccum	Be patient, re-add on structure
3	Hidden Sleeper	Flat/quiet → surprise revival	Hold seed, add on pulse
4	Dead Coin	No flow, slow bleed	Exit/recycle
5	Fakeout/Exhausted Top	One-bar pop, no follow-through	Trim, tighten trail
6	Rotation / Mean-Revert	Weak on risk-on → leads next leg	Buy after majors cool

Learning’s job: estimate state probabilities and transition likelihoods (not a single label).

2) The Six Core Signals (kept minimal)
Signal	Meaning	Quick Proxy
Momentum (m)	Direction + speed	(EMA_15m − EMA_1h) / EMA_1h + 1h return Z
Conviction (c)	Narrative/social heat	Mentions velocity / engagement
Liquidity (l)	Participation	Volume / avg_volume, orderbook depth
Volatility (v)	Opportunity vs chaos	stdev(returns_6h)
Structure (s)	Support/resistance integrity	Volume profile + pivot trendlines
Relative Strength (r)	Divergence vs majors	Residual vs SOL/ETH/BNB (β-hedged)

PM computes/ingests these; Learning assigns weights by regime.

3) RSI–Price Divergence + Diagonal Breakouts (the core trading edge)
3.1 RSI (custom from your OHLC)

Wilder-style EMA gains/losses (e.g., RSI(14)).

Optionally volume-weighted RSI: RSI × (vol / avg_vol).

3.2 Trend Slopes (over W bars)

price_slope = LR(close[-W:])

rsi_slope = LR(RSI[-W:])

Normalize to Z if cross-asset comparability needed.

3.3 Divergence

Bullish divergence: price_slope < 0 and rsi_slope > 0 (persist ≥ K bars).

Bearish divergence: price_slope > 0 and rsi_slope < 0 (persist ≥ K bars).

Interpretation: Divergence = energy building against price direction.
Use it as a setup (not a trigger).

3.4 Diagonal Trendlines & Breaks

Detect pivots (k=3–5): pivot_high if high[i] == max(high[i−k:i+k]), pivot_low similar.

Fit lines through last 2–3 pivot_lows (for downtrend tests) and pivot_highs (for uptrend tests).

Bull break: close > trend_high + α·ATR; Bear break reversed.

Require retest or ATR buffer to reduce false breaks.

3.5 Volume Context

Volume Oscillator: VO = EMA_1h(vol) / EMA_24h(vol).

Climax bar: vol >= k × max(vol_72h) + wick structure → potential top/bottom.

Treat volume as a multiplier, not a gate.

4) From Signals to Actions — Scale Plans (not binary trades)
4.1 Bull Scale-In Template (laddered)

Setup (A): Bullish divergence (RSI↑, price↓, ≥K bars).

Trigger (B): Bull diagonal breakout (ATR-buffer).

Confirmers (C): VO ≥ 1.5 or positive residual vs majors.

Action:

add_now: small (e.g., 25% of add budget) on breakout close.

limit_retest: trendline/vwap/EMA(15).

limit_pullback: −1·ATR from breakout.

Cancel pending adds if reclaimed below trendline − α·ATR.

4.2 Bear Scale-Out Template (mirror)

Setup: Bearish divergence.

Trigger: Bear diagonal breakdown.

Action: Trim 10–30%, tighten trailing stop; allow buyback on reclaim.

4.3 Signal Strength → Sizing
div_strength = |price_slope_z| + |rsi_slope_z|
break_score  = (close - trendline) / ATR
vol_score    = log(VO)

signal_score = w1*div_strength + w2*break_score + w3*vol_score
size = size_fn(signal_score)  # monotonic map with caps

5) Speed Classes (rate-of-change matters)
Class	Example	Bias
Flash (<15m)	+30–100%	Instant partial harvest; deep re-entry bids
Impulse (hours)	+50–200%	Ladder out; re-add on 20–30% retrace
Trend (days)	sustained	Slow trail; smaller re-adds
Parabolic (>3d)	blow-off	Heavy harvest; no re-add until reset

Compute ROC, bucket by historical percentiles; switch to harvest-and-reload mode on extreme speed.

6) Portfolio Context & Divergence vs Majors

Majors basket (SOL/ETH/BNB): regress per-token returns on basket → residual r.

Divergence score D: EMA_1h(r) / stdev_1h(r) (Z).

Leaders on down days: Majors < 0 and D ≥ +1 → earlier harvest on next thrust + aggressive buyback after first dip.

Day map (intraday): Entries on fear (breadth down), harvest on euphoria (breadth up).

Portfolio levers (Learning-tuned):

Aggressiveness mode

Cut pressure

Harvest bias

Time patience (36/72/120h checkpoints)

Capital deployment rate

7) Guardrails (low-cap specifics)

Do-Not-Touch window: first 6–12h after entry.

72h checkpoint: reassess (not auto-exit). Look for pulse vs exhaustion:

Exhaustion (drain): vol trend collapsing, mentions −80% → halve (free a slot).

Pulse: vol spike 3–5×, reversal wick → small add with tight invalidation.

Re-entry lock: No reopen within 36h unless price ≤ 0.70 × last_exit and (fresh bull break or rsi_slope > 0).

Slippage/Depth: skip orders when spread > S_max or depth < D_min.

Hysteresis: cooldown M bars after failed breakout to avoid churn.

Soft/Hard count bands: pre-trim at 30; must reduce above 34 (prefer mid-caps without leadership).

8) State Engine (how this breathes)

PM maintains a state probability vector per coin:

{ "trender": 0.45, "early_hype": 0.20, "fakeout": 0.15, "dead": 0.10, "rotation": 0.10 }


Learning updates this vector; PM blends actions accordingly (no whiplash).

Transitions (e.g., EarlyHype→Dip→Trender) drive lever switches.

Speed class augments state to choose harvest vs reload bias.

9) Data Model (minimal, enough to learn)

Per timeframe (1m/5m):

price_slope, rsi, rsi_slope, div_persist_bars

pivot_hi/lo, trendline_hi/lo, break_score, atr

vol, vol_osc, climax_flag

majors_beta, residual, D (divergence vs majors)

signal_score, speed_class

Per decision strand (PM → Controller):

{
  "action": "add_now|limit_retest|trim|trail|hold",
  "size_pct": 0.15,
  "reasons": ["bull_divergence","diagonal_break","VO>1.8"],
  "context": {
    "state_probs": {...},
    "portfolio_mode": "recover|good|euphoria|dip|double_dip|oh_shit",
    "locks": {"reentry": true}
  }
}


Outcomes for learning:

forward_pnl_6h/24h/72h

slippage_bps, fill_quality

regret_metric (sold vs held cohort)

10) Implementation Phases (quick to slow)

Phase 1 — Core signals & templates

Compute RSI, slopes, pivots, trendlines, ATR, VO.

Implement Bull Scale-In and Bear Scale-Out templates.

Add guardrails (DNT, checkpoints, locks).

Log decision strands + outcomes.

Phase 2 — Divergence vs Majors & Speed

Add β-hedged residuals and D.

Add speed classes and harvest-reload behavior.

Start Learning on size/threshold weights.

Phase 3 — State Engine

Emit/ingest state_probs from Learning.

Smooth lever transitions; add hysteresis and portfolio-level tuning.

11) Configuration (sane defaults; Learning will tune)
windows:
  rsi_period: 14
  slope_bars_1m: 30
  slope_bars_5m: 20
  pivot_k: 4
  atr_period: 14

breakout:
  atr_buffer_alpha: 0.3
  retest_preference: vwap_or_trendline

divergence:
  min_persist_bars: 6
  w_div: 0.5
  w_break: 0.3
  w_vol: 0.2

volume:
  vo_spike: 1.8        # EMA1h/EMA24h
  climax_k: 3.0

guards:
  do_not_touch_h: 8
  checkpoint_h: [36, 72, 168]
  reentry_lock_h: 36
  reentry_discount: 0.30
  slippage_max_bps: 40
  spread_max_bps: 60

portfolio:
  soft_band: [28, 34]
  max_positions_hard: 40

12) Pseudo Interfaces (drop-in ready)
def compute_signals(candles_1m, candles_5m, mentions, majors):
    # returns dict of core signals incl. price_slope, rsi_slope, pivots, trendlines, ATR, VO, D, speed_class
    ...

def bull_scale_in_plan(signals, cfg):
    if signals['bull_div'] and signals['bull_break']:
        score = score_signal(signals, cfg)
        return [
            {"type":"add_now", "size": f(score)},
            {"type":"limit_retest", "px": signals['trend_hi'], "size": g(score)},
            {"type":"limit_pullback", "px": signals['close']-signals['ATR'], "size": h(score)}
        ]
    return []

def bear_scale_out_plan(signals, cfg):
    if signals['bear_div'] and signals['bear_break']:
        return [{"type":"trim", "size": 0.15}, {"type":"tighten_trail": True}]
    return []

13) How This Stays Simple (without losing depth)

One core combo: RSI–price divergence (setup) + diagonal breakout (trigger).

One context multiplier: volume/ATR (confidence).

One portfolio compass: divergence vs majors + breadth (mood).

Everything else: levers and logs for Learning to tune over time.

Final Note

This playbook turns your intuition into a compact, auditable system:

Detect mispriced energy (RSI–price divergence).

Wait for structure break (diagonals).

Scale intelligently (ladders) with volume context.

Harvest/reload using speed and portfolio mood.

Keep learning which thresholds/sizes work best for your niche


=========

Position Manager Architecture (v2)

Low-Cap Dynamic State & Divergence System

0. Overview — Philosophy & Objective

Purpose: Provide intelligent, adaptive position management for volatile, low-cap coins — balancing simplicity and flexibility, so behavior can evolve through learning rather than rigid rules.

Core principle:
We don’t label coins as “good” or “bad.” We track how they behave, how those behaviors change, and how the portfolio should respond in rhythm with that motion.

The Position Manager (PM) defines the levers — the structural logic.
The Learning System defines the motion — how those levers are pulled.

1. Market Behavior Archetypes

Low-caps cycle between recognizable states.
Each state is temporary, and coins constantly transition between them.

#	Archetype	Description	Desired PM Behavior
1	Strong Trender	Sustained upward moves, shallow pullbacks, steady attention.	Scale in on dips; trail profits upward.
2	Early Hype → Dip → Second Wave	Pump soon after entry, correction, then reacceleration.	Wait out dip, re-add near structure or diagonal break.
3	Hidden Sleeper	Quiet, low-volume, sudden revival.	Hold seed; scale when volume returns.
4	Dead Coin	Volume decay, narrative gone, price bleed.	Exit or halve after time checkpoint.
5	Fakeout / Exhausted Top	Sharp pump with collapse in volume.	Trim quickly; avoid re-adding near top dip.
6	Rotation / Mean-Revert	Weak during rallies, leads in next rotation.	Watch divergence vs majors; enter early next leg.

Learning predicts state probabilities and transition likelihoods.
PM acts on transitions — not static categories.

2. Core Metrics — What We Measure

Six continuous signals describe every coin’s state:

Signal	Description	Typical Formula
Momentum (m)	Direction & speed	(EMA_15m − EMA_1h) / EMA_1h + 1h return Z
Conviction (c)	Social & narrative intensity	Mentions velocity, engagement change
Liquidity (l)	Participation & tradability	vol / avg_vol, orderbook depth
Volatility (v)	Energy & risk	stdev(returns_6h)
Structure (s)	Integrity of support/resistance	Volume profile, pivot trendlines
Relative Strength (r)	Divergence vs majors	residual after β-regression vs SOL/ETH/BNB

Everything else (state, levers, scaling, reflection) derives from these.

3. Volume System — The Market’s Pulse

Volume is the heartbeat of low-caps.
It reveals conviction, exhaustion, and reversals better than price alone.

3.1 Volume Oscillator
𝑉
𝑂
=
𝐸
𝑀
𝐴
1
ℎ
(
𝑉
)
𝐸
𝑀
𝐴
24
ℎ
(
𝑉
)
VO=
EMA
24h
	​

(V)
EMA
1h
	​

(V)
	​


VO > 1.5 → expanding participation.

VO < 0.7 → fading interest (danger zone).

3.2 Volume Divergence (Price vs Volume)

When price and volume disagree:

Type	Meaning	Implication
Bullish divergence	Price down, volume up	Absorption — accumulation, potential reversal
Bearish divergence	Price up, volume up sharply	Distribution — possible blow-off top
Neutral / Drain	Both declining	Death spiral — narrative fading
3.3 Volume Extremes (Climax Detection)

A single bar’s volume vs history:

if volume ≥ 3× max(volume_72h):
    if long_lower_wick → Exhaustion bottom (potential add)
    if long_upper_wick → Blow-off top (harvest)


After a climax, expect quiet phase → reaccumulation → breakout.

3.4 Volume Dry-Up (Setup Phase)

Sustained low volume (<0.4× 24h average) → “coiled spring” setup, especially if RSI rising or diagonal pressure building.

3.5 Volume in Context

Rising volume confirms breakouts.

Sudden spikes confirm reversals.

Gradual decay signals the end of narrative energy.

Volume doesn’t tell direction — it tells importance.

4. Momentum, RSI & Divergence System
4.1 Custom RSI

Compute from your own OHLC:

RS = EMA(gains, N) / EMA(losses, N)
RSI = 100 - 100 / (1 + RS)


Optionally volume-weighted RSI = RSI × (vol / avg_vol).

4.2 RSI–Price Divergence

Compare slopes:

price_slope = LR(close[-W:])
rsi_slope   = LR(RSI[-W:])

Type	Criteria	Meaning
Bullish divergence	price_slope < 0 & rsi_slope > 0	Energy building → potential bottom
Bearish divergence	price_slope > 0 & rsi_slope < 0	Exhaustion forming
Strength		sum of

Persistence ≥ K bars filters noise.

4.3 Combined Logic

Setup: Divergence appears.

Trigger: Diagonal breakout (see next section).

Confirmation: Volume spike or positive relative strength.

Action: Laddered add (breakout, retest, pullback).

Divergence = setup, breakout = go signal, volume = confidence.

5. Structural Context — Support, Resistance & Diagonals

Structure = where participants agree on value.

5.1 Support / Resistance Zones

From volume-by-price peaks:

sup_zone: nearest cluster below price.

res_zone: nearest cluster above price.

Compute:

𝑠
𝑢
𝑝
𝐶
=
1
−
∣
𝑝
𝑟
𝑖
𝑐
𝑒
−
𝑠
𝑢
𝑝
𝑧
𝑜
𝑛
𝑒
∣
𝑝
𝑟
𝑖
𝑐
𝑒
𝑟
𝑎
𝑛
𝑔
𝑒
supC=1−
price
r
	​

ange
∣price−sup
z
	​

one∣
	​


High supC → stable base.
High resP → nearing ceiling.

5.2 Diagonal Trendlines

Detect pivots:

pivot_high = high[i] == max(high[i-3:i+3])
pivot_low  = low[i]  == min(low[i-3:i+3])


Fit regression lines through last 2–3 pivots.

Break conditions:

Bull break: close > trend_high + α·ATR

Bear break: close < trend_low − α·ATR
(α≈0.2–0.5)

5.3 Diagonal + Divergence Fusion
Condition	Signal	Behavior
RSI↑, Price↓ + Bull diagonal break	Accumulation break	Scale-in
RSI↓, Price↑ + Bear diagonal break	Exhaustion break	Harvest / tighten
Divergence but no break	Setup only	Watch for trigger
Break without divergence	Potential fakeout	Reduce size or wait for confirmation
6. Time & Lifecycle Rules
6.1 The 36-Hour Rule (clarified)

Purpose: Prevent premature exits on mild dips.

NOT a block on profit-taking.

Implementation:

<36h: Don’t cut purely for small losses.

If coin performs very well (fast profit), ignore 36h; harvest normally.

Exception: system stress (portfolio >34 positions).

6.2 The 72-Hour Checkpoint

Checkpoint, not timeout.

Re-evaluate conviction.

If still red >−20% and volume/mentions collapsed → halve.

If volume rising → hold / add small.

6.3 Speed Classes
Type	Example	Bias
Flash (mins)	+30–100%	Quick partial harvest; deep re-entry
Impulse (hours)	+50–200%	Ladder out; reload 20–30% below
Trend (days)	sustained	Trail; slow re-adds
Parabolic (multi-days)	blow-off	Full harvest; wait reset

Use ROC percentile to classify speed; faster = more aggressive harvest.

6.4 Re-Entry Logic

No reopen within 36h unless:

Price ≤ 0.70× last exit and

Either RSI slope ≥ 0 or fresh diagonal breakout.

7. Portfolio Context — Market Mood & Divergence vs Majors
7.1 Breadth & Mood
Portfolio Mode	Market Behavior	PM Response
Dip / Double Dip	majors red, breadth <40%	Deploy capital (risk-on)
Oh-Shit	capitulation, vol spike	Hold or add only on pulse
Recover	majors stabilizing	Harvest partials, prep rotation adds
Good / Euphoria	majors strong, breadth >70%	Harvest aggressively, reduce adds
7.2 Divergence vs Majors

Compute β of each token vs SOL/ETH/BNB.
Residual strength:

𝑟
~
=
𝑟
𝑡
𝑜
𝑘
𝑒
𝑛
−
𝛽
×
𝑟
𝑚
𝑎
𝑗
𝑜
𝑟
𝑠
r
~
=r
token
	​

−β×r
majors
	​


Divergence score:

𝐷
=
𝐸
𝑀
𝐴
1
ℎ
(
𝑟
~
)
𝑠
𝑡
𝑑
𝑒
𝑣
1
ℎ
(
𝑟
~
)
D=
stdev
1h
	​

(
r
~
)
EMA
1h
	​

(
r
~
)
	​


D ≥ +1 (leading on down days) → early harvest next rally; re-add post-dip.

D ≤ −1 (lagging on up days) → candidate for rotation buy later.

8. State Engine — Adaptive Behavior Flow

Each coin maintains a state probability vector:

{
 "trender": 0.4,
 "hype_dip": 0.3,
 "fakeout": 0.1,
 "dead": 0.1,
 "rotation": 0.1
}


Learning updates this every few minutes.
PM blends actions based on this mix, avoiding binary flips.

8.1 Transitions Drive Decisions

Early Hype → Dip → Trender: patience then scaling.

Trender → Fakeout → Dead: staged trimming.

Dead → Sleeper → Pump: seed again small.

8.2 State + Speed = Behavior
State	Speed	PM Bias
Trender	High	Harvest / reload
HypeDip	Low	Patient add
Dead	Any	Cut / halve
Rotation	Medium	Prep early entries
9. PM Levers (exposed to Learning System)
Lever	Range	What it Controls	Typical Influence
Aggressiveness Mode	patient → aggressive	Entry % and scaling	set by market volatility
Cut Pressure	0–1	Urgency to trim	portfolio drawdown velocity
Harvest Bias	0–1	Profit-taking frequency	equity curve slope
Time Patience	24–168h	Review intervals	trend persistence
Conviction Multiplier	0.5–1.5	Tolerance for dips	narrative heat
Divergence Sensitivity	0–1	Weight of residuals vs majors	rotation detection
Capital Deployment Rate	0–1	New position frequency	breadth + risk regime

Learning tunes these continuously.

10. Implementation Notes
10.1 Signal Storage

Table: technical_signals_1m

Column	Type	Description
timestamp	datetime	bar close
open/high/low/close/vol	float	raw data
rsi	float	computed RSI(14)
price_slope, rsi_slope	float	slopes over W bars
div_persist_bars	int	persistence counter
pivot_hi/lo, trend_hi/lo	float	diagonals
atr	float	volatility measure
vol_osc, climax_flag	float/bool	volume state
D	float	divergence vs majors
speed_class	enum	flash / impulse / trend / parabolic
10.2 Decision Strand Schema
{
  "action": "add_now|limit_retest|trim|trail|hold",
  "size_pct": 0.2,
  "reasons": ["bull_divergence","diag_break","VO>1.5"],
  "context": {
    "state_probs": {...},
    "portfolio_mode": "dip|good|euphoria",
    "locks": {"reentry": true}
  },
  "timestamp": "...",
  "forward_pnl_24h": null
}

11. Pseudo Execution Loop (Readable Spec)
for token in watchlist:
    sig = compute_signals(token)

    # Setup-Trigger-Confirm
    bull_div = sig.price_slope < 0 and sig.rsi_slope > 0 and sig.persist >= 6
    bull_break = sig.close > sig.trend_hi + 0.3*sig.atr
    vol_conf = sig.vol_osc >= 1.5
    D = sig.D

    if bull_div and bull_break:
        plan = ladder_adds(sig, D, vol_conf)
        emit_decision(token, plan, reason="bull_div+break")

    elif sig.bear_div and sig.bear_break:
        emit_decision(token, trim_plan(sig), reason="bear_div+break")

    # Check checkpoints
    if sig.age_h > 72:
        if sig.pnl < -0.2 and sig.vol_osc < 0.7:
            halve(token)
        elif sig.pnl > 0.3 and sig.speed_class == "flash":
            harvest(token)

12. Configuration Defaults
windows:
  rsi_period: 14
  slope_bars: 30
  pivot_k: 4
  atr_period: 14

thresholds:
  min_div_persist: 6
  vol_spike: 1.8
  climax_k: 3.0
  atr_buffer: 0.3

timing:
  do_not_touch_h: 8
  review_h: [36,72,168]
  reentry_lock_h: 36
  reentry_discount: 0.30

portfolio:
  soft_band: [28,34]
  hard_limit: 40
  spread_max_bps: 60

13. Summary — Why This Works

Volume reveals conviction.

RSI–Price divergence reveals hidden energy.

Diagonal breaks reveal timing.

Speed & time windows define when to harvest vs reload.

State probabilities keep behavior fluid.

Levers make it learnable.

Result:
A position manager that doesn’t predict price — it listens to rhythm,
and continuously learns where conviction, timing, and flow align.