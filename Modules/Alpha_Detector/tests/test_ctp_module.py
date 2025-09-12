#!/usr/bin/env python3
"""
Test CTP Module

Simple test to verify CTP module components work correctly.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager
from src.intelligence.llm_integration.llm_client import MockLLMClient
from src.intelligence.conditional_trading_planner import ConditionalTradingPlannerAgent


async def test_ctp_module():
    """Test CTP module initialization and basic functionality."""
    
    print("🧪 TESTING CTP MODULE")
    print("=" * 50)
    
    try:
        # Initialize dependencies
        print("📊 Initializing dependencies...")
        supabase_manager = SupabaseManager()
        llm_client = MockLLMClient()
        
        # Initialize CTP agent
        print("🤖 Initializing CTP Agent...")
        ctp_agent = ConditionalTradingPlannerAgent(supabase_manager, llm_client)
        
        # Test system status
        print("📈 Getting system status...")
        status = await ctp_agent.get_system_status()
        print(f"✅ System Status: {status['status']}")
        print(f"📊 Statistics: {status.get('statistics', {})}")
        
        # Test learning insights
        print("🧠 Getting learning insights...")
        insights = await ctp_agent.get_learning_insights()
        print(f"✅ Found {len(insights)} learning insights")
        
        print("\n🎉 CTP MODULE TEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"❌ CTP MODULE TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ctp_module())
    sys.exit(0 if success else 1)
