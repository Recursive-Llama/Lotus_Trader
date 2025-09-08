"""
CIL Experiment Orchestration Engine

Section 4: Experiment Orchestration (CIL)
- From Global View → Experiment Ideas (cross-agent triggers, family-level gaps, persistence checks)
- Hypothesis Framing (expected conditions, success metrics, time horizons)
- Agent Assignment (capabilities, focus, exploration budget)
- Experiment Design Parameters (parameter sweeps, guardrails, tracking)
- Success/Failure Criteria (measurable thresholds, novelty assessment)
- Feedback Loop (agents report results, CIL integrates into global view)

Vector Search Integration:
- Vector similarity for experiment design and hypothesis generation
- Vector embeddings for experiment pattern matching and optimization
- Vector search for experiment outcome analysis and learning
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem


class ExperimentShape(Enum):
    """Canonical experiment shapes"""
    DURABILITY = "durability"  # Same family, spanning regimes/sessions
    STACK = "stack"  # A∧B confluence test
    LEAD_LAG = "lead_lag"  # A→B causal hint
    ABLATION = "ablation"  # Remove feature; measure edge decay
    BOUNDARY = "boundary"  # Find failure surface


class ExperimentStatus(Enum):
    """Experiment status"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExperimentHypothesis:
    """Experiment hypothesis"""
    hypothesis_id: str
    hypothesis_text: str
    expected_conditions: Dict[str, Any]
    success_metrics: Dict[str, float]
    time_horizon: str
    confidence_level: float
    evidence_basis: List[str]


@dataclass
class ExperimentDesign:
    """Experiment design"""
    experiment_id: str
    hypothesis: ExperimentHypothesis
    shape: ExperimentShape
    target_agents: List[str]
    parameter_sweeps: Dict[str, List[Any]]
    guardrails: Dict[str, Any]
    tracking_requirements: List[str]
    ttl_hours: int
    priority_score: float


@dataclass
class ExperimentAssignment:
    """Experiment assignment to agents"""
    assignment_id: str
    experiment_id: str
    target_agent: str
    assignment_type: str  # "strict", "bounded", "exploratory"
    directives: Dict[str, Any]
    success_criteria: Dict[str, float]
    reporting_requirements: List[str]
    deadline: datetime


@dataclass
class ExperimentResult:
    """Experiment result"""
    result_id: str
    experiment_id: str
    agent_id: str
    outcome: str  # "success", "failure", "partial", "inconclusive"
    metrics: Dict[str, float]
    lessons_learned: List[str]
    recommendations: List[str]
    confidence_score: float
    completion_time: datetime


class ExperimentOrchestrationEngine:
    """
    CIL Experiment Orchestration Engine
    
    Responsibilities:
    1. From Global View → Experiment Ideas (cross-agent triggers, family-level gaps, persistence checks)
    2. Hypothesis Framing (expected conditions, success metrics, time horizons)
    3. Agent Assignment (capabilities, focus, exploration budget)
    4. Experiment Design Parameters (parameter sweeps, guardrails, tracking)
    5. Success/Failure Criteria (measurable thresholds, novelty assessment)
    6. Feedback Loop (agents report results, CIL integrates into global view)
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Orchestration configuration
        self.max_concurrent_experiments = 10
        self.experiment_timeout_hours = 24
        self.min_sample_size = 10
        self.success_threshold = 0.7
        self.novelty_threshold = 0.6
        
        # Agent capabilities mapping
        self.agent_capabilities = {
            'raw_data_intelligence': ['divergence_detection', 'volume_analysis', 'microstructure'],
            'indicator_intelligence': ['rsi_analysis', 'macd_signals', 'bollinger_bands'],
            'pattern_intelligence': ['composite_patterns', 'multi_timeframe', 'pattern_strength'],
            'system_control': ['parameter_optimization', 'threshold_management', 'performance_monitoring']
        }
        
    async def orchestrate_experiments(self, global_view: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrate experiments based on global view
        
        Args:
            global_view: Output from GlobalSynthesisEngine
            
        Returns:
            Dict containing orchestration results
        """
        try:
            # Perform orchestration operations in parallel
            results = await asyncio.gather(
                self.generate_experiment_ideas(global_view),
                self.design_experiments(global_view),
                self.assign_experiments(global_view),
                self.track_experiment_progress(),
                self.process_experiment_results(),
                return_exceptions=True
            )
            
            # Structure orchestration results
            orchestration_results = {
                'experiment_ideas': results[0] if not isinstance(results[0], Exception) else [],
                'experiment_designs': results[1] if not isinstance(results[1], Exception) else [],
                'experiment_assignments': results[2] if not isinstance(results[2], Exception) else [],
                'active_experiments': results[3] if not isinstance(results[3], Exception) else [],
                'completed_experiments': results[4] if not isinstance(results[4], Exception) else [],
                'orchestration_timestamp': datetime.now(timezone.utc),
                'orchestration_errors': [str(r) for r in results if isinstance(r, Exception)]
            }
            
            # Publish orchestration results as CIL strand
            await self._publish_orchestration_results(orchestration_results)
            
            return orchestration_results
            
        except Exception as e:
            print(f"Error orchestrating experiments: {e}")
            return {'error': str(e), 'orchestration_timestamp': datetime.now(timezone.utc)}
    
    async def generate_experiment_ideas(self, global_view: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate experiment ideas from global view
        
        Returns:
            List of experiment ideas with triggers and rationale
        """
        try:
            experiment_ideas = []
            
            # Get global view components
            cross_agent_correlation = global_view.get('cross_agent_correlation', {})
            coverage_analysis = global_view.get('coverage_analysis', {})
            signal_families = global_view.get('signal_families', [])
            meta_patterns = global_view.get('meta_patterns', [])
            doctrine_insights = global_view.get('doctrine_insights', [])
            
            # Generate ideas from cross-agent correlations
            correlation_ideas = await self._generate_correlation_experiment_ideas(cross_agent_correlation)
            experiment_ideas.extend(correlation_ideas)
            
            # Generate ideas from coverage gaps
            coverage_ideas = await self._generate_coverage_experiment_ideas(coverage_analysis)
            experiment_ideas.extend(coverage_ideas)
            
            # Generate ideas from signal families
            family_ideas = await self._generate_family_experiment_ideas(signal_families)
            experiment_ideas.extend(family_ideas)
            
            # Generate ideas from meta-patterns
            pattern_ideas = await self._generate_pattern_experiment_ideas(meta_patterns)
            experiment_ideas.extend(pattern_ideas)
            
            # Generate ideas from doctrine insights
            doctrine_ideas = await self._generate_doctrine_experiment_ideas(doctrine_insights)
            experiment_ideas.extend(doctrine_ideas)
            
            return experiment_ideas
            
        except Exception as e:
            print(f"Error generating experiment ideas: {e}")
            return []
    
    async def design_experiments(self, global_view: Dict[str, Any]) -> List[ExperimentDesign]:
        """
        Design experiments from experiment ideas
        
        Returns:
            List of ExperimentDesign objects
        """
        try:
            # Get experiment ideas
            experiment_ideas = await self.generate_experiment_ideas(global_view)
            
            experiment_designs = []
            for idea in experiment_ideas:
                # Create hypothesis
                hypothesis = await self._create_experiment_hypothesis(idea)
                
                # Determine experiment shape
                shape = self._determine_experiment_shape(idea)
                
                # Select target agents
                target_agents = self._select_target_agents(idea, hypothesis)
                
                # Design parameter sweeps
                parameter_sweeps = self._design_parameter_sweeps(idea, hypothesis)
                
                # Set guardrails
                guardrails = self._set_experiment_guardrails(idea, hypothesis)
                
                # Define tracking requirements
                tracking_requirements = self._define_tracking_requirements(idea, hypothesis)
                
                # Calculate priority score
                priority_score = self._calculate_priority_score(idea, hypothesis)
                
                # Create experiment design
                experiment_design = ExperimentDesign(
                    experiment_id=f"EXP_{int(datetime.now().timestamp())}_{len(experiment_designs)}",
                    hypothesis=hypothesis,
                    shape=shape,
                    target_agents=target_agents,
                    parameter_sweeps=parameter_sweeps,
                    guardrails=guardrails,
                    tracking_requirements=tracking_requirements,
                    ttl_hours=self.experiment_timeout_hours,
                    priority_score=priority_score
                )
                
                experiment_designs.append(experiment_design)
            
            return experiment_designs
            
        except Exception as e:
            print(f"Error designing experiments: {e}")
            return []
    
    async def assign_experiments(self, global_view: Dict[str, Any]) -> List[ExperimentAssignment]:
        """
        Assign experiments to agents
        
        Returns:
            List of ExperimentAssignment objects
        """
        try:
            # Get experiment designs
            experiment_designs = await self.design_experiments(global_view)
            
            # Get current active experiments to avoid overloading agents
            active_experiments = await self._get_active_experiments()
            agent_workloads = self._calculate_agent_workloads(active_experiments)
            
            experiment_assignments = []
            for design in experiment_designs:
                # Check if we can assign this experiment
                if len(active_experiments) >= self.max_concurrent_experiments:
                    break
                
                # Assign to each target agent
                for target_agent in design.target_agents:
                    # Check agent workload
                    if agent_workloads.get(target_agent, 0) >= 3:  # Max 3 experiments per agent
                        continue
                    
                    # Determine assignment type
                    assignment_type = self._determine_assignment_type(design, target_agent)
                    
                    # Create directives
                    directives = self._create_agent_directives(design, target_agent, assignment_type)
                    
                    # Define success criteria
                    success_criteria = self._define_success_criteria(design, target_agent)
                    
                    # Set reporting requirements
                    reporting_requirements = self._set_reporting_requirements(design, target_agent)
                    
                    # Calculate deadline
                    deadline = datetime.now(timezone.utc) + timedelta(hours=design.ttl_hours)
                    
                    # Create assignment
                    assignment = ExperimentAssignment(
                        assignment_id=f"ASSIGN_{int(datetime.now().timestamp())}_{len(experiment_assignments)}",
                        experiment_id=design.experiment_id,
                        target_agent=target_agent,
                        assignment_type=assignment_type,
                        directives=directives,
                        success_criteria=success_criteria,
                        reporting_requirements=reporting_requirements,
                        deadline=deadline
                    )
                    
                    experiment_assignments.append(assignment)
                    
                    # Update agent workload
                    agent_workloads[target_agent] = agent_workloads.get(target_agent, 0) + 1
            
            return experiment_assignments
            
        except Exception as e:
            print(f"Error assigning experiments: {e}")
            return []
    
    async def track_experiment_progress(self) -> List[Dict[str, Any]]:
        """
        Track progress of active experiments
        
        Returns:
            List of active experiment status updates
        """
        try:
            # Get active experiments from database
            query = """
                SELECT id, experiment_id, target_agent, assignment_type, deadline, created_at
                FROM AD_strands 
                WHERE kind = 'experiment_assignment' 
                AND module_intelligence->>'status' = 'active'
                AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [])
            
            active_experiments = []
            for row in result:
                # Check if experiment is still active
                deadline = row.get('deadline')
                if deadline and datetime.now(timezone.utc) > deadline:
                    # Mark as failed due to timeout
                    await self._mark_experiment_failed(row.get('experiment_id'), 'timeout')
                else:
                    active_experiments.append(row)
            
            return active_experiments
            
        except Exception as e:
            print(f"Error tracking experiment progress: {e}")
            return []
    
    async def process_experiment_results(self) -> List[ExperimentResult]:
        """
        Process completed experiment results
        
        Returns:
            List of ExperimentResult objects
        """
        try:
            # Get completed experiments from database
            query = """
                SELECT id, experiment_id, agent_id, module_intelligence, created_at
                FROM AD_strands 
                WHERE kind = 'experiment_result' 
                AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [])
            
            experiment_results = []
            for row in result:
                module_intel = row.get('module_intelligence', {})
                
                result_obj = ExperimentResult(
                    result_id=row.get('id'),
                    experiment_id=row.get('experiment_id'),
                    agent_id=row.get('agent_id'),
                    outcome=module_intel.get('outcome', 'unknown'),
                    metrics=module_intel.get('metrics', {}),
                    lessons_learned=module_intel.get('lessons_learned', []),
                    recommendations=module_intel.get('recommendations', []),
                    confidence_score=module_intel.get('confidence_score', 0.0),
                    completion_time=row.get('created_at')
                )
                
                experiment_results.append(result_obj)
            
            return experiment_results
            
        except Exception as e:
            print(f"Error processing experiment results: {e}")
            return []
    
    async def _generate_correlation_experiment_ideas(self, cross_agent_correlation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate experiment ideas from cross-agent correlations"""
        ideas = []
        
        # Check for high correlation strength
        correlation_strength = cross_agent_correlation.get('correlation_strength', 0.0)
        if correlation_strength > 0.7:
            ideas.append({
                'trigger': 'high_correlation_strength',
                'rationale': f'High cross-agent correlation detected ({correlation_strength:.2f})',
                'experiment_type': 'correlation_validation',
                'priority': 'high',
                'expected_conditions': {
                    'correlation_threshold': 0.7,
                    'min_sample_size': 20
                }
            })
        
        # Check for confluence events
        confluence_events = cross_agent_correlation.get('confluence_events', [])
        if len(confluence_events) > 3:
            ideas.append({
                'trigger': 'multiple_confluence_events',
                'rationale': f'Multiple confluence events detected ({len(confluence_events)})',
                'experiment_type': 'confluence_analysis',
                'priority': 'medium',
                'expected_conditions': {
                    'confluence_count': len(confluence_events),
                    'similarity_threshold': 0.8
                }
            })
        
        # Check for lead-lag patterns
        lead_lag_patterns = cross_agent_correlation.get('lead_lag_patterns', [])
        if lead_lag_patterns:
            ideas.append({
                'trigger': 'lead_lag_patterns',
                'rationale': f'Lead-lag patterns detected ({len(lead_lag_patterns)})',
                'experiment_type': 'lead_lag_validation',
                'priority': 'medium',
                'expected_conditions': {
                    'lead_lag_count': len(lead_lag_patterns),
                    'consistency_threshold': 0.6
                }
            })
        
        return ideas
    
    async def _generate_coverage_experiment_ideas(self, coverage_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate experiment ideas from coverage analysis"""
        ideas = []
        
        # Check for blind spots
        blind_spots = coverage_analysis.get('blind_spots', [])
        if blind_spots:
            ideas.append({
                'trigger': 'blind_spots_detected',
                'rationale': f'Blind spots identified ({len(blind_spots)})',
                'experiment_type': 'coverage_expansion',
                'priority': 'high',
                'expected_conditions': {
                    'blind_spot_count': len(blind_spots),
                    'coverage_threshold': 0.8
                }
            })
        
        # Check for coverage gaps
        coverage_gaps = coverage_analysis.get('coverage_gaps', [])
        if coverage_gaps:
            ideas.append({
                'trigger': 'coverage_gaps_detected',
                'rationale': f'Coverage gaps identified ({len(coverage_gaps)})',
                'experiment_type': 'gap_filling',
                'priority': 'medium',
                'expected_conditions': {
                    'gap_count': len(coverage_gaps),
                    'efficiency_threshold': 0.7
                }
            })
        
        return ideas
    
    async def _generate_family_experiment_ideas(self, signal_families: List[Any]) -> List[Dict[str, Any]]:
        """Generate experiment ideas from signal families"""
        ideas = []
        
        for family in signal_families:
            if hasattr(family, 'family_strength'):
                # Check for strong families that need durability testing
                if family.family_strength > 0.8:
                    ideas.append({
                        'trigger': 'strong_family_durability',
                        'rationale': f'Strong family {family.family_name} needs durability testing',
                        'experiment_type': 'durability_test',
                        'priority': 'medium',
                        'expected_conditions': {
                            'family_name': family.family_name,
                            'strength_threshold': 0.8
                        }
                    })
                
                # Check for declining families
                if hasattr(family, 'evolution_trend') and family.evolution_trend == 'declining':
                    ideas.append({
                        'trigger': 'declining_family',
                        'rationale': f'Family {family.family_name} is declining',
                        'experiment_type': 'decline_analysis',
                        'priority': 'high',
                        'expected_conditions': {
                            'family_name': family.family_name,
                            'trend': 'declining'
                        }
                    })
        
        return ideas
    
    async def _generate_pattern_experiment_ideas(self, meta_patterns: List[Any]) -> List[Dict[str, Any]]:
        """Generate experiment ideas from meta-patterns"""
        ideas = []
        
        for pattern in meta_patterns:
            if hasattr(pattern, 'strength_score'):
                # Check for strong patterns that need validation
                if pattern.strength_score > 0.8:
                    ideas.append({
                        'trigger': 'strong_meta_pattern',
                        'rationale': f'Strong meta-pattern {pattern.pattern_name} needs validation',
                        'experiment_type': 'pattern_validation',
                        'priority': 'high',
                        'expected_conditions': {
                            'pattern_name': pattern.pattern_name,
                            'strength_threshold': 0.8
                        }
                    })
        
        return ideas
    
    async def _generate_doctrine_experiment_ideas(self, doctrine_insights: List[Any]) -> List[Dict[str, Any]]:
        """Generate experiment ideas from doctrine insights"""
        ideas = []
        
        for insight in doctrine_insights:
            if hasattr(insight, 'confidence_level'):
                # Check for high-confidence insights that need testing
                if insight.confidence_level > 0.8:
                    ideas.append({
                        'trigger': 'high_confidence_insight',
                        'rationale': f'High-confidence insight: {insight.insight_type}',
                        'experiment_type': 'insight_validation',
                        'priority': 'medium',
                        'expected_conditions': {
                            'insight_type': insight.insight_type,
                            'confidence_threshold': 0.8
                        }
                    })
        
        return ideas
    
    async def _create_experiment_hypothesis(self, idea: Dict[str, Any]) -> ExperimentHypothesis:
        """Create experiment hypothesis from idea"""
        hypothesis_id = f"HYP_{int(datetime.now().timestamp())}"
        
        # Generate hypothesis text based on idea
        trigger = idea.get('trigger', 'unknown')
        rationale = idea.get('rationale', 'No rationale provided')
        
        hypothesis_text = f"If {trigger}, then {rationale}"
        
        # Set expected conditions
        expected_conditions = idea.get('expected_conditions', {})
        
        # Define success metrics
        success_metrics = {
            'accuracy': 0.8,
            'precision': 0.7,
            'recall': 0.7,
            'f1_score': 0.7
        }
        
        # Set time horizon
        time_horizon = "24_hours"
        
        # Calculate confidence level
        confidence_level = 0.7  # Placeholder - would be calculated based on evidence
        
        # Set evidence basis
        evidence_basis = [rationale]
        
        return ExperimentHypothesis(
            hypothesis_id=hypothesis_id,
            hypothesis_text=hypothesis_text,
            expected_conditions=expected_conditions,
            success_metrics=success_metrics,
            time_horizon=time_horizon,
            confidence_level=confidence_level,
            evidence_basis=evidence_basis
        )
    
    def _determine_experiment_shape(self, idea: Dict[str, Any]) -> ExperimentShape:
        """Determine experiment shape from idea"""
        experiment_type = idea.get('experiment_type', 'unknown')
        
        if 'durability' in experiment_type:
            return ExperimentShape.DURABILITY
        elif 'confluence' in experiment_type or 'correlation' in experiment_type:
            return ExperimentShape.STACK
        elif 'lead_lag' in experiment_type:
            return ExperimentShape.LEAD_LAG
        elif 'decline' in experiment_type or 'ablation' in experiment_type:
            return ExperimentShape.ABLATION
        elif 'boundary' in experiment_type or 'gap' in experiment_type:
            return ExperimentShape.BOUNDARY
        else:
            return ExperimentShape.DURABILITY  # Default
    
    def _select_target_agents(self, idea: Dict[str, Any], hypothesis: ExperimentHypothesis) -> List[str]:
        """Select target agents for experiment"""
        experiment_type = idea.get('experiment_type', 'unknown')
        
        # Select agents based on experiment type and capabilities
        if 'divergence' in experiment_type or 'volume' in experiment_type:
            return ['raw_data_intelligence']
        elif 'rsi' in experiment_type or 'macd' in experiment_type or 'bollinger' in experiment_type:
            return ['indicator_intelligence']
        elif 'pattern' in experiment_type or 'composite' in experiment_type:
            return ['pattern_intelligence']
        elif 'parameter' in experiment_type or 'optimization' in experiment_type:
            return ['system_control']
        else:
            # Default to multiple agents for complex experiments
            return ['raw_data_intelligence', 'indicator_intelligence']
    
    def _design_parameter_sweeps(self, idea: Dict[str, Any], hypothesis: ExperimentHypothesis) -> Dict[str, List[Any]]:
        """Design parameter sweeps for experiment"""
        parameter_sweeps = {}
        
        experiment_type = idea.get('experiment_type', 'unknown')
        
        if 'divergence' in experiment_type:
            parameter_sweeps = {
                'rsi_period': [14, 21, 28],
                'divergence_threshold': [0.1, 0.2, 0.3],
                'lookback_period': [5, 10, 15]
            }
        elif 'volume' in experiment_type:
            parameter_sweeps = {
                'volume_threshold': [1.5, 2.0, 2.5],
                'time_window': [5, 10, 15],
                'smoothing_period': [3, 5, 7]
            }
        elif 'correlation' in experiment_type:
            parameter_sweeps = {
                'correlation_threshold': [0.6, 0.7, 0.8],
                'time_window': [60, 120, 240],
                'min_sample_size': [10, 20, 30]
            }
        else:
            # Default parameter sweeps
            parameter_sweeps = {
                'threshold': [0.5, 0.7, 0.9],
                'window': [10, 20, 30],
                'confidence': [0.6, 0.8, 0.9]
            }
        
        return parameter_sweeps
    
    def _set_experiment_guardrails(self, idea: Dict[str, Any], hypothesis: ExperimentHypothesis) -> Dict[str, Any]:
        """Set experiment guardrails"""
        return {
            'max_runtime_hours': self.experiment_timeout_hours,
            'min_sample_size': self.min_sample_size,
            'max_false_positive_rate': 0.3,
            'min_confidence_threshold': 0.6,
            'stop_on_anomaly': True,
            'max_memory_usage_mb': 1000
        }
    
    def _define_tracking_requirements(self, idea: Dict[str, Any], hypothesis: ExperimentHypothesis) -> List[str]:
        """Define tracking requirements for experiment"""
        return [
            'performance_metrics',
            'confidence_scores',
            'false_positive_rate',
            'execution_time',
            'resource_usage',
            'anomaly_detection',
            'lesson_learned'
        ]
    
    def _calculate_priority_score(self, idea: Dict[str, Any], hypothesis: ExperimentHypothesis) -> float:
        """Calculate priority score for experiment"""
        priority = idea.get('priority', 'medium')
        confidence_level = hypothesis.confidence_level
        
        priority_weights = {
            'high': 0.9,
            'medium': 0.6,
            'low': 0.3
        }
        
        base_priority = priority_weights.get(priority, 0.6)
        
        # Adjust based on confidence level
        adjusted_priority = base_priority * confidence_level
        
        return min(adjusted_priority, 1.0)
    
    async def _get_active_experiments(self) -> List[Dict[str, Any]]:
        """Get currently active experiments"""
        query = """
            SELECT id, experiment_id, target_agent, created_at
            FROM AD_strands 
            WHERE kind = 'experiment_assignment' 
            AND module_intelligence->>'status' = 'active'
            AND created_at > NOW() - INTERVAL '24 hours'
        """
        
        result = await self.supabase_manager.execute_query(query, [])
        return result
    
    def _calculate_agent_workloads(self, active_experiments: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate current agent workloads"""
        workloads = {}
        
        for experiment in active_experiments:
            agent = experiment.get('target_agent', 'unknown')
            workloads[agent] = workloads.get(agent, 0) + 1
        
        return workloads
    
    def _determine_assignment_type(self, design: ExperimentDesign, target_agent: str) -> str:
        """Determine assignment type for agent"""
        # Check agent capabilities
        agent_caps = self.agent_capabilities.get(target_agent, [])
        
        # Determine assignment type based on experiment complexity
        if design.shape in [ExperimentShape.DURABILITY, ExperimentShape.BOUNDARY]:
            return "strict"
        elif design.shape in [ExperimentShape.STACK, ExperimentShape.LEAD_LAG]:
            return "bounded"
        else:
            return "exploratory"
    
    def _create_agent_directives(self, design: ExperimentDesign, target_agent: str, assignment_type: str) -> Dict[str, Any]:
        """Create directives for agent"""
        return {
            'experiment_id': design.experiment_id,
            'hypothesis': design.hypothesis.hypothesis_text,
            'shape': design.shape.value,
            'parameter_sweeps': design.parameter_sweeps,
            'assignment_type': assignment_type,
            'guardrails': design.guardrails,
            'tracking_requirements': design.tracking_requirements,
            'ttl_hours': design.ttl_hours
        }
    
    def _define_success_criteria(self, design: ExperimentDesign, target_agent: str) -> Dict[str, float]:
        """Define success criteria for agent"""
        return {
            'min_accuracy': design.hypothesis.success_metrics.get('accuracy', 0.8),
            'min_precision': design.hypothesis.success_metrics.get('precision', 0.7),
            'min_recall': design.hypothesis.success_metrics.get('recall', 0.7),
            'max_false_positive_rate': 0.3,
            'min_confidence': 0.6
        }
    
    def _set_reporting_requirements(self, design: ExperimentDesign, target_agent: str) -> List[str]:
        """Set reporting requirements for agent"""
        return [
            'experiment_progress',
            'intermediate_results',
            'anomaly_reports',
            'final_results',
            'lessons_learned',
            'recommendations'
        ]
    
    async def _mark_experiment_failed(self, experiment_id: str, reason: str):
        """Mark experiment as failed"""
        try:
            # Update experiment status in database
            update_data = {
                'module_intelligence': {
                    'status': 'failed',
                    'failure_reason': reason,
                    'failed_at': datetime.now(timezone.utc).isoformat()
                }
            }
            
            # This would typically update the database record
            # For now, we'll just log it
            print(f"Experiment {experiment_id} marked as failed: {reason}")
            
        except Exception as e:
            print(f"Error marking experiment as failed: {e}")
    
    async def _publish_orchestration_results(self, orchestration_results: Dict[str, Any]):
        """Publish orchestration results as CIL strand"""
        try:
            # Create CIL orchestration strand
            cil_strand = {
                'id': f"cil_experiment_orchestration_{int(datetime.now().timestamp())}",
                'kind': 'cil_experiment_orchestration',
                'module': 'alpha',
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'experiment_orchestration_engine',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'session_bucket': 'GLOBAL',
                'regime': 'system',
                'tags': ['agent:central_intelligence:experiment_orchestration_engine:orchestration_complete'],
                'module_intelligence': {
                    'orchestration_type': 'experiment_orchestration',
                    'experiment_ideas_count': len(orchestration_results.get('experiment_ideas', [])),
                    'experiment_designs_count': len(orchestration_results.get('experiment_designs', [])),
                    'experiment_assignments_count': len(orchestration_results.get('experiment_assignments', [])),
                    'active_experiments_count': len(orchestration_results.get('active_experiments', [])),
                    'completed_experiments_count': len(orchestration_results.get('completed_experiments', [])),
                    'orchestration_errors': orchestration_results.get('orchestration_errors', [])
                },
                'sig_sigma': 1.0,
                'sig_confidence': 1.0,
                'sig_direction': 'neutral',
                'outcome_score': 1.0,
                'created_at': datetime.now(timezone.utc)
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing orchestration results: {e}")


# Example usage and testing
async def main():
    """Example usage of ExperimentOrchestrationEngine"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create experiment orchestration engine
    orchestration_engine = ExperimentOrchestrationEngine(supabase_manager, llm_client)
    
    # Mock global view
    global_view = {
        'cross_agent_correlation': {'correlation_strength': 0.8},
        'coverage_analysis': {'blind_spots': [], 'coverage_gaps': []},
        'signal_families': [],
        'meta_patterns': [],
        'doctrine_insights': []
    }
    
    # Orchestrate experiments
    orchestration_results = await orchestration_engine.orchestrate_experiments(global_view)
    
    print("CIL Experiment Orchestration Results:")
    print(f"Experiment Ideas: {len(orchestration_results.get('experiment_ideas', []))}")
    print(f"Experiment Designs: {len(orchestration_results.get('experiment_designs', []))}")
    print(f"Experiment Assignments: {len(orchestration_results.get('experiment_assignments', []))}")
    print(f"Active Experiments: {len(orchestration_results.get('active_experiments', []))}")
    print(f"Completed Experiments: {len(orchestration_results.get('completed_experiments', []))}")


if __name__ == "__main__":
    asyncio.run(main())
