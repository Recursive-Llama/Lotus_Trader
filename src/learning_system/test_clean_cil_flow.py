"""
Test Clean CIL Flow - Option 2 Implementation

Tests the clean CIL module that handles both:
1. Pattern processing → predictions
2. Prediction review creation

This verifies the complete CIL data flow.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

from src.learning_system.clean_cil_module import CleanCILModule
from src.learning_system.event_driven_learning_system import EventDrivenLearningSystem
from src.learning_system.supabase_manager import SupabaseManager
from src.learning_system.llm_client import OpenRouterClient
from src.learning_system.prompt_manager import PromptManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_clean_cil_flow():
    """Test the complete clean CIL flow"""
    try:
        logger.info("🧪 Testing Clean CIL Flow - Option 2 Implementation")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        prompt_manager = PromptManager()
        
        # Initialize clean CIL module
        cil = CleanCILModule(supabase_manager, llm_client)
        
        # Initialize event-driven system
        event_system = EventDrivenLearningSystem(supabase_manager, llm_client, prompt_manager)
        
        logger.info("✅ Components initialized")
        
        # Test 1: Create a test pattern strand
        logger.info("\n📊 Test 1: Creating test pattern strand")
        
        test_pattern_strand = {
            'id': f"test_pattern_{int(datetime.now().timestamp())}",
            'kind': 'pattern',
            'module': 'alpha',
            'agent_id': 'raw_data_intelligence',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'session_bucket': 'GLOBAL',
            'regime': 'bullish',
            'tags': ['test', 'pattern'],
            'content': {
                'pattern_type': 'bullish_breakout',
                'confidence': 0.85,
                'significance': 'high',
                'pattern_group': {
                    'asset': 'BTCUSDT',
                    'timeframe': '1h',
                    'group_type': 'single_single',
                    'patterns': [
                        {
                            'pattern_type': 'bullish_breakout',
                            'confidence': 0.85,
                            'significance': 'high'
                        }
                    ]
                }
            },
            'module_intelligence': {
                'confidence': 0.85,
                'quality': 'high',
                'significance': 'high'
            },
            'sig_sigma': 2.1,
            'confidence': 0.85,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert test pattern strand
        result = supabase_manager.client.table('ad_strands').insert(test_pattern_strand).execute()
        if result.data:
            logger.info(f"✅ Created test pattern strand: {test_pattern_strand['id']}")
        else:
            logger.error("❌ Failed to create test pattern strand")
            return False
        
        # Test 2: Process pattern strand through CIL
        logger.info("\n🎯 Test 2: Processing pattern strand through CIL")
        
        success = await cil.process_pattern_strand(test_pattern_strand)
        if success:
            logger.info("✅ CIL processed pattern strand successfully")
        else:
            logger.error("❌ CIL failed to process pattern strand")
            return False
        
        # Test 3: Check if predictions were created
        logger.info("\n📈 Test 3: Checking if predictions were created")
        
        prediction_result = supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction').execute()
        if prediction_result.data:
            logger.info(f"✅ Found {len(prediction_result.data)} prediction strands")
            for pred in prediction_result.data:
                logger.info(f"  - Prediction: {pred['id']} (confidence: {pred.get('confidence', 'N/A')})")
        else:
            logger.warning("⚠️  No prediction strands found")
        
        # Test 4: Check if prediction_review strands were created
        logger.info("\n📊 Test 4: Checking if prediction_review strands were created")
        
        review_result = supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').execute()
        if review_result.data:
            logger.info(f"✅ Found {len(review_result.data)} prediction_review strands")
            for review in review_result.data:
                logger.info(f"  - Review: {review['id']} (outcome: {review.get('content', {}).get('outcome', 'N/A')})")
        else:
            logger.info("ℹ️  No prediction_review strands found (expected if no predictions are finalized)")
        
        # Test 5: Test event-driven system
        logger.info("\n🚀 Test 5: Testing event-driven system")
        
        # Create another test pattern strand
        test_pattern_2 = test_pattern_strand.copy()
        test_pattern_2['id'] = f"test_pattern_2_{int(datetime.now().timestamp())}"
        test_pattern_2['content']['pattern_type'] = 'bearish_reversal'
        test_pattern_2['content']['confidence'] = 0.75
        
        # Insert second test pattern
        result2 = supabase_manager.client.table('ad_strands').insert(test_pattern_2).execute()
        if result2.data:
            logger.info(f"✅ Created second test pattern strand: {test_pattern_2['id']}")
            
            # Process through event system
            event_success = await event_system.process_strand_event(test_pattern_2)
            if event_success:
                logger.info("✅ Event system processed pattern strand successfully")
            else:
                logger.error("❌ Event system failed to process pattern strand")
                return False
        else:
            logger.error("❌ Failed to create second test pattern strand")
            return False
        
        # Test 6: Get module status
        logger.info("\n📊 Test 6: Getting CIL module status")
        
        status = await cil.get_module_status()
        logger.info(f"✅ CIL Status: {status}")
        
        # Test 7: Clean up test data
        logger.info("\n🧹 Test 7: Cleaning up test data")
        
        # Delete test strands
        test_ids = [test_pattern_strand['id'], test_pattern_2['id']]
        for test_id in test_ids:
            try:
                supabase_manager.client.table('ad_strands').delete().eq('id', test_id).execute()
                logger.info(f"✅ Deleted test strand: {test_id}")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete test strand {test_id}: {e}")
        
        logger.info("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_clean_cil_flow()
    if success:
        logger.info("✅ Clean CIL Flow test passed!")
    else:
        logger.error("❌ Clean CIL Flow test failed!")
    return success


if __name__ == "__main__":
    asyncio.run(main())
