📄 UPTREND_ENGINE_V4_SPEC.md

Below is the full document.
Once you confirm, I can polish formatting, generate diagrams, or split into sub-files.

Uptrend Engine v4 — EMA Phase System
Formal Specification (Based on Production Code)

Last Updated: 2025-12-01

0. Purpose

The Uptrend Engine v4 is a single-timeframe trend-state machine that converts raw OHLCV + TA inputs into a discrete trend phase:
S0, S1, S2, S3, or S4.

The engine:

Detects clean trend transitions using EMA-band structure

Emits entry signals, trim signals, decay scores, and emergency flags

Assigns metadata for trend lifecycle (e.g., S3 start timestamp)

Feeds other Lotus components:

Decision Maker

Position sizing

Learning System (pattern_scope_stats)

OX/DX/EDX regime logic

Analytics, dashboards, and state event streams

The engine never places trades.
Its responsibility is:

“Classify the chart into a regime, compute all signals/scores, and publish the state.”

1. State Machine Overview

The engine outputs one of five states:

State	Meaning	Notes
S0	Downtrend / Exit	No buys; strong bearish EMA structure
S1	Primer / Early Uptrend	EMA60 primer buys; testing trend emergence
S2	Defensive Regime	Price > EMA333; trend forming but not fully aligned
S3	Full Uptrend	Strong alignment; allows DX buys, decay management, trims
S4	No Clear State	Bootstrap / holding pattern until trend clarity

Transition rules are strictly deterministic and based entirely on EMA-order structure.

2. EMA Structure Model

The engine relies on six EMAs:

Fast band: EMA20, EMA30

Mid: EMA60

Slow band: EMA144, EMA250, EMA333

State classification is based exclusively on their relative ordering.

2.1 S3 Order (Bullish Alignment)

Defined as:

EMA20 > EMA60
EMA30 > EMA60
EMA60 > EMA144 > EMA250 > EMA333


This forms a clean upward EMA “stack”:
Fast above Mid above Slow, each spaced correctly.

2.2 S0 Order (Bearish Alignment)

Defined as:

EMA20 < EMA60
EMA30 < EMA60
EMA60 < EMA144 < EMA250 < EMA333


Reverse of S3: full bearish alignment.

2.3 Global Exit Precedence — Fast Band at Bottom

If:

EMA20 < min(EMA60,EMA144,EMA250,EMA333)
AND
EMA30 < min(EMA60,EMA144,EMA250,EMA333)


→ Override all logic and force S0, with:

exit_position = True
exit_reason = fast_band_at_bottom


This represents a catastrophic trend breakdown.

3. Bootstrap Behaviour

If no previous state:

If S3 order → bootstrap into S3, set s3_start_ts

Else if S0 order → bootstrap into S0

Else → assign S4 (“watch-only”) until clear S0/S3 emerges

This prevents fake S1/S2 signals during startup.

4. State Definitions & Transitions

Below each state is defined precisely as coded.

4.1 S0 — Pure Downtrend

Stay in S0 unless:

Fast band above EMA60
AND
Price > EMA60


→ Transition to S1 (primer)

Diagnostics include S1 buy-test even during the transition.

4.2 S1 — Primer / Early Uptrend

S1 is where the engine watches for a potential new trend.

Conditions to remain S1:

Price must remain ≤ EMA333

If price > EMA333 → S1 → S2 transition

Core behavior in S1:

Tests S1 buy signal anchored to EMA60 (see Buy Logic)

4.3 S2 — Defensive Regime (Above EMA333)

S2 is an intermediate bullish regime:

Price > EMA333

EMAs not yet in full S3 alignment

Transitions:

Price < EMA333 → S2 → S1

S3 order present → S2 → S3

Behaviors:

Compute OX (overextension)

Set trim flags if:

OX >= 0.65 AND price within 1 ATR of any SR level


Compute S2 retest-buy at EMA333

4.4 S3 — Full Uptrend

S3 enables full trend operation:

DX rebuys

First dip buy

OX trims

EDX decay management

Emergency exit region tracking

Exit from S3:

If all EMAs fall below EMA333:

Clear S3 metadata

Set S0 with exit flags

4.5 S4 — No State / Watch-Only

Stay S4 until either S3 order (→ S3) or S0 order (→ S0)

Diagnostics minimal

Generated primarily during bootstrap or ambiguous alignment

5. Buy Logic — Overview

There are four types of buys:

S1 Primer Buy (EMA60)

S2 Retest Buy (EMA333)

S3 First-Dip Buy (early S3 only)

S3 DX Buy (discount within trend)

Each uses a common helper:

Trend Strength + S/R Boost Gate
TS = f(RSI_slope_10, ADX_slope_10)
SR_boost = proximity(SR_levels to EMA_anchor, halo)
Threshold: TS + SR_boost >= 0.60

5.1 S1 Buy (EMA60)

Anchor: EMA60

Conditions:

|price − EMA60| ≤ 1 ATR

Slope OK:

EMA60_slope > 0 OR EMA144_slope >= 0


TS + SR ≥ 0.60

Outcome:

buy_signal = True

5.2 S2 Retest Buy (EMA333)

Anchor: EMA333

Differences from S1:

Halo = 0.5 ATR (tighter)

Slope check based on slow structure:

EMA250_slope > 0 OR EMA333_slope >= 0

5.3 S3 First-Dip Buy

Allowed only once per S3 episode
(first_dip_buy_taken = True afterwards).

Requirements:

price ≥ EMA333 (no emergency exit zone)

Within first N bars of S3 start:

≤ 6 bars → price near EMA20/30 (0.5 ATR)

≤ 12 bars → price near EMA60 (0.5 ATR)

Slope OK:

EMA144_slope > 0 OR EMA250_slope >= 0


TS + SR ≥ 0.50 (looser)

Produces:

first_dip_buy_flag = True

5.4 S3 DX Buy (Discount Zone Buy)

Conditions:

Price ≤ EMA144 (discount hallway)

Slope OK: EMA250_slope > 0 OR EMA333_slope >= 0

TS + S/R ≥ 0.60

Emergency exit NOT active

DX ≥ threshold (adaptive):

threshold = DX_BASE 
            + EDX_suppression 
            - price_position_boost


Where:

EDX elevates threshold as trend decays

Price position inside EMA144–EMA333 lowers threshold near EMA333

Produces:

buy_flag = True

6. Trim Logic

Applies to S2 and S3.

trim_flag = (OX >= 0.65) AND (price within 1 ATR of any S/R level)


This detects overextension into resistance.

7. Emergency Logic
7.1 Emergency Exit Region (S3)

If price < EMA333:

emergency_exit = True


Effects:

Blocks DX buys

Recorded in payload

Used to detect reclaimed_ema333 when price rises back above

Does not change state.

7.2 Hard Exit from S3 → S0

If all EMAs drop below EMA333:

state = S0
exit_position = True
exit_reason = all_emas_below_333
clear s3_start_ts
clear first_dip_buy_taken


This is the structural failure of the trend.

8. Score Systems
8.1 TS (Trend Strength)

TS = normalized composite of:

RSI_slope_10

ADX_slope_10

Range [0,1].

Used in all buy decisions.

8.2 OX (Overextension)

Computed in:

S2 (OX-only)

S3 (OX boosted by EDX)

Components:

Distance from EMA20/60/144/250

Expansion (separation slopes)

ATR surge

Fragility (EMA20 curvature)

OX ∈ [0,1].

8.3 DX (Discount)

Used only in S3.

Measures “buyable discount location”:

Position of price in EMA144→EMA333 hallway

Exhaustion

Relief (ATR/RSI/ADX)

Curl

Large DX → oversold within trend.

8.4 EDX (Decay)

3-window decay measure of trend health since S3 start.

Windows:

Full: since S3 entry

Mid: last ⅔

Recent: last ⅓

Components:

Slow-field momentum (EMA250/333 slopes, RSI and ADX trend)

Structure failure (HH/HL vs LH/LL)

Participation decay (AVWAP slope)

EMA compression (EMA144–333, EMA250–333)

EDX ∈ [0,1].

High EDX → late-stage trend → suppress DX buys.

9. Metadata & Events

Each payload includes:

state

timestamp

price + full EMA set

buy/trim flags

scores (OX/DX/EDX/TS)

diagnostics (always populated)

s3_start_ts (metadata)

first_dip_buy_taken

Engine emits:

uptrend_state_change


events into uptrend_state_events.

**10. Notes for Future Expansion

(Crypto → Stocks, Commodities, FX, Index Futures, Bonds)**

This lays groundwork for the next phase of your question.

The engine is largely universal because:

EMAs work across all markets

ATR, RSI, ADX, separations, slopes all apply

State machine logic (EMA order) is asset-agnostic

Decay (EDX) windows automatically self-adapt

However, certain adaptations are required:

10.1 ATR behaviour differs in stocks/commodities

ATR in equities is much more sensitive to earnings gaps, news shocks.
Need:

Optional “gap normalization”

Possibly use True Range without overnight gap

Or separate intraday/overnight regimes

10.2 Volume behaviour differs drastically

Crypto = 24/7, continuous volume
Stocks = discrete sessions, zero volume overnight
Commodities = session-based
FX = 24/5

Effects:

AVWAP slope may require timezone/session handling

Volume-based exhaustion/relief requires session normalization

10.3 EMA333 vs intraday bars

For assets with limited history or shorter sessions, EMA333 may represent months of data.
Need:

Adaptive slow-band periods (e.g., 55/144/200 or 100/200/300 variants)

Or create synthetic continuous OHLC streams for equities

10.4 FX and Commodities have fewer “climaxy” OX patterns

Adjust:

ATR surge scaling

Expansion coefficients

Fragility scaling

10.5 Equity indices trend cleaner → EDX windows are extremely powerful

But require:

Event blackout periods (NFP, CPI, FOMC)

Adaptive windowing around macro events

10.6 Bonds require different volatility scaling

Bond markets trend tightly and rarely display crypto-style S3 expansions.

Probably need:

Different constants for EDX slope filters

Smaller halo multipliers

Possibly a tighter EMA band

✦
I will produce a full extension spec once we finish this doc.