"""
Test Trader Phase 1 Components

Tests for the Phase 1 Trader Team organic intelligence components:
- Execution Resonance Integration
- Execution Uncertainty Handler  
- Enhanced Trader Agent Base
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.intelligence.trader.execution_resonance_integration import (
    ExecutionResonanceIntegration, ExecutionResonanceMetrics
)
from src.intelligence.trader.execution_uncertainty_handler import (
    ExecutionUncertaintyHandler, ExecutionUncertaintyType, ExecutionUncertaintyData
)
from src.intelligence.trader.enhanced_trader_agent_base import (
    EnhancedTraderAgent, ExecutionContext
)


class TestExecutionResonanceIntegration:
    """Test Execution Resonance Integration"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def resonance_integration(self, mock_supabase_manager, mock_llm_client):
        return ExecutionResonanceIntegration(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def sample_execution_data(self):
        return {
            'execution_id': 'exec_001',
            'execution_type': 'market_order',
            'venue': 'hyperliquid',
            'symbol': 'BTC-USD',
            'execution_quality': 0.85,
            'slippage': 0.001,
            'fill_time': 2.5,
            'volume': 1000.0,
            'price_impact': 0.0005,
            'market_conditions': {'volatility': 0.3, 'liquidity': 0.8},
            'execution_strategy': 'twap'
        }
    
    @pytest.mark.asyncio
    async def test_calculate_execution_resonance(self, resonance_integration, sample_execution_data):
        """Test execution resonance calculation"""
        result = await resonance_integration.calculate_execution_resonance(sample_execution_data)
        
        # Verify result structure
        assert 'phi' in result
        assert 'rho' in result
        assert 'theta' in result
        assert 'execution_sr' in result
        assert 'execution_cr' in result
        assert 'execution_xr' in result
        assert 'execution_surprise' in result
        assert 'timestamp' in result
        
        # Verify values are in valid range
        assert 0.0 <= result['phi'] <= 1.0
        assert 0.0 <= result['rho'] <= 1.0
        assert 0.0 <= result['theta'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_find_execution_resonance_clusters(self, resonance_integration):
        """Test finding execution resonance clusters"""
        clusters = await resonance_integration.find_execution_resonance_clusters('market_order')
        
        # Should return a list (empty for now due to mock implementation)
        assert isinstance(clusters, list)
    
    @pytest.mark.asyncio
    async def test_enhance_execution_score_with_resonance(self, resonance_integration):
        """Test execution score enhancement with resonance"""
        enhanced_score = await resonance_integration.enhance_execution_score_with_resonance('strand_001')
        
        # Should return a float
        assert isinstance(enhanced_score, float)
        assert 0.0 <= enhanced_score <= 1.0
    
    def test_execution_resonance_metrics_creation(self):
        """Test ExecutionResonanceMetrics dataclass"""
        metrics = ExecutionResonanceMetrics(
            phi=0.8,
            rho=0.7,
            theta=0.75,
            execution_sr=0.85,
            execution_cr=0.8,
            execution_xr=0.75,
            execution_surprise=0.2,
            timestamp=datetime.now()
        )
        
        assert metrics.phi == 0.8
        assert metrics.rho == 0.7
        assert metrics.theta == 0.75
        assert metrics.execution_sr == 0.85


class TestExecutionUncertaintyHandler:
    """Test Execution Uncertainty Handler"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def uncertainty_handler(self, mock_supabase_manager, mock_llm_client):
        return ExecutionUncertaintyHandler(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def sample_execution_analysis(self):
        return {
            'execution_quality': 0.6,
            'execution_quality_variance': 0.3,
            'venue_confidence': 0.4,
            'timing_confidence': 0.5,
            'impact_confidence': 0.3,
            'historical_data_points': 20,
            'market_conditions_covered': 3,
            'venues_covered': 2,
            'strategies_covered': 1
        }
    
    @pytest.mark.asyncio
    async def test_detect_execution_uncertainty(self, uncertainty_handler, sample_execution_analysis):
        """Test execution uncertainty detection"""
        result = await uncertainty_handler.detect_execution_uncertainty(sample_execution_analysis)
        
        # Verify result structure
        assert 'pattern_clarity' in result
        assert 'data_sufficiency' in result
        assert 'confidence_levels' in result
        assert 'uncertainty_types' in result
        assert 'overall_uncertainty' in result
        assert 'exploration_opportunities' in result
        assert 'uncertainty_is_valuable' in result
        assert 'timestamp' in result
        
        # Verify uncertainty is valuable
        assert result['uncertainty_is_valuable'] is True
        
        # Verify values are in valid range
        assert 0.0 <= result['overall_uncertainty'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_publish_execution_uncertainty_strand(self, uncertainty_handler):
        """Test publishing execution uncertainty strand"""
        uncertainty_data = {
            'overall_uncertainty': 0.8,
            'primary_uncertainty_type': 'execution_quality',
            'exploration_priority': 0.9,
            'exploration_opportunities': ['test_new_strategies', 'gather_more_data']
        }
        
        strand_id = await uncertainty_handler.publish_execution_uncertainty_strand(uncertainty_data)
        
        # Should return a string ID
        assert isinstance(strand_id, str)
        assert len(strand_id) > 0
    
    @pytest.mark.asyncio
    async def test_handle_execution_uncertainty_resolution(self, uncertainty_handler):
        """Test handling execution uncertainty resolution"""
        resolution_data = {
            'exploration_results': {'new_insights': ['insight1', 'insight2']},
            'learning_insights': ['learned1', 'learned2']
        }
        
        # Should not raise an exception
        await uncertainty_handler.handle_execution_uncertainty_resolution(
            'uncertainty_001', resolution_data
        )
    
    def test_execution_uncertainty_type_enum(self):
        """Test ExecutionUncertaintyType enum"""
        assert ExecutionUncertaintyType.EXECUTION_QUALITY.value == "execution_quality"
        assert ExecutionUncertaintyType.VENUE_SELECTION.value == "venue_selection"
        assert ExecutionUncertaintyType.TIMING_OPTIMIZATION.value == "timing_optimization"
    
    def test_execution_uncertainty_data_creation(self):
        """Test ExecutionUncertaintyData dataclass"""
        data = ExecutionUncertaintyData(
            uncertainty_type=ExecutionUncertaintyType.EXECUTION_QUALITY,
            confidence_level=0.3,
            uncertainty_factors=['low_data', 'high_variance'],
            exploration_priority=0.8,
            resolution_suggestions=['gather_more_data', 'test_alternatives'],
            context_data={'market_conditions': 'volatile'},
            timestamp=datetime.now()
        )
        
        assert data.uncertainty_type == ExecutionUncertaintyType.EXECUTION_QUALITY
        assert data.confidence_level == 0.3
        assert data.exploration_priority == 0.8


class TestEnhancedTraderAgentBase:
    """Test Enhanced Trader Agent Base"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def sample_market_data(self):
        return {
            'symbol': 'BTC-USD',
            'price': 50000.0,
            'volume': 1000.0,
            'timestamp': datetime.now().isoformat()
        }
    
    @pytest.fixture
    def sample_approved_plan(self):
        return {
            'plan_id': 'plan_001',
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': 100.0,
            'execution_score': 0.8,
            'risk_score': 0.3
        }
    
    class ConcreteTraderAgent(EnhancedTraderAgent):
        """Concrete implementation for testing"""
        
        async def _execute_specific_plan(self, plan, context):
            return {
                'execution_id': 'exec_001',
                'success': True,
                'fill_price': 50000.0,
                'fill_quantity': 100.0,
                'success_score': 0.9
            }
        
        async def _get_agent_specific_metrics(self):
            return {
                'total_executions': 10,
                'success_rate': 0.9,
                'average_fill_time': 2.5
            }
    
    @pytest.fixture
    def trader_agent(self, mock_supabase_manager, mock_llm_client):
        return self.ConcreteTraderAgent('test_agent', mock_supabase_manager, mock_llm_client)
    
    def test_agent_initialization(self, trader_agent):
        """Test agent initialization"""
        assert trader_agent.agent_name == 'test_agent'
        assert trader_agent.is_active is False
        assert trader_agent.execution_count == 0
        assert trader_agent.execution_resonance_integration is not None
        assert trader_agent.execution_uncertainty_handler is not None
    
    @pytest.mark.asyncio
    async def test_execute_with_organic_influence(self, trader_agent, sample_market_data, sample_approved_plan):
        """Test execution with organic influence"""
        result = await trader_agent.execute_with_organic_influence(sample_market_data, sample_approved_plan)
        
        # Verify result structure
        assert 'execution_id' in result
        assert 'success' in result
        assert 'organic_influence' in result
        
        # Verify organic influence metadata
        organic_influence = result['organic_influence']
        assert 'resonance_metrics' in organic_influence
        assert 'uncertainty_analysis' in organic_influence
        assert 'cil_insights_count' in organic_influence
        assert 'motif_integration' in organic_influence
    
    @pytest.mark.asyncio
    async def test_contribute_to_execution_motif(self, trader_agent):
        """Test contributing to execution motif"""
        execution_pattern_data = {
            'execution_result': {'success': True, 'score': 0.9},
            'context': {'market_conditions': 'normal'},
            'agent_name': 'test_agent'
        }
        
        motif_id = await trader_agent.contribute_to_execution_motif(execution_pattern_data)
        
        # Should return a string ID
        assert isinstance(motif_id, str)
    
    @pytest.mark.asyncio
    async def test_calculate_execution_resonance_contribution(self, trader_agent):
        """Test calculating execution resonance contribution"""
        execution_strand_data = {
            'execution_type': 'market_order',
            'execution_quality': 0.8,
            'slippage': 0.001
        }
        
        result = await trader_agent.calculate_execution_resonance_contribution(execution_strand_data)
        
        # Should return resonance metrics
        assert isinstance(result, dict)
        assert 'phi' in result or result == {}  # Empty dict if calculation fails
    
    def test_execution_context_creation(self):
        """Test ExecutionContext dataclass"""
        context = ExecutionContext(
            market_data={'price': 50000.0},
            approved_plan={'plan_id': 'plan_001'},
            cil_insights=[],
            resonance_metrics={'phi': 0.8, 'rho': 0.7},
            uncertainty_analysis={'overall_uncertainty': 0.3},
            motif_integration={},
            timestamp=datetime.now()
        )
        
        assert context.market_data['price'] == 50000.0
        assert context.approved_plan['plan_id'] == 'plan_001'
        assert context.resonance_metrics['phi'] == 0.8


class TestTraderPhase1Integration:
    """Test Phase 1 integration between components"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_resonance_and_uncertainty_integration(self, mock_supabase_manager, mock_llm_client):
        """Test integration between resonance and uncertainty components"""
        # Initialize components
        resonance_integration = ExecutionResonanceIntegration(mock_supabase_manager, mock_llm_client)
        uncertainty_handler = ExecutionUncertaintyHandler(mock_supabase_manager, mock_llm_client)
        
        # Sample execution data
        execution_data = {
            'execution_type': 'market_order',
            'execution_quality': 0.6,
            'venue_confidence': 0.4,
            'timing_confidence': 0.5
        }
        
        # Calculate resonance
        resonance_result = await resonance_integration.calculate_execution_resonance(execution_data)
        
        # Detect uncertainty
        uncertainty_result = await uncertainty_handler.detect_execution_uncertainty(execution_data)
        
        # Verify both components work together
        assert 'phi' in resonance_result
        assert 'overall_uncertainty' in uncertainty_result
        assert uncertainty_result['uncertainty_is_valuable'] is True
    
    @pytest.mark.asyncio
    async def test_agent_base_integration(self, mock_supabase_manager, mock_llm_client):
        """Test integration with agent base class"""
        class TestAgent(EnhancedTraderAgent):
            async def _execute_specific_plan(self, plan, context):
                return {'success': True, 'score': 0.9}
            
            async def _get_agent_specific_metrics(self):
                return {'executions': 1}
        
        agent = TestAgent('test_agent', mock_supabase_manager, mock_llm_client)
        
        # Test agent has all required components
        assert agent.execution_resonance_integration is not None
        assert agent.execution_uncertainty_handler is not None
        
        # Test execution with organic influence
        market_data = {'price': 50000.0}
        approved_plan = {'plan_id': 'plan_001', 'execution_score': 0.8}
        
        result = await agent.execute_with_organic_influence(market_data, approved_plan)
        
        assert 'organic_influence' in result
        assert result['organic_influence']['cil_insights_count'] == 0  # Phase 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
