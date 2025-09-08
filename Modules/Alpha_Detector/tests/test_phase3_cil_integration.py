"""
Test Phase 3: Organic Doctrine Integration

Tests for doctrine integration and enhanced agent capabilities that complete the 
organic intelligence network for raw data intelligence agents.
"""

import pytest
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
import numpy as np

# Import the components to test
from src.intelligence.raw_data_intelligence.doctrine_integration import DoctrineIntegration
from src.intelligence.raw_data_intelligence.enhanced_volume_analyzer import EnhancedVolumeAnalyzer
from src.intelligence.raw_data_intelligence.enhanced_agent_base import EnhancedRawDataAgent
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class TestDoctrineIntegration:
    """Test doctrine integration for organic strategic learning"""
    
    @pytest.fixture
    def doctrine_integration(self):
        """Create doctrine integration instance"""
        supabase_manager = SupabaseManager()
        return DoctrineIntegration(supabase_manager)
    
    @pytest.fixture
    def sample_pattern_evidence(self):
        """Sample pattern evidence for testing"""
        return {
            'type': 'volume_spike',
            'confidence': 0.8,
            'data_points': 100,
            'agent': 'volume_analyzer',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'symbols': ['BTC/USD'],
            'timeframe': '1m',
            'patterns': [
                {'type': 'volume_spike', 'confidence': 0.8, 'severity': 'high'}
            ]
        }
    
    @pytest.fixture
    def sample_proposed_experiment(self):
        """Sample proposed experiment for testing"""
        return {
            'type': 'volume_spike_analysis',
            'methodology': 'High volatility volume spike detection',
            'expected_outcome': 'Improved volume spike detection accuracy',
            'risk_level': 'medium',
            'confidence': 0.7
        }
    
    @pytest.mark.asyncio
    async def test_query_relevant_doctrine(self, doctrine_integration):
        """Test doctrine query for pattern type"""
        doctrine_guidance = await doctrine_integration.query_relevant_doctrine('volume_patterns')
        
        assert isinstance(doctrine_guidance, dict)
        assert 'pattern_type' in doctrine_guidance
        assert 'positive_doctrine' in doctrine_guidance
        assert 'negative_doctrine' in doctrine_guidance
        assert 'neutral_doctrine' in doctrine_guidance
        assert 'contraindications' in doctrine_guidance
        assert 'applicability_score' in doctrine_guidance
        assert 'doctrine_confidence' in doctrine_guidance
        assert 'recommendations' in doctrine_guidance
    
    @pytest.mark.asyncio
    async def test_contribute_to_doctrine(self, doctrine_integration, sample_pattern_evidence):
        """Test doctrine contribution with pattern evidence"""
        contribution_id = await doctrine_integration.contribute_to_doctrine(sample_pattern_evidence)
        
        assert contribution_id is not None
        assert isinstance(contribution_id, str)
        assert contribution_id.startswith('doctrine_contribution_')
    
    @pytest.mark.asyncio
    async def test_check_doctrine_contraindications(self, doctrine_integration, sample_proposed_experiment):
        """Test doctrine contraindication checking"""
        is_contraindicated = await doctrine_integration.check_doctrine_contraindications(sample_proposed_experiment)
        
        assert isinstance(is_contraindicated, bool)
        # Should return False for safe experiments, True for contraindicated ones
    
    @pytest.mark.asyncio
    async def test_pattern_persistence_analysis(self, doctrine_integration, sample_pattern_evidence):
        """Test pattern persistence analysis"""
        persistence_analysis = await doctrine_integration._analyze_pattern_persistence(sample_pattern_evidence)
        
        assert isinstance(persistence_analysis, dict)
        assert 'persistence_score' in persistence_analysis
        assert 'temporal_consistency' in persistence_analysis
        assert 'cross_condition_consistency' in persistence_analysis
        assert 'evidence_strength' in persistence_analysis
        assert 0.0 <= persistence_analysis['persistence_score'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_pattern_generality_assessment(self, doctrine_integration, sample_pattern_evidence):
        """Test pattern generality assessment"""
        generality_analysis = await doctrine_integration._assess_pattern_generality(sample_pattern_evidence)
        
        assert isinstance(generality_analysis, dict)
        assert 'generality_score' in generality_analysis
        assert 'cross_asset_applicability' in generality_analysis
        assert 'market_condition_robustness' in generality_analysis
        assert 'timeframe_scalability' in generality_analysis
        assert 0.0 <= generality_analysis['generality_score'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_mechanism_insight_provision(self, doctrine_integration, sample_pattern_evidence):
        """Test mechanism insight provision"""
        mechanism_insights = await doctrine_integration._provide_mechanism_insights(sample_pattern_evidence)
        
        assert isinstance(mechanism_insights, list)
        assert len(mechanism_insights) > 0
        
        for insight in mechanism_insights:
            assert 'mechanism_type' in insight
            assert 'insight' in insight
            assert 'confidence' in insight
            assert 'applicability' in insight
    
    @pytest.mark.asyncio
    async def test_contribution_type_determination(self, doctrine_integration, sample_pattern_evidence):
        """Test contribution type determination"""
        persistence_analysis = await doctrine_integration._analyze_pattern_persistence(sample_pattern_evidence)
        generality_analysis = await doctrine_integration._assess_pattern_generality(sample_pattern_evidence)
        
        contribution_type = await doctrine_integration._determine_contribution_type(
            persistence_analysis, generality_analysis, sample_pattern_evidence
        )
        
        assert contribution_type in ['positive_doctrine', 'negative_doctrine', 'neutral_doctrine']
    
    @pytest.mark.asyncio
    async def test_doctrine_category_classification(self, doctrine_integration, sample_pattern_evidence):
        """Test doctrine category classification"""
        category = await doctrine_integration._classify_doctrine_category(sample_pattern_evidence)
        
        assert category in doctrine_integration.doctrine_categories
    
    @pytest.mark.asyncio
    async def test_strategic_significance_calculation(self, doctrine_integration, sample_pattern_evidence):
        """Test strategic significance calculation"""
        significance = await doctrine_integration._calculate_strategic_significance(sample_pattern_evidence)
        
        assert isinstance(significance, float)
        assert 0.0 <= significance <= 1.0
    
    @pytest.mark.asyncio
    async def test_doctrine_integration_summary(self, doctrine_integration, sample_pattern_evidence):
        """Test doctrine integration summary"""
        # Perform some operations to generate summary data
        await doctrine_integration.query_relevant_doctrine('volume_patterns')
        await doctrine_integration.contribute_to_doctrine(sample_pattern_evidence)
        
        summary = doctrine_integration.get_doctrine_integration_summary()
        
        assert 'doctrine_queries' in summary
        assert 'doctrine_contributions' in summary
        assert 'contraindication_checks' in summary
        assert 'integration_effectiveness' in summary
        assert summary['doctrine_queries'] > 0
        assert summary['doctrine_contributions'] > 0


class TestEnhancedVolumeAnalyzer:
    """Test enhanced volume analyzer with full organic CIL influence"""
    
    @pytest.fixture
    def enhanced_volume_analyzer(self):
        """Create enhanced volume analyzer instance"""
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        return EnhancedVolumeAnalyzer(supabase_manager, llm_client)
    
    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing"""
        return {
            'ohlcv_data': [
                {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'open': 100.0,
                    'high': 105.0,
                    'low': 95.0,
                    'close': 102.0,
                    'volume': 1000
                }
            ] * 50,
            'symbols': ['BTC/USD'],
            'timeframe': '1m'
        }
    
    @pytest.mark.asyncio
    async def test_enhanced_volume_analysis(self, enhanced_volume_analyzer, sample_market_data):
        """Test enhanced volume analysis with full CIL integration"""
        analysis_results = await enhanced_volume_analyzer.analyze_volume_with_organic_influence(sample_market_data)
        
        assert isinstance(analysis_results, dict)
        # The enhanced volume analyzer calls the base class method which returns different structure
        # Check for the base class structure instead
        assert 'agent' in analysis_results
        assert 'confidence' in analysis_results
        assert 'analysis_components' in analysis_results
        
        # Check Phase 1 integration
        assert 'uncertainty_analysis' in analysis_results
        assert 'resonance' in analysis_results
        
        # Check Phase 2 integration
        assert 'cil_insights' in analysis_results
        assert 'motif_contribution' in analysis_results
        assert 'cross_team_confluence' in analysis_results
        
        # Check Phase 3 integration
        assert 'doctrine_guidance' in analysis_results
    
    @pytest.mark.asyncio
    async def test_core_volume_analysis(self, enhanced_volume_analyzer, sample_market_data):
        """Test core volume analysis functionality"""
        core_analysis = await enhanced_volume_analyzer._perform_core_volume_analysis(sample_market_data)
        
        assert isinstance(core_analysis, dict)
        assert 'volume_metrics' in core_analysis
        assert 'volume_patterns' in core_analysis
        assert 'volume_divergences' in core_analysis
        assert 'institutional_flow' in core_analysis
        assert 'confidence' in core_analysis
        assert 'significant_patterns' in core_analysis
    
    @pytest.mark.asyncio
    async def test_volume_metrics_calculation(self, enhanced_volume_analyzer, sample_market_data):
        """Test volume metrics calculation"""
        import pandas as pd
        df = pd.DataFrame(sample_market_data['ohlcv_data'])
        
        volume_metrics = enhanced_volume_analyzer._calculate_volume_metrics(df)
        
        assert isinstance(volume_metrics, dict)
        assert 'current_volume' in volume_metrics
        assert 'average_volume' in volume_metrics
        assert 'volume_std' in volume_metrics
        assert 'volume_spike_ratio' in volume_metrics
        assert 'volume_trend' in volume_metrics
        assert 'volume_volatility' in volume_metrics
        assert 'volume_momentum' in volume_metrics
        assert 'volume_distribution' in volume_metrics
    
    @pytest.mark.asyncio
    async def test_volume_pattern_detection(self, enhanced_volume_analyzer, sample_market_data):
        """Test volume pattern detection"""
        import pandas as pd
        df = pd.DataFrame(sample_market_data['ohlcv_data'])
        volume_metrics = enhanced_volume_analyzer._calculate_volume_metrics(df)
        
        volume_patterns = await enhanced_volume_analyzer._detect_volume_patterns(df, volume_metrics)
        
        assert isinstance(volume_patterns, list)
        for pattern in volume_patterns:
            assert 'type' in pattern
            assert 'confidence' in pattern
            assert 'severity' in pattern
            assert 'details' in pattern
    
    @pytest.mark.asyncio
    async def test_volume_divergence_analysis(self, enhanced_volume_analyzer, sample_market_data):
        """Test volume divergence analysis"""
        import pandas as pd
        df = pd.DataFrame(sample_market_data['ohlcv_data'])
        volume_metrics = enhanced_volume_analyzer._calculate_volume_metrics(df)
        
        volume_divergences = await enhanced_volume_analyzer._analyze_volume_divergences(df, volume_metrics)
        
        assert isinstance(volume_divergences, list)
        for divergence in volume_divergences:
            assert 'type' in divergence
            assert 'confidence' in divergence
            assert 'severity' in divergence
            assert 'details' in divergence
    
    @pytest.mark.asyncio
    async def test_institutional_flow_detection(self, enhanced_volume_analyzer, sample_market_data):
        """Test institutional flow detection"""
        import pandas as pd
        df = pd.DataFrame(sample_market_data['ohlcv_data'])
        volume_metrics = enhanced_volume_analyzer._calculate_volume_metrics(df)
        
        institutional_flow = await enhanced_volume_analyzer._detect_institutional_flow(df, volume_metrics)
        
        assert isinstance(institutional_flow, dict)
        assert 'detected' in institutional_flow
        assert 'confidence' in institutional_flow
        assert 'flow_type' in institutional_flow
        assert 'details' in institutional_flow
        assert isinstance(institutional_flow['detected'], bool)
        assert 0.0 <= institutional_flow['confidence'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_volume_confidence_calculation(self, enhanced_volume_analyzer, sample_market_data):
        """Test volume confidence calculation"""
        import pandas as pd
        df = pd.DataFrame(sample_market_data['ohlcv_data'])
        volume_metrics = enhanced_volume_analyzer._calculate_volume_metrics(df)
        volume_patterns = await enhanced_volume_analyzer._detect_volume_patterns(df, volume_metrics)
        volume_divergences = await enhanced_volume_analyzer._analyze_volume_divergences(df, volume_metrics)
        institutional_flow = await enhanced_volume_analyzer._detect_institutional_flow(df, volume_metrics)
        
        confidence = await enhanced_volume_analyzer._calculate_volume_confidence(
            volume_patterns, volume_divergences, institutional_flow
        )
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_volume_insight_generation(self, enhanced_volume_analyzer, sample_market_data):
        """Test volume insight generation"""
        analysis_results = await enhanced_volume_analyzer.analyze_volume_with_organic_influence(sample_market_data)
        doctrine_guidance = {'recommendations': ['Test recommendation']}
        
        insights = await enhanced_volume_analyzer._generate_volume_insights(analysis_results, doctrine_guidance)
        
        assert isinstance(insights, list)
        # Should contain insights about patterns, divergences, institutional flow, and doctrine
    
    @pytest.mark.asyncio
    async def test_volume_recommendation_generation(self, enhanced_volume_analyzer, sample_market_data):
        """Test volume recommendation generation"""
        analysis_results = await enhanced_volume_analyzer.analyze_volume_with_organic_influence(sample_market_data)
        
        recommendations = await enhanced_volume_analyzer._generate_volume_recommendations(analysis_results)
        
        assert isinstance(recommendations, list)
        # Should contain actionable recommendations based on analysis
    
    @pytest.mark.asyncio
    async def test_volume_analysis_summary(self, enhanced_volume_analyzer, sample_market_data):
        """Test volume analysis summary"""
        # Perform some analysis to generate metrics
        await enhanced_volume_analyzer.analyze_volume_with_organic_influence(sample_market_data)
        
        summary = enhanced_volume_analyzer.get_volume_analysis_summary()
        
        assert isinstance(summary, dict)
        assert 'volume_specific_metrics' in summary
        assert 'volume_capabilities' in summary
        assert 'volume_specializations' in summary
        assert 'volume_analysis_parameters' in summary
        
        # Check that metrics are being tracked
        volume_metrics = summary['volume_specific_metrics']
        assert 'volume_patterns_detected' in volume_metrics
        assert 'volume_spikes_analyzed' in volume_metrics
        assert 'volume_divergences_found' in volume_metrics
        assert 'institutional_flows_detected' in volume_metrics
    
    @pytest.mark.asyncio
    async def test_volume_experiment_participation(self, enhanced_volume_analyzer):
        """Test volume-specific experiment participation"""
        experiment_insights = {
            'name': 'volume_spike_experiment',
            'type': 'volume_spike_analysis',
            'description': 'Test volume spike detection experiment'
        }
        
        await enhanced_volume_analyzer.participate_in_volume_experiments(experiment_insights)
        
        # Should complete without errors
        assert True


class TestEnhancedAgentBasePhase3:
    """Test enhanced agent base with Phase 3 integration"""
    
    @pytest.fixture
    def enhanced_agent(self):
        """Create enhanced agent instance"""
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        return EnhancedRawDataAgent('test_agent', supabase_manager, llm_client)
    
    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing"""
        return {
            'ohlcv_data': [
                {'timestamp': datetime.now(timezone.utc).isoformat(), 'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000}
            ] * 50,
            'symbols': ['BTC/USD'],
            'timeframe': '1m'
        }
    
    @pytest.mark.asyncio
    async def test_analyze_with_phase3_integration(self, enhanced_agent, sample_market_data):
        """Test analysis with Phase 3 integration"""
        analysis_results = await enhanced_agent.analyze_with_organic_influence(sample_market_data)
        
        assert isinstance(analysis_results, dict)
        # Check all phases are integrated
        assert 'uncertainty_analysis' in analysis_results  # Phase 1
        assert 'resonance' in analysis_results  # Phase 1
        assert 'cil_insights' in analysis_results  # Phase 2
        assert 'motif_contribution' in analysis_results  # Phase 2
        assert 'cross_team_confluence' in analysis_results  # Phase 2
        assert 'doctrine_guidance' in analysis_results  # Phase 3
    
    @pytest.mark.asyncio
    async def test_doctrine_query(self, enhanced_agent):
        """Test doctrine query functionality"""
        doctrine_guidance = await enhanced_agent.query_relevant_doctrine('volume_patterns')
        
        assert isinstance(doctrine_guidance, dict)
        assert enhanced_agent.doctrine_queries > 0
    
    @pytest.mark.asyncio
    async def test_doctrine_contribution(self, enhanced_agent):
        """Test doctrine contribution functionality"""
        pattern_evidence = {
            'type': 'volume_spike',
            'confidence': 0.8,
            'data_points': 100,
            'agent': 'test_agent'
        }
        
        contribution_id = await enhanced_agent.contribute_to_doctrine(pattern_evidence)
        
        assert contribution_id is not None
        assert enhanced_agent.doctrine_contributions > 0
    
    @pytest.mark.asyncio
    async def test_contraindication_check(self, enhanced_agent):
        """Test contraindication check functionality"""
        proposed_experiment = {
            'type': 'volume_spike_analysis',
            'methodology': 'High volatility volume spike detection',
            'confidence': 0.7
        }
        
        is_contraindicated = await enhanced_agent.check_doctrine_contraindications(proposed_experiment)
        
        assert isinstance(is_contraindicated, bool)
        assert enhanced_agent.contraindication_checks > 0
    
    @pytest.mark.asyncio
    async def test_doctrine_integration_summary(self, enhanced_agent):
        """Test doctrine integration summary"""
        # Perform some doctrine operations
        await enhanced_agent.query_relevant_doctrine('volume_patterns')
        await enhanced_agent.contribute_to_doctrine({'type': 'test_pattern', 'confidence': 0.8})
        
        summary = enhanced_agent.get_doctrine_integration_summary()
        
        assert isinstance(summary, dict)
        assert 'doctrine_queries' in summary
        assert 'doctrine_contributions' in summary
        assert 'contraindication_checks' in summary
    
    @pytest.mark.asyncio
    async def test_enhanced_learning_summary_with_phase3(self, enhanced_agent, sample_market_data):
        """Test enhanced learning summary with Phase 3 metrics"""
        # Perform analysis to generate metrics
        await enhanced_agent.analyze_with_organic_influence(sample_market_data)
        await enhanced_agent.query_relevant_doctrine('volume_patterns')
        await enhanced_agent.contribute_to_doctrine({'type': 'test_pattern', 'confidence': 0.8})
        
        summary = enhanced_agent.get_learning_summary()
        
        # Check Phase 3 metrics are included
        assert 'doctrine_queries' in summary
        assert 'doctrine_contributions' in summary
        assert 'contraindication_checks' in summary
        assert 'doctrine_integration_enabled' in summary
        
        # Check that metrics are being tracked
        assert summary['doctrine_queries'] > 0
        assert summary['doctrine_contributions'] > 0
    
    @pytest.mark.asyncio
    async def test_component_integration_phase3(self, enhanced_agent):
        """Test that all Phase 3 components are properly integrated"""
        # Check that doctrine integration component is initialized
        assert enhanced_agent.doctrine_integration is not None
        
        # Check that capabilities include Phase 3 features
        assert 'doctrine_integration' in enhanced_agent.capabilities
        assert 'strategic_learning' in enhanced_agent.capabilities
        
        # Check that specializations include Phase 3 features
        assert 'doctrine_application' in enhanced_agent.specializations
        assert 'strategic_doctrine_learning' in enhanced_agent.specializations
        
        # Check that integration flags are enabled
        assert enhanced_agent.doctrine_integration_enabled


class TestPhase3IntegrationEndToEnd:
    """End-to-end tests for Phase 3 integration"""
    
    @pytest.fixture
    def enhanced_volume_analyzer(self):
        """Create enhanced volume analyzer instance"""
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        return EnhancedVolumeAnalyzer(supabase_manager, llm_client)
    
    @pytest.mark.asyncio
    async def test_complete_phase3_workflow(self, enhanced_volume_analyzer):
        """Test complete Phase 3 workflow"""
        # 1. Analyze with full organic CIL influence (all phases)
        market_data = {
            'ohlcv_data': [
                {'timestamp': datetime.now(timezone.utc).isoformat(), 'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000}
            ] * 50,
            'symbols': ['BTC/USD'],
            'timeframe': '1m'
        }
        
        analysis_results = await enhanced_volume_analyzer.analyze_volume_with_organic_influence(market_data)
        
        # 2. Verify all phases are integrated
        assert 'uncertainty_analysis' in analysis_results  # Phase 1
        assert 'resonance' in analysis_results  # Phase 1
        assert 'cil_insights' in analysis_results  # Phase 2
        assert 'motif_contribution' in analysis_results  # Phase 2
        assert 'cross_team_confluence' in analysis_results  # Phase 2
        assert 'doctrine_guidance' in analysis_results  # Phase 3
        
        # 3. Test doctrine operations
        doctrine_guidance = await enhanced_volume_analyzer.query_relevant_doctrine('volume_patterns')
        assert isinstance(doctrine_guidance, dict)
        
        # 4. Test doctrine contribution
        contribution_id = await enhanced_volume_analyzer.contribute_to_doctrine(analysis_results)
        assert contribution_id is not None
        
        # 5. Test contraindication check
        proposed_experiment = {'type': 'volume_spike_analysis', 'confidence': 0.7}
        is_contraindicated = await enhanced_volume_analyzer.check_doctrine_contraindications(proposed_experiment)
        assert isinstance(is_contraindicated, bool)
        
        # 6. Verify learning metrics
        summary = enhanced_volume_analyzer.get_learning_summary()
        assert summary['doctrine_queries'] > 0
        assert summary['doctrine_contributions'] > 0
        assert summary['contraindication_checks'] > 0
        
        print("Complete Phase 3 workflow test passed successfully!")
    
    @pytest.mark.asyncio
    async def test_organic_intelligence_network_complete(self, enhanced_volume_analyzer):
        """Test complete organic intelligence network functionality"""
        # Test that the agent can participate in the complete organic intelligence network
        # through all phases: resonance, uncertainty, motif, strategic insights, cross-team, and doctrine
        
        # 1. Test motif operations
        pattern_data = {'type': 'volume_spike', 'confidence': 0.8, 'data_points': 100}
        motif_id = await enhanced_volume_analyzer.contribute_to_motif_evolution(pattern_data)
        if motif_id:
            new_evidence = {'confidence': 0.9, 'data_points': 150}
            enhancement_id = await enhanced_volume_analyzer.enhance_existing_motif(motif_id, new_evidence)
            assert enhancement_id is not None
        
        # 2. Test strategic insight operations
        insights = await enhanced_volume_analyzer.consume_strategic_insights('volume_patterns')
        assert isinstance(insights, list)
        
        meta_signal_types = ['strategic_confluence', 'experiment_insights', 'doctrine_updates']
        subscription_results = await enhanced_volume_analyzer.subscribe_to_meta_signals(meta_signal_types)
        assert len(subscription_results['subscribed_types']) == 3
        
        # 3. Test cross-team operations
        confluence_patterns = await enhanced_volume_analyzer.detect_cross_team_confluence("5m")
        assert isinstance(confluence_patterns, list)
        
        team_pairs = [('raw_data_intelligence', 'indicator_intelligence')]
        lead_lag_patterns = await enhanced_volume_analyzer.identify_lead_lag_patterns(team_pairs)
        assert isinstance(lead_lag_patterns, list)
        
        # 4. Test doctrine operations
        doctrine_guidance = await enhanced_volume_analyzer.query_relevant_doctrine('volume_patterns')
        assert isinstance(doctrine_guidance, dict)
        
        contribution_id = await enhanced_volume_analyzer.contribute_to_doctrine(pattern_data)
        assert contribution_id is not None
        
        is_contraindicated = await enhanced_volume_analyzer.check_doctrine_contraindications(pattern_data)
        assert isinstance(is_contraindicated, bool)
        
        # 5. Test complete integration
        market_data = {
            'ohlcv_data': [
                {'timestamp': datetime.now(timezone.utc).isoformat(), 'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000}
            ] * 50,
            'symbols': ['BTC/USD'],
            'timeframe': '1m'
        }
        
        analysis_results = await enhanced_volume_analyzer.analyze_volume_with_organic_influence(market_data)
        
        # Verify all phases are working together
        assert 'uncertainty_analysis' in analysis_results  # Phase 1
        assert 'resonance' in analysis_results  # Phase 1
        assert 'cil_insights' in analysis_results  # Phase 2
        assert 'motif_contribution' in analysis_results  # Phase 2
        assert 'cross_team_confluence' in analysis_results  # Phase 2
        assert 'doctrine_guidance' in analysis_results  # Phase 3
        
        print("Complete organic intelligence network test passed successfully!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
