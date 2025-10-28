# PM System Architecture & Data Flow


## 🎯 **Overview**

The Position Manager (PM) system is a 4-layer architecture that processes lowcap positions through geometry analysis, tracking, and decision-making to execute trades.

## 📊 **System Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Positions     │    │   Geometry      │    │    Tracker      │    │   PM Core       │
│   Database      │───▶│   Builder       │───▶│   (5min)        │───▶│   (1h)          │
│                 │    │   (Daily)      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │                        │
         ▼                        ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Active Tokens   │    │ S/R Levels     │    │ Geometry Flags  │    │ A/E Levers      │
│ Contract Addrs  │    │ Diagonals       │    │ Break Detection │    │ Actions         │
│ Status: active  │    │ Fib Levels      │    │ Trend Changes   │    │ Decision Types  │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔄 **Data Flow & Timing**

### **1. Positions Database** (Continuous)
- **Source**: `lowcap_positions` table
- **Content**: Active token contracts, chains, status
- **Updates**: When new positions added/removed

### **2. Geometry Builder** (Daily at :10 UTC)
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py`
- **Frequency**: Once per day
- **Input**: 14 days of 1h OHLC data from `lowcap_price_data_ohlc`
- **Process**:
  - Finds swing highs/lows (percentage-based prominence)
  - Clusters into S/R levels with strength scoring
  - Fits diagonal trendlines (uptrend/downtrend segments)
  - Calculates Fibonacci levels with S/R correlation
- **Output**: Stored in `positions.features.geometry`
  ```json
  {
    "levels": {"sr_levels": [...]},
    "diagonals": {"uptrend_highs_1": {...}, "downtrend_lows_2": {...}},
    "trend_segments": 2,
    "updated_at": "2025-01-22T10:00:00Z"
  }
  ```

### Trend terminology (clarified)

- **Initial trend seed**: The very first trend inferred from ATH/ATL order.
  - ATL → ATH first ⇒ uptrend seed
  - ATH → ATL first ⇒ downtrend seed
  - Used only to bootstrap the first diagonals.
- **Current structural trend (`geometry_trend`)**: The trend geometry considers active after applying its own confirmation logic over time. Persisted at `geometry.current_trend.trend_type`. This may change as geometry confirms flips; it is slower and more conservative than tracker flips.

### Geometry outputs (contract)

- `levels.sr_levels`: horizontal lines and zones with `price`, `strength`, optional `source` (ATH/ATL/Fib/cluster).
- `diagonals`: one or more entries keyed like `uptrend_highs_1`, `uptrend_lows_1`, `downtrend_highs_1`, `downtrend_lows_1` each with:
  - `slope`, `intercept`, `anchor_time_iso`, `r2_score`, `confidence`.
- `current_trend`: `{ has_current, trend_type, lines_count }` plus optional `last_change` and `attempt` for audit.

### **3. Tracker** (Every 5 minutes)
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py`
- **Frequency**: Every 5 minutes (offset 0)
- **Input**: 
  - Stored geometry from positions
  - Latest 15m OHLC data for price comparison
- **Process**:
  - **S/R Analysis**: Split `sr_levels` into supports/resistances based on current price
  - **Diagonal Projection**: Project stored diagonals to "now". Tracker does not fit new lines.
    - `projected_price = slope × hours_since(anchor_time_iso) + intercept`
  - **Two trend notions (kept separately)**:
    - `geometry_trend` = `geometry.current_trend.trend_type` (structural, slow)
    - `tracker_trend` = maintained by tracker from 15m projections (nimble); may temporarily differ
  - **Decision rules**:
    - When trend is downtrend (by either notion): monitor only break ABOVE `downtrend_highs_*` ⇒ `diag_break = bull`, flip `tracker_trend` to uptrend.
    - When trend is uptrend: monitor break BELOW `uptrend_lows_*` ⇒ `diag_break = bear`, flip `tracker_trend` to downtrend. Also expose `uptrend_highs_*` as diagonal resistance and `uptrend_lows_*` as diagonal support for runtime logic/zones.
    - If multiple candidate lines exist per side, select deterministically by `confidence` (fallback `r2_score`).
  - **Retrace Logic**: 68–100% retrace handling from breakout tops/bottoms
- **Output**: Updates `positions.features.geometry` with flags
  ```json
  {
    "sr_break": "bull|bear|none",
    "sr_conf": 0.0-1.0,
    "diag_break": "bull|bear|none", 
    "diag_conf": 0.0-1.0,
    "diag_status": {"uptrend_highs_1": {"projected_price_native": 0.0, "above_below": "above|below", "state": "none|breakout|retrace_ready"}},
    "diag_levels": {"diag_support": {"price": 0.0, "strength": 0.0}, "diag_resistance": {"price": 0.0, "strength": 0.0}},
    "geometry_trend": "uptrend|downtrend|null",
    "tracker_trend": "uptrend|downtrend|null",
    "tracker_trend_changed": true,
    "tracker_trend_change_time": "2025-01-22T15:05:00Z",
    "tracked_at": "2025-01-22T15:05:00Z"
  }
  ```

### **3.1. TA Tracker (Every 5 minutes)**
- Purpose: Compute fast TA signals independent of geometry; store under `features.ta` for PM Core and future gating.
- Data Sources:
  - 1m: `lowcap_price_data_1m` → OBV, EMA_long(60), consecutive-below counter
  - 15m: `lowcap_price_data_ohlc` → RSI(14), VO_z (z-score of volume over rolling 30 bars), ATR(14)
- Storage Contract (`features.ta`):
  ```json
  {
    "ta": {
      "rsi": { "value": 54.2, "divergence": "bull|bear|hidden_bull|hidden_bear|none", "lookback_bars": 15 },
      "obv": { "value": 12345.0, "slope_z_per_bar": 0.07, "divergence": "bull|bear|hidden_bull|hidden_bear|none", "window_bars": 4 },
      "volume": { "vo_z_15m": 0.9, "window_bars": 30, "breakout_vo_z_peak": 1.4 },
      "ema": { "ema_long_1m": 0.0000062, "consec_below_ema_long": 3, "ema_mid_15m": 0.0000065, "ema_mid_15m_break": false },
      "atr": { "atr_15m": 0.0000008 },
      "pillars": { "obv_rising": true, "vo_moderate": true, "rsi_bull_div": false, "count": 2 },
      "updated_at": "2025-01-22T15:05:00Z"
    }
  }
  ```
- RSI Divergence Method:
  - Compute RSI(14) on 15m closes; detect pivots using 5-bar swing highs/lows; compare last two pivots against price pivots to classify divergences.
- OBV Slope Normalization:
  - OBV from 1m; linear regression slope over N bars (mode-dependent); z-score slope per bar within the window so thresholds are coin-agnostic.
- EMAs vs Structure Policy:
  - Structure = geometry boundaries (S/R, diagonals, breakout line). Structure defines thesis validity.
  - EMAs = dynamic baselines for trailing/emergency control; track crosses and `consec_below_ema_long`.
- Historical Data Requirements:
  - Minimum: 60×1m bars for EMA_long; 30×15m bars for VO_z window; 14×15m for RSI/ATR; 6–10×1m bars for OBV slope window. Older data improves stability.
- Output does not duplicate geometry flips; it only provides TA features/flags.

#### Mode-Dependent TA Gates (Applied later by PM Core)
- Envelope 1 (Support/Wedge): pillars = {RSI bull divergence, OBV slope_z rising, VO_z ≥ +0.3}
  - Aggressive: any 1; Normal: any 2; Patient: all 3
  - EMA preference: Aggressive none; Normal require no `ema_mid_15m_break`; Patient require reclaim of `ema_long_1m`
- Envelope 2 (Breakout/Retest): after confirmed breakout
  - Retest band (simple v1): within +0.25 × ATR(15m) above breakout line B; reject deeper undercuts
  - Pillars: Aggressive any 1 of {VO_z ≥ +0.5, OBV inflection > 0, RSI > 50 with bull divergence context}; Normal any 2; Patient all 3
- Exhaustion TPs inside resistance zones (diagonal upper or horizontal S/R)
  - Aggressive E: thresholds tight (OBV roll ≤ −0.05/3 bars, VO_z climax ≥ +1.2)
  - Normal E: medium (≤ −0.075/4, ≥ +1.5)
  - Patient E: strict (≤ −0.10/6, ≥ +2.0)
- Emergency/trail exits
  - EMA_long gap: sell when close < EMA_long − k × ATR(1m); k Agg 0.25 / Norm 0.40 / Pat 0.60
  - Arm `trail_pending` on fewer consecutive closes for Aggressive E, more for Patient E
  - Accept a single full-body close below `ema_mid_15m` as sufficient for Aggressive E; stricter for Patient

#### Examples

- Uptrend (no flip):
```json
{
  "geometry_trend": "uptrend",
  "tracker_trend": "uptrend",
  "diag_levels": {
    "diag_support": {"price": 0.0000061, "strength": 0.82},
    "diag_resistance": {"price": 0.0000069, "strength": 0.78}
  },
  "diag_break": "none"
}
```

- Downtrend bull breakout (flip tracker):
```json
{
  "geometry_trend": "downtrend",
  "tracker_trend": "uptrend",
  "tracker_trend_changed": true,
  "diag_break": "bull",
  "diag_conf": 0.7
}
```

### **4. PM Core Tick** (Every hour)
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- **Frequency**: Every hour (offset 6)
- **Input**: 
  - Geometry flags from tracker
  - Phase state (macro/meso/micro)
  - Portfolio context
- **Process**:
  - Computes A/E levers based on geometry + TA + intent
  - Plans actions (add/trim/demote/hold)
  - Writes decision strands
- **Output**: Action decisions for execution
  ```json
  {
    "decision_type": "add|trim|demote|hold",
    "size_frac": 0.0-1.0,
    "reasons": {"sr_break": "bull", "diag_conf": 0.8, ...}
  }
  ```

## 🎯 **Key Components**

### **Geometry System**
- **Purpose**: Structural analysis (S/R, diagonals, Fibs)
- **Timing**: Daily (sufficient for structural changes)
- **Data**: 1h OHLC for clean trendlines
- **Output**: Static levels and trendlines

### **Tracker System**
- **Purpose**: Dynamic break detection and trend changes
- **Timing**: 5 minutes (responsive to price action)
- **Data**: 15m OHLC for confirmation
- **Output**: Break flags and trend state

### **PM Core System**
- **Purpose**: Decision making and action planning
- **Timing**: Hourly (strategic decisions)
- **Data**: Geometry flags + market context
- **Output**: Trade decisions

Clarification on consumption and divergence handling
- PM Core primarily keys off tracker flags (`sr_break`, `diag_break`, `diag_conf/strength`) for responsiveness.
- `geometry_trend` is used as structural context. If `tracker_trend` temporarily differs from `geometry_trend`, policy may reduce sizes or require stronger confidence.

## 🔧 **Data Structure Mappings**

### **Geometry → Tracker**
```python
# Geometry outputs
geometry = {
    "levels": {"sr_levels": [{"price": 0.000005, "strength": 8}]},
    "diagonals": {"uptrend_highs_1": {"slope": 0.000001, "intercept": 0.000004, "anchor_time_iso": "2025-01-20T10:00:00Z"}}
}

# Tracker processes
current_price = 0.000006
supports = [level for level in sr_levels if current_price > level["price"]]
resistances = [level for level in sr_levels if current_price < level["price"]]
```

### **Tracker → PM Core**
```python
# Tracker outputs
geometry_flags = {
    "sr_break": "bull",
    "sr_conf": 0.8,
    "diag_break": "none",
    "diag_conf": 0.0
}

# PM Core processes
if sr_break == "bull" and sr_conf >= 0.5:
    # Increase A lever, plan add action
    a_final += 0.15 * sr_conf
```

## ⚡ **Performance Considerations**

### **Data Sources**
- **Geometry**: Uses 1h OHLC (cleaner, less data)
- **Tracker**: Uses 15m OHLC (responsive, manageable)
- **PM Core**: Uses flags only (lightweight)

### **Timing Optimization**
- **Geometry**: Daily (structural changes are slow)
- **Tracker**: 5min (price breaks need responsiveness)
- **PM Core**: Hourly (strategic decisions don't need 5min updates)

### **Database Efficiency**
- **Geometry**: Stores computed levels (no recalculation)
- **Tracker**: Reads stored geometry + latest price
- **PM Core**: Reads flags + market context

## 🚀 **Future Enhancements**

### **Price Monitor Integration**
- **Current**: Tracker updates flags
- **Future**: Price Monitor executes trades based on flags
- **Timing**: 30-second price monitoring for entries/exits

### **Real-time Execution**
- **Current**: Hourly decision making
- **Future**: Sub-minute execution for breakouts/retests
- **Architecture**: Tracker → Price Monitor → Trade Execution

## 📋 **Configuration**

### **Environment Variables**
```bash
GEOMETRY_TRACKER_ENABLED=1  # Enable tracker
ACTIONS_ENABLED=1           # Enable PM actions
GEOM_LOOKBACK_DAYS=14      # Geometry analysis window
```

### **Scheduling**
```python
# run_social_trading.py
schedule_5min(0, tracker_main)      # Every 5 minutes
schedule_hourly(6, pm_core_main)    # Every hour at :06
schedule_daily(10, geometry_main)   # Daily at :10
```

## 🔍 **Debugging & Monitoring**

### **Key Logs**
- **Geometry**: "Geometry built for X positions"
- **Tracker**: "Geometry tracker failed" (if errors)
- **PM Core**: "pm_core_tick wrote X strands for Y positions"

### **Data Verification**
- Check `positions.features.geometry` for stored levels
- Verify `sr_break`/`diag_break` flags are updating
- Monitor action decisions in `ad_strands` table

---

*This architecture ensures responsive geometry tracking while maintaining efficient resource usage and clear separation of concerns.*
