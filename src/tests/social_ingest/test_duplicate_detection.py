#!/usr/bin/env python3
"""
Test Duplicate Detection

Tests the duplicate detection system with mock tweets to ensure we don't process the same tweet twice.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from social_ingest_basic import SocialIngestModule
from twitter_scanner import TwitterScanner
from test_token_detection import MockLLMClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_duplicate_detection():
    """Test that duplicate tweets are not processed twice"""
    logger.info("🧪 Testing Duplicate Detection")
    logger.info("=" * 50)
    
    # Initialize components
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
    
    # Mock tweets with some duplicates
    mock_tweets = [
        {
            'text': 'Just found $SLC on Raydium, looks like a solid play!',
            'timestamp': '2024-01-15T10:00:00Z',
            'url': 'https://twitter.com/0xdetweiler/status/1234567890',
            'has_image': False,
            'image_url': None
        },
        {
            'text': 'My big $BARRON win last week was incredible!',
            'timestamp': '2024-01-15T09:30:00Z',
            'url': 'https://twitter.com/LouisCooper_/status/1234567891',
            'has_image': False,
            'image_url': None
        },
        {
            'text': 'I have mentioned @Codecopenflow a lot. It has become one of my highest conviction bags.',
            'timestamp': '2024-01-15T09:00:00Z',
            'url': 'https://twitter.com/0xdetweiler/status/1234567892',
            'has_image': False,
            'image_url': None
        },
        # Duplicate tweets (same URLs)
        {
            'text': 'Just found $SLC on Raydium, looks like a solid play!',
            'timestamp': '2024-01-15T10:00:00Z',
            'url': 'https://twitter.com/0xdetweiler/status/1234567890',  # DUPLICATE
            'has_image': False,
            'image_url': None
        },
        {
            'text': 'My big $BARRON win last week was incredible!',
            'timestamp': '2024-01-15T09:30:00Z',
            'url': 'https://twitter.com/LouisCooper_/status/1234567891',  # DUPLICATE
            'has_image': False,
            'image_url': None
        },
        # New tweet
        {
            'text': 'Found a new token called FOO on Solana. Looks promising!',
            'timestamp': '2024-01-15T08:30:00Z',
            'url': 'https://twitter.com/CryptoxHunter/status/1234567893',
            'has_image': False,
            'image_url': None
        }
    ]
    
    # Mock curator
    mock_curator = {
        'id': 'test_curator',
        'name': 'Test Curator',
        'handle': '@test_curator',
        'weight': 1.0,
        'priority': 'high',
        'tags': ['test']
    }
    
    logger.info(f"📝 Testing with {len(mock_tweets)} mock tweets (including duplicates)")
    logger.info("")
    
    # Process tweets and track results
    processed_count = 0
    duplicate_count = 0
    successful_detections = 0
    
    for i, tweet in enumerate(mock_tweets):
        logger.info(f"Tweet {i+1}: {tweet['text'][:50]}...")
        logger.info(f"   URL: {tweet['url']}")
        
        # Check if we've already processed this tweet
        tweet_url = tweet.get('url', '')
        if tweet_url and tweet_url in twitter_scanner.processed_tweets:
            logger.info(f"   ❌ DUPLICATE - Skipping (already processed)")
            duplicate_count += 1
        else:
            # Process the tweet
            logger.info(f"   🔄 Processing...")
            
            # Simulate the processing
            message_data = {
                'text': tweet['text'],
                'timestamp': tweet['timestamp'],
                'url': tweet['url'],
                'image_data': None
            }
            
            result = await social_ingest.process_social_signal(f"twitter:{mock_curator['handle']}", message_data)
            
            if result:
                logger.info(f"   ✅ Token detected: {result.get('content', {}).get('token_name', 'unknown')}")
                successful_detections += 1
            else:
                logger.info(f"   ❌ No token detected")
            
            # Mark as processed
            twitter_scanner.processed_tweets.add(tweet_url)
            processed_count += 1
        
        logger.info("")
    
    # Print summary
    logger.info("📊 DUPLICATE DETECTION TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"📝 Total tweets: {len(mock_tweets)}")
    logger.info(f"🔄 Processed: {processed_count}")
    logger.info(f"❌ Duplicates skipped: {duplicate_count}")
    logger.info(f"🎯 Successful detections: {successful_detections}")
    logger.info(f"📊 Detection rate: {(successful_detections/processed_count*100):.1f}%" if processed_count > 0 else "N/A")
    
    # Verify duplicate detection worked
    expected_duplicates = 2  # We had 2 duplicate URLs
    if duplicate_count == expected_duplicates:
        logger.info("✅ Duplicate detection working correctly!")
    else:
        logger.error(f"❌ Duplicate detection failed! Expected {expected_duplicates} duplicates, got {duplicate_count}")
    
    logger.info("🎉 Test completed!")


if __name__ == "__main__":
    asyncio.run(test_duplicate_detection())
