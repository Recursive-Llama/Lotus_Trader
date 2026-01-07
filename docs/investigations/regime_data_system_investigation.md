# Regime Data System - Full Investigation

**Date**: 2025-01-XX  
**Status**: System is partially working, but has data gaps  
**Priority**: Medium (not critical, but needs attention)

---

## Executive Summary

The regime data system is **architecturally complete and running**, but has **data collection gaps** that prevent it from fully functioning. The system is scheduled correctly and the pipeline executes, but:

1. ✅ **Working**: ALT composite (1m), dominance collection, bucket composites
2. ⚠️ **Partial**: BTC data (missing from majors_price_data_ohlc for some timeframes)
3. ❌ **Broken**: ALT composite for 1h/1d (missing component data)

The system **is being used** by `compute_levers()` to calculate A/E scores, but with incomplete data, the regime signals may not be accurate.

---

## 1. What is the Regime System?

The regime system is a **market regime detection and A/E scoring system** that replaces the old phase-based approach. Instead of using string phases like "dip", "good", "euphoria", it uses **Uptrend Engine states** (S0/S1/S2/S3) from multiple market drivers to compute Aggressiveness (A) and Exitness (E) scores.

### 1.1 Core Concept

The system tracks **5 regime drivers** across **3 timeframes**:

**Drivers:**
1. **BTC** - Bitcoin trend (affects all tokens)
2. **ALT** - Altcoin composite (SOL/ETH/BNB/HYPE average)
3. **BUCKET** - Market cap bucket composites (nano/small/mid/big)
4. **BTC.d** - BTC dominance (inverted - uptrend = risk-off)
5. **USDT.d** - USDT dominance (inverted, 3x weight - uptrend = strong risk-off)

**Timeframes:**
- **Macro (1d)** - Slow shifts, big picture (weight: 0.50)
- **Meso (1h)** - Main operational timeframe (weight: 0.40)
- **Micro (1m)** - Tactical adjustments (weight: 0.10)

**Total**: 5 drivers × 3 timeframes = **15 regime channels** per token

### 1.2 How It Works

For each token, the system:
1. Reads Uptrend Engine states from all 5 drivers across 3 timeframes
2. Maps states/flags to ΔA/ΔE deltas using lookup tables
3. Applies driver weights (BTC=1.0, ALT=1.5, BUCKET=3.0, BTC.d=-1.0, USDT.d=-3.0)
4. Applies timeframe multipliers based on execution timeframe
5. Sums all contributions to get final A/E scores
6. Adds intent deltas (hi_buy, profit, sell, mock)
7. Clamps to [0, 1]

---

## 2. System Architecture

The regime system consists of **4 main components**:

### 2.1 Regime Price Collector (`regime_price_collector.py`)

**Purpose**: Collects OHLC data for all regime drivers

**What it does:**
- **BTC**: Reads from `majors_price_data_ohlc` (written by Hyperliquid WS or Binance backfill)
- **ALT**: Computes composite from SOL/ETH/BNB/HYPE in `majors_price_data_ohlc`
- **Buckets**: Computes composites from tokens in each bucket (reads from `lowcap_price_data_ohlc`)
- **Dominance**: Fetches BTC.d and USDT.d from CoinGecko API (1m only, then rolls up to 1h/1d)

**Output**: Writes to `regime_price_data_ohlc` table

**Schedule**: 
- 1m: Every minute (via `run_trade.py`)
- 1h: Every hour (via `run_trade.py`)
- 1d: Daily (via `run_trade.py`)

### 2.2 Regime TA Tracker (`regime_ta_tracker.py`)

**Purpose**: Computes technical analysis indicators for regime drivers

**What it does:**
- Reads OHLC from `regime_price_data_ohlc`
- Computes EMAs (20, 30, 50, 60, 144, 250, 333), slopes, ATR, ADX, RSI, separations
- Writes TA data to `lowcap_positions` table (status='regime_driver')

**Output**: Updates `features.ta` in regime driver positions

**Schedule**: Runs after price collection (via `regime_runner.py`)

### 2.3 Uptrend Engine V4 (`uptrend_engine_v4.py`)

**Purpose**: Computes S0/S1/S2/S3 states and flags for regime drivers

**What it does:**
- Reads TA data from regime driver positions
- Runs Uptrend Engine state machine
- Computes states (S0/S1/S2/S3), flags (buy, trim, rebuy), transitions
- Writes to `features.uptrend_engine_v4` in regime driver positions

**Output**: Updates `features.uptrend_engine_v4` in regime driver positions

**Schedule**: Runs after TA tracker (via `regime_runner.py`)

### 2.4 Regime A/E Calculator (`regime_ae_calculator.py`)

**Purpose**: Computes final A/E scores from regime states

**What it does:**
- Reads regime driver states from `lowcap_positions` (status='regime_driver')
- Applies state/flag/transition delta tables
- Applies driver weights and timeframe multipliers
- Sums contributions across all drivers/timeframes
- Adds intent deltas (capped at ±0.4)
- Returns final A/E scores

**Output**: Used by `compute_levers()` in `pm/levers.py`

**Schedule**: Called on-demand when `compute_levers()` is invoked

---

## 3. Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Price Collection (regime_price_collector.py)             │
│    - Collects BTC from majors_price_data_ohlc               │
│    - Computes ALT composite from SOL/ETH/BNB/HYPE           │
│    - Computes bucket composites from lowcap_price_data_ohlc  │
│    - Fetches dominance from CoinGecko                        │
│    └─> Writes to regime_price_data_ohlc                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. TA Computation (regime_ta_tracker.py)                     │
│    - Reads OHLC from regime_price_data_ohlc                  │
│    - Computes EMAs, slopes, ATR, ADX, RSI                    │
│    └─> Updates features.ta in lowcap_positions               │
│        (status='regime_driver')                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Uptrend Engine (uptrend_engine_v4.py)                    │
│    - Reads TA from regime driver positions                   │
│    - Computes S0/S1/S2/S3 states                            │
│    - Computes flags (buy, trim, rebuy)                      │
│    - Detects transitions (S3→S0, etc.)                      │
│    └─> Updates features.uptrend_engine_v4                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. A/E Calculation (regime_ae_calculator.py)                 │
│    - Reads states from regime driver positions               │
│    - Applies delta tables (state/flags/transitions)           │
│    - Applies driver weights (BTC=1.0, ALT=1.5, etc.)        │
│    - Applies timeframe multipliers                          │
│    - Sums contributions                                      │
│    - Adds intent deltas                                      │
│    └─> Returns (A, E) scores                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Usage (pm/levers.py -> compute_levers())                 │
│    - Called for each token in PM Core Tick                  │
│    - Uses A/E to determine position sizing and exit logic    │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Database Schema

### 4.1 `regime_price_data_ohlc`

Stores OHLC data for all regime drivers:

```sql
CREATE TABLE regime_price_data_ohlc (
    driver TEXT NOT NULL,              -- 'BTC', 'ALT', 'nano', 'small', 'mid', 'big', 'BTC.d', 'USDT.d'
    timeframe TEXT NOT NULL,           -- '1m', '1h', '1d'
    timestamp TIMESTAMPTZ NOT NULL,
    book_id TEXT NOT NULL DEFAULT 'onchain_crypto',
    open_usd NUMERIC NOT NULL,
    high_usd NUMERIC NOT NULL,
    low_usd NUMERIC NOT NULL,
    close_usd NUMERIC NOT NULL,
    volume NUMERIC NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'binance',  -- 'binance', 'composite', 'coingecko'
    component_count INT,                      -- Number of tokens in composite
    PRIMARY KEY (driver, book_id, timeframe, timestamp)
);
```

### 4.2 Regime Driver Positions (`lowcap_positions`)

Regime drivers are stored as special positions:

```sql
-- Example regime driver position:
token_contract: "regime_btc" | "regime_alt" | "regime_nano" | etc.
token_chain: "regime"
token_ticker: "BTC" | "ALT" | "nano" | etc.
timeframe: "1d" | "1h" | "1m"  -- Regime timeframe
status: "regime_driver"
features: {
  "ta": {...},                    -- TA indicators
  "uptrend_engine_v4": {          -- Uptrend Engine states/flags
    "state": "S3",
    "buy_signal": false,
    "trim_flag": true,
    "prev_state": "S2",
    ...
  }
}
```

---

## 5. Current Status (From Logs)

### 5.1 What's Working ✅

1. **ALT Composite (1m)**: Successfully computing and writing 1000+ bars
2. **Dominance Collection**: BTC.d and USDT.d being collected from CoinGecko
3. **Dominance Rollup**: Successfully rolling up 1m → 1h → 1d
4. **Bucket Composites**: System attempts to compute (no errors in logs)
5. **Scheduling**: System runs every minute (1m) and hourly (1h)

### 5.2 What's Partially Working ⚠️

1. **BTC Data**: 
   - **Issue**: "No BTC bar found in majors_price_data_ohlc for 1m/1h/1d"
   - **Cause**: BTC data may not be in `majors_price_data_ohlc` for these timeframes
   - **Impact**: BTC regime driver has no price data → no TA → no state → no contribution to A/E
   - **Fix Needed**: Ensure BTC is written to `majors_price_data_ohlc` for all timeframes

### 5.3 What's Broken ❌

1. **ALT Composite (1h/1d)**:
   - **Issue**: "Missing ALT components for 1h/1d: ['SOL', 'ETH', 'BNB', 'HYPE']"
   - **Cause**: SOL/ETH/BNB/HYPE data exists in `majors_price_data_ohlc` but not for 1h/1d timeframes
   - **Impact**: ALT composite cannot be computed for 1h/1d → no ALT regime signal for meso/macro
   - **Fix Needed**: Ensure majors are rolled up to 1h/1d, or backfill from Binance

---

## 6. Integration Points

### 6.1 `compute_levers()` Integration

The regime system is **actively used** in `pm/levers.py`:

```python
def compute_levers(
    features: Dict[str, Any],
    bucket_context: Dict[str, Any] | None = None,
    position_bucket: str | None = None,
    bucket_config: Dict[str, Any] | None = None,
    exec_timeframe: str = "1h",
) -> Dict[str, Any]:
    # ...
    calculator = RegimeAECalculator()
    a_regime, e_regime = calculator.compute_ae_for_token(
        token_bucket=position_bucket or "small",
        exec_timeframe=exec_timeframe,
        intent_delta_a=intent_delta_a,
        intent_delta_e=intent_delta_e,
    )
    # ...
```

**Called from**: `pm_core_tick.py` for every position

### 6.2 Scheduling

In `run_trade.py`:

```python
# 1 Minute Jobs
tasks.append(asyncio.create_task(
    self._schedule_at_interval(60, 
        lambda: run_regime_pipeline(timeframe="1m"), 
        "Regime 1m")
))

# Hourly Jobs
tasks.append(asyncio.create_task(
    self._schedule_hourly(1, 
        lambda: run_regime_pipeline(timeframe="1h"), 
        "Regime 1h")
))
```

---

## 7. State/Flag/Transition System

### 7.1 States

- **S0**: Downtrend/bad → A↓, E↑ (risk-off)
- **S1**: Early uptrend/best asymmetry → A↑↑, E↓ (best buy zone)
- **S2**: No man's land → A↓ (vs S1), E↑ (cautious)
- **S3**: Confirmed uptrend → A↑, E slightly ↓ (ride the trend)

### 7.2 Flags

- **Buy flag (S1)**: Strong A↑ pulse
- **Trim flag (S2/S3)**: E↑↑, A↓ (harvest profits)
- **Rebuy flag (S2/S3)**: A↑↑, E↓ (reload after trim)

### 7.3 Transitions (Emergency Exits)

- **S3→S0**: Nuclear event → A↓↓↓, E↑↑↑
- **S2→S0**: Risk-off pulse → A↓↓, E↑↑
- **S1→S0**: Early failure → A↓, E↑

### 7.4 Delta Tables

Located in `regime_ae_calculator.py`:

```python
STATE_DELTAS = {
    "S0": (-0.30, +0.30),  # (ΔA, ΔE)
    "S1": (+0.25, -0.15),
    "S2": (+0.10, +0.05),
    "S3": (+0.20, -0.05),
}

FLAG_DELTAS = {
    ("S1", "buy_signal"): (+0.20, -0.10),
    ("S2", "trim_flag"): (-0.20, +0.25),
    ("S3", "trim_flag"): (-0.25, +0.30),
    # ...
}
```

---

## 8. Issues Found

### 8.1 Missing BTC Data

**Symptom**: Logs show "No BTC bar found in majors_price_data_ohlc for 1m/1h/1d"

**Root Cause**: BTC may not be written to `majors_price_data_ohlc` for these timeframes, or the query is looking in the wrong place.

**Impact**: BTC regime driver has no price data → no TA → no state → no contribution to A/E for BTC driver.

**Fix**: 
1. Check if BTC is being written to `majors_price_data_ohlc` by Hyperliquid WS
2. If not, ensure Binance backfill writes BTC for all timeframes
3. Verify the query in `regime_price_collector._get_latest_major_bar()` is correct

### 8.2 Missing ALT Components for 1h/1d

**Symptom**: Logs show "Missing ALT components for 1h/1d: ['SOL', 'ETH', 'BNB', 'HYPE']"

**Root Cause**: SOL/ETH/BNB/HYPE data exists in `majors_price_data_ohlc` but only for 1m timeframe (from Hyperliquid WS). The system needs 1h/1d data to compute ALT composite for meso/macro.

**Impact**: ALT composite cannot be computed for 1h/1d → no ALT regime signal for meso/macro timeframes.

**Fix**:
1. Ensure majors are rolled up to 1h/1d (check `OneMinuteRollup` or `GenericOHLCRollup`)
2. Or backfill majors from Binance for 1h/1d timeframes
3. Verify the query in `regime_price_collector._compute_alt_composite()` handles all timeframes

### 8.3 Data Freshness

**Observation**: Dominance values in logs are static (BTC.d=57.24%, USDT.d=6.06%) across multiple runs.

**Possible Issue**: CoinGecko API may be rate-limited or cached, or the system is not fetching fresh data.

**Fix**: Verify CoinGecko API is returning fresh data, check rate limits.

---

## 9. Verification Steps

To verify the system is working correctly:

### 9.1 Check Price Data

```sql
-- Check if BTC data exists for all timeframes
SELECT driver, timeframe, COUNT(*) as bar_count, MAX(timestamp) as latest
FROM regime_price_data_ohlc
WHERE driver = 'BTC'
GROUP BY driver, timeframe;

-- Check ALT composite data
SELECT driver, timeframe, COUNT(*) as bar_count, MAX(timestamp) as latest
FROM regime_price_data_ohlc
WHERE driver = 'ALT'
GROUP BY driver, timeframe;

-- Check dominance data
SELECT driver, timeframe, COUNT(*) as bar_count, MAX(timestamp) as latest
FROM regime_price_data_ohlc
WHERE driver IN ('BTC.d', 'USDT.d')
GROUP BY driver, timeframe;
```

### 9.2 Check Regime Driver Positions

```sql
-- Check if regime driver positions exist
SELECT token_ticker, timeframe, status, 
       features->'uptrend_engine_v4'->>'state' as state,
       features->'uptrend_engine_v4'->>'buy_signal' as buy_signal,
       features->'uptrend_engine_v4'->>'trim_flag' as trim_flag
FROM lowcap_positions
WHERE status = 'regime_driver'
ORDER BY token_ticker, timeframe;
```

### 9.3 Test A/E Calculation

```bash
# Run regime summary
python -m src.intelligence.lowcap_portfolio_manager.jobs.regime_runner --summary

# Test A/E calculation for a specific bucket
python -m src.intelligence.lowcap_portfolio_manager.jobs.regime_ae_calculator \
    --bucket small --timeframe 1h
```

---

## 10. Recommendations

### 10.1 Immediate Fixes

1. **Fix BTC Data Collection**:
   - Verify BTC is written to `majors_price_data_ohlc` for all timeframes
   - If not, add Binance backfill for BTC 1h/1d
   - Fix query in `regime_price_collector._get_latest_major_bar()`

2. **Fix ALT Composite for 1h/1d**:
   - Ensure majors are rolled up to 1h/1d
   - Or backfill majors from Binance for 1h/1d
   - Verify rollup logic in `OneMinuteRollup` or `GenericOHLCRollup`

3. **Verify Dominance Freshness**:
   - Check CoinGecko API rate limits
   - Ensure fresh data is being fetched (not cached)

### 10.2 Monitoring

1. **Add Health Checks**:
   - Check if all regime drivers have recent data (< 5 minutes old for 1m, < 1 hour for 1h)
   - Alert if any driver is missing data

2. **Add Metrics**:
   - Track how many regime drivers have valid states
   - Track A/E calculation success rate
   - Track data freshness per driver/timeframe

### 10.3 Testing

1. **Unit Tests**:
   - Test ALT composite calculation with missing components
   - Test A/E calculation with missing driver data
   - Test rollup logic for dominance

2. **Integration Tests**:
   - Test full pipeline (price → TA → uptrend → A/E)
   - Test with missing data scenarios
   - Test with partial data scenarios

---

## 11. Conclusion

The regime data system is **architecturally sound and mostly working**, but has **data collection gaps** that prevent it from fully functioning. The system is:

- ✅ **Scheduled correctly** (runs every minute/hour)
- ✅ **Pipeline executes** (price → TA → uptrend → A/E)
- ✅ **Integrated with PM Core** (used in `compute_levers()`)
- ⚠️ **Missing BTC data** for some timeframes
- ❌ **Missing ALT components** for 1h/1d

**Priority**: Medium - The system will work with partial data (falls back to neutral A/E), but won't be accurate until all data is collected.

**Next Steps**:
1. Fix BTC data collection
2. Fix ALT composite for 1h/1d
3. Add monitoring/health checks
4. Add unit/integration tests

---

## Appendix: Key Files

- `src/intelligence/lowcap_portfolio_manager/jobs/regime_price_collector.py` - Price collection
- `src/intelligence/lowcap_portfolio_manager/jobs/regime_ta_tracker.py` - TA computation
- `src/intelligence/lowcap_portfolio_manager/jobs/regime_ae_calculator.py` - A/E calculation
- `src/intelligence/lowcap_portfolio_manager/jobs/regime_runner.py` - Pipeline orchestration
- `src/intelligence/lowcap_portfolio_manager/pm/levers.py` - Integration point
- `src/database/regime_price_data_ohlc_schema.sql` - Database schema
- `docs/inprogress/Regime_engine.md` - Full specification



