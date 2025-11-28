# Uptrend Engine v4 - Specification

## Document Purpose

This specification defines **Uptrend Engine v4**, a clean reimplementation based on lessons learned from v2 and v3. The goal is a **working, testable, maintainable** state machine with proper diagnostics and clear separation of concerns.

**Version History:**
- **v2**: Original production engine (geometry-based S/R, complex S2 management)
- **v3**: EMA Phase System attempt (simplified entry, but diagnostics broken, logic duplicated)
- **v4**: Clean reimplementation with working diagnostics, single source of truth

---

## Architecture Principles

### Signal Emission Model

**The Uptrend Engine emits signals and flags — it does NOT make trading decisions.**

- **Engine responsibility**: Compute state, conditions, quality scores; emit clear signals
- **External responsibility**: Portfolio Manager (production) or Backtester (simulation) interprets flags and executes trades
- **Output format**: Structured payload with state, flags, scores, levels, and **diagnostics**

### Single Source of Truth

- **Engine logic**: Defined once in `uptrend_engine_v4.py`
- **Backtester**: Calls engine methods directly, preserves diagnostics, visualizes results
- **No duplication**: Backtester does NOT reimplement state machine logic

### Diagnostics Requirement

**ALL state transitions and conditions MUST emit diagnostics:**
- Slope values (actual numbers, not just boolean flags)
- Condition checks (entry_zone, slope_ok, ts_ok with values)
- Missing conditions (why entry blocked)
- Diagnostic data persists in JSON output for analysis

---

## Data Sources

### Shared TA Utilities (`ta_utils.py`)

**Single source of truth for all TA calculations:**

- **Location**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_utils.py`
- **Purpose**: Shared functions used by both `ta_tracker.py` (production) and backtesters
- **Critical functions**:
  - `ema_slope_normalized()`: Computes EMA slope as %/bar (matches TA tracker exactly)
  - `ema_series()`: EMA calculation with first-value initialization
  - `atr_series_wilder()`, `adx_series_wilder()`: ATR/ADX calculations
  - `lin_slope()`: Base linear regression (used by normalized slope)

**Why shared utilities?**
- **Prevents drift**: TA tracker and backtester use identical calculations
- **Easier testing**: Test utilities once, validate both production and backtesting
- **Maintenance**: Fix bugs in one place, both systems benefit
- **Consistency guarantee**: Impossible for backtester to diverge from production

**Implementation requirement**:
- `ta_tracker.py` imports from `ta_utils.py` (refactor existing code)
- `backtest_uptrend_v4.py` imports from `ta_utils.py` (no local implementations)
- Both use `ema_slope_normalized()` for all slope calculations

### TA Tracker Integration

**Slopes are read from TA tracker, not computed in the engine:**

- **Source**: `features.ta.ema_slopes` (pre-computed by `ta_tracker.py`)
- **Format**: Normalized as %/bar (already divided by latest EMA value)
- **Window**: 10-bar linear regression
- **Available EMAs**: ema20_slope, ema60_slope, ema144_slope, ema250_slope, ema333_slope
- **Derivatives**: d_ema60_slope, d_ema144_slope, d_ema250_slope, d_ema333_slope (acceleration)

**Why not compute in engine?**
- TA tracker runs continuously, slopes available from before S1
- Ensures consistency between production and backtesting
- Reduces computation overhead in engine

**Backtester simulation**: Uses `ta_utils.ema_slope_normalized()` to match production exactly (no manual normalization needed).

### Geometry (S/R Levels)

**Used for exits and optional entry boost, not required for entry:**
- Source: `features.geometry.levels.sr_levels`
- S3 exits: Geometry context for exit decisions (kept from v2)
- Entry boost: Optional S/R boost up to +0.15 on TS if S/R level within `1.0 * ATR` of EMA60/EMA333

---

## State Machine: Simplified EMA Phase System

### State Flow

```
S0 (Pure Downtrend)
  ↓
S1 (Primer) → Buy Signal (direct, no S2 state)
  ↓
S2 (Defensive - price > EMA333)
  ↓
S3 (Trending - full bullish alignment)
```

**Key simplification from v3:**
- Removed acceleration pattern persistence for S1 entry (was causing late triggers)
- Removed S2 as entry state (buy directly from S1)
- Added S2 as defensive regime when price > EMA333
- S3 only reachable from S2 (not from S0/S1)

---

## State Definitions

### S0: Pure Downtrend

**Definition**: Perfect bearish EMA order (band-based).

**Required Order**:
```
EMA20 < EMA60 AND EMA30 < EMA60  (fast band below mid)
AND
EMA60 < EMA144 < EMA250 < EMA333  (slow descending)
```

**Notes:**
- EMA20 and EMA30 treated as a "fast band" — order between them doesn't matter
- First violation: when fast band (20/30) crosses above EMA60 → transition to S1

**Transition from S0:**
- To S1: `fast_band_above_60 AND price > EMA60` (must come from S0)

**Output payload:**
```json
{
  "state": "S0",
  "flag": {"watch_only": true},
  "scores": {},
  "diagnostics": {}
}
```

**Kept from v2/v3**: Band-based order check (v3 improvement)

---

### S1: Primer (First Disorder)

**Definition**: Fast band above EMA60, price above EMA60, ready for entry.

**Entry Conditions**:
1. `EMA20 > EMA60 AND EMA30 > EMA60` (fast band above 60)
2. `Price > EMA60`
3. Must come from S0 OR S2 (S2 → S1 when price drops below EMA333)

**Key Simplification from v3:**
- ❌ **Removed**: Acceleration pattern detection (S1.A/S1.B)
- ❌ **Removed**: 3-bar persistence requirement
- ✅ **New**: Can come from S0 or S2 (S2→S1 flip-flop expected when price < EMA333)
- ✅ **New**: Flip-flopping between S0/S1 is expected and acceptable

**Purpose**: Looking for entries at EMA60 when buy conditions are met.

**Exit from S1:**
- To S0: `fast_band_at_bottom` (immediate, no persistence, EXITS POSITION)
  - Condition: `EMA20 < min(EMA60, EMA144, EMA250, EMA333) AND EMA30 < min(EMA60, EMA144, EMA250, EMA333)`
- To S2: `price > EMA333` (from S1 only, not an exit - just flip-flop between entry levels)

**Important**: Until S3 is reached, the ONLY exit condition is fast band at bottom. S1→S2 is NOT an exit, just switching between entry levels (EMA60 vs EMA333).

**Output payload (always includes diagnostics):**
```json
{
  "state": "S1",
  "flag": {
    "s1_valid": true,
    "buy_signal": true/false
  },
  "scores": {
    "ts": 0.0-1.0,
    "ts_with_boost": 0.0-1.0
  },
  "diagnostics": {
    "buy_check": {
      "entry_zone": true/false,
      "slope_ok": true/false,
      "ts_ok": true/false,
      "ema60_slope": 0.00316,  // Actual value from TA tracker
      "ema144_slope": 0.00133   // Actual value from TA tracker
    }
  }
}
```

**CRITICAL**: Diagnostics MUST be populated on every S1 state, even when buy_signal is false.

---

### Buy Signal (from S1)

**Definition**: Entry conditions met while in S1. State remains S1.

**Entry Conditions** (ALL must be true):
1. **Entry Zone**: `abs(price - EMA60) ≤ 1.0 * ATR`
   - Halo = `1.0 * ATR` (dynamic, not fixed 3%)
2. **Slope OK**: `EMA60_slope > 0.0 OR EMA144_slope >= 0.0`
   - Slopes from TA tracker (10-bar %/bar, already normalized)
   - At least one EMA rising
3. **TS Gate**: `TS + S/R boost >= 0.58`
   - Base TS: computed from RSI slope + ADX slope (from v2/v3)
   - S/R boost: Optional +0.15 max if S/R level within `1.0 * ATR` of EMA60
   - Boost not required (just nice-to-have)

**Removed from v2/v3:**
- ❌ TI (Trend Integrity) - was too slow, removed as entry filter
- ❌ Acceleration patterns
- ❌ Price > EMA60 requirement (removed - can dip below and still buy if in S1)

**Kept from v2/v3:**
- ✅ TS calculation method (RSI + ADX sigmoid)
- ✅ S/R boost logic (optional, not required)
- ✅ Entry zone halo = 1.0 * ATR (v3 improvement from 0.5 * ATR)

**Output flag**: `buy_signal: true` (state remains "S1")

---

### S2: Defensive Regime

**Definition**: Price above EMA333, but not yet full bullish alignment. Defensive position management.

**Entry Conditions**:
- `price > EMA333`
- Must come from S1 (or S2→S1→S2 flip-flop scenario)

**Note**: S2 can also re-enter from S1 after a price drop below EMA333. This is expected flip-flopping between entry levels.

**Exit from S2:**
- To S1: `price < EMA333` (flip-flop back to EMA60 entry level, NOT an exit)
- To S0: `fast_band_at_bottom` (global exit precedence, EXITS POSITION)
- To S3: `full_bullish_alignment` (see S3 definition)

**Purpose**: Looking for exits at expansion (OX trims) and entries at EMA333 (retest buys). Switching between S1 and S2 based on price relative to EMA333 is expected flip-flopping - both are active trading states.

**S2 Behaviors:**

1. **Trim Flags** (pump trims):
   - Reuse S3's OX calculation
   - Emit `trim_flag: true` when `OX >= 0.65`
   - Purpose: Reduce risk, compound position on pumps

2. **Retest Buy Flags** (at EMA333):
   - Entry zone: `abs(price - EMA333) ≤ 1.0 * ATR`
   - Slope OK: `EMA250_slope > 0.0 OR EMA333_slope >= 0.0`
   - TS gate: `TS + S/R boost >= 0.58`
   - S/R boost: Anchored to EMA333 (same halo = 1.0 * ATR)
   - Emit `buy_flag: true` (state remains S2)

**No fakeout handling in S2** (simplified from S3)

**Important Distinction**: 
- **S1**: Active trading state - looking for entries at EMA60
- **S2**: Active trading state - looking for exits at expansion (OX trims) and entries at EMA333 (retest buys)
- **S1↔S2 flip-flop**: Expected behavior based on price relative to EMA333 - NOT exits, just switching entry levels
- **Only exit until S3**: Fast band at bottom (global precedence)

**Output payload:**
```json
{
  "state": "S2",
  "flag": {
    "defensive": true,
    "trim_flag": true/false,
    "buy_flag": true/false,
    "entry_zone_333": true/false
  },
  "scores": {
    "ox": 0.0-1.0,
    "ts": 0.0-1.0,
    "ts_with_boost": 0.0-1.0
  },
  "diagnostics": {
    "s2_retest_check": {
      "entry_zone_333": true/false,
      "slope_ok_333": true/false,
      "ts_ok": true/false,
      "ema250_slope": 0.0,
      "ema333_slope": 0.0
    }
  }
}
```

**New in v4**: S2 as defensive regime (concept from v3, but clarified here)

---

### S3: Trending (Full Bullish Alignment)

**Definition**: All EMAs above EMA333, full bullish order.

**Entry Conditions** (from S2 only):
- Must come from S2
- Full bullish alignment (band-based):
  ```
  EMA20 > EMA60 AND EMA30 > EMA60  (fast band above mid)
  AND
  EMA60 > EMA144 > EMA250 > EMA333  (slow ascending)
  ```

**Kept from v2/v3:**
- ✅ OX/DX/EDX calculations (these were working well)
- ✅ Emergency exit: `price < EMA333` (immediate, single close)
- ✅ Fakeout recovery: Price reclaims above EMA333 + TI >= 0.60 AND TS >= 0.58
- ✅ S3→S0 reset: ALL EMAs (20, 30, 60, 144, 250) break below EMA333
- ✅ Geometry context for exits (from v2)

**Removed from v2/v3:**
- ❌ TI as entry filter (still computed for fakeout recovery)

**Output payload:**
```json
{
  "state": "S3",
  "flags": {
    "trending": true,
    "dx_flag": true/false,
    "emergency_exit": {
      "active": true/false,
      "reason": "price_below_ema333"
    },
    "fakeout_recovery": true/false
  },
  "scores": {
    "ox": 0.0-1.0,
    "dx": 0.0-1.0,
    "edx": 0.0-1.0,
    "ti": 0.0-1.0,
    "ts": 0.0-1.0
  },
  "sr_context": {
    "halo": 0.0,
    "base_sr_level": 0.0,
    "flipped_sr_levels": []
  }
}
```

---

## Global Exit Precedence

**Fast Band at Bottom Exit** (overrides all states):
- Condition: `EMA20 < min(EMA60, EMA144, EMA250, EMA333) AND EMA30 < min(EMA60, EMA144, EMA250, EMA333)`
- Action: Exit to S0 immediately, exit position
- No persistence required
- Applies to S1, S2, S3

**Kept from v3**: Global exit logic

---

## Score Calculations

### TI/TS (Trend Integrity / Trend Strength)

**Purpose**: Entry quality gates (TS primary, TI for fakeout recovery only)

**TS Calculation** (kept from v2/v3):
```
rsi_term = sigmoid(rsi_slope_10, k=0.5)
adx_term = sigmoid(adx_slope_10, k=0.3) if adx >= 18 else 0.0
trend_strength = 0.6 * rsi_term + 0.4 * adx_term
```

**S/R Boost** (optional, not required):
- Check if S/R level within `1.0 * ATR` of anchor (EMA60 for S1, EMA333 for S2)
- Boost = `min(0.15, (sr_strength / 20.0) * 0.15)`
- Applied to TS: `ts_with_boost = min(1.0, ts_base + boost)`

**TI Calculation** (kept from v2/v3, used for fakeout recovery only):
- Support persistence (EMA60-based, last 3 bars)
- EMA alignment score
- Volatility coherence
- `trend_integrity = 0.55 * support_persistence + 0.35 * ema_alignment + 0.10 * volatility_coherence`

**Changes from v3:**
- ❌ TI removed as entry filter (was 0.45 threshold)
- ✅ TS threshold: 0.58 (kept from v3)
- ✅ S/R boost moved to TS (not TI)

### OX/DX/EDX (S3 Regime Management)

**Kept from v2/v3** (these were working well):
- **OX**: Overextension score (rail separation, expansion, ATR surge, fragility)
- **DX**: Deep Zone score (location, exhaustion, relief, curl)
- **EDX**: Expansion Decay score (slow down, structure failure, participation decay, volatility disorder)

**Thresholds**:
- OX_SELL_THRESHOLD: 0.65 (trim flags in S2 and S3)
- DX_BUY_THRESHOLD: 0.65 (buy flags in S3 deep zones)

**Reused in S2**: OX calculation for trim flags (from v3)

---

## Bootstrap Logic

**Initial State Determination (no previous state):**

When the engine starts with no previous state history, we can only confidently bootstrap to clear trends:

1. **Bootstrap to S3**: If all EMAs above EMA333 (full bullish trend)
2. **Bootstrap to S0**: If perfect bearish order (full bearish trend)
3. **Otherwise**: No state assigned (or "S4" / "no_state" for clarity) - wait until clear trend emerges

**Rationale**: 
- S1 and S2 are transition/trading states that require context (where did we come from?)
- Without history, we can't know if we're entering mid-transition
- Only clear trends (S0 downtrend or S3 uptrend) can be bootstrapped with confidence
- It's fine to have "no state" until S0 or S3 is reached - this means we're in noise, not a clear trend

**Implementation**: If bootstrapping doesn't yield S0 or S3, emit `state: null` or `state: "S4"` with `watch_only: true` until a clear trend emerges.

---

## Implementation Notes

### Payload Builder

**Every payload MUST include diagnostics when relevant:**
- S1: Always include `buy_check` diagnostics (even when buy_signal false)
- S2: Include `s2_retest_check` diagnostics
- S3: Include OX/DX/EDX component diagnostics

**Diagnostics structure:**
```json
{
  "diagnostics": {
    "buy_check": {
      "entry_zone": true/false,
      "slope_ok": true/false,
      "ts_ok": true/false,
      "ema60_slope": 0.00316,      // Actual value
      "ema144_slope": 0.00133,      // Actual value
      "ts_score": 0.45,
      "ts_with_boost": 0.60
    }
  }
}
```

### Backtester Requirements

**Backtester v4 MUST:**
1. Call engine methods directly (no duplicate logic)
2. Preserve all diagnostics in JSON output
3. Visualize diagnostics in charts (slope values, condition checks)
4. Show TS threshold markers at 0.0, 0.3, 0.6, 0.9, 0.58

**Backtester MUST NOT:**
- Reimplement state machine logic
- Override or strip diagnostics
- Compute slopes differently than TA tracker

### Testing Requirements

**Must verify:**
1. Slopes are positive when EMAs are rising
2. Diagnostics populated for all S1 states
3. Buy signals trigger when all conditions met
4. TS threshold markers appear correctly in charts
5. No empty diagnostics `{}` in JSON output

---

## What's New in v4

### New Concepts
1. **S2 as defensive regime** (clarified from v3)
2. **Buy signal directly from S1** (no separate S2 entry state)
3. **Diagnostics requirement** (must be populated, not optional)
4. **Single source of truth** (backtester calls engine, no duplication)

### Simplified from v3
1. **S1 entry**: Removed acceleration patterns, removed persistence (was causing late triggers)
2. **S0/S1 flip-flopping**: Now expected and acceptable (removed persistence requirements)
3. **TI entry gate**: Removed (was too slow)
4. **Entry zone**: Fixed at 1.0 * ATR (not 0.5 * ATR)

### Kept from v2/v3
1. **OX/DX/EDX calculations** (v2, working well)
2. **TS calculation method** (v2/v3)
3. **Emergency exit logic** (v2/v3)
4. **Fakeout recovery** (v2/v3)
5. **Geometry for exits** (v2)
6. **Band-based EMA order** (v3 improvement)
7. **Fast band at bottom exit** (v3)
8. **TA tracker slopes** (v4: uses `ta_utils.ema_slope_normalized()`, single source of truth)

---

## Migration Notes

### From v3 to v4

**What breaks:**
- v3's `analyze_single()` logic (will be replaced with direct engine calls)
- v3's acceleration pattern detection (removed)
- v3's S1 persistence (removed)

**What works:**
- TA data format (same)
- Geometry format (same)
- OX/DX/EDX calculations (reuse code)
- TI/TS calculations (reuse code, adjust thresholds)

**Migration path:**
1. Create v4 engine with clean state machine
2. Reuse v2/v3 calculation methods (OX/DX/EDX, TI/TS)
3. Create v4 backtester that calls engine directly
4. Test side-by-side with v3 results

---

## Quick Reference: Entry/Exit Conditions

### Entry Conditions Summary

**S0 → S1:**
- Fast band above 60: `EMA20 > EMA60 AND EMA30 > EMA60`
- Price above 60: `price > EMA60`
- Must come from S0 OR S2 (S2→S1 when price drops below EMA333)

**S2 → S1:**
- `price < EMA333` (flip-flop, not an exit - switching from EMA333 entry level back to EMA60 entry level)

**S1 → Buy Signal:**
- Entry zone: `abs(price - EMA60) ≤ 1.0 * ATR`
- Slope OK: `EMA60_slope > 0.0 OR EMA144_slope >= 0.0` (from TA tracker)
- TS gate: `TS + S/R boost >= 0.58`

**S1 → S2:**
- `price > EMA333`
- Must come from S1

**S2 → S3:**
- Full bullish alignment: `EMA20 > EMA60 AND EMA30 > EMA60 AND EMA60 > EMA144 > EMA250 > EMA333`
- Must come from S2

### Exit Conditions Summary

**S1 → S0:**
- Fast band at bottom: `EMA20 < min(EMA60, EMA144, EMA250, EMA333) AND EMA30 < min(...)`
- Immediate (no persistence)
- **EXITS POSITION** (only exit condition until S3)

**S2 → S1:**
- `price < EMA333`
- **NOT an exit** - just flip-flopping between entry levels (EMA333 → EMA60)
- Expected behavior, both are active trading states

**S2 → S0:**
- Fast band at bottom (same as S1→S0)
- Global precedence (exits position)

**S3 → S0:**
- All EMAs below 333: `EMA20 < EMA333 AND EMA30 < EMA333 AND EMA60 < EMA333 AND EMA144 < EMA333 AND EMA250 < EMA333`

**S3 Emergency Exit:**
- `price < EMA333` (flag only, doesn't change state)

---

## Open Questions / Future Improvements

1. **S1 acceleration patterns**: Removed for simplicity, but could be added back as optional enhancement if needed
2. **S2 entry bonus**: Should we add S/R boost for S2 entry (like S1 has)?
3. **TS threshold tuning**: 0.58 works, but could be parameterized for testing
4. **Diagnostics visualization**: Could add more granular condition markers in charts

---

## References

- **v2 Spec**: `docs/trencher_improvements/PM/OG/SM_UPTREND.MD`
- **v3 Spec**: `docs/trencher_improvements/PM/ema_pulse/EMA_Phase_Spec_v1.md`
- **EMA Pulse Concept**: `docs/trencher_improvements/PM/ema_pulse/ema_pulse_and_acceleration_v1.md`

