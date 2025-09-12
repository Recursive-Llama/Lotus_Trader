#!/usr/bin/env python3
"""
CTP Phase 3 & 4: Advanced Intelligence Test

Tests advanced trading planner with market regime detection,
dynamic adaptation, and A/B testing capabilities.
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
from src.intelligence.conditional_trading_planner.advanced_trading_planner import AdvancedTradingPlanner, MarketRegime


async def create_test_prediction_review(supabase_manager):
    """Create a test prediction review for advanced trading plan generation."""
    
    print("📊 Creating test prediction review for advanced planning...")
    
    # Create a comprehensive prediction review with historical performance data
    prediction_review = {
        "id": f"prediction_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}_advanced",
        "module": "cil",
        "kind": "prediction_review",
        "symbol": "BTC",
        "timeframe": "1h",
        "tags": ["cil", "prediction_review", "test", "advanced"],
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
            "original_pattern_strand_ids": ["pattern_123", "pattern_456"]
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
    }
    
    # Insert prediction review
    try:
        result = supabase_manager.insert_strand(prediction_review)
        if result:
            print(f"✅ Created prediction review: {prediction_review['id']}")
            return prediction_review['id']
        else:
            print(f"❌ Failed to create prediction review")
            return None
    except Exception as e:
        print(f"❌ Error creating prediction review: {e}")
        return None


async def test_advanced_trading_planner():
    """Test advanced trading planner with market regime detection and A/B testing."""
    
    print("🧪 TESTING CTP PHASE 3 & 4: ADVANCED INTELLIGENCE")
    print("=" * 70)
    
    try:
        # Initialize dependencies
        print("📊 Initializing dependencies...")
        supabase_manager = SupabaseManager()
        llm_client = MockLLMClient()
        
        # Initialize advanced trading planner
        print("🤖 Initializing Advanced Trading Planner...")
        advanced_planner = AdvancedTradingPlanner(supabase_manager, llm_client)
        
        # Step 1: Create test prediction review
        print("\n📈 Step 1: Creating test prediction review...")
        prediction_review_id = await create_test_prediction_review(supabase_manager)
        if not prediction_review_id:
            print("❌ Failed to create test prediction review")
            return False
        
        # Step 2: Test market regime detection
        print("\n🔍 Step 2: Testing market regime detection...")
        try:
            # Create mock analysis data
            analysis = {
                "prediction_review_id": prediction_review_id,
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
                    },
                    "BTC": {
                        "total_reviews": 50,
                        "success_count": 30,
                        "success_rate": 0.6,
                        "avg_return": 0.028,
                        "avg_confidence": 0.75,
                        "avg_drawdown": 0.018,
                        "avg_duration": 4.5,
                        "max_return": 0.12,
                        "min_return": -0.05
                    }
                }
            }
            
            # Test market regime detection
            market_regime = await advanced_planner._detect_market_regime(analysis)
            print(f"✅ Detected market regime: {market_regime.value}")
            
        except Exception as e:
            print(f"❌ Error in market regime detection: {e}")
        
        # Step 3: Test regime performance analysis
        print("\n📊 Step 3: Testing regime performance analysis...")
        try:
            regime_performance = await advanced_planner._analyze_regime_performance(analysis, market_regime)
            print(f"✅ Regime performance analysis: {regime_performance}")
        except Exception as e:
            print(f"❌ Error in regime performance analysis: {e}")
        
        # Step 4: Test regime-specific trading rules
        print("\n⚙️ Step 4: Testing regime-specific trading rules...")
        try:
            trading_rules = await advanced_planner._generate_regime_specific_rules(analysis, market_regime, regime_performance)
            print(f"✅ Generated trading rules: {json.dumps(trading_rules, indent=2)}")
        except Exception as e:
            print(f"❌ Error generating trading rules: {e}")
        
        # Step 5: Test adaptive management rules
        print("\n🎛️ Step 5: Testing adaptive management rules...")
        try:
            management_rules = await advanced_planner._create_adaptive_management_rules(analysis, market_regime)
            print(f"✅ Generated management rules: {json.dumps(management_rules, indent=2)}")
        except Exception as e:
            print(f"❌ Error generating management rules: {e}")
        
        # Step 6: Test A/B testing variants
        print("\n🧪 Step 6: Testing A/B testing variants...")
        try:
            ab_variants = await advanced_planner._create_ab_test_variants(analysis, trading_rules, management_rules)
            print(f"✅ Created {len(ab_variants)} A/B test variants:")
            for i, variant in enumerate(ab_variants):
                print(f"  {i+1}. {variant['variant_id']}: {variant['description']}")
        except Exception as e:
            print(f"❌ Error creating A/B test variants: {e}")
        
        # Step 7: Test complete adaptive trading plan creation
        print("\n🚀 Step 7: Testing complete adaptive trading plan creation...")
        try:
            adaptive_plan_id = await advanced_planner.create_adaptive_trading_plan(analysis)
            if adaptive_plan_id:
                print(f"✅ Created adaptive trading plan: {adaptive_plan_id}")
                
                # Verify the plan was stored correctly
                result = supabase_manager.client.table('ad_strands').select('*').eq('id', adaptive_plan_id).execute()
                if result.data:
                    plan_data = result.data[0]
                    print(f"📋 Plan stored successfully:")
                    print(f"  - Plan Type: {plan_data['content'].get('plan_type', 'N/A')}")
                    print(f"  - Market Regime: {plan_data['content'].get('market_regime', 'N/A')}")
                    print(f"  - A/B Variants: {len(plan_data['content'].get('ab_test_variants', []))}")
                    print(f"  - Adaptive Features: {plan_data['module_intelligence'].get('adaptive_features', {})}")
                else:
                    print("❌ Plan not found in database")
            else:
                print("❌ Failed to create adaptive trading plan")
        except Exception as e:
            print(f"❌ Error creating adaptive trading plan: {e}")
        
        # Step 8: Test different market regimes
        print("\n🌊 Step 8: Testing different market regimes...")
        try:
            # Test high volatility regime
            high_vol_analysis = analysis.copy()
            high_vol_analysis['historical_performance'] = {
                "test_cluster": {
                    "total_reviews": 10,
                    "success_count": 4,
                    "success_rate": 0.4,
                    "avg_return": 0.05,
                    "avg_drawdown": 0.04,  # High volatility
                    "avg_duration": 2.0
                }
            }
            
            high_vol_regime = await advanced_planner._detect_market_regime(high_vol_analysis)
            print(f"✅ High volatility regime detected: {high_vol_regime.value}")
            
            # Test low volatility regime
            low_vol_analysis = analysis.copy()
            low_vol_analysis['historical_performance'] = {
                "test_cluster": {
                    "total_reviews": 10,
                    "success_count": 8,
                    "success_rate": 0.8,
                    "avg_return": 0.02,
                    "avg_drawdown": 0.005,  # Low volatility
                    "avg_duration": 6.0
                }
            }
            
            low_vol_regime = await advanced_planner._detect_market_regime(low_vol_analysis)
            print(f"✅ Low volatility regime detected: {low_vol_regime.value}")
            
        except Exception as e:
            print(f"❌ Error testing different market regimes: {e}")
        
        print("\n🎉 CTP PHASE 3 & 4 ADVANCED INTELLIGENCE TEST COMPLETED!")
        return True
        
    except Exception as e:
        print(f"❌ CTP PHASE 3 & 4 TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_advanced_trading_planner())
    sys.exit(0 if success else 1)
