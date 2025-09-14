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


# Lineage & Provenance System Integration
class LineageType(Enum):
    """Types of lineage relationships"""
    PARENT_CHILD = "parent_child"
    SIBLING = "sibling"
    DESCENDANT = "descendant"
    ANCESTOR = "ancestor"
    MUTATION = "mutation"
    MERGE = "merge"
    SPLIT = "split"


class ProvenanceType(Enum):
    """Types of provenance information"""
    CREATION = "creation"
    MODIFICATION = "modification"
    DERIVATION = "derivation"
    INFLUENCE = "influence"
    REFERENCE = "reference"
    VALIDATION = "validation"


class MutationType(Enum):
    """Types of mutations in lineage"""
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    CONDITION_REFINEMENT = "condition_refinement"
    SCOPE_EXPANSION = "scope_expansion"
    SCOPE_REDUCTION = "scope_reduction"
    COMBINATION = "combination"
    SPLIT = "split"
    MERGE = "merge"


@dataclass
class LineageNode:
    """A node in the lineage tree"""
    node_id: str
    node_type: str  # 'experiment', 'lesson', 'pattern', 'doctrine'
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    status: str  # 'active', 'retired', 'superseded'


@dataclass
class LineageEdge:
    """An edge in the lineage tree"""
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: LineageType
    mutation_note: str
    confidence: float
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class ProvenanceRecord:
    """A provenance record for tracking lineage"""
    record_id: str
    entity_id: str
    entity_type: str
    provenance_type: ProvenanceType
    source_entity_id: Optional[str]
    source_entity_type: Optional[str]
    mutation_details: Dict[str, Any]
    confidence: float
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class FamilyTree:
    """A family tree for a signal family"""
    family_name: str
    root_nodes: List[str]
    nodes: Dict[str, LineageNode]
    edges: Dict[str, LineageEdge]
    provenance_records: List[ProvenanceRecord]
    tree_depth: int
    branch_count: int
    created_at: datetime
    updated_at: datetime


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
        
        # Lineage & Provenance System Configuration
        self.family_trees: Dict[str, FamilyTree] = {}
        self.lineage_nodes: Dict[str, LineageNode] = {}
        self.lineage_edges: Dict[str, LineageEdge] = {}
        self.provenance_records: List[ProvenanceRecord] = []
        self.circular_patterns: Set[str] = set()
        
        # Lineage & Provenance parameters
        self.max_tree_depth = 10
        self.max_branches_per_node = 5
        self.similarity_threshold = 0.8
        self.circular_detection_threshold = 0.9
        
        # Initialize family trees
        self._initialize_family_trees()
    
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
    
    def _initialize_family_trees(self):
        """Initialize family trees for known signal families"""
        families = [
            'divergence', 'volume', 'correlation', 'session', 'cross_asset',
            'pattern', 'indicator', 'microstructure', 'regime', 'volatility'
        ]
        
        for family in families:
            self.family_trees[family] = FamilyTree(
                family_name=family,
                root_nodes=[],
                nodes={},
                edges={},
                provenance_records=[],
                tree_depth=0,
                branch_count=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
    
    # Lineage & Provenance System Methods
    async def process_lineage_provenance(self, new_entities: List[Dict[str, Any]],
                                       existing_lineage: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process lineage and provenance for new entities to track family trees
        and prevent circular rediscovery patterns.
        Uses module_intelligence for lineage data storage.
        """
        logger.info("Processing lineage and provenance analysis.")
        
        try:
            # Analyze lineage for new entities
            lineage_analyses = await self._analyze_lineage(new_entities, existing_lineage)
            
            # Detect circular patterns
            circular_detections = await self._detect_circular_patterns(new_entities, existing_lineage)
            
            # Update family trees
            tree_updates = await self._update_family_trees(lineage_analyses, circular_detections)
            
            # Generate provenance records
            provenance_generation = await self._generate_provenance_records(new_entities, lineage_analyses)
            
            # Compile results
            results = {
                'lineage_analyses': lineage_analyses,
                'circular_detections': circular_detections,
                'tree_updates': tree_updates,
                'provenance_generation': provenance_generation,
                'lineage_timestamp': datetime.now(timezone.utc),
                'lineage_errors': []
            }
            
            # Publish results
            await self._publish_lineage_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing lineage provenance: {e}")
            return {
                'lineage_analyses': [],
                'circular_detections': [],
                'tree_updates': {},
                'provenance_generation': [],
                'lineage_timestamp': datetime.now(timezone.utc),
                'lineage_errors': [str(e)]
            }
    
    async def _analyze_lineage(self, new_entities: List[Dict[str, Any]],
                             existing_lineage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze lineage relationships for new entities"""
        lineage_analyses = []
        
        for entity in new_entities:
            # Prepare analysis data
            analysis_data = {
                'entity_id': entity.get('entity_id', f"ENTITY_{int(datetime.now().timestamp())}"),
                'entity_type': entity.get('entity_type', 'unknown'),
                'content': entity.get('content', {}),
                'metadata': entity.get('metadata', {}),
                'created_at': entity.get('created_at', datetime.now(timezone.utc).isoformat()),
                'family': entity.get('family', 'unknown'),
                'existing_nodes': existing_lineage.get('nodes', {}),
                'existing_edges': existing_lineage.get('edges', {}),
                'recent_additions': existing_lineage.get('recent_additions', [])
            }
            
            # Generate lineage analysis using LLM
            analysis = await self._generate_lineage_analysis(analysis_data)
            
            if analysis:
                lineage_analyses.append({
                    'entity_id': analysis_data['entity_id'],
                    'lineage_analysis': analysis['lineage_analysis'],
                    'provenance_insights': analysis.get('provenance_insights', []),
                    'circular_risk_assessment': analysis.get('circular_risk_assessment', {}),
                    'uncertainty_flags': analysis.get('uncertainty_flags', [])
                })
        
        return lineage_analyses
    
    async def _generate_lineage_analysis(self, analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate lineage analysis using LLM"""
        try:
            # Generate analysis using LLM
            analysis = await self._generate_llm_analysis(
                self._get_lineage_analysis_prompt(), analysis_data
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating lineage analysis: {e}")
            return None
    
    async def _detect_circular_patterns(self, new_entities: List[Dict[str, Any]],
                                      existing_lineage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect circular rediscovery patterns"""
        circular_detections = []
        
        for entity in new_entities:
            # Prepare detection data
            detection_data = {
                'entity_id': entity.get('entity_id', f"ENTITY_{int(datetime.now().timestamp())}"),
                'entity_type': entity.get('entity_type', 'unknown'),
                'content': entity.get('content', {}),
                'family': entity.get('family', 'unknown'),
                'family_tree': existing_lineage.get('family_trees', {}).get(entity.get('family', 'unknown'), {}),
                'recent_patterns': existing_lineage.get('recent_patterns', []),
                'historical_patterns': existing_lineage.get('historical_patterns', [])
            }
            
            # Generate circular detection using LLM
            detection = await self._generate_circular_detection(detection_data)
            
            if detection:
                circular_detections.append({
                    'entity_id': detection_data['entity_id'],
                    'circular_detection': detection['circular_detection'],
                    'circular_risk': detection.get('circular_risk', {}),
                    'lineage_recommendations': detection.get('lineage_recommendations', [])
                })
        
        return circular_detections
    
    async def _generate_circular_detection(self, detection_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate circular detection using LLM"""
        try:
            # Generate detection using LLM
            detection = await self._generate_llm_analysis(
                self._get_circular_detection_prompt(), detection_data
            )
            
            return detection
            
        except Exception as e:
            logger.error(f"Error generating circular detection: {e}")
            return None
    
    async def _update_family_trees(self, lineage_analyses: List[Dict[str, Any]],
                                 circular_detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update family trees based on lineage analyses using module_intelligence"""
        tree_updates = {}
        
        for analysis in lineage_analyses:
            entity_id = analysis['entity_id']
            lineage_analysis = analysis['lineage_analysis']
            
            # Determine family from entity module_intelligence (simplified)
            family = lineage_analysis.get('module_intelligence', {}).get('motif_family', 'divergence')
            
            if family in self.family_trees:
                family_tree = self.family_trees[family]
                
                # Create lineage node with module_intelligence data
                node = LineageNode(
                    node_id=entity_id,
                    node_type='experiment',
                    content={
                        'hypothesis': lineage_analysis.get('module_intelligence', {}).get('mechanism_hypothesis', 'Test hypothesis'),
                        'module_intelligence': lineage_analysis.get('module_intelligence', {})
                    },
                    metadata={'family': family},
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    status='active'
                )
                
                # Add node to family tree
                family_tree.nodes[entity_id] = node
                
                # Create lineage edges based on analysis
                edges_created = []
                for parent_candidate in lineage_analysis.get('parent_candidates', []):
                    edge = LineageEdge(
                        edge_id=f"EDGE_{entity_id}_{parent_candidate['node_id']}",
                        source_node_id=parent_candidate['node_id'],
                        target_node_id=entity_id,
                        relationship_type=LineageType(parent_candidate['relationship_type']),
                        mutation_note=parent_candidate.get('mutation_note', ''),
                        confidence=parent_candidate['confidence'],
                        created_at=datetime.now(timezone.utc),
                        metadata={}
                    )
                    
                    family_tree.edges[edge.edge_id] = edge
                    edges_created.append(edge.edge_id)
                
                # Update tree metrics
                family_tree.tree_depth = max(family_tree.tree_depth, 1)
                family_tree.branch_count = len(family_tree.edges)
                family_tree.updated_at = datetime.now(timezone.utc)
                
                tree_updates[family] = {
                    'nodes_added': 1,
                    'edges_added': len(edges_created),
                    'tree_depth': family_tree.tree_depth,
                    'branch_count': family_tree.branch_count,
                    'updated_at': family_tree.updated_at.isoformat()
                }
        
        return tree_updates
    
    async def _generate_provenance_records(self, new_entities: List[Dict[str, Any]],
                                         lineage_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate provenance records for new entities"""
        provenance_generation = []
        
        for entity, analysis in zip(new_entities, lineage_analyses):
            entity_id = analysis['entity_id']
            lineage_analysis = analysis['lineage_analysis']
            
            # Create provenance record
            provenance_record = ProvenanceRecord(
                record_id=f"PROV_{entity_id}",
                entity_id=entity_id,
                entity_type=entity.get('entity_type', 'unknown'),
                provenance_type=ProvenanceType.CREATION,
                source_entity_id=lineage_analysis.get('parent_candidates', [{}])[0].get('node_id') if lineage_analysis.get('parent_candidates') else None,
                source_entity_type='experiment',
                mutation_details=lineage_analysis.get('parent_candidates', [{}])[0].get('mutation_note', '') if lineage_analysis.get('parent_candidates') else '',
                confidence=lineage_analysis.get('parent_candidates', [{}])[0].get('confidence', 0.5) if lineage_analysis.get('parent_candidates') else 0.5,
                created_at=datetime.now(timezone.utc),
                metadata={'family': entity.get('family', 'unknown')}
            )
            
            # Add to provenance records
            self.provenance_records.append(provenance_record)
            
            provenance_generation.append({
                'record_id': provenance_record.record_id,
                'entity_id': entity_id,
                'provenance_type': provenance_record.provenance_type.value,
                'source_entity_id': provenance_record.source_entity_id,
                'mutation_details': provenance_record.mutation_details,
                'confidence': provenance_record.confidence,
                'created_at': provenance_record.created_at.isoformat()
            })
        
        return provenance_generation
    
    async def _generate_llm_analysis(self, prompt_template: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate LLM analysis using prompt template"""
        try:
            # Format prompt with data
            formatted_prompt = prompt_template.format(**data)
            
            # Call LLM (mock implementation)
            # In real implementation, use self.llm_client
            if 'lineage_analysis' in formatted_prompt:
                response = {
                    "lineage_analysis": {
                        "parent_candidates": [
                            {
                                "node_id": "PARENT_1",
                                "relationship_type": "parent_child",
                                "confidence": 0.85,
                                "mutation_note": "Parameter adjustment for volatility threshold"
                            }
                        ],
                        "sibling_candidates": [
                            {
                                "node_id": "SIBLING_1",
                                "relationship_type": "sibling",
                                "confidence": 0.72,
                                "similarity_score": 0.78
                            }
                        ],
                        "influence_candidates": [
                            {
                                "node_id": "INFLUENCE_1",
                                "relationship_type": "influence",
                                "confidence": 0.68,
                                "influence_type": "parameter"
                            }
                        ]
                    },
                    "provenance_insights": [
                        "Strong parent-child relationship with parameter mutation",
                        "Moderate sibling relationship with similar approach",
                        "Weak influence from related experiment"
                    ],
                    "circular_risk_assessment": {
                        "risk_level": "low",
                        "risk_factors": ["Parameter variation", "Condition refinement"],
                        "prevention_suggestions": ["Monitor parameter ranges", "Track condition evolution"]
                    },
                    "uncertainty_flags": ["Limited historical context"]
                }
            elif 'circular_detection' in formatted_prompt:
                response = {
                    "circular_detection": {
                        "duplicate_candidates": [
                            {
                                "node_id": "DUPLICATE_1",
                                "similarity_score": 0.92,
                                "duplicate_type": "near",
                                "confidence": 0.88
                            }
                        ],
                        "cyclical_patterns": [],
                        "redundant_variations": [
                            {
                                "base_node": "BASE_1",
                                "variation_type": "parameter",
                                "redundancy_score": 0.75,
                                "confidence": 0.82
                            }
                        ]
                    },
                    "circular_risk": {
                        "overall_risk": "medium",
                        "risk_score": 0.65,
                        "primary_risks": ["Near-duplicate pattern", "Parameter redundancy"],
                        "prevention_actions": ["Increase parameter diversity", "Expand condition scope"]
                    },
                    "lineage_recommendations": [
                        "Consider different parameter ranges",
                        "Explore alternative conditions",
                        "Monitor for cyclical patterns"
                    ]
                }
            else:
                response = {
                    "family_tree_analysis": {
                        "topology_insights": [
                            "Balanced branching structure",
                            "Good depth distribution",
                            "Efficient node utilization"
                        ],
                        "growth_patterns": [
                            "Steady growth in divergence family",
                            "Recent focus on parameter refinement",
                            "Increasing cross-family connections"
                        ],
                        "evolution_trends": [
                            "Progressive parameter optimization",
                            "Condition scope expansion",
                            "Approach diversification"
                        ],
                        "optimization_opportunities": [
                            "Reduce redundant branches",
                            "Optimize edge relationships",
                            "Improve node utilization"
                        ]
                    },
                    "tree_metrics": {
                        "branching_factor": 0.75,
                        "depth_efficiency": 0.82,
                        "node_utilization": 0.68,
                        "edge_efficiency": 0.71
                    },
                    "recommendations": [
                        "Optimize tree structure",
                        "Improve node utilization",
                        "Enhance edge efficiency"
                    ],
                    "uncertainty_flags": ["Limited tree depth data"]
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating LLM analysis: {e}")
            return None
    
    def _get_lineage_analysis_prompt(self) -> str:
        """Get lineage analysis prompt template"""
        return """
        Analyze the lineage and provenance of this entity.
        
        Entity Details:
        - ID: {entity_id}
        - Type: {entity_type}
        - Content: {content}
        - Metadata: {metadata}
        - Created At: {created_at}
        
        Existing Lineage Context:
        - Family: {family}
        - Existing Nodes: {existing_nodes}
        - Existing Edges: {existing_edges}
        - Recent Additions: {recent_additions}
        
        Analyze lineage relationships:
        1. Parent-child relationships (direct derivation)
        2. Sibling relationships (parallel development)
        3. Mutation patterns (parameter adjustments, refinements)
        4. Merge/split patterns (combination or division)
        5. Influence relationships (indirect connections)
        
        Respond in JSON format:
        {{
            "lineage_analysis": {{
                "parent_candidates": [
                    {{
                        "node_id": "node_id",
                        "relationship_type": "parent_child|sibling|mutation|merge|split",
                        "confidence": 0.0-1.0,
                        "mutation_note": "description of relationship"
                    }}
                ],
                "sibling_candidates": [
                    {{
                        "node_id": "node_id",
                        "relationship_type": "sibling",
                        "confidence": 0.0-1.0,
                        "similarity_score": 0.0-1.0
                    }}
                ],
                "influence_candidates": [
                    {{
                        "node_id": "node_id",
                        "relationship_type": "influence",
                        "confidence": 0.0-1.0,
                        "influence_type": "parameter|condition|scope|approach"
                    }}
                ]
            }},
            "provenance_insights": ["list of insights"],
            "circular_risk_assessment": {{
                "risk_level": "low|medium|high",
                "risk_factors": ["list of risk factors"],
                "prevention_suggestions": ["list of suggestions"]
            }},
            "uncertainty_flags": ["any uncertainties"]
        }}
        """
    
    def _get_circular_detection_prompt(self) -> str:
        """Get circular detection prompt template"""
        return """
        Detect potential circular rediscovery patterns in the lineage.
        
        New Entity:
        - ID: {entity_id}
        - Type: {entity_type}
        - Content: {content}
        - Family: {family}
        
        Existing Lineage:
        - Family Tree: {family_tree}
        - Recent Patterns: {recent_patterns}
        - Historical Patterns: {historical_patterns}
        
        Analyze for circular rediscovery:
        1. Direct duplicates (identical content)
        2. Near-duplicates (high similarity)
        3. Cyclical patterns (A→B→C→A)
        4. Redundant variations (same approach, different parameters)
        5. Historical repetition (same pattern, different time)
        
        Respond in JSON format:
        {{
            "circular_detection": {{
                "duplicate_candidates": [
                    {{
                        "node_id": "node_id",
                        "similarity_score": 0.0-1.0,
                        "duplicate_type": "exact|near|parameter_variant|temporal_variant",
                        "confidence": 0.0-1.0
                    }}
                ],
                "cyclical_patterns": [
                    {{
                        "cycle_nodes": ["node1", "node2", "node3"],
                        "cycle_type": "direct|indirect|parameter_cycle",
                        "confidence": 0.0-1.0
                    }}
                ],
                "redundant_variations": [
                    {{
                        "base_node": "node_id",
                        "variation_type": "parameter|condition|scope",
                        "redundancy_score": 0.0-1.0,
                        "confidence": 0.0-1.0
                    }}
                ]
            }},
            "circular_risk": {{
                "overall_risk": "low|medium|high",
                "risk_score": 0.0-1.0,
                "primary_risks": ["list of primary risks"],
                "prevention_actions": ["list of prevention actions"]
            }},
            "lineage_recommendations": ["list of recommendations"]
        }}
        """
    
    async def _publish_lineage_results(self, results: Dict[str, Any]):
        """Publish lineage results as CIL strand"""
        try:
            # Create CIL lineage strand
            cil_strand = {
                'id': f"cil_lineage_provenance_{int(datetime.now().timestamp())}",
                'kind': 'cil_lineage_provenance',
                'module': 'alpha',
                'symbol': 'ALL',
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': ['agent:central_intelligence:governance_system:lineage_processed'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.9,
                'sig_confidence': 0.95,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'team_member': 'governance_system',
                'strategic_meta_type': 'lineage_provenance',
                'resonance_score': 0.9
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            logger.error(f"Error publishing lineage results: {e}")

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
                'team_member': 'governance_system',
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
