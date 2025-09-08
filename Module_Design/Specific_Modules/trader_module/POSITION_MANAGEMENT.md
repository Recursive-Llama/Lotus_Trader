# Trader Module - Position Management Build Plan

*Mathematical implementation of position tracking, risk management, and P&L calculation*

## Executive Summary

This document provides the mathematical implementation of position management for the Trader Module, including real-time position tracking, risk management, P&L calculation, and performance attribution with detailed formulas and algorithms. The position management system operates across a multi-venue ecosystem, tracking positions across centralized exchanges, decentralized protocols, and emerging venues with venue-specific intelligence.

## Mathematical Foundations

### 1. Position Tracking Mathematics

#### **Position Update Formulas**
```python
# Core position update algorithm
def update_position(position, fill_data):
    """Update position based on fill data using mathematical formulas"""
    symbol = fill_data['symbol']
    quantity = fill_data['quantity']
    price = fill_data['price']
    side = fill_data['side']
    timestamp = fill_data['timestamp']
    
    if symbol not in position:
        position[symbol] = initialize_position(symbol)
    
    if side == 'buy':
        return update_long_position(position[symbol], quantity, price, timestamp)
    else:
        return update_short_position(position[symbol], quantity, price, timestamp)

# Long position update
def update_long_position(position, quantity, price, timestamp):
    """Update long position with mathematical precision"""
    old_quantity = position['quantity']
    old_avg_price = position['avg_price']
    old_total_cost = position['total_cost']
    
    # Calculate new position values
    new_quantity = old_quantity + quantity
    new_total_cost = old_total_cost + (quantity * price)
    new_avg_price = new_total_cost / new_quantity if new_quantity > 0 else 0
    
    # Update position
    position['quantity'] = new_quantity
    position['avg_price'] = new_avg_price
    position['total_cost'] = new_total_cost
    position['last_updated'] = timestamp
    
    # Calculate position metrics
    position['position_value'] = new_quantity * price
    position['unrealized_pnl'] = calculate_unrealized_pnl(position, price)
    
    return position

# Short position update
def update_short_position(position, quantity, price, timestamp):
    """Update short position with mathematical precision"""
    old_quantity = position['quantity']
    old_avg_price = position['avg_price']
    old_total_cost = position['total_cost']
    
    if old_quantity > 0:  # Closing long position
        # Calculate realized P&L
        realized_pnl = (price - old_avg_price) * min(quantity, old_quantity)
        position['realized_pnl'] += realized_pnl
        
        # Update quantity
        new_quantity = old_quantity - quantity
        position['quantity'] = max(0, new_quantity)
        
        # Reset avg_price if position closed
        if new_quantity <= 0:
            position['avg_price'] = 0
            position['total_cost'] = 0
        else:
            # Recalculate avg_price for remaining position
            remaining_cost = old_total_cost - (old_avg_price * quantity)
            position['avg_price'] = remaining_cost / new_quantity if new_quantity > 0 else 0
            position['total_cost'] = remaining_cost
    
    else:  # Opening short position
        # Calculate new position values
        new_quantity = old_quantity - quantity
        new_total_cost = old_total_cost + (quantity * price)
        new_avg_price = new_total_cost / abs(new_quantity) if new_quantity != 0 else 0
        
        # Update position
        position['quantity'] = new_quantity
        position['avg_price'] = new_avg_price
        position['total_cost'] = new_total_cost
    
    position['last_updated'] = timestamp
    position['position_value'] = abs(new_quantity) * price
    position['unrealized_pnl'] = calculate_unrealized_pnl(position, price)
    
    return position
```

#### **P&L Calculation Formulas**
```python
# Unrealized P&L calculation
def calculate_unrealized_pnl(position, current_price):
    """Calculate unrealized P&L with mathematical precision"""
    quantity = position['quantity']
    avg_price = position['avg_price']
    
    if quantity == 0:
        return 0.0
    
    if quantity > 0:  # Long position
        unrealized_pnl = (current_price - avg_price) * quantity
    else:  # Short position
        unrealized_pnl = (avg_price - current_price) * abs(quantity)
    
    return unrealized_pnl

# Total P&L calculation
def calculate_total_pnl(position, current_price):
    """Calculate total P&L (realized + unrealized)"""
    realized_pnl = position.get('realized_pnl', 0.0)
    unrealized_pnl = calculate_unrealized_pnl(position, current_price)
    
    return realized_pnl + unrealized_pnl

# P&L percentage calculation
def calculate_pnl_percentage(position, current_price):
    """Calculate P&L as percentage of initial investment"""
    total_cost = position.get('total_cost', 0.0)
    if total_cost == 0:
        return 0.0
    
    total_pnl = calculate_total_pnl(position, current_price)
    return (total_pnl / total_cost) * 100
```

### 2. Risk Management Mathematics

#### **Value at Risk (VaR) Calculation**
```python
# VaR calculation using historical simulation
def calculate_var(position, market_data, confidence_level=0.95):
    """Calculate Value at Risk for position"""
    symbol = position['symbol']
    quantity = position['quantity']
    current_price = market_data['current_price']
    volatility = market_data['volatility']
    
    if quantity == 0:
        return 0.0
    
    # Calculate position value
    position_value = abs(quantity) * current_price
    
    # Calculate VaR using normal distribution approximation
    z_score = norm.ppf(confidence_level)
    var = position_value * volatility * z_score
    
    return var

# Portfolio VaR calculation
def calculate_portfolio_var(positions, correlation_matrix, confidence_level=0.95):
    """Calculate portfolio-level VaR"""
    if not positions:
        return 0.0
    
    # Calculate individual position VaRs
    position_vars = []
    position_values = []
    
    for position in positions:
        var = calculate_var(position, position['market_data'], confidence_level)
        position_vars.append(var)
        position_values.append(abs(position['quantity']) * position['current_price'])
    
    # Calculate portfolio variance
    portfolio_variance = 0.0
    total_value = sum(position_values)
    
    for i, pos_i in enumerate(positions):
        for j, pos_j in enumerate(positions):
            weight_i = position_values[i] / total_value
            weight_j = position_values[j] / total_value
            correlation = correlation_matrix[i][j]
            volatility_i = pos_i['market_data']['volatility']
            volatility_j = pos_j['market_data']['volatility']
            
            portfolio_variance += weight_i * weight_j * correlation * volatility_i * volatility_j
    
    # Calculate portfolio VaR
    portfolio_volatility = np.sqrt(portfolio_variance)
    z_score = norm.ppf(confidence_level)
    portfolio_var = total_value * portfolio_volatility * z_score
    
    return portfolio_var
```

#### **Maximum Drawdown Calculation**
```python
# Maximum drawdown calculation
def calculate_maximum_drawdown(pnl_series):
    """Calculate maximum drawdown from P&L series"""
    if not pnl_series:
        return 0.0
    
    # Calculate cumulative P&L
    cumulative_pnl = np.cumsum(pnl_series)
    
    # Calculate running maximum
    running_max = np.maximum.accumulate(cumulative_pnl)
    
    # Calculate drawdown
    drawdown = cumulative_pnl - running_max
    
    # Return maximum drawdown
    return abs(np.min(drawdown))

# Drawdown duration calculation
def calculate_drawdown_duration(pnl_series):
    """Calculate duration of maximum drawdown"""
    if not pnl_series:
        return 0
    
    # Calculate cumulative P&L
    cumulative_pnl = np.cumsum(pnl_series)
    
    # Calculate running maximum
    running_max = np.maximum.accumulate(cumulative_pnl)
    
    # Find drawdown periods
    drawdown = cumulative_pnl - running_max
    drawdown_periods = drawdown < 0
    
    # Calculate duration of maximum drawdown
    max_drawdown = abs(np.min(drawdown))
    max_drawdown_indices = np.where(drawdown == -max_drawdown)[0]
    
    if len(max_drawdown_indices) == 0:
        return 0
    
    # Find start and end of maximum drawdown period
    max_drawdown_start = max_drawdown_indices[0]
    max_drawdown_end = max_drawdown_indices[-1]
    
    return max_drawdown_end - max_drawdown_start + 1
```

### 3. Performance Attribution Mathematics

#### **Performance Attribution Formulas**
```python
# Performance attribution by signal
def calculate_signal_attribution(execution_results, signal_performance):
    """Calculate performance attribution by signal source"""
    attribution = {}
    
    for result in execution_results:
        signal_id = result['signal_id']
        pnl = result['pnl']
        
        if signal_id not in attribution:
            attribution[signal_id] = {
                'total_pnl': 0.0,
                'total_quantity': 0.0,
                'num_trades': 0,
                'avg_pnl_per_trade': 0.0
            }
        
        attribution[signal_id]['total_pnl'] += pnl
        attribution[signal_id]['total_quantity'] += result['quantity']
        attribution[signal_id]['num_trades'] += 1
    
    # Calculate average P&L per trade
    for signal_id in attribution:
        if attribution[signal_id]['num_trades'] > 0:
            attribution[signal_id]['avg_pnl_per_trade'] = (
                attribution[signal_id]['total_pnl'] / 
                attribution[signal_id]['num_trades']
            )
    
    return attribution

# Performance attribution by venue
def calculate_venue_attribution(execution_results):
    """Calculate performance attribution by execution venue"""
    venue_attribution = {}
    
    for result in execution_results:
        venue = result['venue']
        pnl = result['pnl']
        slippage = result['slippage']
        latency = result['latency']
        
        if venue not in venue_attribution:
            venue_attribution[venue] = {
                'total_pnl': 0.0,
                'total_slippage': 0.0,
                'total_latency': 0.0,
                'num_trades': 0,
                'avg_pnl_per_trade': 0.0,
                'avg_slippage': 0.0,
                'avg_latency': 0.0
            }
        
        venue_attribution[venue]['total_pnl'] += pnl
        venue_attribution[venue]['total_slippage'] += slippage
        venue_attribution[venue]['total_latency'] += latency
        venue_attribution[venue]['num_trades'] += 1
    
    # Calculate averages
    for venue in venue_attribution:
        if venue_attribution[venue]['num_trades'] > 0:
            venue_attribution[venue]['avg_pnl_per_trade'] = (
                venue_attribution[venue]['total_pnl'] / 
                venue_attribution[venue]['num_trades']
            )
            venue_attribution[venue]['avg_slippage'] = (
                venue_attribution[venue]['total_slippage'] / 
                venue_attribution[venue]['num_trades']
            )
            venue_attribution[venue]['avg_latency'] = (
                venue_attribution[venue]['total_latency'] / 
                venue_attribution[venue]['num_trades']
            )
    
    return venue_attribution
```

#### **Sharpe Ratio Calculation**
```python
# Sharpe ratio calculation
def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """Calculate Sharpe ratio for returns series"""
    if len(returns) < 2:
        return 0.0
    
    # Calculate excess returns
    excess_returns = returns - risk_free_rate
    
    # Calculate Sharpe ratio
    mean_return = np.mean(excess_returns)
    std_return = np.std(excess_returns)
    
    if std_return == 0:
        return 0.0
    
    sharpe_ratio = mean_return / std_return
    
    return sharpe_ratio

# Information ratio calculation
def calculate_information_ratio(returns, benchmark_returns):
    """Calculate information ratio vs benchmark"""
    if len(returns) != len(benchmark_returns):
        return 0.0
    
    # Calculate active returns
    active_returns = returns - benchmark_returns
    
    # Calculate information ratio
    mean_active_return = np.mean(active_returns)
    std_active_return = np.std(active_returns)
    
    if std_active_return == 0:
        return 0.0
    
    information_ratio = mean_active_return / std_active_return
    
    return information_ratio
```

## Implementation Classes

### 1. Multi-Venue Position Tracker

```python
class MultiVenuePositionTracker:
    """Mathematical position tracking system across multi-venue ecosystem"""
    
    def __init__(self, config):
        self.config = config
        self.positions = {}  # symbol -> position data
        self.venue_positions = {}  # venue -> symbol -> position data
        self.position_history = []
        self.performance_metrics = {}
        self.venue_performance = {}  # venue -> performance data
        self.cross_venue_arbitrage = CrossVenueArbitrageTracker()
        self.liquidity_aggregator = LiquidityAggregator()
    
    def update_position(self, fill_data):
        """Update position based on fill data across multi-venue ecosystem"""
        symbol = fill_data['symbol']
        venue = fill_data['venue']
        venue_type = fill_data.get('venue_type', 'unknown')
        
        # Initialize symbol position if needed
        if symbol not in self.positions:
            self.positions[symbol] = self._initialize_position(symbol)
        
        # Initialize venue position if needed
        if venue not in self.venue_positions:
            self.venue_positions[venue] = {}
        if symbol not in self.venue_positions[venue]:
            self.venue_positions[venue][symbol] = self._initialize_position(symbol)
        
        # Update global position
        self.positions[symbol] = self._update_position_math(
            self.positions[symbol], fill_data
        )
        
        # Update venue-specific position
        self.venue_positions[venue][symbol] = self._update_position_math(
            self.venue_positions[venue][symbol], fill_data
        )
        
        # Update venue performance
        self._update_venue_performance(venue, fill_data)
        
        # Check for cross-venue arbitrage opportunities
        self._check_cross_venue_arbitrage(symbol, fill_data)
        
        # Update performance metrics
        self._update_performance_metrics(symbol)
        
        # Add to history
        self.position_history.append({
            'timestamp': fill_data['timestamp'],
            'symbol': symbol,
            'venue': venue,
            'venue_type': venue_type,
            'action': fill_data['side'],
            'quantity': fill_data['quantity'],
            'price': fill_data['price'],
            'position_after': self.positions[symbol].copy(),
            'venue_position_after': self.venue_positions[venue][symbol].copy()
        })
    
    def _check_cross_venue_arbitrage(self, symbol, fill_data):
        """Check for cross-venue arbitrage opportunities"""
        # Get current prices across all venues
        venue_prices = {}
        for venue, positions in self.venue_positions.items():
            if symbol in positions and positions[symbol]['quantity'] != 0:
                # Get current price from venue
                current_price = self._get_venue_price(symbol, venue)
                venue_prices[venue] = current_price
        
        # Check for arbitrage opportunities
        if len(venue_prices) >= 2:
            arbitrage_opportunities = self.cross_venue_arbitrage.detect_opportunities(
                symbol, venue_prices, fill_data
            )
            
            if arbitrage_opportunities:
                self._log_arbitrage_opportunities(symbol, arbitrage_opportunities)
    
    def get_aggregated_position(self, symbol):
        """Get aggregated position across all venues"""
        if symbol not in self.positions:
            return None
        
        # Calculate aggregated position across venues
        total_quantity = 0
        total_cost = 0
        total_realized_pnl = 0
        
        for venue, positions in self.venue_positions.items():
            if symbol in positions:
                position = positions[symbol]
                total_quantity += position['quantity']
                total_cost += position['total_cost']
                total_realized_pnl += position['realized_pnl']
        
        # Calculate weighted average price
        avg_price = total_cost / total_quantity if total_quantity != 0 else 0
        
        return {
            'symbol': symbol,
            'total_quantity': total_quantity,
            'avg_price': avg_price,
            'total_cost': total_cost,
            'realized_pnl': total_realized_pnl,
            'venue_breakdown': self._get_venue_breakdown(symbol)
        }
    
    def _get_venue_breakdown(self, symbol):
        """Get position breakdown by venue"""
        breakdown = {}
        
        for venue, positions in self.venue_positions.items():
            if symbol in positions:
                position = positions[symbol]
                breakdown[venue] = {
                    'quantity': position['quantity'],
                    'avg_price': position['avg_price'],
                    'realized_pnl': position['realized_pnl'],
                    'position_value': abs(position['quantity']) * position.get('current_price', 0)
                }
        
        return breakdown
    
    def _initialize_position(self, symbol):
        """Initialize new position"""
        return {
            'symbol': symbol,
            'quantity': 0.0,
            'avg_price': 0.0,
            'total_cost': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'position_value': 0.0,
            'last_updated': None,
            'num_trades': 0,
            'total_volume': 0.0
        }
    
    def _update_position_math(self, position, fill_data):
        """Update position using mathematical formulas"""
        quantity = fill_data['quantity']
        price = fill_data['price']
        side = fill_data['side']
        timestamp = fill_data['timestamp']
        
        if side == 'buy':
            return self._update_long_position(position, quantity, price, timestamp)
        else:
            return self._update_short_position(position, quantity, price, timestamp)
    
    def _update_long_position(self, position, quantity, price, timestamp):
        """Update long position with mathematical precision"""
        old_quantity = position['quantity']
        old_avg_price = position['avg_price']
        old_total_cost = position['total_cost']
        
        # Calculate new position values
        new_quantity = old_quantity + quantity
        new_total_cost = old_total_cost + (quantity * price)
        new_avg_price = new_total_cost / new_quantity if new_quantity > 0 else 0
        
        # Update position
        position['quantity'] = new_quantity
        position['avg_price'] = new_avg_price
        position['total_cost'] = new_total_cost
        position['last_updated'] = timestamp
        position['num_trades'] += 1
        position['total_volume'] += quantity
        
        return position
    
    def _update_short_position(self, position, quantity, price, timestamp):
        """Update short position with mathematical precision"""
        old_quantity = position['quantity']
        old_avg_price = position['avg_price']
        old_total_cost = position['total_cost']
        
        if old_quantity > 0:  # Closing long position
            # Calculate realized P&L
            realized_pnl = (price - old_avg_price) * min(quantity, old_quantity)
            position['realized_pnl'] += realized_pnl
            
            # Update quantity
            new_quantity = old_quantity - quantity
            position['quantity'] = max(0, new_quantity)
            
            # Reset avg_price if position closed
            if new_quantity <= 0:
                position['avg_price'] = 0
                position['total_cost'] = 0
            else:
                # Recalculate avg_price for remaining position
                remaining_cost = old_total_cost - (old_avg_price * quantity)
                position['avg_price'] = remaining_cost / new_quantity if new_quantity > 0 else 0
                position['total_cost'] = remaining_cost
        
        else:  # Opening short position
            # Calculate new position values
            new_quantity = old_quantity - quantity
            new_total_cost = old_total_cost + (quantity * price)
            new_avg_price = new_total_cost / abs(new_quantity) if new_quantity != 0 else 0
            
            # Update position
            position['quantity'] = new_quantity
            position['avg_price'] = new_avg_price
            position['total_cost'] = new_total_cost
        
        position['last_updated'] = timestamp
        position['num_trades'] += 1
        position['total_volume'] += quantity
        
        return position
    
    def calculate_unrealized_pnl(self, symbol, current_price):
        """Calculate unrealized P&L for position"""
        if symbol not in self.positions:
            return 0.0
        
        position = self.positions[symbol]
        quantity = position['quantity']
        avg_price = position['avg_price']
        
        if quantity == 0:
            return 0.0
        
        if quantity > 0:  # Long position
            unrealized_pnl = (current_price - avg_price) * quantity
        else:  # Short position
            unrealized_pnl = (avg_price - current_price) * abs(quantity)
        
        return unrealized_pnl
    
    def get_position_summary(self, symbol, current_price):
        """Get comprehensive position summary"""
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        unrealized_pnl = self.calculate_unrealized_pnl(symbol, current_price)
        total_pnl = position['realized_pnl'] + unrealized_pnl
        
        return {
            'symbol': symbol,
            'quantity': position['quantity'],
            'avg_price': position['avg_price'],
            'current_price': current_price,
            'position_value': abs(position['quantity']) * current_price,
            'realized_pnl': position['realized_pnl'],
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': total_pnl,
            'num_trades': position['num_trades'],
            'total_volume': position['total_volume'],
            'last_updated': position['last_updated']
        }
```

### 2. Risk Manager

```python
class RiskManager:
    """Mathematical risk management system"""
    
    def __init__(self, config):
        self.config = config
        self.risk_limits = config.get('risk_limits', {})
        self.var_confidence = config.get('var_confidence', 0.95)
        self.max_drawdown_limit = config.get('max_drawdown_limit', 0.1)
        self.concentration_limit = config.get('concentration_limit', 0.2)
    
    def check_position_risk(self, position, market_data):
        """Check position-level risk limits"""
        risk_checks = {}
        
        # Check position size limit
        position_value = abs(position['quantity']) * market_data['current_price']
        max_position_value = self.risk_limits.get('max_position_value', 100000)
        risk_checks['position_size'] = {
            'value': position_value,
            'limit': max_position_value,
            'breach': position_value > max_position_value
        }
        
        # Check VaR limit
        var = calculate_var(position, market_data, self.var_confidence)
        max_var = self.risk_limits.get('max_var', 5000)
        risk_checks['var'] = {
            'value': var,
            'limit': max_var,
            'breach': var > max_var
        }
        
        # Check concentration limit
        total_portfolio_value = self._calculate_total_portfolio_value()
        concentration = position_value / total_portfolio_value if total_portfolio_value > 0 else 0
        risk_checks['concentration'] = {
            'value': concentration,
            'limit': self.concentration_limit,
            'breach': concentration > self.concentration_limit
        }
        
        return risk_checks
    
    def check_portfolio_risk(self, positions, correlation_matrix):
        """Check portfolio-level risk limits"""
        risk_checks = {}
        
        # Check portfolio VaR
        portfolio_var = calculate_portfolio_var(positions, correlation_matrix, self.var_confidence)
        max_portfolio_var = self.risk_limits.get('max_portfolio_var', 20000)
        risk_checks['portfolio_var'] = {
            'value': portfolio_var,
            'limit': max_portfolio_var,
            'breach': portfolio_var > max_portfolio_var
        }
        
        # Check maximum drawdown
        pnl_series = self._get_pnl_series()
        max_drawdown = calculate_maximum_drawdown(pnl_series)
        risk_checks['max_drawdown'] = {
            'value': max_drawdown,
            'limit': self.max_drawdown_limit,
            'breach': max_drawdown > self.max_drawdown_limit
        }
        
        # Check correlation risk
        correlation_risk = self._calculate_correlation_risk(positions, correlation_matrix)
        max_correlation_risk = self.risk_limits.get('max_correlation_risk', 0.8)
        risk_checks['correlation_risk'] = {
            'value': correlation_risk,
            'limit': max_correlation_risk,
            'breach': correlation_risk > max_correlation_risk
        }
        
        return risk_checks
    
    def _calculate_total_portfolio_value(self):
        """Calculate total portfolio value"""
        total_value = 0.0
        for position in self.positions.values():
            if position['quantity'] != 0:
                # This would need current price from market data
                # For now, use avg_price as approximation
                total_value += abs(position['quantity']) * position['avg_price']
        return total_value
    
    def _calculate_correlation_risk(self, positions, correlation_matrix):
        """Calculate correlation risk in portfolio"""
        if len(positions) < 2:
            return 0.0
        
        # Calculate weighted average correlation
        position_values = [abs(pos['quantity']) * pos['current_price'] for pos in positions]
        total_value = sum(position_values)
        
        weighted_correlation = 0.0
        for i, pos_i in enumerate(positions):
            for j, pos_j in enumerate(positions):
                if i != j:
                    weight_i = position_values[i] / total_value
                    weight_j = position_values[j] / total_value
                    correlation = correlation_matrix[i][j]
                    weighted_correlation += weight_i * weight_j * correlation
        
        return weighted_correlation
```

### 3. Performance Tracker

```python
class PerformanceTracker:
    """Mathematical performance tracking system"""
    
    def __init__(self, config):
        self.config = config
        self.performance_history = []
        self.attribution_data = {}
        self.benchmark_data = []
    
    def track_execution_performance(self, execution_result):
        """Track execution performance metrics"""
        performance_metrics = {
            'timestamp': execution_result['timestamp'],
            'symbol': execution_result['symbol'],
            'signal_id': execution_result['signal_id'],
            'venue': execution_result['venue'],
            'strategy': execution_result['strategy'],
            'quantity': execution_result['quantity'],
            'price': execution_result['price'],
            'slippage': execution_result['slippage'],
            'latency': execution_result['latency'],
            'execution_score': execution_result['execution_score'],
            'pnl': execution_result.get('pnl', 0.0)
        }
        
        self.performance_history.append(performance_metrics)
        
        # Update attribution data
        self._update_attribution_data(performance_metrics)
    
    def calculate_performance_metrics(self, time_period=None):
        """Calculate comprehensive performance metrics"""
        if time_period:
            filtered_history = self._filter_by_time_period(time_period)
        else:
            filtered_history = self.performance_history
        
        if not filtered_history:
            return {}
        
        # Calculate basic metrics
        total_pnl = sum(metric['pnl'] for metric in filtered_history)
        total_trades = len(filtered_history)
        avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0
        
        # Calculate execution quality metrics
        avg_slippage = np.mean([metric['slippage'] for metric in filtered_history])
        avg_latency = np.mean([metric['latency'] for metric in filtered_history])
        avg_execution_score = np.mean([metric['execution_score'] for metric in filtered_history])
        
        # Calculate risk metrics
        pnl_series = [metric['pnl'] for metric in filtered_history]
        volatility = np.std(pnl_series) if len(pnl_series) > 1 else 0
        sharpe_ratio = calculate_sharpe_ratio(pnl_series)
        max_drawdown = calculate_maximum_drawdown(pnl_series)
        
        # Calculate win rate
        winning_trades = sum(1 for metric in filtered_history if metric['pnl'] > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'avg_pnl_per_trade': avg_pnl_per_trade,
            'avg_slippage': avg_slippage,
            'avg_latency': avg_latency,
            'avg_execution_score': avg_execution_score,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate
        }
    
    def calculate_attribution_analysis(self):
        """Calculate performance attribution analysis"""
        attribution = {}
        
        # Attribution by signal
        signal_attribution = calculate_signal_attribution(
            self.performance_history, {}
        )
        
        # Attribution by venue
        venue_attribution = calculate_venue_attribution(
            self.performance_history
        )
        
        # Attribution by strategy
        strategy_attribution = self._calculate_strategy_attribution()
        
        return {
            'signal_attribution': signal_attribution,
            'venue_attribution': venue_attribution,
            'strategy_attribution': strategy_attribution
        }
    
    def _calculate_strategy_attribution(self):
        """Calculate performance attribution by strategy"""
        strategy_attribution = {}
        
        for metric in self.performance_history:
            strategy = metric['strategy']
            pnl = metric['pnl']
            
            if strategy not in strategy_attribution:
                strategy_attribution[strategy] = {
                    'total_pnl': 0.0,
                    'num_trades': 0,
                    'avg_pnl_per_trade': 0.0
                }
            
            strategy_attribution[strategy]['total_pnl'] += pnl
            strategy_attribution[strategy]['num_trades'] += 1
        
        # Calculate averages
        for strategy in strategy_attribution:
            if strategy_attribution[strategy]['num_trades'] > 0:
                strategy_attribution[strategy]['avg_pnl_per_trade'] = (
                    strategy_attribution[strategy]['total_pnl'] / 
                    strategy_attribution[strategy]['num_trades']
                )
        
        return strategy_attribution
```

## Database Schema

### Position Management Tables

```sql
-- Position tracking
CREATE TABLE trader_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    avg_price DECIMAL(20,8) NOT NULL,
    total_cost DECIMAL(20,8) DEFAULT 0,
    realized_pnl DECIMAL(20,8) DEFAULT 0,
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    position_value DECIMAL(20,8) DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Risk metrics
    var_95 DECIMAL(20,8),
    max_loss DECIMAL(20,8),
    concentration_ratio DECIMAL(5,4),
    
    INDEX idx_trader_positions_symbol (symbol),
    INDEX idx_trader_positions_updated (last_updated)
);

-- Position history
CREATE TABLE trader_position_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID REFERENCES trader_positions(id),
    action VARCHAR(10) NOT NULL, -- 'buy', 'sell'
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    realized_pnl DECIMAL(20,8),
    unrealized_pnl DECIMAL(20,8),
    position_after JSONB,
    
    INDEX idx_trader_position_history_position (position_id),
    INDEX idx_trader_position_history_timestamp (timestamp)
);

-- Performance tracking
CREATE TABLE trader_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    signal_id UUID,
    venue VARCHAR(50) NOT NULL,
    strategy VARCHAR(20) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    slippage DECIMAL(8,4),
    latency_ms INTEGER,
    execution_score DECIMAL(3,2),
    pnl DECIMAL(20,8),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_trader_performance_symbol (symbol),
    INDEX idx_trader_performance_signal (signal_id),
    INDEX idx_trader_performance_venue (venue),
    INDEX idx_trader_performance_strategy (strategy),
    INDEX idx_trader_performance_timestamp (timestamp)
);

-- Risk metrics
CREATE TABLE trader_risk_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    portfolio_var DECIMAL(20,8),
    max_drawdown DECIMAL(8,4),
    concentration_risk DECIMAL(5,4),
    correlation_risk DECIMAL(5,4),
    volatility DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    
    INDEX idx_trader_risk_metrics_timestamp (timestamp)
);
```

## Configuration

```yaml
position_management:
  risk_limits:
    max_position_value: 100000
    max_var: 5000
    max_portfolio_var: 20000
    max_drawdown_limit: 0.1
    concentration_limit: 0.2
    max_correlation_risk: 0.8
  
  var_calculation:
    confidence_level: 0.95
    lookback_days: 252
    method: "historical_simulation"
  
  performance_tracking:
    history_size: 10000
    attribution_enabled: true
    benchmark_enabled: true
    benchmark_symbol: "SPY"
  
  position_tracking:
    real_time_updates: true
    history_retention_days: 365
    pnl_calculation_frequency: "1m"
```

---

*This position management build plan provides the mathematical foundations and implementation details for comprehensive position tracking, risk management, and performance attribution in the Trader Module.*
