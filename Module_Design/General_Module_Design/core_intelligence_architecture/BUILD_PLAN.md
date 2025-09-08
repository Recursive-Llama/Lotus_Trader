# Core Intelligence Architecture - Build Plan

*Comprehensive implementation guide for the organic intelligence system foundation*

## Executive Summary

This build plan implements the foundational intelligence architecture where each module becomes a self-contained intelligence unit with its own curator layer, complete trading plan generation, and self-learning capabilities. The architecture ensures mathematical integrity while enabling organic growth and adaptation.

## Phase 1: Foundation Architecture (Weeks 1-4)

### 1.1 Curator Framework Implementation

#### Core Curator Class
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import logging

class CuratorAction(Enum):
    VETO = "veto"
    NUDGE = "nudge" 
    APPROVE = "approve"

@dataclass
class CuratorContribution:
    curator_type: str
    action: CuratorAction
    contribution: float  # c_{j,i} ∈ [-κ_j, +κ_j]
    reason: str
    evidence: Dict
    confidence: float
    timestamp: float

class BaseCurator(ABC):
    """Base class for all module-specific curators"""
    
    def __init__(self, 
                 curator_type: str,
                 kappa: float = 0.15,  # Bounded influence cap
                 veto_threshold: float = 0.8):
        self.curator_type = curator_type
        self.kappa = kappa
        self.veto_threshold = veto_threshold
        self.logger = logging.getLogger(f"curator.{curator_type}")
        
    @abstractmethod
    def evaluate(self, 
                 detector_sigma: float,
                 context: Dict) -> CuratorContribution:
        """Evaluate and return curator contribution"""
        pass
        
    def _apply_bounds(self, raw_contribution: float) -> float:
        """Apply bounded influence: c_{j,i} ∈ [-κ_j, +κ_j]"""
        return np.clip(raw_contribution, -self.kappa, self.kappa)
        
    def _should_veto(self, confidence: float) -> bool:
        """Determine if curator should veto based on confidence"""
        return confidence < self.veto_threshold
```

#### Curator Registry
```python
class CuratorRegistry:
    """Manages all curators for a module"""
    
    def __init__(self, module_type: str):
        self.module_type = module_type
        self.curators: Dict[str, BaseCurator] = {}
        self.curator_weights: Dict[str, float] = {}
        
    def register_curator(self, curator: BaseCurator, weight: float = 1.0):
        """Register a curator with its influence weight"""
        self.curators[curator.curator_type] = curator
        self.curator_weights[curator.curator_type] = weight
        
    def evaluate_all(self, 
                    detector_sigma: float,
                    context: Dict) -> List[CuratorContribution]:
        """Evaluate all curators and return contributions"""
        contributions = []
        
        for curator_type, curator in self.curators.items():
            try:
                contribution = curator.evaluate(detector_sigma, context)
                contributions.append(contribution)
            except Exception as e:
                self.logger.error(f"Curator {curator_type} failed: {e}")
                
        return contributions
        
    def compute_curated_score(self, 
                            detector_sigma: float,
                            contributions: List[CuratorContribution]) -> Tuple[float, bool]:
        """Compute final curated score with bounded influence"""
        
        # Check for hard vetos
        vetos = [c for c in contributions if c.action == CuratorAction.VETO]
        if vetos:
            return detector_sigma, False
            
        # Apply soft nudges in log-space
        log_det_sigma = np.log(detector_sigma)
        soft_contributions = [c for c in contributions if c.action == CuratorAction.NUDGE]
        
        total_nudge = sum(c.contribution for c in soft_contributions)
        curated_log_sigma = log_det_sigma + total_nudge
        
        return np.exp(curated_log_sigma), True
```

### 1.2 Module-Specific Curator Implementations

#### Alpha Detector Curators
```python
class DSICurator(BaseCurator):
    """Deep Signal Intelligence curator for microstructure evidence"""
    
    def __init__(self):
        super().__init__("dsi", kappa=0.12)
        
    def evaluate(self, detector_sigma: float, context: Dict) -> CuratorContribution:
        # Extract DSI evidence from context
        mx_evidence = context.get('mx_evidence', 0.0)
        mx_confirm = context.get('mx_confirm', 0.0)
        expert_performance = context.get('expert_performance', {})
        
        # Compute DSI quality score
        dsi_quality = self._compute_dsi_quality(mx_evidence, mx_confirm, expert_performance)
        
        # Determine action
        if dsi_quality < 0.3:
            action = CuratorAction.VETO
            contribution = 0.0
        elif dsi_quality > 0.7:
            action = CuratorAction.APPROVE
            contribution = 0.0
        else:
            action = CuratorAction.NUDGE
            contribution = self._apply_bounds((dsi_quality - 0.5) * 0.2)
            
        return CuratorContribution(
            curator_type=self.curator_type,
            action=action,
            contribution=contribution,
            reason=f"DSI quality: {dsi_quality:.3f}",
            evidence={"dsi_quality": dsi_quality, "mx_evidence": mx_evidence},
            confidence=dsi_quality,
            timestamp=time.time()
        )
        
    def _compute_dsi_quality(self, mx_evidence: float, mx_confirm: float, 
                           expert_performance: Dict) -> float:
        """Compute DSI quality score from 0-1"""
        # Weighted combination of evidence strength and expert performance
        evidence_strength = (mx_evidence + mx_confirm) / 2.0
        
        # Expert performance factor
        expert_factor = np.mean(list(expert_performance.values())) if expert_performance else 0.5
        
        # Combined quality score
        return 0.6 * evidence_strength + 0.4 * expert_factor

class PatternCurator(BaseCurator):
    """Pattern recognition curator for candlestick and chart patterns"""
    
    def __init__(self):
        super().__init__("pattern", kappa=0.10)
        
    def evaluate(self, detector_sigma: float, context: Dict) -> CuratorContribution:
        patterns = context.get('patterns', {})
        pattern_confidence = context.get('pattern_confidence', 0.0)
        
        # Evaluate pattern quality
        pattern_quality = self._evaluate_patterns(patterns, pattern_confidence)
        
        if pattern_quality < 0.4:
            action = CuratorAction.VETO
            contribution = 0.0
        elif pattern_quality > 0.8:
            action = CuratorAction.APPROVE
            contribution = 0.0
        else:
            action = CuratorAction.NUDGE
            contribution = self._apply_bounds((pattern_quality - 0.6) * 0.15)
            
        return CuratorContribution(
            curator_type=self.curator_type,
            action=action,
            contribution=contribution,
            reason=f"Pattern quality: {pattern_quality:.3f}",
            evidence={"patterns": patterns, "quality": pattern_quality},
            confidence=pattern_quality,
            timestamp=time.time()
        )
        
    def _evaluate_patterns(self, patterns: Dict, confidence: float) -> float:
        """Evaluate pattern recognition quality"""
        if not patterns:
            return 0.0
            
        # Weight patterns by their historical accuracy
        pattern_weights = {
            'doji': 0.8, 'hammer': 0.7, 'shooting_star': 0.6,
            'engulfing': 0.9, 'harami': 0.5, 'morning_star': 0.8
        }
        
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for pattern, detected in patterns.items():
            if detected and pattern in pattern_weights:
                weight = pattern_weights[pattern]
                total_weight += weight
                weighted_confidence += weight * confidence
                
        return weighted_confidence / total_weight if total_weight > 0 else 0.0

class RegimeCurator(BaseCurator):
    """Market regime curator for timing and context"""
    
    def __init__(self):
        super().__init__("regime", kappa=0.08)
        
    def evaluate(self, detector_sigma: float, context: Dict) -> CuratorContribution:
        regime = context.get('regime', 'unknown')
        regime_confidence = context.get('regime_confidence', 0.0)
        volatility = context.get('volatility', 0.0)
        
        # Evaluate regime alignment
        regime_quality = self._evaluate_regime(regime, regime_confidence, volatility)
        
        if regime_quality < 0.3:
            action = CuratorAction.VETO
            contribution = 0.0
        elif regime_quality > 0.8:
            action = CuratorAction.APPROVE
            contribution = 0.0
        else:
            action = CuratorAction.NUDGE
            contribution = self._apply_bounds((regime_quality - 0.5) * 0.1)
            
        return CuratorContribution(
            curator_type=self.curator_type,
            action=action,
            contribution=contribution,
            reason=f"Regime quality: {regime_quality:.3f}",
            evidence={"regime": regime, "confidence": regime_confidence},
            confidence=regime_quality,
            timestamp=time.time()
        )
        
    def _evaluate_regime(self, regime: str, confidence: float, volatility: float) -> float:
        """Evaluate regime alignment quality"""
        # Regime-specific quality factors
        regime_quality_map = {
            'trending': 0.8 if volatility > 0.02 else 0.4,
            'ranging': 0.6 if volatility < 0.02 else 0.3,
            'volatile': 0.7 if volatility > 0.05 else 0.2,
            'calm': 0.5 if volatility < 0.01 else 0.3,
            'unknown': 0.1
        }
        
        base_quality = regime_quality_map.get(regime, 0.1)
        confidence_factor = confidence
        
        return base_quality * confidence_factor
```

#### Decision Maker Curators
```python
class RiskCurator(BaseCurator):
    """Risk management curator for portfolio risk assessment"""
    
    def __init__(self):
        super().__init__("risk", kappa=0.15)
        
    def evaluate(self, detector_sigma: float, context: Dict) -> CuratorContribution:
        portfolio_risk = context.get('portfolio_risk', 0.0)
        position_size = context.get('position_size', 0.0)
        max_risk = context.get('max_risk', 0.01)  # 1% max risk
        
        # Compute risk quality
        risk_quality = self._evaluate_risk(portfolio_risk, position_size, max_risk)
        
        if risk_quality < 0.2:
            action = CuratorAction.VETO
            contribution = 0.0
        elif risk_quality > 0.8:
            action = CuratorAction.APPROVE
            contribution = 0.0
        else:
            action = CuratorAction.NUDGE
            contribution = self._apply_bounds((risk_quality - 0.5) * 0.2)
            
        return CuratorContribution(
            curator_type=self.curator_type,
            action=action,
            contribution=contribution,
            reason=f"Risk quality: {risk_quality:.3f}",
            evidence={"portfolio_risk": portfolio_risk, "position_size": position_size},
            confidence=risk_quality,
            timestamp=time.time()
        )
        
    def _evaluate_risk(self, portfolio_risk: float, position_size: float, max_risk: float) -> float:
        """Evaluate risk management quality"""
        # Risk should be within bounds
        if portfolio_risk + position_size > max_risk:
            return 0.0
            
        # Prefer lower risk for higher quality
        risk_ratio = (portfolio_risk + position_size) / max_risk
        return 1.0 - (risk_ratio ** 2)  # Quadratic penalty for high risk
```

### 1.3 Database Schema Implementation

#### Curator Actions Table
```sql
-- Curator actions tracking
CREATE TABLE curator_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detector_id UUID REFERENCES detector_registry(id),
    module_type TEXT NOT NULL,  -- 'alpha_detector', 'decision_maker', 'trader'
    curator_type TEXT NOT NULL,  -- 'dsi', 'pattern', 'divergence', etc.
    action_type TEXT NOT NULL CHECK (action_type IN ('veto', 'nudge', 'approve')),
    contribution FLOAT8,         -- c_{j,i} for nudges
    reason TEXT,
    evidence JSONB,             -- Supporting data
    confidence FLOAT8,          -- Curator confidence 0-1
    created_at TIMESTAMP DEFAULT NOW(),
    curator_version TEXT,       -- For audit trail
    INDEX idx_curator_actions_detector (detector_id),
    INDEX idx_curator_actions_module (module_type),
    INDEX idx_curator_actions_curator (curator_type),
    INDEX idx_curator_actions_created (created_at)
);

-- Curator performance tracking
CREATE TABLE curator_kpis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_type TEXT NOT NULL,
    curator_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value FLOAT8,
    measurement_window_start TIMESTAMP,
    measurement_window_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_curator_kpis_module (module_type),
    INDEX idx_curator_kpis_curator (curator_type),
    INDEX idx_curator_kpis_metric (metric_name)
);

-- Curator configuration
CREATE TABLE curator_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_type TEXT NOT NULL,
    curator_type TEXT NOT NULL,
    kappa FLOAT8 NOT NULL,      -- Bounded influence cap
    veto_threshold FLOAT8 NOT NULL,
    weight FLOAT8 DEFAULT 1.0,  -- Curator weight
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(module_type, curator_type)
);
```

### 1.4 Curator Orchestration System

```python
class CuratorOrchestrator:
    """Orchestrates all curators for a module"""
    
    def __init__(self, module_type: str):
        self.module_type = module_type
        self.registry = CuratorRegistry(module_type)
        self.db_client = DatabaseClient()
        self.logger = logging.getLogger(f"curator_orchestrator.{module_type}")
        
    def setup_curators(self):
        """Initialize all curators for this module"""
        if self.module_type == "alpha_detector":
            self._setup_alpha_detector_curators()
        elif self.module_type == "decision_maker":
            self._setup_decision_maker_curators()
        elif self.module_type == "trader":
            self._setup_trader_curators()
            
    def _setup_alpha_detector_curators(self):
        """Setup Alpha Detector curators"""
        curators = [
            DSICurator(),
            PatternCurator(),
            RegimeCurator(),
            # Add other curators...
        ]
        
        for curator in curators:
            self.registry.register_curator(curator)
            
    def curate_signal(self, 
                     detector_sigma: float,
                     context: Dict) -> Tuple[float, bool, List[CuratorContribution]]:
        """Apply curator layer to detector signal"""
        
        # Get all curator contributions
        contributions = self.registry.evaluate_all(detector_sigma, context)
        
        # Compute curated score
        curated_sigma, approved = self.registry.compute_curated_score(
            detector_sigma, contributions
        )
        
        # Log curator actions
        self._log_curator_actions(contributions)
        
        return curated_sigma, approved, contributions
        
    def _log_curator_actions(self, contributions: List[CuratorContribution]):
        """Log all curator actions to database"""
        for contribution in contributions:
            self.db_client.insert_curator_action(
                detector_id=contribution.evidence.get('detector_id'),
                module_type=self.module_type,
                curator_type=contribution.curator_type,
                action_type=contribution.action.value,
                contribution=contribution.contribution,
                reason=contribution.reason,
                evidence=contribution.evidence,
                confidence=contribution.confidence,
                curator_version="1.0"
            )
```

## Phase 2: Module Integration (Weeks 5-8)

### 2.1 Alpha Detector Integration

```python
class EnhancedAlphaDetector:
    """Alpha Detector with integrated curator layer"""
    
    def __init__(self):
        self.curator_orchestrator = CuratorOrchestrator("alpha_detector")
        self.curator_orchestrator.setup_curators()
        # ... existing detector components
        
    def process_signal(self, market_data: Dict) -> Optional[TradingPlan]:
        """Process market data through enhanced detector with curators"""
        
        # 1. Compute base detector signal
        detector_sigma = self._compute_detector_sigma(market_data)
        
        # 2. Prepare context for curators
        context = self._prepare_curator_context(market_data, detector_sigma)
        
        # 3. Apply curator layer
        curated_sigma, approved, contributions = self.curator_orchestrator.curate_signal(
            detector_sigma, context
        )
        
        # 4. Generate trading plan if approved
        if approved and curated_sigma >= self.publish_threshold:
            return self._generate_trading_plan(market_data, curated_sigma, context)
            
        return None
        
    def _prepare_curator_context(self, market_data: Dict, detector_sigma: float) -> Dict:
        """Prepare context data for curators"""
        return {
            'detector_sigma': detector_sigma,
            'mx_evidence': market_data.get('mx_evidence', 0.0),
            'mx_confirm': market_data.get('mx_confirm', 0.0),
            'patterns': market_data.get('patterns', {}),
            'regime': market_data.get('regime', 'unknown'),
            'volatility': market_data.get('volatility', 0.0),
            'expert_performance': market_data.get('expert_performance', {}),
            # ... other context data
        }
```

### 2.2 Decision Maker Integration

```python
class EnhancedDecisionMaker:
    """Decision Maker with integrated curator layer"""
    
    def __init__(self):
        self.curator_orchestrator = CuratorOrchestrator("decision_maker")
        self.curator_orchestrator.setup_curators()
        # ... existing decision maker components
        
    def evaluate_trading_plan(self, trading_plan: TradingPlan) -> DecisionResult:
        """Evaluate trading plan with curator layer"""
        
        # Prepare context for curators
        context = self._prepare_decision_context(trading_plan)
        
        # Apply curator layer
        curated_score, approved, contributions = self.curator_orchestrator.curate_signal(
            trading_plan.signal_strength, context
        )
        
        if approved:
            return DecisionResult(
                approved=True,
                modified_plan=self._apply_curator_modifications(trading_plan, contributions),
                curator_feedback=contributions
            )
        else:
            return DecisionResult(
                approved=False,
                rejection_reasons=[c.reason for c in contributions if c.action == CuratorAction.VETO],
                curator_feedback=contributions
            )
```

## Phase 3: Testing & Validation (Weeks 9-12)

### 3.1 Curator Performance Testing

```python
class CuratorPerformanceTester:
    """Test and validate curator performance"""
    
    def __init__(self):
        self.test_cases = self._load_test_cases()
        
    def test_curator_bounds(self):
        """Test that curator contributions respect bounds"""
        for curator_type in ['dsi', 'pattern', 'regime']:
            curator = self._create_curator(curator_type)
            
            # Test extreme inputs
            extreme_contexts = self._generate_extreme_contexts()
            
            for context in extreme_contexts:
                contribution = curator.evaluate(1.0, context)
                assert abs(contribution.contribution) <= curator.kappa
                
    def test_curator_consistency(self):
        """Test curator consistency across similar inputs"""
        # Test that similar inputs produce similar outputs
        pass
        
    def test_curator_performance(self):
        """Test curator performance against ground truth"""
        # Test against historical data with known outcomes
        pass
```

### 3.2 Integration Testing

```python
class IntegrationTester:
    """Test full system integration"""
    
    def test_end_to_end_flow(self):
        """Test complete signal flow through all modules"""
        # 1. Generate test market data
        market_data = self._generate_test_market_data()
        
        # 2. Process through Alpha Detector
        trading_plan = self.alpha_detector.process_signal(market_data)
        
        # 3. Evaluate through Decision Maker
        if trading_plan:
            decision = self.decision_maker.evaluate_trading_plan(trading_plan)
            
            # 4. Execute through Trader
            if decision.approved:
                execution_result = self.trader.execute_plan(decision.modified_plan)
                
        # 5. Verify all curator actions were logged
        self._verify_curator_logging()
```

## Phase 4: Production Deployment (Weeks 13-16)

### 4.1 Monitoring & Alerting

```python
class CuratorMonitor:
    """Monitor curator performance and health"""
    
    def __init__(self):
        self.alert_thresholds = {
            'veto_rate': 0.3,      # Alert if >30% veto rate
            'nudge_magnitude': 0.1, # Alert if nudges too large
            'response_time': 1.0,   # Alert if >1s response time
        }
        
    def check_curator_health(self):
        """Check health of all curators"""
        for module_type in ['alpha_detector', 'decision_maker', 'trader']:
            for curator_type in self._get_curator_types(module_type):
                self._check_curator_health(module_type, curator_type)
                
    def _check_curator_health(self, module_type: str, curator_type: str):
        """Check health of specific curator"""
        # Check veto rate
        veto_rate = self._get_veto_rate(module_type, curator_type)
        if veto_rate > self.alert_thresholds['veto_rate']:
            self._send_alert(f"High veto rate for {curator_type}: {veto_rate}")
            
        # Check response time
        avg_response_time = self._get_avg_response_time(module_type, curator_type)
        if avg_response_time > self.alert_thresholds['response_time']:
            self._send_alert(f"Slow response time for {curator_type}: {avg_response_time}")
```

### 4.2 Performance Optimization

```python
class CuratorOptimizer:
    """Optimize curator performance"""
    
    def optimize_curator_weights(self):
        """Optimize curator weights based on performance"""
        # Use historical performance to adjust curator weights
        pass
        
    def calibrate_curator_thresholds(self):
        """Calibrate curator thresholds based on market conditions"""
        # Adjust thresholds based on market volatility and regime
        pass
```

## Mathematical Foundations

### Bounded Influence Mathematics

The curator system is mathematically grounded in bounded influence theory:

1. **Curator Contributions**: `c_{j,i} ∈ [-κ_j, +κ_j]` where `κ_j ≤ 0.15`
2. **Final Score**: `log Σ̃_i = log(det_sigma_i) + Σ_{j∈soft} c_{j,i}`
3. **Publication Decision**: Publish if no hard vetos AND `Σ̃_i ≥ τ_publish`

### Curator Quality Metrics

- **Accuracy**: `P(correct_prediction | curator_approval)`
- **Precision**: `P(profitable_signal | curator_approval)`
- **Recall**: `P(curator_approval | profitable_signal)`
- **F1 Score**: `2 * (precision * recall) / (precision + recall)`

## Configuration Management

### Curator Configuration Schema

```yaml
curators:
  alpha_detector:
    dsi:
      kappa: 0.12
      veto_threshold: 0.3
      weight: 1.0
    pattern:
      kappa: 0.10
      veto_threshold: 0.4
      weight: 0.8
    regime:
      kappa: 0.08
      veto_threshold: 0.3
      weight: 0.9
      
  decision_maker:
    risk:
      kappa: 0.15
      veto_threshold: 0.2
      weight: 1.0
    allocation:
      kappa: 0.10
      veto_threshold: 0.4
      weight: 0.7
      
  trader:
    execution:
      kappa: 0.08
      veto_threshold: 0.5
      weight: 0.9
```

## Success Metrics

### Phase 1 Success Criteria
- [ ] All curator classes implemented and tested
- [ ] Database schema deployed
- [ ] Basic curator orchestration working
- [ ] Unit tests passing with >90% coverage

### Phase 2 Success Criteria
- [ ] Alpha Detector integration complete
- [ ] Decision Maker integration complete
- [ ] Trader integration complete
- [ ] End-to-end signal flow working

### Phase 3 Success Criteria
- [ ] All integration tests passing
- [ ] Performance benchmarks met
- [ ] Curator accuracy >80%
- [ ] System latency <100ms

### Phase 4 Success Criteria
- [ ] Production deployment successful
- [ ] Monitoring and alerting working
- [ ] Curator performance optimized
- [ ] System stability >99.9%

---

*This build plan provides the complete foundation for implementing the Core Intelligence Architecture with detailed formulas, implementation phases, and success criteria.*
