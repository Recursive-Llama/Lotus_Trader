# Conditional Trading Planner (CTP) Design

## **Overview**

The Conditional Trading Planner (CTP) is a **Trading Strategy Intelligence Engine** that transforms Prediction Reviews into sophisticated conditional trading plans. It learns from actual market outcomes to create increasingly intelligent trading strategies.

## **System Architecture**

```
Raw Data Intelligence → CIL (Prediction Reviews) → CTP (Conditional Trading Plans) → DM (Decision Maker) → TD (Trader) → Trade Outcomes → CTP
```

### **CTP's Single Responsibility**
**"Given Prediction Reviews and Trade Outcomes, what are the smartest conditional trading plans?"**

## **Data Sources**

### **Input 1: Prediction Reviews** (`kind: 'prediction_review'`)
```json
{
  "group_signature": "BTC_1h_volume_spike_divergence",
  "pattern_group": {
    "asset": "BTC",
    "timeframe": "1h", 
    "group_type": "multi_single",
    "patterns": [...]
  },
  "outcome": {
    "success": true,
    "return_pct": 3.2,
    "max_drawdown": -1.1,
    "duration_hours": 4.5
  },
  "confidence": 0.85,
  "method": "code",
  "cluster_keys": [
    "pattern_timeframe_BTC_1h_volume_spike_divergence",
    "asset_BTC",
    "timeframe_1h", 
    "outcome_success",
    "pattern_multi_single",
    "group_type_multi_single",
    "method_code"
  ],
  "original_pattern_strand_ids": ["strand_123", "strand_456"]
}
```

### **Input 2: Trade Outcomes** (`kind: 'trade_outcome'`) - Future
```json
{
  "trade_id": "trade_789",
  "ctp_id": "ctp_001",
  "execution": {
    "entry_price": 45000.0,
    "entry_time": "2024-01-15T10:30:00Z",
    "stop_loss": 44100.0,
    "target_price": 46800.0,
    "exit_price": 46500.0,
    "exit_time": "2024-01-15T14:45:00Z"
  },
  "performance": {
    "success": true,
    "return_pct": 3.33,
    "max_drawdown": -2.0,
    "duration_hours": 4.25,
    "r_r_ratio": 1.67
  },
  "analysis": {
    "hit_stop_loss": false,
    "reached_target": true,
    "better_entry_available": false,
    "optimal_exit_time": "2024-01-15T14:30:00Z"
  }
}
```

## **CTP Decision-Making Process**

### **Step 1: New Prediction Review Trigger**
When a new `prediction_review` strand is created, CTP analyzes it:

1. **Extract Pattern Information**
   - Group signature: "BTC_1h_volume_spike_divergence"
   - Asset: "BTC"
   - Timeframe: "1h"
   - Pattern types: ["volume_spike", "divergence"]
   - Group type: "multi_single"

2. **Identify Relevant Clusters**
   - Pattern+Timeframe: "BTC_1h_volume_spike_divergence"
   - Asset: "BTC"
   - Timeframe: "1h"
   - Pattern: "multi_single"
   - Group Type: "multi_single"
   - Method: "code" or "llm"

### **Step 2: Historical Performance Analysis**
Query all prediction reviews in relevant clusters:

```sql
-- Pattern+Timeframe cluster
SELECT * FROM AD_strands 
WHERE kind = 'prediction_review' 
AND content->>'group_signature' = 'BTC_1h_volume_spike_divergence'
ORDER BY created_at DESC;

-- Asset cluster  
SELECT * FROM AD_strands 
WHERE kind = 'prediction_review' 
AND content->>'asset' = 'BTC'
ORDER BY created_at DESC;

-- Timeframe cluster
SELECT * FROM AD_strands 
WHERE kind = 'prediction_review' 
AND content->>'timeframe' = '1h'
ORDER BY created_at DESC;
```

**Calculate Performance Metrics:**
- Success rate: 60% (12/20 predictions)
- Average return: 3.2%
- Average R/R ratio: 2.8
- Average duration: 4.5 hours
- Confidence correlation: 0.85+ predictions perform better

### **Step 3: Trade Outcome Analysis** (When Available)
Query trade outcomes for similar patterns:

```sql
SELECT * FROM AD_strands 
WHERE kind = 'trade_outcome'
AND content->>'asset' = 'BTC'
AND content->>'timeframe' = '1h'
ORDER BY created_at DESC;
```

**Compare Performance:**
- Prediction Reviews: 60% success, 3.2% return, 2.8 R/R
- Trade Outcomes: 55% success, 2.8% return, 2.5 R/R
- **Insight**: Predictions are slightly optimistic, but still profitable

### **Step 4: Conditional Trading Plan Generation**

Based on historical analysis, create intelligent trading rules:

#### **Basic Plan Structure:**
```json
{
  "plan_id": "ctp_001",
  "trigger_conditions": {
    "group_signature": "BTC_1h_volume_spike_divergence",
    "min_confidence": 0.7,
    "min_pattern_count": 2
  },
  "trading_rules": {
    "direction": "long",
    "entry_condition": "price_breaks_above_divergence_level",
    "stop_loss": "2%_below_entry",
    "target_price": "6%_above_entry", 
    "position_sizing": "confidence_weighted"
  },
  "management_rules": {
    "if_volume_spikes_again": "take_50%_profit",
    "if_price_drops_1%": "add_another_position",
    "if_breaks_resistance": "move_stop_to_breakeven",
    "if_reversal_pattern": "exit_early"
  },
  "performance_expectations": {
    "success_rate": 0.60,
    "avg_return": 0.032,
    "r_r_ratio": 2.8,
    "avg_duration_hours": 4.5
  }
}
```

#### **Advanced Plan Structure:**
```json
{
  "plan_id": "ctp_002", 
  "trigger_conditions": {
    "group_signature": "BTC_1h_volume_spike_divergence",
    "min_confidence": 0.8,
    "rsi_condition": "rsi < 30",
    "volume_condition": "volume > 1.5x_average"
  },
  "trading_rules": {
    "direction": "long",
    "entry_strategy": "limit_order_at_support",
    "stop_loss": "1.5%_below_support",
    "target_price": "resistance_level",
    "position_sizing": "kelly_criterion_based"
  },
  "management_rules": {
    "if_price_drops_1%": "add_position_at_lower_support",
    "if_volume_spikes_again": "take_50%_profit_move_stop_breakeven",
    "if_breaks_resistance": "trail_stop_1%_below_price",
    "if_rsi_overbought": "take_75%_profit",
    "if_divergence_weakens": "exit_immediately"
  },
  "risk_management": {
    "max_position_size": "2%_of_portfolio",
    "max_drawdown": "1%_of_portfolio", 
    "max_duration_hours": 8,
    "correlation_limit": "no_more_than_3_similar_trades"
  }
}
```

## **Learning System Integration**

### **Multi-Cluster Learning** (Reuse CIL System)
CTP uses the same 7-cluster system as CIL for both Trade Outcomes and Trade Outcome Reviews:

#### **Trade Outcome Clustering**
1. **Pattern+Timeframe**: Exact group signature matches
2. **Asset**: All trades on same asset
3. **Timeframe**: All trades in same timeframe  
4. **Outcome**: Success vs failure patterns
5. **Pattern**: Pattern type (multi_single, single_single, etc.)
6. **Group Type**: Group classification
7. **Method**: Code vs LLM performance

#### **Trade Outcome Review Clustering**
After creating Trade Outcome Reviews, they are clustered using the same 7 dimensions:
- **Pattern+Timeframe**: Reviews from same pattern+timeframe
- **Asset**: Reviews from same asset
- **Timeframe**: Reviews from same timeframe
- **Outcome**: Success vs failure review patterns
- **Pattern**: Review pattern type
- **Group Type**: Review group classification
- **Method**: Review method type

#### **Clustering Process**
```python
# Step 1: Trade Outcomes → Trade Outcome Reviews
for trade_outcome in trade_outcomes:
    review = await create_trade_outcome_review(trade_outcome)
    await store_review(review)

# Step 2: Cluster Trade Outcome Reviews
for cluster_type in ['pattern_timeframe', 'asset', 'timeframe', 'outcome', 'pattern', 'group_type', 'method']:
    clusters = await get_review_clusters(cluster_type)
    for cluster in clusters:
        if len(cluster) >= 3:
            await create_braid_level_1(cluster, cluster_type)
```

### **Braid Level Progression**
As CTP processes more trade outcomes and learns from performance:

- **Level 1**: Individual trade outcomes → Trade Outcome Reviews
- **Level 2**: Clusters of similar Trade Outcome Reviews (3+ reviews)
- **Level 3**: Asset-specific trading patterns (3+ clusters)
- **Level 4**: Market-wide trading strategies (3+ asset clusters)
- **Level 5+**: Meta-strategies and market regime adaptation

### **LLM Learning Analysis** (Multi-Phase)
Use LLM to analyze trade outcome clusters in focused phases:

```python
class CTPLearningAnalyzer:
    async def analyze_trade_outcome_cluster(self, cluster_type, cluster_key, trade_outcomes, candlestick_data):
        """Analyze cluster of trade outcomes with candlestick data in focused phases"""
        
        # Phase 1: Market Behavior Analysis
        market_analysis = await self.analyze_market_behavior(cluster_key, trade_outcomes, candlestick_data)
        
        # Phase 2: Entry/Exit Optimization
        entry_exit_analysis = await self.analyze_entry_exit_optimization(cluster_key, trade_outcomes, candlestick_data)
        
        # Phase 3: Risk Management Insights
        risk_analysis = await self.analyze_risk_management(cluster_key, trade_outcomes, candlestick_data)
        
        # Phase 4: Strategy Refinement
        strategy_analysis = await self.analyze_strategy_refinement(cluster_key, trade_outcomes, candlestick_data)
        
        return {
            "market_behavior": market_analysis,
            "entry_exit": entry_exit_analysis,
            "risk_management": risk_analysis,
            "strategy_refinement": strategy_analysis
        }
    
    async def analyze_market_behavior(self, cluster_key, trade_outcomes, candlestick_data):
        """Phase 1: Focus on market behavior patterns"""
        prompt = f"""
        Analyze the market behavior patterns in this trade cluster:
        
        Cluster: {cluster_key}
        Trade Count: {len(trade_outcomes)}
        Success Rate: {self.calculate_success_rate(trade_outcomes):.2%}
        
        Trade Outcomes:
        {self.format_trade_outcomes(trade_outcomes)}
        
        Candlestick Data:
        {self.format_candlestick_analysis(candlestick_data, trade_outcomes)}
        
        Focus on:
        1. What specific market conditions led to success vs failure?
        2. How did volume, volatility, and price action differ between winners/losers?
        3. What were the key reversal/continuation signals in the candlestick data?
        4. How did support/resistance levels behave during these trades?
        """
        return await self.llm_client.generate_completion(prompt)
    
    async def analyze_entry_exit_optimization(self, cluster_key, trade_outcomes, candlestick_data):
        """Phase 2: Focus on entry/exit optimization"""
        prompt = f"""
        Analyze entry/exit optimization opportunities in this trade cluster:
        
        Cluster: {cluster_key}
        Trade Outcomes:
        {self.format_trade_outcomes(trade_outcomes)}
        
        Candlestick Data:
        {self.format_candlestick_analysis(candlestick_data, trade_outcomes)}
        
        Focus on:
        1. What were the optimal entry points based on candlestick patterns?
        2. How could stop losses have been better positioned?
        3. What exit signals were most reliable in the price action?
        4. How did market microstructure affect execution?
        """
        return await self.llm_client.generate_completion(prompt)
    
    async def analyze_risk_management(self, cluster_key, trade_outcomes, candlestick_data):
        """Phase 3: Focus on risk management insights"""
        prompt = f"""
        Analyze risk management opportunities in this trade cluster:
        
        Cluster: {cluster_key}
        Trade Outcomes:
        {self.format_trade_outcomes(trade_outcomes)}
        
        Focus on:
        1. What position sizing would have maximized returns?
        2. How could correlation risks have been better managed?
        3. What market regime changes affected these trades?
        4. How did news/events impact the price action during trades?
        """
        return await self.llm_client.generate_completion(prompt)
    
    async def analyze_strategy_refinement(self, cluster_key, trade_outcomes, candlestick_data):
        """Phase 4: Focus on strategy refinement"""
        prompt = f"""
        Analyze strategy refinement opportunities in this trade cluster:
        
        Cluster: {cluster_key}
        Trade Outcomes:
        {self.format_trade_outcomes(trade_outcomes)}
        
        Focus on:
        1. What new conditional rules should we add based on this analysis?
        2. How can we better identify high-probability setups?
        3. What market conditions should we avoid?
        4. How can we improve our entry/exit timing?
        """
        return await self.llm_client.generate_completion(prompt)
```

## **CTP Module Structure**

### **Core Components**

1. **Prediction Review Analyzer**
   - Processes new prediction reviews
   - Extracts pattern information
   - Identifies relevant clusters

2. **Historical Performance Calculator**
   - Queries prediction review clusters
   - Calculates success rates, R/R ratios, returns
   - Identifies performance patterns

3. **Trade Outcome Processor**
   - Processes trade outcome data
   - Compares prediction vs actual performance
   - Identifies execution improvements
   - Pulls in candlestick data for analysis

4. **Trading Plan Generator**
   - Creates conditional trading rules
   - Incorporates historical performance data
   - Generates risk management rules

5. **Learning System** (Unified)
   - Multi-cluster grouping of trade outcomes (reuse CIL system)
   - Braid level progression: Trade Outcomes → Trade Outcome Reviews
   - LLM analysis with candlestick data for deep insights
   - Continuous plan optimization based on learning

6. **Error Handler & Fallbacks**
   - LLM analysis failure handling (retry 3 times, 30-second timeout)
   - Missing data fallbacks (log warning, skip analysis)
   - Data quality validation and error logging
   - Basic plan generation when advanced analysis fails

### **Database Schema**

#### **Trading Plans** (`kind: 'trading_plan'`)
```json
{
  "plan_id": "ctp_001",
  "trigger_conditions": {...},
  "trading_rules": {...},
  "management_rules": {...},
  "performance_expectations": {...},
  "cluster_keys": [...],
  "created_at": "2024-01-15T10:30:00Z",
  "last_updated": "2024-01-15T14:45:00Z",
  "status": "active"
}
```

#### **Trade Outcome Reviews** (`kind: 'trade_outcome_review'`)
```json
{
  "review_id": "trade_outcome_review_001",
  "trade_outcome_id": "trade_789",
  "ctp_id": "ctp_001",
  "cluster_keys": [
    "pattern_timeframe_BTC_1h_volume_spike_divergence",
    "asset_BTC",
    "timeframe_1h",
    "outcome_success",
    "pattern_multi_single",
    "group_type_multi_single",
    "method_code"
  ],
  "analysis": {
    "candlestick_insights": {...},
    "market_conditions": {...},
    "execution_quality": {...},
    "improvement_suggestions": {...}
  },
  "braid_level": 1,
  "created_at": "2024-01-15T14:45:00Z"
}
```

## **Implementation Phases**

### **Phase 1: Basic CTP** (Week 1)
- Prediction review analyzer
- Historical performance calculator
- Basic trading plan generator
- Simple conditional rules

### **Phase 2: Learning Integration** (Week 2)
- Multi-cluster grouping system
- Braid level progression
- LLM learning analysis
- Plan optimization

### **Phase 3: Trade Outcome Integration** (Week 3)
- Trade outcome analyzer
- Prediction vs actual comparison
- Execution improvement insights
- Advanced risk management

### **Phase 4: Advanced Intelligence** (Week 4)
- Market regime detection
- Dynamic plan adaptation
- A/B testing framework
- Meta-strategy development

## **Key Success Metrics**

### **Trading Plan Quality**
- Plan success rate > 55%
- Average R/R ratio > 2.0
- Plan adoption rate > 80%
- Plan evolution rate (improvements over time)

### **Learning Effectiveness**
- Cluster analysis accuracy
- Braid level progression speed
- LLM insight quality
- Performance improvement rate

### **System Performance**
- Plan generation time < 5 seconds
- Learning cycle time < 30 seconds
- Database query performance
- Memory usage optimization

## **Integration Points**

### **Input Integration**
- **CIL**: Receives prediction reviews via strand creation
- **Database**: Queries historical data via Supabase
- **Future**: Trade outcomes from TD module

### **Output Integration**
- **DM**: Sends conditional trading plans
- **Database**: Stores plans and performance data
- **Future**: Receives trade outcomes for learning

### **Learning Integration**
- **CIL Learning System**: Reuses multi-cluster grouping
- **LLM**: Uses same OpenRouter client
- **Database**: Uses same AD_strands table structure

## **Risk Management**

### **Trading Plan Risks**
- Over-optimization on historical data
- Market regime changes
- Correlation risks between plans
- Execution slippage and costs

### **System Risks**
- Database performance with large datasets
- LLM API rate limits and costs
- Learning system complexity
- Plan generation accuracy

### **Mitigation Strategies**
- Regular plan performance review
- Market regime detection
- Correlation monitoring
- Execution cost analysis
- System performance monitoring

## **Future Enhancements**

### **Advanced Features**
- Multi-asset correlation analysis
- Market regime adaptation
- Dynamic position sizing
- Real-time plan updates
- Social sentiment integration

### **Integration Expansions**
- Social media data analysis
- News sentiment analysis
- Economic indicator integration
- Cross-market analysis
- Alternative data sources

## **Summary**

The CTP is a **Trading Strategy Intelligence Engine** that:

1. **Learns from Prediction Reviews** - What patterns actually work
2. **Analyzes Trade Outcomes** - How well we executed
3. **Creates Conditional Plans** - Smart trading rules based on data
4. **Continuously Improves** - Uses multi-cluster learning and braid progression
5. **Adapts to Markets** - Evolves strategies based on performance

It transforms raw market data into intelligent, data-driven trading strategies that get smarter over time.

The CTP doesn't predict prices - it learns from actual market behavior and creates increasingly sophisticated conditional trading plans that maximize the probability of success based on what actually worked before.
