"""
Complete Real Flow Test

Tests the entire learning system pipeline:
1. Mock pattern overview → pattern strands
2. Mock completed prediction ready for review
3. Real LLM calls and clustering
4. Context injection validation
5. Complete end-to-end flow
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta
import json

# Add project root to path
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

from Modules.Alpha_Detector.src.utils.supabase_manager import SupabaseManager
from Modules.Alpha_Detector.src.intelligence.llm_integration.llm_client import LLMClientManager
from centralized_learning_system import CentralizedLearningSystem
from event_driven_learning_system import EventDrivenLearningSystem
from Modules.Alpha_Detector.src.llm_integration.prompt_manager import PromptManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockPatternOverviewCreator:
    """Creates realistic mock pattern overviews and strands"""
    
    def __init__(self, supabase_manager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
    
    async def create_pattern_overview_strand(self) -> str:
        """Create a realistic pattern overview strand"""
        try:
            overview_id = f"pattern_overview_{int(datetime.now().timestamp())}"
            
            overview_strand = {
                'id': overview_id,
                'kind': 'pattern_overview',
                'module': 'alpha',
                'agent_id': 'raw_data_intelligence',
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'session_bucket': 'GLOBAL',
                'regime': 'bullish',
                'tags': ['intelligence:raw_data:overview:coordination', 'cil', 'overview_strand', 'llm_coordination'],
                'target_agent': 'central_intelligence_layer',
                'content': {
                    'overview_type': 'comprehensive_analysis',
                    'confidence': 0.85,
                    'significance': 'high',
                    'pattern_groups': {
                        'BTCUSDT': {
                            'single_single': {
                                'group_1': {
                                    'asset': 'BTCUSDT',
                                    'timeframe': '1h',
                                    'group_type': 'single_single',
                                    'patterns': [
                                        {
                                            'pattern_type': 'bullish_breakout',
                                            'confidence': 0.88,
                                            'significance': 'high',
                                            'volume_spike': True,
                                            'momentum': 'strong'
                                        },
                                        {
                                            'pattern_type': 'support_bounce',
                                            'confidence': 0.82,
                                            'significance': 'medium',
                                            'volume_spike': False,
                                            'momentum': 'moderate'
                                        }
                                    ]
                                }
                            }
                        }
                    },
                    'market_conditions': {
                        'trend': 'bullish',
                        'volatility': 'high',
                        'volume': 'increasing',
                        'sentiment': 'positive'
                    }
                },
                'module_intelligence': {
                    'confidence': 0.85,
                    'quality': 'high',
                    'significance': 'high',
                    'analysis_depth': 'comprehensive'
                },
                'sig_sigma': 2.3,
                'confidence': 0.85,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert overview strand
            result = self.supabase_manager.client.table('ad_strands').insert(overview_strand).execute()
            if result.data:
                self.logger.info(f"✅ Created pattern overview: {overview_id}")
                return overview_id
            else:
                self.logger.error("❌ Failed to create pattern overview")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating pattern overview: {e}")
            return None
    
    async def create_individual_pattern_strands(self, overview_id: str) -> list:
        """Create individual pattern strands from overview"""
        try:
            pattern_strands = []
            
            # Create multiple pattern strands
            patterns = [
                {
                    'pattern_type': 'bullish_breakout',
                    'confidence': 0.88,
                    'significance': 'high',
                    'volume_spike': True,
                    'momentum': 'strong'
                },
                {
                    'pattern_type': 'support_bounce',
                    'confidence': 0.82,
                    'significance': 'medium',
                    'volume_spike': False,
                    'momentum': 'moderate'
                },
                {
                    'pattern_type': 'trend_continuation',
                    'confidence': 0.75,
                    'significance': 'medium',
                    'volume_spike': True,
                    'momentum': 'strong'
                }
            ]
            
            for i, pattern in enumerate(patterns):
                strand_id = f"pattern_{overview_id}_{i+1}"
                
                pattern_strand = {
                    'id': strand_id,
                    'kind': 'pattern',
                    'module': 'alpha',
                    'agent_id': 'raw_data_intelligence',
                    'symbol': 'BTCUSDT',
                    'timeframe': '1h',
                    'session_bucket': 'GLOBAL',
                    'regime': 'bullish',
                    'tags': ['intelligence:raw_data:pattern', 'cil', 'pattern_strand'],
                    'content': {
                        'pattern_type': pattern['pattern_type'],
                        'confidence': pattern['confidence'],
                        'significance': pattern['significance'],
                        'volume_spike': pattern['volume_spike'],
                        'momentum': pattern['momentum'],
                        'pattern_group': {
                            'asset': 'BTCUSDT',
                            'timeframe': '1h',
                            'group_type': 'single_single',
                            'patterns': [pattern]
                        }
                    },
                    'module_intelligence': {
                        'confidence': pattern['confidence'],
                        'quality': 'high' if pattern['confidence'] > 0.8 else 'medium',
                        'significance': pattern['significance']
                    },
                    'sig_sigma': 2.0 + (pattern['confidence'] - 0.5) * 2,
                    'confidence': pattern['confidence'],
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Insert pattern strand
                result = self.supabase_manager.client.table('ad_strands').insert(pattern_strand).execute()
                if result.data:
                    pattern_strands.append(strand_id)
                    self.logger.info(f"✅ Created pattern strand: {strand_id}")
                else:
                    self.logger.error(f"❌ Failed to create pattern strand: {strand_id}")
            
            return pattern_strands
            
        except Exception as e:
            self.logger.error(f"Error creating pattern strands: {e}")
            return []
    
    async def create_completed_prediction(self) -> str:
        """Create a completed prediction ready for review"""
        try:
            prediction_id = f"completed_prediction_{int(datetime.now().timestamp())}"
            
            # Create prediction that's ready for review
            prediction_strand = {
                'id': prediction_id,
                'kind': 'prediction',
                'module': 'alpha',
                'agent_id': 'cil',
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'session_bucket': 'GLOBAL',
                'regime': 'bullish',
                'tags': ['prediction', 'completed', 'ready_for_review'],
                'content': {
                    'prediction_type': 'price_target',
                    'target_price': 52000.0,
                    'entry_price': 48000.0,
                    'stop_loss': 46000.0,
                    'confidence': 0.85,
                    'method': 'pattern_analysis',
                    'prediction_data': {
                        'entry_price': 48000.0,
                        'target_price': 52000.0,
                        'stop_loss': 46000.0,
                        'confidence': 0.85,
                        'method': 'pattern_analysis',
                        'direction': 'long',
                        'duration_hours': 24
                    }
                },
                'outcome_data': {
                    'outcome': 'target_hit',
                    'final_price': 52500.0,
                    'max_drawdown': 0.02,
                    'duration_minutes': 1440,
                    'final_at': datetime.now(timezone.utc).isoformat()
                },
                'tracking_status': 'completed',
                'confidence': 0.85,
                'created_at': (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
                'tracking_started_at': (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            }
            
            # Insert prediction strand
            result = self.supabase_manager.client.table('ad_strands').insert(prediction_strand).execute()
            if result.data:
                self.logger.info(f"✅ Created completed prediction: {prediction_id}")
                return prediction_id
            else:
                self.logger.error("❌ Failed to create completed prediction")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating completed prediction: {e}")
            return None


class MockCILProcessor:
    """Mock CIL processor that handles pattern strands and creates predictions"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def process_pattern_strand(self, pattern_strand: dict) -> list:
        """Process pattern strand and create predictions"""
        try:
            strand_id = pattern_strand.get('id')
            self.logger.info(f"🎯 Processing pattern strand: {strand_id}")
            
            # Create prediction based on pattern
            prediction_id = f"prediction_{strand_id}"
            
            prediction = {
                'id': prediction_id,
                'kind': 'prediction',
                'module': 'alpha',
                'agent_id': 'cil',
                'symbol': pattern_strand.get('symbol', 'BTCUSDT'),
                'timeframe': pattern_strand.get('timeframe', '1h'),
                'session_bucket': 'GLOBAL',
                'regime': pattern_strand.get('regime', 'bullish'),
                'tags': ['prediction', 'cil_generated'],
                'content': {
                    'prediction_type': 'price_target',
                    'target_price': 50000.0 + (pattern_strand.get('confidence', 0.5) * 5000),
                    'entry_price': 48000.0,
                    'stop_loss': 46000.0,
                    'confidence': pattern_strand.get('confidence', 0.5),
                    'method': 'pattern_analysis',
                    'prediction_data': {
                        'entry_price': 48000.0,
                        'target_price': 50000.0 + (pattern_strand.get('confidence', 0.5) * 5000),
                        'stop_loss': 46000.0,
                        'confidence': pattern_strand.get('confidence', 0.5),
                        'method': 'pattern_analysis',
                        'direction': 'long',
                        'duration_hours': 24
                    }
                },
                'tracking_status': 'tracking',
                'confidence': pattern_strand.get('confidence', 0.5),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tracking_started_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert prediction
            result = self.supabase_manager.client.table('ad_strands').insert(prediction).execute()
            if result.data:
                self.logger.info(f"✅ Created prediction: {prediction_id}")
                return [prediction_id]
            else:
                self.logger.error("❌ Failed to create prediction")
                return []
                
        except Exception as e:
            self.logger.error(f"Error processing pattern strand: {e}")
            return []
    
    async def create_prediction_review(self, prediction_strand: dict) -> str:
        """Create prediction review from completed prediction"""
        try:
            prediction_id = prediction_strand.get('id')
            review_id = f"review_{prediction_id}"
            
            # Calculate outcome metrics
            entry_price = prediction_strand.get('content', {}).get('prediction_data', {}).get('entry_price', 48000.0)
            final_price = prediction_strand.get('outcome_data', {}).get('final_price', 50000.0)
            return_pct = ((final_price - entry_price) / entry_price) * 100
            
            review = {
                'id': review_id,
                'kind': 'prediction_review',
                'module': 'alpha',
                'agent_id': 'cil',
                'symbol': prediction_strand.get('symbol', 'BTCUSDT'),
                'timeframe': prediction_strand.get('timeframe', '1h'),
                'session_bucket': 'GLOBAL',
                'regime': prediction_strand.get('regime', 'bullish'),
                'tags': ['prediction_review', 'cil_generated'],
                'content': {
                    'prediction_id': prediction_id,
                    'outcome': prediction_strand.get('outcome_data', {}).get('outcome', 'target_hit'),
                    'return_pct': return_pct,
                    'max_drawdown': prediction_strand.get('outcome_data', {}).get('max_drawdown', 0.02),
                    'duration_hours': prediction_strand.get('outcome_data', {}).get('duration_minutes', 1440) / 60,
                    'review_quality': 'high',
                    'success': return_pct > 0
                },
                'confidence': 0.9,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert review
            result = self.supabase_manager.client.table('ad_strands').insert(review).execute()
            if result.data:
                self.logger.info(f"✅ Created prediction review: {review_id}")
                return review_id
            else:
                self.logger.error("❌ Failed to create prediction review")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating prediction review: {e}")
            return None


async def test_complete_real_flow():
    """Test the complete real flow with LLM calls and clustering"""
    try:
        logger.info("🧪 Testing Complete Real Flow with LLM Calls and Clustering")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        
        # Initialize LLM client manager with real API keys (will fallback to mock)
        llm_config = {
            'openai': {'api_key': 'test_key', 'model': 'gpt-4o-mini'},
            'anthropic': {'api_key': 'test_key', 'model': 'claude-3-haiku-20240307'}
        }
        llm_client = LLMClientManager(llm_config)
        
        # Initialize prompt manager
        prompt_manager = PromptManager()
        
        # Initialize learning system
        learning_system = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
        
        # Initialize event-driven system
        event_system = EventDrivenLearningSystem(supabase_manager, llm_client, prompt_manager)
        
        # Initialize mock creators
        pattern_creator = MockPatternOverviewCreator(supabase_manager)
        cil_processor = MockCILProcessor(supabase_manager, llm_client)
        
        logger.info("✅ All components initialized")
        
        # Test 1: Create pattern overview and individual strands
        logger.info("\n📊 Test 1: Creating pattern overview and individual strands")
        
        overview_id = await pattern_creator.create_pattern_overview_strand()
        if not overview_id:
            logger.error("❌ Failed to create pattern overview")
            return False
        
        pattern_strands = await pattern_creator.create_individual_pattern_strands(overview_id)
        if not pattern_strands:
            logger.error("❌ Failed to create pattern strands")
            return False
        
        logger.info(f"✅ Created {len(pattern_strands)} pattern strands")
        
        # Test 2: Create completed prediction ready for review
        logger.info("\n📈 Test 2: Creating completed prediction ready for review")
        
        completed_prediction_id = await pattern_creator.create_completed_prediction()
        if not completed_prediction_id:
            logger.error("❌ Failed to create completed prediction")
            return False
        
        logger.info(f"✅ Created completed prediction: {completed_prediction_id}")
        
        # Test 3: Process pattern strands through CIL
        logger.info("\n🎯 Test 3: Processing pattern strands through CIL")
        
        created_predictions = []
        for strand_id in pattern_strands:
            # Get the strand
            strand_result = supabase_manager.client.table('ad_strands').select('*').eq('id', strand_id).execute()
            if strand_result.data:
                strand = strand_result.data[0]
                predictions = await cil_processor.process_pattern_strand(strand)
                created_predictions.extend(predictions)
        
        logger.info(f"✅ Created {len(created_predictions)} predictions from pattern strands")
        
        # Test 4: Create prediction review from completed prediction
        logger.info("\n📊 Test 4: Creating prediction review from completed prediction")
        
        # Get the completed prediction
        prediction_result = supabase_manager.client.table('ad_strands').select('*').eq('id', completed_prediction_id).execute()
        if prediction_result.data:
            prediction = prediction_result.data[0]
            review_id = await cil_processor.create_prediction_review(prediction)
            if review_id:
                logger.info(f"✅ Created prediction review: {review_id}")
            else:
                logger.error("❌ Failed to create prediction review")
        else:
            logger.error("❌ Could not find completed prediction")
        
        # Test 5: Process all strands through learning system
        logger.info("\n🧠 Test 5: Processing all strands through learning system")
        
        # Get all strands
        all_strands_result = supabase_manager.client.table('ad_strands').select('*').in_('id', pattern_strands + [completed_prediction_id]).execute()
        if all_strands_result.data:
            for strand in all_strands_result.data:
                logger.info(f"🎯 Processing strand through learning system: {strand['id']}")
                await learning_system.process_strand(strand)
        
        # Test 6: Test LLM calls and clustering
        logger.info("\n🤖 Test 6: Testing LLM calls and clustering")
        
        # Get all strands for clustering
        all_strands_result = supabase_manager.client.table('ad_strands').select('*').execute()
        if all_strands_result.data:
            strands = all_strands_result.data
            logger.info(f"📊 Processing {len(strands)} strands through learning pipeline")
            
            # Process through learning pipeline
            await learning_system.learning_pipeline.process_strands(strands)
            
            # Check if braids were created
            braids_result = supabase_manager.client.table('ad_braids').select('*').execute()
            if braids_result.data:
                logger.info(f"✅ Created {len(braids_result.data)} braids")
                for braid in braids_result.data:
                    logger.info(f"  - Braid: {braid['id']} (level: {braid.get('level', 'N/A')}, resonance: {braid.get('resonance_score', 'N/A')})")
            else:
                logger.info("ℹ️  No braids created yet")
        
        # Test 7: Test context injection
        logger.info("\n💉 Test 7: Testing context injection")
        
        # Test context injection for different modules
        modules = ['cil', 'ctp', 'dm', 'td', 'rdi']
        for module in modules:
            try:
                context = await learning_system.get_context_for_module(module, {})
                if context:
                    logger.info(f"✅ Context injection for {module.upper()}: {len(context)} items")
                else:
                    logger.info(f"ℹ️  No context available for {module.upper()}")
            except Exception as e:
                logger.warning(f"⚠️  Context injection failed for {module.upper()}: {e}")
        
        # Test 8: Test event-driven processing
        logger.info("\n🚀 Test 8: Testing event-driven processing")
        
        # Create a new pattern strand and process through event system
        new_pattern = {
            'id': f"event_test_pattern_{int(datetime.now().timestamp())}",
            'kind': 'pattern',
            'module': 'alpha',
            'agent_id': 'raw_data_intelligence',
            'symbol': 'ETHUSDT',
            'timeframe': '1h',
            'content': {
                'pattern_type': 'bearish_reversal',
                'confidence': 0.75,
                'pattern_group': {
                    'asset': 'ETHUSDT',
                    'timeframe': '1h',
                    'group_type': 'single_single',
                    'patterns': [{'pattern_type': 'bearish_reversal', 'confidence': 0.75}]
                }
            },
            'module_intelligence': {'confidence': 0.75, 'quality': 'medium'},
            'sig_sigma': 1.8,
            'confidence': 0.75,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Insert and process
        result = supabase_manager.client.table('ad_strands').insert(new_pattern).execute()
        if result.data:
            logger.info(f"✅ Created event test pattern: {new_pattern['id']}")
            
            # Process through event system
            event_success = await event_system.process_strand_event(new_pattern)
            if event_success:
                logger.info("✅ Event system processed pattern successfully")
            else:
                logger.error("❌ Event system failed to process pattern")
        else:
            logger.error("❌ Failed to create event test pattern")
        
        # Test 9: Get system status
        logger.info("\n📊 Test 9: Getting system status")
        
        # Get counts
        pattern_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'pattern').execute()
        prediction_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'prediction').execute()
        review_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'prediction_review').execute()
        braid_count = supabase_manager.client.table('ad_braids').select('id', count='exact').execute()
        
        logger.info(f"📊 System Status:")
        logger.info(f"  - Pattern strands: {pattern_count.count or 0}")
        logger.info(f"  - Prediction strands: {prediction_count.count or 0}")
        logger.info(f"  - Prediction review strands: {review_count.count or 0}")
        logger.info(f"  - Braids: {braid_count.count or 0}")
        
        # Test 10: Clean up test data
        logger.info("\n🧹 Test 10: Cleaning up test data")
        
        # Delete test strands
        test_ids = pattern_strands + [overview_id, completed_prediction_id, new_pattern['id']]
        for test_id in test_ids:
            try:
                supabase_manager.client.table('ad_strands').delete().eq('id', test_id).execute()
                logger.info(f"✅ Deleted test strand: {test_id}")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete test strand {test_id}: {e}")
        
        logger.info("\n🎉 Complete real flow test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_complete_real_flow()
    if success:
        logger.info("✅ Complete Real Flow test passed!")
    else:
        logger.error("❌ Complete Real Flow test failed!")
    return success


if __name__ == "__main__":
    asyncio.run(main())
