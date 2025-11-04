# Uptrend Engine V6 Specification

## Overview

Uptrend Engine V6 implements the **new EDX design** (3-window S3-relative approach) with proper backtester support. V6 fixes the implementation issues from V4 while keeping the advanced EDX calculation that measures long-term trend health.

**Key Fix**: All database access methods properly respect backtester time filters, ensuring EDX calculation works identically in production and backtest contexts.

## Core Principles

1. **Signal Emission**: Engine emits flags/signals; Portfolio Manager makes trading decisions
2. **Single Source of Truth**: All TA calculations from `ta_tracker.py` via `ta_utils.py`
3. **New EDX Design**: 3-window S3-relative approach for measuring trend decay
4. **Backtester Compatibility**: All engine methods work identically in production and backtest contexts
5. **Proper Time Filtering**: All database queries respect `target_ts` in backtest context

## State Machine

```
S0 (Bearish) → S1 (Primer) → Buy Signal → S2 (Defensive) → S3 (Trending)
     ↑                              ↓                           ↓
     └────────── Global Exit ───────┴──────────────────────────┘
```

### State Definitions

#### S0: Bearish Regime
**Definition**: Perfect bearish EMA order (band-based)
- `EMA20 < EMA60` AND `EMA30 < EMA60` (fast band below mid)
- `EMA60 < EMA144 < EMA250 < EMA333` (slow descending)

**Entry**: Bootstrap or from any state via Global Exit

**Exit to S1**: `EMA20 > EMA60` AND `EMA30 > EMA60` AND `Price > EMA60`

**No entries, no trims** - just waiting for reversal

---

#### S1: Primer (Entry Zone at EMA60)
**Definition**: Fast band above EMA60, price above EMA60
- `EMA20 > EMA60` AND `EMA30 > EMA60` (fast band above mid)
- `Price > EMA60`

**Entry**: From S0 or S2 (when `price < EMA333`)

**Exit to S0**: Global Exit (`fast_band_at_bottom`)

**Exit to S2**: `price > EMA333` (flip-flop, not an exit)

**Buy Signal** (emits `buy_flag = true`, state remains S1):
- **Entry Zone**: `abs(price - EMA60) <= 1.0 * ATR`
- **Slope OK**: `EMA60_slope > 0.0 OR EMA144_slope >= 0.0` (from TA tracker, normalized %/bar)
- **TS Gate**: `TS + S/R_boost >= 0.58`
  - TS computed from EMA alignment, momentum, volume
  - S/R boost: +0.15 max if price within 1×ATR of S/R level near EMA60

**Diagnostics**: MUST populate `buy_check` diagnostics on every S1 state

---

#### Buy Signal (from S1)
**Type**: Flag emission (not a state)
**Emitted when**: All S1 buy signal conditions met
**State remains**: S1
**Purpose**: Portfolio Manager decides when to actually enter

---

#### S2: Defensive Regime (Entry Zone at EMA333)
**Definition**: Price above EMA333, but not full bullish alignment

**Entry**: From S1 when `price > EMA333`

**Exit to S1**: `price < EMA333` (flip-flop, not an exit)

**Exit to S0**: Global Exit (`fast_band_at_bottom`)

**Exit to S3**: `full_bullish_alignment` (band-based)

**Behaviors**:
1. **Trim Flags** (emits `trim_flag = true`, state remains S2):
   - `OX >= 0.65` AND `price within 1×ATR of S/R level`
   - OX computed using simple rails/expansion/fragility (no EDX needed for S2)
   
2. **Retest Buy Flags** (emits `buy_flag = true`, state remains S2):
   - **Entry Zone**: `abs(price - EMA333) <= 0.5 * ATR`
   - **Slope OK**: `EMA250_slope > 0.0 OR EMA333_slope >= 0.0`
   - **TS Gate**: `TS + S/R_boost >= 0.58` (S/R boost anchored to EMA333)

**No fakeout handling in S2**

---

#### S3: Trending (Full Bullish Alignment)
**Definition**: All EMAs above EMA333, full bullish order
- `EMA20 > EMA60` AND `EMA30 > EMA60` (fast band above mid)
- `EMA60 > EMA144 > EMA250 > EMA333` (slow ascending)

**Entry**: From S2 only (via `full_bullish_alignment`)
- **CRITICAL**: On S2→S3 transition, record `s3_start_ts` in `features.uptrend_engine_v6_meta.s3_start_ts`
- This timestamp is used for EDX's 3-window calculation

**Exit to S0**: All EMAs below EMA333 (global bearish reset)
- On S3→S0 exit, clear `s3_start_ts` from metadata

**Behaviors**:
1. **Trim Flags** (emits `trim_flag = true`, state remains S3):
   - `OX >= 0.65` AND `price within 1×ATR of S/R level`
   - OX computed with EDX boost (see EDX section)

2. **DX Buy Signals** (emits `buy_flag = true`, state remains S3):
   - **DX Threshold**: `DX >= threshold` (see EDX sliding scale below)
   - **Price Position**: `price <= EMA144` (discount zone)
   - **Slope OK**: `EMA250_slope > 0.0 OR EMA333_slope >= 0.0`
   - **TS Gate**: `TS + S/R_boost >= 0.58`
   - **EDX Suppression**: DX threshold adjusted based on EDX score (see below)

3. **Emergency Exit** (emits `emergency_exit_flag = true`, state remains S3):
   - `price < EMA333`
   - Flag only, no state change
   - Portfolio Manager decides on action

---

### Global Exit Precedence

**Fast Band at Bottom**: Overrides ALL states, exits position
- Condition: `EMA20 < min(EMA60, EMA144, EMA250, EMA333)` AND `EMA30 < min(EMA60, EMA144, EMA250, EMA333)`
- Immediate exit to S0
- Exits position (`exit_position = true`)

---

## Score Calculations

### OX (Overextension) - Used in S2 and S3
**Purpose**: Measure price extension from EMAs

**Components**:
- Rail scores (distance from EMA20/60/144/250, sigmoid normalized)
- Expansion (EMA separation rates)
- ATR surge (current vs mean)
- Fragility (EMA20 slope inversion)

**Formula**: Weighted sum, clamped 0-1

**S2 OX**: Base formula only (no EDX boost)

**S3 OX**: Base formula + EDX boost
- `ox_base = weighted_sum(...)`
- `edx_boost = max(0.0, min(0.5, edx - 0.5))`
- `ox = ox_base * (1.0 + 0.33 * edx_boost)`
- Higher EDX = more overextension risk

**Threshold**: `OX >= 0.65` for trim flags

---

### DX (Deep Zone) - Used in S3
**Purpose**: Measure price position in EMA144-EMA333 hallway

**Components**:
- Location score: `exp(-3.0 * x)` where `x = (price - EMA333) / (EMA144 - EMA333)`
- Compression multiplier: Higher when EMA band is tight
- Curl/relief: Momentum and exhaustion patterns

**Formula**: Combined score, clamped 0-1

**EDX Sliding Scale** (affects DX buy threshold):
- **EDX >= 0.7**: `dx_threshold = 0.65 + 0.15 = 0.80` (high decay regime, require higher DX)
- **EDX 0.5-0.7**: `dx_threshold = 0.65 + (edx - 0.5) * 0.5` (linear from 0.65 to 0.80)
- **EDX < 0.5**: `dx_threshold = 0.65` (base threshold)

**Price Position Boost** (additional adjustment):
- Buying power highest near EMA333 (retest zone)
- Decreases as price moves toward EMA144
- Adjustment: `±0.10` based on position within band

**Final DX Buy Check**:
- `dx >= dx_threshold_adjusted` AND `price <= EMA144` AND `slope_ok` AND `ts_ok`

---

### EDX (Expansion Decay Index) - Used in S3
**Purpose**: Measure long-term trend health using 3-window S3-relative approach

**Key Innovation**: Measures decay across three time windows relative to S3 start, not just recent bars.

#### Window Calculation
Windows are calculated based on S3 duration:
- **Window 1 (Full)**: Since S3 start (all bars since entry to S3)
- **Window 2 (2/3)**: Last 2/3 of S3 duration
- **Window 3 (1/3)**: Last 1/3 of S3 duration (most recent)

**Minimum Requirements**:
- Window 1: Minimum 9 bars (otherwise return fallback EDX = 0.5)
- Window 2: Minimum 6 bars (if S3 duration < 9 bars, window 2 = None)
- Window 3: Minimum 3 bars (if S3 duration < 6 bars, window 3 = None)

#### Components (Each Computed for All 3 Windows)

**1. Slow-Field Momentum (30% weight)**:
- EMA250/333 slopes (normalized %/bar)
- RSI trend (slope of RSI over window)
- ADX trend (slope of ADX over window)
- Higher score = weakening momentum

**2. Structure Failure (25% weight)**:
- ZigZag HH/HL ratio over window
- Uses ATR-adaptive swing detection
- Higher score = more structure breakdown (lower highs, lower lows)

**3. Participation Decay (20% weight)**:
- AVWAP (Anchored Volume-Weighted Average Price) slope over window
- AVWAP = cumulative VWAP since S3 start
- Negative or flattening slope = participation decay

**4. EMA Structure Compression (10% weight)**:
- EMA144-333 separation trend
- EMA250-333 separation trend
- Compression (negative separation slope) = decay

**Removed Components**:
- ❌ Volatility Disorder (removed - too noisy)

#### Window Comparison Logic
For each component, compare scores across windows:
- **Decay Pattern**: w3 > w2 > w1 (all increasing = decay accelerating)
- **Stable Pattern**: w1 ≈ w2 ≈ w3 (stable trend health)
- **Improving Pattern**: w1 > w2 > w3 (trend strengthening)

**Decay Score Calculation**:
```python
if all 3 windows available:
    if w3 > w2 > w1:  # Decay accelerating
        decay = 0.2*w1 + 0.3*w2 + 0.5*w3  # Weight recent more
    elif w2 > w1:  # Recent weakening
        decay = 0.3*w1 + 0.7*w2
    else:  # Stable or improving
        decay = (w1 + w2) / 2.0
elif 2 windows available:
    if w2 > w1:
        decay = 0.3*w1 + 0.7*w2
    else:
        decay = (w1 + w2) / 2.0
else:  # Only window 1
    decay = w1
```

#### Final EDX Score
```python
edx = (
    0.30 * slow_decay +
    0.25 * struct_decay +
    0.20 * part_decay +
    0.10 * comp_decay
)
edx = max(0.0, min(1.0, edx))
```

#### Fallback EDX
If S3 start timestamp is missing or insufficient bars:
- Use fallback calculation (simpler, single-window approach)
- Return EDX = 0.5 (neutral)
- Set `diagnostics.fallback = true`

#### Diagnostics
EDX diagnostics include:
- Component decay scores: `edx_slow`, `edx_struct`, `edx_part`, `edx_geom`
- Window sizes: `window1_bars`, `window2_bars`, `window3_bars`
- Individual window scores: `w1_slow`, `w2_slow`, `w3_slow`, etc.
- Fallback flag: `fallback: true/false`

---

### TS (Trend Strength) - Used in S1, S2, S3
**Purpose**: Measure trend health and momentum

**Components**:
- EMA alignment score
- Momentum indicators (RSI/ADX trends)
- Volume participation
- Price structure (swing patterns)

**Formula**: Weighted combination, clamped 0-1

**Gate**: `TS + S/R_boost >= 0.58` for all buy signals

**S/R Boost**: +0.15 max if price within 1×ATR of relevant S/R level
- S1: S/R near EMA60
- S2: S/R near EMA333
- S3: S/R near EMA144 or EMA333

---

## Data Sources

### TA Tracker Integration
- **EMA Values**: `ta.ema.ema20`, `ema30`, `ema60`, `ema144`, `ema250`, `ema333`
- **EMA Slopes**: `ta.ema_slopes.ema60_slope`, `ema144_slope`, etc. (normalized %/bar, 10-bar linear regression)
- **ATR**: `ta.atr.atr_1h`
- **Momentum**: `ta.momentum.rsi_1h`, `adx_1h`
- **Separations**: `ta.separations.dsep_fast_5`, `dsep_mid_5`

**All from `ta_tracker.py` via `ta_utils.py`** - single source of truth

### Geometry Integration
- **S/R Levels**: From `features.geometry.sr_levels` (built by `geometry_build_daily.py`)
- Used for:
  - TS S/R boost calculation
  - Trim flag S/R halo check

### OHLC Data for EDX
- **Source**: `_fetch_ohlc_since(contract, chain, s3_start_ts, limit=500)`
- **CRITICAL**: Must respect backtester time filter (`lte("timestamp", target_ts)`)
- **Purpose**: Calculate AVWAP, ZigZag, EMA separations over S3 windows

---

## Implementation Notes

### Bootstrap Logic
**On first run** (no previous state):
- If `full_bullish_alignment`: Bootstrap to S3
  - **CRITICAL**: Record `s3_start_ts` in `features.uptrend_engine_v6_meta.s3_start_ts`
- Else if `perfect_bearish_order`: Bootstrap to S0
- Else: "No State" (S4) - watch only until clear trend emerges

### S3 Start Timestamp Management
**Recording**:
- On S2→S3 transition: Record current timestamp as `s3_start_ts`
- On bootstrap to S3: Record current timestamp as `s3_start_ts`

**Clearing**:
- On S3→S0 exit: Clear `s3_start_ts` from metadata

**Usage**:
- EDX calculation uses `s3_start_ts` to determine window boundaries
- If missing, EDX falls back to simple calculation

### State Persistence
- Previous state read from `features.uptrend_engine_v6.state`
- New state written to `features.uptrend_engine_v6` after each evaluation
- Backtester maintains same structure in memory

### Signal Emission
All signals are **flags** in the payload, not state changes:
- `buy_flag: true` - Entry opportunity detected
- `trim_flag: true` - Overextension + S/R proximity detected
- `emergency_exit_flag: true` - Price broke below EMA333 in S3

**Portfolio Manager decides** on actual trading actions based on these flags.

### Diagnostics Requirement
Every payload MUST include comprehensive diagnostics:
- **S1**: `diagnostics.buy_check` (entry_zone_ok, slope_ok, ts_ok, slopes, scores)
- **S2**: `diagnostics.s2_retest_check`, `scores.ox`
- **S3**: `diagnostics.s3_buy_check`, `scores.ox`, `scores.dx`, `scores.edx`, `diagnostics.edx_*`

---

## Backtester Requirements

### Time Filtering (CRITICAL)
All data access methods must respect `target_ts`:
- `_latest_close_1h()`: `lte("timestamp", target_ts)`
- `_fetch_recent_ohlc()`: `lte("timestamp", target_ts)`
- `_fetch_ohlc_since()`: `gte("timestamp", since) AND lte("timestamp", target_ts)` ⚠️ **CRITICAL FIX**

### Method Overrides
Backtester must override:
1. `_latest_close_1h()` - filter by target_ts
2. `_fetch_recent_ohlc()` - filter by target_ts
3. `_fetch_ohlc_since()` - filter by target_ts ⚠️ **THIS WAS MISSING IN V4**

### State Machine Alignment
Backtester's `analyze_single()` must **directly call engine methods**:
- Use same state transition logic
- Call `_check_buy_signal_conditions()` directly
- Call `_compute_ox_only()` for S2
- Call `_compute_s3_scores()` for S3 (includes EDX calculation)
- Pass `current_ts=target_ts.isoformat()` to `_compute_s3_scores()` for EDX

### S3 Start Timestamp in Backtester
**On S2→S3 transition**:
- Set `features["uptrend_engine_v6_meta"]["s3_start_ts"] = target_ts.isoformat()`

**On bootstrap to S3**:
- Set `features["uptrend_engine_v6_meta"]["s3_start_ts"] = target_ts.isoformat()`

**On S3 stay**:
- Ensure `s3_start_ts` is set (if missing, set to current `target_ts`)

**No database writes** - just store in features dict for next iteration

---

## Key Fixes from V4

### Fixed Issues
1. **`_fetch_ohlc_since()` time filter**: Now properly filters by `target_ts` in backtester
2. **S3 start timestamp**: Properly recorded and passed to EDX calculation
3. **Backtester EDX**: Now receives `current_ts` parameter to avoid database calls
4. **Window boundaries**: Correctly calculated from S3 start timestamp in backtester context

### Kept from V4
1. **3-window EDX design**: All components and logic preserved
2. **EDX sliding scale**: DX threshold adjustment based on EDX score
3. **S2 OX-only**: Simple OX calculation for S2 (no EDX needed)
4. **State machine flow**: Proven logic unchanged

---

## Quick Reference

### Entry Conditions
- **S1 Buy**: Entry zone + Slope OK + TS >= 0.58
- **S2 Retest Buy**: Entry zone (0.5×ATR) + Slope OK + TS >= 0.58
- **S3 DX Buy**: DX >= threshold (adjusted by EDX) + Price <= EMA144 + Slope OK + TS >= 0.58

### Exit Conditions
- **Global Exit**: Fast band at bottom (overrides all)
- **S3→S0**: All EMAs below EMA333
- **Emergency Exit** (flag only): Price < EMA333 in S3

### Trim Conditions
- **S2 Trim**: OX >= 0.65 AND price within 1×ATR of S/R level
- **S3 Trim**: OX (with EDX boost) >= 0.65 AND price within 1×ATR of S/R level

### EDX Usage
- **OX Boost**: Higher EDX = higher OX (more extension risk)
- **DX Suppression**: Higher EDX = higher DX threshold (less buying power)
- **Diagnostics**: Full window-by-window breakdown for analysis

---

## File Structure

```
src/intelligence/lowcap_portfolio_manager/jobs/
  ├── uptrend_engine_v6.py          # Main engine (extends base UptrendEngine)
  └── ta_utils.py                   # Shared TA utilities (reused)

backtester/v6/code/
  ├── backtest_uptrend_v6.py        # Backtest engine (extends UptrendEngineV6)
  ├── run_backtest.py               # Single backtest runner
  ├── run_batch_backtest.py         # Batch backtest runner
  └── README.md                     # Backtest documentation
```

---

## Migration Notes

### From V4 to V6
1. **Fix `_fetch_ohlc_since()` in backtester**: Add `lte("timestamp", target_ts)` filter
2. **Ensure S3 start timestamp**: Properly record on S2→S3 and bootstrap
3. **Pass current_ts to EDX**: Backtester passes `target_ts.isoformat()` to `_compute_s3_scores()`
4. **Verify window calculations**: EDX windows calculated correctly from S3 start in backtest context

### Testing Checklist
- [ ] S1→Buy Signal works
- [ ] S2 trim flags trigger correctly
- [ ] S2 retest buys trigger correctly
- [ ] S2→S3 transition works (s3_start_ts recorded)
- [ ] S3 EDX calculates correctly (3 windows, all components)
- [ ] S3 trim flags trigger correctly (OX with EDX boost)
- [ ] S3 DX buys trigger correctly (with EDX sliding scale)
- [ ] S3→S0 exit works (s3_start_ts cleared)
- [ ] Global exit (fast band at bottom) works from all states
- [ ] Backtest runs full duration without crashes
- [ ] Backtest EDX matches production EDX (same windows, same scores)
- [ ] Backtest results match production logic

---

## Future Considerations

### Potential Enhancements
1. **EDX Smoothing**: EMA smoothing of EDX raw score (deferred if needed)
2. **Emergency Exit Recovery**: Fakeout detection logic (deferred to V7 if needed)
3. **EDX Visualization**: Chart plotting of EDX and component breakdowns

### Performance
- EDX calculation is O(N) where N = S3 duration (typically < 500 bars)
- Database queries in EDX are bounded (limit=500)
- All TA from pre-computed tracker (no redundant calculations)

---

**Version**: 6.0  
**Last Updated**: 2025-01-03  
**Status**: Spec Complete - New EDX Design with Proper Backtester Support
