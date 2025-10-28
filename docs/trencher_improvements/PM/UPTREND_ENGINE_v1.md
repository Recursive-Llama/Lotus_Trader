# Uptrend Engine v1

Note: Canonical state definitions, thresholds, constants, unified payload schema, and event hooks are defined in `SM_UPTREND.MD`. This document references that spec and focuses on system wiring and usage.

## 🎯 **Executive Summary**

**Purpose**: Automated uptrend detection, entry, and management system for lowcap cryptocurrency trading.

**Core Philosophy**: "Trade confirmed uptrends, ride momentum, exit on structure failure"

**Key Innovation**: Multi-sensor confirmation system combining structural analysis (diagonals), momentum flow (EMAs), trend strength (ADX), and energy signals (RSI/volume) to identify high-probability continuation setups.

**Target**: Multi-day trend riding with precise entry timing and clean exit management.

## 📊 **System Overview**

### **Input Data Sources**
- **Price Data**: 1m/15m/1h OHLCV from `lowcap_price_data_ohlc`
- **Geometry**: Diagonals and S/R levels from existing geometry system
- **TA Indicators**: RSI, EMAs, ADX, ATR, VO_z computed on 15m/1h frames
- **Market Context**: 50+ coin universe with relative strength analysis

### **Output Signals**
- **Opportunity Ranking**: Composite score (0-100) for all monitored coins
- **Entry Triggers**: Three distinct setup types with precise timing
- **Exit Signals**: Planned profit-taking and emergency invalidation
- **Position Management**: Dynamic sizing based on risk/reward ratios
-
- **Unified State Output**: All state emissions follow the unified payload schema from `SM_UPTREND.MD`.
- **Events**: Emits `s1_breakout`, `s2_support_touch`, `s3_sr_reclaim`, `s4_euphoria_on/off`, `s5_reentry_on/off`, `emergency_exit_on/off` with levels and key scores (see SM).

### **System Timing**
- **Scanning**: Every 5 minutes for opportunity detection
- **Decision Making**: Hourly for strategic position adjustments  
- **Execution**: Real-time for entry/exit triggers
- **Trend Duration**: Multi-day position holding with trail management

## 🔧 **Core Indicators (6-Sensor System)**

### **Multi-Timeframe Interaction**
- **15m = Trigger Frame**: Compression detection, VO_z windows, expansion pulses
- **1h = Trend Frame**: State machine, Setup A/B/C detection, ADX strength
- **4h = Context Filter**: Only take 1h flips in 4h up-bias (optional robustness)
- **Integration**: 15m feeds 1h logic, 4h provides market regime context

### **1. Structure Sensor - Diagonals**
- **Purpose**: Detect structural regime changes and trend channels
- **Data**: Geometry diagonals from daily analysis
- **Confidence Weighting**: 0.1 × bars (more accurate over time)
- **Signals**: 
  - Downtrend diagonal break = structural shift (with EMA/ADX confirmation)
  - Uptrend diagonal bounds = dynamic support/resistance (guide, not standalone)
  - Past trend diagonals = key resistance levels for parabolic moves
- **Usage**: Always combined with other signals, never standalone triggers

### **2. Flow Sensor - EMAs**
- **Purpose**: Confirm momentum direction and trend health
- **Configuration**: EMA 20/50/200 on 1h, EMA 20 on 15m
- **Signals**:
  - EMA 20 > EMA 50 with EMA 50 rising = uptrend confirmation
  - Price above EMA 20(15m) = entry timing
  - Close below EMA 50 = trend invalidation

### **3. Strength Sensor - ADX**
- **Purpose**: Measure trend phase and momentum amplitude
- **Configuration**: ADX 14 on 1h timeframe
- **Signals**:
  - ADX < 20 = compression phase (pre-breakout context)
  - ADX 20-35 = emerging trend (sweet spot for entries)
  - ADX > 40 = mature trend (watch for exhaustion)
  - Rising ADX = trend strengthening
  - Falling ADX = trend weakening

### **4. Energy Sensor - RSI**
- **Purpose**: Detect regime shifts and trend exhaustion
- **Configuration**: RSI 14 on 1h and 15m
- **Signals**:
  - RSI 40-80 = healthy uptrend regime
  - RSI divergence + structure failure = exit signal
  - RSI < 30 = oversold (potential reversal)

### **5. Volume Sensor - VO_z Windows**
- **Purpose**: Confirm thrust on breakouts and retests
- **Configuration**: 15m volume z-score over 30-bar window (for setup windows). See `SM_UPTREND.MD` for 1h VO_z computation (log-volume EWMA z with winsorization and caps) used by the state machine.
- **Signals**:
  - VO_z window (≥3 spikes of z≥2.0 in 20 bars) = thrust confirmation
  - Use only to confirm A/B entries, not as standalone triggers
  - Ignore isolated volume spikes

### **6. Volatility Sensor - ATR**
- **Purpose**: Position sizing, invalidation levels, and trail management
- **Configuration**: ATR 14 on 1h for stops, 15m for entries
- **Signals**:
  - ATR-based invalidation bands
  - Chandelier trail calculations
  - Volatility-adjusted position sizing

## 🎯 **Uptrend State Machine (S0-S5)**

### **S0 - Downtrend (Baseline)**
- **Price**: ≤ EMA 50(1h) or EMA 20 ≤ EMA 50(1h)
- **Structure**: Descending diagonal intact
- **Strength**: ADX ≤ 20 or falling
- **Watchlist**: 15m compression detected (ATR slope < 0 for ≥60 bars) → tag as "coiling"

### **S1 - Breakout Probe (First Structural Break)**
- **Trigger**: 1h close above descending diagonal (confidence-weighted) OR 1h close above EMA 50 + diagonal pierced
- **Requirement**: Expansion pulse within 16×15m bars (4 hours):
  - ATR slope crosses > 0 AND true range ≥ ATR(14) (require 2 consecutive positive readings)
  - OR VO_z window (≥3 spikes of z≥2.0 in 20 bars)
- **Failure**: No pulse in time → revert to S0
- **Freshness Decay**: If no Setup A/B triggers within 48 hours after S2, decay to S3 passive or revert to S0
- **Note**: Diagonal break alone is insufficient; requires EMA/ADX confirmation

### **S2 - Trend Confirmed (New Uptrend)**
- **Structure**: 1h close above diagonal
- **Flow**: EMA 20 > EMA 50, EMA 50 rising
- **Energy**: Expansion pulse observed on 15m
- **Strength**: ADX(1h) > 20 and rising (optional)
- **Action**: Anchor AVWAP(flip), open to Setup A/B entries
- **Freshness Timer**: Start 48-hour countdown for Setup A/B triggers

### **S3 - Continuation (Healthy Uptrend)**
- **Maintain**: Price > EMA 50(1h) and > AVWAP(flip)
- **Structure**: Higher highs/lows on 1h
- **Energy**: ADX flat/rising OR ATR slope ≥ 0
- **Add-ons**: New compression→pulse cycles = Setup C opportunities

<!-- Removed: S3.5 Cooling; cooling/re-entry is covered by S5 per SM spec. -->

### **S4 - Euphoria / Overextension (Exit Management Phase)**
- **Trigger**: `euphoria_curve ≥ 0.70` for 3 consecutive 1h bars (per SM)
- **Exit Gate**: Exits fire only when BOTH `geometry_touch` (upper diagonal/major S/R/extension target) AND `exhaustion_confirmed` (≥2 of HH-fail, ADX roll, ATR cool, giveback; ignore ADX-roll if peak<28)
- **Execution**: 30% fractal sells per AND-event; 1-bar grace after S4 activation before executing exits
- **Note**: See `SM_UPTREND.MD` for exact computations and diagnostics

### **S5 - Re-Entry / Cooling Consolidation**
- **Trigger**: As per SM — `cooldown_integrity ≥ 0.6` AND `reentry_readiness ≥ 0.6` (with hysteresis)
- **Behavior**: Re-engage near EMA50/diagonal halo when structure cools but remains intact; momentum restart returns to S3
- **Invalidation**: Emergency exit protocol remains separate and state-agnostic (see below)

### **Emergency Exit (State-Agnostic)**
- **Trigger**: 1h close below EMA50 AND lower ascending diagonal → bounce-exit protocol
- **Bounce protocol**: Snapshot levels; halo= max(0.5×ATR, 3%); T=6 bars (T=3 in news windows); exit on bounce to zone or earlier fail-safes; reclaim of either level with VO_z burst cancels when EMA–diagonal spread >1.5×ATR
- See `SM_UPTREND.MD` for exact details

## 🚀 **Entry Types (3 Setups)**

### **Setup A - Trend Change Entry (Downtrend → Uptrend)**
- **Context**: Diagonal break from downtrend to uptrend (S1→S2 transition)
- **Trigger**: Break above descending diagonal + EMA confirmation (EMA 20 > EMA 50, EMA 50 rising)
- **Entry**: Retest of the **diagonal** that was broken (if price comes back that low)
- **Fallback**: If diagonal retest doesn't occur, convert to Setup B (S/R level retest)
- **Confirmation**: RSI > 40, bullish engulfing or strong close on 15m
- **Invalidation**: Break back into downtrend (diagonal break fails, trend change invalidated)
- **Why It Works**: We're buying the trend change at the source (the diagonal that defined the old downtrend)
- **Risk**: Medium - trend changes can fail, but we have clear invalidation

### **Setup B - Uptrend Continuation Entry (S/R Flip)**
- **Context**: Within an existing uptrend (S2-S3 states)
- **Trigger**: Break of horizontal S/R level (resistance → support flip)
- **Entry**: Retest of the **S/R level** that was broken (now acting as support)
- **Confirmation**: VO_z window on initial break, quieter on retest
- **Invalidation**: Break back below the S/R level (support fails)
- **Why It Works**: Classic breakout-retest pattern within a confirmed uptrend
- **Risk**: Low - we're buying support in an uptrend

### **Setup C - Channel Support Buy (Trend Continuation)**
- **Context**: Ascending channel defined by diagonals (S3 continuation)
- **Trigger**: Touch of lower channel line with RSI(15m) > 40
- **Confirmation**: No 1h structure break, price holds above EMA 20
- **Invalidation**: Break below channel + last 1h swing low
- **Why It Works**: Trend continuation within established channel
- **Risk**: Medium - channels can break, but we have clear invalidation

## 📈 **Exit Strategy**

### **Planned Profit-Taking**
- **Primary Target**: RSI divergence + structure failure confirmation
- **Structure Failure**: No Higher High after divergence + close below EMA 20
- **Geometry Confirmation**: Break of current uptrend diagonal or key S/R level
- **Past Trend Diagonals**: Critical resistance from previous trends (parabolic moves)

### **Trail Management (Signal-Based, Not Mechanical)**
- **Chandelier Context**: Highest close - k×ATR(14) where k=3.0 (used for alerting, not hard stops)
- **ATR Bands**: Position sizing and danger zone detection (1.5×ATR below entry = alert)
- **No Mechanical Stops**: Only structural invalidation triggers exits
- **Acceleration Adjustment**: Tighten trail (k→2.5) when price accelerates far from EMA 20
- **Reconnection Logic**: Loosen trail (k→3.5) when price returns to EMA 20

### **Exit Strategy (Two-Phase System)**
**Phase A - Exit Trigger Detection:**
- Close below Chandelier line, OR
- Close below EMA 50 + diagonal break, OR  
- Structure invalidation (HH/HL pattern break)
- → Sets "Pending Exit State" (signal, not execution)

**Phase B - Bounce Exit Execution:**
- Wait for price to retest the broken level (diagonal, EMA 50, or S/R level that triggered the exit)
- OR retest of the Chandelier line from below
- **Exit on Retest**: Sell when price approaches the underside of the broken level (1h close near the level)
- **Weak Bounce Cut**: If bounce forms but fails to reach the broken level, then 1h close below the bounce low → immediate exit

**Self-Healing Logic:**
- If bounce forms and price reclaims the broken level with RSI(1h) > 50 and ADX rising → Cancel exit (trend reasserted)
- BUT maintain exit readiness if this reassertion fails (1h close falls back below the level)
- If ADX < 25 and RSI < 45 → Confirm trend exhaustion before executing

**All Exit Logic Based on 1h Closes:**
- Exit triggers: 1h close below Chandelier/EMA 50/diagonal
- Retest exit: 1h close near underside of broken level
- Weak bounce cut: 1h close below bounce low
- Self-healing: 1h close reclaiming broken level

## 🏆 **Opportunity Ranking (Composite Score)**

### **Dynamic Weighting System**
- **Strong Market (BTC ADX > 25)**: Raise "Ignition Activity" weight to 30%
- **Choppy Markets**: Raise "Compression Potential" weight to 35%
- **Context Sensitivity**: Weights adapt to market regime for optimal opportunity detection

### **Regime Quality (25%)**
- Diagonal break + EMA alignment + ADX > 20
- Freshness: Flip occurred within last 2 days
- Strength: ADX rising slope > 0.5 per bar

### **Compression Potential (25%)**
- **ATR Normalization**: ATR(14) / Close (15m) for scale-invariant volatility
- **Volatility Slope**: EMA of linear regression slope of ATR_norm over 200 bars (≈2.1 days)
  - Negative slope = compressing volatility (triangle/wedge forming)
  - Slope approaching zero = near apex (energy bottleneck)
  - **Adaptive Confirmation**: Require 2 consecutive positive readings to confirm expansion pulse
- **Compression Duration**: Slope < 0 for ≥60 bars (≈15 hours) = "coiling" state
- **Energy Buildup**: Flat RSI midrange (40-60) before expansion

### **Ignition Activity (20%)**
- **Expansion Pulse**: Volatility slope crosses from negative to positive + price impulse > ATR(14)
- **VO_z Window**: Presence around diagonal break (≥3 spikes of z≥2.0 in 20 bars)
- **ADX Rising**: Slope confirmation > 0.5 per bar
- **Volume Expansion**: Recent average vs. compression period

### **Liquidity & Cleanliness (20%)**
- Dollar volume: 14-day average (Close × Volume)
- Wick noise penalty: Clean candle patterns preferred
- Overhead supply: Distance to 30-day high

### **Trend-Space (10%)**
- Channel projection distance to upper diagonal
- RSI runway: Distance from current RSI to 80
- Measured move potential from base formation

## 💰 **Risk Management**

### **Position Sizing**
- **Risk/Reward Based**: Size = (Account Risk %) / (Risk per Trade)
- **Risk per Trade**: Distance from entry to invalidation level
- **Reward Target**: Distance to nearest resistance or channel projection
- **Minimum R/R**: 2.0 before costs, 1.5 after costs

### **Invalidation Placement (Conceptual, Not Mechanical)**
- **Primary**: Structural invalidation only (1h swing low break, diagonal break, EMA 50 loss)
- **ATR Context**: Use ATR bands for position sizing and danger zone alerts (1.5×ATR below entry)
- **No Mechanical Stops**: ATR-based levels are context, not hard exit triggers
- **Exit Execution**: Always on bounce/retest, never at the low of the flush

### **Trail Logic**
- **Chandelier Base**: k = 3.0×ATR(14) from highest close
- **Acceleration Mode**: k = 2.5×ATR when price > 2×ATR from EMA 20
- **Reconnection Mode**: k = 3.5×ATR when price returns to EMA 20
- **Maximum Trail**: Never trail closer than initial invalidation

## 🔄 **Integration with PM System**

### **Geometry Integration**
- **Uses Existing**: Diagonal detection and S/R level computation
- **Extends**: Past trend diagonal tracking for resistance levels
- **Adds**: AVWAP(flip) computation and storage

### **TA Integration**
- **Extends Current**: RSI, EMAs, ATR from existing TA tracker
- **Adds New**: ADX computation and VO_z window detection
- **Enhances**: RSI divergence with structure failure confirmation

### **Decision Flow**
1. **Scanner**: Every 5min, evaluate all 50+ coins
2. **Ranker**: Composite score calculation and top-N selection
3. **PM Core**: Hourly strategic decisions and position adjustments
4. **Execution**: Real-time entry/exit trigger monitoring

### **Data Requirements**
- **Minimum History**: 14-day backfill for geometry analysis
- **Update Frequency**: 5min for opportunity scanning
- **Storage**: Extend existing `features.geometry` and `features.ta` schemas

## 📋 **Implementation Specifications**

### **State Machine Parameters**
- **ATR Normalization**: ATR(14) / Close for scale-invariant volatility
- **Volatility Slope Window**: 200 bars (≈2.1 days on 15m)
- **Compression Threshold**: Slope < 0 for ≥60 bars (≈15 hours)
- **Expansion Pulse Timeout**: 16×15m bars (4 hours) after S1 trigger
- **ADX Thresholds**: >20 for activation, >40 for mature trend, rollover for exhaustion

### **Energy Detection**
- **Compression**: ATR slope < 0 for ≥60 bars = "coiling" state
- **Expansion Pulse**: Slope crosses > 0 AND true range ≥ ATR(14)
- **VO_z Window**: ≥3 spikes of z≥2.0 in 20-bar window
- **Exhaustion**: ATR spike >1.5×median then drop >30% within 20 bars

### **Structure & Flow**
- **EMA Alignment**: EMA 20 > EMA 50 with EMA 50 rising
- **Diagonal Breaks**: 1h close above descending diagonal
- **AVWAP Anchor**: Set at the S1 breakout close (per SM) for dynamic support; fakeout reset within 24 bars re-arms S1 and re-anchors on next valid S1

### **Scanning Order**
1. **Compression Detection**: Low volatility + flat RSI + tight ranges
2. **Flip Detection**: Diagonal break + EMA alignment + ADX activation
3. **Ignition Confirmation**: VO_z windows + volume expansion
4. **Filter Application**: Liquidity, cleanliness, trend-space evaluation

### **Performance Targets**
- **Win Rate**: 60-70% on Setup A entries
- **Average R**: 2.5-3.0 on winning trades
- **Maximum Drawdown**: < 15% of account
- **Time in Trade**: 3-14 days average holding period

## 📊 **Logging & Analytics**

### **State Transition Logging**
For backtests and live monitoring, log every state transition with:
```json
{
  "timestamp": "2025-01-22T15:05:00Z",
  "symbol": "POLYTALE",
  "state_from": "S0",
  "state_to": "S1", 
  "composite_score": 78.5,
  "avg_R": 2.8,
  "time_in_state": 1440,
  "trigger_reason": "diagonal_break",
  "confidence": 0.85
}
```

### **Performance Analytics**
- **State Transition Accuracy**: Track S0-S5 transition success rates
- **Setup Detection Precision**: Monitor Setup A/B/C accuracy vs outcomes
- **R/R Performance**: Average risk/reward ratios by setup type
- **False Signal Learning**: Adaptive threshold adjustment based on historical performance

### **Visual Validation**
- **S-Transition Charts**: Plot state transitions on price charts
- **Geometry Alignment**: Verify state changes align with diagonal breaks
- **Compression Visualization**: Show ATR slope and expansion pulses
- **Composite Score Heatmaps**: Track opportunity quality over time

## 🚀 **Next Steps**

1. **Implement ADX Computation**: Add to existing TA tracker
2. **Build Composite Ranker**: 5-component scoring system with dynamic weighting
3. **Create Setup Scanner**: A/B/C entry detection logic with freshness timers
4. **Wire Exit Signals**: RSI divergence + structure failure with adaptive learning
5. **Add State Transition Logging**: Comprehensive analytics and monitoring
6. **Test on Historical Data**: Validate thresholds and parameters statistically
7. **Deploy to Live System**: Integrate with existing PM architecture

### **Immediate Prototype Steps**
1. **State-Transition Logger**: Using historical 15m/1h data
2. **Back-fill 20-30 coins**: Run composite score daily, verify top-5 picks
3. **Plot S-transitions**: Visual validation on charts
4. **Tune Parameters**: Adjust thresholds until false-flips < 10%

---

*This engine focuses on high-probability continuation setups while maintaining strict risk management and clean exit strategies. The adaptive learning system ensures continuous improvement based on market feedback.*
