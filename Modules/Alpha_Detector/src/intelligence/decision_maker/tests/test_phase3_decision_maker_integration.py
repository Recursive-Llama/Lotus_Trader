"""
Test Suite for Decision Maker Phase 3 CIL Integration

Tests the implementation of Phase 3 components:
- RiskDoctrineIntegration
- EnhancedRiskAssessmentAgent
- EnhancedDecisionMakerAgent (Phase 3 specific methods)

Validates organic risk doctrine integration and enhanced capabilities.
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

from src.intelligence.decision_maker.risk_doctrine_integration import RiskDoctrineIntegration
from src.intelligence.decision_maker.enhanced_risk_assessment_agent import EnhancedRiskAssessmentAgent
from src.intelligence.decision_maker.enhanced_decision_agent_base import EnhancedDecisionMakerAgent

class TestRiskDoctrineIntegration:
    """Test RiskDoctrineIntegration component"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def risk_doctrine_integration(self, mock_supabase_manager):
        """Create RiskDoctrineIntegration instance for testing"""
        return RiskDoctrineIntegration(mock_supabase_manager)

    @pytest.mark.asyncio
    async def test_query_relevant_risk_doctrine(self, risk_doctrine_integration):
        """Test querying relevant risk doctrine"""
        risk_type = "portfolio_risk"
        
        doctrine_guidance = await risk_doctrine_integration.query_relevant_risk_doctrine(risk_type)
        
        # Verify doctrine guidance structure
        assert 'recommendations' in doctrine_guidance
        assert isinstance(doctrine_guidance['recommendations'], list)
        assert len(doctrine_guidance['recommendations']) > 0
        
        for rec in doctrine_guidance['recommendations']:
            assert 'doctrine_id' in rec
            assert 'type' in rec
            assert 'risk_type' in rec
            assert 'confidence' in rec

    @pytest.mark.asyncio
    async def test_contribute_to_risk_doctrine(self, risk_doctrine_integration):
        """Test contributing to risk doctrine"""
        risk_pattern_evidence = {
            'agent': 'test_agent',
            'risk_type': 'portfolio_risk',
            'confidence': 0.8,
            'evidence': 'test_evidence'
        }
        
        contribution_id = await risk_doctrine_integration.contribute_to_risk_doctrine(risk_pattern_evidence)
        
        # Verify contribution ID is generated
        assert isinstance(contribution_id, str)
        assert len(contribution_id) > 0

    @pytest.mark.asyncio
    async def test_check_risk_doctrine_contraindications(self, risk_doctrine_integration):
        """Test checking risk doctrine contraindications"""
        # Test non-contraindicated experiment
        safe_experiment = {
            'experiment_id': 'safe_exp_1',
            'strategy_type': 'low_risk_strategy'
        }
        
        is_contraindicated = await risk_doctrine_integration.check_risk_doctrine_contraindications(safe_experiment)
        assert is_contraindicated == False
        
        # Test contraindicated experiment
        risky_experiment = {
            'experiment_id': 'risky_exp_1',
            'strategy_type': 'high_risk_strategy'
        }
        
        is_contraindicated = await risk_doctrine_integration.check_risk_doctrine_contraindications(risky_experiment)
        assert is_contraindicated == True

    @pytest.mark.asyncio
    async def test_evolve_risk_doctrine(self, risk_doctrine_integration):
        """Test evolving risk doctrine"""
        evolution_evidence = {
            'evidence_type': 'new_risk_pattern',
            'evolution_type': 'natural_learning',
            'confidence': 0.9
        }
        
        evolution_id = await risk_doctrine_integration.evolve_risk_doctrine(evolution_evidence)
        
        # Verify evolution ID is generated
        assert isinstance(evolution_id, str)
        assert len(evolution_id) > 0

    @pytest.mark.asyncio
    async def test_apply_risk_doctrine_guidance(self, risk_doctrine_integration):
        """Test applying risk doctrine guidance"""
        risk_analysis = {
            'risk_type': 'portfolio_risk',
            'confidence': 0.6
        }
        
        doctrine_guidance = {
            'recommendations': [
                {'confidence': 0.9, 'type': 'positive_guidance'},
                {'confidence': 0.7, 'type': 'neutral_guidance'}
            ]
        }
        
        enhanced_analysis = await risk_doctrine_integration.apply_risk_doctrine_guidance(risk_analysis, doctrine_guidance)
        
        # Verify enhanced analysis structure
        assert 'doctrine_guidance_applied' in enhanced_analysis
        assert 'doctrine_confidence_boost' in enhanced_analysis
        assert enhanced_analysis['doctrine_confidence_boost'] > 0

    @pytest.mark.asyncio
    async def test_identify_risk_doctrine_gaps(self, risk_doctrine_integration):
        """Test identifying risk doctrine gaps"""
        risk_pattern_data = {
            'risk_type': 'new_risk_type',
            'confidence': 0.5
        }
        
        gaps = await risk_doctrine_integration.identify_risk_doctrine_gaps(risk_pattern_data)
        
        # Verify gaps structure
        assert isinstance(gaps, list)
        assert len(gaps) > 0
        
        for gap in gaps:
            assert 'gap_id' in gap
            assert 'risk_type' in gap
            assert 'gap_description' in gap
            assert 'priority' in gap
            assert 'suggested_actions' in gap

    @pytest.mark.asyncio
    async def test_validate_risk_doctrine_consistency(self, risk_doctrine_integration):
        """Test validating risk doctrine consistency"""
        new_doctrine_entry = {
            'risk_type': 'portfolio_risk',
            'type': 'positive_guidance',
            'confidence': 0.8
        }
        
        validation_result = await risk_doctrine_integration.validate_risk_doctrine_consistency(new_doctrine_entry)
        
        # Verify validation result structure
        assert 'is_consistent' in validation_result
        assert 'conflicts' in validation_result
        assert 'suggestions' in validation_result
        assert 'confidence_score' in validation_result

    def test_get_risk_doctrine_integration_summary(self, risk_doctrine_integration):
        """Test getting risk doctrine integration summary"""
        summary = risk_doctrine_integration.get_risk_doctrine_integration_summary()
        
        # Verify summary structure
        assert 'risk_doctrine_integration_status' in summary
        assert 'total_risk_doctrine_entries' in summary
        assert 'last_risk_doctrine_update' in summary
        assert 'doctrine_types' in summary
        assert 'risk_types_covered' in summary

class TestEnhancedRiskAssessmentAgent:
    """Test EnhancedRiskAssessmentAgent component"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        return Mock()

    @pytest.fixture
    def enhanced_risk_agent(self, mock_supabase_manager, mock_llm_client):
        """Create EnhancedRiskAssessmentAgent instance for testing"""
        return EnhancedRiskAssessmentAgent("test_risk_agent", mock_supabase_manager, mock_llm_client)

    @pytest.mark.asyncio
    async def test_enhanced_risk_analysis(self, enhanced_risk_agent):
        """Test enhanced risk analysis with all phases integrated"""
        market_data = {'symbol': 'BTC', 'price': 50000}
        raw_data_analysis = {'patterns': ['volume_spike'], 'confidence': 0.6}
        
        result = await enhanced_risk_agent.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify enhanced analysis structure
        assert 'agent' in result
        assert 'risk_confidence' in result
        assert 'risk_type' in result
        assert 'risk_details' in result
        assert 'analysis_components' in result
        assert result['agent'] == 'test_risk_agent'

    @pytest.mark.asyncio
    async def test_core_risk_analysis(self, enhanced_risk_agent):
        """Test core risk analysis functionality"""
        market_data = {'symbol': 'ETH', 'price': 3000}
        raw_data_analysis = {'patterns': ['divergence'], 'confidence': 0.7}
        
        result = await enhanced_risk_agent._perform_core_risk_analysis(market_data, raw_data_analysis)
        
        # Verify core analysis structure
        assert 'agent' in result
        assert 'risk_confidence' in result
        assert 'risk_type' in result
        assert 'risk_details' in result
        assert 'analysis_components' in result

    def test_calculate_portfolio_risk_metrics(self, enhanced_risk_agent):
        """Test portfolio risk metrics calculation"""
        market_data = {'symbol': 'BTC', 'price': 50000}
        raw_data_analysis = {'patterns': ['volume_spike']}
        
        metrics = enhanced_risk_agent._calculate_portfolio_risk_metrics(market_data, raw_data_analysis)
        
        # Verify metrics structure
        assert 'var_1d' in metrics
        assert 'var_7d' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'portfolio_value' in metrics
        assert 'risk_score' in metrics

    def test_analyze_concentration_risk(self, enhanced_risk_agent):
        """Test concentration risk analysis"""
        market_data = {'symbol': 'BTC', 'price': 50000}
        
        analysis = enhanced_risk_agent._analyze_concentration_risk(market_data)
        
        # Verify analysis structure
        assert 'concentration_score' in analysis
        assert 'risks' in analysis
        assert 'recommendations' in analysis

    def test_evaluate_liquidity_risk(self, enhanced_risk_agent):
        """Test liquidity risk evaluation"""
        market_data = {'symbol': 'ETH', 'price': 3000}
        
        evaluation = enhanced_risk_agent._evaluate_liquidity_risk(market_data)
        
        # Verify evaluation structure
        assert 'liquidity_score' in evaluation
        assert 'risks' in evaluation
        assert 'recommendations' in evaluation

    def test_assess_compliance_risk(self, enhanced_risk_agent):
        """Test compliance risk assessment"""
        market_data = {'symbol': 'BTC', 'price': 50000}
        
        assessment = enhanced_risk_agent._assess_compliance_risk(market_data)
        
        # Verify assessment structure
        assert 'compliance_score' in assessment
        assert 'risks' in assessment
        assert 'recommendations' in assessment

    def test_calculate_overall_risk_confidence(self, enhanced_risk_agent):
        """Test overall risk confidence calculation"""
        portfolio_metrics = {'risk_score': 0.6}
        concentration_analysis = {'concentration_score': 0.7}
        liquidity_evaluation = {'liquidity_score': 0.8}
        compliance_assessment = {'compliance_score': 0.9}
        
        confidence = enhanced_risk_agent._calculate_overall_risk_confidence(
            portfolio_metrics, concentration_analysis, liquidity_evaluation, compliance_assessment
        )
        
        # Verify confidence is within valid range
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_apply_risk_doctrine_guidance(self, enhanced_risk_agent):
        """Test applying risk doctrine guidance"""
        risk_analysis = {
            'risk_type': 'portfolio_risk',
            'confidence': 0.6
        }
        
        enhanced_analysis = await enhanced_risk_agent.apply_risk_doctrine_guidance(risk_analysis)
        
        # Verify enhanced analysis structure
        assert 'doctrine_guidance_applied' in enhanced_analysis
        assert 'doctrine_confidence_boost' in enhanced_analysis

    @pytest.mark.asyncio
    async def test_generate_risk_recommendations(self, enhanced_risk_agent):
        """Test generating risk recommendations"""
        risk_analysis = {
            'risk_details': {
                'portfolio_risk_metrics': {'risk_score': 0.8},
                'concentration_risk_analysis': {'concentration_score': 0.9},
                'liquidity_risk_evaluation': {'liquidity_score': 0.3},
                'compliance_risk_assessment': {'compliance_score': 0.8}
            }
        }
        
        recommendations = await enhanced_risk_agent.generate_risk_recommendations(risk_analysis)
        
        # Verify recommendations structure
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        for rec in recommendations:
            assert 'type' in rec
            assert 'priority' in rec
            assert 'description' in rec
            assert 'suggested_actions' in rec

    @pytest.mark.asyncio
    async def test_participate_in_risk_experiments(self, enhanced_risk_agent):
        """Test participating in risk experiments"""
        # Test safe experiment
        safe_experiment = {
            'experiment_id': 'safe_exp_1',
            'strategy_type': 'low_risk_strategy'
        }
        
        result = await enhanced_risk_agent.participate_in_risk_experiments(safe_experiment)
        
        # Verify participation result
        assert 'participation_status' in result
        assert 'experiment_id' in result
        assert result['participation_status'] == 'accepted'
        
        # Test risky experiment
        risky_experiment = {
            'experiment_id': 'risky_exp_1',
            'strategy_type': 'high_risk_strategy'
        }
        
        result = await enhanced_risk_agent.participate_in_risk_experiments(risky_experiment)
        
        # Verify participation result
        assert result['participation_status'] == 'declined'
        assert 'reason' in result

    @pytest.mark.asyncio
    async def test_get_enhanced_risk_learning_summary(self, enhanced_risk_agent):
        """Test getting enhanced risk learning summary"""
        summary = await enhanced_risk_agent.get_enhanced_risk_learning_summary()
        
        # Verify enhanced summary structure
        assert 'agent' in summary
        assert 'portfolio_risks_assessed' in summary
        assert 'concentration_risks_identified' in summary
        assert 'liquidity_risks_evaluated' in summary
        assert 'compliance_risks_monitored' in summary
        assert 'risk_doctrine_applications' in summary
        assert 'agent_type' in summary
        assert 'phase_3_integration' in summary

class TestEnhancedDecisionMakerAgentPhase3:
    """Test EnhancedDecisionMakerAgent Phase 3 specific methods"""

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
    async def test_query_relevant_risk_doctrine(self, enhanced_agent):
        """Test querying relevant risk doctrine"""
        risk_type = "portfolio_risk"
        
        doctrine_guidance = await enhanced_agent.query_relevant_risk_doctrine(risk_type)
        
        # Verify doctrine guidance is returned
        assert isinstance(doctrine_guidance, dict)
        assert 'recommendations' in doctrine_guidance

    @pytest.mark.asyncio
    async def test_contribute_to_risk_doctrine(self, enhanced_agent):
        """Test contributing to risk doctrine"""
        risk_pattern_evidence = {
            'agent': 'test_agent',
            'risk_type': 'portfolio_risk',
            'confidence': 0.8
        }
        
        contribution_id = await enhanced_agent.contribute_to_risk_doctrine(risk_pattern_evidence)
        
        # Verify contribution ID is generated
        assert isinstance(contribution_id, str)
        assert len(contribution_id) > 0

    @pytest.mark.asyncio
    async def test_check_risk_doctrine_contraindications(self, enhanced_agent):
        """Test checking risk doctrine contraindications"""
        # Test safe experiment
        safe_experiment = {
            'experiment_id': 'safe_exp_1',
            'strategy_type': 'low_risk_strategy'
        }
        
        is_contraindicated = await enhanced_agent.check_risk_doctrine_contraindications(safe_experiment)
        assert is_contraindicated == False
        
        # Test risky experiment
        risky_experiment = {
            'experiment_id': 'risky_exp_1',
            'strategy_type': 'high_risk_strategy'
        }
        
        is_contraindicated = await enhanced_agent.check_risk_doctrine_contraindications(risky_experiment)
        assert is_contraindicated == True

    def test_enable_risk_doctrine_integration(self, enhanced_agent):
        """Test enabling/disabling risk doctrine integration"""
        # Test enabling
        enhanced_agent.enable_risk_doctrine_integration(True)
        assert enhanced_agent.risk_doctrine_integration_enabled == True
        
        # Test disabling
        enhanced_agent.enable_risk_doctrine_integration(False)
        assert enhanced_agent.risk_doctrine_integration_enabled == False

    def test_get_risk_doctrine_integration_summary(self, enhanced_agent):
        """Test getting risk doctrine integration summary"""
        summary = enhanced_agent.get_risk_doctrine_integration_summary()
        
        # Verify summary structure
        assert isinstance(summary, dict)
        assert 'risk_doctrine_integration_status' in summary

    @pytest.mark.asyncio
    async def test_analyze_risk_with_phase3_integration(self, enhanced_agent):
        """Test risk analysis with Phase 3 integration"""
        market_data = {'symbol': 'BTC', 'price': 50000}
        raw_data_analysis = {'patterns': ['volume_spike'], 'confidence': 0.6}
        
        result = await enhanced_agent.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify Phase 3 components are integrated
        assert 'risk_doctrine_guidance' in result
        assert 'agent' in result
        assert result['agent'] == 'test_agent'

    @pytest.mark.asyncio
    async def test_get_risk_learning_summary_phase3(self, enhanced_agent):
        """Test getting risk learning summary with Phase 3 metrics"""
        summary = await enhanced_agent.get_risk_learning_summary()
        
        # Verify Phase 3 metrics are included
        assert 'risk_doctrine_queries' in summary
        assert 'risk_doctrine_contributions' in summary
        assert 'risk_contraindication_checks' in summary
        assert 'risk_doctrine_integration_enabled' in summary

class TestPhase3IntegrationEndToEnd:
    """End-to-end integration tests for Phase 3"""

    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing"""
        return Mock()

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        return Mock()

    @pytest.mark.asyncio
    async def test_complete_phase3_workflow(self, mock_supabase_manager, mock_llm_client):
        """Test complete Phase 3 workflow"""
        # Create components
        risk_doctrine = RiskDoctrineIntegration(mock_supabase_manager)
        enhanced_risk_agent = EnhancedRiskAssessmentAgent("test_risk_agent", mock_supabase_manager, mock_llm_client)
        
        # Test data
        market_data = {'symbol': 'ETH', 'price': 3000}
        raw_data_analysis = {'patterns': ['divergence'], 'confidence': 0.6}
        
        # Run complete workflow
        result = await enhanced_risk_agent.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify workflow completed successfully with Phase 3 components
        assert 'agent' in result
        assert 'risk_doctrine_guidance' in result
        assert result['agent'] == 'test_risk_agent'

    @pytest.mark.asyncio
    async def test_organic_risk_doctrine_network(self, mock_supabase_manager, mock_llm_client):
        """Test organic risk doctrine network functionality"""
        # Create multiple agents
        agent1 = EnhancedRiskAssessmentAgent("risk_agent_1", mock_supabase_manager, mock_llm_client)
        agent2 = EnhancedRiskAssessmentAgent("risk_agent_2", mock_supabase_manager, mock_llm_client)
        
        # Test data
        market_data = {'symbol': 'BTC', 'price': 50000}
        raw_data_analysis = {'patterns': ['volume_spike'], 'confidence': 0.7}
        
        # Run analysis on both agents
        result1 = await agent1.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        result2 = await agent2.analyze_risk_with_organic_influence(market_data, raw_data_analysis)
        
        # Verify both agents completed successfully with Phase 3 integration
        assert result1['agent'] == 'risk_agent_1'
        assert result2['agent'] == 'risk_agent_2'
        assert 'risk_doctrine_guidance' in result1
        assert 'risk_doctrine_guidance' in result2

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
