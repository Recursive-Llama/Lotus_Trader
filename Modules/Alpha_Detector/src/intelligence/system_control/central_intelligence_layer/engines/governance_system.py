"""
CIL Governance System
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class DecisionOwnership(Enum):
    """Decision ownership levels"""
    CIL_OWNED = "cil_owned"
    AGENT_OWNED = "agent_owned"
    SHARED = "shared"
    HUMAN_OVERRIDE = "human_override"


class ConflictType(Enum):
    """Types of conflicts that can occur"""
    OVERLAP = "overlap"
    BUDGET_CONTENTION = "budget_contention"
    CONTRADICTION = "contradiction"
    RESOURCE_CONFLICT = "resource_conflict"
    PRIORITY_CONFLICT = "priority_conflict"


class ResolutionStrategy(Enum):
    """Conflict resolution strategies"""
    CIL_ARBITRATION = "cil_arbitration"
    AGENT_NEGOTIATION = "agent_negotiation"
    HUMAN_INTERVENTION = "human_intervention"
    AUTOMATIC_RESOLUTION = "automatic_resolution"
    ESCALATION = "escalation"


class AutonomyLimit(Enum):
    """Autonomy limit types"""
    GOAL_REDEFINITION = "goal_redefinition"
    BEACON_IGNORANCE = "beacon_ignorance"
    LESSON_FORMAT_VIOLATION = "lesson_format_violation"
    RESOURCE_OVERRUN = "resource_overrun"
    SAFETY_VIOLATION = "safety_violation"


@dataclass
class DecisionBoundary:
    """Boundary definition for decision ownership"""
    decision_type: str
    ownership: DecisionOwnership
    description: str
    constraints: List[str]
    escalation_triggers: List[str]
    created_at: datetime


@dataclass
class ConflictResolution:
    """Conflict resolution record"""
    conflict_id: str
    conflict_type: ConflictType
    involved_agents: List[str]
    conflict_description: str
    resolution_strategy: ResolutionStrategy
    resolution_details: Dict[str, Any]
    resolution_outcome: str
    resolved_at: datetime
    created_at: datetime


@dataclass
class AutonomyViolation:
    """Autonomy limit violation record"""
    violation_id: str
    agent_id: str
    violation_type: AutonomyLimit
    violation_description: str
    severity: str
    corrective_action: str
    resolved: bool
    created_at: datetime


@dataclass
class HumanOverride:
    """Human override record"""
    override_id: str
    override_type: str
    target_agent: str
    override_reason: str
    override_details: Dict[str, Any]
    override_duration: Optional[timedelta]
    created_by: str
    created_at: datetime


@dataclass
class SystemResilienceCheck:
    """System resilience check record"""
    check_id: str
    check_type: str
    check_result: str
    resilience_score: float
    recommendations: List[str]
    action_required: bool
    created_at: datetime


class GovernanceSystem:
    """CIL Governance System - Section 8"""
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Configuration
        self.conflict_resolution_timeout_minutes = 30
        self.autonomy_violation_threshold = 3
        self.resilience_check_interval_hours = 6
        self.human_override_cooldown_hours = 24
        self.escalation_threshold = 0.8
        
        # Decision boundaries
        self.decision_boundaries = self._initialize_decision_boundaries()
        
        # Governance state
        self.active_conflicts = {}
        self.autonomy_violations = {}
        self.human_overrides = {}
        self.resilience_checks = {}
    
    def _initialize_decision_boundaries(self) -> List[DecisionBoundary]:
        """Initialize decision boundaries"""
        boundaries = [
            DecisionBoundary(
                decision_type="global_view",
                ownership=DecisionOwnership.CIL_OWNED,
                description="CIL owns the global view of all signals and patterns",
                constraints=["agents_cannot_modify_global_view", "cil_has_final_authority"],
                escalation_triggers=["agent_challenges_global_view", "contradictory_evidence"],
                created_at=datetime.now(timezone.utc)
            ),
            DecisionBoundary(
                decision_type="hypothesis_framing",
                ownership=DecisionOwnership.CIL_OWNED,
                description="CIL owns hypothesis framing and experiment orchestration",
                constraints=["agents_cannot_create_own_hypotheses", "cil_assigns_experiments"],
                escalation_triggers=["agent_creates_unauthorized_hypothesis", "experiment_assignment_conflict"],
                created_at=datetime.now(timezone.utc)
            ),
            DecisionBoundary(
                decision_type="doctrine_updates",
                ownership=DecisionOwnership.CIL_OWNED,
                description="CIL owns doctrine updates and system-wide learning",
                constraints=["agents_cannot_modify_doctrine", "cil_curates_knowledge"],
                escalation_triggers=["agent_modifies_doctrine", "doctrine_conflict"],
                created_at=datetime.now(timezone.utc)
            ),
            DecisionBoundary(
                decision_type="local_tactics",
                ownership=DecisionOwnership.AGENT_OWNED,
                description="Agents own local tactics, parameter choices, and micro-hypotheses",
                constraints=["cil_cannot_micromanage_tactics", "agents_have_tactical_autonomy"],
                escalation_triggers=["cil_micromanages_tactics", "tactical_conflict"],
                created_at=datetime.now(timezone.utc)
            ),
            DecisionBoundary(
                decision_type="experiment_execution",
                ownership=DecisionOwnership.AGENT_OWNED,
                description="Agents own execution of assigned experiments",
                constraints=["cil_cannot_execute_experiments", "agents_own_execution_methods"],
                escalation_triggers=["cil_interferes_with_execution", "execution_conflict"],
                created_at=datetime.now(timezone.utc)
            ),
            DecisionBoundary(
                decision_type="lesson_reporting",
                ownership=DecisionOwnership.AGENT_OWNED,
                description="Agents own reporting structured lessons from outcomes",
                constraints=["agents_must_report_lessons", "cil_cannot_fabricate_lessons"],
                escalation_triggers=["agent_fails_to_report", "lesson_format_violation"],
                created_at=datetime.now(timezone.utc)
            )
        ]
        return boundaries
    
    async def process_governance(self, global_synthesis_results: Dict[str, Any],
                               experiment_results: Dict[str, Any],
                               learning_feedback_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process governance decisions and conflicts"""
        try:
            # Check for conflicts
            conflicts = await self._detect_conflicts(
                global_synthesis_results, experiment_results, learning_feedback_results
            )
            
            # Resolve conflicts
            conflict_resolutions = await self._resolve_conflicts(conflicts)
            
            # Check autonomy limits
            autonomy_violations = await self._check_autonomy_limits(
                global_synthesis_results, experiment_results
            )
            
            # Process human overrides
            human_overrides = await self._process_human_overrides()
            
            # Check system resilience
            resilience_checks = await self._check_system_resilience(
                global_synthesis_results, learning_feedback_results
            )
            
            # Compile results
            results = {
                'conflicts_detected': conflicts,
                'conflict_resolutions': conflict_resolutions,
                'autonomy_violations': autonomy_violations,
                'human_overrides': human_overrides,
                'resilience_checks': resilience_checks,
                'governance_timestamp': datetime.now(timezone.utc),
                'governance_errors': []
            }
            
            # Publish results
            await self._publish_governance_results(results)
            
            return results
            
        except Exception as e:
            print(f"Error processing governance: {e}")
            return {
                'conflicts_detected': [],
                'conflict_resolutions': [],
                'autonomy_violations': [],
                'human_overrides': [],
                'resilience_checks': [],
                'governance_timestamp': datetime.now(timezone.utc),
                'governance_errors': [str(e)]
            }
    
    async def _detect_conflicts(self, global_synthesis_results: Dict[str, Any],
                              experiment_results: Dict[str, Any],
                              learning_feedback_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect conflicts in the system"""
        conflicts = []
        
        # Check for overlaps
        overlaps = await self._detect_overlaps(global_synthesis_results)
        conflicts.extend(overlaps)
        
        # Check for budget contention
        budget_conflicts = await self._detect_budget_contention(experiment_results)
        conflicts.extend(budget_conflicts)
        
        # Check for contradictions
        contradictions = await self._detect_contradictions(learning_feedback_results)
        conflicts.extend(contradictions)
        
        # Check for resource conflicts
        resource_conflicts = await self._detect_resource_conflicts(experiment_results)
        conflicts.extend(resource_conflicts)
        
        # Check for priority conflicts
        priority_conflicts = await self._detect_priority_conflicts(global_synthesis_results)
        conflicts.extend(priority_conflicts)
        
        return conflicts
    
    async def _detect_overlaps(self, global_synthesis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect overlapping agent activities"""
        overlaps = []
        
        # Check for redundant experiments
        experiment_ideas = global_synthesis_results.get('experiment_ideas', [])
        for i, idea1 in enumerate(experiment_ideas):
            for j, idea2 in enumerate(experiment_ideas[i+1:], i+1):
                if await self._are_experiments_overlapping(idea1, idea2):
                    overlap = {
                        'conflict_id': f"OVERLAP_{int(datetime.now().timestamp())}",
                        'conflict_type': ConflictType.OVERLAP.value,
                        'involved_agents': [idea1.get('target_agent', 'unknown'), idea2.get('target_agent', 'unknown')],
                        'conflict_description': f"Overlapping experiments: {idea1.get('hypothesis', '')} vs {idea2.get('hypothesis', '')}",
                        'severity': 'medium',
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    overlaps.append(overlap)
        
        return overlaps
    
    async def _are_experiments_overlapping(self, idea1: Dict[str, Any], idea2: Dict[str, Any]) -> bool:
        """Check if two experiments are overlapping"""
        # Check if they target the same family
        if idea1.get('family') == idea2.get('family'):
            return True
        
        # Check if they have similar conditions
        conditions1 = idea1.get('conditions', {})
        conditions2 = idea2.get('conditions', {})
        
        # Check for regime overlap
        if conditions1.get('regime') == conditions2.get('regime'):
            return True
        
        # Check for session overlap
        if conditions1.get('session') == conditions2.get('session'):
            return True
        
        return False
    
    async def _detect_budget_contention(self, experiment_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect budget contention conflicts"""
        conflicts = []
        
        # Check for exploration budget conflicts
        active_experiments = experiment_results.get('active_experiments', [])
        total_budget = 1.0
        used_budget = sum(exp.get('budget_allocation', 0) for exp in active_experiments)
        
        if used_budget > total_budget:
            conflict = {
                'conflict_id': f"BUDGET_{int(datetime.now().timestamp())}",
                'conflict_type': ConflictType.BUDGET_CONTENTION.value,
                'involved_agents': [exp.get('agent_id', 'unknown') for exp in active_experiments],
                'conflict_description': f"Budget overrun: {used_budget:.2f} > {total_budget:.2f}",
                'severity': 'high',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            conflicts.append(conflict)
        
        return conflicts
    
    async def _detect_contradictions(self, learning_feedback_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect contradictory results"""
        conflicts = []
        
        # Check for contradictory lessons
        lessons = learning_feedback_results.get('lessons', [])
        for i, lesson1 in enumerate(lessons):
            for j, lesson2 in enumerate(lessons[i+1:], i+1):
                if await self._are_lessons_contradictory(lesson1, lesson2):
                    conflict = {
                        'conflict_id': f"CONTRADICTION_{int(datetime.now().timestamp())}",
                        'conflict_type': ConflictType.CONTRADICTION.value,
                        'involved_agents': [lesson1.get('source_agent', 'unknown'), lesson2.get('source_agent', 'unknown')],
                        'conflict_description': f"Contradictory lessons: {lesson1.get('outcome', '')} vs {lesson2.get('outcome', '')}",
                        'severity': 'high',
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    conflicts.append(conflict)
        
        return conflicts
    
    async def _are_lessons_contradictory(self, lesson1: Dict[str, Any], lesson2: Dict[str, Any]) -> bool:
        """Check if two lessons are contradictory"""
        # Check if they have opposite outcomes
        outcome1 = lesson1.get('outcome', '')
        outcome2 = lesson2.get('outcome', '')
        
        if (outcome1 == 'success' and outcome2 == 'failure') or (outcome1 == 'failure' and outcome2 == 'success'):
            # Check if they target similar patterns
            pattern1 = lesson1.get('pattern_family', '')
            pattern2 = lesson2.get('pattern_family', '')
            
            if pattern1 == pattern2:
                return True
        
        return False
    
    async def _detect_resource_conflicts(self, experiment_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect resource conflicts"""
        conflicts = []
        
        # Check for concurrent experiment conflicts
        active_experiments = experiment_results.get('active_experiments', [])
        
        # Group experiments by resource type
        resource_groups = {}
        for exp in active_experiments:
            resource_type = exp.get('resource_type', 'general')
            if resource_type not in resource_groups:
                resource_groups[resource_type] = []
            resource_groups[resource_type].append(exp)
        
        # Check for conflicts within each resource group
        for resource_type, experiments in resource_groups.items():
            if len(experiments) > 1:
                conflict = {
                    'conflict_id': f"RESOURCE_{int(datetime.now().timestamp())}",
                    'conflict_type': ConflictType.RESOURCE_CONFLICT.value,
                    'involved_agents': [exp.get('agent_id', 'unknown') for exp in experiments],
                    'conflict_description': f"Resource conflict on {resource_type}: {len(experiments)} concurrent experiments",
                    'severity': 'medium',
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                conflicts.append(conflict)
        
        return conflicts
    
    async def _detect_priority_conflicts(self, global_synthesis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect priority conflicts"""
        conflicts = []
        
        # Check for conflicting priorities in experiment ideas
        experiment_ideas = global_synthesis_results.get('experiment_ideas', [])
        
        # Group by priority
        priority_groups = {}
        for idea in experiment_ideas:
            priority = idea.get('priority', 'medium')
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(idea)
        
        # Check for too many high priority items
        high_priority = priority_groups.get('high', [])
        if len(high_priority) > 3:  # Arbitrary threshold
            conflict = {
                'conflict_id': f"PRIORITY_{int(datetime.now().timestamp())}",
                'conflict_type': ConflictType.PRIORITY_CONFLICT.value,
                'involved_agents': [idea.get('target_agent', 'unknown') for idea in high_priority],
                'conflict_description': f"Too many high priority experiments: {len(high_priority)}",
                'severity': 'medium',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            conflicts.append(conflict)
        
        return conflicts
    
    async def _resolve_conflicts(self, conflicts: List[Dict[str, Any]]) -> List[ConflictResolution]:
        """Resolve detected conflicts"""
        resolutions = []
        
        for conflict in conflicts:
            resolution = await self._resolve_single_conflict(conflict)
            if resolution:
                resolutions.append(resolution)
        
        return resolutions
    
    async def _resolve_single_conflict(self, conflict: Dict[str, Any]) -> Optional[ConflictResolution]:
        """Resolve a single conflict"""
        try:
            conflict_type = ConflictType(conflict['conflict_type'])
            involved_agents = conflict['involved_agents']
            severity = conflict.get('severity', 'medium')
            
            # Determine resolution strategy
            if severity == 'high':
                resolution_strategy = ResolutionStrategy.CIL_ARBITRATION
            elif len(involved_agents) == 2:
                resolution_strategy = ResolutionStrategy.AGENT_NEGOTIATION
            else:
                resolution_strategy = ResolutionStrategy.AUTOMATIC_RESOLUTION
            
            # Generate resolution details
            resolution_details = await self._generate_resolution_details(conflict, resolution_strategy)
            
            # Create resolution record
            resolution = ConflictResolution(
                conflict_id=conflict['conflict_id'],
                conflict_type=conflict_type,
                involved_agents=involved_agents,
                conflict_description=conflict['conflict_description'],
                resolution_strategy=resolution_strategy,
                resolution_details=resolution_details,
                resolution_outcome='resolved',
                resolved_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            
            return resolution
            
        except Exception as e:
            print(f"Error resolving conflict: {e}")
            return None
    
    async def _generate_resolution_details(self, conflict: Dict[str, Any], 
                                         strategy: ResolutionStrategy) -> Dict[str, Any]:
        """Generate resolution details based on strategy"""
        if strategy == ResolutionStrategy.CIL_ARBITRATION:
            return {
                'action': 'cil_arbitration',
                'decision': 'cil_makes_final_decision',
                'rationale': 'High severity conflict requires CIL intervention',
                'enforcement': 'mandatory'
            }
        elif strategy == ResolutionStrategy.AGENT_NEGOTIATION:
            return {
                'action': 'agent_negotiation',
                'decision': 'agents_negotiate_solution',
                'rationale': 'Two agents can negotiate a solution',
                'enforcement': 'voluntary'
            }
        elif strategy == ResolutionStrategy.AUTOMATIC_RESOLUTION:
            return {
                'action': 'automatic_resolution',
                'decision': 'system_automatically_resolves',
                'rationale': 'Low severity conflict can be automatically resolved',
                'enforcement': 'automatic'
            }
        else:
            return {
                'action': 'escalation',
                'decision': 'escalate_to_human',
                'rationale': 'Complex conflict requires human intervention',
                'enforcement': 'human_required'
            }
    
    async def _check_autonomy_limits(self, global_synthesis_results: Dict[str, Any],
                                   experiment_results: Dict[str, Any]) -> List[AutonomyViolation]:
        """Check for autonomy limit violations"""
        violations = []
        
        # Check for goal redefinition violations
        goal_violations = await self._check_goal_redefinition_violations(experiment_results)
        violations.extend(goal_violations)
        
        # Check for beacon ignorance violations
        beacon_violations = await self._check_beacon_ignorance_violations(global_synthesis_results)
        violations.extend(beacon_violations)
        
        # Check for lesson format violations
        format_violations = await self._check_lesson_format_violations(experiment_results)
        violations.extend(format_violations)
        
        # Check for resource overrun violations
        resource_violations = await self._check_resource_overrun_violations(experiment_results)
        violations.extend(resource_violations)
        
        # Check for safety violations
        safety_violations = await self._check_safety_violations(experiment_results)
        violations.extend(safety_violations)
        
        return violations
    
    async def _check_goal_redefinition_violations(self, experiment_results: Dict[str, Any]) -> List[AutonomyViolation]:
        """Check for goal redefinition violations"""
        violations = []
        
        # Check if any agent is trying to redefine the master goal
        active_experiments = experiment_results.get('active_experiments', [])
        
        for exp in active_experiments:
            if exp.get('goal_redefinition_attempt', False):
                violation = AutonomyViolation(
                    violation_id=f"GOAL_VIOLATION_{int(datetime.now().timestamp())}",
                    agent_id=exp.get('agent_id', 'unknown'),
                    violation_type=AutonomyLimit.GOAL_REDEFINITION,
                    violation_description="Agent attempted to redefine master goal",
                    severity='high',
                    corrective_action='block_goal_redefinition',
                    resolved=False,
                    created_at=datetime.now(timezone.utc)
                )
                violations.append(violation)
        
        return violations
    
    async def _check_beacon_ignorance_violations(self, global_synthesis_results: Dict[str, Any]) -> List[AutonomyViolation]:
        """Check for beacon ignorance violations"""
        violations = []
        
        # Check if agents are ignoring CIL beacons
        experiment_ideas = global_synthesis_results.get('experiment_ideas', [])
        
        for idea in experiment_ideas:
            if idea.get('ignores_beacon', False):
                violation = AutonomyViolation(
                    violation_id=f"BEACON_VIOLATION_{int(datetime.now().timestamp())}",
                    agent_id=idea.get('target_agent', 'unknown'),
                    violation_type=AutonomyLimit.BEACON_IGNORANCE,
                    violation_description="Agent ignored CIL beacon directive",
                    severity='medium',
                    corrective_action='enforce_beacon_compliance',
                    resolved=False,
                    created_at=datetime.now(timezone.utc)
                )
                violations.append(violation)
        
        return violations
    
    async def _check_lesson_format_violations(self, experiment_results: Dict[str, Any]) -> List[AutonomyViolation]:
        """Check for lesson format violations"""
        violations = []
        
        # Check if agents are not following lesson format requirements
        active_experiments = experiment_results.get('active_experiments', [])
        
        for exp in active_experiments:
            if exp.get('lesson_format_violation', False):
                violation = AutonomyViolation(
                    violation_id=f"FORMAT_VIOLATION_{int(datetime.now().timestamp())}",
                    agent_id=exp.get('agent_id', 'unknown'),
                    violation_type=AutonomyLimit.LESSON_FORMAT_VIOLATION,
                    violation_description="Agent violated lesson format requirements",
                    severity='low',
                    corrective_action='enforce_lesson_format',
                    resolved=False,
                    created_at=datetime.now(timezone.utc)
                )
                violations.append(violation)
        
        return violations
    
    async def _check_resource_overrun_violations(self, experiment_results: Dict[str, Any]) -> List[AutonomyViolation]:
        """Check for resource overrun violations"""
        violations = []
        
        # Check if agents are overrunning resource limits
        active_experiments = experiment_results.get('active_experiments', [])
        
        for exp in active_experiments:
            if exp.get('resource_overrun', False):
                violation = AutonomyViolation(
                    violation_id=f"RESOURCE_VIOLATION_{int(datetime.now().timestamp())}",
                    agent_id=exp.get('agent_id', 'unknown'),
                    violation_type=AutonomyLimit.RESOURCE_OVERRUN,
                    violation_description="Agent overran resource limits",
                    severity='medium',
                    corrective_action='enforce_resource_limits',
                    resolved=False,
                    created_at=datetime.now(timezone.utc)
                )
                violations.append(violation)
        
        return violations
    
    async def _check_safety_violations(self, experiment_results: Dict[str, Any]) -> List[AutonomyViolation]:
        """Check for safety violations"""
        violations = []
        
        # Check if agents are violating safety constraints
        active_experiments = experiment_results.get('active_experiments', [])
        
        for exp in active_experiments:
            if exp.get('safety_violation', False):
                violation = AutonomyViolation(
                    violation_id=f"SAFETY_VIOLATION_{int(datetime.now().timestamp())}",
                    agent_id=exp.get('agent_id', 'unknown'),
                    violation_type=AutonomyLimit.SAFETY_VIOLATION,
                    violation_description="Agent violated safety constraints",
                    severity='critical',
                    corrective_action='immediate_safety_stop',
                    resolved=False,
                    created_at=datetime.now(timezone.utc)
                )
                violations.append(violation)
        
        return violations
    
    async def _process_human_overrides(self) -> List[HumanOverride]:
        """Process human overrides"""
        overrides = []
        
        # Check for pending human overrides
        pending_overrides = await self._get_pending_human_overrides()
        
        for override_data in pending_overrides:
            override = HumanOverride(
                override_id=override_data.get('override_id', f"OVERRIDE_{int(datetime.now().timestamp())}"),
                override_type=override_data.get('override_type', 'general'),
                target_agent=override_data.get('target_agent', 'unknown'),
                override_reason=override_data.get('override_reason', 'human_intervention'),
                override_details=override_data.get('override_details', {}),
                override_duration=override_data.get('override_duration'),
                created_by=override_data.get('created_by', 'human'),
                created_at=datetime.now(timezone.utc)
            )
            overrides.append(override)
        
        return overrides
    
    async def _get_pending_human_overrides(self) -> List[Dict[str, Any]]:
        """Get pending human overrides from database"""
        # Mock implementation - in real system, query database
        return []
    
    async def _check_system_resilience(self, global_synthesis_results: Dict[str, Any],
                                     learning_feedback_results: Dict[str, Any]) -> List[SystemResilienceCheck]:
        """Check system resilience"""
        checks = []
        
        # Check for runaway experiments
        runaway_check = await self._check_runaway_experiments(global_synthesis_results)
        checks.append(runaway_check)
        
        # Check for local bias
        bias_check = await self._check_local_bias(learning_feedback_results)
        checks.append(bias_check)
        
        # Check for system stability
        stability_check = await self._check_system_stability(global_synthesis_results)
        checks.append(stability_check)
        
        return checks
    
    async def _check_runaway_experiments(self, global_synthesis_results: Dict[str, Any]) -> SystemResilienceCheck:
        """Check for runaway experiments"""
        experiment_ideas = global_synthesis_results.get('experiment_ideas', [])
        
        # Check for too many false positives
        false_positive_count = sum(1 for idea in experiment_ideas if idea.get('false_positive_rate', 0) > 0.5)
        
        if false_positive_count > 3:
            result = 'failed'
            score = 0.3
            recommendations = ['Implement stop rules', 'Reduce experiment frequency', 'Increase success thresholds']
            action_required = True
        else:
            result = 'passed'
            score = 0.8
            recommendations = ['Continue monitoring', 'Maintain current thresholds']
            action_required = False
        
        return SystemResilienceCheck(
            check_id=f"RUNAWAY_CHECK_{int(datetime.now().timestamp())}",
            check_type='runaway_experiments',
            check_result=result,
            resilience_score=score,
            recommendations=recommendations,
            action_required=action_required,
            created_at=datetime.now(timezone.utc)
        )
    
    async def _check_local_bias(self, learning_feedback_results: Dict[str, Any]) -> SystemResilienceCheck:
        """Check for local bias"""
        lessons = learning_feedback_results.get('lessons', [])
        
        # Check if agents are following envelopes
        envelope_violations = sum(1 for lesson in lessons if lesson.get('envelope_violation', False))
        
        if envelope_violations > 2:
            result = 'failed'
            score = 0.4
            recommendations = ['Enforce envelope compliance', 'Increase monitoring', 'Reduce agent autonomy']
            action_required = True
        else:
            result = 'passed'
            score = 0.7
            recommendations = ['Continue monitoring', 'Maintain current autonomy levels']
            action_required = False
        
        return SystemResilienceCheck(
            check_id=f"BIAS_CHECK_{int(datetime.now().timestamp())}",
            check_type='local_bias',
            check_result=result,
            resilience_score=score,
            recommendations=recommendations,
            action_required=action_required,
            created_at=datetime.now(timezone.utc)
        )
    
    async def _check_system_stability(self, global_synthesis_results: Dict[str, Any]) -> SystemResilienceCheck:
        """Check system stability"""
        # Check for system performance metrics
        performance_metrics = global_synthesis_results.get('performance_metrics', {})
        
        # Calculate stability score
        stability_score = 0.8  # Mock calculation
        
        if stability_score < 0.6:
            result = 'failed'
            score = stability_score
            recommendations = ['Reduce system load', 'Increase resource allocation', 'Optimize performance']
            action_required = True
        else:
            result = 'passed'
            score = stability_score
            recommendations = ['Continue monitoring', 'Maintain current performance']
            action_required = False
        
        return SystemResilienceCheck(
            check_id=f"STABILITY_CHECK_{int(datetime.now().timestamp())}",
            check_type='system_stability',
            check_result=result,
            resilience_score=score,
            recommendations=recommendations,
            action_required=action_required,
            created_at=datetime.now(timezone.utc)
        )
    
    async def _publish_governance_results(self, results: Dict[str, Any]):
        """Publish governance results as CIL strand"""
        try:
            # Create CIL governance strand
            cil_strand = {
                'id': f"cil_governance_{int(datetime.now().timestamp())}",
                'kind': 'cil_governance',
                'module': 'alpha',
                'symbol': 'ALL',
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': ['agent:central_intelligence:governance_system:governance_processed'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.9,
                'sig_confidence': 0.95,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'governance_system',
                'strategic_meta_type': 'governance_decision',
                'resonance_score': 0.9
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing governance results: {e}")


# Example usage and testing
async def main():
    """Example usage of GovernanceSystem"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create governance system
    governance_system = GovernanceSystem(supabase_manager, llm_client)
    
    # Mock input data
    global_synthesis_results = {
        'experiment_ideas': [
            {
                'type': 'divergence_analysis',
                'family': 'divergence',
                'hypothesis': 'Test hypothesis 1',
                'target_agent': 'raw_data_intelligence',
                'priority': 'high',
                'false_positive_rate': 0.3
            },
            {
                'type': 'divergence_analysis',
                'family': 'divergence',
                'hypothesis': 'Test hypothesis 2',
                'target_agent': 'indicator_intelligence',
                'priority': 'high',
                'false_positive_rate': 0.4
            }
        ],
        'performance_metrics': {
            'system_load': 0.7,
            'response_time': 0.5,
            'throughput': 0.8
        }
    }
    
    experiment_results = {
        'active_experiments': [
            {
                'agent_id': 'raw_data_intelligence',
                'budget_allocation': 0.6,
                'resource_type': 'general',
                'goal_redefinition_attempt': False,
                'lesson_format_violation': False,
                'resource_overrun': False,
                'safety_violation': False
            },
            {
                'agent_id': 'indicator_intelligence',
                'budget_allocation': 0.5,
                'resource_type': 'general',
                'goal_redefinition_attempt': False,
                'lesson_format_violation': False,
                'resource_overrun': False,
                'safety_violation': False
            }
        ]
    }
    
    learning_feedback_results = {
        'lessons': [
            {
                'source_agent': 'raw_data_intelligence',
                'outcome': 'success',
                'pattern_family': 'divergence',
                'envelope_violation': False
            },
            {
                'source_agent': 'indicator_intelligence',
                'outcome': 'failure',
                'pattern_family': 'divergence',
                'envelope_violation': False
            }
        ]
    }
    
    # Process governance
    results = await governance_system.process_governance(
        global_synthesis_results, experiment_results, learning_feedback_results
    )
    
    print("Governance Processing Results:")
    print(f"Conflicts Detected: {len(results['conflicts_detected'])}")
    print(f"Conflict Resolutions: {len(results['conflict_resolutions'])}")
    print(f"Autonomy Violations: {len(results['autonomy_violations'])}")
    print(f"Human Overrides: {len(results['human_overrides'])}")
    print(f"Resilience Checks: {len(results['resilience_checks'])}")


if __name__ == "__main__":
    asyncio.run(main())
