"""
Test Twitter Connection

Simple test to verify Twitter authentication and curator monitoring works.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.intelligence.social_ingest.twitter_auth_setup import TwitterAuthSetup
from src.intelligence.social_ingest.twitter_scanner import TwitterScanner
from src.intelligence.social_ingest.social_ingest_basic import SocialIngestModule

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        if "FOO" in prompt or "BAR" in prompt or "$" in prompt:
            return '{"token_name": "FOO", "network": "solana", "contract_address": "So1aNa1234567890abcdef", "sentiment": "positive", "confidence": 0.85, "trading_intention": "buy", "has_chart": true, "chart_type": "price", "chart_analysis": "bullish pattern", "additional_info": "New launch on Raydium"}'
        else:
            return 'null'


async def test_twitter_connection():
    """Test Twitter connection and authentication"""
    logger.info("🧪 Testing Twitter Connection...")
    
    # Test 1: Check if cookies exist
    cookies_file = "src/config/twitter_cookies.json"
    if not os.path.exists(cookies_file):
        logger.warning("❌ No cookies found. Run twitter_auth_setup.py first")
        return False
    
    # Test 2: Test saved cookies
    auth_setup = TwitterAuthSetup()
    success = await auth_setup.test_saved_cookies()
    
    if not success:
        logger.error("❌ Cookie test failed")
        return False
    
    logger.info("✅ Twitter connection test passed!")
    return True


async def test_curator_monitoring():
    """Test monitoring a specific curator"""
    logger.info("👀 Testing Curator Monitoring...")
    
    # Test monitoring @0xdetweiler
    auth_setup = TwitterAuthSetup()
    success = await auth_setup.monitor_curator("@0xdetweiler", max_tweets=3)
    
    if success:
        logger.info("✅ Curator monitoring test passed!")
    else:
        logger.error("❌ Curator monitoring test failed")
    
    return success


async def test_full_pipeline():
    """Test the full social lowcap pipeline with real Twitter"""
    logger.info("🚀 Testing Full Social Lowcap Pipeline...")
    
    try:
        # Initialize components
        supabase_manager = MockSupabaseManager()
        llm_client = MockLLMClient()
        
        # Create social ingest module
        social_ingest = SocialIngestModule(supabase_manager, llm_client)
        
        # Create Twitter scanner
        scanner = TwitterScanner(social_ingest)
        
        # Test single curator check
        logger.info("🔍 Testing single curator check...")
        await scanner._check_curator(scanner.twitter_curators[0])
        
        logger.info("✅ Full pipeline test completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Full pipeline test failed: {e}")
        return False


async def main():
    """Main test function"""
    logger.info("🐦 Twitter Connection Tests")
    logger.info("=" * 50)
    
    # Test 1: Twitter connection
    logger.info("\n1️⃣ Testing Twitter Connection...")
    connection_ok = await test_twitter_connection()
    
    if not connection_ok:
        logger.error("❌ Twitter connection failed. Please run twitter_auth_setup.py first")
        return
    
    # Test 2: Curator monitoring
    logger.info("\n2️⃣ Testing Curator Monitoring...")
    monitoring_ok = await test_curator_monitoring()
    
    if not monitoring_ok:
        logger.error("❌ Curator monitoring failed")
        return
    
    # Test 3: Full pipeline
    logger.info("\n3️⃣ Testing Full Pipeline...")
    pipeline_ok = await test_full_pipeline()
    
    if pipeline_ok:
        logger.info("\n🎉 All tests passed! Twitter connection is working!")
        logger.info("   You can now run the full social lowcap scanner")
    else:
        logger.error("\n❌ Some tests failed. Check the logs above.")


if __name__ == "__main__":
    asyncio.run(main())
