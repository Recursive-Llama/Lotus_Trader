"""
CIL Learning & Feedback Engine

Section 5: Learning & Feedback (CIL)
- Capture All Outcomes (successes, failures, anomalies, partial results)
- Structure Results into Lessons (family/type, context, outcome, persistence, novelty, surprise rating)
- Update Strand-Braid Memory (insert lessons, cluster into braids, compress into doctrine)
- Doctrine Feedback (promote lessons, retire dead ends, refine focus)
- Cross-Agent Distribution (share updated doctrine with agents)
- Continuous Improvement (each feedback loop sharpens the system)

Vector Search Integration:
- Vector clustering for lesson organization and doctrine formation
- Vector embeddings for lesson similarity and pattern matching
- Vector search for cross-agent knowledge distribution and learning
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem
from .prediction_outcome_tracker import PredictionOutcomeTracker

logger = logging.getLogger(__name__)


class LessonType(Enum):
    """Lesson types"""
    SUCCESS = "success"
    FAILURE = "failure"
    ANOMALY = "anomaly"
    PARTIAL = "partial"
    INSIGHT = "insight"
    WARNING = "warning"


class DoctrineStatus(Enum):
    """Doctrine status"""
    PROVISIONAL = "provisional"
    AFFIRMED = "affirmed"
    RETIRED = "retired"
    CONTRAINDICATED = "contraindicated"


# Doctrine of Negatives System Integration
class NegativeType(Enum):
    """Types of negative patterns"""
    CONTRAINDICATED = "contraindicated"
    FAILURE_MODE = "failure_mode"
    ANTI_PATTERN = "anti_pattern"
    TOXIC_COMBINATION = "toxic_combination"
    REGIME_INCOMPATIBLE = "regime_incompatible"
    TIMING_INAPPROPRIATE = "timing_inappropriate"


class NegativeSeverity(Enum):
    """Severity levels for negative patterns"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NegativeStatus(Enum):
    """Status of negative pattern entries"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"
    INVESTIGATING = "investigating"


class NegativeSource(Enum):
    """Source of negative pattern identification"""
    EXPERIMENTAL_FAILURE = "experimental_failure"
    HISTORICAL_ANALYSIS = "historical_analysis"
    LLM_INSIGHT = "llm_insight"
    HUMAN_INPUT = "human_input"
    SYSTEM_DETECTION = "system_detection"


@dataclass
class Lesson:
    """Structured lesson"""
    lesson_id: str
    lesson_type: LessonType
    pattern_family: str
    context: Dict[str, Any]
    outcome: str
    persistence_score: float
    novelty_score: float
    surprise_rating: float
    evidence_count: int
    confidence_level: float
    mechanism_hypothesis: Optional[str]
    fails_when: List[str]
    created_at: datetime


@dataclass
class Braid:
    """Clustered lessons (braid)"""
    braid_id: str
    braid_name: str
    pattern_family: str
    lessons: List[Lesson]
    aggregate_metrics: Dict[str, float]
    doctrine_status: DoctrineStatus
    lineage: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class DoctrineUpdate:
    """Doctrine update"""
    update_id: str
    update_type: str  # "promote", "retire", "refine", "contraindicate"
    pattern_family: str
    rationale: str
    evidence: List[str]
    confidence_level: float
    affected_agents: List[str]
    created_at: datetime


# Doctrine of Negatives System Integration
@dataclass
class NegativePattern:
    """Negative pattern entry"""
    pattern_id: str
    negative_type: NegativeType
    pattern_description: str
    contraindicated_conditions: List[str]
    severity_level: NegativeSeverity
    status: NegativeStatus
    source: NegativeSource
    evidence_count: int
    confidence_score: float
    created_at: datetime
    updated_at: datetime


@dataclass
class NegativeAnalysis:
    """Analysis of negative patterns"""
    analysis_id: str
    pattern_combinations: List[str]
    negative_type: NegativeType
    severity_assessment: NegativeSeverity
    risk_factors: List[str]
    mitigation_strategies: List[str]
    confidence_level: float
    analysis_timestamp: datetime


@dataclass
class NegativeViolation:
    """Violation of negative doctrine"""
    violation_id: str
    experiment_id: str
    violated_patterns: List[str]
    violation_type: NegativeType
    severity_level: NegativeSeverity
    violation_description: str
    detected_at: datetime
    recommended_action: str


@dataclass
class DoctrineEvolution:
    """Evolution of negative doctrine"""
    evolution_id: str
    evolution_type: str  # "addition", "modification", "retirement"
    affected_patterns: List[str]
    evolution_rationale: str
    evidence_supporting: List[str]
    confidence_level: float
    evolved_at: datetime


class LearningFeedbackEngine:
    """
    CIL Learning & Feedback Engine
    
    Responsibilities:
    1. Capture All Outcomes (successes, failures, anomalies, partial results)
    2. Structure Results into Lessons (family/type, context, outcome, persistence, novelty, surprise rating)
    3. Update Strand-Braid Memory (insert lessons, cluster into braids, compress into doctrine)
    4. Doctrine Feedback (promote lessons, retire dead ends, refine focus)
    5. Cross-Agent Distribution (share updated doctrine with agents)
    6. Continuous Improvement (each feedback loop sharpens the system)
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        self.prediction_tracker = PredictionOutcomeTracker(supabase_manager, llm_client)
        
        # Learning configuration
        self.lesson_clustering_threshold = 0.7
        self.doctrine_promotion_threshold = 0.8
        self.doctrine_retirement_threshold = 0.3
        self.surprise_threshold = 0.6
        self.novelty_threshold = 0.5
        
        # Braid configuration
        self.min_lessons_per_braid = 3
        self.max_lessons_per_braid = 20
        self.braid_consolidation_threshold = 0.8
        
        # Doctrine of Negatives System configuration
        self.negative_patterns = {}
        self.negative_doctrine = {}
        self.violation_detection_threshold = 0.8
        self.negative_evolution_threshold = 0.7
        self.doctrine_evolution_window_days = 30
        
    async def process_learning_feedback(self, orchestration_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process learning and feedback from orchestration results
        
        Args:
            orchestration_results: Output from ExperimentOrchestrationEngine
            
        Returns:
            Dict containing learning and feedback results
        """
        try:
            # Process prediction outcomes first
            prediction_outcomes = await self.process_prediction_outcomes()
            
            # Perform learning operations in parallel
            results = await asyncio.gather(
                self.capture_all_outcomes(orchestration_results),
                self.structure_results_into_lessons(orchestration_results),
                self.update_strand_braid_memory(orchestration_results),
                self.generate_doctrine_feedback(orchestration_results),
                self.distribute_doctrine_updates(orchestration_results),
                self.assess_continuous_improvement(orchestration_results),
                return_exceptions=True
            )
            
            # Structure learning results
            learning_results = {
                'prediction_outcomes': prediction_outcomes,
                'captured_outcomes': results[0] if not isinstance(results[0], Exception) else [],
                'structured_lessons': results[1] if not isinstance(results[1], Exception) else [],
                'updated_braids': results[2] if not isinstance(results[2], Exception) else [],
                'doctrine_updates': results[3] if not isinstance(results[3], Exception) else [],
                'distributed_updates': results[4] if not isinstance(results[4], Exception) else [],
                'improvement_assessment': results[5] if not isinstance(results[5], Exception) else {},
                'learning_timestamp': datetime.now(timezone.utc),
                'learning_errors': [str(r) for r in results if isinstance(r, Exception)]
            }
            
            # Publish learning results as CIL strand
            await self._publish_learning_results(learning_results)
            
            return learning_results
            
        except Exception as e:
            print(f"Error processing learning feedback: {e}")
            return {'error': str(e), 'learning_timestamp': datetime.now(timezone.utc)}
    
    async def process_prediction_outcomes(self) -> Dict[str, Any]:
        """
        Process prediction outcomes and integrate them into learning
        
        Returns:
            Dict containing prediction outcome processing results
        """
        try:
            # Get prediction accuracy statistics
            prediction_stats = await self.prediction_tracker.get_prediction_accuracy_stats()
            
            # Process any pending predictions
            await self.prediction_tracker._track_pending_predictions()
            
            # Create learning insights from prediction outcomes
            prediction_insights = await self._generate_prediction_insights(prediction_stats)
            
            return {
                'prediction_stats': prediction_stats,
                'prediction_insights': prediction_insights,
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing prediction outcomes: {e}")
            return {'error': str(e), 'processed_at': datetime.now(timezone.utc).isoformat()}
    
    async def _generate_prediction_insights(self, prediction_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights from prediction statistics"""
        insights = []
        
        try:
            total_predictions = prediction_stats.get('total_predictions', 0)
            avg_accuracy = prediction_stats.get('avg_accuracy', 0)
            avg_confidence = prediction_stats.get('avg_confidence', 0)
            high_accuracy_rate = prediction_stats.get('high_accuracy_rate', 0)
            high_confidence_accuracy_rate = prediction_stats.get('high_confidence_accuracy_rate', 0)
            
            # Generate insights based on statistics
            if total_predictions > 0:
                if avg_accuracy > 0.7:
                    insights.append({
                        'type': 'success',
                        'message': f"High prediction accuracy: {avg_accuracy:.3f}",
                        'recommendation': 'Continue current prediction strategies',
                        'confidence': 0.8
                    })
                elif avg_accuracy < 0.4:
                    insights.append({
                        'type': 'warning',
                        'message': f"Low prediction accuracy: {avg_accuracy:.3f}",
                        'recommendation': 'Review and improve prediction models',
                        'confidence': 0.9
                    })
                
                if high_confidence_accuracy_rate > 0.8:
                    insights.append({
                        'type': 'success',
                        'message': f"Excellent confidence calibration: {high_confidence_accuracy_rate:.3f}",
                        'recommendation': 'System is well-calibrated for risk management',
                        'confidence': 0.8
                    })
                elif high_confidence_accuracy_rate < 0.5:
                    insights.append({
                        'type': 'warning',
                        'message': f"Poor confidence calibration: {high_confidence_accuracy_rate:.3f}",
                        'recommendation': 'Improve confidence estimation models',
                        'confidence': 0.9
                    })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating prediction insights: {e}")
            return []
    
    async def capture_all_outcomes(self, orchestration_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Capture all outcomes from orchestration results
        
        Returns:
            List of captured outcomes with metadata
        """
        try:
            captured_outcomes = []
            
            # Get experiment results
            completed_experiments = orchestration_results.get('completed_experiments', [])
            
            for experiment in completed_experiments:
                # Capture experiment outcome
                outcome = {
                    'outcome_id': f"OUTCOME_{int(datetime.now().timestamp())}_{len(captured_outcomes)}",
                    'experiment_id': experiment.experiment_id,
                    'agent_id': experiment.agent_id,
                    'outcome_type': experiment.outcome,
                    'metrics': experiment.metrics,
                    'lessons_learned': experiment.lessons_learned,
                    'recommendations': experiment.recommendations,
                    'confidence_score': experiment.confidence_score,
                    'completion_time': experiment.completion_time,
                    'captured_at': datetime.now(timezone.utc)
                }
                
                captured_outcomes.append(outcome)
            
            # Get active experiment progress
            active_experiments = orchestration_results.get('active_experiments', [])
            
            for experiment in active_experiments:
                # Capture progress outcome
                progress_outcome = {
                    'outcome_id': f"PROGRESS_{int(datetime.now().timestamp())}_{len(captured_outcomes)}",
                    'experiment_id': experiment.get('experiment_id'),
                    'agent_id': experiment.get('target_agent'),
                    'outcome_type': 'progress',
                    'progress_metrics': {
                        'time_elapsed': (datetime.now(timezone.utc) - experiment.get('created_at')).total_seconds() / 3600,
                        'deadline_remaining': (experiment.get('deadline') - datetime.now(timezone.utc)).total_seconds() / 3600
                    },
                    'captured_at': datetime.now(timezone.utc)
                }
                
                captured_outcomes.append(progress_outcome)
            
            return captured_outcomes
            
        except Exception as e:
            print(f"Error capturing outcomes: {e}")
            return []
    
    async def structure_results_into_lessons(self, orchestration_results: Dict[str, Any]) -> List[Lesson]:
        """
        Structure captured outcomes into lessons
        
        Returns:
            List of structured Lesson objects
        """
        try:
            # Get captured outcomes
            captured_outcomes = await self.capture_all_outcomes(orchestration_results)
            
            structured_lessons = []
            for outcome in captured_outcomes:
                # Determine lesson type
                lesson_type = self._determine_lesson_type(outcome)
                
                # Extract pattern family
                pattern_family = self._extract_pattern_family(outcome)
                
                # Determine context
                context = self._extract_lesson_context(outcome)
                
                # Calculate persistence score
                persistence_score = self._calculate_persistence_score(outcome)
                
                # Calculate novelty score
                novelty_score = self._calculate_novelty_score(outcome)
                
                # Calculate surprise rating
                surprise_rating = self._calculate_surprise_rating(outcome)
                
                # Count evidence
                evidence_count = self._count_evidence(outcome)
                
                # Calculate confidence level
                confidence_level = self._calculate_confidence_level(outcome)
                
                # Generate mechanism hypothesis
                mechanism_hypothesis = await self._generate_mechanism_hypothesis(outcome)
                
                # Determine failure conditions
                fails_when = await self._determine_failure_conditions(outcome)
                
                # Create lesson
                lesson = Lesson(
                    lesson_id=f"LESSON_{int(datetime.now().timestamp())}_{len(structured_lessons)}",
                    lesson_type=lesson_type,
                    pattern_family=pattern_family,
                    context=context,
                    outcome=outcome.get('outcome_type', 'unknown'),
                    persistence_score=persistence_score,
                    novelty_score=novelty_score,
                    surprise_rating=surprise_rating,
                    evidence_count=evidence_count,
                    confidence_level=confidence_level,
                    mechanism_hypothesis=mechanism_hypothesis,
                    fails_when=fails_when,
                    created_at=datetime.now(timezone.utc)
                )
                
                structured_lessons.append(lesson)
            
            return structured_lessons
            
        except Exception as e:
            print(f"Error structuring lessons: {e}")
            return []
    
    async def update_strand_braid_memory(self, orchestration_results: Dict[str, Any]) -> List[Braid]:
        """
        Update strand-braid memory with new lessons
        
        Returns:
            List of updated Braid objects
        """
        try:
            # Get structured lessons
            structured_lessons = await self.structure_results_into_lessons(orchestration_results)
            
            # Get existing braids
            existing_braids = await self._get_existing_braids()
            
            # Cluster lessons into braids
            updated_braids = []
            
            for lesson in structured_lessons:
                # Find matching braid or create new one
                matching_braid = self._find_matching_braid(lesson, existing_braids)
                
                if matching_braid:
                    # Add lesson to existing braid
                    matching_braid.lessons.append(lesson)
                    matching_braid.updated_at = datetime.now(timezone.utc)
                    
                    # Update aggregate metrics
                    matching_braid.aggregate_metrics = self._calculate_braid_metrics(matching_braid.lessons)
                    
                    # Update doctrine status
                    matching_braid.doctrine_status = self._update_doctrine_status(matching_braid)
                    
                    updated_braids.append(matching_braid)
                else:
                    # Create new braid
                    new_braid = Braid(
                        braid_id=f"BRAID_{int(datetime.now().timestamp())}_{len(updated_braids)}",
                        braid_name=f"{lesson.pattern_family}_braid",
                        pattern_family=lesson.pattern_family,
                        lessons=[lesson],
                        aggregate_metrics=self._calculate_braid_metrics([lesson]),
                        doctrine_status=DoctrineStatus.PROVISIONAL,
                        lineage={'created_from': lesson.lesson_id},
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    
                    updated_braids.append(new_braid)
            
            # Consolidate braids if needed
            consolidated_braids = await self._consolidate_braids(updated_braids)
            
            # Save braids to database
            await self._save_braids_to_database(consolidated_braids)
            
            return consolidated_braids
            
        except Exception as e:
            print(f"Error updating strand-braid memory: {e}")
            return []
    
    async def generate_doctrine_feedback(self, orchestration_results: Dict[str, Any]) -> List[DoctrineUpdate]:
        """
        Generate doctrine feedback from updated braids
        
        Returns:
            List of DoctrineUpdate objects
        """
        try:
            # Get updated braids
            updated_braids = await self.update_strand_braid_memory(orchestration_results)
            
            doctrine_updates = []
            
            for braid in updated_braids:
                # Check if braid should be promoted
                if self._should_promote_braid(braid):
                    update = DoctrineUpdate(
                        update_id=f"PROMOTE_{int(datetime.now().timestamp())}_{len(doctrine_updates)}",
                        update_type="promote",
                        pattern_family=braid.pattern_family,
                        rationale=f"Braid {braid.braid_name} meets promotion criteria",
                        evidence=[lesson.lesson_id for lesson in braid.lessons],
                        confidence_level=braid.aggregate_metrics.get('confidence', 0.0),
                        affected_agents=self._get_affected_agents(braid),
                        created_at=datetime.now(timezone.utc)
                    )
                    doctrine_updates.append(update)
                
                # Check if braid should be retired
                elif self._should_retire_braid(braid):
                    update = DoctrineUpdate(
                        update_id=f"RETIRE_{int(datetime.now().timestamp())}_{len(doctrine_updates)}",
                        update_type="retire",
                        pattern_family=braid.pattern_family,
                        rationale=f"Braid {braid.braid_name} meets retirement criteria",
                        evidence=[lesson.lesson_id for lesson in braid.lessons],
                        confidence_level=braid.aggregate_metrics.get('confidence', 0.0),
                        affected_agents=self._get_affected_agents(braid),
                        created_at=datetime.now(timezone.utc)
                    )
                    doctrine_updates.append(update)
                
                # Check if braid should be refined
                elif self._should_refine_braid(braid):
                    update = DoctrineUpdate(
                        update_id=f"REFINE_{int(datetime.now().timestamp())}_{len(doctrine_updates)}",
                        update_type="refine",
                        pattern_family=braid.pattern_family,
                        rationale=f"Braid {braid.braid_name} needs refinement",
                        evidence=[lesson.lesson_id for lesson in braid.lessons],
                        confidence_level=braid.aggregate_metrics.get('confidence', 0.0),
                        affected_agents=self._get_affected_agents(braid),
                        created_at=datetime.now(timezone.utc)
                    )
                    doctrine_updates.append(update)
                
                # Check if braid should be contraindicated
                elif self._should_contraindicate_braid(braid):
                    update = DoctrineUpdate(
                        update_id=f"CONTRAINDICATE_{int(datetime.now().timestamp())}_{len(doctrine_updates)}",
                        update_type="contraindicate",
                        pattern_family=braid.pattern_family,
                        rationale=f"Braid {braid.braid_name} should be contraindicated",
                        evidence=[lesson.lesson_id for lesson in braid.lessons],
                        confidence_level=braid.aggregate_metrics.get('confidence', 0.0),
                        affected_agents=self._get_affected_agents(braid),
                        created_at=datetime.now(timezone.utc)
                    )
                    doctrine_updates.append(update)
            
            return doctrine_updates
            
        except Exception as e:
            print(f"Error generating doctrine feedback: {e}")
            return []
    
    async def distribute_doctrine_updates(self, orchestration_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Distribute doctrine updates to affected agents
        
        Returns:
            List of distribution results
        """
        try:
            # Get doctrine updates
            doctrine_updates = await self.generate_doctrine_feedback(orchestration_results)
            
            distribution_results = []
            
            for update in doctrine_updates:
                # Create distribution strands for each affected agent
                for agent_id in update.affected_agents:
                    distribution_strand = {
                        'id': f"DOCTRINE_{update.update_id}_{agent_id}",
                        'kind': 'doctrine_update',
                        'module': 'alpha',
                        'agent_id': 'central_intelligence_layer',
                        'team_member': 'learning_feedback_engine',
                        'symbol': 'SYSTEM',
                        'timeframe': 'system',
                        'session_bucket': 'GLOBAL',
                        'regime': 'system',
                        'tags': [f'agent:{agent_id}:coordinator:doctrine_update'],
                        'module_intelligence': {
                            'update_type': update.update_type,
                            'pattern_family': update.pattern_family,
                            'rationale': update.rationale,
                            'evidence': update.evidence,
                            'confidence_level': update.confidence_level,
                            'target_agent': agent_id
                        },
                        'sig_sigma': 1.0,
                        'sig_confidence': update.confidence_level,
                        'sig_direction': 'neutral',
                        'outcome_score': 1.0,
                        'created_at': datetime.now(timezone.utc)
                    }
                    
                    # Insert distribution strand
                    await self.supabase_manager.insert_strand(distribution_strand)
                    
                    distribution_results.append({
                        'update_id': update.update_id,
                        'target_agent': agent_id,
                        'distribution_status': 'sent',
                        'distributed_at': datetime.now(timezone.utc)
                    })
            
            return distribution_results
            
        except Exception as e:
            print(f"Error distributing doctrine updates: {e}")
            return []
    
    async def assess_continuous_improvement(self, orchestration_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess continuous improvement of the system
        
        Returns:
            Dict containing improvement assessment
        """
        try:
            # Get all learning components
            captured_outcomes = await self.capture_all_outcomes(orchestration_results)
            structured_lessons = await self.structure_results_into_lessons(orchestration_results)
            updated_braids = await self.update_strand_braid_memory(orchestration_results)
            doctrine_updates = await self.generate_doctrine_feedback(orchestration_results)
            
            # Calculate improvement metrics
            improvement_metrics = {
                'outcomes_processed': len(captured_outcomes),
                'lessons_structured': len(structured_lessons),
                'braids_updated': len(updated_braids),
                'doctrine_updates_generated': len(doctrine_updates),
                'system_learning_rate': self._calculate_learning_rate(structured_lessons),
                'doctrine_evolution_rate': self._calculate_doctrine_evolution_rate(doctrine_updates),
                'pattern_discovery_rate': self._calculate_pattern_discovery_rate(updated_braids),
                'knowledge_retention_rate': self._calculate_knowledge_retention_rate(updated_braids)
            }
            
            # Assess system sharpening
            system_sharpening = {
                'accuracy_improvement': self._assess_accuracy_improvement(structured_lessons),
                'efficiency_improvement': self._assess_efficiency_improvement(structured_lessons),
                'novelty_improvement': self._assess_novelty_improvement(structured_lessons),
                'resilience_improvement': self._assess_resilience_improvement(updated_braids)
            }
            
            # Generate improvement recommendations
            improvement_recommendations = await self._generate_improvement_recommendations(
                improvement_metrics, system_sharpening
            )
            
            return {
                'improvement_metrics': improvement_metrics,
                'system_sharpening': system_sharpening,
                'improvement_recommendations': improvement_recommendations,
                'assessment_timestamp': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            print(f"Error assessing continuous improvement: {e}")
            return {'error': str(e), 'assessment_timestamp': datetime.now(timezone.utc)}
    
    def _determine_lesson_type(self, outcome: Dict[str, Any]) -> LessonType:
        """Determine lesson type from outcome"""
        outcome_type = outcome.get('outcome_type', 'unknown')
        
        if outcome_type == 'success':
            return LessonType.SUCCESS
        elif outcome_type == 'failure':
            return LessonType.FAILURE
        elif outcome_type == 'anomaly':
            return LessonType.ANOMALY
        elif outcome_type == 'partial':
            return LessonType.PARTIAL
        elif outcome_type == 'progress':
            return LessonType.INSIGHT
        else:
            return LessonType.INSIGHT  # Default
    
    def _extract_pattern_family(self, outcome: Dict[str, Any]) -> str:
        """Extract pattern family from outcome"""
        # Try to extract from experiment context
        experiment_id = outcome.get('experiment_id', '')
        if 'divergence' in experiment_id.lower():
            return 'divergence'
        elif 'volume' in experiment_id.lower():
            return 'volume_analysis'
        elif 'correlation' in experiment_id.lower():
            return 'correlation_analysis'
        elif 'pattern' in experiment_id.lower():
            return 'pattern_recognition'
        else:
            return 'general'  # Default
    
    def _extract_lesson_context(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Extract lesson context from outcome"""
        return {
            'experiment_id': outcome.get('experiment_id'),
            'agent_id': outcome.get('agent_id'),
            'outcome_type': outcome.get('outcome_type'),
            'completion_time': outcome.get('completion_time'),
            'metrics': outcome.get('metrics', {}),
            'confidence_score': outcome.get('confidence_score', 0.0)
        }
    
    def _calculate_persistence_score(self, outcome: Dict[str, Any]) -> float:
        """Calculate persistence score for outcome"""
        # Base persistence on confidence and evidence
        confidence = outcome.get('confidence_score', 0.0)
        metrics = outcome.get('metrics', {})
        
        # Calculate persistence based on metrics consistency
        if 'accuracy' in metrics and 'precision' in metrics:
            consistency = (metrics['accuracy'] + metrics['precision']) / 2
        else:
            consistency = confidence
        
        return min(consistency, 1.0)
    
    def _calculate_novelty_score(self, outcome: Dict[str, Any]) -> float:
        """Calculate novelty score for outcome"""
        # Base novelty on surprise and uniqueness
        metrics = outcome.get('metrics', {})
        
        # Check for novel patterns in metrics
        novelty_indicators = 0
        if 'accuracy' in metrics and metrics['accuracy'] > 0.8:
            novelty_indicators += 1
        if 'precision' in metrics and metrics['precision'] > 0.8:
            novelty_indicators += 1
        if 'recall' in metrics and metrics['recall'] > 0.8:
            novelty_indicators += 1
        
        return min(novelty_indicators / 3.0, 1.0)
    
    def _calculate_surprise_rating(self, outcome: Dict[str, Any]) -> float:
        """Calculate surprise rating for outcome"""
        # Base surprise on unexpected outcomes
        outcome_type = outcome.get('outcome_type', 'unknown')
        confidence = outcome.get('confidence_score', 0.0)
        
        if outcome_type == 'anomaly':
            return 0.9  # High surprise for anomalies
        elif outcome_type == 'failure' and confidence > 0.7:
            return 0.8  # High surprise for confident failures
        elif outcome_type == 'success' and confidence < 0.5:
            return 0.7  # High surprise for low-confidence successes
        else:
            return 0.3  # Low surprise for expected outcomes
    
    def _count_evidence(self, outcome: Dict[str, Any]) -> int:
        """Count evidence for outcome"""
        evidence_count = 0
        
        # Count metrics as evidence
        metrics = outcome.get('metrics', {})
        evidence_count += len(metrics)
        
        # Count lessons learned as evidence
        lessons_learned = outcome.get('lessons_learned', [])
        evidence_count += len(lessons_learned)
        
        # Count recommendations as evidence
        recommendations = outcome.get('recommendations', [])
        evidence_count += len(recommendations)
        
        return max(evidence_count, 1)  # At least 1 evidence
    
    def _calculate_confidence_level(self, outcome: Dict[str, Any]) -> float:
        """Calculate confidence level for outcome"""
        return outcome.get('confidence_score', 0.5)
    
    async def _generate_mechanism_hypothesis(self, outcome: Dict[str, Any]) -> Optional[str]:
        """Generate mechanism hypothesis for outcome"""
        # This would typically use LLM to generate hypotheses
        # For now, return a placeholder
        outcome_type = outcome.get('outcome_type', 'unknown')
        pattern_family = self._extract_pattern_family(outcome)
        
        return f"Mechanism hypothesis for {pattern_family} {outcome_type}: Placeholder hypothesis"
    
    async def _determine_failure_conditions(self, outcome: Dict[str, Any]) -> List[str]:
        """Determine failure conditions for outcome"""
        # This would typically analyze the outcome to determine failure conditions
        # For now, return placeholder conditions
        return [
            "Low confidence threshold",
            "Insufficient evidence",
            "Contradictory results"
        ]
    
    async def _get_existing_braids(self) -> List[Braid]:
        """Get existing braids from database"""
        # This would typically query the database for existing braids
        # For now, return empty list
        return []
    
    def _find_matching_braid(self, lesson: Lesson, existing_braids: List[Braid]) -> Optional[Braid]:
        """Find matching braid for lesson"""
        for braid in existing_braids:
            if braid.pattern_family == lesson.pattern_family:
                return braid
        return None
    
    def _calculate_braid_metrics(self, lessons: List[Lesson]) -> Dict[str, float]:
        """Calculate aggregate metrics for braid"""
        if not lessons:
            return {}
        
        return {
            'avg_persistence': sum(lesson.persistence_score for lesson in lessons) / len(lessons),
            'avg_novelty': sum(lesson.novelty_score for lesson in lessons) / len(lessons),
            'avg_surprise': sum(lesson.surprise_rating for lesson in lessons) / len(lessons),
            'avg_confidence': sum(lesson.confidence_level for lesson in lessons) / len(lessons),
            'total_evidence': sum(lesson.evidence_count for lesson in lessons),
            'lesson_count': len(lessons)
        }
    
    def _update_doctrine_status(self, braid: Braid) -> DoctrineStatus:
        """Update doctrine status for braid"""
        metrics = braid.aggregate_metrics
        
        if metrics.get('avg_confidence', 0.0) > self.doctrine_promotion_threshold:
            return DoctrineStatus.AFFIRMED
        elif metrics.get('avg_confidence', 0.0) < self.doctrine_retirement_threshold:
            return DoctrineStatus.RETIRED
        else:
            return DoctrineStatus.PROVISIONAL
    
    async def _consolidate_braids(self, braids: List[Braid]) -> List[Braid]:
        """Consolidate similar braids"""
        # This would typically merge similar braids
        # For now, return braids as-is
        return braids
    
    async def _save_braids_to_database(self, braids: List[Braid]):
        """Save braids to database"""
        for braid in braids:
            # Create braid strand
            braid_strand = {
                'id': braid.braid_id,
                'kind': 'braid',
                'module': 'alpha',
                'agent_id': 'central_intelligence_layer',
                'team_member': 'learning_feedback_engine',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'session_bucket': 'GLOBAL',
                'regime': 'system',
                'tags': ['agent:central_intelligence:learning_feedback_engine:braid_updated'],
                'module_intelligence': {
                    'braid_name': braid.braid_name,
                    'pattern_family': braid.pattern_family,
                    'aggregate_metrics': braid.aggregate_metrics,
                    'doctrine_status': braid.doctrine_status.value,
                    'lineage': braid.lineage,
                    'lesson_count': len(braid.lessons)
                },
                'sig_sigma': 1.0,
                'sig_confidence': braid.aggregate_metrics.get('avg_confidence', 0.0),
                'sig_direction': 'neutral',
                'outcome_score': 1.0,
                'created_at': braid.created_at,
                'updated_at': braid.updated_at
            }
            
            # Insert braid strand
            await self.supabase_manager.insert_strand(braid_strand)
    
    def _should_promote_braid(self, braid: Braid) -> bool:
        """Check if braid should be promoted"""
        metrics = braid.aggregate_metrics
        return (metrics.get('avg_confidence', 0.0) > self.doctrine_promotion_threshold and
                metrics.get('lesson_count', 0) >= self.min_lessons_per_braid)
    
    def _should_retire_braid(self, braid: Braid) -> bool:
        """Check if braid should be retired"""
        metrics = braid.aggregate_metrics
        return (metrics.get('avg_confidence', 0.0) < self.doctrine_retirement_threshold and
                metrics.get('lesson_count', 0) >= self.min_lessons_per_braid)
    
    def _should_refine_braid(self, braid: Braid) -> bool:
        """Check if braid should be refined"""
        metrics = braid.aggregate_metrics
        return (self.doctrine_retirement_threshold <= metrics.get('avg_confidence', 0.0) <= self.doctrine_promotion_threshold and
                metrics.get('lesson_count', 0) >= self.min_lessons_per_braid)
    
    def _should_contraindicate_braid(self, braid: Braid) -> bool:
        """Check if braid should be contraindicated"""
        # Check for high failure rate
        failure_lessons = [lesson for lesson in braid.lessons if lesson.lesson_type == LessonType.FAILURE]
        failure_rate = len(failure_lessons) / len(braid.lessons) if braid.lessons else 0
        
        return failure_rate > 0.7  # 70% failure rate
    
    def _get_affected_agents(self, braid: Braid) -> List[str]:
        """Get agents affected by braid"""
        # Extract unique agents from lessons
        agents = set()
        for lesson in braid.lessons:
            if 'agent_id' in lesson.context:
                agents.add(lesson.context['agent_id'])
        
        return list(agents) if agents else ['raw_data_intelligence', 'indicator_intelligence']
    
    def _calculate_learning_rate(self, lessons: List[Lesson]) -> float:
        """Calculate system learning rate"""
        if not lessons:
            return 0.0
        
        # Calculate based on novelty and surprise
        avg_novelty = sum(lesson.novelty_score for lesson in lessons) / len(lessons)
        avg_surprise = sum(lesson.surprise_rating for lesson in lessons) / len(lessons)
        
        return (avg_novelty + avg_surprise) / 2
    
    def _calculate_doctrine_evolution_rate(self, doctrine_updates: List[DoctrineUpdate]) -> float:
        """Calculate doctrine evolution rate"""
        if not doctrine_updates:
            return 0.0
        
        # Count different types of updates
        update_types = set(update.update_type for update in doctrine_updates)
        return len(update_types) / 4.0  # 4 possible update types
    
    def _calculate_pattern_discovery_rate(self, braids: List[Braid]) -> float:
        """Calculate pattern discovery rate"""
        if not braids:
            return 0.0
        
        # Count new patterns
        new_patterns = sum(1 for braid in braids if braid.doctrine_status == DoctrineStatus.PROVISIONAL)
        return new_patterns / len(braids)
    
    def _calculate_knowledge_retention_rate(self, braids: List[Braid]) -> float:
        """Calculate knowledge retention rate"""
        if not braids:
            return 0.0
        
        # Calculate based on affirmed braids
        affirmed_braids = sum(1 for braid in braids if braid.doctrine_status == DoctrineStatus.AFFIRMED)
        return affirmed_braids / len(braids)
    
    def _assess_accuracy_improvement(self, lessons: List[Lesson]) -> float:
        """Assess accuracy improvement"""
        if not lessons:
            return 0.0
        
        # Calculate based on success lessons
        success_lessons = [lesson for lesson in lessons if lesson.lesson_type == LessonType.SUCCESS]
        return len(success_lessons) / len(lessons)
    
    def _assess_efficiency_improvement(self, lessons: List[Lesson]) -> float:
        """Assess efficiency improvement"""
        if not lessons:
            return 0.0
        
        # Calculate based on persistence scores
        avg_persistence = sum(lesson.persistence_score for lesson in lessons) / len(lessons)
        return avg_persistence
    
    def _assess_novelty_improvement(self, lessons: List[Lesson]) -> float:
        """Assess novelty improvement"""
        if not lessons:
            return 0.0
        
        # Calculate based on novelty scores
        avg_novelty = sum(lesson.novelty_score for lesson in lessons) / len(lessons)
        return avg_novelty
    
    def _assess_resilience_improvement(self, braids: List[Braid]) -> float:
        """Assess resilience improvement"""
        if not braids:
            return 0.0
        
        # Calculate based on affirmed braids
        affirmed_braids = sum(1 for braid in braids if braid.doctrine_status == DoctrineStatus.AFFIRMED)
        return affirmed_braids / len(braids)
    
    async def _generate_improvement_recommendations(self, improvement_metrics: Dict[str, Any], 
                                                  system_sharpening: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Analyze metrics and generate recommendations
        if improvement_metrics.get('system_learning_rate', 0.0) < 0.5:
            recommendations.append("Increase system learning rate by exploring more novel patterns")
        
        if improvement_metrics.get('doctrine_evolution_rate', 0.0) < 0.3:
            recommendations.append("Accelerate doctrine evolution by promoting more patterns")
        
        if system_sharpening.get('accuracy_improvement', 0.0) < 0.7:
            recommendations.append("Improve accuracy by focusing on high-confidence patterns")
        
        if system_sharpening.get('efficiency_improvement', 0.0) < 0.6:
            recommendations.append("Enhance efficiency by consolidating similar patterns")
        
        return recommendations
    
    # Doctrine of Negatives System Methods
    async def process_doctrine_of_negatives_analysis(self, experiment_designs: List[Dict[str, Any]],
                                                   pattern_conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process doctrine of negatives analysis"""
        try:
            # Analyze patterns for negative combinations
            negative_analyses = await self._analyze_negative_patterns(experiment_designs, pattern_conditions)
            
            # Detect violations of negative doctrine
            negative_violations = await self._detect_negative_violations(experiment_designs)
            
            # Evolve negative doctrine based on new evidence
            doctrine_evolution = await self._evolve_negative_doctrine(negative_analyses, negative_violations)
            
            # Update negative patterns based on analysis and evolution
            pattern_updates = await self._update_negative_patterns(negative_analyses, doctrine_evolution)
            
            # Compile results
            results = {
                'negative_analyses': len(negative_analyses),
                'negative_violations': len(negative_violations),
                'doctrine_evolution': len(doctrine_evolution),
                'pattern_updates': len(pattern_updates),
                'doctrine_insights': self._compile_doctrine_insights(negative_analyses, negative_violations, doctrine_evolution)
            }
            
            # Publish doctrine results
            await self._publish_doctrine_results(results)
            
            return results
            
        except Exception as e:
            print(f"Error in doctrine of negatives analysis: {e}")
            return {'error': str(e)}
    
    async def _analyze_negative_patterns(self, experiment_designs: List[Dict[str, Any]],
                                       pattern_conditions: List[Dict[str, Any]]) -> List[NegativeAnalysis]:
        """Analyze patterns for negative combinations"""
        analyses = []
        
        for design in experiment_designs:
            # Check for negative pattern combinations
            pattern_combinations = self._extract_pattern_combinations(design)
            
            if len(pattern_combinations) > 1:  # Only analyze if multiple patterns
                # Generate negative analysis
                analysis_data = {
                    'pattern_combinations': pattern_combinations,
                    'experiment_context': design.get('context', {}),
                    'historical_evidence': self._get_historical_evidence(pattern_combinations)
                }
                
                analysis = await self._generate_negative_analysis(analysis_data)
                if analysis:
                    analyses.append(analysis)
        
        return analyses
    
    async def _detect_negative_violations(self, experiment_designs: List[Dict[str, Any]]) -> List[NegativeViolation]:
        """Detect violations of negative doctrine"""
        violations = []
        
        for design in experiment_designs:
            # Check against known negative patterns
            violated_patterns = self._check_negative_violations(design)
            
            if violated_patterns:
                # Generate violation detection
                detection_data = {
                    'experiment_design': design,
                    'violated_patterns': violated_patterns,
                    'negative_doctrine': self.negative_doctrine
                }
                
                violation_analysis = await self._generate_violation_detection(detection_data)
                if violation_analysis:
                    # Create violation record
                    violation = NegativeViolation(
                        violation_id=f"violation_{design.get('experiment_id', 'unknown')}_{int(datetime.now().timestamp())}",
                        experiment_id=design.get('experiment_id', 'unknown'),
                        violated_patterns=violated_patterns,
                        violation_type=NegativeType(violation_analysis.get('violation_type', 'contraindicated')),
                        severity_level=NegativeSeverity(violation_analysis.get('severity_level', 'medium')),
                        violation_description=violation_analysis.get('violation_description', ''),
                        detected_at=datetime.now(timezone.utc),
                        recommended_action=violation_analysis.get('recommended_action', '')
                    )
                    violations.append(violation)
        
        return violations
    
    async def _evolve_negative_doctrine(self, negative_analyses: List[NegativeAnalysis],
                                      violation_detections: List[NegativeViolation]) -> List[Dict[str, Any]]:
        """Evolve negative doctrine based on new evidence"""
        evolution_updates = []
        
        # Analyze patterns for doctrine evolution
        for analysis in negative_analyses:
            if analysis.confidence_level >= self.negative_evolution_threshold:
                # Generate doctrine evolution
                evolution_data = {
                    'negative_analysis': analysis,
                    'existing_doctrine': self.negative_doctrine,
                    'violation_evidence': [v for v in violation_detections if v.violation_type == analysis.negative_type]
                }
                
                evolution = await self._generate_doctrine_evolution(evolution_data)
                if evolution:
                    evolution_updates.append(evolution)
        
        return evolution_updates
    
    async def _update_negative_patterns(self, negative_analyses: List[NegativeAnalysis],
                                      doctrine_evolution: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update negative patterns based on analysis and evolution"""
        pattern_updates = []
        
        # Update patterns based on analyses
        for analysis in negative_analyses:
            pattern_id = f"negative_{analysis.negative_type.value}_{int(datetime.now().timestamp())}"
            
            # Create or update negative pattern
            negative_pattern = NegativePattern(
                pattern_id=pattern_id,
                negative_type=analysis.negative_type,
                pattern_description=f"Negative pattern: {', '.join(analysis.pattern_combinations)}",
                contraindicated_conditions=analysis.risk_factors,
                severity_level=analysis.severity_assessment,
                status=NegativeStatus.ACTIVE,
                source=NegativeSource.SYSTEM_DETECTION,
                evidence_count=1,
                confidence_score=analysis.confidence_level,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.negative_patterns[pattern_id] = negative_pattern
            
            pattern_updates.append({
                'pattern_id': pattern_id,
                'update_type': 'created',
                'negative_type': analysis.negative_type.value,
                'severity_level': analysis.severity_assessment.value
            })
        
        # Update doctrine based on evolution
        for evolution in doctrine_evolution:
            evolution_type = evolution.get('evolution_type', 'addition')
            affected_patterns = evolution.get('affected_patterns', [])
            
            if evolution_type == 'addition':
                # Add new negative patterns to doctrine
                for pattern_id in affected_patterns:
                    if pattern_id in self.negative_patterns:
                        self.negative_doctrine[pattern_id] = self.negative_patterns[pattern_id]
            
            elif evolution_type == 'modification':
                # Modify existing patterns
                for pattern_id in affected_patterns:
                    if pattern_id in self.negative_patterns:
                        self.negative_patterns[pattern_id].updated_at = datetime.now(timezone.utc)
            
            elif evolution_type == 'retirement':
                # Retire patterns
                for pattern_id in affected_patterns:
                    if pattern_id in self.negative_patterns:
                        self.negative_patterns[pattern_id].status = NegativeStatus.RETIRED
                        if pattern_id in self.negative_doctrine:
                            del self.negative_doctrine[pattern_id]
            
            pattern_updates.append({
                'evolution_type': evolution_type,
                'affected_patterns': affected_patterns,
                'confidence_level': evolution.get('confidence_level', 0.0)
            })
        
        return pattern_updates
    
    def _extract_pattern_combinations(self, design: Dict[str, Any]) -> List[str]:
        """Extract pattern combinations from experiment design"""
        combinations = []
        
        # Extract patterns from design
        patterns = design.get('patterns', [])
        if isinstance(patterns, list):
            combinations.extend(patterns)
        elif isinstance(patterns, dict):
            combinations.extend(patterns.keys())
        
        # Extract from context
        context = design.get('context', {})
        if 'pattern_types' in context:
            combinations.extend(context['pattern_types'])
        
        return list(set(combinations))  # Remove duplicates
    
    def _get_historical_evidence(self, pattern_combinations: List[str]) -> List[Dict[str, Any]]:
        """Get historical evidence for pattern combinations"""
        evidence = []
        
        # Simple historical evidence lookup
        for combination in pattern_combinations:
            # Check if we have historical data for this combination
            if combination in self.negative_patterns:
                pattern = self.negative_patterns[combination]
                evidence.append({
                    'pattern': combination,
                    'negative_type': pattern.negative_type.value,
                    'severity': pattern.severity_level.value,
                    'evidence_count': pattern.evidence_count,
                    'confidence': pattern.confidence_score
                })
        
        return evidence
    
    def _check_negative_violations(self, design: Dict[str, Any]) -> List[str]:
        """Check experiment design against negative doctrine"""
        violations = []
        
        # Extract patterns from design
        pattern_combinations = self._extract_pattern_combinations(design)
        
        # Check against negative doctrine
        for pattern_id, negative_pattern in self.negative_doctrine.items():
            if negative_pattern.status == NegativeStatus.ACTIVE:
                # Check if design violates this negative pattern
                for condition in negative_pattern.contraindicated_conditions:
                    if any(condition.lower() in combo.lower() for combo in pattern_combinations):
                        violations.append(pattern_id)
                        break
        
        return violations
    
    async def _generate_negative_analysis(self, analysis_data: Dict[str, Any]) -> Optional[NegativeAnalysis]:
        """Generate negative analysis using LLM"""
        try:
            # Generate LLM analysis
            llm_analysis = await self._generate_llm_analysis(self._get_negative_analysis_prompt(), analysis_data)
            
            if llm_analysis:
                return NegativeAnalysis(
                    analysis_id=f"analysis_{int(datetime.now().timestamp())}",
                    pattern_combinations=analysis_data.get('pattern_combinations', []),
                    negative_type=NegativeType(llm_analysis.get('negative_type', 'contraindicated')),
                    severity_assessment=NegativeSeverity(llm_analysis.get('severity_level', 'medium')),
                    risk_factors=llm_analysis.get('risk_factors', []),
                    mitigation_strategies=llm_analysis.get('mitigation_strategies', []),
                    confidence_level=llm_analysis.get('confidence_level', 0.5),
                    analysis_timestamp=datetime.now(timezone.utc)
                )
            
            return None
            
        except Exception as e:
            print(f"Error generating negative analysis: {e}")
            return None
    
    async def _generate_violation_detection(self, detection_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate violation detection using LLM"""
        try:
            # Generate LLM analysis
            llm_analysis = await self._generate_llm_analysis(self._get_violation_detection_prompt(), detection_data)
            
            return llm_analysis
            
        except Exception as e:
            print(f"Error generating violation detection: {e}")
            return None
    
    async def _generate_doctrine_evolution(self, evolution_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate doctrine evolution using LLM"""
        try:
            # Generate LLM analysis
            llm_analysis = await self._generate_llm_analysis(self._get_doctrine_evolution_prompt(), evolution_data)
            
            return llm_analysis
            
        except Exception as e:
            print(f"Error generating doctrine evolution: {e}")
            return None
    
    async def _generate_llm_analysis(self, prompt_template: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate LLM analysis using prompt template"""
        try:
            # Format prompt with data
            formatted_prompt = prompt_template.format(**data)
            
            # Get LLM response
            response = await self.llm_client.generate_response(
                prompt=formatted_prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse JSON response
            if response and response.strip():
                return json.loads(response)
            
            return None
            
        except Exception as e:
            print(f"Error generating LLM analysis: {e}")
            return None
    
    def _compile_doctrine_insights(self, negative_analyses: List[NegativeAnalysis], 
                                 negative_violations: List[NegativeViolation],
                                 doctrine_evolution: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compile doctrine insights from analyses, violations, and evolution"""
        insights = []
        
        # Insights from negative analyses
        for analysis in negative_analyses:
            insight = {
                'type': 'negative_analysis',
                'negative_type': analysis.negative_type.value,
                'severity': analysis.severity_assessment.value,
                'pattern_combinations': analysis.pattern_combinations,
                'confidence_level': analysis.confidence_level,
                'risk_factors_count': len(analysis.risk_factors)
            }
            insights.append(insight)
        
        # Insights from violations
        for violation in negative_violations:
            insight = {
                'type': 'negative_violation',
                'violation_type': violation.violation_type.value,
                'severity': violation.severity_level.value,
                'violated_patterns': violation.violated_patterns,
                'experiment_id': violation.experiment_id,
                'recommended_action': violation.recommended_action
            }
            insights.append(insight)
        
        # Insights from doctrine evolution
        for evolution in doctrine_evolution:
            insight = {
                'type': 'doctrine_evolution',
                'evolution_type': evolution.get('evolution_type', 'unknown'),
                'affected_patterns': evolution.get('affected_patterns', []),
                'confidence_level': evolution.get('confidence_level', 0.0)
            }
            insights.append(insight)
        
        return insights
    
    async def _publish_doctrine_results(self, results: Dict[str, Any]):
        """Publish doctrine results as CIL strand"""
        try:
            # Create CIL strand with doctrine results
            strand_data = {
                'id': f"cil_doctrine_{int(datetime.now().timestamp())}",
                'kind': 'cil_doctrine_analysis',
                'module': 'alpha',
                'agent_id': 'central_intelligence_layer',
                'team_member': 'learning_feedback_engine',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'session_bucket': 'GLOBAL',
                'regime': 'system',
                'tags': ['agent:central_intelligence:learning_feedback_engine:doctrine_analysis'],
                'module_intelligence': {
                    'analysis_type': 'doctrine_analysis',
                    'negative_analyses': results.get('negative_analyses', 0),
                    'negative_violations': results.get('negative_violations', 0),
                    'doctrine_evolution': results.get('doctrine_evolution', 0),
                    'pattern_updates': results.get('pattern_updates', 0),
                    'doctrine_insights': results.get('doctrine_insights', [])
                },
                'sig_sigma': 1.0,
                'sig_confidence': 0.8,
                'sig_direction': 'neutral',
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc)
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(strand_data)
            
        except Exception as e:
            print(f"Error publishing doctrine results: {e}")
    
    def _get_negative_analysis_prompt(self) -> str:
        """Get negative analysis prompt template"""
        return """
        Analyze the following pattern combinations for potential negative interactions.
        
        Pattern Combinations: {pattern_combinations}
        Experiment Context: {experiment_context}
        Historical Evidence: {historical_evidence}
        
        Provide analysis in JSON format:
        {{
            "negative_type": "one of: contraindicated, failure_mode, anti_pattern, toxic_combination, regime_incompatible, timing_inappropriate",
            "severity_level": "one of: low, medium, high, critical",
            "risk_factors": ["list of risk factors"],
            "mitigation_strategies": ["list of mitigation strategies"],
            "confidence_level": 0.0-1.0,
            "analysis_rationale": "detailed explanation"
        }}
        """
    
    def _get_violation_detection_prompt(self) -> str:
        """Get violation detection prompt template"""
        return """
        Detect violations of negative doctrine in the following experiment design.
        
        Experiment Design: {experiment_design}
        Violated Patterns: {violated_patterns}
        Negative Doctrine: {negative_doctrine}
        
        Provide detection in JSON format:
        {{
            "violation_type": "one of: contraindicated, failure_mode, anti_pattern, toxic_combination, regime_incompatible, timing_inappropriate",
            "severity_level": "one of: low, medium, high, critical",
            "violation_description": "detailed description of the violation",
            "recommended_action": "recommended action to address the violation"
        }}
        """
    
    def _get_doctrine_evolution_prompt(self) -> str:
        """Get doctrine evolution prompt template"""
        return """
        Evolve the negative doctrine based on new evidence and analysis.
        
        Negative Analysis: {negative_analysis}
        Existing Doctrine: {existing_doctrine}
        Violation Evidence: {violation_evidence}
        
        Provide evolution in JSON format:
        {{
            "evolution_type": "one of: addition, modification, retirement",
            "affected_patterns": ["list of affected pattern IDs"],
            "evolution_rationale": "detailed rationale for the evolution",
            "confidence_level": 0.0-1.0
        }}
        """
    
    async def _publish_learning_results(self, learning_results: Dict[str, Any]):
        """Publish learning results as CIL strand"""
        try:
            # Create CIL learning strand
            cil_strand = {
                'id': f"cil_learning_feedback_{int(datetime.now().timestamp())}",
                'kind': 'cil_learning_feedback',
                'module': 'alpha',
                'agent_id': 'central_intelligence_layer',
                'team_member': 'learning_feedback_engine',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'session_bucket': 'GLOBAL',
                'regime': 'system',
                'tags': ['agent:central_intelligence:learning_feedback_engine:learning_complete'],
                'module_intelligence': {
                    'learning_type': 'learning_feedback',
                    'outcomes_processed': len(learning_results.get('captured_outcomes', [])),
                    'lessons_structured': len(learning_results.get('structured_lessons', [])),
                    'braids_updated': len(learning_results.get('updated_braids', [])),
                    'doctrine_updates_generated': len(learning_results.get('doctrine_updates', [])),
                    'improvement_metrics': self._serialize_for_json(learning_results.get('improvement_assessment', {}).get('improvement_metrics', {})),
                    'learning_errors': learning_results.get('learning_errors', [])
                },
                'sig_sigma': 1.0,
                'sig_confidence': 1.0,
                'sig_direction': 'neutral',
                'outcome_score': 1.0,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into database
            self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing learning results: {e}")
    
    def _serialize_for_json(self, obj):
        """Serialize object for JSON compatibility"""
        if isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return self._serialize_for_json(obj.__dict__)
        else:
            return obj


# Example usage and testing
async def main():
    """Example usage of LearningFeedbackEngine"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create learning feedback engine
    learning_engine = LearningFeedbackEngine(supabase_manager, llm_client)
    
    # Mock orchestration results
    orchestration_results = {
        'completed_experiments': [],
        'active_experiments': [],
        'experiment_ideas': [],
        'experiment_designs': [],
        'experiment_assignments': []
    }
    
    # Process learning feedback
    learning_results = await learning_engine.process_learning_feedback(orchestration_results)
    
    print("CIL Learning & Feedback Results:")
    print(f"Outcomes Processed: {len(learning_results.get('captured_outcomes', []))}")
    print(f"Lessons Structured: {len(learning_results.get('structured_lessons', []))}")
    print(f"Braids Updated: {len(learning_results.get('updated_braids', []))}")
    print(f"Doctrine Updates: {len(learning_results.get('doctrine_updates', []))}")
    print(f"Improvement Assessment: {learning_results.get('improvement_assessment', {})}")


if __name__ == "__main__":
    asyncio.run(main())
