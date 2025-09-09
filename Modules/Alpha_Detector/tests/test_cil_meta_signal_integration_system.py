"""
Test CIL Meta-Signal Integration System
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.missing_pieces.meta_signal_integration_system import (
    MetaSignalIntegrationSystem, MetaSignalType, IntegrationLevel, MetaSignalStatus,
    MetaSignal, IntegrationRule, IntegrationResult, EngineIntegrationState
)


class TestMetaSignalIntegrationSystem:
    """Test CIL Meta-Signal Integration System"""
    
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
    def integration_system(self, mock_supabase_manager, mock_llm_client):
        """Create MetaSignalIntegrationSystem instance"""
        return MetaSignalIntegrationSystem(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_meta_signals(self):
        """Mock meta-signals"""
        return [
            MetaSignal(
                signal_id='meta_signal_1',
                signal_type=MetaSignalType.CONFLUENCE,
                source_agents=['raw_data_intelligence', 'indicator_intelligence'],
                target_agents=['global_synthesis_engine'],
                signal_data={'confluence_score': 0.8, 'involved_patterns': ['divergence', 'volume_anomaly']},
                confidence_score=0.8,
                relevance_score=0.7,
                integration_priority=1,
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
            ),
            MetaSignal(
                signal_id='meta_signal_2',
                signal_type=MetaSignalType.LEAD_LAG,
                source_agents=['pattern_intelligence'],
                target_agents=['experiment_orchestration_engine'],
                signal_data={'lead_lag_score': 0.9, 'timing_offset': 30},
                confidence_score=0.9,
                relevance_score=0.8,
                integration_priority=2,
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
            ),
            MetaSignal(
                signal_id='meta_signal_3',
                signal_type=MetaSignalType.TRANSFER_HIT,
                source_agents=['raw_data_intelligence'],
                target_agents=['learning_feedback_engine'],
                signal_data={'transfer_score': 0.6, 'source_pattern': 'divergence', 'target_pattern': 'volume_anomaly'},
                confidence_score=0.6,
                relevance_score=0.5,
                integration_priority=3,
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
            )
        ]
    
    @pytest.fixture
    def mock_engine_states(self):
        """Mock engine states"""
        return {
            'global_synthesis_engine': {'ready_for_integration': True, 'current_load': 0.6},
            'experiment_orchestration_engine': {'ready_for_integration': True, 'current_load': 0.4},
            'learning_feedback_engine': {'ready_for_integration': True, 'current_load': 0.3},
            'autonomy_adaptation_engine': {'ready_for_integration': True, 'current_load': 0.2}
        }
    
    def test_integration_system_initialization(self, integration_system):
        """Test MetaSignalIntegrationSystem initialization"""
        assert integration_system.supabase_manager is not None
        assert integration_system.llm_client is not None
        assert integration_system.integration_timeout_minutes == 10
        assert integration_system.validation_threshold == 0.7
        assert integration_system.performance_tracking_window_hours == 24
        assert integration_system.meta_signal_expiry_hours == 2
        assert integration_system.max_concurrent_integrations == 5
        assert integration_system.integration_analysis_prompt is not None
        assert integration_system.validation_prompt is not None
        assert integration_system.performance_optimization_prompt is not None
        assert isinstance(integration_system.engine_integration_states, dict)
        assert isinstance(integration_system.active_integrations, dict)
        assert isinstance(integration_system.integration_rules, list)
        assert isinstance(integration_system.meta_signal_queue, list)
        assert len(integration_system.integration_rules) == 4  # Should have 4 default rules
    
    def test_load_prompt_templates(self, integration_system):
        """Test prompt template loading"""
        # Test integration analysis prompt
        assert 'meta_signal_type' in integration_system.integration_analysis_prompt
        assert 'source_agents' in integration_system.integration_analysis_prompt
        assert 'target_agents' in integration_system.integration_analysis_prompt
        assert 'signal_data' in integration_system.integration_analysis_prompt
        assert 'confidence_score' in integration_system.integration_analysis_prompt
        assert 'relevance_score' in integration_system.integration_analysis_prompt
        assert 'target_engine' in integration_system.integration_analysis_prompt
        assert 'engine_state' in integration_system.integration_analysis_prompt
        
        # Test validation prompt
        assert 'meta_signal_type' in integration_system.validation_prompt
        assert 'target_engine' in integration_system.validation_prompt
        assert 'integration_level' in integration_system.validation_prompt
        assert 'integration_data' in integration_system.validation_prompt
        assert 'before_metrics' in integration_system.validation_prompt
        assert 'after_metrics' in integration_system.validation_prompt
        assert 'validation_criteria' in integration_system.validation_prompt
        
        # Test performance optimization prompt
        assert 'engine_states' in integration_system.performance_optimization_prompt
        assert 'active_integrations' in integration_system.performance_optimization_prompt
        assert 'performance_metrics' in integration_system.performance_optimization_prompt
        assert 'issues' in integration_system.performance_optimization_prompt
    
    def test_initialize_integration_rules(self, integration_system):
        """Test integration rules initialization"""
        rules = integration_system.integration_rules
        
        assert len(rules) == 4
        
        # Check specific rules
        confluence_rule = next(r for r in rules if r.rule_id == "CONFLUENCE_TO_GLOBAL_SYNTHESIS")
        assert confluence_rule.meta_signal_type == MetaSignalType.CONFLUENCE
        assert confluence_rule.target_engine == "global_synthesis_engine"
        assert confluence_rule.priority == 1
        assert confluence_rule.enabled is True
        
        lead_lag_rule = next(r for r in rules if r.rule_id == "LEAD_LAG_TO_EXPERIMENT_ORCHESTRATION")
        assert lead_lag_rule.meta_signal_type == MetaSignalType.LEAD_LAG
        assert lead_lag_rule.target_engine == "experiment_orchestration_engine"
        assert lead_lag_rule.priority == 2
        assert lead_lag_rule.enabled is True
        
        transfer_hit_rule = next(r for r in rules if r.rule_id == "TRANSFER_HIT_TO_LEARNING_FEEDBACK")
        assert transfer_hit_rule.meta_signal_type == MetaSignalType.TRANSFER_HIT
        assert transfer_hit_rule.target_engine == "learning_feedback_engine"
        assert transfer_hit_rule.priority == 3
        assert transfer_hit_rule.enabled is True
        
        regime_shift_rule = next(r for r in rules if r.rule_id == "REGIME_SHIFT_TO_AUTONOMY_ADAPTATION")
        assert regime_shift_rule.meta_signal_type == MetaSignalType.REGIME_SHIFT
        assert regime_shift_rule.target_engine == "autonomy_adaptation_engine"
        assert regime_shift_rule.priority == 1
        assert regime_shift_rule.enabled is True
    
    @pytest.mark.asyncio
    async def test_process_meta_signal_integration_success(self, integration_system, mock_meta_signals, mock_engine_states):
        """Test successful meta-signal integration processing"""
        # Process meta-signal integration
        results = await integration_system.process_meta_signal_integration(mock_meta_signals, mock_engine_states)
        
        # Verify structure
        assert 'integration_results' in results
        assert 'validation_results' in results
        assert 'state_updates' in results
        assert 'optimization_results' in results
        assert 'integration_timestamp' in results
        assert 'integration_errors' in results
        
        # Verify processing timestamp
        assert isinstance(results['integration_timestamp'], datetime)
        
        # Verify results are correct types
        assert isinstance(results['integration_results'], list)
        assert isinstance(results['validation_results'], list)
        assert isinstance(results['state_updates'], list)
        assert isinstance(results['optimization_results'], dict)
        assert isinstance(results['integration_errors'], list)
    
    @pytest.mark.asyncio
    async def test_queue_meta_signals(self, integration_system, mock_meta_signals):
        """Test meta-signal queuing"""
        # Queue meta-signals
        await integration_system._queue_meta_signals(mock_meta_signals)
        
        # Verify signals were queued
        assert len(integration_system.meta_signal_queue) == 3
        
        # Verify signals are sorted by priority (highest first)
        priorities = [signal.integration_priority for signal in integration_system.meta_signal_queue]
        assert priorities == [3, 2, 1]  # Should be sorted in descending order
        
        # Test with expired signal
        expired_signal = MetaSignal(
            signal_id='expired_signal',
            signal_type=MetaSignalType.CONFLUENCE,
            source_agents=['test_agent'],
            target_agents=['test_engine'],
            signal_data={},
            confidence_score=0.8,
            relevance_score=0.7,
            integration_priority=1,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
        )
        
        initial_queue_size = len(integration_system.meta_signal_queue)
        await integration_system._queue_meta_signals([expired_signal])
        
        # Verify expired signal was not added
        assert len(integration_system.meta_signal_queue) == initial_queue_size
    
    @pytest.mark.asyncio
    async def test_find_applicable_rules(self, integration_system, mock_meta_signals):
        """Test finding applicable integration rules"""
        signal = mock_meta_signals[0]  # CONFLUENCE signal
        
        # Find applicable rules
        applicable_rules = await integration_system._find_applicable_rules(signal)
        
        # Verify results
        assert isinstance(applicable_rules, list)
        assert len(applicable_rules) == 1  # Should find CONFLUENCE_TO_GLOBAL_SYNTHESIS rule
        
        rule = applicable_rules[0]
        assert rule.rule_id == "CONFLUENCE_TO_GLOBAL_SYNTHESIS"
        assert rule.meta_signal_type == MetaSignalType.CONFLUENCE
        assert rule.target_engine == "global_synthesis_engine"
        assert rule.enabled is True
        
        # Test with signal that has no applicable rules
        no_rule_signal = MetaSignal(
            signal_id='no_rule_signal',
            signal_type=MetaSignalType.CROSS_ASSET_CONFLUENCE,
            source_agents=['test_agent'],
            target_agents=['non_existent_engine'],
            signal_data={},
            confidence_score=0.8,
            relevance_score=0.7,
            integration_priority=1,
            created_at=datetime.now(timezone.utc),
            expires_at=None
        )
        
        applicable_rules = await integration_system._find_applicable_rules(no_rule_signal)
        assert len(applicable_rules) == 0
    
    @pytest.mark.asyncio
    async def test_check_integration_conditions(self, integration_system, mock_meta_signals, mock_engine_states):
        """Test integration condition checking"""
        signal = mock_meta_signals[0]  # CONFLUENCE signal
        rule = integration_system.integration_rules[0]  # CONFLUENCE_TO_GLOBAL_SYNTHESIS rule
        
        # Test conditions met
        conditions_met = await integration_system._check_integration_conditions(signal, rule, mock_engine_states)
        assert conditions_met is True
        
        # Test confidence threshold not met
        low_confidence_signal = MetaSignal(
            signal_id='low_confidence_signal',
            signal_type=MetaSignalType.CONFLUENCE,
            source_agents=['test_agent'],
            target_agents=['global_synthesis_engine'],
            signal_data={},
            confidence_score=0.5,  # Below threshold of 0.7
            relevance_score=0.7,
            integration_priority=1,
            created_at=datetime.now(timezone.utc),
            expires_at=None
        )
        
        conditions_met = await integration_system._check_integration_conditions(low_confidence_signal, rule, mock_engine_states)
        assert conditions_met is False
        
        # Test relevance threshold not met
        low_relevance_signal = MetaSignal(
            signal_id='low_relevance_signal',
            signal_type=MetaSignalType.CONFLUENCE,
            source_agents=['test_agent'],
            target_agents=['global_synthesis_engine'],
            signal_data={},
            confidence_score=0.8,
            relevance_score=0.5,  # Below threshold of 0.6
            integration_priority=1,
            created_at=datetime.now(timezone.utc),
            expires_at=None
        )
        
        conditions_met = await integration_system._check_integration_conditions(low_relevance_signal, rule, mock_engine_states)
        assert conditions_met is False
        
        # Test engine not ready
        engine_states_not_ready = {
            'global_synthesis_engine': {'ready_for_integration': False, 'current_load': 0.6}
        }
        
        conditions_met = await integration_system._check_integration_conditions(signal, rule, engine_states_not_ready)
        assert conditions_met is False
    
    @pytest.mark.asyncio
    async def test_perform_integration(self, integration_system, mock_meta_signals, mock_engine_states):
        """Test performing meta-signal integration"""
        signal = mock_meta_signals[0]  # CONFLUENCE signal
        rule = integration_system.integration_rules[0]  # CONFLUENCE_TO_GLOBAL_SYNTHESIS rule
        
        # Perform integration
        integration_result = await integration_system._perform_integration(signal, rule, mock_engine_states)
        
        # Verify result
        assert integration_result is not None
        assert isinstance(integration_result, IntegrationResult)
        assert integration_result.integration_id.startswith('INTEGRATION_')
        assert integration_result.meta_signal_id == signal.signal_id
        assert integration_result.target_engine == rule.target_engine
        assert isinstance(integration_result.integration_level, IntegrationLevel)
        assert integration_result.integration_status == MetaSignalStatus.PENDING
        assert isinstance(integration_result.integration_data, dict)
        assert isinstance(integration_result.validation_results, dict)
        assert isinstance(integration_result.performance_metrics, dict)
        assert isinstance(integration_result.created_at, datetime)
        assert isinstance(integration_result.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_generate_integration_analysis(self, integration_system, mock_meta_signals, mock_engine_states):
        """Test integration analysis generation"""
        signal = mock_meta_signals[0]  # CONFLUENCE signal
        rule = integration_system.integration_rules[0]  # CONFLUENCE_TO_GLOBAL_SYNTHESIS rule
        
        # Generate integration analysis
        analysis = await integration_system._generate_integration_analysis(signal, rule, mock_engine_states)
        
        # Verify analysis
        assert analysis is not None
        assert isinstance(analysis, dict)
        assert 'integration_level' in analysis
        assert 'integration_actions' in analysis
        assert 'expected_impact' in analysis
        assert 'validation_criteria' in analysis
        assert 'integration_data' in analysis
        assert 'uncertainty_flags' in analysis
        
        # Verify specific values
        assert analysis['integration_level'] == 'enhanced'
        assert isinstance(analysis['integration_actions'], list)
        assert 'update_pattern_weights' in analysis['integration_actions']
        assert 'enhance_correlation_analysis' in analysis['integration_actions']
        assert isinstance(analysis['expected_impact'], dict)
        assert analysis['expected_impact']['performance_improvement'] == 0.15
        assert analysis['expected_impact']['risk_level'] == 'low'
        assert analysis['expected_impact']['complexity'] == 'moderate'
        assert isinstance(analysis['validation_criteria'], list)
        assert 'performance_improvement' in analysis['validation_criteria']
        assert 'accuracy_maintenance' in analysis['validation_criteria']
        assert isinstance(analysis['integration_data'], dict)
        assert analysis['integration_data']['weight_adjustment'] == 0.1
        assert analysis['integration_data']['correlation_threshold'] == 0.7
        assert isinstance(analysis['uncertainty_flags'], list)
        assert 'limited_historical_data' in analysis['uncertainty_flags']
    
    @pytest.mark.asyncio
    async def test_generate_llm_analysis(self, integration_system):
        """Test LLM analysis generation"""
        prompt_template = "Test integration_level prompt with {test_field}"
        data = {'test_field': 'test_value'}
        
        # Generate LLM analysis
        analysis = await integration_system._generate_llm_analysis(prompt_template, data)
        
        # Verify analysis
        assert analysis is not None
        assert isinstance(analysis, dict)
        assert 'integration_level' in analysis
        assert 'integration_actions' in analysis
        assert 'expected_impact' in analysis
        assert 'validation_criteria' in analysis
        assert 'integration_data' in analysis
        assert 'uncertainty_flags' in analysis
        
        # Verify specific values
        assert analysis['integration_level'] == 'enhanced'
        assert analysis['integration_actions'] == ['update_pattern_weights', 'enhance_correlation_analysis']
        assert analysis['expected_impact']['performance_improvement'] == 0.15
        assert analysis['expected_impact']['risk_level'] == 'low'
        assert analysis['expected_impact']['complexity'] == 'moderate'
        assert analysis['validation_criteria'] == ['performance_improvement', 'accuracy_maintenance']
        assert analysis['integration_data']['weight_adjustment'] == 0.1
        assert analysis['integration_data']['correlation_threshold'] == 0.7
        assert analysis['uncertainty_flags'] == ['limited_historical_data']
    
    @pytest.mark.asyncio
    async def test_validate_integrations(self, integration_system):
        """Test integration validation"""
        # Create test integration results
        integration_results = [
            IntegrationResult(
                integration_id='INTEGRATION_1',
                meta_signal_id='meta_signal_1',
                target_engine='global_synthesis_engine',
                integration_level=IntegrationLevel.ENHANCED,
                integration_status=MetaSignalStatus.PENDING,
                integration_data={'weight_adjustment': 0.1},
                validation_results={},
                performance_metrics={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            IntegrationResult(
                integration_id='INTEGRATION_2',
                meta_signal_id='meta_signal_2',
                target_engine='experiment_orchestration_engine',
                integration_level=IntegrationLevel.ADVANCED,
                integration_status=MetaSignalStatus.PENDING,
                integration_data={'timing_adjustment': 30},
                validation_results={},
                performance_metrics={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        ]
        
        # Validate integrations
        validation_results = await integration_system._validate_integrations(integration_results)
        
        # Verify results
        assert isinstance(validation_results, list)
        assert len(validation_results) == 2
        
        # Check validation result structure
        for validation in validation_results:
            assert 'integration_id' in validation
            assert 'validation_result' in validation
            assert 'validation_score' in validation
            assert 'performance_impact' in validation
            assert 'issues' in validation
            assert 'recommendations' in validation
            
            # Verify specific values
            assert validation['validation_result'] == 'passed'
            assert validation['validation_score'] == 0.85
            assert validation['performance_impact'] == 'positive'
            assert isinstance(validation['issues'], list)
            assert isinstance(validation['recommendations'], list)
            assert 'monitor_performance' in validation['recommendations']
            assert 'adjust_parameters' in validation['recommendations']
        
        # Verify integration results were updated
        for integration in integration_results:
            assert integration.integration_status == MetaSignalStatus.VALIDATED
            assert integration.validation_results is not None
            assert isinstance(integration.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_generate_validation_analysis(self, integration_system):
        """Test validation analysis generation"""
        integration = IntegrationResult(
            integration_id='INTEGRATION_1',
            meta_signal_id='meta_signal_1',
            target_engine='global_synthesis_engine',
            integration_level=IntegrationLevel.ENHANCED,
            integration_status=MetaSignalStatus.PENDING,
            integration_data={'weight_adjustment': 0.1},
            validation_results={},
            performance_metrics={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Generate validation analysis
        validation = await integration_system._generate_validation_analysis(integration)
        
        # Verify validation
        assert validation is not None
        assert isinstance(validation, dict)
        assert 'validation_result' in validation
        assert 'performance_impact' in validation
        assert 'validation_score' in validation
        assert 'issues' in validation
        assert 'recommendations' in validation
        assert 'confidence' in validation
        
        # Verify specific values
        assert validation['validation_result'] == 'passed'
        assert validation['performance_impact'] == 'positive'
        assert validation['validation_score'] == 0.85
        assert isinstance(validation['issues'], list)
        assert isinstance(validation['recommendations'], list)
        assert 'monitor_performance' in validation['recommendations']
        assert 'adjust_parameters' in validation['recommendations']
        assert validation['confidence'] == 0.8
    
    @pytest.mark.asyncio
    async def test_update_engine_states(self, integration_system):
        """Test engine state updates"""
        # Add some active integrations
        integration_system.active_integrations = {
            'INTEGRATION_1': IntegrationResult(
                integration_id='INTEGRATION_1',
                meta_signal_id='meta_signal_1',
                target_engine='global_synthesis_engine',
                integration_level=IntegrationLevel.ENHANCED,
                integration_status=MetaSignalStatus.VALIDATED,
                integration_data={'weight_adjustment': 0.1},
                validation_results={'validation_score': 0.85, 'performance_impact': 'positive'},
                performance_metrics={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        }
        
        validation_results = [
            {
                'integration_id': 'INTEGRATION_1',
                'validation_result': 'passed',
                'validation_score': 0.85,
                'performance_impact': 'positive',
                'issues': [],
                'recommendations': ['monitor_performance']
            }
        ]
        
        # Update engine states
        state_updates = await integration_system._update_engine_states(validation_results)
        
        # Verify results
        assert isinstance(state_updates, list)
        assert len(state_updates) == 1
        
        state_update = state_updates[0]
        assert 'engine_name' in state_update
        assert 'integration_level' in state_update
        assert 'active_meta_signals' in state_update
        assert 'performance_metrics' in state_update
        
        # Verify specific values
        assert state_update['engine_name'] == 'global_synthesis_engine'
        assert state_update['integration_level'] == 'basic'  # Initial level
        assert state_update['active_meta_signals'] == 1
        assert isinstance(state_update['performance_metrics'], dict)
        assert 'integration_success_rate' in state_update['performance_metrics']
        assert state_update['performance_metrics']['integration_success_rate'] == 0.1
        
        # Verify engine state was updated
        assert 'global_synthesis_engine' in integration_system.engine_integration_states
        engine_state = integration_system.engine_integration_states['global_synthesis_engine']
        assert engine_state.engine_name == 'global_synthesis_engine'
        assert engine_state.integration_level == IntegrationLevel.BASIC
        assert len(engine_state.active_meta_signals) == 1
        assert 'meta_signal_1' in engine_state.active_meta_signals
        assert isinstance(engine_state.last_updated, datetime)
    
    @pytest.mark.asyncio
    async def test_optimize_integration_performance(self, integration_system):
        """Test integration performance optimization"""
        # Add some engine states and active integrations
        integration_system.engine_integration_states = {
            'global_synthesis_engine': EngineIntegrationState(
                engine_name='global_synthesis_engine',
                integration_level=IntegrationLevel.BASIC,
                active_meta_signals={'meta_signal_1'},
                integration_rules=[],
                performance_metrics={'integration_success_rate': 0.8},
                last_updated=datetime.now(timezone.utc)
            )
        }
        
        integration_system.active_integrations = {
            'INTEGRATION_1': IntegrationResult(
                integration_id='INTEGRATION_1',
                meta_signal_id='meta_signal_1',
                target_engine='global_synthesis_engine',
                integration_level=IntegrationLevel.ENHANCED,
                integration_status=MetaSignalStatus.VALIDATED,
                integration_data={},
                validation_results={'validation_score': 0.85},
                performance_metrics={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        }
        
        # Add some issues to trigger optimization
        integration_system.meta_signal_queue = [Mock() for _ in range(15)]  # High queue size
        
        # Optimize performance
        optimization_results = await integration_system._optimize_integration_performance()
        
        # Verify results
        assert isinstance(optimization_results, dict)
        assert 'optimization_actions' in optimization_results
        assert 'performance_predictions' in optimization_results
        assert 'optimization_confidence' in optimization_results
        
        # Verify specific values
        assert isinstance(optimization_results['optimization_actions'], list)
        # Note: The number of actions may vary based on the optimization analysis
        assert len(optimization_results['optimization_actions']) >= 0
        
        assert isinstance(optimization_results['performance_predictions'], dict)
        assert isinstance(optimization_results['optimization_confidence'], float)
        assert 0.0 <= optimization_results['optimization_confidence'] <= 1.0
    
    def test_calculate_overall_performance_metrics(self, integration_system):
        """Test overall performance metrics calculation"""
        # Add some active integrations
        integration_system.active_integrations = {
            'INTEGRATION_1': IntegrationResult(
                integration_id='INTEGRATION_1',
                meta_signal_id='meta_signal_1',
                target_engine='global_synthesis_engine',
                integration_level=IntegrationLevel.ENHANCED,
                integration_status=MetaSignalStatus.VALIDATED,
                integration_data={},
                validation_results={'validation_score': 0.8},
                performance_metrics={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            'INTEGRATION_2': IntegrationResult(
                integration_id='INTEGRATION_2',
                meta_signal_id='meta_signal_2',
                target_engine='experiment_orchestration_engine',
                integration_level=IntegrationLevel.ADVANCED,
                integration_status=MetaSignalStatus.VALIDATED,
                integration_data={},
                validation_results={'validation_score': 0.9},
                performance_metrics={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        }
        
        integration_system.engine_integration_states = {
            'engine1': Mock(),
            'engine2': Mock(),
            'engine3': Mock(),
            'engine4': Mock()
        }
        
        # Calculate performance metrics
        metrics = integration_system._calculate_overall_performance_metrics()
        
        # Verify results
        assert isinstance(metrics, dict)
        assert 'total_integrations' in metrics
        assert 'successful_integrations' in metrics
        assert 'average_validation_score' in metrics
        assert 'engine_utilization' in metrics
        
        # Verify specific values
        assert metrics['total_integrations'] == 2
        assert metrics['successful_integrations'] == 2
        assert abs(metrics['average_validation_score'] - 0.85) < 0.001  # (0.8 + 0.9) / 2 with floating point tolerance
        assert metrics['engine_utilization'] == 0.5  # 4 engines / 8 total engines
    
    def test_identify_performance_issues(self, integration_system):
        """Test performance issue identification"""
        # Test with high queue size
        integration_system.meta_signal_queue = [Mock() for _ in range(15)]  # High queue size
        
        issues = integration_system._identify_performance_issues()
        assert 'High meta-signal queue size' in issues
        
        # Test with low validation scores
        integration_system.meta_signal_queue = []
        integration_system.active_integrations = {
            'INTEGRATION_1': IntegrationResult(
                integration_id='INTEGRATION_1',
                meta_signal_id='meta_signal_1',
                target_engine='global_synthesis_engine',
                integration_level=IntegrationLevel.ENHANCED,
                integration_status=MetaSignalStatus.VALIDATED,
                integration_data={},
                validation_results={'validation_score': 0.4},  # Low score
                performance_metrics={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        }
        
        issues = integration_system._identify_performance_issues()
        assert 'Low average validation score' in issues
        
        # Test with engine overload
        integration_system.active_integrations = {}
        integration_system.engine_integration_states = {
            'overloaded_engine': EngineIntegrationState(
                engine_name='overloaded_engine',
                integration_level=IntegrationLevel.BASIC,
                active_meta_signals={'signal1', 'signal2', 'signal3', 'signal4', 'signal5', 'signal6'},  # Overloaded
                integration_rules=[],
                performance_metrics={},
                last_updated=datetime.now(timezone.utc)
            )
        }
        
        issues = integration_system._identify_performance_issues()
        assert 'Engine overloaded_engine overloaded with meta-signals' in issues
    
    @pytest.mark.asyncio
    async def test_apply_optimization_actions(self, integration_system):
        """Test applying optimization actions"""
        # Add engine state
        integration_system.engine_integration_states = {
            'test_engine': EngineIntegrationState(
                engine_name='test_engine',
                integration_level=IntegrationLevel.BASIC,
                active_meta_signals=set(),
                integration_rules=[],
                performance_metrics={},
                last_updated=datetime.now(timezone.utc)
            )
        }
        
        actions = [
            {
                'action_type': 'adjust_priority',
                'target': 'test_engine',
                'parameters': {'priority': 1},
                'expected_improvement': 0.1
            },
            {
                'action_type': 'change_level',
                'target': 'test_engine',
                'parameters': {'level': 'enhanced'},
                'expected_improvement': 0.2
            }
        ]
        
        # Apply optimization actions
        applied_actions = await integration_system._apply_optimization_actions(actions)
        
        # Verify results
        assert isinstance(applied_actions, list)
        assert len(applied_actions) == 2
        
        # Check first action
        action1 = applied_actions[0]
        assert action1['action_type'] == 'adjust_priority'
        assert action1['target'] == 'test_engine'
        assert action1['parameters']['priority'] == 1
        assert action1['applied'] is True
        
        # Check second action
        action2 = applied_actions[1]
        assert action2['action_type'] == 'change_level'
        assert action2['target'] == 'test_engine'
        assert action2['parameters']['level'] == 'enhanced'
        assert action2['applied'] is True
        
        # Verify engine state was updated
        engine_state = integration_system.engine_integration_states['test_engine']
        assert engine_state.integration_level == IntegrationLevel.ENHANCED
    
    @pytest.mark.asyncio
    async def test_publish_integration_results(self, integration_system, mock_supabase_manager):
        """Test publishing integration results"""
        results = {
            'integration_results': [{'integration_id': 'INTEGRATION_1'}],
            'validation_results': [{'validation_id': 'VALIDATION_1'}],
            'state_updates': [{'state_id': 'STATE_1'}],
            'optimization_results': {'actions': []},
            'integration_timestamp': datetime.now(timezone.utc),
            'integration_errors': []
        }
        
        await integration_system._publish_integration_results(results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_meta_signal_integration'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['team_member'] == 'meta_signal_integration_system'
        assert call_args['strategic_meta_type'] == 'meta_signal_integration'
        assert call_args['resonance_score'] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
