"""
CIL Output & Directive System
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class DirectiveType(Enum):
    """Types of directives CIL can send to agents"""
    EXPERIMENT_ASSIGNMENT = "experiment_assignment"
    FOCUS_DIRECTIVE = "focus_directive"
    COORDINATION_REQUEST = "coordination_request"
    RESOURCE_ALLOCATION = "resource_allocation"
    DOCTRINE_UPDATE = "doctrine_update"
    STRATEGIC_PLAN = "strategic_plan"


class AutonomyLevel(Enum):
    """Agent autonomy levels"""
    STRICT = "strict"
    BOUNDED = "bounded"
    EXPLORATORY = "exploratory"


class DirectivePriority(Enum):
    """Directive priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Beacon:
    """High-level directional theme"""
    theme: str
    intent: str
    context: Dict[str, Any]
    confidence: float
    created_at: datetime


@dataclass
class Envelope:
    """Constraints and parameters"""
    constraints: Dict[str, Any]
    parameters: Dict[str, Any]
    guardrails: Dict[str, Any]
    time_horizon: str
    created_at: datetime


@dataclass
class Seed:
    """Optional hints and starting points"""
    hints: List[str]
    starting_points: List[str]
    suggestions: List[str]
    confidence: float
    created_at: datetime


@dataclass
class ExperimentDirective:
    """Structured experiment directive"""
    directive_id: str
    directive_type: DirectiveType
    target_agent: str
    hypothesis: str
    expected_conditions: Dict[str, Any]
    success_criteria: Dict[str, Any]
    duration_hours: int
    logging_requirements: List[str]
    autonomy_level: AutonomyLevel
    priority: DirectivePriority
    beacon: Optional[Beacon]
    envelope: Optional[Envelope]
    seed: Optional[Seed]
    created_at: datetime


@dataclass
class FeedbackRequest:
    """Request for feedback from agents"""
    request_id: str
    target_agent: str
    request_type: str
    requirements: List[str]
    deadline: datetime
    priority: DirectivePriority
    created_at: datetime


@dataclass
class CrossAgentCoordination:
    """Coordination between multiple agents"""
    coordination_id: str
    coordination_type: str
    participating_agents: List[str]
    coordination_plan: Dict[str, Any]
    dependencies: List[str]
    success_metrics: Dict[str, Any]
    created_at: datetime


class OutputDirectiveSystem:
    """CIL Output & Directive System - Section 7"""
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Configuration
        self.directive_timeout_hours = 24
        self.feedback_timeout_hours = 6
        self.coordination_timeout_hours = 12
        self.max_concurrent_directives = 10
        self.directive_retry_attempts = 3
        
        # Agent capabilities mapping
        self.agent_capabilities = {
            'raw_data_intelligence': ['divergence_detection', 'volume_analysis', 'microstructure_analysis'],
            'indicator_intelligence': ['rsi_analysis', 'macd_signals', 'bollinger_bands', 'technical_indicators'],
            'pattern_intelligence': ['composite_patterns', 'multi_timeframe_analysis', 'pattern_strength'],
            'system_control': ['parameter_optimization', 'threshold_management', 'performance_monitoring']
        }
        
        # Directive tracking
        self.active_directives = {}
        self.pending_feedback = {}
        self.coordination_sessions = {}
    
    async def generate_outputs_and_directives(self, global_synthesis_results: Dict[str, Any], 
                                            experiment_results: Dict[str, Any],
                                            learning_feedback_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate outputs and directives based on CIL analysis"""
        try:
            # Generate different types of outputs
            experiment_directives = await self._generate_experiment_directives(
                global_synthesis_results, experiment_results
            )
            
            feedback_requests = await self._generate_feedback_requests(
                learning_feedback_results, experiment_results
            )
            
            cross_agent_coordination = await self._generate_cross_agent_coordination(
                global_synthesis_results, experiment_results
            )
            
            strategic_plans = await self._generate_strategic_plans(
                global_synthesis_results, learning_feedback_results
            )
            
            # Compile results
            results = {
                'experiment_directives': experiment_directives,
                'feedback_requests': feedback_requests,
                'cross_agent_coordination': cross_agent_coordination,
                'strategic_plans': strategic_plans,
                'output_timestamp': datetime.now(timezone.utc),
                'output_errors': []
            }
            
            # Publish results
            await self._publish_output_results(results)
            
            return results
            
        except Exception as e:
            print(f"Error generating outputs and directives: {e}")
            return {
                'experiment_directives': [],
                'feedback_requests': [],
                'cross_agent_coordination': [],
                'strategic_plans': [],
                'output_timestamp': datetime.now(timezone.utc),
                'output_errors': [str(e)]
            }
    
    async def _generate_experiment_directives(self, global_synthesis_results: Dict[str, Any],
                                            experiment_results: Dict[str, Any]) -> List[ExperimentDirective]:
        """Generate experiment directives for agents"""
        directives = []
        
        # Extract experiment ideas from global synthesis
        experiment_ideas = global_synthesis_results.get('experiment_ideas', [])
        
        for idea in experiment_ideas:
            # Determine target agent based on capabilities
            target_agent = await self._determine_target_agent(idea)
            if not target_agent:
                continue
            
            # Create experiment directive
            directive = await self._create_experiment_directive(idea, target_agent, global_synthesis_results)
            if directive:
                directives.append(directive)
        
        return directives
    
    async def _determine_target_agent(self, experiment_idea: Dict[str, Any]) -> Optional[str]:
        """Determine which agent should handle the experiment"""
        idea_type = experiment_idea.get('type', '')
        idea_family = experiment_idea.get('family', '')
        
        # Map experiment types to agent capabilities
        if 'divergence' in idea_type.lower() or 'volume' in idea_type.lower():
            return 'raw_data_intelligence'
        elif 'rsi' in idea_type.lower() or 'macd' in idea_type.lower() or 'technical' in idea_type.lower():
            return 'indicator_intelligence'
        elif 'pattern' in idea_type.lower() or 'composite' in idea_type.lower():
            return 'pattern_intelligence'
        elif 'parameter' in idea_type.lower() or 'threshold' in idea_type.lower():
            return 'system_control'
        
        # Default to raw_data_intelligence for unknown types
        return 'raw_data_intelligence'
    
    async def _create_experiment_directive(self, experiment_idea: Dict[str, Any], 
                                         target_agent: str,
                                         global_synthesis_results: Dict[str, Any]) -> Optional[ExperimentDirective]:
        """Create a structured experiment directive"""
        try:
            # Generate directive components
            beacon = await self._create_beacon(experiment_idea, global_synthesis_results)
            envelope = await self._create_envelope(experiment_idea, target_agent)
            seed = await self._create_seed(experiment_idea, global_synthesis_results)
            
            # Determine autonomy level
            autonomy_level = await self._determine_autonomy_level(target_agent, experiment_idea)
            
            # Determine priority
            priority = await self._determine_priority(experiment_idea, global_synthesis_results)
            
            # Create directive
            directive = ExperimentDirective(
                directive_id=f"DIRECTIVE_{int(datetime.now().timestamp())}",
                directive_type=DirectiveType.EXPERIMENT_ASSIGNMENT,
                target_agent=target_agent,
                hypothesis=experiment_idea.get('hypothesis', ''),
                expected_conditions=experiment_idea.get('conditions', {}),
                success_criteria=experiment_idea.get('success_criteria', {}),
                duration_hours=experiment_idea.get('duration_hours', 24),
                logging_requirements=experiment_idea.get('logging_requirements', []),
                autonomy_level=autonomy_level,
                priority=priority,
                beacon=beacon,
                envelope=envelope,
                seed=seed,
                created_at=datetime.now(timezone.utc)
            )
            
            return directive
            
        except Exception as e:
            print(f"Error creating experiment directive: {e}")
            return None
    
    async def _create_beacon(self, experiment_idea: Dict[str, Any], 
                           global_synthesis_results: Dict[str, Any]) -> Beacon:
        """Create a beacon (directional theme)"""
        theme = experiment_idea.get('family', 'general_exploration')
        intent = experiment_idea.get('hypothesis', 'Explore new patterns')
        
        context = {
            'regime': global_synthesis_results.get('current_regime', 'unknown'),
            'session': global_synthesis_results.get('current_session', 'unknown'),
            'volatility': global_synthesis_results.get('volatility_level', 'medium')
        }
        
        confidence = experiment_idea.get('confidence', 0.7)
        
        return Beacon(
            theme=theme,
            intent=intent,
            context=context,
            confidence=confidence,
            created_at=datetime.now(timezone.utc)
        )
    
    async def _create_envelope(self, experiment_idea: Dict[str, Any], target_agent: str) -> Envelope:
        """Create an envelope (constraints and parameters)"""
        constraints = {
            'max_experiments': 1,
            'time_limit_hours': experiment_idea.get('duration_hours', 24),
            'resource_limit': 'standard'
        }
        
        parameters = {
            'confidence_threshold': 0.7,
            'similarity_threshold': 0.8,
            'success_threshold': 0.6
        }
        
        guardrails = {
            'stop_on_failure': True,
            'max_false_positives': 5,
            'min_sample_size': 10
        }
        
        time_horizon = f"{experiment_idea.get('duration_hours', 24)}_hours"
        
        return Envelope(
            constraints=constraints,
            parameters=parameters,
            guardrails=guardrails,
            time_horizon=time_horizon,
            created_at=datetime.now(timezone.utc)
        )
    
    async def _create_seed(self, experiment_idea: Dict[str, Any], 
                         global_synthesis_results: Dict[str, Any]) -> Seed:
        """Create a seed (optional hints)"""
        hints = experiment_idea.get('hints', [])
        starting_points = experiment_idea.get('starting_points', [])
        suggestions = experiment_idea.get('suggestions', [])
        
        confidence = experiment_idea.get('seed_confidence', 0.6)
        
        return Seed(
            hints=hints,
            starting_points=starting_points,
            suggestions=suggestions,
            confidence=confidence,
            created_at=datetime.now(timezone.utc)
        )
    
    async def _determine_autonomy_level(self, target_agent: str, experiment_idea: Dict[str, Any]) -> AutonomyLevel:
        """Determine autonomy level for the agent"""
        # Check agent performance
        agent_performance = await self._get_agent_performance(target_agent)
        
        if agent_performance > 0.8:
            return AutonomyLevel.EXPLORATORY
        elif agent_performance > 0.6:
            return AutonomyLevel.BOUNDED
        else:
            return AutonomyLevel.STRICT
    
    async def _get_agent_performance(self, agent_id: str) -> float:
        """Get agent performance score"""
        # Mock performance score - in real implementation, query database
        performance_scores = {
            'raw_data_intelligence': 0.8,
            'indicator_intelligence': 0.7,
            'pattern_intelligence': 0.75,
            'system_control': 0.6
        }
        return performance_scores.get(agent_id, 0.5)
    
    async def _determine_priority(self, experiment_idea: Dict[str, Any], 
                                global_synthesis_results: Dict[str, Any]) -> DirectivePriority:
        """Determine directive priority"""
        confidence = experiment_idea.get('confidence', 0.5)
        urgency = experiment_idea.get('urgency', 'medium')
        
        if confidence > 0.9 and urgency == 'high':
            return DirectivePriority.CRITICAL
        elif confidence > 0.8 or urgency == 'high':
            return DirectivePriority.HIGH
        elif confidence > 0.6:
            return DirectivePriority.MEDIUM
        else:
            return DirectivePriority.LOW
    
    async def _generate_feedback_requests(self, learning_feedback_results: Dict[str, Any],
                                        experiment_results: Dict[str, Any]) -> List[FeedbackRequest]:
        """Generate feedback requests for agents"""
        requests = []
        
        # Extract lessons that need feedback
        lessons = learning_feedback_results.get('lessons', [])
        
        for lesson in lessons:
            if lesson.get('needs_feedback', False):
                request = await self._create_feedback_request(lesson, experiment_results)
                if request:
                    requests.append(request)
        
        return requests
    
    async def _create_feedback_request(self, lesson: Dict[str, Any], 
                                     experiment_results: Dict[str, Any]) -> Optional[FeedbackRequest]:
        """Create a feedback request"""
        try:
            target_agent = lesson.get('source_agent', 'unknown')
            request_type = lesson.get('feedback_type', 'general')
            
            requirements = [
                'Report raw results (success/fail/anomaly)',
                'Log structured lessons into system memory',
                'Highlight surprises or unexpected patterns',
                'Suggest refinements if observed'
            ]
            
            deadline = datetime.now(timezone.utc) + timedelta(hours=self.feedback_timeout_hours)
            priority = DirectivePriority.MEDIUM
            
            request = FeedbackRequest(
                request_id=f"FEEDBACK_{int(datetime.now().timestamp())}",
                target_agent=target_agent,
                request_type=request_type,
                requirements=requirements,
                deadline=deadline,
                priority=priority,
                created_at=datetime.now(timezone.utc)
            )
            
            return request
            
        except Exception as e:
            print(f"Error creating feedback request: {e}")
            return None
    
    async def _generate_cross_agent_coordination(self, global_synthesis_results: Dict[str, Any],
                                               experiment_results: Dict[str, Any]) -> List[CrossAgentCoordination]:
        """Generate cross-agent coordination plans"""
        coordinations = []
        
        # Extract confluence events that need coordination
        confluence_events = global_synthesis_results.get('confluence_events', [])
        
        for event in confluence_events:
            if event.get('needs_coordination', False):
                coordination = await self._create_cross_agent_coordination(event, global_synthesis_results)
                if coordination:
                    coordinations.append(coordination)
        
        return coordinations
    
    async def _create_cross_agent_coordination(self, confluence_event: Dict[str, Any],
                                             global_synthesis_results: Dict[str, Any]) -> Optional[CrossAgentCoordination]:
        """Create cross-agent coordination plan"""
        try:
            participating_agents = confluence_event.get('involved_agents', [])
            coordination_type = confluence_event.get('coordination_type', 'parallel')
            
            coordination_plan = {
                'sequence': confluence_event.get('sequence', 'parallel'),
                'dependencies': confluence_event.get('dependencies', []),
                'communication_protocol': 'database_strands',
                'success_criteria': confluence_event.get('success_criteria', {})
            }
            
            dependencies = confluence_event.get('dependencies', [])
            success_metrics = confluence_event.get('success_metrics', {})
            
            coordination = CrossAgentCoordination(
                coordination_id=f"COORD_{int(datetime.now().timestamp())}",
                coordination_type=coordination_type,
                participating_agents=participating_agents,
                coordination_plan=coordination_plan,
                dependencies=dependencies,
                success_metrics=success_metrics,
                created_at=datetime.now(timezone.utc)
            )
            
            return coordination
            
        except Exception as e:
            print(f"Error creating cross-agent coordination: {e}")
            return None
    
    async def _generate_strategic_plans(self, global_synthesis_results: Dict[str, Any],
                                      learning_feedback_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate strategic plans"""
        plans = []
        
        # Extract insights that can form strategic plans
        insights = global_synthesis_results.get('insights', [])
        doctrine_updates = learning_feedback_results.get('doctrine_updates', [])
        
        for insight in insights:
            if insight.get('plan_worthy', False):
                plan = await self._create_strategic_plan(insight, doctrine_updates)
                if plan:
                    plans.append(plan)
        
        return plans
    
    async def _create_strategic_plan(self, insight: Dict[str, Any], 
                                   doctrine_updates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Create a strategic plan"""
        try:
            plan = {
                'plan_id': f"PLAN_{int(datetime.now().timestamp())}",
                'plan_type': insight.get('plan_type', 'strategic_exploration'),
                'evidence_stack': insight.get('evidence', []),
                'conditions': {
                    'activate': insight.get('activation_conditions', {}),
                    'confirm': insight.get('confirmation_conditions', {}),
                    'invalidate': insight.get('invalidation_conditions', {})
                },
                'scope': {
                    'assets': insight.get('target_assets', []),
                    'timeframes': insight.get('target_timeframes', []),
                    'regimes': insight.get('target_regimes', [])
                },
                'provenance': {
                    'source_insights': [insight.get('id', '')],
                    'doctrine_references': [d.get('id', '') for d in doctrine_updates],
                    'confidence_level': insight.get('confidence', 0.7)
                },
                'notes': {
                    'mechanism': insight.get('mechanism_hypothesis', ''),
                    'risks': insight.get('risks', []),
                    'fails_when': insight.get('fails_when', [])
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            return plan
            
        except Exception as e:
            print(f"Error creating strategic plan: {e}")
            return None
    
    async def _publish_output_results(self, results: Dict[str, Any]):
        """Publish output results as CIL strand"""
        try:
            # Create CIL output strand
            cil_strand = {
                'id': f"cil_output_directive_{int(datetime.now().timestamp())}",
                'kind': 'cil_output_directive',
                'module': 'alpha',
                'symbol': 'ALL',
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': ['agent:central_intelligence:output_directive_system:directives_generated'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.8,
                'sig_confidence': 0.9,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'output_directive_system',
                'strategic_meta_type': 'directive_generation',
                'resonance_score': 0.8
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing output results: {e}")


# Example usage and testing
async def main():
    """Example usage of OutputDirectiveSystem"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create output directive system
    output_system = OutputDirectiveSystem(supabase_manager, llm_client)
    
    # Mock input data
    global_synthesis_results = {
        'experiment_ideas': [
            {
                'type': 'divergence_volume_confluence',
                'family': 'divergence',
                'hypothesis': 'Divergence + volume spike = stronger signal',
                'conditions': {'regime': 'high_vol', 'session': 'US'},
                'success_criteria': {'accuracy': 0.8, 'persistence': 0.7},
                'duration_hours': 24,
                'confidence': 0.8,
                'urgency': 'medium'
            }
        ],
        'confluence_events': [
            {
                'needs_coordination': True,
                'involved_agents': ['raw_data_intelligence', 'indicator_intelligence'],
                'coordination_type': 'sequential',
                'dependencies': ['divergence_detection'],
                'success_criteria': {'combined_accuracy': 0.85}
            }
        ],
        'insights': [
            {
                'plan_worthy': True,
                'plan_type': 'strategic_exploration',
                'evidence': ['confluence_pattern', 'volume_anomaly'],
                'activation_conditions': {'volatility': 'high'},
                'target_assets': ['BTC', 'ETH'],
                'confidence': 0.8
            }
        ]
    }
    
    experiment_results = {}
    learning_feedback_results = {
        'lessons': [
            {
                'needs_feedback': True,
                'source_agent': 'raw_data_intelligence',
                'feedback_type': 'pattern_validation'
            }
        ],
        'doctrine_updates': [
            {'id': 'doctrine_123', 'type': 'promotion'}
        ]
    }
    
    # Generate outputs and directives
    results = await output_system.generate_outputs_and_directives(
        global_synthesis_results, experiment_results, learning_feedback_results
    )
    
    print("Output and Directive Generation Results:")
    print(f"Experiment Directives: {len(results['experiment_directives'])}")
    print(f"Feedback Requests: {len(results['feedback_requests'])}")
    print(f"Cross-Agent Coordination: {len(results['cross_agent_coordination'])}")
    print(f"Strategic Plans: {len(results['strategic_plans'])}")


if __name__ == "__main__":
    asyncio.run(main())
