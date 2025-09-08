# Trader Module - Core Architecture Build Plan

*Mathematical foundations and core implementation for the Trader Module*

## Executive Summary

This document provides the mathematical foundations and core architecture for the Trader Module, incorporating the sophisticated mathematical formulas from the existing system while building a comprehensive execution engine. The Trader Module functions as a self-contained "garden" that provides tools for connecting to data sources and exchanges, enabling LLM-driven trading decisions across multiple venues.

## Mathematical Foundations

### 1. Execution Quality Metrics

#### **Execution Score Formula**
```python
# Core execution quality score
execution_score = w_slippage * (1 - slippage_penalty) + 
                  w_latency * (1 - latency_penalty) + 
                  w_adherence * adherence_score + 
                  w_venue * venue_score

# Where:
slippage_penalty = min(1.0, |actual_price - expected_price| / expected_price)
latency_penalty = min(1.0, execution_latency_ms / max_latency_ms)
adherence_score = 1.0 - |actual_size - expected_size| / expected_size
venue_score = venue_performance_score
```

#### **Slippage Calculation**
```python
# Market impact and slippage calculation
def calculate_slippage(execution_data):
    """Calculate slippage vs expected price"""
    expected_price = execution_data['expected_price']
    actual_price = execution_data['actual_price']
    side = execution_data['side']
    
    if side == 'buy':
        slippage = (actual_price - expected_price) / expected_price
    else:  # sell
        slippage = (expected_price - actual_price) / expected_price
    
    return slippage

# Market impact model
def calculate_market_impact(order_size, market_depth, volatility):
    """Calculate expected market impact"""
    # Almgren-Chriss model simplified
    impact = (order_size / market_depth) * volatility * 0.1
    return impact
```

#### **Latency Measurement**
```python
# Execution latency calculation
def calculate_latency(order_time, fill_time, network_latency=0):
    """Calculate total execution latency"""
    execution_latency = (fill_time - order_time).total_seconds() * 1000  # ms
    total_latency = execution_latency + network_latency
    return total_latency

# Latency penalty function
def latency_penalty(latency_ms, max_latency_ms=1000):
    """Calculate latency penalty score"""
    if latency_ms <= max_latency_ms:
        return 0.0
    else:
        return min(1.0, (latency_ms - max_latency_ms) / max_latency_ms)
```

### 2. Trading Tools Architecture

#### **Database-Driven Tool Architecture**
```python
# Database-driven tool system using strands and intelligence layer
class DatabaseDrivenTradingTools:
    """Tools that use database intelligence and strands for trading decisions"""
    
    def __init__(self, db_connection, intelligence_layer):
        self.db = db_connection
        self.intelligence = intelligence_layer
        
        # Simple tool registry - easy to add new tools
        self.tools = {
            # Exchange tools
            'hyperliquid': HyperliquidTool(self.db),
            'binance': BinanceTool(self.db),
            'coinbase': CoinbaseTool(self.db),
            'raydium': RaydiumTool(self.db),
            'uniswap': UniswapTool(self.db),
            'jupiter': JupiterTool(self.db),
            
            # Data source tools
            'coingecko': CoinGeckoTool(self.db),
            'defi_llama': DeFiLlamaTool(self.db),
            'dune': DuneTool(self.db),
            'the_graph': TheGraphTool(self.db),
            
            # Intelligence tools (these are the key ones!)
            'liquidity_aggregator': LiquidityAggregationTool(self.db),
            'venue_optimizer': VenueOptimizationTool(self.db),
            'arbitrage_detector': ArbitrageDetectionTool(self.db),
            'strand_analyzer': StrandAnalysisTool(self.db),
            'regime_detector': RegimeDetectionTool(self.db)
        }
    
    def get_available_tools(self):
        """Get available tools with descriptions for LLM"""
        return {
            tool_name: {
                'description': tool.get_description(),
                'capabilities': tool.get_capabilities(),
                'requires': tool.get_requirements()
            }
            for tool_name, tool in self.tools.items()
        }
    
    def execute_tool(self, tool_name, action, **kwargs):
        """Execute tool with database intelligence"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not available")
        
        tool = self.tools[tool_name]
        
        # All tools get access to database and intelligence layer
        return tool.execute(action, db=self.db, intelligence=self.intelligence, **kwargs)
    
    def get_strand_context(self, symbol, timeframe='1h', limit=100):
        """Get relevant strands for context"""
        return self.db.query("""
            SELECT * FROM tr_strand 
            WHERE symbol = %s AND timeframe = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (symbol, timeframe, limit))
    
    def get_intelligence_context(self, symbol, context_type='trading'):
        """Get intelligence layer context for symbol"""
        return self.intelligence.get_context(symbol, context_type)
```

#### **Intelligence-Powered Tools**
```python
class LiquidityAggregationTool:
    """Tool for aggregating liquidity across venues using database intelligence"""
    
    def __init__(self, db):
        self.db = db
    
    def get_description(self):
        return "Aggregate liquidity across multiple venues and chains"
    
    def get_capabilities(self):
        return ["cross_venue_liquidity", "best_execution_venue", "liquidity_ranking"]
    
    def execute(self, action, db, intelligence, **kwargs):
        if action == "aggregate_liquidity":
            return self._aggregate_liquidity(db, intelligence, **kwargs)
        elif action == "find_best_venue":
            return self._find_best_venue(db, intelligence, **kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def _aggregate_liquidity(self, db, intelligence, symbol, order_size, side):
        """Aggregate liquidity using database intelligence"""
        # Query recent liquidity data from strands
        liquidity_data = db.query("""
            SELECT venue, tr_predict->>'fill_prob' as fill_prob,
                   tr_predict->>'slip_bps' as slip_bps,
                   exec_metrics->>'slip_real_bps' as real_slip
            FROM tr_strand 
            WHERE symbol = %s 
            AND created_at > NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
        """, (symbol,))
        
        # Use intelligence layer to analyze patterns
        intelligence_analysis = intelligence.analyze_liquidity_patterns(
            symbol, liquidity_data
        )
        
        # Aggregate across venues
        venue_liquidity = {}
        for row in liquidity_data:
            venue = row['venue']
            if venue not in venue_liquidity:
                venue_liquidity[venue] = {
                    'total_liquidity': 0,
                    'avg_slippage': 0,
                    'fill_probability': 0,
                    'intelligence_score': 0
                }
            
            # Aggregate metrics
            venue_liquidity[venue]['total_liquidity'] += order_size
            venue_liquidity[venue]['avg_slippage'] += float(row['slip_bps'] or 0)
            venue_liquidity[venue]['fill_probability'] += float(row['fill_prob'] or 0)
        
        # Apply intelligence layer insights
        for venue, data in venue_liquidity.items():
            data['intelligence_score'] = intelligence_analysis.get(venue, {}).get('score', 0.5)
            data['avg_slippage'] /= len([r for r in liquidity_data if r['venue'] == venue])
            data['fill_probability'] /= len([r for r in liquidity_data if r['venue'] == venue])
        
        return venue_liquidity

class VenueOptimizationTool:
    """Tool for optimizing venue selection using historical performance"""
    
    def __init__(self, db):
        self.db = db
    
    def get_description(self):
        return "Optimize venue selection based on historical performance and intelligence"
    
    def execute(self, action, db, intelligence, **kwargs):
        if action == "optimize_venue":
            return self._optimize_venue(db, intelligence, **kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def _optimize_venue(self, db, intelligence, symbol, order_size, side):
        """Optimize venue selection using database intelligence"""
        # Query historical performance from strands
        performance_data = db.query("""
            SELECT venue, 
                   AVG((exec_metrics->>'slip_real_bps')::float) as avg_slippage,
                   AVG((tr_predict->>'latency_ms')::float) as avg_latency,
                   COUNT(*) as trade_count,
                   AVG(CASE WHEN (exec_metrics->>'slip_real_bps')::float < 10 THEN 1 ELSE 0 END) as success_rate
            FROM tr_strand 
            WHERE symbol = %s 
            AND created_at > NOW() - INTERVAL '7 days'
            GROUP BY venue
        """, (symbol,))
        
        # Use intelligence layer for venue scoring
        venue_scores = {}
        for row in performance_data:
            venue = row['venue']
            score = intelligence.calculate_venue_score(
                venue, row['avg_slippage'], row['avg_latency'], 
                row['success_rate'], row['trade_count']
            )
            venue_scores[venue] = score
        
        # Return optimized venue recommendation
        best_venue = max(venue_scores, key=venue_scores.get) if venue_scores else None
        
        return {
            'recommended_venue': best_venue,
            'venue_scores': venue_scores,
            'confidence': venue_scores.get(best_venue, 0) if best_venue else 0
        }
```

#### **Simple Tool Interface for LLM**
```python
# Simple tool interface that LLM can use
class LLMTradingInterface:
    """Simple interface for LLM to access trading tools"""
    
    def __init__(self, trading_tools):
        self.tools = trading_tools
    
    def get_tool_descriptions(self):
        """Get tool descriptions for LLM"""
        return {
            'exchanges': {
                'hyperliquid': 'Connect to Hyperliquid exchange for trading',
                'binance': 'Connect to Binance exchange for trading', 
                'coinbase': 'Connect to Coinbase exchange for trading',
                'raydium': 'Connect to Raydium DEX on Solana',
                'uniswap': 'Connect to Uniswap DEX on Ethereum',
                'jupiter': 'Connect to Jupiter aggregator on Solana'
            },
            'data_sources': {
                'coingecko': 'Get price data from CoinGecko',
                'defi_llama': 'Get DeFi data from DeFiLlama',
                'dune': 'Query on-chain data from Dune Analytics',
                'the_graph': 'Query blockchain data from The Graph'
            }
        }
    
    def execute_tool(self, tool_name, action, **kwargs):
        """Execute a tool action"""
        if tool_name in self.tools.exchange_tools:
            return self.tools.exchange_tools[tool_name].execute(action, **kwargs)
        elif tool_name in self.tools.data_tools:
            return self.tools.data_tools[tool_name].execute(action, **kwargs)
        else:
            raise ValueError(f"Tool {tool_name} not found")
    
    def get_market_info(self, symbol):
        """Get market information for symbol"""
        # LLM can choose which data source to use
        return {
            'price': self.tools.data_tools['coingecko'].get_price(symbol),
            'volume': self.tools.data_tools['coingecko'].get_volume(symbol),
            'liquidity': self.tools.data_tools['defi_llama'].get_liquidity(symbol)
        }
    
    def check_exchange_availability(self, symbol):
        """Check which exchanges have the symbol"""
        available = {}
        for exchange_name, exchange_tool in self.tools.exchange_tools.items():
            try:
                available[exchange_name] = exchange_tool.has_symbol(symbol)
            except:
                available[exchange_name] = False
        return available
```

### 3. Position Management Mathematics

#### **Position Tracking Formulas**
```python
# Position update formulas
def update_position(position, fill_data):
    """Update position based on fill data"""
    symbol = fill_data['symbol']
    quantity = fill_data['quantity']
    price = fill_data['price']
    side = fill_data['side']
    
    if symbol not in position:
        position[symbol] = {
            'quantity': 0.0,
            'avg_price': 0.0,
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0,
            'total_cost': 0.0
        }
    
    if side == 'buy':
        # Add to position
        old_quantity = position[symbol]['quantity']
        old_avg_price = position[symbol]['avg_price']
        old_total_cost = position[symbol]['total_cost']
        
        new_quantity = old_quantity + quantity
        new_total_cost = old_total_cost + (quantity * price)
        new_avg_price = new_total_cost / new_quantity if new_quantity > 0 else 0
        
        position[symbol]['quantity'] = new_quantity
        position[symbol]['avg_price'] = new_avg_price
        position[symbol]['total_cost'] = new_total_cost
        
    else:  # sell
        # Reduce position
        old_quantity = position[symbol]['quantity']
        old_avg_price = position[symbol]['avg_price']
        
        # Calculate realized P&L
        realized_pnl = (price - old_avg_price) * min(quantity, old_quantity)
        position[symbol]['realized_pnl'] += realized_pnl
        
        # Update quantity
        new_quantity = old_quantity - quantity
        position[symbol]['quantity'] = max(0, new_quantity)
        
        # If position closed, reset avg_price
        if new_quantity <= 0:
            position[symbol]['avg_price'] = 0.0
            position[symbol]['total_cost'] = 0.0
    
    return position

# Unrealized P&L calculation
def calculate_unrealized_pnl(position, current_price):
    """Calculate unrealized P&L for position"""
    if position['quantity'] == 0:
        return 0.0
    
    if position['quantity'] > 0:  # Long position
        return (current_price - position['avg_price']) * position['quantity']
    else:  # Short position
        return (position['avg_price'] - current_price) * abs(position['quantity'])
```

### 4. Risk Management Mathematics

#### **Position Risk Calculation**
```python
# Position risk assessment
def calculate_position_risk(position, market_data, risk_params):
    """Calculate position risk metrics"""
    symbol = position['symbol']
    quantity = position['quantity']
    avg_price = position['avg_price']
    current_price = market_data['current_price']
    volatility = market_data['volatility']
    
    # Value at Risk (VaR) calculation
    position_value = abs(quantity) * current_price
    var_95 = position_value * volatility * 1.645  # 95% VaR
    
    # Maximum loss calculation
    if quantity > 0:  # Long position
        max_loss = position_value - (quantity * avg_price)
    else:  # Short position
        max_loss = (quantity * avg_price) - position_value
    
    # Risk-adjusted return
    expected_return = calculate_expected_return(position, market_data)
    risk_adjusted_return = expected_return / (volatility + 1e-10)
    
    return {
        'position_value': position_value,
        'var_95': var_95,
        'max_loss': max_loss,
        'risk_adjusted_return': risk_adjusted_return,
        'volatility': volatility
    }

# Portfolio risk calculation
def calculate_portfolio_risk(positions, correlation_matrix):
    """Calculate portfolio-level risk"""
    position_values = [pos['quantity'] * pos['current_price'] for pos in positions]
    portfolio_value = sum(position_values)
    
    # Portfolio variance calculation
    portfolio_variance = 0.0
    for i, pos_i in enumerate(positions):
        for j, pos_j in enumerate(positions):
            weight_i = position_values[i] / portfolio_value
            weight_j = position_values[j] / portfolio_value
            correlation = correlation_matrix[i][j]
            volatility_i = pos_i['volatility']
            volatility_j = pos_j['volatility']
            
            portfolio_variance += weight_i * weight_j * correlation * volatility_i * volatility_j
    
    portfolio_volatility = np.sqrt(portfolio_variance)
    portfolio_var = portfolio_value * portfolio_volatility * 1.645
    
    return {
        'portfolio_value': portfolio_value,
        'portfolio_volatility': portfolio_volatility,
        'portfolio_var': portfolio_var,
        'concentration_risk': max(position_values) / portfolio_value
    }
```

## Core Architecture Implementation

### 1. Trader Module Core Class

```python
class TraderModule:
    """Core Trader Module with tool-based trading capabilities"""
    
    def __init__(self, config):
        self.config = config
        self.trading_tools = TradingTools()
        self.llm_interface = LLMTradingInterface(self.trading_tools)
        self.position_tracker = PositionTracker()
        self.risk_manager = RiskManager(config)
        self.execution_engine = ExecutionEngine(config)
        self.performance_tracker = PerformanceTracker()
        
        # Simple execution parameters
        self.execution_weights = {
            'slippage': 0.3,
            'latency': 0.2,
            'adherence': 0.3,
            'venue': 0.2
        }
    
    def get_available_tools(self):
        """Get available trading tools for LLM"""
        return self.llm_interface.get_tool_descriptions()
    
    def execute_llm_command(self, command, **kwargs):
        """Execute LLM trading command using tools"""
        return self.llm_interface.execute_tool(command, **kwargs)
    
    def execute_trading_plan(self, trading_plan):
        """Execute trading plan using available tools"""
        # 1. Validate trading plan
        validation_result = self._validate_trading_plan(trading_plan)
        if not validation_result['valid']:
            return self._create_execution_result('rejected', validation_result)
        
        # 2. Get market data using tools
        market_data = self.llm_interface.get_market_info(trading_plan['symbol'])
        
        # 3. Check available exchanges
        available_exchanges = self.llm_interface.check_exchange_availability(trading_plan['symbol'])
        
        # 4. Execute using selected exchange (LLM can choose)
        execution_result = self._execute_with_tools(trading_plan, available_exchanges, market_data)
        
        # 5. Update position
        self._update_position(execution_result)
        
        # 6. Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(execution_result)
        
        return execution_result
    
    def _execute_with_tools(self, trading_plan, available_exchanges, market_data):
        """Execute trading plan using available tools"""
        # Simple execution - LLM can choose exchange
        # For now, use first available exchange
        selected_exchange = None
        for exchange, available in available_exchanges.items():
            if available:
                selected_exchange = exchange
                break
        
        if not selected_exchange:
            return self._create_execution_result('rejected', 'No exchanges available')
        
        # Execute using selected exchange tool
        execution_result = self.llm_interface.execute_tool(
            selected_exchange, 
            'place_order',
            symbol=trading_plan['symbol'],
            side=trading_plan['direction'],
            quantity=trading_plan['position_size'],
            price=trading_plan.get('entry_price')
        )
        
        return execution_result
```

### 2. Venue Selection Engine

```python
class VenueSelectionEngine:
    """Mathematical venue selection engine"""
    
    def __init__(self, venue_clients, weights):
        self.venue_clients = venue_clients
        self.weights = weights
        self.venue_performance = {}
    
    def select_optimal_venue(self, trading_plan):
        """Select optimal venue using mathematical scoring"""
        venue_scores = {}
        
        for venue_name, client in self.venue_clients.items():
            # Calculate individual scores
            liquidity_score = self._calculate_liquidity_score(trading_plan, client)
            fee_score = self._calculate_fee_score(trading_plan, client)
            latency_score = self._calculate_latency_score(client)
            reliability_score = self._calculate_reliability_score(venue_name)
            
            # Calculate weighted score
            total_score = (
                self.weights['liquidity'] * liquidity_score +
                self.weights['fees'] * fee_score +
                self.weights['latency'] * latency_score +
                self.weights['reliability'] * reliability_score
            )
            
            venue_scores[venue_name] = {
                'total_score': total_score,
                'liquidity_score': liquidity_score,
                'fee_score': fee_score,
                'latency_score': latency_score,
                'reliability_score': reliability_score
            }
        
        # Select venue with highest score
        optimal_venue = max(venue_scores, key=lambda x: venue_scores[x]['total_score'])
        
        return {
            'venue_name': optimal_venue,
            'scores': venue_scores[optimal_venue],
            'all_scores': venue_scores
        }
    
    def _calculate_liquidity_score(self, trading_plan, client):
        """Calculate liquidity score for venue"""
        symbol = trading_plan['symbol']
        order_size = trading_plan['position_size']
        side = trading_plan['direction']
        
        # Get order book data
        orderbook = client.get_orderbook(symbol)
        
        if side == 'buy':
            # Calculate ask side liquidity
            ask_liquidity = sum(level['size'] for level in orderbook['asks'][:5])
            required_liquidity = order_size * 1.2  # 20% buffer
            liquidity_score = min(1.0, ask_liquidity / required_liquidity)
        else:
            # Calculate bid side liquidity
            bid_liquidity = sum(level['size'] for level in orderbook['bids'][:5])
            required_liquidity = order_size * 1.2  # 20% buffer
            liquidity_score = min(1.0, bid_liquidity / required_liquidity)
        
        return liquidity_score
    
    def _calculate_fee_score(self, trading_plan, client):
        """Calculate fee score for venue"""
        symbol = trading_plan['symbol']
        order_size = trading_plan['position_size']
        
        # Get fee structure
        fees = client.get_fee_structure(symbol)
        
        # Calculate expected fees
        expected_fees = order_size * fees['taker_fee']
        max_acceptable_fees = order_size * 0.001  # 0.1% max
        
        # Calculate fee score
        fee_score = 1.0 - min(1.0, expected_fees / max_acceptable_fees)
        
        return fee_score
    
    def _calculate_latency_score(self, client):
        """Calculate latency score for venue"""
        # Get historical latency data
        latency_data = client.get_latency_metrics()
        avg_latency = latency_data['avg_latency_ms']
        max_acceptable_latency = 1000  # 1 second
        
        # Calculate latency score
        latency_score = 1.0 - min(1.0, avg_latency / max_acceptable_latency)
        
        return latency_score
    
    def _calculate_reliability_score(self, venue_name):
        """Calculate reliability score for venue"""
        if venue_name not in self.venue_performance:
            return 0.5  # Default score
        
        performance = self.venue_performance[venue_name]
        success_rate = performance['success_rate']
        uptime = performance['uptime']
        
        # Calculate reliability score
        reliability_score = (success_rate + uptime) / 2
        
        return reliability_score
```

### 3. Execution Engine

```python
class ExecutionEngine:
    """Mathematical execution engine"""
    
    def __init__(self, config):
        self.config = config
        self.execution_strategies = {
            'market': MarketOrderStrategy(),
            'limit': LimitOrderStrategy(),
            'twap': TWAPStrategy(),
            'vwap': VWAPStrategy()
        }
    
    def execute_order(self, trading_plan, venue, execution_params):
        """Execute order using optimal strategy"""
        # Select execution strategy
        strategy = self._select_execution_strategy(trading_plan, execution_params)
        
        # Execute using selected strategy
        execution_result = strategy.execute(trading_plan, venue, execution_params)
        
        # Calculate execution metrics
        execution_metrics = self._calculate_execution_metrics(execution_result)
        
        return {
            'execution_result': execution_result,
            'execution_metrics': execution_metrics,
            'strategy_used': strategy.name
        }
    
    def _select_execution_strategy(self, trading_plan, execution_params):
        """Select optimal execution strategy"""
        order_size = trading_plan['position_size']
        time_horizon = trading_plan['time_horizon']
        urgency = execution_params.get('urgency', 'normal')
        
        # Strategy selection logic
        if urgency == 'high' or time_horizon < 60:  # Less than 1 minute
            return self.execution_strategies['market']
        elif order_size > 10000:  # Large order
            return self.execution_strategies['twap']
        elif execution_params.get('use_vwap', False):
            return self.execution_strategies['vwap']
        else:
            return self.execution_strategies['limit']
    
    def _calculate_execution_metrics(self, execution_result):
        """Calculate execution performance metrics"""
        # Calculate slippage
        slippage = self._calculate_slippage(execution_result)
        
        # Calculate latency
        latency = self._calculate_latency(execution_result)
        
        # Calculate adherence
        adherence = self._calculate_adherence(execution_result)
        
        # Calculate venue score
        venue_score = self._calculate_venue_score(execution_result)
        
        # Calculate total execution score
        total_score = (
            self.config['execution_weights']['slippage'] * (1 - slippage) +
            self.config['execution_weights']['latency'] * (1 - latency) +
            self.config['execution_weights']['adherence'] * adherence +
            self.config['execution_weights']['venue'] * venue_score
        )
        
        return {
            'slippage': slippage,
            'latency': latency,
            'adherence': adherence,
            'venue_score': venue_score,
            'total_score': total_score
        }
```

## Database Schema

### Trader Module Strands (tr_strand)

```sql
-- Trader / Execution strands (following Lotus architecture)
CREATE TABLE tr_strand (
    id TEXT PRIMARY KEY,                    -- ULID
    lifecycle_id TEXT,                      -- Thread identifier
    parent_id TEXT,                         -- Linkage to parent strand
    module TEXT DEFAULT 'tr',               -- Module identifier
    kind TEXT,                              -- 'strand'|'execution'|'fill'|'position'
    symbol TEXT,                            -- Trading symbol
    timeframe TEXT,                         -- '1m'|'5m'|'15m'|'1h'|'4h'|'1d'
    session_bucket TEXT,                    -- Session identifier
    regime TEXT,                            -- Market regime
    decision_id TEXT,                       -- Reference to dm_strand
    order_spec JSONB,                       -- Order specification
    route_hint TEXT,                        -- Execution route hint
    tr_predict JSONB,                       -- {fill_prob, slip_bps, latency_ms}
    fills JSONB,                            -- [{px,qty,ts,venue}, ...]
    exec_metrics JSONB,                     -- {slip_real_bps, latency_ms, fees}
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for fast queries
CREATE INDEX tr_strand_symbol_time ON tr_strand(symbol, created_at DESC);
CREATE INDEX tr_strand_lifecycle ON tr_strand(lifecycle_id);
CREATE INDEX tr_strand_decision ON tr_strand(decision_id);
CREATE INDEX tr_strand_venue ON tr_strand((exec_metrics->>'venue'));

-- Tool execution tracking
CREATE TABLE tr_tool_executions (
    id TEXT PRIMARY KEY,
    strand_id TEXT REFERENCES tr_strand(id),
    tool_name TEXT NOT NULL,
    action TEXT NOT NULL,
    input_params JSONB,
    output_result JSONB,
    execution_time_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Venue performance tracking
CREATE TABLE tr_venue_performance (
    id TEXT PRIMARY KEY,
    venue TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    session_bucket TEXT NOT NULL,
    total_trades INTEGER DEFAULT 0,
    successful_trades INTEGER DEFAULT 0,
    total_slippage_bps DECIMAL(8,4) DEFAULT 0,
    total_latency_ms INTEGER DEFAULT 0,
    total_pnl DECIMAL(20,8) DEFAULT 0,
    avg_slippage_bps DECIMAL(8,4),
    avg_latency_ms INTEGER,
    success_rate DECIMAL(5,4),
    last_updated TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(venue, symbol, timeframe, session_bucket)
);

-- Tool registry (for easy tool management)
CREATE TABLE tr_tool_registry (
    tool_name TEXT PRIMARY KEY,
    tool_type TEXT NOT NULL,                -- 'exchange'|'data_source'|'intelligence'
    description TEXT,
    capabilities JSONB,                     -- List of capabilities
    requirements JSONB,                     -- Required parameters
    config_schema JSONB,                    -- Configuration schema
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Insert default tools
INSERT INTO tr_tool_registry (tool_name, tool_type, description, capabilities) VALUES
('hyperliquid', 'exchange', 'Connect to Hyperliquid exchange', '["place_order", "get_balance", "get_positions"]'),
('binance', 'exchange', 'Connect to Binance exchange', '["place_order", "get_balance", "get_positions"]'),
('coinbase', 'exchange', 'Connect to Coinbase exchange', '["place_order", "get_balance", "get_positions"]'),
('raydium', 'exchange', 'Connect to Raydium DEX on Solana', '["swap", "get_pool_info", "get_quote"]'),
('uniswap', 'exchange', 'Connect to Uniswap DEX on Ethereum', '["swap", "get_pool_info", "get_quote"]'),
('jupiter', 'exchange', 'Connect to Jupiter aggregator on Solana', '["get_quote", "swap", "get_routes"]'),
('coingecko', 'data_source', 'Get price data from CoinGecko', '["get_price", "get_volume", "get_market_data"]'),
('defi_llama', 'data_source', 'Get DeFi data from DeFiLlama', '["get_liquidity", "get_tvl", "get_protocols"]'),
('dune', 'data_source', 'Query on-chain data from Dune Analytics', '["query", "get_metrics", "get_charts"]'),
('the_graph', 'data_source', 'Query blockchain data from The Graph', '["query", "get_subgraph", "get_metrics"]'),
('liquidity_aggregator', 'intelligence', 'Aggregate liquidity across venues', '["aggregate_liquidity", "find_best_venue", "liquidity_ranking"]'),
('venue_optimizer', 'intelligence', 'Optimize venue selection', '["optimize_venue", "venue_scoring", "performance_analysis"]'),
('arbitrage_detector', 'intelligence', 'Detect arbitrage opportunities', '["detect_arbitrage", "cross_venue_prices", "arbitrage_analysis"]'),
('strand_analyzer', 'intelligence', 'Analyze strand patterns', '["analyze_patterns", "strand_correlation", "pattern_detection"]'),
('regime_detector', 'intelligence', 'Detect market regimes', '["detect_regime", "regime_analysis", "regime_transition"]');
```

## Configuration

```yaml
trader_module:
  execution:
    default_strategy: "market"
    max_order_size: 10000
    min_order_size: 0.001
    max_slippage: 0.01  # 1%
    max_latency_ms: 1000
    
    # Mathematical weights
    execution_weights:
      slippage: 0.3
      latency: 0.2
      adherence: 0.3
      venue: 0.2
    
    venue_weights:
      liquidity: 0.4
      fees: 0.3
      latency: 0.2
      reliability: 0.1
  
  database:
    dsn: "${TRADER_DB_URL}"
    pool_size: 10
    max_overflow: 20
  
  intelligence_layer:
    enabled: true
    context_cache_ttl: 300  # 5 minutes
    pattern_analysis_enabled: true
  
  tools:
    # Easy to add new tools - just add to registry
    auto_discover: true
    tool_timeout_ms: 30000
    max_retries: 3
  
  # Simple API key configuration
  api_keys:
    hyperliquid: "${HYPERLIQUID_API_KEY}"
    binance: "${BINANCE_API_KEY}"
    coinbase: "${COINBASE_API_KEY}"
    coingecko: "${COINGECKO_API_KEY}"
    defi_llama: "${DEFI_LLAMA_API_KEY}"
    dune: "${DUNE_API_KEY}"
    the_graph: "${THE_GRAPH_API_KEY}"
  
  # RPC endpoints for on-chain tools
  rpc_endpoints:
    solana: "${SOLANA_RPC_URL}"
    ethereum: "${ETHEREUM_RPC_URL}"
    arbitrum: "${ARBITRUM_RPC_URL}"
    polygon: "${POLYGON_RPC_URL}"
  
  # Wallet configuration
  wallets:
    solana: "${SOLANA_WALLET_KEY}"
    ethereum: "${ETHEREUM_WALLET_KEY}"
  
  risk_management:
    max_position_size: 0.1  # 10% max position
    max_daily_volume: 1000000
    stop_loss_enabled: true
    take_profit_enabled: true
    var_limit: 0.05  # 5% VaR limit
    concentration_limit: 0.2  # 20% max concentration
```

---

*This core architecture provides the mathematical foundations and implementation framework for the Trader Module, incorporating sophisticated execution quality metrics, venue selection algorithms, and position management mathematics.*
