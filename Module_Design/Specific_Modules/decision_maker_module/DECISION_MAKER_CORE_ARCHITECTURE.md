# Decision Maker Module - Core Architecture

*Mathematical foundations and core implementation for the Decision Maker Module*

## Executive Summary

This document provides the mathematical foundations and core architecture for the Decision Maker Module, incorporating the sophisticated mathematical formulas from the existing system while building a comprehensive decision-making engine. The Decision Maker Module functions as a self-contained "garden" that evaluates, approves, modifies, or rejects complete trading plans from the Alpha Detector.

## Core Philosophy

The Decision Maker Module is **NOT** a plan generator - it's a **governance and risk management module** that:

- **Receives complete trading plans** from Alpha Detector
- **Evaluates plans** using portfolio risk, allocation, and compliance criteria
- **Approves, modifies, or rejects** plans based on curator evaluation
- **Manages portfolio-level risk** and position sizing
- **Provides governance oversight** without generating trading intelligence

## Mathematical Foundations

### 1. Portfolio Risk Mathematics

#### **Value at Risk (VaR) Calculation**
```python
def calculate_var(portfolio_returns, confidence_level=0.95):
    """Calculate Value at Risk using historical simulation"""
    # Sort returns in ascending order
    sorted_returns = np.sort(portfolio_returns)
    
    # Calculate VaR as percentile
    var_index = int((1 - confidence_level) * len(sorted_returns))
    var = -sorted_returns[var_index]
    
    return var

def calculate_conditional_var(portfolio_returns, var):
    """Calculate Conditional VaR (Expected Shortfall)"""
    # Returns worse than VaR
    tail_returns = portfolio_returns[portfolio_returns <= -var]
    
    if len(tail_returns) == 0:
        return var
    
    # Average of tail returns
    cvar = -np.mean(tail_returns)
    return cvar
```

#### **Portfolio Risk Metrics**
```python
def calculate_portfolio_risk_metrics(positions, market_data, risk_free_rate=0.02):
    """Calculate comprehensive portfolio risk metrics"""
    
    # Portfolio value and weights
    portfolio_value = sum(pos['quantity'] * pos['current_price'] for pos in positions)
    weights = np.array([pos['quantity'] * pos['current_price'] / portfolio_value for pos in positions])
    
    # Expected returns and covariance matrix
    expected_returns = np.array([pos['expected_return'] for pos in positions])
    cov_matrix = market_data['covariance_matrix']
    
    # Portfolio expected return
    portfolio_return = np.dot(weights, expected_returns)
    
    # Portfolio variance
    portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
    portfolio_volatility = np.sqrt(portfolio_variance)
    
    # Sharpe ratio
    excess_return = portfolio_return - risk_free_rate
    sharpe_ratio = excess_return / portfolio_volatility if portfolio_volatility > 0 else 0
    
    # Maximum drawdown
    max_drawdown = calculate_max_drawdown(positions)
    
    # Concentration risk (Herfindahl index)
    concentration_risk = np.sum(weights ** 2)
    
    return {
        'portfolio_value': portfolio_value,
        'portfolio_return': portfolio_return,
        'portfolio_volatility': portfolio_volatility,
        'sharpe_ratio': sharpe_ratio,
        'var_95': calculate_var(portfolio_returns, 0.95),
        'cvar_95': calculate_conditional_var(portfolio_returns, var_95),
        'max_drawdown': max_drawdown,
        'concentration_risk': concentration_risk
    }
```

### 2. Allocation Mathematics

#### **Mean-Variance Optimization**
```python
def mean_variance_optimization(expected_returns, cov_matrix, risk_aversion=1.0):
    """Mean-variance portfolio optimization"""
    
    n_assets = len(expected_returns)
    
    # Objective: maximize (expected_return - risk_aversion * variance)
    # Subject to: sum(weights) = 1, weights >= 0
    
    # Quadratic programming formulation
    # min: 0.5 * w^T * Q * w - c^T * w
    # where Q = risk_aversion * cov_matrix, c = expected_returns
    
    Q = risk_aversion * cov_matrix
    c = expected_returns
    
    # Constraints: sum(weights) = 1
    A_eq = np.ones((1, n_assets))
    b_eq = np.array([1.0])
    
    # Bounds: 0 <= weights <= 1
    bounds = [(0, 1) for _ in range(n_assets)]
    
    # Solve quadratic program
    from scipy.optimize import minimize
    
    def objective(weights):
        return 0.5 * np.dot(weights, np.dot(Q, weights)) - np.dot(c, weights)
    
    result = minimize(
        objective, 
        x0=np.ones(n_assets) / n_assets,
        method='SLSQP',
        bounds=bounds,
        constraints={'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
    )
    
    return result.x if result.success else None

def calculate_allocation_score(proposed_weights, optimal_weights, current_weights):
    """Calculate how well proposed allocation matches optimal allocation"""
    
    # Distance from optimal allocation
    optimal_distance = np.linalg.norm(proposed_weights - optimal_weights)
    
    # Distance from current allocation (turnover cost)
    turnover_distance = np.linalg.norm(proposed_weights - current_weights)
    
    # Combined score (lower is better)
    allocation_score = optimal_distance + 0.1 * turnover_distance
    
    return allocation_score
```

### 3. Crypto Asymmetry Mathematics

#### **Crypto Asymmetry Detection**
```python
def calculate_crypto_asymmetries(market_data, symbol):
    """Calculate crypto-specific structural asymmetries"""
    
    asymmetries = {}
    
    # Open Interest Squeeze (Z_OI)
    oi_data = market_data.get('open_interest', {})
    if oi_data:
        oi_change = oi_data.get('change_24h', 0)
        oi_volatility = oi_data.get('volatility', 0.02)
        z_oi = oi_change / (oi_volatility * np.sqrt(24))  # 24-hour normalization
        asymmetries['oi_squeeze'] = z_oi
    
    # Funding Imbalance (Z_F)
    funding_data = market_data.get('funding_rates', {})
    if funding_data:
        funding_rate = funding_data.get('current', 0)
        funding_volatility = funding_data.get('volatility', 0.001)
        z_f = funding_rate / funding_volatility
        asymmetries['funding_imbalance'] = z_f
    
    # Basis Stress (Z_B)
    basis_data = market_data.get('basis', {})
    if basis_data:
        basis = basis_data.get('current', 0)
        basis_volatility = basis_data.get('volatility', 0.01)
        z_b = basis / basis_volatility
        asymmetries['basis_stress'] = z_b
    
    # Depth Vacuum (Z_D)
    orderbook_data = market_data.get('orderbook', {})
    if orderbook_data:
        bid_depth = orderbook_data.get('bid_depth', 0)
        ask_depth = orderbook_data.get('ask_depth', 0)
        depth_imbalance = (ask_depth - bid_depth) / (ask_depth + bid_depth)
        asymmetries['depth_vacuum'] = depth_imbalance
    
    # Combined asymmetry score
    asymmetry_scores = [abs(v) for v in asymmetries.values()]
    combined_asymmetry = np.mean(asymmetry_scores) if asymmetry_scores else 0
    
    asymmetries['combined_score'] = combined_asymmetry
    
    return asymmetries

def scale_budget_for_asymmetry(base_budget, asymmetries, max_scaling=2.0):
    """Scale budget based on crypto asymmetries"""
    
    combined_score = asymmetries.get('combined_score', 0)
    
    # Scaling factor based on asymmetry strength
    # Higher asymmetry = higher scaling (up to max_scaling)
    scaling_factor = 1.0 + min(combined_score * 0.5, max_scaling - 1.0)
    
    scaled_budget = base_budget * scaling_factor
    
    return scaled_budget, scaling_factor
```

## Core Architecture

### 1. Decision Maker Module Class

```python
class DecisionMakerModule:
    """Self-contained intelligence module for decision making"""
    
    def __init__(self, module_id: str, parent_modules: Optional[List[str]] = None):
        self.module_id = module_id
        self.module_type = 'decision_maker'
        self.parent_modules = parent_modules or []
        
        # Core Intelligence State
        self.intelligence = ModuleIntelligence(module_id=module_id)
        
        # Module Components
        self.curator_layer = self._initialize_curator_layer()
        self.portfolio_manager = self._initialize_portfolio_manager()
        self.risk_engine = self._initialize_risk_engine()
        self.allocation_engine = self._initialize_allocation_engine()
        self.crypto_asymmetry_engine = self._initialize_crypto_asymmetry_engine()
        self.learning_system = self._initialize_learning_system()
        self.communication_protocol = self._initialize_communication_protocol()
        
        # Mathematical Consciousness Patterns
        self.observer_effects = ObserverEffectEngine()
        self.entanglement_manager = EntanglementManager()
        self.resonance_engine = self._initialize_resonance_engine()
        
        # Performance Tracking
        self.performance_metrics = PerformanceTracker()
        self.decision_history = []
    
    def _initialize_curator_layer(self):
        """Initialize decision maker specific curator layer"""
        return DecisionMakerCuratorLayer(
            module_type='decision_maker',
            curators={
                'risk_curator': RiskCurator(weight=0.4, var_threshold=0.02),
                'allocation_curator': AllocationCurator(weight=0.3, diversification_threshold=0.7),
                'timing_curator': TimingCurator(weight=0.2, market_hours_only=True),
                'cost_curator': CostCurator(weight=0.1, max_transaction_cost=0.002),
                'compliance_curator': ComplianceCurator(weight=0.05, regulatory_limits=True)
            }
        )
    
    def _initialize_portfolio_manager(self):
        """Initialize portfolio management system"""
        return PortfolioManager(
            max_portfolio_value=1000000,  # $1M max
            max_position_size=0.1,        # 10% max per position
            max_daily_turnover=0.2,       # 20% max daily turnover
            risk_budget=0.02              # 2% max portfolio risk
        )
    
    def _initialize_risk_engine(self):
        """Initialize risk management engine"""
        return RiskEngine(
            var_confidence=0.95,
            max_var=0.02,                 # 2% max VaR
            max_cvar=0.03,                # 3% max CVaR
            max_drawdown=0.1,             # 10% max drawdown
            correlation_threshold=0.7     # Max correlation between positions
        )
    
    def _initialize_allocation_engine(self):
        """Initialize asset allocation engine"""
        return AllocationEngine(
            rebalance_threshold=0.05,     # 5% drift threshold
            transaction_cost=0.001,       # 0.1% transaction cost
            min_position_size=0.01,       # 1% minimum position
            max_concentration=0.3         # 30% max concentration
        )
    
    def _initialize_crypto_asymmetry_engine(self):
        """Initialize crypto asymmetry detection engine"""
        return CryptoAsymmetryEngine(
            asymmetry_threshold=1.0,      # Asymmetry detection threshold
            max_budget_scaling=2.0,       # 2x max budget scaling
            rebalance_frequency='1h'      # Hourly asymmetry check
        )
    
    def evaluate_trading_plan(self, trading_plan: Dict, market_context: Dict) -> Dict:
        """Evaluate trading plan and make decision"""
        
        # 1. Validate trading plan
        validation_result = self._validate_trading_plan(trading_plan)
        if not validation_result['valid']:
            return self._create_rejection_decision(validation_result)
        
        # 2. Calculate portfolio impact
        portfolio_impact = self._calculate_portfolio_impact(trading_plan)
        
        # 3. Apply risk assessment
        risk_assessment = self.risk_engine.assess_risk(trading_plan, portfolio_impact)
        
        # 4. Check allocation constraints
        allocation_check = self.allocation_engine.check_allocation(trading_plan, portfolio_impact)
        
        # 5. Detect crypto asymmetries
        asymmetries = self.crypto_asymmetry_engine.detect_asymmetries(trading_plan, market_context)
        
        # 6. Apply curator layer evaluation
        curator_evaluation = self.curator_layer.evaluate_plan(
            trading_plan, portfolio_impact, risk_assessment, allocation_check, asymmetries
        )
        
        # 7. Make final decision
        decision = self._make_final_decision(
            trading_plan, portfolio_impact, risk_assessment, 
            allocation_check, asymmetries, curator_evaluation
        )
        
        # 8. Record decision for learning
        self._record_decision(trading_plan, decision)
        
        return decision
    
    def _validate_trading_plan(self, trading_plan: Dict) -> Dict:
        """Validate trading plan structure and requirements"""
        validation_result = {
            'valid': True,
            'issues': [],
            'warnings': []
        }
        
        # Check required fields
        required_fields = ['symbol', 'direction', 'position_size', 'entry_conditions']
        for field in required_fields:
            if field not in trading_plan:
                validation_result['valid'] = False
                validation_result['issues'].append(f'Missing required field: {field}')
        
        # Check position size limits
        if 'position_size' in trading_plan:
            position_size = trading_plan['position_size']
            if position_size > self.portfolio_manager.max_position_size:
                validation_result['valid'] = False
                validation_result['issues'].append(f'Position size {position_size} exceeds limit {self.portfolio_manager.max_position_size}')
        
        # Check symbol validity
        if 'symbol' in trading_plan:
            if not self._is_symbol_tradeable(trading_plan['symbol']):
                validation_result['valid'] = False
                validation_result['issues'].append(f'Symbol {trading_plan["symbol"]} not tradeable')
        
        return validation_result
    
    def _calculate_portfolio_impact(self, trading_plan: Dict) -> Dict:
        """Calculate impact of trading plan on current portfolio"""
        
        # Get current portfolio state
        current_portfolio = self.portfolio_manager.get_current_portfolio()
        
        # Calculate new portfolio with this trade
        new_portfolio = self._simulate_portfolio_with_trade(current_portfolio, trading_plan)
        
        # Calculate impact metrics
        impact_metrics = {
            'current_value': current_portfolio['total_value'],
            'new_value': new_portfolio['total_value'],
            'value_change': new_portfolio['total_value'] - current_portfolio['total_value'],
            'current_risk': current_portfolio['portfolio_risk'],
            'new_risk': new_portfolio['portfolio_risk'],
            'risk_change': new_portfolio['portfolio_risk'] - current_portfolio['portfolio_risk'],
            'current_concentration': current_portfolio['concentration_risk'],
            'new_concentration': new_portfolio['concentration_risk'],
            'concentration_change': new_portfolio['concentration_risk'] - current_portfolio['concentration_risk']
        }
        
        return impact_metrics
    
    def _make_final_decision(self, trading_plan, portfolio_impact, risk_assessment, 
                           allocation_check, asymmetries, curator_evaluation) -> Dict:
        """Make final decision based on all evaluations"""
        
        # Calculate decision score
        decision_score = self._calculate_decision_score(
            portfolio_impact, risk_assessment, allocation_check, 
            asymmetries, curator_evaluation
        )
        
        # Determine decision
        if decision_score >= 0.7:
            decision_type = 'approve'
            modified_plan = trading_plan
        elif decision_score >= 0.4:
            decision_type = 'modify'
            modified_plan = self._modify_trading_plan(trading_plan, decision_score)
        else:
            decision_type = 'reject'
            modified_plan = None
        
        # Create decision result
        decision = {
            'decision_id': str(uuid.uuid4()),
            'plan_id': trading_plan.get('plan_id'),
            'decision_type': decision_type,
            'decision_score': decision_score,
            'trading_plan': modified_plan,
            'rejection_reasons': [] if decision_type != 'reject' else self._get_rejection_reasons(
                portfolio_impact, risk_assessment, allocation_check, curator_evaluation
            ),
            'risk_assessment': risk_assessment,
            'portfolio_impact': portfolio_impact,
            'asymmetries': asymmetries,
            'curator_decisions': curator_evaluation,
            'created_at': datetime.now(timezone.utc),
            'valid_until': datetime.now(timezone.utc).timestamp() + 3600  # 1 hour
        }
        
        return decision
    
    def _calculate_decision_score(self, portfolio_impact, risk_assessment, 
                                allocation_check, asymmetries, curator_evaluation) -> float:
        """Calculate overall decision score"""
        
        # Base score from curator evaluation
        base_score = curator_evaluation.get('score', 0.5)
        
        # Risk adjustment
        risk_score = risk_assessment.get('risk_score', 0.5)
        risk_adjustment = (risk_score - 0.5) * 0.3  # ±15% adjustment
        
        # Allocation adjustment
        allocation_score = allocation_check.get('allocation_score', 0.5)
        allocation_adjustment = (allocation_score - 0.5) * 0.2  # ±10% adjustment
        
        # Asymmetry adjustment
        asymmetry_score = asymmetries.get('combined_score', 0)
        asymmetry_adjustment = min(asymmetry_score * 0.1, 0.2)  # Up to 20% boost
        
        # Portfolio impact adjustment
        impact_score = self._calculate_impact_score(portfolio_impact)
        impact_adjustment = (impact_score - 0.5) * 0.1  # ±5% adjustment
        
        # Calculate final score
        final_score = base_score + risk_adjustment + allocation_adjustment + asymmetry_adjustment + impact_adjustment
        
        # Ensure score is between 0 and 1
        final_score = max(0.0, min(1.0, final_score))
        
        return final_score
```

## Database Schema

### Decision Maker Strands (dm_strand)

```sql
-- Decision Maker strands (following Lotus architecture)
CREATE TABLE dm_strand (
    id TEXT PRIMARY KEY,                    -- ULID
    lifecycle_id TEXT,                      -- Thread identifier
    parent_id TEXT,                         -- Linkage to parent strand
    module TEXT DEFAULT 'dm',               -- Module identifier
    kind TEXT,                              -- 'decision'|'evaluation'|'risk_assessment'
    symbol TEXT,                            -- Trading symbol
    timeframe TEXT,                         -- '1m'|'5m'|'15m'|'1h'|'4h'|'1d'
    session_bucket TEXT,                    -- Session identifier
    regime TEXT,                            -- Market regime
    alpha_bundle_ref TEXT,                  -- Reference to sig_strand
    dm_alpha JSONB,                         -- Fused alpha signal data
    dm_budget JSONB,                        -- Budget allocation data
    dm_decision JSONB,                      -- Decision result
    risk_metrics JSONB,                     -- Risk assessment metrics
    portfolio_impact JSONB,                 -- Portfolio impact analysis
    asymmetries JSONB,                      -- Crypto asymmetry data
    curator_decisions JSONB,                -- Curator evaluation results
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for fast queries
CREATE INDEX dm_strand_symbol_time ON dm_strand(symbol, created_at DESC);
CREATE INDEX dm_strand_lifecycle ON dm_strand(lifecycle_id);
CREATE INDEX dm_strand_alpha_ref ON dm_strand(alpha_bundle_ref);
CREATE INDEX dm_strand_decision_type ON dm_strand((dm_decision->>'decision_type'));
```

## Configuration

```yaml
decision_maker_module:
  portfolio:
    max_portfolio_value: 1000000
    max_position_size: 0.1
    max_daily_turnover: 0.2
    risk_budget: 0.02
  
  risk_management:
    var_confidence: 0.95
    max_var: 0.02
    max_cvar: 0.03
    max_drawdown: 0.1
    correlation_threshold: 0.7
  
  allocation:
    rebalance_threshold: 0.05
    transaction_cost: 0.001
    min_position_size: 0.01
    max_concentration: 0.3
  
  crypto_asymmetries:
    asymmetry_threshold: 1.0
    max_budget_scaling: 2.0
    rebalance_frequency: "1h"
  
  curators:
    risk:
      weight: 0.4
      var_threshold: 0.02
    allocation:
      weight: 0.3
      diversification_threshold: 0.7
    timing:
      weight: 0.2
      market_hours_only: true
    cost:
      weight: 0.1
      max_transaction_cost: 0.002
    compliance:
      weight: 0.05
      regulatory_limits: true
```

This provides the complete core architecture for the Decision Maker Module with all the mathematical foundations, risk management, portfolio allocation, and crypto asymmetry detection capabilities!
