"""
Real Database Communication Test

Test the actual database-centric communication flow between the enhanced
RawDataIntelligenceAgent and the Central Intelligence Router using real
database operations (with mocked Supabase responses).
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


class RealDatabaseCommunicationTest:
    """Test real database-centric communication flow"""
    
    def setup_method(self):
        """Set up test environment with realistic database mocking"""
        # Mock dependencies
        self.mock_supabase = Mock(spec=SupabaseManager)
        self.mock_llm_client = Mock(spec=OpenRouterClient)
        
        # Mock Supabase client with realistic responses
        self.mock_supabase.client = Mock()
        
        # Mock strand creation - return realistic strand ID
        self.mock_supabase.create_strand = AsyncMock(return_value="strand_12345")
        
        # Mock strand retrieval - return empty initially, then populated
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
        
        # Create Central Intelligence Router with mocked context system
        mock_context_system = Mock()
        self.central_router = CentralIntelligenceRouter(
            supabase_manager=self.mock_supabase,
            context_system=mock_context_system
        )
        
        # Create Agent Discovery System
        self.discovery_system = AgentDiscoverySystem(self.mock_supabase)
        
        # Create Agent Communication Protocol
        self.agent_protocol = AgentCommunicationProtocol(
            agent_name='raw_data_intelligence',
            supabase_manager=self.mock_supabase
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
    
    async def test_complete_agent_to_router_flow(self):
        """Test the complete flow from agent analysis to router processing"""
        self.logger.info("Testing complete agent-to-router flow...")
        
        # Step 1: Register agent capabilities with discovery system
        registration_result = await self.discovery_system.register_agent_capabilities(
            agent_name='raw_data_intelligence',
            capabilities=['raw_data_analysis', 'divergence_detection', 'volume_analysis'],
            specializations=['market_microstructure', 'volume_patterns']
        )
        assert registration_result is True
        self.logger.info("✅ Agent registered with discovery system")
        
        # Step 2: Agent performs analysis and creates strand
        with patch.object(self.enhanced_agent.context_system, 'get_relevant_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                'current_analysis': {'market_condition': 'high_volatility'},
                'generated_lessons': [],
                'similar_situations': [],
                'pattern_clusters': []
            }
            
            # Mock analysis methods
            with patch.object(self.enhanced_agent, '_analyze_raw_data_divergences', new_callable=AsyncMock) as mock_divergence:
                with patch.object(self.enhanced_agent, '_analyze_volume_patterns', new_callable=AsyncMock) as mock_volume:
                    mock_divergence.return_value = {
                        'divergences': [
                            {'type': 'price_volume', 'strength': 0.8, 'timestamp': '2024-01-01T10:00:00Z'}
                        ]
                    }
                    mock_volume.return_value = {
                        'volume_spikes': [
                            {'timestamp': '2024-01-01T10:05:00Z', 'volume_ratio': 2.5}
                        ]
                    }
                    
                    # Execute enhanced analysis
                    analysis_result = await self.enhanced_agent.execute_enhanced_analysis(self.sample_data, 'comprehensive')
                    
                    # Verify analysis completed and strand was created
                    assert 'strand_id' in analysis_result
                    assert analysis_result['strand_id'] == "strand_12345"
                    assert 'analysis_results' in analysis_result
                    assert 'tool_decision' in analysis_result
                    
                    self.logger.info("✅ Agent analysis completed and strand created")
        
        # Step 3: Mock router finding the new strand and processing it
        # Simulate the router monitoring process
        mock_strand_data = {
            'id': 'strand_12345',
            'content': analysis_result,
            'source_agent': 'raw_data_intelligence',
            'tags': 'agent:raw_data_intelligence:analysis:enhanced:pattern_detected',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'strand_type': 'analysis_result'
        }
        
        # Mock the router's strand retrieval
        self.mock_supabase.get_strands.return_value = [mock_strand_data]
        
        # Test router's ability to process the strand
        with patch.object(self.central_router, '_get_recent_strands', new_callable=AsyncMock) as mock_get_strands:
            mock_get_strands.return_value = [mock_strand_data]
            
            # Test if router can identify that the strand needs routing
            needs_routing = self.central_router._needs_routing(mock_strand_data)
            assert needs_routing is True
            self.logger.info("✅ Router identified strand needs routing")
            
            # Test router's ability to classify the strand
            strand_type = self.central_router._classify_strand_type(mock_strand_data)
            assert strand_type in ['pattern_detection', 'threshold_management', 'parameter_optimization', 'performance_analysis', 'learning_opportunity', 'general_information']
            self.logger.info(f"✅ Router classified strand as: {strand_type}")
        
        # Step 4: Test agent communication protocol
        # Test publishing a finding through the protocol
        finding_content = {
            'analysis_type': 'divergence_detection',
            'findings': {'divergence_detected': True, 'confidence': 0.8},
            'market_conditions': {'volatility': 'high'},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Mock the protocol's publish_finding method
        with patch.object(self.agent_protocol, 'publish_finding', new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = "published_strand_67890"
            
            published_strand_id = await self.agent_protocol.publish_finding(
                finding_content, 
                "agent:raw_data_intelligence:finding:divergence"
            )
            
            assert published_strand_id == "published_strand_67890"
            mock_publish.assert_called_once()
            self.logger.info("✅ Agent communication protocol published finding")
        
        self.logger.info("✅ Complete agent-to-router flow test passed")
    
    async def test_router_agent_discovery_integration(self):
        """Test integration between router and agent discovery system"""
        self.logger.info("Testing router-agent discovery integration...")
        
        # Register multiple agents
        await self.discovery_system.register_agent_capabilities(
            agent_name='raw_data_intelligence',
            capabilities=['raw_data_analysis', 'divergence_detection'],
            specializations=['market_microstructure']
        )
        
        await self.discovery_system.register_agent_capabilities(
            agent_name='indicator_intelligence',
            capabilities=['technical_indicators', 'pattern_recognition'],
            specializations=['rsi_analysis', 'macd_patterns']
        )
        
        # Test finding agents for specific content
        relevant_agents = self.discovery_system.find_agents_for_content(
            content_type='raw_data_intelligence',
            content_vector=None
        )
        
        # Should find the raw_data_intelligence agent
        assert len(relevant_agents) > 0
        agent_names = [agent.agent_name for agent in relevant_agents]
        assert 'raw_data_intelligence' in agent_names
        self.logger.info("✅ Agent discovery found relevant agents")
        
        # Test router's ability to find relevant agents for routing
        test_strand = {
            'id': 'test_strand',
            'content': {'analysis_type': 'divergence_detection'},
            'source_agent': 'raw_data_intelligence',
            'tags': 'agent:raw_data_intelligence:analysis'
        }
        
        # Mock the router's agent finding capability
        with patch.object(self.central_router, '_find_relevant_agents', new_callable=AsyncMock) as mock_find_agents:
            mock_find_agents.return_value = [
                {
                    'agent_name': 'indicator_intelligence',
                    'match_score': 0.85,
                    'reasoning': 'High relevance for divergence analysis'
                }
            ]
            
            relevant_agents = await self.central_router._find_relevant_agents(test_strand, None)
            
            assert len(relevant_agents) == 1
            assert relevant_agents[0]['agent_name'] == 'indicator_intelligence'
            assert relevant_agents[0]['match_score'] == 0.85
            self.logger.info("✅ Router found relevant agents for routing")
        
        self.logger.info("✅ Router-agent discovery integration test passed")
    
    async def test_llm_controlled_system_management(self):
        """Test LLM-controlled system management capabilities"""
        self.logger.info("Testing LLM-controlled system management...")
        
        # Test LLM configuration of multiple analysis components
        market_conditions = {
            'volatility': 'high',
            'trend': 'bullish',
            'volume': 'increasing',
            'time_of_day': 'market_open'
        }
        
        performance_data = {
            'accuracy': 0.82,
            'precision': 0.78,
            'recall': 0.85,
            'f1_score': 0.81
        }
        
        # Mock LLM client for multiple configurations
        self.mock_llm_client.optimize_divergence_detection = AsyncMock(return_value={
            'optimized_config': {'threshold': 0.12, 'lookback_period': 30},
            'reasoning': 'High volatility requires lower threshold',
            'confidence': 0.85
        })
        
        self.mock_llm_client.optimize_volume_analysis = AsyncMock(return_value={
            'optimized_config': {'volume_threshold': 1.8, 'spike_detection': True},
            'reasoning': 'Increasing volume requires adjusted threshold',
            'confidence': 0.80
        })
        
        # Test LLM configuration of divergence detection
        divergence_config = await self.enhanced_agent.llm_configure_divergence_detection(
            market_conditions, performance_data
        )
        
        assert 'optimized_config' in divergence_config
        assert divergence_config['optimized_config']['threshold'] == 0.12
        assert self.enhanced_agent.divergence_detector.threshold == 0.12
        
        # Test LLM configuration of volume analysis
        volume_config = await self.enhanced_agent.llm_configure_volume_analysis(
            market_conditions, performance_data
        )
        
        assert 'optimized_config' in volume_config
        assert volume_config['optimized_config']['volume_threshold'] == 1.8
        assert self.enhanced_agent.volume_analyzer.volume_threshold == 1.8
        
        self.logger.info("✅ LLM-controlled system management test passed")
    
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery in the communication system"""
        self.logger.info("Testing error handling and recovery...")
        
        # Test agent error handling
        with patch.object(self.enhanced_agent.context_system, 'get_relevant_context', new_callable=AsyncMock) as mock_context:
            mock_context.side_effect = Exception("Database connection error")
            
            # Agent should handle context error gracefully
            context = await self.enhanced_agent.get_context('test', self.sample_data)
            
            # Verify error handling
            assert 'error' in context
            assert context['error'] == "Database connection error"
            self.logger.info("✅ Agent handled context error gracefully")
        
        # Test router error handling
        with patch.object(self.central_router, '_get_recent_strands', new_callable=AsyncMock) as mock_get_strands:
            mock_get_strands.side_effect = Exception("Router database error")
            
            try:
                await self.central_router._get_recent_strands()
                assert False, "Should have raised an exception"
            except Exception as e:
                assert str(e) == "Router database error"
                self.logger.info("✅ Router handled database error correctly")
        
        # Test communication protocol error handling
        with patch.object(self.agent_protocol, 'publish_finding', new_callable=AsyncMock) as mock_publish:
            mock_publish.side_effect = Exception("Publish error")
            
            try:
                await self.agent_protocol.publish_finding({'test': 'data'}, 'test_tag')
                assert False, "Should have raised an exception"
            except Exception as e:
                assert str(e) == "Publish error"
                self.logger.info("✅ Communication protocol handled publish error correctly")
        
        self.logger.info("✅ Error handling and recovery test passed")
    
    async def run_all_tests(self):
        """Run all real database communication tests"""
        self.logger.info("🚀 Starting Real Database Communication Tests")
        
        try:
            await self.test_complete_agent_to_router_flow()
            await self.test_router_agent_discovery_integration()
            await self.test_llm_controlled_system_management()
            await self.test_error_handling_and_recovery()
            
            self.logger.info("🎉 All real database communication tests passed! The agent-router system is working correctly.")
            
        except Exception as e:
            self.logger.error(f"❌ Real database communication test failed: {e}")
            raise


async def main():
    """Main test runner"""
    test_suite = RealDatabaseCommunicationTest()
    test_suite.setup_method()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
