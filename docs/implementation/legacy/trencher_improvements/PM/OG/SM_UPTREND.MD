Global Definitions & Constants (applies to S0–S5)

Signal timeframe: 1 h (primary). Optional: 15 m micro-confirm; 4 h macro filter (read-only, never overrides 1 h facts).

Core functions/metrics

- ATR: Wilder, period = 14 (1 h).
- ATR_norm: ATR(14) / EMA(price, 50). Slopes computed over ΔN bars (default N = 10).
- VO_z (volume z-score):
  - v = log(1 + raw_volume);
  - rolling EWMA mean/var with N = 64 bars (α = 2/(N+1));
  - winsorize v at rolling 2nd/98th percentiles before z;
  - VO_z = (v − μ_EWMA) / σ_EWMA, clipped to [-4, +6].
- sigmoid(x, k): 1/(1 + exp(-x/k)) with scale k specified per usage.
- EMA slope: linear regression slope of EMA series over N bars, reported per-bar; normalize by price via (slope / EMA) when used in % terms.

Anchors & geometry

- AVWAP_flip: anchored at the S1 breakout bar close (first bar that breaks the descending diagonal and closes above EMA20 & EMA50 under S1 guardrails). Fakeout reset: if within 24 bars of S1 price fully closes back below both EMAs and the broken diagonal, invalidate cycle and re-arm S1; re-anchor AVWAP on the next valid S1.
- Ascending/descending diagonals: derived from recent zigzag pivots (see ZigZag Parameters). For diagnostics and rails, use linear regression through the last 2–3 relevant pivot pairs.

ZigZag Parameters (used for HH/HL, S/R flips, continuation_quality)

- Amplitude threshold λ = 1.2 × ATR_1h at pivot start (ATR-adaptive).
- Backstep b = 3 bars (pivot must stand for 3 bars without being exceeded).
- Minimum leg duration = 4 bars.
- K legs for stats: last 3 up legs and 3 down legs.
- Wick relaxer: compute leg amplitude from closes, but accept pivot if intrabar extreme exceeds λ×ATR by ≥ 0.25 ATR.
- Illiquid guard: if ATR/price < 0.003 and average spread > 0.3×ATR, bump λ by +0.2.

Global thresholds & hysteresis (centralized)

- can_still_enter: on ≥ 0.70 for 3 bars; off < 0.60 for 3 bars.
- trend_healthy: on ≥ 0.70 for 3 bars; off < 0.60 for 3 bars.
- euphoria_curve: S3→S4 when ≥ 0.70 for 3 consecutive bars; leave S4 when < 0.55 for 3 bars.

**Implementation**: Hysteresis state is tracked in `uptrend_engine_meta.hysteresis` with on_count/off_count counters for each flag to prevent rapid flipping.
- Emergency bounce window T = 6 bars; halo = max(0.5×ATR_1h, 3% of price).
- ADX floors: use 18 as a soft floor for momentum/euphoria logic unless otherwise stated.

Unified State Payload Schema (for all states)

```json
{
  "state": "Sx",
  "timeframe": "1h",
  "t0": "ISO8601",
  "flag": {"...": true},
  "scores": {"...": 0.0},
  "levels": {"...": 0.0},
  "diagnostics": {"...": 0.0},
  "meta": {
    "asset": "TICKER",
    "atr_period": 14,
    "vo_z_window": 64,
    "sigmoid_scale": {"rsi": 0.5, "adx": 0.3}
  }
}
```

Events & logging hooks

- Events: s1_breakout, s2_support_touch, s3_sr_reclaim, s4_euphoria_on/off, s5_reentry_on/off, emergency_exit_on/off (emit asset, ts, levels, key scores).
- Backtests: on every state transition, log pre_scores → post_scores and reason_codes (bitset of gates that flipped).

=================

🜂 S0 — Downtrend / Coil Formation (Descriptive State)
Narrative

The market is still technically in a downtrend, but the violence of that move is fading.
Momentum has spent itself; volatility is contracting.
Price action starts showing early signs of exhaustion — not strength yet, but the end of weakness.
Energy is quietly building inside structure that still points down.

Hard Guardrails

The broader structure remains bearish (descending diagonal intact, price below 1h EMA50).

No uptrend confirmation exists.

This state never implies an entry — it’s informational only.

We assume continuation of the downtrend until clear expansion suggests otherwise.

Evidence Dimensions

(What the sensors tell us when this state is true)

Domain	Directional Signs	Description
Structure (Diagonals / Levels)	Lower highs still intact, but the angle of descent is flattening.	The diagonal itself begins to lose slope; each new low has less momentum.
Flow (EMAs)	EMA20 < EMA50; the distance between them is shrinking.	Downtrend still active, but compression between moving averages implies fading strength.
Volatility (ATR_norm)	Volatility contracting (ATR_norm slope negative).	Energy is being stored; market activity tightening.
Momentum (RSI)	RSI forming higher lows from deeply oversold zone (<30 → rising).	The structure of RSI improves — it’s turning upward, not its absolute value that matters.
Volume / VO_z	Background activity is muted, but isolated bursts (high VO_z events) wil occur on failed breaks of structure (above or below trend and/or support). These events mark final liquidity flushes and add evidence of exhaustion if followed by quick reversals.
Trend Strength (ADX)	ADX falling toward low levels.	Trend losing power; no new directional energy.

Each of these are observable facts, not thresholds.
The state machine simply reports how many of these conditions are simultaneously true.

Scoring Hook (Continuous)

For each domain, we compute a 0–1 “fit” to the S0 archetype:

1 means “textbook S0 behaviour” (clear compression, declining ADX, RSI stabilising).

0 means “opposite of S0” (expanding volatility, strong ADX rise, EMAs widening).

Composite S0 confidence = weighted mean of all sensor fits.
This is the fact layer — the raw description.

Aggressiveness Lens (Interpretive Only)

Aggressiveness does not change the facts; it changes how the system labels confidence for higher-level components:

At low aggressiveness (0.0–0.3), S0 is viewed as “dead market — ignore.”

At high aggressiveness (0.7–1.0), S0 may be seen as “potential coil forming — pay attention soon.”
The underlying measurements stay identical.

Summary Sentence

S0 describes a market still in downtrend but with declining volatility, weakening trend strength, and first signs of momentum stabilisation. It signals the dissipation of energy, not yet its reversal.

=================


================

S0 Minimal Payload (diagnostic, unified schema)

```json
{
  "state": "S0",
  "timeframe": "1h",
  "t0": "ISO8601",
  "flag": {},
  "scores": {
    "s0_confidence": 0.58,
    "atr_norm_slope": -0.12,
    "ema_alignment": 0.20,
    "adx_level": 0.18
  },
  "levels": {
    "ema20": 1.205,
    "ema50": 1.230
  },
  "diagnostics": {
    "rsi_regime": "sub-40",
    "vo_z_cluster": false
  },
  "meta": { "atr_period": 14, "vo_z_window": 64 }
}
```

🜁 S1 — Breakout & Reversal Confirmation (Descriptive State)
Narrative

After a prolonged downtrend and compression, the market finally shifts polarity.
Price and flow both reverse direction: diagonals break, EMAs flip, volatility expands.
This stage measures the strength and integrity of that reversal — not its longevity.
It tells us whether this was a true structural reversal or just a sharp reflex.

Hard Guardrails

Structural downtrend must be broken — descending diagonal decisively pierced.

EMA flip visible: price closes above both EMA20 and EMA50, with short EMA curling upward.

Volatility expansion (ATR rising) confirms energy release.

This state is purely diagnostic: it reports that a breakout occurred and evaluates its quality.

No directional bias assumed beyond describing the event.

Evidence Dimensions
Domain	Directional Signs	Description
Structure (Diagonals / Levels)	Descending diagonal broken from below; price now trades above prior trendline.	Confirms that the structural downtrend is over. This break defines the origin zone of the reversal (usually near the EMAs).
Flow (EMAs)	EMA20 crosses upward toward/above EMA50.	Flow reversal verified; moving average structure now supports bullish rotation.
Volatility (ATR / Range)	True range expands sharply (multiple ATRs within short duration).	The energy release from the coil — breakout speed and amplitude measured in ATR units.
Volume (VO_z)	Volume expands meaningfully during the breakout phase, typically within a window rather than a single spike.
Cluster rule: within 30 bars, either count(VO_z ≥ +2) ≥ 3 OR Σ max(0, VO_z) ≥ 6.
This confirms that participation surged at the moment of structural reversal, regardless of whether enthusiasm persisted.
Momentum (RSI)	RSI surges upward through 30–40 zone, breaking prior swing highs.	Momentum confirms price reversal; strength of the push measured by RSI acceleration.
Time / Price Dynamics	The breakout’s character can manifest in two distinct but equally valid forms:

Violent stab: A rapid, high-amplitude thrust — often news- or hype-driven — that retraces more deeply but still marks genuine reversal energy.

Measured march: A steadier, disciplined advance with minimal wicks and consistent progress; slower but usually more structurally durable.
Both patterns express expansion of volatility and price range; they simply differ in tempo and emotional tone.
The system records each as legitimate S1 behaviour, tagging their profiles for later comparison.
Strength (ADX)	ADX begins turning up from suppressed levels.	First evidence of trend power re-emerging.
Scoring Hook (Continuous)

Each dimension contributes to a Breakout Strength Score:

0 → breakout failed or absent.

1 → textbook diagonal + EMA flip with strong expansion.

Components of the score:

Structural integrity: clean diagonal/EMA reversal.

Expansion quality: ATR % increase vs baseline.

Volume validation: VO_z burst magnitude.

Momentum drive: RSI acceleration.

This score is used later to classify how “decisive” the breakout was.

Aggressiveness Lens (Interpretive Only)

Aggressiveness doesn’t change the facts — only how quickly the system recognises them:

Low aggressiveness: require clear EMA flip + full candle close above diagonal + volume confirmation.

High aggressiveness: label breakout once EMAs curl and volatility expands, even if close not fully confirmed.
At all points, the state itself remains purely descriptive.

Summary Sentence

S1 describes a confirmed breakout: the downtrend structure and EMA alignment reverse, volatility expands, and price accelerates sharply. The system measures where the breakout began and how strong it was in ATR and indicator terms.

=========

=========

S1 Minimal Payload (diagnostic, unified schema)

```json
{
  "state": "S1",
  "timeframe": "1h",
  "t0": "ISO8601",
  "flag": { "breakout_confirmed": true },
  "scores": {
    "breakout_strength": 0.62,
    "structural_integrity": 0.68,
    "expansion_quality": 0.71,
    "volume_cluster": 0.78,
    "momentum_drive": 0.65
  },
  "levels": {
    "breakout_price": 1.245,
    "ema20": 1.240,
    "ema50": 1.232,
    "avwap_flip_anchor": 1.238
  },
  "diagnostics": {
    "diag_break": "bull",
    "vo_z_cluster_true": true
  },
  "meta": { "atr_period": 14, "vo_z_window": 64 }
}
```

🜂 S2 — Trend Confirmed (Structural Holding & Continuation Potential)
Narrative

The market proves its breakout was real.
Price pulls back, tests the new supports, and holds.
Structure, flow, and volatility synchronise — the chaos of S1 becomes rhythm.
This is the first sustainable form of the uptrend.

Human Psychology

Relief sellers exit; strong-hand buyers replace them at better cost bases.
Former bag-holders use early strength to escape; smart participants accumulate.
Volatility cools as trust builds.
In lowcaps, with no shorts, supply turns over from weak to strong holders — a slow transfusion that steadies the trend.

Hard Guardrails

At least one major support (AVWAP / EMA50 / flipped diagonal) holds on 1 h closes.

No 1 h close back into the breakout base.

EMA20 > EMA50, both with positive slopes.

Down-diagonal remains broken.

This state is descriptive only — it reports that the uptrend is structurally sound.

Evidence Dimensions
Domain	Observation	Interpretation
Structure	1 h closes above ≥1 anchor (AVWAP, EMA50, flipped diagonal). Wicks below are fine; closes matter.	Foundation holding; structural faith intact.
Flow (EMAs)	EMA20 > EMA50 with positive slopes and widening separation.	Confirmed flow alignment.
Volatility (ATR)	ATR_norm stable → slightly positive.	Energy organized, trend sustainable.
Volume (VO_z)	Volume moderates yet remains above pre-breakout baseline.	Conviction replacing frenzy.
Momentum (RSI)	RSI rising sequence of higher lows; trend of RSI positive.	Sustained directional drive.
Strength (ADX)	ADX trending upward or convex.	Internal coherence.
Behaviour	Deep pullbacks acceptable if structural anchors respected; wicks below supports imply absorption.	Normal digestion after breakout.
Flag System & Continuous Scores

**Trigger**: S2 emits when price touches halo of one of the three supports (EMA50/AVWAP/diagonal) AND gets a close ≥ that support. Emits continuously as conditions change.

When S2 conditions hold, emit the state object:

{
  "flag": {
    "uptrend_holding": true,
    "uptrend_confirmed": false,
    "uptrend_failed": false
  },
  "supports": {
    "current_support": "AVWAP",
    "order": ["AVWAP", "EMA50", "diagonal"],
    "halo": "max(0.5*ATR_1h, 3% of price)",
    "t0": "2025-10-27T12:00Z"
  },
  "scores": {
    "trend_integrity": 0.73,
    "trend_strength": 0.71,
    "breakout_quality": 0.65
  },
  "diagnostics": {
    "support_persistence": 0.74,
    "reaction_bounce_atr": 0.9,
    "closes_above_since_t0": 7,
    "absorption_wicks_since_t0": 3,
    "ema_alignment": 0.68,
    "volatility_coherence": 0.81,
    "rsi_trend": 0.70,
    "adx_trend": 0.66
  }
}

Computation Logic

**Support Persistence (0–1)** — single composite score combining all support-related factors:

```
support_persistence = 0.25 * touch_confirm
                   + 0.20 * reaction_quality
                   + 0.40 * close_persistence
                   + 0.15 * absorption_wicks
```

Components:

1. **touch_confirm (0–1)**:
   - 1 if `low <= support_level + halo` at t0 AND a `close >= support_level` occurred (same bar or later)
   - 0 otherwise

2. **reaction_quality (0–1)**:
   - `bounce_atr = (max_high_since_t0 - support_level) / ATR_1h`
   - `reaction_quality = min(1, bounce_atr / 1.0)`
   - Captures peak bounce since t0; saturates at 1 ATR

3. **close_persistence (0–1)**:
   - Count of 1h closes ≥ support_level since t0
   - `close_persistence = 1 - exp(-closes_above / 6)`
   - Main driver of persistence; soft saturation

4. **absorption_wicks (0–1)**:
   - Count candles where `low < support_level` but `close >= support_level` since t0
   - `absorption_wicks = 1 - exp(-wick_count / 2)`
   - Shows demand absorption; 2–3 good wicks → near 1.0

**Trend Integrity (0–1)**:

```
trend_integrity = 0.65 * support_persistence
                + 0.25 * ema_alignment
                + 0.10 * volatility_coherence
```

- **support_persistence**: primary signal (defined above)
- **ema_alignment (0–1)**: Composite of three factors (simple & effective):
  - 0.33 if EMA20 > EMA50
  - 0.33 if both EMA20 and EMA50 slopes > 0 (rise rate over recent bars)
  - 0.33 × sigmoid(separation) where separation = (EMA20 - EMA50) / EMA50 × 100
- **volatility_coherence (0–1)**: Volatility reduction since breakout (reduction = better):
  - `atr_at_breakout` = ATR value at S1 breakout bar
  - `atr_now` = current ATR
  - `reduction_ratio = (atr_now - atr_at_breakout) / atr_at_breakout`
  - `volatility_coherence = sigmoid(-reduction_ratio / threshold)` (negative reduction ratio = ATR went down = good)
  - Null-guard: if `atr_at_breakout` ≈ 0, set `volatility_coherence = 0.5`.

**Trend Strength (0–1)**:

```
trend_strength = (rsi_trend + adx_trend) / 2
```

- **rsi_trend (0–1)**: Momentum since t0 — don't overcomplicate:
  - `rsi_slope` = linear regression slope of RSI since t0
  - `rsi_trend = 0.5 + sigmoid(rsi_slope / scale)` (0.5 = neutral, >0.5 = rising = good)
  - Tuning parameter: `scale` (start with ~0.5, adjust in backtests)
  - Looking for: Is RSI showing upward momentum or making higher highs since t0?
- **adx_trend (0–1)**: Strength since t0 — don't overcomplicate:
  - `adx_slope` = linear regression slope of ADX since t0  
  - `adx_trend = 0.5 + sigmoid(adx_slope / scale)` (0.5 = neutral, >0.5 = rising = good)
  - Tuning parameter: `scale` (start with ~0.3, adjust in backtests)
  - Looking for: Is ADX trending up or showing upward momentum since the retest?

Note: Removed price_slope — upward movement post-retest can be weakness (bear flag pattern). RSI + ADX capture momentum without rewarding weak drift.

**Support Tier Boost** (depth = more safety = higher confidence):

When computing final scores for PM, apply tier-based boosts based on current_support:

- **AVWAP (top tier)**: 0% boost → integrity and strength unchanged
- **EMA50 (mid tier)**: +15% boost → integrity × 1.15, strength × 1.15 (capped at 1.0)
- **diagonal (bottom tier)**: +30% boost → integrity × 1.30, strength × 1.30 (capped at 1.0)

**Rationale**: Being at a lower, stronger support tier provides more downside safety, making the uptrend more robust → scores deserve a confidence boost. Closer to the base = more reliable hold.

**Tuning Parameters** (adjust in backtests before live deployment):

- **support_persistence weights**: touch_confirm (0.25), reaction_quality (0.20), close_persistence (0.40), absorption_wicks (0.15)
- **volatility_coherence**: `threshold` in sigmoid (start ~0.3, adjust based on ATR behavior)
- **rsi_trend**: `scale` parameter (start ~0.5)
- **adx_trend**: `scale` parameter (start ~0.3)
- **trend_integrity weights**: support_persistence (0.65), ema_alignment (0.25), volatility_coherence (0.10)
- **ema_alignment**: separation sigmoid scale factor (start ~10–50)
- **close_persistence**: k value in exp decay (start 6, meaning ~6 closes → ~0.63 score)
- **absorption_wicks**: m value in exp decay (start 2, meaning ~2 wicks → near 1.0)
- **uptrend_confirmed**: monotonic window for trend_strength (start with 4–6 bars)
- **tier boost percentages**: AVWAP (0%), EMA50 (15%), diagonal (30%) — may need adjustment

Support Stepping & Flag Behaviour

**t0 Definition**: timestamp of first touch of current_support's halo when S2 started. **t0 never changes** after initial set (until all supports fail and S2 ends). Continuous measurement from original t0 through all step-downs and reclaims.

**Supports**: EMA50 (1h), AVWAP(flip), flipped ascending diagonal. Base is NOT a support.

**Stepping Order**: AVWAP → EMA50 → diagonal → FAIL

**Flag Transitions**:

- **uptrend_holding = true**: price touched halo at t0 AND got close ≥ current_support

- **Step down**: on any close < current_support → move to next lower anchor. **t0 unchanged** (continues measuring from original touch). Scores adjust:
  - `trend_integrity *= 0.4` (weakness shows; scores dented but not zeroed)
  - `trend_strength *= 0.6` (momentum lost but not wiped)
  - Scores can rebuild quickly at lower tier because tier boost applies (EMA50: +15%, diagonal: +30%)

Order of operations (score updates): on step-down or reclaim → (1) apply dent/boost factors to prior scores, (2) recompute component terms with current data, (3) apply tier boost based on current_support, (4) clamp to [0, 1].

**Reclaim Behavior**: if close ≥ higher anchor → set as current_support. **t0 unchanged** (continues measuring from original touch). Reclaiming higher supports is highly bullish:
  - `trend_integrity *= 1.3` (reclaim is MORE bullish than never breaking)
  - `trend_strength *= 1.6` (shows returning strength)
  - Reclaim shows buyers are stronger; this is MORE bullish than a clean hold

- **uptrend_failed = true**: all three supports break on 1h closes

- **uptrend_confirmed = true**: when ALL of:
  - support_persistence ≥ 0.6
  - reaction_quality ≥ 0.3 (bounced at least 0.3 ATR)
  - trend_strength rising (monotonic over last ~4–6 bars)
  - minor S/R reclaims: S/R levels reclaimed (closed above) since t0 have cumulative score ≥ 30
    - All S/R levels have scores in database; sum the scores of reclaimed levels
  - Signals handoff toward S3 (informational, not entry signal)

**Implementation**: 
- Monotonic check: `check_monotonic_trend_strength()` verifies trend_strength series is non-decreasing over last 5 bars
- S/R reclaim score: `compute_sr_reclaim_score()` queries `lowcap_sr_levels` table for reclaimed levels since t0 and sums their scores
- Both values exposed in scores payload for diagnostics

Entry Execution & Aggressiveness Interface (for PM use)

**This is the primary entry phase.** Entries occur on retests of supports (AVWAP/EMA50/diagonal) when structural integrity and strength meet aggressiveness thresholds.

For aggressiveness A ∈ [0, 1], the required thresholds form a **continuous curve** (not discrete bands):

```
τ_integrity(A) = 0.90 - (0.40 × A)
τ_strength(A) = 0.75 - (0.35 × A)
```

This curve maps:
- A = 0.1 (Patient) → integrity ≥ 0.86, strength ≥ 0.72
- A = 0.5 (Normal) → integrity ≥ 0.70, strength ≥ 0.58
- A = 1.0 (Aggressive) → integrity ≥ 0.50, strength ≥ 0.40

**Behavior mapping** (approximate, shown for reference):

| A-range | Bias | Expected support tier | Integrity τ | Strength τ |
|---------|------|---------------------|------------|------------|
| 0.0–0.3 | Patient | Bottom (diagonal) | ≥ 0.8 | ≥ 0.7 |
| 0.3–0.6 | Normal | Mid (EMA50) | ≥ 0.7 | ≥ 0.6 |
| 0.6–1.0 | Aggressive | Top (AVWAP) | ≥ 0.6 | ≥ 0.4 |

The PM executes **entries** when:
```
trend_integrity ≥ τ_int(A) AND trend_strength ≥ τ_str(A) AND current_support_tier ≤ allowed_tier(A)
```

Where `allowed_tier` maps: A < 0.3 → diagonal only, A < 0.6 → EMA50+, A ≥ 0.6 → AVWAP+.

Summary

S2 is the phase of structural confirmation — support holds, flow aligns, and volatility stabilises.
The system reports uptrend holding status and continuously scores integrity and strength, providing the PM with a real-time confidence curve for entries and risk management.


===========


==========

🜃 S3 — Continuation & Final Entry Phase
Narrative

The uptrend is alive and marching. Structure and flow are intact; price advances by reclaiming horizontal S/R levels and respecting its ascending diagonal and EMAs. S3 exists to answer two questions for the PM:
1. "Can we still enter on S/R flips?"
2. "Is euphoria building (extension away from rails + ATR surge)?"

We monitor both: entry viability (via continuation_quality) and euphoria buildup (via euphoria_curve). When euphoria_curve ≥ 0.70 for 3 consecutive bars, we move to S4 — not because of weakness, but because the trend is **extending beyond sustainable rails** into euphoric blow-off territory. Emergency exits remain independent and can trigger at any time if structure breaks.

Human Psychology

Confidence → conviction. Dips are bought quickly; each successful reclaim attracts late participants. Early buyers trim into strength; crowd chases S/R breaks. Greed rises, but the trend still behaves—until it doesn’t.

Hard Guardrails

Price above EMA50 (1h) and within/above the active ascending diagonal (direction guide, not a stop).

EMA alignment positive (EMA20 > EMA50; EMA50 rising).

Entries in S3 occur only on horizontal S/R flips (break → hold on closes → buy retest). Ideally look for these towards the lower end of the range, S/R breaks (diagonal, EMA50, AVWAP).

This state is descriptive: it reports entry viability and trend health; it does not force trades.

Evidence Dimensions (descriptive, not gates)
Domain	Observation	What it tells us
Structure	Price holds above EMA50; ascending diagonal intact; HH/HL rhythm	Trend body intact
S/R Reclaims	Recent levels broken & held on closes; clean retests	Fresh demand, valid continuation entries
Momentum	RSI making higher lows after pullbacks; ADX pulsing up from resets	Energy renewal (not exhaustion)
Volatility	ATR expands on pushes, contracts on pullbacks (organized)	Healthy “breathing”
Geometry (context)	Near upper channel → caution; hits prior diagonals from above → caution	Proximity to resistance / possible exhaustion
Flags (what the PM needs at a glance)

- **can_still_enter**: true/false
  - True means S/R flip entries are still valid (continuation_quality above threshold)
  - Used for entry decisions, NOT for S3→S4 transition

- **trend_healthy**: true/false
  - Structural health snapshot (integrity above threshold)
  - Must be true to stay in S3; if false, emergency exit considerations apply

- **euphoria_building**: true/false
  - Indicates euphoria_curve ≥ 0.70 for 3 consecutive bars
  - When true → signals transition to S4 (extension/overextension, not weakness)
  - This is what moves us from entry management to exit management

- **emergency_exit.active**: true/false (independent failsafe; see below)

Emergency Exit (independent of S3/S4)

Trigger (exact): set emergency_exit.active = true when a 1h close is below both:

EMA50 (1h) and

the lower ascending diagonal (active trend boundary).

Bounce-exit protocol (programmatic):

Snapshot on trigger: break_time, break_low, ema50_at_break, diagonal_at_break.

Define bounce zone = band between those two levels with halo:
halo = max(0.5 * ATR_1h, 3% * price).

First-bounce window: next T = 6 1h bars (E-adaptive below).
If price rallies ≥ 0.5 ATR from the post-break low and touches the bounce zone, exit there (prefer diagonal underside if both overlap).

Fail-safes:

New low before zone touch (low < break_low − 0.5 ATR) → exit immediately.

Time expiry (no zone touch within T bars) → exit on first local bounce peak.

Reclaim cancel: if price closes back above both EMA50 and diagonal before a fail-safe, set emergency_exit.active = false.

Exit action and E-integration (full liquidation):

- Emergency exit always liquidates 100% of the position. E controls immediacy and strictness:
  - Immediate exit (high E): if E ≥ 0.8, skip bounce protocol; exit 100% immediately on the close below both EMA50 and diagonal.
  - Tightened bounce (mid E): if 0.5 ≤ E < 0.8, apply bounce protocol with tighter parameters:
    - T(E) = round(6 − 3×E), clamped to [3, 6]
    - halo(E) = max(0.5×ATR_1h, 3% of price) × (1 − 0.4×E), with floor at 0.3×ATR_1h
    - giveback_before_touch(E) = (0.5 − 0.2×E)×ATR_1h, clamped to [0.3×ATR_1h, 0.5×ATR_1h]
    - reclaim cancel (high E ≥ 0.7): require reclaim of both levels plus VO_z ≥ +2 to cancel emergency state
  - Standard bounce (low E): if E < 0.5, use default parameters (T = 6, halo as defined, 0.5×ATR giveback).

Edge cases:

- Wide spread: if (EMA50 − diagonal) > 1.5×ATR at break, allow reclaim of either level (EMA50 or diagonal) with a concurrent VO_z burst (≥ +2) to cancel the emergency_exit.
- News windows (optional calendar hook): during known high-impact events, set T = 3 bars instead of 6.

PM Payload (S3)

(Minimal fields the PM consumes; diagnostics are for logs/analysis.)

{
  "flag": {
    "can_still_enter": true,
    "trend_healthy": true,
    "euphoria_building": false,
    "emergency_exit": { "active": false }
  },
  "levels": {
    "ema20": 1.2450,
    "ema50": 1.2325,
    "ascending_diagonal": 1.2280,
    "next_resistance": 1.2780,
    "highest_close": 1.2780
  },
  "reclaims": [
    {"level": 1.2420, "held_closes": 2, "reclaim_score": 0.78, "time": "…"},
    {"level": 1.2550, "held_closes": 2, "reclaim_score": 0.71, "time": "…"}
  ],
  "scores": {
    "continuation_quality": 0.74,
    "trend_integrity": 0.68,
    "trend_strength": 0.72,
    "euphoria_curve": 0.55
  },
  "diagnostics": {
    "channel_position": "mid",
    "hh_hl_sequence": "intact",
    "rsi_state": "rising",
    "adx_state": "rising",
    "atr_state": "organized"
  }
}


continuation_quality → "Can we still enter on S/R flips?"

trend_integrity → "Is the trend's body intact?"

trend_strength → momentum context (RSI/ADX blend).

euphoria_curve → "Is price extending away from rails with ATR surge?" When ≥ 0.70 for 3 consecutive bars, triggers S3→S4 transition (blow-off territory, not weakness). We move to S4 to manage exits when euphoria reaches dangerous levels.

Transition Rules (clean + non-flippy)

Stay in S3 while:
- trend_healthy = true (structure intact), AND
- euphoria_building = false (not yet in euphoric blow-off)

Move to S4 when:
- euphoria_curve ≥ 0.70 for 3 consecutive bars (extension/overextension detected)

Note: can_still_enter is for entry decisions only, not for state transitions. We can enter while euphoria builds (late but valid if risk/reward acceptable).

Scores & Hysteresis

**Trend Integrity (0–1)** — Same structure as S2, with S3-specific volatility term:

```
trend_integrity = 0.65 * support_persistence
                + 0.25 * ema_alignment
                + 0.10 * volatility_progress
```

- **support_persistence**: From S2 (unchanged)
- **ema_alignment**: From S2 (unchanged)
- **volatility_progress (0–1)**: S3-specific — measures "healthy breathing":
  - For last M bars (e.g., 20), compute fraction where: `(return > 0 AND ΔATR > 0) OR (return < 0 AND ΔATR < 0)`
  - `volatility_progress = p_breathe` (fraction of bars where ATR expands on advances, contracts on pullbacks)
  - High = healthy trend breathing; Low = drift or disorder

**Trend Strength (0–1)** — Momentum temperature (aligned with S2):

```
trend_strength = 0.6 * rsi_state + 0.4 * adx_state
```

- **rsi_state (0–1)**: `sigmoid(RSI_slope over last ~10 bars)`; clipped if RSI regime < 40
- **adx_state (0–1)**: `sigmoid(ADX_slope over last ~10 bars)`; clipped if ADX < ~18

Entry floor: if ADX < 16, cap `trend_strength ≤ 0.55` regardless of RSI to avoid momentum mirages.

**Continuation Quality (0–1)** — Unique to S3; zero overlap with integrity/strength:

Answers: "Is the trend still thrusting cleanly forward (can we still enter on S/R flips)?"

Base components:

```
continuation_quality_base = 0.6 * power_score + 0.4 * time_score
```

**Step A — Detect recent swings (HH/HL)**:
- Identify last K up legs (HL → HH) and K down legs (HH → HL) from zigzag detector (K = 2–3)
- For each leg: `amplitude_ATR = |price_change| / ATR_at_start`, `duration_bars`
- Compute means: `up_amp`, `down_amp`, `up_time`, `down_time`

**Step B — Compute ratios**:
- **power_score**: `sigmoid((up_amp / down_amp - 1) / 0.3)` — up vs down size-adjusted
- **time_score**: `sigmoid((down_time / up_time - 1) / 0.3)` — speed of up vs down legs

**Step C — Optional bump**:
- `+0.05` if ≥1 clean S/R reclaim in last N bars (cap at 1.0)

**Euphoria Curve (0–1)** — Detects extension/overextension before S4 transition:

Detects price curving away from its rails + ATR volatility surge.

```
euphoria_curve =
  0.40 * sigmoid((ATR_now / ATR_20bar_avg) - 1)    // volatility expansion (core signal)
+ 0.20 * sigmoid((price - EMA20)/ATR - 2)          // distance from EMA20 rails
+ 0.15 * sigmoid((price - AVWAP_flip)/ATR - 3)     // AVWAP separation
+ 0.20 * sigmoid((price - upper_diagonal)/ATR - 1)  // big boost above upper diagonal
+ 0.05 * saturating_count(VO_z ≥ +2, window=12)    // volume burst
```

- **ATR expansion is the core signal (40% weight)** — if volatility doesn't surge, we're not in euphoria yet
- When ≥ 0.70 for 3 consecutive bars → S3→S4 transition (blow-off territory, not weakness)
- High euphoria = price moved away from EMAs/AVWAP/upper diagonal with ATR expansion = overextension building
Guardrails:

- Per-term clipping: cap each weighted sub-term’s contribution to ≤ its nominal weight (prevents single-feature dominance).
- ADX floor: if ADX < 18, cap `euphoria_curve` at 0.65 (prevents distance-only euphoria in dead tape).

Refinements (location, absorption, channel awareness):

- Pullback quality:

```
pullback_quality = 0.5 * sigmoid((0.8 - |(close - EMA20)/ATR|) / 0.3)
                 + 0.5 * sigmoid((fib_382_to_618 - |retrace_ratio - 0.5|) / 0.15)
```

- Retest absorption (evaluate around the reclaim retest window, default 3 bars):

```
absorption_score = 0.6 * sigmoid((wick_down/ATR - 0.3)/0.2)
                 + 0.4 * sigmoid((Σ VO_z on retest_window) / 3.0)
```

- Channel penalty near upper rail:

```
channel_penalty = sigmoid((dist_upper/ATR - 0.5) / 0.3)
```

- Final combination:

```
continuation_quality = 0.5 * continuation_quality_base
                     + 0.5 * pullback_quality
continuation_quality = max(continuation_quality, continuation_quality + 0.1 * absorption_score)
continuation_quality *= (1 - 0.25 * channel_penalty)
continuation_quality = min(1.0, max(0.0, continuation_quality))
```

- Late-stage guard: if `euphoria_curve ≥ 0.75` and channel_position = upper, require `continuation_quality ≥ 0.70` for new entries.

**Flag Hysteresis**:

- **can_still_enter**: `true` if `continuation_quality ≥ 0.60`
  - Off if < 0.60 for 3 consecutive bars
  - Back on if > 0.70 for 3 bars
  - Used for entry decisions, not state transitions

- **trend_healthy**: `true` if `trend_integrity ≥ 0.60`
  - Off if < 0.60 for 3 consecutive bars
  - Back on if > 0.70 for 3 bars
  - Must stay true to remain in S3

- **euphoria_building**: `true` if `euphoria_curve ≥ 0.70` for 3 consecutive bars
  - When true → transition to S4 (extension/overextension, not weakness)
  - Set to `false` when euphoria_curve drops back below 0.55 for 3 bars

**Aggressiveness Interface (for PM use)**

For aggressiveness A ∈ [0, 1], entry thresholds form a **continuous curve**:

```
τ_continuation(A) = 0.90 - (0.30 × A)
τ_integrity(A) = 0.85 - (0.25 × A)
```

This curve maps:
- A = 0.1 (Patient) → continuation ≥ 0.87, integrity ≥ 0.83
- A = 0.5 (Normal) → continuation ≥ 0.75, integrity ≥ 0.73
- A = 1.0 (Aggressive) → continuation ≥ 0.60, integrity ≥ 0.60

The PM executes **entries** when:
```
continuation_quality ≥ τ_continuation(A) AND trend_integrity ≥ τ_integrity(A) AND can_still_enter = true
```

**Note**: `reclaim_score` in payload comes from geometry system (all S/R levels have scores in database).
If absent, fallback proxy: `reclaim_score = sigmoid(held_closes/2 + retest_distance/ATR - 1)`.

Emergency exit can trigger in any state; it is not S4.

==========

=========
🜄 S4 — Euphoria / Overextension (Exit Management Phase)

Narrative

Price has moved far from EMA20/AVWAP rails; ATR volatility has surged. Momentum, volume, and emotion all amplify together. This is euphoria — not weakness. We stop new entries, hold profits, and prepare controlled exits.

Human Psychology

Everyone sees it now. Buyers chase gaps; early holders distribute into strength. Indicators show overbought while price continues higher. Smart participants sell into that noise, never out of fear.

Hard Guardrails

* HH/HL pattern still intact
* EMA50 and ascending diagonal unbroken → no emergency exit yet
* **euphoria_curve ≥ 0.70 for 3 consecutive 1h bars** triggers S4
* No new entries while S4 active

Transition Rules

**Enter S4**: euphoria_curve ≥ 0.70 for 3 consecutive bars (extension/overextension detected)

**Stay in S4**: while structure holds (HH/HL intact, EMA50/diagonal unbroken) and euphoria_curve > 0.55

**Exits ONLY fire when BOTH conditions align**:

1. We're at/near a top-side geometry level (upper diagonal / major S/R / measured move), **AND**
2. Exhaustion is showing (HH fail starting, volatility cooling, momentum roll)

Exit Trigger Logic

**Geometry touch** (location side of AND):
* Price tags/overshoots an upper diagonal or major resistance (scored S/R), OR
* Reaches a measured-move/extension target

**Exhaustion confirmed** (exhaustion side of AND — must observe at least two):

* **HH fail on closes** (can be local) or **lower high attempt** that stalls.
* **ADX roll**: ADX previously ≥ 40, now down ≥ 5. Ignore this signal if the peak < 28.
* **ATR cool**: ATR down ≥ 30% from its 10-bar peak.
* **Giveback**: from most recent high, drawdown ≥ 1.5× ATR.
* (Optional minor) **RSI divergence** over the last swing.

Computation Logic

**Euphoria Curve** (0–1) — same calculation as defined in S3

**Exhaustion Confirmed** — count exhaustion signals (need ≥2):

- hh_fail: last push failed to close above prior high
- adx_rolled: ADX peaked ≥40, now ≤ peak - 5
- atr_cooled: ATR dropped ≥30% from 10-bar peak
- giveback_big: (recent_high - close) ≥ 1.5× ATR
- rsi_divergence (optional minor signal)

**Exit Execution**:

**Aggressiveness Interface (for PM use)**

For exit assertiveness E ∈ [0, 1], exit thresholds form a **continuous curve**:

```
τ_exhaustion(E) = 3.0 - (1.0 × E)
```

This curve maps:
- E = 0.1 (Patient) → need ≥ 2.9 exhaustion signals (round to 3) → more confirmation
- E = 0.5 (Normal) → need ≥ 2.5 exhaustion signals (round to 3) → standard
- E = 1.0 (Aggressive) → need ≥ 2.0 exhaustion signals → earlier exits

Exit execution:
```
exhaustion_confirmed = (exhaustion_signals >= τ_exhaustion(E))
geometry_touch = touches(upper_diagonal or major_SR or extension_target)
chandelier_broken = (close < highest_close - k×ATR)

# Primary exit: geometry + exhaustion
if geometry_touch AND exhaustion_confirmed:
    sell_fraction(0.30)  # 30% of remaining

# Chandelier trailing stop (independent; E-adaptive)
# k adapts with E: k(E) = clamp(3.5 − 1.5×E, 2.0, 4.0)
if chandelier_broken:
    # Scale reduction by E bucket: Patient 15%, Normal 30%, Aggressive 60%
    if E >= 0.72:
        sell_fraction(0.60)
    elif E >= 0.58:
        sell_fraction(0.30)
    elif E >= 0.40:
        sell_fraction(0.15)
    else:
        sell_fraction(0.15)

# Second fractal event (either type)
if second event occurs later:
    sell_fraction(0.30)  # 30% of what's left (fractal ladder)

# k adjustment: 3.0 normal, 2.5 if price > 2×ATR above EMA20
```

Additional grace:

- After S4 activation, do not execute exits on the same activation bar; require at least 1 completed bar before acting on exit triggers.

**Exit Types Summary**:

1. **Planned exits** (geometry + exhaustion): Sell 30% when at geometry level AND exhaustion confirmed
2. **Chandelier trailing stop**: E-adaptive. k(E) = clamp(3.5 − 1.5×E, 2.0, 4.0). On trigger, sell 15%/30%/60% for Patient/Normal/Aggressive E buckets.
3. **Emergency exit**: 1h close below both EMA50 AND ascending diagonal → bounce-exit protocol
   - If bounce fails (new low below break_low - 0.5×ATR) → flush remaining

PM Payload (S4)

```json
{
  "flag": {
    "s4_active": true,
    "sell_on_strength": true,
    "emergency_exit": { "active": false }
  },
  "scores": {
    "euphoria_curve": 0.81,
    "exhaustion_watch": 0.66,
    "trend_integrity": 0.78,
    "trend_strength": 0.86
  },
  "exits": {
    "geometry_touch": true,
    "exhaustion_confirmed": true,
    "sell_fraction": 0.30
  },
  "levels": {
    "upper_diagonal": 1.312,
    "major_sr": 1.305,
    "ema50": 1.230,
    "avwap_flip": 1.224,
    "highest_close": 1.312
  }
}
```

Summary

S4 is the euphoria/overextension phase where we manage exits (not entries). Exits only fire when BOTH geometry_touch AND exhaustion_confirmed (≥2 exhaustion signals). We sell in 30% fractal reductions. Emergency exit remains a separate mechanical failsafe.

=========


Implementation clarifications (engine alignment)

- AVWAP flip persistence: on S1 transition, persist `avwap_flip_anchor_ts` and recompute `levels.avwap_flip` each tick from 1h VWAP since anchor.
- S2 stepping mechanics: maintain `s2_meta` with `current_support`, stable `t0_ts`, and one-shot flags `dent_pending` / `reclaim_boost_pending` to apply dents/boosts exactly once during step-down/reclaim.
- Unified supports payload: emit `supports.current_support`, `supports.order`, and `supports.halo`; expose S2 component scores under `scores` (`support_persistence`, `reaction_quality`, `close_persistence`, `absorption_wicks`).
- Euphoria diagonal nuance: apply a stronger boost when price is above the upper diagonal and a smaller boost when approaching from below.
- Emergency exit payload: record `break_time`, `break_low`, `ema50_at_break`, `diagonal_at_break`, dynamic `halo`, and `bounce_zone {low, high}`; include `suggested_action` among [monitor, exit_on_bounce_zone_touch, exit_immediately_new_low]; deactivate on reclaim of both EMA50 and diagonal.
- Hysteresis implementation: track flag states in `uptrend_engine_meta.hysteresis` with on_count/off_count counters to prevent rapid flag flipping; applies to can_still_enter, trend_healthy, and euphoria_building flags.
- Series robustness: guard EMA/ATR/RSI computations with padding and alignment to avoid gaps; these are implementation details that do not change model intent.


========

🜅 S5 — Re-Entry / Cooling Consolidation

Narrative

The blow-off has passed; price is cooling back toward structural rails. Volatility compresses, ADX relaxes, but price respects EMA50 and the lower diagonal without breaking. We already sold into strength during S4; now we look to re-enter near the trend's backbone before the next leg begins. **Same trend, smaller amplitude.**

Human Psychology

The hype is gone. Chasers from the top are nursing losses. Strong hands accumulate quietly along the same structural rails that held the trend together. This is where disciplined systems buy while sentiment is numb.

Hard Guardrails

* EMA50 and lower diagonal unbroken (no emergency exit)
* Volatility cooled from S4 peak (ATR < 80% of peak)
* HH/HL pattern still intact (trend structure holds)
* S5 active when cooldown_integrity ≥ 0.6 AND reentry_readiness ≥ 0.6 for 2 consecutive bars
* Deactivate if either drops below 0.5 for 2 consecutive bars

Transition Rules

**Enter S5**: After S4, when euphoria_curve drops below 0.55 for 2 bars AND cooldown_integrity ≥ 0.6

**Stay in S5**: cooldown_integrity ≥ 0.6 AND reentry_readiness ≥ 0.6 (structure intact, ready to re-enter)

**Exit S5**: 
- Emergency exit fires (1h close below EMA50 AND diagonal) → full reset
- Momentum restarts (RSI > 60, ADX > 25) → back to S3 for continuation

Scoring Blocks

S5 uses two independent scores (feeds same PM schema as S2–S4):

**1. cooldown_integrity (0–1)** — "Has the trend cooled and reset cleanly, without breaking?"

```
cooldown_integrity =
  0.40 * structural_hold
+ 0.35 * volatility_cool
+ 0.25 * momentum_reset
```

**structural_hold (0–1)**:
- above_ema50_ratio = fraction of last N bars (≈10) with close ≥ EMA50
- above_diagonal_ratio = same vs lower diagonal
- structural_hold = 0.6×above_ema50_ratio + 0.4×above_diagonal_ratio

**volatility_cool (0–1)**:
- ratio = ATR_now / ATR_peak_S4
- if ratio > 1.2: volatility_cool = 0.3 (still hot)
- elif 0.6 ≤ ratio ≤ 1.0: volatility_cool = 1.0 (perfect cooldown)
- else: volatility_cool = 0.5 (too quiet/apathy)

**momentum_reset (0–1)**:
- rsi_mid = 1 - |RSI_now - 50|/50
- adx_mid = sigmoid((25 - |ADX_now - 25|) / 5)
- momentum_reset = 0.6×rsi_mid + 0.4×adx_mid

**2. reentry_readiness (0–1)** — "Is the structure showing the right mix of stability + latent strength to buy again?"

```
reentry_readiness =
  0.45 * location_quality
+ 0.35 * compression_quality
+ 0.20 * early_pulse
```

**location_quality (0–1)**:
- dist = (close - EMA50) / ATR
- location_quality = sigmoid(-|dist| / 0.5) (best near EMA50)
- Bonus +0.1 if low touched within 0.25 ATR of diagonal

**compression_quality (0–1)**:
- atr_slope = slope(ATR, 10 bars)
- compression_quality = sigmoid(atr_slope / 0.2) (small positive slope → 0.6–0.8)

**early_pulse (0–1)**:
- rsi_slope = slope(RSI, 8 bars)
- adx_slope = slope(ADX, 8 bars)
- early_pulse = 0.5×sigmoid(rsi_slope/0.4) + 0.5×sigmoid(adx_slope/0.3)

**Note**: Global trend_integrity and trend_strength continue evolving in S5 (inherit from prior states).

Flag Logic

```
# S5 activation requires 2 consecutive bars above thresholds (hysteresis)
if cooldown_integrity >= 0.6 AND reentry_readiness >= 0.6:
    s5_on_count += 1
    s5_off_count = 0
    if s5_on_count >= 2:
        s5_active = True
        reentry_signal = True
elif cooldown_integrity < 0.6 OR reentry_readiness < 0.6:
    s5_off_count += 1
    s5_on_count = 0
    if s5_off_count >= 2:
        s5_active = False
        reentry_signal = False
```

**Implementation**: S5 hysteresis state tracked in `uptrend_engine_meta.hysteresis.s5_activation` with on_count/off_count counters to prevent rapid activation/deactivation.

**Aggressiveness Interface (for PM use)**

For aggressiveness A ∈ [0, 1], re-entry thresholds form a **continuous curve**:

```
τ_cooldown(A) = 0.70 - (0.10 × A)
τ_reentry(A) = 0.70 - (0.10 × A)
```

This curve maps:
- A = 0.1 (Patient) → both scores ≥ 0.69 → wait for stronger cooldown/reset
- A = 0.5 (Normal) → both scores ≥ 0.65 → standard re-entry readiness
- A = 1.0 (Aggressive) → both scores ≥ 0.60 → earlier re-entry acceptance

The PM executes **re-entries** when:
```
cooldown_integrity >= τ_cooldown(A) AND reentry_readiness >= τ_reentry(A) AND s5_active = True
```

Hysteresis: need 2 consecutive bars above thresholds to flip on; drops below 0.5 for 2 bars to flip off.

PM Payload (S5)

```json
{
  "flag": {
    "s5_active": true,
    "reentry_signal": true,
    "emergency_exit": { "active": false }
  },
  "scores": {
    "cooldown_integrity": 0.74,
    "reentry_readiness": 0.71,
    "trend_integrity": 0.70,
    "trend_strength": 0.52
  },
  "levels": {
    "ema50": 1.230,
    "lower_diagonal": 1.228,
    "halo": 0.5
  },
  "playbook": {
    "entry_rule": "enter full normal size near EMA50/diagonal halo",
    "stop_rule": "close below EMA50 & diagonal",
    "position_size": "standard (or larger if prior profit banked)"
  }
}
```

Summary

**cooldown_integrity ≥ 0.6**: Structure cooled but intact — volatility decompressed, momentum reset, but no structural break.

**reentry_readiness ≥ 0.6**: Perfect re-engagement zone — price near EMA50/diagonal, compression showing early pulse.

**Action**: Enter full-size (or slightly heavier using prior profits) near EMA50/diagonal halo.

**Invalidation**: Emergency exit (close below EMA50 AND diagonal) → full trend reset.

**Success**: Once momentum resumes (RSI > 60, ADX > 25) → return to S3 for continuation.
