"""
Simple Test for Social Lowcap Pipeline

Tests the basic social ingest module with the new curator configuration.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.intelligence.social_ingest.social_ingest_basic import SocialIngestModule

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockSupabaseManager:
    """Mock Supabase manager for testing"""
    
    def create_strand(self, strand_data):
        """Mock strand creation"""
        logger.info(f"Mock: Created strand {strand_data['kind']} for {strand_data['content']['curator_id']}")
        return {
            **strand_data,
            'id': f"strand_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'created_at': datetime.now(timezone.utc)
        }
    
    def update_curator_last_seen(self, curator_id):
        """Mock curator update"""
        logger.info(f"Mock: Updated last_seen for curator {curator_id}")


class MockLLMClient:
    """Mock LLM client for testing"""
    
    async def generate_async(self, prompt, system_message=None, image=None):
        """Mock LLM response"""
        # Simulate token extraction
        if "FOO" in prompt or "BAR" in prompt:
            return '{"token_name": "FOO", "network": "solana", "contract_address": "So1aNa1234567890abcdef", "sentiment": "positive", "confidence": 0.85, "trading_intention": "buy", "has_chart": true, "chart_type": "price", "chart_analysis": "bullish pattern", "additional_info": "New launch on Raydium"}'
        else:
            return 'null'


async def test_social_ingest():
    """Test the social ingest module"""
    logger.info("🧪 Testing Social Ingest Module...")
    
    # Initialize components
    supabase_manager = MockSupabaseManager()
    llm_client = MockLLMClient()
    
    # Create social ingest module
    social_ingest = SocialIngestModule(supabase_manager, llm_client)
    
    # Test curator loading
    logger.info(f"✅ Loaded {len(social_ingest.enabled_curators)} curators")
    
    # Test curator lookup
    test_curator_id = "twitter:@0xdetweiler"
    if test_curator_id in social_ingest.enabled_curators:
        curator = social_ingest.enabled_curators[test_curator_id]
        logger.info(f"✅ Found curator: {curator['name']} ({curator['platform_data']['handle']})")
    else:
        logger.warning(f"❌ Curator {test_curator_id} not found")
    
    # Test message processing
    test_messages = [
        {
            'text': 'Just found $FOO on Raydium, looks like a solid play!',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/0xdetweiler/status/1234567890'
        },
        {
            'text': 'BAR token pumping on Uniswap, might be worth a look',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/0xdetweiler/status/1234567891'
        },
        {
            'text': 'Just had lunch, weather is nice today',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/0xdetweiler/status/1234567892'
        }
    ]
    
    for i, message in enumerate(test_messages):
        logger.info(f"\n📝 Testing message {i+1}: {message['text'][:50]}...")
        
        result = await social_ingest.process_social_signal(test_curator_id, message)
        
        if result:
            logger.info(f"✅ Created strand: {result['kind']}")
            logger.info(f"   Token: {result['content']['token']['ticker']}")
            logger.info(f"   Chain: {result['content']['token']['chain']}")
            logger.info(f"   Venue: {result['content']['venue']['dex']}")
            logger.info(f"   Has Chart: {result['content']['message']['has_chart']}")
        else:
            logger.info("❌ No strand created (no token found)")
    
    logger.info("\n🎉 Social Ingest Module test completed!")


async def test_curator_config():
    """Test curator configuration loading"""
    logger.info("🧪 Testing Curator Configuration...")
    
    # Test loading from config file
    social_ingest = SocialIngestModule(None, None)
    
    # Check if curators loaded correctly
    expected_curators = ['0xdetweiler', 'louiscooper', 'zinceth', 'cryptotrissy', 'cryptoxhunter']
    
    for curator_id in expected_curators:
        if curator_id in social_ingest.enabled_curators:
            curator = social_ingest.enabled_curators[curator_id]
            logger.info(f"✅ {curator['name']}: {curator['platforms']['twitter']['handle']} (weight: {curator['platforms']['twitter']['weight']})")
        else:
            logger.warning(f"❌ Curator {curator_id} not found")
    
    # Test platform-specific lookup
    twitter_curator_id = "twitter:@0xdetweiler"
    if twitter_curator_id in social_ingest.enabled_curators:
        curator = social_ingest.enabled_curators[twitter_curator_id]
        logger.info(f"✅ Platform lookup: {curator['name']} on {curator['platform']}")
    else:
        logger.warning(f"❌ Platform lookup failed for {twitter_curator_id}")
    
    logger.info("🎉 Curator Configuration test completed!")


async def main():
    """Run all tests"""
    logger.info("🚀 Starting Social Lowcap Pipeline Tests...\n")
    
    try:
        await test_curator_config()
        print("\n" + "="*50 + "\n")
        await test_social_ingest()
        
        logger.info("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
