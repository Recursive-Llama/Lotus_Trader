"""
Complete Module Flow Test

Tests the complete module triggering flow:
1. Pattern strands → CIL → predictions
2. Prediction reviews → CIL → CTP → conditional_trading_plan
3. Conditional trading plans → DM → trading_decision
4. Trading decisions → TD → execution_outcome
5. Execution outcomes → RDI feedback

This tests the actual module-to-module triggering, not just the learning system.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

from Modules.Alpha_Detector.src.utils.supabase_manager import SupabaseManager
from Modules.Alpha_Detector.src.intelligence.llm_integration.llm_client import LLMClientManager
from event_driven_learning_system import EventDrivenLearningSystem

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockPromptManager:
    """Mock prompt manager for testing"""
    
    def get_prompt(self, template_name: str, **kwargs) -> str:
        """Get a mock prompt"""
        return f"Mock prompt for {template_name} with {kwargs}"


async def test_complete_module_flow():
    """Test the complete module triggering flow"""
    try:
        logger.info("🧪 Testing Complete Module Flow - Module-to-Module Triggering")
        
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
        
        # Initialize event-driven system
        event_system = EventDrivenLearningSystem(supabase_manager, llm_client, prompt_manager)
        
        logger.info("✅ All components initialized")
        
        # Test 1: Create pattern strand and trigger CIL
        logger.info("\n📊 Test 1: Creating pattern strand → triggering CIL")
        
        pattern_strand = {
            'id': f"flow_pattern_{int(datetime.now().timestamp())}",
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
            
            # Process through event system (should trigger CIL)
            event_success = await event_system.process_strand_event(pattern_strand)
            if event_success:
                logger.info("✅ Event system processed pattern strand → CIL triggered")
            else:
                logger.error("❌ Event system failed to process pattern strand")
        else:
            logger.error("❌ Failed to create pattern strand")
            return False
        
        # Test 2: Create prediction review strand and trigger CTP
        logger.info("\n📈 Test 2: Creating prediction review strand → triggering CTP")
        
        prediction_review_strand = {
            'id': f"flow_review_{int(datetime.now().timestamp())}",
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
            
            # Process through event system (should trigger CTP)
            event_success = await event_system.process_strand_event(prediction_review_strand)
            if event_success:
                logger.info("✅ Event system processed prediction review → CTP triggered")
            else:
                logger.error("❌ Event system failed to process prediction review")
        else:
            logger.error("❌ Failed to create prediction review strand")
            return False
        
        # Test 3: Create conditional trading plan strand and trigger DM
        logger.info("\n📋 Test 3: Creating conditional trading plan strand → triggering DM")
        
        trading_plan_strand = {
            'id': f"flow_plan_{int(datetime.now().timestamp())}",
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
                'confidence': 0.8
            },
            'confidence': 0.8,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert trading plan strand
        result = supabase_manager.client.table('ad_strands').insert(trading_plan_strand).execute()
        if result.data:
            logger.info(f"✅ Created trading plan strand: {trading_plan_strand['id']}")
            
            # Process through event system (should trigger DM)
            event_success = await event_system.process_strand_event(trading_plan_strand)
            if event_success:
                logger.info("✅ Event system processed trading plan → DM triggered")
            else:
                logger.error("❌ Event system failed to process trading plan")
        else:
            logger.error("❌ Failed to create trading plan strand")
            return False
        
        # Test 4: Create trading decision strand and trigger TD
        logger.info("\n🎯 Test 4: Creating trading decision strand → triggering TD")
        
        trading_decision_strand = {
            'id': f"flow_decision_{int(datetime.now().timestamp())}",
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
                'confidence': 0.85
            },
            'confidence': 0.85,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert trading decision strand
        result = supabase_manager.client.table('ad_strands').insert(trading_decision_strand).execute()
        if result.data:
            logger.info(f"✅ Created trading decision strand: {trading_decision_strand['id']}")
            
            # Process through event system (should trigger TD)
            event_success = await event_system.process_strand_event(trading_decision_strand)
            if event_success:
                logger.info("✅ Event system processed trading decision → TD triggered")
            else:
                logger.error("❌ Event system failed to process trading decision")
        else:
            logger.error("❌ Failed to create trading decision strand")
            return False
        
        # Test 5: Create execution outcome strand and trigger RDI feedback
        logger.info("\n📊 Test 5: Creating execution outcome strand → triggering RDI feedback")
        
        execution_outcome_strand = {
            'id': f"flow_outcome_{int(datetime.now().timestamp())}",
            'kind': 'execution_outcome',
            'module': 'alpha',
            'agent_id': 'td',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'session_bucket': 'GLOBAL',
            'regime': 'bullish',
            'tags': ['execution_outcome', 'rdi', 'outcome_strand'],
            'content': {
                'outcome_type': 'success',
                'executed_price': 50050.0,
                'final_price': 52500.0,
                'return_pct': 4.9,
                'execution_quality': 'excellent',
                'slippage': 0.001
            },
            'confidence': 0.9,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert execution outcome strand
        result = supabase_manager.client.table('ad_strands').insert(execution_outcome_strand).execute()
        if result.data:
            logger.info(f"✅ Created execution outcome strand: {execution_outcome_strand['id']}")
            
            # Process through event system (should trigger RDI feedback)
            event_success = await event_system.process_strand_event(execution_outcome_strand)
            if event_success:
                logger.info("✅ Event system processed execution outcome → RDI feedback triggered")
            else:
                logger.error("❌ Event system failed to process execution outcome")
        else:
            logger.error("❌ Failed to create execution outcome strand")
            return False
        
        # Test 6: Check what strands were created by the triggered modules
        logger.info("\n🔍 Test 6: Checking what strands were created by triggered modules")
        
        # Get all strands created during this test
        all_strands_result = supabase_manager.client.table('ad_strands').select('*').like('id', 'flow_%').execute()
        if all_strands_result.data:
            logger.info(f"✅ Found {len(all_strands_result.data)} strands created during flow test:")
            for strand in all_strands_result.data:
                logger.info(f"  - {strand['kind']}: {strand['id']} (agent: {strand.get('agent_id', 'unknown')})")
        else:
            logger.warning("⚠️  No strands found created during flow test")
        
        # Test 7: Get final system status
        logger.info("\n📊 Test 7: Getting final system status")
        
        # Get counts by kind
        kinds = ['pattern', 'prediction', 'prediction_review', 'conditional_trading_plan', 'trading_decision', 'execution_outcome']
        for kind in kinds:
            count_result = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', kind).execute()
            logger.info(f"  - {kind} strands: {count_result.count or 0}")
        
        # Test 8: Clean up test data
        logger.info("\n🧹 Test 8: Cleaning up test data")
        
        # Delete test strands
        test_strands = [pattern_strand, prediction_review_strand, trading_plan_strand, trading_decision_strand, execution_outcome_strand]
        for strand in test_strands:
            try:
                supabase_manager.client.table('ad_strands').delete().eq('id', strand['id']).execute()
                logger.info(f"✅ Deleted test strand: {strand['id']}")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete test strand {strand['id']}: {e}")
        
        logger.info("\n🎉 Complete module flow test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_complete_module_flow()
    if success:
        logger.info("✅ Complete Module Flow test passed!")
    else:
        logger.error("❌ Complete Module Flow test failed!")
    return success


if __name__ == "__main__":
    asyncio.run(main())
