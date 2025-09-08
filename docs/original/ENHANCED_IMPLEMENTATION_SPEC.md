# Enhanced Implementation Specification - Trading Intelligence System

*Source: [build_docs_v1](../build_docs_v1/) + Trading Intelligence System Architecture*

## Overview

This document restores the **detailed technical depth** that was lost in the high-level architecture documents. It provides the complete implementation specifications, mathematical formulas, algorithms, and technical details needed to build the Trading Intelligence System.

## Core Mathematical Formulas

### **1. Kernel Resonance System (Restored)**

#### **Core Selection Layer (Simons) - Signal Quality Metrics (sq_* namespace)**
```python
# Signal quality score (NOT trade profitability)
sq_score = w_accuracy * sq_accuracy + w_precision * sq_precision + w_stability * sq_stability + w_orthogonality * sq_orthogonality - w_cost * sq_cost
```

#### **Phase Resonance Layer (Kernel) (kr_* namespace)**
```python
# Kernel resonance components
kr_hbar = σ(zscore(Page_Hinkley_statistic))        # Market surprise/structural breaks
kr_coherence = spectral_coherence(signal, returns)  # Spectral coherence with returns
kr_phi = |corr(PnL, opportunity_factor)|           # Field resonance/regime alignment
kr_theta = entropy_penalty(memberships)            # Context complexity penalty
kr_rho = complexity_penalty(strategy_dsl)          # Recursive depth penalty
kr_emergence = improvement_slope(sq_score)         # Emergence potential
kr_novelty = embedding_distance(embedding, cohort) # Novelty in embedding space

# Kernel resonance calculation
kr_delta_phi = kr_hbar * kr_coherence * (
    kr_phi**alpha * kr_novelty**beta * kr_emergence**gamma
) / ((1 - kr_theta)**delta * (1 - kr_rho)**epsilon + 1e-6)
```

#### **Final Selection Score (det_* namespace)**
```python
# Geometric blend of both layers
det_sigma = sq_score**u * kr_delta_phi**(1-u)

# Uncertainty abstention
det_abstained = (det_uncert > tau_U) OR (dq_status != 'ok')
```

#### **State-Space Process Implementation**
```python
# State updates
kr_phi_i(t)   = kr_phi_i(t-1) * kr_rho_i(t)
kr_theta_i(t) = kr_theta_i(t-1) + kr_hbar(t) * Σ_j [ kr_phi_j(t) * kr_rho_j(t) ]
kr_rho_i(t+1) = σ( kr_rho_i(t) + α * kr_delta_phi_i(t) - λ * kr_rho_i(t) )

# Sigmoid function
σ(x) = 1 / (1 + e^{-x})
```

#### **Kairos & Entrainment Implementation**
```python
# Market spectrum (Fourier/Wavelet)
X(ω_k,t) = market_spectrum(frequency_k, time_t)

# Detector weight
W_i(t) = kr_phi_i(t) * kr_theta_i(t) * kr_rho_i(t)

# Kairos Score (Timing)
det_kairos_i(t) = [ Σ_k |X(ω_k,t)| * cos( angle(X(ω_k,t)) - phase_i(ω_k) ) * w_k ] / [ Σ_k |X(ω_k,t)| * w_k ] * W_i(t) / ( max_j W_j(t) + ε )

# Entrainment (Ensemble Coherence)
det_entrain_r(t) * e^{i Ψ(t)} = (1/M) * Σ_{m=1..M} e^{i φ_m(t)}
```

### **2. Residual Manufacturing Formulas (Restored)**

#### **Core Residual Formula**
```python
# Core Formula
z_residual = (actual - predicted) / prediction_std

# IQR Clamp
z_residual_clamped = clamp(z_residual, -3.0, 3.0)

# Regime Boost
severity = base_severity * (1 + regime_boost_factor)
```

#### **Cross-Sectional Residual Factory**
```python
# Ridge Regression Model
r_i,t+τ = β^T F_i,t + ε_i,t

# Ridge Regularization
β = (X^T X + λI)^(-1) X^T y

# Factor Definitions
F_market = (r_i - r_risk_free) / σ_market
F_sector = (r_i - r_sector) / σ_sector
F_size = log(market_cap) - log(market_cap_median)
F_liquidity = log(volume) - log(volume_median)
F_onchain = (active_addresses - active_addresses_ma) / active_addresses_std
F_funding = (funding_rate - funding_rate_ma) / funding_rate_std
```

#### **Kalman Filter Residual Factory**
```python
# State Space Model
m_t = A * m_{t-1} + B * X_t + η_t    (state equation)
P_t = C * m_t + ε_t                   (observation equation)

# Kalman Filter Equations
# Prediction
m_t|t-1 = A * m_{t-1|t-1}
P_t|t-1 = A * P_{t-1|t-1} * A^T + Q

# Update
K_t = P_t|t-1 * C^T * (C * P_t|t-1 * C^T + R)^(-1)
m_t|t = m_t|t-1 + K_t * (y_t - C * m_t|t-1)
P_t|t = (I - K_t * C) * P_t|t-1
```

#### **Order Flow Residual Factory**
```python
# Flow-Fit Model
ΔP_t = α + β₁ * QI_t + β₂ * DS_t + β₃ * MO_t + β₄ * VPIN_t + ε_t

# VPIN Calculation
VPIN_t = Σ|V_buy - V_sell| / (V_buy + V_sell)

# Flow Features
QI_t = (bid_size - ask_size) / (bid_size + ask_size)  # Queue imbalance
DS_t = (ask_price - bid_price) / (ask_size + bid_size)  # Depth slope
MO_t = market_orders / total_orders  # Market order intensity
```

#### **Basis/Carry Residual Factory**
```python
# Basis Prediction Model
basis_t = α + β₁ * funding_t + β₂ * OI_t + β₃ * RV_t + β₄ * term_structure_t + ε_t

# Term Structure Slope
term_structure = (funding_1d - funding_8h) / (8h - 1d)
```

#### **Lead-Lag Network Residual Factory**
```python
# Cointegration Model
r_i,t = α + β * r_j,t-k + γ * r_market,t + ε_t

# Cointegration Test
ADF_test = (ρ - 1) / SE(ρ)
```

#### **Breadth/Market Mode Residual Factory**
```python
# Market Regime Classification
P(regime_k | features) = softmax(W * features + b)

# Breadth Calculation
breadth = (advancing_issues - declining_issues) / total_issues
```

#### **Volatility Surface Residual Factory**
```python
# Volatility Surface Model
σ(K, T) = σ_ATM + β₁ * (K - S) + β₂ * (K - S)² + β₃ * T + β₄ * T² + ε
```

#### **Seasonality Residual Factory**
```python
# Seasonal Decomposition
y_t = trend_t + seasonal_t + residual_t

# Time-of-Day Effects
seasonal_t = Σ(β_h * hour_dummy_h + β_d * day_dummy_d + β_w * week_dummy_w)
```

### **3. DSI Integration Formulas (Enhanced)**

#### **MicroTape Tokenization**
```python
# MicroTape Processing
microtape_tokens = tokenize_microtape(orderbook_data, trade_data, volume_data)

# Expert Evidence Fusion
mx_evidence = Σ(w_i * expert_i_output) / Σ(w_i)

# Evidence Boost for Kernel Resonance
kr_enhanced_sigma = det_sigma * (1 + β_mx * mx_evidence)
```

#### **Micro-Expert Ecosystem**
```python
# Grammar/FSM Expert
fsm_output = fsm_expert.evaluate(microtape_tokens)

# Sequence Classifier Expert
classifier_output = tiny_classifier.predict(microtape_sequence)

# Anomaly Scorer Expert
anomaly_output = anomaly_scorer.score(microtape_distribution)

# Divergence Verifier Expert
divergence_output = divergence_verifier.verify(rsi_signal, macd_signal)

# Evidence Fusion
mx_evidence = bayesian_fusion([fsm_output, classifier_output, anomaly_output, divergence_output])
```

## Detailed Implementation Algorithms

### **1. Residual Factory Implementation**

#### **Cross-Sectional Residual Factory**
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

#### **Kalman Filter Residual Factory**
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

### **2. Module Intelligence Implementation**

#### **Alpha Detector Module**
```python
class AlphaDetectorModule:
    def __init__(self, module_id, parent_modules=None):
        self.module_id = module_id
        self.module_type = 'alpha_detector'
        self.parent_modules = parent_modules or []
        
        # Module Intelligence
        self.learning_rate = 0.01
        self.adaptation_threshold = 0.7
        self.performance_history = []
        self.learning_patterns = {}
        self.innovation_score = 0.0
        self.specialization_index = 0.0
        
        # Core Detector Components
        self.residual_factories = self._initialize_residual_factories()
        self.kernel_resonance = self._initialize_kernel_resonance()
        self.dsi_integration = self._initialize_dsi_integration()
        self.trading_plan_generator = self._initialize_trading_plan_generator()
        self.curator_layer = self._initialize_curator_layer()
    
    def generate_trading_plan(self, market_data, dsi_evidence, regime_context):
        """Generate complete trading plan from market data"""
        # 1. Generate residuals using all factories
        residuals = self._generate_residuals(market_data)
        
        # 2. Apply kernel resonance selection
        selected_residuals = self._apply_kernel_resonance(residuals, dsi_evidence)
        
        # 3. Generate trading plan
        trading_plan = self.trading_plan_generator.generate(
            selected_residuals, dsi_evidence, regime_context
        )
        
        # 4. Validate through curator layer
        validated_plan = self.curator_layer.validate_plan(trading_plan)
        
        return validated_plan
    
    def _generate_residuals(self, market_data):
        """Generate residuals using all 8 factories"""
        residuals = {}
        
        for factory_name, factory in self.residual_factories.items():
            try:
                result = factory.compute_residuals(market_data)
                residuals[factory_name] = result
            except Exception as e:
                logger.warning(f"Residual factory {factory_name} failed: {e}")
                continue
        
        return residuals
    
    def _apply_kernel_resonance(self, residuals, dsi_evidence):
        """Apply kernel resonance selection to residuals"""
        selected_residuals = {}
        
        for factory_name, residual_data in residuals.items():
            # Calculate kernel resonance score
            kr_score = self.kernel_resonance.calculate_enhanced_sigma(
                residual_data['z_residual'], dsi_evidence
            )
            
            # Apply DSI evidence boost
            if dsi_evidence:
                kr_score *= (1 + dsi_evidence.get('mx_evidence', 0) * 0.3)
            
            # Select if above threshold
            if kr_score > self.kernel_resonance.sigma_min:
                selected_residuals[factory_name] = residual_data
                selected_residuals[factory_name]['kr_score'] = kr_score
        
        return selected_residuals
```

### **3. DSI System Implementation**

#### **MicroTape Tokenization**
```python
class MicroTapeTokenizer:
    def __init__(self):
        self.token_size = 64  # tokens per microtape
        self.overlap = 0.5    # 50% overlap between tapes
        self.experts = self._initialize_experts()
    
    def tokenize(self, orderbook_data, trade_data, volume_data):
        """Tokenize market microstructure data into MicroTape"""
        # 1. Extract microstructure features
        features = self._extract_microstructure_features(
            orderbook_data, trade_data, volume_data
        )
        
        # 2. Create overlapping windows
        windows = self._create_overlapping_windows(features)
        
        # 3. Tokenize each window
        tokens = []
        for window in windows:
            token = self._tokenize_window(window)
            tokens.append(token)
        
        return tokens
    
    def _extract_microstructure_features(self, orderbook_data, trade_data, volume_data):
        """Extract microstructure features from raw data"""
        features = {}
        
        # Order book features
        features['bid_ask_spread'] = orderbook_data['ask_price'] - orderbook_data['bid_price']
        features['mid_price'] = (orderbook_data['ask_price'] + orderbook_data['bid_price']) / 2
        features['volume_imbalance'] = (orderbook_data['bid_size'] - orderbook_data['ask_size']) / (orderbook_data['bid_size'] + orderbook_data['ask_size'])
        
        # Trade features
        features['trade_size'] = trade_data['size']
        features['trade_price'] = trade_data['price']
        features['trade_direction'] = trade_data['side']  # 'buy' or 'sell'
        
        # Volume features
        features['volume'] = volume_data['volume']
        features['volume_rate'] = volume_data['volume'] / volume_data['time_window']
        
        return features
    
    def _create_overlapping_windows(self, features, window_size=64, overlap=0.5):
        """Create overlapping windows of features"""
        windows = []
        step_size = int(window_size * (1 - overlap))
        
        for i in range(0, len(features) - window_size + 1, step_size):
            window = features[i:i + window_size]
            windows.append(window)
        
        return windows
    
    def _tokenize_window(self, window):
        """Convert window of features to token"""
        # Convert features to token representation
        token = self._features_to_token(window)
        return token
```

#### **Micro-Expert Ecosystem**
```python
class MicroExpertEcosystem:
    def __init__(self):
        self.experts = {
            'fsm': FSMExpert(),
            'classifier': TinyClassifierExpert(),
            'anomaly': AnomalyScorerExpert(),
            'divergence': DivergenceVerifierExpert()
        }
        self.fusion_weights = self._initialize_fusion_weights()
    
    def evaluate(self, microtape_tokens):
        """Evaluate MicroTape tokens using all experts"""
        expert_outputs = {}
        
        for expert_name, expert in self.experts.items():
            try:
                output = expert.evaluate(microtape_tokens)
                expert_outputs[expert_name] = output
            except Exception as e:
                logger.warning(f"Expert {expert_name} failed: {e}")
                expert_outputs[expert_name] = 0.0
        
        # Fuse expert outputs
        fused_evidence = self._fuse_expert_outputs(expert_outputs)
        
        return fused_evidence
    
    def _fuse_expert_outputs(self, expert_outputs):
        """Fuse expert outputs using Bayesian combination"""
        # Weighted average of expert outputs
        weighted_sum = sum(
            self.fusion_weights[expert_name] * output
            for expert_name, output in expert_outputs.items()
        )
        
        total_weight = sum(self.fusion_weights.values())
        
        if total_weight > 0:
            fused_evidence = weighted_sum / total_weight
        else:
            fused_evidence = 0.0
        
        return fused_evidence
```

## Database Schema Implementation

### **1. Enhanced Module Tables**

#### **modules Table**
```sql
CREATE TABLE modules (
    module_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_type VARCHAR(50) NOT NULL, -- 'alpha_detector', 'decision_maker', 'trader'
    module_version VARCHAR(20) NOT NULL,
    parent_modules JSONB, -- Array of parent module IDs
    offspring_modules JSONB, -- Array of offspring module IDs
    generational_depth INTEGER DEFAULT 0,
    
    -- Module Intelligence
    learning_rate DECIMAL(3,2) DEFAULT 0.01, -- 0-1
    adaptation_threshold DECIMAL(3,2) DEFAULT 0.7, -- 0-1
    performance_history JSONB, -- Historical performance data
    learning_patterns JSONB, -- Learned patterns and behaviors
    innovation_score DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    specialization_index DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    
    -- Module Communication
    communication_latency_ms INTEGER DEFAULT 0,
    message_throughput_per_sec INTEGER DEFAULT 0,
    intelligence_sharing_rate DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    collaboration_score DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    peer_ratings JSONB, -- Ratings from other modules
    network_centrality DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    
    -- Module Replication
    replication_readiness DECIMAL(3,2) DEFAULT 0.0, -- 0-1
    parent_performance JSONB, -- Performance of parent modules
    mutation_rate DECIMAL(3,2) DEFAULT 0.1, -- 0-1
    recombination_rate DECIMAL(3,2) DEFAULT 0.1, -- 0-1
    offspring_count INTEGER DEFAULT 0,
    
    -- Module Lifecycle
    lifecycle_stage VARCHAR(20) DEFAULT 'experimental', -- 'experimental', 'active', 'deprecated', 'archived'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active' -- 'active', 'inactive', 'failed'
);
```

#### **trading_plans Table**
```sql
CREATE TABLE trading_plans (
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id UUID REFERENCES modules(module_id),
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Core Trading Plan
    signal_strength DECIMAL(3,2) NOT NULL, -- 0-1
    direction VARCHAR(10) NOT NULL, -- 'long', 'short', 'neutral'
    entry_conditions JSONB, -- Trigger conditions
    entry_price DECIMAL(20,8),
    position_size DECIMAL(5,2), -- % of portfolio
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    time_horizon VARCHAR(10), -- '1m', '5m', '15m', '1h', '4h', '1d'
    risk_reward_ratio DECIMAL(5,2),
    confidence_score DECIMAL(3,2) NOT NULL, -- 0-1
    
    -- Intelligence Validation
    microstructure_evidence JSONB, -- DSI evidence
    regime_context JSONB, -- Market regime context
    module_intelligence JSONB, -- Module-specific intelligence
    execution_notes TEXT,
    valid_until TIMESTAMP WITH TIME ZONE,
    validation_status VARCHAR(20) DEFAULT 'pending', -- 'validated', 'pending', 'failed'
    
    -- Risk Management
    risk_assessment JSONB, -- Risk analysis results
    portfolio_impact JSONB, -- Portfolio impact analysis
    
    -- Performance Tracking
    execution_status VARCHAR(20), -- 'executed', 'partial', 'failed', 'cancelled'
    executed_price DECIMAL(20,8),
    executed_quantity DECIMAL(20,8),
    execution_cost DECIMAL(20,8),
    slippage DECIMAL(8,4),
    pnl DECIMAL(20,8),
    performance_metrics JSONB, -- Detailed performance analysis
    attribution_analysis JSONB -- Performance attribution analysis
);
```

### **2. DSI Integration Tables**

#### **dsi_evidence Table**
```sql
CREATE TABLE dsi_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES trading_plans(plan_id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- MicroTape Evidence
    mx_evidence DECIMAL(3,2) NOT NULL, -- 0-1
    mx_confirm BOOLEAN NOT NULL,
    mx_expert_contributions JSONB, -- Individual expert outputs
    mx_microtape_hash VARCHAR(64), -- Hash of input MicroTape
    mx_processing_latency_ms INTEGER,
    mx_confidence_interval JSONB, -- Confidence interval for evidence score
    
    -- Micro-Expert Ecosystem
    mx_fsm_experts JSONB, -- Grammar/FSM expert outputs
    mx_classifier_experts JSONB, -- Tiny sequence classifier outputs
    mx_anomaly_experts JSONB, -- Anomaly scorer outputs
    mx_divergence_experts JSONB, -- Divergence verifier outputs
    mx_expert_weights JSONB, -- Learned weights for expert contributions
    mx_expert_survival_rates JSONB, -- Expert survival rates over time
    
    -- DSI Integration
    mx_evidence_boost DECIMAL(5,4), -- Evidence boost factor
    mx_confirm_rate DECIMAL(3,2), -- Confirmation rate across micro-experts
    mx_expert_survival_rate DECIMAL(3,2), -- Expert contribution survival rate
    mx_latency_p50 INTEGER, -- 50th percentile processing latency
    mx_latency_p95 INTEGER, -- 95th percentile processing latency
    mx_throughput_per_second INTEGER -- Expert processing throughput
);
```

### **3. Enhanced Feature Tables**

#### **market_data_1m Table (Enhanced)**
```sql
CREATE TABLE market_data_1m (
    -- Core OHLCV data (preserved)
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- DSI Integration (new)
    mx_evidence DECIMAL(3,2), -- DSI evidence score
    mx_confirm BOOLEAN, -- DSI confirmation flag
    mx_expert_contributions JSONB, -- DSI expert outputs
    
    -- Module Intelligence (new)
    module_intelligence JSONB, -- Module-specific intelligence
    module_learning_updates JSONB, -- Learning updates from modules
    
    -- Enhanced Features (preserved + enhanced)
    -- ... (all existing features from v1)
    
    PRIMARY KEY (symbol, timestamp)
);
```

## Performance Requirements

### **1. Latency Targets**
- **Trading Plans**: < 100ms (Alpha Detector → Decision Maker)
- **Approvals**: < 50ms (Decision Maker → Trader)
- **Feedback**: < 500ms (Trader → Alpha Detector)
- **Intelligence Sharing**: < 1s (All modules)
- **DSI Processing**: < 10ms (MicroTape analysis)

### **2. Throughput Targets**
- **Trading Plans**: 1000 plans/second
- **Feedback Messages**: 500 messages/second
- **Intelligence Broadcasts**: 100 broadcasts/second
- **Replication Signals**: 10 signals/second
- **DSI Processing**: 1000+ expert evaluations/second

### **3. Reliability Targets**
- **Message Delivery**: 99.9% success rate
- **System Availability**: 99.99% uptime
- **Data Integrity**: 100% message integrity
- **Module Health**: 99.9% module availability

### **4. Memory Requirements**
- **Per Symbol Per Minute**: ~7KB (residual factories + DSI)
- **Per Symbol Per Hour**: ~420KB
- **Per Symbol Per Day**: ~10MB
- **Total System Memory**: ~1GB for 100 symbols

## Configuration Management

### **1. Kernel Resonance Configuration**
```yaml
kernel_resonance:
  # Geometric blend weights
  u: 0.6                    # Weight for Simons core (sq_score)
  
  # Phase resonance weights
  alpha: 1.0                # Field resonance (kr_phi) weight
  beta: 0.8                 # Novelty (kr_novelty) weight  
  gamma: 0.8                # Emergence (kr_emergence) weight
  delta: 0.7                # Context complexity penalty weight
  epsilon: 0.7              # Depth complexity penalty weight
  
  # Selection thresholds
  sigma_min: 0.35           # Minimum sigma_select for promotion
  sigma_deprecate: 0.05     # Sigma threshold for deprecation
  uncertainty_max: 0.3      # Maximum uncertainty for execution
  
  # Computation parameters
  surprise_window: 252      # Days for structural break detection
  coherence_bands: [0.1, 0.9]  # Frequency bands for spectral coherence
  novelty_embedding_dim: 1536  # Embedding dimension for novelty
  emergence_slope_window: 30   # Days for emergence slope calculation
```

### **2. Residual Factory Configuration**
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
```

### **3. DSI Configuration**
```yaml
dsi_system:
  microtape:
    token_size: 64
    overlap: 0.5
    processing_latency_target: 10  # ms
  
  micro_experts:
    fsm_expert:
      enabled: true
      pattern_library_size: 1000
      evaluation_latency_target: 2  # ms
    
    classifier_expert:
      enabled: true
      model_size: "1B"  # 1B parameters
      evaluation_latency_target: 3  # ms
    
    anomaly_expert:
      enabled: true
      distribution_window: 1000
      evaluation_latency_target: 2  # ms
    
    divergence_expert:
      enabled: true
      rsi_period: 14
      macd_periods: [12, 26, 9]
      evaluation_latency_target: 1  # ms
  
  fusion:
    method: "bayesian"
    weights: "adaptive"
    confidence_threshold: 0.7
```

## Testing Strategy

### **1. Unit Tests**
```python
class TestKernelResonance:
    def test_sq_score_calculation(self):
        """Test signal quality score calculation"""
        # Test data
        accuracy = 0.8
        precision = 0.7
        stability = 0.9
        orthogonality = 0.6
        cost = 0.3
        
        # Calculate sq_score
        sq_score = calculate_sq_score(accuracy, precision, stability, orthogonality, cost)
        
        # Assertions
        assert 0 <= sq_score <= 1
        assert sq_score > 0.5  # Should be reasonable score
    
    def test_kr_delta_phi_calculation(self):
        """Test kernel resonance calculation"""
        # Test data
        kr_hbar = 0.8
        kr_coherence = 0.7
        kr_phi = 0.6
        kr_novelty = 0.5
        kr_emergence = 0.4
        kr_theta = 0.2
        kr_rho = 0.3
        
        # Calculate kr_delta_phi
        kr_delta_phi = calculate_kr_delta_phi(
            kr_hbar, kr_coherence, kr_phi, kr_novelty, 
            kr_emergence, kr_theta, kr_rho
        )
        
        # Assertions
        assert 0 <= kr_delta_phi <= 1
        assert kr_delta_phi > 0  # Should be positive
```

### **2. Integration Tests**
```python
class TestResidualFactoryIntegration:
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
```

### **3. Performance Tests**
```python
class TestPerformanceRequirements:
    def test_dsi_processing_latency(self):
        """Test DSI processing meets latency requirements"""
        dsi_system = DSISystem()
        
        start_time = time.time()
        evidence = dsi_system.process_microtape(mock_microtape)
        processing_time = (time.time() - start_time) * 1000  # ms
        
        assert processing_time < 10  # Should be < 10ms
    
    def test_trading_plan_generation_latency(self):
        """Test trading plan generation meets latency requirements"""
        detector = AlphaDetectorModule()
        
        start_time = time.time()
        plan = detector.generate_trading_plan(mock_market_data, mock_dsi_evidence, mock_regime_context)
        generation_time = (time.time() - start_time) * 1000  # ms
        
        assert generation_time < 100  # Should be < 100ms
```

## Monitoring and Alerting

### **1. Performance Metrics**
```python
class TradingIntelligenceMonitor:
    def __init__(self):
        self.metrics = {
            'trading_plan_latency': Histogram('trading_plan_latency_ms', 'Trading plan generation latency', ['module_type']),
            'dsi_processing_latency': Histogram('dsi_processing_latency_ms', 'DSI processing latency', ['expert_type']),
            'module_performance': Gauge('module_performance_score', 'Module performance score', ['module_id', 'module_type']),
            'replication_success_rate': Gauge('replication_success_rate', 'Module replication success rate', ['module_type']),
            'intelligence_sharing_rate': Gauge('intelligence_sharing_rate', 'Intelligence sharing rate', ['module_id']),
            'trading_plan_success_rate': Gauge('trading_plan_success_rate', 'Trading plan success rate', ['module_id'])
        }
    
    def update_trading_plan_metrics(self, module_id, module_type, latency_ms):
        """Update trading plan generation metrics"""
        self.metrics['trading_plan_latency'].labels(
            module_type=module_type
        ).observe(latency_ms)
    
    def update_dsi_metrics(self, expert_type, latency_ms):
        """Update DSI processing metrics"""
        self.metrics['dsi_processing_latency'].labels(
            expert_type=expert_type
        ).observe(latency_ms)
```

### **2. Alerting Rules**
```yaml
alerts:
  - alert: TradingPlanLatencyHigh
    expr: trading_plan_latency_ms > 100
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Trading plan generation latency high for {{ $labels.module_type }}"
  
  - alert: DSIProcessingLatencyHigh
    expr: dsi_processing_latency_ms > 10
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "DSI processing latency high for {{ $labels.expert_type }}"
  
  - alert: ModulePerformanceDegraded
    expr: module_performance_score < 0.5
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "Module {{ $labels.module_id }} performance degraded"
  
  - alert: ReplicationFailure
    expr: replication_success_rate < 0.6
    for: 15m
    labels:
      severity: critical
    annotations:
      summary: "Module replication success rate low for {{ $labels.module_type }}"
```

---

*This enhanced implementation specification restores all the detailed technical depth needed to build the Trading Intelligence System, including mathematical formulas, algorithms, database schemas, performance requirements, and testing strategies.*
