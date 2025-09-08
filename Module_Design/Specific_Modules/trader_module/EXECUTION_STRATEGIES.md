# Trader Module - Execution Strategies Build Plan

*Mathematical implementation of execution strategies with detailed formulas*

## Executive Summary

This document provides the mathematical implementation of execution strategies for the Trader Module, including market orders, limit orders, TWAP, VWAP, and adaptive strategies with detailed formulas and algorithms. The strategies are designed to work across a multi-venue ecosystem, with venue-specific optimizations for centralized exchanges, decentralized protocols, and emerging venues.

## Mathematical Foundations

### 1. Market Order Strategy

#### **Market Order Execution Formula**
```python
# Market order execution with slippage estimation
def execute_market_order(trading_plan, venue, execution_params):
    """Execute market order with mathematical slippage estimation"""
    symbol = trading_plan['symbol']
    quantity = trading_plan['position_size']
    side = trading_plan['direction']
    
    # Get current market data
    orderbook = venue.get_orderbook(symbol)
    current_price = get_mid_price(orderbook)
    
    # Calculate expected slippage
    expected_slippage = calculate_market_impact(quantity, orderbook, side)
    
    # Calculate expected execution price
    if side == 'buy':
        expected_price = current_price * (1 + expected_slippage)
    else:
        expected_price = current_price * (1 - expected_slippage)
    
    # Execute order
    order_result = venue.place_market_order(symbol, quantity, side)
    
    # Calculate actual slippage
    actual_slippage = calculate_actual_slippage(order_result, expected_price, side)
    
    return {
        'order_id': order_result['order_id'],
        'executed_price': order_result['price'],
        'executed_quantity': order_result['quantity'],
        'expected_price': expected_price,
        'expected_slippage': expected_slippage,
        'actual_slippage': actual_slippage,
        'execution_time': order_result['timestamp']
    }

# Market impact calculation using Almgren-Chriss model
def calculate_market_impact(quantity, orderbook, side):
    """Calculate expected market impact using Almgren-Chriss model"""
    # Get market depth
    if side == 'buy':
        depth_levels = orderbook['asks']
    else:
        depth_levels = orderbook['bids']
    
    # Calculate available liquidity
    available_liquidity = sum(level['size'] for level in depth_levels[:5])
    
    # Calculate market impact
    if quantity <= available_liquidity:
        # Linear impact for small orders
        impact = (quantity / available_liquidity) * 0.001  # 0.1% base impact
    else:
        # Quadratic impact for large orders
        impact = 0.001 + ((quantity - available_liquidity) / available_liquidity) ** 2 * 0.005
    
    return min(impact, 0.01)  # Cap at 1%
```

### 2. Limit Order Strategy

#### **Limit Order Pricing Formula**
```python
# Limit order pricing with optimal spread calculation
def calculate_limit_price(trading_plan, venue, execution_params):
    """Calculate optimal limit price using mathematical models"""
    symbol = trading_plan['symbol']
    quantity = trading_plan['position_size']
    side = trading_plan['direction']
    urgency = execution_params.get('urgency', 'normal')
    
    # Get market data
    orderbook = venue.get_orderbook(symbol)
    mid_price = get_mid_price(orderbook)
    spread = get_spread(orderbook)
    
    # Calculate optimal spread offset
    if urgency == 'high':
        spread_offset = 0.1  # 10% of spread
    elif urgency == 'normal':
        spread_offset = 0.3  # 30% of spread
    else:  # low urgency
        spread_offset = 0.5  # 50% of spread
    
    # Calculate limit price
    if side == 'buy':
        limit_price = mid_price - (spread * spread_offset)
    else:
        limit_price = mid_price + (spread * spread_offset)
    
    # Apply price constraints
    limit_price = apply_price_constraints(limit_price, orderbook, side)
    
    return limit_price

# Fill probability estimation
def estimate_fill_probability(limit_price, orderbook, side, time_horizon):
    """Estimate fill probability for limit order"""
    if side == 'buy':
        # Check if limit price is above best ask
        best_ask = orderbook['asks'][0]['price']
        if limit_price >= best_ask:
            return 1.0  # Immediate fill
        
        # Calculate probability based on order book depth
        depth_above = sum(level['size'] for level in orderbook['asks'] if level['price'] <= limit_price)
        total_depth = sum(level['size'] for level in orderbook['asks'][:10])
        
        base_probability = depth_above / total_depth if total_depth > 0 else 0
        
        # Time decay factor
        time_decay = np.exp(-time_horizon / 300)  # 5-minute half-life
        
        return base_probability * time_decay
    
    else:  # sell
        # Check if limit price is below best bid
        best_bid = orderbook['bids'][0]['price']
        if limit_price <= best_bid:
            return 1.0  # Immediate fill
        
        # Calculate probability based on order book depth
        depth_below = sum(level['size'] for level in orderbook['bids'] if level['price'] >= limit_price)
        total_depth = sum(level['size'] for level in orderbook['bids'][:10])
        
        base_probability = depth_below / total_depth if total_depth > 0 else 0
        
        # Time decay factor
        time_decay = np.exp(-time_horizon / 300)  # 5-minute half-life
        
        return base_probability * time_decay
```

### 3. TWAP Strategy

#### **TWAP Execution Formula**
```python
# Time-Weighted Average Price execution
def execute_twap_strategy(trading_plan, venue, execution_params):
    """Execute TWAP strategy with mathematical optimization"""
    symbol = trading_plan['symbol']
    total_quantity = trading_plan['position_size']
    side = trading_plan['direction']
    time_horizon = trading_plan['time_horizon']  # in minutes
    
    # Calculate execution parameters
    num_intervals = max(1, time_horizon // 1)  # 1-minute intervals
    quantity_per_interval = total_quantity / num_intervals
    
    # Calculate interval timing
    interval_duration = 60  # 1 minute in seconds
    start_time = datetime.now()
    
    execution_results = []
    remaining_quantity = total_quantity
    
    for i in range(num_intervals):
        if remaining_quantity <= 0:
            break
        
        # Calculate interval start time
        interval_start = start_time + timedelta(seconds=i * interval_duration)
        
        # Wait until interval start
        wait_until(interval_start)
        
        # Calculate quantity for this interval
        interval_quantity = min(quantity_per_interval, remaining_quantity)
        
        # Execute order for this interval
        order_result = execute_interval_order(
            symbol, interval_quantity, side, venue, execution_params
        )
        
        execution_results.append(order_result)
        remaining_quantity -= order_result['executed_quantity']
    
    # Calculate TWAP metrics
    twap_metrics = calculate_twap_metrics(execution_results, total_quantity)
    
    return {
        'execution_results': execution_results,
        'twap_metrics': twap_metrics,
        'total_executed': total_quantity - remaining_quantity,
        'remaining_quantity': remaining_quantity
    }

# TWAP metrics calculation
def calculate_twap_metrics(execution_results, total_quantity):
    """Calculate TWAP execution metrics"""
    if not execution_results:
        return {
            'twap_price': 0.0,
            'market_impact': 0.0,
            'execution_quality': 0.0
        }
    
    # Calculate TWAP price
    total_value = sum(result['executed_price'] * result['executed_quantity'] 
                     for result in execution_results)
    total_executed = sum(result['executed_quantity'] for result in execution_results)
    
    twap_price = total_value / total_executed if total_executed > 0 else 0.0
    
    # Calculate market impact
    market_impact = calculate_twap_market_impact(execution_results, twap_price)
    
    # Calculate execution quality
    execution_quality = calculate_twap_execution_quality(execution_results, total_quantity)
    
    return {
        'twap_price': twap_price,
        'market_impact': market_impact,
        'execution_quality': execution_quality,
        'total_executed': total_executed,
        'num_intervals': len(execution_results)
    }

# TWAP market impact calculation
def calculate_twap_market_impact(execution_results, twap_price):
    """Calculate market impact for TWAP execution"""
    if not execution_results:
        return 0.0
    
    # Calculate average market impact
    impacts = []
    for result in execution_results:
        # Get market price at execution time
        market_price = get_market_price_at_time(result['execution_time'])
        
        # Calculate impact
        impact = abs(result['executed_price'] - market_price) / market_price
        impacts.append(impact)
    
    return np.mean(impacts) if impacts else 0.0
```

### 4. VWAP Strategy

#### **VWAP Execution Formula**
```python
# Volume-Weighted Average Price execution
def execute_vwap_strategy(trading_plan, venue, execution_params):
    """Execute VWAP strategy with mathematical optimization"""
    symbol = trading_plan['symbol']
    total_quantity = trading_plan['position_size']
    side = trading_plan['direction']
    time_horizon = trading_plan['time_horizon']  # in minutes
    
    # Get historical volume data for VWAP calculation
    volume_data = get_historical_volume(symbol, time_horizon)
    
    # Calculate VWAP target
    vwap_target = calculate_vwap_target(volume_data, time_horizon)
    
    # Calculate execution schedule
    execution_schedule = calculate_vwap_schedule(
        total_quantity, volume_data, time_horizon
    )
    
    execution_results = []
    remaining_quantity = total_quantity
    
    for interval in execution_schedule:
        if remaining_quantity <= 0:
            break
        
        # Wait until interval start
        wait_until(interval['start_time'])
        
        # Calculate quantity for this interval
        interval_quantity = min(interval['target_quantity'], remaining_quantity)
        
        # Execute order for this interval
        order_result = execute_interval_order(
            symbol, interval_quantity, side, venue, execution_params
        )
        
        execution_results.append(order_result)
        remaining_quantity -= order_result['executed_quantity']
    
    # Calculate VWAP metrics
    vwap_metrics = calculate_vwap_metrics(execution_results, vwap_target)
    
    return {
        'execution_results': execution_results,
        'vwap_metrics': vwap_metrics,
        'vwap_target': vwap_target,
        'total_executed': total_quantity - remaining_quantity,
        'remaining_quantity': remaining_quantity
    }

# VWAP target calculation
def calculate_vwap_target(volume_data, time_horizon):
    """Calculate VWAP target from historical data"""
    if not volume_data:
        return 0.0
    
    # Calculate VWAP over time horizon
    total_value = sum(bar['close'] * bar['volume'] for bar in volume_data)
    total_volume = sum(bar['volume'] for bar in volume_data)
    
    vwap_target = total_value / total_volume if total_volume > 0 else 0.0
    
    return vwap_target

# VWAP schedule calculation
def calculate_vwap_schedule(total_quantity, volume_data, time_horizon):
    """Calculate VWAP execution schedule"""
    if not volume_data:
        # Fallback to TWAP if no volume data
        num_intervals = max(1, time_horizon // 1)
        quantity_per_interval = total_quantity / num_intervals
        
        schedule = []
        for i in range(num_intervals):
            schedule.append({
                'start_time': datetime.now() + timedelta(minutes=i),
                'target_quantity': quantity_per_interval
            })
        
        return schedule
    
    # Calculate volume-weighted schedule
    total_volume = sum(bar['volume'] for bar in volume_data)
    num_intervals = len(volume_data)
    
    schedule = []
    for i, bar in enumerate(volume_data):
        # Calculate target quantity based on volume proportion
        volume_proportion = bar['volume'] / total_volume
        target_quantity = total_quantity * volume_proportion
        
        schedule.append({
            'start_time': bar['timestamp'],
            'target_quantity': target_quantity
        })
    
    return schedule

# VWAP metrics calculation
def calculate_vwap_metrics(execution_results, vwap_target):
    """Calculate VWAP execution metrics"""
    if not execution_results:
        return {
            'vwap_achieved': 0.0,
            'vwap_deviation': 0.0,
            'execution_quality': 0.0
        }
    
    # Calculate achieved VWAP
    total_value = sum(result['executed_price'] * result['executed_quantity'] 
                     for result in execution_results)
    total_executed = sum(result['executed_quantity'] for result in execution_results)
    
    vwap_achieved = total_value / total_executed if total_executed > 0 else 0.0
    
    # Calculate VWAP deviation
    vwap_deviation = abs(vwap_achieved - vwap_target) / vwap_target if vwap_target > 0 else 0.0
    
    # Calculate execution quality
    execution_quality = 1.0 - vwap_deviation
    
    return {
        'vwap_achieved': vwap_achieved,
        'vwap_target': vwap_target,
        'vwap_deviation': vwap_deviation,
        'execution_quality': execution_quality,
        'total_executed': total_executed
    }
```

### 5. Multi-Venue Adaptive Strategy

#### **Venue-Aware Adaptive Execution Formula**
```python
# Multi-venue adaptive execution strategy
def execute_multi_venue_adaptive_strategy(trading_plan, venue_ecosystem, execution_params):
    """Execute adaptive strategy across multi-venue ecosystem"""
    symbol = trading_plan['symbol']
    quantity = trading_plan['position_size']
    side = trading_plan['direction']
    time_horizon = trading_plan['time_horizon']
    
    # Analyze market conditions across venues
    market_conditions = analyze_multi_venue_market_conditions(symbol, venue_ecosystem)
    
    # Select optimal venue and strategy combination
    venue_strategy = select_optimal_venue_strategy(market_conditions, trading_plan, venue_ecosystem)
    
    # Execute using selected venue-strategy combination
    if venue_strategy['venue_type'] == 'cex':
        return execute_cex_strategy(trading_plan, venue_strategy, execution_params)
    elif venue_strategy['venue_type'] == 'dex':
        return execute_dex_strategy(trading_plan, venue_strategy, execution_params)
    elif venue_strategy['venue_type'] == 'hybrid':
        return execute_hybrid_strategy(trading_plan, venue_strategy, execution_params)
    elif venue_strategy['venue_type'] == 'emerging':
        return execute_emerging_strategy(trading_plan, venue_strategy, execution_params)
    else:
        raise ValueError(f"Unknown venue type: {venue_strategy['venue_type']}")

def analyze_multi_venue_market_conditions(symbol, venue_ecosystem):
    """Analyze market conditions across multiple venues"""
    market_conditions = {}
    
    # Analyze CEX conditions
    for cex in venue_ecosystem['centralized']:
        if cex['enabled']:
            conditions = analyze_cex_market_conditions(symbol, cex)
            market_conditions[f"cex_{cex['name']}"] = conditions
    
    # Analyze DEX conditions
    for chain, dexes in venue_ecosystem['decentralized'].items():
        for dex in dexes:
            if dex['enabled']:
                conditions = analyze_dex_market_conditions(symbol, dex, chain)
                market_conditions[f"dex_{chain}_{dex['name']}"] = conditions
    
    # Calculate aggregated conditions
    aggregated_conditions = calculate_aggregated_market_conditions(market_conditions)
    
    return {
        'venue_conditions': market_conditions,
        'aggregated': aggregated_conditions
    }

def select_optimal_venue_strategy(market_conditions, trading_plan, venue_ecosystem):
    """Select optimal venue-strategy combination"""
    venue_strategy_scores = {}
    
    # Evaluate CEX venue-strategy combinations
    for cex in venue_ecosystem['centralized']:
        if cex['enabled']:
            venue_key = f"cex_{cex['name']}"
            if venue_key in market_conditions['venue_conditions']:
                conditions = market_conditions['venue_conditions'][venue_key]
                strategies = ['market', 'limit', 'twap', 'vwap']
                
                for strategy in strategies:
                    score = calculate_venue_strategy_score(cex, strategy, conditions, trading_plan)
                    venue_strategy_scores[f"{venue_key}_{strategy}"] = {
                        'venue': cex,
                        'strategy': strategy,
                        'venue_type': 'cex',
                        'score': score
                    }
    
    # Evaluate DEX venue-strategy combinations
    for chain, dexes in venue_ecosystem['decentralized'].items():
        for dex in dexes:
            if dex['enabled']:
                venue_key = f"dex_{chain}_{dex['name']}"
                if venue_key in market_conditions['venue_conditions']:
                    conditions = market_conditions['venue_conditions'][venue_key]
                    strategies = ['market', 'limit', 'twap']  # DEX-specific strategies
                    
                    for strategy in strategies:
                        score = calculate_venue_strategy_score(dex, strategy, conditions, trading_plan, chain)
                        venue_strategy_scores[f"{venue_key}_{strategy}"] = {
                            'venue': dex,
                            'strategy': strategy,
                            'venue_type': 'dex',
                            'chain': chain,
                            'score': score
                        }
    
    # Select best venue-strategy combination
    best_combination = max(venue_strategy_scores, key=lambda x: venue_strategy_scores[x]['score'])
    
    return venue_strategy_scores[best_combination]

# Market conditions analysis
def analyze_market_conditions(symbol, venue):
    """Analyze market conditions for strategy selection"""
    # Get current market data
    orderbook = venue.get_orderbook(symbol)
    recent_trades = venue.get_recent_trades(symbol, limit=100)
    
    # Calculate market metrics
    spread = get_spread(orderbook)
    volatility = calculate_volatility(recent_trades)
    volume = calculate_volume(recent_trades)
    liquidity = calculate_liquidity(orderbook)
    
    # Calculate market condition scores
    conditions = {
        'spread': spread,
        'volatility': volatility,
        'volume': volume,
        'liquidity': liquidity,
        'market_stress': calculate_market_stress(spread, volatility, volume),
        'trend_strength': calculate_trend_strength(recent_trades)
    }
    
    return conditions

# Strategy selection based on market conditions
def select_adaptive_strategy(market_conditions, trading_plan):
    """Select optimal strategy based on market conditions"""
    spread = market_conditions['spread']
    volatility = market_conditions['volatility']
    liquidity = market_conditions['liquidity']
    market_stress = market_conditions['market_stress']
    quantity = trading_plan['position_size']
    time_horizon = trading_plan['time_horizon']
    
    # Strategy selection logic
    if market_stress > 0.8:  # High market stress
        return 'market'  # Use market orders for immediate execution
    elif liquidity < 0.3:  # Low liquidity
        return 'limit'  # Use limit orders to avoid market impact
    elif quantity > 10000:  # Large order
        if time_horizon > 60:  # Long time horizon
            return 'vwap'  # Use VWAP for large orders
        else:
            return 'twap'  # Use TWAP for medium time horizon
    elif volatility > 0.05:  # High volatility
        return 'limit'  # Use limit orders to avoid volatility
    else:
        return 'market'  # Default to market orders
```

## Implementation Classes

### 1. Execution Strategy Base Class

```python
class ExecutionStrategy:
    """Base class for execution strategies"""
    
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.performance_metrics = {}
    
    def execute(self, trading_plan, venue, execution_params):
        """Execute trading plan using this strategy"""
        raise NotImplementedError
    
    def calculate_expected_performance(self, trading_plan, venue):
        """Calculate expected performance metrics"""
        raise NotImplementedError
    
    def update_performance(self, execution_result):
        """Update strategy performance based on execution result"""
        # Update performance metrics
        self.performance_metrics.update(execution_result['metrics'])
    
    def get_performance_score(self):
        """Get overall performance score for this strategy"""
        if not self.performance_metrics:
            return 0.5
        
        # Calculate weighted performance score
        weights = self.config.get('performance_weights', {
            'slippage': 0.3,
            'latency': 0.2,
            'adherence': 0.3,
            'venue': 0.2
        })
        
        total_score = 0.0
        total_weight = 0.0
        
        for metric, weight in weights.items():
            if metric in self.performance_metrics:
                score = self.performance_metrics[metric]
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.5
```

### 2. Market Order Strategy Implementation

```python
class MarketOrderStrategy(ExecutionStrategy):
    """Market order execution strategy"""
    
    def __init__(self, config):
        super().__init__("market", config)
        self.max_slippage = config.get('max_slippage', 0.01)
        self.max_latency = config.get('max_latency', 1000)
    
    def execute(self, trading_plan, venue, execution_params):
        """Execute market order"""
        symbol = trading_plan['symbol']
        quantity = trading_plan['position_size']
        side = trading_plan['direction']
        
        # Get current market data
        orderbook = venue.get_orderbook(symbol)
        current_price = get_mid_price(orderbook)
        
        # Calculate expected slippage
        expected_slippage = self.calculate_expected_slippage(quantity, orderbook, side)
        
        # Check slippage limits
        if expected_slippage > self.max_slippage:
            return self._create_rejection_result(
                f"Expected slippage {expected_slippage:.4f} exceeds limit {self.max_slippage:.4f}"
            )
        
        # Execute order
        start_time = datetime.now()
        order_result = venue.place_market_order(symbol, quantity, side)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Check latency limits
        if execution_time > self.max_latency:
            return self._create_rejection_result(
                f"Execution latency {execution_time:.0f}ms exceeds limit {self.max_latency}ms"
            )
        
        # Calculate actual slippage
        actual_slippage = self.calculate_actual_slippage(order_result, current_price, side)
        
        # Calculate performance metrics
        metrics = self.calculate_performance_metrics(
            order_result, expected_slippage, actual_slippage, execution_time
        )
        
        return {
            'strategy': self.name,
            'order_id': order_result['order_id'],
            'executed_price': order_result['price'],
            'executed_quantity': order_result['quantity'],
            'execution_time': execution_time,
            'metrics': metrics,
            'status': 'filled'
        }
    
    def calculate_expected_slippage(self, quantity, orderbook, side):
        """Calculate expected slippage for market order"""
        if side == 'buy':
            depth_levels = orderbook['asks']
        else:
            depth_levels = orderbook['bids']
        
        # Calculate available liquidity
        available_liquidity = sum(level['size'] for level in depth_levels[:5])
        
        # Calculate market impact
        if quantity <= available_liquidity:
            impact = (quantity / available_liquidity) * 0.001
        else:
            impact = 0.001 + ((quantity - available_liquidity) / available_liquidity) ** 2 * 0.005
        
        return min(impact, 0.01)
    
    def calculate_actual_slippage(self, order_result, expected_price, side):
        """Calculate actual slippage from execution result"""
        actual_price = order_result['price']
        
        if side == 'buy':
            slippage = (actual_price - expected_price) / expected_price
        else:
            slippage = (expected_price - actual_price) / expected_price
        
        return slippage
    
    def calculate_performance_metrics(self, order_result, expected_slippage, actual_slippage, execution_time):
        """Calculate performance metrics for market order"""
        # Slippage score (lower is better)
        slippage_score = max(0, 1 - (actual_slippage / 0.01))
        
        # Latency score (lower is better)
        latency_score = max(0, 1 - (execution_time / 1000))
        
        # Adherence score (always 1.0 for market orders)
        adherence_score = 1.0
        
        # Venue score (based on execution success)
        venue_score = 1.0 if order_result['status'] == 'filled' else 0.0
        
        return {
            'slippage': slippage_score,
            'latency': latency_score,
            'adherence': adherence_score,
            'venue': venue_score,
            'expected_slippage': expected_slippage,
            'actual_slippage': actual_slippage,
            'execution_time': execution_time
        }
```

### 3. Strategy Selection Engine

```python
class StrategySelectionEngine:
    """Engine for selecting optimal execution strategy"""
    
    def __init__(self, strategies, config):
        self.strategies = strategies
        self.config = config
        self.performance_history = {}
        self.learning_rate = config.get('learning_rate', 0.01)
    
    def select_strategy(self, trading_plan, venue, execution_params):
        """Select optimal strategy for trading plan"""
        # Analyze market conditions
        market_conditions = self.analyze_market_conditions(trading_plan['symbol'], venue)
        
        # Calculate strategy scores
        strategy_scores = {}
        for strategy_name, strategy in self.strategies.items():
            score = self.calculate_strategy_score(
                strategy, trading_plan, venue, market_conditions
            )
            strategy_scores[strategy_name] = score
        
        # Select strategy with highest score
        selected_strategy = max(strategy_scores, key=strategy_scores.get)
        
        return {
            'strategy': selected_strategy,
            'strategy_scores': strategy_scores,
            'market_conditions': market_conditions
        }
    
    def calculate_strategy_score(self, strategy, trading_plan, venue, market_conditions):
        """Calculate score for specific strategy"""
        # Base performance score
        performance_score = strategy.get_performance_score()
        
        # Market condition adjustment
        condition_adjustment = self.calculate_condition_adjustment(
            strategy, market_conditions, trading_plan
        )
        
        # Learning adjustment
        learning_adjustment = self.calculate_learning_adjustment(strategy.name)
        
        # Calculate final score
        final_score = (
            performance_score * 0.5 +
            condition_adjustment * 0.3 +
            learning_adjustment * 0.2
        )
        
        return final_score
    
    def calculate_condition_adjustment(self, strategy, market_conditions, trading_plan):
        """Calculate adjustment based on market conditions"""
        # Strategy-specific condition adjustments
        if strategy.name == 'market':
            # Market orders work well in normal conditions
            return 1.0 if market_conditions['market_stress'] < 0.5 else 0.5
        elif strategy.name == 'limit':
            # Limit orders work well in volatile conditions
            return 1.0 if market_conditions['volatility'] > 0.03 else 0.7
        elif strategy.name == 'twap':
            # TWAP works well for large orders
            return 1.0 if trading_plan['position_size'] > 5000 else 0.6
        elif strategy.name == 'vwap':
            # VWAP works well for large orders with volume data
            return 1.0 if trading_plan['position_size'] > 10000 else 0.6
        else:
            return 0.5
    
    def calculate_learning_adjustment(self, strategy_name):
        """Calculate learning-based adjustment"""
        if strategy_name not in self.performance_history:
            return 0.5
        
        # Calculate recent performance
        recent_performance = self.performance_history[strategy_name][-10:]
        if not recent_performance:
            return 0.5
        
        avg_performance = np.mean(recent_performance)
        return avg_performance
    
    def update_strategy_performance(self, strategy_name, execution_result):
        """Update strategy performance based on execution result"""
        if strategy_name not in self.performance_history:
            self.performance_history[strategy_name] = []
        
        # Calculate performance score
        performance_score = execution_result['metrics'].get('total_score', 0.5)
        
        # Add to performance history
        self.performance_history[strategy_name].append(performance_score)
        
        # Keep only recent history
        if len(self.performance_history[strategy_name]) > 100:
            self.performance_history[strategy_name] = self.performance_history[strategy_name][-100:]
```

## Configuration

```yaml
execution_strategies:
  market:
    enabled: true
    max_slippage: 0.01
    max_latency_ms: 1000
    performance_weights:
      slippage: 0.4
      latency: 0.3
      adherence: 0.0
      venue: 0.3
  
  limit:
    enabled: true
    max_spread_offset: 0.5
    min_fill_probability: 0.3
    max_wait_time_minutes: 5
    performance_weights:
      slippage: 0.3
      latency: 0.2
      adherence: 0.3
      venue: 0.2
  
  twap:
    enabled: true
    min_intervals: 5
    max_intervals: 60
    interval_duration_minutes: 1
    performance_weights:
      slippage: 0.2
      latency: 0.1
      adherence: 0.4
      venue: 0.3
  
  vwap:
    enabled: true
    min_volume_data_points: 10
    max_deviation: 0.02
    performance_weights:
      slippage: 0.2
      latency: 0.1
      adherence: 0.5
      venue: 0.2
  
  adaptive:
    enabled: true
    learning_rate: 0.01
    performance_history_size: 100
    condition_weights:
      market_stress: 0.3
      volatility: 0.2
      liquidity: 0.2
      volume: 0.1
      trend_strength: 0.2
```

---

*This execution strategies build plan provides the mathematical foundations and implementation details for all execution strategies in the Trader Module, including sophisticated algorithms for market impact calculation, fill probability estimation, and adaptive strategy selection.*
