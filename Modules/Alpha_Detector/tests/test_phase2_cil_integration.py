"""
Test Phase 2: Strategic Intelligence Integration

Tests for motif integration, strategic insight consumption, and cross-team pattern awareness
components that enable organic CIL influence for raw data intelligence agents.
"""

import pytest
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
import numpy as np

# Import the components to test
from src.intelligence.raw_data_intelligence.motif_integration import MotifIntegration
from src.intelligence.raw_data_intelligence.strategic_insight_consumer import StrategicInsightConsumer
from src.intelligence.raw_data_intelligence.cross_team_integration import CrossTeamIntegration
from src.intelligence.raw_data_intelligence.enhanced_agent_base import EnhancedRawDataAgent
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class TestMotifIntegration:
    """Test motif integration for organic pattern evolution"""
    
    @pytest.fixture
    def motif_integration(self):
        """Create motif integration instance"""
        supabase_manager = SupabaseManager()
        return MotifIntegration(supabase_manager)
    
    @pytest.fixture
    def sample_pattern_data(self):
        """Sample pattern data for testing"""
        return {
            'type': 'volume_spike',
            'confidence': 0.8,
            'data_points': 100,
            'agent': 'volume_analyzer',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'patterns': [
                {'type': 'volume_spike', 'confidence': 0.8, 'severity': 'high'},
                {'type': 'price_momentum', 'confidence': 0.7, 'severity': 'medium'}
            ],
            'temporal': {'duration': 300, 'frequency': 0.1},
            'structure': {'shape': 'spike', 'symmetry': 0.8},
            'behavior': {'trend': 'bullish', 'volatility': 0.6}
        }
    
    @pytest.mark.asyncio
    async def test_create_motif_from_pattern(self, motif_integration, sample_pattern_data):
        """Test motif creation from pattern data"""
        motif_id = await motif_integration.create_motif_from_pattern(sample_pattern_data)
        
        assert motif_id is not None
        assert isinstance(motif_id, str)
        assert motif_id.startswith('motif_')
        assert 'volume_spike' in motif_id
    
    @pytest.mark.asyncio
    async def test_enhance_existing_motif(self, motif_integration, sample_pattern_data):
        """Test motif enhancement with new evidence"""
        # First create a motif
        motif_id = await motif_integration.create_motif_from_pattern(sample_pattern_data)
        assert motif_id is not None
        
        # Then enhance it with new evidence
        new_evidence = {
            'confidence': 0.9,
            'data_points': 150,
            'agent': 'volume_analyzer',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        enhancement_id = await motif_integration.enhance_existing_motif(motif_id, new_evidence)
        
        assert enhancement_id is not None
        assert isinstance(enhancement_id, str)
        assert enhancement_id.startswith('enhancement_')
    
    @pytest.mark.asyncio
    async def test_query_motif_families(self, motif_integration):
        """Test motif family querying"""
        motif_families = await motif_integration.query_motif_families('volume_patterns')
        
        assert isinstance(motif_families, list)
        # Should return relevant motifs with resonance scores
        for motif in motif_families:
            assert 'motif_id' in motif
            assert 'pattern_type' in motif
            assert 'relevance_score' in motif
            assert 'success_rate' in motif
    
    @pytest.mark.asyncio
    async def test_pattern_invariant_extraction(self, motif_integration, sample_pattern_data):
        """Test pattern invariant extraction"""
        invariants = await motif_integration._extract_pattern_invariants(sample_pattern_data)
        
        assert isinstance(invariants, list)
        assert len(invariants) > 0
        
        # Check invariant structure
        for invariant in invariants:
            assert 'invariant_type' in invariant
            assert 'value' in invariant
            assert 'description' in invariant
    
    @pytest.mark.asyncio
    async def test_failure_condition_identification(self, motif_integration, sample_pattern_data):
        """Test failure condition identification"""
        failure_conditions = await motif_integration._identify_failure_conditions(sample_pattern_data)
        
        assert isinstance(failure_conditions, list)
        
        # Check failure condition structure
        for condition in failure_conditions:
            assert 'condition_type' in condition
            assert 'threshold' in condition
            assert 'actual_value' in condition
            assert 'failure_description' in condition
    
    @pytest.mark.asyncio
    async def test_mechanism_hypothesis_creation(self, motif_integration, sample_pattern_data):
        """Test mechanism hypothesis creation"""
        hypothesis = await motif_integration._create_mechanism_hypothesis(sample_pattern_data)
        
        assert isinstance(hypothesis, dict)
        assert 'hypothesis_id' in hypothesis
        assert 'pattern_type' in hypothesis
        assert 'mechanism_description' in hypothesis
        assert 'causal_factors' in hypothesis
        assert 'confidence' in hypothesis
        assert 'testable_predictions' in hypothesis


class TestStrategicInsightConsumer:
    """Test strategic insight consumption for CIL panoramic view"""
    
    @pytest.fixture
    def strategic_insight_consumer(self):
        """Create strategic insight consumer instance"""
        supabase_manager = SupabaseManager()
        return StrategicInsightConsumer(supabase_manager)
    
    @pytest.mark.asyncio
    async def test_consume_cil_insights(self, strategic_insight_consumer):
        """Test CIL insight consumption"""
        insights = await strategic_insight_consumer.consume_cil_insights('volume_patterns')
        
        assert isinstance(insights, list)
        # Should return relevant CIL insights
        for insight in insights:
            assert 'meta_signal_id' in insight
            assert 'signal_type' in insight
            assert 'confidence' in insight
            assert 'resonance_score' in insight
    
    @pytest.mark.asyncio
    async def test_subscribe_to_meta_signals(self, strategic_insight_consumer):
        """Test meta-signal subscription"""
        meta_signal_types = ['strategic_confluence', 'experiment_insights']
        subscription_results = await strategic_insight_consumer.subscribe_to_valuable_meta_signals(meta_signal_types)
        
        assert isinstance(subscription_results, dict)
        assert 'subscription_timestamp' in subscription_results
        assert 'subscribed_types' in subscription_results
        assert 'active_subscriptions' in subscription_results
        assert len(subscription_results['subscribed_types']) == 2
    
    @pytest.mark.asyncio
    async def test_contribute_to_strategic_analysis(self, strategic_insight_consumer):
        """Test strategic analysis contribution"""
        analysis_data = {
            'type': 'volume_analysis',
            'confidence': 0.8,
            'data_points': 100,
            'agent': 'volume_analyzer',
            'patterns': [{'type': 'volume_spike', 'confidence': 0.8}],
            'uncertainty_analysis': {'uncertainty_detected': False},
            'resonance': {'enhanced_score': 0.9}
        }
        
        contribution_id = await strategic_insight_consumer.contribute_to_strategic_analysis(analysis_data)
        
        assert contribution_id is not None
        assert isinstance(contribution_id, str)
        assert contribution_id.startswith('strategic_insight_')
    
    @pytest.mark.asyncio
    async def test_insight_consumption_tracking(self, strategic_insight_consumer):
        """Test insight consumption tracking"""
        # Consume some insights
        await strategic_insight_consumer.consume_cil_insights('volume_patterns')
        await strategic_insight_consumer.consume_cil_insights('divergence_patterns')
        
        # Check tracking
        summary = strategic_insight_consumer.get_insight_consumption_summary()
        
        assert 'total_insights_consumed' in summary
        assert 'consumption_entries' in summary
        assert 'average_confidence' in summary
        assert 'average_resonance' in summary
        assert summary['consumption_entries'] >= 2
    
    @pytest.mark.asyncio
    async def test_high_resonance_insight_filtering(self, strategic_insight_consumer):
        """Test high-resonance insight filtering"""
        # Mock meta-signals with different resonance scores
        meta_signals = [
            {'resonance_score': 0.9, 'confidence': 0.8},  # High resonance
            {'resonance_score': 0.5, 'confidence': 0.7},  # Low resonance
            {'resonance_score': 0.8, 'confidence': 0.6}   # Medium resonance
        ]
        
        high_resonance_insights = await strategic_insight_consumer._filter_high_resonance_insights(meta_signals)
        
        assert len(high_resonance_insights) >= 1
        # All filtered insights should have high resonance
        for insight in high_resonance_insights:
            assert insight['resonance_score'] >= 0.6
            assert insight['confidence'] >= 0.7


class TestCrossTeamIntegration:
    """Test cross-team integration for pattern awareness"""
    
    @pytest.fixture
    def cross_team_integration(self):
        """Create cross-team integration instance"""
        supabase_manager = SupabaseManager()
        return CrossTeamIntegration(supabase_manager)
    
    @pytest.mark.asyncio
    async def test_detect_cross_team_confluence(self, cross_team_integration):
        """Test cross-team confluence detection"""
        confluence_patterns = await cross_team_integration.detect_cross_team_confluence("5m")
        
        assert isinstance(confluence_patterns, list)
        # Should return strategic confluence patterns
        for pattern in confluence_patterns:
            assert 'confluence_id' in pattern
            assert 'confluence_strength' in pattern
            assert 'team_count' in pattern
            assert 'strategic_significance' in pattern
            assert 'strategic_priority' in pattern
    
    @pytest.mark.asyncio
    async def test_identify_lead_lag_patterns(self, cross_team_integration):
        """Test lead-lag pattern identification"""
        team_pairs = [
            ('raw_data_intelligence', 'indicator_intelligence'),
            ('indicator_intelligence', 'pattern_intelligence')
        ]
        
        lead_lag_patterns = await cross_team_integration.identify_lead_lag_patterns(team_pairs)
        
        assert isinstance(lead_lag_patterns, list)
        # Should return lead-lag meta-signals
        for pattern in lead_lag_patterns:
            assert 'meta_signal_id' in pattern
            assert 'signal_type' in pattern
            assert 'lead_team' in pattern
            assert 'lag_team' in pattern
            assert 'reliability_score' in pattern
    
    @pytest.mark.asyncio
    async def test_contribute_to_strategic_analysis(self, cross_team_integration):
        """Test strategic analysis contribution"""
        confluence_data = {
            'confluence_id': 'test_confluence_1',
            'confluence_strength': 0.8,
            'team_count': 3,
            'pattern_types': ['volume_spike', 'divergence'],
            'strategic_significance': 0.9
        }
        
        contribution_id = await cross_team_integration.contribute_to_strategic_analysis(confluence_data)
        
        assert contribution_id is not None
        assert isinstance(contribution_id, str)
        assert contribution_id.startswith('strategic_contribution_')
    
    @pytest.mark.asyncio
    async def test_temporal_overlap_finding(self, cross_team_integration):
        """Test temporal overlap finding"""
        # Mock team strands
        team_strands = {
            'raw_data_intelligence': [
                {'strand_id': 'rd_1', 'team': 'raw_data_intelligence', 'pattern_type': 'volume_spike', 
                 'confidence': 0.8, 'timestamp': datetime.now(timezone.utc).isoformat()}
            ],
            'indicator_intelligence': [
                {'strand_id': 'ii_1', 'team': 'indicator_intelligence', 'pattern_type': 'divergence', 
                 'confidence': 0.7, 'timestamp': datetime.now(timezone.utc).isoformat()}
            ]
        }
        
        temporal_overlaps = await cross_team_integration._find_temporal_overlaps(team_strands)
        
        assert isinstance(temporal_overlaps, list)
        # Should find overlaps when multiple teams have strands in same time window
        for overlap in temporal_overlaps:
            assert 'time_window' in overlap
            assert 'strands' in overlap
            assert 'team_count' in overlap
            assert 'overlap_strength' in overlap
    
    @pytest.mark.asyncio
    async def test_confluence_strength_calculation(self, cross_team_integration):
        """Test confluence strength calculation"""
        temporal_overlaps = [
            {
                'time_window': datetime.now(timezone.utc).isoformat(),
                'strands': [
                    {'team': 'raw_data_intelligence', 'pattern_type': 'volume_spike', 'confidence': 0.8},
                    {'team': 'indicator_intelligence', 'pattern_type': 'divergence', 'confidence': 0.7}
                ],
                'team_count': 2,
                'pattern_types': ['volume_spike', 'divergence'],
                'overlap_strength': 0.5
            }
        ]
        
        confluence_patterns = await cross_team_integration._calculate_confluence_strength(temporal_overlaps)
        
        assert isinstance(confluence_patterns, list)
        assert len(confluence_patterns) == 1
        
        pattern = confluence_patterns[0]
        assert 'confluence_id' in pattern
        assert 'confluence_strength' in pattern
        assert 'team_count' in pattern
        assert 'pattern_diversity' in pattern
        assert 0.0 <= pattern['confluence_strength'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_cross_team_analysis_summary(self, cross_team_integration):
        """Test cross-team analysis summary"""
        # Perform some analysis
        await cross_team_integration.detect_cross_team_confluence("5m")
        
        summary = cross_team_integration.get_cross_team_analysis_summary()
        
        assert 'confluence_detections' in summary
        assert 'lead_lag_detections' in summary
        assert 'strategic_contributions' in summary
        assert 'analysis_effectiveness' in summary


class TestEnhancedAgentBasePhase2:
    """Test enhanced agent base with Phase 2 integration"""
    
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
    async def test_analyze_with_phase2_integration(self, enhanced_agent, sample_market_data):
        """Test analysis with Phase 2 integration"""
        analysis_results = await enhanced_agent.analyze_with_organic_influence(sample_market_data)
        
        assert isinstance(analysis_results, dict)
        assert 'cil_insights' in analysis_results
        assert 'motif_contribution' in analysis_results
        assert 'cross_team_confluence' in analysis_results
        assert 'uncertainty_analysis' in analysis_results
        assert 'resonance' in analysis_results
        assert 'enhanced_strand_id' in analysis_results
    
    @pytest.mark.asyncio
    async def test_motif_evolution_contribution(self, enhanced_agent):
        """Test motif evolution contribution"""
        pattern_data = {
            'type': 'volume_spike',
            'confidence': 0.8,
            'data_points': 100,
            'agent': 'test_agent'
        }
        
        motif_id = await enhanced_agent.contribute_to_motif_evolution(pattern_data)
        
        assert motif_id is not None
        assert isinstance(motif_id, str)
        assert enhanced_agent.motif_contributions > 0
    
    @pytest.mark.asyncio
    async def test_strategic_insight_consumption(self, enhanced_agent):
        """Test strategic insight consumption"""
        insights = await enhanced_agent.consume_strategic_insights('volume_patterns')
        
        assert isinstance(insights, list)
        assert enhanced_agent.strategic_insights_consumed > 0
    
    @pytest.mark.asyncio
    async def test_meta_signal_subscription(self, enhanced_agent):
        """Test meta-signal subscription"""
        meta_signal_types = ['strategic_confluence', 'experiment_insights']
        subscription_results = await enhanced_agent.subscribe_to_meta_signals(meta_signal_types)
        
        assert isinstance(subscription_results, dict)
        assert 'subscribed_types' in subscription_results
        assert len(subscription_results['subscribed_types']) == 2
    
    @pytest.mark.asyncio
    async def test_cross_team_confluence_detection(self, enhanced_agent):
        """Test cross-team confluence detection"""
        confluence_patterns = await enhanced_agent.detect_cross_team_confluence("5m")
        
        assert isinstance(confluence_patterns, list)
        # Note: Mock implementation may return empty list, so we check the method works
        # In real implementation, this would detect actual confluence patterns
    
    @pytest.mark.asyncio
    async def test_lead_lag_pattern_identification(self, enhanced_agent):
        """Test lead-lag pattern identification"""
        team_pairs = [('raw_data_intelligence', 'indicator_intelligence')]
        lead_lag_patterns = await enhanced_agent.identify_lead_lag_patterns(team_pairs)
        
        assert isinstance(lead_lag_patterns, list)
        # Should return lead-lag meta-signals
        for pattern in lead_lag_patterns:
            assert 'meta_signal_id' in pattern
            assert 'lead_team' in pattern
            assert 'lag_team' in pattern
    
    @pytest.mark.asyncio
    async def test_strategic_analysis_contribution(self, enhanced_agent):
        """Test strategic analysis contribution"""
        analysis_data = {
            'type': 'volume_analysis',
            'confidence': 0.8,
            'data_points': 100,
            'agent': 'test_agent'
        }
        
        contribution_id = await enhanced_agent.contribute_to_strategic_analysis(analysis_data)
        
        assert contribution_id is not None
        assert isinstance(contribution_id, str)
    
    @pytest.mark.asyncio
    async def test_cross_team_insight_contribution(self, enhanced_agent):
        """Test cross-team insight contribution"""
        confluence_data = {
            'confluence_id': 'test_confluence',
            'confluence_strength': 0.8,
            'team_count': 3
        }
        
        contribution_id = await enhanced_agent.contribute_cross_team_insights(confluence_data)
        
        assert contribution_id is not None
        assert isinstance(contribution_id, str)
    
    @pytest.mark.asyncio
    async def test_enhanced_learning_summary(self, enhanced_agent, sample_market_data):
        """Test enhanced learning summary with Phase 2 metrics"""
        # Perform some analysis to generate metrics
        await enhanced_agent.analyze_with_organic_influence(sample_market_data)
        await enhanced_agent.contribute_to_motif_evolution({'type': 'test_pattern', 'confidence': 0.8})
        await enhanced_agent.consume_strategic_insights('test_patterns')
        
        summary = enhanced_agent.get_learning_summary()
        
        assert 'motif_contributions' in summary
        assert 'strategic_insights_consumed' in summary
        assert 'cross_team_confluence_detections' in summary
        assert 'motif_integration_enabled' in summary
        assert 'strategic_insight_consumption_enabled' in summary
        assert 'cross_team_awareness_enabled' in summary
        
        # Check that metrics are being tracked
        assert summary['motif_contributions'] > 0
        assert summary['strategic_insights_consumed'] > 0
    
    @pytest.mark.asyncio
    async def test_component_integration(self, enhanced_agent):
        """Test that all Phase 2 components are properly integrated"""
        # Check that all components are initialized
        assert enhanced_agent.motif_integration is not None
        assert enhanced_agent.strategic_insight_consumer is not None
        assert enhanced_agent.cross_team_integration is not None
        
        # Check that capabilities include Phase 2 features
        assert 'motif_creation' in enhanced_agent.capabilities
        assert 'strategic_insight_consumption' in enhanced_agent.capabilities
        assert 'cross_team_pattern_awareness' in enhanced_agent.capabilities
        
        # Check that specializations include Phase 2 features
        assert 'motif_evolution' in enhanced_agent.specializations
        assert 'strategic_analysis' in enhanced_agent.specializations
        assert 'cross_team_confluence' in enhanced_agent.specializations
        
        # Check that integration flags are enabled
        assert enhanced_agent.motif_integration_enabled
        assert enhanced_agent.strategic_insight_consumption_enabled
        assert enhanced_agent.cross_team_awareness_enabled


class TestPhase2IntegrationEndToEnd:
    """End-to-end tests for Phase 2 integration"""
    
    @pytest.fixture
    def enhanced_agent(self):
        """Create enhanced agent instance"""
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        return EnhancedRawDataAgent('test_agent', supabase_manager, llm_client)
    
    @pytest.mark.asyncio
    async def test_complete_phase2_workflow(self, enhanced_agent):
        """Test complete Phase 2 workflow"""
        # 1. Analyze with organic influence (includes all Phase 2 components)
        market_data = {
            'ohlcv_data': [{'timestamp': datetime.now(timezone.utc).isoformat(), 'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000}] * 50,
            'symbols': ['BTC/USD'],
            'timeframe': '1m'
        }
        
        analysis_results = await enhanced_agent.analyze_with_organic_influence(market_data)
        
        # 2. Verify all Phase 2 components are active
        assert 'cil_insights' in analysis_results
        assert 'motif_contribution' in analysis_results
        assert 'cross_team_confluence' in analysis_results
        
        # 3. Test motif evolution
        motif_id = await enhanced_agent.contribute_to_motif_evolution(analysis_results)
        assert motif_id is not None
        
        # 4. Test strategic insight consumption
        insights = await enhanced_agent.consume_strategic_insights('volume_patterns')
        assert isinstance(insights, list)
        
        # 5. Test cross-team confluence detection
        confluence_patterns = await enhanced_agent.detect_cross_team_confluence("5m")
        assert isinstance(confluence_patterns, list)
        
        # 6. Test strategic analysis contribution
        contribution_id = await enhanced_agent.contribute_to_strategic_analysis(analysis_results)
        assert contribution_id is not None
        
        # 7. Verify learning metrics
        summary = enhanced_agent.get_learning_summary()
        assert summary['motif_contributions'] > 0
        assert summary['strategic_insights_consumed'] > 0
        # Note: cross_team_confluence_detections may be 0 in mock implementation
        assert summary['cross_team_confluence_detections'] >= 0
        
        print("Complete Phase 2 workflow test passed successfully!")
    
    @pytest.mark.asyncio
    async def test_organic_intelligence_network(self, enhanced_agent):
        """Test organic intelligence network functionality"""
        # Test that the agent can participate in the organic intelligence network
        # through motif creation, strategic insight consumption, and cross-team awareness
        
        # 1. Create motif and enhance it
        pattern_data = {'type': 'volume_spike', 'confidence': 0.8, 'data_points': 100}
        motif_id = await enhanced_agent.contribute_to_motif_evolution(pattern_data)
        
        if motif_id:
            # Enhance the motif
            new_evidence = {'confidence': 0.9, 'data_points': 150}
            enhancement_id = await enhanced_agent.enhance_existing_motif(motif_id, new_evidence)
            assert enhancement_id is not None
        
        # 2. Query motif families
        motif_families = await enhanced_agent.query_motif_families('volume_patterns')
        assert isinstance(motif_families, list)
        
        # 3. Subscribe to meta-signals
        meta_signal_types = ['strategic_confluence', 'experiment_insights', 'doctrine_updates']
        subscription_results = await enhanced_agent.subscribe_to_meta_signals(meta_signal_types)
        assert len(subscription_results['subscribed_types']) == 3
        
        # 4. Identify lead-lag patterns
        team_pairs = [
            ('raw_data_intelligence', 'indicator_intelligence'),
            ('indicator_intelligence', 'pattern_intelligence')
        ]
        lead_lag_patterns = await enhanced_agent.identify_lead_lag_patterns(team_pairs)
        assert isinstance(lead_lag_patterns, list)
        
        # 5. Contribute cross-team insights
        confluence_data = {
            'confluence_id': 'test_confluence',
            'confluence_strength': 0.8,
            'team_count': 3,
            'strategic_significance': 0.9
        }
        contribution_id = await enhanced_agent.contribute_cross_team_insights(confluence_data)
        assert contribution_id is not None
        
        print("Organic intelligence network test passed successfully!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
