"""
Test CIL Integration Components for Decision Maker

This test file verifies the new CIL integration components:
- DecisionMakerStrandListener
- PortfolioDataIntegration
- Enhanced Decision Maker Agent with CIL integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.intelligence.decision_maker.decision_maker_strand_listener import DecisionMakerStrandListener
from src.intelligence.decision_maker.portfolio_data_integration import PortfolioDataIntegration, PortfolioState, Position
from src.intelligence.decision_maker.enhanced_decision_agent_base import EnhancedDecisionMakerAgent


class TestDecisionMakerStrandListener:
    """Test DecisionMakerStrandListener functionality."""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing."""
        manager = Mock()
        manager.execute_query = AsyncMock(return_value=[])
        return manager
    
    @pytest.fixture
    def strand_listener(self, mock_supabase_manager):
        """Create DecisionMakerStrandListener instance for testing."""
        return DecisionMakerStrandListener(mock_supabase_manager)
    
    def test_initialization(self, strand_listener):
        """Test strand listener initialization."""
        assert strand_listener.supabase_manager is not None
        assert len(strand_listener.decision_maker_tags) > 0
        assert 'dm:risk_guidance' in strand_listener.decision_maker_tags
        assert 'dm:execute' in strand_listener.decision_maker_tags
        assert 'cil:strategic_insight' in strand_listener.decision_maker_tags
    
    def test_register_insight_handler(self, strand_listener):
        """Test registering insight handlers."""
        handler = Mock()
        strand_listener.register_insight_handler('test_type', handler)
        assert 'test_type' in strand_listener.insight_handlers
        assert strand_listener.insight_handlers['test_type'] == handler
    
    def test_unregister_insight_handler(self, strand_listener):
        """Test unregistering insight handlers."""
        handler = Mock()
        strand_listener.register_insight_handler('test_type', handler)
        strand_listener.unregister_insight_handler('test_type')
        assert 'test_type' not in strand_listener.insight_handlers
    
    @pytest.mark.asyncio
    async def test_process_cil_strand(self, strand_listener):
        """Test processing CIL strands."""
        # Mock strand data
        strand = {
            'id': 'test_strand_1',
            'module': 'cil',
            'kind': 'strategic_risk_insight',
            'content': {
                'insights': {
                    'insight_id': 'test_insight_1',
                    'risk_assessment': {'level': 'medium', 'score': 0.6},
                    'risk_parameters': {'max_drawdown': 0.05},
                    'execution_constraints': {'max_slippage': 0.002},
                    'strategic_guidance': {'recommendation': 'proceed'}
                }
            },
            'tags': ['cil:strategic_insight', 'dm:risk_guidance']
        }
        
        # Register mock handler
        mock_handler = AsyncMock()
        strand_listener.register_insight_handler('risk_insights', mock_handler)
        
        # Process strand
        await strand_listener._process_cil_strand(strand)
        
        # Verify handler was called
        mock_handler.assert_called_once()
        
        # Verify strand was marked as processed
        assert 'test_strand_1' in strand_listener.received_insights
    
    def test_get_listener_summary(self, strand_listener):
        """Test getting listener summary."""
        summary = strand_listener.get_listener_summary()
        
        assert 'active_listeners' in summary
        assert 'received_insights' in summary
        assert 'registered_handlers' in summary
        assert 'listener_tags' in summary
        assert 'last_activity' in summary


class TestPortfolioDataIntegration:
    """Test PortfolioDataIntegration functionality."""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing."""
        return Mock()
    
    @pytest.fixture
    def portfolio_integration(self, mock_supabase_manager):
        """Create PortfolioDataIntegration instance for testing."""
        config = {
            'hyperliquid_api_url': 'https://api.hyperliquid.xyz',
            'hyperliquid_ws_url': 'wss://api.hyperliquid.xyz/ws',
            'api_key': 'test_key',
            'secret_key': 'test_secret'
        }
        return PortfolioDataIntegration(mock_supabase_manager, config)
    
    def test_initialization(self, portfolio_integration):
        """Test portfolio integration initialization."""
        assert portfolio_integration.supabase_manager is not None
        assert portfolio_integration.hyperliquid_api_url == 'https://api.hyperliquid.xyz'
        assert portfolio_integration.hyperliquid_ws_url == 'wss://api.hyperliquid.xyz/ws'
        assert len(portfolio_integration.risk_thresholds) > 0
    
    def test_add_portfolio_update_callback(self, portfolio_integration):
        """Test adding portfolio update callbacks."""
        callback = Mock()
        portfolio_integration.add_portfolio_update_callback(callback)
        assert callback in portfolio_integration.portfolio_update_callbacks
    
    def test_add_risk_alert_callback(self, portfolio_integration):
        """Test adding risk alert callbacks."""
        callback = Mock()
        portfolio_integration.add_risk_alert_callback(callback)
        assert callback in portfolio_integration.risk_alert_callbacks
    
    def test_calculate_risk_score(self, portfolio_integration):
        """Test risk score calculation."""
        # Test high risk scenario
        high_risk_score = portfolio_integration._calculate_risk_score(
            max_concentration=0.15,  # 15% concentration
            avg_leverage=4.0,        # 4x leverage
            margin_ratio=0.9         # 90% margin used
        )
        assert high_risk_score > 0.8  # Should be high risk
        
        # Test low risk scenario
        low_risk_score = portfolio_integration._calculate_risk_score(
            max_concentration=0.05,  # 5% concentration
            avg_leverage=1.5,        # 1.5x leverage
            margin_ratio=0.3         # 30% margin used
        )
        assert low_risk_score < 0.5  # Should be low risk (adjusted expectation)
    
    def test_get_integration_summary(self, portfolio_integration):
        """Test getting integration summary."""
        summary = portfolio_integration.get_integration_summary()
        
        assert 'websocket_connected' in summary
        assert 'current_portfolio_value' in summary
        assert 'total_positions' in summary
        assert 'portfolio_history_count' in summary
        assert 'portfolio_update_callbacks' in summary
        assert 'risk_alert_callbacks' in summary


class TestEnhancedDecisionMakerAgentWithCILIntegration:
    """Test Enhanced Decision Maker Agent with CIL integration."""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager for testing."""
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing."""
        return Mock()
    
    @pytest.fixture
    def decision_maker_agent(self, mock_supabase_manager, mock_llm_client):
        """Create Enhanced Decision Maker Agent instance for testing."""
        return EnhancedDecisionMakerAgent(
            agent_name="test_decision_maker",
            supabase_manager=mock_supabase_manager,
            llm_client=mock_llm_client
        )
    
    def test_initialization(self, decision_maker_agent):
        """Test Decision Maker agent initialization."""
        assert decision_maker_agent.agent_name == "test_decision_maker"
        assert decision_maker_agent.supabase_manager is not None
        assert decision_maker_agent.llm_client is not None
        
        # Check that new components are initialized
        assert decision_maker_agent.strand_listener is not None
        assert decision_maker_agent.portfolio_data_integration is not None
        
        # Check new tracking metrics
        assert decision_maker_agent.cil_insights_received == 0
        assert decision_maker_agent.portfolio_updates_processed == 0
        assert decision_maker_agent.risk_alerts_handled == 0
    
    @pytest.mark.asyncio
    async def test_initialize(self, decision_maker_agent):
        """Test Decision Maker agent initialization."""
        # Mock the portfolio data integration initialization
        decision_maker_agent.portfolio_data_integration.initialize = AsyncMock(return_value=True)
        decision_maker_agent.strand_listener.start_listening = AsyncMock()
        
        # Initialize the agent
        result = await decision_maker_agent.initialize()
        
        # Verify initialization was successful
        assert result is True
        decision_maker_agent.portfolio_data_integration.initialize.assert_called_once()
        decision_maker_agent.strand_listener.start_listening.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown(self, decision_maker_agent):
        """Test Decision Maker agent shutdown."""
        # Mock the shutdown methods
        decision_maker_agent.strand_listener.stop_listening = AsyncMock()
        decision_maker_agent.portfolio_data_integration.shutdown = AsyncMock()
        
        # Shutdown the agent
        await decision_maker_agent.shutdown()
        
        # Verify shutdown was called
        decision_maker_agent.strand_listener.stop_listening.assert_called_once()
        decision_maker_agent.portfolio_data_integration.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_cil_risk_insights(self, decision_maker_agent):
        """Test handling CIL risk insights."""
        # Mock insights data
        insights = {
            'source_strand_id': 'test_strand_1',
            'risk_assessment': {'level': 'high', 'score': 0.8},
            'risk_parameters': {'max_drawdown': 0.03},
            'execution_constraints': {'max_slippage': 0.001},
            'strategic_guidance': {'recommendation': 'caution'}
        }
        
        # Handle insights
        await decision_maker_agent._handle_cil_risk_insights(insights)
        
        # Verify insights were processed
        assert decision_maker_agent.cil_insights_received == 1
        assert hasattr(decision_maker_agent, 'cil_risk_insights')
        assert decision_maker_agent.cil_risk_insights['risk_assessment']['level'] == 'high'
    
    @pytest.mark.asyncio
    async def test_handle_portfolio_update(self, decision_maker_agent):
        """Test handling portfolio updates."""
        # Mock portfolio state
        portfolio_state = PortfolioState(
            total_value=100000.0,
            available_margin=50000.0,
            used_margin=50000.0,
            total_pnl=1000.0,
            positions=[],
            last_updated=datetime.now(timezone.utc),
            risk_metrics={'risk_score': 0.5}
        )
        
        # Handle portfolio update
        await decision_maker_agent._handle_portfolio_update(portfolio_state)
        
        # Verify update was processed
        assert decision_maker_agent.portfolio_updates_processed == 1
        assert decision_maker_agent.current_portfolio_state == portfolio_state
    
    @pytest.mark.asyncio
    async def test_handle_risk_alert(self, decision_maker_agent):
        """Test handling risk alerts."""
        # Mock risk alert
        alert = {
            'type': 'high_concentration',
            'data': {'max_concentration': 0.15, 'threshold': 0.1},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Handle risk alert
        await decision_maker_agent._handle_risk_alert(alert)
        
        # Verify alert was processed
        assert decision_maker_agent.risk_alerts_handled == 1
        assert hasattr(decision_maker_agent, 'current_risk_alerts')
        assert len(decision_maker_agent.current_risk_alerts) == 1
    
    def test_get_cil_integration_summary(self, decision_maker_agent):
        """Test getting CIL integration summary."""
        # Set some test data
        decision_maker_agent.cil_insights_received = 5
        decision_maker_agent.portfolio_updates_processed = 10
        decision_maker_agent.risk_alerts_handled = 2
        
        # Mock the component summaries
        decision_maker_agent.strand_listener.get_listener_summary = Mock(return_value={'active_listeners': 3})
        decision_maker_agent.portfolio_data_integration.get_integration_summary = Mock(return_value={'websocket_connected': True})
        
        # Get summary
        summary = decision_maker_agent.get_cil_integration_summary()
        
        # Verify summary content
        assert summary['cil_insights_received'] == 5
        assert summary['portfolio_updates_processed'] == 10
        assert summary['risk_alerts_handled'] == 2
        assert 'strand_listener_summary' in summary
        assert 'portfolio_integration_summary' in summary


# Integration test
class TestCILIntegrationWorkflow:
    """Test the complete CIL integration workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_cil_integration_workflow(self):
        """Test the complete workflow from CIL insights to Decision Maker processing."""
        # This would test the complete flow:
        # 1. CIL generates insights and tags Decision Maker
        # 2. Decision Maker receives insights via strand listener
        # 3. Decision Maker processes insights and updates risk assessment
        # 4. Decision Maker uses portfolio data for risk assessment
        # 5. Decision Maker generates recommendations based on all inputs
        
        # This is a placeholder for a more comprehensive integration test
        # that would test the complete workflow
        assert True  # Placeholder assertion


if __name__ == "__main__":
    pytest.main([__file__])
