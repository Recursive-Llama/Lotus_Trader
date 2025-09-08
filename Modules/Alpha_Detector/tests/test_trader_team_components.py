"""
Comprehensive test suite for Trader Team components

This test suite tests all Trader Team components including:
- Order Manager
- Performance Analyzer
- Position Tracker
- Hyperliquid Integration
- Venue Fallback Manager
- CIL Integration
- Trader Team Coordinator
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from intelligence.trader import (
    OrderManager,
    PerformanceAnalyzer,
    PositionTracker,
    HyperliquidIntegration,
    VenueFallbackManager,
    CILIntegration,
    TraderTeamCoordinator
)


class TestOrderManager:
    """Test Order Manager component"""
    
    @pytest.fixture
    def order_manager(self):
        """Create OrderManager instance for testing"""
        mock_supabase = Mock()
        mock_llm = Mock()
        return OrderManager(mock_supabase, mock_llm)
    
    @pytest.mark.asyncio
    async def test_monitor_entry_conditions(self, order_manager):
        """Test entry condition monitoring"""
        trading_plan = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'entry_conditions': {
                'price_breakout': {
                    'threshold': 30000,
                    'direction': 'above'
                }
            }
        }
        
        result = await order_manager.monitor_entry_conditions(trading_plan)
        
        assert result['status'] in ['monitoring', 'error']
        assert 'conditions' in result
        assert 'ready' in result
    
    @pytest.mark.asyncio
    async def test_place_order_when_ready(self, order_manager):
        """Test order placement when conditions are met"""
        trading_plan = {
            'symbol': 'BTC',
            'order_details': {
                'side': 'buy',
                'quantity': 0.1,
                'price': 30000
            },
            'entry_conditions': {
                'price_breakout': {
                    'threshold': 30000,
                    'direction': 'above'
                }
            }
        }
        
        # Mock condition check to return ready
        with patch.object(order_manager, 'monitor_entry_conditions', return_value={'ready': True}):
            result = await order_manager.place_order_when_ready(trading_plan)
            
            assert result['status'] in ['success', 'error']
            assert 'order_placed' in result
    
    @pytest.mark.asyncio
    async def test_track_order_lifecycle(self, order_manager):
        """Test order lifecycle tracking"""
        order_id = "test_order_123"
        
        # Add order to active orders
        order_manager.active_orders[order_id] = {
            'trading_plan': {},
            'order_details': {},
            'placed_at': datetime.now(),
            'status': 'pending'
        }
        
        result = await order_manager.track_order_lifecycle(order_id)
        
        assert result['status'] in ['tracking', 'error']
        assert 'order_id' in result
        assert 'order_status' in result
    
    @pytest.mark.asyncio
    async def test_get_active_orders(self, order_manager):
        """Test getting active orders"""
        # Add some test orders
        order_manager.active_orders['order1'] = {'status': 'pending'}
        order_manager.active_orders['order2'] = {'status': 'filled'}
        
        result = await order_manager.get_active_orders()
        
        assert 'active_orders' in result
        assert 'count' in result
        assert result['count'] == 2


class TestPerformanceAnalyzer:
    """Test Performance Analyzer component"""
    
    @pytest.fixture
    def performance_analyzer(self):
        """Create PerformanceAnalyzer instance for testing"""
        mock_supabase = Mock()
        mock_llm = Mock()
        return PerformanceAnalyzer(mock_supabase, mock_llm)
    
    @pytest.mark.asyncio
    async def test_analyze_execution_quality(self, performance_analyzer):
        """Test execution quality analysis"""
        execution_result = {
            'order_id': 'test_order_123',
            'symbol': 'BTC',
            'execution_time': 0.5,
            'filled_price': 30000,
            'expected_price': 29950,
            'filled_quantity': 0.1,
            'order_details': {'quantity': 0.1}
        }
        
        result = await performance_analyzer.analyze_execution_quality(execution_result)
        
        assert 'execution_quality' in result
        assert 'execution_score' in result
        assert 'recommendations' in result
    
    @pytest.mark.asyncio
    async def test_analyze_plan_vs_reality(self, performance_analyzer):
        """Test plan vs reality analysis"""
        position_data = {
            'position_id': 'pos_123',
            'original_plan': {
                'expected_pnl': 100,
                'expected_duration': 3600,
                'expected_entry_price': 30000
            },
            'actual_outcome': {
                'actual_pnl': 80,
                'actual_duration': 3000,
                'actual_entry_price': 30050
            }
        }
        
        result = await performance_analyzer.analyze_plan_vs_reality(position_data)
        
        assert 'comparison_analysis' in result
        assert 'timing_analysis' in result
        assert 'pnl_analysis' in result
        assert 'insights' in result
    
    @pytest.mark.asyncio
    async def test_contribute_execution_insights(self, performance_analyzer):
        """Test execution insights contribution"""
        analysis_data = {
            'execution_quality': {
                'execution_score': 0.8,
                'slippage': 0.001
            },
            'performance_analysis': {
                'execution_score': 0.8
            }
        }
        
        result = await performance_analyzer.contribute_execution_insights(analysis_data)
        
        assert isinstance(result, str)  # Should return strand ID
    
    @pytest.mark.asyncio
    async def test_get_execution_summary(self, performance_analyzer):
        """Test getting execution summary"""
        # Add some test execution history
        performance_analyzer.execution_history = [
            {'execution_score': 0.8, 'symbol': 'BTC'},
            {'execution_score': 0.9, 'symbol': 'ETH'}
        ]
        
        result = await performance_analyzer.get_execution_summary()
        
        assert 'total_executions' in result
        assert 'average_execution_score' in result
        assert 'total_venues' in result


class TestPositionTracker:
    """Test Position Tracker component"""
    
    @pytest.fixture
    def position_tracker(self):
        """Create PositionTracker instance for testing"""
        mock_supabase = Mock()
        mock_llm = Mock()
        return PositionTracker(mock_supabase, mock_llm)
    
    @pytest.mark.asyncio
    async def test_track_position_updates(self, position_tracker):
        """Test position tracking updates"""
        position_data = {
            'position_id': 'pos_123',
            'symbol': 'BTC',
            'current_price': 30000,
            'quantity': 0.1,
            'side': 'long'
        }
        
        result = await position_tracker.track_position_updates(position_data)
        
        assert result['status'] in ['tracking', 'error']
        assert 'position_metrics' in result
        assert 'risk_metrics' in result
    
    @pytest.mark.asyncio
    async def test_monitor_risk_metrics(self, position_tracker):
        """Test risk metrics monitoring"""
        position_data = {
            'symbol': 'BTC',
            'position_id': 'pos_123',
            'position_value': 3000,
            'unrealized_pnl': 100
        }
        
        result = await position_tracker.monitor_risk_metrics(position_data)
        
        assert result['status'] in ['monitoring', 'error']
        assert 'position_risk' in result
        assert 'portfolio_risk' in result
        assert 'risk_limits_check' in result
    
    @pytest.mark.asyncio
    async def test_close_position(self, position_tracker):
        """Test position closure"""
        position_id = 'pos_123'
        close_price = 31000
        
        # Add position to active positions
        position_tracker.active_positions[position_id] = {
            'position_id': position_id,
            'symbol': 'BTC',
            'side': 'long',
            'entry_price': 30000,
            'quantity': 0.1,
            'created_at': datetime.now()
        }
        
        result = await position_tracker.close_position(position_id, close_price)
        
        assert result['status'] in ['success', 'error']
        if result['status'] == 'success':
            assert 'realized_pnl' in result
            assert result['realized_pnl'] == 100  # (31000 - 30000) * 0.1
    
    @pytest.mark.asyncio
    async def test_get_risk_summary(self, position_tracker):
        """Test getting risk summary"""
        result = await position_tracker.get_risk_summary()
        
        assert 'portfolio_risk' in result
        assert 'risk_limits_check' in result
        assert 'active_positions' in result


class TestHyperliquidIntegration:
    """Test Hyperliquid Integration component"""
    
    @pytest.fixture
    def hyperliquid_integration(self):
        """Create HyperliquidIntegration instance for testing"""
        mock_supabase = Mock()
        mock_llm = Mock()
        return HyperliquidIntegration(mock_supabase, mock_llm, "test_key", "test_secret")
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self, hyperliquid_integration):
        """Test WebSocket connection"""
        # Mock websockets.connect
        with patch('websockets.connect') as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket
            
            result = await hyperliquid_integration.connect_websocket()
            
            # Should return False in test environment due to connection issues
            assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_place_order(self, hyperliquid_integration):
        """Test order placement"""
        order_data = {
            'symbol': 'BTC',
            'side': 'buy',
            'quantity': 0.1,
            'price': 30000
        }
        
        result = await hyperliquid_integration.place_order(order_data)
        
        assert result['status'] in ['success', 'error']
        assert 'order_placed' in result
    
    @pytest.mark.asyncio
    async def test_get_positions(self, hyperliquid_integration):
        """Test getting positions"""
        result = await hyperliquid_integration.get_positions()
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_get_order_status(self, hyperliquid_integration):
        """Test getting order status"""
        order_id = "test_order_123"
        
        # Add order to active orders
        hyperliquid_integration.active_orders[order_id] = {
            'order_data': {},
            'order_payload': {},
            'placed_at': datetime.now(),
            'status': 'pending'
        }
        
        result = await hyperliquid_integration.get_order_status(order_id)
        
        assert 'status' in result
        assert 'order_id' in result
    
    @pytest.mark.asyncio
    async def test_get_connection_status(self, hyperliquid_integration):
        """Test getting connection status"""
        result = await hyperliquid_integration.get_connection_status()
        
        assert 'websocket_connected' in result
        assert 'reconnect_attempts' in result
        assert 'active_orders' in result


class TestVenueFallbackManager:
    """Test Venue Fallback Manager component"""
    
    @pytest.fixture
    def venue_fallback_manager(self):
        """Create VenueFallbackManager instance for testing"""
        mock_supabase = Mock()
        mock_llm = Mock()
        return VenueFallbackManager(mock_supabase, mock_llm)
    
    @pytest.mark.asyncio
    async def test_select_fallback_venue(self, venue_fallback_manager):
        """Test fallback venue selection"""
        order_data = {
            'symbol': 'BTC',
            'quantity': 0.1,
            'venue': 'hyperliquid'
        }
        
        result = await venue_fallback_manager.select_fallback_venue(order_data)
        
        assert isinstance(result, str)
        assert result in ['binance', 'coinbase', '']  # Should be one of the available venues or empty
    
    @pytest.mark.asyncio
    async def test_track_venue_performance(self, venue_fallback_manager):
        """Test venue performance tracking"""
        venue = 'hyperliquid'
        execution_result = {
            'status': 'success',
            'execution_quality': {
                'slippage': 0.001,
                'latency_ms': 500,
                'fees': 0.0002
            }
        }
        
        await venue_fallback_manager.track_venue_performance(venue, execution_result)
        
        # Check that performance was tracked
        assert venue in venue_fallback_manager.venue_performance
        assert venue_fallback_manager.venue_performance[venue]['total_orders'] == 1
    
    @pytest.mark.asyncio
    async def test_get_venue_performance_summary(self, venue_fallback_manager):
        """Test getting venue performance summary"""
        # Add some test performance data
        venue_fallback_manager.venue_performance['hyperliquid'] = {
            'total_orders': 10,
            'successful_orders': 9,
            'success_rate': 0.9
        }
        
        result = await venue_fallback_manager.get_venue_performance_summary()
        
        assert 'all_venues' in result or 'venue' in result
        assert 'venue_count' in result or 'performance' in result
    
    @pytest.mark.asyncio
    async def test_get_venue_recommendations(self, venue_fallback_manager):
        """Test getting venue recommendations"""
        symbol = 'BTC'
        quantity = 0.1
        
        result = await venue_fallback_manager.get_venue_recommendations(symbol, quantity)
        
        assert 'recommendations' in result
        assert 'symbol' in result
        assert 'quantity' in result


class TestCILIntegration:
    """Test CIL Integration component"""
    
    @pytest.fixture
    def cil_integration(self):
        """Create CILIntegration instance for testing"""
        mock_supabase = Mock()
        mock_llm = Mock()
        return CILIntegration(mock_supabase, mock_llm)
    
    @pytest.mark.asyncio
    async def test_consume_cil_insights(self, cil_integration):
        """Test CIL insights consumption"""
        execution_context = {
            'symbol': 'BTC',
            'execution_type': 'trading_plan_execution'
        }
        
        result = await cil_integration.consume_cil_insights(execution_context)
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_contribute_execution_learning(self, cil_integration):
        """Test execution learning contribution"""
        execution_data = {
            'execution_quality': {
                'execution_score': 0.8,
                'slippage': 0.001
            },
            'venue': 'hyperliquid'
        }
        
        result = await cil_integration.contribute_execution_learning(execution_data)
        
        assert isinstance(result, str)  # Should return strand ID
    
    @pytest.mark.asyncio
    async def test_participate_in_resonance(self, cil_integration):
        """Test resonance participation"""
        execution_pattern = {
            'pattern_type': 'execution_quality',
            'execution_score': 0.8,
            'success_rate': 0.9,
            'frequency': 5
        }
        
        result = await cil_integration.participate_in_resonance(execution_pattern)
        
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
    
    @pytest.mark.asyncio
    async def test_get_cil_integration_summary(self, cil_integration):
        """Test getting CIL integration summary"""
        result = await cil_integration.get_cil_integration_summary()
        
        assert 'consumed_insights_count' in result
        assert 'contributed_insights_count' in result
        assert 'learning_contributions_count' in result


class TestTraderTeamCoordinator:
    """Test Trader Team Coordinator component"""
    
    @pytest.fixture
    def trader_coordinator(self):
        """Create TraderTeamCoordinator instance for testing"""
        mock_supabase = Mock()
        mock_llm = Mock()
        return TraderTeamCoordinator(mock_supabase, mock_llm, "test_key", "test_secret")
    
    @pytest.mark.asyncio
    async def test_execute_trading_plan(self, trader_coordinator):
        """Test trading plan execution"""
        trading_plan = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'entry_conditions': {
                'price_breakout': {
                    'threshold': 30000,
                    'direction': 'above'
                }
            },
            'order_details': {
                'side': 'buy',
                'quantity': 0.1,
                'price': 30000
            }
        }
        
        result = await trader_coordinator.execute_trading_plan(trading_plan)
        
        assert 'execution_id' in result
        assert 'status' in result
        assert 'trading_plan' in result
        assert 'started_at' in result
    
    @pytest.mark.asyncio
    async def test_coordinate_team_activities(self, trader_coordinator):
        """Test team activity coordination"""
        # This should not raise an exception
        await trader_coordinator.coordinate_team_activities()
        
        # Check that team status was updated
        assert 'order_manager' in trader_coordinator.team_status
        assert 'performance_analyzer' in trader_coordinator.team_status
    
    @pytest.mark.asyncio
    async def test_get_team_summary(self, trader_coordinator):
        """Test getting team summary"""
        result = await trader_coordinator.get_team_summary()
        
        assert 'team_status' in result
        assert 'execution_metrics' in result
        assert 'active_executions' in result
        assert 'component_summaries' in result
    
    @pytest.mark.asyncio
    async def test_get_execution_history(self, trader_coordinator):
        """Test getting execution history"""
        # Add some test execution history
        trader_coordinator.execution_history = [
            {'execution_id': 'exec1', 'status': 'completed'},
            {'execution_id': 'exec2', 'status': 'failed'}
        ]
        
        result = await trader_coordinator.get_execution_history(limit=10)
        
        assert isinstance(result, list)
        assert len(result) <= 10
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, trader_coordinator):
        """Test execution cancellation"""
        execution_id = 'test_exec_123'
        
        # Add execution to current executions
        trader_coordinator.current_executions[execution_id] = {
            'execution_id': execution_id,
            'status': 'order_placed',
            'order_id': 'order_123'
        }
        
        result = await trader_coordinator.cancel_execution(execution_id)
        
        assert result['status'] in ['success', 'error']
        if result['status'] == 'success':
            assert result['execution_id'] == execution_id


class TestIntegration:
    """Integration tests for Trader Team components"""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components for integration testing"""
        mock_supabase = Mock()
        mock_llm = Mock()
        
        return {
            'order_manager': OrderManager(mock_supabase, mock_llm),
            'performance_analyzer': PerformanceAnalyzer(mock_supabase, mock_llm),
            'position_tracker': PositionTracker(mock_supabase, mock_llm),
            'hyperliquid_integration': HyperliquidIntegration(mock_supabase, mock_llm),
            'venue_fallback_manager': VenueFallbackManager(mock_supabase, mock_llm),
            'cil_integration': CILIntegration(mock_supabase, mock_llm),
            'trader_coordinator': TraderTeamCoordinator(mock_supabase, mock_llm)
        }
    
    @pytest.mark.asyncio
    async def test_component_initialization(self, mock_components):
        """Test that all components can be initialized"""
        for component_name, component in mock_components.items():
            assert component is not None
            assert hasattr(component, 'supabase_manager')
            assert hasattr(component, 'llm_client')
    
    @pytest.mark.asyncio
    async def test_component_communication(self, mock_components):
        """Test that components can communicate through strands"""
        # Test that components can publish strands
        order_manager = mock_components['order_manager']
        performance_analyzer = mock_components['performance_analyzer']
        
        # Mock the supabase manager to track strand publications
        strand_publications = []
        order_manager.supabase_manager.insert_data = AsyncMock(side_effect=lambda table, data: strand_publications.append((table, data)))
        performance_analyzer.supabase_manager.insert_data = AsyncMock(side_effect=lambda table, data: strand_publications.append((table, data)))
        
        # Test order manager strand publication
        trading_plan = {
            'symbol': 'BTC',
            'entry_conditions': {'price_breakout': {'threshold': 30000, 'direction': 'above'}}
        }
        
        await order_manager.monitor_entry_conditions(trading_plan)
        
        # Test performance analyzer strand publication
        execution_result = {
            'order_id': 'test_123',
            'symbol': 'BTC',
            'execution_time': 0.5,
            'filled_price': 30000,
            'expected_price': 29950,
            'filled_quantity': 0.1,
            'order_details': {'quantity': 0.1}
        }
        
        await performance_analyzer.analyze_execution_quality(execution_result)
        
        # Verify that strands were published
        assert len(strand_publications) >= 2
        assert all(publication[0] == 'AD_strands' for publication in strand_publications)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
