"""
Test Agent-Router Integration

Comprehensive integration test for connecting the enhanced RawDataIntelligenceAgent
to the Central Intelligence Router and testing database-centric communication.
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


class TestAgentRouterIntegration:
    """Test suite for agent-router integration"""
    
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
            'tools_to_use': ['divergence_detector', 'volume_analyzer'],
            'tool_configurations': {
                'divergence_detector': {'threshold': 0.15, 'lookback_period': 25},
                'volume_analyzer': {'volume_threshold': 2.0, 'spike_detection': True}
            },
            'reasoning': 'High volatility detected, adjusting parameters',
            'confidence': 0.8
        })
        
        # Create enhanced agent
        self.enhanced_agent = RawDataIntelligenceAgent(self.mock_supabase, self.mock_llm_client)
        
        # Create Central Intelligence Router
        self.central_router = CentralIntelligenceRouter(
            db_manager=self.mock_supabase,
            context_system=None,  # Will mock this
            vector_store=None     # Will mock this
        )
        
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
    
    async def test_agent_registration_with_router(self):
        """Test registering the enhanced agent with the Central Intelligence Router"""
        self.logger.info("Testing agent registration with router...")
        
        # Register agent capabilities with the router
        agent_capabilities = {
            'agent_name': 'raw_data_intelligence',
            'capabilities': self.enhanced_agent.capabilities,
            'specializations': self.enhanced_agent.specializations,
            'available_tools': list(self.enhanced_agent.available_tools.keys()),
            'communication_protocol': 'database_centric'
        }
        
        # Mock the router's agent registration
        with patch.object(self.central_router, 'register_agent_capabilities', new_callable=AsyncMock) as mock_register:
            mock_register.return_value = True
            
            result = await self.central_router.register_agent_capabilities(agent_capabilities)
            
            # Verify registration was successful
            assert result is True
            mock_register.assert_called_once_with(agent_capabilities)
        
        self.logger.info("✅ Agent registration test passed")
    
    async def test_agent_strand_creation_and_routing(self):
        """Test that the enhanced agent creates strands and the router routes them"""
        self.logger.info("Testing agent strand creation and routing...")
        
        # Mock context system for the agent
        with patch.object(self.enhanced_agent.context_system, 'get_relevant_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                'current_analysis': {'test': 'data'},
                'generated_lessons': [],
                'similar_situations': [],
                'pattern_clusters': []
            }
            
            # Mock analysis methods
            with patch.object(self.enhanced_agent, '_analyze_raw_data_divergences', new_callable=AsyncMock) as mock_divergence:
                with patch.object(self.enhanced_agent, '_analyze_volume_patterns', new_callable=AsyncMock) as mock_volume:
                    mock_divergence.return_value = {'divergences': 'test'}
                    mock_volume.return_value = {'volume': 'test'}
                    
                    # Execute enhanced analysis (this should create a strand)
                    result = await self.enhanced_agent.execute_enhanced_analysis(self.sample_data, 'comprehensive')
                    
                    # Verify strand was created
                    assert 'strand_id' in result
                    assert result['strand_id'] == "test_strand_id"
                    
                    # Verify Supabase was called to create strand
                    self.mock_supabase.create_strand.assert_called()
                    
                    # Now test router monitoring and routing
                    with patch.object(self.central_router, 'monitor_strands', new_callable=AsyncMock) as mock_monitor:
                        with patch.object(self.central_router, 'route_agent_communication', new_callable=AsyncMock) as mock_route:
                            mock_monitor.return_value = [{'id': 'test_strand_id', 'content': result}]
                            mock_route.return_value = True
                            
                            # Simulate router monitoring the new strand
                            monitored_strands = await self.central_router.monitor_strands()
                            
                            # Verify monitoring found the strand
                            assert len(monitored_strands) == 1
                            assert monitored_strands[0]['id'] == 'test_strand_id'
                            
                            # Simulate router routing the strand
                            routing_result = await self.central_router.route_agent_communication(monitored_strands[0])
                            
                            # Verify routing was successful
                            assert routing_result is True
        
        self.logger.info("✅ Agent strand creation and routing test passed")
    
    async def test_agent_communication_protocol(self):
        """Test the agent communication protocol"""
        self.logger.info("Testing agent communication protocol...")
        
        # Create communication protocol for the agent
        agent_protocol = AgentCommunicationProtocol(
            agent_name='raw_data_intelligence',
            db_manager=self.mock_supabase
        )
        
        # Test publishing a finding
        finding_content = {
            'analysis_type': 'divergence_detection',
            'findings': {'divergence_detected': True, 'confidence': 0.8},
            'market_conditions': {'volatility': 'high'}
        }
        
        with patch.object(agent_protocol, 'publish_finding', new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = "published_strand_id"
            
            strand_id = await agent_protocol.publish_finding(finding_content, "agent:raw_data_intelligence:finding")
            
            # Verify finding was published
            assert strand_id == "published_strand_id"
            mock_publish.assert_called_once()
        
        # Test listening for routed strands
        with patch.object(agent_protocol, 'listen_for_routed_strands', new_callable=AsyncMock) as mock_listen:
            mock_listen.return_value = [{'id': 'routed_strand_id', 'content': 'routed_content'}]
            
            routed_strands = await agent_protocol.listen_for_routed_strands()
            
            # Verify routed strands were received
            assert len(routed_strands) == 1
            assert routed_strands[0]['id'] == 'routed_strand_id'
        
        self.logger.info("✅ Agent communication protocol test passed")
    
    async def test_agent_discovery_system(self):
        """Test the agent discovery system"""
        self.logger.info("Testing agent discovery system...")
        
        # Create agent discovery system
        discovery_system = AgentDiscoverySystem(self.mock_supabase)
        
        # Test registering agent capabilities
        agent_capabilities = {
            'agent_name': 'raw_data_intelligence',
            'capabilities': ['raw_data_analysis', 'divergence_detection'],
            'specializations': ['market_microstructure', 'volume_analysis'],
            'performance_metrics': {'accuracy': 0.85, 'precision': 0.80}
        }
        
        with patch.object(discovery_system, 'register_agent_capabilities', new_callable=AsyncMock) as mock_register:
            mock_register.return_value = True
            
            result = await discovery_system.register_agent_capabilities(agent_capabilities)
            
            # Verify registration was successful
            assert result is True
            mock_register.assert_called_once_with(agent_capabilities)
        
        # Test finding agents for content
        with patch.object(discovery_system, 'find_agents_for_content', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = [{'agent_name': 'raw_data_intelligence', 'match_score': 0.9}]
            
            relevant_agents = await discovery_system.find_agents_for_content('divergence_detection', None)
            
            # Verify relevant agents were found
            assert len(relevant_agents) == 1
            assert relevant_agents[0]['agent_name'] == 'raw_data_intelligence'
            assert relevant_agents[0]['match_score'] == 0.9
        
        self.logger.info("✅ Agent discovery system test passed")
    
    async def test_complete_agent_router_flow(self):
        """Test the complete flow from agent analysis to router routing"""
        self.logger.info("Testing complete agent-router flow...")
        
        # Step 1: Agent performs analysis and creates strand
        with patch.object(self.enhanced_agent.context_system, 'get_relevant_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                'current_analysis': {'test': 'data'},
                'generated_lessons': [],
                'similar_situations': [],
                'pattern_clusters': []
            }
            
            with patch.object(self.enhanced_agent, '_analyze_raw_data_divergences', new_callable=AsyncMock) as mock_divergence:
                mock_divergence.return_value = {'divergences': 'test'}
                
                # Agent executes analysis
                analysis_result = await self.enhanced_agent.execute_enhanced_analysis(self.sample_data, 'comprehensive')
                
                # Verify analysis completed and strand was created
                assert 'strand_id' in analysis_result
                assert analysis_result['strand_id'] == "test_strand_id"
        
        # Step 2: Router monitors and routes the strand
        with patch.object(self.central_router, 'monitor_strands', new_callable=AsyncMock) as mock_monitor:
            with patch.object(self.central_router, 'route_agent_communication', new_callable=AsyncMock) as mock_route:
                # Mock router finding the new strand
                mock_monitor.return_value = [{
                    'id': 'test_strand_id',
                    'content': analysis_result,
                    'source_agent': 'raw_data_intelligence',
                    'tags': 'agent:raw_data_intelligence:analysis:enhanced'
                }]
                
                # Mock router routing the strand
                mock_route.return_value = True
                
                # Router monitors strands
                monitored_strands = await self.central_router.monitor_strands()
                
                # Verify router found the strand
                assert len(monitored_strands) == 1
                assert monitored_strands[0]['source_agent'] == 'raw_data_intelligence'
                
                # Router routes the strand
                routing_result = await self.central_router.route_agent_communication(monitored_strands[0])
                
                # Verify routing was successful
                assert routing_result is True
        
        # Step 3: Verify the complete flow worked
        self.logger.info("✅ Complete agent-router flow test passed")
    
    async def test_llm_controlled_parameter_management(self):
        """Test LLM-controlled parameter management in real scenarios"""
        self.logger.info("Testing LLM-controlled parameter management...")
        
        # Test LLM configuration of divergence detection
        market_conditions = {'volatility': 'high', 'trend': 'bullish'}
        performance_data = {'accuracy': 0.8, 'precision': 0.75}
        
        # Mock LLM client for divergence configuration
        self.mock_llm_client.optimize_divergence_detection = AsyncMock(return_value={
            'optimized_config': {'threshold': 0.12, 'lookback_period': 30},
            'reasoning': 'Market showing increased volatility',
            'confidence': 0.85
        })
        
        # Test LLM configuration
        config_result = await self.enhanced_agent.llm_configure_divergence_detection(market_conditions, performance_data)
        
        # Verify configuration was successful
        assert 'optimized_config' in config_result
        assert config_result['optimized_config']['threshold'] == 0.12
        assert config_result['optimized_config']['lookback_period'] == 30
        
        # Verify parameters were actually updated in the agent
        assert self.enhanced_agent.divergence_detector.threshold == 0.12
        assert self.enhanced_agent.divergence_detector.lookback_period == 30
        
        # Verify LLM client was called
        self.mock_llm_client.optimize_divergence_detection.assert_called_once()
        
        self.logger.info("✅ LLM-controlled parameter management test passed")
    
    async def test_error_handling_integration(self):
        """Test error handling in the integrated system"""
        self.logger.info("Testing error handling in integration...")
        
        # Test agent error handling
        with patch.object(self.enhanced_agent.context_system, 'get_relevant_context', new_callable=AsyncMock) as mock_context:
            mock_context.side_effect = Exception("Database error")
            
            # Agent should handle context error gracefully
            context = await self.enhanced_agent.get_context('test', self.sample_data)
            
            # Verify error handling
            assert 'error' in context
            assert context['error'] == "Database error"
        
        # Test router error handling
        with patch.object(self.central_router, 'monitor_strands', new_callable=AsyncMock) as mock_monitor:
            mock_monitor.side_effect = Exception("Router error")
            
            try:
                await self.central_router.monitor_strands()
                assert False, "Should have raised an exception"
            except Exception as e:
                assert str(e) == "Router error"
        
        self.logger.info("✅ Error handling integration test passed")
    
    async def run_all_tests(self):
        """Run all integration tests"""
        self.logger.info("🚀 Starting Agent-Router Integration Tests")
        
        try:
            await self.test_agent_registration_with_router()
            await self.test_agent_strand_creation_and_routing()
            await self.test_agent_communication_protocol()
            await self.test_agent_discovery_system()
            await self.test_complete_agent_router_flow()
            await self.test_llm_controlled_parameter_management()
            await self.test_error_handling_integration()
            
            self.logger.info("🎉 All integration tests passed! Agent-Router connection is working correctly.")
            
        except Exception as e:
            self.logger.error(f"❌ Integration test failed: {e}")
            raise


async def main():
    """Main test runner"""
    test_suite = TestAgentRouterIntegration()
    test_suite.setup_method()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

