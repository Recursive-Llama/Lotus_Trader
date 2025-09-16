#!/usr/bin/env python3
"""
Twitter Monitor Runner

Simple script to start the Twitter monitoring system.
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
from src.llm_integration.llm_client import LLMClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('twitter_monitor.log')
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Main monitoring function"""
    logger.info("🚀 Starting Twitter Social Lowcap Monitor")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize components
        logger.info("🔧 Initializing components...")
        
        # Mock LLM client for now (replace with real one)
        llm_client = LLMClient()
        
        # Initialize social ingest module
        social_ingest = SocialIngestModule(
            supabase_manager=None,  # Mock for now
            llm_client=llm_client,
            config_path="src/config/twitter_curators.yaml"
        )
        
        # Initialize Twitter scanner
        twitter_scanner = TwitterScanner(
            social_ingest_module=social_ingest,
            config_path="src/config/twitter_curators.yaml"
        )
        
        logger.info("✅ Components initialized successfully")
        logger.info(f"📊 Monitoring {len(twitter_scanner.twitter_curators)} curators")
        
        # Start monitoring
        logger.info("🔄 Starting Twitter monitoring...")
        await twitter_scanner.start_monitoring()
        
    except KeyboardInterrupt:
        logger.info("⏹️  Monitoring stopped by user")
    except Exception as e:
        logger.error(f"❌ Error in monitoring: {e}")
    finally:
        logger.info("🛑 Shutting down Twitter monitor")


if __name__ == "__main__":
    asyncio.run(main())

