"""
Test CIL Input Processor Engine
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.engines.input_processor import (
    InputProcessor, AgentOutput, CrossAgentMetaData, MarketRegimeContext,
    HistoricalPerformance, ExperimentRegistry
)


class TestInputProcessor:
    """Test CIL Input Processor Engine"""
    
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
    def input_processor(self, mock_supabase_manager, mock_llm_client):
        """Create InputProcessor instance"""
        return InputProcessor(mock_supabase_manager, mock_llm_client)
    
    def test_input_processor_initialization(self, input_processor):
        """Test InputProcessor initialization"""
        assert input_processor.supabase_manager is not None
        assert input_processor.llm_client is not None
        assert input_processor.agent_output_window_hours == 24
        assert input_processor.cross_agent_analysis_window_hours == 48
        assert input_processor.historical_analysis_window_days == 30
        assert input_processor.experiment_registry_window_days == 7
    
    @pytest.mark.asyncio
    async def test_process_all_inputs_success(self, input_processor, mock_supabase_manager):
        """Test successful processing of all inputs"""
        # Mock database responses
        mock_supabase_manager.execute_query.return_value = [
            {
                'id': 'strand_1',
                'agent_id': 'agent_1',
                'kind': 'detection',
                'module_intelligence': {'pattern_type': 'divergence'},
                'sig_sigma': 0.8,
                'sig_confidence': 0.7,
                'outcome_score': 0.6,
                'tags': ['agent:test:detection'],
                'created_at': datetime.now(timezone.utc),
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US'
            }
        ]
        
        # Process all inputs
        result = await input_processor.process_all_inputs()
        
        # Verify structure
        assert 'agent_outputs' in result
        assert 'cross_agent_metadata' in result
        assert 'market_regime_context' in result
        assert 'historical_performance' in result
        assert 'experiment_registry' in result
        assert 'processing_timestamp' in result
        assert 'processing_errors' in result
        
        # Verify processing timestamp
        assert isinstance(result['processing_timestamp'], datetime)
    
    @pytest.mark.asyncio
    async def test_process_agent_outputs(self, input_processor, mock_supabase_manager):
        """Test agent output processing"""
        # Mock database response
        mock_supabase_manager.execute_query.return_value = [
            {
                'id': 'strand_1',
                'agent_id': 'raw_data_intelligence',
                'kind': 'detection',
                'module_intelligence': {
                    'pattern_type': 'divergence',
                    'hypothesis_notes': 'Testing divergence detection'
                },
                'sig_sigma': 0.8,
                'sig_confidence': 0.7,
                'outcome_score': 0.6,
                'tags': ['agent:raw_data:detection', 'profitable'],
                'created_at': datetime.now(timezone.utc),
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US'
            }
        ]
        
        # Process agent outputs
        agent_outputs = await input_processor.process_agent_outputs()
        
        # Verify results
        assert len(agent_outputs) == 1
        output = agent_outputs[0]
        assert isinstance(output, AgentOutput)
        assert output.agent_id == 'raw_data_intelligence'
        assert output.detection_type == 'divergence'
        assert output.confidence == 0.7
        assert output.signal_strength == 0.8
        assert output.hypothesis_notes == 'Testing divergence detection'
        assert 'profitable' in output.performance_tags
    
    @pytest.mark.asyncio
    async def test_process_cross_agent_metadata(self, input_processor, mock_supabase_manager):
        """Test cross-agent metadata processing"""
        # Mock database response with multiple agents
        mock_supabase_manager.execute_query.return_value = [
            {
                'id': 'strand_1',
                'agent_id': 'agent_1',
                'kind': 'detection',
                'module_intelligence': {'pattern_type': 'divergence'},
                'created_at': datetime.now(timezone.utc) - timedelta(minutes=5),
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'sig_sigma': 0.8,
                'sig_confidence': 0.7
            },
            {
                'id': 'strand_2',
                'agent_id': 'agent_2',
                'kind': 'detection',
                'module_intelligence': {'pattern_type': 'volume_spike'},
                'created_at': datetime.now(timezone.utc) - timedelta(minutes=3),
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'sig_sigma': 0.9,
                'sig_confidence': 0.8
            }
        ]
        
        # Process cross-agent metadata
        metadata = await input_processor.process_cross_agent_metadata()
        
        # Verify results
        assert isinstance(metadata, CrossAgentMetaData)
        assert 'agent_1' in metadata.timing_patterns
        assert 'agent_2' in metadata.timing_patterns
        assert 'divergence' in metadata.signal_families
        assert 'volume_spike' in metadata.signal_families
        assert len(metadata.coverage_map) > 0
    
    @pytest.mark.asyncio
    async def test_process_market_regime_context(self, input_processor, mock_supabase_manager):
        """Test market regime context processing"""
        # Mock database response
        mock_supabase_manager.execute_query.return_value = [
            {
                'regime': 'high_vol',
                'session_bucket': 'US',
                'symbol': 'BTC',
                'timeframe': '1h',
                'avg_signal_strength': 0.8,
                'detection_count': 10
            },
            {
                'regime': 'high_vol',
                'session_bucket': 'EU',
                'symbol': 'ETH',
                'timeframe': '4h',
                'avg_signal_strength': 0.6,
                'detection_count': 5
            }
        ]
        
        # Process market regime context
        context = await input_processor.process_market_regime_context()
        
        # Verify results
        assert isinstance(context, MarketRegimeContext)
        assert context.current_regime == 'high_vol'
        assert 'US' in context.session_structure
        assert 'EU' in context.session_structure
        assert 'BTC' in context.cross_asset_state
        assert 'ETH' in context.cross_asset_state
        assert context.volatility_band in ['high_vol', 'medium_vol', 'low_vol']
    
    @pytest.mark.asyncio
    async def test_process_historical_performance(self, input_processor, mock_supabase_manager):
        """Test historical performance processing"""
        # Mock database response
        mock_supabase_manager.execute_query.return_value = [
            {
                'id': 'strand_1',
                'kind': 'detection',
                'agent_id': 'agent_1',
                'sig_sigma': 0.9,
                'sig_confidence': 0.8,
                'outcome_score': 0.7,
                'module_intelligence': {'pattern_type': 'divergence'},
                'tags': ['success'],
                'created_at': datetime.now(timezone.utc),
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol'
            },
            {
                'id': 'strand_2',
                'kind': 'lesson',
                'agent_id': 'agent_2',
                'sig_sigma': 0.3,
                'sig_confidence': 0.2,
                'outcome_score': 0.1,
                'module_intelligence': {'pattern_type': 'failed_pattern'},
                'tags': ['lesson', 'failure'],
                'created_at': datetime.now(timezone.utc),
                'symbol': 'ETH',
                'timeframe': '4h',
                'regime': 'low_vol'
            }
        ]
        
        # Process historical performance
        performance = await input_processor.process_historical_performance()
        
        # Verify results
        assert isinstance(performance, HistoricalPerformance)
        assert len(performance.success_patterns) > 0
        assert len(performance.failed_patterns) > 0
        assert len(performance.lesson_strands) > 0
    
    @pytest.mark.asyncio
    async def test_process_experiment_registry(self, input_processor, mock_supabase_manager):
        """Test experiment registry processing"""
        # Mock database response
        mock_supabase_manager.execute_query.return_value = [
            {
                'id': 'exp_1',
                'kind': 'experiment_active',
                'experiment_id': 'EXP_001',
                'module_intelligence': {'hypothesis': 'Test divergence detection'},
                'tags': ['experiment:active'],
                'created_at': datetime.now(timezone.utc),
                'sig_sigma': 0.5,
                'sig_confidence': 0.6,
                'outcome_score': 0.0
            },
            {
                'id': 'exp_2',
                'kind': 'experiment_completed',
                'experiment_id': 'EXP_002',
                'module_intelligence': {'hypothesis': 'Test volume analysis'},
                'tags': ['experiment:completed'],
                'created_at': datetime.now(timezone.utc),
                'sig_sigma': 0.8,
                'sig_confidence': 0.7,
                'outcome_score': 0.8
            }
        ]
        
        # Process experiment registry
        registry = await input_processor.process_experiment_registry()
        
        # Verify results
        assert isinstance(registry, ExperimentRegistry)
        assert len(registry.active_experiments) > 0
        assert len(registry.completed_experiments) > 0
    
    def test_extract_detection_type(self, input_processor):
        """Test detection type extraction"""
        # Test with module intelligence
        row = {
            'module_intelligence': {'pattern_type': 'divergence'},
            'tags': ['agent:test:detection'],
            'kind': 'detection'
        }
        detection_type = input_processor._extract_detection_type(row, row['module_intelligence'])
        assert detection_type == 'divergence'
        
        # Test with tags
        row = {
            'module_intelligence': {},
            'tags': ['agent:test:detection:volume_spike'],
            'kind': 'detection'
        }
        detection_type = input_processor._extract_detection_type(row, row['module_intelligence'])
        assert detection_type == 'volume_spike'
        
        # Test with kind
        row = {
            'module_intelligence': {},
            'tags': [],
            'kind': 'pattern_detection'
        }
        detection_type = input_processor._extract_detection_type(row, row['module_intelligence'])
        assert detection_type == 'pattern_detection'
    
    def test_extract_performance_tags(self, input_processor):
        """Test performance tag extraction"""
        # Test with performance tags
        row = {
            'tags': ['profitable', 'high_accuracy', 'success'],
            'module_intelligence': {'performance_rating': 'excellent'}
        }
        performance_tags = input_processor._extract_performance_tags(row, row['module_intelligence'])
        assert 'profitable' in performance_tags
        assert 'performance:excellent' in performance_tags
        
        # Test without performance tags
        row = {
            'tags': ['agent:test:detection'],
            'module_intelligence': {}
        }
        performance_tags = input_processor._extract_performance_tags(row, row['module_intelligence'])
        assert len(performance_tags) == 0
    
    def test_calculate_strand_similarity(self, input_processor):
        """Test strand similarity calculation"""
        strand1 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'module_intelligence': {'pattern_type': 'divergence'}
        }
        
        strand2 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'module_intelligence': {'pattern_type': 'divergence'}
        }
        
        similarity = input_processor._calculate_strand_similarity(strand1, strand2)
        assert similarity == 1.0  # Perfect match
        
        # Test partial match
        strand3 = {
            'symbol': 'ETH',
            'timeframe': '4h',
            'regime': 'low_vol',
            'session_bucket': 'EU',
            'module_intelligence': {'pattern_type': 'volume_spike'}
        }
        
        similarity = input_processor._calculate_strand_similarity(strand1, strand3)
        assert 0.0 < similarity < 1.0  # Partial match
    
    def test_determine_volatility_band(self, input_processor):
        """Test volatility band determination"""
        # High volatility
        result = [{'avg_signal_strength': 0.9}, {'avg_signal_strength': 0.8}]
        volatility = input_processor._determine_volatility_band(result)
        assert volatility == 'high_vol'
        
        # Medium volatility
        result = [{'avg_signal_strength': 0.6}, {'avg_signal_strength': 0.5}]
        volatility = input_processor._determine_volatility_band(result)
        assert volatility == 'medium_vol'
        
        # Low volatility
        result = [{'avg_signal_strength': 0.3}, {'avg_signal_strength': 0.2}]
        volatility = input_processor._determine_volatility_band(result)
        assert volatility == 'low_vol'
    
    def test_determine_correlation_state(self, input_processor):
        """Test correlation state determination"""
        # Loose correlation
        result = [
            {'symbol': 'BTC'}, {'symbol': 'ETH'}, {'symbol': 'SOL'},
            {'symbol': 'ADA'}, {'symbol': 'DOT'}, {'symbol': 'LINK'}
        ]
        correlation = input_processor._determine_correlation_state(result)
        assert correlation == 'loose_correlation'
        
        # Moderate correlation
        result = [
            {'symbol': 'BTC'}, {'symbol': 'ETH'}, {'symbol': 'SOL'}
        ]
        correlation = input_processor._determine_correlation_state(result)
        assert correlation == 'moderate_correlation'
        
        # Tight correlation
        result = [{'symbol': 'BTC'}, {'symbol': 'ETH'}]
        correlation = input_processor._determine_correlation_state(result)
        assert correlation == 'tight_correlation'
    
    @pytest.mark.asyncio
    async def test_publish_processing_results(self, input_processor, mock_supabase_manager):
        """Test publishing processing results"""
        processed_inputs = {
            'agent_outputs': [{'agent_id': 'test_agent'}],
            'cross_agent_metadata': {'confluence_events': [{'event': 'test'}]},
            'market_regime_context': {'current_regime': 'high_vol'},
            'experiment_registry': {'active_experiments': [{'id': 'exp_1'}]},
            'processing_errors': []
        }
        
        await input_processor._publish_processing_results(processed_inputs)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_input_processing'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['cil_team_member'] == 'input_processor'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
