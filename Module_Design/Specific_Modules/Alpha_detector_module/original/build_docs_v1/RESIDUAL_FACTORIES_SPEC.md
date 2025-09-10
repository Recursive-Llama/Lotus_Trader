# Residual Factories Technical Specification

*Source: [alpha_detector_build_convo.md](../alpha_detector_build_convo.md) + [WWJSD.md](WWJSD.md)*

## Overview

This document provides the detailed mathematical formulas, algorithms, and implementation specifications for the 8 residual factories that form the core of our residual manufacturing system. Each factory predicts expected values and computes residuals for anomaly detection.

## Residual Manufacturing Formula

**Core Formula**: `z_residual = (actual - predicted) / prediction_std`

**IQR Clamp**: `z_residual_clamped = clamp(z_residual, -3.0, 3.0)`

**Regime Boost**: `severity = base_severity * (1 + regime_boost_factor)`

---

## 1. Cross-Sectional Residual Factory

### Mathematical Model

**Ridge Regression Model**:
```
r_i,t+τ = β^T F_i,t + ε_i,t
```

Where:
- `r_i,t+τ` = forward return for asset i at time t+τ
- `β` = factor loadings (ridge-regularized)
- `F_i,t` = factor exposures [market, sector, size, liquidity, on-chain, funding/OI]
- `ε_i,t` = residual (our divergence signal)

**Ridge Regularization**:
```
β = (X^T X + λI)^(-1) X^T y
```

Where:
- `λ` = regularization parameter (cross-validated)
- `X` = factor matrix
- `y` = target returns

### Factor Definitions

**Market Factor**: `F_market = (r_i - r_risk_free) / σ_market`

**Sector Factor**: `F_sector = (r_i - r_sector) / σ_sector`

**Size Factor**: `F_size = log(market_cap) - log(market_cap_median)`

**Liquidity Factor**: `F_liquidity = log(volume) - log(volume_median)`

**On-Chain Factor**: `F_onchain = (active_addresses - active_addresses_ma) / active_addresses_std`

**Funding Factor**: `F_funding = (funding_rate - funding_rate_ma) / funding_rate_std`

### Implementation Algorithm

```python
def cross_sectional_residual_factory(symbols, features, target_returns, lookback_days=252):
    """
    Cross-sectional residual factory using ridge regression
    """
    # 1. Prepare factor matrix
    factor_matrix = prepare_factors(symbols, features)
    
    # 2. Ridge regression with purged CV
    model = Ridge(alpha=ridge_alpha)
    model.fit(factor_matrix, target_returns)
    
    # 3. Predict expected returns
    predictions = model.predict(factor_matrix)
    
    # 4. Compute residuals
    residuals = target_returns - predictions
    
    # 5. Standardize residuals
    z_residuals = residuals / np.std(residuals)
    
    return {
        'z_residual': z_residuals,
        'prediction': predictions,
        'prediction_std': np.std(residuals),
        'factor_loadings': model.coef_,
        'residual_rank': rankdata(residuals) / len(residuals)
    }
```

---

## 2. Kalman Filter Residual Factory

### Mathematical Model

**State Space Model**:
```
m_t = A * m_{t-1} + B * X_t + η_t    (state equation)
P_t = C * m_t + ε_t                   (observation equation)
```

Where:
- `m_t` = latent state vector [trend, volatility, mean_reversion]
- `A` = state transition matrix
- `B` = control matrix
- `X_t` = exogenous variables [volume, OI, funding]
- `η_t` = process noise ~ N(0, Q)
- `ε_t` = observation noise ~ N(0, R)

**Kalman Filter Equations**:
```
# Prediction
m_t|t-1 = A * m_{t-1|t-1}
P_t|t-1 = A * P_{t-1|t-1} * A^T + Q

# Update
K_t = P_t|t-1 * C^T * (C * P_t|t-1 * C^T + R)^(-1)
m_t|t = m_t|t-1 + K_t * (y_t - C * m_t|t-1)
P_t|t = (I - K_t * C) * P_t|t-1
```

### Implementation Algorithm

```python
def kalman_residual_factory(price_series, volume_series, oi_series, funding_series):
    """
    Kalman filter residual factory using state-space model
    """
    # 1. Initialize state space model
    state_dim = 3  # [trend, volatility, mean_reversion]
    A = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 0.95]])  # state transition
    B = np.array([[0.1, 0.05, 0.02], [0, 0.1, 0], [0, 0, 0.1]])  # control
    C = np.array([[1, 1, 0]])  # observation
    
    # 2. Initialize Kalman filter
    kf = KalmanFilter(transition_matrices=A, observation_matrices=C)
    kf = kf.em(price_series, n_iter=10)
    
    # 3. Get state estimates
    state_means, state_covs = kf.smooth(price_series)
    
    # 4. Compute predictions
    predictions = C @ state_means.T
    
    # 5. Compute residuals
    residuals = price_series - predictions[0]
    
    # 6. Standardize residuals
    z_residuals = residuals / np.sqrt(np.diag(state_covs))
    
    return {
        'z_residual': z_residuals,
        'kalman_state': state_means,
        'kalman_innovation': residuals,
        'kalman_prediction_std': np.sqrt(np.diag(state_covs))
    }
```

---

## 3. Order Flow Residual Factory

### Mathematical Model

**Flow-Fit Model**:
```
ΔP_t = α + β₁ * QI_t + β₂ * DS_t + β₃ * MO_t + β₄ * VPIN_t + ε_t
```

Where:
- `ΔP_t` = price change
- `QI_t` = queue imbalance = (bid_size - ask_size) / (bid_size + ask_size)
- `DS_t` = depth slope = (ask_price - bid_price) / (ask_size + bid_size)
- `MO_t` = market order intensity = market_orders / total_orders
- `VPIN_t` = volume-synchronized probability of informed trading

**VPIN Calculation**:
```
VPIN_t = Σ|V_buy - V_sell| / (V_buy + V_sell)
```

### Implementation Algorithm

```python
def order_flow_residual_factory(trades, orderbook, lookback_minutes=60):
    """
    Order flow residual factory using microstructure features
    """
    # 1. Compute flow features
    queue_imbalance = compute_queue_imbalance(orderbook)
    depth_slope = compute_depth_slope(orderbook)
    mo_intensity = compute_mo_intensity(trades)
    vpin = compute_vpin(trades)
    
    # 2. Prepare feature matrix
    features = np.column_stack([queue_imbalance, depth_slope, mo_intensity, vpin])
    
    # 3. Ridge regression
    model = Ridge(alpha=0.1)
    model.fit(features, price_changes)
    
    # 4. Predict price changes
    predictions = model.predict(features)
    
    # 5. Compute residuals
    residuals = price_changes - predictions
    
    # 6. Standardize residuals
    z_residuals = residuals / np.std(residuals)
    
    return {
        'z_residual': z_residuals,
        'flow_prediction': predictions,
        'flow_features': {
            'queue_imbalance': queue_imbalance,
            'depth_slope': depth_slope,
            'mo_intensity': mo_intensity,
            'vpin': vpin
        },
        'flow_prediction_std': np.std(residuals)
    }
```

---

## 4. Basis/Carry Residual Factory

### Mathematical Model

**Basis Prediction Model**:
```
basis_t = α + β₁ * funding_t + β₂ * OI_t + β₃ * RV_t + β₄ * term_structure_t + ε_t
```

Where:
- `basis_t` = perp_price - spot_price
- `funding_t` = funding rate
- `OI_t` = open interest
- `RV_t` = realized volatility
- `term_structure_t` = term structure slope

**Term Structure Slope**:
```
term_structure = (funding_1d - funding_8h) / (8h - 1d)
```

### Implementation Algorithm

```python
def basis_carry_residual_factory(perp_prices, spot_prices, funding_rates, oi_data, rv_data):
    """
    Basis/carry residual factory using funding and OI models
    """
    # 1. Compute basis
    basis = perp_prices - spot_prices
    
    # 2. Compute term structure
    term_structure = compute_term_structure(funding_rates)
    
    # 3. Prepare features
    features = np.column_stack([
        funding_rates,
        oi_data,
        rv_data,
        term_structure
    ])
    
    # 4. Ridge regression
    model = Ridge(alpha=0.1)
    model.fit(features, basis)
    
    # 5. Predict basis
    predictions = model.predict(features)
    
    # 6. Compute residuals
    residuals = basis - predictions
    
    # 7. Standardize residuals
    z_residuals = residuals / np.std(residuals)
    
    return {
        'z_residual': z_residuals,
        'carry_prediction': predictions,
        'carry_features': {
            'funding': funding_rates,
            'oi': oi_data,
            'rv': rv_data,
            'term_structure': term_structure
        },
        'carry_prediction_std': np.std(residuals)
    }
```

---

## 5. Lead-Lag Network Residual Factory

### Mathematical Model

**Cointegration Model**:
```
r_i,t = α + β * r_j,t-k + γ * r_market,t + ε_t
```

**Cointegration Test**:
```
ADF_test = (ρ - 1) / SE(ρ)
```

Where:
- `r_i,t` = return of asset i at time t
- `r_j,t-k` = return of asset j at time t-k (lag k)
- `r_market,t` = market return at time t
- `ρ` = autoregressive coefficient

### Implementation Algorithm

```python
def lead_lag_network_residual_factory(symbols, returns_matrix, max_lag=5):
    """
    Lead-lag network residual factory using cointegration
    """
    residuals_dict = {}
    
    for i, symbol_i in enumerate(symbols):
        residuals_list = []
        
        for j, symbol_j in enumerate(symbols):
            if i == j:
                continue
                
            # 1. Test cointegration
            for lag in range(1, max_lag + 1):
                y = returns_matrix[i, lag:]
                X = returns_matrix[j, :-lag]
                
                # Engle-Granger test
                if engle_granger_test(y, X):
                    # 2. Fit cointegration model
                    model = LinearRegression()
                    model.fit(X.reshape(-1, 1), y)
                    
                    # 3. Compute residuals
                    predictions = model.predict(X.reshape(-1, 1))
                    residuals = y - predictions
                    
                    residuals_list.append(residuals)
                    break
        
        # 4. Combine residuals
        if residuals_list:
            combined_residuals = np.mean(residuals_list, axis=0)
            z_residuals = combined_residuals / np.std(combined_residuals)
        else:
            z_residuals = np.zeros(len(returns_matrix[i]))
        
        residuals_dict[symbol_i] = {
            'z_residual': z_residuals,
            'network_prediction': predictions,
            'correlation_strength': np.corrcoef(y, X)[0, 1] if len(X) > 0 else 0
        }
    
    return residuals_dict
```

---

## 6. Breadth/Market Mode Residual Factory

### Mathematical Model

**Market Regime Classification**:
```
P(regime_k | features) = softmax(W * features + b)
```

**Breadth Calculation**:
```
breadth = (advancing_issues - declining_issues) / total_issues
```

### Implementation Algorithm

```python
def breadth_market_mode_residual_factory(symbols, returns_matrix, volume_matrix):
    """
    Breadth/market mode residual factory using regime classification
    """
    # 1. Compute market breadth
    market_returns = np.mean(returns_matrix, axis=0)
    advancing = np.sum(returns_matrix > 0, axis=0)
    declining = np.sum(returns_matrix < 0, axis=0)
    breadth = (advancing - declining) / len(symbols)
    
    # 2. Compute volume breadth
    volume_returns = np.mean(volume_matrix, axis=0)
    volume_advancing = np.sum(volume_matrix > 0, axis=0)
    volume_declining = np.sum(volume_matrix < 0, axis=0)
    volume_breadth = (volume_advancing - volume_declining) / len(symbols)
    
    # 3. Regime classification features
    features = np.column_stack([
        market_returns,
        breadth,
        volume_breadth,
        np.std(returns_matrix, axis=0),  # volatility
        np.mean(volume_matrix, axis=0)   # volume
    ])
    
    # 4. Regime classification
    regime_model = RandomForestClassifier(n_estimators=100)
    regimes = regime_model.fit_predict(features)
    
    # 5. Compute regime-specific residuals
    residuals_dict = {}
    for i, symbol in enumerate(symbols):
        symbol_returns = returns_matrix[i]
        regime_returns = market_returns[regimes == regimes[i]]
        
        if len(regime_returns) > 0:
            residuals = symbol_returns - np.mean(regime_returns)
            z_residuals = residuals / np.std(residuals)
        else:
            z_residuals = np.zeros(len(symbol_returns))
        
        residuals_dict[symbol] = {
            'z_residual': z_residuals,
            'market_regime': regimes[i],
            'breadth': breadth[i],
            'regime_confidence': regime_model.predict_proba(features[i:i+1])[0].max()
        }
    
    return residuals_dict
```

---

## 7. Volatility Surface Residual Factory

### Mathematical Model

**Volatility Surface Model**:
```
σ(K, T) = σ_ATM + β₁ * (K - S) + β₂ * (K - S)² + β₃ * T + β₄ * T² + ε
```

Where:
- `σ(K, T)` = implied volatility at strike K and maturity T
- `σ_ATM` = at-the-money volatility
- `K` = strike price
- `S` = spot price
- `T` = time to maturity

### Implementation Algorithm

```python
def volatility_surface_residual_factory(spot_prices, strikes, maturities, implied_vols):
    """
    Volatility surface residual factory using term structure and skew models
    """
    # 1. Compute moneyness
    moneyness = strikes / spot_prices
    
    # 2. Prepare features
    features = np.column_stack([
        moneyness - 1,  # (K - S) / S
        (moneyness - 1) ** 2,  # (K - S)² / S²
        maturities,
        maturities ** 2
    ])
    
    # 3. Ridge regression
    model = Ridge(alpha=0.1)
    model.fit(features, implied_vols)
    
    # 4. Predict implied volatility
    predictions = model.predict(features)
    
    # 5. Compute residuals
    residuals = implied_vols - predictions
    
    # 6. Standardize residuals
    z_residuals = residuals / np.std(residuals)
    
    return {
        'z_residual': z_residuals,
        'vol_prediction': predictions,
        'vol_features': {
            'moneyness': moneyness,
            'maturity': maturities,
            'atm_vol': np.mean(implied_vols[moneyness == 1])
        },
        'vol_prediction_std': np.std(residuals)
    }
```

---

## 8. Seasonality Residual Factory

### Mathematical Model

**Seasonal Decomposition**:
```
y_t = trend_t + seasonal_t + residual_t
```

**Time-of-Day Effects**:
```
seasonal_t = Σ(β_h * hour_dummy_h + β_d * day_dummy_d + β_w * week_dummy_w)
```

### Implementation Algorithm

```python
def seasonality_residual_factory(price_series, timestamps):
    """
    Seasonality residual factory using time-of-day effects
    """
    # 1. Extract time features
    hours = timestamps.hour
    days = timestamps.dayofweek
    weeks = timestamps.isocalendar().week
    
    # 2. Create dummy variables
    hour_dummies = pd.get_dummies(hours, prefix='hour')
    day_dummies = pd.get_dummies(days, prefix='day')
    week_dummies = pd.get_dummies(weeks, prefix='week')
    
    # 3. Prepare features
    features = np.column_stack([
        hour_dummies.values,
        day_dummies.values,
        week_dummies.values
    ])
    
    # 4. Ridge regression
    model = Ridge(alpha=0.1)
    model.fit(features, price_series)
    
    # 5. Predict seasonal component
    predictions = model.predict(features)
    
    # 6. Compute residuals
    residuals = price_series - predictions
    
    # 7. Standardize residuals
    z_residuals = residuals / np.std(residuals)
    
    return {
        'z_residual': z_residuals,
        'seasonal_prediction': predictions,
        'seasonal_features': {
            'hour_effects': model.coef_[:24],
            'day_effects': model.coef_[24:31],
            'week_effects': model.coef_[31:]
        },
        'seasonal_prediction_std': np.std(residuals)
    }
```

---

## Model Training Implementation

### Purged Cross-Validation

```python
def purged_cv_trainer(X, y, model, n_splits=5, purge_days=5):
    """
    Purged cross-validation for time series data
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores = []
    
    for train_idx, test_idx in tscv.split(X):
        # Purge training data near test period
        purge_start = test_idx[0] - purge_days
        purge_end = test_idx[-1] + purge_days
        
        # Remove purged data from training
        train_mask = (train_idx < purge_start) | (train_idx > purge_end)
        train_idx_clean = train_idx[train_mask]
        
        # Train and test
        model.fit(X[train_idx_clean], y[train_idx_clean])
        score = model.score(X[test_idx], y[test_idx])
        scores.append(score)
    
    return np.mean(scores), np.std(scores)
```

### False Discovery Rate Control

```python
def fdr_control(p_values, alpha=0.05):
    """
    Benjamini-Hochberg FDR control
    """
    sorted_indices = np.argsort(p_values)
    sorted_p_values = p_values[sorted_indices]
    
    # Benjamini-Hochberg procedure
    m = len(p_values)
    critical_values = (np.arange(1, m + 1) / m) * alpha
    
    # Find largest k such that p(k) <= critical_value(k)
    significant = sorted_p_values <= critical_values
    if np.any(significant):
        k = np.max(np.where(significant)[0])
        return sorted_indices[:k+1]
    else:
        return np.array([])
```

### Rolling Out-of-Sample Validation

```python
def rolling_oos_validation(X, y, model, train_window=252, test_window=21):
    """
    Rolling out-of-sample validation
    """
    predictions = []
    actuals = []
    
    for i in range(train_window, len(X) - test_window + 1):
        # Training window
        X_train = X[i-train_window:i]
        y_train = y[i-train_window:i]
        
        # Test window
        X_test = X[i:i+test_window]
        y_test = y[i:i+test_window]
        
        # Train and predict
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        
        predictions.extend(pred)
        actuals.extend(y_test)
    
    return np.array(predictions), np.array(actuals)
```

---

## Performance Considerations

### Computational Complexity

**Cross-Sectional Factory**: O(n²p) where n = number of assets, p = number of features
**Kalman Factory**: O(n³) where n = state dimension
**Order Flow Factory**: O(n) where n = number of trades
**Basis/Carry Factory**: O(n) where n = number of time points
**Lead-Lag Network**: O(n²k) where n = number of assets, k = max lag
**Breadth/Market Mode**: O(n) where n = number of assets
**Volatility Surface**: O(n) where n = number of strikes
**Seasonality Factory**: O(n) where n = number of time points

### Memory Requirements

**Per Symbol Per Minute**:
- Cross-Sectional: ~1KB (factor loadings + residuals)
- Kalman: ~2KB (state vector + covariance)
- Order Flow: ~0.5KB (flow features)
- Basis/Carry: ~0.5KB (carry features)
- Lead-Lag Network: ~1KB (correlation matrix)
- Breadth/Market Mode: ~0.5KB (regime classification)
- Volatility Surface: ~1KB (vol surface)
- Seasonality: ~0.5KB (seasonal effects)

**Total per Symbol**: ~7KB per minute = ~420KB per hour = ~10MB per day

### Latency Impact

**Feature Computation**: +2-5ms per symbol
**Model Prediction**: +1-3ms per symbol
**Residual Calculation**: +0.5-1ms per symbol
**Total Additional Latency**: +3.5-9ms per symbol

---

## Integration with Existing Codebase

### Feature Builder Integration

```python
class ResidualFeatureBuilder(FeatureBuilder):
    def __init__(self):
        super().__init__()
        self.residual_factories = {
            'cross_sectional': CrossSectionalResidualFactory(),
            'kalman': KalmanResidualFactory(),
            'order_flow': OrderFlowResidualFactory(),
            'basis_carry': BasisCarryResidualFactory(),
            'lead_lag_network': LeadLagNetworkResidualFactory(),
            'breadth_market_mode': BreadthMarketModeResidualFactory(),
            'volatility_surface': VolatilitySurfaceResidualFactory(),
            'seasonality': SeasonalityResidualFactory()
        }
    
    def build_residual_features(self, snapshot: FeatureSnapshot) -> FeatureSnapshot:
        """Build residual features using all 8 factories"""
        residual_features = {}
        
        for factory_name, factory in self.residual_factories.items():
            try:
                result = factory.compute_residuals(snapshot)
                residual_features.update(result)
            except Exception as e:
                logger.warning(f"Residual factory {factory_name} failed: {e}")
                continue
        
        return snapshot.copy(update=residual_features)
```

### Detector Integration

```python
class ResidualSpikeDetector(SpikeDetector):
    def check_trigger(self, snapshot: FeatureSnapshot) -> Tuple[bool, int]:
        """Check trigger using residual features instead of z-scores"""
        if not self._check_dq_gates(snapshot):
            return False, 0
        
        if not self._check_regime_gates(snapshot):
            return False, 0
        
        # Use residual features
        primary_residual = getattr(snapshot, f'z_{self.feature}_residual_m_1')
        if primary_residual is None:
            return False, 0
        
        if abs(primary_residual) < self.threshold:
            return False, 0
        
        # Calculate severity with regime boost
        severity = self.calculate_severity(
            primary_residual=primary_residual,
            secondary_residual=getattr(snapshot, f'z_{self.secondary_feature}_residual_m_1'),
            regime_boost=self._get_regime_boost(snapshot)
        )
        
        return True, severity
```

---

## Configuration Management

### Residual Factory Configuration

```yaml
residual_factories:
  cross_sectional:
    enabled: true
    retrain_frequency: "1d"
    lookback_days: 252
    ridge_alpha: 0.1
    features: ["market", "sector", "size", "liquidity", "onchain", "funding"]
    regime_gates:
      atr_percentile: [20, 90]
      adx_bands: [12, 35]
  
  kalman:
    enabled: true
    retrain_frequency: "1d"
    state_dimension: 3
    process_noise: 0.01
    observation_noise: 0.1
    regime_gates:
      atr_percentile: [20, 90]
      session_phase: ["us_eu_overlap", "asia_open"]
  
  order_flow:
    enabled: true
    retrain_frequency: "1h"
    lookback_minutes: 60
    features: ["queue_imbalance", "depth_slope", "mo_intensity", "vpin"]
    regime_gates:
      atr_percentile: [20, 90]
      liquidity_regime: ["normal", "high"]
  
  # ... other factories
```

---

## Monitoring and Alerting

### Model Performance Metrics

```python
class ResidualFactoryMonitor:
    def __init__(self):
        self.metrics = {
            'r2_score': Gauge('residual_factory_r2_score', 'R² score by factory', ['factory_name']),
            'mae': Gauge('residual_factory_mae', 'Mean Absolute Error by factory', ['factory_name']),
            'rmse': Gauge('residual_factory_rmse', 'Root Mean Square Error by factory', ['factory_name']),
            'retrain_status': Gauge('residual_factory_retrain_status', 'Retrain status by factory', ['factory_name']),
            'prediction_latency': Histogram('residual_factory_prediction_latency', 'Prediction latency by factory', ['factory_name']),
            'regime_gate_effectiveness': Gauge('residual_factory_regime_gate_effectiveness', 'Regime gate effectiveness by factory', ['factory_name'])
        }
    
    def update_metrics(self, factory_name: str, performance: dict):
        """Update metrics for a specific factory"""
        self.metrics['r2_score'].labels(factory_name=factory_name).set(performance['r2_score'])
        self.metrics['mae'].labels(factory_name=factory_name).set(performance['mae'])
        self.metrics['rmse'].labels(factory_name=factory_name).set(performance['rmse'])
        self.metrics['retrain_status'].labels(factory_name=factory_name).set(performance['retrain_status'])
        self.metrics['prediction_latency'].labels(factory_name=factory_name).observe(performance['latency'])
        self.metrics['regime_gate_effectiveness'].labels(factory_name=factory_name).set(performance['regime_effectiveness'])
```

### Alerting Rules

```yaml
alerts:
  - alert: ResidualModelDegradation
    expr: residual_factory_r2_score < 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Residual factory {{ $labels.factory_name }} R² score below threshold"
  
  - alert: ModelRetrainFailure
    expr: residual_factory_retrain_status == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Residual factory {{ $labels.factory_name }} retrain failed"
  
  - alert: RegimeGateIneffectiveness
    expr: residual_factory_regime_gate_effectiveness < 0.5
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Residual factory {{ $labels.factory_name }} regime gates ineffective"
```

---

## Testing Strategy

### Unit Tests

```python
class TestResidualFactories:
    def test_cross_sectional_factory(self):
        """Test cross-sectional residual factory"""
        factory = CrossSectionalResidualFactory()
        result = factory.compute_residuals(mock_snapshot)
        
        assert 'z_residual' in result
        assert 'prediction' in result
        assert 'factor_loadings' in result
        assert len(result['z_residual']) == len(mock_snapshot.returns)
    
    def test_kalman_factory(self):
        """Test Kalman filter residual factory"""
        factory = KalmanResidualFactory()
        result = factory.compute_residuals(mock_snapshot)
        
        assert 'z_residual' in result
        assert 'kalman_state' in result
        assert 'kalman_innovation' in result
        assert result['kalman_state'].shape[1] == 3  # state dimension
    
    def test_order_flow_factory(self):
        """Test order flow residual factory"""
        factory = OrderFlowResidualFactory()
        result = factory.compute_residuals(mock_snapshot)
        
        assert 'z_residual' in result
        assert 'flow_features' in result
        assert 'queue_imbalance' in result['flow_features']
        assert 'depth_slope' in result['flow_features']
    
    # ... other factory tests
```

### Integration Tests

```python
class TestResidualIntegration:
    def test_feature_builder_integration(self):
        """Test residual feature builder integration"""
        builder = ResidualFeatureBuilder()
        snapshot = builder.build_residual_features(mock_snapshot)
        
        # Check all residual features are present
        for factory_name in ['cross_sectional', 'kalman', 'order_flow', 'basis_carry']:
            assert hasattr(snapshot, f'z_{factory_name}_residual_m_1')
            assert hasattr(snapshot, f'{factory_name}_prediction_m_1')
    
    def test_detector_integration(self):
        """Test detector integration with residuals"""
        detector = ResidualSpikeDetector()
        snapshot = mock_snapshot_with_residuals()
        
        triggered, severity = detector.check_trigger(snapshot)
        assert isinstance(triggered, bool)
        assert isinstance(severity, int)
        assert severity >= 0
```

## Validation

A residual recipe `R` MUST publish:

**Stationarity Evidence**: ADF p-value < 0.10 on training window
**Coverage**: %bars with non-null outputs ≥ 99%
**Leakage Audit**: no future bars used (enforced by framework)

## Composability

Residuals are DAGs:

**Nodes**: transforms (detrend, z-score, volatility-scale, EWMA, HP filter)
**Edges**: data flow
**Constraints**: acyclic, timestamp-preserving, side-effect free

**Recombination**: `R_new = α·R_a ⊕ (1-α)·R_b`, with α∈[0,1] applied at transform-compatible layers.

---

## Conclusion

This specification provides the complete mathematical foundation and implementation details for all 8 residual factories. Each factory is designed to be:

1. **Mathematically Sound**: Based on proven quantitative finance principles
2. **Computationally Efficient**: Optimized for real-time processing
3. **Regime Aware**: Respects market regime gates for signal quality
4. **Robust**: Includes proper error handling and fallback mechanisms
5. **Monitorable**: Comprehensive metrics and alerting
6. **Testable**: Full unit and integration test coverage

The residual manufacturing system transforms our detector from simple anomaly detection to sophisticated divergence manufacturing, providing the mathematical foundation for high-quality, regime-aware market signals.
