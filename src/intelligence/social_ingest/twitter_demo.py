"""
Twitter Demo - Working Example

This demonstrates the complete Twitter connection and curator monitoring.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from twitter_auth_setup import TwitterAuthSetup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def demo_twitter_monitoring():
    """Demo Twitter monitoring with real connection"""
    logger.info("🐦 Twitter Social Lowcap Demo")
    logger.info("=" * 50)
    
    # Check if cookies exist
    cookies_file = "../../config/twitter_cookies.json"
    if not os.path.exists(cookies_file):
        logger.error("❌ No cookies found. Please run twitter_auth_setup.py first")
        return
    
    # Initialize auth setup
    auth_setup = TwitterAuthSetup()
    
    # Test connection
    logger.info("🔍 Testing Twitter connection...")
    connection_ok = await auth_setup.test_saved_cookies()
    
    if not connection_ok:
        logger.error("❌ Twitter connection failed")
        return
    
    logger.info("✅ Twitter connection working!")
    
    # Monitor our configured curators
    curators = ["@0xdetweiler", "@LouisCooper_", "@zinceth", "@Cryptotrissy", "@CryptoxHunter"]
    
    for curator in curators:
        logger.info(f"\n👀 Monitoring {curator}...")
        try:
            success = await auth_setup.monitor_curator(curator, max_tweets=2)
            if success:
                logger.info(f"✅ Successfully monitored {curator}")
            else:
                logger.warning(f"⚠️  Issues monitoring {curator}")
        except Exception as e:
            logger.error(f"❌ Error monitoring {curator}: {e}")
    
    logger.info("\n🎉 Twitter monitoring demo complete!")
    logger.info("   The system is ready for real-time monitoring")


async def main():
    """Main demo function"""
    await demo_twitter_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
