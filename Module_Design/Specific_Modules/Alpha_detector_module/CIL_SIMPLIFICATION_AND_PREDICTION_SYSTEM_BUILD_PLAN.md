# CIL Simplification and Prediction System Build Plan

## **Overview**

This document outlines the complete build plan for simplifying the Central Intelligence Layer (CIL) and implementing a comprehensive prediction system with dual code/LLM predictions, pattern recognition, and continuous learning.

## **Current State Analysis**

### **What We Have**
- ✅ **Raw Data Intelligence Agent** - Working with team coordination and LLM meta-analysis
- ✅ **Strand Creation System** - Individual and overview strands
- ✅ **Database Schema** - AD_strands table with 60+ columns
- ✅ **Learning System** - Basic learning from experiment results
- ✅ **Clustering Thresholds** - 5+ strands, 0.6+ persistence, 0.5+ novelty, 0.4+ surprise

### **What Needs Simplification**
- ❌ **CIL Complexity** - 16 components (8 core + 6 missing + 2 additional)
- ❌ **No Prediction System** - No systematic prediction creation and tracking
- ❌ **No Pattern Recognition** - No immediate pattern recognition from strands
- ❌ **Limited Learning** - Only works with experiment results, not all strands

## **Simplified Architecture**

### **Core CIL Components (Keep)**
1. **Prediction Engine** - Main prediction creation and tracking engine
2. **Learning System** - Continuous learning from every prediction (with thresholds)
3. **Prediction Tracker** - Track all predictions and outcomes
4. **Outcome Analysis** - Analyze completed predictions
5. **Conditional Plan Manager** - Create trading plans from confident patterns
6. **DatabaseDrivenContextSystem** - Single context system with filters (existing)
7. **Pattern Grouping System** - Group patterns by 5-minute cycles and asset combinations

### **Advanced CIL Components (Move to Advanced_CIL module)**
1. **Why-Map Generator**
2. **Confluence Graph Builder**
3. **Experiment Grammar**
4. **Resonance Prioritization**
5. **Lineage & Provenance**
6. **Global Synthesis Engine**
7. **Experiment Orchestration**
8. **System Resonance Manager**

## **Prediction System Design**

### **1. Kind Alignment System**

**Raw Data Intelligence Outputs:**
- `kind: 'pattern'` - Individual pattern strands from analyzers
- `kind: 'pattern_overview'` - Overview strands (tagged for CIL with `tags: ['cil']`)

**Prediction Engine Outputs:**
- `kind: 'prediction'` - Individual predictions
- `kind: 'prediction_review'` - Overview of prediction outcomes

**Context System Usage:**
- **Pattern Detection**: Filter by `kind: 'pattern'` to find similar patterns
- **Prediction Creation**: Filter by `kind: 'prediction_review'` to find historical outcomes

### **2. Single Context System (Simplified)**

#### **DatabaseDrivenContextSystem with Filters**

**Single Context System for All Needs:**
- **Pattern Detection**: Filter by `kind: 'pattern'` to find similar patterns
- **Prediction Creation**: Filter by `kind: 'prediction'` to find historical outcomes
- **Same System**: One `DatabaseDrivenContextSystem` with different filters
- **Simpler**: No need for two separate context systems

```python
class PredictionEngine:
    def __init__(self, db_manager: SupabaseManager):
        self.context_system = DatabaseDrivenContextSystem(db_manager)
    
    async def get_pattern_context(self, pattern):
        """Get context for pattern detection - 'Have we seen this pattern before?'"""
        return await self.context_system.get_relevant_context({
            'kind': 'pattern',
            'pattern_type': pattern['type'],
            'asset': pattern['symbol'],
            'timeframe': pattern['timeframe']
        })
    
    async def get_prediction_context(self, pattern_group):
        """Get context for prediction creation - exact + similar matches"""
        
        # 1. Get exact group matches
        exact_context = await self.get_exact_group_context(pattern_group)
        
        # 2. Get similar group matches (70% similarity threshold)
        similar_context = await self.get_similar_group_context(pattern_group)
        
        # 3. Combine and score confidence
        combined_context = {
            'exact_matches': exact_context,
            'similar_matches': similar_context,
            'exact_count': len(exact_context),
            'similar_count': len(similar_context),
            'confidence_level': self.calculate_confidence_level(exact_context, similar_context)
        }
        
        return combined_context
    
    async def get_exact_group_context(self, pattern_group):
        """Get exact group signature matches"""
        group_signature = self.create_group_signature(pattern_group)
        
        return await self.context_system.get_relevant_context({
            'kind': 'prediction_review',
            'group_signature': group_signature,
            'asset': pattern_group['asset']
        })
    
    async def get_similar_group_context(self, pattern_group):
        """Get similar groups with 70% similarity threshold"""
        
        # Query for similar groups (same asset, overlapping pattern types)
        similar_groups = await self.context_system.get_relevant_context({
            'kind': 'prediction_review',
            'asset': pattern_group['asset'],
            'pattern_types': pattern_group['pattern_types']
        })
        
        # Score similarity for each group
        scored_groups = []
        for group in similar_groups:
            similarity_score = self.calculate_similarity_score(pattern_group, group)
            if similarity_score >= 0.7:  # 70% similarity threshold
                scored_groups.append({
                    'group': group,
                    'similarity_score': similarity_score,
                    'match_type': 'similar',
                    'differences': self.identify_differences(pattern_group, group)
                })
        
        return scored_groups
    
    def calculate_similarity_score(self, current_group, historical_group):
        """Calculate similarity score between groups"""
        
        # Pattern type overlap
        current_types = set(p['pattern_type'] for p in current_group['patterns'])
        historical_types = set(p['pattern_type'] for p in historical_group['patterns'])
        pattern_overlap = len(current_types.intersection(historical_types)) / len(current_types.union(historical_types))
        
        # Timeframe overlap
        current_timeframes = set(p['timeframe'] for p in current_group['patterns'])
        historical_timeframes = set(p['timeframe'] for p in historical_group['patterns'])
        timeframe_overlap = len(current_timeframes.intersection(historical_timeframes)) / len(current_timeframes.union(historical_timeframes))
        
        # Cycle proximity (within 10x timeframe)
        cycle_proximity = self.calculate_cycle_proximity(current_group, historical_group)
        
        # Weighted similarity score
        similarity_score = (
            pattern_overlap * 0.5 +      # 50% weight on pattern types
            timeframe_overlap * 0.3 +    # 30% weight on timeframes
            cycle_proximity * 0.2        # 20% weight on cycle proximity
        )
        
        return similarity_score
    
    def identify_differences(self, current_group, historical_group):
        """Identify specific differences between groups"""
        differences = []
        
        # Pattern type differences
        current_types = set(p['pattern_type'] for p in current_group['patterns'])
        historical_types = set(p['pattern_type'] for p in historical_group['patterns'])
        
        if current_types != historical_types:
            differences.append(f"Pattern types: {current_types} vs {historical_types}")
        
        # Timeframe differences
        current_timeframes = set(p['timeframe'] for p in current_group['patterns'])
        historical_timeframes = set(p['timeframe'] for p in historical_group['patterns'])
        
        if current_timeframes != historical_timeframes:
            differences.append(f"Timeframes: {current_timeframes} vs {historical_timeframes}")
        
        return differences
```

### **2. Dual Prediction Creation (Code + LLM)**

```python
class PredictionEngine:
    async def create_prediction(self, pattern_group):
        """Create both code and LLM predictions with outcome-based context"""
        
        # 1. Get prediction context (exact + similar matches)
        prediction_context = await self.get_prediction_context(pattern_group)
        
        # 2. Create code prediction using historical outcomes
        code_prediction = await self.create_code_prediction(pattern_group, prediction_context)
        
        # 3. Create LLM prediction using historical outcomes
        llm_prediction = await self.create_llm_prediction(pattern_group, prediction_context)
        
        # 4. Create prediction with clear similarity indicators
        prediction = self.create_prediction_with_similarity_context(pattern_group, prediction_context, code_prediction, llm_prediction)
        
        # 5. Store prediction as strand
        prediction_strand = await self.create_prediction_strand(prediction)
        
        return prediction_strand['id']
    
    def create_prediction_with_similarity_context(self, pattern_group, context, code_prediction, llm_prediction):
        """Create prediction with clear similarity indicators"""
        
        # Determine match quality
        match_quality = self.determine_match_quality(context)
        
        # Generate prediction notes
        prediction_notes = self.generate_prediction_notes(context)
        
        prediction = {
            'pattern_group': pattern_group,
            'code_prediction': code_prediction,
            'llm_prediction': llm_prediction,
            'context_metadata': {
                'exact_matches': context['exact_count'],
                'similar_matches': context['similar_count'],
                'confidence_level': context['confidence_level'],
                'similarity_scores': [g['similarity_score'] for g in context['similar_matches']],
                'match_quality': match_quality,
                'differences': self.get_all_differences(context['similar_matches'])
            },
            'prediction_notes': prediction_notes,
            'kind': 'prediction',
            'tracking_status': 'active'
        }
        
        return prediction
    
    def generate_prediction_notes(self, context):
        """Generate clear notes about match quality"""
        
        if context['exact_count'] > 0:
            return f"Based on {context['exact_count']} exact matches"
        elif context['similar_count'] > 0:
            avg_similarity = sum(g['similarity_score'] for g in context['similar_matches']) / len(context['similar_matches'])
            return f"Based on {context['similar_count']} similar matches (avg similarity: {avg_similarity:.2f}) - NOT EXACT MATCH"
        else:
            return "No historical matches - first prediction for this group"
    
    def determine_match_quality(self, context):
        """Determine overall match quality"""
        if context['exact_count'] > 0:
            return 'exact'
        elif context['similar_count'] > 0:
            return 'similar'
        else:
            return 'first_time'
    
    def get_all_differences(self, similar_matches):
        """Get all differences from similar matches"""
        all_differences = []
        for match in similar_matches:
            all_differences.extend(match['differences'])
        return list(set(all_differences))  # Remove duplicates
```

### **2. Prediction Structure**

```python
class Prediction:
    def __init__(self, pattern):
        self.pattern_id = pattern['id']
        self.asset = pattern['symbol']
        self.pattern_type = pattern['type']
        self.timeframe = pattern['timeframe']
        self.confidence = pattern['confidence']
        
        # Trading parameters
        self.entry_price = pattern['current_price']
        self.exit_price = None
        self.stop_loss = None
        self.prediction_duration = self.calculate_duration(timeframe)  # 20x timeframe
        
        # Analysis parameters
        self.entry_time = datetime.now(timezone.utc)
        self.exit_time = None
        self.status = 'active'
        
        # Historical context
        self.historical_context = None
        self.prediction_method = None  # 'code' or 'llm'
```

### **3. Timeframe Duration Calculation**

```python
def calculate_duration(timeframe):
    """Calculate prediction duration as 20x the timeframe"""
    durations = {
        '1m': timedelta(minutes=20),
        '5m': timedelta(minutes=100),  # 1h 40m
        '15m': timedelta(hours=5),     # 5 hours
        '1h': timedelta(hours=20),     # 20 hours
        '4h': timedelta(days=3.33),    # ~3.3 days
        '1d': timedelta(days=20)       # 20 days
    }
    return durations.get(timeframe, timedelta(hours=1))
```

## **Pattern Grouping System**

### **6 Categories of Pattern Grouping (Important for Multi-Pattern Analysis)**

```python
class PatternGroupingSystem:
    def group_patterns(self, patterns, overview_cycle):
        """Group patterns into 6 categories for multi-pattern analysis"""
        
        asset_groups = self.group_by_asset(patterns)
        grouped_patterns = {}
        
        for asset, asset_patterns in asset_groups.items():
            grouped_patterns[asset] = {
                # A. Single patterns, single timeframe, same cycle
                'single_single': self.get_single_patterns_single_timeframe(asset_patterns, overview_cycle),
                
                # B. Multiple patterns, single timeframe, same cycle
                'multi_single': self.get_multiple_patterns_single_timeframe(asset_patterns, overview_cycle),
                
                # C. Single patterns, multiple timeframes, same cycle
                'single_multi': self.get_single_patterns_multiple_timeframes(asset_patterns, overview_cycle),
                
                # D. Multiple patterns, multiple timeframes, same cycle
                'multi_multi': self.get_multiple_patterns_multiple_timeframes(asset_patterns, overview_cycle),
                
                # E. Single patterns, single timeframe, multiple cycles
                'single_multi_cycle': self.get_single_patterns_multiple_cycles(asset_patterns, overview_cycle),
                
                # F. Multiple patterns, multiple cycles
                'multi_multi_cycle': self.get_multiple_patterns_multiple_cycles(asset_patterns, overview_cycle)
            }
        
        return grouped_patterns
```

### **Why Pattern Grouping is Important:**

1. **Single Pattern Analysis**: Individual patterns by `pattern_type` + `asset` + `timeframe`
2. **Multi-Pattern Analysis**: Exact pattern groups by `asset` + `timeframe` + `5-minute cycle`
3. **Pattern Group Recognition**: When we see the **exact same group** again, we recognize it
4. **Historical Performance**: Use performance of that **exact group**, not just individual patterns
5. **Combination Analysis**: Volume spike + divergence in same 5-minute cycle = one group
6. **Group-Based Predictions**: Create predictions for **pattern groups**, not just individual patterns

### **How Pattern Grouping Works (All 6 Categories):**

```python
class PatternGroupingSystem:
    def extract_pattern_groups_from_overview(self, overview_strand):
        """Extract pattern groups from pattern_overview strand - all 6 categories"""
        
        # 1. Get linked individual patterns from overview
        individual_patterns = self.get_linked_patterns(overview_strand)
        
        # 2. Group by asset first
        asset_groups = self.group_by_asset(individual_patterns)
        
        # 3. For each asset, create all 6 grouping categories
        all_pattern_groups = {}
        
        for asset, asset_patterns in asset_groups.items():
            all_pattern_groups[asset] = {
                # A. Single patterns, single timeframe, same cycle
                'single_single': self.group_single_single(asset_patterns),
                
                # B. Multiple patterns, single timeframe, same cycle
                'multi_single': self.group_multi_single(asset_patterns),
                
                # C. Single patterns, multiple timeframes, same cycle
                'single_multi': self.group_single_multi(asset_patterns),
                
                # D. Multiple patterns, multiple timeframes, same cycle
                'multi_multi': self.group_multi_multi(asset_patterns),
                
                # E. Single patterns, single timeframe, multiple cycles
                'single_multi_cycle': self.group_single_multi_cycle(asset_patterns),
                
                # F. Multiple patterns, multiple cycles
                'multi_multi_cycle': self.group_multi_multi_cycle(asset_patterns)
            }
        
        return all_pattern_groups
    
    def group_single_single(self, patterns):
        """A. Single patterns, single timeframe, same cycle"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['pattern_type']}_{pattern['timeframe']}_{pattern['cycle_time']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'single_single',
                    'asset': pattern['asset'],
                    'timeframe': pattern['timeframe'],
                    'cycle_time': pattern['cycle_time'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        return groups
    
    def group_multi_single(self, patterns):
        """B. Multiple patterns, single timeframe, same cycle"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['timeframe']}_{pattern['cycle_time']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'multi_single',
                    'asset': pattern['asset'],
                    'timeframe': pattern['timeframe'],
                    'cycle_time': pattern['cycle_time'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple patterns
        return {k: v for k, v in groups.items() if len(v['patterns']) > 1}
    
    def group_single_multi(self, patterns):
        """C. Single patterns, multiple timeframes, same cycle"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['pattern_type']}_{pattern['cycle_time']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'single_multi',
                    'asset': pattern['asset'],
                    'pattern_type': pattern['pattern_type'],
                    'cycle_time': pattern['cycle_time'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple timeframes
        return {k: v for k, v in groups.items() if len(set(p['timeframe'] for p in v['patterns'])) > 1}
    
    def group_multi_multi(self, patterns):
        """D. Multiple patterns, multiple timeframes, same cycle"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['cycle_time']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'multi_multi',
                    'asset': pattern['asset'],
                    'cycle_time': pattern['cycle_time'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple patterns AND multiple timeframes
        return {k: v for k, v in groups.items() 
                if len(v['patterns']) > 1 and len(set(p['timeframe'] for p in v['patterns'])) > 1}
    
    def group_single_multi_cycle(self, patterns):
        """E. Single patterns, single timeframe, multiple cycles"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['pattern_type']}_{pattern['timeframe']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'single_multi_cycle',
                    'asset': pattern['asset'],
                    'pattern_type': pattern['pattern_type'],
                    'timeframe': pattern['timeframe'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple cycles
        return {k: v for k, v in groups.items() if len(set(p['cycle_time'] for p in v['patterns'])) > 1}
    
    def group_multi_multi_cycle(self, patterns):
        """F. Multiple patterns, multiple cycles"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['asset']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'multi_multi_cycle',
                    'asset': pattern['asset'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple patterns AND multiple cycles
        return {k: v for k, v in groups.items() 
                if len(v['patterns']) > 1 and len(set(p['cycle_time'] for p in v['patterns'])) > 1}
    
    def create_group_signature(self, pattern_group):
        """Create unique signature for pattern group (excludes exact cycle numbers)"""
        group_type = pattern_group['group_type']
        
        if group_type == 'single_single':
            return f"{pattern_group['asset']}_{pattern_group['timeframe']}_{pattern_group['patterns'][0]['pattern_type']}"
        
        elif group_type == 'multi_single':
            pattern_types = sorted([p['pattern_type'] for p in pattern_group['patterns']])
            return f"{pattern_group['asset']}_{pattern_group['timeframe']}_{'_'.join(pattern_types)}"
        
        elif group_type == 'single_multi':
            timeframes = sorted([p['timeframe'] for p in pattern_group['patterns']])
            return f"{pattern_group['asset']}_{pattern_group['pattern_type']}_{'_'.join(timeframes)}"
        
        elif group_type == 'multi_multi':
            pattern_types = sorted([p['pattern_type'] for p in pattern_group['patterns']])
            timeframes = sorted([p['timeframe'] for p in pattern_group['patterns']])
            return f"{pattern_group['asset']}_{'_'.join(pattern_types)}_{'_'.join(timeframes)}"
        
        elif group_type == 'single_multi_cycle':
            # Count cycles, not specific cycle times
            cycle_count = len(set(p['cycle_time'] for p in pattern_group['patterns']))
            return f"{pattern_group['asset']}_{pattern_group['pattern_type']}_{pattern_group['timeframe']}_cycles_{cycle_count}"
        
        elif group_type == 'multi_multi_cycle':
            pattern_types = sorted([p['pattern_type'] for p in pattern_group['patterns']])
            cycle_count = len(set(p['cycle_time'] for p in pattern_group['patterns']))
            return f"{pattern_group['asset']}_{'_'.join(pattern_types)}_cycles_{cycle_count}"
```

### **Timeframe Weighting**

```python
def calculate_timeframe_weight(timeframe):
    """Higher timeframes hold significantly more weight"""
    weights = {
        '1m': 1.0,
        '5m': 2.0,
        '15m': 5.0,
        '1h': 10.0,
        '4h': 20.0,
        '1d': 50.0
    }
    return weights.get(timeframe, 1.0)
```

## **Prediction Analysis System**

### **Comprehensive Outcome Analysis**

```python
class PredictionAnalyzer:
    async def analyze_completed_prediction(self, prediction_id):
        """Fully analyze a completed prediction"""
        
        prediction = await self.get_prediction(prediction_id)
        price_data = await self.get_price_data_for_period(
            prediction.asset, 
            prediction.entry_time, 
            prediction.exit_time
        )
        
        analysis = {
            'prediction_id': prediction_id,
            'asset': prediction.asset,
            'pattern_type': prediction.pattern_type,
            'prediction_method': prediction.prediction_method,
            
            # Profit/Loss Analysis
            'final_profit_loss': self.calculate_final_pnl(prediction, price_data),
            'max_profit_reached': self.calculate_max_profit(prediction, price_data),
            'max_loss_reached': self.calculate_max_loss(prediction, price_data),
            'was_profitable_at_end': self.was_profitable_at_end(prediction, price_data),
            'was_profitable_at_any_time': self.was_profitable_at_any_time(prediction, price_data),
            
            # Exit Analysis
            'reached_exit_price': self.reached_exit_price(prediction, price_data),
            'exceeded_exit_price': self.exceeded_exit_price(prediction, price_data),
            'should_exit_have_been_higher': self.should_exit_have_been_higher(prediction, price_data),
            
            # Stop Loss Analysis
            'hit_stop_loss': self.hit_stop_loss(prediction, price_data),
            'went_lower_after_stop': self.went_lower_after_stop(prediction, price_data),
            'went_higher_after_stop': self.went_higher_after_stop(prediction, price_data),
            
            # Entry Analysis
            'better_entry_time': self.find_better_entry_time(prediction, price_data),
            'new_patterns_at_better_entry': self.find_new_patterns_at_better_entry(prediction, price_data),
            
            # Method Comparison (if both code and LLM)
            'code_vs_llm_comparison': self.compare_code_vs_llm(prediction),
            'which_method_was_better': self.determine_better_method(prediction),
            'key_differences': self.identify_key_differences(prediction),
            'lessons_learned': self.extract_lessons_learned(prediction)
        }
        
        return analysis
```

## **Learning System Integration**

### **Threshold-Based Learning**

```python
class LearningSystem:
    def __init__(self):
        # Use existing thresholds from LEARNING_AND_CLUSTERING_UPGRADE_PLAN.md
        self.cluster_thresholds = {
            'min_strands': 5,
            'min_avg_persistence': 0.6,
            'min_avg_novelty': 0.5,
            'min_avg_surprise': 0.4
        }
        
        # New prediction-specific thresholds - learn from everything
        self.prediction_thresholds = {
            'min_predictions_for_learning': 3,     # Much lower - learn quickly
            'min_data_points': 3,                  # Need at least 3 data points
            'learning_trigger': 'any_completion',  # Learn from every completed prediction
            'pattern_confidence_threshold': 0.0,   # Learn from all confidence levels
            'outcome_analysis_threshold': 1,       # Analyze every single outcome
            'learn_from_failures': True,           # Failures are valuable data
            'learn_from_successes': True,          # Successes confirm patterns
            'learn_from_partial_successes': True   # Partial successes show nuance
        }
    
    async def process_learning_cycle(self):
        """Process every completed prediction for learning - no minimum thresholds"""
        
        # 1. Get ALL completed predictions (no minimum threshold)
        completed_predictions = await self.get_completed_predictions()
        
        # 2. Process every prediction for learning
        for prediction in completed_predictions:
            # Analyze the prediction outcome
            analysis = await self.prediction_analyzer.analyze_completed_prediction(prediction['id'])
            
            # Update historical context with this outcome
            await self.update_historical_context(analysis)
            
            # Update pattern learning (even from 1 sample)
            await self.update_pattern_learning(analysis)
            
            # Update method performance (code vs LLM)
            await self.update_method_performance(analysis)
            
            # Store lessons learned
            await self.store_lessons_learned(analysis)
        
        # 3. Update context system with new learnings
        await self.context_system.index_database_records(await self.get_recent_strands())
```

## **Implementation Plan**

### **Phase 1: CIL Simplification (Week 1)**

1. **Move Advanced Components**
   ```bash
   mkdir Modules/Advanced_CIL/
   # Move complex CIL components to Advanced_CIL module
   ```

2. **Create Simplified CIL Structure**
   ```python
   # Keep only core components in main CIL
   class SimplifiedCIL:
       def __init__(self):
           self.pattern_recognition = CILPatternRecognitionAgent()
           self.learning_system = LearningSystem()
           self.prediction_tracker = PredictionTracker()
           self.outcome_analyzer = PredictionAnalyzer()
           self.plan_manager = ConditionalPlanManager()
   ```

3. **Update CIL Integration Points**
   - Update RMC to send patterns to simplified CIL
   - Remove complex orchestration
   - Focus on pattern → prediction → learning flow

### **Phase 2: Prediction System (Week 2)**

1. **Create Prediction Context System**
   ```python
   # Implement PredictionContextSystem
   # - Query completed prediction strands
   # - Group by pattern type and 5-minute cycles
   # - Calculate historical performance metrics
   ```

2. **Implement Dual Prediction Creation**
   - Code-based prediction engine using historical outcomes
   - LLM-based prediction engine using historical outcomes
   - Store both as prediction strands

3. **Create Pattern Classification System**
   - 6-category classification
   - Timeframe weighting
   - Asset grouping
   - 5-minute cycle pattern grouping

### **Phase 3: Analysis System (Week 3)**

1. **Implement Prediction Analyzer**
   - Comprehensive outcome analysis
   - Better entry time detection
   - Code vs LLM comparison

2. **Create Learning Integration**
   - Historical context pulling
   - Pattern success rate updates
   - Method performance tracking

3. **Add Threshold-Based Learning**
   - Use existing clustering thresholds
   - Add prediction-specific thresholds
   - Trigger learning cycles

### **Phase 4: Multi-Cluster Learning System (Week 4)**

1. **Multi-Cluster Grouping Engine**
   ```python
   class MultiClusterGroupingEngine:
       def group_prediction_reviews(self, prediction_reviews):
           """Group prediction reviews into 7 cluster types"""
           
           clusters = {
               # 1. Pattern + Timeframe (exact group signature)
               'pattern_timeframe': self.group_by_pattern_timeframe(prediction_reviews),
               
               # 2. Asset only
               'asset': self.group_by_asset(prediction_reviews),
               
               # 3. Timeframe only
               'timeframe': self.group_by_timeframe(prediction_reviews),
               
               # 4. Success or Failure
               'outcome': self.group_by_outcome(prediction_reviews),
               
               # 5. Pattern only (no timeframe)
               'pattern': self.group_by_pattern(prediction_reviews),
               
               # 6. Group Type (single_single, multi_single, etc.)
               'group_type': self.group_by_group_type(prediction_reviews),
               
               # 7. Method (Code vs LLM)
               'method': self.group_by_method(prediction_reviews)
           }
           
           return clusters
   ```

2. **Enhanced Prediction Review Strands**
   ```python
   def create_prediction_review_strand(self, prediction, analysis):
       """Create prediction review strand with cluster keys and original pattern links"""
       
       # Extract pattern group information
       pattern_group = prediction['pattern_group']
       group_signature = self.create_group_signature(pattern_group)
       
       # Extract original pattern strand IDs from pattern group
       original_pattern_strand_ids = [
           p.get('strand_id') for p in pattern_group['patterns'] 
           if p.get('strand_id')
       ]
       
       # Generate all cluster keys
       cluster_keys = [
           f"pattern_timeframe_{group_signature}",           # Pattern + Timeframe
           f"asset_{prediction['asset']}",                   # Asset
           f"timeframe_{prediction['timeframe']}",           # Timeframe
           f"outcome_{analysis['outcome']}",                 # Success/Failure
           f"pattern_{pattern_group['group_type']}",         # Pattern type
           f"group_type_{pattern_group['group_type']}",      # Group type
           f"method_{prediction['prediction_method']}"       # Method
       ]
       
       return {
           'kind': 'prediction_review',
           'content': {
               'prediction_id': prediction['id'],
               'pattern_group': pattern_group,
               'group_signature': group_signature,
               'cluster_keys': cluster_keys,
               'original_pattern_strand_ids': original_pattern_strand_ids,  # NEW: Link to original patterns
               'outcome': analysis['outcome'],
               'success_rate': analysis['success_rate'],
               'confidence': analysis['confidence'],
               'method': prediction['prediction_method'],
               'analysis_metadata': analysis
           },
           'tags': ['cil', 'learning', 'prediction_review']
       }
   ```

3. **Braid Level Progression System**
   ```python
   class BraidLevelManager:
       def __init__(self):
           self.braid_levels = {}  # Track braid levels per cluster
       
       async def process_braid_creation(self, cluster_type, cluster_key):
           """Process braid creation for a specific cluster"""
           
           # Get all strands in this cluster
           cluster_strands = await self.get_cluster_strands(cluster_type, cluster_key)
           
           # Group by braid level
           level_groups = self.group_by_braid_level(cluster_strands)
           
           # Process each level
           for level, strands in level_groups.items():
               if len(strands) >= 3:  # 3+ strands needed for next level
                   await self.create_next_level_braid(level, strands, cluster_type, cluster_key)
       
       async def create_next_level_braid(self, current_level, strands, cluster_type, cluster_key):
           """Create braid at next level from 3+ strands of current level"""
           
           next_level = current_level + 1
           
           # Create braid strand
           braid_strand = {
               'kind': 'braid',
               'content': {
                   'braid_level': next_level,
                   'cluster_type': cluster_type,
                   'cluster_key': cluster_key,
                   'source_strands': [s['id'] for s in strands],
                   'source_level': current_level,
                   'created_at': datetime.now(timezone.utc)
               },
               'tags': ['cil', 'braid', f'level_{next_level}']
           }
           
           # Store braid strand
           braid_id = await self.store_strand(braid_strand)
           
           # Update source strands to reference this braid
           await self.update_source_strands(strands, braid_id)
           
           return braid_id
   ```

4. **LLM Learning Analysis System**
   ```python
   class LLMLearningAnalyzer:
       def __init__(self, llm_client, context_system):
           self.llm_client = llm_client
           self.context_system = context_system
       
       async def analyze_cluster_for_learning(self, cluster_type, cluster_key, prediction_reviews):
           """Analyze a cluster of prediction reviews and extract learning insights"""
           
           # 1. Get original pattern strands for context
           pattern_context = await self.get_original_pattern_context(prediction_reviews)
           
           # 2. Prepare cluster data for LLM analysis
           cluster_data = self.prepare_cluster_data(prediction_reviews, pattern_context)
           
           # 3. Create LLM prompt for cluster analysis
           prompt = self.create_cluster_analysis_prompt(cluster_type, cluster_key, cluster_data)
           
           # 4. Get LLM analysis
           llm_response = await self.llm_client.generate_completion(prompt)
           
           # 5. Parse and structure the learning insights
           learning_insights = self.parse_learning_insights(llm_response, cluster_type, cluster_key)
           
           # 6. Create learning braid strand
           learning_braid = await self.create_learning_braid(learning_insights, cluster_type, cluster_key)
           
           return learning_braid
       
       async def get_original_pattern_context(self, prediction_reviews):
           """Get original pattern strands that led to these predictions"""
           
           pattern_contexts = []
           for pr in prediction_reviews:
               # Get original pattern strand IDs from prediction review
               pattern_strand_ids = pr.get('content', {}).get('original_pattern_strand_ids', [])
               
               # Query database for each pattern strand
               for strand_id in pattern_strand_ids:
                   pattern_strand = await self.get_pattern_strand_by_id(strand_id)
                   if pattern_strand:
                       pattern_contexts.append(pattern_strand)
           
           return pattern_contexts
       
       async def get_pattern_strand_by_id(self, strand_id):
           """Get pattern strand by ID from database"""
           query = """
               SELECT * FROM AD_strands 
               WHERE id = %s AND kind = 'pattern'
           """
           result = await self.context_system.supabase_manager.execute_query(query, [strand_id])
           return dict(result[0]) if result else None
       
       def prepare_cluster_data(self, prediction_reviews, pattern_contexts):
           """Prepare structured data for LLM analysis"""
           
           return {
               'cluster_type': cluster_type,
               'cluster_key': cluster_key,
               'prediction_count': len(prediction_reviews),
               'predictions': prediction_reviews,
               'original_patterns': pattern_contexts,
               'success_rate': self.calculate_success_rate(prediction_reviews),
               'avg_confidence': self.calculate_avg_confidence(prediction_reviews),
               'avg_return': self.calculate_avg_return(prediction_reviews),
               'avg_drawdown': self.calculate_avg_drawdown(prediction_reviews)
           }
       
       def create_cluster_analysis_prompt(self, cluster_type, cluster_key, cluster_data):
           """Create LLM prompt for cluster analysis"""
           
           prompt = f"""
           Analyze this cluster of {cluster_type} predictions and extract numerical, stats-focused learning insights.
           
           Cluster: {cluster_key}
           Prediction Count: {cluster_data['prediction_count']}
           Success Rate: {cluster_data['success_rate']:.2%}
           Avg Confidence: {cluster_data['avg_confidence']:.2f}
           Avg Return: {cluster_data['avg_return']:.2%}
           Avg Drawdown: {cluster_data['avg_drawdown']:.2%}
           
           Prediction Details:
           {self.format_prediction_details(cluster_data['predictions'])}
           
           Original Patterns:
           {self.format_pattern_details(cluster_data['original_patterns'])}
           
           Please analyze this data and provide:
           1. What patterns can we see in the data?
           2. What mistakes did we make?
           3. What did we do well?
           4. What can we learn from this cluster?
           5. What should we do differently next time?
           
           Keep your analysis numerical and stats-focused. No narratives, just facts and insights.
           """
           
           return prompt
       
       def parse_learning_insights(self, llm_response, cluster_type, cluster_key):
           """Parse LLM response into structured learning insights"""
           
           return {
               'cluster_type': cluster_type,
               'cluster_key': cluster_key,
               'analysis_timestamp': datetime.now(timezone.utc),
               'insights': {
                   'patterns_observed': self.extract_patterns_observed(llm_response),
                   'mistakes_identified': self.extract_mistakes_identified(llm_response),
                   'success_factors': self.extract_success_factors(llm_response),
                   'lessons_learned': self.extract_lessons_learned(llm_response),
                   'recommendations': self.extract_recommendations(llm_response)
               },
               'metadata': {
                   'llm_model': 'openrouter',
                   'analysis_type': 'cluster_learning',
                   'confidence': self.calculate_analysis_confidence(llm_response)
               }
           }
       
       async def create_learning_braid(self, learning_insights, cluster_type, cluster_key):
           """Create learning braid strand from insights"""
           
           learning_braid = {
               'kind': 'learning_braid',
               'content': {
                   'cluster_type': cluster_type,
                   'cluster_key': cluster_key,
                   'learning_insights': learning_insights,
                   'created_at': datetime.now(timezone.utc),
                   'braid_level': 1  # This is a learning braid, not a prediction braid
               },
               'tags': ['cil', 'learning', 'braid', f'cluster_{cluster_type}']
           }
           
           return learning_braid
   ```

5. **Per-Cluster Learning System**
   ```python
   class PerClusterLearningSystem:
       def __init__(self):
           self.cluster_thresholds = {
               'min_predictions_for_learning': 3,     # 3+ prediction reviews
               'min_confidence': 0.1,                 # Very low threshold
               'min_sample_size': 3,                  # Need at least 3 data points
               'learn_from_failures': True,           # Failures are valuable!
               'learn_from_successes': True           # Successes confirm patterns
           }
           self.llm_analyzer = LLMLearningAnalyzer(llm_client, context_system)
       
       async def process_cluster_learning(self, cluster_type, cluster_key):
           """Process learning for a specific cluster"""
           
           # Get prediction reviews in this cluster
           prediction_reviews = await self.get_cluster_prediction_reviews(cluster_type, cluster_key)
           
           # Check if meets learning thresholds
           if self.meets_learning_thresholds(prediction_reviews):
               # Analyze cluster for learning insights using LLM
               learning_braid = await self.llm_analyzer.analyze_cluster_for_learning(
                   cluster_type, cluster_key, prediction_reviews
               )
               
               # Update context system with new learnings
               await self.update_context_system(learning_braid)
       
       def meets_learning_thresholds(self, prediction_reviews):
           """Check if cluster meets learning thresholds"""
           
           if len(prediction_reviews) < self.cluster_thresholds['min_predictions_for_learning']:
               return False
           
           # Check confidence threshold (very low - learn from everything)
           avg_confidence = sum(pr['confidence'] for pr in prediction_reviews) / len(prediction_reviews)
           if avg_confidence < self.cluster_thresholds['min_confidence']:
               return False
           
           return True
   ```

6. **Database Query Examples**
   ```sql
   -- Cluster 1: Pattern + Timeframe (Exact Match)
   SELECT * FROM AD_strands 
   WHERE kind = 'prediction_review' 
   AND content->>'group_signature' = 'BTC_1h_volume_spike_divergence'
   AND content->>'asset' = 'BTC'
   ORDER BY created_at DESC;

   -- Cluster 2: Asset Only
   SELECT * FROM AD_strands 
   WHERE kind = 'prediction_review' 
   AND content->>'asset' = 'BTC'
   ORDER BY created_at DESC;

   -- Cluster 3: Timeframe Only
   SELECT * FROM AD_strands 
   WHERE kind = 'prediction_review' 
   AND content->>'timeframe' = '1h'
   ORDER BY created_at DESC;

   -- Cluster 4: Success/Failure
   SELECT * FROM AD_strands 
   WHERE kind = 'prediction_review' 
   AND content->>'success' = 'true'
   ORDER BY created_at DESC;

   -- Cluster 5: Pattern Only (No Timeframe)
   SELECT * FROM AD_strands 
   WHERE kind = 'prediction_review' 
   AND content->>'group_type' = 'multi_single'
   ORDER BY created_at DESC;

   -- Cluster 6: Group Type
   SELECT * FROM AD_strands 
   WHERE kind = 'prediction_review' 
   AND content->>'group_type' = 'multi_single'
   ORDER BY created_at DESC;

   -- Cluster 7: Method (Code vs LLM)
   SELECT * FROM AD_strands 
   WHERE kind = 'prediction_review' 
   AND content->>'method' = 'code'
   ORDER BY created_at DESC;

   -- Get Original Pattern Strands
   SELECT * FROM AD_strands 
   WHERE id = ANY(%s) AND kind = 'pattern';
   ```

7. **Complete Implementation Flow**
   ```python
   # Step 1: Multi-Cluster Grouping
   clusters = [
       ('pattern_timeframe', 'group_signature + asset'),
       ('asset', 'asset'),
       ('timeframe', 'timeframe'),
       ('outcome', 'success'),
       ('pattern', 'group_type'),
       ('group_type', 'group_type'),
       ('method', 'method')
   ]

   # Step 2: Process Each Cluster
   for cluster_name, query_field in clusters:
       # Get prediction reviews in this cluster
       prediction_reviews = await get_cluster_prediction_reviews(cluster_name, query_field)
       
       # Check if meets learning thresholds (3+ predictions)
       if len(prediction_reviews) >= 3:
           # Get original pattern strands for context
           pattern_contexts = await get_original_pattern_context(prediction_reviews)
           
           # LLM analyzes cluster and creates learning insights
           learning_braid = await llm_analyzer.analyze_cluster_for_learning(
               cluster_name, query_field, prediction_reviews, pattern_contexts
           )
           
           # Store learning braid
           await store_learning_braid(learning_braid)
           
           # Update context system
           await update_context_system(learning_braid)

   # Step 3: Braid Level Progression
   # When 3+ learning braids exist in a cluster, create next level braid
   for cluster_name, query_field in clusters:
       braids = await get_learning_braids_in_cluster(cluster_name, query_field)
       if len(braids) >= 3:
           next_level_braid = await create_next_level_braid(braids, cluster_name, query_field)
           await store_braid(next_level_braid)
   ```

### **Phase 5: Integration and Testing (Week 5)**

1. **Integrate with RMC**
   - Update RMC to send pattern overviews to CIL
   - Implement pattern extraction from strands
   - Test end-to-end flow

2. **Real Data Testing**
   - Test with live market data
   - Verify prediction accuracy
   - Test learning system

3. **Performance Optimization**
   - Optimize database queries
   - Ensure real-time performance
   - Add monitoring and alerting

## **Database Schema Updates**

### **Use Existing AD_strands Table (No New Tables Needed!)**

We already have everything we need in the existing `AD_strands` table:

```sql
-- Existing columns we'll use for predictions:
-- kind: 'prediction' (already exists)
-- prediction_data: JSONB (already exists) - entry_price, target_price, stop_loss, max_time
-- outcome_data: JSONB (already exists) - final_outcome, max_drawdown, time_to_outcome  
-- prediction_score: FLOAT (already exists) - accuracy score
-- outcome_score: FLOAT (already exists) - execution quality
-- tracking_status: VARCHAR (already exists) - active|completed|expired|cancelled
-- module_intelligence: JSONB (already exists) - can store pattern_type
```

### **Optional: Create Views for Easier Querying**

```sql
-- View for completed prediction outcomes
CREATE VIEW prediction_outcomes AS
SELECT 
    id,
    symbol,
    timeframe,
    prediction_data,
    outcome_data,
    prediction_score,
    outcome_score,
    tracking_status,
    module_intelligence,
    created_at,
    updated_at
FROM AD_strands 
WHERE kind = 'prediction' 
AND tracking_status = 'completed';

-- View for active predictions
CREATE VIEW active_predictions AS
SELECT 
    id,
    symbol,
    timeframe,
    prediction_data,
    tracking_status,
    module_intelligence,
    created_at
FROM AD_strands 
WHERE kind = 'prediction' 
AND tracking_status = 'active';
```

### **No Schema Changes Required!**

The existing `AD_strands` table already has all the columns we need for the prediction system. We just need to:

1. **Store predictions as strands** with `kind: 'prediction'`
2. **Use existing columns** for prediction data and outcomes
3. **Query by kind and tracking_status** to get prediction context
4. **Use existing indexes** for performance

## **API Endpoints**

### **Prediction Management**

```python
# Create prediction from pattern
POST /api/predictions/create
{
    "pattern_id": "strand_123",
    "asset": "BTC",
    "pattern_type": "volume_spike",
    "timeframe": "1h"
}

# Get prediction status
GET /api/predictions/{prediction_id}

# Update prediction (when completed)
PUT /api/predictions/{prediction_id}
{
    "status": "completed",
    "exit_price": 45000.0,
    "exit_time": "2024-01-15T10:30:00Z"
}

# Get prediction analysis
GET /api/predictions/{prediction_id}/analysis

# Get pattern learning data
GET /api/pattern-learning/{pattern_type}/{asset}/{timeframe}
```

## **Monitoring and Alerting**

### **Key Metrics**

1. **Prediction Metrics**
   - Total predictions created
   - Success rate by pattern type
   - Code vs LLM performance
   - Average prediction duration

2. **Learning Metrics**
   - Patterns learned per cycle
   - Historical context updates
   - Method performance improvements
   - Threshold triggers

3. **System Metrics**
   - Prediction processing time
   - Learning cycle duration
   - Database query performance
   - Memory usage

### **Alerts**

1. **High Priority**
   - Prediction success rate drops below 30%
   - Learning system fails to process
   - Database connection issues

2. **Medium Priority**
   - Code vs LLM performance gap > 20%
   - Prediction processing time > 5 minutes
   - Memory usage > 80%

3. **Low Priority**
   - New pattern types detected
   - Learning thresholds reached
   - System performance updates

## **Success Criteria**

### **Phase 1: CIL Simplification**
- ✅ Advanced CIL components moved to separate module
- ✅ Simplified CIL with 5 core components
- ✅ RMC integration updated
- ✅ No breaking changes to existing functionality

### **Phase 2: Prediction System**
- ✅ Dual prediction creation (code + LLM)
- ✅ 6-category pattern classification
- ✅ Timeframe weighting system
- ✅ Prediction database schema

### **Phase 3: Analysis System**
- ✅ Comprehensive outcome analysis
- ✅ Better entry time detection
- ✅ Code vs LLM comparison
- ✅ Learning system integration

### **Phase 4: Multi-Cluster Learning System**
- ✅ Multi-cluster grouping engine implemented
- ✅ Enhanced prediction review strands with cluster keys and original pattern links
- ✅ Braid level progression system (no cap)
- ✅ Per-cluster learning with 3+ prediction threshold
- ✅ 7 cluster types: pattern+timeframe, asset, timeframe, outcome, pattern, group_type, method
- ✅ LLM learning analysis with original pattern context
- ✅ Database query examples for all cluster types
- ✅ Complete implementation flow with step-by-step process

### **Phase 5: Integration and Testing**
- ✅ End-to-end flow working
- ✅ Real data testing completed
- ✅ Performance optimized
- ✅ Monitoring and alerting active

## **Risk Mitigation**

### **Technical Risks**

1. **Performance Issues**
   - Risk: Dual prediction creation may be slow
   - Mitigation: Implement async processing and caching

2. **Database Overload**
   - Risk: Too many predictions and analyses
   - Mitigation: Implement data archiving and cleanup

3. **Learning System Complexity**
   - Risk: Learning system becomes too complex
   - Mitigation: Keep learning simple, focus on core metrics

### **Business Risks**

1. **Prediction Accuracy**
   - Risk: Predictions may not be accurate enough
   - Mitigation: Continuous learning and improvement

2. **System Reliability**
   - Risk: System may fail during critical times
   - Mitigation: Robust error handling and fallbacks

## **Next Steps**

1. **Review and Approve** this build plan
2. **Start Phase 1** - CIL simplification
3. **Create Advanced_CIL module** - Move complex components
4. **Implement prediction system** - Core prediction creation
5. **Add analysis system** - Comprehensive outcome analysis
6. **Integrate and test** - End-to-end testing
7. **Deploy and monitor** - Production deployment

## **Summary of Key Changes**

### **Simplified Architecture:**
1. **Two Context Systems** - Pattern detection vs prediction outcomes
2. **Use Existing Database** - No new tables, use AD_strands with kind='prediction'
3. **Dual Predictions** - Code + LLM for every pattern, compare after completion
4. **Continuous Learning** - Learn from every prediction (no minimum thresholds)
5. **5-Minute Cycle Grouping** - Treat pattern groups as single patterns

### **Key Benefits:**
- **Simpler Implementation** - Reuse existing systems and database
- **Better Context** - Prediction outcomes more valuable than pattern detection
- **Continuous Learning** - Learn from every prediction, success or failure
- **Dual Validation** - Code and LLM predictions for comparison
- **Multi-Cluster Learning** - 7 different clustering approaches for comprehensive learning
- **Braid Level Progression** - Unlimited compression and learning depth
- **LLM Learning Analysis** - Extract insights from clusters with original pattern context
- **Original Pattern Context** - LLM sees full picture: Pattern → Prediction → Outcome → Learning
- **No Schema Changes** - Use existing AD_strands table

### **Implementation Order:**
1. **Week 1**: CIL simplification (move complex components)
2. **Week 2**: Prediction context system + dual prediction creation
3. **Week 3**: Analysis system + learning integration
4. **Week 4**: Multi-cluster learning system + braid level progression
5. **Week 5**: Testing + optimization

This plan provides a clear path to simplify the CIL while adding a comprehensive prediction system that learns continuously from market data.
