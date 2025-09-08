"""
Test Enhanced Raw Data Intelligence Agent

Comprehensive test for the enhanced RawDataIntelligenceAgent with LLM control capabilities.
Tests the complete LLM Agents as System Managers architecture.
"""

import asyncio
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from llm_integration.openrouter_client import OpenRouterClient
from utils.supabase_manager import SupabaseManager


class TestEnhancedRawDataIntelligence:
    """Test suite for enhanced RawDataIntelligenceAgent"""
    
    def setup_method(self):
        """Set up test environment"""
        # Mock dependencies
        self.mock_supabase = Mock(spec=SupabaseManager)
        self.mock_llm_client = Mock(spec=OpenRouterClient)
        
        # Mock Supabase client chain
        self.mock_supabase.client = Mock()
        self.mock_supabase.client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        self.mock_supabase.create_strand = AsyncMock(return_value="test_strand_id")
        
        # Mock LLM client methods
        self.mock_llm_client.decide_tool_usage = AsyncMock(return_value={
            'tools_to_use': ['divergence_detector', 'volume_analyzer'],
            'tool_configurations': {
                'divergence_detector': {'threshold': 0.15, 'lookback_period': 25},
                'volume_analyzer': {'volume_threshold': 2.0, 'spike_detection': True}
            },
            'reasoning': 'High volatility detected, adjusting parameters',
            'confidence': 0.8
        })
        
        self.mock_llm_client.optimize_divergence_detection = AsyncMock(return_value={
            'optimized_config': {'threshold': 0.12, 'lookback_period': 30},
            'reasoning': 'Market showing increased volatility',
            'confidence': 0.85
        })
        
        # Create agent
        self.agent = RawDataIntelligenceAgent(self.mock_supabase, self.mock_llm_client)
        
        # Create sample market data
        self.sample_data = self._create_sample_market_data()
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _create_sample_market_data(self) -> pd.DataFrame:
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        
        data = []
        for i, date in enumerate(dates):
            # Create realistic OHLCV data with some patterns
            base_price = 50000 + i * 10 + np.sin(i * 0.1) * 100
            high = base_price + np.random.uniform(0, 50)
            low = base_price - np.random.uniform(0, 50)
            open_price = base_price + np.random.uniform(-20, 20)
            close = base_price + np.random.uniform(-20, 20)
            volume = np.random.uniform(1000, 10000)
            
            data.append({
                'timestamp': date,
                'symbol': 'BTC',
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    async def test_agent_initialization(self):
        """Test agent initialization with enhanced capabilities"""
        self.logger.info("Testing agent initialization...")
        
        # Check basic properties
        assert self.agent.agent_name == "raw_data_intelligence"
        assert len(self.agent.capabilities) > 0
        assert len(self.agent.specializations) > 0
        assert len(self.agent.available_tools) == 5
        
        # Check tool registry
        expected_tools = [
            'divergence_detector', 'volume_analyzer', 'microstructure_analyzer',
            'time_pattern_detector', 'cross_asset_analyzer'
        ]
        for tool in expected_tools:
            assert tool in self.agent.available_tools
            assert 'configurable_parameters' in self.agent.available_tools[tool]
            assert 'documentation' in self.agent.available_tools[tool]
        
        # Check analysis components
        assert hasattr(self.agent, 'divergence_detector')
        assert hasattr(self.agent, 'volume_analyzer')
        assert hasattr(self.agent, 'microstructure_analyzer')
        assert hasattr(self.agent, 'time_pattern_detector')
        assert hasattr(self.agent, 'cross_asset_analyzer')
        
        self.logger.info("✅ Agent initialization test passed")
    
    async def test_get_context(self):
        """Test context retrieval from database"""
        self.logger.info("Testing context retrieval...")
        
        # Mock context system
        with patch.object(self.agent.context_system, 'get_relevant_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                'current_analysis': {'test': 'data'},
                'generated_lessons': [{'lesson': 'test lesson'}],
                'similar_situations': [{'situation': 'test'}],
                'pattern_clusters': [{'cluster': 'test'}]
            }
            
            context = await self.agent.get_context('test_analysis', self.sample_data)
            
            # Verify context was retrieved
            assert 'current_analysis' in context
            assert 'generated_lessons' in context
            assert len(context['generated_lessons']) == 1
            
            # Verify context system was called correctly
            mock_context.assert_called_once()
            call_args = mock_context.call_args[0][0]
            assert call_args['agent_name'] == 'raw_data_intelligence'
            assert call_args['analysis_type'] == 'test_analysis'
        
        self.logger.info("✅ Context retrieval test passed")
    
    async def test_decide_tool_usage(self):
        """Test LLM tool usage decision"""
        self.logger.info("Testing LLM tool usage decision...")
        
        context = {'test': 'context'}
        
        tool_decision = await self.agent.decide_tool_usage(context, self.sample_data)
        
        # Verify tool decision structure
        assert 'tools_to_use' in tool_decision
        assert 'tool_configurations' in tool_decision
        assert 'reasoning' in tool_decision
        assert 'confidence' in tool_decision
        
        # Verify LLM client was called
        self.mock_llm_client.decide_tool_usage.assert_called_once()
        
        # Verify tool configurations
        assert 'divergence_detector' in tool_decision['tool_configurations']
        assert 'volume_analyzer' in tool_decision['tool_configurations']
        
        self.logger.info("✅ Tool usage decision test passed")
    
    async def test_configure_tool(self):
        """Test tool configuration"""
        self.logger.info("Testing tool configuration...")
        
        # Test configuring divergence detector
        config = {'threshold': 0.15, 'lookback_period': 25}
        
        result = await self.agent.configure_tool('divergence_detector', config)
        
        # Verify configuration was successful
        assert result is True
        
        # Verify parameters were updated
        assert self.agent.divergence_detector.threshold == 0.15
        assert self.agent.divergence_detector.lookback_period == 25
        
        # Test configuring volume analyzer
        volume_config = {'volume_threshold': 2.0, 'spike_detection': True}
        
        result = await self.agent.configure_tool('volume_analyzer', volume_config)
        
        # Verify configuration was successful
        assert result is True
        
        # Verify parameters were updated
        assert self.agent.volume_analyzer.volume_threshold == 2.0
        assert self.agent.volume_analyzer.spike_detection is True
        
        self.logger.info("✅ Tool configuration test passed")
    
    async def test_store_results(self):
        """Test storing analysis results as strands"""
        self.logger.info("Testing result storage...")
        
        results = {
            'analysis_type': 'test_analysis',
            'results': {'test': 'data'},
            'confidence': 0.8
        }
        
        tool_decision = {
            'tools_to_use': ['divergence_detector'],
            'reasoning': 'Test reasoning'
        }
        
        strand_id = await self.agent.store_results(results, tool_decision)
        
        # Verify strand was created
        assert strand_id == "test_strand_id"
        
        # Verify Supabase was called
        self.mock_supabase.create_strand.assert_called_once()
        
        # Verify analysis history was updated
        assert len(self.agent.analysis_history) == 1
        assert self.agent.analysis_history[0]['strand_id'] == "test_strand_id"
        
        self.logger.info("✅ Result storage test passed")
    
    async def test_execute_enhanced_analysis(self):
        """Test complete enhanced analysis flow"""
        self.logger.info("Testing enhanced analysis execution...")
        
        # Mock context system
        with patch.object(self.agent.context_system, 'get_relevant_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                'current_analysis': {'test': 'data'},
                'generated_lessons': [],
                'similar_situations': [],
                'pattern_clusters': []
            }
            
            # Mock analysis methods
            with patch.object(self.agent, '_analyze_raw_data_divergences', new_callable=AsyncMock) as mock_divergence:
                with patch.object(self.agent, '_analyze_volume_patterns', new_callable=AsyncMock) as mock_volume:
                    mock_divergence.return_value = {'divergences': 'test'}
                    mock_volume.return_value = {'volume': 'test'}
                    
                    # Execute enhanced analysis
                    result = await self.agent.execute_enhanced_analysis(self.sample_data, 'comprehensive')
                    
                    # Verify result structure
                    assert 'analysis_results' in result
                    assert 'tool_decision' in result
                    assert 'configured_tools' in result
                    assert 'context_used' in result
                    assert 'strand_id' in result
                    assert 'timestamp' in result
                    
                    # Verify analysis was executed
                    assert len(result['configured_tools']) == 2
                    assert 'divergence_detector' in result['configured_tools']
                    assert 'volume_analyzer' in result['configured_tools']
                    
                    # Verify analysis methods were called
                    mock_divergence.assert_called_once()
                    mock_volume.assert_called_once()
        
        self.logger.info("✅ Enhanced analysis execution test passed")
    
    async def test_llm_configure_divergence_detection(self):
        """Test LLM-controlled divergence detection configuration"""
        self.logger.info("Testing LLM divergence detection configuration...")
        
        market_conditions = {'volatility': 'high', 'trend': 'bullish'}
        performance_data = {'accuracy': 0.8, 'precision': 0.75}
        
        result = await self.agent.llm_configure_divergence_detection(market_conditions, performance_data)
        
        # Verify result structure
        assert 'optimized_config' in result
        assert 'reasoning' in result
        assert 'confidence' in result
        
        # Verify LLM client was called
        self.mock_llm_client.optimize_divergence_detection.assert_called_once()
        
        # Verify configuration was applied
        assert self.agent.divergence_detector.threshold == 0.12
        assert self.agent.divergence_detector.lookback_period == 30
        
        self.logger.info("✅ LLM divergence configuration test passed")
    
    async def test_llm_configure_volume_analysis(self):
        """Test LLM-controlled volume analysis configuration"""
        self.logger.info("Testing LLM volume analysis configuration...")
        
        # Mock LLM client for volume analysis
        self.mock_llm_client.optimize_volume_analysis = AsyncMock(return_value={
            'optimized_config': {'volume_threshold': 2.5, 'spike_detection': True},
            'reasoning': 'High volume activity detected',
            'confidence': 0.9
        })
        
        market_conditions = {'volume': 'high', 'activity': 'increased'}
        performance_data = {'volume_accuracy': 0.85}
        
        result = await self.agent.llm_configure_volume_analysis(market_conditions, performance_data)
        
        # Verify result structure
        assert 'optimized_config' in result
        assert 'reasoning' in result
        assert 'confidence' in result
        
        # Verify LLM client was called
        self.mock_llm_client.optimize_volume_analysis.assert_called_once()
        
        # Verify configuration was applied
        assert self.agent.volume_analyzer.volume_threshold == 2.5
        assert self.agent.volume_analyzer.spike_detection is True
        
        self.logger.info("✅ LLM volume configuration test passed")
    
    async def test_agent_status(self):
        """Test agent status reporting"""
        self.logger.info("Testing agent status...")
        
        status = self.agent.get_agent_status()
        
        # Verify status structure
        assert 'agent_name' in status
        assert 'is_running' in status
        assert 'capabilities' in status
        assert 'specializations' in status
        assert 'available_tools' in status
        assert 'last_analysis_time' in status
        assert 'analysis_count' in status
        assert 'communication_stats' in status
        
        # Verify values
        assert status['agent_name'] == 'raw_data_intelligence'
        assert status['is_running'] is False
        assert len(status['available_tools']) == 5
        # Note: analysis_count may be > 0 due to previous tests
        
        self.logger.info("✅ Agent status test passed")
    
    async def test_error_handling(self):
        """Test error handling in enhanced methods"""
        self.logger.info("Testing error handling...")
        
        # Test context retrieval error
        with patch.object(self.agent.context_system, 'get_relevant_context', new_callable=AsyncMock) as mock_context:
            mock_context.side_effect = Exception("Database error")
            
            context = await self.agent.get_context('test', self.sample_data)
            
            # Verify error handling
            assert 'error' in context
            assert context['error'] == "Database error"
        
        # Test tool configuration error
        result = await self.agent.configure_tool('nonexistent_tool', {})
        assert result is False
        
        # Test LLM decision error
        self.mock_llm_client.decide_tool_usage.side_effect = Exception("LLM error")
        
        tool_decision = await self.agent.decide_tool_usage({}, self.sample_data)
        
        # Verify fallback behavior
        assert 'tools_to_use' in tool_decision
        assert 'reasoning' in tool_decision
        assert 'Fallback due to error' in tool_decision['reasoning']
        
        self.logger.info("✅ Error handling test passed")
    
    async def run_all_tests(self):
        """Run all tests"""
        self.logger.info("🚀 Starting Enhanced Raw Data Intelligence Agent Tests")
        
        try:
            await self.test_agent_initialization()
            await self.test_get_context()
            await self.test_decide_tool_usage()
            await self.test_configure_tool()
            await self.test_store_results()
            await self.test_execute_enhanced_analysis()
            await self.test_llm_configure_divergence_detection()
            await self.test_llm_configure_volume_analysis()
            await self.test_agent_status()
            await self.test_error_handling()
            
            self.logger.info("🎉 All tests passed! Enhanced Raw Data Intelligence Agent is working correctly.")
            
        except Exception as e:
            self.logger.error(f"❌ Test failed: {e}")
            raise


async def main():
    """Main test runner"""
    test_suite = TestEnhancedRawDataIntelligence()
    test_suite.setup_method()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
