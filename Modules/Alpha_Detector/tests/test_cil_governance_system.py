"""
Test CIL Governance System
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.engines.governance_system import (
    GovernanceSystem, DecisionOwnership, ConflictType, ResolutionStrategy, AutonomyLimit,
    DecisionBoundary, ConflictResolution, AutonomyViolation, HumanOverride, SystemResilienceCheck
)


class TestGovernanceSystem:
    """Test CIL Governance System"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager"""
        manager = Mock()
        manager.execute_query = AsyncMock()
        manager.insert_strand = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenRouterClient"""
        return Mock()
    
    @pytest.fixture
    def governance_system(self, mock_supabase_manager, mock_llm_client):
        """Create GovernanceSystem instance"""
        return GovernanceSystem(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_global_synthesis_results(self):
        """Mock global synthesis results"""
        return {
            'experiment_ideas': [
                {
                    'type': 'divergence_analysis',
                    'family': 'divergence',
                    'hypothesis': 'Test hypothesis 1',
                    'target_agent': 'raw_data_intelligence',
                    'priority': 'high',
                    'false_positive_rate': 0.3,
                    'conditions': {'regime': 'high_vol', 'session': 'US'}
                },
                {
                    'type': 'divergence_analysis',
                    'family': 'divergence',
                    'hypothesis': 'Test hypothesis 2',
                    'target_agent': 'indicator_intelligence',
                    'priority': 'high',
                    'false_positive_rate': 0.4,
                    'conditions': {'regime': 'high_vol', 'session': 'US'}
                },
                {
                    'type': 'rsi_analysis',
                    'family': 'technical',
                    'hypothesis': 'Test hypothesis 3',
                    'target_agent': 'indicator_intelligence',
                    'priority': 'medium',
                    'false_positive_rate': 0.2,
                    'conditions': {'regime': 'sideways', 'session': 'EU'}
                }
            ],
            'performance_metrics': {
                'system_load': 0.7,
                'response_time': 0.5,
                'throughput': 0.8
            }
        }
    
    @pytest.fixture
    def mock_experiment_results(self):
        """Mock experiment results"""
        return {
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
                    'goal_redefinition_attempt': True,
                    'lesson_format_violation': False,
                    'resource_overrun': True,
                    'safety_violation': False
                },
                {
                    'agent_id': 'pattern_intelligence',
                    'budget_allocation': 0.4,
                    'resource_type': 'specialized',
                    'goal_redefinition_attempt': False,
                    'lesson_format_violation': True,
                    'resource_overrun': False,
                    'safety_violation': True
                }
            ]
        }
    
    @pytest.fixture
    def mock_learning_feedback_results(self):
        """Mock learning feedback results"""
        return {
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
                },
                {
                    'source_agent': 'pattern_intelligence',
                    'outcome': 'success',
                    'pattern_family': 'technical',
                    'envelope_violation': True
                }
            ]
        }
    
    def test_governance_system_initialization(self, governance_system):
        """Test GovernanceSystem initialization"""
        assert governance_system.supabase_manager is not None
        assert governance_system.llm_client is not None
        assert governance_system.conflict_resolution_timeout_minutes == 30
        assert governance_system.autonomy_violation_threshold == 3
        assert governance_system.resilience_check_interval_hours == 6
        assert governance_system.human_override_cooldown_hours == 24
        assert governance_system.escalation_threshold == 0.8
        assert len(governance_system.decision_boundaries) == 6
        assert isinstance(governance_system.decision_boundaries[0], DecisionBoundary)
    
    def test_initialize_decision_boundaries(self, governance_system):
        """Test decision boundaries initialization"""
        boundaries = governance_system._initialize_decision_boundaries()
        
        assert len(boundaries) == 6
        
        # Check specific boundaries
        global_view_boundary = next(b for b in boundaries if b.decision_type == 'global_view')
        assert global_view_boundary.ownership == DecisionOwnership.CIL_OWNED
        assert 'agents_cannot_modify_global_view' in global_view_boundary.constraints
        
        local_tactics_boundary = next(b for b in boundaries if b.decision_type == 'local_tactics')
        assert local_tactics_boundary.ownership == DecisionOwnership.AGENT_OWNED
        assert 'cil_cannot_micromanage_tactics' in local_tactics_boundary.constraints
    
    @pytest.mark.asyncio
    async def test_process_governance_success(self, governance_system, mock_global_synthesis_results, 
                                            mock_experiment_results, mock_learning_feedback_results):
        """Test successful governance processing"""
        # Process governance
        results = await governance_system.process_governance(
            mock_global_synthesis_results, mock_experiment_results, mock_learning_feedback_results
        )
        
        # Verify structure
        assert 'conflicts_detected' in results
        assert 'conflict_resolutions' in results
        assert 'autonomy_violations' in results
        assert 'human_overrides' in results
        assert 'resilience_checks' in results
        assert 'governance_timestamp' in results
        assert 'governance_errors' in results
        
        # Verify processing timestamp
        assert isinstance(results['governance_timestamp'], datetime)
        
        # Verify results are lists
        assert isinstance(results['conflicts_detected'], list)
        assert isinstance(results['conflict_resolutions'], list)
        assert isinstance(results['autonomy_violations'], list)
        assert isinstance(results['human_overrides'], list)
        assert isinstance(results['resilience_checks'], list)
        assert isinstance(results['governance_errors'], list)
    
    @pytest.mark.asyncio
    async def test_detect_conflicts(self, governance_system, mock_global_synthesis_results, 
                                  mock_experiment_results, mock_learning_feedback_results):
        """Test conflict detection"""
        # Detect conflicts
        conflicts = await governance_system._detect_conflicts(
            mock_global_synthesis_results, mock_experiment_results, mock_learning_feedback_results
        )
        
        # Verify results
        assert isinstance(conflicts, list)
        assert len(conflicts) > 0  # Should detect some conflicts
        
        # Check conflict structure
        for conflict in conflicts:
            assert 'conflict_id' in conflict
            assert 'conflict_type' in conflict
            assert 'involved_agents' in conflict
            assert 'conflict_description' in conflict
            assert 'severity' in conflict
            assert 'created_at' in conflict
            assert conflict['conflict_id'].startswith(('OVERLAP_', 'BUDGET_', 'CONTRADICTION_', 'RESOURCE_', 'PRIORITY_'))
    
    @pytest.mark.asyncio
    async def test_detect_overlaps(self, governance_system, mock_global_synthesis_results):
        """Test overlap detection"""
        # Detect overlaps
        overlaps = await governance_system._detect_overlaps(mock_global_synthesis_results)
        
        # Verify results
        assert isinstance(overlaps, list)
        assert len(overlaps) > 0  # Should detect overlapping experiments
        
        # Check overlap structure
        for overlap in overlaps:
            assert overlap['conflict_type'] == ConflictType.OVERLAP.value
            assert overlap['conflict_id'].startswith('OVERLAP_')
            assert len(overlap['involved_agents']) >= 2
    
    @pytest.mark.asyncio
    async def test_are_experiments_overlapping(self, governance_system):
        """Test experiment overlap detection"""
        # Test same family overlap
        idea1 = {'family': 'divergence', 'conditions': {'regime': 'high_vol'}}
        idea2 = {'family': 'divergence', 'conditions': {'regime': 'sideways'}}
        assert await governance_system._are_experiments_overlapping(idea1, idea2) is True
        
        # Test same regime overlap
        idea1 = {'family': 'divergence', 'conditions': {'regime': 'high_vol'}}
        idea2 = {'family': 'technical', 'conditions': {'regime': 'high_vol'}}
        assert await governance_system._are_experiments_overlapping(idea1, idea2) is True
        
        # Test same session overlap
        idea1 = {'family': 'divergence', 'conditions': {'session': 'US'}}
        idea2 = {'family': 'technical', 'conditions': {'session': 'US'}}
        assert await governance_system._are_experiments_overlapping(idea1, idea2) is True
        
        # Test no overlap
        idea1 = {'family': 'divergence', 'conditions': {'regime': 'high_vol', 'session': 'US'}}
        idea2 = {'family': 'technical', 'conditions': {'regime': 'sideways', 'session': 'EU'}}
        assert await governance_system._are_experiments_overlapping(idea1, idea2) is False
    
    @pytest.mark.asyncio
    async def test_detect_budget_contention(self, governance_system):
        """Test budget contention detection"""
        # Test budget overrun
        experiment_results = {
            'active_experiments': [
                {'agent_id': 'agent1', 'budget_allocation': 0.6},
                {'agent_id': 'agent2', 'budget_allocation': 0.5}
            ]
        }
        
        conflicts = await governance_system._detect_budget_contention(experiment_results)
        
        assert isinstance(conflicts, list)
        assert len(conflicts) > 0  # Should detect budget overrun
        assert conflicts[0]['conflict_type'] == ConflictType.BUDGET_CONTENTION.value
        assert conflicts[0]['conflict_id'].startswith('BUDGET_')
        
        # Test no budget conflict
        experiment_results = {
            'active_experiments': [
                {'agent_id': 'agent1', 'budget_allocation': 0.3},
                {'agent_id': 'agent2', 'budget_allocation': 0.4}
            ]
        }
        
        conflicts = await governance_system._detect_budget_contention(experiment_results)
        assert len(conflicts) == 0  # Should not detect budget conflict
    
    @pytest.mark.asyncio
    async def test_detect_contradictions(self, governance_system):
        """Test contradiction detection"""
        learning_feedback_results = {
            'lessons': [
                {
                    'source_agent': 'agent1',
                    'outcome': 'success',
                    'pattern_family': 'divergence'
                },
                {
                    'source_agent': 'agent2',
                    'outcome': 'failure',
                    'pattern_family': 'divergence'
                }
            ]
        }
        
        conflicts = await governance_system._detect_contradictions(learning_feedback_results)
        
        assert isinstance(conflicts, list)
        assert len(conflicts) > 0  # Should detect contradictory lessons
        assert conflicts[0]['conflict_type'] == ConflictType.CONTRADICTION.value
        assert conflicts[0]['conflict_id'].startswith('CONTRADICTION_')
    
    @pytest.mark.asyncio
    async def test_are_lessons_contradictory(self, governance_system):
        """Test lesson contradiction detection"""
        # Test contradictory lessons
        lesson1 = {'outcome': 'success', 'pattern_family': 'divergence'}
        lesson2 = {'outcome': 'failure', 'pattern_family': 'divergence'}
        assert await governance_system._are_lessons_contradictory(lesson1, lesson2) is True
        
        # Test non-contradictory lessons
        lesson1 = {'outcome': 'success', 'pattern_family': 'divergence'}
        lesson2 = {'outcome': 'success', 'pattern_family': 'divergence'}
        assert await governance_system._are_lessons_contradictory(lesson1, lesson2) is False
        
        # Test different pattern families
        lesson1 = {'outcome': 'success', 'pattern_family': 'divergence'}
        lesson2 = {'outcome': 'failure', 'pattern_family': 'technical'}
        assert await governance_system._are_lessons_contradictory(lesson1, lesson2) is False
    
    @pytest.mark.asyncio
    async def test_detect_resource_conflicts(self, governance_system):
        """Test resource conflict detection"""
        experiment_results = {
            'active_experiments': [
                {'agent_id': 'agent1', 'resource_type': 'general'},
                {'agent_id': 'agent2', 'resource_type': 'general'},
                {'agent_id': 'agent3', 'resource_type': 'specialized'}
            ]
        }
        
        conflicts = await governance_system._detect_resource_conflicts(experiment_results)
        
        assert isinstance(conflicts, list)
        assert len(conflicts) > 0  # Should detect resource conflicts
        assert conflicts[0]['conflict_type'] == ConflictType.RESOURCE_CONFLICT.value
        assert conflicts[0]['conflict_id'].startswith('RESOURCE_')
    
    @pytest.mark.asyncio
    async def test_detect_priority_conflicts(self, governance_system):
        """Test priority conflict detection"""
        global_synthesis_results = {
            'experiment_ideas': [
                {'target_agent': 'agent1', 'priority': 'high'},
                {'target_agent': 'agent2', 'priority': 'high'},
                {'target_agent': 'agent3', 'priority': 'high'},
                {'target_agent': 'agent4', 'priority': 'high'},
                {'target_agent': 'agent5', 'priority': 'medium'}
            ]
        }
        
        conflicts = await governance_system._detect_priority_conflicts(global_synthesis_results)
        
        assert isinstance(conflicts, list)
        assert len(conflicts) > 0  # Should detect priority conflicts
        assert conflicts[0]['conflict_type'] == ConflictType.PRIORITY_CONFLICT.value
        assert conflicts[0]['conflict_id'].startswith('PRIORITY_')
    
    @pytest.mark.asyncio
    async def test_resolve_conflicts(self, governance_system):
        """Test conflict resolution"""
        conflicts = [
            {
                'conflict_id': 'TEST_CONFLICT_1',
                'conflict_type': ConflictType.OVERLAP.value,
                'involved_agents': ['agent1', 'agent2'],
                'conflict_description': 'Test overlap conflict',
                'severity': 'high'
            },
            {
                'conflict_id': 'TEST_CONFLICT_2',
                'conflict_type': ConflictType.BUDGET_CONTENTION.value,
                'involved_agents': ['agent1', 'agent2', 'agent3'],
                'conflict_description': 'Test budget conflict',
                'severity': 'medium'
            }
        ]
        
        resolutions = await governance_system._resolve_conflicts(conflicts)
        
        assert isinstance(resolutions, list)
        assert len(resolutions) == 2
        
        # Check resolution structure
        for resolution in resolutions:
            assert isinstance(resolution, ConflictResolution)
            assert resolution.conflict_id.startswith('TEST_CONFLICT_')
            assert isinstance(resolution.conflict_type, ConflictType)
            assert isinstance(resolution.resolution_strategy, ResolutionStrategy)
            assert resolution.resolution_outcome == 'resolved'
            assert isinstance(resolution.resolved_at, datetime)
            assert isinstance(resolution.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_resolve_single_conflict(self, governance_system):
        """Test single conflict resolution"""
        conflict = {
            'conflict_id': 'TEST_CONFLICT',
            'conflict_type': ConflictType.OVERLAP.value,
            'involved_agents': ['agent1', 'agent2'],
            'conflict_description': 'Test conflict',
            'severity': 'high'
        }
        
        resolution = await governance_system._resolve_single_conflict(conflict)
        
        assert resolution is not None
        assert isinstance(resolution, ConflictResolution)
        assert resolution.conflict_id == 'TEST_CONFLICT'
        assert resolution.conflict_type == ConflictType.OVERLAP
        assert resolution.resolution_strategy == ResolutionStrategy.CIL_ARBITRATION  # High severity
        assert resolution.resolution_outcome == 'resolved'
    
    @pytest.mark.asyncio
    async def test_generate_resolution_details(self, governance_system):
        """Test resolution details generation"""
        conflict = {'conflict_type': ConflictType.OVERLAP.value, 'severity': 'high'}
        
        # Test CIL arbitration
        details = await governance_system._generate_resolution_details(conflict, ResolutionStrategy.CIL_ARBITRATION)
        assert details['action'] == 'cil_arbitration'
        assert details['decision'] == 'cil_makes_final_decision'
        assert details['enforcement'] == 'mandatory'
        
        # Test agent negotiation
        details = await governance_system._generate_resolution_details(conflict, ResolutionStrategy.AGENT_NEGOTIATION)
        assert details['action'] == 'agent_negotiation'
        assert details['decision'] == 'agents_negotiate_solution'
        assert details['enforcement'] == 'voluntary'
        
        # Test automatic resolution
        details = await governance_system._generate_resolution_details(conflict, ResolutionStrategy.AUTOMATIC_RESOLUTION)
        assert details['action'] == 'automatic_resolution'
        assert details['decision'] == 'system_automatically_resolves'
        assert details['enforcement'] == 'automatic'
    
    @pytest.mark.asyncio
    async def test_check_autonomy_limits(self, governance_system, mock_global_synthesis_results, mock_experiment_results):
        """Test autonomy limit checking"""
        # Check autonomy limits
        violations = await governance_system._check_autonomy_limits(
            mock_global_synthesis_results, mock_experiment_results
        )
        
        # Verify results
        assert isinstance(violations, list)
        assert len(violations) > 0  # Should detect some violations
        
        # Check violation structure
        for violation in violations:
            assert isinstance(violation, AutonomyViolation)
            assert violation.violation_id.startswith(('GOAL_VIOLATION_', 'BEACON_VIOLATION_', 'FORMAT_VIOLATION_', 'RESOURCE_VIOLATION_', 'SAFETY_VIOLATION_'))
            assert isinstance(violation.violation_type, AutonomyLimit)
            assert violation.severity in ['low', 'medium', 'high', 'critical']
            assert isinstance(violation.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_check_goal_redefinition_violations(self, governance_system):
        """Test goal redefinition violation checking"""
        experiment_results = {
            'active_experiments': [
                {'agent_id': 'agent1', 'goal_redefinition_attempt': True},
                {'agent_id': 'agent2', 'goal_redefinition_attempt': False}
            ]
        }
        
        violations = await governance_system._check_goal_redefinition_violations(experiment_results)
        
        assert isinstance(violations, list)
        assert len(violations) == 1  # Should detect one violation
        assert violations[0].violation_type == AutonomyLimit.GOAL_REDEFINITION
        assert violations[0].agent_id == 'agent1'
        assert violations[0].severity == 'high'
        assert violations[0].corrective_action == 'block_goal_redefinition'
    
    @pytest.mark.asyncio
    async def test_check_beacon_ignorance_violations(self, governance_system):
        """Test beacon ignorance violation checking"""
        global_synthesis_results = {
            'experiment_ideas': [
                {'target_agent': 'agent1', 'ignores_beacon': True},
                {'target_agent': 'agent2', 'ignores_beacon': False}
            ]
        }
        
        violations = await governance_system._check_beacon_ignorance_violations(global_synthesis_results)
        
        assert isinstance(violations, list)
        assert len(violations) == 1  # Should detect one violation
        assert violations[0].violation_type == AutonomyLimit.BEACON_IGNORANCE
        assert violations[0].agent_id == 'agent1'
        assert violations[0].severity == 'medium'
        assert violations[0].corrective_action == 'enforce_beacon_compliance'
    
    @pytest.mark.asyncio
    async def test_check_lesson_format_violations(self, governance_system):
        """Test lesson format violation checking"""
        experiment_results = {
            'active_experiments': [
                {'agent_id': 'agent1', 'lesson_format_violation': True},
                {'agent_id': 'agent2', 'lesson_format_violation': False}
            ]
        }
        
        violations = await governance_system._check_lesson_format_violations(experiment_results)
        
        assert isinstance(violations, list)
        assert len(violations) == 1  # Should detect one violation
        assert violations[0].violation_type == AutonomyLimit.LESSON_FORMAT_VIOLATION
        assert violations[0].agent_id == 'agent1'
        assert violations[0].severity == 'low'
        assert violations[0].corrective_action == 'enforce_lesson_format'
    
    @pytest.mark.asyncio
    async def test_check_resource_overrun_violations(self, governance_system):
        """Test resource overrun violation checking"""
        experiment_results = {
            'active_experiments': [
                {'agent_id': 'agent1', 'resource_overrun': True},
                {'agent_id': 'agent2', 'resource_overrun': False}
            ]
        }
        
        violations = await governance_system._check_resource_overrun_violations(experiment_results)
        
        assert isinstance(violations, list)
        assert len(violations) == 1  # Should detect one violation
        assert violations[0].violation_type == AutonomyLimit.RESOURCE_OVERRUN
        assert violations[0].agent_id == 'agent1'
        assert violations[0].severity == 'medium'
        assert violations[0].corrective_action == 'enforce_resource_limits'
    
    @pytest.mark.asyncio
    async def test_check_safety_violations(self, governance_system):
        """Test safety violation checking"""
        experiment_results = {
            'active_experiments': [
                {'agent_id': 'agent1', 'safety_violation': True},
                {'agent_id': 'agent2', 'safety_violation': False}
            ]
        }
        
        violations = await governance_system._check_safety_violations(experiment_results)
        
        assert isinstance(violations, list)
        assert len(violations) == 1  # Should detect one violation
        assert violations[0].violation_type == AutonomyLimit.SAFETY_VIOLATION
        assert violations[0].agent_id == 'agent1'
        assert violations[0].severity == 'critical'
        assert violations[0].corrective_action == 'immediate_safety_stop'
    
    @pytest.mark.asyncio
    async def test_process_human_overrides(self, governance_system):
        """Test human override processing"""
        overrides = await governance_system._process_human_overrides()
        
        assert isinstance(overrides, list)
        # Mock implementation returns empty list
        assert len(overrides) == 0
    
    @pytest.mark.asyncio
    async def test_check_system_resilience(self, governance_system, mock_global_synthesis_results, mock_learning_feedback_results):
        """Test system resilience checking"""
        # Check system resilience
        checks = await governance_system._check_system_resilience(
            mock_global_synthesis_results, mock_learning_feedback_results
        )
        
        # Verify results
        assert isinstance(checks, list)
        assert len(checks) == 3  # Should have 3 types of checks
        
        # Check resilience check structure
        for check in checks:
            assert isinstance(check, SystemResilienceCheck)
            assert check.check_id.startswith(('RUNAWAY_CHECK_', 'BIAS_CHECK_', 'STABILITY_CHECK_'))
            assert check.check_type in ['runaway_experiments', 'local_bias', 'system_stability']
            assert check.check_result in ['passed', 'failed']
            assert 0.0 <= check.resilience_score <= 1.0
            assert isinstance(check.recommendations, list)
            assert isinstance(check.action_required, bool)
            assert isinstance(check.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_check_runaway_experiments(self, governance_system):
        """Test runaway experiment checking"""
        # Test with high false positive rate
        global_synthesis_results = {
            'experiment_ideas': [
                {'false_positive_rate': 0.6},
                {'false_positive_rate': 0.7},
                {'false_positive_rate': 0.8},
                {'false_positive_rate': 0.9}
            ]
        }
        
        check = await governance_system._check_runaway_experiments(global_synthesis_results)
        
        assert isinstance(check, SystemResilienceCheck)
        assert check.check_type == 'runaway_experiments'
        assert check.check_result == 'failed'
        assert check.resilience_score == 0.3
        assert check.action_required is True
        assert 'Implement stop rules' in check.recommendations
        
        # Test with low false positive rate
        global_synthesis_results = {
            'experiment_ideas': [
                {'false_positive_rate': 0.2},
                {'false_positive_rate': 0.3}
            ]
        }
        
        check = await governance_system._check_runaway_experiments(global_synthesis_results)
        
        assert check.check_result == 'passed'
        assert check.resilience_score == 0.8
        assert check.action_required is False
    
    @pytest.mark.asyncio
    async def test_check_local_bias(self, governance_system):
        """Test local bias checking"""
        # Test with envelope violations
        learning_feedback_results = {
            'lessons': [
                {'envelope_violation': True},
                {'envelope_violation': True},
                {'envelope_violation': True}
            ]
        }
        
        check = await governance_system._check_local_bias(learning_feedback_results)
        
        assert isinstance(check, SystemResilienceCheck)
        assert check.check_type == 'local_bias'
        assert check.check_result == 'failed'
        assert check.resilience_score == 0.4
        assert check.action_required is True
        assert 'Enforce envelope compliance' in check.recommendations
        
        # Test without envelope violations
        learning_feedback_results = {
            'lessons': [
                {'envelope_violation': False},
                {'envelope_violation': False}
            ]
        }
        
        check = await governance_system._check_local_bias(learning_feedback_results)
        
        assert check.check_result == 'passed'
        assert check.resilience_score == 0.7
        assert check.action_required is False
    
    @pytest.mark.asyncio
    async def test_check_system_stability(self, governance_system):
        """Test system stability checking"""
        global_synthesis_results = {
            'performance_metrics': {
                'system_load': 0.7,
                'response_time': 0.5,
                'throughput': 0.8
            }
        }
        
        check = await governance_system._check_system_stability(global_synthesis_results)
        
        assert isinstance(check, SystemResilienceCheck)
        assert check.check_type == 'system_stability'
        assert check.check_result == 'passed'
        assert check.resilience_score == 0.8
        assert check.action_required is False
        assert 'Continue monitoring' in check.recommendations
    
    @pytest.mark.asyncio
    async def test_publish_governance_results(self, governance_system, mock_supabase_manager):
        """Test publishing governance results"""
        results = {
            'conflicts_detected': [{'conflict_id': 'TEST_CONFLICT'}],
            'conflict_resolutions': [{'resolution_id': 'TEST_RESOLUTION'}],
            'autonomy_violations': [{'violation_id': 'TEST_VIOLATION'}],
            'human_overrides': [{'override_id': 'TEST_OVERRIDE'}],
            'resilience_checks': [{'check_id': 'TEST_CHECK'}],
            'governance_timestamp': datetime.now(timezone.utc),
            'governance_errors': []
        }
        
        await governance_system._publish_governance_results(results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_governance'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['team_member'] == 'governance_system'
        assert call_args['strategic_meta_type'] == 'governance_decision'
        assert call_args['resonance_score'] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
