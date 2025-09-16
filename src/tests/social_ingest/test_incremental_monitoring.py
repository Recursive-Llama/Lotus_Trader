#!/usr/bin/env python3
"""
Test Incremental Monitoring

Tests the proper incremental monitoring logic that tracks the most recent tweet
and only processes new tweets since the last check.
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


class IncrementalMonitoringTester:
    """Test incremental monitoring logic"""
    
    def __init__(self):
        self.curator_last_seen = {}  # {curator_id: last_tweet_url}
        self.processed_tweets = set()
        self.processed_count = 0
    
    def simulate_curator_check(self, curator_id: str, tweets: list, check_number: int):
        """Simulate checking a curator for new tweets"""
        logger.info(f"🔍 Check #{check_number} for {curator_id}")
        logger.info(f"   Available tweets: {[t['url'] for t in tweets]}")
        
        if not tweets:
            logger.info(f"   ❌ No tweets found")
            return []
        
        # Get the most recent tweet URL
        most_recent_tweet_url = tweets[0]['url']
        
        # Check if we've seen this curator before
        if curator_id in self.curator_last_seen:
            last_seen_url = self.curator_last_seen[curator_id]
            logger.info(f"   📝 Last seen tweet: {last_seen_url}")
            
            # If the most recent tweet is the same as last time, no new tweets
            if most_recent_tweet_url == last_seen_url:
                logger.info(f"   ✅ No new tweets (same as last check)")
                return []
            
            # Find new tweets (tweets after the last seen one)
            new_tweets = []
            for tweet in tweets:
                tweet_url = tweet['url']
                if tweet_url == last_seen_url:
                    break  # Stop when we reach the last seen tweet
                new_tweets.append(tweet)
            
            logger.info(f"   🆕 Found {len(new_tweets)} new tweets")
        else:
            # First time checking this curator - process only the most recent tweet
            new_tweets = [tweets[0]]  # Only process the most recent tweet
            logger.info(f"   🆕 First time checking, processing most recent tweet")
        
        # Process new tweets
        processed_tweets = []
        for tweet in new_tweets:
            tweet_url = tweet['url']
            if tweet_url not in self.processed_tweets:
                logger.info(f"   ✅ Processing: {tweet['text'][:50]}...")
                self.processed_tweets.add(tweet_url)
                self.processed_count += 1
                processed_tweets.append(tweet)
            else:
                logger.info(f"   ❌ Duplicate: {tweet['text'][:50]}...")
        
        # Update last seen tweet for this curator
        self.curator_last_seen[curator_id] = most_recent_tweet_url
        logger.info(f"   📝 Updated last seen: {most_recent_tweet_url}")
        logger.info("")
        
        return processed_tweets


async def test_incremental_monitoring():
    """Test the incremental monitoring logic"""
    logger.info("🧪 Testing Incremental Monitoring Logic")
    logger.info("=" * 60)
    
    tester = IncrementalMonitoringTester()
    
    # Simulate a curator's timeline over multiple checks
    curator_id = "twitter:@0xdetweiler"
    
    # Check 1: First time, 3 tweets available
    tweets_check1 = [
        {"url": "https://twitter.com/0xdetweiler/status/1003", "text": "Tweet 3 - Most recent"},
        {"url": "https://twitter.com/0xdetweiler/status/1002", "text": "Tweet 2 - Middle"},
        {"url": "https://twitter.com/0xdetweiler/status/1001", "text": "Tweet 1 - Oldest"}
    ]
    
    # Check 2: Same tweets (no new ones)
    tweets_check2 = [
        {"url": "https://twitter.com/0xdetweiler/status/1003", "text": "Tweet 3 - Most recent"},
        {"url": "https://twitter.com/0xdetweiler/status/1002", "text": "Tweet 2 - Middle"},
        {"url": "https://twitter.com/0xdetweiler/status/1001", "text": "Tweet 1 - Oldest"}
    ]
    
    # Check 3: 2 new tweets added
    tweets_check3 = [
        {"url": "https://twitter.com/0xdetweiler/status/1005", "text": "Tweet 5 - Newest"},
        {"url": "https://twitter.com/0xdetweiler/status/1004", "text": "Tweet 4 - New"},
        {"url": "https://twitter.com/0xdetweiler/status/1003", "text": "Tweet 3 - Previously seen"},
        {"url": "https://twitter.com/0xdetweiler/status/1002", "text": "Tweet 2 - Old"},
        {"url": "https://twitter.com/0xdetweiler/status/1001", "text": "Tweet 1 - Oldest"}
    ]
    
    # Check 4: 1 more new tweet
    tweets_check4 = [
        {"url": "https://twitter.com/0xdetweiler/status/1006", "text": "Tweet 6 - Latest"},
        {"url": "https://twitter.com/0xdetweiler/status/1005", "text": "Tweet 5 - Previously seen"},
        {"url": "https://twitter.com/0xdetweiler/status/1004", "text": "Tweet 4 - Previously seen"},
        {"url": "https://twitter.com/0xdetweiler/status/1003", "text": "Tweet 3 - Old"},
        {"url": "https://twitter.com/0xdetweiler/status/1002", "text": "Tweet 2 - Old"},
        {"url": "https://twitter.com/0xdetweiler/status/1001", "text": "Tweet 1 - Oldest"}
    ]
    
    # Run the checks
    logger.info("📅 Timeline Simulation:")
    logger.info("")
    
    # Check 1
    processed1 = tester.simulate_curator_check(curator_id, tweets_check1, 1)
    
    # Check 2
    processed2 = tester.simulate_curator_check(curator_id, tweets_check2, 2)
    
    # Check 3
    processed3 = tester.simulate_curator_check(curator_id, tweets_check3, 3)
    
    # Check 4
    processed4 = tester.simulate_curator_check(curator_id, tweets_check4, 4)
    
    # Print summary
    logger.info("📊 INCREMENTAL MONITORING TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"🔍 Total checks: 4")
    logger.info(f"✅ Total tweets processed: {tester.processed_count}")
    logger.info(f"📝 Check 1 (first time): {len(processed1)} tweets")
    logger.info(f"📝 Check 2 (no new): {len(processed2)} tweets")
    logger.info(f"📝 Check 3 (2 new): {len(processed3)} tweets")
    logger.info(f"📝 Check 4 (1 new): {len(processed4)} tweets")
    logger.info("")
    logger.info("🎯 Expected behavior:")
    logger.info("   ✅ First check: Process 1 tweet (most recent)")
    logger.info("   ✅ Second check: Process 0 tweets (no new)")
    logger.info("   ✅ Third check: Process 2 tweets (new ones)")
    logger.info("   ✅ Fourth check: Process 1 tweet (new one)")
    
    # Verify results
    expected_processed = 4  # 1 + 0 + 2 + 1
    if tester.processed_count == expected_processed:
        logger.info("✅ Incremental monitoring working correctly!")
    else:
        logger.error(f"❌ Expected {expected_processed} processed tweets, got {tester.processed_count}")
    
    logger.info("🎉 Test completed!")


if __name__ == "__main__":
    asyncio.run(test_incremental_monitoring())
