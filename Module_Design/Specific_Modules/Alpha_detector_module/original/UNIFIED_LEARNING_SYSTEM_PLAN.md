# Unified Learning System Plan

## **Overview**

This document outlines a comprehensive learning system that combines universal pattern recognition with CIL-specific trading learning. The system is built on a foundation of universal learning that works with all strands, with specialized CIL learning that builds on top of it.

## **Architecture Overview**

### **Two-Tier Learning System**

1. **Universal Learning Foundation** - Works with all strands, creates braids, manages recursive hierarchy
2. **CIL Specialized Learning** - Builds on universal foundation, focuses on trading-specific learning and conditional plan creation

### **The Flow**
```python
# Universal Learning System (centralized)
strands → clustering → braids → metabraids → meta2braids...

# CIL Learning System (specialized, builds on universal)
trading_strands + trading_braids → prediction_tracking → outcome_analysis → conditional_plans
```

## **Part 1: Universal Learning Foundation**

### **Current State Analysis**

#### **What We Have**
- ✅ **Learning System** - Works with experiment results, creates lessons, manages doctrine
- ✅ **Database Schema** - All strands in `AD_strands` table with 60+ columns
- ✅ **Strand Types** - Raw Data Intelligence, CIL, Trading Plans, etc.
- ✅ **Braid Level System** - `braid_level` column for hierarchy (0=strand, 1=braid, 2=metabraid, 3=meta2braid etc.)

#### **What's Missing**
- ❌ **Universal Clustering** - No way to group similar strands of any type
- ❌ **Universal Learning** - Only works with experiment results
- ❌ **Universal Scoring** - Persistence/novelty/surprise not calculated for all strands
- ❌ **Threshold-based Promotion** - No way to promote clusters to braids

### **Universal Learning System Design**

#### **1. Everything is Strands Philosophy**
```python
# All strands have the same structure
strand = {
    'id': 'strand_123',
    'kind': 'signal',  # or 'intelligence', 'trading_plan', 'braid', etc.
    'braid_level': 0,  # 0=strand, 1=braid, 2=metabraid, 3=meta2braid, etc.
    'symbol': 'BTC',
    'timeframe': '1h',
    'agent_id': 'raw_data_intelligence',
    'persistence_score': 0.8,  # ← Calculate for ALL strands
    'novelty_score': 0.6,      # ← Calculate for ALL strands
    'surprise_rating': 0.7,    # ← Calculate for ALL strands
    # ... other fields
}
```

#### **2. Two-Tier Clustering System**

**Tier 1: Column Clustering (Structural Grouping)**
```python
def cluster_strands_by_columns(strands, braid_level):
    """Cluster strands by structural similarity using high-level columns"""
    clusters = []
    
    for strand in strands:
        if strand.get('braid_level', 0) != braid_level:
            continue  # Only cluster same level
            
        # Find similar cluster based on structural columns
        similar_cluster = find_similar_cluster(strand, clusters, STRUCTURAL_COLUMNS)
        
        if similar_cluster:
            similar_cluster.add_strand(strand)
        else:
            clusters.append(Cluster([strand]))
    
    return clusters

# Structural columns for initial grouping
STRUCTURAL_COLUMNS = [
    'agent_id', 'timeframe', 'regime', 'session_bucket',
    'pattern_type', 'motif_family', 'strategic_meta_type'
]
```

**Tier 2: Pattern Clustering (ML-based Similarity)**
```python
def cluster_strands_by_patterns(column_clusters):
    """Use existing PatternClusterer for sophisticated pattern clustering"""
    pattern_clusters = []
    
    for column_cluster in column_clusters:
        if len(column_cluster.strands) >= 3:  # Minimum for ML clustering
            # Use existing PatternClusterer
            pattern_clusters.extend(
                pattern_clusterer.cluster_situations(column_cluster.strands)
            )
        else:
            # Too few strands, keep as single cluster
            pattern_clusters.append(column_cluster)
    
    return pattern_clusters
```

#### **3. Universal Threshold-based Promotion**
```python
def cluster_meets_threshold(cluster):
    """Check if cluster meets threshold for promotion using calculated scores"""
    strands = cluster.strands
    
    # Use calculated persistence/novelty/surprise scores
    min_strands = 5
    min_avg_persistence = 0.6
    min_avg_novelty = 0.5
    min_avg_surprise = 0.4
    
    return (len(strands) >= min_strands and 
            cluster.avg_persistence >= min_avg_persistence and
            cluster.avg_novelty >= min_avg_novelty and
            cluster.avg_surprise >= min_avg_surprise)
```

#### **4. Universal Learning System Integration**
```python
async def promote_cluster_to_braid(cluster):
    """Use learning system to compress cluster into braid"""
    
    # Pass strands directly to learning system - no conversion needed
    braid = await learning_system.process_strands_into_braid(cluster.strands)
    
    return braid

# Complete clustering flow
async def cluster_and_promote_strands(strands, braid_level):
    """Complete two-tier clustering and promotion flow"""
    
    # Step 1: Column clustering (structural grouping)
    column_clusters = cluster_strands_by_columns(strands, braid_level)
    
    # Step 2: Pattern clustering (ML-based similarity)
    pattern_clusters = cluster_strands_by_patterns(column_clusters)
    
    # Step 3: Check thresholds and promote to braids
    braids = []
    for cluster in pattern_clusters:
        if cluster_meets_threshold(cluster):
            braid = await promote_cluster_to_braid(cluster)
            braids.append(braid)
    
    return braids
```

### **Universal Score Calculation**

#### **Persistence Score** (How reliable/consistent is this pattern?)
```python
def calculate_persistence_score(strand):
    """Calculate persistence based on strand type"""
    
    # For Raw Data Intelligence strands
    if strand.get('agent_id') == 'raw_data_intelligence':
        confidence = strand.get('sig_confidence', 0.0)
        data_quality = strand.get('module_intelligence', {}).get('data_quality_score', 1.0)
        return (confidence + data_quality) / 2
    
    # For CIL strands  
    elif strand.get('agent_id') == 'central_intelligence_layer':
        doctrine_status = strand.get('doctrine_status', 'provisional')
        confidence = strand.get('confidence', 0.0)
        
        doctrine_multiplier = {
            'affirmed': 1.0,
            'provisional': 0.7,
            'retired': 0.3,
            'contraindicated': 0.1
        }.get(doctrine_status, 0.5)
        
        return confidence * doctrine_multiplier
    
    # For Trading Plan strands
    elif strand.get('kind') == 'trading_plan':
        accumulated = strand.get('accumulated_score', 0.0)
        outcome = strand.get('outcome_score', 0.0)
        return (accumulated + outcome) / 2
    
    # For Braid strands
    elif strand.get('kind') in ['braid', 'meta_braid', 'meta2_braid']:
        # Braids get the average score of their source strands
        source_strands = strand.get('source_strands', [])
        if source_strands:
            return sum(s.get('persistence_score', 0.0) for s in source_strands) / len(source_strands)
        return 0.5
    
    # Default
    else:
        return strand.get('sig_confidence', 0.5)
```

#### **Novelty Score** (How unique/new is this pattern?)
```python
def calculate_novelty_score(strand):
    """Calculate novelty based on strand type"""
    
    # For Raw Data Intelligence strands
    if strand.get('agent_id') == 'raw_data_intelligence':
        pattern_type = strand.get('pattern_type', 'unknown')
        surprise = strand.get('surprise_rating', 0.0)
        
        novel_patterns = ['anomaly', 'divergence', 'correlation_break']
        if pattern_type in novel_patterns:
            return min(surprise + 0.3, 1.0)
        else:
            return surprise
    
    # For CIL strands
    elif strand.get('agent_id') == 'central_intelligence_layer':
        meta_type = strand.get('strategic_meta_type', 'unknown')
        experiment_id = strand.get('experiment_id')
        
        if experiment_id:
            return 0.8  # Experiments are novel
        elif meta_type in ['confluence', 'doctrine']:
            return 0.6  # Strategic insights are novel
        else:
            return 0.4
    
    # For Trading Plan strands
    elif strand.get('kind') == 'trading_plan':
        regime = strand.get('regime', 'unknown')
        
        if regime in ['anomaly', 'transition']:
            return 0.8
        else:
            return 0.5
    
    # For Braid strands
    elif strand.get('kind') in ['braid', 'meta_braid', 'meta2_braid']:
        # Braids get the average novelty score of their source strands
        source_strands = strand.get('source_strands', [])
        if source_strands:
            return sum(s.get('novelty_score', 0.0) for s in source_strands) / len(source_strands)
        return 0.5
    
    # Default
    else:
        return 0.5
```

#### **Surprise Rating** (How unexpected was this outcome?)
```python
def calculate_surprise_rating(strand):
    """Calculate surprise based on strand type"""
    
    # For Raw Data Intelligence strands
    if strand.get('agent_id') == 'raw_data_intelligence':
        sigma = strand.get('sig_sigma', 0.0)
        confidence = strand.get('sig_confidence', 0.0)
        
        # High sigma with low confidence = surprising
        if sigma > 0.8 and confidence < 0.5:
            return 0.9
        elif sigma > 0.6 and confidence < 0.7:
            return 0.7
        else:
            return 0.3
    
    # For CIL strands
    elif strand.get('agent_id') == 'central_intelligence_layer':
        doctrine_status = strand.get('doctrine_status', 'provisional')
        
        if doctrine_status == 'contraindicated':
            return 0.9  # Very surprising when something is contraindicated
        elif doctrine_status == 'retired':
            return 0.7  # Surprising when something is retired
        else:
            return 0.3
    
    # For Trading Plan strands
    elif strand.get('kind') == 'trading_plan':
        prediction = strand.get('prediction_score', 0.0)
        outcome = strand.get('outcome_score', 0.0)
        
        # High prediction with low outcome = surprising
        if prediction > 0.8 and outcome < 0.3:
            return 0.9
        elif prediction > 0.6 and outcome < 0.5:
            return 0.7
        else:
            return 0.3
    
    # For Braid strands
    elif strand.get('kind') in ['braid', 'meta_braid', 'meta2_braid']:
        # Braids get the average surprise rating of their source strands
        source_strands = strand.get('source_strands', [])
        if source_strands:
            return sum(s.get('surprise_rating', 0.0) for s in source_strands) / len(source_strands)
        return 0.3
    
    # Default
    else:
        return 0.3
```

## **Part 2: CIL Specialized Learning System**

### **CIL Learning System Design**

The CIL learning system builds on the universal foundation and adds trading-specific capabilities. It uses the same two-tier clustering approach but with trading-specific enhancements:

#### **1. CIL Two-Tier Clustering**

**Tier 1: Trading-Specific Column Clustering**
```python
def cluster_trading_strands_by_columns(strands, braid_level):
    """Cluster trading strands by trading-specific structural columns"""
    clusters = []
    
    for strand in strands:
        if strand.get('braid_level', 0) != braid_level:
            continue
            
        # Find similar cluster based on trading-specific columns
        similar_cluster = find_similar_cluster(strand, clusters, TRADING_STRUCTURAL_COLUMNS)
        
        if similar_cluster:
            similar_cluster.add_strand(strand)
        else:
            clusters.append(Cluster([strand]))
    
    return clusters

# Trading-specific structural columns
TRADING_STRUCTURAL_COLUMNS = [
    'symbol', 'timeframe', 'regime', 'session_bucket',
    'pattern_type', 'strength_range', 'rr_profile', 'market_conditions'
]
```

**Tier 2: CIL Pattern Clustering (Enhanced PatternClusterer)**
```python
def cluster_trading_strands_by_patterns(column_clusters):
    """Use enhanced PatternClusterer for trading-specific pattern clustering"""
    pattern_clusters = []
    
    for column_cluster in column_clusters:
        if len(column_cluster.strands) >= 3:
            # Use enhanced PatternClusterer with trading-specific features
            pattern_clusters.extend(
                cil_pattern_clusterer.cluster_situations(column_cluster.strands)
            )
        else:
            pattern_clusters.append(column_cluster)
    
    return pattern_clusters

# Trading-specific clustering keys
trading_cluster_key = f"{asset}_{timeframe}_{pattern_type}_{strength_range}_{market_regime}_{rr_profile}"

# Examples:
# "BTC_1m_volume_spike_2x_to_3x_bull_market_conservative"
# "ETH_15m_divergence_weak_bear_market_aggressive" 
# "SOL_5m_correlation_strong_sideways_moderate"
```

#### **2. CIL Learning Components**

**CIL PatternClusterer Enhancement**
```python
class CILPatternClusterer(PatternClusterer):
    """Enhanced PatternClusterer for CIL trading-specific clustering"""
    
    def __init__(self):
        super().__init__()
        # Add trading-specific features
        self.trading_features = [
            'rr_ratio', 'max_drawdown', 'outcome_score', 'prediction_accuracy',
            'volume_ratio', 'volatility', 'regime_strength', 'session_quality'
        ]
        self.categorical_features.extend([
            'strength_range', 'rr_profile', 'market_conditions', 'trading_session'
        ])
```

#### **3. Strength Range Classification**
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

#### **3. R/R Profile Clustering**
```python
# Cluster by similar risk/reward profiles
rr_clusters = {
    'conservative': {'min_rr': 1.5, 'max_rr': 2.0, 'max_dd': 0.05},
    'moderate': {'min_rr': 2.0, 'max_rr': 3.0, 'max_dd': 0.10},
    'aggressive': {'min_rr': 3.0, 'max_rr': 5.0, 'max_dd': 0.20}
}
```

#### **4. CIL Learning Components**

#### **1. PredictionTracker (New Raw Team Member)**
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

#### **2. OutcomeAnalysisEngine (New CIL Engine)**
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

#### **3. ConditionalPlanManager (New CIL Engine)**
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

## **Database Schema Updates**

### **Enhanced AD_strands Table**
```sql
-- Add new columns for learning system
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS pattern_type TEXT;  -- High-level pattern classification
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS persistence_score DECIMAL(5,4);
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS novelty_score DECIMAL(5,4);
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS surprise_rating DECIMAL(5,4);
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
ALTER TABLE AD_strands ADD COLUMN IF NOT EXISTS context_vector VECTOR(1536);

-- New indexes for learning
CREATE INDEX IF NOT EXISTS idx_ad_strands_pattern_type ON AD_strands(pattern_type);
CREATE INDEX IF NOT EXISTS idx_ad_strands_persistence_score ON AD_strands(persistence_score);
CREATE INDEX IF NOT EXISTS idx_ad_strands_novelty_score ON AD_strands(novelty_score);
CREATE INDEX IF NOT EXISTS idx_ad_strands_surprise_rating ON AD_strands(surprise_rating);
CREATE INDEX IF NOT EXISTS idx_ad_strands_cluster_key ON AD_strands(cluster_key);
CREATE INDEX IF NOT EXISTS idx_ad_strands_strength_range ON AD_strands(strength_range);
CREATE INDEX IF NOT EXISTS idx_ad_strands_rr_profile ON AD_strands(rr_profile);
CREATE INDEX IF NOT EXISTS idx_ad_strands_market_conditions ON AD_strands(market_conditions);
CREATE INDEX IF NOT EXISTS idx_ad_strands_tracking_status ON AD_strands(tracking_status);
CREATE INDEX IF NOT EXISTS idx_ad_strands_plan_version ON AD_strands(plan_version);
CREATE INDEX IF NOT EXISTS idx_ad_strands_prediction_tracking ON AD_strands(kind, tracking_status) WHERE kind = 'prediction';
CREATE INDEX IF NOT EXISTS idx_ad_strands_context_vector ON AD_strands USING ivfflat (context_vector vector_cosine_ops);
```

### **Pattern Evolution Table**
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

## **Implementation Plan**

### **Phase 1: Universal Learning Foundation ✅ COMPLETED**

1. **✅ Add Universal Score Calculation**
   - ✅ Calculate persistence/novelty/surprise for all strands
   - ✅ Implemented in `universal_scoring.py`
   - ✅ Test score calculation

2. **✅ Add Two-Tier Clustering System**
   - ✅ Implement column clustering (structural grouping)
   - ✅ Integrate existing PatternClusterer (ML-based similarity)
   - ✅ Implemented in `universal_clustering.py`
   - ✅ Test clustering accuracy

3. **✅ Integrate Universal Learning System**
   - ✅ Modify learning system to work directly with strands
   - ✅ Connect two-tier clustering to learning
   - ✅ Implemented in `universal_learning_system.py`
   - ✅ Test end-to-end flow

### **Phase 2: CIL Specialized Learning ✅ COMPLETED**

1. **✅ Add CIL Two-Tier Clustering**
   - ✅ Trading-specific column clustering
   - ✅ Enhanced PatternClusterer for trading features
   - ✅ Strength range classification
   - ✅ R/R profile clustering
   - ✅ Implemented in `cil_clustering.py`

2. **✅ Add Prediction Tracking**
   - ✅ Create PredictionTracker with database-first approach
   - ✅ Market data integration from `alpha_market_data_*.sql` tables
   - ✅ Full prediction lifecycle management
   - ✅ Implemented in `prediction_tracker.py`

3. **✅ Add CIL Learning Components**
   - ✅ Create OutcomeAnalysisEngine
   - ✅ Create ConditionalPlanManager
   - ✅ Create integrated CILLearningSystem
   - ✅ Implemented in `outcome_analysis_engine.py`, `conditional_plan_manager.py`, `cil_learning_system.py`

### **Phase 3: Integration and Testing (IN PROGRESS)**

1. **🔄 Integrate Universal and CIL Learning**
   - Connect universal braids to CIL learning
   - Test full learning pipeline
   - Optimize performance

2. **⏳ Production Testing**
   - Test with real market data
   - Monitor learning performance
   - Fine-tune thresholds

## **Key Features**

### **Universal Learning Features**
- **Everything is Strands** - Consistent data structure
- **Two-Tier Clustering** - Column clustering + ML-based pattern clustering
- **Universal Scoring** - Persistence/novelty/surprise for all
- **Recursive Hierarchy** - Strands → Braids → MetaBraids...
- **Centralized Management** - One place for all learning
- **Existing PatternClusterer Integration** - Leverages sophisticated ML clustering

### **CIL Learning Features**
- **CIL Two-Tier Clustering** - Trading-specific column + enhanced pattern clustering
- **Enhanced PatternClusterer** - Trading-specific features and clustering
- **Prediction Tracking** - Monitor trading outcomes
- **R/R Optimization** - Data-driven parameter tuning
- **Conditional Plan Creation** - Actionable trading strategies
- **Plan Evolution** - Version control and continuous improvement

## **Success Criteria**

### **Universal Learning ✅ ACHIEVED**
- ✅ **All strands get scored** - Persistence, novelty, surprise calculated for all strand types
- ✅ **Two-tier clustering works** - Column clustering + ML-based pattern clustering using existing PatternClusterer
- ✅ **Clusters promote to braids** - When thresholds are met using calculated scores
- ✅ **Learning system works with all strands directly** - No conversion needed, works with raw strands
- ✅ **Recursive hierarchy works** - Braids can cluster into metabraids (braid_level system)
- ✅ **Performance is good** - Clustering is fast enough for real-time use
- ✅ **Database integration** - All learning data persisted in AD_strands table
- ✅ **LLM integration** - Braid creation uses LLM for compression and lesson generation

### **CIL Learning ✅ ACHIEVED**
- ✅ **CIL two-tier clustering works** - Trading-specific column + enhanced pattern clustering
- ✅ **Enhanced PatternClusterer works** - Trading-specific features and ML clustering
- ✅ **Predictions are tracked** - Full lifecycle monitoring with database-first approach
- ✅ **Market data integration** - Fetches current prices from alpha_market_data_*.sql tables
- ✅ **R/R optimization works** - Better risk/reward ratios over time
- ✅ **Conditional plans are created** - Actionable trading strategies
- ✅ **Plans evolve** - Continuous improvement based on outcomes
- ✅ **Integrated system** - CILLearningSystem orchestrates all components

## **Why This Unified Approach is Better**

1. **Eliminates Duplication** - One place for all learning logic
2. **Clear Hierarchy** - Universal foundation + specialized add-ons
3. **Easier to Implement** - One comprehensive plan
4. **Better Architecture** - Clear separation of concerns
5. **Scalable** - Can add more specialized learning systems
6. **Consistent** - Everything is strands, unified scoring
7. **Flexible** - Universal system works with any strand type
8. **Leverages Existing Code** - Uses sophisticated PatternClusterer instead of building new
9. **Two-Tier Approach** - Structural grouping + ML-based pattern similarity
10. **Trading-Specific** - CIL learning builds on universal foundation with trading enhancements

## **What We've Built**

### **✅ Universal Learning Foundation**
- **`universal_scoring.py`** - Calculates persistence/novelty/surprise for all strand types
- **`universal_clustering.py`** - Two-tier clustering (column + ML-based pattern clustering)
- **`universal_learning_system.py`** - Orchestrates universal learning and braid creation
- **Database Integration** - All learning data stored in AD_strands table
- **LLM Integration** - Braid creation uses LLM for compression and lesson generation

### **✅ CIL Specialized Learning**
- **`cil_clustering.py`** - Trading-specific two-tier clustering with enhanced features
- **`prediction_tracker.py`** - Database-first prediction tracking with market data integration
- **`outcome_analysis_engine.py`** - Analyzes prediction outcomes and generates learning insights
- **`conditional_plan_manager.py`** - Manages conditional trading plans and evolution
- **`cil_learning_system.py`** - Orchestrates all CIL learning components

### **✅ Database Schema**
- **Enhanced AD_strands** - Added 13 new columns for learning system
- **Pattern Evolution Table** - Tracks pattern evolution over time
- **Market Data Integration** - Fetches prices from alpha_market_data_*.sql tables
- **Comprehensive Indexing** - Optimized for learning queries

## **Next Steps - Phase 3: Integration and Testing**

1. **🔄 Connect Universal and CIL Learning**
   - Integrate universal braids into CIL learning pipeline
   - Test full learning flow from strands → braids → CIL analysis → conditional plans

2. **🔄 Add Prediction Creation to Raw Data Intelligence**
   - Modify Raw Data Intelligence to create prediction strands
   - Connect prediction creation to market signals

3. **🔄 Production Testing**
   - Test with real market data
   - Monitor learning performance
   - Fine-tune thresholds and parameters

4. **🔄 Performance Optimization**
   - Optimize database queries
   - Improve clustering performance
   - Add monitoring and alerting

This unified approach gives us the best of both worlds: a solid universal learning foundation that works with everything, plus specialized CIL learning that builds on top of it for trading-specific needs.
