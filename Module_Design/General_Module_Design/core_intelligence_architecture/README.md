# Core Intelligence Architecture

*Source: [organic_intelligence_overview.md](../organic_intelligence_overview.md) + [intelligence_commincation_roughplan.md](../build_docs/intelligence_commincation_roughplan.md)*

## Goal
Define the organic intelligence system where each module is a self-contained garden with its own curator layer and intelligence capabilities.

## Core Philosophy

Each module becomes a **self-contained intelligence unit** with:
- **Its own curator layer** - specialized curators for each module's domain
- **Complete trading plan generation** - Alpha Detector generates full plans, Decision Maker just approves/modifies
- **Self-learning and self-correcting** - each module continuously improves itself
- **Independent operation** - modules can function autonomously while communicating

## Module-Level Intelligence Architecture

### Alpha Detector Module
**Curators**: DSI, Pattern, Divergence, Regime, Evolution, Performance
**Intelligence**: Generates complete trading plans (not just signals)
**Self-Learning**: Continuously improves detector performance and pattern recognition
**Output**: Full trading plans with entry/exit conditions, position sizing, risk management

### Decision Maker Module
**Curators**: Risk, Allocation, Timing, Cost, Compliance
**Intelligence**: Evaluates trading plans and provides yes/no approval or modifications
**Self-Learning**: Learns from portfolio performance and risk management outcomes
**Output**: Approved/modified trading plans or rejections with reasons

### Trader Module
**Curators**: Execution, Latency, Slippage, Position, Performance
**Intelligence**: Executes trades and manages positions
**Self-Learning**: Optimizes execution strategies and venue selection
**Output**: Execution reports and performance feedback

## Curator Layer Design

### Curator Principles
- **Narrow Mandate**: Each curator has a specific domain of expertise
- **Bounded Influence**: Curators can only apply bounded log-space nudges
- **Hard Vetoes vs Soft Nudges**: Binary vetoes for critical issues, soft nudges for improvements
- **Machine Score as Anchor**: Curator contributions are bounded and cannot overwhelm machine scores

### Curator Types by Module

#### Alpha Detector Curators
- **DSI Curator**: Microstructure evidence quality and expert performance
- **Pattern Curator**: Candlestick and chart pattern validation
- **Divergence Curator**: RSI/MACD divergence confirmation
- **Regime Curator**: Market regime alignment and timing
- **Evolution Curator**: Detector breeding and mutation control
- **Performance Curator**: Signal quality and detector fitness

#### Decision Maker Curators
- **Risk Curator**: Portfolio risk and position sizing
- **Allocation Curator**: Asset allocation and diversification
- **Timing Curator**: Entry/exit timing optimization
- **Cost Curator**: Transaction cost and slippage management
- **Compliance Curator**: Regulatory and policy adherence

#### Trader Curators
- **Execution Curator**: Order execution quality and venue selection
- **Latency Curator**: Execution speed and timing
- **Slippage Curator**: Market impact and cost control
- **Position Curator**: Position tracking and risk management
- **Performance Curator**: P&L attribution and analysis

## Curator Math (Bounded Influence)

### Curator Contributions
Define curator contributions `c_{j,i} ∈ [-κ_j, +κ_j]` with small caps (e.g., `κ_j ≤ 0.15`).

### Final Curated Score
```python
log Σ̃_i = log(det_sigma_i) + Σ_{j∈soft} c_{j,i}
```

### Publication Decision
Publish if:
- No hard veto flags, AND
- `Σ̃_i ≥ τ_publish`

## Database Schema

### Curator Actions Table
```sql
CREATE TABLE curator_actions (
    id UUID PRIMARY KEY,
    detector_id UUID REFERENCES detector_registry(id),
    curator_type TEXT NOT NULL,  -- 'dsi', 'pattern', 'divergence', etc.
    action_type TEXT NOT NULL,   -- 'veto', 'nudge', 'approve'
    contribution FLOAT8,         -- c_{j,i} for nudges
    reason TEXT,
    evidence JSONB,             -- Supporting data
    created_at TIMESTAMP DEFAULT NOW(),
    curator_version TEXT        -- For audit trail
);
```

### Curator KPIs Table
```sql
CREATE TABLE curator_kpis (
    id UUID PRIMARY KEY,
    curator_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value FLOAT8,
    measurement_window_start TIMESTAMP,
    measurement_window_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Implementation Notes

### Bounded Influence Enforcement
- All curator contributions are capped by `κ_j`
- Hard vetoes are binary and absolute
- Soft nudges are additive in log-space only
- Full audit trail for all curator actions

### Curator Training & Learning
- Each curator has specific training on their domain
- Regular calibration against ground truth
- Performance feedback loops
- Rotation to prevent bias
- **Strand-Braid Learning Integration**: Curators learn from their own performance through the strand-braid system

### Escalation Paths
- Curator disagreements go to arbitration
- System can override curators in extreme cases
- All overrides are logged and reviewed

## Curator Learning Integration

### Curator Performance Tracking
Each curator's performance is tracked and used for learning:

```python
class CuratorLearningSystem:
    """Learning system for curator performance improvement"""
    
    def __init__(self, module_type: str):
        self.module_type = module_type
        self.curator_performance = {}
        self.learning_system = EnhancedModuleLearning(module_type)
    
    def update_curator_performance(self, curator_contribution: CuratorContribution, outcome: Dict):
        """Update curator performance based on trading outcome"""
        
        # Extract curator-specific performance data
        curator_data = {
            'curator_type': curator_contribution.curator_type,
            'action': curator_contribution.action.value,
            'contribution': curator_contribution.contribution,
            'confidence': curator_contribution.confidence,
            'outcome_score': outcome.get('score', 0.0),
            'was_correct': outcome.get('was_correct', False),
            'timestamp': curator_contribution.timestamp
        }
        
        # Store in strands table for strand-braid learning
        self.learning_system.update_performance(curator_data, outcome)
        
        # Update curator-specific performance tracking
        self._update_curator_metrics(curator_data)
    
    def _update_curator_metrics(self, curator_data: Dict):
        """Update curator-specific performance metrics"""
        curator_type = curator_data['curator_type']
        
        if curator_type not in self.curator_performance:
            self.curator_performance[curator_type] = {
                'total_decisions': 0,
                'correct_decisions': 0,
                'veto_accuracy': 0.0,
                'nudge_effectiveness': 0.0,
                'confidence_calibration': 0.0
            }
        
        metrics = self.curator_performance[curator_type]
        metrics['total_decisions'] += 1
        
        if curator_data['was_correct']:
            metrics['correct_decisions'] += 1
        
        # Update accuracy metrics
        accuracy = metrics['correct_decisions'] / metrics['total_decisions']
        metrics['accuracy'] = accuracy
        
        # Update curator weights based on performance
        self._adjust_curator_weights(curator_type, accuracy)
```

### Curator Strand-Braid Learning
Curators learn through the strand-braid system:

```python
class CuratorStrandBraidLearning:
    """Strand-braid learning specifically for curator performance"""
    
    def __init__(self, module_type: str):
        self.module_type = module_type
        self.strand_scorer = CuratorStrandScoring()
        self.strand_clusterer = CuratorStrandClustering()
        self.braid_creator = CuratorBraidCreation()
    
    def cluster_curator_strands(self, curator_type: str):
        """Cluster curator performance strands by similarity"""
        
        # Get curator-specific strands
        curator_strands = self._get_curator_strands(curator_type)
        
        # Cluster by curator-specific columns
        clusters = self.strand_clusterer.cluster_strands(curator_strands)
        
        # Create braids for high-performing clusters
        braids = self.braid_creator.create_braids_from_clusters(clusters)
        
        return braids
    
    def generate_curator_lessons(self, curator_type: str):
        """Generate lessons for specific curator type"""
        
        # Get curator braids
        braids = self.cluster_curator_strands(curator_type)
        
        # Generate LLM lessons
        lessons = []
        for braid in braids:
            lesson = self._generate_curator_lesson(braid, curator_type)
            lessons.append(lesson)
        
        return lessons
    
    def _generate_curator_lesson(self, braid: Dict, curator_type: str) -> Dict:
        """Generate specific lesson for curator type"""
        
        lesson_prompt = f"""
        Generate a curator improvement lesson for {curator_type} curator:
        
        Performance Data: {braid['lesson']}
        Curator Type: {curator_type}
        Accumulated Score: {braid['accumulated_score']}
        
        Focus on:
        1. When this curator performs well/poorly
        2. What conditions lead to accurate decisions
        3. How to improve curator confidence calibration
        4. Specific recommendations for this curator type
        
        Format as JSON with: title, description, conditions, recommendations, confidence
        """
        
        return self._call_llm(lesson_prompt)
```

### Curator-Specific Learning Columns
Different curator types learn from different performance patterns:

```python
class CuratorStrandClustering(StrandClustering):
    """Clustering specifically for curator performance strands"""
    
    def _get_clustering_columns(self):
        """Define clustering columns for curator learning"""
        return [
            'curator_type',      # 'dsi', 'pattern', 'regime', etc.
            'action',           # 'veto', 'nudge', 'approve'
            'confidence',       # Curator confidence level
            'market_regime',    # Market conditions
            'signal_strength',  # Original signal strength
            'outcome_score'     # Trading outcome score
        ]

class CuratorStrandScoring(ModuleStrandScoring):
    """Scoring specifically for curator performance"""
    
    def _get_module_scoring_weights(self):
        """Define scoring weights for curator performance"""
        return {
            'accuracy': 0.4,           # How often curator was correct
            'confidence_calibration': 0.3,  # How well confidence matches accuracy
            'outcome_impact': 0.3      # How much curator decision affected outcome
        }
```

### Lesson Feedback Integration - Critical Decision Improvement
The most important aspect of the learning system is how lessons are fed back into curator decisions:

```python
class LessonEnhancedCuratorOrchestrator:
    """Curator orchestrator enhanced with lesson feedback"""
    
    def __init__(self, module_type: str):
        self.module_type = module_type
        self.registry = CuratorRegistry(module_type)
        self.lesson_feedback = LessonFeedbackSystem(module_type)
        self.db_client = DatabaseClient()
        self.logger = logging.getLogger(f"lesson_enhanced_curator.{module_type}")
        
    def curate_signal_with_lessons(self, 
                                 detector_sigma: float,
                                 context: Dict) -> Tuple[float, bool, List[CuratorContribution]]:
        """Apply curator layer with lesson-enhanced context"""
        
        # 1. Apply lessons to enhance context
        enhanced_context = self.lesson_feedback.apply_lessons_to_decisions(context)
        
        # 2. Get all curator contributions with enhanced context
        contributions = self.registry.evaluate_all(detector_sigma, enhanced_context)
        
        # 3. Apply lesson-based curator weight adjustments
        lesson_adjusted_contributions = self._apply_lesson_weight_adjustments(contributions, enhanced_context)
        
        # 4. Compute curated score with lesson enhancements
        curated_sigma, approved = self.registry.compute_curated_score(
            detector_sigma, lesson_adjusted_contributions
        )
        
        # 5. Log curator actions with lesson metadata
        self._log_curator_actions_with_lessons(lesson_adjusted_contributions, enhanced_context)
        
        return curated_sigma, approved, lesson_adjusted_contributions
    
    def _apply_lesson_weight_adjustments(self, 
                                       contributions: List[CuratorContribution], 
                                       enhanced_context: Dict) -> List[CuratorContribution]:
        """Apply lesson-based weight adjustments to curator contributions"""
        
        adjusted_contributions = []
        
        for contribution in contributions:
            # Get lesson-based weight adjustment for this curator
            weight_adjustment = enhanced_context.get(f'{contribution.curator_type}_weight', 1.0)
            
            # Apply weight adjustment to contribution
            adjusted_contribution = CuratorContribution(
                curator_type=contribution.curator_type,
                action=contribution.action,
                contribution=contribution.contribution * weight_adjustment,
                reason=f"{contribution.reason} (lesson-enhanced: {weight_adjustment:.3f})",
                evidence=contribution.evidence,
                confidence=contribution.confidence,
                timestamp=contribution.timestamp
            )
            
            adjusted_contributions.append(adjusted_contribution)
        
        return adjusted_contributions
    
    def _log_curator_actions_with_lessons(self, 
                                        contributions: List[CuratorContribution], 
                                        enhanced_context: Dict):
        """Log curator actions with lesson metadata"""
        
        for contribution in contributions:
            # Add lesson metadata to evidence
            lesson_metadata = {
                'lesson_enhanced': True,
                'lessons_applied': enhanced_context.get('lessons_applied', []),
                'weight_adjustment': enhanced_context.get(f'{contribution.curator_type}_weight', 1.0),
                'confidence_boost': enhanced_context.get('confidence_boost', 1.0)
            }
            
            # Merge with existing evidence
            enhanced_evidence = {**contribution.evidence, **lesson_metadata}
            
            self.db_client.insert_curator_action(
                detector_id=enhanced_evidence.get('detector_id'),
                module_type=self.module_type,
                curator_type=contribution.curator_type,
                action_type=contribution.action.value,
                contribution=contribution.contribution,
                reason=contribution.reason,
                evidence=enhanced_evidence,
                confidence=contribution.confidence,
                curator_version="lesson-enhanced-1.0"
            )
```

### Real-Time Lesson Application in Curators
```python
class LessonEnhancedCurator(BaseCurator):
    """Base curator enhanced with real-time lesson application"""
    
    def __init__(self, curator_type: str, kappa: float = 0.15, veto_threshold: float = 0.8):
        super().__init__(curator_type, kappa, veto_threshold)
        self.lesson_cache = LessonCache()
        self.lesson_matcher = LessonMatcher()
    
    def evaluate_with_lessons(self, detector_sigma: float, context: Dict) -> CuratorContribution:
        """Evaluate with lesson-enhanced context"""
        
        # 1. Get relevant lessons for this curator type
        relevant_lessons = self._get_curator_specific_lessons(context)
        
        # 2. Apply lesson insights to context
        enhanced_context = self._apply_curator_lessons(context, relevant_lessons)
        
        # 3. Make evaluation with enhanced context
        contribution = self.evaluate(detector_sigma, enhanced_context)
        
        # 4. Add lesson metadata to contribution
        contribution.evidence['lesson_enhanced'] = True
        contribution.evidence['lessons_applied'] = [l['id'] for l in relevant_lessons]
        
        return contribution
    
    def _get_curator_specific_lessons(self, context: Dict) -> List[Dict]:
        """Get lessons specific to this curator type"""
        
        query = {
            'module': self.module_type,
            'curator_type': self.curator_type,
            'kind': 'braid',
            'conditions': {
                'symbol': context.get('symbol'),
                'regime': context.get('regime'),
                'timeframe': context.get('timeframe')
            }
        }
        
        return self.lesson_cache.get_lessons(query)
    
    def _apply_curator_lessons(self, context: Dict, lessons: List[Dict]) -> Dict:
        """Apply curator-specific lesson insights"""
        
        enhanced_context = context.copy()
        
        for lesson in lessons:
            # Apply curator-specific adjustments
            if lesson.get('curator_adjustments'):
                adjustments = lesson['curator_adjustments']
                
                # Adjust kappa based on lesson
                if 'kappa_adjustment' in adjustments:
                    self.kappa *= adjustments['kappa_adjustment']
                
                # Adjust veto threshold based on lesson
                if 'veto_threshold_adjustment' in adjustments:
                    self.veto_threshold *= adjustments['veto_threshold_adjustment']
                
                # Apply confidence adjustments
                if 'confidence_adjustment' in adjustments:
                    enhanced_context['confidence'] *= adjustments['confidence_adjustment']
        
        return enhanced_context
```

### Lesson-Driven Curator Weight Adaptation
```python
class LessonDrivenWeightAdaptation:
    """Adapt curator weights based on lesson insights"""
    
    def __init__(self, module_type: str):
        self.module_type = module_type
        self.weight_history = {}
        self.performance_tracker = CuratorPerformanceTracker()
    
    def adapt_weights_from_lessons(self, lessons: List[Dict]):
        """Adapt curator weights based on lesson insights"""
        
        for lesson in lessons:
            if lesson.get('type') == 'curator_performance_lesson':
                curator_type = lesson.get('curator_type')
                performance_insight = lesson.get('performance_insight')
                
                # Extract weight adjustment from lesson
                weight_adjustment = self._extract_weight_adjustment(performance_insight)
                
                # Apply weight adjustment
                self._apply_weight_adjustment(curator_type, weight_adjustment)
                
                # Track weight change
                self._track_weight_change(curator_type, weight_adjustment)
    
    def _extract_weight_adjustment(self, performance_insight: Dict) -> float:
        """Extract weight adjustment from performance insight"""
        
        # Analyze performance patterns
        accuracy = performance_insight.get('accuracy', 0.5)
        confidence_calibration = performance_insight.get('confidence_calibration', 0.5)
        outcome_impact = performance_insight.get('outcome_impact', 0.5)
        
        # Calculate weight adjustment
        performance_score = (accuracy + confidence_calibration + outcome_impact) / 3.0
        
        # Convert performance score to weight adjustment
        if performance_score > 0.7:
            return 1.1  # Increase weight for good performance
        elif performance_score < 0.4:
            return 0.9  # Decrease weight for poor performance
        else:
            return 1.0  # No change for average performance
    
    def _apply_weight_adjustment(self, curator_type: str, adjustment: float):
        """Apply weight adjustment to curator"""
        
        # Update curator weight in registry
        self.curator_registry.update_curator_weight(curator_type, adjustment)
        
        # Log weight change
        self.logger.info(f"Adjusted {curator_type} weight by {adjustment:.3f}")
    
    def _track_weight_change(self, curator_type: str, adjustment: float):
        """Track weight change for analysis"""
        
        if curator_type not in self.weight_history:
            self.weight_history[curator_type] = []
        
        self.weight_history[curator_type].append({
            'timestamp': datetime.now(),
            'adjustment': adjustment,
            'new_weight': self.curator_registry.get_curator_weight(curator_type)
        })
```

## Integration with Existing System

The Curator Layer sits between the **Kernel Resonance System** and **Signal Publication**:

1. **Kernel Resonance** computes `det_sigma`
2. **Curator Layer** applies bounded influence → `curated_sigma`
3. **Signal Publication** emits signals based on `curated_sigma`
4. **Curator Learning** tracks performance and improves through strand-braid system

This maintains the mathematical integrity while adding human oversight and continuous learning.

---

*This specification provides the foundation for module-level intelligence architecture, ensuring each module has its own curator layer while maintaining system-wide coherence and learning capabilities.*
