"""
Simple Flow Test with Mock Components

Tests the clean CIL flow concept without complex dependencies.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

from Modules.Alpha_Detector.src.utils.supabase_manager import SupabaseManager
from Modules.Alpha_Detector.src.intelligence.llm_integration.llm_client import LLMClientManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockPredictionEngine:
    """Mock prediction engine for testing"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def process_pattern_overview(self, pattern_strand):
        """Mock process pattern overview"""
        try:
            strand_id = pattern_strand.get('id')
            self.logger.info(f"🎯 Mock processing pattern: {strand_id}")
            
            # Create mock prediction
            prediction = {
                'id': f"prediction_{strand_id}",
                'kind': 'prediction',
                'module': 'alpha',
                'agent_id': 'cil',
                'symbol': pattern_strand.get('symbol', 'BTCUSDT'),
                'timeframe': pattern_strand.get('timeframe', '1h'),
                'content': {
                    'prediction_type': 'price_target',
                    'target_price': 50000.0,
                    'confidence': 0.8,
                    'method': 'pattern_analysis'
                },
                'confidence': 0.8,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert prediction
            result = self.supabase_manager.client.table('ad_strands').insert(prediction).execute()
            if result.data:
                self.logger.info(f"✅ Created mock prediction: {prediction['id']}")
                return [prediction['id']]
            else:
                self.logger.error("❌ Failed to create mock prediction")
                return []
                
        except Exception as e:
            self.logger.error(f"Error in mock prediction engine: {e}")
            return []


class MockReviewCreator:
    """Mock review creator for testing"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def process_finalized_predictions(self):
        """Mock process finalized predictions"""
        try:
            # Check for predictions that could be reviewed
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction').execute()
            
            if not result.data:
                self.logger.info("No predictions found for review")
                return 0
            
            created_count = 0
            
            for prediction in result.data:
                # Create mock review
                review = {
                    'id': f"review_{prediction['id']}",
                    'kind': 'prediction_review',
                    'module': 'alpha',
                    'agent_id': 'cil',
                    'symbol': prediction.get('symbol', 'BTCUSDT'),
                    'timeframe': prediction.get('timeframe', '1h'),
                    'content': {
                        'prediction_id': prediction['id'],
                        'outcome': 'success',
                        'return_pct': 5.2,
                        'review_quality': 'high'
                    },
                    'confidence': 0.9,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Insert review
                review_result = self.supabase_manager.client.table('ad_strands').insert(review).execute()
                if review_result.data:
                    created_count += 1
                    self.logger.info(f"✅ Created mock review: {review['id']}")
            
            return created_count
            
        except Exception as e:
            self.logger.error(f"Error in mock review creator: {e}")
            return 0


class MockCleanCILModule:
    """Mock clean CIL module for testing"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Initialize mock components
        self.prediction_engine = MockPredictionEngine(supabase_manager, llm_client)
        self.review_creator = MockReviewCreator(supabase_manager, llm_client)
    
    async def process_pattern_strand(self, pattern_strand):
        """Process a pattern strand - this is the main entry point"""
        try:
            strand_id = pattern_strand.get('id')
            self.logger.info(f"🎯 Mock CIL processing pattern strand: {strand_id}")
            
            # 1. Process pattern strand → create predictions
            prediction_ids = await self.prediction_engine.process_pattern_overview(pattern_strand)
            
            if prediction_ids:
                self.logger.info(f"✅ Created {len(prediction_ids)} predictions from pattern {strand_id}")
            else:
                self.logger.warning(f"⚠️  No predictions created from pattern {strand_id}")
            
            # 2. Check for finalized predictions → create prediction_review strands
            review_count = await self.review_creator.process_finalized_predictions()
            
            if review_count > 0:
                self.logger.info(f"✅ Created {review_count} prediction_review strands from finalized predictions")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error processing pattern strand {strand_id}: {e}")
            return False
    
    async def get_module_status(self):
        """Get current module status"""
        try:
            # Get counts of different strand types
            pattern_count = await self._get_strand_count('pattern')
            prediction_count = await self._get_strand_count('prediction')
            review_count = await self._get_strand_count('prediction_review')
            
            return {
                'module': 'MockCIL',
                'status': 'active',
                'pattern_strands': pattern_count,
                'prediction_strands': prediction_count,
                'prediction_review_strands': review_count,
                'last_processed': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting module status: {e}")
            return {'module': 'MockCIL', 'status': 'error', 'error': str(e)}
    
    async def _get_strand_count(self, kind):
        """Get count of strands by kind"""
        try:
            result = self.supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', kind).execute()
            return result.count or 0
        except Exception as e:
            self.logger.error(f"Error getting strand count for {kind}: {e}")
            return 0


async def test_mock_cil_flow():
    """Test the mock CIL flow"""
    try:
        logger.info("🧪 Testing Mock CIL Flow - Option 2 Implementation")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        
        # Initialize LLM client manager
        llm_config = {
            'openai': {'api_key': 'test_key', 'model': 'gpt-4o-mini'},
            'anthropic': {'api_key': 'test_key', 'model': 'claude-3-haiku-20240307'}
        }
        llm_client = LLMClientManager(llm_config)
        
        # Initialize mock CIL
        cil = MockCleanCILModule(supabase_manager, llm_client)
        
        logger.info("✅ Mock CIL module initialized")
        
        # Test 1: Create a test pattern strand
        logger.info("\n📊 Test 1: Creating test pattern strand")
        
        test_pattern_strand = {
            'id': f"mock_test_pattern_{int(datetime.now().timestamp())}",
            'kind': 'pattern',
            'module': 'alpha',
            'agent_id': 'raw_data_intelligence',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'session_bucket': 'GLOBAL',
            'regime': 'bullish',
            'tags': ['test', 'pattern', 'mock'],
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
        
        # Test 2: Process pattern strand through mock CIL
        logger.info("\n🎯 Test 2: Processing pattern strand through mock CIL")
        
        success = await cil.process_pattern_strand(test_pattern_strand)
        if success:
            logger.info("✅ Mock CIL processed pattern strand successfully")
        else:
            logger.error("❌ Mock CIL failed to process pattern strand")
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
            logger.info("ℹ️  No prediction_review strands found")
        
        # Test 5: Get module status
        logger.info("\n📊 Test 5: Getting mock CIL module status")
        
        status = await cil.get_module_status()
        logger.info(f"✅ Mock CIL Status: {status}")
        
        # Test 6: Clean up test data
        logger.info("\n🧹 Test 6: Cleaning up test data")
        
        # Delete test strands
        test_ids = [test_pattern_strand['id']]
        for test_id in test_ids:
            try:
                supabase_manager.client.table('ad_strands').delete().eq('id', test_id).execute()
                logger.info(f"✅ Deleted test strand: {test_id}")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete test strand {test_id}: {e}")
        
        logger.info("\n🎉 All mock tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_mock_cil_flow()
    if success:
        logger.info("✅ Mock CIL Flow test passed!")
    else:
        logger.error("❌ Mock CIL Flow test failed!")
    return success


if __name__ == "__main__":
    asyncio.run(main())
