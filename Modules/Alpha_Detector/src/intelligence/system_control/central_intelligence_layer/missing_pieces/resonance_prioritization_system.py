"""
CIL Resonance Prioritization System - Additional Missing Piece 1
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


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


class ResonancePrioritizationSystem:
    """CIL Resonance Prioritization System - Experiment queue prioritization by resonance score"""
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Configuration
        self.max_queue_size = 50
        self.family_cap_percentage = 0.3  # Max 30% of queue from one family
        self.resonance_threshold = 0.6
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
        
        # System state
        self.experiment_candidates: Dict[str, ExperimentCandidate] = {}
        self.resonance_scores: Dict[str, ResonanceScore] = {}
        self.prioritized_queues: Dict[str, PrioritizedQueue] = {}
        self.family_performance: Dict[str, Dict[str, float]] = {}
        
        # LLM prompt templates
        self.resonance_analysis_prompt = self._load_resonance_analysis_prompt()
        self.prioritization_prompt = self._load_prioritization_prompt()
        
        # Initialize family performance tracking
        self._initialize_family_performance()
    
    def _load_resonance_analysis_prompt(self) -> str:
        """Load resonance analysis prompt template"""
        return """
        Analyze the resonance potential of this experiment candidate.
        
        Experiment Details:
        - Type: {experiment_type}
        - Hypothesis: {hypothesis}
        - Target Agents: {target_agents}
        - Expected Conditions: {expected_conditions}
        - Success Metrics: {success_metrics}
        - Time Horizon: {time_horizon}
        - Family: {family}
        - Context: {context}
        
        Historical Context:
        - Family Performance: {family_performance}
        - Recent Patterns: {recent_patterns}
        - Cross-Agent Activity: {cross_agent_activity}
        - Temporal Trends: {temporal_trends}
        
        Analyze resonance potential across:
        1. Pattern resonance (alignment with known successful patterns)
        2. Family resonance (family performance and saturation)
        3. Cross-agent resonance (multi-agent coordination potential)
        4. Temporal resonance (timing and market conditions)
        5. Contextual resonance (regime and session alignment)
        
        Respond in JSON format:
        {{
            "resonance_analysis": {{
                "pattern_resonance": 0.0-1.0,
                "family_resonance": 0.0-1.0,
                "cross_agent_resonance": 0.0-1.0,
                "temporal_resonance": 0.0-1.0,
                "contextual_resonance": 0.0-1.0,
                "overall_resonance": 0.0-1.0,
                "confidence": 0.0-1.0
            }},
            "resonance_insights": ["list of insights"],
            "prioritization_recommendations": ["list of recommendations"],
            "uncertainty_flags": ["any uncertainties"]
        }}
        """
    
    def _load_prioritization_prompt(self) -> str:
        """Load prioritization prompt template"""
        return """
        Prioritize experiment candidates based on resonance scores and system constraints.
        
        Candidates with Resonance Scores:
        {candidates_with_scores}
        
        System Constraints:
        - Max Queue Size: {max_queue_size}
        - Family Cap Percentage: {family_cap_percentage}
        - Current Queue: {current_queue}
        - Family Caps: {family_caps}
        
        Prioritization Criteria:
        1. Overall resonance score (primary)
        2. Family diversity and caps
        3. Resource availability
        4. Temporal urgency
        5. Cross-agent coordination potential
        
        Create prioritized queue order considering:
        - Resonance score ranking
        - Family cap enforcement
        - Resource balance
        - Strategic importance
        
        Respond in JSON format:
        {{
            "prioritized_queue": {{
                "queue_order": ["candidate_id_1", "candidate_id_2", ...],
                "family_distribution": {{"family": "count"}},
                "resonance_distribution": {{"score_range": "count"}},
                "resource_allocation": {{"agent": "experiment_count"}}
            }},
            "prioritization_insights": ["list of insights"],
            "constraint_violations": ["any violations"],
            "optimization_suggestions": ["list of suggestions"]
        }}
        """
    
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
    
    async def process_resonance_prioritization(self, experiment_candidates: List[Dict[str, Any]],
                                             system_context: Dict[str, Any]) -> Dict[str, Any]:
        """Process resonance prioritization for experiment candidates"""
        try:
            # Add candidates to system
            added_candidates = await self._add_experiment_candidates(experiment_candidates)
            
            # Calculate resonance scores
            resonance_calculations = await self._calculate_resonance_scores(added_candidates, system_context)
            
            # Create prioritized queue
            queue_creation = await self._create_prioritized_queue(resonance_calculations, system_context)
            
            # Update family performance
            performance_updates = await self._update_family_performance()
            
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
            print(f"Error processing resonance prioritization: {e}")
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
    
    async def _calculate_resonance_scores(self, candidate_ids: List[str],
                                        system_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate resonance scores for candidates"""
        resonance_calculations = []
        
        for candidate_id in candidate_ids:
            candidate = self.experiment_candidates[candidate_id]
            
            # Prepare analysis data
            analysis_data = {
                'experiment_type': candidate.experiment_type,
                'hypothesis': candidate.hypothesis,
                'target_agents': candidate.target_agents,
                'expected_conditions': candidate.expected_conditions,
                'success_metrics': candidate.success_metrics,
                'time_horizon': candidate.time_horizon,
                'family': candidate.family,
                'context': candidate.context,
                'family_performance': self.family_performance.get(candidate.family, {}),
                'recent_patterns': system_context.get('recent_patterns', []),
                'cross_agent_activity': system_context.get('cross_agent_activity', {}),
                'temporal_trends': system_context.get('temporal_trends', {})
            }
            
            # Generate resonance analysis using LLM
            analysis = await self._generate_resonance_analysis(analysis_data)
            
            if analysis:
                # Create resonance score
                resonance_score = ResonanceScore(
                    candidate_id=candidate_id,
                    pattern_resonance=analysis['resonance_analysis']['pattern_resonance'],
                    family_resonance=analysis['resonance_analysis']['family_resonance'],
                    cross_agent_resonance=analysis['resonance_analysis']['cross_agent_resonance'],
                    temporal_resonance=analysis['resonance_analysis']['temporal_resonance'],
                    contextual_resonance=analysis['resonance_analysis']['contextual_resonance'],
                    overall_resonance=analysis['resonance_analysis']['overall_resonance'],
                    confidence=analysis['resonance_analysis']['confidence'],
                    calculated_at=datetime.now(timezone.utc)
                )
                
                # Store resonance score
                self.resonance_scores[candidate_id] = resonance_score
                
                resonance_calculations.append({
                    'candidate_id': candidate_id,
                    'resonance_score': resonance_score,
                    'resonance_insights': analysis.get('resonance_insights', []),
                    'prioritization_recommendations': analysis.get('prioritization_recommendations', []),
                    'uncertainty_flags': analysis.get('uncertainty_flags', [])
                })
        
        return resonance_calculations
    
    async def _generate_resonance_analysis(self, analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate resonance analysis using LLM"""
        try:
            # Generate analysis using LLM
            analysis = await self._generate_llm_analysis(
                self.resonance_analysis_prompt, analysis_data
            )
            
            return analysis
            
        except Exception as e:
            print(f"Error generating resonance analysis: {e}")
            return None
    
    async def _create_prioritized_queue(self, resonance_calculations: List[Dict[str, Any]],
                                      system_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create prioritized experiment queue"""
        # Prepare prioritization data
        candidates_with_scores = []
        for calc in resonance_calculations:
            candidate = self.experiment_candidates[calc['candidate_id']]
            resonance_score = calc['resonance_score']
            
            candidates_with_scores.append({
                'candidate_id': calc['candidate_id'],
                'experiment_type': candidate.experiment_type,
                'family': candidate.family,
                'priority': candidate.priority.value,
                'resonance_score': resonance_score.overall_resonance,
                'confidence': resonance_score.confidence,
                'target_agents': candidate.target_agents,
                'resource_requirements': candidate.resource_requirements
            })
        
        # Calculate family caps
        family_caps = self._calculate_family_caps()
        
        # Prepare prioritization data
        prioritization_data = {
            'candidates_with_scores': candidates_with_scores,
            'max_queue_size': self.max_queue_size,
            'family_cap_percentage': self.family_cap_percentage,
            'current_queue': list(self.experiment_candidates.keys()),
            'family_caps': family_caps
        }
        
        # Generate prioritization using LLM
        prioritization = await self._generate_prioritization(prioritization_data)
        
        if prioritization:
            # Create prioritized queue
            queue_id = f"QUEUE_{int(datetime.now().timestamp())}"
            queue = PrioritizedQueue(
                queue_id=queue_id,
                queue_name="Resonance-Prioritized Experiment Queue",
                candidates=[self.experiment_candidates[cid] for cid in prioritization['prioritized_queue']['queue_order']],
                resonance_scores={cid: self.resonance_scores[cid] for cid in prioritization['prioritized_queue']['queue_order'] if cid in self.resonance_scores},
                queue_order=prioritization['prioritized_queue']['queue_order'],
                family_caps=family_caps,
                total_capacity=self.max_queue_size,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Store prioritized queue
            self.prioritized_queues[queue_id] = queue
            
            return {
                'queue_id': queue_id,
                'queue_name': queue.queue_name,
                'queue_order': prioritization['prioritized_queue']['queue_order'],
                'family_distribution': prioritization['prioritized_queue']['family_distribution'],
                'resonance_distribution': prioritization['prioritized_queue']['resonance_distribution'],
                'resource_allocation': prioritization['prioritized_queue']['resource_allocation'],
                'prioritization_insights': prioritization.get('prioritization_insights', []),
                'constraint_violations': prioritization.get('constraint_violations', []),
                'optimization_suggestions': prioritization.get('optimization_suggestions', []),
                'created_at': queue.created_at.isoformat()
            }
        
        return {}
    
    def _calculate_family_caps(self) -> Dict[str, int]:
        """Calculate family caps based on current candidates"""
        family_counts = {}
        for candidate in self.experiment_candidates.values():
            family_counts[candidate.family] = family_counts.get(candidate.family, 0) + 1
        
        family_caps = {}
        for family, count in family_counts.items():
            family_caps[family] = max(1, int(count * self.family_cap_percentage))
        
        return family_caps
    
    async def _generate_prioritization(self, prioritization_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate prioritization using LLM"""
        try:
            # Generate prioritization using LLM
            prioritization = await self._generate_llm_analysis(
                self.prioritization_prompt, prioritization_data
            )
            
            return prioritization
            
        except Exception as e:
            print(f"Error generating prioritization: {e}")
            return None
    
    async def _update_family_performance(self) -> List[Dict[str, Any]]:
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
    
    async def _generate_llm_analysis(self, prompt_template: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate LLM analysis using prompt template"""
        try:
            # Format prompt with data
            formatted_prompt = prompt_template.format(**data)
            
            # Call LLM (mock implementation)
            # In real implementation, use self.llm_client
            if 'resonance_analysis' in formatted_prompt:
                response = {
                    "resonance_analysis": {
                        "pattern_resonance": 0.75,
                        "family_resonance": 0.68,
                        "cross_agent_resonance": 0.82,
                        "temporal_resonance": 0.71,
                        "contextual_resonance": 0.69,
                        "overall_resonance": 0.73,
                        "confidence": 0.85
                    },
                    "resonance_insights": [
                        "Strong cross-agent coordination potential",
                        "Good alignment with current market conditions",
                        "Family performance indicates moderate saturation"
                    ],
                    "prioritization_recommendations": [
                        "High priority due to cross-agent potential",
                        "Consider pairing with related experiments",
                        "Monitor family saturation levels"
                    ],
                    "uncertainty_flags": ["Limited historical data for this family"]
                }
            else:
                # Extract candidate IDs from the data to use in response
                candidate_ids = []
                if 'candidates_with_scores' in data:
                    candidate_ids = [c['candidate_id'] for c in data['candidates_with_scores']]
                
                response = {
                    "prioritized_queue": {
                        "queue_order": candidate_ids if candidate_ids else ["CANDIDATE_1", "CANDIDATE_2", "CANDIDATE_3"],
                        "family_distribution": {"divergence": 2, "volume": 1, "correlation": 1},
                        "resonance_distribution": {"high": 2, "medium": 1, "low": 0},
                        "resource_allocation": {"raw_data_intelligence": 2, "indicator_intelligence": 1}
                    },
                    "prioritization_insights": [
                        "High resonance candidates prioritized",
                        "Family diversity maintained within caps",
                        "Resource allocation balanced across agents"
                    ],
                    "constraint_violations": [],
                    "optimization_suggestions": [
                        "Consider increasing family caps for high-performing families",
                        "Monitor resource utilization across agents"
                    ]
                }
            
            return response
            
        except Exception as e:
            print(f"Error generating LLM analysis: {e}")
            return None
    
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
                'tags': ['agent:central_intelligence:resonance_prioritization_system:prioritization_processed'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.9,
                'sig_confidence': 0.95,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'resonance_prioritization_system',
                'strategic_meta_type': 'resonance_prioritization',
                'resonance_score': 0.9
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing prioritization results: {e}")


# Example usage and testing
async def main():
    """Example usage of ResonancePrioritizationSystem"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create resonance prioritization system
    prioritization_system = ResonancePrioritizationSystem(supabase_manager, llm_client)
    
    # Mock experiment candidates
    experiment_candidates = [
        {
            'candidate_id': 'CANDIDATE_1',
            'experiment_type': 'durability',
            'hypothesis': 'Divergence patterns persist across high volatility regimes',
            'target_agents': ['raw_data_intelligence', 'indicator_intelligence'],
            'expected_conditions': {'regime': 'high_vol', 'timeframe': '1h'},
            'success_metrics': {'accuracy': 0.85, 'persistence': 0.8},
            'time_horizon': 'medium',
            'family': 'divergence',
            'priority': 'high'
        },
        {
            'candidate_id': 'CANDIDATE_2',
            'experiment_type': 'stack',
            'hypothesis': 'Volume + correlation breakdowns create stronger signals',
            'target_agents': ['raw_data_intelligence', 'pattern_intelligence'],
            'expected_conditions': {'regime': 'sideways', 'timeframe': '4h'},
            'success_metrics': {'accuracy': 0.9, 'novelty': 0.7},
            'time_horizon': 'short',
            'family': 'volume',
            'priority': 'medium'
        }
    ]
    
    system_context = {
        'recent_patterns': ['divergence_high_vol', 'volume_spike'],
        'cross_agent_activity': {'raw_data_intelligence': 0.8, 'indicator_intelligence': 0.6},
        'temporal_trends': {'high_vol_periods': 0.3, 'sideways_periods': 0.7}
    }
    
    # Process resonance prioritization
    results = await prioritization_system.process_resonance_prioritization(experiment_candidates, system_context)
    
    print("Resonance Prioritization Results:")
    print(f"Added Candidates: {len(results['added_candidates'])}")
    print(f"Resonance Calculations: {len(results['resonance_calculations'])}")
    print(f"Queue Creation: {results['queue_creation']}")
    print(f"Performance Updates: {len(results['performance_updates'])}")


if __name__ == "__main__":
    asyncio.run(main())
