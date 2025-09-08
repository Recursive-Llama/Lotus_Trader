"""
Test Suite for Decision Maker Phase 1 CIL Integration

Tests the implementation of Phase 1 components:
- RiskResonanceIntegration
- RiskUncertaintyHandler  
- EnhancedDecisionMakerAgent

Validates organic CIL influence, risk resonance calculations, and uncertainty-driven curiosity.
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

from src.intelligence.decision_maker.risk_resonance_integration import RiskResonanceIntegration
from src.intelligence.decision_maker.risk_uncertainty_handler import RiskUncertaintyHandler
from src.intelligence.decision_maker.enhanced_decision_agent_base import EnhancedDecisionMakerAgent

class TestRiskResonanceIntegration:
    """Test RiskResonanceIntegration component"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def risk_resonance_integration(self, mock_supabase_manager):
        """Create RiskResonanceIntegration instance for testing"""
        return RiskResonanceIntegration(mock_supabase_manager)

    @pytest.mark.asyncio
    async def test_calculate_risk_resonance(self, risk_resonance_integration):
        """Test risk resonance calculation"""
        risk_strand_data = {
            'risk_confidence': 0.7,
            'risk_type': 'portfolio_risk',
            'data': 'test_data'
        }
        
        result = await risk_resonance_integration.calculate_risk_resonance(risk_strand_data)
        
        # Verify result structure
        assert 'phi' in result
        assert 'rho' in result
        assert 'theta_contribution' in result
        assert 'telemetry' in result
        assert 'enhanced_risk_score' in result
        
        # Verify values are within expected ranges
        assert 0.0 <= result['phi'] <= 1.0
        assert 0.0 <= result['rho'] <= 1.0
        assert 0.0 <= result['enhanced_risk_score'] <= 2.0  # Can be enhanced above 1.0
        
        # Verify telemetry structure
        telemetry = result['telemetry']
        assert 'risk_sr' in telemetry
        assert 'risk_cr' in telemetry
        assert 'risk_xr' in telemetry
        assert 'risk_surprise' in telemetry

    @pytest.mark.asyncio
    async def test_find_risk_resonance_clusters(self, risk_resonance_integration):
        """Test finding risk resonance clusters"""
        risk_type = "portfolio_risk"
        
        clusters = await risk_resonance_integration.find_risk_resonance_clusters(risk_type)
        
        # Verify clusters structure
        assert isinstance(clusters, list)
        assert len(clusters) > 0
        
        for cluster in clusters:
            assert 'cluster_id' in cluster
            assert 'avg_phi' in cluster
            assert 'avg_rho' in cluster
            assert 'risk_patterns_count' in cluster
            assert 'strategic_risk_value' in cluster

    @pytest.mark.asyncio
    async def test_enhance_risk_score_with_resonance(self, risk_resonance_integration):
        """Test risk score enhancement with resonance"""
        risk_strand_id = "test_risk_strand_123"
        base_risk_score = 0.6
        
        enhanced_score = await risk_resonance_integration.enhance_risk_score_with_resonance(risk_strand_id, base_risk_score)
        
        # Verify enhanced score is higher than base score
        assert enhanced_score >= base_risk_score
        assert enhanced_score <= 2.0  # Should not exceed reasonable bounds

    @pytest.mark.asyncio
    async def test_detect_risk_feedback_loops(self, risk_resonance_integration):
        """Test risk feedback loop detection"""
        risk_strand_id = "test_risk_strand_456"
        
        feedback_loops = await risk_resonance_integration.detect_risk_feedback_loops(risk_strand_id)
        
        # Verify feedback loops structure
        assert isinstance(feedback_loops, list)
        
        for loop in feedback_loops:
            assert 'loop_id' in loop
            assert 'type' in loop
            assert 'strength' in loop
            assert 'related_risk_strands' in loop
            assert loop['type'] in ['positive', 'negative']

class TestRiskUncertaintyHandler:
    """Test RiskUncertaintyHandler component"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def risk_uncertainty_handler(self, mock_supabase_manager):
        """Create RiskUncertaintyHandler instance for testing"""
        return RiskUncertaintyHandler(mock_supabase_manager)

    @pytest.mark.asyncio
    async def test_detect_risk_uncertainty(self, risk_uncertainty_handler):
        """Test risk uncertainty detection"""
        risk_analysis_result = {
            'risk_confidence': 0.3,  # Low confidence = high uncertainty
            'risk_type': 'portfolio_risk',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'agent': 'test_agent'
        }
        
        uncertainty_details = await risk_uncertainty_handler.detect_risk_uncertainty(risk_analysis_result)
        
        # Verify uncertainty detection structure
        assert 'risk_uncertainty_detected' in uncertainty_details
        assert 'risk_uncertainty_score' in uncertainty_details
        assert 'risk_confidence_level' in uncertainty_details
        assert 'exploration_priority' in uncertainty_details
        assert 'risk_type' in uncertainty_details
        
        # Verify uncertainty is detected for low confidence
        assert uncertainty_details['risk_uncertainty_detected'] == True
        assert uncertainty_details['risk_uncertainty_score'] == 0.7  # 1.0 - 0.3
        assert uncertainty_details['exploration_priority'] == 'medium'  # 0.7 is medium priority

    @pytest.mark.asyncio
    async def test_publish_risk_uncertainty_strand(self, risk_uncertainty_handler):
        """Test publishing risk uncertainty strand"""
        risk_uncertainty_data = {
            'risk_uncertainty_detected': True,
            'risk_uncertainty_score': 0.8,
            'exploration_priority': 'high',
            'risk_type': 'portfolio_risk'
        }
        
        strand_id = await risk_uncertainty_handler.publish_risk_uncertainty_strand(risk_uncertainty_data)
        
        # Verify strand ID is generated
        assert isinstance(strand_id, str)
        assert len(strand_id) > 0
        assert 'risk_uncertainty_strand_' in strand_id

    @pytest.mark.asyncio
    async def test_handle_risk_uncertainty_resolution(self, risk_uncertainty_handler):
        """Test handling risk uncertainty resolution"""
        risk_uncertainty_id = "test_uncertainty_123"
        resolution_data = {
            'status': 'resolved',
            'progress': 'completed',
            'new_insights': ['insight1', 'insight2']
        }
        
        # Should not raise any exceptions
        await risk_uncertainty_handler.handle_risk_uncertainty_resolution(risk_uncertainty_id, resolution_data)

    @pytest.mark.asyncio
    async def test_assess_risk_pattern_clarity(self, risk_uncertainty_handler):
        """Test risk pattern clarity assessment"""
        risk_analysis_result = {
            'risk_patterns': [
                {'type': 'pattern1', 'confidence': 0.4},
                {'type': 'pattern2', 'confidence': 0.8}
            ]
        }
        
        clarity_assessment = await risk_uncertainty_handler.assess_risk_pattern_clarity(risk_analysis_result)
        
        # Verify clarity assessment structure
        assert 'pattern_count' in clarity_assessment
        assert 'clarity_score' in clarity_assessment
        assert 'uncertainty_indicators' in clarity_assessment
        assert 'exploration_opportunities' in clarity_assessment
        
        assert clarity_assessment['pattern_count'] == 2
        assert len(clarity_assessment['uncertainty_indicators']) > 0  # Should detect low confidence pattern

class TestEnhancedDecisionMakerAgent:
    """Test EnhancedDecisionMakerAgent component"""

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
    async def test_analyze_risk_with_organic_influence(self, enhanced_agent):
        """Test risk analysis with organic CIL influence"""
        market_data = {'symbol': 'BTC', 'price': 50000}
        raw_data_analysis = {'patterns': ['pattern1'], 'confidence': 0.7}
        
        result = await enhanced_agent.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify result structure
        assert 'agent' in result
        assert 'timestamp' in result
        assert 'risk_confidence' in result
        assert 'risk_type' in result
        assert 'risk_resonance' in result
        assert 'risk_uncertainty_analysis' in result
        assert 'enhanced_strand_id' in result
        
        # Verify agent name
        assert result['agent'] == 'test_agent'

    @pytest.mark.asyncio
    async def test_get_risk_learning_summary(self, enhanced_agent):
        """Test getting risk learning summary"""
        summary = await enhanced_agent.get_risk_learning_summary()
        
        # Verify summary structure
        assert 'agent' in summary
        assert 'risk_uncertainty_resolutions' in summary
        assert 'risk_resonance_contributions' in summary
        assert 'organic_risk_insights_gained' in summary
        assert 'learning_history_length' in summary
        assert 'cil_integration_enabled' in summary
        
        # Verify agent name
        assert summary['agent'] == 'test_agent'

    def test_get_capabilities(self, enhanced_agent):
        """Test getting agent capabilities"""
        capabilities = enhanced_agent.get_capabilities()
        
        # Verify capabilities structure
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert 'risk_analysis' in capabilities
        assert 'organic_cil_integration' in capabilities

    def test_get_specializations(self, enhanced_agent):
        """Test getting agent specializations"""
        specializations = enhanced_agent.get_specializations()
        
        # Verify specializations structure
        assert isinstance(specializations, list)
        assert len(specializations) > 0
        assert 'risk_pattern_detection' in specializations
        assert 'organic_risk_learning' in specializations

    def test_enable_cil_integration(self, enhanced_agent):
        """Test enabling/disabling CIL integration"""
        # Test enabling
        enhanced_agent.enable_cil_integration(True)
        assert enhanced_agent.cil_integration_enabled == True
        
        # Test disabling
        enhanced_agent.enable_cil_integration(False)
        assert enhanced_agent.cil_integration_enabled == False

    @pytest.mark.asyncio
    async def test_calculate_risk_resonance_contribution(self, enhanced_agent):
        """Test calculating risk resonance contribution"""
        risk_strand_data = {
            'risk_confidence': 0.6,
            'risk_type': 'portfolio_risk'
        }
        
        result = await enhanced_agent.calculate_risk_resonance_contribution(risk_strand_data)
        
        # Verify result structure
        assert 'risk_resonance' in result
        assert 'risk_influence' in result
        assert 'contribution_timestamp' in result

class TestPhase1IntegrationEndToEnd:
    """End-to-end integration tests for Phase 1"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        return Mock()

    @pytest.mark.asyncio
    async def test_complete_phase1_workflow(self, mock_supabase_manager, mock_llm_client):
        """Test complete Phase 1 workflow"""
        # Create components
        risk_resonance = RiskResonanceIntegration(mock_supabase_manager)
        risk_uncertainty = RiskUncertaintyHandler(mock_supabase_manager)
        enhanced_agent = EnhancedDecisionMakerAgent("test_agent", mock_supabase_manager, mock_llm_client)
        
        # Test data
        market_data = {'symbol': 'BTC', 'price': 50000}
        raw_data_analysis = {'patterns': ['volume_spike'], 'confidence': 0.6}
        
        # Run complete workflow
        result = await enhanced_agent.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify workflow completed successfully
        assert 'agent' in result
        assert 'risk_resonance' in result
        assert 'risk_uncertainty_analysis' in result
        assert result['agent'] == 'test_agent'

    @pytest.mark.asyncio
    async def test_organic_risk_intelligence_network(self, mock_supabase_manager, mock_llm_client):
        """Test organic risk intelligence network functionality"""
        # Create multiple agents
        agent1 = EnhancedDecisionMakerAgent("risk_agent_1", mock_supabase_manager, mock_llm_client)
        agent2 = EnhancedDecisionMakerAgent("risk_agent_2", mock_supabase_manager, mock_llm_client)
        
        # Test data
        market_data = {'symbol': 'ETH', 'price': 3000}
        raw_data_analysis = {'patterns': ['divergence'], 'confidence': 0.5}
        
        # Run analysis on both agents
        result1 = await agent1.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        result2 = await agent2.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify both agents completed successfully
        assert result1['agent'] == 'risk_agent_1'
        assert result2['agent'] == 'risk_agent_2'
        assert 'risk_resonance' in result1
        assert 'risk_resonance' in result2

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
