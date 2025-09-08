# Decision Maker Module - Role Specification

*Crystal clear definition of what the Decision Maker Module receives, does, and reports*

## **CORE ROLE: GOVERNANCE & RISK MANAGEMENT MODULE**

The Decision Maker Module is **NOT** a plan generator - it's a **governance and risk management module** that evaluates, approves, modifies, or rejects complete trading plans from the Alpha Detector.

## **What the Decision Maker Module RECEIVES:**

### **Input: Complete Trading Plans (det-alpha-1.0 events)**
```python
# Schema for what Decision Maker receives from Alpha Detector
class CompleteTradingPlan:
    """Complete trading plan from Alpha Detector"""
    
    # Core plan data
    plan_id: str
    signal_id: str
    symbol: str
    
    # Trading parameters
    direction: str  # 'long', 'short', 'neutral'
    position_size: float  # % of portfolio
    entry_price: Optional[float]  # Target entry price
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # Entry/exit conditions
    entry_conditions: Dict[str, Any]  # Market conditions to trigger entry
    exit_conditions: Dict[str, Any]   # Market conditions to trigger exit
    
    # Risk management
    risk_reward_ratio: float
    confidence_score: float  # 0-1
    time_horizon: str  # "1m", "5m", "15m", "1h", "4h", "1d"
    
    # Intelligence validation
    microstructure_evidence: Optional[Dict[str, Any]] = None
    regime_context: Optional[Dict[str, Any]] = None
    module_intelligence: Optional[Dict[str, Any]] = None
    
    # Execution notes
    execution_notes: Optional[str] = None
    valid_until: datetime
```

## **What the Decision Maker Module DOES:**

### **1. Plan Validation**
```python
def validate_trading_plan(self, plan: CompleteTradingPlan) -> Dict:
    """Validate the trading plan structure and requirements"""
    validation_result = {
        'valid': True,
        'issues': [],
        'warnings': []
    }
    
    # Check required fields
    required_fields = ['plan_id', 'symbol', 'direction', 'position_size', 'entry_conditions']
    for field in required_fields:
        if field not in plan:
            validation_result['valid'] = False
            validation_result['issues'].append(f'Missing required field: {field}')
    
    # Check position size limits
    if plan.position_size > self.portfolio_manager.max_position_size:
        validation_result['valid'] = False
        validation_result['issues'].append(f'Position size {plan.position_size} exceeds limit')
    
    # Check symbol validity
    if not self._is_symbol_tradeable(plan.symbol):
        validation_result['valid'] = False
        validation_result['issues'].append(f'Symbol {plan.symbol} not tradeable')
    
    return validation_result
```

### **2. Risk Assessment**
```python
def assess_plan_risk(self, plan: CompleteTradingPlan) -> Dict:
    """Assess risk impact of trading plan on portfolio"""
    
    # Get current portfolio state
    current_portfolio = self.portfolio_manager.get_current_portfolio()
    
    # Calculate portfolio impact
    portfolio_impact = self._calculate_portfolio_impact(plan, current_portfolio)
    
    # Calculate VaR impact
    var_impact = self._calculate_var_impact(plan, current_portfolio)
    
    # Calculate correlation risk
    correlation_risk = self._calculate_correlation_risk(plan, current_portfolio)
    
    # Calculate concentration risk
    concentration_risk = self._calculate_concentration_risk(plan, current_portfolio)
    
    # Overall risk score
    risk_score = self._calculate_risk_score(var_impact, correlation_risk, concentration_risk)
    
    return {
        'overall_score': risk_score,
        'var_impact': var_impact,
        'correlation_risk': correlation_risk,
        'concentration_risk': concentration_risk,
        'portfolio_impact': portfolio_impact,
        'hard_veto': risk_score < 0.3,  # Hard veto if too risky
        'veto_reason': 'Risk limits exceeded' if risk_score < 0.3 else None
    }
```

### **3. Allocation Evaluation**
```python
def evaluate_allocation(self, plan: CompleteTradingPlan) -> Dict:
    """Evaluate allocation impact of trading plan"""
    
    # Get current allocation state
    current_allocation = self.allocation_engine.get_current_allocation()
    
    # Calculate new allocation with this trade
    new_allocation = self._simulate_allocation_with_trade(current_allocation, plan)
    
    # Check diversification constraints
    diversification_check = self._check_diversification_constraints(new_allocation)
    
    # Check concentration limits
    concentration_check = self._check_concentration_limits(new_allocation)
    
    # Check rebalancing costs
    rebalancing_cost = self._calculate_rebalancing_cost(current_allocation, new_allocation)
    
    # Overall allocation score
    allocation_score = self._calculate_allocation_score(
        diversification_check, concentration_check, rebalancing_cost
    )
    
    return {
        'overall_score': allocation_score,
        'diversification_check': diversification_check,
        'concentration_check': concentration_check,
        'rebalancing_cost': rebalancing_cost,
        'hard_veto': allocation_score < 0.3,  # Hard veto if allocation constraints violated
        'veto_reason': 'Allocation constraints violated' if allocation_score < 0.3 else None
    }
```

### **4. Crypto Asymmetry Analysis**
```python
def analyze_crypto_asymmetries(self, plan: CompleteTradingPlan, market_context: Dict) -> Dict:
    """Analyze crypto-specific structural asymmetries"""
    
    symbol = plan.symbol
    market_data = market_context.get('market_data', {})
    
    # Detect asymmetries
    asymmetries = self.crypto_asymmetry_engine.detect_asymmetries(symbol, market_data)
    
    # Calculate budget scaling
    base_budget = plan.position_size
    scaled_budget, scaling_factor = self._scale_budget_for_asymmetry(base_budget, asymmetries)
    
    # Determine if asymmetry is significant
    asymmetry_detected = asymmetries.get('combined_score', 0) > self.asymmetry_threshold
    
    return {
        'asymmetries': asymmetries,
        'base_budget': base_budget,
        'scaled_budget': scaled_budget,
        'scaling_factor': scaling_factor,
        'asymmetry_detected': asymmetry_detected,
        'combined_score': asymmetries.get('combined_score', 0)
    }
```

### **5. Curator Layer Evaluation**
```python
def evaluate_with_curators(self, plan: CompleteTradingPlan, risk_assessment: Dict, 
                          allocation_evaluation: Dict, asymmetry_analysis: Dict) -> Dict:
    """Evaluate plan through curator layer"""
    
    # Prepare context for curators
    curator_context = {
        'trading_plan': plan,
        'risk_assessment': risk_assessment,
        'allocation_evaluation': allocation_evaluation,
        'asymmetry_analysis': asymmetry_analysis,
        'portfolio_state': self.portfolio_manager.get_current_portfolio()
    }
    
    # Get curator evaluations
    curator_evaluations = {}
    total_weight = 0
    weighted_score = 0
    
    for curator_name, curator in self.curator_layer.curators.items():
        evaluation = curator.evaluate(plan, curator_context)
        weight = curator.weight
        
        curator_evaluations[curator_name] = {
            'score': evaluation['score'],
            'contribution': evaluation['score'] * weight,
            'reason': evaluation.get('reason', ''),
            'confidence': evaluation.get('confidence', 0.5)
        }
        
        weighted_score += evaluation['score'] * weight
        total_weight += weight
    
    # Calculate final curator score
    final_score = weighted_score / total_weight if total_weight > 0 else 0.5
    
    # Check for hard vetoes
    hard_vetoes = [name for name, eval in curator_evaluations.items() 
                   if eval.get('hard_veto', False)]
    
    return {
        'score': final_score,
        'curator_evaluations': curator_evaluations,
        'hard_vetoes': hard_vetoes,
        'overall_approved': len(hard_vetoes) == 0 and final_score >= 0.5
    }
```

### **6. Final Decision Making**
```python
def make_final_decision(self, plan: CompleteTradingPlan, risk_assessment: Dict,
                       allocation_evaluation: Dict, asymmetry_analysis: Dict,
                       curator_evaluation: Dict) -> Dict:
    """Make final decision based on all evaluations"""
    
    # Calculate decision score
    decision_score = self._calculate_decision_score(
        risk_assessment, allocation_evaluation, asymmetry_analysis, curator_evaluation
    )
    
    # Check for hard vetoes
    if risk_assessment.get('hard_veto', False):
        return self._create_rejection_decision('Risk hard veto', risk_assessment['veto_reason'])
    
    if allocation_evaluation.get('hard_veto', False):
        return self._create_rejection_decision('Allocation hard veto', allocation_evaluation['veto_reason'])
    
    if curator_evaluation.get('hard_vetoes'):
        return self._create_rejection_decision('Curator hard veto', f"Vetoes from: {', '.join(curator_evaluation['hard_vetoes'])}")
    
    # Determine decision based on score
    if decision_score >= 0.7:
        return self._create_approval_decision(plan, decision_score)
    elif decision_score >= 0.4:
        return self._create_modification_decision(plan, decision_score, risk_assessment, allocation_evaluation)
    else:
        return self._create_rejection_decision('Low confidence', f'Decision score {decision_score} below threshold')
    
def _create_approval_decision(self, plan: CompleteTradingPlan, score: float) -> Dict:
    """Create approval decision"""
    return {
        'decision_id': str(uuid.uuid4()),
        'plan_id': plan.plan_id,
        'decision_type': 'approve',
        'decision_score': score,
        'trading_plan': plan,
        'rejection_reasons': [],
        'modifications': [],
        'confidence': score,
        'created_at': datetime.now(timezone.utc),
        'valid_until': datetime.now(timezone.utc).timestamp() + 3600  # 1 hour
    }
    
def _create_modification_decision(self, plan: CompleteTradingPlan, score: float,
                                risk_assessment: Dict, allocation_evaluation: Dict) -> Dict:
    """Create modification decision"""
    modifications = self._suggest_modifications(plan, risk_assessment, allocation_evaluation)
    modified_plan = self._apply_modifications(plan, modifications)
    
    return {
        'decision_id': str(uuid.uuid4()),
        'plan_id': plan.plan_id,
        'decision_type': 'modify',
        'decision_score': score,
        'trading_plan': modified_plan,
        'rejection_reasons': [],
        'modifications': modifications,
        'confidence': score,
        'created_at': datetime.now(timezone.utc),
        'valid_until': datetime.now(timezone.utc).timestamp() + 3600  # 1 hour
    }
    
def _create_rejection_decision(self, reason: str, details: str) -> Dict:
    """Create rejection decision"""
    return {
        'decision_id': str(uuid.uuid4()),
        'plan_id': None,
        'decision_type': 'reject',
        'decision_score': 0.0,
        'trading_plan': None,
        'rejection_reasons': [{'reason': reason, 'details': details}],
        'modifications': [],
        'confidence': 0.0,
        'created_at': datetime.now(timezone.utc),
        'valid_until': datetime.now(timezone.utc).timestamp() + 3600  # 1 hour
    }
```

## **What the Decision Maker Module REPORTS BACK:**

### **Output: Decision Results (dm-decision-1.0 events)**
```python
# Schema for what Decision Maker reports back to other modules
class DecisionResult:
    """Decision result from Decision Maker"""
    
    # Core decision data
    decision_id: str
    plan_id: str
    decision_type: str  # 'approve', 'modify', 'reject'
    decision_score: float  # 0-1
    confidence: float  # 0-1
    
    # Decision details
    trading_plan: Optional[CompleteTradingPlan]  # Modified plan if approved/modified
    rejection_reasons: List[Dict[str, str]]  # Reasons if rejected
    modifications: List[Dict[str, Any]]  # Modifications if modified
    
    # Analysis results
    risk_assessment: Dict[str, Any]  # Risk analysis results
    allocation_evaluation: Dict[str, Any]  # Allocation analysis results
    asymmetry_analysis: Dict[str, Any]  # Crypto asymmetry analysis
    curator_decisions: Dict[str, Any]  # Curator evaluation results
    
    # Metadata
    created_at: datetime
    valid_until: datetime
    reported_to: List[str]  # Which modules received this decision
```

### **Reporting Process**
```python
def report_decision_result(self, decision_result: Dict):
    """Report decision result back to other modules"""
    
    # Send decision to Trader
    self.send_decision_to_trader(decision_result)
    
    # Send feedback to Alpha Detector
    self.send_feedback_to_alpha_detector(decision_result)
    
    # Send learning data to Learning Systems
    self.send_learning_data_to_learning_systems(decision_result)
    
    # Store for internal learning
    self.learning_system.record_decision(decision_result)

def send_decision_to_trader(self, decision_result: Dict):
    """Send decision to Trader Module for execution"""
    decision_message = {
        'event_type': 'dm-decision-1.0',
        'source_module': self.module_id,
        'target_modules': ['trader'],
        'payload': decision_result,
        'timestamp': datetime.now(timezone.utc).timestamp()
    }
    
    self.outbox.publish_message(decision_message)

def send_feedback_to_alpha_detector(self, decision_result: Dict):
    """Send decision feedback to Alpha Detector for learning"""
    feedback_message = {
        'event_type': 'dm-feedback-1.0',
        'source_module': self.module_id,
        'target_modules': ['alpha_detector'],
        'payload': {
            'decision_id': decision_result['decision_id'],
            'decision_type': decision_result['decision_type'],
            'decision_score': decision_result['decision_score'],
            'rejection_reasons': decision_result.get('rejection_reasons', []),
            'modifications': decision_result.get('modifications', []),
            'risk_insights': decision_result.get('risk_assessment', {}),
            'allocation_insights': decision_result.get('allocation_evaluation', {}),
            'learning_insights': self.learning_system.get_recent_insights()
        },
        'timestamp': datetime.now(timezone.utc).timestamp()
    }
    
    self.outbox.publish_message(feedback_message)
```

## **Key Points:**

1. **Decision Maker Module RECEIVES** complete trading plans from Alpha Detector
2. **Decision Maker Module EVALUATES** those plans using risk, allocation, and compliance criteria
3. **Decision Maker Module DECIDES** approve, modify, or reject based on evaluation
4. **Decision Maker Module REPORTS** decision results back to Trader and Alpha Detector
5. **Decision Maker Module LEARNS** from decision outcomes to improve future decisions

The Decision Maker Module is the **governance and risk management engine** of the system - it takes complete trading plans and decides whether they should be executed, modified, or rejected based on portfolio risk, allocation constraints, and compliance requirements.
