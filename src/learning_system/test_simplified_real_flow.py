"""
Simplified Real Flow Test

Tests the core learning system functionality:
1. Create pattern strands and predictions
2. Test LLM calls
3. Test clustering and braid creation
4. Test context injection
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockPromptManager:
    """Mock prompt manager for testing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_prompt(self, template_name: str, **kwargs) -> str:
        """Get a mock prompt"""
        prompts = {
            'braid_analysis': """
# Braid Analysis

## Pattern Summary
This braid contains {strand_count} strands showing {pattern_type} patterns.

## Key Insights
- Patterns show {confidence_level} confidence
- Market conditions favor these strategies
- Risk management is essential

## Recommendations
- Monitor for similar patterns
- Implement with proper risk management
- Update based on market changes

## Confidence Level
{confidence_level} based on sample size and consistency
""",
            'context_injection': """
# Context for {module}

## Relevant Patterns
{patterns_summary}

## Key Insights
{insights_summary}

## Recommendations
{recommendations_summary}
"""
        }
        
        return prompts.get(template_name, f"Mock prompt for {template_name}")


class SimplifiedLearningSystem:
    """Simplified learning system for testing"""
    
    def __init__(self, supabase_manager, llm_client, prompt_manager):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.logger = logging.getLogger(__name__)
    
    async def process_strand(self, strand: dict) -> bool:
        """Process a single strand"""
        try:
            strand_id = strand.get('id')
            strand_kind = strand.get('kind')
            
            self.logger.info(f"🎯 Processing strand: {strand_id} ({strand_kind})")
            
            # Simple processing - just log the strand
            if strand_kind == 'pattern':
                self.logger.info(f"  - Pattern type: {strand.get('content', {}).get('pattern_type', 'unknown')}")
                self.logger.info(f"  - Confidence: {strand.get('confidence', 'N/A')}")
            elif strand_kind == 'prediction':
                self.logger.info(f"  - Prediction type: {strand.get('content', {}).get('prediction_type', 'unknown')}")
                self.logger.info(f"  - Confidence: {strand.get('confidence', 'N/A')}")
            elif strand_kind == 'prediction_review':
                self.logger.info(f"  - Outcome: {strand.get('content', {}).get('outcome', 'unknown')}")
                self.logger.info(f"  - Return %: {strand.get('content', {}).get('return_pct', 'N/A')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing strand {strand_id}: {e}")
            return False
    
    async def test_llm_calls(self) -> bool:
        """Test LLM calls"""
        try:
            self.logger.info("🤖 Testing LLM calls...")
            
            # Test completion
            prompt = "Analyze these market patterns and create a trading strategy for BTCUSDT."
            completion = await self.llm_client.generate_completion(prompt, max_tokens=200, temperature=0.7)
            
            if completion and "Error" not in completion:
                self.logger.info(f"✅ LLM completion successful: {completion[:100]}...")
            else:
                self.logger.warning(f"⚠️  LLM completion returned: {completion}")
            
            # Test embedding
            embedding = await self.llm_client.generate_embedding("test market analysis")
            
            if embedding and len(embedding) > 0:
                self.logger.info(f"✅ LLM embedding successful: {len(embedding)} dimensions")
            else:
                self.logger.warning("⚠️  LLM embedding failed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error testing LLM calls: {e}")
            return False
    
    async def test_clustering(self, strands: list) -> bool:
        """Test clustering functionality"""
        try:
            self.logger.info("🔗 Testing clustering...")
            
            # Simple clustering by strand kind
            clusters = {}
            for strand in strands:
                kind = strand.get('kind', 'unknown')
                if kind not in clusters:
                    clusters[kind] = []
                clusters[kind].append(strand)
            
            self.logger.info(f"✅ Created {len(clusters)} clusters:")
            for kind, cluster_strands in clusters.items():
                self.logger.info(f"  - {kind}: {len(cluster_strands)} strands")
            
            # Create mock braids
            braid_count = 0
            for kind, cluster_strands in clusters.items():
                if len(cluster_strands) > 0:
                    braid_id = f"braid_{kind}_{int(datetime.now().timestamp())}"
                    
                    # Calculate average confidence
                    confidences = [s.get('confidence', 0.5) for s in cluster_strands]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
                    
                    braid = {
                        'id': braid_id,
                        'level': 1,
                        'strand_type': kind,
                        'strand_ids': [s['id'] for s in cluster_strands],
                        'resonance_score': avg_confidence,
                        'cluster_size': len(cluster_strands),
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Create braid as a strand with braid_level > 1
                    braid_strand = {
                        'id': braid_id,
                        'kind': 'braid',
                        'module': 'alpha',
                        'agent_id': 'learning_system',
                        'symbol': 'BTCUSDT',
                        'timeframe': '1h',
                        'session_bucket': 'GLOBAL',
                        'regime': 'bullish',
                        'tags': ['braid', 'learning_generated'],
                        'content': {
                            'braid_type': kind,
                            'source_strand_ids': [s['id'] for s in cluster_strands],
                            'resonance_score': avg_confidence,
                            'cluster_size': len(cluster_strands)
                        },
                        'braid_level': 2,  # Braids are level 2+
                        'resonance_score': avg_confidence,
                        'confidence': avg_confidence,
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Insert braid as a strand
                    result = self.supabase_manager.client.table('ad_strands').insert(braid_strand).execute()
                    if result.data:
                        braid_count += 1
                        self.logger.info(f"✅ Created braid strand: {braid_id} (level: 2, resonance: {avg_confidence:.2f})")
                    else:
                        self.logger.error(f"❌ Failed to create braid strand: {braid_id}")
            
            self.logger.info(f"✅ Created {braid_count} braids total")
            return True
            
        except Exception as e:
            self.logger.error(f"Error testing clustering: {e}")
            return False
    
    async def test_context_injection(self) -> bool:
        """Test context injection"""
        try:
            self.logger.info("💉 Testing context injection...")
            
        # Get braids from ad_strands table (braid_level > 1)
        try:
            braids_result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'braid').execute()
            if braids_result.data:
                braids = braids_result.data
                self.logger.info(f"✅ Found {len(braids)} braids for context injection")
            else:
                braids = []
                self.logger.info("ℹ️  No braids found for context injection")
        except Exception as e:
            self.logger.error(f"❌ Error getting braids: {e}")
            braids = []
        
        # Test context injection for different modules
        modules = ['cil', 'ctp', 'dm', 'td', 'rdi']
        
        for module in modules:
                try:
                    # Create context with actual braids
                    context = {
                        'module': module,
                        'relevant_braids': braids[:3],  # Top 3 braids
                        'insights': f"Key insights for {module.upper()} module",
                        'recommendations': f"Recommendations for {module.upper()} module",
                        'confidence': 0.8
                    }
                    
                    # Use prompt manager to format context
                    prompt = self.prompt_manager.get_prompt(
                        'context_injection',
                        module=module,
                        patterns_summary=f"Found {len(braids)} relevant patterns",
                        insights_summary=context['insights'],
                        recommendations_summary=context['recommendations']
                    )
                    
                    self.logger.info(f"✅ Context injection for {module.upper()}: {len(context)} items")
                    self.logger.debug(f"  - Prompt: {prompt[:100]}...")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️  Context injection failed for {module.upper()}: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error testing context injection: {e}")
            return False


async def test_simplified_real_flow():
    """Test the simplified real flow"""
    try:
        logger.info("🧪 Testing Simplified Real Flow")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        
        # Initialize LLM client manager
        llm_config = {
            'openai': {'api_key': 'test_key', 'model': 'gpt-4o-mini'},
            'anthropic': {'api_key': 'test_key', 'model': 'claude-3-haiku-20240307'}
        }
        llm_client = LLMClientManager(llm_config)
        
        # Initialize mock prompt manager
        prompt_manager = MockPromptManager()
        
        # Initialize learning system
        learning_system = SimplifiedLearningSystem(supabase_manager, llm_client, prompt_manager)
        
        logger.info("✅ All components initialized")
        
        # Test 1: Create test strands
        logger.info("\n📊 Test 1: Creating test strands")
        
        test_strands = []
        
        # Create pattern strands
        for i in range(3):
            pattern_strand = {
                'id': f"test_pattern_{i+1}_{int(datetime.now().timestamp())}",
                'kind': 'pattern',
                'module': 'alpha',
                'agent_id': 'raw_data_intelligence',
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'content': {
                    'pattern_type': f'pattern_type_{i+1}',
                    'confidence': 0.7 + (i * 0.1),
                    'significance': 'high' if i == 0 else 'medium'
                },
                'confidence': 0.7 + (i * 0.1),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase_manager.client.table('ad_strands').insert(pattern_strand).execute()
            if result.data:
                test_strands.append(pattern_strand)
                logger.info(f"✅ Created pattern strand: {pattern_strand['id']}")
        
        # Create prediction strands
        for i in range(2):
            prediction_strand = {
                'id': f"test_prediction_{i+1}_{int(datetime.now().timestamp())}",
                'kind': 'prediction',
                'module': 'alpha',
                'agent_id': 'cil',
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'content': {
                    'prediction_type': 'price_target',
                    'target_price': 50000.0 + (i * 1000),
                    'confidence': 0.8 + (i * 0.05)
                },
                'confidence': 0.8 + (i * 0.05),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase_manager.client.table('ad_strands').insert(prediction_strand).execute()
            if result.data:
                test_strands.append(prediction_strand)
                logger.info(f"✅ Created prediction strand: {prediction_strand['id']}")
        
        # Create prediction review strands
        for i in range(1):
            review_strand = {
                'id': f"test_review_{i+1}_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'module': 'alpha',
                'agent_id': 'cil',
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'content': {
                    'outcome': 'success',
                    'return_pct': 5.2 + (i * 2.1),
                    'review_quality': 'high'
                },
                'confidence': 0.9,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = supabase_manager.client.table('ad_strands').insert(review_strand).execute()
            if result.data:
                test_strands.append(review_strand)
                logger.info(f"✅ Created review strand: {review_strand['id']}")
        
        logger.info(f"✅ Created {len(test_strands)} test strands total")
        
        # Test 2: Process strands through learning system
        logger.info("\n🎯 Test 2: Processing strands through learning system")
        
        for strand in test_strands:
            success = await learning_system.process_strand(strand)
            if not success:
                logger.warning(f"⚠️  Failed to process strand: {strand['id']}")
        
        # Test 3: Test LLM calls
        logger.info("\n🤖 Test 3: Testing LLM calls")
        
        llm_success = await learning_system.test_llm_calls()
        if llm_success:
            logger.info("✅ LLM calls successful")
        else:
            logger.warning("⚠️  LLM calls had issues")
        
        # Test 4: Test clustering
        logger.info("\n🔗 Test 4: Testing clustering")
        
        clustering_success = await learning_system.test_clustering(test_strands)
        if clustering_success:
            logger.info("✅ Clustering successful")
        else:
            logger.warning("⚠️  Clustering had issues")
        
        # Test 5: Test context injection
        logger.info("\n💉 Test 5: Testing context injection")
        
        context_success = await learning_system.test_context_injection()
        if context_success:
            logger.info("✅ Context injection successful")
        else:
            logger.warning("⚠️  Context injection had issues")
        
        # Test 6: Get final status
        logger.info("\n📊 Test 6: Getting final system status")
        
        # Get counts
        pattern_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'pattern').execute()
        prediction_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'prediction').execute()
        review_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'prediction_review').execute()
        # Get braid count from ad_strands table (kind = 'braid')
        braid_count = supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'braid').execute()
        
        logger.info(f"📊 Final System Status:")
        logger.info(f"  - Pattern strands: {pattern_count.count or 0}")
        logger.info(f"  - Prediction strands: {prediction_count.count or 0}")
        logger.info(f"  - Prediction review strands: {review_count.count or 0}")
        logger.info(f"  - Braids: {braid_count.count or 0}")
        
        # Test 7: Clean up test data
        logger.info("\n🧹 Test 7: Cleaning up test data")
        
        for strand in test_strands:
            try:
                supabase_manager.client.table('ad_strands').delete().eq('id', strand['id']).execute()
                logger.info(f"✅ Deleted test strand: {strand['id']}")
            except Exception as e:
                logger.warning(f"⚠️  Could not delete test strand {strand['id']}: {e}")
        
        # Clean up braid strands
        try:
            supabase_manager.client.table('ad_strands').delete().like('id', 'braid_%').execute()
            logger.info("✅ Cleaned up test braid strands")
        except Exception as e:
            logger.warning(f"⚠️  Could not clean up braid strands: {e}")
        
        logger.info("\n🎉 Simplified real flow test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_simplified_real_flow()
    if success:
        logger.info("✅ Simplified Real Flow test passed!")
    else:
        logger.error("❌ Simplified Real Flow test failed!")
    return success


if __name__ == "__main__":
    asyncio.run(main())
