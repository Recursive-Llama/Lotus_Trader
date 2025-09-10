# Feature Specifications

*Source: [alpha_detector_build_convo.md §5.1-5.6](../alpha_detector_build_convo.md#feature-computation-spec-per-family)*

## Overview

The detector computes features on a 1-minute time lattice with rollups to 15m and 1h. All features use **residual manufacturing** - predicting expected values and computing residuals from actual values, rather than simple z-score normalization. This approach accounts for market regimes, cross-sectional relationships, and time-of-day effects.

## Feature Families

### 0. Evolutionary Features

**Parallel Testbed**: Run N detectors + M residual factories concurrently on the same data window with identical pre-trade constraints.

**Cohort Scoring**: Compute `S_i` (selection score) per detector and publish cohort leaderboard snapshots (hourly/daily).

**Lifecycle Hooks**: States: experimental → active → deprecated → archived with promotion/retirement gates (see Config).

**Auto-Reseeding**: Periodically instantiate mutations of top-K survivors (param jitters, input swaps, residual recombinations).

**Kill-Switch Discipline**: Hard stop for dq_status≠ok, ingest_lag breaches, or universe exits (hysteresis rules).

**Backtesting Framework**: Quick, lightweight validation for detector development and early feedback.

**Dead Branches Logging**: Automatic failure logging with pattern recognition and institutional memory.

**Kernel Resonance System**: Two-layer selection with Simons core (psi_score) + phase alignment (delta_phi) for enhanced detector selection.

### 0. Deep Signal Intelligence Features (Phase 1 Addition)

The Deep Signal Intelligence (DSI) system provides microstructure-level intelligence for signal vs noise separation through MicroTape analysis and micro-expert ecosystem.

#### MicroTape Tokenization Features
- `mx_evidence` - Fused evidence score from micro-experts (0-1)
- `mx_confirm` - Binary confirmation flag from micro-experts (boolean)
- `mx_expert_contributions` - Individual expert outputs (JSONB)
- `mx_microtape_hash` - Hash of input MicroTape for provenance

#### Micro-Expert Ecosystem Features
- `mx_fsm_experts` - Grammar/FSM expert outputs (compiled patterns)
- `mx_classifier_experts` - Tiny sequence classifier outputs (1-3B models)
- `mx_anomaly_experts` - Anomaly scorer outputs (distributional outliers)
- `mx_divergence_experts` - Divergence verifier outputs (RSI/MACD confirmation)

#### DSI Integration Features
- `mx_evidence_boost` - Evidence boost factor for kernel resonance
- `mx_confirm_rate` - Confirmation rate across micro-experts
- `mx_expert_survival_rate` - Expert contribution survival rate
- `mx_latency_p50` - 50th percentile processing latency

### 1. Kernel Resonance Features (Phase 1 Addition)

**Enhanced Selection System**: Two-layer detector selection combining Simons core metrics with phase-aligned resonance.

#### Core Selection Layer (Simons) - Signal Quality Metrics (sq_* namespace)
- `sq_score` - Composite signal quality score (0-1) combining accuracy, precision, stability, orthogonality, cost
- `sq_accuracy` - Signal accuracy component (0-1)
- `sq_precision` - Signal precision component (0-1)
- `sq_stability` - Signal stability component (0-1)
- `sq_orthogonality` - Signal orthogonality component (0-1)
- `sq_cost` - Signal cost component (0-1)

#### Phase Resonance Layer (Kernel) (kr_* namespace)
- `kr_hbar` - Market surprise/structural breaks (0-1)
- `kr_coherence` - Spectral coherence with returns (0-1)
- `kr_phi` - Field resonance/regime alignment (0-1)
- `kr_theta` - Context complexity penalty (0-1)
- `kr_rho` - Recursive depth penalty (0-1)
- `kr_emergence` - Emergence potential/learning slope (0-1)
- `kr_novelty` - Novelty in embedding space (0-1)

#### Kernel Integration (det_* namespace)
- `kr_delta_phi` - Kernel resonance score (0-1)
- `det_sigma` - Final selection score (0-1)
- `det_kairos` - Kairos score (0-1)
- `det_entrain_r` - Entrainment order (0-1)
- `det_uncert` - Uncertainty variance (0-1)
- `det_abstained` - Abstention decision (boolean)

#### Mathematical Formulas

**Core Signal Quality (Simons) - Detailed Calculations**

**sq_accuracy (directional hit rate, confidence-weighted):**
```python
# Windowing: use a pinned evaluation window per detector (e.g., 60d, bar-aligned)
# Let r_t→t+h be forward return for horizon h
# Let s_t be the detector's standardized signal

sq_accuracy = Σ_t 1{sign(s_t) = sign(r_t→t+h)} ⋅ |s_t| / Σ_t |s_t|
```

**sq_precision (signal sharpness via slope t-stat):**
```python
# Regression: r_t→t+h = β*s_t + ε_t
# sq_precision = |β̂| / SE(β̂) clipped to [0, T_max]
# Optionally rescale to [0,1] by logistic on the t-stat

sq_precision = clip01(t_stat(beta, se).logistic())
```

**sq_stability (IR stability):**
```python
# Compute rolling IRs on subwindows W (e.g., weekly)
# IR_w = E[P]_w / σ(P)_w
# sq_stability = 1 - sd(IR_w) / (|E[IR_w]| + ε)

sq_stability = 1 - sd(rolling_IR(P)) / (abs(mean(rolling_IR(P))) + 1e-6
```

**sq_orthogonality (vs active cohort PnLs):**
```python
# sq_orthogonality = 1 - max_{j≠i} |ρ(P_i, P_j)|

sq_orthogonality = 1 - max_abs_corr(P_i, P_actives)
```

**sq_cost (turnover & impact):**
```python
# sq_cost = fees + slippage_bps * turnover + κ * turnover²

sq_cost = fees + slippage_bps * turnover + kappa * turnover**2
```

**Aggregate (Simons core):**
```python
sq_score = w_a * sq_accuracy + w_p * sq_precision + w_s * sq_stability + w_o * sq_orthogonality - w_c * sq_cost
```

**State-Space Process Updates - Detailed Implementation**
```python
# clip01(x) := min(1, max(0, x))

# State updates (per bar/window)
kr_phi_i(t)   = clip01( kr_phi_i(t-1) * kr_rho_i(t) )

kr_theta_i(t) = clip01( kr_theta_i(t-1)
                      + kr_hbar(t) * Σ_j [ kr_phi_j(t) * kr_rho_j(t) ]
                      - η * (kr_theta_i(t-1) - θ_bar) )   # mean reversion

kr_rho_i(t+1) = clip01( σ( kr_rho_i(t) + α * kr_delta_phi_i(t) - λ * kr_rho_i(t) ) )

# Sigmoid function
σ(x) = 1 / (1 + e^{-x})
```

**Kernel Resonance Components - Detailed Calculations**

**kr_hbar (surprise via Page–Hinkley on realized variance or factor returns):**
```python
# Maintain cumulative PH statistic on x_t (e.g., log-RV or 1st IPCA factor)
# PH_t = max(0, PH_{t-1} + x_t - μ - δ)
# Normalize via logistic: kr_hbar = σ(zscore(PH_t))

kr_hbar = logistic(zscore(page_hinkley(logRV)))
```

**kr_coherence (magnitude-squared coherence between s_t and r_t→t+h):**
```python
# Compute cross/auto spectra on STFT or wavelet
# C(ω) = |S_sr(ω)|² / (S_ss(ω) * S_rr(ω))
# kr_coherence = Σ_{ω∈B_i} C(ω) * w_ω
# where B_i is the detector's declared band; renormalize to [0,1]

kr_coherence = band_coherence(s, fwd_ret, band=B_i)
```

**kr_phi (field resonance / regime alignment):**
```python
# kr_phi = |corr(P_i, F | P_active)|
# with F a latent "opportunity" factor (e.g., top IPCA/dispersion factor)

kr_phi = abs(partial_corr(P_i, OpportunityFactor | P_actives))
```

**kr_theta (context complexity penalty, higher = worse):**
```python
# Support term u = #{t: |s_t| > τ_s} / T
# Regime entropy H = -Σ_g p_g * log(p_g) for the regimes the detector relies on
# kr_theta = 1 - u * (1 - H/H_max)

kr_theta = 1 - support(s, τ_s) * (1 - regime_entropy()/Hmax)
```

**kr_rho (recursive depth/description length penalty):**
```python
# kr_rho = σ(α_d * depth + β_d * nodes)

kr_rho = σ(αd * depth(recipe) + βd * nodes(recipe))
```

**kr_emergence (learning/transfer slope):**
```python
# kr_emergence = σ(slope_τ(det_sigma) + λ * median(det_sigma on adjacent universes))

kr_emergence = logistic(slope(det_sigma_history) + λ * median_xfer(det_sigma))
```

**kr_novelty (representation-space distinctiveness):**
```python
# Embed detector by recipe/features/return-shape; cosine distance to actives
# kr_novelty = median_{j∈active} d(embed(i), embed(j))

kr_novelty = median_cosine_distance(embed(i), embeds_active)
```

**Kernel Resonance Calculation:**
```python
# kr_delta_phi = kr_hbar * kr_coherence * kr_phi^α * kr_novelty^β * kr_emergence^γ / ((1-kr_theta)^δ * (1-kr_rho)^ε + 10^-6)

kr_delta_phi = kr_hbar * kr_coherence * (
    kr_phi**α * kr_novelty**β * kr_emergence**γ
) / ((1-kr_theta)**δ * (1-kr_rho)**ε + 1e-6)
```

**Kairos (Timing) & Entrainment (Ensemble Coherence) - Detailed Calculations**

**Timing (Kairos):**
```python
# Let X(ω_k,t) be market spectrum; W_i = kr_phi * kr_theta * kr_rho
# det_kairos_i(t) = Σ_k |X(ω_k,t)| * cos(∠X - phase_i(ω_k)) * w_k / Σ_k |X(ω_k,t)| * w_k * W_i / (max_j W_j + ε)

det_kairos = kairos_alignment(market_spectrum, phase_i, W=kr_phi*kr_theta*kr_rho)
```

**Ensemble Coherence (Kuramoto):**
```python
# det_entrain_r * e^{iΨ} = (1/M) * Σ_{m=1..M} e^{iφ_m(t)}

det_entrain_r = kuramoto_order(phases_of_market_modes)
```

**Uncertainty (mutation disagreement):**
```python
# det_uncert_i(t) = Var_k(s_{i,k}(t))

det_uncert = var(child_signals(siblings_of_i))
```

**Final Selection Score**
```python
# Final selection (route/allocate by this)
det_sigma_i(t) = sq_score_i(t)^u * kr_delta_phi_i(t)^(1-u)
```

**Execution Gates**
```python
# Complete execution gate logic
Trade only if:
  det_kairos_i(t) ≥ τ_K
  det_entrain_r(t) ≥ τ_r
  det_uncert_i(t) ≤ τ_U
  and data quality ok

# Abstention decision
det_abstained = (det_uncert > tau_U) OR (dq_status != 'ok')
```

**Observer Effect & Regularization - Detailed Implementation**

**Contraction Mapping:**
```python
# Ensure braid/prior update T has Lipschitz L < 1 via weight decay or early stop
|| T(p) - T(q) || ≤ L || p - q ||, with L < 1 (weight-decay / early-stop)
```

**Witness Penalty (Crowding):**
```python
# penalty_i = 1 / (1 + c * share_i^p)
# kr_coherence_i ← kr_coherence_i * penalty_i
# (or apply to kr_phi)

penalty = 1 / (1 + c * share_i**p)
kr_coherence *= penalty
```

**Sanity Constraints**
```python
# Clip state variables to [0,1]
kr_phi_i(t) = clip(kr_phi_i(t), 0, 1)
kr_theta_i(t) = clip(kr_theta_i(t), 0, 1)
kr_rho_i(t) = clip(kr_rho_i(t), 0, 1)

# Regularize kr_rho with λ; ensure linearized spectral radius < 1
kr_rho_i(t+1) = kr_rho_i(t) + α * kr_delta_phi_i(t) - λ * kr_rho_i(t)
```

### 1. Price / Returns / Volatility

**Raw Features:**
- `open`, `high`, `low`, `close` - OHLC from trade prints
- `mid_close` - minute-close midprice from BBO
- `ret_s_30`, `ret_m_1`, `ret_m_5`, `ret_m_15` - returns over different windows
- `ret_abs_m_1` - absolute 1-minute return
- `rv_m_1` - realized volatility proxy
- `atr_proxy_m_1` - ATR proxy (high-low)/mid_close

**Residual Features:**
- `z_ret_residual_m_1` - residual of absolute returns (actual - predicted) / prediction_std
- `q_ret_residual_m_1` - quantile rank of return residuals
- `ret_prediction_m_1` - predicted absolute return based on regime/context
- `ret_prediction_std_m_1` - standard deviation of return predictions

### 2. Flow / CVD (Cumulative Volume Delta)

**Raw Features:**
- `v_buy_m_1`, `v_sell_m_1`, `v_total_m_1` - taker-labeled volume
- `trade_count_m_1` - number of prints
- `cvd_delta_m_1` - v_buy - v_sell
- `cvd_level` - running total (daily anchored)
- `cvd_slope_m_5` - OLS slope over 5 minutes

**Residual Features:**
- `z_vol_residual_m_1` - residual of volume (actual - predicted) / prediction_std
- `q_vol_residual_m_1` - quantile rank of volume residuals
- `vol_prediction_m_1` - predicted volume based on price volatility, time of day, session phase
- `vol_prediction_std_m_1` - standard deviation of volume predictions

### 3. Positioning (Open Interest & Liquidations)

**Raw Features:**
- `oi_open`, `oi_close`, `oi_min`, `oi_max` - OI samples within minute
- `oi_delta_m_5` - 5-minute OI change
- `oi_roc_m_5` - 5-minute OI rate of change
- `liq_count_m_5`, `liq_notional_m_5` - liquidation counts/notional
- `oi_staleness_ms` - milliseconds since last OI sample

**Residual Features:**
- `z_oi_residual_m_5` - residual of OI rate of change (actual - predicted) / prediction_std
- `q_oi_residual_m_5` - quantile rank of OI residuals
- `oi_prediction_m_5` - predicted OI rate of change based on price action, funding, volatility
- `oi_prediction_std_m_5` - standard deviation of OI predictions

### 4. Perp State (Funding & Basis)

**Raw Features:**
- `funding_h_1` - hourly funding rate
- `basis_bp_m_5` - 5-minute rolling basis in bps
- `time_to_next_funding_sec` - seconds to next funding

**Residual Features:**
- `z_basis_residual_m_5` - residual of basis (actual - predicted) / prediction_std
- `basis_prediction_m_5` - predicted basis based on funding, OI, volatility, term structure
- `basis_prediction_std_m_5` - standard deviation of basis predictions

### 5. Liquidity / Microstructure

**Raw Features:**
- `spread_mean_m_1` - time-weighted average spread
- `spread_p95_m_1` - 95th percentile spread
- `obi_top5_mean_m_1` - order book imbalance (top 5 levels)
- `depth_top5_quote_median_m_1` - median depth (top 5 levels)

**Residual Features:**
- `z_spread_residual_m_1` - residual of spread (actual - predicted) / prediction_std
- `spread_prediction_m_1` - predicted spread based on volatility, volume, time of day
- `spread_prediction_std_m_1` - standard deviation of spread predictions

### 6. Momentum Indicators (Phase 1 Addition)

**Raw Features:**
- `rsi_14`, `rsi_21`, `rsi_50` - Relative Strength Index (0-100)
- `macd_line`, `macd_signal`, `macd_histogram` - MACD components (12,26,9)
- `stoch_k_14`, `stoch_d_14` - Stochastic Oscillator (0-100)
- `roc_10`, `roc_20` - Rate of Change (percentage)
- `adx_14`, `adx_21` - Average Directional Index (0-100)
- `hma_100` - Hull Moving Average (100 period)
- `atr_14`, `atr_21` - Average True Range (price units)

**Momentum Calculation Logic:**
- **RSI**: RSI = 100 - (100 / (1 + RS)) where RS = avg_gain / avg_loss
- **MACD**: MACD = EMA(12) - EMA(26), Signal = EMA(9) of MACD, Histogram = MACD - Signal
- **Stochastic**: %K = (close - lowest_low) / (highest_high - lowest_low) × 100, %D = SMA(3) of %K
- **ROC**: ROC = (close - close_n_periods_ago) / close_n_periods_ago × 100
- **ADX**: ADX = 100 × SMA(DX) where DX = |DI+ - DI-| / (DI+ + DI-)
- **HMA**: HMA = WMA(2×WMA(n/2) - WMA(n)) where WMA = weighted moving average
- **ATR**: ATR = SMA(True Range) where True Range = max(high-low, |high-prev_close|, |low-prev_close|)

**Residual Features:**
- `z_rsi_residual_14`, `z_macd_residual`, `z_stoch_residual_14` - residuals of momentum indicators
- `q_rsi_residual_14`, `q_macd_residual`, `q_stoch_residual_14` - quantile ranks of residuals
- `rsi_prediction_14`, `macd_prediction`, `stoch_prediction_14` - predicted momentum values
- `momentum_prediction_std` - standard deviation of momentum predictions

### 7. Swing Detection (Phase 1 Addition)

**Raw Features:**
- `swing_highs[]` - array of swing high points (mechanical detection)
- `swing_lows[]` - array of swing low points (mechanical detection)
- `swing_high_time[]` - timestamps of swing highs
- `swing_low_time[]` - timestamps of swing lows
- `current_swing_high`, `current_swing_low` - most recent swings
- `swing_validation_pending` - swings awaiting confirmation

**Swing Detection Logic:**
- **Swing High**: `high[t] = max(high[t-k1...t+k2])` where k1=3, k2=2
- **Swing Low**: `low[t] = min(low[t-k1...t+k2])` where k1=3, k2=2
- **Confirmation**: Swings locked after k2 bars to avoid look-ahead bias

### 8. Advanced Trend Features (Phase 1 Addition)

**Raw Features:**
- `hma_100_slope` - slope of Hull Moving Average (trend direction)
- `atr_percentile_252` - ATR percentile over 252 periods (volatility regime)
- `trend_strength` - composite trend strength score
- `volatility_regime` - classification: low/medium/high volatility

**Normalized:**
- `z_hma_slope`, `z_atr_percentile` - z-scores of trend features

### 9. Level Detection (Phase 2 Addition)

**Raw Features:**
- `prior_day_high`, `prior_day_low` - previous day's high/low
- `weekly_high`, `weekly_low` - current week's high/low
- `vwap_session` - session VWAP
- `vwap_weekly` - weekly VWAP
- `level_proximity_score` - proximity to significant levels

### 10. Breadth Features (Phase 2 Addition)

**Raw Features:**
- `pct_above_ma50`, `pct_above_ma200` - percentage of universe above MA
- `nh_nl` - new highs minus new lows
- `advance_decline_ratio` - advancing vs declining issues
- `breadth_composite` - composite breadth score

**Normalized:**
- `z_breadth_composite` - z-score of breadth composite

### 11. Divergence Detection Features (Phase 1 Addition)

**Hidden Momentum Divergence (Continuation Signals):**
- `hidden_momentum_bull_strength` - strength of hidden bullish momentum divergence (0-1)
- `hidden_momentum_bear_strength` - strength of hidden bearish momentum divergence (0-1)
- `hidden_momentum_trigger` - trigger condition for hidden momentum divergence
- `hidden_momentum_context_score` - context score for divergence validity

**Classic RSI/MACD Divergence (Reversal Signals):**
- `price_rsi_divergence_strength` - strength of price vs RSI divergence (0-1)
- `price_macd_divergence_strength` - strength of price vs MACD divergence (0-1)
- `rsi_divergence_type` - type of RSI divergence (bullish/bearish/hidden)
- `macd_divergence_type` - type of MACD divergence (bullish/bearish/hidden)

**Delta/Volume Divergence (Microstructure Absorption):**
- `delta_volume_divergence_strength` - strength of delta vs volume divergence (0-1)
- `cumulative_delta_divergence` - cumulative delta divergence signal
- `volume_absorption_score` - volume absorption at significant levels

**Divergence Detection Logic:**
- **Hidden Momentum**: Price makes higher high, RSI makes lower high (bearish) OR price makes lower low, RSI makes higher low (bullish)
- **Classic Divergence**: Price makes higher high, indicator makes lower high (bearish) OR price makes lower low, indicator makes higher low (bullish)
- **Delta/Volume**: Price breaks level but volume/delta doesn't confirm the move
- **Context Gates**: Trend direction, volatility regime, level proximity must align
- **Strength Scoring**: Based on divergence magnitude, time span, and confirmation factors

### 12. Residual Manufacturing Features (Phase 1 Addition)

**Cross-Sectional Residuals:**
- `z_cross_sectional_residual_m_1` - cross-sectional residual from factor model
- `cross_sectional_prediction_m_1` - predicted value from market/sector/size factors
- `factor_loadings` - JSONB array of factor loadings (market, sector, size, liquidity)
- `residual_rank` - percentile rank of residual within cross-section

**Time-Series Residuals:**
- `z_kalman_residual_m_1` - Kalman filter innovation residual
- `kalman_state` - latent fair value estimate from state-space model
- `kalman_innovation` - price innovation from state model
- `kalman_prediction_std` - prediction uncertainty from Kalman filter

**Order Flow Residuals:**
- `z_flow_residual_m_1` - order flow prediction residual
- `flow_prediction_m_1` - predicted price change from order flow model
- `flow_features` - JSONB array of flow features (queue imbalance, depth slope, MO intensity)
- `flow_prediction_std` - standard deviation of flow predictions

**Basis/Carry Residuals:**
- `z_carry_residual_m_5` - basis/carry prediction residual
- `carry_prediction_m_5` - predicted basis from funding/OI/volatility model
- `carry_features` - JSONB array of carry features (funding, OI, RV, term structure)
- `carry_prediction_std` - standard deviation of carry predictions

**Lead-Lag Network Residuals:**
- `z_network_residual_m_1` - lead-lag network prediction residual
- `network_prediction_m_1` - predicted value from lead-lag relationships
- `network_features` - JSONB array of network features (correlations, lags, cointegration)
- `network_prediction_std` - standard deviation of network predictions

**Breadth/Market Mode Residuals:**
- `z_breadth_residual_m_5` - market breadth prediction residual
- `breadth_prediction_m_5` - predicted breadth from market mode model
- `market_mode` - current market mode classification (trending/ranging/volatile)
- `breadth_prediction_std` - standard deviation of breadth predictions

**Volatility Surface Residuals:**
- `z_vol_surface_residual_m_1` - volatility surface prediction residual
- `vol_surface_prediction_m_1` - predicted volatility from surface model
- `vol_surface_features` - JSONB array of vol surface features (term structure, skew, kurtosis)
- `vol_surface_prediction_std` - standard deviation of vol surface predictions

**Seasonality/Time-of-Day Residuals:**
- `z_seasonal_residual_m_1` - seasonal prediction residual
- `seasonal_prediction_m_1` - predicted value from seasonal model
- `seasonal_features` - JSONB array of seasonal features (hour, day, week, month effects)
- `seasonal_prediction_std` - standard deviation of seasonal predictions

### 13. Regime Classification Features (Phase 1 Addition)

**Volatility Regime:**
- `atr_percentile_252` - ATR percentile over 252 periods (0-100)
- `volatility_regime` - classification: "low" | "medium" | "high"
- `vol_regime_confidence` - confidence in volatility regime classification (0-1)

**Trend Regime:**
- `adx_14`, `adx_21` - Average Directional Index (0-100)
- `trend_regime` - classification: "trending" | "ranging"
- `trend_direction` - classification: "up" | "down" | "sideways"
- `trend_strength` - composite trend strength score (0-1)

**Session Phase:**
- `session_phase` - classification: "asia" | "europe" | "us" | "overlap"
- `time_of_day` - hour of day (0-23)
- `day_of_week` - day of week (0-6)
- `is_market_open` - boolean for active trading hours

**Market Regime:**
- `market_regime` - composite market regime classification
- `regime_confidence` - confidence in regime classification (0-1)
- `regime_duration` - time in current regime (minutes)
- `regime_transition_prob` - probability of regime transition (0-1)

**Liquidity Regime:**
- `liquidity_regime` - classification: "high" | "medium" | "low"
- `spread_regime` - classification based on spread percentiles
- `volume_regime` - classification based on volume percentiles
- `depth_regime` - classification based on order book depth

### 14. Cheap Flags (Detector-Friendly Booleans)

- `is_vol_spike_m_1` - volume spike flag
- `is_price_spike_up_m_1`, `is_price_spike_down_m_1` - price spike flags
- `is_oi_spike_up_m_5`, `is_oi_spike_down_m_5` - OI spike flags
- `is_spread_stress_m_1` - spread stress flag
- `is_liq_cluster_m_5` - liquidation cluster flag
- `is_divergence_bullish_m_5`, `is_divergence_bearish_m_5` - divergence flags

### 13. Pattern Detection Features (Phase 1 Addition)

**Candlestick Patterns (Single Bar):**
- `is_doji` - doji pattern (body < 10% of total range)
- `is_hammer` - hammer pattern (long lower shadow, short upper shadow)
- `is_shooting_star` - shooting star pattern (long upper shadow, short lower shadow)
- `is_bull_engulfing` - bullish engulfing pattern (current bar engulfs previous)
- `is_bear_engulfing` - bearish engulfing pattern (current bar engulfs previous)
- `is_harami_bull` - bullish harami pattern (small body inside previous large body)
- `is_harami_bear` - bearish harami pattern (small body inside previous large body)
- `is_three_white_soldiers` - three consecutive bullish candles
- `is_three_black_crows` - three consecutive bearish candles

**Support/Resistance Detection (Multi-Bar):**
- `near_support` - price within 1% of nearest support level
- `near_resistance` - price within 1% of nearest resistance level
- `support_breakout` - price breaks below support level
- `resistance_breakout` - price breaks above resistance level
- `support_reclaim` - price reclaims support level after breakout
- `resistance_reclaim` - price reclaims resistance level after breakout
- `level_strength` - strength score of current level (0-1)
- `level_age` - age of current level in bars
- `level_touches` - number of times level has been touched

**Chart Patterns (Multi-Bar):**
- `is_falling_wedge` - falling wedge pattern (converging trend lines)
- `is_rising_wedge` - rising wedge pattern (converging trend lines)
- `is_bull_flag` - bull flag pattern (consolidation after uptrend)
- `is_bear_flag` - bear flag pattern (consolidation after downtrend)
- `is_ascending_triangle` - ascending triangle pattern
- `is_descending_triangle` - descending triangle pattern
- `is_symmetrical_triangle` - symmetrical triangle pattern
- `is_head_shoulders` - head and shoulders pattern
- `is_inverse_head_shoulders` - inverse head and shoulders pattern
- `is_double_top` - double top pattern
- `is_double_bottom` - double bottom pattern

**Diagonal Trend Line Detection (Multi-Bar):**
- `diagonal_support_slope` - slope of rising support trend line
- `diagonal_resistance_slope` - slope of falling resistance trend line
- `diagonal_channel_width` - width of diagonal channel (resistance - support)
- `diagonal_support_break` - price breaks below rising support line
- `diagonal_resistance_break` - price breaks above falling resistance line
- `diagonal_channel_break` - price breaks out of diagonal channel
- `diagonal_line_strength` - strength of diagonal line (R-squared, 0-1)
- `diagonal_touches` - number of times price touched diagonal line
- `diagonal_age` - age of diagonal line in bars
- `diagonal_support_distance` - distance from current price to support line
- `diagonal_resistance_distance` - distance from current price to resistance line
- `diagonal_convergence_rate` - rate at which support/resistance lines converge

**Pattern Confirmation Features:**
- `pattern_volume_confirmation` - volume confirms pattern breakout
- `pattern_time_confirmation` - pattern has sufficient time development
- `pattern_strength_score` - overall pattern strength (0-1)
- `pattern_completion_pct` - percentage of pattern completed
- `pattern_target_price` - projected target price if pattern completes
- `pattern_stop_loss` - suggested stop loss level
- `pattern_risk_reward` - risk/reward ratio

**Level Detection Features:**
- `prior_day_high`, `prior_day_low` - previous day's high/low levels
- `weekly_high`, `weekly_low` - current week's high/low levels
- `monthly_high`, `monthly_low` - current month's high/low levels
- `vwap_session` - session VWAP level
- `vwap_weekly` - weekly VWAP level
- `vwap_monthly` - monthly VWAP level
- `round_number_levels` - nearby round number levels (e.g., 50000, 51000)
- `fibonacci_levels` - nearby Fibonacci retracement levels
- `pivot_points` - daily/weekly pivot points

**Pattern History Storage:**
- `pattern_history` - JSONB array of recent patterns detected
- `swing_point_history` - JSONB array of swing highs/lows
- `level_history` - JSONB array of significant levels
- `breakout_history` - JSONB array of recent breakouts
- `pattern_performance` - JSONB array of pattern success rates

**Normalized Pattern Features:**
- `z_pattern_strength` - z-score of pattern strength
- `z_level_proximity` - z-score of level proximity
- `z_volume_confirmation` - z-score of volume confirmation
- `q_pattern_strength` - quantile rank of pattern strength
- `q_level_proximity` - quantile rank of level proximity

**Pattern Detection Logic:**
- **Candlestick Patterns**: Detected on single bar using OHLC data
  - Body size = |close - open|, Total range = high - low
  - Doji: body < 10% of total range
  - Hammer: lower shadow > 2× body AND upper shadow < body
  - Engulfing: current bar completely engulfs previous bar
- **Support/Resistance**: Detected using swing points and level clustering
  - Level identification: Price levels with 3+ touches within 1% range
  - Breakout detection: Price closes beyond level with volume confirmation
  - Level strength: Based on number of touches and time held
- **Chart Patterns**: Detected using trend line analysis and pattern recognition
  - Wedges: Converging trend lines (falling wedge = descending support + resistance)
  - Triangles: Horizontal support/resistance with converging trend lines
  - Flags: Consolidation patterns after strong moves
  - Head & Shoulders: Three peaks with middle peak highest
- **Diagonal Trend Lines**: Linear regression on swing points
  - Support line: Linear regression on swing lows (slope > 0 for rising)
  - Resistance line: Linear regression on swing highs (slope < 0 for falling)
  - Line strength: R-squared value (0-1) measuring fit quality
  - Breakout detection: Price closes beyond diagonal line with volume
- **Confirmation**: Volume, time, and price action confirmation required
  - Volume confirmation: Volume spike > 1.5× average volume
  - Time confirmation: Pattern must develop over minimum time period
  - Strength confirmation: Pattern strength score > threshold
- **History**: Patterns stored in memory for 100 bars, then archived to DB

**Memory Requirements:**
- **Pattern History**: 100 bars per symbol (2 hours of 1m data)
- **Swing Points**: 50 swing points per symbol
- **Level History**: 20 significant levels per symbol
- **Pattern Storage**: ~1KB per symbol per hour

## Residual Manufacturing Strategy

*Source: [alpha_detector_build_convo.md §4](../alpha_detector_build_convo.md#baseline--normalization-strategy) + WWJSD.md residual factories*

### Predictive Models
- **Cross-Sectional**: Daily ridge regression on market/sector/size/liquidity factors
- **Time-Series**: Kalman filter state-space models with trend/volatility regimes
- **Order Flow**: Flow-fit models using queue imbalance, depth slope, MO intensity
- **Basis/Carry**: Funding/OI/volatility models for perp-spot basis prediction
- **Lead-Lag Network**: Cointegration and correlation models across assets
- **Breadth/Market Mode**: Market-wide regime classification models
- **Volatility Surface**: Term structure and skew models for vol prediction
- **Seasonality**: Time-of-day, day-of-week, seasonal effect models

### Residual Calculation
- **Residual**: `residual_t = (actual_t - predicted_t) / prediction_std_t`
- **Prediction Std**: Rolling standard deviation of prediction errors
- **IQR Clamp**: Applied only for severity scoring, not storage

### Regime Gates
- **ATR Percentile**: Only trade in normal volatility (20th-90th percentile)
- **ADX Bands**: Only trade in trending markets (ADX 12-35)
- **Session Phase**: Only trade during active hours (US/EU overlap, Asia open)
- **Market Regime**: Only trade in appropriate market conditions

### Quantiles
- Online quantile estimation (t-digest or P²) on residuals
- Stored as `q_t ∈ [0,1]` with confidence indicators

## Window Naming Convention

- **Seconds**: `_s_XX` (e.g., `ret_s_30`)
- **Minutes**: `_m_XX` (e.g., `z_vol_m_1`, `oi_roc_m_5`)
- **Hours**: `_h_XX` (e.g., `funding_h_1`)

## Data Quality & Regime Gates

*Source: [alpha_detector_build_convo.md §8](../alpha_detector_build_convo.md#data-quality--safety-rails) + WWJSD.md regime gates*

### Data Quality Gates
- **Warm-up**: No residual emission until min_samples ≥ 200
- **Illiquidity**: Block spikes if `v_total_m_1 < v_min` or `spread_mean_m_1 > spread_cap`
- **Freshness**: OI features NULL if `oi_staleness_ms > 20000`
- **DQ Status**: `ok` | `partial` | `stale` based on feed quality

### Regime Gates (WWJSD Integration)
- **ATR Percentile**: Only emit signals when `atr_percentile_252 ∈ [20, 90]`
- **ADX Bands**: Only emit signals when `adx_14 ∈ [12, 35]`
- **Session Phase**: Only emit signals during active trading hours
- **Volatility Regime**: Only emit signals in "medium" volatility regime
- **Trend Regime**: Only emit signals in "trending" markets
- **Market Regime**: Only emit signals in appropriate market conditions

## Implementation Notes

1. **Rollups**: 15m/1h recomputed from 1m, never averaged
2. **Independence**: Each timeframe has its own baselines
3. **Persistence**: Baseline state saved every minute for fast restarts
4. **Extensibility**: New features go in `extras_json` first, then promoted to typed columns

---

*For complete feature definitions and formulas, see [alpha_detector_build_convo.md §5](../alpha_detector_build_convo.md#feature-computation-spec-per-family)*
