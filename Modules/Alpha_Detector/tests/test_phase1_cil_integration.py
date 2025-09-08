"""
Test Phase 1 CIL Integration for Raw Data Intelligence

Tests the Phase 1 implementation of organic CIL integration:
- Uncertainty Handler with positive framing
- Resonance Integration with φ, ρ, θ calculations
- Enhanced Agent Base Class with organic influence
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

from src.intelligence.raw_data_intelligence.uncertainty_handler import UncertaintyHandler
from src.intelligence.raw_data_intelligence.resonance_integration import ResonanceIntegration
from src.intelligence.raw_data_intelligence.enhanced_agent_base import EnhancedRawDataAgent


class TestUncertaintyHandler:
    """Test Uncertainty Handler with positive framing"""
    
    @pytest.fixture
    def uncertainty_handler(self):
        mock_supabase = Mock()
        return UncertaintyHandler(mock_supabase)
    
    @pytest.fixture
    def mock_analysis_result(self):
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'confidence': 0.4,  # Low confidence - should trigger uncertainty
            'data_points': 30,  # Below threshold - should trigger uncertainty
            'patterns': [
                {'type': 'volume_spike', 'severity': 'medium', 'confidence': 0.8},
                {'type': 'divergence', 'severity': 'low', 'confidence': 0.3}
            ],
            'analysis_components': {
                'volume': {'confidence': 0.8},
                'divergence': {'confidence': 0.3}
            },
            'significant_patterns': [
                {'type': 'volume_spike', 'severity': 'medium', 'confidence': 0.8}
            ]
        }
    
    @pytest.mark.asyncio
    async def test_uncertainty_detection_positive_framing(self, uncertainty_handler, mock_analysis_result):
        """Test that uncertainty is detected and framed positively"""
        result = await uncertainty_handler.detect_uncertainty(mock_analysis_result)
        
        # Should detect uncertainty (low confidence, insufficient data)
        assert result['uncertainty_detected'] == True
        assert len(result['uncertainty_types']) > 0
        assert len(result['exploration_opportunities']) > 0
        
        # Should have positive framing
        assert 'confidence_low' in result['uncertainty_types'] or 'data_insufficiency' in result['uncertainty_types']
        assert result['uncertainty_priority'] in ['low', 'medium', 'high']
    
    @pytest.mark.asyncio
    async def test_uncertainty_strand_publishing(self, uncertainty_handler, mock_analysis_result):
        """Test uncertainty strand publishing with positive framing"""
        uncertainty_data = await uncertainty_handler.detect_uncertainty(mock_analysis_result)
        strand_id = await uncertainty_handler.publish_uncertainty_strand(uncertainty_data)
        
        # Should return a strand ID
        assert strand_id is not None
        assert isinstance(strand_id, str)
        assert 'uncertainty_' in strand_id
    
    @pytest.mark.asyncio
    async def test_uncertainty_resolution_handling(self, uncertainty_handler, mock_analysis_result):
        """Test uncertainty resolution handling"""
        uncertainty_data = await uncertainty_handler.detect_uncertainty(mock_analysis_result)
        uncertainty_id = await uncertainty_handler.publish_uncertainty_strand(uncertainty_data)
        
        resolution_data = {
            'progress': 0.8,
            'learning_gained': {'key_insights': ['uncertainty_cause_identified']},
            'new_insights': ['resolution_method_improved']
        }
        
        resolution_strand = await uncertainty_handler.handle_uncertainty_resolution(
            uncertainty_id, resolution_data
        )
        
        # Should handle resolution successfully
        assert resolution_strand is not None


class TestResonanceIntegration:
    """Test Resonance Integration with φ, ρ, θ calculations"""
    
    @pytest.fixture
    def resonance_integration(self):
        mock_supabase = Mock()
        return ResonanceIntegration(mock_supabase)
    
    @pytest.fixture
    def mock_strand_data(self):
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'confidence': 0.7,
            'patterns': [
                {'type': 'volume_spike', 'severity': 'high', 'confidence': 0.9},
                {'type': 'volume_spike', 'severity': 'medium', 'confidence': 0.8}
            ],
            'analysis_components': {
                'volume': {'confidence': 0.8, 'patterns': 2},
                'divergence': {'confidence': 0.6, 'patterns': 1}
            },
            'significant_patterns': [
                {'type': 'volume_spike', 'severity': 'high', 'confidence': 0.9}
            ]
        }
    
    @pytest.mark.asyncio
    async def test_strand_resonance_calculation(self, resonance_integration, mock_strand_data):
        """Test φ, ρ, θ resonance calculations"""
        result = await resonance_integration.calculate_strand_resonance(mock_strand_data)
        
        # Should calculate all resonance values
        assert 'phi' in result
        assert 'rho' in result
        assert 'theta' in result
        assert 'enhanced_score' in result
        assert 'telemetry' in result
        assert 'resonance_confidence' in result
        
        # Values should be between 0 and 1
        assert 0.0 <= result['phi'] <= 1.0
        assert 0.0 <= result['rho'] <= 1.0
        assert 0.0 <= result['theta'] <= 1.0
        assert 0.0 <= result['enhanced_score'] <= 1.0
        assert 0.0 <= result['resonance_confidence'] <= 1.0
        
        # Enhanced score should be higher than base confidence
        assert result['enhanced_score'] >= mock_strand_data['confidence']
    
    @pytest.mark.asyncio
    async def test_resonance_cluster_finding(self, resonance_integration):
        """Test resonance cluster finding"""
        clusters = await resonance_integration.find_resonance_clusters('volume_spike')
        
        # Should return list of clusters
        assert isinstance(clusters, list)
        # Note: Mock implementation returns empty list, but structure is correct
    
    @pytest.mark.asyncio
    async def test_score_enhancement_with_resonance(self, resonance_integration):
        """Test score enhancement with resonance"""
        enhanced_score = await resonance_integration.enhance_score_with_resonance('test_strand_id')
        
        # Should return enhanced score
        assert isinstance(enhanced_score, float)
        assert enhanced_score >= 0.0


class TestEnhancedAgentBase:
    """Test Enhanced Agent Base Class with organic influence"""
    
    @pytest.fixture
    def enhanced_agent(self):
        mock_supabase = Mock()
        mock_llm = Mock()
        return EnhancedRawDataAgent('test_agent', mock_supabase, mock_llm)
    
    @pytest.fixture
    def mock_market_data(self):
        return {
            'symbol': 'BTC-USD',
            'data': 'mock_market_data',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    @pytest.mark.asyncio
    async def test_organic_influence_analysis(self, enhanced_agent, mock_market_data):
        """Test analysis with organic CIL influence"""
        result = await enhanced_agent.analyze_with_organic_influence(mock_market_data)
        
        # Should return enhanced analysis results
        assert 'timestamp' in result
        assert 'agent' in result
        assert result['agent'] == 'test_agent'
        
        # Should have CIL integration components
        assert 'resonance' in result
        assert 'uncertainty_analysis' in result
        assert 'enhanced_score' in result
        
        # Should have positive uncertainty framing
        uncertainty_analysis = result['uncertainty_analysis']
        assert 'uncertainty_detected' in uncertainty_analysis
        assert 'exploration_opportunities' in uncertainty_analysis
    
    @pytest.mark.asyncio
    async def test_resonance_contribution(self, enhanced_agent):
        """Test resonance contribution calculation"""
        mock_strand_data = {
            'confidence': 0.7,
            'patterns': [{'type': 'test_pattern', 'confidence': 0.8}]
        }
        
        result = await enhanced_agent.calculate_resonance_contribution(mock_strand_data)
        
        # Should return resonance contribution
        assert 'agent' in result
        assert 'resonance_contribution' in result
        assert 'theta_contribution' in result
        assert 'organic_influence' in result
        
        # Should track contribution
        assert enhanced_agent.resonance_contributions > 0
    
    @pytest.mark.asyncio
    async def test_organic_experiment_participation(self, enhanced_agent):
        """Test organic experiment participation"""
        experiment_insights = {
            'experiment_id': 'test_experiment',
            'type': 'uncertainty_resolution',
            'insights': ['test_insight']
        }
        
        result = await enhanced_agent.participate_in_organic_experiments(experiment_insights)
        
        # Should return experiment results
        assert 'agent' in result
        assert 'experiment_id' in result
        assert 'participation_timestamp' in result
        assert 'results' in result
        assert 'learning_gained' in result
    
    def test_learning_summary(self, enhanced_agent):
        """Test learning summary generation"""
        summary = enhanced_agent.get_learning_summary()
        
        # Should return learning summary
        assert 'agent' in summary
        assert 'uncertainty_resolutions' in summary
        assert 'resonance_contributions' in summary
        assert 'organic_insights_gained' in summary
        assert 'cil_integration_enabled' in summary
        assert 'uncertainty_embrace_enabled' in summary
        assert 'resonance_enhancement_enabled' in summary


class TestPhase1Integration:
    """Test Phase 1 integration end-to-end"""
    
    @pytest.fixture
    def phase1_setup(self):
        mock_supabase = Mock()
        mock_llm = Mock()
        
        uncertainty_handler = UncertaintyHandler(mock_supabase)
        resonance_integration = ResonanceIntegration(mock_supabase)
        enhanced_agent = EnhancedRawDataAgent('integration_test_agent', mock_supabase, mock_llm)
        
        return {
            'uncertainty_handler': uncertainty_handler,
            'resonance_integration': resonance_integration,
            'enhanced_agent': enhanced_agent
        }
    
    @pytest.mark.asyncio
    async def test_phase1_end_to_end(self, phase1_setup):
        """Test Phase 1 integration end-to-end"""
        enhanced_agent = phase1_setup['enhanced_agent']
        
        # Test market data
        market_data = {
            'symbol': 'ETH-USD',
            'data': 'mock_ethereum_data',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Run organic CIL-influenced analysis
        result = await enhanced_agent.analyze_with_organic_influence(market_data)
        
        # Verify all Phase 1 components are working
        assert result['agent'] == 'integration_test_agent'
        assert 'resonance' in result
        assert 'uncertainty_analysis' in result
        assert 'enhanced_score' in result
        
        # Verify uncertainty is embraced positively
        uncertainty_analysis = result['uncertainty_analysis']
        if uncertainty_analysis['uncertainty_detected']:
            assert len(uncertainty_analysis['exploration_opportunities']) > 0
            assert uncertainty_analysis['uncertainty_priority'] in ['low', 'medium', 'high']
        
        # Verify resonance enhancement
        resonance = result['resonance']
        assert resonance['enhanced_score'] >= result.get('confidence', 0.0)
        
        # Verify learning tracking
        learning_summary = enhanced_agent.get_learning_summary()
        assert learning_summary['cil_integration_enabled'] == True
        assert learning_summary['uncertainty_embrace_enabled'] == True
        assert learning_summary['resonance_enhancement_enabled'] == True


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
