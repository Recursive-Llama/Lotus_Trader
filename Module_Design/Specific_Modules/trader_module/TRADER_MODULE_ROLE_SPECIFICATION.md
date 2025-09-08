# Trader Module - Role Specification

*Crystal clear definition of what the Trader Module receives, does, and reports*

## **CORE ROLE: EXECUTION MODULE**

The Trader Module is **NOT** a plan generator - it's an **execution module** that receives approved trading plans and executes them.

## **What the Trader Module RECEIVES:**

### **Input: Approved Trading Plans (dm-decision-1.0 events)**
```python
# Schema for what Trader receives from Decision Maker
class ApprovedTradingPlan:
    """Complete trading plan approved by Decision Maker"""
    
    # Core plan data
    plan_id: str
    signal_id: str
    decision_id: str
    symbol: str
    
    # Trading parameters
    direction: str  # 'long', 'short'
    position_size: float  # % of portfolio
    entry_price: Optional[float]  # Target entry price
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # Entry/exit conditions
    entry_conditions: Dict[str, Any]  # Market conditions to trigger entry
    exit_conditions: Dict[str, Any]   # Market conditions to trigger exit
    
    # Risk management
    max_position_size: float
    risk_reward_ratio: float
    confidence_score: float
    
    # Execution parameters
    execution_strategy: str  # 'market', 'limit', 'twap'
    max_slippage: float
    max_latency_ms: int
    venue_preferences: List[str]
    
    # Metadata
    created_at: datetime
    valid_until: datetime
    execution_notes: Optional[str]
```

## **What the Trader Module DOES:**

### **1. Plan Validation**
```python
def validate_approved_plan(self, plan: ApprovedTradingPlan) -> Dict:
    """Validate the approved plan before execution"""
    validation_result = {
        'valid': True,
        'issues': [],
        'warnings': []
    }
    
    # Check if plan is still valid (not expired)
    if datetime.now() > plan.valid_until:
        validation_result['valid'] = False
        validation_result['issues'].append('Plan expired')
    
    # Check position size limits
    if plan.position_size > plan.max_position_size:
        validation_result['valid'] = False
        validation_result['issues'].append('Position size exceeds limit')
    
    # Check if symbol is tradeable
    if not self._is_symbol_tradeable(plan.symbol):
        validation_result['valid'] = False
        validation_result['issues'].append('Symbol not tradeable')
    
    return validation_result
```

### **2. Entry Condition Monitoring**
```python
def check_entry_conditions(self, plan: ApprovedTradingPlan) -> bool:
    """Monitor market conditions for entry trigger"""
    current_market_data = self._get_current_market_data(plan.symbol)
    
    # Check each entry condition
    for condition_type, condition_value in plan.entry_conditions.items():
        if condition_type == 'price_above':
            if current_market_data['price'] <= condition_value:
                return False
        elif condition_type == 'price_below':
            if current_market_data['price'] >= condition_value:
                return False
        elif condition_type == 'volume_spike':
            if current_market_data['volume'] < condition_value:
                return False
        elif condition_type == 'volatility_threshold':
            if current_market_data['volatility'] < condition_value:
                return False
    
    return True
```

### **3. Venue Selection**
```python
def select_optimal_venue(self, plan: ApprovedTradingPlan) -> str:
    """Select best venue for execution based on plan requirements"""
    available_venues = self._get_available_venues(plan.symbol)
    
    venue_scores = {}
    for venue in available_venues:
        score = self._calculate_venue_score(venue, plan)
        venue_scores[venue] = score
    
    # Select venue with highest score
    best_venue = max(venue_scores, key=venue_scores.get)
    return best_venue

def _calculate_venue_score(self, venue: str, plan: ApprovedTradingPlan) -> float:
    """Calculate venue score based on plan requirements"""
    venue_data = self._get_venue_data(venue, plan.symbol)
    
    # Liquidity score
    liquidity_score = min(1.0, venue_data['liquidity'] / plan.position_size)
    
    # Latency score
    latency_score = max(0.0, 1.0 - (venue_data['latency_ms'] / plan.max_latency_ms))
    
    # Slippage score
    expected_slippage = venue_data['expected_slippage']
    slippage_score = max(0.0, 1.0 - (expected_slippage / plan.max_slippage))
    
    # Historical performance score
    performance_score = venue_data['success_rate']
    
    # Weighted combination
    total_score = (
        liquidity_score * 0.3 +
        latency_score * 0.2 +
        slippage_score * 0.2 +
        performance_score * 0.3
    )
    
    return total_score
```

### **4. Trade Execution**
```python
def execute_trade(self, plan: ApprovedTradingPlan, venue: str) -> Dict:
    """Execute the trade on selected venue"""
    execution_id = str(uuid.uuid4())
    
    try:
        # Get current market data
        market_data = self._get_current_market_data(plan.symbol)
        
        # Calculate execution parameters
        execution_params = self._calculate_execution_params(plan, market_data)
        
        # Execute based on strategy
        if plan.execution_strategy == 'market':
            result = self._execute_market_order(plan, venue, execution_params)
        elif plan.execution_strategy == 'limit':
            result = self._execute_limit_order(plan, venue, execution_params)
        elif plan.execution_strategy == 'twap':
            result = self._execute_twap_order(plan, venue, execution_params)
        else:
            raise ValueError(f"Unknown execution strategy: {plan.execution_strategy}")
        
        # Calculate actual metrics
        actual_slippage = self._calculate_actual_slippage(result, plan)
        actual_latency = self._calculate_actual_latency(result)
        
        execution_result = {
            'execution_id': execution_id,
            'plan_id': plan.plan_id,
            'symbol': plan.symbol,
            'venue': venue,
            'status': 'filled' if result['success'] else 'failed',
            'executed_price': result['price'],
            'executed_quantity': result['quantity'],
            'expected_price': execution_params['expected_price'],
            'actual_slippage': actual_slippage,
            'actual_latency_ms': actual_latency,
            'fees': result.get('fees', 0),
            'execution_time': datetime.now(timezone.utc),
            'error_message': result.get('error_message')
        }
        
        return execution_result
        
    except Exception as e:
        return {
            'execution_id': execution_id,
            'plan_id': plan.plan_id,
            'symbol': plan.symbol,
            'venue': venue,
            'status': 'failed',
            'error_message': str(e),
            'execution_time': datetime.now(timezone.utc)
        }
```

### **5. Position Tracking**
```python
def update_position_tracking(self, execution_result: Dict):
    """Update position tracking after execution"""
    symbol = execution_result['symbol']
    
    if execution_result['status'] == 'filled':
        # Update position
        self.position_tracker.update_position(
            symbol=symbol,
            quantity=execution_result['executed_quantity'],
            price=execution_result['executed_price'],
            side=execution_result.get('side', 'buy'),
            execution_id=execution_result['execution_id']
        )
        
        # Update P&L
        self.position_tracker.update_pnl(symbol)
        
        # Check exit conditions
        self._check_exit_conditions(symbol)

def _check_exit_conditions(self, symbol: str):
    """Check if any positions should be exited"""
    current_position = self.position_tracker.get_position(symbol)
    if not current_position:
        return
    
    # Get current market data
    market_data = self._get_current_market_data(symbol)
    
    # Check stop loss
    if current_position['stop_loss'] and market_data['price'] <= current_position['stop_loss']:
        self._execute_exit(symbol, 'stop_loss', market_data['price'])
    
    # Check take profit
    elif current_position['take_profit'] and market_data['price'] >= current_position['take_profit']:
        self._execute_exit(symbol, 'take_profit', market_data['price'])
    
    # Check other exit conditions
    elif self._check_other_exit_conditions(symbol, market_data):
        self._execute_exit(symbol, 'condition_met', market_data['price'])
```

## **What the Trader Module REPORTS BACK:**

### **Output: Execution Reports (exec-report-1.0 events)**
```python
# Schema for what Trader reports back to other modules
class ExecutionReport:
    """Execution report sent back to Alpha Detector and Decision Maker"""
    
    # Core execution data
    execution_id: str
    plan_id: str
    signal_id: str
    decision_id: str
    symbol: str
    
    # Execution results
    status: str  # 'filled', 'partial', 'failed', 'cancelled'
    executed_price: float
    executed_quantity: float
    execution_time: datetime
    
    # Performance metrics
    slippage: float  # Actual vs expected price
    latency_ms: int  # Execution latency
    adherence_score: float  # How well execution followed plan
    venue_score: float  # Venue performance score
    
    # Position updates
    position_after: Dict[str, Any]  # Position state after execution
    pnl_impact: float  # P&L impact of this execution
    
    # Learning data
    what_worked: List[str]  # What worked well
    what_didnt_work: List[str]  # What didn't work
    lessons_learned: List[str]  # Key lessons
    
    # Metadata
    created_at: datetime
    reported_to: List[str]  # Which modules received this report
```

### **Reporting Process**
```python
def report_execution_result(self, execution_result: Dict):
    """Report execution result back to other modules"""
    
    # Create execution report
    report = ExecutionReport(
        execution_id=execution_result['execution_id'],
        plan_id=execution_result['plan_id'],
        symbol=execution_result['symbol'],
        status=execution_result['status'],
        executed_price=execution_result.get('executed_price', 0),
        executed_quantity=execution_result.get('executed_quantity', 0),
        execution_time=execution_result['execution_time'],
        slippage=execution_result.get('actual_slippage', 0),
        latency_ms=execution_result.get('actual_latency_ms', 0),
        adherence_score=self._calculate_adherence_score(execution_result),
        venue_score=self._calculate_venue_score(execution_result),
        position_after=self.position_tracker.get_position(execution_result['symbol']),
        pnl_impact=self._calculate_pnl_impact(execution_result),
        what_worked=self._identify_what_worked(execution_result),
        what_didnt_work=self._identify_what_didnt_work(execution_result),
        lessons_learned=self._extract_lessons_learned(execution_result),
        created_at=datetime.now(timezone.utc),
        reported_to=['alpha_detector', 'decision_maker', 'learning_systems']
    )
    
    # Send to Alpha Detector
    self.communication_protocol.send_to_alpha_detector(report)
    
    # Send to Decision Maker
    self.communication_protocol.send_to_decision_maker(report)
    
    # Send to Learning Systems
    self.communication_protocol.send_to_learning_systems(report)
    
    # Store for internal learning
    self.learning_system.update_performance(execution_result)
```

## **Key Points:**

1. **Trader Module RECEIVES** approved trading plans from Decision Maker
2. **Trader Module EXECUTES** those plans (doesn't create them)
3. **Trader Module TRACKS** positions and monitors exit conditions
4. **Trader Module REPORTS** execution results back to all other modules
5. **Trader Module LEARNS** from execution performance to improve future execution

The Trader Module is the **execution engine** of the system - it takes approved plans and makes them happen in the real world, then reports back on how it went.
