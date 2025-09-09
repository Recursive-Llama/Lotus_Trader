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


# Cross-Agent Learning Orchestration System Integration
class LearningType(Enum):
    """Types of learning orchestration"""
    DISTRIBUTED = "distributed"
    COLLABORATIVE = "collaborative"
    TRANSFER = "transfer"
    META_LEARNING = "meta_learning"
    FEDERATED = "federated"


class LearningPhase(Enum):
    """Phases of learning orchestration"""
    PLANNING = "planning"
    COORDINATION = "coordination"
    EXECUTION = "execution"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"


class LearningStatus(Enum):
    """Status of learning orchestration"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"


class AgentRole(Enum):
    """Roles of agents in learning orchestration"""
    LEADER = "leader"
    FOLLOWER = "follower"
    COORDINATOR = "coordinator"
    VALIDATOR = "validator"
    SYNTHESIZER = "synthesizer"


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


# Cross-Agent Learning Orchestration System Integration
@dataclass
class LearningSession:
    """A learning session for cross-agent orchestration"""
    session_id: str
    learning_type: LearningType
    learning_phase: LearningPhase
    status: LearningStatus
    participating_agents: List[str]
    session_plan: Dict[str, Any]
    learning_tasks: List[str]
    coordination_requirements: List[Dict[str, Any]]
    success_criteria: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class LearningTask:
    """A learning task within a session"""
    task_id: str
    session_id: str
    assigned_agent: str
    agent_role: AgentRole
    task_description: str
    learning_objectives: List[str]
    expected_outcomes: List[str]
    dependencies: List[str]
    deadline: datetime
    status: LearningStatus
    created_at: datetime


@dataclass
class LearningCoordination:
    """Coordination between agents in learning"""
    coordination_id: str
    session_id: str
    coordination_type: str
    participating_agents: List[str]
    coordination_plan: Dict[str, Any]
    communication_protocol: List[Dict[str, Any]]
    synchronization_points: List[Dict[str, Any]]
    status: LearningStatus
    created_at: datetime


@dataclass
class LearningSynthesis:
    """Synthesis of learning results"""
    synthesis_id: str
    session_id: str
    synthesis_type: str
    input_results: List[Dict[str, Any]]
    synthesis_methodology: Dict[str, Any]
    synthesized_insights: List[Dict[str, Any]]
    learning_transfer_opportunities: List[Dict[str, Any]]
    confidence_score: float
    created_at: datetime


@dataclass
class AgentWorkload:
    """Agent workload tracking"""
    agent_id: str
    active_tasks: List[str]
    completed_tasks: List[str]
    pending_tasks: List[str]
    workload_capacity: float
    current_utilization: float
    performance_metrics: Dict[str, float]
    last_updated: datetime


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
        
        # Cross-Agent Learning Orchestration System Configuration
        self.learning_sessions: Dict[str, LearningSession] = {}
        self.learning_tasks: Dict[str, LearningTask] = {}
        self.learning_coordinations: Dict[str, LearningCoordination] = {}
        self.learning_syntheses: Dict[str, LearningSynthesis] = {}
        self.agent_workloads: Dict[str, AgentWorkload] = {}
        
        # Learning orchestration parameters
        self.learning_orchestration_enabled = True
        self.max_concurrent_sessions = 5
        self.learning_session_timeout_hours = 24
        self.workload_balancing_threshold = 0.8
        self.learning_transfer_threshold = 0.7
        
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
    
    # Cross-Agent Learning Orchestration System Methods
    async def process_cross_agent_learning_orchestration(self, global_view: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process cross-agent learning orchestration to coordinate learning sessions,
        manage agent workloads, and synthesize learning results across the system.
        """
        logger.info("Processing cross-agent learning orchestration.")
        
        try:
            # Process learning orchestration
            orchestration_results = await self._orchestrate_learning_sessions(global_view)
            
            # Manage agent workloads
            workload_results = await self._manage_agent_workloads(global_view)
            
            # Synthesize learning results
            synthesis_results = await self._synthesize_learning_results(global_view)
            
            # Compile orchestration insights
            orchestration_insights = await self._compile_orchestration_insights(
                orchestration_results, workload_results, synthesis_results
            )
            
            # Publish orchestration results
            await self._publish_orchestration_results(orchestration_insights)
            
            return {
                "orchestration_status": "completed",
                "learning_sessions_managed": len(orchestration_results.get("sessions", [])),
                "workload_balancing_actions": len(workload_results.get("actions", [])),
                "learning_syntheses": len(synthesis_results.get("syntheses", [])),
                "orchestration_insights": len(orchestration_insights)
            }
            
        except Exception as e:
            logger.error(f"Error in cross-agent learning orchestration: {e}")
            return {"orchestration_status": "error", "error": str(e)}
    
    async def _orchestrate_learning_sessions(self, global_view: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate learning sessions across agents"""
        sessions = []
        
        # Analyze learning opportunities from global view
        learning_opportunities = await self._identify_learning_opportunities(global_view)
        
        for opportunity in learning_opportunities:
            # Create learning session
            session = await self._create_learning_session(opportunity)
            if session:
                sessions.append(session)
                self.learning_sessions[session.session_id] = session
        
        return {"sessions": sessions}
    
    async def _identify_learning_opportunities(self, global_view: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify learning opportunities from global view"""
        opportunities = []
        
        # Analyze patterns for learning potential
        patterns = global_view.get("patterns", [])
        for pattern in patterns:
            if pattern.get("learning_potential", 0) > self.learning_transfer_threshold:
                opportunities.append({
                    "type": "pattern_learning",
                    "pattern_id": pattern.get("id"),
                    "learning_type": LearningType.PATTERN_ANALYSIS,
                    "participating_agents": ["raw_data_intelligence", "pattern_intelligence"],
                    "learning_objectives": ["understand_pattern_mechanisms", "improve_detection_accuracy"]
                })
        
        # Analyze failures for learning potential
        failures = global_view.get("failures", [])
        for failure in failures:
            if failure.get("learning_value", 0) > self.learning_transfer_threshold:
                opportunities.append({
                    "type": "failure_learning",
                    "failure_id": failure.get("id"),
                    "learning_type": LearningType.FAILURE_ANALYSIS,
                    "participating_agents": failure.get("involved_agents", []),
                    "learning_objectives": ["understand_failure_modes", "prevent_recurrence"]
                })
        
        return opportunities
    
    async def _create_learning_session(self, opportunity: Dict[str, Any]) -> Optional[LearningSession]:
        """Create a learning session from an opportunity"""
        try:
            session_id = f"learning_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create learning tasks for participating agents
            learning_tasks = []
            for agent_id in opportunity["participating_agents"]:
                task = LearningTask(
                    task_id=f"task_{session_id}_{agent_id}",
                    session_id=session_id,
                    assigned_agent=agent_id,
                    agent_role=AgentRole.LEARNER,
                    task_description=f"Learn from {opportunity['type']}",
                    learning_objectives=opportunity["learning_objectives"],
                    expected_outcomes=["improved_understanding", "enhanced_capabilities"],
                    dependencies=[],
                    deadline=datetime.now() + timedelta(hours=self.learning_session_timeout_hours),
                    status=LearningStatus.PENDING,
                    created_at=datetime.now()
                )
                learning_tasks.append(task)
                self.learning_tasks[task.task_id] = task
            
            # Create learning session
            session = LearningSession(
                session_id=session_id,
                learning_type=opportunity["learning_type"],
                learning_phase=LearningPhase.PLANNING,
                status=LearningStatus.ACTIVE,
                participating_agents=opportunity["participating_agents"],
                session_plan={
                    "objectives": opportunity["learning_objectives"],
                    "methodology": "collaborative_analysis",
                    "success_criteria": {"completion_rate": 0.8, "learning_transfer": 0.7}
                },
                learning_tasks=[task.task_id for task in learning_tasks],
                coordination_requirements=[],
                success_criteria={"learning_transfer": 0.7, "knowledge_retention": 0.8},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Error creating learning session: {e}")
            return None
    
    async def _manage_agent_workloads(self, global_view: Dict[str, Any]) -> Dict[str, Any]:
        """Manage agent workloads and balance learning tasks"""
        actions = []
        
        # Update agent workload tracking
        for agent_id in self.agent_capabilities.keys():
            workload = await self._update_agent_workload(agent_id)
            self.agent_workloads[agent_id] = workload
            
            # Check if workload balancing is needed
            if workload.current_utilization > self.workload_balancing_threshold:
                action = await self._balance_agent_workload(agent_id, workload)
                if action:
                    actions.append(action)
        
        return {"actions": actions}
    
    async def _update_agent_workload(self, agent_id: str) -> AgentWorkload:
        """Update workload tracking for an agent"""
        # Get active tasks for this agent
        active_tasks = [task_id for task_id, task in self.learning_tasks.items() 
                       if task.assigned_agent == agent_id and task.status == LearningStatus.ACTIVE]
        
        # Get completed tasks
        completed_tasks = [task_id for task_id, task in self.learning_tasks.items() 
                          if task.assigned_agent == agent_id and task.status == LearningStatus.COMPLETED]
        
        # Get pending tasks
        pending_tasks = [task_id for task_id, task in self.learning_tasks.items() 
                        if task.assigned_agent == agent_id and task.status == LearningStatus.PENDING]
        
        # Calculate utilization (simplified)
        total_tasks = len(active_tasks) + len(pending_tasks)
        capacity = 10  # Assume each agent can handle 10 concurrent tasks
        utilization = min(total_tasks / capacity, 1.0)
        
        return AgentWorkload(
            agent_id=agent_id,
            active_tasks=active_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            workload_capacity=capacity,
            current_utilization=utilization,
            performance_metrics={"completion_rate": len(completed_tasks) / max(len(completed_tasks) + len(active_tasks), 1)},
            last_updated=datetime.now()
        )
    
    async def _balance_agent_workload(self, agent_id: str, workload: AgentWorkload) -> Optional[Dict[str, Any]]:
        """Balance workload for an overloaded agent"""
        if workload.current_utilization <= self.workload_balancing_threshold:
            return None
        
        # Find agents with lower utilization
        available_agents = [aid for aid, wl in self.agent_workloads.items() 
                           if wl.current_utilization < self.workload_balancing_threshold and aid != agent_id]
        
        if not available_agents:
            return None
        
        # Redistribute some tasks
        tasks_to_redistribute = workload.pending_tasks[:2]  # Move 2 pending tasks
        
        return {
            "action_type": "workload_redistribution",
            "source_agent": agent_id,
            "target_agents": available_agents[:1],
            "tasks_to_redistribute": tasks_to_redistribute,
            "reason": "high_utilization"
        }
    
    async def _synthesize_learning_results(self, global_view: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize learning results across sessions"""
        syntheses = []
        
        # Find completed learning sessions
        completed_sessions = [session for session in self.learning_sessions.values() 
                             if session.status == LearningStatus.COMPLETED]
        
        for session in completed_sessions:
            # Gather results from session tasks
            session_tasks = [task for task in self.learning_tasks.values() 
                           if task.session_id == session.session_id]
            
            input_results = []
            for task in session_tasks:
                input_results.append({
                    "task_id": task.task_id,
                    "agent_id": task.assigned_agent,
                    "learning_objectives": task.learning_objectives,
                    "outcomes": task.expected_outcomes
                })
            
            # Create learning synthesis
            synthesis = LearningSynthesis(
                synthesis_id=f"synthesis_{session.session_id}",
                session_id=session.session_id,
                synthesis_type="cross_agent_learning",
                input_results=input_results,
                synthesis_methodology={"approach": "collaborative_analysis", "integration": "pattern_synthesis"},
                synthesized_insights=[
                    {"insight": "improved_pattern_recognition", "confidence": 0.8},
                    {"insight": "enhanced_collaboration", "confidence": 0.7}
                ],
                learning_transfer_opportunities=[
                    {"opportunity": "apply_to_similar_patterns", "transfer_potential": 0.8}
                ],
                confidence_score=0.75,
                created_at=datetime.now()
            )
            
            syntheses.append(synthesis)
            self.learning_syntheses[synthesis.synthesis_id] = synthesis
        
        return {"syntheses": syntheses}
    
    async def _compile_orchestration_insights(self, orchestration_results: Dict[str, Any], 
                                            workload_results: Dict[str, Any], 
                                            synthesis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compile insights from orchestration results"""
        insights = []
        
        # Learning session insights
        sessions = orchestration_results.get("sessions", [])
        if sessions:
            insights.append({
                "type": "learning_orchestration",
                "insight": f"Managed {len(sessions)} learning sessions",
                "recommendation": "Continue cross-agent learning coordination",
                "confidence": 0.8
            })
        
        # Workload balancing insights
        actions = workload_results.get("actions", [])
        if actions:
            insights.append({
                "type": "workload_balancing",
                "insight": f"Performed {len(actions)} workload balancing actions",
                "recommendation": "Monitor agent utilization patterns",
                "confidence": 0.7
            })
        
        # Learning synthesis insights
        syntheses = synthesis_results.get("syntheses", [])
        if syntheses:
            insights.append({
                "type": "learning_synthesis",
                "insight": f"Generated {len(syntheses)} learning syntheses",
                "recommendation": "Apply synthesized insights to improve system performance",
                "confidence": 0.8
            })
        
        return insights
    
    async def _publish_orchestration_results(self, orchestration_insights: List[Dict[str, Any]]):
        """Publish orchestration results to the database"""
        try:
            # Create strand for orchestration results
            strand_data = {
                "agent_id": self.agent_id,
                "team_member": "output_directive_system",
                "strand_type": "cross_agent_learning_orchestration",
                "content": "Cross-agent learning orchestration completed",
                "metadata": {
                    "orchestration_insights": orchestration_insights,
                    "learning_sessions_count": len(self.learning_sessions),
                    "active_tasks_count": len([t for t in self.learning_tasks.values() if t.status == LearningStatus.ACTIVE]),
                    "workload_balancing_actions": len([w for w in self.agent_workloads.values() if w.current_utilization > self.workload_balancing_threshold])
                },
                "confidence": 0.8,
                "signal_strength": 0.7,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.supabase_manager.insert_strand(strand_data)
            logger.info("Published cross-agent learning orchestration results.")
            
        except Exception as e:
            logger.error(f"Error publishing orchestration results: {e}")

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
