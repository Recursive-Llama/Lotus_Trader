#!/usr/bin/env python3
"""
Simple Duplicate Detection Test

Tests the duplicate detection logic without complex imports.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleDuplicateTester:
    """Simple duplicate detection tester"""
    
    def __init__(self):
        self.processed_tweets = set()
        self.processed_count = 0
        self.duplicate_count = 0
    
    def process_tweet(self, tweet_url: str, tweet_text: str) -> bool:
        """Process a tweet, checking for duplicates"""
        if tweet_url in self.processed_tweets:
            logger.info(f"❌ DUPLICATE - Skipping: {tweet_text[:50]}...")
            self.duplicate_count += 1
            return False
        else:
            logger.info(f"✅ NEW - Processing: {tweet_text[:50]}...")
            self.processed_tweets.add(tweet_url)
            self.processed_count += 1
            return True
    
    def print_summary(self, total_tweets: int):
        """Print test summary"""
        logger.info("")
        logger.info("📊 DUPLICATE DETECTION TEST SUMMARY")
        logger.info("=" * 50)
        logger.info(f"📝 Total tweets: {total_tweets}")
        logger.info(f"✅ Processed: {self.processed_count}")
        logger.info(f"❌ Duplicates skipped: {self.duplicate_count}")
        logger.info(f"📊 Duplicate rate: {(self.duplicate_count/total_tweets*100):.1f}%")


async def test_duplicate_detection():
    """Test duplicate detection with mock data"""
    logger.info("🧪 Testing Duplicate Detection Logic")
    logger.info("=" * 50)
    
    tester = SimpleDuplicateTester()
    
    # Mock tweets with duplicates
    mock_tweets = [
        ("https://twitter.com/user/status/123", "Just found $SLC on Raydium!"),
        ("https://twitter.com/user/status/124", "My big $BARRON win was incredible!"),
        ("https://twitter.com/user/status/125", "I mentioned @Codecopenflow a lot."),
        ("https://twitter.com/user/status/123", "Just found $SLC on Raydium!"),  # DUPLICATE
        ("https://twitter.com/user/status/124", "My big $BARRON win was incredible!"),  # DUPLICATE
        ("https://twitter.com/user/status/126", "Found a new token called FOO!"),  # NEW
        ("https://twitter.com/user/status/123", "Just found $SLC on Raydium!"),  # DUPLICATE AGAIN
    ]
    
    logger.info(f"📝 Testing with {len(mock_tweets)} tweets (including duplicates)")
    logger.info("")
    
    # Process each tweet
    for i, (url, text) in enumerate(mock_tweets):
        logger.info(f"Tweet {i+1}:")
        tester.process_tweet(url, text)
    
    # Print results
    tester.print_summary(len(mock_tweets))
    
    # Verify expected results
    expected_duplicates = 3  # We have 3 duplicate URLs
    if tester.duplicate_count == expected_duplicates:
        logger.info("✅ Duplicate detection working correctly!")
    else:
        logger.error(f"❌ Expected {expected_duplicates} duplicates, got {tester.duplicate_count}")
    
    logger.info("🎉 Test completed!")


if __name__ == "__main__":
    asyncio.run(test_duplicate_detection())
