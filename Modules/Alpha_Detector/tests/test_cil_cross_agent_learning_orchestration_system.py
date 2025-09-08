"""
Test suite for CIL Cross-Agent Learning Orchestration System
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from src.intelligence.system_control.central_intelligence_layer.missing_pieces.cross_agent_learning_orchestration_system import (
    CrossAgentLearningOrchestrationSystem,
    LearningType,
    LearningPhase,
    LearningStatus,
    AgentRole,
    LearningTask,
    LearningSession,
    LearningCoordination,
    LearningSynthesis
)


class TestCrossAgentLearningOrchestrationSystem:
    """Test suite for CrossAgentLearningOrchestrationSystem"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager"""
        manager = Mock()
        manager.insert_strand = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenRouterClient"""
        client = Mock()
        return client
    
    @pytest.fixture
    def orchestration_system(self, mock_supabase_manager, mock_llm_client):
        """Create CrossAgentLearningOrchestrationSystem instance"""
        return CrossAgentLearningOrchestrationSystem(mock_supabase_manager, mock_llm_client)
    
    def test_cross_agent_learning_orchestration_system_initialization(self, orchestration_system):
        """Test system initialization"""
        assert orchestration_system.supabase_manager is not None
        assert orchestration_system.llm_client is not None
        assert orchestration_system.max_concurrent_sessions == 5
        assert orchestration_system.learning_timeout_hours == 24
        assert orchestration_system.coordination_interval_minutes == 15
        assert orchestration_system.synthesis_threshold == 0.8
        assert orchestration_system.agent_capacity_limit == 3
        assert len(orchestration_system.active_sessions) == 0
        assert len(orchestration_system.learning_tasks) == 0
        assert len(orchestration_system.learning_coordinations) == 0
        assert len(orchestration_system.learning_syntheses) == 0
        assert len(orchestration_system.agent_workloads) == 5
    
    def test_initialize_agent_workloads(self, orchestration_system):
        """Test agent workloads initialization"""
        expected_agents = [
            'raw_data_intelligence',
            'indicator_intelligence', 
            'pattern_intelligence',
            'system_control',
            'central_intelligence_layer'
        ]
        
        for agent in expected_agents:
            assert agent in orchestration_system.agent_workloads
            assert orchestration_system.agent_workloads[agent] == 0
    
    @pytest.mark.asyncio
    async def test_process_cross_agent_learning_orchestration(self, orchestration_system):
        """Test processing cross-agent learning orchestration"""
        learning_requests = [
            {
                'objectives': ['Improve pattern detection', 'Enhance signal accuracy'],
                'learning_type': 'distributed',
                'priority': 'high',
                'deadline': '2024-01-15T12:00:00Z',
                'constraints': ['max_agents_3']
            }
        ]
        
        agent_statuses = {
            'raw_data_intelligence': {'status': 'active', 'capacity': 0.6},
            'indicator_intelligence': {'status': 'active', 'capacity': 0.4}
        }
        
        results = await orchestration_system.process_cross_agent_learning_orchestration(
            learning_requests, agent_statuses
        )
        
        assert 'session_plans' in results
        assert 'coordination_results' in results
        assert 'synthesis_results' in results
        assert 'workload_updates' in results
        assert 'orchestration_timestamp' in results
        assert 'orchestration_errors' in results
        assert isinstance(results['session_plans'], list)
        assert isinstance(results['coordination_results'], list)
        assert isinstance(results['synthesis_results'], list)
        assert isinstance(results['workload_updates'], list)
    
    @pytest.mark.asyncio
    async def test_plan_learning_sessions(self, orchestration_system):
        """Test planning learning sessions"""
        learning_requests = [
            {
                'objectives': ['Test objective 1', 'Test objective 2'],
                'learning_type': 'collaborative',
                'priority': 'medium',
                'deadline': '2024-01-16T18:00:00Z',
                'constraints': ['min_agents_2']
            }
        ]
        
        agent_statuses = {
            'raw_data_intelligence': {'status': 'active', 'capacity': 0.5},
            'pattern_intelligence': {'status': 'active', 'capacity': 0.7}
        }
        
        session_plans = await orchestration_system._plan_learning_sessions(learning_requests, agent_statuses)
        
        assert isinstance(session_plans, list)
        if session_plans:
            plan = session_plans[0]
            assert 'session_id' in plan
            assert 'session_name' in plan
            assert 'learning_type' in plan
            assert 'participating_agents' in plan
            assert 'session_goals' in plan
            assert 'task_count' in plan
            assert 'plan_quality' in plan
            assert 'created_at' in plan
    
    @pytest.mark.asyncio
    async def test_generate_learning_plan(self, orchestration_system):
        """Test generating learning plan"""
        planning_data = {
            'learning_objectives': ['Objective 1', 'Objective 2'],
            'available_agents': ['agent1', 'agent2'],
            'agent_capabilities': {'agent1': {'capability': 'test'}},
            'learning_type': 'distributed',
            'priority': 'high',
            'deadline': '2024-01-15T12:00:00Z',
            'constraints': ['constraint1']
        }
        
        plan = await orchestration_system._generate_learning_plan(planning_data)
        
        assert plan is not None
        assert 'session_plan' in plan
        assert 'learning_insights' in plan
        assert 'uncertainty_flags' in plan
        assert 'session_name' in plan['session_plan']
        assert 'learning_type' in plan['session_plan']
        assert 'participating_agents' in plan['session_plan']
    
    @pytest.mark.asyncio
    async def test_create_learning_tasks(self, orchestration_system):
        """Test creating learning tasks"""
        session = LearningSession(
            session_id="TEST_SESSION_123",
            session_name="Test Session",
            learning_type=LearningType.DISTRIBUTED,
            participating_agents=['agent1', 'agent2'],
            session_goals=['Goal 1', 'Goal 2'],
            session_plan={
                'task_distribution': {
                    'agent1': ['Task 1', 'Task 2'],
                    'agent2': ['Task 3']
                }
            },
            current_phase=LearningPhase.PLANNING,
            session_status=LearningStatus.PENDING,
            progress_metrics={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=None
        )
        
        session_plan = {
            'task_distribution': {
                'agent1': ['Task 1', 'Task 2'],
                'agent2': ['Task 3']
            }
        }
        
        tasks = await orchestration_system._create_learning_tasks(session, session_plan)
        
        assert len(tasks) == 3
        assert all(isinstance(task, LearningTask) for task in tasks)
        assert all(task.learning_type == LearningType.DISTRIBUTED for task in tasks)
        assert all(task.status == LearningStatus.PENDING for task in tasks)
        assert all(task.task_requirements['session_id'] == session.session_id for task in tasks)
    
    @pytest.mark.asyncio
    async def test_coordinate_learning_sessions(self, orchestration_system):
        """Test coordinating learning sessions"""
        # Add an active session
        session = LearningSession(
            session_id="TEST_SESSION_456",
            session_name="Test Active Session",
            learning_type=LearningType.COLLABORATIVE,
            participating_agents=['agent1', 'agent2'],
            session_goals=['Goal 1'],
            session_plan={
                'coordination_plan': {
                    'coordination_type': 'hierarchical',
                    'coordination_schedule': 'every_15_minutes'
                }
            },
            current_phase=LearningPhase.COORDINATION,
            session_status=LearningStatus.ACTIVE,
            progress_metrics={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=None
        )
        
        orchestration_system.active_sessions[session.session_id] = session
        
        coordination_results = await orchestration_system._coordinate_learning_sessions()
        
        assert isinstance(coordination_results, list)
        if coordination_results:
            result = coordination_results[0]
            assert 'coordination_id' in result
            assert 'session_id' in result
            assert 'coordination_actions' in result
            assert 'coordination_insights' in result
            assert 'next_phase_recommendations' in result
            assert 'created_at' in result
    
    def test_get_agent_progress(self, orchestration_system):
        """Test getting agent progress"""
        session = LearningSession(
            session_id="TEST_SESSION_789",
            session_name="Test Progress Session",
            learning_type=LearningType.DISTRIBUTED,
            participating_agents=['agent1', 'agent2'],
            session_goals=['Goal 1'],
            session_plan={},
            current_phase=LearningPhase.EXECUTION,
            session_status=LearningStatus.ACTIVE,
            progress_metrics={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=None
        )
        
        # Add some tasks
        task1 = LearningTask(
            task_id="TASK_1",
            learning_type=LearningType.DISTRIBUTED,
            learning_phase=LearningPhase.EXECUTION,
            task_description="Task 1",
            assigned_agents=['agent1'],
            task_requirements={'session_id': session.session_id},
            dependencies=[],
            priority=1,
            status=LearningStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deadline=None
        )
        
        task2 = LearningTask(
            task_id="TASK_2",
            learning_type=LearningType.DISTRIBUTED,
            learning_phase=LearningPhase.EXECUTION,
            task_description="Task 2",
            assigned_agents=['agent1'],
            task_requirements={'session_id': session.session_id},
            dependencies=[],
            priority=1,
            status=LearningStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deadline=None
        )
        
        orchestration_system.learning_tasks[task1.task_id] = task1
        orchestration_system.learning_tasks[task2.task_id] = task2
        
        progress = orchestration_system._get_agent_progress(session)
        
        assert 'agent1' in progress
        assert progress['agent1']['completed_tasks'] == 1
        assert progress['agent1']['total_tasks'] == 2
        assert progress['agent1']['progress_percentage'] == 50.0
        assert progress['agent1']['current_status'] == 'active'
    
    def test_identify_current_issues(self, orchestration_system):
        """Test identifying current issues"""
        session = LearningSession(
            session_id="TEST_SESSION_ISSUES",
            session_name="Test Issues Session",
            learning_type=LearningType.DISTRIBUTED,
            participating_agents=['agent1'],
            session_goals=['Goal 1'],
            session_plan={},
            current_phase=LearningPhase.EXECUTION,
            session_status=LearningStatus.ACTIVE,
            progress_metrics={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=None
        )
        
        # Add overdue task
        overdue_task = LearningTask(
            task_id="OVERDUE_TASK",
            learning_type=LearningType.DISTRIBUTED,
            learning_phase=LearningPhase.EXECUTION,
            task_description="Overdue Task",
            assigned_agents=['agent1'],
            task_requirements={'session_id': session.session_id},
            dependencies=[],
            priority=1,
            status=LearningStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deadline=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        orchestration_system.learning_tasks[overdue_task.task_id] = overdue_task
        
        issues = orchestration_system._identify_current_issues(session)
        
        assert isinstance(issues, list)
        assert any("overdue" in issue.lower() for issue in issues)
    
    @pytest.mark.asyncio
    async def test_generate_coordination(self, orchestration_system):
        """Test generating coordination"""
        coordination_data = {
            'session_id': 'TEST_SESSION',
            'learning_type': 'distributed',
            'current_phase': 'coordination',
            'participating_agents': ['agent1', 'agent2'],
            'agent_progress': {'agent1': {'progress_percentage': 50}},
            'coordination_requirements': {'type': 'hierarchical'},
            'current_issues': ['Issue 1']
        }
        
        coordination = await orchestration_system._generate_coordination(coordination_data)
        
        assert coordination is not None
        assert 'coordination_actions' in coordination
        assert 'coordination_insights' in coordination
        assert 'next_phase_recommendations' in coordination
        assert isinstance(coordination['coordination_actions'], list)
        assert isinstance(coordination['coordination_insights'], list)
        assert isinstance(coordination['next_phase_recommendations'], list)
    
    @pytest.mark.asyncio
    async def test_synthesize_learning_results(self, orchestration_system):
        """Test synthesizing learning results"""
        # Add session ready for synthesis
        session = LearningSession(
            session_id="TEST_SYNTHESIS_SESSION",
            session_name="Test Synthesis Session",
            learning_type=LearningType.DISTRIBUTED,
            participating_agents=['agent1', 'agent2'],
            session_goals=['Goal 1', 'Goal 2'],
            session_plan={'success_criteria': ['Criteria 1']},
            current_phase=LearningPhase.SYNTHESIS,
            session_status=LearningStatus.ACTIVE,
            progress_metrics={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=None
        )
        
        orchestration_system.active_sessions[session.session_id] = session
        
        synthesis_results = await orchestration_system._synthesize_learning_results()
        
        assert isinstance(synthesis_results, list)
        if synthesis_results:
            result = synthesis_results[0]
            assert 'synthesis_id' in result
            assert 'session_id' in result
            assert 'synthesis_output' in result
            assert 'synthesis_quality' in result
            assert 'synthesis_confidence' in result
            assert 'created_at' in result
    
    def test_collect_agent_results(self, orchestration_system):
        """Test collecting agent results"""
        session = LearningSession(
            session_id="TEST_RESULTS_SESSION",
            session_name="Test Results Session",
            learning_type=LearningType.DISTRIBUTED,
            participating_agents=['agent1', 'agent2'],
            session_goals=['Goal 1'],
            session_plan={},
            current_phase=LearningPhase.SYNTHESIS,
            session_status=LearningStatus.ACTIVE,
            progress_metrics={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=None
        )
        
        # Add completed tasks
        completed_task = LearningTask(
            task_id="COMPLETED_TASK",
            learning_type=LearningType.DISTRIBUTED,
            learning_phase=LearningPhase.EXECUTION,
            task_description="Completed Task",
            assigned_agents=['agent1'],
            task_requirements={'session_id': session.session_id},
            dependencies=[],
            priority=1,
            status=LearningStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deadline=None
        )
        
        orchestration_system.learning_tasks[completed_task.task_id] = completed_task
        
        results = orchestration_system._collect_agent_results(session)
        
        assert isinstance(results, list)
        if results:
            result = results[0]
            assert 'agent_id' in result
            assert 'completed_tasks' in result
            assert 'task_results' in result
            assert 'performance_metrics' in result
            assert result['agent_id'] == 'agent1'
            assert result['completed_tasks'] == 1
    
    @pytest.mark.asyncio
    async def test_generate_synthesis(self, orchestration_system):
        """Test generating synthesis"""
        synthesis_data = {
            'session_id': 'TEST_SESSION',
            'learning_type': 'distributed',
            'synthesis_type': 'cross_agent_synthesis',
            'agent_results': [{'agent_id': 'agent1', 'completed_tasks': 2}],
            'learning_objectives': ['Objective 1'],
            'synthesis_requirements': ['Requirement 1']
        }
        
        synthesis = await orchestration_system._generate_synthesis(synthesis_data)
        
        assert synthesis is not None
        assert 'synthesis_output' in synthesis
        assert 'synthesis_quality' in synthesis
        assert 'synthesis_confidence' in synthesis
        assert 'uncertainty_flags' in synthesis
        assert isinstance(synthesis['synthesis_output'], dict)
        assert 0.0 <= synthesis['synthesis_quality'] <= 1.0
        assert 0.0 <= synthesis['synthesis_confidence'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_update_agent_workloads(self, orchestration_system):
        """Test updating agent workloads"""
        # Add some active tasks
        active_task = LearningTask(
            task_id="ACTIVE_TASK",
            learning_type=LearningType.DISTRIBUTED,
            learning_phase=LearningPhase.EXECUTION,
            task_description="Active Task",
            assigned_agents=['raw_data_intelligence'],
            task_requirements={},
            dependencies=[],
            priority=1,
            status=LearningStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            deadline=None
        )
        
        orchestration_system.learning_tasks[active_task.task_id] = active_task
        
        workload_updates = await orchestration_system._update_agent_workloads()
        
        assert isinstance(workload_updates, list)
        assert len(workload_updates) == 5  # All agents
        
        for update in workload_updates:
            assert 'agent_id' in update
            assert 'old_workload' in update
            assert 'new_workload' in update
            assert 'workload_change' in update
            assert 'capacity_utilization' in update
            assert 'updated_at' in update
            assert isinstance(update['old_workload'], int)
            assert isinstance(update['new_workload'], int)
            assert isinstance(update['workload_change'], int)
            assert isinstance(update['capacity_utilization'], float)
    
    @pytest.mark.asyncio
    async def test_generate_llm_analysis(self, orchestration_system):
        """Test generating LLM analysis"""
        prompt_template = "Test prompt with {test_field}"
        data = {'test_field': 'test_value'}
        
        result = await orchestration_system._generate_llm_analysis(prompt_template, data)
        
        assert result is not None
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_publish_orchestration_results(self, orchestration_system):
        """Test publishing orchestration results"""
        results = {
            'session_plans': [{'session_id': 'test_session'}],
            'coordination_results': [],
            'synthesis_results': [],
            'workload_updates': [],
            'orchestration_timestamp': datetime.now(timezone.utc),
            'orchestration_errors': []
        }
        
        await orchestration_system._publish_orchestration_results(results)
        
        # Verify supabase_manager.insert_strand was called
        orchestration_system.supabase_manager.insert_strand.assert_called_once()
        
        # Verify the strand structure
        call_args = orchestration_system.supabase_manager.insert_strand.call_args[0][0]
        assert 'id' in call_args
        assert 'kind' in call_args
        assert 'content' in call_args
        assert call_args['kind'] == 'cil_cross_agent_learning_orchestration'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['cil_team_member'] == 'cross_agent_learning_orchestration_system'
    
    def test_learning_type_enum(self):
        """Test LearningType enum values"""
        assert LearningType.DISTRIBUTED.value == "distributed"
        assert LearningType.COLLABORATIVE.value == "collaborative"
        assert LearningType.TRANSFER.value == "transfer"
        assert LearningType.META_LEARNING.value == "meta_learning"
        assert LearningType.FEDERATED.value == "federated"
    
    def test_learning_phase_enum(self):
        """Test LearningPhase enum values"""
        assert LearningPhase.PLANNING.value == "planning"
        assert LearningPhase.COORDINATION.value == "coordination"
        assert LearningPhase.EXECUTION.value == "execution"
        assert LearningPhase.SYNTHESIS.value == "synthesis"
        assert LearningPhase.VALIDATION.value == "validation"
    
    def test_learning_status_enum(self):
        """Test LearningStatus enum values"""
        assert LearningStatus.PENDING.value == "pending"
        assert LearningStatus.ACTIVE.value == "active"
        assert LearningStatus.COMPLETED.value == "completed"
        assert LearningStatus.FAILED.value == "failed"
        assert LearningStatus.SUSPENDED.value == "suspended"
    
    def test_agent_role_enum(self):
        """Test AgentRole enum values"""
        assert AgentRole.LEADER.value == "leader"
        assert AgentRole.FOLLOWER.value == "follower"
        assert AgentRole.COORDINATOR.value == "coordinator"
        assert AgentRole.VALIDATOR.value == "validator"
        assert AgentRole.SYNTHESIZER.value == "synthesizer"


if __name__ == "__main__":
    pytest.main([__file__])
