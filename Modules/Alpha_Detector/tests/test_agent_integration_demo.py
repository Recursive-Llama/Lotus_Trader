"""
Agent Integration Demo

This demonstrates how the Central Intelligence Router system would work
with actual LLM agents in a real scenario.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock

# Import the components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from llm_integration.central_intelligence_router import CentralIntelligenceRouter
from llm_integration.agent_communication_protocol import AgentCommunicationProtocol
from llm_integration.agent_discovery_system import AgentDiscoverySystem
from llm_integration.tag_conventions import TagConventionSystem
from utils.supabase_manager import SupabaseManager


class MockLLMAgent:
    """Mock LLM Agent for demonstration"""
    
    def __init__(self, name: str, capabilities: list, specializations: list):
        self.name = name
        self.capabilities = capabilities
        self.specializations = specializations
        self.communication_protocol = None
        self.is_running = False
    
    async def start(self, supabase_manager, discovery_system):
        """Start the agent"""
        # Create communication protocol
        self.communication_protocol = AgentCommunicationProtocol(self.name, supabase_manager)
        
        # Register capabilities
        await discovery_system.register_agent_capabilities(
            self.name, self.capabilities, self.specializations
        )
        
        # Start listening for messages
        self.communication_protocol.start_listening()
        self.is_running = True
        
        print(f"🤖 Agent '{self.name}' started with capabilities: {self.capabilities}")
    
    async def publish_finding(self, content: dict, tags: str = None):
        """Publish a finding"""
        if self.communication_protocol:
            message_id = await self.communication_protocol.publish_finding(content, tags)
            print(f"📤 Agent '{self.name}' published finding: {message_id}")
            return message_id
        return None
    
    async def stop(self):
        """Stop the agent"""
        if self.communication_protocol:
            self.communication_protocol.stop_listening()
        self.is_running = False
        print(f"🛑 Agent '{self.name}' stopped")


async def demo_agent_integration():
    """Demonstrate how agents would actually interact"""
    
    print("🚀 Starting Agent Integration Demo...")
    print("=" * 60)
    
    # Create mock Supabase manager
    mock_supabase = Mock(spec=SupabaseManager)
    mock_supabase.client = Mock()
    mock_supabase.client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "demo_id"}]
    mock_supabase.client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    mock_supabase.client.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "demo_id"}]
    
    # Create mock context system
    mock_context_system = Mock()
    
    # Create the central intelligence system
    discovery_system = AgentDiscoverySystem(mock_supabase)
    router = CentralIntelligenceRouter(mock_supabase, mock_context_system)
    tag_system = TagConventionSystem()
    
    print("\n📋 Step 1: Creating LLM Agents")
    print("-" * 40)
    
    # Create mock LLM agents
    pattern_detector = MockLLMAgent(
        "pattern_detector",
        ["pattern_detection", "signal_detection", "technical_analysis"],
        ["rsi_analysis", "macd_analysis", "bollinger_analysis"]
    )
    
    threshold_manager = MockLLMAgent(
        "threshold_manager", 
        ["threshold_management", "parameter_control", "system_control"],
        ["signal_thresholds", "confidence_thresholds", "risk_thresholds"]
    )
    
    raw_data_intelligence = MockLLMAgent(
        "raw_data_intelligence",
        ["raw_data_analysis", "market_microstructure", "volume_analysis"],
        ["ohlcv_patterns", "volume_spikes", "time_based_patterns"]
    )
    
    print("\n🚀 Step 2: Starting Agents")
    print("-" * 40)
    
    # Start all agents
    await pattern_detector.start(mock_supabase, discovery_system)
    await threshold_manager.start(mock_supabase, discovery_system)
    await raw_data_intelligence.start(mock_supabase, discovery_system)
    
    print("\n📊 Step 3: Agent Discovery System Status")
    print("-" * 40)
    
    # Check agent status
    agent_status = discovery_system.get_agent_status()
    print(f"Registered agents: {len(agent_status)}")
    for agent_name, status in agent_status.items():
        print(f"  🤖 {agent_name}: {status['capabilities']}")
    
    print("\n💬 Step 4: Agent Communication Demo")
    print("-" * 40)
    
    # Simulate agent communication
    print("🔍 Raw Data Intelligence detects a pattern...")
    await raw_data_intelligence.publish_finding({
        "pattern_type": "volume_spike",
        "symbol": "BTC",
        "confidence": 0.85,
        "details": "Unusual volume spike detected at 14:30 UTC"
    }, "intelligence:raw_data:pattern_detected:volume_spike")
    
    print("\n📈 Pattern Detector analyzes the data...")
    await pattern_detector.publish_finding({
        "pattern_type": "rsi_divergence",
        "symbol": "BTC", 
        "confidence": 0.78,
        "details": "Bullish RSI divergence detected"
    }, "intelligence:indicator:pattern_detected:rsi_divergence")
    
    print("\n⚙️ Pattern Detector requests threshold analysis...")
    await pattern_detector.communication_protocol.tag_other_agent(
        target_agent="threshold_manager",
        content={
            "request_type": "threshold_analysis",
            "pattern_confidence": 0.78,
            "suggested_threshold": 0.75
        },
        action_type="threshold_analysis"
    )
    
    print("\n🎯 Step 5: Central Router Capabilities")
    print("-" * 40)
    
    # Register agents with router
    router.register_agent_capabilities(
        "pattern_detector",
        ["pattern_detection", "signal_detection", "technical_analysis"],
        ["rsi_analysis", "macd_analysis", "bollinger_analysis"]
    )
    
    router.register_agent_capabilities(
        "threshold_manager",
        ["threshold_management", "parameter_control", "system_control"],
        ["signal_thresholds", "confidence_thresholds", "risk_thresholds"]
    )
    
    router.register_agent_capabilities(
        "raw_data_intelligence",
        ["raw_data_analysis", "market_microstructure", "volume_analysis"],
        ["ohlcv_patterns", "volume_spikes", "time_based_patterns"]
    )
    
    # Check router status
    router_stats = router.get_routing_stats()
    print(f"Router monitoring: {router_stats['is_monitoring']}")
    print(f"Active agents: {router_stats['active_agents']}")
    print(f"Total agents: {router_stats['total_agents']}")
    
    print("\n🏷️ Step 6: Tag System Demo")
    print("-" * 40)
    
    # Create and parse tags
    routing_tag = tag_system.create_agent_routing_tag(
        target_agent="threshold_manager",
        source_strand_id="strand_123",
        routing_reason="pattern_detected",
        priority="high"
    )
    
    direct_tag = tag_system.create_agent_direct_tag(
        target_agent="pattern_detector",
        action_type="threshold_analysis",
        source_agent="raw_data_intelligence"
    )
    
    print(f"Routing tag: {routing_tag}")
    print(f"Direct tag: {direct_tag}")
    
    # Parse tags
    parsed_routing = tag_system.parse_tag(routing_tag)
    parsed_direct = tag_system.parse_tag(direct_tag)
    
    print(f"Parsed routing: {parsed_routing}")
    print(f"Parsed direct: {parsed_direct}")
    
    print("\n🛑 Step 7: Stopping Agents")
    print("-" * 40)
    
    # Stop all agents
    await pattern_detector.stop()
    await threshold_manager.stop()
    await raw_data_intelligence.stop()
    
    print("\n✅ Agent Integration Demo Complete!")
    print("=" * 60)
    print("\n📊 What This Demo Showed:")
    print("  ✅ Agent creation and capability registration")
    print("  ✅ Agent communication through database")
    print("  ✅ Central router agent management")
    print("  ✅ Tag-based message routing")
    print("  ✅ Agent discovery and capability mapping")
    print("\n🎯 Next Steps for Full Integration:")
    print("  🔄 Connect to real Supabase database")
    print("  🔄 Implement actual LLM agents with real capabilities")
    print("  🔄 Start the Central Router monitoring")
    print("  🔄 Integrate with existing Core Detection Engine")
    print("  🔄 Add real-time message processing")


if __name__ == "__main__":
    asyncio.run(demo_agent_integration())
