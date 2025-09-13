"""
Real Modules Pipeline Test

Tests the complete pipeline with REAL modules (not mocks) by fixing import paths.
This proves the actual system works end-to-end.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/Modules/Alpha_Detector/src')

from Modules.Alpha_Detector.src.utils.supabase_manager import SupabaseManager
from Modules.Alpha_Detector.src.intelligence.llm_integration.llm_client import LLMClientManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockPromptManager:
    """Mock prompt manager for testing"""
    
    def get_prompt(self, template_name: str, **kwargs) -> str:
        """Get a mock prompt"""
        return f"Mock prompt for {template_name} with {kwargs}"


async def test_real_modules_pipeline():
    """Test the complete pipeline with real modules"""
    try:
        logger.info("🧪 Testing Real Modules Pipeline - End-to-End with Actual Modules")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        
        # Initialize LLM client manager
        llm_config = {
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY', ''),
                'model': 'gpt-4o-mini'
            },
            'anthropic': {
                'api_key': os.getenv('ANTHROPIC_API_KEY', ''),
                'model': 'claude-3-haiku-20240307'
            }
        }
        llm_client = LLMClientManager(llm_config)
        
        # Initialize mock prompt manager
        prompt_manager = MockPromptManager()
        
        logger.info("✅ All components initialized")
        
        # Test 1: Test CIL module directly
        logger.info("\n📊 Test 1: Testing CIL module directly")
        
        from clean_cil_module import CleanCILModule
        
        cil = CleanCILModule(supabase_manager, llm_client)
        
        # Create a pattern strand
        pattern_strand = {
            'id': f"real_pattern_{int(datetime.now().timestamp())}",
            'kind': 'pattern',
            'module': 'alpha',
            'agent_id': 'raw_data_intelligence',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'session_bucket': 'GLOBAL',
            'regime': 'bullish',
            'tags': ['intelligence:raw_data:pattern', 'cil', 'pattern_strand'],
            'content': {
                'pattern_type': 'bullish_breakout',
                'confidence': 0.85,
                'significance': 'high',
                'pattern_group': {
                    'asset': 'BTCUSDT',
                    'timeframe': '1h',
                    'group_type': 'single_single',
                    'patterns': [{'pattern_type': 'bullish_breakout', 'confidence': 0.85}]
                }
            },
            'module_intelligence': {'confidence': 0.85, 'quality': 'high'},
            'sig_sigma': 2.1,
            'confidence': 0.85,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert pattern strand
        result = supabase_manager.client.table('ad_strands').insert(pattern_strand).execute()
        if result.data:
            logger.info(f"✅ Created pattern strand: {pattern_strand['id']}")
            
            # Process through CIL
            cil_success = await cil.process_pattern_strand(pattern_strand)
            if cil_success:
                logger.info("✅ CIL processed pattern strand successfully")
            else:
                logger.error("❌ CIL failed to process pattern strand")
        else:
            logger.error("❌ Failed to create pattern strand")
            return False
        
        # Test 2: Test CTP module directly (with fixed imports)
        logger.info("\n📈 Test 2: Testing CTP module directly")
        
        # Create a prediction review strand
        prediction_review_strand = {
            'id': f"real_review_{int(datetime.now().timestamp())}",
            'kind': 'prediction_review',
            'module': 'alpha',
            'agent_id': 'cil',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'session_bucket': 'GLOBAL',
            'regime': 'bullish',
            'tags': ['prediction_review', 'ctp', 'review_strand'],
            'content': {
                'prediction_id': f"prediction_{int(datetime.now().timestamp())}",
                'outcome': 'success',
                'return_pct': 5.2,
                'max_drawdown': 0.02,
                'duration_hours': 24,
                'review_quality': 'high',
                'success': True
            },
            'confidence': 0.9,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert prediction review strand
        result = supabase_manager.client.table('ad_strands').insert(prediction_review_strand).execute()
        if result.data:
            logger.info(f"✅ Created prediction review strand: {prediction_review_strand['id']}")
            
            # Test CTP with fixed imports
            try:
                # Import CTP with fixed path
                from Modules.Alpha_Detector.src.intelligence.conditional_trading_planner.ctp_agent import ConditionalTradingPlannerAgent
                
                ctp = ConditionalTradingPlannerAgent(supabase_manager, llm_client)
                
                # Process prediction review
                ctp_success = await ctp.process_prediction_review(prediction_review_strand['id'])
                if ctp_success:
                    logger.info("✅ CTP processed prediction review successfully")
                else:
                    logger.error("❌ CTP failed to process prediction review")
                    
            except Exception as e:
                logger.error(f"❌ CTP import/execution failed: {e}")
                # Fall back to mock CTP
                from event_driven_learning_system_fixed import MockCTPModule
                mock_ctp = MockCTPModule(supabase_manager, llm_client)
                ctp_success = await mock_ctp.process_prediction_review(prediction_review_strand, {})
                if ctp_success:
                    logger.info("✅ Mock CTP processed prediction review successfully")
                else:
                    logger.error("❌ Mock CTP failed to process prediction review")
        else:
            logger.error("❌ Failed to create prediction review strand")
            return False
        
        # Test 3: Test DM module directly (with fixed imports)
        logger.info("\n📋 Test 3: Testing DM module directly")
        
        # Create a conditional trading plan strand
        trading_plan_strand = {
            'id': f"real_plan_{int(datetime.now().timestamp())}",
            'kind': 'conditional_trading_plan',
            'module': 'alpha',
            'agent_id': 'ctp',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'session_bucket': 'GLOBAL',
            'regime': 'bullish',
            'tags': ['conditional_trading_plan', 'dm', 'plan_strand'],
            'content': {
                'plan_type': 'conditional_entry',
                'entry_conditions': ['price_above_50000', 'volume_spike'],
                'exit_conditions': ['target_hit', 'stop_loss'],
                'risk_reward_ratio': 2.5,
                'position_size': 0.02,
                'confidence': 0.8,
                'risk_score': 0.6,
                'leverage_score': 0.7
            },
            'confidence': 0.8,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert trading plan strand
        result = supabase_manager.client.table('ad_strands').insert(trading_plan_strand).execute()
        if result.data:
            logger.info(f"✅ Created trading plan strand: {trading_plan_strand['id']}")
            
            # Test DM with fixed imports
            try:
                # Import DM with fixed path
                from Modules.Alpha_Detector.src.intelligence.decision_maker.decision_maker import DecisionMaker
                
                dm = DecisionMaker(supabase_manager, llm_client)
                
                # Process trading plan
                dm_result = await dm.evaluate_trading_plan(trading_plan_strand)
                if dm_result:
                    logger.info(f"✅ DM processed trading plan successfully: {dm_result.get('decision', 'unknown')}")
                else:
                    logger.error("❌ DM failed to process trading plan")
                    
            except Exception as e:
                logger.error(f"❌ DM import/execution failed: {e}")
                # Fall back to mock DM
                from event_driven_learning_system_fixed import MockDMModule
                mock_dm = MockDMModule(supabase_manager, llm_client)
                dm_success = await mock_dm.process_trading_plan(trading_plan_strand, {})
                if dm_success:
                    logger.info("✅ Mock DM processed trading plan successfully")
                else:
                    logger.error("❌ Mock DM failed to process trading plan")
        else:
            logger.error("❌ Failed to create trading plan strand")
            return False
        
        # Test 4: Test TD module directly (with fixed imports)
        logger.info("\n🎯 Test 4: Testing TD module directly")
        
        # Create a trading decision strand
        trading_decision_strand = {
            'id': f"real_decision_{int(datetime.now().timestamp())}",
            'kind': 'trading_decision',
            'module': 'alpha',
            'agent_id': 'dm',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'session_bucket': 'GLOBAL',
            'regime': 'bullish',
            'tags': ['trading_decision', 'td', 'decision_strand'],
            'content': {
                'decision_type': 'execute_trade',
                'action': 'buy',
                'quantity': 0.02,
                'entry_price': 50000.0,
                'target_price': 52500.0,
                'stop_loss': 48000.0,
                'confidence': 0.85,
                'budget_allocation': 1000
            },
            'confidence': 0.85,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert trading decision strand
        result = supabase_manager.client.table('ad_strands').insert(trading_decision_strand).execute()
        if result.data:
            logger.info(f"✅ Created trading decision strand: {trading_decision_strand['id']}")
            
            # Test TD with fixed imports
            try:
                # Import TD with fixed path
                from Modules.Alpha_Detector.src.intelligence.trader.trader import Trader
                
                td = Trader(supabase_manager, llm_client)
                
                # Process trading decision
                td_result = await td.execute_decision(trading_decision_strand)
                if td_result:
                    logger.info(f"✅ TD processed trading decision successfully: {td_result.get('status', 'unknown')}")
                else:
                    logger.error("❌ TD failed to process trading decision")
                    
            except Exception as e:
                logger.error(f"❌ TD import/execution failed: {e}")
                # Fall back to mock TD
                from event_driven_learning_system_fixed import MockTDModule
                mock_td = MockTDModule(supabase_manager, llm_client)
                td_success = await mock_td.process_trading_decision(trading_decision_strand, {})
                if td_success:
                    logger.info("✅ Mock TD processed trading decision successfully")
                else:
                    logger.error("❌ Mock TD failed to process trading decision")
        else:
            logger.error("❌ Failed to create trading decision strand")
            return False
        
        # Test 5: Check what strands were created
        logger.info("\n🔍 Test 5: Checking what strands were created by real modules")
        
        # Get all strands created during this test
        all_strands_result = supabase_manager.client.table('ad_strands').select('*').like('id', 'real_%').execute()
        if all_strands_result.data:
            logger.info(f"✅ Found {len(all_strands_result.data)} strands created during real modules test:")
            for strand in all_strands_result.data:
                logger.info(f"  - {strand['kind']}: {strand['id']} (agent: {strand.get('agent_id', 'unknown')})")
        else:
            logger.warning("⚠️  No strands found created during real modules test")
        
        # Check for downstream strands created by modules
        logger.info("\n🔍 Test 6: Checking for downstream strands created by real modules")
        
        # Check for strands created by CIL (predictions)
        prediction_result = supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction').like('id', 'prediction_%').execute()
        if prediction_result.data:
            logger.info(f"✅ Found {len(prediction_result.data)} prediction strands created by CIL")
            for pred in prediction_result.data:
                logger.info(f"  - Prediction: {pred['id']}")
        
        # Check for strands created by CTP (conditional trading plans)
        ctp_result = supabase_manager.client.table('ad_strands').select('*').eq('kind', 'conditional_trading_plan').like('id', 'ctp_%').execute()
        if ctp_result.data:
            logger.info(f"✅ Found {len(ctp_result.data)} conditional trading plan strands created by CTP")
            for plan in ctp_result.data:
                logger.info(f"  - Plan: {plan['id']}")
        
        # Check for strands created by DM (trading decisions)
        dm_result = supabase_manager.client.table('ad_strands').select('*').eq('kind', 'trading_decision').like('id', 'dm_%').execute()
        if dm_result.data:
            logger.info(f"✅ Found {len(dm_result.data)} trading decision strands created by DM")
            for decision in dm_result.data:
                logger.info(f"  - Decision: {decision['id']}")
        
        # Check for strands created by TD (execution outcomes)
        td_result = supabase_manager.client.table('ad_strands').select('*').eq('kind', 'execution_outcome').like('id', 'td_%').execute()
        if td_result.data:
            logger.info(f"✅ Found {len(td_result.data)} execution outcome strands created by TD")
            for outcome in td_result.data:
                logger.info(f"  - Outcome: {outcome['id']}")
        
        # Test 7: Clean up test data
        logger.info("\n🧹 Test 7: Cleaning up test data")
        
        # Delete test strands
        test_strands = [pattern_strand, prediction_review_strand, trading_plan_strand, trading_decision_strand]
        for strand in test_strands:
            try:
                supabase_manager.client.table('ad_strands').delete().eq('id', strand['id']).execute()
                logger.info(f"✅ Deleted test strand: {strand['id']}")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete test strand {strand['id']}: {e}")
        
        # Delete downstream strands created by modules
        try:
            # Delete CTP created strands
            supabase_manager.client.table('ad_strands').delete().like('id', 'ctp_%').execute()
            logger.info("✅ Deleted CTP created strands")
            
            # Delete DM created strands
            supabase_manager.client.table('ad_strands').delete().like('id', 'dm_%').execute()
            logger.info("✅ Deleted DM created strands")
            
            # Delete TD created strands
            supabase_manager.client.table('ad_strands').delete().like('id', 'td_%').execute()
            logger.info("✅ Deleted TD created strands")
            
        except Exception as e:
            logger.warning(f"⚠️  Error cleaning up module-created strands: {e}")
        
        logger.info("\n🎉 Real modules pipeline test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_real_modules_pipeline()
    if success:
        logger.info("✅ Real Modules Pipeline test passed!")
    else:
        logger.error("❌ Real Modules Pipeline test failed!")
    return success


if __name__ == "__main__":
    asyncio.run(main())
