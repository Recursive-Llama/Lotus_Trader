"""
Test Suite for Decision Maker Phase 2 CIL Integration

Tests the implementation of Phase 2 components:
- RiskMotifIntegration
- StrategicRiskInsightConsumer
- CrossTeamRiskIntegration
- EnhancedDecisionMakerAgent (Phase 2 specific methods)

Validates strategic risk intelligence integration, motif creation, and cross-team awareness.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any, List

# Import the components to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from src.intelligence.decision_maker.risk_motif_integration import RiskMotifIntegration
from src.intelligence.decision_maker.strategic_risk_insight_consumer import StrategicRiskInsightConsumer
from src.intelligence.decision_maker.cross_team_risk_integration import CrossTeamRiskIntegration
from src.intelligence.decision_maker.enhanced_decision_agent_base import EnhancedDecisionMakerAgent

class TestRiskMotifIntegration:
    """Test RiskMotifIntegration component"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def risk_motif_integration(self, mock_supabase_manager):
        """Create RiskMotifIntegration instance for testing"""
        return RiskMotifIntegration(mock_supabase_manager)

    @pytest.mark.asyncio
    async def test_create_risk_motif_from_pattern(self, risk_motif_integration):
        """Test creating risk motif from pattern"""
        risk_pattern_data = {
            'risk_type': 'portfolio_risk',
            'risk_confidence': 0.8,
            'agent': 'test_agent',
            'strand_id': 'test_strand_123'
        }
        
        motif_id = await risk_motif_integration.create_risk_motif_from_pattern(risk_pattern_data)
        
        # Verify motif ID is generated
        assert isinstance(motif_id, str)
        assert len(motif_id) > 0

    @pytest.mark.asyncio
    async def test_enhance_existing_risk_motif(self, risk_motif_integration):
        """Test enhancing existing risk motif"""
        risk_motif_id = "test_motif_123"
        new_risk_evidence = {
            'risk_type': 'portfolio_risk',
            'confidence': 0.9,
            'new_insights': ['insight1', 'insight2']
        }
        
        enhancement_id = await risk_motif_integration.enhance_existing_risk_motif(risk_motif_id, new_risk_evidence)
        
        # Verify enhancement ID is generated
        assert isinstance(enhancement_id, str)
        assert len(enhancement_id) > 0

    @pytest.mark.asyncio
    async def test_query_risk_motif_families(self, risk_motif_integration):
        """Test querying risk motif families"""
        risk_type = "portfolio_risk"
        
        motif_families = await risk_motif_integration.query_risk_motif_families(risk_type)
        
        # Verify motif families structure
        assert isinstance(motif_families, list)
        assert len(motif_families) > 0
        
        for family in motif_families:
            assert 'risk_motif_id' in family
            assert 'type' in family
            assert 'avg_resonance' in family
            assert 'risk_patterns_count' in family

    @pytest.mark.asyncio
    async def test_find_related_risk_motifs(self, risk_motif_integration):
        """Test finding related risk motifs"""
        risk_pattern_data = {
            'risk_type': 'portfolio_risk',
            'confidence': 0.7
        }
        
        related_motifs = await risk_motif_integration.find_related_risk_motifs(risk_pattern_data)
        
        # Verify related motifs structure
        assert isinstance(related_motifs, list)
        
        for motif in related_motifs:
            assert 'risk_motif_id' in motif
            assert 'type' in motif
            assert 'similarity_score' in motif
            assert 'resonance_score' in motif

    @pytest.mark.asyncio
    async def test_evolve_risk_motif(self, risk_motif_integration):
        """Test evolving risk motif"""
        risk_motif_id = "test_motif_456"
        evolution_data = {
            'evolution_type': 'natural_selection',
            'new_evidence': 'test_evidence'
        }
        
        evolution_id = await risk_motif_integration.evolve_risk_motif(risk_motif_id, evolution_data)
        
        # Verify evolution ID is generated
        assert isinstance(evolution_id, str)
        assert len(evolution_id) > 0

class TestStrategicRiskInsightConsumer:
    """Test StrategicRiskInsightConsumer component"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def strategic_risk_insight_consumer(self, mock_supabase_manager):
        """Create StrategicRiskInsightConsumer instance for testing"""
        return StrategicRiskInsightConsumer(mock_supabase_manager)

    @pytest.mark.asyncio
    async def test_consume_cil_risk_insights(self, strategic_risk_insight_consumer):
        """Test consuming CIL risk insights"""
        risk_type = "portfolio_risk"
        
        insights = await strategic_risk_insight_consumer.consume_cil_risk_insights(risk_type)
        
        # Verify insights structure
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        for insight in insights:
            assert 'insight_id' in insight
            assert 'type' in insight
            assert 'strategic_value' in insight
            assert 'details' in insight

    @pytest.mark.asyncio
    async def test_subscribe_to_valuable_risk_meta_signals(self, strategic_risk_insight_consumer):
        """Test subscribing to valuable risk meta signals"""
        risk_meta_signal_types = ['strategic_risk_confluence', 'risk_experiment_insights', 'unknown_type']
        
        subscription_result = await strategic_risk_insight_consumer.subscribe_to_valuable_risk_meta_signals(risk_meta_signal_types)
        
        # Verify subscription result structure
        assert 'subscribed_types' in subscription_result
        assert 'unsubscribed_types' in subscription_result
        assert 'subscription_timestamp' in subscription_result
        
        # Verify some types were subscribed to
        assert len(subscription_result['subscribed_types']) > 0

    @pytest.mark.asyncio
    async def test_contribute_to_strategic_risk_analysis(self, strategic_risk_insight_consumer):
        """Test contributing to strategic risk analysis"""
        risk_analysis_data = {
            'agent': 'test_agent',
            'risk_type': 'portfolio_risk',
            'confidence': 0.8
        }
        
        contribution_id = await strategic_risk_insight_consumer.contribute_to_strategic_risk_analysis(risk_analysis_data)
        
        # Verify contribution ID is generated
        assert isinstance(contribution_id, str)
        assert len(contribution_id) > 0

    @pytest.mark.asyncio
    async def test_apply_risk_insights_to_analysis(self, strategic_risk_insight_consumer):
        """Test applying risk insights to analysis"""
        risk_insights = [
            {'strategic_value': 'high', 'type': 'market_risk_regime_shift'},
            {'strategic_value': 'medium', 'type': 'portfolio_concentration_alert'}
        ]
        current_risk_analysis = {
            'risk_type': 'portfolio_risk',
            'confidence': 0.6
        }
        
        enhanced_analysis = await strategic_risk_insight_consumer.apply_risk_insights_to_analysis(risk_insights, current_risk_analysis)
        
        # Verify enhanced analysis structure
        assert 'cil_risk_insights_applied' in enhanced_analysis
        assert 'risk_confidence_boost' in enhanced_analysis
        assert enhanced_analysis['risk_confidence_boost'] > 0

    @pytest.mark.asyncio
    async def test_identify_valuable_risk_experiments(self, strategic_risk_insight_consumer):
        """Test identifying valuable risk experiments"""
        risk_insights = [
            {'strategic_value': 'high', 'type': 'market_risk_regime_shift', 'insight_id': 'insight_1'},
            {'strategic_value': 'medium', 'type': 'portfolio_concentration_alert', 'insight_id': 'insight_2'}
        ]
        
        experiments = await strategic_risk_insight_consumer.identify_valuable_risk_experiments(risk_insights)
        
        # Verify experiments structure
        assert isinstance(experiments, list)
        assert len(experiments) > 0  # Should have at least one high-value experiment
        
        for experiment in experiments:
            assert 'experiment_id' in experiment
            assert 'type' in experiment
            assert 'priority' in experiment
            assert 'suggested_actions' in experiment

class TestCrossTeamRiskIntegration:
    """Test CrossTeamRiskIntegration component"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def cross_team_risk_integration(self, mock_supabase_manager):
        """Create CrossTeamRiskIntegration instance for testing"""
        return CrossTeamRiskIntegration(mock_supabase_manager)

    @pytest.mark.asyncio
    async def test_detect_cross_team_risk_confluence(self, cross_team_risk_integration):
        """Test detecting cross-team risk confluence"""
        time_window = "5m"
        
        confluence_patterns = await cross_team_risk_integration.detect_cross_team_risk_confluence(time_window)
        
        # Verify confluence patterns structure
        assert isinstance(confluence_patterns, list)
        assert len(confluence_patterns) > 0
        
        for pattern in confluence_patterns:
            assert 'confluence_id' in pattern
            assert 'description' in pattern
            assert 'teams' in pattern
            assert 'strength' in pattern
            assert 'risk_types' in pattern

    @pytest.mark.asyncio
    async def test_identify_risk_lead_lag_patterns(self, cross_team_risk_integration):
        """Test identifying risk lead-lag patterns"""
        team_pairs = [('raw_data_intelligence', 'decision_maker'), ('pattern_intelligence', 'decision_maker')]
        
        lead_lag_patterns = await cross_team_risk_integration.identify_risk_lead_lag_patterns(team_pairs)
        
        # Verify lead-lag patterns structure
        assert isinstance(lead_lag_patterns, list)
        assert len(lead_lag_patterns) > 0
        
        for pattern in lead_lag_patterns:
            assert 'lead_team' in pattern
            assert 'lag_team' in pattern
            assert 'risk_pattern_type' in pattern
            assert 'lag_time_min' in pattern
            assert 'consistency' in pattern

    @pytest.mark.asyncio
    async def test_contribute_to_strategic_risk_analysis(self, cross_team_risk_integration):
        """Test contributing to strategic risk analysis"""
        risk_confluence_data = {
            'description': 'Test confluence pattern',
            'teams': ['decision_maker', 'raw_data_intelligence'],
            'strength': 0.8
        }
        
        contribution_id = await cross_team_risk_integration.contribute_to_strategic_risk_analysis(risk_confluence_data)
        
        # Verify contribution ID is generated
        assert isinstance(contribution_id, str)
        assert len(contribution_id) > 0

    @pytest.mark.asyncio
    async def test_analyze_risk_correlation_matrix(self, cross_team_risk_integration):
        """Test analyzing risk correlation matrix"""
        team_risk_data = {
            'decision_maker': [{'risk_type': 'portfolio_risk', 'confidence': 0.8}],
            'raw_data_intelligence': [{'risk_type': 'volume_risk', 'confidence': 0.7}]
        }
        
        correlation_analysis = await cross_team_risk_integration.analyze_risk_correlation_matrix(team_risk_data)
        
        # Verify correlation analysis structure
        assert 'correlation_matrix' in correlation_analysis
        assert 'strongest_correlations' in correlation_analysis
        assert 'analysis_timestamp' in correlation_analysis

    @pytest.mark.asyncio
    async def test_detect_risk_anomaly_clusters(self, cross_team_risk_integration):
        """Test detecting risk anomaly clusters"""
        time_window = "10m"
        
        anomaly_clusters = await cross_team_risk_integration.detect_risk_anomaly_clusters(time_window)
        
        # Verify anomaly clusters structure
        assert isinstance(anomaly_clusters, list)
        assert len(anomaly_clusters) > 0
        
        for cluster in anomaly_clusters:
            assert 'cluster_id' in cluster
            assert 'description' in cluster
            assert 'teams_involved' in cluster
            assert 'anomaly_strength' in cluster
            assert 'risk_types' in cluster

class TestEnhancedDecisionMakerAgentPhase2:
    """Test EnhancedDecisionMakerAgent Phase 2 specific methods"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        return Mock()

    @pytest.fixture
    def enhanced_agent(self, mock_supabase_manager, mock_llm_client):
        """Create EnhancedDecisionMakerAgent instance for testing"""
        return EnhancedDecisionMakerAgent("test_agent", mock_supabase_manager, mock_llm_client)

    @pytest.mark.asyncio
    async def test_contribute_to_risk_motif(self, enhanced_agent):
        """Test contributing to risk motif"""
        risk_pattern_data = {
            'risk_type': 'portfolio_risk',
            'confidence': 0.8,
            'agent': 'test_agent'
        }
        
        motif_id = await enhanced_agent.contribute_to_risk_motif(risk_pattern_data)
        
        # Verify motif ID is generated
        assert isinstance(motif_id, str)
        assert len(motif_id) > 0

    @pytest.mark.asyncio
    async def test_consume_strategic_risk_insights(self, enhanced_agent):
        """Test consuming strategic risk insights"""
        risk_type = "portfolio_risk"
        
        insights = await enhanced_agent.consume_strategic_risk_insights(risk_type)
        
        # Verify insights are returned
        assert isinstance(insights, list)
        assert len(insights) > 0

    @pytest.mark.asyncio
    async def test_detect_cross_team_risk_confluence(self, enhanced_agent):
        """Test detecting cross-team risk confluence"""
        time_window = "5m"
        
        confluence_patterns = await enhanced_agent.detect_cross_team_risk_confluence(time_window)
        
        # Verify confluence patterns are returned
        assert isinstance(confluence_patterns, list)
        assert len(confluence_patterns) > 0

    def test_enable_risk_motif_integration(self, enhanced_agent):
        """Test enabling/disabling risk motif integration"""
        # Test enabling
        enhanced_agent.enable_risk_motif_integration(True)
        assert enhanced_agent.risk_motif_integration_enabled == True
        
        # Test disabling
        enhanced_agent.enable_risk_motif_integration(False)
        assert enhanced_agent.risk_motif_integration_enabled == False

    def test_enable_strategic_risk_insight_consumption(self, enhanced_agent):
        """Test enabling/disabling strategic risk insight consumption"""
        # Test enabling
        enhanced_agent.enable_strategic_risk_insight_consumption(True)
        assert enhanced_agent.strategic_risk_insight_consumption_enabled == True
        
        # Test disabling
        enhanced_agent.enable_strategic_risk_insight_consumption(False)
        assert enhanced_agent.strategic_risk_insight_consumption_enabled == False

    def test_enable_cross_team_risk_awareness(self, enhanced_agent):
        """Test enabling/disabling cross-team risk awareness"""
        # Test enabling
        enhanced_agent.enable_cross_team_risk_awareness(True)
        assert enhanced_agent.cross_team_risk_awareness_enabled == True
        
        # Test disabling
        enhanced_agent.enable_cross_team_risk_awareness(False)
        assert enhanced_agent.cross_team_risk_awareness_enabled == False

    @pytest.mark.asyncio
    async def test_analyze_risk_with_phase2_integration(self, enhanced_agent):
        """Test risk analysis with Phase 2 integration"""
        market_data = {'symbol': 'BTC', 'price': 50000}
        raw_data_analysis = {'patterns': ['volume_spike'], 'confidence': 0.6}
        
        result = await enhanced_agent.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify Phase 2 components are integrated
        assert 'cil_risk_insights' in result
        assert 'risk_motif_contribution' in result
        assert 'cross_team_risk_confluence' in result

    @pytest.mark.asyncio
    async def test_get_risk_learning_summary_phase2(self, enhanced_agent):
        """Test getting risk learning summary with Phase 2 metrics"""
        summary = await enhanced_agent.get_risk_learning_summary()
        
        # Verify Phase 2 metrics are included
        assert 'risk_motif_contributions' in summary
        assert 'strategic_risk_insights_consumed' in summary
        assert 'cross_team_risk_confluence_detections' in summary
        assert 'risk_motif_integration_enabled' in summary
        assert 'strategic_risk_insight_consumption_enabled' in summary
        assert 'cross_team_risk_awareness_enabled' in summary

class TestPhase2IntegrationEndToEnd:
    """End-to-end integration tests for Phase 2"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        return Mock()

    @pytest.mark.asyncio
    async def test_complete_phase2_workflow(self, mock_supabase_manager, mock_llm_client):
        """Test complete Phase 2 workflow"""
        # Create components
        risk_motif = RiskMotifIntegration(mock_supabase_manager)
        strategic_insight_consumer = StrategicRiskInsightConsumer(mock_supabase_manager)
        cross_team_integration = CrossTeamRiskIntegration(mock_supabase_manager)
        enhanced_agent = EnhancedDecisionMakerAgent("test_agent", mock_supabase_manager, mock_llm_client)
        
        # Test data
        market_data = {'symbol': 'ETH', 'price': 3000}
        raw_data_analysis = {'patterns': ['divergence'], 'confidence': 0.6}
        
        # Run complete workflow
        result = await enhanced_agent.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify workflow completed successfully with Phase 2 components
        assert 'agent' in result
        assert 'cil_risk_insights' in result
        assert 'risk_motif_contribution' in result
        assert 'cross_team_risk_confluence' in result
        assert result['agent'] == 'test_agent'

    @pytest.mark.asyncio
    async def test_strategic_risk_intelligence_network(self, mock_supabase_manager, mock_llm_client):
        """Test strategic risk intelligence network functionality"""
        # Create multiple agents
        agent1 = EnhancedDecisionMakerAgent("risk_agent_1", mock_supabase_manager, mock_llm_client)
        agent2 = EnhancedDecisionMakerAgent("risk_agent_2", mock_supabase_manager, mock_llm_client)
        
        # Test data
        market_data = {'symbol': 'BTC', 'price': 50000}
        raw_data_analysis = {'patterns': ['volume_spike'], 'confidence': 0.7}
        
        # Run analysis on both agents
        result1 = await agent1.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        result2 = await agent2.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify both agents completed successfully with Phase 2 integration
        assert result1['agent'] == 'risk_agent_1'
        assert result2['agent'] == 'risk_agent_2'
        assert 'cil_risk_insights' in result1
        assert 'cil_risk_insights' in result2
        assert 'risk_motif_contribution' in result1
        assert 'risk_motif_contribution' in result2

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
