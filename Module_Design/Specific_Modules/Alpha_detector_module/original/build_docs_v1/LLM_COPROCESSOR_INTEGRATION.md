# LLM Coprocessor Integration: Deep Intelligence Weaving

*Source: [intelligence_commincation_roughplan.md](../intelligence_commincation_roughplan.md) + Enhanced Integration with Alpha Detector System*

## Executive Summary

The LLM Coprocessor Integration represents a fundamental enhancement to the Alpha Detector system, introducing **Deep Signal Intelligence (DSI)** that operates at the microstructure level to separate signal from noise. This integration weaves intelligence throughout the existing architecture while maintaining the core principles of deterministic, numeric computation in the hot path.

**Key Innovation**: Each module becomes a **self-contained intelligence unit** with its own curator layer, trading plan generation, and self-learning capabilities. The Alpha Detector module generates complete trading plans, not just signals, while the Decision Maker module provides only yes/no approval or plan modifications.

## The Missing Intelligence Layer

### Current System Architecture
The existing Alpha Detector system has:
- **Evolutionary Selection**: Breeds many small detectors, measures fitness, lets survivors advance
- **Residual Manufacturing**: Uses predictive models instead of simple z-scores
- **Kernel Resonance**: Two-layer selection combining Simons core + phase resonance
- **Curator Layer**: High-level governance and oversight
- **Numeric Hot Path**: Pure mathematical computation for speed and determinism

### The Gap: Module-Level Intelligence and Self-Learning
The current system excels at:
- High-level pattern detection (candlesticks, divergences, regime changes)
- Cross-sectional analysis and factor modeling
- Evolutionary selection and optimization

But lacks:
- **Module-level intelligence**: Each module should be self-contained with its own curator layer
- **Complete trading plan generation**: Alpha Detector should generate full trading plans, not just signals
- **Self-learning and self-correcting**: Each module should improve itself based on its own performance
- **Microstructure intelligence**: Reading order book dynamics, trade tape patterns, liquidity vacuums
- **Signal-in-noise routing**: Understanding when detectors deserve attention based on market microstructure
- **Real-time pattern confirmation**: Validating high-level signals with low-level evidence

## Module-Level Intelligence Architecture

### 1. **Curator as Intelligence Level in Each Module**

Each module becomes a **self-contained intelligence unit** with its own curator layer:

#### Alpha Detector Module Curators
- **DSI Curator**: Microstructure evidence quality and expert performance
- **Pattern Curator**: Candlestick and chart pattern validation
- **Divergence Curator**: RSI/MACD divergence confirmation
- **Regime Curator**: Market regime alignment and timing
- **Evolution Curator**: Detector breeding and mutation control
- **Performance Curator**: Signal quality and detector fitness

#### Decision Maker Module Curators
- **Risk Curator**: Portfolio risk and position sizing
- **Allocation Curator**: Asset allocation and diversification
- **Timing Curator**: Entry/exit timing optimization
- **Cost Curator**: Transaction cost and slippage management
- **Compliance Curator**: Regulatory and policy adherence

#### Trader Module Curators
- **Execution Curator**: Order execution quality and venue selection
- **Latency Curator**: Execution speed and timing
- **Slippage Curator**: Market impact and cost control
- **Position Curator**: Position tracking and risk management
- **Performance Curator**: P&L attribution and analysis

### 2. **Complete Trading Plan Generation**

The Alpha Detector module generates **complete trading plans**, not just signals:

#### Trading Plan Schema
```python
class TradingPlan:
    def __init__(self):
        self.signal_strength: float          # Signal confidence [0,1]
        self.direction: str                  # 'long', 'short', 'neutral'
        self.entry_conditions: List[str]     # Trigger conditions
        self.entry_price: float              # Target entry price
        self.position_size: float            # Position size as % of portfolio
        self.stop_loss: float                # Stop loss price
        self.take_profit: float              # Take profit price
        self.time_horizon: str               # '1m', '5m', '15m', '1h', '4h', '1d'
        self.risk_reward_ratio: float        # Risk/reward ratio
        self.confidence_score: float         # Overall confidence [0,1]
        self.microstructure_evidence: Dict   # DSI evidence
        self.regime_context: Dict           # Market regime context
        self.execution_notes: str           # Execution instructions
        self.valid_until: datetime          # Plan expiration
```

#### Plan Generation Process
1. **Signal Detection**: Standard detector triggers
2. **DSI Validation**: Microstructure evidence confirmation
3. **Risk Assessment**: Position sizing and risk calculation
4. **Entry/Exit Planning**: Price targets and timing
5. **Execution Planning**: Venue selection and order type
6. **Curator Review**: Module-level curator validation
7. **Plan Finalization**: Complete trading plan output

### 3. **Self-Learning and Self-Correcting at Module Level**

Each module continuously learns and improves itself:

#### Learning Mechanisms
- **Performance Feedback**: Track plan success/failure rates
- **Curator Learning**: Curators learn from their decisions
- **Parameter Optimization**: Continuous tuning of module parameters
- **Pattern Recognition**: Learn new patterns and market behaviors
- **Adaptive Thresholds**: Adjust detection thresholds based on performance

#### Self-Correction Process
```python
class ModuleSelfLearning:
    def __init__(self, module_type):
        self.module_type = module_type
        self.performance_history = []
        self.learning_rate = 0.01
        self.adaptation_threshold = 0.1
    
    def update_performance(self, plan_id, outcome):
        """Update performance based on trading outcome"""
        self.performance_history.append({
            'plan_id': plan_id,
            'outcome': outcome,
            'timestamp': datetime.now()
        })
        
        # Trigger learning if performance degrades
        if self.performance_degraded():
            self.adapt_parameters()
    
    def adapt_parameters(self):
        """Adapt module parameters based on performance"""
        # Analyze performance patterns
        patterns = self.analyze_performance_patterns()
        
        # Update parameters
        for pattern in patterns:
            if pattern['type'] == 'threshold_adjustment':
                self.adjust_thresholds(pattern['adjustment'])
            elif pattern['type'] == 'curator_weight_update':
                self.update_curator_weights(pattern['weights'])
            elif pattern['type'] == 'new_pattern_detection':
                self.add_new_pattern(pattern['pattern'])
```

## Deep Signal Intelligence (DSI) Architecture

### Core Design Principles

#### 1. **Hot Path Ban**
- No LLM calls in live scoring
- All outputs must be compiled, versioned, and numerically validated
- Runtime path stays numeric and fast (< 10ms)

#### 2. **Many Small Models (Jim Simmons Style)**
- Dozens of tiny experts running in parallel
- Survival-of-the-fittest: experts with positive contribution survive
- Orthogonality: correlation cap among experts' outputs

#### 3. **Evidence-Based Integration**
- DSI produces numeric evidence, not decisions
- Evidence feeds into existing kernel resonance system
- Maintains mathematical integrity and auditability

### MicroTape Tokenization System

#### Event Stream Processing
The DSI system tokenizes Hyperliquid socket data into a **MicroTape** - a compact, loss-aware event stream:

```python
# MicroTape Event Types
TICK: {
    dPx_bps: float,           # Price change in basis points
    vol_rel: float,           # Volume relative to recent average
    spread_bps: float,        # Bid-ask spread
    book_imb_1: float,        # Top-of-book imbalance
    book_imb_5: float,        # 5-level book imbalance
    book_imb_10: float,       # 10-level book imbalance
    depth_slope: float,       # Order book depth slope
    cancel_rate: float,       # Order cancellation rate
    sweep_flag: bool,         # Market order sweep detected
    funding_tick: bool        # Funding rate update
}

CANDLE: {
    wick_up_bps: float,       # Upper wick size
    wick_dn_bps: float,       # Lower wick size
    body_bps: float,          # Body size
    range_pctl: float,        # Range percentile
    close_loc: float,         # Close location within range
    gap_flag: bool            # Gap from previous candle
}

DERIVED: {
    OI_delta: float,          # Open interest change
    basis_delta: float,       # Basis change
    microprice_drift: float,  # Microprice drift
    runlen_aggr: float,       # Aggressive trade run length
    l2_imbalance_shock: float # L2 imbalance shock
}
```

#### Rolling Window Processing
- Maintains last 256 events per symbol
- 50-200ms cadence for real-time processing
- Loss-aware compression for efficient storage

### Micro-Expert Ecosystem

#### 1. **Grammar/FSM Experts (Zero-Latency)**
**Purpose**: Compiled candlestick and order book grammars
**Examples**:
- "Three wicks + depth vacuum + sweep within N ticks"
- "Order book depletion + aggressive run + spread widening"
- "Funding rate flip + OI spike + price divergence"

**Implementation**:
```python
class FSMExpert:
    def __init__(self, grammar_spec):
        self.fsm = compile_grammar(grammar_spec)
        self.state = initial_state()
    
    def process_tick(self, tick_event):
        self.state = self.fsm.transition(self.state, tick_event)
        return {
            'z': self.state.confidence,
            'f': self.state.pattern_detected,
            'conf': self.state.calibrated_confidence
        }
```

#### 2. **Tiny Sequence Classifiers (1-3B Models)**
**Purpose**: State labeling for complex patterns
**Examples**:
- Incipient squeeze detection
- Fakeout risk assessment
- Retest validation
- Exhaustion signals

**Implementation**:
```python
class SequenceClassifier:
    def __init__(self, model_path):
        self.model = load_quantized_model(model_path)
        self.sequence_buffer = deque(maxlen=64)
    
    def process_sequence(self, microtape_window):
        features = self.extract_features(microtape_window)
        logits = self.model(features)
        return {
            'z': logits[0],  # Log-likelihood ratio
            'f': logits[1] > 0.5,  # Binary classification
            'conf': sigmoid(logits[1])  # Calibrated confidence
        }
```

#### 3. **Anomaly Scorers**
**Purpose**: Distributional outlier detection
**Methods**:
- Density ratio estimation
- Kernel Density Estimation (KDE)
- Isolation Forest
- One-class SVM

**Implementation**:
```python
class AnomalyScorer:
    def __init__(self, method='isolation_forest'):
        self.model = IsolationForest(contamination=0.1)
        self.calibration_data = []
    
    def score_anomaly(self, features):
        anomaly_score = self.model.decision_function([features])[0]
        return {
            'z': anomaly_score,
            'f': anomaly_score < -0.5,
            'conf': self.calibrate_confidence(anomaly_score)
        }
```

#### 4. **Divergence Verifiers**
**Purpose**: Confirm RSI/MACD divergences with microstructure evidence
**Logic**:
- RSI divergence + order book confirmation
- MACD divergence + trade tape validation
- Volume divergence + liquidity confirmation

### Evidence Fusion System

#### Bayesian Accumulator
```python
def fuse_micro_evidence(expert_outputs, weights, confirmation_threshold):
    """
    Fuse multiple expert outputs into unified evidence
    """
    # Log-likelihood ratio fusion
    micro_LLR = sum(w_j * z_j for w_j, z_j in zip(weights, expert_outputs))
    
    # M-of-N confirmation
    micro_confirm = sum(a_j * f_j for a_j, f_j in zip(weights, expert_outputs)) >= confirmation_threshold
    
    # Calibrated evidence score
    micro_evidence = sigmoid(micro_LLR)
    
    return {
        'mx_evidence': micro_evidence,
        'mx_confirm': micro_confirm,
        'expert_contributions': expert_outputs
    }
```

#### Expert Weight Learning
```python
def learn_expert_weights(expert_outputs, detector_performance, lookback_days=30):
    """
    Learn expert weights based on contribution to detector performance
    """
    # Compute contribution to det_sigma improvement
    contributions = []
    for expert_id, outputs in expert_outputs.items():
        correlation = np.corrcoef(outputs['z'], detector_performance)[0,1]
        contributions.append(correlation)
    
    # Normalize weights
    weights = softmax(contributions)
    return weights
```

## Integration with Existing Systems

### 1. **Module-Level Intelligence Integration**

#### Alpha Detector Module Enhancement
```python
class EnhancedAlphaDetector:
    def __init__(self):
        self.dsi_system = DeepSignalIntelligence()
        self.curators = {
            'dsi': DSICurator(),
            'pattern': PatternCurator(),
            'divergence': DivergenceCurator(),
            'regime': RegimeCurator(),
            'evolution': EvolutionCurator(),
            'performance': PerformanceCurator()
        }
        self.self_learning = ModuleSelfLearning('alpha_detector')
    
    def generate_trading_plan(self, market_data):
        """Generate complete trading plan with module-level intelligence"""
        # 1. Standard signal detection
        signals = self.detect_signals(market_data)
        
        # 2. DSI validation
        dsi_evidence = self.dsi_system.process_microtape(market_data)
        
        # 3. Curator review
        curator_decisions = {}
        for curator_name, curator in self.curators.items():
            curator_decisions[curator_name] = curator.evaluate(signals, dsi_evidence)
        
        # 4. Generate trading plan
        if self.all_curators_approve(curator_decisions):
            plan = self.create_trading_plan(signals, dsi_evidence, curator_decisions)
            return plan
        else:
            return None  # Vetoed by curators
    
    def create_trading_plan(self, signals, dsi_evidence, curator_decisions):
        """Create complete trading plan with all necessary details"""
        return TradingPlan(
            signal_strength=self.calculate_signal_strength(signals, dsi_evidence),
            direction=self.determine_direction(signals),
            entry_conditions=self.generate_entry_conditions(signals, dsi_evidence),
            entry_price=self.calculate_entry_price(signals, dsi_evidence),
            position_size=self.calculate_position_size(signals, curator_decisions),
            stop_loss=self.calculate_stop_loss(signals, dsi_evidence),
            take_profit=self.calculate_take_profit(signals, dsi_evidence),
            time_horizon=self.determine_time_horizon(signals),
            risk_reward_ratio=self.calculate_risk_reward(signals),
            confidence_score=self.calculate_confidence(signals, dsi_evidence, curator_decisions),
            microstructure_evidence=dsi_evidence,
            regime_context=self.get_regime_context(signals),
            execution_notes=self.generate_execution_notes(signals, dsi_evidence),
            valid_until=self.calculate_expiration(signals)
        )
```

#### Decision Maker Module Integration
```python
class EnhancedDecisionMaker:
    def __init__(self):
        self.curators = {
            'risk': RiskCurator(),
            'allocation': AllocationCurator(),
            'timing': TimingCurator(),
            'cost': CostCurator(),
            'compliance': ComplianceCurator()
        }
        self.self_learning = ModuleSelfLearning('decision_maker')
    
    def evaluate_trading_plan(self, trading_plan):
        """Evaluate trading plan and provide yes/no or modifications"""
        # 1. Curator evaluation
        curator_decisions = {}
        for curator_name, curator in self.curators.items():
            curator_decisions[curator_name] = curator.evaluate(trading_plan)
        
        # 2. Generate decision
        if self.all_curators_approve(curator_decisions):
            return {
                'decision': 'approve',
                'plan': trading_plan,
                'modifications': None
            }
        elif self.can_modify(curator_decisions):
            modified_plan = self.apply_modifications(trading_plan, curator_decisions)
            return {
                'decision': 'modify',
                'plan': modified_plan,
                'modifications': self.get_modifications(curator_decisions)
            }
        else:
            return {
                'decision': 'reject',
                'plan': None,
                'modifications': None,
                'reasons': self.get_rejection_reasons(curator_decisions)
            }
```

### 2. **Kernel Resonance Enhancement with Module Intelligence**

#### Current Formula
```python
det_sigma = sq_score**u * kr_delta_phi**(1-u)
```

#### Enhanced with Module Intelligence
```python
# Module-level intelligence integration
def calculate_enhanced_det_sigma(signals, dsi_evidence, curator_decisions):
    # Base kernel resonance
    base_det_sigma = sq_score**u * kr_delta_phi**(1-u)
    
    # DSI evidence boost
    dsi_boost = 1 + β_mx * dsi_evidence['mx_evidence']
    
    # Curator confidence weighting
    curator_confidence = calculate_curator_confidence(curator_decisions)
    
    # Module learning adjustment
    learning_adjustment = get_module_learning_adjustment()
    
    # Enhanced selection score
    enhanced_det_sigma = base_det_sigma * dsi_boost * curator_confidence * learning_adjustment
    
    return enhanced_det_sigma
```

#### Integration Points
- **mx_evidence**: Continuous evidence score [0,1] from DSI
- **mx_confirm**: Binary confirmation flag from DSI
- **curator_decisions**: Module-level curator evaluations
- **learning_adjustment**: Self-learning parameter updates
- **β_mx, γ_mx**: Learned parameters from OOS validation

### 2. **Residual Factory Enhancement**

#### Cross-Sectional Factory Integration
```python
def enhanced_cross_sectional_residual(symbols, features, target_returns, dsi_evidence):
    """
    Enhanced cross-sectional residual with DSI evidence
    """
    # Standard residual calculation
    base_residual = cross_sectional_residual_factory(symbols, features, target_returns)
    
    # DSI evidence weighting
    if dsi_evidence['mx_confirm']:
        evidence_weight = 1 + dsi_evidence['mx_evidence']
        base_residual['z_residual'] *= evidence_weight
        base_residual['prediction_std'] /= evidence_weight
    
    return base_residual
```

#### Kalman Factory Integration
```python
def enhanced_kalman_residual(state_data, observation_data, dsi_evidence):
    """
    Enhanced Kalman residual with DSI evidence
    """
    # Standard Kalman filtering
    base_residual = kalman_residual_factory(state_data, observation_data)
    
    # DSI evidence integration
    if dsi_evidence['mx_confirm']:
        # Adjust innovation covariance based on evidence
        innovation_cov = base_residual['innovation_cov'] / (1 + dsi_evidence['mx_evidence'])
        base_residual['innovation_cov'] = innovation_cov
    
    return base_residual
```

### 3. **Detector Specification Enhancement**

#### Enhanced Detector Inputs
```python
class EnhancedDetectorSpec:
    def __init__(self, base_spec):
        self.base_spec = base_spec
        self.dsi_inputs = {
            'mx_evidence': 'Continuous evidence score [0,1]',
            'mx_confirm': 'Binary confirmation flag',
            'expert_contributions': 'Individual expert outputs'
        }
    
    def check_trigger(self, snapshot, dsi_evidence):
        # Standard trigger logic
        base_trigger = self.base_spec.check_trigger(snapshot)
        
        # DSI evidence integration
        if dsi_evidence['mx_confirm']:
            evidence_boost = 1 + dsi_evidence['mx_evidence'] * 0.2  # Max 20% boost
            base_trigger['severity'] *= evidence_boost
        
        return base_trigger
```

### 4. **Curator Layer Integration**

#### DSI Curator
```python
class DSICurator:
    """
    Curator specifically for DSI evidence quality
    """
    def __init__(self):
        self.mandate = "DSI evidence quality and expert performance"
        self.veto_threshold = 0.3  # Evidence quality threshold
    
    def evaluate_detector(self, detector_id, dsi_evidence):
        """
        Evaluate detector based on DSI evidence quality
        """
        evidence_quality = self.assess_evidence_quality(dsi_evidence)
        
        if evidence_quality < self.veto_threshold:
            return {
                'action': 'veto',
                'reason': 'Poor DSI evidence quality',
                'evidence': evidence_quality
            }
        elif evidence_quality > 0.8:
            return {
                'action': 'nudge',
                'contribution': 0.05,  # Small positive nudge
                'reason': 'High DSI evidence quality'
            }
        else:
            return {'action': 'approve'}
```

## Database Schema Extensions

### DSI Expert Registry
```sql
CREATE TABLE dsi_experts (
    expert_id TEXT PRIMARY KEY,
    expert_type TEXT NOT NULL,  -- 'fsm', 'classifier', 'anomaly', 'divergence'
    spec JSONB NOT NULL,        -- Expert specification
    version TEXT NOT NULL,
    latency_p50 REAL,           -- 50th percentile latency
    auc_oos REAL,               -- Out-of-sample AUC
    contrib_det_sigma REAL,     -- Contribution to det_sigma
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### DSI Annotations
```sql
CREATE TABLE dsi_annotations (
    id UUID PRIMARY KEY,
    asset_uid INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    mx_evidence REAL NOT NULL,      -- Fused evidence score
    mx_confirm BOOLEAN NOT NULL,    -- Binary confirmation
    expert_contributions JSONB,     -- Individual expert outputs
    microtape_hash TEXT,           -- Hash of input MicroTape
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dsi_annotations_asset_time ON dsi_annotations(asset_uid, timestamp);
CREATE INDEX idx_dsi_annotations_evidence ON dsi_annotations(mx_evidence);
```

### Enhanced Detector Metrics
```sql
-- Add DSI columns to existing detector_metrics_daily table
ALTER TABLE detector_metrics_daily ADD COLUMN mx_evidence_avg REAL;
ALTER TABLE detector_metrics_daily ADD COLUMN mx_confirm_rate REAL;
ALTER TABLE detector_metrics_daily ADD COLUMN dsi_contribution REAL;
```

## Implementation Phases

### Phase 1: MicroTape + FSM Experts (Weeks 1-4)
**Goals**:
- Implement MicroTape tokenization system
- Deploy 5 FSM experts for basic patterns
- Measure latency and accuracy

**Deliverables**:
- MicroTape tokenization pipeline
- FSM expert framework
- Basic pattern detection (wick patterns, order book depletion)
- Latency measurement < 5ms

### Phase 2: Tiny Models + Anomaly Detection (Weeks 5-8)
**Goals**:
- Deploy 1-3B quantized models
- Implement anomaly scorers
- Add divergence verifiers

**Deliverables**:
- Quantized model deployment
- Anomaly detection pipeline
- Divergence verification system
- Expert weight learning

### Phase 3: Evidence Fusion + Integration (Weeks 9-12)
**Goals**:
- Implement Bayesian fusion
- Integrate with kernel resonance
- Update detector specifications

**Deliverables**:
- Evidence fusion system
- Kernel resonance enhancement
- Enhanced detector specs
- Performance validation

### Phase 4: Curator Integration + Optimization (Weeks 13-16)
**Goals**:
- Add DSI curator
- Optimize expert weights
- Full system integration

**Deliverables**:
- DSI curator implementation
- Weight optimization system
- End-to-end integration
- Performance monitoring

## Performance Metrics

### Latency Targets
- **MicroTape processing**: < 2ms
- **Expert evaluation**: < 5ms per expert
- **Evidence fusion**: < 1ms
- **Total DSI latency**: < 10ms

### Quality Metrics
- **Evidence accuracy**: > 70% correlation with detector performance
- **Expert survival rate**: > 60% of experts contribute positively
- **False positive rate**: < 10% for mx_confirm
- **Detector improvement**: > 15% improvement in det_sigma

### Monitoring
- **Expert performance**: Track individual expert contributions
- **Evidence quality**: Monitor mx_evidence distribution
- **Integration impact**: Measure det_sigma improvement
- **System health**: Latency, accuracy, and stability metrics

## Configuration Management

### DSI Configuration
```yaml
dsi:
  microtape:
    window_size: 256
    processing_cadence_ms: 100
    compression_ratio: 0.8
  
  experts:
    fsm_experts: 5
    classifier_experts: 3
    anomaly_experts: 2
    divergence_experts: 2
  
  fusion:
    confirmation_threshold: 0.6
    weight_learning_window: 30
    max_boost_factor: 0.2
  
  integration:
    kr_delta_phi_boost: true
    kr_theta_penalty_relief: true
    beta_mx: 0.1
    gamma_mx: 0.05
```

## Future Enhancements

### 1. **Advanced Expert Types**
- **Reinforcement Learning Experts**: Learn optimal trading actions
- **Ensemble Experts**: Combine multiple model types
- **Regime-Specific Experts**: Specialized for different market conditions

### 2. **Cross-Asset Intelligence**
- **Cross-Asset DSI**: Evidence sharing across related assets
- **Market-Wide Patterns**: System-wide microstructure analysis
- **Correlation Intelligence**: Cross-asset pattern detection

### 3. **Temporal Intelligence**
- **Multi-Scale Analysis**: Different timeframes for different patterns
- **Temporal Embeddings**: Time-aware pattern representation
- **Seasonal Intelligence**: Time-of-day and seasonal patterns

### 4. **Adaptive Learning**
- **Online Learning**: Continuous expert weight updates
- **Meta-Learning**: Learning to learn new patterns
- **Transfer Learning**: Knowledge transfer across assets

## Conclusion

The LLM Coprocessor Integration represents a fundamental enhancement to the Alpha Detector system, introducing **Module-Level Intelligence** that transforms each module into a self-contained, self-learning intelligence unit. This integration:

1. **Module-Level Intelligence**: Each module has its own curator layer and intelligence capabilities
2. **Complete Trading Plan Generation**: Alpha Detector generates full trading plans, not just signals
3. **Self-Learning and Self-Correcting**: Each module continuously improves itself based on performance
4. **Deep Signal Intelligence**: Microstructure-level intelligence for signal vs noise separation
5. **Preserves Jim Simmons Principles**: Many small, orthogonal experts with evidence-based selection

### Key Architectural Changes

#### 1. **Curator as Intelligence Level**
- Each module has specialized curators for its domain
- Curators provide bounded influence and veto capabilities
- Module-level intelligence enables independent operation

#### 2. **Complete Trading Plan Generation**
- Alpha Detector generates full trading plans with entry/exit conditions
- Decision Maker provides only yes/no approval or plan modifications
- Trading intelligence lives within the signal module

#### 3. **Self-Learning at Module Level**
- Each module learns from its own performance
- Continuous parameter optimization and adaptation
- Module-specific pattern recognition and improvement

The integration weaves intelligence throughout the existing architecture while maintaining the core principles that make the system reliable, auditable, and effective. It addresses the critical gaps in module-level intelligence, complete trading plan generation, and self-learning capabilities while preserving the evolutionary, evidence-based approach that makes the system successful.

This approach creates a truly **organic intelligence system** where each module is a self-contained "garden" that can be easily replicated, knows how to communicate, but is unique to its creator, and continuously improves itself through learning and adaptation.

---

*This specification provides a comprehensive integration plan for the LLM Coprocessor system with the existing Alpha Detector architecture, ensuring seamless enhancement while maintaining system integrity and performance.*
