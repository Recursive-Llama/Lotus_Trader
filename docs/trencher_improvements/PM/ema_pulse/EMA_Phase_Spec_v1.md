# EMA Phase System v1 - Specification

## Architecture Principle

**The Uptrend Engine emits signals and flags — it does NOT make trading decisions.**

- Engine outputs: state transitions, condition flags, quality scores
- Decision makers: Portfolio Manager (production) or Backtester (simulation)
- Engine responsibility: compute and emit clear, actionable signals
- External responsibility: interpret flags and execute trades

---

## Conceptual Foundation

### The Breathing Model

Think of EMAs as **threads in a flow of air**:

- **Inhale (compression)**: EMAs converge, spacing tightens
- **Exhale (expansion)**: EMAs diverge, spacing widens
- **Order**: Hierarchy — who's on top, who's below
- **Breath rhythm**: How quickly order is changing (the pulse)
- **Curvature**: How each line is bending (the physical motion)

### Three Components

1. **Order** = Structure (EMA stacking arrangement)
2. **Acceleration of order** = Momentum of structural change
3. **Curvature** = Physical bending of each EMA line

When order breaks down while curvature turns up → potential forming (inhale).  
When order expands and curvature flattens → energy spent (exhale).

---

## State Definitions

### S0: Pure Downtrend (Compression/Base)

**Definition**: Perfect bearish EMA order maintained.

**Required Order** (strict, no tolerance):
```
EMA333 > EMA250 > EMA144 > EMA60 > EMA30 > EMA20
```

**Transition to S1**: First violation occurs when **EMA20/30 crosses above EMA60**.

**Output flags**: `state: "S0"`, `watch_only: true`

---

### S1: Primer (First Disorder + 60 Turning Up)

**Definition**: Order broken (20/30 above 60), EMA60 showing lift signal.

**Entry conditions** (from S0):
- **EMA20 > EMA60 AND EMA30 > EMA60** (both fast band EMAs must be above 60 — first order violation)
- PLUS one of two EMA60 acceleration patterns (see below)
- **Optional safety valve (v1 default: disabled)**: Allow `EMA20 > 60 AND EMA30 ≥ 60` for 1 bar, but both must be `> 60` by bar 2; otherwise revert to S0.

**S1.A — Accelerating Up**:
```
- S_micro(60) > S_meso(60) > S_base(60)  (strictly ordered)
- AND S_meso(60) ≥ 0  (slope is flat-to-positive)
- Persistence: Must hold for 3 bars
```

**S1.B — Steady Lift** (non-accelerating, but up):
```
- S_micro(60) ≈ S_meso(60) > S_base(60)  (micro ~ meso, both > base)
- AND S_meso(60) ≥ 0  (slope is flat-to-positive)
- Persistence: Must hold for 3 bars
```

**Critical**: In both S1.A and S1.B, `S_meso(60) ≥ 0` is required. We do NOT call it bottoming if the meso slope is still negative — a less-negative downslope is not sufficient for S1.

**Noise tolerance**: Use `noise_band = stdev(slope over last W_meso bars) * 0.2` to ignore flickers. (Compute stdev over the same W_meso window for self-consistent scale.)

**Cancel conditions** (any triggers return to S0; **both conditions require 3-bar persistence** before state actually flips to S0):
1. **Rolling over** (must persist 3 bars):
   - `S_micro(60) < S_meso(60)`
   - AND `S_meso(60) ≤ 0`
   - AND `S_micro(60) < 0` (micro must be negative)
2. **Fast band drops** (must persist 3 bars):
   - EMA20 AND EMA30 both below EMA60

**Persistence blocking**: During the 3-bar cancel persistence check, **S1→S2 transition is blocked**.

**Output flags**: 
- `state: "S1"`
- `acceleration_type: "accelerating_up" | "steady_lift"`
- `s1_valid: true` (only when not in cancel persistence)

---

### S2: Buy Signal 1 (Swing Entry)

**Definition**: Price and fast band above EMA60, ready for entry.

**Entry conditions** (from S1 only, all must be true):
1. **Price > EMA60**
2. **EMA20 > EMA60 AND EMA30 > EMA60** (fast band above 60)
3. **Entry zone**: Price within **halo = 0.5 * ATR** of EMA60 (adaptive zone, replaces fixed 3%)
4. **Slope requirement**: `S_meso(60) > 0` **OR** `S_meso(144) ≥ 0`
5. **Quality gates**: `TI ≥ 0.45` AND `TS ≥ 0.58` (TS is primary gate; TI reduced for breakout/retest entry)
6. **Optional S2 entry bonus**: If an S/R level (from geometry) is within halo of EMA60, boost TI by up to +0.15 based on S/R strength. This is optional and does not block entry if absent.

**TI/TS Computation** (pre-entry, last 3 bars):
- **Support persistence** (55% weight): Tracks price behavior relative to EMA60 over last 3 bars
  - Close persistence: % of closes above EMA60
  - Reaction quality: Bounce off EMA60 (measured in ATR)
  - Absorption wicks: Wicks below EMA60 with closes above
  - Touch confirm: Current price within halo and above EMA60
- **EMA alignment** (35% weight): Slow EMA slopes, acceleration, fast>mid ordering
- **Volatility coherence** (10% weight): ATR behavior relative to mean

**Note**: Multiple aligned conditions provide filtering; no additional persistence/hysteresis needed.

**Reset to S0** (before reaching S3):
- EMA20 OR EMA30 crosses back below EMA60
- **3-bar persistence** required before reset (prevents flicker on choppy assets)
- Exit position and revert to S0 logic after persistence confirmed

**Output flags**:
- `state: "S2"`
- `buy_signal: true` (when all entry conditions met)
- `ti_score: <value>`, `ts_score: <value>`
- `entry_zone: true` (price within halo of EMA60)

---

### S3: Trending (Operating Regime)

**Definition**: All EMAs above EMA333 (bullish alignment achieved).

**Required condition**:
```
ALL of: EMA20, EMA30, EMA60, EMA144, EMA250 > EMA333
```

**Note**: Intra-stack order between these EMAs is less important. Only requirement is all above 333.

**Price requirement**: Price does NOT need to be above EMA333 for S3 status. Price can temporarily dip below 333 (triggers emergency exit flag, separate from S3 status).

**Output flags**:
- `state: "S3"`
- `trending: true`
- `ox_score: <value>`, `dx_score: <value>`, `edx_score: <value>`
- `ti_score: <value>`, `ts_score: <value>` (computed and stored)

---

## State Transitions

### S0 → S1
**Trigger**: EMA20/30 crosses above EMA60 + EMA60 acceleration signal (S1.A or S1.B)
**Blocking**: None (from S0 baseline)

### S1 → S2
**Trigger**: All S2 entry conditions met (see S2 definition)
**Blocking**: 
- Cannot trigger during S1 cancel persistence (3-bar check)
- Must wait until cancel check completes with no cancel

### S2 → S3
**Trigger**: All EMAs above EMA333 (see S3 definition)
**Blocking**: None (natural progression)

### S2 → S0 (Reset)
**Trigger**: EMA20 OR EMA30 crosses back below EMA60
**Action**: **3-bar persistence** required before reset (prevents flicker). After persistence confirmed: exit position, reset cycle.

**Note**: The reset persistence counter is cleared if fast band recovers above EMA60 before the 3-bar threshold is reached.

**Optional cooldown (v1 default: disabled)**: After an S2→S0 reset, require `EMA20 < EMA60 AND EMA30 < EMA60` for 2 bars before allowing S1 again. This prevents churny S2→S0→S1 loops on choppy assets. Leave commented off in v1; enable as field switch if needed.

### S3 → Emergency Exit (Flag Only)
**Trigger**: Price breaks below EMA333
**Action**: Emit `emergency_exit: { active: true, reason: "price_below_ema333" }`
**Note**: Does NOT change state to S0. Still in S3, but warning flag active.
**Persistence**: Emergency exit flag can trigger on a **single close below EMA333**; no persistence required. This is an immediate warning signal, not a state transition.

### S3 → S0 (Reset)
**Trigger**: ALL of the following EMAs break below EMA333: **EMA20, EMA30, EMA60, EMA144, EMA250** (exact list: all 5 must be below 333)
**Action**: Full trend reset, clear S1/S2 meta, enter S0

### Emergency Exit → Fakeout Recovery
**Trigger**: While in emergency exit state:
- Price reclaims above EMA333
- AND `TI ≥ 0.45` AND `TS ≥ 0.58` (currently testing with reduced TI threshold)
- AND this occurs BEFORE S0 reset triggers (before other EMAs break below 333)
**Action**: Clear emergency exit flag, remain/return to S3
**Output**: `fakeout_recovery: true`, `emergency_exit: { active: false }`

**Note**: TI threshold may be raised to 0.60 after initial testing phase.

---

## Tri-Window Acceleration

### Window Sizes (proportional to EMA length n)

```
W_micro = max(5, round(n / 15))
W_meso  = max(10, round(n / 5))
W_base  = max(20, round(n / 2))
```

**Examples**:
- EMA20: (5, 10, 20)
- EMA60: (5, 12, 30)
- EMA144: (10, 30, 70)
- EMA333: (20, 65, 165)

### Slope Calculation

For EMA(n), compute:
```
slope_t = EMA[n]_t - EMA[n]_{t-1}
S_micro = mean(slope, last W_micro bars)
S_meso  = mean(slope, last W_meso bars)
S_base  = mean(slope, last W_base bars)
```

### Acceleration Classification

**Noise band**: `band = stdev(slope) * 0.2`

**Comparison functions**:
```python
def gt(a, b): return (a - b) > band  # strictly greater (with noise tolerance)
def lt(a, b): return (b - a) > band  # strictly less
def approx(a, b): return abs(a - b) <= band  # approximately equal
```

**Accelerating up**: `gt(S_micro, S_meso) AND gt(S_meso, S_base) AND gt(S_base, 0) AND (S_meso >= 0)`

**Accelerating down**: `lt(S_micro, S_meso) AND lt(S_meso, S_base) AND lt(S_base, 0) AND (S_meso <= 0)`

**Rolling over**: `lt(S_micro, S_meso) AND gt(S_meso, S_base)`

**Bottoming**: `gt(S_micro, S_meso) AND lt(S_meso, S_base)`

**Steady up**: `approx(S_micro, S_meso) AND gt(S_micro, S_base) AND gt(S_meso, S_base) AND (S_micro >= 0) AND (S_meso >= 0)`

**Steady**: `approx(S_micro, S_meso) AND approx(S_meso, S_base)`

---

## Integration Points (What We Keep)

### TI/TS (Trend Integrity / Trend Strength)
- **S2 entries**: Used as quality gates (TI ≥ 0.45, TS ≥ 0.58)
  - **TS is primary gate** (momentum-based: RSI slope + ADX slope)
  - **TI is monitored** (reduced threshold for breakout/retest entry context)
  - **Computation**: EMA60-based support persistence (last 3 bars, pre-entry) + EMA alignment + volatility coherence
- **S3 fakeout recovery**: Used as quality gates (TI ≥ 0.45, TS ≥ 0.58) — currently testing with reduced threshold
- **Storage**: Compute and store in S3 (even during emergency exit) for potential fakeout analysis

**TI Formula**:
```
TI = 0.55 * support_persistence + 0.35 * ema_alignment + 0.10 * volatility_coherence
+ (optional S/R boost: up to +0.15 if S/R level near EMA60)
```

**Support Persistence Components** (last 3 bars, relative to EMA60):
- 40% close persistence (closes above EMA60)
- 25% touch confirm (current price within halo)
- 20% reaction quality (bounce off EMA60 in ATR terms)
- 15% absorption wicks (wicks below, closes above)

### OX/DX/EDX (Overextension / Deep Zone / Expansion Decay)

**Purpose**: In S3 (trending regime), these scores measure trend quality, extension, and potential reversal zones.

**Reference Implementation**: Use `_compute_s3_scores()` from `uptrend_engine_v2.py` as the source implementation. The formulas below summarize the logic.

#### EDX (Expansion Decay Index)

**What it measures**: How much the trend is losing energy / showing structural weakness.

**Components** (weighted composite):
1. **Slow curvature decay** (30%):
   - EMA250 slope negative: `sigmoid(-ema250_slope / 0.00025)`
   - EMA333 slope negative: `sigmoid(-ema333_slope / 0.0002)`
   - Average: `0.5 * ema250_term + 0.5 * ema333_term`

2. **Structure failure** (25%):
   - Closes below EMA60 ratio (last 50 bars)
   - Lower-low fraction (consecutive lower lows)
   - Combined: `0.5 * sigmoid((ll_ratio - 0.5) / 0.2) + 0.5 * sigmoid((below_mid_ratio - 0.4) / 0.2)`

3. **Participation decay** (20%):
   - Volume Z-score negative: `sigmoid(-vo_z_1h / 1.0)`
   - Measures loss of buying interest

4. **Volatility disorder** (15%):
   - ATR asymmetry: compare up-bar vs down-bar True Range
   - Higher down-bar TR relative to up-bar = more disorder
   - Formula: `sigmoid(((down_avg / up_avg) - 1.0) / 0.2)`

5. **Geometry rollover** (10%):
   - Band separations rolling negative: `0.6 * sigmoid(-dsep_mid / 0.0010) + 0.4 * sigmoid(-dsep_fast / 0.0015)`

**Composite**:
```
EDX_raw = 0.30 * slow_down + 0.25 * struct + 0.20 * part_decay + 0.15 * asym + 0.10 * geom_roll
```

**Smoothing**: EMA(20) with asset-change reset to prevent cross-contamination between positions.

**Output**: `0.0` (healthy) to `1.0` (decaying). Higher = trend weakening.

#### OX (Overextension Index)

**What it measures**: How stretched/extended the trend is (sell zone indicator).

**Components**:
1. **Rail distances** (80%):
   - Rail fast: `sigmoid((price - EMA20) / (ATR * 1.5))` — 35% weight
   - Rail mid: `sigmoid((price - EMA60) / (ATR * 2.0))` — 20% weight
   - Rail 144: `sigmoid((price - EMA144) / (ATR * 1.5))` — 10% weight
   - Rail 250: `sigmoid((price - EMA250) / (ATR * 2.0))` — 10% weight

2. **Expansion** (15%):
   - Fast separation: `sigmoid(dsep_fast / 0.0015)` — 10% weight
   - Mid separation: `sigmoid(dsep_mid / 0.0010)` — 5% weight

3. **ATR surge** (5%):
   - `sigmoid((ATR_1h / ATR_mean_20) - 1.0)`

4. **Fragility** (5%):
   - EMA20 slope negative: `sigmoid(-ema20_slope / 0.0008)`

**Base composite**:
```
OX_base = 0.35*rail_fast + 0.20*rail_mid + 0.10*rail_144 + 0.10*rail_250 +
          0.10*exp_fast + 0.05*exp_mid + 0.05*atr_surge + 0.05*fragility
```

**EDX modulation** (+33% max boost):
- `edx_boost = max(0.0, min(0.5, edx - 0.5))`  (only if EDX > 0.5)
- `OX = OX_base * (1.0 + 0.33 * edx_boost)`

**Output**: `0.0` (not extended) to `1.0` (very extended). Higher = sell signal.

**v3 Enhancement**: Wait for **early signs of EMA/ATR rollover** before triggering sells:
- EMA20/30/60 showing rolling over (from tri-window acceleration)
- OR ATR starting to cool from peak
- OR dsep_fast/mid turning negative

This prevents premature sells in strong trends that are just pausing.

#### DX (Deep Zone Index)

**What it measures**: Buy zone within the 144→333 hallway (consolidation/pullback entry).

**Components**:
1. **Location** (45%):
   - Normalized position in EMA144→EMA333 band: `x = (price - EMA144) / (EMA333 - EMA144)`
   - Deeper = higher score: `exp(-3.0 * x)`
   - Compression multiplier: If band < 3% of price, boost: `(1.0 + 0.3 * comp_mult)`

2. **Exhaustion** (25%):
   - Volume Z-score negative: `sigmoid(-vo_z_1h / 1.0)`

3. **Relief** (25%):
   - ATR cooling: `sigmoid(((ATR_1h / ATR_mean_20) - 0.9) / 0.05)` — 50% weight
   - Momentum relief: `0.5 * sigmoid(RSI_slope / 0.5) + 0.5 * sigmoid(ADX_slope / 0.3)` — 50% weight
   - (Note: ADX must be ≥ 18.0 floor for ADX term to contribute)

4. **Curl** (5%):
   - EMA144 acceleration positive: `1.0 if d_ema144_slope > 0.0 else 0.0`

**Base composite**:
```
DX_base = 0.45 * dx_location + 0.25 * exhaustion + 0.25 * relief + 0.05 * curl
```

**EDX suppression** (score reduction, not gate):
- `supp = max(0.0, min(0.4, edx - 0.6))`  (only if EDX > 0.6)
- `DX = DX_base * (1.0 - 0.5 * supp)`

**DX flag**: `true` when `price <= EMA144` (in the hallway zone).

**Output**: `0.0` (not in buy zone) to `1.0` (strong buy zone). Higher = buy signal.

#### Signal Thresholds (from v2 backtester)

**Normal aggressiveness** (A = 0.5):
- **DX buy**: `dx >= 0.65` AND `dx_flag == true`
- **OX sell**: `ox >= 0.65` (with EDX boost modulation)
- **TI/TS gates**: Use for S2 entries (0.45/0.58) and fakeout recovery (0.45/0.58) — currently testing with reduced TI

**Note**: Current sell signals work well but may be slightly aggressive. Tune later based on backtest results.

#### Diagnostics Output

Each score computation also emits detailed diagnostics:
- Individual component values (rail_fast, exp_fast, dx_location, exhaustion, etc.)
- EDX sub-components (edx_slow, edx_struct, edx_part, edx_vol_dis, edx_geom)
- AVWAP since S1 breakout (if available)

These are useful for debugging and tuning thresholds.

#### v3 Considerations

1. **EMA rollover integration**: Use tri-window acceleration to detect early EMA rollover before OX triggers
2. **ATR volatility**: Monitor ATR cooling from peak as additional sell confirmation
3. **Band separation**: Watch dsep_fast/mid turning negative as structural warning
4. **Keep existing logic**: The core formulas work well; we're adding earlier detection gates, not replacing them

### Geometry S/R Levels
- **Removed from**: Entry signals, S1/S2 state management
- **Kept for**: Exit stop-loss levels, risk management
- **Usage**: External systems (PM) use geometry for exit decisions

---

## Implementation Notes

### Close-Basis Evaluations

**All order, crossover, and price-vs-EMA checks are evaluated on bar close.**

This includes:
- EMA hierarchy checks (S0, S3)
- Crossover detection (S0→S1, S1→S2, S2→S0)
- Price vs EMA comparisons (emergency exit, DX flag)
- Acceleration condition checks

This keeps the engine deterministic and avoids intrabar ping-pong signals.

### Persistence Rules

- **S1 acceleration**: Must persist 3 bars before valid S1 state
- **S1 cancel check**: Must persist 3 bars before canceling to S0
- **Other transitions**: Rely on multi-condition alignment (no generic 3-bar waits)

### Signal Emission Format

Engine outputs to `features["uptrend_engine"]`:

```json
{
  "state": "S1" | "S2" | "S3" | "S0",
  "timeframe": "1h",
  "t0": "<iso_timestamp>",
  "flag": {
    "watch_only": true,  // S0
    "s1_valid": true,    // S1
    "buy_signal": true,  // S2
    "entry_zone": true,  // S2 (price within halo = 0.5 * ATR of EMA60)
    "trending": true     // S3
  },
  "flags": {  // S3 uses "flags" (plural)
    "emergency_exit": {
      "active": true,
      "reason": "price_below_ema333"
    },
    "fakeout_recovery": false
  },
  "scores": {
    "ti": 0.65,
    "ts": 0.62,
    "ox": 0.45,
    "dx": 0.38,
    "edx": 0.25
  },
  "acceleration": {  // S1 only
    "ema60": {
      "type": "accelerating_up" | "steady_lift",
      "s_micro": 0.0012,
      "s_meso": 0.0008,
      "s_base": -0.0001
    }
  },
  "levels": {
    "ema20": 1.234,
    "ema30": 1.228,
    "ema60": 1.215,
    "ema144": 1.198,
    "ema250": 1.175,
    "ema333": 1.160
  }
}
```

### External Decision Making

- **Backtester**: Interprets flags, simulates entries/exits
- **Portfolio Manager**: Reads flags, executes real trades
- **Engine**: Only computes and emits — never decides to trade

---

## Summary: What Changed

### From v2 to v3

**State Detection**:
- v2: Band-based (dsep, ATR, volume clusters)
- v3: EMA hierarchy + tri-window acceleration

**S1 Definition**:
- v2: Complex breakout conditions
- v3: Order break + EMA60 lift (accelerating or steady)

**S2 Definition**:
- v2: Dynamic S/R management with geometry
- v3: Static EMA60-based entry zone (halo = 0.5 * ATR, adaptive)

**S3 Definition**:
- v2: Price > EMA333 (8/10 bars) + momentum
- v3: All EMAs above EMA333 (cleaner, simpler)

**Geometry**:
- v2: Core to S1/S2 state management
- v3: Removed from entries, kept for exits only

**Emergency Exit**:
- v2: Price < EMA333 → immediate S0 transition
- v3: Price < EMA333 → warning flag (separate from S0 reset)

**Fakeout Recovery**:
- v2: Not explicitly modeled
- v3: Price recovery + TI/TS quality check → stay in S3

---

## Testing Checklist

- [ ] S0 → S1: Order break + acceleration detection
- [ ] S1 persistence: 3-bar validation works
- [ ] S1 cancel: Rolling over detection + persistence
- [ ] S1 cancel: Fast band drop detection + persistence
- [ ] S1 cancel blocks S1→S2 during persistence check
- [ ] S1→S2: All entry conditions align correctly
- [ ] S2→S3: All EMAs above 333 transition
- [ ] S2→S0: Fast band crosses back below 60
- [ ] S3 emergency exit: Price < 333 flag emission
- [ ] S3 fakeout: Price recovery + TI/TS gates
- [ ] S3→S0: All EMAs below 333 reset
- [ ] TI/TS computation in S2 and S3
- [ ] OX/DX/EDX computation in S3

---

**Version**: v1  
**Date**: 2025-01-31  
**Status**: Ready for implementation

