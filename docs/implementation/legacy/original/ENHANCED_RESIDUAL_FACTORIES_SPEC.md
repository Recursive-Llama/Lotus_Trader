# Enhanced Residual Factories Specification - Trading Intelligence System

*Source: [build_docs_v1/RESIDUAL_FACTORIES_SPEC.md](../build_docs_v1/RESIDUAL_FACTORIES_SPEC.md) + Trading Intelligence System Integration*

## Overview

This document restores the **complete mathematical formulas, algorithms, and implementation details** for the 8 residual factories that form the core of our residual manufacturing system. Each factory predicts expected values and computes residuals for anomaly detection, now enhanced with **DSI integration** and **module intelligence**.

## Residual Manufacturing Formula

**Core Formula**: `z_residual = (actual - predicted) / prediction_std`

**IQR Clamp**: `z_residual_clamped = clamp(z_residual, -3.0, 3.0)`

**Regime Boost**: `severity = base_severity * (1 + regime_boost_factor)`

**DSI Enhancement**: `z_residual_enhanced = z_residual * (1 + β_mx * mx_evidence)`

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

## DSI Integration Enhancement

### Enhanced Residual Calculation

```python
def enhanced_residual_calculation(base_residuals, dsi_evidence, module_intelligence):
    """
    Enhance residuals with DSI evidence and module intelligence
    """
    enhanced_residuals = {}
    
    for factory_name, residual_data in base_residuals.items():
        # Base residual
        z_residual = residual_data['z_residual']
        
        # DSI evidence boost
        dsi_boost = 1.0
        if dsi_evidence:
            dsi_boost = 1 + (dsi_evidence.get('mx_evidence', 0) * 0.3)
        
        # Module intelligence boost
        module_boost = 1.0
        if module_intelligence:
            learning_rate = module_intelligence.get('learning_rate', 0.01)
            innovation_score = module_intelligence.get('innovation_score', 0.0)
            module_boost = 1 + (learning_rate * 0.5) + (innovation_score * 0.2)
        
        # Enhanced residual
        enhanced_z_residual = z_residual * dsi_boost * module_boost
        
        # Clamp to reasonable range
        enhanced_z_residual = np.clip(enhanced_z_residual, -5.0, 5.0)
        
        enhanced_residuals[factory_name] = {
            **residual_data,
            'z_residual': enhanced_z_residual,
            'dsi_boost': dsi_boost,
            'module_boost': module_boost,
            'enhancement_factor': dsi_boost * module_boost
        }
    
    return enhanced_residuals
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
**DSI Enhancement**: +1-2ms per symbol
**Total Additional Latency**: +4.5-11ms per symbol

---

*This enhanced specification restores all the detailed mathematical formulas and algorithms for the 8 residual factories, now integrated with DSI evidence and module intelligence for the Trading Intelligence System.*
