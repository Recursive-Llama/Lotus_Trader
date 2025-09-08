"""
Test suite for CIL Resonance Prioritization System
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from src.intelligence.system_control.central_intelligence_layer.missing_pieces.resonance_prioritization_system import (
    ResonancePrioritizationSystem,
    ExperimentPriority,
    ResonanceType,
    ExperimentStatus,
    ExperimentCandidate,
    ResonanceScore,
    PrioritizedQueue
)


class TestResonancePrioritizationSystem:
    """Test suite for ResonancePrioritizationSystem"""
    
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
    def prioritization_system(self, mock_supabase_manager, mock_llm_client):
        """Create ResonancePrioritizationSystem instance"""
        return ResonancePrioritizationSystem(mock_supabase_manager, mock_llm_client)
    
    def test_resonance_prioritization_system_initialization(self, prioritization_system):
        """Test system initialization"""
        assert prioritization_system.supabase_manager is not None
        assert prioritization_system.llm_client is not None
        assert prioritization_system.max_queue_size == 50
        assert prioritization_system.family_cap_percentage == 0.3
        assert prioritization_system.resonance_threshold == 0.6
        assert len(prioritization_system.priority_boost_factors) == 4
        assert len(prioritization_system.resonance_weights) == 5
        assert len(prioritization_system.experiment_candidates) == 0
        assert len(prioritization_system.resonance_scores) == 0
        assert len(prioritization_system.prioritized_queues) == 0
        assert len(prioritization_system.family_performance) == 10
    
    def test_initialize_family_performance(self, prioritization_system):
        """Test family performance initialization"""
        expected_families = [
            'divergence', 'volume', 'correlation', 'session', 'cross_asset',
            'pattern', 'indicator', 'microstructure', 'regime', 'volatility'
        ]
        
        for family in expected_families:
            assert family in prioritization_system.family_performance
            performance = prioritization_system.family_performance[family]
            assert 'success_rate' in performance
            assert 'completion_rate' in performance
            assert 'novelty_score' in performance
            assert 'persistence_score' in performance
            assert 'last_updated' in performance
            assert 0.0 <= performance['success_rate'] <= 1.0
            assert 0.0 <= performance['completion_rate'] <= 1.0
            assert 0.0 <= performance['novelty_score'] <= 1.0
            assert 0.0 <= performance['persistence_score'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_process_resonance_prioritization(self, prioritization_system):
        """Test processing resonance prioritization"""
        experiment_candidates = [
            {
                'candidate_id': 'TEST_CANDIDATE_1',
                'experiment_type': 'durability',
                'hypothesis': 'Test hypothesis 1',
                'target_agents': ['agent1', 'agent2'],
                'expected_conditions': {'regime': 'high_vol'},
                'success_metrics': {'accuracy': 0.8},
                'time_horizon': 'medium',
                'family': 'divergence',
                'priority': 'high'
            }
        ]
        
        system_context = {
            'recent_patterns': ['pattern1', 'pattern2'],
            'cross_agent_activity': {'agent1': 0.8},
            'temporal_trends': {'trend1': 0.5}
        }
        
        results = await prioritization_system.process_resonance_prioritization(
            experiment_candidates, system_context
        )
        
        assert 'added_candidates' in results
        assert 'resonance_calculations' in results
        assert 'queue_creation' in results
        assert 'performance_updates' in results
        assert 'prioritization_timestamp' in results
        assert 'prioritization_errors' in results
        assert isinstance(results['added_candidates'], list)
        assert isinstance(results['resonance_calculations'], list)
        assert isinstance(results['performance_updates'], list)
        assert isinstance(results['prioritization_errors'], list)
    
    @pytest.mark.asyncio
    async def test_add_experiment_candidates(self, prioritization_system):
        """Test adding experiment candidates"""
        candidates = [
            {
                'candidate_id': 'TEST_CANDIDATE_1',
                'experiment_type': 'durability',
                'hypothesis': 'Test hypothesis 1',
                'target_agents': ['agent1'],
                'expected_conditions': {'regime': 'high_vol'},
                'success_metrics': {'accuracy': 0.8},
                'time_horizon': 'medium',
                'family': 'divergence',
                'priority': 'high'
            },
            {
                'candidate_id': 'TEST_CANDIDATE_2',
                'experiment_type': 'stack',
                'hypothesis': 'Test hypothesis 2',
                'target_agents': ['agent2'],
                'expected_conditions': {'regime': 'sideways'},
                'success_metrics': {'accuracy': 0.9},
                'time_horizon': 'short',
                'family': 'volume',
                'priority': 'medium'
            }
        ]
        
        added_candidates = await prioritization_system._add_experiment_candidates(candidates)
        
        assert len(added_candidates) == 2
        assert 'TEST_CANDIDATE_1' in added_candidates
        assert 'TEST_CANDIDATE_2' in added_candidates
        
        # Verify candidates were added to system
        assert 'TEST_CANDIDATE_1' in prioritization_system.experiment_candidates
        assert 'TEST_CANDIDATE_2' in prioritization_system.experiment_candidates
        
        candidate1 = prioritization_system.experiment_candidates['TEST_CANDIDATE_1']
        assert candidate1.experiment_type == 'durability'
        assert candidate1.hypothesis == 'Test hypothesis 1'
        assert candidate1.family == 'divergence'
        assert candidate1.priority == ExperimentPriority.HIGH
        assert candidate1.status == ExperimentStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_calculate_resonance_scores(self, prioritization_system):
        """Test calculating resonance scores"""
        # Add a candidate first
        candidates = [{
            'candidate_id': 'TEST_CANDIDATE_1',
            'experiment_type': 'durability',
            'hypothesis': 'Test hypothesis',
            'target_agents': ['agent1'],
            'expected_conditions': {'regime': 'high_vol'},
            'success_metrics': {'accuracy': 0.8},
            'time_horizon': 'medium',
            'family': 'divergence',
            'priority': 'high'
        }]
        
        await prioritization_system._add_experiment_candidates(candidates)
        
        system_context = {
            'recent_patterns': ['pattern1'],
            'cross_agent_activity': {'agent1': 0.8},
            'temporal_trends': {'trend1': 0.5}
        }
        
        resonance_calculations = await prioritization_system._calculate_resonance_scores(
            ['TEST_CANDIDATE_1'], system_context
        )
        
        assert len(resonance_calculations) == 1
        calculation = resonance_calculations[0]
        assert 'candidate_id' in calculation
        assert 'resonance_score' in calculation
        assert 'resonance_insights' in calculation
        assert 'prioritization_recommendations' in calculation
        assert 'uncertainty_flags' in calculation
        assert calculation['candidate_id'] == 'TEST_CANDIDATE_1'
        assert isinstance(calculation['resonance_score'], ResonanceScore)
    
    @pytest.mark.asyncio
    async def test_generate_resonance_analysis(self, prioritization_system):
        """Test generating resonance analysis"""
        analysis_data = {
            'experiment_type': 'durability',
            'hypothesis': 'Test hypothesis',
            'target_agents': ['agent1'],
            'expected_conditions': {'regime': 'high_vol'},
            'success_metrics': {'accuracy': 0.8},
            'time_horizon': 'medium',
            'family': 'divergence',
            'context': {'test': 'value'},
            'family_performance': {'success_rate': 0.7},
            'recent_patterns': ['pattern1'],
            'cross_agent_activity': {'agent1': 0.8},
            'temporal_trends': {'trend1': 0.5}
        }
        
        analysis = await prioritization_system._generate_resonance_analysis(analysis_data)
        
        assert analysis is not None
        assert 'resonance_analysis' in analysis
        assert 'resonance_insights' in analysis
        assert 'prioritization_recommendations' in analysis
        assert 'uncertainty_flags' in analysis
        
        resonance_analysis = analysis['resonance_analysis']
        assert 'pattern_resonance' in resonance_analysis
        assert 'family_resonance' in resonance_analysis
        assert 'cross_agent_resonance' in resonance_analysis
        assert 'temporal_resonance' in resonance_analysis
        assert 'contextual_resonance' in resonance_analysis
        assert 'overall_resonance' in resonance_analysis
        assert 'confidence' in resonance_analysis
        
        # Verify resonance scores are in valid range
        for key in ['pattern_resonance', 'family_resonance', 'cross_agent_resonance', 
                   'temporal_resonance', 'contextual_resonance', 'overall_resonance', 'confidence']:
            assert 0.0 <= resonance_analysis[key] <= 1.0
    
    @pytest.mark.asyncio
    async def test_create_prioritized_queue(self, prioritization_system):
        """Test creating prioritized queue"""
        # Add candidates and calculate resonance scores first
        candidates = [
            {
                'candidate_id': 'TEST_CANDIDATE_1',
                'experiment_type': 'durability',
                'hypothesis': 'Test hypothesis 1',
                'target_agents': ['agent1'],
                'expected_conditions': {'regime': 'high_vol'},
                'success_metrics': {'accuracy': 0.8},
                'time_horizon': 'medium',
                'family': 'divergence',
                'priority': 'high'
            },
            {
                'candidate_id': 'TEST_CANDIDATE_2',
                'experiment_type': 'stack',
                'hypothesis': 'Test hypothesis 2',
                'target_agents': ['agent2'],
                'expected_conditions': {'regime': 'sideways'},
                'success_metrics': {'accuracy': 0.9},
                'time_horizon': 'short',
                'family': 'volume',
                'priority': 'medium'
            }
        ]
        
        await prioritization_system._add_experiment_candidates(candidates)
        
        system_context = {
            'recent_patterns': ['pattern1'],
            'cross_agent_activity': {'agent1': 0.8, 'agent2': 0.6},
            'temporal_trends': {'trend1': 0.5}
        }
        
        resonance_calculations = await prioritization_system._calculate_resonance_scores(
            ['TEST_CANDIDATE_1', 'TEST_CANDIDATE_2'], system_context
        )
        
        queue_creation = await prioritization_system._create_prioritized_queue(
            resonance_calculations, system_context
        )
        
        assert 'queue_id' in queue_creation
        assert 'queue_name' in queue_creation
        assert 'queue_order' in queue_creation
        assert 'family_distribution' in queue_creation
        assert 'resonance_distribution' in queue_creation
        assert 'resource_allocation' in queue_creation
        assert 'prioritization_insights' in queue_creation
        assert 'constraint_violations' in queue_creation
        assert 'optimization_suggestions' in queue_creation
        assert 'created_at' in queue_creation
        
        assert isinstance(queue_creation['queue_order'], list)
        assert isinstance(queue_creation['family_distribution'], dict)
        assert isinstance(queue_creation['resonance_distribution'], dict)
        assert isinstance(queue_creation['resource_allocation'], dict)
    
    def test_calculate_family_caps(self, prioritization_system):
        """Test calculating family caps"""
        # Add some candidates with different families
        candidates = [
            ExperimentCandidate(
                candidate_id='CANDIDATE_1',
                experiment_type='durability',
                hypothesis='Test 1',
                target_agents=['agent1'],
                expected_conditions={},
                success_metrics={},
                time_horizon='medium',
                resource_requirements={},
                family='divergence',
                context={},
                created_at=datetime.now(timezone.utc),
                priority=ExperimentPriority.HIGH,
                status=ExperimentStatus.PENDING
            ),
            ExperimentCandidate(
                candidate_id='CANDIDATE_2',
                experiment_type='stack',
                hypothesis='Test 2',
                target_agents=['agent2'],
                expected_conditions={},
                success_metrics={},
                time_horizon='short',
                resource_requirements={},
                family='divergence',
                context={},
                created_at=datetime.now(timezone.utc),
                priority=ExperimentPriority.MEDIUM,
                status=ExperimentStatus.PENDING
            ),
            ExperimentCandidate(
                candidate_id='CANDIDATE_3',
                experiment_type='lead_lag',
                hypothesis='Test 3',
                target_agents=['agent3'],
                expected_conditions={},
                success_metrics={},
                time_horizon='long',
                resource_requirements={},
                family='volume',
                context={},
                created_at=datetime.now(timezone.utc),
                priority=ExperimentPriority.LOW,
                status=ExperimentStatus.PENDING
            )
        ]
        
        for candidate in candidates:
            prioritization_system.experiment_candidates[candidate.candidate_id] = candidate
        
        family_caps = prioritization_system._calculate_family_caps()
        
        assert 'divergence' in family_caps
        assert 'volume' in family_caps
        assert family_caps['divergence'] >= 1  # At least 1
        assert family_caps['volume'] >= 1  # At least 1
        assert family_caps['divergence'] >= family_caps['volume']  # More divergence candidates
    
    @pytest.mark.asyncio
    async def test_generate_prioritization(self, prioritization_system):
        """Test generating prioritization"""
        prioritization_data = {
            'candidates_with_scores': [
                {
                    'candidate_id': 'CANDIDATE_1',
                    'experiment_type': 'durability',
                    'family': 'divergence',
                    'priority': 'high',
                    'resonance_score': 0.8,
                    'confidence': 0.9,
                    'target_agents': ['agent1'],
                    'resource_requirements': {}
                }
            ],
            'max_queue_size': 50,
            'family_cap_percentage': 0.3,
            'current_queue': ['CANDIDATE_1'],
            'family_caps': {'divergence': 2}
        }
        
        prioritization = await prioritization_system._generate_prioritization(prioritization_data)
        
        assert prioritization is not None
        assert 'prioritized_queue' in prioritization
        assert 'prioritization_insights' in prioritization
        assert 'constraint_violations' in prioritization
        assert 'optimization_suggestions' in prioritization
        
        queue = prioritization['prioritized_queue']
        assert 'queue_order' in queue
        assert 'family_distribution' in queue
        assert 'resonance_distribution' in queue
        assert 'resource_allocation' in queue
        
        assert isinstance(queue['queue_order'], list)
        assert isinstance(queue['family_distribution'], dict)
        assert isinstance(queue['resonance_distribution'], dict)
        assert isinstance(queue['resource_allocation'], dict)
    
    @pytest.mark.asyncio
    async def test_update_family_performance(self, prioritization_system):
        """Test updating family performance"""
        performance_updates = await prioritization_system._update_family_performance()
        
        assert isinstance(performance_updates, list)
        assert len(performance_updates) == 10  # 10 families
        
        for update in performance_updates:
            assert 'family' in update
            assert 'old_performance' in update
            assert 'new_performance' in update
            assert 'updated_at' in update
            
            family = update['family']
            old_perf = update['old_performance']
            new_perf = update['new_performance']
            
            # Verify performance metrics were updated
            assert new_perf['success_rate'] >= old_perf['success_rate']
            assert new_perf['completion_rate'] >= old_perf['completion_rate']
            assert new_perf['novelty_score'] <= old_perf['novelty_score']  # Decreases over time
            assert new_perf['persistence_score'] >= old_perf['persistence_score']
            
            # Verify all metrics are in valid range
            for metric in ['success_rate', 'completion_rate', 'novelty_score', 'persistence_score']:
                assert 0.0 <= new_perf[metric] <= 1.0
    
    @pytest.mark.asyncio
    async def test_generate_llm_analysis(self, prioritization_system):
        """Test generating LLM analysis"""
        prompt_template = "Test prompt with {test_field}"
        data = {'test_field': 'test_value'}
        
        result = await prioritization_system._generate_llm_analysis(prompt_template, data)
        
        assert result is not None
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_publish_prioritization_results(self, prioritization_system):
        """Test publishing prioritization results"""
        results = {
            'added_candidates': ['CANDIDATE_1'],
            'resonance_calculations': [{'candidate_id': 'CANDIDATE_1'}],
            'queue_creation': {'queue_id': 'QUEUE_1'},
            'performance_updates': [{'family': 'divergence'}],
            'prioritization_timestamp': datetime.now(timezone.utc),
            'prioritization_errors': []
        }
        
        await prioritization_system._publish_prioritization_results(results)
        
        # Verify supabase_manager.insert_strand was called
        prioritization_system.supabase_manager.insert_strand.assert_called_once()
        
        # Verify the strand structure
        call_args = prioritization_system.supabase_manager.insert_strand.call_args[0][0]
        assert 'id' in call_args
        assert 'kind' in call_args
        assert 'content' in call_args
        assert call_args['kind'] == 'cil_resonance_prioritization'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['cil_team_member'] == 'resonance_prioritization_system'
    
    def test_experiment_priority_enum(self):
        """Test ExperimentPriority enum values"""
        assert ExperimentPriority.LOW.value == "low"
        assert ExperimentPriority.MEDIUM.value == "medium"
        assert ExperimentPriority.HIGH.value == "high"
        assert ExperimentPriority.CRITICAL.value == "critical"
    
    def test_resonance_type_enum(self):
        """Test ResonanceType enum values"""
        assert ResonanceType.PATTERN_RESONANCE.value == "pattern_resonance"
        assert ResonanceType.FAMILY_RESONANCE.value == "family_resonance"
        assert ResonanceType.CROSS_AGENT_RESONANCE.value == "cross_agent_resonance"
        assert ResonanceType.TEMPORAL_RESONANCE.value == "temporal_resonance"
        assert ResonanceType.CONTEXTUAL_RESONANCE.value == "contextual_resonance"
    
    def test_experiment_status_enum(self):
        """Test ExperimentStatus enum values"""
        assert ExperimentStatus.PENDING.value == "pending"
        assert ExperimentStatus.QUEUED.value == "queued"
        assert ExperimentStatus.ACTIVE.value == "active"
        assert ExperimentStatus.COMPLETED.value == "completed"
        assert ExperimentStatus.FAILED.value == "failed"
        assert ExperimentStatus.CANCELLED.value == "cancelled"
    
    def test_experiment_candidate_dataclass(self):
        """Test ExperimentCandidate dataclass"""
        candidate = ExperimentCandidate(
            candidate_id='TEST_CANDIDATE',
            experiment_type='durability',
            hypothesis='Test hypothesis',
            target_agents=['agent1'],
            expected_conditions={'regime': 'high_vol'},
            success_metrics={'accuracy': 0.8},
            time_horizon='medium',
            resource_requirements={},
            family='divergence',
            context={},
            created_at=datetime.now(timezone.utc),
            priority=ExperimentPriority.HIGH,
            status=ExperimentStatus.PENDING
        )
        
        assert candidate.candidate_id == 'TEST_CANDIDATE'
        assert candidate.experiment_type == 'durability'
        assert candidate.hypothesis == 'Test hypothesis'
        assert candidate.target_agents == ['agent1']
        assert candidate.family == 'divergence'
        assert candidate.priority == ExperimentPriority.HIGH
        assert candidate.status == ExperimentStatus.PENDING
    
    def test_resonance_score_dataclass(self):
        """Test ResonanceScore dataclass"""
        score = ResonanceScore(
            candidate_id='TEST_CANDIDATE',
            pattern_resonance=0.8,
            family_resonance=0.7,
            cross_agent_resonance=0.9,
            temporal_resonance=0.6,
            contextual_resonance=0.75,
            overall_resonance=0.75,
            confidence=0.85,
            calculated_at=datetime.now(timezone.utc)
        )
        
        assert score.candidate_id == 'TEST_CANDIDATE'
        assert score.pattern_resonance == 0.8
        assert score.family_resonance == 0.7
        assert score.cross_agent_resonance == 0.9
        assert score.temporal_resonance == 0.6
        assert score.contextual_resonance == 0.75
        assert score.overall_resonance == 0.75
        assert score.confidence == 0.85
    
    def test_prioritized_queue_dataclass(self):
        """Test PrioritizedQueue dataclass"""
        candidates = [
            ExperimentCandidate(
                candidate_id='CANDIDATE_1',
                experiment_type='durability',
                hypothesis='Test 1',
                target_agents=['agent1'],
                expected_conditions={},
                success_metrics={},
                time_horizon='medium',
                resource_requirements={},
                family='divergence',
                context={},
                created_at=datetime.now(timezone.utc),
                priority=ExperimentPriority.HIGH,
                status=ExperimentStatus.PENDING
            )
        ]
        
        resonance_scores = {
            'CANDIDATE_1': ResonanceScore(
                candidate_id='CANDIDATE_1',
                pattern_resonance=0.8,
                family_resonance=0.7,
                cross_agent_resonance=0.9,
                temporal_resonance=0.6,
                contextual_resonance=0.75,
                overall_resonance=0.75,
                confidence=0.85,
                calculated_at=datetime.now(timezone.utc)
            )
        }
        
        queue = PrioritizedQueue(
            queue_id='TEST_QUEUE',
            queue_name='Test Queue',
            candidates=candidates,
            resonance_scores=resonance_scores,
            queue_order=['CANDIDATE_1'],
            family_caps={'divergence': 2},
            total_capacity=50,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert queue.queue_id == 'TEST_QUEUE'
        assert queue.queue_name == 'Test Queue'
        assert len(queue.candidates) == 1
        assert len(queue.resonance_scores) == 1
        assert queue.queue_order == ['CANDIDATE_1']
        assert queue.family_caps == {'divergence': 2}
        assert queue.total_capacity == 50


if __name__ == "__main__":
    pytest.main([__file__])
