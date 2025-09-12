#!/usr/bin/env python3
"""
CTP Phase 2: Learning Integration Test

Tests the integration of CTP with CIL learning system for trade outcome analysis.
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager
from src.intelligence.llm_integration.llm_client import MockLLMClient
from src.intelligence.conditional_trading_planner import ConditionalTradingPlannerAgent


async def create_test_trade_outcomes(supabase_manager):
    """Create test trade outcome strands for learning system testing."""
    
    print("📊 Creating test trade outcome strands...")
    
    # Create test trade outcomes with different patterns
    test_trade_outcomes = [
        {
            "id": f"trade_outcome_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
            "module": "ctp",
            "kind": "trade_outcome",
            "symbol": "BTC",
            "timeframe": "1h",
            "tags": ["ctp", "trade_outcome", "test"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "braid_level": 1,
            "lesson": "",
            "content": {
                "trade_id": "trade_001",
                "ctp_id": "ctp_001",
                "asset": "BTC",
                "timeframe": "1h",
                "entry_price": 45000.0,
                "entry_time": "2024-01-15T10:30:00Z",
                "exit_price": 46500.0,
                "exit_time": "2024-01-15T14:45:00Z",
                "stop_loss": 44100.0,
                "target_price": 46800.0,
                "position_size": 0.1,
                "execution_method": "limit_order",
                "slippage": 0.05,
                "fees": 0.1,
                "success": True,
                "return_pct": 3.33,
                "duration_hours": 4.25,
                "r_r_ratio": 1.67
            },
            "module_intelligence": {
                "trade_type": "long",
                "pattern_type": "volume_spike",
                "group_type": "multi_single",
                "method": "code"
            },
            "cluster_key": []
        },
        {
            "id": f"trade_outcome_{datetime.now().strftime('%Y%m%d_%H%M%S')}_002",
            "module": "ctp",
            "kind": "trade_outcome",
            "symbol": "BTC",
            "timeframe": "1h",
            "tags": ["ctp", "trade_outcome", "test"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "braid_level": 1,
            "lesson": "",
            "content": {
                "trade_id": "trade_002",
                "ctp_id": "ctp_002",
                "asset": "BTC",
                "timeframe": "1h",
                "entry_price": 46000.0,
                "entry_time": "2024-01-15T15:00:00Z",
                "exit_price": 44800.0,
                "exit_time": "2024-01-15T18:30:00Z",
                "stop_loss": 44100.0,
                "target_price": 48000.0,
                "position_size": 0.1,
                "execution_method": "market_order",
                "slippage": 0.15,
                "fees": 0.1,
                "success": False,
                "return_pct": -2.61,
                "duration_hours": 3.5,
                "r_r_ratio": 0.0
            },
            "module_intelligence": {
                "trade_type": "long",
                "pattern_type": "divergence",
                "group_type": "single_single",
                "method": "llm"
            },
            "cluster_key": []
        },
        {
            "id": f"trade_outcome_{datetime.now().strftime('%Y%m%d_%H%M%S')}_003",
            "module": "ctp",
            "kind": "trade_outcome",
            "symbol": "ETH",
            "timeframe": "4h",
            "tags": ["ctp", "trade_outcome", "test"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "braid_level": 1,
            "lesson": "",
            "content": {
                "trade_id": "trade_003",
                "ctp_id": "ctp_003",
                "asset": "ETH",
                "timeframe": "4h",
                "entry_price": 3200.0,
                "entry_time": "2024-01-15T12:00:00Z",
                "exit_price": 3360.0,
                "exit_time": "2024-01-15T20:00:00Z",
                "stop_loss": 3040.0,
                "target_price": 3520.0,
                "position_size": 0.2,
                "execution_method": "limit_order",
                "slippage": 0.02,
                "fees": 0.1,
                "success": True,
                "return_pct": 5.0,
                "duration_hours": 8.0,
                "r_r_ratio": 2.5
            },
            "module_intelligence": {
                "trade_type": "long",
                "pattern_type": "volume_spike",
                "group_type": "multi_single",
                "method": "code"
            },
            "cluster_key": []
        }
    ]
    
    # Insert trade outcomes into database
    for trade_outcome in test_trade_outcomes:
        try:
            result = supabase_manager.insert_strand(trade_outcome)
            if result:
                print(f"✅ Created trade outcome: {trade_outcome['id']}")
            else:
                print(f"❌ Failed to create trade outcome: {trade_outcome['id']}")
        except Exception as e:
            print(f"❌ Error creating trade outcome {trade_outcome['id']}: {e}")
    
    return len(test_trade_outcomes)


async def test_ctp_learning_integration():
    """Test CTP learning system integration with CIL components."""
    
    print("🧪 TESTING CTP PHASE 2: LEARNING INTEGRATION")
    print("=" * 60)
    
    try:
        # Initialize dependencies
        print("📊 Initializing dependencies...")
        supabase_manager = SupabaseManager()
        llm_client = MockLLMClient()
        
        # Initialize CTP agent
        print("🤖 Initializing CTP Agent...")
        ctp_agent = ConditionalTradingPlannerAgent(supabase_manager, llm_client)
        
        # Step 1: Create test trade outcomes
        print("\n📈 Step 1: Creating test trade outcomes...")
        trade_outcome_count = await create_test_trade_outcomes(supabase_manager)
        print(f"✅ Created {trade_outcome_count} test trade outcomes")
        
        # Step 2: Test learning system initialization
        print("\n🧠 Step 2: Testing learning system initialization...")
        learning_system = ctp_agent.learning_system
        print(f"✅ Learning system initialized: {type(learning_system).__name__}")
        
        # Step 3: Test cluster grouping for trade outcomes
        print("\n🔍 Step 3: Testing trade outcome clustering...")
        try:
            clusters = await learning_system._get_trade_outcome_clusters()
            print(f"✅ Found {len(clusters)} cluster types")
            for cluster_type, cluster_groups in clusters.items():
                print(f"  📊 {cluster_type}: {len(cluster_groups)} groups")
                for cluster_key, trade_outcomes in cluster_groups.items():
                    print(f"    - {cluster_key}: {len(trade_outcomes)} trade outcomes")
        except Exception as e:
            print(f"❌ Error testing clustering: {e}")
        
        # Step 4: Test learning cycle
        print("\n🔄 Step 4: Testing CTP learning cycle...")
        try:
            learning_result = await ctp_agent.run_learning_cycle()
            print(f"✅ Learning cycle completed: {learning_result}")
        except Exception as e:
            print(f"❌ Error in learning cycle: {e}")
        
        # Step 5: Test learning insights retrieval
        print("\n💡 Step 5: Testing learning insights retrieval...")
        try:
            insights = await ctp_agent.get_learning_insights()
            print(f"✅ Retrieved {len(insights)} learning insights")
            for i, insight in enumerate(insights[:3]):  # Show first 3
                print(f"  {i+1}. Braid Level {insight.get('braid_level', 'N/A')}: {insight.get('cluster_type', 'N/A')}")
        except Exception as e:
            print(f"❌ Error retrieving insights: {e}")
        
        # Step 6: Test system statistics
        print("\n📊 Step 6: Testing system statistics...")
        try:
            status = await ctp_agent.get_system_status()
            print(f"✅ System status: {status['status']}")
            print(f"📈 Statistics: {status.get('statistics', {})}")
        except Exception as e:
            print(f"❌ Error getting system status: {e}")
        
        print("\n🎉 CTP PHASE 2 LEARNING INTEGRATION TEST COMPLETED!")
        return True
        
    except Exception as e:
        print(f"❌ CTP PHASE 2 TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ctp_learning_integration())
    sys.exit(0 if success else 1)
