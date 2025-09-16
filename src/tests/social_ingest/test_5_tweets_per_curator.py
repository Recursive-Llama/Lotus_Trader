#!/usr/bin/env python3
"""
Test 5 Tweets Per Curator

Fetches 5 recent tweets from each configured curator and processes them through the LLM pipeline.
Tests the complete flow including duplicate detection.
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.intelligence.social_ingest.social_ingest_basic import SocialIngestModule
from src.intelligence.social_ingest.twitter_scanner import TwitterScanner
from src.intelligence.social_ingest.test_token_detection import MockLLMClient
from playwright.async_api import async_playwright

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TweetTester:
    """Test class for fetching and processing tweets from curators"""
    
    def __init__(self):
        self.llm_client = MockLLMClient()
        self.social_ingest = SocialIngestModule(
            supabase_manager=None,
            llm_client=self.llm_client,
            config_path="src/config/twitter_curators.yaml"
        )
        self.twitter_scanner = TwitterScanner(
            social_ingest_module=self.social_ingest,
            config_path="src/config/twitter_curators.yaml"
        )
        self.results = []
    
    async def test_all_curators(self, tweets_per_curator: int = 5):
        """Test fetching and processing tweets from all curators"""
        logger.info("🧪 Testing 5 Tweets Per Curator")
        logger.info("=" * 60)
        logger.info(f"📊 Testing {len(self.twitter_scanner.twitter_curators)} curators")
        logger.info(f"🎯 Fetching {tweets_per_curator} tweets per curator")
        logger.info("")
        
        # Initialize Playwright
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Load cookies if they exist
            await self.twitter_scanner._load_cookies()
            self.twitter_scanner.page = page
            
            # Test each curator
            for i, curator in enumerate(self.twitter_scanner.twitter_curators):
                logger.info(f"🔍 Testing Curator {i+1}/{len(self.twitter_scanner.twitter_curators)}: {curator['handle']}")
                logger.info("-" * 50)
                
                try:
                    # Fetch tweets from this curator
                    tweets = await self._fetch_curator_tweets(curator, tweets_per_curator)
                    
                    if not tweets:
                        logger.warning(f"⚠️  No tweets found for {curator['handle']}")
                        continue
                    
                    logger.info(f"📝 Found {len(tweets)} tweets from {curator['handle']}")
                    
                    # Process each tweet through the LLM pipeline
                    curator_results = []
                    for j, tweet in enumerate(tweets):
                        logger.info(f"   Tweet {j+1}: {tweet['text'][:80]}...")
                        
                        # Process the tweet
                        result = await self._process_tweet(curator, tweet)
                        curator_results.append({
                            'tweet': tweet,
                            'result': result,
                            'success': result is not None
                        })
                        
                        if result:
                            logger.info(f"   ✅ Token detected: {result.get('content', {}).get('token_name', 'unknown')}")
                        else:
                            logger.info(f"   ❌ No token detected")
                    
                    # Store results for this curator
                    self.results.append({
                        'curator': curator,
                        'tweets': curator_results,
                        'total_tweets': len(tweets),
                        'successful_detections': sum(1 for r in curator_results if r['success'])
                    })
                    
                    logger.info(f"📊 Curator {curator['handle']}: {sum(1 for r in curator_results if r['success'])}/{len(tweets)} tweets had tokens")
                    logger.info("")
                    
                except Exception as e:
                    logger.error(f"❌ Error testing curator {curator['handle']}: {e}")
                    continue
            
            # Print summary
            self._print_summary()
            
        finally:
            await browser.close()
            await playwright.stop()
    
    async def _fetch_curator_tweets(self, curator: Dict[str, Any], max_tweets: int) -> List[Dict[str, Any]]:
        """Fetch tweets from a specific curator"""
        try:
            handle = curator['handle']
            logger.debug(f"Fetching tweets from {handle}")
            
            # Navigate to curator's Twitter profile
            profile_url = f"https://twitter.com/{handle.replace('@', '')}"
            await self.twitter_scanner.page.goto(profile_url, wait_until='networkidle')
            
            # Wait for tweets to load
            await self.twitter_scanner.page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
            
            # Extract tweets
            tweets = await self.twitter_scanner.page.evaluate(f"""
                () => {{
                    const tweetElements = document.querySelectorAll('[data-testid="tweet"]');
                    const tweets = [];
                    
                    for (let i = 0; i < Math.min({max_tweets}, tweetElements.length); i++) {{
                        const tweetEl = tweetElements[i];
                        try {{
                            const textEl = tweetEl.querySelector('[data-testid="tweetText"]');
                            const text = textEl ? textEl.innerText : '';
                            
                            const timeEl = tweetEl.querySelector('time');
                            const timestamp = timeEl ? timeEl.getAttribute('datetime') : new Date().toISOString();
                            
                            const linkEl = tweetEl.querySelector('a[href*="/status/"]');
                            const url = linkEl ? 'https://twitter.com' + linkEl.getAttribute('href') : '';
                            
                            // Check for images
                            const imageEl = tweetEl.querySelector('[data-testid="tweetPhoto"] img');
                            const hasImage = !!imageEl;
                            const imageUrl = imageEl ? imageEl.src : null;
                            
                            if (text.trim()) {{
                                tweets.push({{
                                    text: text,
                                    timestamp: timestamp,
                                    url: url,
                                    has_image: hasImage,
                                    image_url: imageUrl
                                }});
                            }}
                        }} catch (e) {{
                            console.error('Error extracting tweet:', e);
                        }}
                    }}
                    
                    return tweets;
                }}
            """)
            
            return tweets
            
        except Exception as e:
            logger.error(f"Error fetching tweets from {curator['handle']}: {e}")
            return []
    
    async def _process_tweet(self, curator: Dict[str, Any], tweet: Dict[str, Any]) -> Any:
        """Process a single tweet through the LLM pipeline"""
        try:
            # Download image if present
            image_data = None
            if tweet.get('has_image') and tweet.get('image_url'):
                image_data = await self._download_image(tweet['image_url'])
            
            # Prepare message data
            message_data = {
                'text': tweet['text'],
                'timestamp': tweet['timestamp'],
                'url': tweet['url'],
                'image_data': image_data
            }
            
            # Process with social ingest module
            curator_id = f"twitter:{curator['handle']}"
            result = await self.social_ingest.process_social_signal(curator_id, message_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")
            return None
    
    async def _download_image(self, image_url: str) -> bytes:
        """Download image data from URL"""
        try:
            response = await self.twitter_scanner.page.request.get(image_url)
            if response.ok:
                return await response.body()
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
        return None
    
    def _print_summary(self):
        """Print test summary"""
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        
        total_curators = len(self.results)
        total_tweets = sum(r['total_tweets'] for r in self.results)
        total_detections = sum(r['successful_detections'] for r in self.results)
        
        logger.info(f"📈 Curators tested: {total_curators}")
        logger.info(f"📝 Total tweets processed: {total_tweets}")
        logger.info(f"🎯 Successful token detections: {total_detections}")
        logger.info(f"📊 Success rate: {(total_detections/total_tweets*100):.1f}%" if total_tweets > 0 else "N/A")
        logger.info("")
        
        # Per-curator breakdown
        for result in self.results:
            curator = result['curator']
            successful = result['successful_detections']
            total = result['total_tweets']
            rate = (successful/total*100) if total > 0 else 0
            
            logger.info(f"   {curator['handle']}: {successful}/{total} ({rate:.1f}%)")
        
        logger.info("")
        logger.info("🎉 Test completed!")


async def main():
    """Main test function"""
    tester = TweetTester()
    await tester.test_all_curators(tweets_per_curator=5)


if __name__ == "__main__":
    asyncio.run(main())
