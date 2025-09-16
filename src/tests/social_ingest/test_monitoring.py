#!/usr/bin/env python3
"""
Test Twitter Monitoring

Quick test to verify the monitoring system works.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.intelligence.social_ingest.social_ingest_basic import SocialIngestModule
from src.intelligence.social_ingest.twitter_scanner import TwitterScanner
from src.intelligence.social_ingest.test_token_detection import MockLLMClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_monitoring():
    """Test the monitoring system with a short run"""
    logger.info("🧪 Testing Twitter Monitoring System")
    logger.info("=" * 50)
    
    try:
        # Initialize with mock components
        llm_client = MockLLMClient()
        
        social_ingest = SocialIngestModule(
            supabase_manager=None,
            llm_client=llm_client,
            config_path="src/config/twitter_curators.yaml"
        )
        
        twitter_scanner = TwitterScanner(
            social_ingest_module=social_ingest,
            config_path="src/config/twitter_curators.yaml"
        )
        
        logger.info(f"📊 Found {len(twitter_scanner.twitter_curators)} curators to monitor")
        
        # Test a single curator check (without starting full monitoring)
        if twitter_scanner.twitter_curators:
            curator = twitter_scanner.twitter_curators[0]
            logger.info(f"🔍 Testing curator: {curator['handle']}")
            
            # Initialize browser for testing
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Load cookies if they exist
            await twitter_scanner._load_cookies()
            twitter_scanner.page = page
            
            # Test curator check
            await twitter_scanner._check_curator(curator)
            
            await browser.close()
            await playwright.stop()
            
        logger.info("✅ Monitoring test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_monitoring())
