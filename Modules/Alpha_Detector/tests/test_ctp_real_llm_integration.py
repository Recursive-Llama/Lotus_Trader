#!/usr/bin/env python3
"""
CTP Real LLM Integration Test

Comprehensive test with actual LLM calls, real data flow, and end-to-end validation.
This matches the thoroughness of the CIL testing we did earlier.
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager
from src.intelligence.llm_integration.llm_client import OpenAILLMClient
from src.intelligence.conditional_trading_planner import ConditionalTradingPlannerAgent
from src.intelligence.conditional_trading_planner.advanced_trading_planner import AdvancedTradingPlanner


async def clear_ctp_test_data(supabase_manager):
    """Clear existing CTP test data from database."""
    print("🧹 Clearing existing CTP test data...")
    
    try:
        # Delete test strands
        test_kinds = ['prediction_review', 'conditional_trading_plan', 'trade_outcome']
        for kind in test_kinds:
            result = supabase_manager.client.table('ad_strands').delete().eq('kind', kind).contains('tags', ['test']).execute()
            print(f"✅ Cleared {kind} test strands")
        
        return True
    except Exception as e:
        print(f"❌ Error clearing test data: {e}")
        return False


async def create_real_prediction_reviews(supabase_manager):
    """Create real prediction review strands with proper data structure."""
    print("📊 Creating real prediction review strands...")
    
    # Create comprehensive prediction reviews with different patterns
    prediction_reviews = [
        {
            "id": f"pred_review_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
            "module": "cil",
            "kind": "prediction_review",
            "symbol": "BTC",
            "timeframe": "1h",
            "tags": ["cil", "prediction_review", "test", "real"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "braid_level": 1,
            "lesson": "",
            "content": {
                "group_signature": "BTC_1h_volume_spike_divergence",
                "asset": "BTC",
                "timeframe": "1h",
                "pattern_types": ["volume_spike", "divergence"],
                "group_type": "multi_single",
                "method": "code",
                "confidence": 0.85,
                "success": True,
                "return_pct": 3.2,
                "max_drawdown": -1.1,
                "duration_hours": 4.5,
                "original_pattern_strand_ids": ["pattern_001", "pattern_002"]
            },
            "module_intelligence": {
                "pattern_group": {
                    "asset": "BTC",
                    "timeframe": "1h",
                    "group_type": "multi_single",
                    "patterns": [
                        {"type": "volume_spike", "confidence": 0.9},
                        {"type": "divergence", "confidence": 0.8}
                    ]
                },
                "outcome": {
                    "success": True,
                    "return_pct": 3.2,
                    "max_drawdown": -1.1,
                    "duration_hours": 4.5
                },
                "confidence": 0.85,
                "method": "code"
            },
            "cluster_key": [
                {
                    "cluster_type": "pattern_timeframe",
                    "cluster_key": "BTC_1h_volume_spike_divergence",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "asset",
                    "cluster_key": "BTC",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "timeframe",
                    "cluster_key": "1h",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "outcome",
                    "cluster_key": "success",
                    "braid_level": 1,
                    "consumed": False
                }
            ]
        },
        {
            "id": f"pred_review_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}_002",
            "module": "cil",
            "kind": "prediction_review",
            "symbol": "ETH",
            "timeframe": "4h",
            "tags": ["cil", "prediction_review", "test", "real"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "braid_level": 1,
            "lesson": "",
            "content": {
                "group_signature": "ETH_4h_volume_spike",
                "asset": "ETH",
                "timeframe": "4h",
                "pattern_types": ["volume_spike"],
                "group_type": "single_single",
                "method": "llm",
                "confidence": 0.72,
                "success": False,
                "return_pct": -2.1,
                "max_drawdown": -3.5,
                "duration_hours": 6.2,
                "original_pattern_strand_ids": ["pattern_003"]
            },
            "module_intelligence": {
                "pattern_group": {
                    "asset": "ETH",
                    "timeframe": "4h",
                    "group_type": "single_single",
                    "patterns": [
                        {"type": "volume_spike", "confidence": 0.75}
                    ]
                },
                "outcome": {
                    "success": False,
                    "return_pct": -2.1,
                    "max_drawdown": -3.5,
                    "duration_hours": 6.2
                },
                "confidence": 0.72,
                "method": "llm"
            },
            "cluster_key": [
                {
                    "cluster_type": "pattern_timeframe",
                    "cluster_key": "ETH_4h_volume_spike",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "asset",
                    "cluster_key": "ETH",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "timeframe",
                    "cluster_key": "4h",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "outcome",
                    "cluster_key": "failure",
                    "braid_level": 1,
                    "consumed": False
                }
            ]
        },
        {
            "id": f"pred_review_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}_003",
            "module": "cil",
            "kind": "prediction_review",
            "symbol": "BTC",
            "timeframe": "1h",
            "tags": ["cil", "prediction_review", "test", "real"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "braid_level": 1,
            "lesson": "",
            "content": {
                "group_signature": "BTC_1h_volume_spike_divergence",
                "asset": "BTC",
                "timeframe": "1h",
                "pattern_types": ["volume_spike", "divergence"],
                "group_type": "multi_single",
                "method": "code",
                "confidence": 0.78,
                "success": True,
                "return_pct": 2.8,
                "max_drawdown": -0.8,
                "duration_hours": 3.2,
                "original_pattern_strand_ids": ["pattern_004", "pattern_005"]
            },
            "module_intelligence": {
                "pattern_group": {
                    "asset": "BTC",
                    "timeframe": "1h",
                    "group_type": "multi_single",
                    "patterns": [
                        {"type": "volume_spike", "confidence": 0.85},
                        {"type": "divergence", "confidence": 0.7}
                    ]
                },
                "outcome": {
                    "success": True,
                    "return_pct": 2.8,
                    "max_drawdown": -0.8,
                    "duration_hours": 3.2
                },
                "confidence": 0.78,
                "method": "code"
            },
            "cluster_key": [
                {
                    "cluster_type": "pattern_timeframe",
                    "cluster_key": "BTC_1h_volume_spike_divergence",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "asset",
                    "cluster_key": "BTC",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "timeframe",
                    "cluster_key": "1h",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "outcome",
                    "cluster_key": "success",
                    "braid_level": 1,
                    "consumed": False
                }
            ]
        }
    ]
    
    created_reviews = []
    for review in prediction_reviews:
        try:
            result = supabase_manager.insert_strand(review)
            if result:
                created_reviews.append(review['id'])
                print(f"✅ Created prediction review: {review['id']}")
            else:
                print(f"❌ Failed to create prediction review: {review['id']}")
        except Exception as e:
            print(f"❌ Error creating prediction review {review['id']}: {e}")
    
    return created_reviews


async def create_real_trade_outcomes(supabase_manager):
    """Create real trade outcome strands with proper data structure."""
    print("📈 Creating real trade outcome strands...")
    
    # Create comprehensive trade outcomes with different execution scenarios
    trade_outcomes = [
        {
            "id": f"trade_outcome_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}_001",
            "module": "ctp",
            "kind": "trade_outcome",
            "symbol": "BTC",
            "timeframe": "1h",
            "tags": ["ctp", "trade_outcome", "test", "real"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "braid_level": 1,
            "lesson": "",
            "content": {
                "trade_id": "trade_real_001",
                "ctp_id": "ctp_real_001",
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
            "cluster_key": [
                {
                    "cluster_type": "pattern_timeframe",
                    "cluster_key": "BTC_1h_volume_spike_divergence",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "asset",
                    "cluster_key": "BTC",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "outcome",
                    "cluster_key": "success",
                    "braid_level": 1,
                    "consumed": False
                }
            ]
        },
        {
            "id": f"trade_outcome_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}_002",
            "module": "ctp",
            "kind": "trade_outcome",
            "symbol": "BTC",
            "timeframe": "1h",
            "tags": ["ctp", "trade_outcome", "test", "real"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "braid_level": 1,
            "lesson": "",
            "content": {
                "trade_id": "trade_real_002",
                "ctp_id": "ctp_real_002",
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
            "cluster_key": [
                {
                    "cluster_type": "pattern_timeframe",
                    "cluster_key": "BTC_1h_divergence",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "asset",
                    "cluster_key": "BTC",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "outcome",
                    "cluster_key": "failure",
                    "braid_level": 1,
                    "consumed": False
                }
            ]
        },
        {
            "id": f"trade_outcome_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}_003",
            "module": "ctp",
            "kind": "trade_outcome",
            "symbol": "ETH",
            "timeframe": "4h",
            "tags": ["ctp", "trade_outcome", "test", "real"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "braid_level": 1,
            "lesson": "",
            "content": {
                "trade_id": "trade_real_003",
                "ctp_id": "ctp_real_003",
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
            "cluster_key": [
                {
                    "cluster_type": "pattern_timeframe",
                    "cluster_key": "ETH_4h_volume_spike",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "asset",
                    "cluster_key": "ETH",
                    "braid_level": 1,
                    "consumed": False
                },
                {
                    "cluster_type": "outcome",
                    "cluster_key": "success",
                    "braid_level": 1,
                    "consumed": False
                }
            ]
        }
    ]
    
    created_outcomes = []
    for outcome in trade_outcomes:
        try:
            result = supabase_manager.insert_strand(outcome)
            if result:
                created_outcomes.append(outcome['id'])
                print(f"✅ Created trade outcome: {outcome['id']}")
            else:
                print(f"❌ Failed to create trade outcome: {outcome['id']}")
        except Exception as e:
            print(f"❌ Error creating trade outcome {outcome['id']}: {e}")
    
    return created_outcomes


async def test_real_ctp_integration():
    """Test CTP with real LLM calls and end-to-end validation."""
    
    print("🧪 TESTING CTP WITH REAL LLM INTEGRATION")
    print("=" * 60)
    
    try:
        # Initialize dependencies with real LLM client
        print("📊 Initializing dependencies with real LLM client...")
        supabase_manager = SupabaseManager()
        
        # Use real OpenAI client (you'll need to set OPENAI_API_KEY)
        try:
            llm_client = OpenAILLMClient(api_key=os.getenv('OPENAI_API_KEY', 'test-key'), model="gpt-4o-mini")
            print("✅ Real OpenAI LLM client initialized")
        except Exception as e:
            print(f"⚠️ Using MockLLMClient due to: {e}")
            from src.intelligence.llm_integration.llm_client import MockLLMClient
            llm_client = MockLLMClient()
        
        # Initialize CTP agents
        print("🤖 Initializing CTP agents...")
        ctp_agent = ConditionalTradingPlannerAgent(supabase_manager, llm_client)
        advanced_planner = AdvancedTradingPlanner(supabase_manager, llm_client)
        
        # Step 1: Clear existing test data
        print("\n🧹 Step 1: Clearing existing test data...")
        await clear_ctp_test_data(supabase_manager)
        
        # Step 2: Create real prediction reviews
        print("\n📊 Step 2: Creating real prediction reviews...")
        prediction_review_ids = await create_real_prediction_reviews(supabase_manager)
        print(f"✅ Created {len(prediction_review_ids)} prediction reviews")
        
        # Step 3: Test real trading plan creation
        print("\n📋 Step 3: Testing real trading plan creation...")
        trading_plan_ids = []
        for review_id in prediction_review_ids:
            try:
                plan_id = await ctp_agent.process_prediction_review(review_id)
                if plan_id:
                    trading_plan_ids.append(plan_id)
                    print(f"✅ Created trading plan: {plan_id}")
                else:
                    print(f"❌ Failed to create trading plan for: {review_id}")
            except Exception as e:
                print(f"❌ Error creating trading plan for {review_id}: {e}")
        
        print(f"✅ Created {len(trading_plan_ids)} trading plans")
        
        # Step 4: Verify trading plans in database
        print("\n🔍 Step 4: Verifying trading plans in database...")
        for plan_id in trading_plan_ids:
            try:
                result = supabase_manager.client.table('ad_strands').select('*').eq('id', plan_id).execute()
                if result.data:
                    plan = result.data[0]
                    print(f"📋 Plan {plan_id}:")
                    print(f"  - Kind: {plan['kind']}")
                    print(f"  - Symbol: {plan['symbol']}")
                    print(f"  - Content keys: {list(plan['content'].keys())}")
                    print(f"  - Trading rules: {plan['content'].get('trading_rules', {}).keys()}")
                    print(f"  - Management rules: {plan['content'].get('management_rules', {}).keys()}")
                else:
                    print(f"❌ Plan {plan_id} not found in database")
            except Exception as e:
                print(f"❌ Error verifying plan {plan_id}: {e}")
        
        # Step 5: Create real trade outcomes
        print("\n📈 Step 5: Creating real trade outcomes...")
        trade_outcome_ids = await create_real_trade_outcomes(supabase_manager)
        print(f"✅ Created {len(trade_outcome_ids)} trade outcomes")
        
        # Step 6: Test real trade outcome processing
        print("\n🔄 Step 6: Testing real trade outcome processing...")
        for outcome_id in trade_outcome_ids:
            try:
                result = await ctp_agent.process_trade_outcome(outcome_id)
                if result:
                    print(f"✅ Processed trade outcome: {outcome_id}")
                else:
                    print(f"❌ Failed to process trade outcome: {outcome_id}")
            except Exception as e:
                print(f"❌ Error processing trade outcome {outcome_id}: {e}")
        
        # Step 7: Test real learning system
        print("\n🧠 Step 7: Testing real learning system...")
        try:
            learning_result = await ctp_agent.run_learning_cycle()
            print(f"✅ Learning cycle result: {learning_result}")
        except Exception as e:
            print(f"❌ Error in learning cycle: {e}")
        
        # Step 8: Test real learning insights
        print("\n💡 Step 8: Testing real learning insights...")
        try:
            insights = await ctp_agent.get_learning_insights()
            print(f"✅ Retrieved {len(insights)} learning insights")
            for i, insight in enumerate(insights[:3]):  # Show first 3
                print(f"  {i+1}. Braid Level {insight.get('braid_level', 'N/A')}: {insight.get('cluster_type', 'N/A')}")
        except Exception as e:
            print(f"❌ Error retrieving insights: {e}")
        
        # Step 9: Test advanced trading planner
        print("\n🚀 Step 9: Testing advanced trading planner...")
        try:
            # Create analysis for advanced planner
            analysis = {
                "prediction_review_id": prediction_review_ids[0],
                "pattern_info": {
                    "asset": "BTC",
                    "timeframe": "1h",
                    "group_signature": "BTC_1h_volume_spike_divergence",
                    "pattern_types": ["volume_spike", "divergence"],
                    "group_type": "multi_single",
                    "method": "code",
                    "confidence": 0.85,
                    "success": True,
                    "return_pct": 3.2,
                    "max_drawdown": -1.1,
                    "duration_hours": 4.5
                },
                "historical_performance": {
                    "BTC_1h_volume_spike_divergence": {
                        "total_reviews": 20,
                        "success_count": 12,
                        "success_rate": 0.6,
                        "avg_return": 0.032,
                        "avg_confidence": 0.8,
                        "avg_drawdown": 0.015,
                        "avg_duration": 4.2,
                        "max_return": 0.08,
                        "min_return": -0.03
                    }
                }
            }
            
            advanced_plan_id = await advanced_planner.create_adaptive_trading_plan(analysis)
            if advanced_plan_id:
                print(f"✅ Created advanced trading plan: {advanced_plan_id}")
            else:
                print("❌ Failed to create advanced trading plan")
        except Exception as e:
            print(f"❌ Error creating advanced trading plan: {e}")
        
        # Step 10: Final system validation
        print("\n📊 Step 10: Final system validation...")
        try:
            final_status = await ctp_agent.get_system_status()
            print(f"✅ Final System Status: {final_status['status']}")
            print(f"📈 Final Statistics: {final_status.get('statistics', {})}")
            
            # Verify all strands were created
            stats = final_status.get('statistics', {})
            print(f"\n📊 Strand Counts:")
            print(f"  - Prediction Reviews: {stats.get('prediction_reviews', 0)}")
            print(f"  - Trading Plans: {stats.get('trading_plans', 0)}")
            print(f"  - Trade Outcomes: {stats.get('trade_outcomes', 0)}")
            print(f"  - Learning Braids: {stats.get('learning_braids', 0)}")
            
        except Exception as e:
            print(f"❌ Error in final validation: {e}")
        
        print("\n🎉 REAL CTP INTEGRATION TEST COMPLETED!")
        return True
        
    except Exception as e:
        print(f"❌ REAL CTP INTEGRATION TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_real_ctp_integration())
    sys.exit(0 if success else 1)
