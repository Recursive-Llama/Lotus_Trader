"""
Test CIL Output & Directive System
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.engines.output_directive_system import (
    OutputDirectiveSystem, DirectiveType, AutonomyLevel, DirectivePriority,
    Beacon, Envelope, Seed, ExperimentDirective, FeedbackRequest, CrossAgentCoordination
)


class TestOutputDirectiveSystem:
    """Test CIL Output & Directive System"""
    
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
    def output_system(self, mock_supabase_manager, mock_llm_client):
        """Create OutputDirectiveSystem instance"""
        return OutputDirectiveSystem(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_global_synthesis_results(self):
        """Mock global synthesis results"""
        return {
            'experiment_ideas': [
                {
                    'type': 'divergence_volume_confluence',
                    'family': 'divergence',
                    'hypothesis': 'Divergence + volume spike = stronger signal',
                    'conditions': {'regime': 'high_vol', 'session': 'US'},
                    'success_criteria': {'accuracy': 0.8, 'persistence': 0.7},
                    'duration_hours': 24,
                    'confidence': 0.8,
                    'urgency': 'medium',
                    'hints': ['Check volume patterns', 'Look for divergence signals'],
                    'starting_points': ['RSI divergence', 'Volume spike detection'],
                    'suggestions': ['Combine with MACD confirmation']
                }
            ],
            'confluence_events': [
                {
                    'needs_coordination': True,
                    'involved_agents': ['raw_data_intelligence', 'indicator_intelligence'],
                    'coordination_type': 'sequential',
                    'dependencies': ['divergence_detection'],
                    'success_criteria': {'combined_accuracy': 0.85},
                    'sequence': 'sequential',
                    'success_metrics': {'accuracy': 0.85, 'timing': 0.8}
                }
            ],
            'insights': [
                {
                    'plan_worthy': True,
                    'plan_type': 'strategic_exploration',
                    'evidence': ['confluence_pattern', 'volume_anomaly'],
                    'activation_conditions': {'volatility': 'high'},
                    'confirmation_conditions': {'volume': 'above_average'},
                    'invalidation_conditions': {'trend': 'strong'},
                    'target_assets': ['BTC', 'ETH'],
                    'target_timeframes': ['1h', '4h'],
                    'target_regimes': ['high_vol', 'sideways'],
                    'confidence': 0.8,
                    'mechanism_hypothesis': 'Liquidity vacuum after failed retest',
                    'risks': ['false_breakout', 'low_volume'],
                    'fails_when': ['strong_trend', 'low_participation']
                }
            ],
            'current_regime': 'high_vol',
            'current_session': 'US',
            'volatility_level': 'high'
        }
    
    @pytest.fixture
    def mock_learning_feedback_results(self):
        """Mock learning feedback results"""
        return {
            'lessons': [
                {
                    'needs_feedback': True,
                    'source_agent': 'raw_data_intelligence',
                    'feedback_type': 'pattern_validation',
                    'lesson_id': 'lesson_123'
                }
            ],
            'doctrine_updates': [
                {'id': 'doctrine_123', 'type': 'promotion', 'confidence': 0.8}
            ]
        }
    
    def test_output_system_initialization(self, output_system):
        """Test OutputDirectiveSystem initialization"""
        assert output_system.supabase_manager is not None
        assert output_system.llm_client is not None
        assert output_system.directive_timeout_hours == 24
        assert output_system.feedback_timeout_hours == 6
        assert output_system.coordination_timeout_hours == 12
        assert output_system.max_concurrent_directives == 10
        assert output_system.directive_retry_attempts == 3
        assert 'raw_data_intelligence' in output_system.agent_capabilities
        assert 'indicator_intelligence' in output_system.agent_capabilities
        assert 'pattern_intelligence' in output_system.agent_capabilities
        assert 'system_control' in output_system.agent_capabilities
    
    @pytest.mark.asyncio
    async def test_generate_outputs_and_directives_success(self, output_system, mock_global_synthesis_results, mock_learning_feedback_results):
        """Test successful output and directive generation"""
        experiment_results = {}
        
        # Generate outputs and directives
        results = await output_system.generate_outputs_and_directives(
            mock_global_synthesis_results, experiment_results, mock_learning_feedback_results
        )
        
        # Verify structure
        assert 'experiment_directives' in results
        assert 'feedback_requests' in results
        assert 'cross_agent_coordination' in results
        assert 'strategic_plans' in results
        assert 'output_timestamp' in results
        assert 'output_errors' in results
        
        # Verify processing timestamp
        assert isinstance(results['output_timestamp'], datetime)
        
        # Verify results are lists
        assert isinstance(results['experiment_directives'], list)
        assert isinstance(results['feedback_requests'], list)
        assert isinstance(results['cross_agent_coordination'], list)
        assert isinstance(results['strategic_plans'], list)
        assert isinstance(results['output_errors'], list)
    
    @pytest.mark.asyncio
    async def test_generate_experiment_directives(self, output_system, mock_global_synthesis_results):
        """Test experiment directive generation"""
        experiment_results = {}
        
        # Generate experiment directives
        directives = await output_system._generate_experiment_directives(
            mock_global_synthesis_results, experiment_results
        )
        
        # Verify results
        assert isinstance(directives, list)
        assert len(directives) == 1  # One experiment idea should generate one directive
        
        directive = directives[0]
        assert isinstance(directive, ExperimentDirective)
        assert directive.directive_id.startswith('DIRECTIVE_')
        assert directive.directive_type == DirectiveType.EXPERIMENT_ASSIGNMENT
        assert directive.target_agent == 'raw_data_intelligence'  # Should map to divergence type
        assert directive.hypothesis == 'Divergence + volume spike = stronger signal'
        assert directive.expected_conditions == {'regime': 'high_vol', 'session': 'US'}
        assert directive.success_criteria == {'accuracy': 0.8, 'persistence': 0.7}
        assert directive.duration_hours == 24
        assert isinstance(directive.autonomy_level, AutonomyLevel)
        assert isinstance(directive.priority, DirectivePriority)
        assert directive.beacon is not None
        assert directive.envelope is not None
        assert directive.seed is not None
        assert isinstance(directive.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_determine_target_agent(self, output_system):
        """Test target agent determination"""
        # Test divergence type
        idea = {'type': 'divergence_analysis', 'family': 'divergence'}
        agent = await output_system._determine_target_agent(idea)
        assert agent == 'raw_data_intelligence'
        
        # Test RSI type
        idea = {'type': 'rsi_analysis', 'family': 'technical'}
        agent = await output_system._determine_target_agent(idea)
        assert agent == 'indicator_intelligence'
        
        # Test pattern type
        idea = {'type': 'composite_pattern', 'family': 'pattern'}
        agent = await output_system._determine_target_agent(idea)
        assert agent == 'pattern_intelligence'
        
        # Test parameter type
        idea = {'type': 'parameter_optimization', 'family': 'system'}
        agent = await output_system._determine_target_agent(idea)
        assert agent == 'system_control'
        
        # Test unknown type
        idea = {'type': 'unknown_type', 'family': 'unknown'}
        agent = await output_system._determine_target_agent(idea)
        assert agent == 'raw_data_intelligence'  # Default
    
    @pytest.mark.asyncio
    async def test_create_experiment_directive(self, output_system, mock_global_synthesis_results):
        """Test experiment directive creation"""
        experiment_idea = {
            'type': 'divergence_volume_confluence',
            'family': 'divergence',
            'hypothesis': 'Test hypothesis',
            'conditions': {'regime': 'high_vol'},
            'success_criteria': {'accuracy': 0.8},
            'duration_hours': 12,
            'confidence': 0.9,
            'urgency': 'high',
            'hints': ['Test hint'],
            'starting_points': ['Test starting point'],
            'suggestions': ['Test suggestion']
        }
        
        target_agent = 'raw_data_intelligence'
        
        # Create experiment directive
        directive = await output_system._create_experiment_directive(
            experiment_idea, target_agent, mock_global_synthesis_results
        )
        
        # Verify directive
        assert directive is not None
        assert directive.directive_id.startswith('DIRECTIVE_')
        assert directive.directive_type == DirectiveType.EXPERIMENT_ASSIGNMENT
        assert directive.target_agent == target_agent
        assert directive.hypothesis == 'Test hypothesis'
        assert directive.expected_conditions == {'regime': 'high_vol'}
        assert directive.success_criteria == {'accuracy': 0.8}
        assert directive.duration_hours == 12
        assert isinstance(directive.autonomy_level, AutonomyLevel)
        assert isinstance(directive.priority, DirectivePriority)
        assert directive.beacon is not None
        assert directive.envelope is not None
        assert directive.seed is not None
        assert isinstance(directive.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_create_beacon(self, output_system, mock_global_synthesis_results):
        """Test beacon creation"""
        experiment_idea = {
            'family': 'divergence',
            'hypothesis': 'Test hypothesis',
            'confidence': 0.8
        }
        
        beacon = await output_system._create_beacon(experiment_idea, mock_global_synthesis_results)
        
        assert isinstance(beacon, Beacon)
        assert beacon.theme == 'divergence'
        assert beacon.intent == 'Test hypothesis'
        assert beacon.context['regime'] == 'high_vol'
        assert beacon.context['session'] == 'US'
        assert beacon.context['volatility'] == 'high'
        assert beacon.confidence == 0.8
        assert isinstance(beacon.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_create_envelope(self, output_system):
        """Test envelope creation"""
        experiment_idea = {
            'duration_hours': 12
        }
        target_agent = 'raw_data_intelligence'
        
        envelope = await output_system._create_envelope(experiment_idea, target_agent)
        
        assert isinstance(envelope, Envelope)
        assert envelope.constraints['max_experiments'] == 1
        assert envelope.constraints['time_limit_hours'] == 12
        assert envelope.constraints['resource_limit'] == 'standard'
        assert envelope.parameters['confidence_threshold'] == 0.7
        assert envelope.parameters['similarity_threshold'] == 0.8
        assert envelope.parameters['success_threshold'] == 0.6
        assert envelope.guardrails['stop_on_failure'] is True
        assert envelope.guardrails['max_false_positives'] == 5
        assert envelope.guardrails['min_sample_size'] == 10
        assert envelope.time_horizon == '12_hours'
        assert isinstance(envelope.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_create_seed(self, output_system, mock_global_synthesis_results):
        """Test seed creation"""
        experiment_idea = {
            'hints': ['Test hint'],
            'starting_points': ['Test starting point'],
            'suggestions': ['Test suggestion'],
            'seed_confidence': 0.7
        }
        
        seed = await output_system._create_seed(experiment_idea, mock_global_synthesis_results)
        
        assert isinstance(seed, Seed)
        assert seed.hints == ['Test hint']
        assert seed.starting_points == ['Test starting point']
        assert seed.suggestions == ['Test suggestion']
        assert seed.confidence == 0.7
        assert isinstance(seed.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_determine_autonomy_level(self, output_system):
        """Test autonomy level determination"""
        # Test high performance
        with patch.object(output_system, '_get_agent_performance', return_value=0.9):
            autonomy = await output_system._determine_autonomy_level('raw_data_intelligence', {})
            assert autonomy == AutonomyLevel.EXPLORATORY
        
        # Test medium performance
        with patch.object(output_system, '_get_agent_performance', return_value=0.7):
            autonomy = await output_system._determine_autonomy_level('raw_data_intelligence', {})
            assert autonomy == AutonomyLevel.BOUNDED
        
        # Test low performance
        with patch.object(output_system, '_get_agent_performance', return_value=0.5):
            autonomy = await output_system._determine_autonomy_level('raw_data_intelligence', {})
            assert autonomy == AutonomyLevel.STRICT
    
    @pytest.mark.asyncio
    async def test_get_agent_performance(self, output_system):
        """Test agent performance retrieval"""
        performance = await output_system._get_agent_performance('raw_data_intelligence')
        assert performance == 0.8
        
        performance = await output_system._get_agent_performance('indicator_intelligence')
        assert performance == 0.7
        
        performance = await output_system._get_agent_performance('pattern_intelligence')
        assert performance == 0.75
        
        performance = await output_system._get_agent_performance('system_control')
        assert performance == 0.6
        
        performance = await output_system._get_agent_performance('unknown_agent')
        assert performance == 0.5
    
    @pytest.mark.asyncio
    async def test_determine_priority(self, output_system, mock_global_synthesis_results):
        """Test priority determination"""
        # Test critical priority
        experiment_idea = {'confidence': 0.95, 'urgency': 'high'}
        priority = await output_system._determine_priority(experiment_idea, mock_global_synthesis_results)
        assert priority == DirectivePriority.CRITICAL
        
        # Test high priority
        experiment_idea = {'confidence': 0.85, 'urgency': 'medium'}
        priority = await output_system._determine_priority(experiment_idea, mock_global_synthesis_results)
        assert priority == DirectivePriority.HIGH
        
        # Test medium priority
        experiment_idea = {'confidence': 0.7, 'urgency': 'low'}
        priority = await output_system._determine_priority(experiment_idea, mock_global_synthesis_results)
        assert priority == DirectivePriority.MEDIUM
        
        # Test low priority
        experiment_idea = {'confidence': 0.5, 'urgency': 'low'}
        priority = await output_system._determine_priority(experiment_idea, mock_global_synthesis_results)
        assert priority == DirectivePriority.LOW
    
    @pytest.mark.asyncio
    async def test_generate_feedback_requests(self, output_system, mock_learning_feedback_results):
        """Test feedback request generation"""
        experiment_results = {}
        
        # Generate feedback requests
        requests = await output_system._generate_feedback_requests(
            mock_learning_feedback_results, experiment_results
        )
        
        # Verify results
        assert isinstance(requests, list)
        assert len(requests) == 1  # One lesson should generate one request
        
        request = requests[0]
        assert isinstance(request, FeedbackRequest)
        assert request.request_id.startswith('FEEDBACK_')
        assert request.target_agent == 'raw_data_intelligence'
        assert request.request_type == 'pattern_validation'
        assert len(request.requirements) == 4
        assert 'Report raw results' in request.requirements[0]
        assert 'Log structured lessons' in request.requirements[1]
        assert 'Highlight surprises' in request.requirements[2]
        assert 'Suggest refinements' in request.requirements[3]
        assert isinstance(request.deadline, datetime)
        assert request.priority == DirectivePriority.MEDIUM
        assert isinstance(request.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_create_feedback_request(self, output_system):
        """Test feedback request creation"""
        lesson = {
            'needs_feedback': True,
            'source_agent': 'indicator_intelligence',
            'feedback_type': 'signal_validation',
            'lesson_id': 'lesson_456'
        }
        experiment_results = {}
        
        request = await output_system._create_feedback_request(lesson, experiment_results)
        
        assert request is not None
        assert request.request_id.startswith('FEEDBACK_')
        assert request.target_agent == 'indicator_intelligence'
        assert request.request_type == 'signal_validation'
        assert len(request.requirements) == 4
        assert isinstance(request.deadline, datetime)
        assert request.priority == DirectivePriority.MEDIUM
        assert isinstance(request.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_generate_cross_agent_coordination(self, output_system, mock_global_synthesis_results):
        """Test cross-agent coordination generation"""
        experiment_results = {}
        
        # Generate cross-agent coordination
        coordinations = await output_system._generate_cross_agent_coordination(
            mock_global_synthesis_results, experiment_results
        )
        
        # Verify results
        assert isinstance(coordinations, list)
        assert len(coordinations) == 1  # One confluence event should generate one coordination
        
        coordination = coordinations[0]
        assert isinstance(coordination, CrossAgentCoordination)
        assert coordination.coordination_id.startswith('COORD_')
        assert coordination.coordination_type == 'sequential'
        assert coordination.participating_agents == ['raw_data_intelligence', 'indicator_intelligence']
        assert coordination.coordination_plan['sequence'] == 'sequential'
        assert coordination.coordination_plan['communication_protocol'] == 'database_strands'
        assert coordination.dependencies == ['divergence_detection']
        assert coordination.success_metrics == {'accuracy': 0.85, 'timing': 0.8}
        assert isinstance(coordination.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_create_cross_agent_coordination(self, output_system, mock_global_synthesis_results):
        """Test cross-agent coordination creation"""
        confluence_event = {
            'needs_coordination': True,
            'involved_agents': ['pattern_intelligence', 'system_control'],
            'coordination_type': 'parallel',
            'dependencies': ['pattern_detection', 'parameter_optimization'],
            'success_criteria': {'combined_accuracy': 0.9},
            'sequence': 'parallel',
            'success_metrics': {'accuracy': 0.9, 'efficiency': 0.8}
        }
        
        coordination = await output_system._create_cross_agent_coordination(
            confluence_event, mock_global_synthesis_results
        )
        
        assert coordination is not None
        assert coordination.coordination_id.startswith('COORD_')
        assert coordination.coordination_type == 'parallel'
        assert coordination.participating_agents == ['pattern_intelligence', 'system_control']
        assert coordination.coordination_plan['sequence'] == 'parallel'
        assert coordination.dependencies == ['pattern_detection', 'parameter_optimization']
        assert coordination.success_metrics == {'accuracy': 0.9, 'efficiency': 0.8}
        assert isinstance(coordination.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_generate_strategic_plans(self, output_system, mock_global_synthesis_results, mock_learning_feedback_results):
        """Test strategic plan generation"""
        # Generate strategic plans
        plans = await output_system._generate_strategic_plans(
            mock_global_synthesis_results, mock_learning_feedback_results
        )
        
        # Verify results
        assert isinstance(plans, list)
        assert len(plans) == 1  # One insight should generate one plan
        
        plan = plans[0]
        assert isinstance(plan, dict)
        assert plan['plan_id'].startswith('PLAN_')
        assert plan['plan_type'] == 'strategic_exploration'
        assert plan['evidence_stack'] == ['confluence_pattern', 'volume_anomaly']
        assert plan['conditions']['activate'] == {'volatility': 'high'}
        assert plan['conditions']['confirm'] == {'volume': 'above_average'}
        assert plan['conditions']['invalidate'] == {'trend': 'strong'}
        assert plan['scope']['assets'] == ['BTC', 'ETH']
        assert plan['scope']['timeframes'] == ['1h', '4h']
        assert plan['scope']['regimes'] == ['high_vol', 'sideways']
        assert plan['provenance']['confidence_level'] == 0.8
        assert plan['notes']['mechanism'] == 'Liquidity vacuum after failed retest'
        assert plan['notes']['risks'] == ['false_breakout', 'low_volume']
        assert plan['notes']['fails_when'] == ['strong_trend', 'low_participation']
        assert 'created_at' in plan
    
    @pytest.mark.asyncio
    async def test_create_strategic_plan(self, output_system, mock_learning_feedback_results):
        """Test strategic plan creation"""
        insight = {
            'plan_worthy': True,
            'plan_type': 'risk_management',
            'evidence': ['risk_pattern', 'volatility_spike'],
            'activation_conditions': {'risk_level': 'high'},
            'confirmation_conditions': {'volatility': 'extreme'},
            'invalidation_conditions': {'risk_level': 'low'},
            'target_assets': ['ETH'],
            'target_timeframes': ['1h'],
            'target_regimes': ['high_vol'],
            'confidence': 0.9,
            'mechanism_hypothesis': 'Risk-off sentiment triggers volatility',
            'risks': ['market_crash', 'liquidity_drain'],
            'fails_when': ['risk_on_sentiment', 'low_volatility']
        }
        doctrine_updates = [{'id': 'doctrine_456', 'type': 'retirement'}]
        
        plan = await output_system._create_strategic_plan(insight, doctrine_updates)
        
        assert plan is not None
        assert plan['plan_id'].startswith('PLAN_')
        assert plan['plan_type'] == 'risk_management'
        assert plan['evidence_stack'] == ['risk_pattern', 'volatility_spike']
        assert plan['conditions']['activate'] == {'risk_level': 'high'}
        assert plan['conditions']['confirm'] == {'volatility': 'extreme'}
        assert plan['conditions']['invalidate'] == {'risk_level': 'low'}
        assert plan['scope']['assets'] == ['ETH']
        assert plan['scope']['timeframes'] == ['1h']
        assert plan['scope']['regimes'] == ['high_vol']
        assert plan['provenance']['confidence_level'] == 0.9
        assert plan['notes']['mechanism'] == 'Risk-off sentiment triggers volatility'
        assert plan['notes']['risks'] == ['market_crash', 'liquidity_drain']
        assert plan['notes']['fails_when'] == ['risk_on_sentiment', 'low_volatility']
        assert 'created_at' in plan
    
    @pytest.mark.asyncio
    async def test_publish_output_results(self, output_system, mock_supabase_manager):
        """Test publishing output results"""
        results = {
            'experiment_directives': [{'directive_id': 'DIRECTIVE_123'}],
            'feedback_requests': [{'request_id': 'FEEDBACK_123'}],
            'cross_agent_coordination': [{'coordination_id': 'COORD_123'}],
            'strategic_plans': [{'plan_id': 'PLAN_123'}],
            'output_timestamp': datetime.now(timezone.utc),
            'output_errors': []
        }
        
        await output_system._publish_output_results(results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_output_directive'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['team_member'] == 'output_directive_system'
        assert call_args['strategic_meta_type'] == 'directive_generation'
        assert call_args['resonance_score'] == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
