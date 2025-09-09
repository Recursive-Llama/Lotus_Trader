# Learning and Clustering Upgrade Plan

## **Overview**

This document outlines a simple upgrade to the existing learning system to work with all strands (not just experiments) and add basic clustering capabilities. This approach is much simpler than the unified clustering system and leverages existing code.

## **Current State**

### **What We Have**
- ✅ **Learning System** - Works with experiment results, creates lessons, manages doctrine
- ✅ **Database Schema** - All strands in `AD_strands` table with 60+ columns
- ✅ **Strand Types** - Raw Data Intelligence, CIL, Trading Plans, etc.
- ✅ **Braid Level System** - `braid_level` column for hierarchy (0=strand, 1=braid, 2=metabraid, 3=meta1braid etc.)

### **What's Missing**
- ❌ **Clustering** - No way to group similar strands
- ❌ **Learning from All Strands** - Only works with experiment results
- ❌ **Persistence/Novelty/Surprise Scores** - Not calculated for all strands
- ❌ **Threshold-based Promotion** - No way to promote clusters to braids

## **The Simple Solution**

### **1. Everything is Strands**
```python
# All strands have the same structure
strand = {
    'id': 'strand_123',
    'kind': 'signal',  # or 'intelligence', 'trading_plan', etc.
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

### **2. Simple Clustering by High-Level Columns**
```python
def cluster_strands_by_similarity(strands, braid_level):
    """Cluster strands of the same level by similarity"""
    clusters = []
    
    for strand in strands:
        if strand.get('braid_level', 0) != braid_level:
            continue  # Only cluster same level
            
        # Find similar cluster based on ALL relevant columns
        similar_cluster = find_similar_cluster(strand, clusters, ALL_RELEVANT_COLUMNS)
        
        if similar_cluster:
            similar_cluster.add_strand(strand)
        else:
            clusters.append(Cluster([strand]))
    
    return clusters
```

### **3. Threshold-based Promotion**
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

### **4. Learning System Integration**
```python
async def promote_cluster_to_braid(cluster):
    """Use learning system to compress cluster into braid"""
    
    # Pass strands directly to learning system - no conversion needed
    braid = await learning_system.process_strands_into_braid(cluster.strands)
    
    return braid
```

## **Implementation Plan**

### **Phase 1: Add Score Calculation (Week 1)**

1. **Add score calculation to all strand creation**
   ```python
   def calculate_strand_scores(strand):
       """Calculate persistence, novelty, surprise for any strand"""
       return {
           'persistence_score': calculate_persistence_score(strand),
           'novelty_score': calculate_novelty_score(strand),
           'surprise_rating': calculate_surprise_rating(strand)
       }
   ```

2. **Update all strand creation points**
   - Raw Data Intelligence agent
   - CIL engines
   - Trading plan creation
   - Experiment results

3. **Test score calculation**
   - Verify scores make sense for different strand types
   - Test with real data

### **Phase 2: Add Basic Clustering (Week 2)**

1. **Create clustering engine**
   ```python
   class SimpleClusteringEngine:
       def __init__(self):
           # Use ALL relevant columns for clustering
           self.clustering_columns = [
               'symbol', 'timeframe', 'agent_id', 'regime', 'session_bucket',
               'pattern_type', 'motif_family', 'strategic_meta_type', 'doctrine_status',
               'autonomy_level', 'directive_type', 'resonance_score', 'phi', 'rho'
               # ... all columns that make sense for clustering
           ]
           self.similarity_threshold = 0.7
           self.promotion_threshold = 0.8
   ```

2. **Add clustering to strand processing**
   - When strand is created, try to cluster it
   - Check if cluster meets threshold
   - If yes, promote to braid

3. **Test clustering**
   - Verify similar strands get clustered together
   - Test threshold-based promotion

### **Phase 3: Integrate Learning System (Week 3)**

1. **Modify learning system to work directly with strands**
   ```python
   async def process_strands_into_braid(self, strands):
       """Process any strands directly into a braid - no conversion needed"""
       # Calculate aggregate metrics directly from strands
       # Determine doctrine status directly from strands
       # Create braid directly from strands
       # Return braid
   ```

2. **Connect clustering to learning**
   - When cluster meets threshold, call learning system
   - Learning system returns braid directly
   - Save braid to database

3. **Test end-to-end flow**
   - Strands → Clustering → Threshold → Learning → Braid

### **Phase 4: Production Testing (Week 4)**

1. **Real data testing**
   - Test with live market data
   - Verify clustering works correctly
   - Test learning system integration

2. **Performance optimization**
   - Ensure clustering is fast enough
   - Optimize database queries

3. **Monitoring and alerting**
   - Track clustering performance
   - Monitor braid creation rate

## **Score Calculation Details**

### **Persistence Score** (How reliable/consistent is this pattern?)
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
    
    # Default
    else:
        return strand.get('sig_confidence', 0.5)
```

### **Novelty Score** (How unique/new is this pattern?)
```python
def calculate_novelty_score(strand):
    """Calculate novelty based on strand type"""
    
    # For Raw Data Intelligence strands
    if strand.get('agent_id') == 'raw_data_intelligence':
        pattern_type = strand.get('module_intelligence', {}).get('pattern_type', 'unknown')
        surprise = strand.get('module_intelligence', {}).get('surprise_rating', 0.0)
        
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
    
    # Default
    else:
        return 0.5
```

### **Surprise Rating** (How unexpected was this outcome?)
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
    
    # Default
    else:
        return 0.3
```

## **Why This Is Much Simpler**

1. **Reuses Existing Code** - Learning system already works, just needs to work with strands directly
2. **Simple Clustering** - Just group by all relevant columns, no complex algorithms
3. **No Conversion Needed** - Learning system works directly with strands, no lesson objects
4. **No New Database Tables** - Uses existing `AD_strands` table
5. **No Migration** - Works with existing data
6. **Incremental** - Can implement piece by piece
7. **Fast** - Simple similarity calculation, no complex clustering
8. **Consistent** - Everything is strands, no special objects

## **Success Criteria**

- ✅ **All strands get scored** - Persistence, novelty, surprise calculated
- ✅ **Similar strands cluster together** - Based on all relevant columns
- ✅ **Clusters promote to braids** - When thresholds are met
- ✅ **Learning system works with all strands directly** - No conversion needed
- ✅ **Recursive hierarchy works** - Braids can cluster into metabraids
- ✅ **Performance is good** - Clustering is fast enough for real-time use

## **Next Steps**

1. **Review and approve** this simple approach
2. **Start with Phase 1** - Add score calculation to all strands
3. **Test score calculation** - Verify scores make sense
4. **Add basic clustering** - Simple similarity-based grouping
5. **Integrate learning system** - Make it work directly with strands
6. **Test end-to-end** - Verify full flow works

This approach is much simpler than the unified clustering system and leverages all the existing work we've already done!
