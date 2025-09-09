# CIL Conditional Plan Learning System - Build Plan

## **Overview**

This document outlines the comprehensive build plan for implementing the CIL Conditional Plan Learning System, which transforms CIL from a passive coordinator into an active strategic signal generator that learns from outcomes and creates actionable trading plans.

## **Current State Analysis**

### **Existing Clustering System (INSUFFICIENT)**
- **Feature-based similarity**: Symbol, timeframe, regime, session, pattern type
- **Simple grouping**: `agent_id + detection_type` 
- **Braid clustering**: By `pattern_family` only
- **Missing**: Asset-specific, strength ranges, R/R analysis, outcome-based clustering

### **The Problem**
Current clustering is **way too basic** for conditional plan learning:
- Groups "raw_data_intelligence_divergence" as one cluster
- No distinction between BTC 1m vs ETH 15m divergences
- No strength range clustering (2x vs 5x volume spikes)
- No R/R profile clustering
- No outcome-based learning

## **Target Architecture**

### **1. Enhanced Clustering System**

#### **A. Multi-Dimensional Clustering Keys**
```python
# Basic clustering key
cluster_key = f"{asset}_{timeframe}_{pattern_type}_{strength_range}_{market_regime}"

# Examples:
# "BTC_1m_volume_spike_2x_to_3x_bull_market"
# "ETH_15m_divergence_weak_bear_market" 
# "SOL_5m_correlation_strong_sideways"
```

#### **B. Strength Range Classification**
```python
# Volume spike ranges
volume_ranges = {
    'weak': (1.2, 1.5),
    'moderate': (1.5, 2.0), 
    'strong': (2.0, 3.0),
    'extreme': (3.0, 5.0),
    'anomalous': (5.0, float('inf'))
}

# Divergence strength ranges  
divergence_ranges = {
    'weak': (0.3, 0.5),
    'moderate': (0.5, 0.7),
    'strong': (0.7, 0.9),
    'extreme': (0.9, 1.0)
}
```

#### **C. R/R Profile Clustering**
```python
# Cluster by similar risk/reward profiles
rr_clusters = {
    'conservative': {'min_rr': 1.5, 'max_rr': 2.0, 'max_dd': 0.05},
    'moderate': {'min_rr': 2.0, 'max_rr': 3.0, 'max_dd': 0.10},
    'aggressive': {'min_rr': 3.0, 'max_rr': 5.0, 'max_dd': 0.20}
}
```

### **2. Prediction Tracking System**

#### **A. PredictionTracker (New Raw Team Member)**
```python
class PredictionTracker:
    """Tracks all predictions until max_time expires"""
    
    async def track_prediction(self, prediction_strand: Dict[str, Any]):
        """Track prediction: entry_price, target_price, stop_loss, max_time"""
        
    async def update_prediction_outcome(self, prediction_id: str, current_price: float):
        """Update every 5 minutes: current_price, max_drawdown, time_remaining"""
        
    async def finalize_prediction(self, prediction_id: str, outcome: str):
        """Finalize: target_hit, stop_hit, expired, max_drawdown_achieved"""
```

#### **B. Prediction Schema**
```sql
-- Add to AD_strands
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS prediction_data JSONB;
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS outcome_data JSONB;
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS max_drawdown DECIMAL(10,4);
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS tracking_status VARCHAR(20) DEFAULT 'active';
```

### **3. Learning Feedback Engine Enhancement**

#### **A. Outcome Analysis Engine (New CIL Engine)**
```python
class OutcomeAnalysisEngine:
    """Analyzes prediction outcomes and generates learning insights"""
    
    async def analyze_outcome_batch(self, cluster_key: str, predictions: List[Dict]) -> Dict:
        """Analyze batch of similar predictions for learning"""
        
    async def calculate_rr_optimization(self, predictions: List[Dict]) -> Dict:
        """Optimize stop loss and target based on historical outcomes"""
        
    async def generate_plan_evolution(self, cluster_key: str, analysis: Dict) -> Dict:
        """Generate evolution recommendations for conditional plans"""
```

#### **B. Conditional Plan Manager (New CIL Engine)**
```python
class ConditionalPlanManager:
    """Manages conditional trading plans and their evolution"""
    
    async def create_conditional_plan(self, cluster_analysis: Dict) -> Dict:
        """Create new conditional plan from cluster analysis"""
        
    async def update_conditional_plan(self, plan_id: str, evolution: Dict) -> Dict:
        """Update existing plan with learning insights"""
        
    async def deprecate_plan(self, plan_id: str, reason: str) -> Dict:
        """Mark plan as deprecated and create new version"""
```

### **4. Database Schema Updates**

#### **A. Enhanced AD_strands Table (Hybrid Approach)**
```sql
-- Add new columns for learning system
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS cluster_key VARCHAR(100);
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS strength_range VARCHAR(20);
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS rr_profile VARCHAR(20);
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS market_conditions VARCHAR(20);
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS prediction_data JSONB;
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS outcome_data JSONB;
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS max_drawdown DECIMAL(10,4);
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS tracking_status VARCHAR(20) DEFAULT 'active';
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS plan_version INT DEFAULT 1;
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS replaces_id VARCHAR(100);
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS replaced_by_id VARCHAR(100);

-- New indexes for learning
CREATE INDEX IF NOT EXISTS idx_ad_strands_cluster_key ON AD_strands(cluster_key);
CREATE INDEX IF NOT EXISTS idx_ad_strands_strength_range ON AD_strands(strength_range);
CREATE INDEX IF NOT EXISTS idx_ad_strands_rr_profile ON AD_strands(rr_profile);
CREATE INDEX IF NOT EXISTS idx_ad_strands_market_conditions ON AD_strands(market_conditions);
CREATE INDEX IF NOT EXISTS idx_ad_strands_tracking_status ON AD_strands(tracking_status);
CREATE INDEX IF NOT EXISTS idx_ad_strands_plan_version ON AD_strands(plan_version);
CREATE INDEX IF NOT EXISTS idx_ad_strands_prediction_tracking ON AD_strands(kind, tracking_status) WHERE kind = 'prediction';
```

#### **B. Data Redundancy Strategy**
**Why we keep both high-level columns AND module_intelligence:**

1. **Performance vs Storage Trade-off**
   - **High-level columns**: Fast clustering, easy queries, indexed
   - **module_intelligence**: Complete data, flexible analysis, detailed insights

2. **Different Use Cases**
   - **Clustering**: Uses high-level columns for speed
   - **Analysis**: Uses module_intelligence for depth
   - **Learning**: Uses both for different purposes

3. **Data Integrity**
   - **High-level columns**: Computed once, consistent
   - **module_intelligence**: Raw data, can change, needs validation

4. **Computed Columns with Validation**
   ```python
   def create_pattern_strand(self, pattern_data):
       # Extract detailed data
       module_intelligence = {
           'pattern_type': pattern_data['type'],
           'volume_ratio': pattern_data.get('volume_ratio', 1.0),
           'divergence_strength': pattern_data.get('divergence_strength', 0.0),
           'regime_analysis': pattern_data.get('regime_analysis', {}),
           'rr_analysis': pattern_data.get('rr_analysis', {}),
           # ... other detailed data
       }
       
       # Compute high-level classifications
       strength_range = self._classify_strength_range(module_intelligence)
       rr_profile = self._classify_rr_profile(module_intelligence)
       market_conditions = self._classify_market_conditions(module_intelligence)
       
       # Validate consistency
       self._validate_classification_consistency(module_intelligence, {
           'strength_range': strength_range,
           'rr_profile': rr_profile,
           'market_conditions': market_conditions
       })
       
       strand = {
           'module_intelligence': module_intelligence,  # Complete data
           'strength_range': strength_range,            # Fast clustering
           'rr_profile': rr_profile,                    # Fast clustering
           'market_conditions': market_conditions,      # Fast clustering
           # ... other fields
       }
       
       return strand
   ```

#### **B. Pattern Evolution Table**
```sql
-- Track pattern evolution over time
CREATE TABLE IF NOT EXISTS pattern_evolution (
    pattern_type VARCHAR(50),
    cluster_key VARCHAR(100),
    version INT,
    success_rate DECIMAL(5,4),
    avg_rr DECIMAL(10,4),
    avg_mdd DECIMAL(10,4),
    sample_size INT,
    last_updated TIMESTAMPTZ,
    PRIMARY KEY (pattern_type, cluster_key, version)
);
```

### **5. Implementation Plan**

#### **Phase 1: Enhanced Clustering (Week 1)**
1. **Update Database Schema** - Add high-level clustering columns
2. **Update InputProcessor** - Add multi-dimensional clustering with hybrid approach
3. **Update LearningFeedbackEngine** - Enhanced braid clustering
4. **Add strength range classification** - Pattern strength analysis with validation
5. **Test clustering granularity** - Verify asset/timeframe/strength clustering

#### **Phase 2: Prediction Tracking (Week 2)**
1. **Create PredictionTracker** - New Raw team member
2. **Update Raw Data Intelligence** - Add prediction creation
3. **Add tracking infrastructure** - 5-minute price updates
4. **Test prediction lifecycle** - Entry → tracking → outcome

#### **Phase 3: Learning Analysis (Week 3)**
1. **Create OutcomeAnalysisEngine** - New CIL engine
2. **Create ConditionalPlanManager** - New CIL engine
3. **Implement R/R optimization** - Brute force → gradient descent
4. **Test learning feedback loop** - Predictions → analysis → plans

#### **Phase 4: Plan Evolution (Week 4)**
1. **Implement plan versioning** - Deprecated → new versions
2. **Add plan monitoring** - RMC checks conditions
3. **Integrate with Decision Maker** - Plan execution
4. **Test full learning cycle** - Pattern → prediction → outcome → plan

### **6. Key Features**

#### **A. Hybrid Clustering Architecture**
- **High-level columns**: Fast clustering, indexed queries, consistent classification
- **module_intelligence**: Complete data, flexible analysis, detailed insights
- **Computed validation**: Ensures consistency between high-level and detailed data
- **Performance optimization**: Uses high-level columns for clustering, detailed data for analysis

#### **B. Granular Clustering**
- **Asset-specific**: BTC vs ETH vs SOL
- **Timeframe-specific**: 1m vs 5m vs 15m vs 1h
- **Pattern-specific**: volume_spike vs divergence vs correlation
- **Strength-specific**: 2x vs 3x vs 5x volume spikes
- **Regime-specific**: bull vs bear vs sideways markets

#### **C. R/R Optimization**
- **Brute force testing** of stop loss/target combinations
- **Expected value calculation** based on historical outcomes
- **Risk-adjusted optimization** considering max drawdown
- **Time decay factors** for different timeframes

#### **D. Plan Evolution**
- **Version control** for conditional plans
- **Deprecation system** for outdated plans
- **Learning integration** from every outcome
- **A/B testing** of plan variations

#### **E. Outcome Learning**
- **Every outcome is a lesson** - target hit, stop hit, expired
- **Detailed analysis** - was target too low? stop too tight?
- **Max drawdown tracking** - what was the worst case?
- **Recovery analysis** - did price recover after stop?

### **7. Success Metrics**

#### **A. Clustering Quality**
- **Cluster purity**: Similar patterns grouped together
- **Cluster separation**: Different patterns in different clusters
- **Learning efficiency**: Faster convergence with better clustering

#### **B. Prediction Accuracy**
- **R/R improvement**: Better risk/reward ratios over time
- **Success rate**: Higher win rates for conditional plans
- **Drawdown control**: Lower maximum drawdowns

#### **C. Plan Evolution**
- **Plan effectiveness**: Higher success rates for evolved plans
- **Learning speed**: Faster adaptation to market changes
- **Knowledge retention**: Better long-term pattern recognition

### **8. Integration Points**

#### **A. Raw Data Intelligence**
- **Creates predictions** with stop loss, target, max time
- **PredictionTracker** monitors all predictions
- **RMC** checks conditional plan conditions

#### **B. Central Intelligence Layer**
- **OutcomeAnalysisEngine** analyzes prediction outcomes
- **ConditionalPlanManager** creates and evolves plans
- **LearningFeedbackEngine** integrates with strand-braid system

#### **C. Decision Maker**
- **Receives conditional plans** from CIL
- **Executes trades** when conditions are met
- **Reports outcomes** back to CIL for learning

### **9. Testing Strategy**

#### **A. Unit Tests**
- **Clustering accuracy** - verify correct grouping
- **R/R optimization** - test optimization algorithms
- **Plan evolution** - verify version control

#### **B. Integration Tests**
- **Full prediction lifecycle** - entry → tracking → outcome
- **Learning feedback loop** - outcome → analysis → plan update
- **Plan execution** - condition check → trade execution

#### **C. Performance Tests**
- **Clustering speed** - handle large numbers of strands
- **Learning efficiency** - fast convergence to optimal plans
- **Memory usage** - efficient storage of learning data

### **10. Future Enhancements**

#### **A. Advanced Clustering**
- **Vector embeddings** for semantic similarity
- **Dynamic clustering** based on market conditions
- **Hierarchical clustering** for multi-level patterns

#### **B. Machine Learning**
- **Gradient descent** for R/R optimization
- **Bayesian optimization** for complex parameter spaces
- **Reinforcement learning** for plan evolution

#### **C. Advanced Analytics**
- **Monte Carlo simulation** for risk analysis
- **Backtesting framework** for plan validation
- **Real-time adaptation** to market regime changes

## **Conclusion**

This build plan transforms the CIL from a basic clustering system into a sophisticated learning engine that:

1. **Learns from every outcome** - not just successes/failures
2. **Creates actionable plans** - specific trading conditions
3. **Evolves continuously** - adapts to market changes
4. **Optimizes risk/reward** - data-driven parameter tuning
5. **Maintains knowledge** - version-controlled plan evolution

### **Hybrid Approach Benefits**

The hybrid clustering architecture provides the best of both worlds:

- **Performance**: High-level columns enable fast clustering and indexed queries
- **Flexibility**: module_intelligence provides complete data for detailed analysis
- **Consistency**: Computed validation ensures data integrity between levels
- **Scalability**: Can handle large datasets with efficient clustering
- **Maintainability**: Clear separation between clustering and analysis concerns

The key insight is that **clustering granularity is critical** - we need asset/timeframe/strength/regime-specific clustering, not just agent/pattern-type clustering. This enables the system to learn that "BTC 1m volume spikes of 2x-3x in bull markets" behave differently than "ETH 15m volume spikes of 5x+ in bear markets" and create appropriate conditional plans for each.

**Next Steps:**
1. **Review and approve** this build plan
2. **Start with Phase 1** - Enhanced clustering system
3. **Iterate and refine** based on testing results
4. **Scale up** to full learning system implementation
