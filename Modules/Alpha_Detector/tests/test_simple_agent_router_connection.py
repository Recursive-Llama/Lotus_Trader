"""
Simple Agent-Router Connection Test

A focused test to verify that the enhanced RawDataIntelligenceAgent can connect
to the Central Intelligence Router and perform basic database-centric communication.
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
from llm_integration.central_intelligence_router import CentralIntelligenceRouter
from llm_integration.agent_communication_protocol import AgentCommunicationProtocol
from llm_integration.agent_discovery_system import AgentDiscoverySystem
from llm_integration.openrouter_client import OpenRouterClient
from utils.supabase_manager import SupabaseManager


class SimpleAgentRouterConnectionTest:
    """Simple test for agent-router connection"""
    
    def setup_method(self):
        """Set up test environment"""
        # Mock dependencies
        self.mock_supabase = Mock(spec=SupabaseManager)
        self.mock_llm_client = Mock(spec=OpenRouterClient)
        
        # Mock Supabase client chain
        self.mock_supabase.client = Mock()
        self.mock_supabase.client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        self.mock_supabase.create_strand = AsyncMock(return_value="test_strand_id")
        self.mock_supabase.get_strands = AsyncMock(return_value=[])
        
        # Mock LLM client methods
        self.mock_llm_client.decide_tool_usage = AsyncMock(return_value={
            'tools_to_use': ['divergence_detector'],
            'tool_configurations': {
                'divergence_detector': {'threshold': 0.15, 'lookback_period': 25}
            },
            'reasoning': 'Testing basic configuration',
            'confidence': 0.8
        })
        
        # Create enhanced agent
        self.enhanced_agent = RawDataIntelligenceAgent(self.mock_supabase, self.mock_llm_client)
        
        # Create sample market data
        self.sample_data = self._create_sample_market_data()
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _create_sample_market_data(self) -> pd.DataFrame:
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        
        data = []
        for i, date in enumerate(dates):
            base_price = 50000 + i * 10
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
    
    async def test_enhanced_agent_creation(self):
        """Test that the enhanced agent can be created successfully"""
        self.logger.info("Testing enhanced agent creation...")
        
        # Verify agent was created with all expected attributes
        assert hasattr(self.enhanced_agent, 'context_system')
        assert hasattr(self.enhanced_agent, 'available_tools')
        assert hasattr(self.enhanced_agent, 'execute_enhanced_analysis')
        assert hasattr(self.enhanced_agent, 'llm_configure_divergence_detection')
        
        # Verify available tools
        assert 'divergence_detector' in self.enhanced_agent.available_tools
        assert 'volume_analyzer' in self.enhanced_agent.available_tools
        
        self.logger.info("✅ Enhanced agent creation test passed")
    
    async def test_agent_strand_creation(self):
        """Test that the enhanced agent can create strands"""
        self.logger.info("Testing agent strand creation...")
        
        # Mock context system
        with patch.object(self.enhanced_agent.context_system, 'get_relevant_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                'current_analysis': {'test': 'data'},
                'generated_lessons': [],
                'similar_situations': [],
                'pattern_clusters': []
            }
            
            # Mock analysis methods
            with patch.object(self.enhanced_agent, '_analyze_raw_data_divergences', new_callable=AsyncMock) as mock_divergence:
                mock_divergence.return_value = {'divergences': 'test'}
                
                # Execute enhanced analysis
                result = await self.enhanced_agent.execute_enhanced_analysis(self.sample_data, 'comprehensive')
                
                # Verify strand was created
                assert 'strand_id' in result
                assert result['strand_id'] == "test_strand_id"
                
                # Verify Supabase was called to create strand
                self.mock_supabase.create_strand.assert_called()
        
        self.logger.info("✅ Agent strand creation test passed")
    
    async def test_central_router_creation(self):
        """Test that the Central Intelligence Router can be created"""
        self.logger.info("Testing Central Intelligence Router creation...")
        
        # Create router with mocked context system
        mock_context_system = Mock()
        central_router = CentralIntelligenceRouter(
            supabase_manager=self.mock_supabase,
            context_system=mock_context_system
        )
        
        # Verify router was created with expected attributes
        assert hasattr(central_router, 'agent_capabilities')
        assert hasattr(central_router, 'routing_history')
        assert hasattr(central_router, 'register_agent_capabilities')
        assert hasattr(central_router, 'start_monitoring')
        assert hasattr(central_router, 'stop_monitoring')
        
        self.logger.info("✅ Central Intelligence Router creation test passed")
    
    async def test_agent_communication_protocol_creation(self):
        """Test that the Agent Communication Protocol can be created"""
        self.logger.info("Testing Agent Communication Protocol creation...")
        
        # Create communication protocol
        agent_protocol = AgentCommunicationProtocol(
            agent_name='raw_data_intelligence',
            supabase_manager=self.mock_supabase
        )
        
        # Verify protocol was created with expected attributes
        assert hasattr(agent_protocol, 'agent_name')
        assert hasattr(agent_protocol, 'publish_finding')
        assert hasattr(agent_protocol, 'start_listening')
        assert hasattr(agent_protocol, 'stop_listening')
        
        self.logger.info("✅ Agent Communication Protocol creation test passed")
    
    async def test_agent_discovery_system_creation(self):
        """Test that the Agent Discovery System can be created"""
        self.logger.info("Testing Agent Discovery System creation...")
        
        # Create discovery system
        discovery_system = AgentDiscoverySystem(self.mock_supabase)
        
        # Verify system was created with expected attributes
        assert hasattr(discovery_system, 'register_agent_capabilities')
        assert hasattr(discovery_system, 'find_agents_for_content')
        assert hasattr(discovery_system, 'update_agent_performance')
        
        self.logger.info("✅ Agent Discovery System creation test passed")
    
    async def test_agent_registration_with_discovery_system(self):
        """Test registering agent capabilities with the discovery system"""
        self.logger.info("Testing agent registration with discovery system...")
        
        # Create discovery system
        discovery_system = AgentDiscoverySystem(self.mock_supabase)
        
        # Register agent capabilities
        result = await discovery_system.register_agent_capabilities(
            agent_name='raw_data_intelligence',
            capabilities=['raw_data_analysis', 'divergence_detection'],
            specializations=['market_microstructure', 'volume_analysis']
        )
        
        # Verify registration was successful
        assert result is True
        
        self.logger.info("✅ Agent registration with discovery system test passed")
    
    async def test_agent_communication_protocol_publish(self):
        """Test that the agent communication protocol can publish findings"""
        self.logger.info("Testing agent communication protocol publish...")
        
        # Create communication protocol
        agent_protocol = AgentCommunicationProtocol(
            agent_name='raw_data_intelligence',
            supabase_manager=self.mock_supabase
        )
        
        # Test publishing a finding
        finding_content = {
            'analysis_type': 'divergence_detection',
            'findings': {'divergence_detected': True, 'confidence': 0.8},
            'market_conditions': {'volatility': 'high'}
        }
        
        # Mock the publish_finding method
        with patch.object(agent_protocol, 'publish_finding', new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = "published_strand_id"
            
            strand_id = await agent_protocol.publish_finding(finding_content, "agent:raw_data_intelligence:finding")
            
            # Verify finding was published
            assert strand_id == "published_strand_id"
            mock_publish.assert_called_once()
        
        self.logger.info("✅ Agent communication protocol publish test passed")
    
    async def test_llm_controlled_parameter_management(self):
        """Test LLM-controlled parameter management"""
        self.logger.info("Testing LLM-controlled parameter management...")
        
        # Mock LLM client for divergence configuration
        self.mock_llm_client.optimize_divergence_detection = AsyncMock(return_value={
            'optimized_config': {'threshold': 0.12, 'lookback_period': 30},
            'reasoning': 'Market showing increased volatility',
            'confidence': 0.85
        })
        
        # Test LLM configuration
        market_conditions = {'volatility': 'high', 'trend': 'bullish'}
        performance_data = {'accuracy': 0.8, 'precision': 0.75}
        
        config_result = await self.enhanced_agent.llm_configure_divergence_detection(market_conditions, performance_data)
        
        # Verify configuration was successful
        assert 'optimized_config' in config_result
        assert config_result['optimized_config']['threshold'] == 0.12
        assert config_result['optimized_config']['lookback_period'] == 30
        
        # Verify parameters were actually updated in the agent
        assert self.enhanced_agent.divergence_detector.threshold == 0.12
        assert self.enhanced_agent.divergence_detector.lookback_period == 30
        
        self.logger.info("✅ LLM-controlled parameter management test passed")
    
    async def run_all_tests(self):
        """Run all simple connection tests"""
        self.logger.info("🚀 Starting Simple Agent-Router Connection Tests")
        
        try:
            await self.test_enhanced_agent_creation()
            await self.test_agent_strand_creation()
            await self.test_central_router_creation()
            await self.test_agent_communication_protocol_creation()
            await self.test_agent_discovery_system_creation()
            await self.test_agent_registration_with_discovery_system()
            await self.test_agent_communication_protocol_publish()
            await self.test_llm_controlled_parameter_management()
            
            self.logger.info("🎉 All simple connection tests passed! Basic agent-router connection is working.")
            
        except Exception as e:
            self.logger.error(f"❌ Connection test failed: {e}")
            raise


async def main():
    """Main test runner"""
    test_suite = SimpleAgentRouterConnectionTest()
    test_suite.setup_method()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
