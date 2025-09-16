"""
Test Token Detection with Sample Tweets

Test the LLM pipeline with tweets that are more likely to contain token mentions.
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timezone

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from social_ingest_basic import SocialIngestModule

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockSupabaseManager:
    """Mock Supabase manager for testing"""
    
    def create_strand(self, strand_data):
        """Mock strand creation"""
        logger.info(f"📝 Created strand: {strand_data['kind']}")
        logger.info(f"   Curator: {strand_data['content']['curator_id']}")
        logger.info(f"   Token: {strand_data['content']['token']['ticker']}")
        logger.info(f"   Chain: {strand_data['content']['token']['chain']}")
        logger.info(f"   Venue: {strand_data['content']['venue']['dex']}")
        logger.info(f"   Has Chart: {strand_data['content']['message']['has_chart']}")
        return {
            **strand_data,
            'id': f"strand_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'created_at': datetime.now(timezone.utc)
        }
    
    def update_curator_last_seen(self, curator_id):
        """Mock curator update"""
        logger.info(f"🔄 Updated last_seen for curator {curator_id}")


class MockLLMClient:
    """Mock LLM client that simulates real token detection"""
    
    async def generate_async(self, prompt, system_message=None, image=None):
        """Mock LLM response with realistic token detection"""
        # Look for common token patterns
        text = prompt.lower()
        
        # Check for specific token mentions
        if '$slc' in text or 'slc' in text:
            return json.dumps({
                "token_name": "SLC",
                "network": "solana",
                "contract_address": "So1aNa1234567890abcdef",
                "sentiment": "positive",
                "confidence": 0.85,
                "trading_intention": "buy",
                "has_chart": True,
                "chart_type": "price",
                "chart_analysis": "bullish pattern",
                "handle_mentioned": None,
                "needs_verification": False,
                "additional_info": "Mentioned with positive sentiment"
            })
        elif '$barron' in text or 'barron' in text:
            return json.dumps({
                "token_name": "BARRON",
                "network": "solana",
                "contract_address": "So1aNa9876543210fedcba",
                "sentiment": "positive",
                "confidence": 0.90,
                "trading_intention": "buy",
                "has_chart": False,
                "chart_type": None,
                "chart_analysis": None,
                "handle_mentioned": None,
                "needs_verification": False,
                "additional_info": "Mentioned as a win"
            })
        elif 'codecopenflow' in text:
            return json.dumps({
                "token_name": None,
                "network": None,
                "contract_address": None,
                "sentiment": "positive",
                "confidence": 0.8,
                "trading_intention": "buy",
                "has_chart": False,
                "chart_type": None,
                "chart_analysis": None,
                "handle_mentioned": "@Codecopenflow",
                "needs_verification": True,
                "additional_info": "Handle mention that might be a token"
            })
        elif '$pepe' in text or 'pepe' in text:
            return json.dumps({
                "token_name": "PEPE",
                "network": "ethereum",
                "contract_address": "0x1234567890abcdef",
                "sentiment": "positive",
                "confidence": 0.75,
                "trading_intention": "buy",
                "has_chart": True,
                "chart_type": "price",
                "chart_analysis": "breakout pattern",
                "handle_mentioned": None,
                "needs_verification": False,
                "additional_info": "Meme token mentioned"
            })
        elif '$doge' in text or 'doge' in text:
            return json.dumps({
                "token_name": "DOGE",
                "network": "ethereum",
                "contract_address": "0xabcdef1234567890",
                "sentiment": "positive",
                "confidence": 0.80,
                "trading_intention": "buy",
                "has_chart": False,
                "chart_type": None,
                "chart_analysis": None,
                "handle_mentioned": None,
                "needs_verification": False,
                "additional_info": "Classic meme token"
            })
        elif any(keyword in text for keyword in ['$', 'token', 'coin', 'pump', 'moon', 'buy', 'sell']):
            # Generic token detection
            return json.dumps({
                "token_name": "UNKNOWN",
                "network": "solana",
                "contract_address": "So1aNa0000000000000000",
                "sentiment": "neutral",
                "confidence": 0.50,
                "trading_intention": "unknown",
                "has_chart": False,
                "chart_type": None,
                "chart_analysis": None,
                "handle_mentioned": None,
                "needs_verification": False,
                "additional_info": "Generic token mention detected"
            })
        else:
            return "null"


async def test_sample_tweets():
    """Test with sample tweets that contain token mentions"""
    logger.info("🧪 Testing Token Detection with Sample Tweets")
    logger.info("=" * 60)
    
    # Initialize components
    supabase_manager = MockSupabaseManager()
    llm_client = MockLLMClient()
    social_ingest = SocialIngestModule(supabase_manager, llm_client)
    
    # Sample tweets with token mentions
    test_tweets = [
        {
            'curator_id': 'twitter:@0xdetweiler',
            'text': 'Just found $SLC on Raydium, looks like a solid play! Chart showing bullish breakout pattern.',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/0xdetweiler/status/1234567890'
        },
        {
            'curator_id': 'twitter:@LouisCooper_',
            'text': 'My big $BARRON win last week was incredible! Still holding for more gains.',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/LouisCooper_/status/1234567891'
        },
        {
            'curator_id': 'twitter:@zinceth',
            'text': 'PEPE is pumping hard right now! Time to ape in before it moons.',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/zinceth/status/1234567892'
        },
        {
            'curator_id': 'twitter:@Cryptotrissy',
            'text': 'DOGE to the moon! This is the way. 🚀',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/Cryptotrissy/status/1234567893'
        },
        {
            'curator_id': 'twitter:@CryptoxHunter',
            'text': 'Found a new token called FOO on Solana. Looks promising!',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/CryptoxHunter/status/1234567894'
        },
        {
            'curator_id': 'twitter:@test',
            'text': 'Just had lunch, weather is nice today. No crypto talk here.',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/test/status/1234567895'
        },
        {
            'curator_id': 'twitter:@0xdetweiler',
            'text': 'I have mentioned @Codecopenflow a lot. It has become one of my highest conviction bags for this year.',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'url': 'https://twitter.com/0xdetweiler/status/1234567896'
        }
    ]
    
    results = []
    
    for i, tweet_data in enumerate(test_tweets):
        logger.info(f"\n{'='*50}")
        logger.info(f"Test {i+1}: {tweet_data['curator_id']}")
        logger.info(f"{'='*50}")
        logger.info(f"📝 Tweet: {tweet_data['text']}")
        
        # Process through social ingest module
        result = await social_ingest.process_social_signal(tweet_data['curator_id'], tweet_data)
        
        if result:
            logger.info(f"✅ SUCCESS - Token detected and processed")
            results.append(True)
        else:
            logger.info(f"❌ FAILED - No token detected")
            results.append(False)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("📊 Token Detection Test Results")
    logger.info(f"{'='*60}")
    
    successful = sum(results)
    total = len(results)
    
    for i, (tweet_data, success) in enumerate(zip(test_tweets, results)):
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"Test {i+1} ({tweet_data['curator_id']}): {status}")
    
    logger.info(f"\n🎯 Results: {successful}/{total} tokens detected successfully")
    
    if successful > 0:
        logger.info("🎉 Token detection is working!")
    else:
        logger.warning("⚠️  Token detection needs improvement")


if __name__ == "__main__":
    asyncio.run(test_sample_tweets())
