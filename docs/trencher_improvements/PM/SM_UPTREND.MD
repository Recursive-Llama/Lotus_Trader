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

🜂 S0 — Coil / Late Downtrend (Watch-Only State)
Narrative

The market is still technically in a downtrend, but the violence of that move is fading.
Momentum has spent itself; volatility is contracting.
Price action starts showing early signs of exhaustion — not strength yet, but the end of weakness.
Energy is quietly building inside structure that still points down.

Market Psychology

Fear has been exhausted. Those who panicked have already sold. Late sellers find few buyers at lower prices. The crowd grows numb; volume dries up. Smart money watches quietly, sensing the turn before it's visible. This is the calm before the storm — compression building energy that will release when structure finally breaks.

**Bands (EMA Structure)**

- **Fast band**: EMA20 + EMA30
  - EMA30 is a stabiliser for fast-band slope noise; EMA20 drives curvature, EMA30 provides trend continuity
- **Mid band**: EMA60–EMA144 (replaces EMA50–EMA100 geometry)
- **Slow band**: EMA250–EMA333 (last to turn; assume down)
- **AVWAP**: Reference only (will anchor on S1 breakout bar close)

Hard Guardrails

The broader structure remains bearish (slow band down, price below mid band).

No uptrend confirmation exists.

This state never implies an entry — it's informational and watch-only.

We assume continuation of the downtrend until clear expansion suggests otherwise.

The quality of S0 compression indicators can signal whether a future S1 breakout is more likely to be genuine or fake: deeper coil and cleaner compression → more trustworthy breakout when it occurs.

What We See in S0 (Facts on Tape)

**1) Flow & Compression (Core)**

- **Fast band flattening**: EMA20 slope ≤ 0, but flattening: Δ(slope_20) > 0
  - EMA30 tracked separately for early confirmation of reversal hints

- **Mid band down & compressing**: slope_60 ≤ 0, slope_144 ≤ 0, and dsep_mid < 0
  - sep_mid = (EMA60 − EMA144)/EMA144
  - dsep_mid = Δ(sep_mid, N=5)

- **Slow band definitively down**: slope_250 < 0 and slope_333 < 0
  - (Optional quality bonus if their down-slope is slowing: Δ(slope_250)>0 or Δ(slope_333)>0)

**2) Volatility & Participation**

- **ATR_norm slope < 0** (volatility contracting)
- **VO_z quiet overall** (winsorized z ≤ 0 most bars; isolated spikes allowed)
- **ADX drifting down** and typically < 18

**3) Price Behaviour Around Bands (Elastic, Not Binary)**

- Price oscillations narrowing toward mid band:
  - Shrinking distance to mid(EMA60, EMA144) over the last K bars
  - Optional metric: rangeZ = zscore(high−low, L=50) trending down

**4) Momentum Exhaustion (Context, Not a Gate)**

- **RSI was oversold** (dipped below 30-40) and now **turning up with some strength**
- RSI forming higher lows from deeply oversold zone while price still makes marginal or equal lows
- The structure of RSI improves — it's turning upward, not its absolute value that matters
- **Useful but not critical**: This provides context for exhaustion, but don't over-rely on RSI alone. Compression and band behavior are the primary signals.

Each of these are observable facts, not thresholds.
The state machine simply reports how many of these conditions are simultaneously true.

Compression Index (Single Dial, 0–1)

Use this to summarize "how coiled" we are. Keep it descriptive; don't trade it.

```
compression_index =
  0.40 * sigmoid( -ATR_norm_slope / k_atr )
+ 0.30 * sigmoid( -dsep_fast     / k_sep )
+ 0.20 * sigmoid( -dsep_mid      / k_sep )
+ 0.10 * sigmoid( -ADX_slope     / k_adx )
```

Where:
- sep_fast = (EMA20 − EMA60)/EMA60
- dsep_fast = Δ(sep_fast, N=5)
- sep_mid = (EMA60 − EMA144)/EMA144
- dsep_mid = Δ(sep_mid, N=5)

**Start parameters**: k_atr=0.05, k_sep=0.0015, k_adx=0.2 (tune in backtests)

**Interpretation**:
- 0.8–1.0 = deep coil
- 0.6–0.8 = forming
- <0.6 = loose/bleeding

This is the fact layer — the raw description. **The deeper the compression (higher compression_index), the more potential energy stored, and the more likely the subsequent S1 breakout is to be real rather than fake.** Deeper compression signals that everything has reset and coiled — when bands are compressed and starting to move up, that's often a better buy setup.

Trader Stance (All Profiles Watch-Only)

Patient / Normal / Aggressive: all watch-only in S0.
No entries, no pre-emptive actions.
We simply monitor progression of:
- compression_index rising
- ATR_norm_slope staying < 0
- fast flattening, mid compressing, slow down

(We'll use these baselines later to judge S1 expansion quality, but S0 itself does nothing.)

Baselines to Store for S1 (Read-Only in S0)

Store these values when S0 is active (used later to evaluate S1 breakout quality):
- atr_norm_baseline
- sep_fast_start
- sep_mid_start
- adx_baseline
- compression_index (final S0 value before S1 transition)

Quality Tags (Optional Diagnostics)

- "coil_quality": "deep|moderate|weak" from compression_index bands
- "slow_band_state": "down|down_slowing" using rate-of-change:
  - rate_change_333 = (slope_333_now - slope_333_prev) / |slope_333_prev|
  - tag down_slowing when rate_change_333 ≥ +0.3 (tuning parameter)

Summary Sentence

S0 describes a market still in downtrend but with declining volatility, weakening trend strength, and first signs of momentum stabilisation. It signals the dissipation of energy, not yet its reversal. The quality of compression (measured by compression_index) provides context for evaluating future breakout reliability.

S0 Minimal Payload (diagnostic, unified schema)

```json
{
  "state": "S0",
  "timeframe": "1h",
  "t0": "ISO8601",
  "flag": { "watch_only": true },
  "scores": {
    "compression_index": 0.78,
    "atr_norm_slope": -0.06,
    "dsep_fast": -0.0009,
    "dsep_mid": -0.0013
  },
  "levels": {
    "ema20": 1.182,
    "ema30": 1.186,
    "ema60": 1.196,
    "ema144": 1.211,
    "ema250": 1.238,
    "ema333": 1.256
  },
  "diagnostics": {
    "ema20_slope": -0.0012,
    "d_ema20_slope": 0.0005,
    "ema30_slope": -0.0010,
    "ema60_slope": -0.0007,
    "ema144_slope": -0.0004,
    "ema250_slope": -0.0009,
    "ema333_slope": -0.0011,
    "adx_level": 15.6,
    "adx_slope": -0.3,
    "vo_z_quiet": true,
    "rsi_regime": "sub-40 rising",
    "coil_quality": "deep",
    "slow_band_state": "down_slowing"
  },
  "baselines": {
    "atr_norm": 0.023,
    "sep_fast_start": 0.0117,
    "sep_mid_start": 0.0124,
    "adx_baseline": 15.6,
    "compression_index": 0.78
  },
  "meta": {
    "atr_period": 14,
    "vo_z_window": 64,
    "bands": {
      "fast": "EMA20+EMA30",
      "mid": "EMA60-EMA144",
      "slow": "EMA250-EMA333"
    },
    "avwap": "reference_only_will_anchor_on_s1"
  }
}
```

=================


================

🜁 S1 — Breakout & Reversal Confirmation (Descriptive State)
Narrative

After S0 coil, the **flow bends up** and **energy releases**. We confirm a regime flip by seeing **EMA curvature up**, **band compression invert → expansion**, and **participation** (VO_z). S1 is **diagnostic**: it marks where the breakout began and measures its quality. No entries yet.

Hard Guardrails (all must pass)

1. **Volatility release:** `ATR_norm_slope > 0` (vs S0 baseline).

2. **Fast-band curvature:** `ema20_slope > 0` **and** `Δ(ema20_slope) > 0`.

3. **Compression inversion (fast-to-mid):** `dsep_fast > 0` where `sep_fast = (EMA20 − EMA60)/EMA60`, `dsep_fast = Δ(sep_fast, N=5)`.

4. **Participation:** **VO_z cluster** true (within 30 bars, `count(VO_z ≥ +2) ≥ 3` **or** `Σ max(0, VO_z) ≥ 6`).

**Note:** Price closes above EMA20/EMA30/EMA60 are **scoring boosts** (not gates). Slopes and compression inversion are the primary signals; price participation enhances breakout_strength but does not block S1 activation.

**Nice-to-have (boost, not gate):**

* Mid band **stops compressing**: `dsep_mid ≥ 0` (`EMA60–EMA144` gap flattening).
* ADX uptick from depressed levels; RSI acceleration > 0.

Scope Clarification

S1 is purely diagnostic. Aggressiveness settings are not applied here and have no influence on trading behavior. The system records S1 conditions to evaluate breakout quality and set the anchor for future S2 entries.

AVWAP (Anchor, Not a Band)

* **Anchor** `AVWAP_flip` at this S1 bar close (for later S2 retests & conviction).
* Compute `avwap_slope_10` (diagnostic): linear-regression slope of AVWAP over last 10 bars, normalized by current AVWAP as % per bar.
  - `+0.05%/bar` → healthy up conviction
  - `−0.05%..+0.05%/bar` → flat/fragile
  - `< −0.05%/bar` → conviction deterioration
* Do **not** gate S1 on AVWAP; it's reference-only here.

Two Valid Breakout "Temperatures"

* **Violent stab:** Big ATR burst, may retrace deeper; still valid.
* **Measured march:** Steady bars, smaller wicks; often more durable.
  We tag but treat both as S1 if guardrails pass.

Scoring Hook (Continuous)

**Breakout Strength (0–1)** blends flow flip, expansion, volume, and momentum:

* **flow_flip_integrity (0–1)**
  * curvature: `sigmoid(ema20_slope/k1) * sigmoid(Δema20_slope/kc)`
  * compression inversion: `sigmoid(dsep_fast/ks)`
  * price context boost: `I(close ≥ EMA60)` (0/1) — reaches mid band = stronger signal
    → `flow_flip_integrity = 0.50*curvature + 0.35*comp_inv + 0.15*price_flag`
  * **Tuning parameters**: k1, kc, ks (start with priors, tune via grid search on S1→S2 hold vs fakeout outcomes)

* **expansion_quality (0–1)**
  * ATR surge vs S0: `(ATR_norm_now − atr_norm_baseline)/atr_norm_baseline` → sigmoid(k≈0.3)
  * gap surge vs S0: `(sep_fast_now − sep_fast_start)/|sep_fast_start|` → sigmoid(k≈0.3)
    → average the two (clip to [0,1])
  * **Note**: Both terms wrapped in sigmoid with k≈0.3 to normalize magnitude differences between ATR and separation deltas before averaging.

* **volume_cluster (0–1)**
  * map VO_z cluster intensity to [0–1]: `min(1, Σ max(0, VO_z)/6 )`

* **momentum_drive (0–1)**
  * RSI acceleration (slope over 10 bars) → sigmoid
  * ADX uptick (ΔADX over 10 bars, start floor ~18) → sigmoid
    → `0.6*RSI_term + 0.4*ADX_term`

**Composite (base):**
```
breakout_strength_base = 0.30*flow_flip_integrity 
                        + 0.25*expansion_quality 
                        + 0.20*volume_cluster 
                        + 0.15*momentum_drive
                        + 0.10*sr_flip_score
```

* **sr_flip_score (0–1)**: Sum of S/R level scores that price broke above during S1 breakout, normalized:
  - Query geometry system for all S/R levels that price broke above during S1 (closed above and held)
  - Sum their scores → `sr_flip_total`
  - Normalize to [0,1]: `sr_flip_score = sigmoid(sr_flip_total / scale)` where scale is a tuning parameter (start ~50, adjust based on typical S/R score ranges)
  - Captures structural participation — breaking multiple strong levels = stronger breakout

**S0 Compression Context (exploratory boost):**
* Apply small boost based on S0 compression depth (deeper compression = more likely real breakout):
  * `breakout_strength = breakout_strength_base * (0.85 + 0.15 * s0_compression_index)`
  * This gives a +0% to +15% boost depending on compression depth (0.7 = 10.5% boost, 1.0 = 15% boost)
* **Note**: This is exploratory and tunable. Compression_index is already tracked; this uses it as context. Since breakout_strength is diagnostic (not an entry gate), this affects quality assessment without directly impacting entries.
* Tune the (0.85, 0.15) weights in backtests if needed.

**Final:**
```
breakout_strength = breakout_strength_base * (0.85 + 0.15 * s0_compression_index)
breakout_strength = min(1.0, breakout_strength)  # cap at 1.0
```

> All comparisons reference **S0 baselines** you logged (atr_norm_baseline, sep_fast_start, compression_index).

**Baseline persistence**: Baselines are frozen at the S0→S1 transition and persist until fakeout or S2 activation. They remain constant throughout S1 to enable consistent breakout quality evaluation.

Fakeout Logic (EMA + AVWAP + S/R Context)

Goal: detect when the breakout was false, and we're back in S0-like conditions.

**Trigger:** `fakeout = (count_true([structural_failure, flow_reversal, conviction_collapse]) >= 2)`

When true → invalidate cycle, re-arm S1 on next breakout (new fast-band curvature + ATR_norm expansion).

**Conditions (need ≥2 of 3):**

1️⃣ **Structural failure:**
   * Price closes below the pre-breakout S/R support level (from geometry system).
   * At S1 breakout, cache the highest S/R support level < breakout_price that price was above/respecting in the recent S0 period (e.g., last 20-30 bars) as `last_support_below_breakout`.
     - This represents the active support level immediately before breakout (not necessarily the absolute lowest from all of S0).
     - Example: if price curled up during S0 and reclaimed a higher S/R level before breakout, use that level.
   * If no such S/R level exists, fallback to the most recent local swing low from S0.
   * If price closes below this cached level, structural failure = true.
   * This invalidates the market's memory of support — shows buyers who defended S1 gave up.

2️⃣ **Flow reversal:**
   * Mid-band slopes turn back down: `ema60_slope < 0` **and** `ema144_slope < 0`
   * **Or** curvature deteriorates: `Δ(ema60_slope) < 0`
   * → signals that the body of the move has rolled over, not just surface noise.

3️⃣ **Conviction collapse:**
   * Use **either** signal to count "conviction collapse"; they catch different failure modes:
     - `avwap_slope_10 <= -0.05%/bar` (slope deterioration), **or**
     - `consecutive_closes_below_avwap >= 3` (persistent pressure)
   * Why OR (not AND): Slope↓ flags broad deterioration even if price chops around AVWAP. 3 closes below flags persistent pressure even if slope is near flat. Requiring both would miss legitimate failures; counting either makes the 2-of-3 system resilient.

**Rationale Summary:**

| Failure Mode | What It Detects | Why It Matters |
|--------------|----------------|----------------|
| S/R break | Invalidates market's memory of support | Shows buyers who defended S1 gave up |
| Mid-band roll | Invalidates field orientation | Slow EMAs turning down = genuine flow reversal |
| AVWAP decline | Invalidates conviction | Average participant now underwater |

This approach is conceptually clean, structurally grounded, and avoids false triggers.

Summary Sentence

S1 declares a breakout **without diagonals**: the **fast band bends up**, **band gaps start expanding** (fast-to-mid compression inverts), **volatility and volume expand**, and price participates (boosts scoring). We anchor AVWAP here for later S2 retests, and we score how decisive the flip was relative to the S0 coil. Fakeout detection uses S/R structure, mid-band flow, and AVWAP conviction — requiring ≥2 of 3 failure modes to invalidate.

S1 Minimal Payload (diagnostic, unified schema)

```json
{
  "state": "S1",
  "timeframe": "1h",
  "t0": "ISO8601",
  "flag": { "breakout_confirmed": true },
  "scores": {
    "breakout_strength": 0.62,
    "flow_flip_integrity": 0.68,
    "expansion_quality": 0.71,
    "volume_cluster": 0.78,
    "momentum_drive": 0.65
  },
  "levels": {
    "breakout_price": 1.245,
    "base_sr_level": 1.212,
    "flipped_sr_levels": [
      {"level": 1.238, "score": 28, "order": 1},
      {"level": 1.232, "score": 22, "order": 2},
      {"level": 1.228, "score": 18, "order": 3}
    ],
    "ema20": 1.240,
    "ema30": 1.241,
    "ema60": 1.232,
    "ema144": 1.226,
    "ema250": 1.218,
    "ema333": 1.212,
    "avwap_flip_anchor": 1.238
  },
  "diagnostics": {
    "curvature_ok": true,
    "dsep_fast": 0.0014,
    "dsep_mid": 0.0002,
    "atr_norm_baseline": 0.023,
    "sep_fast_start": 0.0117,
    "s0_compression_index": 0.78,
    "sr_flip_total": 85,
    "sr_flip_score": 0.82,
    "avwap_slope_10": 0.0006,
    "vo_z_cluster_true": true,
    "breakout_archetype": "measured",
    "price_reached_ema60": true
  },
  "meta": {
    "atr_period": 14,
    "vo_z_window": 64,
    "bands": {
      "fast": "EMA20+EMA30",
      "mid": "EMA60-EMA144",
      "slow": "EMA250-EMA333"
    }
  }
}
```

=========


=========

⟁ S2 — Trend Confirmed (Structural Holding & Continuation Potential)
Narrative

The market proves its breakout was real.
Price pulls back, tests the flipped S/R levels (now acting as supports), and holds.
Structure, flow, and volatility synchronise — the chaos of S1 becomes rhythm.
This is the first sustainable form of the uptrend.

Human Psychology

Relief sellers exit; strong-hand buyers replace them at better cost bases.
Former bag-holders use early strength to escape; smart participants accumulate.
Volatility cools as trust builds.
In lowcaps, with no shorts, supply turns over from weak to strong holders — a slow transfusion that steadies the trend.

Hard Guardrails

* **S2 Activation**: Price touches (within halo) any flipped S/R level (or base) AND gets a close ≥ that level. This marks retest and S2 entry.
* **S2 Persistence**: Once activated, S2 persists while base S/R holds (no 1h close below base S/R) AND mid/slow band slopes are non-negative (structural health maintained).
* Base S/R level = invalidation line — if price closes below base S/R, exit immediately (use bounce logic). Mid/slow band slope deterioration is a diagnostic tag (why we failed), not a gate for exit.
* Fast band (EMA20/30) ignored for structural checks (confluence only).

This state is descriptive only — it reports that the uptrend is structurally sound.

Evidence Dimensions
Domain	Observation	Interpretation
Structure	Price at/on S/R level (base or flipped), with 1h closes ≥ that level. Wicks below are fine; closes matter.	Foundation holding; structural faith intact.
Flow (EMAs)	Mid/slow bands maintaining positive slopes (structural health). Fast band (EMA20/30) provides confluence but not primary support.	Confirmed flow alignment at structural level.
Volatility (ATR)	ATR_norm stable → slightly positive.	Energy organized, trend sustainable.
Volume (VO_z)	Volume moderates yet remains above pre-breakout baseline.	Conviction replacing frenzy.
Momentum (RSI)	RSI rising sequence of higher lows; trend of RSI positive.	Sustained directional drive.
Strength (ADX)	ADX trending upward or convex.	Internal coherence.
Behaviour	Deep pullbacks acceptable if S/R supports respected; wicks below supports imply absorption.	Normal digestion after breakout.

S/R Support Structure (from S1)

* **Base S/R**: The highest S/R support level < breakout_price that price was respecting in S0 (cached in S1 as `base_sr_level`).
  - This is the invalidation line — if price closes below this with mid/slow band deterioration, full invalidation.
  
* **Flipped S/R levels**: All S/R levels that price broke above during S1 breakout (cached as `flipped_sr_levels` array).
  - **Ordered by price descending** (first flipped = highest price level = strongest support tier)
  - If multiple levels break on same bar, order by price descending within that cluster
  - Each level has a score from geometry system and a breakout timestamp
  - These now act as dynamic support tiers

* **EMAs/AVWAP**: Diagnostic only (not support tiers).
  - EMA proximity to active S/R boosts that level's support_persistence score (via ema_alignment component)
  - AVWAP diagnostic tracks conviction (slope direction)

Flag System & Transition

**S1→S2 Transition**: When price touches (within halo) any flipped S/R level (or base) AND gets a close ≥ that level. This marks the end of breakout, start of retest phase.

**Trigger**: S2 emits when conditions above are met. Emits continuously as price moves between S/R levels and conditions change.

When S2 conditions hold, emit the state object:

{
  "flag": {
    "uptrend_holding": true,
    "uptrend_confirmed": false,
    "uptrend_failed": false
  },
  "sr_supports": {
    "current_sr_level": 1.228,
    "current_tier": "flipped_2",
    "base_sr_level": 1.212,
    "flipped_sr_levels": [
      {"level": 1.238, "score": 28, "order": 1},
      {"level": 1.232, "score": 22, "order": 2},
      {"level": 1.228, "score": 18, "order": 3}
    ],
    "halo": "max(0.5*ATR_1h, 3% of price)",  // Computed per level at time of retest (local ATR), not global from t0
    "t0": "2025-10-27T12:00Z"
  },
  "scores": {
    "trend_integrity": 0.73,
    "trend_strength": 0.71,
    "breakout_strength": 0.65
  },
  "diagnostics": {
    "support_persistence": 0.74,
    "reaction_bounce_atr": 0.9,
    "closes_above_since_t0": 7,
    "absorption_wicks_since_t0": 3,
    "ema_alignment": 0.68,
    "volatility_coherence": 0.81,
    "rsi_trend": 0.70,
    "adx_trend": 0.66,
    "mid_band_slope": 0.0008,  // Normalized: slope / EMA60_value → %/bar
    "slow_band_slope": 0.0005,  // Normalized: slope / EMA144_value → %/bar
    "mid_band_accel": 0.0002,  // Normalized: Δ(slope) / EMA60_value → %/bar²
    "slow_band_accel": 0.0001  // Normalized: Δ(slope) / EMA144_value → %/bar²
  }
}

Computation Logic

**Support Persistence (0–1)** — computed per active S/R level (adapts to which level price is testing):

```
support_persistence = 0.25 * touch_confirm
                   + 0.20 * reaction_quality
                   + 0.40 * close_persistence
                   + 0.15 * absorption_wicks
```

Components (evaluated relative to current active S/R level):

1. **touch_confirm (0–1)**:
   - 1 if `low <= current_sr_level + halo` at t0 AND a `close >= current_sr_level` occurred (same bar or later)
   - 0 otherwise

2. **reaction_quality (0–1)**:
   - `bounce_atr = (max_high_since_t0 - current_sr_level) / ATR_1h`
   - `reaction_quality = min(1, bounce_atr / 1.0)`
   - Captures peak bounce since t0; saturates at 1 ATR

3. **close_persistence (0–1)**:
   - Count of 1h closes ≥ current_sr_level since t0
   - `close_persistence = 1 - exp(-closes_above / 6)`
   - Main driver of persistence; soft saturation

4. **absorption_wicks (0–1)**:
   - Count candles where `low < current_sr_level` but `close >= current_sr_level` since t0
   - `absorption_wicks = 1 - exp(-wick_count / 2)`
   - Shows demand absorption; 2–3 good wicks → near 1.0

**Note**: When price steps to a different S/R level, recompute support_persistence relative to the new level.

**Trend Integrity (0–1)**:

```
trend_integrity = 0.55 * support_persistence
                + 0.35 * ema_alignment
                + 0.10 * volatility_coherence
```

- **support_persistence**: primary signal (defined above)
- **ema_alignment (0–1)**: Composite capturing structural flow and foundation:
  - 0.15 if EMA60_slope ≥ 0 (mid band positive — helps, but neutral/negative during retest is OK and doesn't hurt)
  - 0.50 for slow band structural foundation (EMA144, 250, 333):
    - Composite score = `0.30 * slow_flattening + 0.40 * slow_acceleration + 0.30 * slow_positive`
    - **slow_flattening (0–1)**: Measures slope improvement (flattening from negative toward zero):
      - For each of EMA144, 250, 333: if slope was negative N bars ago, compute improvement = `(slope_now - slope_N_bars_ago) / |slope_N_bars_ago|` 
      - Average across the three, then sigmoid → `slow_flattening`
      - Captures structural foundation recovering/improving
    - **slow_acceleration (0–1)**: Measures slope acceleration (rate of change improving):
      - For each of EMA144, 250, 333: `Δ(slope) = slope_now - slope_N_bars_ago` (N = 5-10, tune)
      - If slope is negative: acceleration = positive Δ(slope) means less negative (good)
      - If slope is positive: acceleration = positive Δ(slope) means more positive (good)
      - Average across the three, then sigmoid → `slow_acceleration`
    - **slow_positive (0–1)**: Binary check — fraction of EMA144, 250, 333 with slope ≥ 0
      - `slow_positive = (count(slope ≥ 0) / 3)`
  - 0.20 if EMA20 > EMA60 (fast > mid alignment — ordering check, not structural)
  - 0.15 × sigmoid(separation) where separation = (EMA20 - EMA60) / EMA60 × 100
  - **Note**: Fast band (20-30) ignored for structural checks (confluence only). Mid band (60) positive helps but neutral/negative during retest is acceptable. Slow band (144, 250, 333) is the structural foundation — flattening, acceleration, and turning positive are the core signals.
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

**S/R Level Boost** (depth = more safety = higher confidence):

When computing final scores for PM, apply tier-based boosts based on current S/R tier:

- **First flipped S/R (highest)**: 0% boost → integrity and strength unchanged
- **Subsequent flipped S/R**: +10% boost per tier down → integrity × 1.10, strength × 1.10 (capped at 1.0)
- **Base S/R (lowest, strongest)**: +30% boost → integrity × 1.30, strength × 1.30 (capped at 1.0)

**Rationale**: Being at a lower, stronger S/R tier provides more downside safety, making the uptrend more robust → scores deserve a confidence boost. Closer to the base = more reliable hold.

**Additional Boost**: If price tests an S/R level near EMA60 or EMA144 (within 0.5 ATR), apply +5% boost to that level's support_persistence. This captures EMA proximity as confluence.

**Tuning Parameters** (adjust in backtests before live deployment):

- **support_persistence weights**: touch_confirm (0.25), reaction_quality (0.20), close_persistence (0.40), absorption_wicks (0.15)
- **volatility_coherence**: `threshold` in sigmoid (start ~0.3, adjust based on ATR behavior)
- **rsi_trend**: `scale` parameter (start ~0.5)
- **adx_trend**: `scale` parameter (start ~0.3)
- **trend_integrity weights**: support_persistence (0.55), ema_alignment (0.35), volatility_coherence (0.10)
- **ema_alignment slow band windows**: 
  - Flattening check: N bars lookback to measure improvement (start 5-10, tune)
  - Acceleration check: N bars for Δ slope computation (start 5-10, tune)
- **ema_alignment**: separation sigmoid scale factor (start ~10–50)
- **close_persistence**: k value in exp decay (start 6, meaning ~6 closes → ~0.63 score)
- **absorption_wicks**: m value in exp decay (start 2, meaning ~2 wicks → near 1.0)
- **uptrend_confirmed**: monotonic window for trend_strength (start with 4–6 bars)
- **S/R tier boost percentages**: First flipped (0%), subsequent flipped (+10% per tier), base (+30%) — may need adjustment
- **EMA proximity boost**: +5% to support_persistence if S/R level within 0.5 ATR of EMA60/144

S/R Level Stepping & Flag Behaviour

**t0 Definition**: timestamp of first touch of current_sr_level's halo when S2 started. **t0 never changes** after initial set (until base S/R fails and S2 ends). Continuous measurement from original t0 through all step-downs and reclaims.

**S/R Support Tiers**: Dynamic list from S1:
- **Flipped S/R levels** (ordered by breakout sequence: first flipped = highest)
- **Base S/R** (lowest, strongest, invalidation line)

**Stepping Order**: First flipped → Second flipped → ... → Base S/R → FAIL

**Flag Transitions**:

- **uptrend_holding = true**: price touched halo at t0 AND got close ≥ current_sr_level

- **Step down**: on any close < current_sr_level → move to next lower S/R level. **t0 unchanged** (continues measuring from original touch). Scores adjust:
  - `trend_integrity *= 0.4` (weakness shows; scores dented but not zeroed)
  - `trend_strength *= 0.6` (momentum lost but not wiped)
  - Scores can rebuild quickly at lower tier because tier boost applies (+10% per tier, +30% at base)

Order of operations (score updates): on step-down or reclaim → (1) apply dent/boost factors to prior scores, (2) recompute component terms with current data (support_persistence relative to new level), (3) apply S/R tier boost based on current tier, (4) clamp to [0, 1].

**Reclaim Behavior**: if close ≥ higher S/R level → set as current_sr_level. **t0 unchanged** (continues measuring from original touch). Reclaiming higher S/R levels is highly bullish:
  - `trend_integrity *= 1.3` (reclaim is MORE bullish than never breaking)
  - `trend_strength *= 1.6` (shows returning strength)
  - Reclaim shows buyers are stronger; this is MORE bullish than a clean hold

- **uptrend_failed = true**: price closes below base S/R (immediate invalidation)
  - Exit immediately with bounce logic on close below base S/R (use bounce zone between base S/R and EMA60/144)
  - If mid/slow band slopes also turn negative, that's a diagnostic tag (structural failure reason) but doesn't gate the exit

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

**This is the primary entry phase.** Entries occur on retests of S/R levels when structural integrity and strength meet aggressiveness thresholds.

**Required Conditions:**
- Price must be at/on an S/R level (within halo) — **can be ANY flipped S/R level or base S/R**
- Both trend_integrity AND trend_strength must meet thresholds (adjusted by breakout_strength)

For aggressiveness A ∈ [0, 1], base thresholds form a **continuous curve**:

```
τ_integrity_base(A) = 0.80 - (0.40 × A)
τ_strength_base(A) = 0.75 - (0.35 × A)
```

**Breakout_strength multiplier** (from S1):
- Applies up to 10% threshold reduction:
  - `τ_integrity(A) = τ_integrity_base(A) × (1 - breakout_strength × 0.10)`
  - `τ_strength(A) = τ_strength_base(A) × (1 - breakout_strength × 0.10)`

This curve maps (before breakout_strength multiplier):
- A = 0.1 (Patient) → integrity ≥ 0.76, strength ≥ 0.72
- A = 0.5 (Normal) → integrity ≥ 0.60, strength ≥ 0.58
- A = 1.0 (Aggressive) → integrity ≥ 0.40, strength ≥ 0.40

**Entry Logic:**
```
if price_at_sr_level (within halo) AND trend_integrity >= τ_integrity(A) AND trend_strength >= τ_strength(A):
    if A < 0.3 (Patient):
        entry_signal = true ONLY if current_sr_level == base_sr_level
    else:
        entry_signal = true  # Normal/Aggressive: any S/R level
```

**Key Points:**
- **Patient (A < 0.3)**: Entries only at base S/R (waits for deepest retest)
- **Normal/Aggressive (A ≥ 0.3)**: Entries at ANY S/R level (any flipped level or base) when conditions are met
- Aggressiveness affects threshold curves (Patient needs higher scores, Aggressive accepts lower)
- More aggressive profiles naturally get entries at higher levels (less likely to wait for deeper retests)
- Reclaim entries: When price reclaims a level (close ≥ that level after being below), scores receive reclaim boosts (lines 675-678). If boosted scores then meet thresholds, entry signal triggers naturally.

**Stop Loss / Invalidation:**
- **Invalidation**: Close below base S/R = full invalidation (use bounce logic)
- **Optional**: Can also exit if S/R level fails AND mid/slow band slopes turn negative (structural failure combo)

**Note**: Keep thresholds light initially. Entries require sufficient scores at whichever S/R level price is testing.

Summary

S2 is the phase of structural confirmation — flipped S/R levels hold as supports, flow aligns (mid/slow bands maintain structure), and volatility stabilises.
The system reports uptrend holding status and continuously scores integrity and strength relative to the active S/R level. Entry logic: Patient profiles only enter at base S/R; Normal/Aggressive profiles can enter at any S/R level when price tests it and scores meet aggressiveness thresholds (adjusted by breakout_strength, up to 10% reduction). Reclaim entries occur naturally when boosted scores after reclaim meet thresholds.
Base S/R serves as invalidation; mid/slow band slope deterioration combined with S/R break signals structural failure.


===========


==========

🜄 S3 — Operating Regime: Overextension (OX)

## Narrative
S3 continuously diagnoses the active trend for overextension—the risk of blow-off, buyer exhaustion, or aging parabola. It does NOT give sell signals directly. Instead, it emits OX (overextension), DX (decay), RX (risk-off), and EDX (exhaustion decay) scores for the Portfolio Manager. These are situational scores, not action directives.

OX is specifically a measure of how fragile and extended the market is:
- How far and fast price has moved above its equilibrium rails (bands)
- How much the bands themselves have stretched apart (ribbon opening)
- Acute volatility or participation surges that often signal tops
- Macro background risk as price moves away from slow anchors

## Scoring Logic

```
OX (0–1) = 
  0.35 × sigmoid((price - EMA20) / (k1 × ATR))         // fast blow-off
+ 0.20 × sigmoid((price - EMA60) / (k2 × ATR))         // mid-ribbon stretch
+ 0.10 × sigmoid((price - EMA144) / (k3 × ATR))        // late mid/slow warning
+ 0.10 × sigmoid((price - EMA250) / (k4 × ATR))        // slow exhaustion, nonlinear
+ 0.10 × sigmoid(dsep_fast / ks1)                      // band expansion (EMA20–EMA60 gap increasing)
+ 0.05 × sigmoid(dsep_mid / ks2)                       // band expansion (EMA60–EMA144 gap increasing)
+ 0.05 × sigmoid((ATR_now - ATR_baseline) / k_atr)     // ATR surge above baseline
+ 0.05 × fragility_factor                              // e.g., VO_z cluster, or negative fast-band curvature Δ
```
- Tune coefficients (`k1`, `k2`, `k3`, `k4`, `ks1`, `ks2`, `k_atr`) in backtests.

### **Explanation**
- **Fast-band distance**: Immediate risk of snap reversals (blow-off/hot-move risk)
- **Mid/slow-band distance**: Late-stage “aging” (macro-risk; less fragile, but not to be ignored)
- **Band expansion terms (dsep_fast, dsep_mid)**: Parabolic structure, market crowding in
- **ATR surge**: Confirms crowd energy/froth
- **Fragility_factor**: Empirical signals of stretch e.g. VO_z burst, declining fast-band curvature

### **EDX modulation:**
```
OX_adj = OX × (1 + 0.33 × clip(EDX − 0.5, 0, 0.5))
```
EDX rising from 0.5 to 1.0 increases OX by up to +33% (aging trend regime).

## Diagnostics (included in state output)
- `price_minus_ema20, price_minus_ema60, price_minus_ema144, price_minus_ema250`
- `dsep_fast, dsep_mid` (band gap expansion)
- `ATR_now, ATR_baseline, ATR_surge`
- `fragility_factor` components (VO_z cluster, fast-band curvature change)

## Geometry and S/R Context
- OX is an indicator—flashing warning of stretch
- **Not scored**: proximity to channel tops, S/R, or geometry
- **PM** will map OX state to relevant S/R or geometry for action (eg. place trims just before major resistance)

## S3 Output Example
```json
{
  "state": "S3",
  "scores": {
    "ox": 0.81,
    "ox_adj": 0.93,
    "dx": 0.37,
    "rx": 0.17,
    "edx": 0.78,
    "trend_integrity": 0.68,
    "trend_strength": 0.58
  },
  "sr_context": {
    "current_sr_level": 1.274,
    "nearest_topside_sr": 1.295,
    "halo": 0.0125
  },
  "diagnostics": {
    "price_minus_ema20": 0.012,
    "price_minus_ema60": 0.022,
    "price_minus_ema144": 0.043,
    "price_minus_ema250": 0.081,
    "dsep_fast": 0.0018,
    "dsep_mid": 0.0009,
    "ATR_now": 0.024,
    "ATR_baseline": 0.019,
    "ATR_surge": 0.26,
    "fragility_factor": 0.41,
    "vo_z_cluster": true,
    "ema20_curvature": -0.00012
  }
}
```
trend_integrity and trend_strength are always output in S3 as structural context for the Portfolio Manager. They do not affect OX/DX/RX/EDX but are useful for PM action logic.

## DX — Discount (Buy-the-Dip) Score

**DX** is a continuous score (0–1) indicating the quality of re-entry opportunity after a trend extension—i.e., “is the market sufficiently cooled, in the right structural spot, and showing exhaustion/reversal signs?” The discrete **flag** for "reload zone" (dx_flag) is ON if price is at/under EMA144; the score increases exponentially with depth toward/under EMA333, and is further **boosted** by slow-band compression (tightly wound 144/250/333).

**DX does not include trend_integrity/strength or support_persistence — it is an independent measure of location, exhaustion, relief, and curl.**

### Scoring Logic

```
// Band location (0–1): reload zone proximity & compression boost
x = clamp( (price − EMA144) / (EMA333 − EMA144), 0, 1 )
DX_location = exp(−3·x)     // rapid exponential; maxes at EMA333 and below
DX_band_compression = sigmoid( (historic_min − (EMA333−EMA144)) / historic_min_scale ) // higher when bands compressed, multiplies DX_location
DX_location_final = DX_location × DX_band_compression

// Exhaustion (0–1): signs of seller blowout & absorption
DX_exhaustion = 0.6·min(1, Σ max(0, −VO_z)/6, window=k) + 0.4·(1 − exp(−wick_down_count/2))  // last k bars around zone touch

// Relief (0–1): volatility cooling & early reversal cues
DX_relief = 0.5·sigmoid( (ATR_now/ATR_pullback_peak − 0.9)/0.05 ) + 0.5·max(sigmoid(RSI_slope_5/0.4), sigmoid(ADX_slope_5/0.3))

// Curl: small bonus if slowest flows begin to inflect up
DX_curl = 1 if Δema144_slope > 0 else 0     // bonus only

// Final score:
DX = 0.45·DX_location_final + 0.25·DX_exhaustion + 0.25·DX_relief + 0.05·DX_curl
// Clamp DX to [0,1]
// Compute ONLY when price is in/under 144–333 band; otherwise, DX = 0
```

### Diagnostics (include in S3 output)
- dx_location
- dx_band_compression
- dx_exhaustion (vo_z− sum, wick absorption)
- dx_relief (atr_relief, RSI/ADX_slope)
- dx_curl (Δema144_slope)

### Example Output Structure
```json
{
  "scores": {
    "ox": 0.81,
    "dx": 0.61,
    "dx_flag": true,
    "edx": 0.42,
    "trend_integrity": 0.68,
    "trend_strength": 0.58
  },
  "diagnostics": {
    "dx_location": 0.72,
    "dx_band_compression": 0.94,
    "dx_exhaustion": 0.68,
    "dx_relief": 0.57,
    "dx_curl": 1,
    "price_minus_ema20": 0.012,
    ...
  }
}
```

DX ramps up sharply as price dips deeper into/under the slow-band reload zone, and is highest when bands are tightly compressed, sellers are exhausted, volatility cooled and indicators start to curl up. Trend integrity/strength remain separate context fields for PM gating or modulating actual entry behaviour.

### OX Trim Dynamics (Late-Cycle Adaptation)

> **Important:** When EDX is high (trend decay), OX trim thresholds are dynamically lowered and trims can be triggered on any upward rally into OX bands—even if price is falling or just bouncing off lows—not only at new uptrend peaks. This ensures that exposure reduction happens proactively as the trend ages, not just reactively at blow-off tops. Late-stage bounces and any rallies into band extension zones become valid trim opportunities whenever EDX is elevated.

> In addition, weak trend_integrity or trend_strength (TI/TS) further increases the propensity and size of trims, as interpreted by the PM layer. The PM may (and should) require more aggressive trimming or scaling out as TI/TS scores fall below healthy thresholds—especially in conjunction with high OX or EDX.

> In summary: **higher OX, higher EDX, and weaker TI/TS all boost the likelihood and strength of trims during S3. The Portfolio Manager is expected to layer these together, responding more forcefully as the uptrend decays or danger develops.**

> **EDX Modulation — DX as a Smooth Function of Decay:**
As EDX rises, all discount/rebuy (DX) opportunities are progressively diminished: both the frequency and magnitude of re-entries decrease, and in high-decay regimes, adds shut down regardless of aggressiveness/personality. This is implemented by continuously multiplying DX by a decreasing function of EDX—not by a hard gate—so adaptation is smooth and flexible for all PM logic. In low EDX (fresh uptrend), all rebuys occur at full strength—no additional bonus is needed; this is the default system behaviour.


## EDX — Exhaustion-Decay Index (Meta Trend Vitality Score)

**EDX** is the state machine's continuous, global risk field. It measures the aging and decay of the trend—a normalized score [0,1] that integrates structure loss, momentum fatigue, participation decay, and volatility disorder. EDX is **not an exit trigger** but is the governing moderator for all risk-taking and risk-off behaviour in S3.

### Narrative
- **Low EDX (near 0):** Trend is fresh/healthy. All compounding/adding is encouraged when in the right band; trims are only tactical (OX-only).
- **Rising EDX:** Trend “organism” is tiring. New adds (DX) slow and then turn off; trims (OX) are triggered earlier and heavier; risk-taking drops.
- **High EDX:** Decay regime. No adds occur; trims take priority; full exits favored at any breakdown/bounce; PM is fully defensive.

### Component Signals/Inputs
- **1. Slow-field curvature:**
  - Negative/flattening slopes in EMA250, EMA333
  - Rollovers (ΔEMA250_slope, ΔEMA333_slope < 0)
- **2. Structure failure:**
  - Rising count of lower highs/lower lows (ZigZag in last N bars)
  - Increasing ratio of closes below EMA50/major S/R
  - S/R reclaim attempts failing repeatedly
- **3. Participation decay:**
  - Falling moving average of volume, VO_z imbalance (Σ−VO_z − Σ+VO_z)
  - AVWAP slope flattening or turning negative
- **4. Volatility disorder:**
  - ATR asymmetry between upswings and downswings
  - Recent up-moves resulting in new lows (burst-fail: ATR spikes up then price fails)
- **5. Band geometry rollover:**
  - Slowening or negative slope of (EMA144–EMA333)/price (“the rails flatten or invert”)

### Composite formula
```
EDX_raw = 0.30·slow + 0.25·struct + 0.20·part + 0.15·vol_dis + 0.10·geom
EDX = EMA(EDX_raw, span=20 bars)
```
- Each component is itself a normalized score from its contributing stats.

### Example Output (add to S3 diagnostic/payload)
```json
{
  "scores": {
    "ox": 0.77,
    "dx": 0.09,
    "edx": 0.81,
    ...
  },
  "diagnostics": {
    "edx_slow": 0.91,
    "edx_struct": 0.88,
    "edx_part": 0.63,
    "edx_vol_dis": 0.58,
    "edx_geom": 0.71,
    ...
  }
}
```

### Usage Guidance
- **EDX modulates every risk response:**
  - As EDX rises, rebuys (DX) vanish, OX trims become larger and trigger earlier, adds/compounds are fully routed away, and all exposure should shrink barring exceptional PM overrides.
- **EDX is NOT a discrete exit event.** AVWAP is used as a diagnostic input (e.g., slope sign/conviction) only; it never gates S3 transitions or forces exits on its own.
- PM and higher logic should use EDX as the meta regime flag for dynamic risk-throttling, always in concert with OX, DX, and global TI/TS scores.


## S3 Payload and Logging

This section standardizes what S3 emits every tick and how we persist history for analytics. The same pattern can be mirrored for other states, but S3 is defined explicitly here.

### Base Payload (always)
```json
{
  "state": "S3",
  "scores": {
    "ox": 0.0,
    "dx": 0.0,
    "edx": 0.0,
    "trend_integrity": 0.0,
    "trend_strength": 0.0
  },
  "sr_context": {
    "current_sr_level": 0.0,
    "nearest_topside_sr": 0.0,
    "halo": 0.0
  },
  "flags": {
    "dx_flag": false,
    "emergency_exit": { "active": false }
  }
}
```
- Base payload is minimal and stable for consumers (PM, dashboards). It is emitted every tick.

### Diagnostics Extensions (optional)
- OX diagnostics (when relevant): `price_minus_ema20`, `price_minus_ema60`, `dsep_fast`, `dsep_mid`, `ATR_now`, `ATR_baseline`, `fragility_factor`, etc.
- DX diagnostics (when in/near reload zones): `dx_location`, `dx_band_compression`, `dx_exhaustion`, `dx_relief`, `dx_curl`.
- EDX diagnostics (regime analytics): `edx_slow`, `edx_struct`, `edx_part`, `edx_vol_dis`, `edx_geom`.

> Emit diagnostics when relevant or on threshold crossings to reduce payload bloat. The base payload remains consistent each bar for live operation.

### Logging Policy (history retention)
- Features columns are overwritten each tick; to preserve history, append to a scores log:
  - `scores_log`: (ts, asset, timeframe, scores, flags, sr_context_min, diag_min, schema_version)
  - Persist base scores every tick (cheap, essential).
  - Persist full diagnostics only on events: threshold crossings (OX band enter/exit, DX flag on/off, EDX regime change), state transitions, or PM actions (trim/add/exit).

> This keeps the live payload lean while ensuring full forensic visibility over regime, trims, adds, and decay dynamics in backtests and monitoring.

### S3 Transitions & Bootstrap (note)
- Full invalidation (e.g., decisive break of base S/R; EMA333 circuit-breaker) → drop to S0 immediately; await new S0→S1→S2 sequence.
- Admission to S3 without prior S0/S1/S2 is allowed when history is present and live facts meet thresholds (TI/TS healthy, EDX low, HH/HL present). For brand-new assets with insufficient history, emit S0 until buffers mature.

### Units & Parameters (applies across states)
- Slopes reported/compared as %/bar (slope / EMA_value).
- Halo computed per level at retest time: `halo = max(0.5·ATR_1h, 3%·price)`.
- Sigmoid scales (k) referenced in formulas derive from Global Constants; tune via backtests.


## S3 Readiness by History (New Listings)

This clarifies when regimes/flags are reliable for brand-new assets (no backfill). Times assume 1h bars; lower timeframes accelerate readiness proportionally.

- 0–1 days (~0–24 bars)
  - Available: S0 observation only; fast indicators warming up; no reliable S1/S2/S3.
  - PM: do not enter from SM signals (unless policy forces a seed size).

- 1–3 days (~25–75 bars)
  - Available: early S1 (breakout) and first S2 (pullback/hold) using fast/mid inputs; S3 proto-signals low-confidence.
  - PM: may probe small on S1/S2 if policy permits; treat S3 as degraded.

- 3–6 days (~75–144 bars)
  - Available: S2 robust (trend_integrity/strength credible); S3 largely usable; EMA144 mature; DX limited (hallway up to 250); OX normal.
  - PM: normal S2/S3 actions allowed (subject to aggressiveness); cautious DX.

- 7–14 days (~150–333 bars)
  - Available: full S3 (DX using 144→333 hallway; EDX complete); all scores/flags mature.
  - PM: full regime trading (adds/trims/exits) as specified.

Notes
- With backfilled history, readiness is immediate (treat like mature assets).
- Multi-timeframe (e.g., 15m) can be run in parallel to accelerate early readiness for hot listings.

