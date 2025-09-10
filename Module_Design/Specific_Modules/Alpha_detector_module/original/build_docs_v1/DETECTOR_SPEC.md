# Detector Catalog & Specifications

*Source: [alpha_detector_build_convo.md §9-10](../alpha_detector_build_convo.md#event-detector-catalogue-v01)*

## Overview

The detector system includes 6 classes of signals, each with specific triggers, cooldowns, and severity scoring. All detectors use **residual manufacturing** - they trigger on residuals from predictive models rather than simple z-scores. This approach accounts for market regimes, cross-sectional relationships, and time-of-day effects. All detectors are deterministic and read only from feature snapshots + market context. Each detector generates **complete trading plans** with microstructure intelligence validation.

**Enhanced Selection System**: Detector selection uses a two-layer approach based on **signal quality** (NOT trade profitability):
1. **Signal Quality Core (sq_score)**: Traditional signal accuracy, precision, stability, orthogonality, cost metrics
2. **Phase Resonance (kr_delta_phi)**: Kernel resonance accounting for surprise, coherence, field alignment, complexity, depth, emergence, and novelty
3. **Final Selection (det_sigma)**: Geometric blend of both layers for optimal detector selection

**Note**: These are signal quality metrics for detector selection. Trade profitability analysis (psi_score) happens separately in the trading system.

## Detector Species & Traits

Each detector declares:
- **Trait vector** (features used, horizon, latency tolerance, trade style)
- **Residual diet** (which residual recipes it consumes)
- **Risk posture** (max turnover, max drawdown tolerated)
- **Mutability** (which hyperparams can be jittered, allowable ranges)

## Mutation & Recombination

Detectors MUST implement:
- **mutate(jitter_spec)** → returns child detector configs
- **recombine(other, mix_spec)** → returns hybrid config with combined transforms

## Scoring Contract

Detectors expose standardized outputs:
- **signal_t** ∈ ℝ (per asset×bar)
- **position_t** ∈ [-1,1]
- **trade_intent_t** (limit/market preference, optional)

Framework computes pnl under house execution model; detector code must not embed broker-specific assumptions.

## Detector Classes

### 1. SPIKE Class
*Source: [alpha_detector_build_convo.md §9.2](../alpha_detector_build_convo.md#spike-class)*

**Purpose**: Detect sudden anomalies in key metrics

#### spike.vol_spike_m_1
- **Trigger**: `z_vol_residual_m_1 ≥ 2.5` AND `trade_count_m_1 ≥ 5` AND `regime_gate`
- **Regime Gates**: `atr_percentile_252 ∈ [20, 90]` AND `volatility_regime = "medium"`
- **Cooldown**: 45s | **Half-life**: 120s
- **Payload**: `z_vol_residual_m_1`, `vol_prediction_m_1`, `ret_m_1`, `v_total_m_1`

#### spike.price_spike_up_m_1 / spike.price_spike_down_m_1
- **Trigger**: `z_ret_residual_m_1 ≥ 2.0` AND sign of `ret_m_1` AND `regime_gate`
- **Regime Gates**: `atr_percentile_252 ∈ [20, 90]` AND `trend_regime = "trending"`
- **Cooldown**: 45s | **Half-life**: 120s
- **Payload**: `ret_m_1`, `z_ret_residual_m_1`, `ret_prediction_m_1`, `spread_mean_m_1`

#### spike.oi_spike_up_m_5 / spike.oi_spike_down_m_5
- **Trigger**: `z_oi_residual_m_5 ≥ 2.0` AND `|oi_roc_m_5| ≥ 1.5%` AND `regime_gate`
- **Regime Gates**: `atr_percentile_252 ∈ [20, 90]` AND `market_regime = "normal"`
- **Precondition**: `oi_staleness_ms ≤ 20000`
- **Cooldown**: 60s | **Half-life**: 180s
- **Payload**: `oi_roc_m_5`, `z_oi_residual_m_5`, `oi_prediction_m_5`, `ret_m_5`

### 2. SHIFT Class
*Source: [alpha_detector_build_convo.md §9.3](../alpha_detector_build_convo.md#shift-class)*

**Purpose**: Detect regime changes and structural shifts

#### shift.spread_stress_m_1
- **Trigger**: `z_spread_residual_m_1 ≥ 2.0` AND `regime_gate`
- **Regime Gates**: `atr_percentile_252 ∈ [20, 90]` AND `liquidity_regime = "medium"`
- **Cooldown**: 90s | **Half-life**: 300s
- **Payload**: `z_spread_residual_m_1`, `spread_prediction_m_1`, `spread_p95_m_1`, `v_total_m_1`

#### shift.basis_jolt_m_5
- **Trigger**: `|z_basis_residual_m_5| ≥ 2.5` AND `regime_gate`
- **Regime Gates**: `atr_percentile_252 ∈ [20, 90]` AND `market_regime = "normal"`
- **Cooldown**: 90s | **Half-life**: 300s
- **Payload**: `basis_bp_m_5`, `z_basis_residual_m_5`, `basis_prediction_m_5`, `oi_roc_m_5`

#### shift.funding_jolt_h_1
- **Trigger**: `|Δ funding_h_1| ≥ 10 bps` OR predicted flip ≤ 1h
- **Cooldown**: 300s | **Half-life**: 600s
- **Payload**: `funding_h_1`, `time_to_next_funding_sec`

### 3. QUADRANT Class
*Source: [alpha_detector_build_convo.md §9.4](../alpha_detector_build_convo.md#quadrant-class)*

**Purpose**: Analyze price vs positioning dynamics

#### quadrant.price_up_oi_up_m_5 (trend build)
- **Trigger**: `ret_m_5 ≥ 0.3%` AND `oi_roc_m_5 ≥ 1.0%`
- **Cooldown**: 90s | **Half-life**: 180s

#### quadrant.price_up_oi_down_m_5 (short squeeze)
- **Trigger**: `ret_m_5 ≥ 0.3%` AND `oi_roc_m_5 ≤ -1.0%`
- **Cooldown**: 90s | **Half-life**: 180s

#### quadrant.price_down_oi_up_m_5 (trend down build)
- **Trigger**: `ret_m_5 ≤ -0.3%` AND `oi_roc_m_5 ≥ 1.0%`
- **Cooldown**: 90s | **Half-life**: 180s

#### quadrant.price_down_oi_down_m_5 (long squeeze)
- **Trigger**: `ret_m_5 ≤ -0.3%` AND `oi_roc_m_5 ≤ -1.0%`
- **Cooldown**: 90s | **Half-life**: 180s

### 4. DIVERGENCE Class
*Source: [alpha_detector_build_convo.md §9.5](../alpha_detector_build_convo.md#divergence-class)*

**Purpose**: Detect price vs flow mismatches and momentum divergences

#### div.price_up_cvd_down_m_5
- **Trigger**: `ret_m_5 ≥ 0.3%` AND `Σ_5(cvd_delta_m_1) ≤ -q`
- **Cooldown**: 90s | **Half-life**: 240s
- **Payload**: `ret_m_5`, `Σ_5(cvd_delta)`, `z_vol_m_1`

#### div.price_flat_cvd_trend_m_5
- **Trigger**: `|ret_m_5| ≤ 0.1%` AND `|cvd_slope_m_5| ≥ θ_cvd`
- **Cooldown**: 90s | **Half-life**: 240s
- **Payload**: `cvd_slope_m_5`, `ret_m_5`, `spread_mean_m_1`

#### div.premium_no_oi_m_5
- **Trigger**: `z_basis_m_5 ≥ 2.0` AND `oi_roc_m_5 ≤ 0`
- **Cooldown**: 90s | **Half-life**: 240s
- **Payload**: `basis_bp_m_5`, `oi_roc_m_5`, `ret_m_5`

#### div.hidden_momentum_bull_m_5 (Phase 1 Addition)
- **Purpose**: Hidden momentum divergence (continuation signal)
- **Trigger**: `hma_100_slope > 0` AND `adx_14 > 20` AND `swing_low_current > swing_low_prev` AND `rsi_14_current < rsi_14_prev`
- **Context Gates**: `atr_percentile_252 > 20` AND `level_proximity_score > 0.5`
- **Cooldown**: 120s | **Half-life**: 300s
- **Payload**: `divergence_strength`, `level_proximity`, `vol_state_score`, `trend_alignment`

#### div.hidden_momentum_bear_m_5 (Phase 1 Addition)
- **Purpose**: Hidden momentum divergence (bearish continuation)
- **Trigger**: `hma_100_slope < 0` AND `adx_14 > 20` AND `swing_high_current < swing_high_prev` AND `rsi_14_current > rsi_14_prev`
- **Context Gates**: `atr_percentile_252 > 20` AND `level_proximity_score > 0.5`
- **Cooldown**: 120s | **Half-life**: 300s
- **Payload**: `divergence_strength`, `level_proximity`, `vol_state_score`, `trend_alignment`

#### div.price_rsi_bear_m_5 (Phase 1 Addition)
- **Purpose**: Classic RSI divergence (reversal signal)
- **Trigger**: `price_hh = true` AND `rsi_14_hh = false` AND `rsi_14_current < rsi_14_prev`
- **Context Gates**: `adx_14 ∈ [20,40]` AND `atr_percentile_252 > 20`
- **Cooldown**: 180s | **Half-life**: 360s
- **Payload**: `divergence_strength`, `rsi_14_current`, `rsi_14_prev`, `price_change`

#### div.price_macd_bear_m_5 (Phase 1 Addition)
- **Purpose**: MACD divergence (momentum shift)
- **Trigger**: `price_hh = true` AND `macd_line_hh = false` AND `macd_line_current < macd_line_prev`
- **Context Gates**: `adx_14 ∈ [20,40]` AND `atr_percentile_252 > 20`
- **Cooldown**: 180s | **Half-life**: 360s
- **Payload**: `divergence_strength`, `macd_line_current`, `macd_signal_current`, `macd_histogram`

#### div.delta_volume_bear_m_5 (Phase 1 Addition)
- **Purpose**: Delta/volume divergence at levels
- **Trigger**: `price_hh = true` AND `cum_delta_hh = false` AND `near_significant_level = true`
- **Context Gates**: `level_proximity_score > 0.7` AND `volume_confirm = true`
- **Cooldown**: 90s | **Half-life**: 240s
- **Payload**: `divergence_strength`, `cum_delta_current`, `cum_delta_prev`, `level_proximity`

#### div.breadth_bear_d_1 (Phase 2 Addition)
- **Purpose**: Breadth divergence (market structure)
- **Trigger**: `index_hh = true` AND `breadth_composite_lh = true`
- **Context Gates**: `breadth_composite_zscore < -1.0` AND `universe_size > 20`
- **Cooldown**: 300s | **Half-life**: 600s
- **Payload**: `divergence_strength`, `breadth_composite`, `pct_above_ma50`, `nh_nl`

### 5. PATTERN Class (Phase 1 Addition)
*Source: [alpha_detector_build_convo.md §9.8](../alpha_detector_build_convo.md#pattern-class)*

**Purpose**: Detect chart patterns, candlestick patterns, and support/resistance breakouts

#### pattern.doji_reversal_m_1
- **Purpose**: Doji pattern with reversal confirmation
- **Trigger**: `is_doji = true` AND `pattern_volume_confirmation = true` AND `level_proximity_score > 0.5`
- **Context Gates**: `atr_percentile_252 > 20` AND `spread_mean_m_1 < spread_cap`
- **Cooldown**: 60s | **Half-life**: 180s
- **Payload**: `pattern_strength_score`, `level_proximity`, `volume_confirmation`, `reversal_probability`

#### pattern.hammer_reversal_m_1
- **Purpose**: Hammer pattern with reversal confirmation
- **Trigger**: `is_hammer = true` AND `pattern_volume_confirmation = true` AND `near_support = true`
- **Context Gates**: `atr_percentile_252 > 20` AND `level_strength > 0.6`
- **Cooldown**: 60s | **Half-life**: 180s
- **Payload**: `pattern_strength_score`, `level_strength`, `volume_confirmation`, `reversal_probability`

#### pattern.engulfing_reversal_m_1
- **Purpose**: Engulfing pattern with reversal confirmation
- **Trigger**: (`is_bull_engulfing = true` OR `is_bear_engulfing = true`) AND `pattern_volume_confirmation = true`
- **Context Gates**: `atr_percentile_252 > 20` AND `level_proximity_score > 0.4`
- **Cooldown**: 60s | **Half-life**: 180s
- **Payload**: `pattern_strength_score`, `engulfing_type`, `volume_confirmation`, `reversal_probability`

#### pattern.support_breakout_m_1
- **Purpose**: Support level breakout with volume confirmation
- **Trigger**: `support_breakout = true` AND `pattern_volume_confirmation = true` AND `level_strength > 0.5`
- **Context Gates**: `atr_percentile_252 > 20` AND `level_age > 5`
- **Cooldown**: 90s | **Half-life**: 240s
- **Payload**: `breakout_strength`, `level_strength`, `volume_confirmation`, `target_price`

#### pattern.resistance_breakout_m_1
- **Purpose**: Resistance level breakout with volume confirmation
- **Trigger**: `resistance_breakout = true` AND `pattern_volume_confirmation = true` AND `level_strength > 0.5`
- **Context Gates**: `atr_percentile_252 > 20` AND `level_age > 5`
- **Cooldown**: 90s | **Half-life**: 240s
- **Payload**: `breakout_strength`, `level_strength`, `volume_confirmation`, `target_price`

#### pattern.falling_wedge_m_5
- **Purpose**: Falling wedge pattern with breakout confirmation
- **Trigger**: `is_falling_wedge = true` AND `pattern_time_confirmation = true` AND `pattern_volume_confirmation = true`
- **Context Gates**: `atr_percentile_252 > 20` AND `pattern_completion_pct > 0.6`
- **Cooldown**: 120s | **Half-life**: 300s
- **Payload**: `pattern_strength_score`, `completion_pct`, `target_price`, `stop_loss`

#### pattern.bull_flag_m_5
- **Purpose**: Bull flag pattern with continuation confirmation
- **Trigger**: `is_bull_flag = true` AND `pattern_time_confirmation = true` AND `pattern_volume_confirmation = true`
- **Context Gates**: `atr_percentile_252 > 20` AND `pattern_completion_pct > 0.5`
- **Cooldown**: 120s | **Half-life**: 300s
- **Payload**: `pattern_strength_score`, `completion_pct`, `target_price`, `stop_loss`

#### pattern.ascending_triangle_m_5
- **Purpose**: Ascending triangle pattern with breakout
- **Trigger**: `is_ascending_triangle = true` AND `pattern_time_confirmation = true` AND `resistance_breakout = true`
- **Context Gates**: `atr_percentile_252 > 20` AND `pattern_completion_pct > 0.7`
- **Cooldown**: 120s | **Half-life**: 300s
- **Payload**: `pattern_strength_score`, `completion_pct`, `target_price`, `stop_loss`

#### pattern.head_shoulders_m_5
- **Purpose**: Head and shoulders pattern with neckline break
- **Trigger**: `is_head_shoulders = true` AND `pattern_time_confirmation = true` AND `support_breakout = true`
- **Context Gates**: `atr_percentile_252 > 20` AND `pattern_completion_pct > 0.8`
- **Cooldown**: 180s | **Half-life**: 360s
- **Payload**: `pattern_strength_score`, `completion_pct`, `target_price`, `stop_loss`

#### pattern.double_top_m_5
- **Purpose**: Double top pattern with confirmation
- **Trigger**: `is_double_top = true` AND `pattern_time_confirmation = true` AND `support_breakout = true`
- **Context Gates**: `atr_percentile_252 > 20` AND `pattern_completion_pct > 0.7`
- **Cooldown**: 120s | **Half-life**: 300s
- **Payload**: `pattern_strength_score`, `completion_pct`, `target_price`, `stop_loss`

#### pattern.double_bottom_m_5
- **Purpose**: Double bottom pattern with confirmation
- **Trigger**: `is_double_bottom = true` AND `pattern_time_confirmation = true` AND `resistance_breakout = true`
- **Context Gates**: `atr_percentile_252 > 20` AND `pattern_completion_pct > 0.7`
- **Cooldown**: 120s | **Half-life**: 300s
- **Payload**: `pattern_strength_score`, `completion_pct`, `target_price`, `stop_loss`

#### pattern.diagonal_support_break_m_1
- **Purpose**: Rising support line breakout with volume confirmation
- **Trigger**: `diagonal_support_break = true` AND `pattern_volume_confirmation = true` AND `diagonal_line_strength > 0.6`
- **Context Gates**: `atr_percentile_252 > 20` AND `diagonal_age > 10` AND `diagonal_touches >= 3`
- **Cooldown**: 90s | **Half-life**: 240s
- **Payload**: `diagonal_line_strength`, `breakout_strength`, `volume_confirmation`, `target_price`

#### pattern.diagonal_resistance_break_m_1
- **Purpose**: Falling resistance line breakout with volume confirmation
- **Trigger**: `diagonal_resistance_break = true` AND `pattern_volume_confirmation = true` AND `diagonal_line_strength > 0.6`
- **Context Gates**: `atr_percentile_252 > 20` AND `diagonal_age > 10` AND `diagonal_touches >= 3`
- **Cooldown**: 90s | **Half-life**: 240s
- **Payload**: `diagonal_line_strength`, `breakout_strength`, `volume_confirmation`, `target_price`

#### pattern.diagonal_channel_break_m_5
- **Purpose**: Diagonal channel breakout with confirmation
- **Trigger**: `diagonal_channel_break = true` AND `pattern_time_confirmation = true` AND `pattern_volume_confirmation = true`
- **Context Gates**: `atr_percentile_252 > 20` AND `diagonal_line_strength > 0.7` AND `diagonal_convergence_rate > 0.1`
- **Cooldown**: 120s | **Half-life**: 300s
- **Payload**: `diagonal_line_strength`, `channel_width`, `convergence_rate`, `target_price`

### 6. SYNCHRONY Class
*Source: [alpha_detector_build_convo.md §9.6](../alpha_detector_build_convo.md#synchrony-class)*

**Purpose**: Detect market-wide coordination

#### sync.basket_shock_Δt_5s
- **Trigger**: `shock_count_5s ≥ max(4, ceil(0.15 * universe_size))`
- **Cooldown**: 60s | **Half-life**: 60s
- **Payload**: `shock_count_5s`, `leader`, `dominance_share`

### 6. ROTATION Class
*Source: [alpha_detector_build_convo.md §9.7](../alpha_detector_build_convo.md#rotation-class)*

**Purpose**: Detect leadership and sector changes

#### rot.leader_cooling_followers_hot_m_15
- **Trigger**: 2-bar divergence on leader vs follower metrics
- **Cooldown**: 300s | **Half-life**: 900s
- **Payload**: Leader metrics vs follower median deltas

## Regime Gates (WWJSD Integration)

*Source: [WWJSD.md](../WWJSD.md) regime gates*

### ATR Percentile Gates
- **Range**: `atr_percentile_252 ∈ [20, 90]`
- **Purpose**: Only trade in normal volatility regimes
- **Rationale**: Avoid extreme volatility periods where signals are unreliable
- **Implementation**: Rolling 252-day ATR percentile calculation
- **Formula**: `atr_percentile = rank(ATR_14) / 252 * 100`
- **Gate Logic**: `20 <= atr_percentile <= 90`

### ADX Band Gates
- **Range**: `adx_14 ∈ [12, 35]`
- **Purpose**: Only trade in trending markets
- **Rationale**: Avoid ranging markets where signals have low predictive power
- **Implementation**: 14-period ADX calculation with smoothing
- **Formula**: `ADX = 100 * EMA(100 * |+DI - -DI| / (+DI + -DI))`
- **Gate Logic**: `12 <= ADX <= 35`

### Session Phase Gates
- **Active Hours**: `session_phase ∈ ["us", "europe", "overlap"]`
- **Purpose**: Only trade during active trading hours
- **Rationale**: Avoid low-liquidity periods with unreliable signals
- **Implementation**: Time-based phase detection
- **US/EU Overlap**: 13:00-16:00 UTC (8:00-11:00 EST)
- **Asia Open**: 00:00-02:00 UTC (7:00-9:00 JST)
- **Gate Logic**: `current_time in allowed_phases`

### Market Regime Gates
- **Volatility**: `volatility_regime = "medium"`
- **Trend**: `trend_regime = "trending"`
- **Liquidity**: `liquidity_regime ∈ ["medium", "high"]`
- **Purpose**: Only trade in appropriate market conditions
- **Rationale**: Ensure signals are contextually relevant
- **Implementation**: Multi-factor regime classification
- **Normal Regime**: 20th-80th percentile volatility, moderate trend
- **Trending Regime**: ADX > 25, consistent direction
- **Volatile Regime**: High volatility but not extreme
- **Gate Logic**: `market_regime in [normal, trending, volatile]`

### Volatility Regime Gates
- **Allowed Regimes**: Normal, high (exclude extreme, calm)
- **Purpose**: Avoid extreme volatility conditions
- **Rationale**: Extreme volatility can cause false signals
- **Implementation**: Rolling volatility percentile
- **Normal**: 20th-80th percentile of 30-day volatility
- **High**: 80th-95th percentile of 30-day volatility
- **Gate Logic**: `volatility_regime in [normal, high]`

### Trend Regime Gates
- **Allowed Regimes**: Uptrend, downtrend, sideways (exclude extreme)
- **Purpose**: Only trade in clear trend conditions
- **Rationale**: Divergences work best in trending markets
- **Implementation**: HMA slope and ADX combination
- **Uptrend**: HMA slope > 0, ADX > 20
- **Downtrend**: HMA slope < 0, ADX > 20
- **Sideways**: |HMA slope| < threshold, ADX < 25
- **Gate Logic**: `trend_regime in [uptrend, downtrend, sideways]`

### Liquidity Regime Gates
- **Allowed Regimes**: Normal, high (exclude low, extreme)
- **Purpose**: Ensure sufficient liquidity for reliable signals
- **Rationale**: Low liquidity can cause false signals
- **Implementation**: Volume and spread analysis
- **Normal**: 20th-80th percentile of 30-day volume
- **High**: 80th-95th percentile of 30-day volume
- **Gate Logic**: `liquidity_regime in [normal, high]`

### Regime Gate Implementation Algorithm
```python
def check_regime_gates(snapshot: FeatureSnapshot) -> bool:
    """Check if all regime gates pass"""
    gates = []
    
    # ATR Percentile Gate
    atr_pct = snapshot.atr_percentile_252
    gates.append(20 <= atr_pct <= 90)
    
    # ADX Band Gate
    adx = snapshot.adx_14
    gates.append(12 <= adx <= 35)
    
    # Session Phase Gate
    current_hour = snapshot.timestamp.hour
    us_eu_overlap = 13 <= current_hour <= 16
    asia_open = 0 <= current_hour <= 2
    gates.append(us_eu_overlap or asia_open)
    
    # Market Regime Gate
    market_regime = snapshot.market_regime
    gates.append(market_regime in ['normal', 'trending', 'volatile'])
    
    # Volatility Regime Gate
    vol_regime = snapshot.volatility_regime
    gates.append(vol_regime in ['normal', 'high'])
    
    # Trend Regime Gate
    trend_regime = snapshot.trend_regime
    gates.append(trend_regime in ['uptrend', 'downtrend', 'sideways'])
    
    # Liquidity Regime Gate
    liq_regime = snapshot.liquidity_regime
    gates.append(liq_regime in ['normal', 'high'])
    
    return all(gates)
```

### Regime Gate Configuration
```yaml
regime_gates:
  atr_percentile:
    enabled: true
    min_value: 20
    max_value: 90
    lookback_days: 252
  
  adx_bands:
    enabled: true
    min_value: 12
    max_value: 35
    period: 14
  
  session_phase:
    enabled: true
    allowed_phases: ["us_eu_overlap", "asia_open"]
    us_eu_overlap: "13:00-16:00 UTC"
    asia_open: "00:00-02:00 UTC"
  
  market_regime:
    enabled: true
    allowed_regimes: ["normal", "trending", "volatile"]
    classification_method: "multi_factor"
  
  volatility_regime:
    enabled: true
    allowed_regimes: ["normal", "high"]
    lookback_days: 30
  
  trend_regime:
    enabled: true
    allowed_regimes: ["uptrend", "downtrend", "sideways"]
    hma_period: 100
    adx_threshold: 20
  
  liquidity_regime:
    enabled: true
    allowed_regimes: ["normal", "high"]
    lookback_days: 30
    volume_threshold: 0.8
```

## Severity Scoring

*Source: [alpha_detector_build_convo.md §10](../alpha_detector_build_convo.md#severity-novelty--debounce-model) + WWJSD.md residual scoring*

### Inputs
- `primary_residual` - Main residual metric (clamped)
- `secondary_residual` - Supporting residual confirmation (0-N metrics)
- `breadth` - Market context (0-1)
- `novelty_state` - First seen? Time since last?
- `dq_penalties` - Data quality issues
- `illiquidity_penalty` - Near guard thresholds
- `regime_boost` - Regime gate compliance boost

### Formula
```
core = w1*primary_residual̂ + w2*max(0, secondary_residual̂) + w3*breadth
pen = w_dq*dq_penalty + w_liq*illiquidity_penalty
raw = core + novelty_boost + regime_boost - pen
severity = round(100 * sigmoid(a * raw))
```

### Default Weights by Class
- **spike**: `{w1:1.0, w2:0.5, w3:0.4, a:0.6}`
- **shift**: `{w1:0.7, w2:0.8, w3:0.2, a:0.55}`
- **quadrant**: `{w1:0.8, w2:0.6, w3:0.2, a:0.58}`
- **divergence**: `{w1:0.8, w2:0.7, w3:0.2, a:0.58}`
- **pattern**: `{w1:0.9, w2:0.8, w3:0.3, a:0.65}`
- **synchrony**: `{w1:0.4, w2:0.3, w3:1.0, a:0.55}`
- **rotation**: `{w1:0.7, w2:0.5, w3:0.4, a:0.52}`

## Debounce & Re-emission

### Cooldown Rules
- **Emit when**: No active cooldown AND severity ≥ class threshold
- **Re-emit when**: Within cooldown BUT severity ≥ last_severity × 1.3
- **Subtype change**: Emit immediately with novelty reset

### Budget Controls
- **Per-symbol per-minute**: spike:4, shift:2, quadrant:2, divergence:2, pattern:3, sync:2, rotation:1
- **Global cap**: 800 events/min (drop lowest severity first)

## Gating Rules

All detectors require:
- `dq_status == 'ok'`
- `is_in_universe OR is_hot`
- `warmup == FALSE`
- Illiquidity guards pass
- Class-specific preconditions met
- **Regime gates pass** (ATR percentile, ADX bands, session phase, market regime)

## Example Detector Pack

```yaml
detector_pack: v0.1.0
class_defaults:
  spike: { cooldown_sec: 45, half_life_sec: 120, weights: { w1: 1.0, w2: 0.5, w3: 0.4, a: 0.6 }, publish_threshold: 65 }
detectors:
  - id: spike.vol_spike_m_1
    enabled: true
    inputs: [z_vol_m_1, ret_m_1, v_total_m_1, trade_count_m_1]
    preconditions: [dq_ok, not_illiquid, trade_count_ge_5]
    trigger: "z_vol_m_1 >= 3.0"
budgets:
  per_symbol_per_minute: { spike: 4, shift: 2, quadrant: 2, divergence: 2, sync: 2, rotation: 1 }
```

---

*For complete detector specifications and examples, see [alpha_detector_build_convo.md §9-10](../alpha_detector_build_convo.md#event-detector-catalogue-v01)*
