# Unified Clustering System - Build Plan

## **Overview**

This document outlines the comprehensive build plan for implementing a unified clustering system that feeds into the existing Learning System to create CIL Conditional Plans. The clustering system groups similar strands, and when clusters reach thresholds, they trigger learning and conditional plan creation.

**Key Insight**: The Learning System is already sophisticated and complete - we just need to add clustering as the input layer that feeds it properly.

## **Current State Analysis**

### **The Problem: Clustering and Learning Are Disconnected**
- **Learning System**: Exists and is sophisticated, but receives lessons from orchestration results instead of clustered strands
- **Clustering**: Currently fragmented across subsystems with different grouping logic
- **Missing Link**: No unified clustering that feeds into the learning system
- **CIL Conditional Plans**: Can't be created because learning isn't connected to pattern clustering

### **What We Have vs What We Need**

**✅ What We Have (Learning System):**
- Sophisticated lesson structuring with persistence, novelty, surprise scores
- Doctrine lifecycle management (Provisional → Affirmed → Retired → Contraindicated)
- Doctrine of Negatives system (learns what NOT to do)
- Cross-agent distribution of learnings
- Outcome analysis and prediction tracking
- Conditional plan creation and evolution

**❌ What's Missing (Clustering Layer):**
- Unified clustering that groups strands by asset/timeframe/strength/regime
- Threshold-based promotion from clusters to learning
- Connection between clustered strands and lesson creation
- Integration with CIL conditional plan creation

## **Target Architecture: Clustering → Learning → Conditional Plans**

### **1. The Flow: Strands → Clusters → Learning → Plans**

```
Raw Data Intelligence → Creates Strands
                    ↓
Unified Clustering → Groups Strands by Asset/Timeframe/Strength/Regime
                    ↓
Learning System → When cluster reaches threshold → Learn from cluster
                    ↓
Learning System → Create/Update Conditional Plans
                    ↓
Decision Maker → Execute plans when conditions are met
```

### **2. Cluster Families for Learning Integration**

The clustering system feeds into the existing Learning System, so we need cluster families that align with learning needs:

```python
CLUSTER_FAMILIES = {
    'raw_detection': {
        'primary_key': ['asset', 'timeframe', 'pattern_type', 'strength_range', 'data_quality_band'],
        'purpose': 'Feed raw patterns into learning system for initial lesson creation',
        'thresholds': {
            'min_support': 5,                    # Lower threshold for faster pattern detection
            'min_confidence': 0.7,               # High confidence for reliable signals
            'min_data_quality': 0.8,             # High data quality for accurate detection
            'min_sigma': 0.6,                    # Minimum signal strength
            'max_age_hours': 24,                 # Fresh data only
            'learning_trigger': 'immediate'      # Trigger learning as soon as threshold met
        },
        'owner_agent': 'raw_data_intelligence',
        'learning_integration': {
            'lesson_type': 'pattern_detection',
            'doctrine_status': 'provisional',
            'learning_priority': 'high'
        }
    },
    
    'cil_learning': {
        'primary_key': ['asset', 'timeframe', 'pattern_type', 'strength_range', 'market_regime'],
        'purpose': 'Main learning clusters for conditional plan creation',
        'thresholds': {
            'min_support': 8,                    # Moderate threshold for learning cohorts
            'min_confidence': 0.6,               # Moderate confidence requirement
            'min_outcome_score': 0.5,            # Must have some positive outcomes
            'min_accumulated_score': 0.4,        # Accumulated performance threshold
            'min_stability_days': 3,             # Shorter stability window for faster learning
            'max_variance': 0.3,                 # Low variance for consistent patterns
            'learning_trigger': 'threshold_met'  # Trigger learning when all thresholds met
        },
        'owner_agent': 'central_intelligence_layer',
        'learning_integration': {
            'lesson_type': 'conditional_plan',
            'doctrine_status': 'provisional',
            'learning_priority': 'critical',
            'plan_creation': True
        }
    },
    
    'resonance_learning': {
        'primary_key': ['resonance_frequency_band', 'resonance_amplitude_band', 'resonance_phase_band'],
        'purpose': 'Learn from mathematical resonance patterns for organic evolution',
        'thresholds': {
            'min_resonance': 0.7,                # High resonance requirement
            'min_coherence': 0.8,                # High coherence for resonance
            'min_frequency_stability': 0.85,     # Very stable frequency
            'min_phi': 0.6,                      # Minimum phi (field strength)
            'min_rho': 0.5,                      # Minimum rho (density)
            'min_telemetry_quality': 0.7,        # Quality of resonance telemetry
            'learning_trigger': 'stability_achieved'  # Trigger when resonance stabilizes
        },
        'owner_agent': 'central_intelligence_layer',
        'learning_integration': {
            'lesson_type': 'resonance_pattern',
            'doctrine_status': 'provisional',
            'learning_priority': 'medium',
            'organic_evolution': True
        }
    },
    
    'negative_pattern_learning': {
        'primary_key': ['pattern_combination', 'failure_context', 'market_conditions'],
        'purpose': 'Learn what NOT to do - feed into Doctrine of Negatives',
        'thresholds': {
            'min_failure_count': 3,              # Minimum failures to learn from
            'min_failure_rate': 0.7,             # High failure rate required
            'min_confidence': 0.8,               # High confidence in negative pattern
            'min_context_diversity': 2,          # Multiple contexts where pattern fails
            'max_success_rate': 0.3,             # Low success rate
            'learning_trigger': 'failure_threshold'  # Trigger when failure threshold met
        },
        'owner_agent': 'central_intelligence_layer',
        'learning_integration': {
            'lesson_type': 'negative_pattern',
            'doctrine_status': 'contraindicated',
            'learning_priority': 'high',
            'doctrine_of_negatives': True
        }
    }
}
```

#### **Threshold Design Rationale**

The thresholds are designed to feed the Learning System effectively:

**Raw Detection (Fast Pattern Recognition):**
- `min_support: 5` - Lower threshold for faster pattern detection
- `min_confidence: 0.7` - High confidence for reliable signals
- `learning_trigger: 'immediate'` - Start learning as soon as threshold met
- **Purpose**: Feed initial patterns into learning system quickly

**CIL Learning (Conditional Plan Creation):**
- `min_support: 8` - Moderate threshold for learning cohorts
- `min_outcome_score: 0.5` - Must have positive outcomes for plans
- `min_accumulated_score: 0.4` - Performance-based learning
- `learning_trigger: 'threshold_met'` - Create plans when all thresholds met
- **Purpose**: Create actionable conditional trading plans

**Resonance Learning (Organic Evolution):**
- `min_resonance: 0.7` - High resonance for organic patterns
- `min_phi: 0.6` - Minimum field strength
- `learning_trigger: 'stability_achieved'` - Learn when resonance stabilizes
- **Purpose**: Learn from mathematical resonance patterns

**Negative Pattern Learning (Doctrine of Negatives):**
- `min_failure_count: 3` - Minimum failures to learn from
- `min_failure_rate: 0.7` - High failure rate required
- `learning_trigger: 'failure_threshold'` - Learn what NOT to do
- **Purpose**: Feed into Doctrine of Negatives system

### **3. Integration with Existing Learning System**

#### **A. Enhanced LearningFeedbackEngine**

The clustering system integrates directly with the existing `LearningFeedbackEngine`:

```python
class LearningFeedbackEngine:
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        # Existing initialization...
        self.unified_clustering = UnifiedClusteringSystem(supabase_manager)
        
    async def process_strand_clustering(self, strand: Dict[str, Any]) -> Dict[str, Any]:
        """New method: Cluster strands and trigger learning when thresholds met"""
        try:
            # 1. Assign strand to appropriate clusters
            cluster_assignments = await self.unified_clustering.assign_strand_to_clusters(strand)
            
            # 2. Check if any clusters meet learning thresholds
            learning_triggers = []
            for assignment in cluster_assignments['memberships']:
                if await self._cluster_meets_learning_threshold(assignment):
                    # 3. Trigger learning from clustered strands
                    learning_result = await self._learn_from_cluster(assignment)
                    learning_triggers.append(learning_result)
            
            return {
                'cluster_assignments': cluster_assignments,
                'learning_triggers': learning_triggers
            }
            
        except Exception as e:
            print(f"Error in strand clustering: {e}")
            return {'error': str(e)}
    
    async def _cluster_meets_learning_threshold(self, assignment: Dict[str, Any]) -> bool:
        """Check if cluster meets threshold for learning trigger"""
        family_name = assignment['cluster_family']
        cluster_key = assignment['cluster_key']
        
        # Get cluster stats
        cluster_stats = await self.unified_clustering.get_cluster_stats(family_name, cluster_key)
        
        # Check family-specific thresholds
        family_config = self.unified_clustering.cluster_families[family_name]
        thresholds = family_config['thresholds']
        
        # Check support threshold
        if cluster_stats['strand_count'] < thresholds.get('min_support', 1):
            return False
        
        # Check confidence threshold
        if cluster_stats['avg_confidence'] < thresholds.get('min_confidence', 0.0):
            return False
        
        # Check learning trigger type
        learning_trigger = thresholds.get('learning_trigger', 'threshold_met')
        
        if learning_trigger == 'immediate':
            return True
        elif learning_trigger == 'threshold_met':
            return await self._all_thresholds_met(family_name, cluster_stats, thresholds)
        elif learning_trigger == 'stability_achieved':
            return cluster_stats.get('stability_days', 0) >= thresholds.get('min_stability_days', 0)
        elif learning_trigger == 'failure_threshold':
            return cluster_stats.get('failure_rate', 0) >= thresholds.get('min_failure_rate', 0)
        
                return False
        
    async def _learn_from_cluster(self, assignment: Dict[str, Any]) -> Dict[str, Any]:
        """Learn from clustered strands using existing learning system"""
        try:
            family_name = assignment['cluster_family']
            cluster_key = assignment['cluster_key']
            
            # Get all strands in cluster
            cluster_strands = await self.unified_clustering.get_cluster_strands(family_name, cluster_key)
            
            if not cluster_strands:
                return {'error': 'No strands in cluster'}
            
            # Convert clustered strands to lessons using existing system
            lessons = []
            for strand in cluster_strands:
                lesson = await self._strand_to_lesson(strand, family_name)
                if lesson:
                    lessons.append(lesson)
            
            # Use existing braid creation system
            braids = await self.update_strand_braid_memory_from_lessons(lessons, family_name)
            
            # Create conditional plans if this is a CIL learning cluster
            conditional_plans = []
            if family_name == 'cil_learning':
                conditional_plans = await self._create_conditional_plans_from_braids(braids)
            
            return {
                'family_name': family_name,
                'cluster_key': cluster_key,
                'lessons_created': len(lessons),
                'braids_created': len(braids),
                'conditional_plans_created': len(conditional_plans)
            }
            
        except Exception as e:
            print(f"Error learning from cluster: {e}")
            return {'error': str(e)}
    
    async def _strand_to_lesson(self, strand: Dict[str, Any], family_name: str) -> Optional[Lesson]:
        """Convert strand to lesson using existing lesson creation logic"""
        try:
            # Extract pattern family
            pattern_family = self._extract_pattern_family_from_strand(strand, family_name)
            
            # Determine lesson type based on family
            lesson_type = self._determine_lesson_type_from_family(family_name)
            
            # Calculate scores using existing methods
            persistence_score = self._calculate_persistence_score_from_strand(strand)
            novelty_score = self._calculate_novelty_score_from_strand(strand)
            surprise_rating = self._calculate_surprise_rating_from_strand(strand)
            
            # Create lesson using existing structure
            lesson = Lesson(
                lesson_id=f"LESSON_{strand['id']}_{int(datetime.now().timestamp())}",
                lesson_type=lesson_type,
                pattern_family=pattern_family,
                context=self._extract_lesson_context_from_strand(strand),
                outcome=strand.get('outcome_score', 0.0),
                persistence_score=persistence_score,
                novelty_score=novelty_score,
                surprise_rating=surprise_rating,
                evidence_count=self._count_evidence_from_strand(strand),
                confidence_level=strand.get('sig_confidence', 0.5),
                mechanism_hypothesis=await self._generate_mechanism_hypothesis_from_strand(strand),
                fails_when=await self._determine_failure_conditions_from_strand(strand),
                created_at=datetime.now(timezone.utc)
            )
            
            return lesson
            
        except Exception as e:
            print(f"Error converting strand to lesson: {e}")
            return None
```

#### **B. Conditional Plan Creation**

The clustering system feeds into conditional plan creation:

```python
async def _create_conditional_plans_from_braids(self, braids: List[Braid]) -> List[Dict[str, Any]]:
    """Create conditional trading plans from learned braids"""
    conditional_plans = []
    
    for braid in braids:
        if braid.doctrine_status == DoctrineStatus.AFFIRMED:
            # Extract plan parameters from braid
            plan_params = await self._extract_plan_parameters_from_braid(braid)
            
            # Create conditional plan
            conditional_plan = {
                'plan_id': f"PLAN_{braid.braid_id}_{int(datetime.now().timestamp())}",
                'plan_name': f"Conditional Plan: {braid.braid_name}",
                'pattern_family': braid.pattern_family,
                'conditions': plan_params['conditions'],
                'entry_criteria': plan_params['entry_criteria'],
                'exit_criteria': plan_params['exit_criteria'],
                'risk_management': plan_params['risk_management'],
                'confidence_level': braid.aggregate_metrics.get('avg_confidence', 0.0),
                'expected_rr': plan_params['expected_rr'],
                'max_drawdown': plan_params['max_drawdown'],
                'timeframe': plan_params['timeframe'],
                'asset': plan_params['asset'],
                'market_regime': plan_params['market_regime'],
                'doctrine_status': braid.doctrine_status.value,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            conditional_plans.append(conditional_plan)
            
            # Save plan to database
            await self._save_conditional_plan_to_database(conditional_plan)
            
            # Distribute plan to Decision Maker
            await self._distribute_plan_to_decision_maker(conditional_plan)
    
    return conditional_plans

async def _extract_plan_parameters_from_braid(self, braid: Braid) -> Dict[str, Any]:
    """Extract trading plan parameters from braid using LLM analysis"""
    try:
        # Build prompt for plan extraction
        prompt = self._build_plan_extraction_prompt(braid)
        
        # Get LLM response
        llm_response = await self.llm_client.generate(prompt)
        
        # Parse plan parameters
        plan_params = self._parse_plan_parameters(llm_response)
        
        return plan_params
        
    except Exception as e:
        print(f"Error extracting plan parameters: {e}")
        return self._get_default_plan_parameters(braid)

def _build_plan_extraction_prompt(self, braid: Braid) -> str:
    """Build LLM prompt for extracting trading plan parameters"""
    prompt = f"""
You are an expert trading strategist. You have been given a braid (compressed lesson) that represents a learned trading pattern.

BRAID DATA:
- Braid Name: {braid.braid_name}
- Pattern Family: {braid.pattern_family}
- Doctrine Status: {braid.doctrine_status.value}
- Aggregate Metrics: {braid.aggregate_metrics}
- Lesson Count: {len(braid.lessons)}

Your task is to extract actionable trading plan parameters from this braid.

Please provide a trading plan in the following JSON format:
{{
    "conditions": {{
        "market_regime": "bull|bear|sideways",
        "timeframe": "1m|5m|15m|1h|4h|1d",
        "asset": "BTC|ETH|SOL|etc",
        "volume_requirements": "high|medium|low",
        "volatility_requirements": "high|medium|low"
    }},
    "entry_criteria": {{
        "pattern_type": "volume_spike|divergence|correlation|etc",
        "strength_threshold": 0.0-1.0,
        "confidence_threshold": 0.0-1.0,
        "additional_filters": ["filter1", "filter2"]
    }},
    "exit_criteria": {{
        "target_price_ratio": 1.0-5.0,
        "stop_loss_ratio": 0.5-1.0,
        "time_exit_hours": 1-24,
        "trailing_stop": true|false
    }},
    "risk_management": {{
        "position_size_pct": 0.01-0.1,
        "max_drawdown_pct": 0.01-0.05,
        "correlation_limits": 0.0-1.0,
        "diversification_requirements": ["requirement1", "requirement2"]
    }},
    "expected_rr": 1.0-5.0,
    "max_drawdown": 0.01-0.05,
    "timeframe": "1m|5m|15m|1h|4h|1d",
    "asset": "BTC|ETH|SOL|etc",
    "market_regime": "bull|bear|sideways"
}}

Focus on:
1. What specific conditions must be met for this pattern to work?
2. What are the entry criteria based on the learned pattern?
3. What are the exit criteria for risk management?
4. How should position sizing and risk be managed?
5. What is the expected risk/reward ratio?

Be specific and actionable. This plan will be used by the Decision Maker to execute trades.
"""
    return prompt
```

### **4. Implementation Strategy**

#### **A. Phase 1: Add Clustering to Learning System (Week 1)**

1. **Enhance LearningFeedbackEngine** with clustering capabilities
2. **Add cluster families** for different learning types
3. **Implement strand-to-lesson conversion** using existing learning logic
4. **Test clustering integration** with existing learning system

#### **B. Phase 2: Connect Raw Data Intelligence (Week 2)**

1. **Update raw_data_intelligence** to send strands to learning system
2. **Add prediction tracking** as outlined in `CIL_CONDITIONAL_PLAN_LEARNING_SYSTEM.md`
3. **Connect outcome analysis** to cluster learning
4. **Test end-to-end flow** from strand creation to learning

#### **C. Phase 3: Conditional Plan Creation (Week 3)**

1. **Implement conditional plan creation** from learned braids
2. **Add LLM-based plan parameter extraction**
3. **Connect to Decision Maker** for plan execution
4. **Test full learning cycle** with real data

#### **D. Phase 4: Production Testing (Week 4)**

1. **Real data testing** with live market data
2. **Performance optimization** and monitoring
3. **Documentation** and training
4. **Full system validation**

### **5. Key Benefits of This Approach**

#### **A. Leverages Existing Learning System**
- ✅ **No rebuilding** - Uses existing sophisticated learning system
- ✅ **Proven concepts** - Doctrine management, cross-agent distribution, etc.
- ✅ **Rich metadata** - Persistence, novelty, surprise scores already implemented
- ✅ **LLM integration** - Already has LLM analysis and compression

#### **B. Adds Missing Clustering Layer**
- ✅ **Unified clustering** - Groups strands by asset/timeframe/strength/regime
- ✅ **Threshold-based learning** - Triggers learning when clusters reach thresholds
- ✅ **Conditional plan creation** - Creates actionable trading plans from learned patterns
- ✅ **Integration with CIL** - Feeds into CIL conditional plan system

#### **C. Maintains Architecture**
- ✅ **Existing code works** - No breaking changes
- ✅ **Gradual adoption** - Can implement incrementally
- ✅ **Backward compatibility** - All existing functionality preserved
- ✅ **Performance** - Builds on existing optimized learning system

### **6. Success Metrics**

#### **A. Clustering Quality**
- **Cluster purity**: Similar patterns grouped together
- **Cluster separation**: Different patterns in different clusters
- **Learning efficiency**: Faster convergence with better clustering
- **Threshold accuracy**: Clusters trigger learning at appropriate times

#### **B. Learning Integration**
- **Lesson creation rate**: How many lessons created from clustered strands
- **Braid formation rate**: How many braids created from lessons
- **Doctrine evolution rate**: How quickly patterns move through doctrine lifecycle
- **Cross-agent distribution**: How effectively learnings are shared

#### **C. Conditional Plan Effectiveness**
- **Plan creation rate**: How many conditional plans created from braids
- **Plan success rate**: How often plans lead to successful trades
- **Plan evolution rate**: How quickly plans adapt to market changes
- **Risk management**: How well plans control drawdown and risk

### **7. Conclusion**

This approach transforms the system by:

1. **Adding clustering as input layer** to the existing sophisticated learning system
2. **Connecting pattern detection** to conditional plan creation
3. **Leveraging existing learning concepts** rather than rebuilding everything
4. **Creating actionable trading plans** from learned patterns
5. **Maintaining system architecture** while adding powerful new capabilities

The key insight is that **the Learning System is already complete and sophisticated** - we just need to add the clustering layer that feeds it properly. This approach:

- ✅ **Preserves all existing work** - No data loss or functionality loss
- ✅ **Adds missing clustering** - Groups strands by similarity for learning
- ✅ **Enables conditional plans** - Creates actionable trading strategies
- ✅ **Integrates with CIL** - Feeds into the CIL conditional plan system
- ✅ **Faster implementation** - Builds on existing proven system

**Next Steps:**
1. **Review and approve** this clustering integration approach
2. **Start with Phase 1** - Add clustering to LearningFeedbackEngine
3. **Test integration** - Verify clustering feeds learning properly
4. **Build conditional plans** - Create actionable trading strategies
5. **Scale to production** - Full system with real market data
