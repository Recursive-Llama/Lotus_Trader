# Regime Engine Implementation Plan

**Status**: Planning  
**Last Updated**: 2024-01-15  
**Reference**: `docs/inprogress/Regime_engine.md`

---

## Executive Summary

**What We're Building**: A regime-driven A/E scoring system that uses Uptrend Engine states instead of string-based phases.

**Key Insight**: We're NOT building a separate "Regime Engine" state machine. Instead:
- We reuse **Uptrend Engine** (no changes) to compute states for regime drivers
- We add a small **Regime Mapper** layer to convert states → ΔA/ΔE deltas
- We modify **compute_levers()** to use regime state instead of phases

**Key Changes:**
- Remove: `cut_pressure`, `age boost`, `market cap boost`, string phase names (`dip`, `good`, `euphoria`)
- Add: Regime-driven A/E computation using Uptrend Engine states (S0/S1/S2/S3)
- Keep: Intent deltas (capped at 0.4)

**Architecture (5 Components)**:
1. **Regime Price Collector** → computes composite OHLC data (ALT, buckets, dominance)
2. **Regime TATracker** → computes TA for regime drivers (reuses existing TA logic)
3. **Uptrend Engine** → computes states/flags/scores (NO CHANGES - works as-is)
4. **Regime Mapper** → maps Uptrend Engine states → ΔA/ΔE deltas (NEW, small module)
5. **Modified compute_levers()** → reads regime state, applies weights, sums contributions

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Data Model](#data-model)
3. [State/Flag/Transition Tables](#stateflagtransition-tables)
4. [Weighting System](#weighting-system)
5. [Implementation Components](#implementation-components)
6. [Database Schema](#database-schema)
7. [Integration Points](#integration-points)
8. [Testing Strategy](#testing-strategy)
9. [Migration Plan](#migration-plan)
10. [Open Questions](#open-questions)

---

## 1. Architecture Overview

### 1.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────┐
│ Regime Price Collector (NEW)                          │
│ - Computes ALT composite OHLC                          │
│ - Computes bucket composite OHLC (nano/small/mid/big)  │
│ - Converts dominance → OHLC                            │
│ - Writes to regime_price_data_ohlc                     │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ Regime TATracker (EXTEND existing)                     │
│ - Computes TA for regime driver "positions"            │
│ - Reads from regime_price_data_ohlc                     │
│ - Writes features.ta to regime positions               │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ Uptrend Engine (NO CHANGES)                            │
│ - Runs on regime driver positions                       │
│ - Reads features.ta                                    │
│ - Computes state/flags/scores                          │
│ - Writes features.uptrend_engine_v4                     │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ Regime Mapper (NEW)                                    │
│ - Reads features.uptrend_engine_v4                     │
│ - Maps state → ΔA_base, ΔE_base                        │
│ - Adds flag deltas (buy/trim/rebuy)                    │
│ - Adds transition deltas (S3→S0, etc.)                 │
│ - Writes features.regime_engine_v4                     │
│   {delta_a_raw, delta_e_raw, prev_state, ...}         │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ compute_levers() (MODIFIED)                            │
│ - Reads features.regime_engine_v4 from all drivers     │
│ - Applies execution TF multipliers                     │
│ - Applies driver weights                               │
│ - Sums to get A_regime, E_regime                      │
│ - Adds intent deltas (capped at 0.4)                  │
│ - Clamps to [0,1]                                      │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Regime Drivers

**8 drivers total** (not per token):

| Driver | Type | Price Data Source | Notes |
|--------|------|------------------|-------|
| BTC | Global | `majors_price_data_ohlc` | Already exists |
| ALT | Global | `regime_price_data_ohlc` | Equal-weight SOL/ETH/BNB/HYPE |
| nano | Bucket | `regime_price_data_ohlc` | Equal-weight bucket composite |
| small | Bucket | `regime_price_data_ohlc` | Equal-weight bucket composite |
| mid | Bucket | `regime_price_data_ohlc` | Equal-weight bucket composite |
| big | Bucket | `regime_price_data_ohlc` | Equal-weight bucket composite |
| BTC.d | Dominance | `regime_price_data_ohlc` | Converted from `portfolio_bands` |
| USDT.d | Dominance | `regime_price_data_ohlc` | Converted from `portfolio_bands` |

**Note**: Bucket naming changed from `micro` → `small` to avoid confusion with timeframe `micro`.

### 1.3 Timeframes

**3 regime timeframes** (fixed):

| Regime TF | Candles | Purpose |
|-----------|---------|---------|
| Macro | 1d | Slow shifts, big picture |
| Meso | 1h | Most influential (trading context) |
| Micro | 1m | Tactical adjustments |

**Total computation**: 8 drivers × 3 timeframes = **24 Uptrend Engine runs per candle**

---

## 2. Data Model

### 2.1 Regime Drivers as "Positions"

Regime drivers are stored in `lowcap_positions` table with special identifiers:

```sql
-- Example regime driver position:
token_contract: "BTC" | "ALT" | "nano" | "small" | "mid" | "big" | "BTC.d" | "USDT.d"
token_chain: "regime" (or "hyperliquid" for BTC)
timeframe: "1d" | "1h" | "1m"  -- REGIME timeframe, not execution timeframe
status: "regime_driver"
features: {
  "ta": {...},                    -- TA data (EMAs, slopes, ATR, etc.)
  "uptrend_engine_v4": {...},     -- State/flags/scores from Uptrend Engine
  "regime_engine_v4": {
    "delta_a_raw": float,         -- Pre-weight ΔA
    "delta_e_raw": float,         -- Pre-weight ΔE
    "prev_state": "S3",           -- For transition detection
    "ts": "2024-01-15T10:00:00Z"
  }
}
```

### 2.2 Price Data Table

**New table**: `regime_price_data_ohlc`

```sql
CREATE TABLE regime_price_data_ohlc (
  driver VARCHAR NOT NULL,        -- 'BTC', 'ALT', 'nano', 'small', 'mid', 'big', 'BTC.d', 'USDT.d'
  timeframe VARCHAR NOT NULL,     -- '1d', '1h', '1m' (regime timeframes)
  timestamp TIMESTAMPTZ NOT NULL,
  
  open_usd NUMERIC NOT NULL,
  high_usd NUMERIC NOT NULL,
  low_usd NUMERIC NOT NULL,
  close_usd NUMERIC NOT NULL,
  volume NUMERIC NOT NULL,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (driver, timeframe, timestamp)
);
```

**Data Sources**:
- BTC: Read from `majors_price_data_ohlc` (chain="hyperliquid", token_contract="BTC")
- ALT: Compute equal-weight from `majors_price_data_ohlc` (SOL, ETH, BNB, HYPE)
- Buckets: Compute from `lowcap_price_data_ohlc` using `BucketSeriesComputer`
- BTC.d/USDT.d: **Collect per minute** from CoinGecko `/global` endpoint, roll up to OHLC (1m → 1h → 1d) just like other regime drivers

---

## 3. State/Flag/Transition Tables

**Reference**: `docs/inprogress/Regime_engine.md` lines 1612-1746

### 3.1 Baseline State Deltas

| State | Meaning | ΔA_base | ΔE_base | Notes |
|-------|---------|---------|---------|-------|
| **S0** | Downtrend / bad | **-0.30** | **+0.30** | Strong risk-off |
| **S1** | Early uptrend / best asymmetry | **+0.25** | **-0.15** | Best buy zone |
| **S2** | No man's land | **+0.10** | **+0.05** | Worse than S1 |
| **S3** | Confirmed uptrend | **+0.20** | **-0.05** | Good environment |

### 3.2 Flag Modifiers (Additive)

**Buy Flags**:
- S1 + Buy: ΔA +0.20, ΔE -0.10
- S2 + Buy: ΔA +0.10, ΔE -0.05 (optional, may disable)
- S3 + Buy: ΔA +0.05, ΔE -0.05 (rare)

**Rebuy Flags**:
- S2 + Rebuy: ΔA +0.15, ΔE -0.10
- S3 + Rebuy: ΔA +0.20, ΔE -0.10

**Trim Flags**:
- S2 + Trim: ΔA -0.20, ΔE +0.25
- S3 + Trim: ΔA -0.25, ΔE +0.30

### 3.3 Transition Deltas (Emergency Exits)

| Transition | ΔA_trans | ΔE_trans | Notes |
|------------|----------|----------|-------|
| **S1 → S0** | **-0.40** | **+0.40** | Early uptrend failure |
| **S2 → S0** | **-0.35** | **+0.35** | No man's land collapse |
| **S3 → S0** | **-0.50** | **+0.50** | Confirmed trend nuked |

**Note**: Transition deltas stack with the new S0 baseline.

### 3.4 Dominance Inversion

BTC.d and USDT.d use the **same state table**, but driver weights are negative:
- BTC.d weight: **-1.0**
- USDT.d weight: **-3.0**

This automatically inverts the effect (uptrend in dominance = risk-off).

---

## 4. Weighting System

**Reference**: `docs/inprogress/Regime_engine.md` lines 1165-1262, 1442-1567

### 4.1 Timeframe Weights (Fixed)

| Timeframe | Weight |
|-----------|--------|
| Macro (1d) | 0.50 |
| Meso (1h) | 0.40 |
| Micro (1m) | 0.10 |

### 4.2 Driver Weights

| Driver | Weight | Notes |
|--------|--------|-------|
| BTC | 1.0 | Weakest positive driver |
| ALT composite | 1.5 | Stronger alt indication |
| Bucket composite | 3.0 | Strongest positive (most predictive locally) |
| BTC.d | -1.0 | Negative (risk-off rotation) |
| USDT.d | -3.0 | Very strong negative (cash inflow) |

### 4.3 Execution Timeframe Multipliers

**Applied per-position** based on execution timeframe:

| Exec TF | Macro | Meso | Micro |
|---------|-------|------|-------|
| 1m | 0.05 | 0.35 | 0.60 |
| 5m | 0.10 | 0.50 | 0.40 |
| 15m | 0.15 | 0.55 | 0.30 |
| 1h | 0.30 | 0.55 | 0.15 |
| 4h | 0.55 | 0.40 | 0.05 |
| 1d | 0.80 | 0.18 | 0.02 |

### 4.4 Intent Cap

Intent deltas capped at **±0.4** total effect:
- `|ΔA_intent| ≤ 0.4`
- `|ΔE_intent| ≤ 0.4`

---

## 5. Implementation Components

### 5.1 Regime Price Collector

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/regime_price_collector.py`

**Responsibilities**:
1. **Majors**: Backfill historical OHLC from Binance API, then collect current prices from Hyperliquid WS
2. **ALT Composite OHLC**: Compute equal-weight composite from majors (SOL, ETH, BNB, HYPE)
   - Read OHLC bars from `majors_price_data_ohlc` for each asset
   - **Methodology**:
     - `open = avg(opens)` - Average of first bar's open from each asset
     - `high = max(highs)` - Maximum high across all assets
     - `low = min(lows)` - Minimum low across all assets
     - `close = avg(closes)` - Average of last bar's close from each asset
     - `volume = sum(volumes)` - Total volume across all assets
   - Store in `regime_price_data_ohlc` (driver="ALT")
3. **Bucket Composite OHLC**: Compute equal-weight composite for each bucket (nano, small, mid, big)
   - Read OHLC bars from `lowcap_price_data_ohlc` for all tokens in bucket
   - **Methodology** (same as ALT composite):
     - `open = avg(opens)` - Average of first bar's open from each token
     - `high = max(highs)` - Maximum high across all tokens
     - `low = min(lows)` - Minimum low across all tokens
     - `close = avg(closes)` - Average of last bar's close from each token
     - `volume = sum(volumes)` - Total volume across all tokens
   - Store in `regime_price_data_ohlc` (driver="nano"/"small"/"mid"/"big")
4. **Dominance**: Collect BTC.d and USDT.d per minute from CoinGecko `/global` endpoint
   - Treat dominance percentage (1-100%) as price-like value ($1-$100) for TA calculations
   - Roll up to OHLC (1m → 1h → 1d) using standard OHLC rollup methodology
   - Store in `regime_price_data_ohlc` (driver="BTC.d"/"USDT.d")
5. Write all computed OHLC data to `regime_price_data_ohlc` table

**Schedule**: 
- **Micro (1m)**: Collect dominance per minute, roll up to 1m OHLC
- **Meso (1h)**: Roll up 1m → 1h OHLC
- **Macro (1d)**: Roll up 1h → 1d OHLC

**Dependencies**:
- Binance API (for majors historical backfill)
- Hyperliquid WS (for current majors prices)
- CoinGecko `/global` endpoint (for dominance - collected per minute, well within free tier limits: 10-30 calls/min, ~10k/day)
- `majors_price_data_ohlc` (for BTC, ALT components)
- `lowcap_price_data_ohlc` (for bucket composites)

**OHLC Rollup Methodology**:
- Follows same pattern as existing `GenericOHLCRollup` system
- For 1m → 1h → 1d rollups:
  - `open = first bar's open`
  - `high = max(all highs)`
  - `low = min(all lows)`
  - `close = last bar's close`
  - `volume = sum(all volumes)`

### 5.2 Regime TATracker

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/regime_ta_tracker.py`

**Responsibilities**:
1. Read regime driver positions from `lowcap_positions` (status="regime_driver")
2. Read OHLC data from `regime_price_data_ohlc` (not `lowcap_price_data_ohlc`)
3. Compute TA (EMAs, slopes, ATR, ADX, RSI, etc.) - reuse existing `ta_utils.py`
4. **For dominance drivers**: Treat percentage (1-100%) as price-like value ($1-$100) - TA calculations work normally
5. **Populate `features.ta.latest_price`**: Store latest close price for UptrendEngine to use
   - This avoids UptrendEngine needing to know about regime drivers vs regular positions
   - Single source of truth: TATracker reads OHLC and provides price
   - Keeps UptrendEngine unchanged (just reads from `features.ta.latest_price`)
6. Write `features.ta` to regime positions

**Schedule**: Run after Regime Price Collector (e.g., every 1m/1h/1d depending on regime TF)

**Reuses**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_utils.py`

**Note**: ATR on dominance represents "average true range of dominance percentage" - this is valid and useful for volatility measurement

### 5.3 Uptrend Engine

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`

**Changes**: **NONE** - works as-is, reads price from `features.ta.latest_price`

**What it does**:
- Reads `features.ta` from regime positions (including `latest_price` populated by Regime TATracker)
- **Price reading**: Uses `features.ta.latest_price` if available, otherwise falls back to `_latest_close_1h()` (for backward compatibility)
- Computes state (S0/S1/S2/S3)
- Computes flags (buy/trim/rebuy)
- Computes scores (OX/DX/EDX)
- Writes `features.uptrend_engine_v4`

**Implementation Note**: 
- ✅ **DECISION**: Regime TATracker populates `features.ta.latest_price`
- This keeps UptrendEngine unchanged (no special case logic for regime drivers)
- Single source of truth: TATracker reads OHLC and provides price
- Cleaner separation of concerns

**Schedule**: Run after Regime TATracker

### 5.4 Regime Mapper

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/regime_mapper.py`

**Responsibilities**:
1. Read `features.uptrend_engine_v4` from regime driver positions
2. Map state → ΔA_base, ΔE_base (from state table)
3. Add flag deltas (buy/trim/rebuy) if active
4. Detect transitions (compare `prev_state` vs `state`)
5. Add transition deltas if transition occurred
6. Write `features.regime_engine_v4` with:
   - `delta_a_raw`: Pre-weight ΔA (state + flags + transitions)
   - `delta_e_raw`: Pre-weight ΔE (state + flags + transitions)
   - `prev_state`: Current state (for next run's transition detection)
   - `ts`: Timestamp

**State Table Implementation**:
```python
STATE_DELTAS = {
    "S0": {"delta_a": -0.30, "delta_e": 0.30},
    "S1": {"delta_a": 0.25, "delta_e": -0.15},
    "S2": {"delta_a": 0.10, "delta_e": 0.05},
    "S3": {"delta_a": 0.20, "delta_e": -0.05},
}

FLAG_DELTAS = {
    "buy": {
        "S1": {"delta_a": 0.20, "delta_e": -0.10},
        "S2": {"delta_a": 0.10, "delta_e": -0.05},
        "S3": {"delta_a": 0.05, "delta_e": -0.05},
    },
    "rebuy": {
        "S2": {"delta_a": 0.15, "delta_e": -0.10},
        "S3": {"delta_a": 0.20, "delta_e": -0.10},
    },
    "trim": {
        "S2": {"delta_a": -0.20, "delta_e": 0.25},
        "S3": {"delta_a": -0.25, "delta_e": 0.30},
    },
}

TRANSITION_DELTAS = {
    "S1→S0": {"delta_a": -0.40, "delta_e": 0.40},
    "S2→S0": {"delta_a": -0.35, "delta_e": 0.35},
    "S3→S0": {"delta_a": -0.50, "delta_e": 0.50},
}
```

**Schedule**: Run after Uptrend Engine

### 5.5 Modified `compute_levers()`

**File**: `src/intelligence/lowcap_portfolio_manager/pm/levers.py`

**Changes**:
1. Remove: `phase_macro`, `phase_meso`, `cut_pressure` parameters
2. Remove: `_map_meso_policy()`, `_apply_macro()`, `_apply_cut_pressure()` calls
3. Remove: `_compute_age_component()`, `_compute_market_cap_component()` calls
4. Add: Read regime state from `lowcap_positions` (status="regime_driver")
5. Add: Apply execution TF multipliers
6. Add: Apply driver weights
7. Add: Sum regime contributions
8. Keep: `_apply_intent_deltas()` (with cap at 0.4)

**New Signature**:
```python
def compute_levers(
    features: Dict[str, Any],
    execution_timeframe: str,  # "1m", "5m", "15m", "1h", "4h", "1d"
    position_bucket: str | None,  # "nano", "small", "mid", "big"
    sb_client: Client,  # For reading regime state
) -> Dict[str, Any]:
```

**Algorithm**:
```python
# 1. Start with neutral base
A_base = 0.5
E_base = 0.5

# 2. Read regime state for all drivers
regime_drivers = ["BTC", "ALT", position_bucket, "BTC.d", "USDT.d"]
regime_tfs = ["macro", "meso", "micro"]

# 3. Sum regime contributions
delta_a_regime = 0.0
delta_e_regime = 0.0

for driver in regime_drivers:
    for tf in regime_tfs:
        # Read regime state (with error recovery)
        regime_state = read_regime_state(driver, tf, sb_client)
        
        # Error recovery: Check if state is stale (> 3 bars old)
        if regime_state is None or is_stale(regime_state, tf, bars=3):
            # Fall back to neutral (0.0 deltas) if stale or missing
            delta_a_raw = 0.0
            delta_e_raw = 0.0
            logger.warning(f"Regime state stale/missing for {driver}/{tf}, using neutral")
        else:
            # Get raw deltas
            delta_a_raw = regime_state["delta_a_raw"]
            delta_e_raw = regime_state["delta_e_raw"]
        
        # Apply execution TF multiplier
        tf_mult = EXEC_TF_MULTIPLIERS[execution_timeframe][tf]
        
        # Apply driver weight
        driver_weight = DRIVER_WEIGHTS[driver]
        
        # Accumulate
        delta_a_regime += delta_a_raw * tf_mult * driver_weight
        delta_e_regime += delta_e_raw * tf_mult * driver_weight

# 4. Apply regime deltas
A_regime = A_base + delta_a_regime
E_regime = E_base + delta_e_regime

# 5. Apply intent deltas (capped at 0.4)
A_intent, E_intent, intent_diag = _apply_intent_deltas(A_regime, E_regime, features)
# (intent deltas already capped internally at ±0.4)

# 6. Clamp to [0,1]
A_final = clamp(A_intent, 0.0, 1.0)
E_final = clamp(E_intent, 0.0, 1.0)

# 7. Compute position sizing
position_size_frac = _compute_position_sizing(A_final)

return {
    "A_value": A_final,
    "E_value": E_final,
    "position_size_frac": position_size_frac,
    "diagnostics": {...},
}
```

---

## 6. Database Schema

### 6.1 New Table: `regime_price_data_ohlc`

```sql
CREATE TABLE regime_price_data_ohlc (
  driver VARCHAR NOT NULL,        -- 'BTC', 'ALT', 'nano', 'small', 'mid', 'big', 'BTC.d', 'USDT.d'
  timeframe VARCHAR NOT NULL,     -- '1d', '1h', '1m' (regime timeframes)
  timestamp TIMESTAMPTZ NOT NULL,
  
  open_usd NUMERIC NOT NULL,
  high_usd NUMERIC NOT NULL,
  low_usd NUMERIC NOT NULL,
  close_usd NUMERIC NOT NULL,
  volume NUMERIC NOT NULL,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (driver, timeframe, timestamp)
);

CREATE INDEX idx_regime_price_driver_tf_ts 
  ON regime_price_data_ohlc (driver, timeframe, timestamp DESC);
```

### 6.2 Regime Driver Positions

Stored in existing `lowcap_positions` table:

```sql
-- Example insert:
INSERT INTO lowcap_positions (
  token_contract,    -- 'BTC', 'ALT', 'nano', 'small', 'mid', 'big', 'BTC.d', 'USDT.d'
  token_chain,      -- 'regime' (or 'hyperliquid' for BTC)
  timeframe,        -- '1d', '1h', '1m' (regime timeframe)
  status,           -- 'regime_driver'
  features          -- JSONB with ta, uptrend_engine_v4, regime_engine_v4
) VALUES (...);
```

### 6.3 Features Structure

```json
{
  "ta": {
    "ema": {
      "ema20_1d": 85000.0,
      "ema30_1d": 84000.0,
      ...
    },
    "ema_slopes": {
      "ema20_slope_1d": 0.001,
      ...
    },
    ...
  },
  "uptrend_engine_v4": {
    "state": "S3",
    "flags": {
      "buy": false,
      "trim": true,
      "rebuy": false
    },
    "scores": {
      "ox": 0.72,
      "dx": 0.45,
      "edx": 0.58
    },
    ...
  },
  "regime_engine_v4": {
    "delta_a_raw": 0.15,    -- Pre-weight ΔA
    "delta_e_raw": 0.25,    -- Pre-weight ΔE
    "prev_state": "S2",     -- For transition detection
    "ts": "2024-01-15T10:00:00Z"
  }
}
```

---

## 7. Integration Points

### 7.1 PM Core Tick

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Changes**:
1. Remove: `phase_macro`, `phase_meso`, `cut_pressure` fetching
2. Update: `_active_positions()` to **exclude** regime drivers:
   ```python
   .in_("status", ["watchlist", "active"])  # Excludes "regime_driver"
   ```
3. Update: `compute_levers()` call to new signature:
   ```python
   levers = compute_levers(
       features=position["features"],
       execution_timeframe=position["timeframe"],
       position_bucket=token_bucket,
       sb_client=self.sb,
   )
   ```
4. Remove: `_compute_age_component()` and `_compute_market_cap_component()` calls from `compute_levers()`

### 7.2 Scheduler Integration

**File**: `src/run_trade.py` (or scheduler config)

**New Jobs** (integrated like existing price data jobs):
1. `regime_price_collector` - Run before TA (1m/1h/1d depending on regime TF)
2. `regime_ta_tracker` - Run after price collector
3. `uptrend_engine_v4` - Already exists, will process regime drivers (needs `status="regime_driver"` added to `_active_positions()`)
4. `regime_mapper` - Run after Uptrend Engine

**Scheduler Configuration** (APScheduler):
```python
# Regime Price Collector - Micro (1m)
scheduler.add_job(
    regime_price_collector.run,
    trigger='cron',
    minute='*',  # Every minute
    args=[],  # Uses regime TF="1m" internally
    id='regime_price_collector_1m',
    max_instances=1
)

# Regime Price Collector - Meso (1h)
scheduler.add_job(
    regime_price_collector.run,
    trigger='cron',
    minute=0,  # Every hour at :00
    args=[],  # Uses regime TF="1h" internally
    id='regime_price_collector_1h',
    max_instances=1
)

# Regime Price Collector - Macro (1d)
scheduler.add_job(
    regime_price_collector.run,
    trigger='cron',
    hour=0, minute=0,  # Daily at midnight
    args=[],  # Uses regime TF="1d" internally
    id='regime_price_collector_1d',
    max_instances=1
)

# Regime TATracker - runs after price collector (offset by 5s)
scheduler.add_job(
    regime_ta_tracker.run,
    trigger='cron',
    minute='*', second=5,  # Every minute at :05
    args=[],  # Processes all regime TFs
    id='regime_ta_tracker',
    max_instances=1
)

# Regime Mapper - runs after Uptrend Engine (offset by 10s)
scheduler.add_job(
    regime_mapper.run,
    trigger='cron',
    minute='*', second=10,  # Every minute at :10
    args=[],  # Processes all regime drivers/TFs
    id='regime_mapper',
    max_instances=1
)
```

**Schedule Flow**:
- **Micro (1m)**: Regime Price Collector (every 1m) → Regime TATracker (:05) → Uptrend Engine (:07) → Regime Mapper (:10)
- **Meso (1h)**: Regime Price Collector (every 1h) → Regime TATracker (:05) → Uptrend Engine (:07) → Regime Mapper (:10)
- **Macro (1d)**: Regime Price Collector (daily) → Regime TATracker (:05) → Uptrend Engine (:07) → Regime Mapper (:10)

**Note**: Uptrend Engine already scheduled - needs minor update to process regime drivers:
- Modify `_active_positions()` in `uptrend_engine_v4.py` to include `status="regime_driver"`:
  ```python
  .in_("status", ["watchlist", "active", "regime_driver"])  # Include regime drivers
  ```
- This allows Uptrend Engine to process both regular positions and regime drivers

---

## 8. Testing Strategy

### 8.1 Unit Tests

1. **Regime Mapper**:
   - Test state → ΔA/ΔE mapping
   - Test flag deltas (buy/trim/rebuy)
   - Test transition detection and deltas
   - Test dominance inversion (negative weights)

2. **Regime Price Collector**:
   - **Test Binance API** (isolated test before integration):
     - Test endpoint: `/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1000`
     - Verify response format, data quality, rate limits
     - Test batching logic for historical backfill
   - Test ALT composite computation
   - Test bucket composite computation
   - Test dominance per-minute collection and OHLC rollup (1m → 1h → 1d)

3. **Modified `compute_levers()`**:
   - Test regime contribution summation
   - Test execution TF multiplier application
   - Test driver weight application
   - Test intent cap enforcement

### 8.2 Integration Tests

1. **End-to-End Flow**:
   - Regime Price Collector → Regime TATracker → Uptrend Engine → Regime Mapper → `compute_levers()`
   - Verify A/E scores are computed correctly

2. **Transition Detection**:
   - Simulate S3→S0 transition
   - Verify transition delta is applied

3. **Bucket Selection**:
   - Test that each token only uses its own bucket's regime

### 8.3 Backtesting

- Compare old phase-based A/E vs new regime-based A/E
- Verify regime-driven scores make sense
- Check for regressions in position management

---

## 9. PM Core Tick Changes

### 9.1 Decision: No Refactoring Needed

**Status**: ✅ **RESOLVED** - Regime drivers DON'T go through PM Core Tick (Option 1)

PM Core Tick (`src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`) remains focused on lowcap positions only:
- Regime drivers processed separately (not through PM Core Tick)
- PM Core Tick reads regime state but doesn't process regime drivers
- **No refactoring needed** - only minor changes required

### 9.2 Current Flow

```python
# PM Core Tick.run()
1. Fetch phase_macro, phase_meso, cut_pressure
2. Fetch active positions (lowcap coins)
3. For each position:
   - Call compute_levers(phase_macro, phase_meso, cut_pressure, ...)
   - Plan actions
   - Execute actions
   - Write strands
```

### 9.3 Required Changes (Minimal)

**For Regime Engine Integration**:
1. **Remove phase fetching** - Delete `_latest_phase()`, `_latest_cut_pressure()` calls
2. **Update `_active_positions()`** - Filter out regime drivers (`status != "regime_driver"`)
3. **Update `compute_levers()` call** - New signature reads regime state from positions table
4. **Read regime state** - `compute_levers()` reads from `lowcap_positions` where `status="regime_driver"`

**No Refactoring Needed**:
- PM Core Tick remains focused on lowcap positions only
- Regime drivers are processed separately (not through PM Core Tick)
- Future multi-asset support can be handled separately when needed

### 9.4 Regime State Reading

`compute_levers()` will read regime state directly from `lowcap_positions`:

```python
def compute_levers(
    features: Dict[str, Any],
    execution_timeframe: str,
    position_bucket: Optional[str],
    sb_client: Client,
    # ... other params
) -> Dict[str, Any]:
    """
    Read regime state from regime driver positions.
    
    Regime drivers are stored in lowcap_positions with status="regime_driver".
    Each driver has features.regime_engine_v4 with delta_a_raw, delta_e_raw.
    """
    # Fetch all regime driver positions
    regime_drivers = ["BTC", "ALT", "nano", "small", "mid", "big", "BTC.d", "USDT.d"]
    regime_tfs = ["macro", "meso", "micro"]
    
    regime_state = {}
    for driver in regime_drivers:
        regime_state[driver] = {}
        for tf in regime_tfs:
            position = _fetch_regime_driver_position(driver, tf, sb_client)
            if position:
                regime_engine = position["features"].get("regime_engine_v4", {})
                regime_state[driver][tf] = {
                    "delta_a_raw": regime_engine.get("delta_a_raw", 0.0),
                    "delta_e_raw": regime_engine.get("delta_e_raw", 0.0),
                    "state": regime_engine.get("state", ""),
                    "flags": regime_engine.get("flags", {}),
                }
    
    # Apply weights, execution TF multipliers, sum contributions
    # ... (see compute_levers() implementation)
```

---

## 11. Migration Plan

### Phase 1: Infrastructure (Week 3)
1. **Test Binance API** (isolated test before integration)
   - Create test script: `tests/test_binance_api.py`
   - Test endpoint: `/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1000`
   - Verify: Response format, data quality, rate limits, batching logic
   - Document: API behavior, error handling, data validation
2. Create `regime_price_data_ohlc` table
3. Implement Regime Price Collector
   - Integrate Binance API for majors historical backfill (`/api/v3/klines`)
   - Implement batching logic (1000 candles per request)
   - Fetch current prices from Hyperliquid WS
   - **Dominance**: Collect BTC.d/USDT.d per minute from CoinGecko `/global` endpoint
   - Implement OHLC rollup for dominance (1m → 1h → 1d) just like other regime drivers
4. Create regime driver positions in `lowcap_positions` (auto-create on first run)
   - Required drivers: BTC, ALT
   - Optional drivers: Buckets (nano/small/mid/big), Dominance (BTC.d/USDT.d)
5. Test price data collection
6. Test dominance collection and rollup (verify continuous collection works)

### Phase 2: TA & State Computation (Week 4)
1. Implement Regime TATracker
2. Verify Uptrend Engine works on regime drivers
3. Test state computation for all drivers/TFs
4. Verify `uptrend_state_events` table receives regime driver events

### Phase 3: Regime Mapper (Week 5)
1. Implement Regime Mapper
2. Test state → ΔA/ΔE mapping
3. Test transition detection
4. Test dominance inversion (negative weights)

### Phase 4: Integration (Week 6)
1. Modify `compute_levers()` to use regime state
2. Update PM Core Tick to use new `compute_levers()` signature
3. Update PM Core Tick `_active_positions()` to exclude regime drivers
4. Update scheduler to run regime jobs
5. End-to-end testing

### Phase 5: Cleanup (Week 7)
1. Remove old phase-based code from `compute_levers()` (`_map_meso_policy`, `_apply_macro`, `_apply_cut_pressure`)
2. Remove `cut_pressure` computation from `bands_calc.py` (or repurpose for other uses)
3. Remove phase fetching from PM Core Tick (`_latest_phase()`, `_latest_cut_pressure()`)
4. Update documentation

### Phase 6: Bootstrap & Production (Week 8)
1. Implement startup bootstrap sequence
2. Verify all regime data is populated
3. Monitor regime state changes
4. Production deployment

---

## 12. Bootstrap Sequence

### 12.1 Startup Bootstrap Requirements

**Goal**: Fully align and prepare the system before running PM Core Tick

**Bootstrap Order**:
1. **Price Data**:
   - **Majors**: Backfill historical OHLC from Binance API (up to 1000 candles per request, batch as needed)
   - Fetch current majors prices (BTC, SOL, ETH, BNB, HYPE) from Hyperliquid WS
   - Compute ALT composite
   - Compute bucket composites (nano, small, mid, big)
   - **Dominance**: Start collecting BTC.d and USDT.d per minute from CoinGecko `/global` endpoint (continuous collection, roll up to OHLC)
   - Write to `regime_price_data_ohlc`

2. **TA Computation**:
   - Run Regime TATracker for all regime drivers/TFs
   - Ensure `features.ta` is populated
   - **Error handling**: If TA computation fails for a driver, log error and skip (continue with others)

3. **State Computation**:
   - Run Uptrend Engine for all regime drivers/TFs
   - Run Regime Mapper
   - Ensure `features.regime_engine_v4` is populated
   - **Error handling**: If state computation fails, use last known state (if < 3 bars old), else neutral

4. **Position Data**:
   - Verify active positions have required data
   - Check wallet balances

5. **Regime Driver Positions**:
   - Auto-create if missing
   - Verify all 8 drivers × 3 TFs = 24 positions exist
   - **Required drivers**: BTC, ALT (must exist for system to function)
   - **Optional drivers**: Buckets (nano/small/mid/big), Dominance (BTC.d/USDT.d)
   - If required driver missing: Log error, system can start but with degraded regime signals
   - If optional driver missing: Log warning, continue with available drivers

**Notes**:
- **Macro (1d)**: May need ~1 year of history. Start with meso/micro, build macro over time.
- **Dominance**: Collect per minute continuously, roll up to OHLC (1m → 1h → 1d). Build long-term history over time (needed for full TA/state computation, not just 7-day deltas).
- **Error Recovery**: Use 3-bar window for stale state detection (timeframe-dependent).

### 12.2 Bootstrap Implementation

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/bootstrap_regime.py`

```python
class RegimeBootstrap:
    """Bootstrap all regime data on startup"""
    
    def bootstrap_all(self):
        """Run full bootstrap sequence"""
        # 1. Create regime driver positions (if missing)
        # Required: BTC, ALT
        # Optional: Buckets (nano/small/mid/big), Dominance (BTC.d/USDT.d)
        self._ensure_regime_driver_positions()
        
        # 2. Collect price data (with retry logic)
        collector = RegimePriceCollector()
        
        # Backfill majors from Binance API (historical OHLC) - with retry
        max_retries = 3
        backoff_seconds = [5, 15, 60]
        for attempt in range(max_retries):
            try:
                collector.backfill_majors_from_binance()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = backoff_seconds[attempt]
                    logger.warning(f"Binance backfill failed (attempt {attempt+1}/{max_retries}), retrying in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    logger.error(f"Binance backfill failed after {max_retries} attempts: {e}")
                    # Continue with degraded data (will build up over time)
        
        # Collect current prices from Hyperliquid WS - with retry
        for attempt in range(max_retries):
            try:
                collector.collect_current_prices()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = backoff_seconds[attempt]
                    logger.warning(f"Hyperliquid price collection failed (attempt {attempt+1}/{max_retries}), retrying in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    logger.error(f"Hyperliquid price collection failed after {max_retries} attempts: {e}")
                    # Continue - will retry on next scheduled run
        
        # Start collecting dominance per minute from CoinGecko (continuous collection) - with retry
        for attempt in range(max_retries):
            try:
                collector.start_dominance_collection()  # Begins per-minute collection
                collector.run()  # Collects for all TFs, rolls up dominance to OHLC
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = backoff_seconds[attempt]
                    logger.warning(f"CoinGecko dominance collection failed (attempt {attempt+1}/{max_retries}), retrying in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    logger.error(f"CoinGecko dominance collection failed after {max_retries} attempts: {e}")
                    # Continue - will retry on next scheduled run
        
        # 3. Compute TA
        for tf in ["1d", "1h", "1m"]:
            tracker = RegimeTATracker(timeframe=tf)
            try:
                tracker.run()
            except Exception as e:
                logger.error(f"TA computation failed for {tf}: {e}")
                # Continue with other timeframes
        
        # 4. Compute states
        for tf in ["1d", "1h", "1m"]:
            engine = UptrendEngineV4(timeframe=tf)
            try:
                engine.run()  # Processes regime drivers
            except Exception as e:
                logger.error(f"State computation failed for {tf}: {e}")
                # Use last known state if available (< 3 bars old), else neutral
        
        # 5. Map to deltas
        mapper = RegimeMapper()
        mapper.run()
        
        logger.info("Regime bootstrap complete")
```

**Integration**: Call from `src/run_trade.py` before starting schedulers

**Error Recovery**:
- If regime driver fails: Use last known state if < 3 bars old, else neutral (0.0 deltas)
- Required drivers (BTC, ALT): Must exist or system starts with degraded regime signals
- Optional drivers: System continues with available drivers

---

## 10. Open Questions & Decisions

### 10.1 Resolved Questions

1. **Rebuy Flag Logic**: ✅ **RESOLVED** - Remove "rebuy only after trim" constraint for regime. Reason: Regime drivers (e.g., BTC) don't know if a specific position trimmed. Regime Mapper will apply rebuy flags whenever Uptrend Engine emits them, regardless of position-level trim history.

2. **Bucket Population**: ✅ **RESOLVED** - No minimum population required. Even 1 token in a bucket is useful - it tells us if that specific token is outperforming. More specific = better information.

3. **Dominance OHLC Conversion**: ✅ **RESOLVED** - Keep it simple, similar to 1m → OHLC rollup. Use dominance level as "close", compute high/low from recent history (e.g., last 24h window). Don't overcomplicate.

4. **Regime Driver Initialization**: ✅ **RESOLVED** - Bootstrap all data on startup. Create regime driver positions automatically on first run. Build up macro data over time (may need ~1 year for full macro history, but that's fine - start with meso/micro).

5. **Historical Data**: ✅ **RESOLVED** - Binance API for majors backfill, continuous dominance collection
   - **Majors**: Use Binance API to backfill historical OHLC data (up to 1000 candles per request)
   - **Dominance**: Collect per minute from CoinGecko `/global` endpoint, roll up to OHLC (1m → 1h → 1d) just like other regime drivers. Build long-term history over time (not just 7 days - full OHLC history needed for TA/state computation)

6. **Monitoring**: ✅ **RESOLVED** - Use existing `uptrend_state_events` table. Regime drivers will emit events just like regular positions.

7. **Performance**: ✅ **RESOLVED** - 24 Uptrend Engine runs per candle is acceptable. Only 1m runs frequently (every minute), others are 1h/1d. No caching needed - we're looking for new data each candle.

8. **Error Handling**: ✅ **RESOLVED** - Log and skip. If a regime driver's TA computation fails, log the error and skip that driver for that candle. Continue with other drivers.

### 10.2 Critical: PM Core Tick Refactoring

**Status**: ✅ **RESOLVED** - Option 1 Selected

**Decision**: **Regime drivers DON'T go through PM Core Tick**

**Architecture**:
- Regime drivers processed separately: Regime Price Collector → Regime TATracker → Uptrend Engine → Regime Mapper
- PM Core Tick reads regime state from positions table but doesn't process them
- Regime drivers are "read-only" positions (status="regime_driver")
- **NO refactoring of PM Core Tick needed** - it continues to handle lowcap positions only

**What PM Core Tick Does**:
1. Fetches lowcap positions (excludes regime drivers)
2. Computes A/E scores (via `compute_levers()` which reads regime state)
3. Plans actions (buy/sell/trim)
4. Executes trades
5. Writes strands

**What Changes in PM Core Tick**:
1. **Remove phase fetching** - No more `phase_macro`, `phase_meso`, `cut_pressure`
2. **Update compute_levers() call** - New signature uses regime state (reads from regime driver positions)
3. **Filter regime drivers** - `_active_positions()` excludes `status="regime_driver"`

**No Refactoring Needed**:
- PM Core Tick remains focused on lowcap positions
- Regime state is read-only data that `compute_levers()` consumes
- Future multi-asset support (Hyperliquid, stocks) can be handled separately when needed

---

## Appendix A: Constants Reference

### State Deltas
```python
STATE_DELTAS = {
    "S0": {"delta_a": -0.30, "delta_e": 0.30},
    "S1": {"delta_a": 0.25, "delta_e": -0.15},
    "S2": {"delta_a": 0.10, "delta_e": 0.05},
    "S3": {"delta_a": 0.20, "delta_e": -0.05},
}
```

### Driver Weights
```python
DRIVER_WEIGHTS = {
    "BTC": 1.0,
    "ALT": 1.5,
    "nano": 3.0,
    "small": 3.0,
    "mid": 3.0,
    "big": 3.0,
    "BTC.d": -1.0,
    "USDT.d": -3.0,
}
```

### Timeframe Weights
```python
TF_WEIGHTS = {
    "macro": 0.50,
    "meso": 0.40,
    "micro": 0.10,
}
```

### Execution TF Multipliers
```python
EXEC_TF_MULTIPLIERS = {
    "1m": {"macro": 0.05, "meso": 0.35, "micro": 0.60},
    "5m": {"macro": 0.10, "meso": 0.50, "micro": 0.40},
    "15m": {"macro": 0.15, "meso": 0.55, "micro": 0.30},
    "1h": {"macro": 0.30, "meso": 0.55, "micro": 0.15},
    "4h": {"macro": 0.55, "meso": 0.40, "micro": 0.05},
    "1d": {"macro": 0.80, "meso": 0.18, "micro": 0.02},
}
```

---

## Appendix B: File Structure

```
src/intelligence/lowcap_portfolio_manager/
├── jobs/
│   ├── regime_price_collector.py      # NEW
│   ├── regime_ta_tracker.py           # NEW
│   ├── regime_mapper.py               # NEW
│   ├── uptrend_engine_v4.py           # NO CHANGES (reads price from features.ta.latest_price)
│   └── ta_tracker.py                  # Reference for TA computation
├── pm/
│   └── levers.py                      # MODIFIED
└── spiral/
    └── bucket_series.py               # Reuse for bucket composites

src/database/
└── regime_price_data_ohlc_schema.sql  # NEW
```

---

---

## 13. Summary & Key Decisions

### 13.1 Architecture Summary

**Regime Engine = 5 Components**:
1. **Regime Price Collector** - Computes composite OHLC data
2. **Regime TATracker** - Computes TA for regime drivers
3. **Uptrend Engine** - Computes states/flags/scores (no changes - reads price from features.ta.latest_price)
4. **Regime Mapper** - Maps states → ΔA/ΔE deltas
5. **Modified compute_levers()** - Applies weights and sums regime contributions

**PM Core Tick Changes**:
- ✅ **RESOLVED**: Regime drivers DON'T go through PM Core Tick (Option 1)
- PM Core Tick reads regime state but doesn't process regime drivers
- Only change: Remove phase fetching, update `compute_levers()` call, filter regime drivers
- **NO refactoring needed** - PM Core Tick remains focused on lowcap positions

### 13.2 Key Design Decisions

1. **Regime drivers as "positions"**: Store in `lowcap_positions` with `status="regime_driver"` to reuse Uptrend Engine infrastructure

2. **No rebuy-after-trim constraint**: Regime drivers don't know position-level trim history, so rebuy flags apply whenever Uptrend Engine emits them

3. **No bucket min population**: Even 1 token provides useful information

4. **Simple dominance conversion**: Similar to 1m → OHLC rollup, don't overcomplicate

5. **Bootstrap on startup**: Fully prepare system before running PM Core Tick

6. **Backfill historical data**: Needed for majors (investigate source)

7. **Performance is fine**: Only 1m runs frequently (every minute), others are 1h/1d. No caching needed.

### 13.3 Critical Path

**No PM Core Tick Refactoring Needed**:
- Regime drivers processed separately (not through PM Core Tick)
- PM Core Tick only needs minor changes: remove phase fetching, update `compute_levers()` call
- This significantly reduces implementation risk

**Implementation Order**:
1. **Phase 1-2**: Build regime infrastructure (price collection, TA, state computation)
2. **Phase 3**: Implement Regime Mapper
3. **Phase 4**: Integrate with PM Core Tick (modify `compute_levers()`, filter regime drivers)
4. **Phase 5**: Cleanup old phase-based code

---

## 14. Remaining Open Questions

### 14.1 Implementation Details

1. **Majors Backfill Source**: ✅ **RESOLVED** - Binance API

   **Decision**: Use Binance API for historical majors OHLC backfill
   
   **Why**:
   - Free, no auth required
   - Full historical OHLCV for all major markets
   - All timeframes supported (1m → 1M)
   - High limits: up to 1000 candles per request
   - Can backfill months/years with batching
   
   **Endpoint**: `/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1000`
   
   **Note**: Binance data ≠ global index price, but sufficient for regime drivers
   
   **Implementation**: Loop requests to backfill historical data on bootstrap

2. **Dominance Historical Data**: ✅ **RESOLVED** - Continuous Collection with OHLC Rollup

   **Decision**: Collect dominance per minute from CoinGecko `/global` endpoint, roll up to OHLC (1m → 1h → 1d) just like other regime drivers
   
   **Why**:
   - CoinGecko `/global` endpoint only provides current snapshot (not historical)
   - Historical dominance requires paid Pro endpoint
   - Need full OHLC history for TA computation and state calculation (not just 7-day deltas)
   - Same collection pattern as other regime drivers (continuous per-minute collection)
   
   **Implementation**:
   - On startup: Fetch current BTC.d and USDT.d levels
   - Start collecting per minute from CoinGecko `/global` endpoint
   - Roll up to OHLC: 1m → 1h → 1d (same as majors and buckets)
   - Store in `regime_price_data_ohlc` table
   - Build long-term history over time (needed for full TA/state computation)
   - Display current dominance levels in startup brief

3. **Bootstrap Timing**: ✅ **RESOLVED** - Part of `run_trade.py` Startup

   **Decision**: Bootstrap runs as part of `run_trade.py` startup sequence
   
   **Implementation**:
   - Bootstrap executes before PM Core Tick starts
   - Ensures all regime data is prepared before trading decisions
   - Display bootstrap progress in startup output
   - System waits for bootstrap completion before starting schedulers

4. **Error Recovery**: ✅ **RESOLVED** - 3-Bar Window with Fallback

   **Decision**: Use last known state with 3-bar window, then fall back to neutral
   
   **Implementation**:
   - If regime driver fails to compute state:
     1. Check last known state timestamp
     2. If within 3 bars (timeframe-dependent): use last known state
     3. If > 3 bars old: fall back to neutral (0.0 deltas)
   
   **Missing Regime Drivers on First Run**:
   - **Required drivers**: BTC, ALT (must exist for system to function)
   - **Optional drivers**: Buckets (nano/small/mid/big), Dominance (BTC.d/USDT.d)
   - If required driver missing: Log error, system can start but with degraded regime signals
   - If optional driver missing: Log warning, continue with available drivers

### 14.2 Testing & Validation

5. **Regime State Validation**: How do we verify regime state is correct?
   - Compare against manual calculations?
   - Backtest against historical data?
   - Monitor regime state changes in production?

6. **A/E Score Validation**: How do we verify new regime-driven A/E scores are reasonable?
   - Compare against old phase-based scores during transition?
   - Monitor for extreme values?
   - Alert on unexpected regime state combinations?

### 14.3 Future Considerations

7. **Multi-Asset Support**: ✅ **RECOMMENDED APPROACH**

   **Current State**:
   - `book_id` currently defaults to `"social"` in several places:
     - `decision_maker_lowcap_simple.py`: `self.book_id = self.config.get('book_id', 'social')`
     - `exposure.py`: `position.get("book_id") or "social"`
     - `actions.py`: `position.get("book_id") or "social"`
     - Database schema: `book_id TEXT DEFAULT 'social'`
   
   **Crypto Asset Classes** (all use same crypto regime drivers):
   - `"onchain_crypto"`: Current lowcap pipeline (on-chain tokens)
   - `"spot_crypto"`: Future spot trading (CEX spot markets)
   - `"perp_crypto"`: Future perpetual futures (CEX perp markets)
   - **All three use same crypto regime drivers**: BTC, ALT, crypto buckets (nano/small/mid/big), BTC.d, USDT.d
   
   **Future Asset Classes**:
   - `"stocks"`: Would use stock-specific regime drivers (SPY, QQQ equivalents), stock buckets, stock-specific dominance
   - Other asset classes as needed
   
   **Implementation Approach**:
   - **Change current defaults**: Update `book_id` default from `"social"` to `"onchain_crypto"` for current lowcap pipeline
   - **Regime driver scoping**: Regime driver positions include `book_id` field (e.g., `book_id="onchain_crypto"`)
   - **compute_levers() filtering**: Read regime drivers matching position's `book_id`
   - **Same scoping pattern**: Follow existing pattern used for market cap buckets and timeframes
   
   **Regime Driver Scoping**:
   - Store `book_id` in regime driver positions (`lowcap_positions` with `status="regime_driver"`)
   - **Initial implementation**: Set `book_id="onchain_crypto"` for all crypto regime drivers (BTC, ALT, buckets, BTC.d, USDT.d)
   - **Future extensibility**: Design `compute_levers()` to support multiple `book_id` values sharing same regime drivers
   - **Crypto book_id mapping**: Create mapping function to group crypto `book_id` values:
     ```python
     CRYPTO_BOOK_IDS = {"onchain_crypto", "spot_crypto", "perp_crypto"}
     def get_regime_book_id(book_id: str) -> str:
         # Map crypto book_ids to shared regime driver book_id
         if book_id in CRYPTO_BOOK_IDS:
             return "onchain_crypto"  # All crypto uses same regime drivers
         return book_id  # Other asset classes use their own
     ```
   - `compute_levers()` reads regime drivers using mapped `book_id` (not direct match)
   - **All drivers are scoped**: BTC, ALT, buckets, dominance all filtered by mapped `book_id`
   - **Easy to extend**: Adding `"spot_crypto"` or `"perp_crypto"` just requires adding to `CRYPTO_BOOK_IDS` set
   
   **Code Changes Needed**:
   - Update `decision_maker_lowcap_simple.py`: Change default from `'social'` to `'onchain_crypto'`
   - Update `exposure.py`: Change default from `"social"` to `"onchain_crypto"`
   - Update `actions.py`: Change default from `"social"` to `"onchain_crypto"`
   - Update database schema default (if needed): `book_id TEXT DEFAULT 'onchain_crypto'`
   - Regime driver positions: Set `book_id="onchain_crypto"` for all crypto regime drivers
   - **compute_levers()**: Implement `get_regime_book_id()` mapping function to support multiple crypto `book_id` values

8. **Regime Driver Update Frequency**: ✅ **RECOMMENDED APPROACH**

   **Independent schedule** (not tied to PM Core Tick):
   - Regime drivers update on their own schedule: 1m (micro), 1h (meso), 1d (macro)
   - PM Core Tick runs based on timeframes of positions it's monitoring/trading
   - **It's acceptable if regime state is slightly stale** when PM Core Tick reads it
   - Regime signals are macro/meso/micro context - small delays (< 1 bar) are fine
   
   **Rationale**:
   - PM Core Tick frequency varies by position timeframes (1m, 15m, 1h, 4h positions)
   - Regime drivers are slower-moving signals (macro/meso/micro horizons)
   - Independent schedule simplifies implementation (no coordination needed)
   - Error recovery handles stale data (3-bar window with fallback to neutral)
   
   **Current Design**:
   - Micro (1m): Updates every minute
   - Meso (1h): Updates every hour
   - Macro (1d): Updates daily
   - Total: 24 Uptrend Engine runs per candle (acceptable per plan)

---

**Next Steps**: 
1. ✅ **RESOLVED**: Regime drivers DON'T go through PM Core Tick (Option 1)
2. ✅ **RESOLVED**: Bucket naming (use "small" not "micro")
3. ✅ **RESOLVED**: ALT/Bucket composite OHLC methodology specified
4. ✅ **RESOLVED**: Intent cap corrected to 0.4 (not 2.0)
5. ✅ **RESOLVED**: CoinGecko rate limits (well within free tier)
6. ✅ **RESOLVED**: Dominance treatment (as price-like, 1-100% = $1-$100)
7. ✅ **RESOLVED**: Scheduler integration details added
8. ✅ **RESOLVED**: Bootstrap retry logic specified
9. ✅ **RESOLVED**: UptrendEngine price reading for regime drivers
10. ✅ **RESOLVED**: _active_positions() updates specified
11. Begin Phase 1 implementation

---

## 15. Implementation Checklist

### Phase 1: Infrastructure
- [ ] Create `regime_price_data_ohlc` table schema file (`src/database/regime_price_data_ohlc_schema.sql`)
- [ ] Test Binance API endpoint (`/api/v3/klines`) - isolated test script
- [ ] Implement Regime Price Collector with:
  - [ ] Binance API backfill (with retry logic: 3 attempts, exponential backoff)
  - [ ] ALT composite OHLC computation (avg opens/closes, max highs, min lows, sum volumes)
  - [ ] Bucket composite OHLC computation (nano, small, mid, big) - same methodology as ALT
  - [ ] Dominance collection from CoinGecko (treat 1-100% as $1-$100)
  - [ ] OHLC rollup (1m → 1h → 1d) using standard methodology
- [ ] Create regime driver positions in `lowcap_positions` (auto-create on first run)
- [ ] Test price data collection end-to-end

### Phase 2: TA & State Computation
- [ ] Implement Regime TATracker (reuse `ta_utils.py`)
- [ ] Update UptrendEngine `_active_positions()` to include `status="regime_driver"`
- [ ] Update UptrendEngine price reading for regime drivers (read from `regime_price_data_ohlc`)
- [ ] Test state computation for all drivers/TFs (8 drivers × 3 TFs = 24 positions)
- [ ] Verify `uptrend_state_events` receives regime driver events

### Phase 3: Regime Mapper
- [ ] Implement Regime Mapper
- [ ] Test state → ΔA/ΔE mapping (baseline deltas)
- [ ] Test flag deltas (buy/trim/rebuy)
- [ ] Test transition detection (S1→S0, S2→S0, S3→S0)
- [ ] Test dominance inversion (negative weights)

### Phase 4: Integration
- [ ] Modify `compute_levers()` to:
  - [ ] Read regime state from `lowcap_positions` (status="regime_driver")
  - [ ] Apply execution TF multipliers
  - [ ] Apply driver weights
  - [ ] Sum regime contributions
  - [ ] Remove age/market cap boost components
- [ ] Update PM Core Tick:
  - [ ] Remove `phase_macro`, `phase_meso`, `cut_pressure` fetching
  - [ ] Update `_active_positions()` to exclude `status="regime_driver"`
  - [ ] Update `compute_levers()` call to new signature
- [ ] Add scheduler jobs to `run_trade.py`:
  - [ ] Regime Price Collector (1m, 1h, 1d schedules)
  - [ ] Regime TATracker (after price collector)
  - [ ] Regime Mapper (after Uptrend Engine)
- [ ] End-to-end testing

### Phase 5: Cleanup
- [ ] Remove old phase-based code from `compute_levers()`:
  - [ ] `_map_meso_policy()`
  - [ ] `_apply_macro()`
  - [ ] `_apply_cut_pressure()`
  - [ ] `_compute_age_component()`
  - [ ] `_compute_market_cap_component()`
- [ ] Remove `cut_pressure` computation from `bands_calc.py` (if not repurposed)
- [ ] Remove phase fetching from PM Core Tick (`_latest_phase()`, `_latest_cut_pressure()`)
- [ ] Update documentation

### Phase 6: Bootstrap & Production
- [ ] Implement `RegimeBootstrap` class with retry logic
- [ ] Integrate bootstrap into `run_trade.py` startup sequence
- [ ] Test bootstrap sequence with error recovery (Binance down, CoinGecko rate-limited, etc.)
- [ ] Verify all regime data populated before PM Core Tick starts
- [ ] Production deployment

