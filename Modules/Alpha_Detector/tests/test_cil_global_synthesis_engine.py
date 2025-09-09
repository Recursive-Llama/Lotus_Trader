"""
Test CIL Global Synthesis Engine
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.engines.global_synthesis_engine import (
    GlobalSynthesisEngine, CrossAgentCorrelation, CoverageAnalysis, SignalFamily,
    MetaPattern, DoctrineInsight
)


class TestGlobalSynthesisEngine:
    """Test CIL Global Synthesis Engine"""
    
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
    def synthesis_engine(self, mock_supabase_manager, mock_llm_client):
        """Create GlobalSynthesisEngine instance"""
        return GlobalSynthesisEngine(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_agent_output(self):
        """Mock agent output"""
        output = Mock()
        output.agent_id = 'test_agent'
        output.detection_type = 'divergence'
        output.timestamp = datetime.now(timezone.utc)
        output.context = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US'
        }
        output.confidence = 0.8
        output.signal_strength = 0.7
        return output
    
    @pytest.fixture
    def mock_processed_inputs(self, mock_agent_output):
        """Mock processed inputs"""
        return {
            'agent_outputs': [mock_agent_output],
            'cross_agent_metadata': {
                'confluence_events': [
                    {
                        'timestamp': datetime.now(timezone.utc),
                        'strand1': 'strand_1',
                        'strand2': 'strand_2',
                        'similarity_score': 0.8
                    }
                ],
                'lead_lag_relationships': [
                    {
                        'lead_agent': 'agent_1',
                        'lag_agent': 'agent_2',
                        'lead_lag_score': 0.7,
                        'sample_size': 10
                    }
                ],
                'coverage_map': {
                    'BTC_1h_high_vol_US': {
                        'symbol': 'BTC',
                        'timeframe': '1h',
                        'regime': 'high_vol',
                        'session_bucket': 'US',
                        'agents': ['agent_1', 'agent_2'],
                        'detection_count': 15
                    }
                }
            },
            'market_regime_context': {
                'current_regime': 'high_vol',
                'session_structure': {'US': 10, 'EU': 5},
                'cross_asset_state': {'BTC': 8, 'ETH': 3}
            },
            'historical_performance': {
                'success_patterns': [
                    {
                        'id': 'success_1',
                        'module_intelligence': {'pattern_type': 'divergence'},
                        'outcome_score': 0.8,
                        'sig_confidence': 0.7,
                        'sig_sigma': 0.9,
                        'regime': 'high_vol',
                        'session_bucket': 'US',
                        'created_at': datetime.now(timezone.utc)
                    }
                ],
                'failed_patterns': [
                    {
                        'id': 'failed_1',
                        'module_intelligence': {'pattern_type': 'volume_spike'},
                        'outcome_score': 0.2,
                        'sig_confidence': 0.3,
                        'sig_sigma': 0.4,
                        'regime': 'low_vol',
                        'session_bucket': 'EU',
                        'created_at': datetime.now(timezone.utc)
                    }
                ]
            },
            'experiment_registry': {
                'active_experiments': [],
                'completed_experiments': []
            }
        }
    
    def test_synthesis_engine_initialization(self, synthesis_engine):
        """Test GlobalSynthesisEngine initialization"""
        assert synthesis_engine.supabase_manager is not None
        assert synthesis_engine.llm_client is not None
        assert synthesis_engine.correlation_window_hours == 24
        assert synthesis_engine.family_analysis_window_days == 7
        assert synthesis_engine.correlation_threshold == 0.7
        assert synthesis_engine.confluence_threshold == 0.8
    
    @pytest.mark.asyncio
    async def test_synthesize_global_view_success(self, synthesis_engine, mock_processed_inputs):
        """Test successful global view synthesis"""
        # Mock the individual analysis methods
        with patch.object(synthesis_engine, 'analyze_cross_agent_correlation') as mock_correlation, \
             patch.object(synthesis_engine, 'analyze_coverage_and_blind_spots') as mock_coverage, \
             patch.object(synthesis_engine, 'analyze_signal_families') as mock_families, \
             patch.object(synthesis_engine, 'analyze_meta_patterns') as mock_patterns, \
             patch.object(synthesis_engine, 'form_doctrine_insights') as mock_doctrine:
            
            # Set up mock returns
            mock_correlation.return_value = CrossAgentCorrelation(
                coincidences=[], lead_lag_patterns=[], confluence_events=[],
                correlation_strength=0.8, confidence_score=0.7
            )
            mock_coverage.return_value = CoverageAnalysis(
                redundant_areas=[], blind_spots=[], coverage_gaps=[],
                coverage_score=0.9, efficiency_score=0.8
            )
            mock_families.return_value = []
            mock_patterns.return_value = []
            mock_doctrine.return_value = []
            
            # Synthesize global view
            result = await synthesis_engine.synthesize_global_view(mock_processed_inputs)
            
            # Verify structure
            assert 'cross_agent_correlation' in result
            assert 'coverage_analysis' in result
            assert 'signal_families' in result
            assert 'meta_patterns' in result
            assert 'doctrine_insights' in result
            assert 'synthesis_timestamp' in result
            assert 'synthesis_errors' in result
            
            # Verify processing timestamp
            assert isinstance(result['synthesis_timestamp'], datetime)
    
    @pytest.mark.asyncio
    async def test_analyze_cross_agent_correlation(self, synthesis_engine, mock_processed_inputs):
        """Test cross-agent correlation analysis"""
        # Mock the individual detection methods
        with patch.object(synthesis_engine, '_detect_agent_coincidences') as mock_coincidences, \
             patch.object(synthesis_engine, '_analyze_lead_lag_patterns') as mock_lead_lag, \
             patch.object(synthesis_engine, '_detect_confluence_events') as mock_confluence:
            
            # Set up mock returns
            mock_coincidences.return_value = [
                {
                    'timestamp': datetime.now(timezone.utc),
                    'agent1': 'agent_1',
                    'agent2': 'agent_2',
                    'similarity_score': 0.8
                }
            ]
            mock_lead_lag.return_value = [
                {
                    'lead_agent': 'agent_1',
                    'lag_agent': 'agent_2',
                    'lead_lag_score': 0.7,
                    'consistency_score': 0.8
                }
            ]
            mock_confluence.return_value = [
                {
                    'timestamp': datetime.now(timezone.utc),
                    'strand1': 'strand_1',
                    'strand2': 'strand_2',
                    'similarity_score': 0.9
                }
            ]
            
            # Analyze cross-agent correlation
            correlation = await synthesis_engine.analyze_cross_agent_correlation(mock_processed_inputs)
            
            # Verify results
            assert isinstance(correlation, CrossAgentCorrelation)
            assert len(correlation.coincidences) == 1
            assert len(correlation.lead_lag_patterns) == 1
            assert len(correlation.confluence_events) == 1
            assert correlation.correlation_strength > 0
            assert correlation.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_analyze_coverage_and_blind_spots(self, synthesis_engine, mock_processed_inputs):
        """Test coverage and blind spot analysis"""
        # Analyze coverage and blind spots
        coverage = await synthesis_engine.analyze_coverage_and_blind_spots(mock_processed_inputs)
        
        # Verify results
        assert isinstance(coverage, CoverageAnalysis)
        assert isinstance(coverage.redundant_areas, list)
        assert isinstance(coverage.blind_spots, list)
        assert isinstance(coverage.coverage_gaps, list)
        assert 0.0 <= coverage.coverage_score <= 1.0
        assert 0.0 <= coverage.efficiency_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_signal_families(self, synthesis_engine, mock_processed_inputs):
        """Test signal family analysis"""
        # Mock the family analysis method
        with patch.object(synthesis_engine, '_analyze_signal_family') as mock_family_analysis:
            mock_family_analysis.return_value = SignalFamily(
                family_name='divergence',
                family_members=['signal_1', 'signal_2'],
                performance_metrics={'success_rate': 0.8},
                regime_performance={'high_vol': 0.9},
                session_performance={'US': 0.8},
                evolution_trend='improving',
                family_strength=0.8
            )
            
            # Analyze signal families
            families = await synthesis_engine.analyze_signal_families(mock_processed_inputs)
            
            # Verify results
            assert isinstance(families, list)
            if families:  # Only check if families were found
                family = families[0]
                assert isinstance(family, SignalFamily)
                assert family.family_name == 'divergence'
                assert family.family_strength > 0
    
    @pytest.mark.asyncio
    async def test_analyze_meta_patterns(self, synthesis_engine, mock_processed_inputs):
        """Test meta-pattern analysis"""
        # Mock the meta-pattern analysis methods
        with patch.object(synthesis_engine, '_analyze_confluence_meta_patterns') as mock_confluence, \
             patch.object(synthesis_engine, '_analyze_lead_lag_meta_patterns') as mock_lead_lag, \
             patch.object(synthesis_engine, '_analyze_regime_meta_patterns') as mock_regime:
            
            # Set up mock returns
            mock_confluence.return_value = []
            mock_lead_lag.return_value = []
            mock_regime.return_value = []
            
            # Analyze meta-patterns
            patterns = await synthesis_engine.analyze_meta_patterns(mock_processed_inputs)
            
            # Verify results
            assert isinstance(patterns, list)
    
    @pytest.mark.asyncio
    async def test_form_doctrine_insights(self, synthesis_engine, mock_processed_inputs):
        """Test doctrine insight formation"""
        # Mock the individual analysis methods
        with patch.object(synthesis_engine, 'analyze_signal_families') as mock_families, \
             patch.object(synthesis_engine, 'analyze_meta_patterns') as mock_patterns, \
             patch.object(synthesis_engine, 'analyze_cross_agent_correlation') as mock_correlation, \
             patch.object(synthesis_engine, '_form_family_doctrine_insights') as mock_family_insights, \
             patch.object(synthesis_engine, '_form_pattern_doctrine_insights') as mock_pattern_insights, \
             patch.object(synthesis_engine, '_form_correlation_doctrine_insights') as mock_correlation_insights:
            
            # Set up mock returns
            mock_families.return_value = []
            mock_patterns.return_value = []
            mock_correlation.return_value = CrossAgentCorrelation(
                coincidences=[], lead_lag_patterns=[], confluence_events=[],
                correlation_strength=0.0, confidence_score=0.0
            )
            mock_family_insights.return_value = []
            mock_pattern_insights.return_value = []
            mock_correlation_insights.return_value = []
            
            # Form doctrine insights
            insights = await synthesis_engine.form_doctrine_insights(mock_processed_inputs)
            
            # Verify results
            assert isinstance(insights, list)
    
    def test_are_outputs_similar(self, synthesis_engine, mock_agent_output):
        """Test output similarity detection"""
        # Create similar output
        similar_output = Mock()
        similar_output.agent_id = 'test_agent_2'
        similar_output.detection_type = 'divergence'
        similar_output.context = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US'
        }
        
        # Test similarity
        is_similar = synthesis_engine._are_outputs_similar(mock_agent_output, similar_output)
        assert is_similar is True
        
        # Create different output
        different_output = Mock()
        different_output.agent_id = 'test_agent_3'
        different_output.detection_type = 'volume_spike'
        different_output.context = {
            'symbol': 'ETH',
            'timeframe': '4h',
            'regime': 'low_vol',
            'session_bucket': 'EU'
        }
        
        # Test dissimilarity
        is_similar = synthesis_engine._are_outputs_similar(mock_agent_output, different_output)
        assert is_similar is False
    
    def test_calculate_output_similarity(self, synthesis_engine, mock_agent_output):
        """Test output similarity calculation"""
        # Create similar output
        similar_output = Mock()
        similar_output.detection_type = 'divergence'
        similar_output.context = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US'
        }
        
        # Test similarity calculation
        similarity = synthesis_engine._calculate_output_similarity(mock_agent_output, similar_output)
        assert similarity == 1.0  # Perfect match
        
        # Create partially similar output
        partial_output = Mock()
        partial_output.detection_type = 'volume_spike'
        partial_output.context = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US'
        }
        
        # Test partial similarity
        similarity = synthesis_engine._calculate_output_similarity(mock_agent_output, partial_output)
        assert 0.0 < similarity < 1.0  # Partial match
    
    def test_calculate_correlation_strength(self, synthesis_engine):
        """Test correlation strength calculation"""
        coincidences = [{'similarity_score': 0.8}, {'similarity_score': 0.9}]
        lead_lag_patterns = [{'lead_lag_score': 0.7}, {'lead_lag_score': 0.8}]
        confluence_events = [{'similarity_score': 0.9}]
        
        strength = synthesis_engine._calculate_correlation_strength(
            coincidences, lead_lag_patterns, confluence_events
        )
        
        assert 0.0 <= strength <= 1.0
        assert strength > 0.0  # Should be positive with the test data
    
    def test_calculate_correlation_confidence(self, synthesis_engine):
        """Test correlation confidence calculation"""
        confidence = synthesis_engine._calculate_correlation_confidence(
            total_outputs=100, coincidences=5, lead_lag_patterns=3
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.0  # Should be positive with the test data
    
    def test_calculate_coverage_score(self, synthesis_engine):
        """Test coverage score calculation"""
        coverage_map = {
            'context_1': {'detection_count': 10},
            'context_2': {'detection_count': 5},
            'context_3': {'detection_count': 0}
        }
        
        score = synthesis_engine._calculate_coverage_score(coverage_map)
        assert 0.0 <= score <= 1.0
        assert score == 2/3  # 2 out of 3 contexts have detections
    
    def test_calculate_efficiency_score(self, synthesis_engine):
        """Test efficiency score calculation"""
        redundant_areas = [
            {'efficiency_loss': 2},
            {'efficiency_loss': 1}
        ]
        coverage_map = {
            'context_1': {'agents': ['agent_1', 'agent_2', 'agent_3']},
            'context_2': {'agents': ['agent_4', 'agent_5']}
        }
        
        score = synthesis_engine._calculate_efficiency_score(redundant_areas, coverage_map)
        assert 0.0 <= score <= 1.0
    
    def test_extract_pattern_type(self, synthesis_engine):
        """Test pattern type extraction"""
        # Test with module intelligence
        pattern = {
            'module_intelligence': {'pattern_type': 'divergence'},
            'kind': 'detection'
        }
        pattern_type = synthesis_engine._extract_pattern_type(pattern)
        assert pattern_type == 'divergence'
        
        # Test fallback to kind
        pattern = {
            'module_intelligence': {},
            'kind': 'volume_analysis'
        }
        pattern_type = synthesis_engine._extract_pattern_type(pattern)
        assert pattern_type == 'volume_analysis'
    
    def test_determine_evolution_trend(self, synthesis_engine):
        """Test evolution trend determination"""
        # Test improving trend
        signals = [
            {'outcome_score': 0.5, 'created_at': datetime.now(timezone.utc) - timedelta(hours=2)},
            {'outcome_score': 0.8, 'created_at': datetime.now(timezone.utc)}
        ]
        trend = synthesis_engine._determine_evolution_trend(signals)
        assert trend == 'improving'
        
        # Test declining trend
        signals = [
            {'outcome_score': 0.8, 'created_at': datetime.now(timezone.utc) - timedelta(hours=2)},
            {'outcome_score': 0.5, 'created_at': datetime.now(timezone.utc)}
        ]
        trend = synthesis_engine._determine_evolution_trend(signals)
        assert trend == 'declining'
        
        # Test stable trend
        signals = [
            {'outcome_score': 0.6, 'created_at': datetime.now(timezone.utc) - timedelta(hours=2)},
            {'outcome_score': 0.6, 'created_at': datetime.now(timezone.utc)}
        ]
        trend = synthesis_engine._determine_evolution_trend(signals)
        assert trend == 'stable'
    
    def test_calculate_family_strength(self, synthesis_engine):
        """Test family strength calculation"""
        success_rate = 0.8
        regime_performance = {'high_vol': 0.9, 'low_vol': 0.7}
        session_performance = {'US': 0.8, 'EU': 0.8}
        
        strength = synthesis_engine._calculate_family_strength(
            success_rate, regime_performance, session_performance
        )
        
        assert 0.0 <= strength <= 1.0
        assert strength > 0.0  # Should be positive with the test data
    
    @pytest.mark.asyncio
    async def test_publish_synthesis_results(self, synthesis_engine, mock_supabase_manager):
        """Test publishing synthesis results"""
        global_view = {
            'cross_agent_correlation': {'correlation_strength': 0.8},
            'coverage_analysis': {'coverage_score': 0.9, 'efficiency_score': 0.8},
            'signal_families': [{'family_name': 'divergence'}],
            'meta_patterns': [{'pattern_name': 'confluence'}],
            'doctrine_insights': [{'insight_type': 'recommendation'}],
            'synthesis_errors': []
        }
        
        await synthesis_engine._publish_synthesis_results(global_view)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_global_synthesis'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['team_member'] == 'global_synthesis_engine'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
