"""
Test CIL Experiment Orchestration Engine
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.engines.experiment_orchestration_engine import (
    ExperimentOrchestrationEngine, ExperimentShape, ExperimentStatus,
    ExperimentHypothesis, ExperimentDesign, ExperimentAssignment, ExperimentResult
)


class TestExperimentOrchestrationEngine:
    """Test CIL Experiment Orchestration Engine"""
    
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
    def orchestration_engine(self, mock_supabase_manager, mock_llm_client):
        """Create ExperimentOrchestrationEngine instance"""
        return ExperimentOrchestrationEngine(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_global_view(self):
        """Mock global view"""
        return {
            'cross_agent_correlation': {
                'correlation_strength': 0.8,
                'confluence_events': [
                    {'similarity_score': 0.9, 'timestamp': datetime.now(timezone.utc)},
                    {'similarity_score': 0.8, 'timestamp': datetime.now(timezone.utc)}
                ],
                'lead_lag_patterns': [
                    {'lead_agent': 'agent_1', 'lag_agent': 'agent_2', 'lead_lag_score': 0.7}
                ]
            },
            'coverage_analysis': {
                'blind_spots': [
                    {'context_key': 'BTC_1h_high_vol_US', 'priority': 'high'}
                ],
                'coverage_gaps': [
                    {'context_key': 'ETH_4h_low_vol_EU', 'gap_severity': 3}
                ]
            },
            'signal_families': [
                Mock(family_name='divergence', family_strength=0.9, evolution_trend='improving'),
                Mock(family_name='volume_spike', family_strength=0.6, evolution_trend='declining')
            ],
            'meta_patterns': [
                Mock(pattern_name='confluence_pattern', strength_score=0.8),
                Mock(pattern_name='lead_lag_pattern', strength_score=0.7)
            ],
            'doctrine_insights': [
                Mock(insight_type='family_strength', confidence_level=0.9),
                Mock(insight_type='evolution_trend', confidence_level=0.8)
            ]
        }
    
    def test_orchestration_engine_initialization(self, orchestration_engine):
        """Test ExperimentOrchestrationEngine initialization"""
        assert orchestration_engine.supabase_manager is not None
        assert orchestration_engine.llm_client is not None
        assert orchestration_engine.max_concurrent_experiments == 10
        assert orchestration_engine.experiment_timeout_hours == 24
        assert orchestration_engine.min_sample_size == 10
        assert orchestration_engine.success_threshold == 0.7
        assert orchestration_engine.novelty_threshold == 0.6
        assert 'raw_data_intelligence' in orchestration_engine.agent_capabilities
    
    @pytest.mark.asyncio
    async def test_orchestrate_experiments_success(self, orchestration_engine, mock_global_view):
        """Test successful experiment orchestration"""
        # Mock the individual orchestration methods
        with patch.object(orchestration_engine, 'generate_experiment_ideas') as mock_ideas, \
             patch.object(orchestration_engine, 'design_experiments') as mock_designs, \
             patch.object(orchestration_engine, 'assign_experiments') as mock_assignments, \
             patch.object(orchestration_engine, 'track_experiment_progress') as mock_tracking, \
             patch.object(orchestration_engine, 'process_experiment_results') as mock_results:
            
            # Set up mock returns
            mock_ideas.return_value = [{'trigger': 'test_trigger', 'rationale': 'test_rationale'}]
            mock_designs.return_value = []
            mock_assignments.return_value = []
            mock_tracking.return_value = []
            mock_results.return_value = []
            
            # Orchestrate experiments
            result = await orchestration_engine.orchestrate_experiments(mock_global_view)
            
            # Verify structure
            assert 'experiment_ideas' in result
            assert 'experiment_designs' in result
            assert 'experiment_assignments' in result
            assert 'active_experiments' in result
            assert 'completed_experiments' in result
            assert 'orchestration_timestamp' in result
            assert 'orchestration_errors' in result
            
            # Verify processing timestamp
            assert isinstance(result['orchestration_timestamp'], datetime)
    
    @pytest.mark.asyncio
    async def test_generate_experiment_ideas(self, orchestration_engine, mock_global_view):
        """Test experiment idea generation"""
        # Mock the individual idea generation methods
        with patch.object(orchestration_engine, '_generate_correlation_experiment_ideas') as mock_correlation, \
             patch.object(orchestration_engine, '_generate_coverage_experiment_ideas') as mock_coverage, \
             patch.object(orchestration_engine, '_generate_family_experiment_ideas') as mock_family, \
             patch.object(orchestration_engine, '_generate_pattern_experiment_ideas') as mock_pattern, \
             patch.object(orchestration_engine, '_generate_doctrine_experiment_ideas') as mock_doctrine:
            
            # Set up mock returns
            mock_correlation.return_value = [{'trigger': 'correlation_trigger', 'rationale': 'correlation_rationale'}]
            mock_coverage.return_value = [{'trigger': 'coverage_trigger', 'rationale': 'coverage_rationale'}]
            mock_family.return_value = [{'trigger': 'family_trigger', 'rationale': 'family_rationale'}]
            mock_pattern.return_value = [{'trigger': 'pattern_trigger', 'rationale': 'pattern_rationale'}]
            mock_doctrine.return_value = [{'trigger': 'doctrine_trigger', 'rationale': 'doctrine_rationale'}]
            
            # Generate experiment ideas
            ideas = await orchestration_engine.generate_experiment_ideas(mock_global_view)
            
            # Verify results
            assert isinstance(ideas, list)
            assert len(ideas) == 5  # One from each category
            assert all('trigger' in idea for idea in ideas)
            assert all('rationale' in idea for idea in ideas)
    
    @pytest.mark.asyncio
    async def test_design_experiments(self, orchestration_engine, mock_global_view):
        """Test experiment design"""
        # Mock generate_experiment_ideas
        with patch.object(orchestration_engine, 'generate_experiment_ideas') as mock_ideas:
            mock_ideas.return_value = [
                {
                    'trigger': 'test_trigger',
                    'rationale': 'test_rationale',
                    'experiment_type': 'divergence_test',
                    'priority': 'high',
                    'expected_conditions': {'threshold': 0.8}
                }
            ]
            
            # Design experiments
            designs = await orchestration_engine.design_experiments(mock_global_view)
            
            # Verify results
            assert isinstance(designs, list)
            if designs:  # Only check if designs were created
                design = designs[0]
                assert isinstance(design, ExperimentDesign)
                assert design.experiment_id.startswith('EXP_')
                assert isinstance(design.hypothesis, ExperimentHypothesis)
                assert design.shape in ExperimentShape
                assert isinstance(design.target_agents, list)
                assert isinstance(design.parameter_sweeps, dict)
                assert isinstance(design.guardrails, dict)
                assert isinstance(design.tracking_requirements, list)
                assert design.ttl_hours == orchestration_engine.experiment_timeout_hours
                assert 0.0 <= design.priority_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_assign_experiments(self, orchestration_engine, mock_global_view):
        """Test experiment assignment"""
        # Mock design_experiments and _get_active_experiments
        with patch.object(orchestration_engine, 'design_experiments') as mock_designs, \
             patch.object(orchestration_engine, '_get_active_experiments') as mock_active:
            
            # Create mock experiment design
            mock_hypothesis = ExperimentHypothesis(
                hypothesis_id='HYP_123',
                hypothesis_text='Test hypothesis',
                expected_conditions={'threshold': 0.8},
                success_metrics={'accuracy': 0.8},
                time_horizon='24_hours',
                confidence_level=0.8,
                evidence_basis=['test_evidence']
            )
            
            mock_design = ExperimentDesign(
                experiment_id='EXP_123',
                hypothesis=mock_hypothesis,
                shape=ExperimentShape.DURABILITY,
                target_agents=['raw_data_intelligence'],
                parameter_sweeps={'threshold': [0.5, 0.7, 0.9]},
                guardrails={'max_runtime_hours': 24},
                tracking_requirements=['performance_metrics'],
                ttl_hours=24,
                priority_score=0.8
            )
            
            mock_designs.return_value = [mock_design]
            mock_active.return_value = []  # No active experiments
            
            # Assign experiments
            assignments = await orchestration_engine.assign_experiments(mock_global_view)
            
            # Verify results
            assert isinstance(assignments, list)
            if assignments:  # Only check if assignments were created
                assignment = assignments[0]
                assert isinstance(assignment, ExperimentAssignment)
                assert assignment.assignment_id.startswith('ASSIGN_')
                assert assignment.experiment_id == 'EXP_123'
                assert assignment.target_agent == 'raw_data_intelligence'
                assert assignment.assignment_type in ['strict', 'bounded', 'exploratory']
                assert isinstance(assignment.directives, dict)
                assert isinstance(assignment.success_criteria, dict)
                assert isinstance(assignment.reporting_requirements, list)
                assert isinstance(assignment.deadline, datetime)
    
    @pytest.mark.asyncio
    async def test_track_experiment_progress(self, orchestration_engine, mock_supabase_manager):
        """Test experiment progress tracking"""
        # Mock database response
        mock_supabase_manager.execute_query.return_value = [
            {
                'id': 'assignment_1',
                'experiment_id': 'EXP_123',
                'target_agent': 'raw_data_intelligence',
                'assignment_type': 'strict',
                'deadline': datetime.now(timezone.utc) + timedelta(hours=1),
                'created_at': datetime.now(timezone.utc)
            }
        ]
        
        # Track experiment progress
        active_experiments = await orchestration_engine.track_experiment_progress()
        
        # Verify results
        assert isinstance(active_experiments, list)
        assert len(active_experiments) == 1
        assert active_experiments[0]['experiment_id'] == 'EXP_123'
    
    @pytest.mark.asyncio
    async def test_process_experiment_results(self, orchestration_engine, mock_supabase_manager):
        """Test experiment result processing"""
        # Mock database response
        mock_supabase_manager.execute_query.return_value = [
            {
                'id': 'result_1',
                'experiment_id': 'EXP_123',
                'agent_id': 'raw_data_intelligence',
                'module_intelligence': {
                    'outcome': 'success',
                    'metrics': {'accuracy': 0.8, 'precision': 0.7},
                    'lessons_learned': ['lesson_1', 'lesson_2'],
                    'recommendations': ['recommendation_1'],
                    'confidence_score': 0.8
                },
                'created_at': datetime.now(timezone.utc)
            }
        ]
        
        # Process experiment results
        results = await orchestration_engine.process_experiment_results()
        
        # Verify results
        assert isinstance(results, list)
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExperimentResult)
        assert result.result_id == 'result_1'
        assert result.experiment_id == 'EXP_123'
        assert result.agent_id == 'raw_data_intelligence'
        assert result.outcome == 'success'
        assert isinstance(result.metrics, dict)
        assert isinstance(result.lessons_learned, list)
        assert isinstance(result.recommendations, list)
        assert result.confidence_score == 0.8
        assert isinstance(result.completion_time, datetime)
    
    @pytest.mark.asyncio
    async def test_generate_correlation_experiment_ideas(self, orchestration_engine):
        """Test correlation experiment idea generation"""
        cross_agent_correlation = {
            'correlation_strength': 0.8,
            'confluence_events': [
                {'similarity_score': 0.9},
                {'similarity_score': 0.8},
                {'similarity_score': 0.7},
                {'similarity_score': 0.6}
            ],
            'lead_lag_patterns': [
                {'lead_agent': 'agent_1', 'lag_agent': 'agent_2', 'lead_lag_score': 0.7}
            ]
        }
        
        ideas = await orchestration_engine._generate_correlation_experiment_ideas(cross_agent_correlation)
        
        # Verify results
        assert isinstance(ideas, list)
        assert len(ideas) >= 1  # Should have at least one idea for high correlation
        assert any('high_correlation_strength' in idea['trigger'] for idea in ideas)
        assert any('multiple_confluence_events' in idea['trigger'] for idea in ideas)
        assert any('lead_lag_patterns' in idea['trigger'] for idea in ideas)
    
    @pytest.mark.asyncio
    async def test_generate_coverage_experiment_ideas(self, orchestration_engine):
        """Test coverage experiment idea generation"""
        coverage_analysis = {
            'blind_spots': [
                {'context_key': 'BTC_1h_high_vol_US', 'priority': 'high'},
                {'context_key': 'ETH_4h_low_vol_EU', 'priority': 'medium'}
            ],
            'coverage_gaps': [
                {'context_key': 'SOL_1d_medium_vol_ASIA', 'gap_severity': 3}
            ]
        }
        
        ideas = await orchestration_engine._generate_coverage_experiment_ideas(coverage_analysis)
        
        # Verify results
        assert isinstance(ideas, list)
        assert len(ideas) >= 1  # Should have at least one idea for blind spots
        assert any('blind_spots_detected' in idea['trigger'] for idea in ideas)
        assert any('coverage_gaps_detected' in idea['trigger'] for idea in ideas)
    
    @pytest.mark.asyncio
    async def test_generate_family_experiment_ideas(self, orchestration_engine):
        """Test family experiment idea generation"""
        signal_families = [
            Mock(family_name='divergence', family_strength=0.9, evolution_trend='improving'),
            Mock(family_name='volume_spike', family_strength=0.6, evolution_trend='declining'),
            Mock(family_name='pattern_recognition', family_strength=0.5, evolution_trend='stable')
        ]
        
        ideas = await orchestration_engine._generate_family_experiment_ideas(signal_families)
        
        # Verify results
        assert isinstance(ideas, list)
        assert len(ideas) >= 1  # Should have at least one idea for strong family
        assert any('strong_family_durability' in idea['trigger'] for idea in ideas)
        assert any('declining_family' in idea['trigger'] for idea in ideas)
    
    @pytest.mark.asyncio
    async def test_generate_pattern_experiment_ideas(self, orchestration_engine):
        """Test pattern experiment idea generation"""
        meta_patterns = [
            Mock(pattern_name='confluence_pattern', strength_score=0.9),
            Mock(pattern_name='lead_lag_pattern', strength_score=0.7),
            Mock(pattern_name='weak_pattern', strength_score=0.5)
        ]
        
        ideas = await orchestration_engine._generate_pattern_experiment_ideas(meta_patterns)
        
        # Verify results
        assert isinstance(ideas, list)
        assert len(ideas) >= 1  # Should have at least one idea for strong pattern
        assert any('strong_meta_pattern' in idea['trigger'] for idea in ideas)
    
    @pytest.mark.asyncio
    async def test_generate_doctrine_experiment_ideas(self, orchestration_engine):
        """Test doctrine experiment idea generation"""
        doctrine_insights = [
            Mock(insight_type='family_strength', confidence_level=0.9),
            Mock(insight_type='evolution_trend', confidence_level=0.7),
            Mock(insight_type='weak_insight', confidence_level=0.5)
        ]
        
        ideas = await orchestration_engine._generate_doctrine_experiment_ideas(doctrine_insights)
        
        # Verify results
        assert isinstance(ideas, list)
        assert len(ideas) >= 1  # Should have at least one idea for high confidence insight
        assert any('high_confidence_insight' in idea['trigger'] for idea in ideas)
    
    @pytest.mark.asyncio
    async def test_create_experiment_hypothesis(self, orchestration_engine):
        """Test experiment hypothesis creation"""
        idea = {
            'trigger': 'test_trigger',
            'rationale': 'test_rationale',
            'expected_conditions': {'threshold': 0.8}
        }
        
        hypothesis = await orchestration_engine._create_experiment_hypothesis(idea)
        
        # Verify results
        assert isinstance(hypothesis, ExperimentHypothesis)
        assert hypothesis.hypothesis_id.startswith('HYP_')
        assert 'test_trigger' in hypothesis.hypothesis_text
        assert 'test_rationale' in hypothesis.hypothesis_text
        assert hypothesis.expected_conditions == {'threshold': 0.8}
        assert isinstance(hypothesis.success_metrics, dict)
        assert hypothesis.time_horizon == '24_hours'
        assert 0.0 <= hypothesis.confidence_level <= 1.0
        assert isinstance(hypothesis.evidence_basis, list)
    
    def test_determine_experiment_shape(self, orchestration_engine):
        """Test experiment shape determination"""
        # Test durability shape
        idea = {'experiment_type': 'durability_test'}
        shape = orchestration_engine._determine_experiment_shape(idea)
        assert shape == ExperimentShape.DURABILITY
        
        # Test stack shape
        idea = {'experiment_type': 'confluence_analysis'}
        shape = orchestration_engine._determine_experiment_shape(idea)
        assert shape == ExperimentShape.STACK
        
        # Test lead-lag shape
        idea = {'experiment_type': 'lead_lag_validation'}
        shape = orchestration_engine._determine_experiment_shape(idea)
        assert shape == ExperimentShape.LEAD_LAG
        
        # Test ablation shape
        idea = {'experiment_type': 'decline_analysis'}
        shape = orchestration_engine._determine_experiment_shape(idea)
        assert shape == ExperimentShape.ABLATION
        
        # Test boundary shape
        idea = {'experiment_type': 'gap_filling'}
        shape = orchestration_engine._determine_experiment_shape(idea)
        assert shape == ExperimentShape.BOUNDARY
        
        # Test default shape
        idea = {'experiment_type': 'unknown_type'}
        shape = orchestration_engine._determine_experiment_shape(idea)
        assert shape == ExperimentShape.DURABILITY
    
    def test_select_target_agents(self, orchestration_engine):
        """Test target agent selection"""
        idea = {'experiment_type': 'divergence_test'}
        hypothesis = Mock()
        
        agents = orchestration_engine._select_target_agents(idea, hypothesis)
        assert agents == ['raw_data_intelligence']
        
        idea = {'experiment_type': 'rsi_analysis'}
        agents = orchestration_engine._select_target_agents(idea, hypothesis)
        assert agents == ['indicator_intelligence']
        
        idea = {'experiment_type': 'pattern_validation'}
        agents = orchestration_engine._select_target_agents(idea, hypothesis)
        assert agents == ['pattern_intelligence']
        
        idea = {'experiment_type': 'parameter_optimization'}
        agents = orchestration_engine._select_target_agents(idea, hypothesis)
        assert agents == ['system_control']
        
        idea = {'experiment_type': 'complex_experiment'}
        agents = orchestration_engine._select_target_agents(idea, hypothesis)
        assert len(agents) > 1  # Should select multiple agents for complex experiments
    
    def test_design_parameter_sweeps(self, orchestration_engine):
        """Test parameter sweep design"""
        idea = {'experiment_type': 'divergence_test'}
        hypothesis = Mock()
        
        sweeps = orchestration_engine._design_parameter_sweeps(idea, hypothesis)
        assert isinstance(sweeps, dict)
        assert 'rsi_period' in sweeps
        assert 'divergence_threshold' in sweeps
        assert 'lookback_period' in sweeps
        
        idea = {'experiment_type': 'volume_analysis'}
        sweeps = orchestration_engine._design_parameter_sweeps(idea, hypothesis)
        assert isinstance(sweeps, dict)
        assert 'volume_threshold' in sweeps
        assert 'time_window' in sweeps
        assert 'smoothing_period' in sweeps
    
    def test_set_experiment_guardrails(self, orchestration_engine):
        """Test experiment guardrail setting"""
        idea = {'experiment_type': 'test_experiment'}
        hypothesis = Mock()
        
        guardrails = orchestration_engine._set_experiment_guardrails(idea, hypothesis)
        assert isinstance(guardrails, dict)
        assert 'max_runtime_hours' in guardrails
        assert 'min_sample_size' in guardrails
        assert 'max_false_positive_rate' in guardrails
        assert 'min_confidence_threshold' in guardrails
        assert 'stop_on_anomaly' in guardrails
        assert 'max_memory_usage_mb' in guardrails
    
    def test_define_tracking_requirements(self, orchestration_engine):
        """Test tracking requirements definition"""
        idea = {'experiment_type': 'test_experiment'}
        hypothesis = Mock()
        
        requirements = orchestration_engine._define_tracking_requirements(idea, hypothesis)
        assert isinstance(requirements, list)
        assert 'performance_metrics' in requirements
        assert 'confidence_scores' in requirements
        assert 'false_positive_rate' in requirements
        assert 'execution_time' in requirements
        assert 'resource_usage' in requirements
        assert 'anomaly_detection' in requirements
        assert 'lesson_learned' in requirements
    
    def test_calculate_priority_score(self, orchestration_engine):
        """Test priority score calculation"""
        idea = {'priority': 'high'}
        hypothesis = Mock(confidence_level=0.8)
        
        score = orchestration_engine._calculate_priority_score(idea, hypothesis)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # High priority should be high score
        
        idea = {'priority': 'low'}
        score = orchestration_engine._calculate_priority_score(idea, hypothesis)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Low priority should be low score
    
    @pytest.mark.asyncio
    async def test_get_active_experiments(self, orchestration_engine, mock_supabase_manager):
        """Test getting active experiments"""
        mock_supabase_manager.execute_query.return_value = [
            {
                'id': 'assignment_1',
                'experiment_id': 'EXP_123',
                'target_agent': 'raw_data_intelligence',
                'created_at': datetime.now(timezone.utc)
            }
        ]
        
        active_experiments = await orchestration_engine._get_active_experiments()
        
        assert isinstance(active_experiments, list)
        assert len(active_experiments) == 1
        assert active_experiments[0]['experiment_id'] == 'EXP_123'
    
    def test_calculate_agent_workloads(self, orchestration_engine):
        """Test agent workload calculation"""
        active_experiments = [
            {'target_agent': 'raw_data_intelligence'},
            {'target_agent': 'raw_data_intelligence'},
            {'target_agent': 'indicator_intelligence'}
        ]
        
        workloads = orchestration_engine._calculate_agent_workloads(active_experiments)
        
        assert isinstance(workloads, dict)
        assert workloads['raw_data_intelligence'] == 2
        assert workloads['indicator_intelligence'] == 1
    
    def test_determine_assignment_type(self, orchestration_engine):
        """Test assignment type determination"""
        design = Mock(shape=ExperimentShape.DURABILITY)
        assignment_type = orchestration_engine._determine_assignment_type(design, 'raw_data_intelligence')
        assert assignment_type == 'strict'
        
        design = Mock(shape=ExperimentShape.STACK)
        assignment_type = orchestration_engine._determine_assignment_type(design, 'raw_data_intelligence')
        assert assignment_type == 'bounded'
        
        design = Mock(shape=ExperimentShape.ABLATION)
        assignment_type = orchestration_engine._determine_assignment_type(design, 'raw_data_intelligence')
        assert assignment_type == 'exploratory'
    
    def test_create_agent_directives(self, orchestration_engine):
        """Test agent directive creation"""
        design = Mock(
            experiment_id='EXP_123',
            hypothesis=Mock(hypothesis_text='Test hypothesis'),
            shape=ExperimentShape.DURABILITY,
            parameter_sweeps={'threshold': [0.5, 0.7, 0.9]},
            guardrails={'max_runtime_hours': 24},
            tracking_requirements=['performance_metrics'],
            ttl_hours=24
        )
        
        directives = orchestration_engine._create_agent_directives(design, 'raw_data_intelligence', 'strict')
        
        assert isinstance(directives, dict)
        assert directives['experiment_id'] == 'EXP_123'
        assert directives['hypothesis'] == 'Test hypothesis'
        assert directives['shape'] == 'durability'
        assert directives['assignment_type'] == 'strict'
        assert directives['ttl_hours'] == 24
    
    def test_define_success_criteria(self, orchestration_engine):
        """Test success criteria definition"""
        design = Mock(
            hypothesis=Mock(success_metrics={'accuracy': 0.8, 'precision': 0.7})
        )
        
        criteria = orchestration_engine._define_success_criteria(design, 'raw_data_intelligence')
        
        assert isinstance(criteria, dict)
        assert criteria['min_accuracy'] == 0.8
        assert criteria['min_precision'] == 0.7
        assert criteria['max_false_positive_rate'] == 0.3
        assert criteria['min_confidence'] == 0.6
    
    def test_set_reporting_requirements(self, orchestration_engine):
        """Test reporting requirements setting"""
        design = Mock()
        
        requirements = orchestration_engine._set_reporting_requirements(design, 'raw_data_intelligence')
        
        assert isinstance(requirements, list)
        assert 'experiment_progress' in requirements
        assert 'intermediate_results' in requirements
        assert 'anomaly_reports' in requirements
        assert 'final_results' in requirements
        assert 'lessons_learned' in requirements
        assert 'recommendations' in requirements
    
    @pytest.mark.asyncio
    async def test_publish_orchestration_results(self, orchestration_engine, mock_supabase_manager):
        """Test publishing orchestration results"""
        orchestration_results = {
            'experiment_ideas': [{'trigger': 'test_trigger'}],
            'experiment_designs': [{'experiment_id': 'EXP_123'}],
            'experiment_assignments': [{'assignment_id': 'ASSIGN_123'}],
            'active_experiments': [{'experiment_id': 'EXP_456'}],
            'completed_experiments': [{'experiment_id': 'EXP_789'}],
            'orchestration_errors': []
        }
        
        await orchestration_engine._publish_orchestration_results(orchestration_results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_experiment_orchestration'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['team_member'] == 'experiment_orchestration_engine'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
