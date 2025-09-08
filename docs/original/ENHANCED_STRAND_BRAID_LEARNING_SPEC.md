# Enhanced Strand-Braid Learning Specification

*Integration of strand-braid learning system into Alpha Detector Module*

## Overview

This specification enhances the existing Alpha Detector learning system by adding **strand-braid learning** capabilities. The enhancement integrates seamlessly with the current learning architecture, adding hierarchical learning and LLM-generated lessons while maintaining the existing single-table structure.

## Current Learning System Integration

### **Existing Learning Architecture (90% Complete)**
```python
# Current Alpha Detector Learning (already implemented)
class AlphaDetectorLearning:
    def __init__(self):
        self.performance_history = []
        self.learning_rate = 0.01
        self.adaptation_threshold = 0.1
        self.curator_learning = CuratorLearning()
        self.dsi_learning = DSILearning()
        self.pattern_learning = PatternLearning()
    
    def update_performance(self, plan_id, outcome):
        """Update performance based on trading outcome"""
        self.performance_history.append({
            'plan_id': plan_id,
            'outcome': outcome,
            'timestamp': datetime.now()
        })
        
        # Trigger learning if performance degrades
        if self.performance_degraded():
            self.adapt_parameters()
    
    def analyze_performance_patterns(self):
        """Analyze performance to identify improvement patterns"""
        recent_performance = self.get_recent_performance(days=30)
        
        patterns = []
        
        # Analyze signal quality patterns
        signal_quality_pattern = self.analyze_signal_quality(recent_performance)
        if signal_quality_pattern:
            patterns.append(signal_quality_pattern)
        
        # Analyze curator performance patterns
        curator_performance_pattern = self.analyze_curator_performance(recent_performance)
        if curator_performance_pattern:
            patterns.append(curator_performance_pattern)
        
        # Analyze DSI performance patterns
        dsi_performance_pattern = self.analyze_dsi_performance(recent_performance)
        if dsi_performance_pattern:
            patterns.append(dsi_performance_pattern)
        
        return patterns
```

### **Enhanced Learning Architecture (100% Complete)**
```python
# Enhanced Alpha Detector Learning with Strand-Braid System
class EnhancedAlphaDetectorLearning(AlphaDetectorLearning):
    def __init__(self):
        super().__init__()
        # Add strand-braid learning components
        self.strand_braid_learning = StrandBraidLearning()
        self.llm_lesson_generator = LLMLessonGenerator()
        self.braid_threshold = 3.0  # Configurable threshold
    
    def update_performance(self, plan_id, outcome):
        """Enhanced performance update with strand-braid learning"""
        # Call existing performance update
        super().update_performance(plan_id, outcome)
        
        # Add strand-braid learning
        self.strand_braid_learning.update_strand_performance(plan_id, outcome)
        
        # Trigger braid creation if needed
        self.check_and_create_braids()
    
    def check_and_create_braids(self):
        """Check for braid creation opportunities"""
        # Get recent strands from AD_strands table
        recent_strands = self.get_recent_strands(days=30)
        
        # Cluster strands by similarity
        clusters = self.strand_braid_learning.cluster_strands(recent_strands)
        
        # Create braids for clusters above threshold
        for cluster in clusters:
            if cluster.accumulated_score >= self.braid_threshold:
                self.create_braid_strand(cluster)
```

## Strand-Braid Learning System

### **1. Strand Clustering (Automatic)**
```python
class StrandBraidLearning:
    def __init__(self, module_type='alpha_detector'):
        self.module_type = module_type
        self.clustering_columns = ['symbol', 'timeframe', 'regime', 'session_bucket']
        self.scoring_weights = {
            'sig_sigma': 0.4,      # Signal strength weight
            'sig_confidence': 0.3,  # Signal confidence weight
            'outcome_score': 0.3    # Performance outcome weight
        }
    
    def cluster_strands(self, strands):
        """Cluster strands by similarity using top-level columns"""
        clusters = {}
        
        for strand in strands:
            # Create clustering key from top-level columns
            clustering_key = self._create_clustering_key(strand)
            
            if clustering_key not in clusters:
                clusters[clustering_key] = {
                    'strands': [],
                    'accumulated_score': 0.0,
                    'clustering_columns': clustering_key
                }
            
            clusters[clustering_key]['strands'].append(strand)
            clusters[clustering_key]['accumulated_score'] += self._calculate_strand_score(strand)
        
        return clusters
    
    def _create_clustering_key(self, strand):
        """Create clustering key from top-level columns"""
        return (
            strand.get('symbol', 'UNKNOWN'),
            strand.get('timeframe', 'UNKNOWN'),
            strand.get('regime', 'UNKNOWN'),
            strand.get('session_bucket', 'UNKNOWN')
        )
    
    def _calculate_strand_score(self, strand):
        """Calculate strand score using existing scoring system"""
        score = 0.0
        
        # Signal strength score
        sig_sigma = strand.get('sig_sigma', 0.0)
        score += sig_sigma * self.scoring_weights['sig_sigma']
        
        # Signal confidence score
        sig_confidence = strand.get('sig_confidence', 0.0)
        score += sig_confidence * self.scoring_weights['sig_confidence']
        
        # Performance outcome score (from curator_feedback)
        curator_feedback = strand.get('curator_feedback', {})
        outcome_score = curator_feedback.get('overall_score', 0.0)
        score += outcome_score * self.scoring_weights['outcome_score']
        
        return score
```

### **2. Braid Creation (Same Table)**
```python
def create_braid_strand(self, cluster):
    """Create braid strand in AD_strands table"""
    
    # Send to LLM for lesson generation
    lesson = self.llm_lesson_generator.generate_lesson(cluster['strands'])
    
    # Create braid strand entry (same table structure)
    braid_strand = {
        'id': f"AD_braid_{uuid.uuid4().hex[:12]}",
        'lifecycle_id': f"braid_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'parent_id': None,  # Braids don't have parent strands
        'module': 'alpha',
        'kind': 'braid',  # Tag as braid
        'symbol': cluster['clustering_columns'][0],
        'timeframe': cluster['clustering_columns'][1],
        'session_bucket': cluster['clustering_columns'][3],
        'regime': cluster['clustering_columns'][2],
        
        # Signal data (aggregated from source strands)
        'sig_sigma': self._calculate_aggregated_sigma(cluster['strands']),
        'sig_confidence': self._calculate_aggregated_confidence(cluster['strands']),
        'sig_direction': self._determine_aggregated_direction(cluster['strands']),
        
        # Trading plan data (contains lesson)
        'trading_plan': {
            'lesson': lesson,
            'source_strands': [strand['id'] for strand in cluster['strands']],
            'accumulated_score': cluster['accumulated_score'],
            'cluster_columns': cluster['clustering_columns'],
            'strand_count': len(cluster['strands']),
            'braid_level': 'braid'
        },
        
        # Signal pack (LLM-optimized lesson summary)
        'signal_pack': {
            'signal_type': 'braid_lesson',
            'pattern_detected': lesson.get('pattern_name', 'unknown'),
            'direction': self._determine_aggregated_direction(cluster['strands']),
            'points_of_interest': lesson.get('key_insights', []),
            'confidence_score': cluster['accumulated_score'] / len(cluster['strands'])
        },
        
        # Intelligence data (braid-specific)
        'dsi_evidence': {
            'braid_evidence': lesson.get('evidence_summary', {}),
            'source_evidence': [strand.get('dsi_evidence', {}) for strand in cluster['strands']]
        },
        
        'regime_context': {
            'braid_regime': cluster['clustering_columns'][2],
            'source_regimes': [strand.get('regime', 'unknown') for strand in cluster['strands']]
        },
        
        'event_context': {
            'braid_events': lesson.get('event_patterns', []),
            'source_events': [strand.get('event_context', {}) for strand in cluster['strands']]
        },
        
        # Module intelligence (braid-specific)
        'module_intelligence': {
            'braid_intelligence': lesson.get('intelligence_summary', {}),
            'learning_insights': lesson.get('learning_insights', []),
            'recommendations': lesson.get('recommendations', [])
        },
        
        'curator_feedback': {
            'braid_feedback': lesson.get('curator_insights', {}),
            'source_feedback': [strand.get('curator_feedback', {}) for strand in cluster['strands']]
        },
        
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }
    
    # Insert into AD_strands table
    self.insert_strand(braid_strand)
    
    return braid_strand
```

### **3. LLM Lesson Generation**
```python
class LLMLessonGenerator:
    def __init__(self):
        self.llm_client = LLMClient()
        self.lesson_prompt_template = self._load_lesson_prompt_template()
    
    def generate_lesson(self, strands):
        """Generate lesson from clustered strands"""
        
        # Prepare context for LLM
        context = self._prepare_lesson_context(strands)
        
        # Generate lesson using LLM
        lesson = self.llm_client.generate_lesson(context)
        
        return lesson
    
    def _prepare_lesson_context(self, strands):
        """Prepare context for LLM lesson generation"""
        context = {
            'strands': strands,
            'common_patterns': self._extract_common_patterns(strands),
            'success_factors': self._extract_success_factors(strands),
            'failure_factors': self._extract_failure_factors(strands),
            'market_conditions': self._extract_market_conditions(strands),
            'performance_metrics': self._extract_performance_metrics(strands)
        }
        
        return context
    
    def _extract_common_patterns(self, strands):
        """Extract common patterns from strands"""
        patterns = {
            'signal_strengths': [s.get('sig_sigma', 0.0) for s in strands],
            'confidence_scores': [s.get('sig_confidence', 0.0) for s in strands],
            'directions': [s.get('sig_direction', 'unknown') for s in strands],
            'timeframes': [s.get('timeframe', 'unknown') for s in strands],
            'regimes': [s.get('regime', 'unknown') for s in strands]
        }
        return patterns
    
    def _extract_success_factors(self, strands):
        """Extract success factors from strands"""
        success_factors = []
        for strand in strands:
            curator_feedback = strand.get('curator_feedback', {})
            if curator_feedback.get('overall_score', 0.0) > 0.7:
                success_factors.append({
                    'strand_id': strand['id'],
                    'success_elements': curator_feedback.get('success_elements', [])
                })
        return success_factors
```

## Database Schema Updates

### **AD_strands Table (Updated)**
```sql
-- Alpha Detector strands table (renamed from sig_strand)
CREATE TABLE AD_strands (
    id TEXT PRIMARY KEY,                     -- ULID
    lifecycle_id TEXT,                       -- Thread identifier
    parent_id TEXT,                          -- Linkage to parent strand
    module TEXT DEFAULT 'alpha',             -- Module identifier
    kind TEXT,                               -- 'signal'|'trading_plan'|'intelligence'|'braid'|'meta_braid'|'meta2_braid'
    symbol TEXT,                             -- Trading symbol
    timeframe TEXT,                          -- '1m'|'5m'|'15m'|'1h'|'4h'|'1d'
    session_bucket TEXT,                     -- Session identifier
    regime TEXT,                             -- Market regime
    
    -- Signal data
    sig_sigma FLOAT8,                        -- Signal strength (0-1)
    sig_confidence FLOAT8,                   -- Signal confidence (0-1)
    sig_direction TEXT,                      -- 'long'|'short'|'neutral'
    
    -- Trading plan data
    trading_plan JSONB,                      -- Complete trading plan OR braid lesson
    signal_pack JSONB,                       -- Signal pack for LLM consumption
    
    -- Intelligence data
    dsi_evidence JSONB,                      -- DSI evidence
    regime_context JSONB,                    -- Regime context
    event_context JSONB,                     -- Event context
    
    -- Module intelligence
    module_intelligence JSONB,               -- Module-specific intelligence
    curator_feedback JSONB,                  -- Curator evaluation results
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_AD_strands_symbol_time ON AD_strands(symbol, created_at DESC);
CREATE INDEX idx_AD_strands_lifecycle ON AD_strands(lifecycle_id);
CREATE INDEX idx_AD_strands_kind ON AD_strands(kind);
CREATE INDEX idx_AD_strands_sigma ON AD_strands(sig_sigma);
CREATE INDEX idx_AD_strands_braid_level ON AD_strands((trading_plan->>'braid_level'));
```

## Integration with Existing System

### **1. Seamless Integration**
The strand-braid learning system integrates seamlessly with the existing Alpha Detector learning system:

- **Same Table**: Uses existing `AD_strands` table
- **Same Learning Flow**: Enhances existing `update_performance()` method
- **Same Pattern Analysis**: Builds on existing `analyze_performance_patterns()`
- **Same Scoring**: Uses existing `sig_sigma`, `sig_confidence`, and `curator_feedback` scores

### **2. Enhanced Learning Flow**
```python
# Enhanced learning flow
def enhanced_learning_flow(self, plan_id, outcome):
    # 1. Existing performance update
    self.update_performance(plan_id, outcome)
    
    # 2. Existing pattern analysis
    patterns = self.analyze_performance_patterns()
    
    # 3. Existing parameter adaptation
    self.adapt_parameters(patterns)
    
    # 4. NEW: Strand-braid learning
    self.strand_braid_learning.update_strand_performance(plan_id, outcome)
    
    # 5. NEW: Check for braid creation
    self.check_and_create_braids()
```

### **3. Backward Compatibility**
The enhancement maintains full backward compatibility:

- **Existing Code**: All existing learning code continues to work
- **Existing Data**: All existing data remains accessible
- **Existing Queries**: All existing queries continue to work
- **New Features**: Braid functionality is additive, not replacing

## Configuration

### **Strand-Braid Learning Configuration**
```yaml
strand_braid_learning:
  enabled: true
  braid_threshold: 3.0
  clustering_columns:
    - 'symbol'
    - 'timeframe'
    - 'regime'
    - 'session_bucket'
  scoring_weights:
    sig_sigma: 0.4
    sig_confidence: 0.3
    outcome_score: 0.3
  llm_integration:
    enabled: true
    model: 'gpt-4'
    max_tokens: 1000
    temperature: 0.7
  braid_levels:
    braid: 3.0
    meta_braid: 9.0
    meta2_braid: 27.0
```

## Success Metrics

### **Learning Enhancement Metrics**
- **Braid Creation Rate**: Number of braids created per day
- **Lesson Quality Score**: LLM-generated lesson quality (0-1)
- **Pattern Recognition Improvement**: Improvement in pattern detection accuracy
- **Learning Effectiveness**: Overall learning system effectiveness improvement

### **Integration Metrics**
- **Backward Compatibility**: 100% existing functionality preserved
- **Performance Impact**: <5% performance overhead
- **Data Consistency**: 100% data integrity maintained
- **System Stability**: No disruption to existing operations

---

*This specification seamlessly integrates strand-braid learning into the existing Alpha Detector learning system, adding hierarchical learning and LLM-generated lessons while maintaining full backward compatibility.*
