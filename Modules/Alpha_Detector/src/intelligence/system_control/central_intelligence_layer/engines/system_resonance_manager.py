"""
System Resonance Manager - 8th Core CIL Engine

Monitors all strand resonance patterns across the system, calculates resonance scores
for new strands using mathematical resonance equations, detects resonance clusters
that trigger strategic actions, and manages resonance enhancement of existing scoring system.

Mathematical Resonance Foundation:
- φ_i = φ_(i-1) × ρ_i (fractal self-similarity)
- θ_i = θ_(i-1) + ℏ × ∑(φ_j × ρ_j) (non-local connections)  
- ρ_i(t+1) = ρ_i(t) + α × ∆φ(t) (recursive feedback)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem
from enum import Enum

logger = logging.getLogger(__name__)


# Resonance Prioritization System Integration
class ExperimentPriority(Enum):
    """Experiment priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResonanceType(Enum):
    """Types of resonance for prioritization"""
    PATTERN_RESONANCE = "pattern_resonance"
    FAMILY_RESONANCE = "family_resonance"
    CROSS_AGENT_RESONANCE = "cross_agent_resonance"
    TEMPORAL_RESONANCE = "temporal_resonance"
    CONTEXTUAL_RESONANCE = "contextual_resonance"


class ExperimentStatus(Enum):
    """Experiment status for prioritization"""
    PENDING = "pending"
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExperimentCandidate:
    """A candidate experiment for prioritization"""
    candidate_id: str
    experiment_type: str
    hypothesis: str
    target_agents: List[str]
    expected_conditions: Dict[str, Any]
    success_metrics: Dict[str, Any]
    time_horizon: str
    resource_requirements: Dict[str, Any]
    family: str
    context: Dict[str, Any]
    created_at: datetime
    priority: ExperimentPriority
    status: ExperimentStatus


@dataclass
class ResonanceScore:
    """Resonance score for an experiment candidate"""
    candidate_id: str
    pattern_resonance: float
    family_resonance: float
    cross_agent_resonance: float
    temporal_resonance: float
    contextual_resonance: float
    overall_resonance: float
    confidence: float
    calculated_at: datetime


@dataclass
class PrioritizedQueue:
    """Prioritized experiment queue"""
    queue_id: str
    queue_name: str
    candidates: List[ExperimentCandidate]
    resonance_scores: Dict[str, ResonanceScore]
    queue_order: List[str]
    family_caps: Dict[str, int]
    total_capacity: int
    created_at: datetime
    updated_at: datetime


@dataclass
class ResonanceCluster:
    """Resonance cluster data structure"""
    cluster_id: str
    motif_ids: List[str]
    resonance_strength: float
    cluster_type: str  # 'strategic_opportunity', 'risk_pattern', 'learning_convergence'
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class ResonanceMetaSignal:
    """Resonance-based meta-signal"""
    signal_id: str
    signal_type: str  # 'resonance_cluster', 'field_alignment', 'strategic_opportunity'
    resonance_strength: float
    affected_agents: List[str]
    recommendation: str
    confidence: float
    created_at: datetime


class SystemResonanceManager:
    """
    System Resonance Manager - 8th Core CIL Engine
    
    Responsibilities:
    - Monitors all strand resonance patterns across the system
    - Calculates resonance scores for new strands using mathematical resonance equations
    - Detects resonance clusters that trigger strategic actions
    - Manages resonance enhancement of existing scoring system
    - Publishes resonance-based meta-signals when clusters align
    """
    
    def __init__(self, db_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.db_manager = db_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(db_manager)
        
        # Resonance parameters
        self.resonance_threshold = 0.6
        self.cluster_min_size = 3
        self.field_window_hours = 24
        self.alpha = 0.1  # Learning rate
        self.gamma = 0.9  # Momentum factor
        self.rho_min = 0.1
        self.rho_max = 2.0
        
        # Resonance Prioritization System Configuration
        self.experiment_candidates: Dict[str, ExperimentCandidate] = {}
        self.resonance_scores: Dict[str, ResonanceScore] = {}
        self.prioritized_queues: Dict[str, PrioritizedQueue] = {}
        self.family_performance: Dict[str, Dict[str, float]] = {}
        
        # Prioritization parameters
        self.max_queue_size = 50
        self.family_cap_percentage = 0.3  # Max 30% of queue from one family
        self.prioritization_resonance_threshold = 0.6
        self.priority_boost_factors = {
            ExperimentPriority.LOW: 1.0,
            ExperimentPriority.MEDIUM: 1.2,
            ExperimentPriority.HIGH: 1.5,
            ExperimentPriority.CRITICAL: 2.0
        }
        
        # Resonance calculation weights
        self.resonance_weights = {
            'pattern_resonance': 0.3,
            'family_resonance': 0.25,
            'cross_agent_resonance': 0.2,
            'temporal_resonance': 0.15,
            'contextual_resonance': 0.1
        }
        
        # Initialize family performance tracking
        self._initialize_family_performance()
        
    async def manage_system_resonance(self, global_view: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main resonance management function
        
        Args:
            global_view: Global synthesis results from other CIL engines
            
        Returns:
            Dict containing resonance management results
        """
        try:
            results = {}
            
            # 1. Monitor resonance patterns
            resonance_patterns = await self._monitor_resonance_patterns()
            results["resonance_patterns"] = resonance_patterns
            
            # 2. Calculate resonance scores for new strands
            resonance_scores = await self._calculate_resonance_scores()
            results["resonance_scores"] = resonance_scores
            
            # 3. Detect resonance clusters
            resonance_clusters = await self._detect_resonance_clusters()
            results["resonance_clusters"] = resonance_clusters
            
            # 4. Enhance existing scoring system
            enhanced_scores = await self._enhance_scoring_system()
            results["enhanced_scores"] = enhanced_scores
            
            # 5. Generate resonance-based meta-signals
            meta_signals = await self._generate_resonance_meta_signals(resonance_clusters)
            results["meta_signals"] = meta_signals
            
            # 6. Publish results
            await self._publish_resonance_results(results)
            
            return results
            
        except Exception as e:
            print(f"Error in system resonance management: {e}")
            return {"error": str(e)}
    
    async def _monitor_resonance_patterns(self) -> Dict[str, Any]:
        """Monitor all strand resonance patterns across the system"""
        try:
            # Get recent strands with resonance data
            query = """
            SELECT 
                id, agent_id, detection_type, sig_confidence, sig_sigma,
                resonance_score, phi, rho, telemetry,
                created_at
            FROM AD_strands 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            AND (resonance_score IS NOT NULL OR phi IS NOT NULL OR rho IS NOT NULL)
            ORDER BY created_at DESC
            LIMIT 100
            """
            
            result = await self.db_manager.execute_query(query)
            strands = result.get('data', [])
            
            # Analyze resonance patterns
            patterns = {
                'total_strands': len(strands),
                'high_resonance_strands': len([s for s in strands if s.get('resonance_score', 0) > self.resonance_threshold]),
                'resonance_distribution': self._analyze_resonance_distribution(strands),
                'agent_resonance_patterns': self._analyze_agent_resonance_patterns(strands),
                'temporal_resonance_patterns': self._analyze_temporal_resonance_patterns(strands)
            }
            
            return patterns
            
        except Exception as e:
            print(f"Error monitoring resonance patterns: {e}")
            return {}
    
    async def _calculate_resonance_scores(self) -> Dict[str, Any]:
        """Calculate resonance scores for new strands using mathematical resonance equations"""
        try:
            # Get strands without resonance scores
            query = """
            SELECT 
                id, agent_id, detection_type, sig_confidence, sig_sigma,
                outcome_score, created_at
            FROM AD_strands 
            WHERE resonance_score IS NULL
            AND created_at >= NOW() - INTERVAL '1 hour'
            ORDER BY created_at DESC
            LIMIT 50
            """
            
            result = await self.db_manager.execute_query(query)
            new_strands = result.get('data', [])
            
            calculated_scores = []
            
            for strand in new_strands:
                # Calculate resonance score using mathematical equations
                resonance_score = await self._calculate_strand_resonance(strand)
                
                # Update strand with resonance score
                update_query = """
                UPDATE AD_strands 
                SET resonance_score = %s, phi = %s, rho = %s
                WHERE id = %s
                """
                
                await self.db_manager.execute_query(update_query, [
                    resonance_score['resonance_score'],
                    resonance_score['phi'],
                    resonance_score['rho'],
                    strand['id']
                ])
                
                calculated_scores.append({
                    'strand_id': strand['id'],
                    'resonance_score': resonance_score['resonance_score'],
                    'phi': resonance_score['phi'],
                    'rho': resonance_score['rho']
                })
            
            return {
                'calculated_count': len(calculated_scores),
                'scores': calculated_scores
            }
            
        except Exception as e:
            print(f"Error calculating resonance scores: {e}")
            return {}
    
    async def _detect_resonance_clusters(self) -> List[ResonanceCluster]:
        """Detect resonance clusters that trigger strategic actions"""
        try:
            # Get high-resonance strands
            query = """
            SELECT 
                id, agent_id, detection_type, sig_confidence, sig_sigma,
                resonance_score, phi, rho, created_at
            FROM AD_strands 
            WHERE resonance_score >= %s
            AND created_at >= NOW() - INTERVAL '6 hours'
            ORDER BY resonance_score DESC
            """
            
            result = await self.db_manager.execute_query(query, [self.resonance_threshold])
            high_resonance_strands = result.get('data', [])
            
            clusters = []
            
            if len(high_resonance_strands) >= self.cluster_min_size:
                # Group by agent and detection type
                agent_groups = {}
                for strand in high_resonance_strands:
                    key = f"{strand['agent_id']}_{strand['detection_type']}"
                    if key not in agent_groups:
                        agent_groups[key] = []
                    agent_groups[key].append(strand)
                
                # Create clusters from groups
                for group_key, group_strands in agent_groups.items():
                    if len(group_strands) >= self.cluster_min_size:
                        cluster = ResonanceCluster(
                            cluster_id=f"cluster_{group_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            motif_ids=[s['id'] for s in group_strands],
                            resonance_strength=sum(s['resonance_score'] for s in group_strands) / len(group_strands),
                            cluster_type=self._determine_cluster_type(group_strands),
                            created_at=datetime.now(timezone.utc),
                            metadata={
                                'agent_id': group_strands[0]['agent_id'],
                                'detection_type': group_strands[0]['detection_type'],
                                'strand_count': len(group_strands),
                                'avg_confidence': sum(s['sig_confidence'] for s in group_strands) / len(group_strands)
                            }
                        )
                        clusters.append(cluster)
            
            return clusters
            
        except Exception as e:
            print(f"Error detecting resonance clusters: {e}")
            return []
    
    async def _enhance_scoring_system(self) -> Dict[str, Any]:
        """Manage resonance enhancement of existing scoring system"""
        try:
            # Get current scoring system performance
            query = """
            SELECT 
                AVG(sig_sigma) as avg_sigma,
                AVG(sig_confidence) as avg_confidence,
                AVG(outcome_score) as avg_outcome,
                AVG(resonance_score) as avg_resonance,
                COUNT(*) as total_strands
            FROM AD_strands 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            AND sig_sigma IS NOT NULL
            AND sig_confidence IS NOT NULL
            AND outcome_score IS NOT NULL
            AND resonance_score IS NOT NULL
            """
            
            result = await self.db_manager.execute_query(query)
            scoring_data = result.get('data', [{}])[0]
            
            # Calculate enhanced scores
            enhanced_scores = {
                'current_avg_sigma': scoring_data.get('avg_sigma', 0),
                'current_avg_confidence': scoring_data.get('avg_confidence', 0),
                'current_avg_outcome': scoring_data.get('avg_outcome', 0),
                'current_avg_resonance': scoring_data.get('avg_resonance', 0),
                'total_strands': scoring_data.get('total_strands', 0),
                'enhancement_recommendations': self._generate_enhancement_recommendations(scoring_data)
            }
            
            return enhanced_scores
            
        except Exception as e:
            print(f"Error enhancing scoring system: {e}")
            return {}
    
    async def _generate_resonance_meta_signals(self, clusters: List[ResonanceCluster]) -> List[ResonanceMetaSignal]:
        """Generate resonance-based meta-signals when clusters align"""
        try:
            meta_signals = []
            
            for cluster in clusters:
                if cluster.resonance_strength > 0.8:  # High resonance threshold
                    # Generate meta-signal based on cluster type
                    signal = ResonanceMetaSignal(
                        signal_id=f"resonance_signal_{cluster.cluster_id}",
                        signal_type=cluster.cluster_type,
                        resonance_strength=cluster.resonance_strength,
                        affected_agents=[cluster.metadata['agent_id']],
                        recommendation=self._generate_cluster_recommendation(cluster),
                        confidence=min(cluster.resonance_strength, 0.95),
                        created_at=datetime.now(timezone.utc)
                    )
                    meta_signals.append(signal)
            
            return meta_signals
            
        except Exception as e:
            print(f"Error generating resonance meta-signals: {e}")
            return []
    
    async def _calculate_strand_resonance(self, strand: Dict[str, Any]) -> Dict[str, float]:
        """Calculate resonance score for a single strand using mathematical equations"""
        try:
            # Get similar strands for resonance calculation
            similar_strands = await self._find_similar_strands(strand)
            
            # Calculate φ (fractal self-similarity)
            phi = self._calculate_phi(strand, similar_strands)
            
            # Calculate ρ (recursive depth/feedback factor)
            rho = self._calculate_rho(strand, similar_strands)
            
            # Calculate θ (global context field)
            theta = await self._calculate_theta(strand)
            
            # Calculate final resonance score
            resonance_score = (phi * 0.4) + (rho * 0.3) + (theta * 0.3)
            
            return {
                'resonance_score': min(max(resonance_score, 0.0), 1.0),
                'phi': phi,
                'rho': rho,
                'theta': theta
            }
            
        except Exception as e:
            print(f"Error calculating strand resonance: {e}")
            return {
                'resonance_score': 0.5,
                'phi': 0.5,
                'rho': 0.5,
                'theta': 0.5
            }
    
    async def _find_similar_strands(self, strand: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find similar strands for resonance calculation"""
        try:
            # Simple similarity based on agent_id and detection_type
            query = """
            SELECT 
                id, agent_id, detection_type, sig_confidence, sig_sigma,
                resonance_score, phi, rho, created_at
            FROM AD_strands 
            WHERE agent_id = %s 
            AND detection_type = %s
            AND id != %s
            AND created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            LIMIT 10
            """
            
            result = await self.db_manager.execute_query(query, [
                strand['agent_id'],
                strand['detection_type'],
                strand['id']
            ])
            
            return result.get('data', [])
            
        except Exception as e:
            print(f"Error finding similar strands: {e}")
            return []
    
    def _calculate_phi(self, strand: Dict[str, Any], similar_strands: List[Dict[str, Any]]) -> float:
        """Calculate φ (fractal self-similarity)"""
        if not similar_strands:
            return 0.5
        
        # Calculate similarity based on confidence and sigma
        similarities = []
        for similar in similar_strands:
            conf_sim = 1.0 - abs(strand['sig_confidence'] - similar['sig_confidence'])
            sigma_sim = 1.0 - abs(strand['sig_sigma'] - similar['sig_sigma'])
            similarity = (conf_sim + sigma_sim) / 2.0
            similarities.append(similarity)
        
        # φ_i = φ_(i-1) × ρ_i (fractal self-similarity)
        avg_similarity = sum(similarities) / len(similarities)
        return min(max(avg_similarity, 0.0), 1.0)
    
    def _calculate_rho(self, strand: Dict[str, Any], similar_strands: List[Dict[str, Any]]) -> float:
        """Calculate ρ (recursive depth/feedback factor)"""
        if not similar_strands:
            return 0.5
        
        # Calculate feedback based on recent performance
        recent_rhos = [s.get('rho', 0.5) for s in similar_strands if s.get('rho') is not None]
        if recent_rhos:
            avg_rho = sum(recent_rhos) / len(recent_rhos)
            # ρ_i(t+1) = ρ_i(t) + α × ∆φ(t) (recursive feedback)
            delta_phi = abs(strand['sig_confidence'] - 0.5)  # Simple delta calculation
            new_rho = avg_rho + self.alpha * delta_phi
            return min(max(new_rho, self.rho_min), self.rho_max)
        
        return 0.5
    
    async def _calculate_theta(self, strand: Dict[str, Any]) -> float:
        """Calculate θ (global context field)"""
        try:
            # Get global context from recent strands
            query = """
            SELECT 
                AVG(sig_confidence) as global_confidence,
                AVG(sig_sigma) as global_sigma,
                COUNT(*) as global_count
            FROM AD_strands 
            WHERE created_at >= NOW() - INTERVAL '6 hours'
            """
            
            result = await self.db_manager.execute_query(query)
            global_data = result.get('data', [{}])[0]
            
            if global_data.get('global_count', 0) > 0:
                # θ_i = θ_(i-1) + ℏ × ∑(φ_j × ρ_j) (non-local connections)
                global_confidence = global_data.get('global_confidence', 0.5)
                global_sigma = global_data.get('global_sigma', 0.5)
                
                # Simple theta calculation based on global context
                theta = (global_confidence + global_sigma) / 2.0
                return min(max(theta, 0.0), 1.0)
            
            return 0.5
            
        except Exception as e:
            print(f"Error calculating theta: {e}")
            return 0.5
    
    def _analyze_resonance_distribution(self, strands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze resonance score distribution"""
        if not strands:
            return {}
        
        resonance_scores = [s.get('resonance_score', 0) for s in strands if s.get('resonance_score') is not None]
        
        if not resonance_scores:
            return {}
        
        return {
            'min': min(resonance_scores),
            'max': max(resonance_scores),
            'avg': sum(resonance_scores) / len(resonance_scores),
            'count': len(resonance_scores)
        }
    
    def _analyze_agent_resonance_patterns(self, strands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze resonance patterns by agent"""
        agent_patterns = {}
        
        for strand in strands:
            agent_id = strand.get('agent_id', 'unknown')
            if agent_id not in agent_patterns:
                agent_patterns[agent_id] = {
                    'count': 0,
                    'avg_resonance': 0,
                    'high_resonance_count': 0
                }
            
            agent_patterns[agent_id]['count'] += 1
            resonance_score = strand.get('resonance_score', 0)
            agent_patterns[agent_id]['avg_resonance'] += resonance_score
            
            if resonance_score > self.resonance_threshold:
                agent_patterns[agent_id]['high_resonance_count'] += 1
        
        # Calculate averages
        for agent_id in agent_patterns:
            if agent_patterns[agent_id]['count'] > 0:
                agent_patterns[agent_id]['avg_resonance'] /= agent_patterns[agent_id]['count']
        
        return agent_patterns
    
    def _analyze_temporal_resonance_patterns(self, strands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal resonance patterns"""
        if not strands:
            return {}
        
        # Group by hour
        hourly_patterns = {}
        for strand in strands:
            created_at = strand.get('created_at')
            if created_at:
                hour = created_at.strftime('%Y-%m-%d %H:00')
                if hour not in hourly_patterns:
                    hourly_patterns[hour] = {
                        'count': 0,
                        'avg_resonance': 0,
                        'high_resonance_count': 0
                    }
                
                hourly_patterns[hour]['count'] += 1
                resonance_score = strand.get('resonance_score', 0)
                hourly_patterns[hour]['avg_resonance'] += resonance_score
                
                if resonance_score > self.resonance_threshold:
                    hourly_patterns[hour]['high_resonance_count'] += 1
        
        # Calculate averages
        for hour in hourly_patterns:
            if hourly_patterns[hour]['count'] > 0:
                hourly_patterns[hour]['avg_resonance'] /= hourly_patterns[hour]['count']
        
        return hourly_patterns
    
    def _determine_cluster_type(self, strands: List[Dict[str, Any]]) -> str:
        """Determine the type of resonance cluster"""
        if not strands:
            return 'unknown'
        
        # Analyze cluster characteristics
        avg_confidence = sum(s['sig_confidence'] for s in strands) / len(strands)
        avg_sigma = sum(s['sig_sigma'] for s in strands) / len(strands)
        
        if avg_confidence > 0.8 and avg_sigma > 0.7:
            return 'strategic_opportunity'
        elif avg_confidence < 0.3 or avg_sigma < 0.3:
            return 'risk_pattern'
        else:
            return 'learning_convergence'
    
    def _generate_enhancement_recommendations(self, scoring_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations for scoring system enhancement"""
        recommendations = []
        
        avg_resonance = scoring_data.get('avg_resonance', 0)
        total_strands = scoring_data.get('total_strands', 0)
        
        if avg_resonance < 0.3:
            recommendations.append("Low average resonance - consider adjusting resonance calculation parameters")
        
        if total_strands < 10:
            recommendations.append("Limited data for resonance analysis - wait for more strands")
        
        if avg_resonance > 0.8:
            recommendations.append("High resonance detected - consider implementing resonance-based prioritization")
        
        return recommendations
    
    def _generate_cluster_recommendation(self, cluster: ResonanceCluster) -> str:
        """Generate recommendation based on cluster type"""
        if cluster.cluster_type == 'strategic_opportunity':
            return f"High-resonance strategic opportunity detected in {cluster.metadata['agent_id']} - consider coordinated action"
        elif cluster.cluster_type == 'risk_pattern':
            return f"Risk pattern detected in {cluster.metadata['agent_id']} - implement risk mitigation strategies"
        else:
            return f"Learning convergence detected in {cluster.metadata['agent_id']} - capture lessons and update doctrine"
    
    def _initialize_family_performance(self):
        """Initialize family performance tracking"""
        families = [
            'divergence', 'volume', 'correlation', 'session', 'cross_asset',
            'pattern', 'indicator', 'microstructure', 'regime', 'volatility'
        ]
        
        for family in families:
            self.family_performance[family] = {
                'success_rate': 0.5,
                'completion_rate': 0.5,
                'novelty_score': 0.5,
                'persistence_score': 0.5,
                'last_updated': datetime.now(timezone.utc)
            }
    
    # Resonance Prioritization System Methods
    async def process_resonance_prioritization(self, experiment_candidates: List[Dict[str, Any]],
                                             system_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process resonance prioritization for experiment candidates to create
        prioritized queues based on resonance scores and system constraints.
        """
        logger.info("Processing resonance prioritization for experiment candidates.")
        
        try:
            # Add candidates to system
            added_candidates = await self._add_experiment_candidates(experiment_candidates)
            
            # Calculate resonance scores
            resonance_calculations = await self._calculate_experiment_resonance_scores(added_candidates, system_context)
            
            # Create prioritized queue
            queue_creation = await self._create_prioritized_experiment_queue(resonance_calculations, system_context)
            
            # Update family performance
            performance_updates = await self._update_family_performance_metrics()
            
            # Compile results
            results = {
                'added_candidates': added_candidates,
                'resonance_calculations': resonance_calculations,
                'queue_creation': queue_creation,
                'performance_updates': performance_updates,
                'prioritization_timestamp': datetime.now(timezone.utc),
                'prioritization_errors': []
            }
            
            # Publish results
            await self._publish_prioritization_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing resonance prioritization: {e}")
            return {
                'added_candidates': [],
                'resonance_calculations': [],
                'queue_creation': {},
                'performance_updates': [],
                'prioritization_timestamp': datetime.now(timezone.utc),
                'prioritization_errors': [str(e)]
            }
    
    async def _add_experiment_candidates(self, candidates: List[Dict[str, Any]]) -> List[str]:
        """Add experiment candidates to the system"""
        added_candidates = []
        
        for candidate_data in candidates:
            # Create experiment candidate
            candidate = ExperimentCandidate(
                candidate_id=candidate_data.get('candidate_id', f"CANDIDATE_{int(datetime.now().timestamp())}"),
                experiment_type=candidate_data.get('experiment_type', 'unknown'),
                hypothesis=candidate_data.get('hypothesis', ''),
                target_agents=candidate_data.get('target_agents', []),
                expected_conditions=candidate_data.get('expected_conditions', {}),
                success_metrics=candidate_data.get('success_metrics', {}),
                time_horizon=candidate_data.get('time_horizon', 'medium'),
                resource_requirements=candidate_data.get('resource_requirements', {}),
                family=candidate_data.get('family', 'unknown'),
                context=candidate_data.get('context', {}),
                created_at=datetime.now(timezone.utc),
                priority=ExperimentPriority(candidate_data.get('priority', 'medium')),
                status=ExperimentStatus.PENDING
            )
            
            # Add to system
            self.experiment_candidates[candidate.candidate_id] = candidate
            added_candidates.append(candidate.candidate_id)
        
        return added_candidates
    
    async def _calculate_experiment_resonance_scores(self, candidate_ids: List[str],
                                                   system_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate resonance scores for experiment candidates"""
        resonance_calculations = []
        
        for candidate_id in candidate_ids:
            candidate = self.experiment_candidates[candidate_id]
            
            # Calculate individual resonance components
            pattern_resonance = await self._calculate_pattern_resonance(candidate, system_context)
            family_resonance = await self._calculate_family_resonance(candidate, system_context)
            cross_agent_resonance = await self._calculate_cross_agent_resonance(candidate, system_context)
            temporal_resonance = await self._calculate_temporal_resonance(candidate, system_context)
            contextual_resonance = await self._calculate_contextual_resonance(candidate, system_context)
            
            # Calculate overall resonance score
            overall_resonance = (
                pattern_resonance * self.resonance_weights['pattern_resonance'] +
                family_resonance * self.resonance_weights['family_resonance'] +
                cross_agent_resonance * self.resonance_weights['cross_agent_resonance'] +
                temporal_resonance * self.resonance_weights['temporal_resonance'] +
                contextual_resonance * self.resonance_weights['contextual_resonance']
            )
            
            # Apply priority boost
            priority_boost = self.priority_boost_factors.get(candidate.priority, 1.0)
            overall_resonance = min(overall_resonance * priority_boost, 1.0)
            
            # Create resonance score
            resonance_score = ResonanceScore(
                candidate_id=candidate_id,
                pattern_resonance=pattern_resonance,
                family_resonance=family_resonance,
                cross_agent_resonance=cross_agent_resonance,
                temporal_resonance=temporal_resonance,
                contextual_resonance=contextual_resonance,
                overall_resonance=overall_resonance,
                confidence=0.8,  # Default confidence
                calculated_at=datetime.now(timezone.utc)
            )
            
            # Store resonance score
            self.resonance_scores[candidate_id] = resonance_score
            
            resonance_calculations.append({
                'candidate_id': candidate_id,
                'resonance_score': resonance_score,
                'resonance_insights': [
                    f"Pattern resonance: {pattern_resonance:.2f}",
                    f"Family resonance: {family_resonance:.2f}",
                    f"Cross-agent resonance: {cross_agent_resonance:.2f}",
                    f"Temporal resonance: {temporal_resonance:.2f}",
                    f"Contextual resonance: {contextual_resonance:.2f}"
                ],
                'prioritization_recommendations': [
                    f"Overall resonance: {overall_resonance:.2f}",
                    f"Priority boost applied: {priority_boost:.1f}x"
                ]
            })
        
        return resonance_calculations
    
    async def _calculate_pattern_resonance(self, candidate: ExperimentCandidate, system_context: Dict[str, Any]) -> float:
        """Calculate pattern resonance for a candidate"""
        # Simple pattern resonance calculation based on family performance
        family_perf = self.family_performance.get(candidate.family, {})
        success_rate = family_perf.get('success_rate', 0.5)
        novelty_score = family_perf.get('novelty_score', 0.5)
        
        # Pattern resonance combines success rate and novelty
        pattern_resonance = (success_rate * 0.7) + (novelty_score * 0.3)
        return min(max(pattern_resonance, 0.0), 1.0)
    
    async def _calculate_family_resonance(self, candidate: ExperimentCandidate, system_context: Dict[str, Any]) -> float:
        """Calculate family resonance for a candidate"""
        family_perf = self.family_performance.get(candidate.family, {})
        completion_rate = family_perf.get('completion_rate', 0.5)
        persistence_score = family_perf.get('persistence_score', 0.5)
        
        # Family resonance based on completion and persistence
        family_resonance = (completion_rate * 0.6) + (persistence_score * 0.4)
        return min(max(family_resonance, 0.0), 1.0)
    
    async def _calculate_cross_agent_resonance(self, candidate: ExperimentCandidate, system_context: Dict[str, Any]) -> float:
        """Calculate cross-agent resonance for a candidate"""
        # Cross-agent resonance based on number of target agents
        agent_count = len(candidate.target_agents)
        if agent_count == 0:
            return 0.0
        elif agent_count == 1:
            return 0.3
        elif agent_count == 2:
            return 0.7
        else:
            return 1.0
    
    async def _calculate_temporal_resonance(self, candidate: ExperimentCandidate, system_context: Dict[str, Any]) -> float:
        """Calculate temporal resonance for a candidate"""
        # Temporal resonance based on time horizon
        time_horizon = candidate.time_horizon.lower()
        if time_horizon == 'short':
            return 0.8
        elif time_horizon == 'medium':
            return 0.6
        elif time_horizon == 'long':
            return 0.4
        else:
            return 0.5
    
    async def _calculate_contextual_resonance(self, candidate: ExperimentCandidate, system_context: Dict[str, Any]) -> float:
        """Calculate contextual resonance for a candidate"""
        # Contextual resonance based on expected conditions alignment
        expected_conditions = candidate.expected_conditions
        if not expected_conditions:
            return 0.5
        
        # Simple contextual scoring based on regime and timeframe
        regime_score = 0.7 if expected_conditions.get('regime') else 0.5
        timeframe_score = 0.8 if expected_conditions.get('timeframe') else 0.5
        
        contextual_resonance = (regime_score + timeframe_score) / 2.0
        return min(max(contextual_resonance, 0.0), 1.0)
    
    async def _create_prioritized_experiment_queue(self, resonance_calculations: List[Dict[str, Any]],
                                                 system_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create prioritized experiment queue based on resonance scores"""
        # Sort candidates by overall resonance score
        sorted_candidates = sorted(
            resonance_calculations,
            key=lambda x: x['resonance_score'].overall_resonance,
            reverse=True
        )
        
        # Apply family caps
        family_counts = {}
        queue_order = []
        
        for calc in sorted_candidates:
            candidate = self.experiment_candidates[calc['candidate_id']]
            family = candidate.family
            
            # Check family cap
            family_cap = int(self.max_queue_size * self.family_cap_percentage)
            if family_counts.get(family, 0) < family_cap:
                queue_order.append(calc['candidate_id'])
                family_counts[family] = family_counts.get(family, 0) + 1
                
                # Stop if queue is full
                if len(queue_order) >= self.max_queue_size:
                    break
        
        # Create prioritized queue
        queue_id = f"QUEUE_{int(datetime.now().timestamp())}"
        queue = PrioritizedQueue(
            queue_id=queue_id,
            queue_name="Resonance-Prioritized Experiment Queue",
            candidates=[self.experiment_candidates[cid] for cid in queue_order],
            resonance_scores={cid: self.resonance_scores[cid] for cid in queue_order if cid in self.resonance_scores},
            queue_order=queue_order,
            family_caps=family_counts,
            total_capacity=self.max_queue_size,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Store prioritized queue
        self.prioritized_queues[queue_id] = queue
        
        return {
            'queue_id': queue_id,
            'queue_name': queue.queue_name,
            'queue_order': queue_order,
            'family_distribution': family_counts,
            'resonance_distribution': self._calculate_resonance_distribution(queue_order),
            'resource_allocation': self._calculate_resource_allocation(queue_order),
            'prioritization_insights': [
                f"Created queue with {len(queue_order)} candidates",
                f"Family diversity maintained with caps",
                f"Average resonance: {sum(self.resonance_scores[cid].overall_resonance for cid in queue_order) / len(queue_order):.2f}"
            ],
            'constraint_violations': [],
            'optimization_suggestions': [
                "Monitor family performance for cap adjustments",
                "Consider temporal resonance optimization"
            ],
            'created_at': queue.created_at.isoformat()
        }
    
    def _calculate_resonance_distribution(self, queue_order: List[str]) -> Dict[str, int]:
        """Calculate resonance score distribution in queue"""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for candidate_id in queue_order:
            if candidate_id in self.resonance_scores:
                score = self.resonance_scores[candidate_id].overall_resonance
                if score >= 0.7:
                    distribution['high'] += 1
                elif score >= 0.4:
                    distribution['medium'] += 1
                else:
                    distribution['low'] += 1
        
        return distribution
    
    def _calculate_resource_allocation(self, queue_order: List[str]) -> Dict[str, int]:
        """Calculate resource allocation across agents"""
        allocation = {}
        
        for candidate_id in queue_order:
            if candidate_id in self.experiment_candidates:
                candidate = self.experiment_candidates[candidate_id]
                for agent in candidate.target_agents:
                    allocation[agent] = allocation.get(agent, 0) + 1
        
        return allocation
    
    async def _update_family_performance_metrics(self) -> List[Dict[str, Any]]:
        """Update family performance metrics"""
        performance_updates = []
        
        for family, performance in self.family_performance.items():
            # Simulate performance update (in real implementation, would query database)
            old_performance = performance.copy()
            
            # Update performance metrics
            performance['success_rate'] = min(1.0, performance['success_rate'] + 0.01)
            performance['completion_rate'] = min(1.0, performance['completion_rate'] + 0.005)
            performance['novelty_score'] = max(0.0, performance['novelty_score'] - 0.002)
            performance['persistence_score'] = min(1.0, performance['persistence_score'] + 0.003)
            performance['last_updated'] = datetime.now(timezone.utc)
            
            performance_updates.append({
                'family': family,
                'old_performance': old_performance,
                'new_performance': performance,
                'updated_at': performance['last_updated'].isoformat()
            })
        
        return performance_updates
    
    async def _publish_prioritization_results(self, results: Dict[str, Any]):
        """Publish prioritization results as CIL strand"""
        try:
            # Create CIL prioritization strand
            cil_strand = {
                'id': f"cil_resonance_prioritization_{int(datetime.now().timestamp())}",
                'kind': 'cil_resonance_prioritization',
                'module': 'alpha',
                'symbol': 'ALL',
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': ['agent:central_intelligence:system_resonance_manager:prioritization_processed'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.9,
                'sig_confidence': 0.95,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'team_member': 'system_resonance_manager',
                'strategic_meta_type': 'resonance_prioritization',
                'resonance_score': 0.9
            }
            
            # Insert into database
            await self.db_manager.insert_strand(cil_strand)
            
        except Exception as e:
            logger.error(f"Error publishing prioritization results: {e}")

    async def _publish_resonance_results(self, results: Dict[str, Any]) -> None:
        """Publish resonance management results to database"""
        try:
            # Create CIL strand with resonance results
            strand_data = {
                'agent_id': 'central_intelligence_layer',
                'detection_type': 'system_resonance_management',
                'sig_confidence': 0.8,
                'sig_sigma': 0.7,
                'outcome_score': 0.0,
                'resonance_score': 0.8,
                'strategic_meta_type': 'resonance_analysis',
                'module_intelligence': {
                    'resonance_type': 'system_resonance_management',
                    'patterns_monitored': results.get('resonance_patterns', {}).get('total_strands', 0),
                    'scores_calculated': results.get('resonance_scores', {}).get('calculated_count', 0),
                    'clusters_detected': len(results.get('resonance_clusters', [])),
                    'meta_signals_generated': len(results.get('meta_signals', [])),
                    'enhancement_recommendations': results.get('enhanced_scores', {}).get('enhancement_recommendations', []),
                    'resonance_analysis': results
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into database
            await self.db_manager.insert_data('AD_strands', strand_data)
            
        except Exception as e:
            print(f"Error publishing resonance results: {e}")
