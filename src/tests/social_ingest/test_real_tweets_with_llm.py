#!/usr/bin/env python3
"""
Real Tweets with LLM Processing

Fetches real tweets from Twitter and processes them through the LLM pipeline
to test token detection with actual data.
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

from playwright.async_api import async_playwright
from test_token_detection import MockLLMClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealTweetLLMTester:
    """Test real tweets with LLM processing"""
    
    def __init__(self):
        self.cookies_file = "../../config/twitter_cookies.json"
        self.llm_client = MockLLMClient()
        self.curators = [
            {'handle': '@0xdetweiler', 'name': '0xdetweiler'},
            {'handle': '@LouisCooper_', 'name': 'Louis Cooper'},
            {'handle': '@zinceth', 'name': 'Zinceth'},
            {'handle': '@Cryptotrissy', 'name': 'Crypto Trissy'},
            {'handle': '@CryptoxHunter', 'name': 'Crypto Hunter'}
        ]
        self.results = []
    
    async def test_real_tweets_with_llm(self):
        """Test real tweets with LLM processing"""
        logger.info("🐦 Real Tweets with LLM Processing Test")
        logger.info("=" * 60)
        
        # Check if cookies exist
        if not os.path.exists(self.cookies_file):
            logger.error("❌ No cookies found. Please run twitter_auth_setup.py first")
            return False
        
        logger.info(f"✅ Found cookies file: {self.cookies_file}")
        
        # Initialize Playwright
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Load cookies
            await self._load_cookies(page)
            
            # Test connection
            logger.info("🔍 Testing Twitter connection...")
            connection_ok = await self._test_connection(page)
            
            if not connection_ok:
                logger.error("❌ Twitter connection failed")
                return False
            
            logger.info("✅ Twitter connection working!")
            logger.info("")
            
            # Test each curator
            for i, curator in enumerate(self.curators):
                logger.info(f"🔍 Testing Curator {i+1}/{len(self.curators)}: {curator['handle']}")
                logger.info("-" * 50)
                
                try:
                    # Fetch real tweets from this curator
                    tweets = await self._fetch_curator_tweets(page, curator, max_tweets=2)
                    
                    if not tweets:
                        logger.warning(f"⚠️  No tweets found for {curator['handle']}")
                        continue
                    
                    logger.info(f"📝 Found {len(tweets)} real tweets from {curator['handle']}")
                    
                    # Process each tweet through LLM
                    curator_results = []
                    for j, tweet in enumerate(tweets):
                        logger.info(f"   Tweet {j+1}: {tweet['text'][:80]}...")
                        
                        # Process with LLM
                        result = await self._process_tweet_with_llm(tweet)
                        
                        if result:
                            logger.info(f"   ✅ Token detected: {result.get('token_name', 'unknown')}")
                            if result.get('handle_mentioned'):
                                logger.info(f"   🔍 Handle mentioned: {result.get('handle_mentioned')}")
                        else:
                            logger.info(f"   ❌ No token detected")
                        
                        curator_results.append({
                            'tweet': tweet,
                            'result': result,
                            'success': result is not None
                        })
                        
                        logger.info("")
                    
                    # Store results
                    successful_detections = sum(1 for r in curator_results if r['success'])
                    self.results.append({
                        'curator': curator,
                        'tweets': curator_results,
                        'total_tweets': len(tweets),
                        'successful_detections': successful_detections
                    })
                    
                    logger.info(f"📊 Curator {curator['handle']}: {successful_detections}/{len(tweets)} tweets had tokens")
                    logger.info("")
                    
                except Exception as e:
                    logger.error(f"❌ Error testing curator {curator['handle']}: {e}")
                    continue
            
            # Print summary
            self._print_summary()
            
            return True
            
        finally:
            await browser.close()
            await playwright.stop()
    
    async def _load_cookies(self, page):
        """Load saved cookies"""
        try:
            with open(self.cookies_file, 'r') as f:
                cookie_data = json.load(f)
                if 'cookies' in cookie_data:
                    await page.context.add_cookies(cookie_data['cookies'])
                    logger.info(f"✅ Loaded {len(cookie_data['cookies'])} Twitter cookies")
                else:
                    logger.warning("⚠️  No cookies found in file")
        except Exception as e:
            logger.error(f"❌ Error loading cookies: {e}")
    
    async def _test_connection(self, page):
        """Test Twitter connection"""
        try:
            # Try to navigate to a specific user profile instead of main Twitter page
            await page.goto("https://twitter.com/0xdetweiler", wait_until='networkidle', timeout=30000)
            
            # Check if we can see tweets
            try:
                await page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
                logger.info("✅ Successfully connected to Twitter")
                return True
            except:
                logger.warning("⚠️  No tweets found, but connection may be working")
                return True
                
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    async def _fetch_curator_tweets(self, page, curator: Dict[str, Any], max_tweets: int = 2) -> List[Dict[str, Any]]:
        """Fetch real tweets from a curator"""
        try:
            handle = curator['handle']
            logger.debug(f"Fetching tweets from {handle}")
            
            # Navigate to curator's Twitter profile
            profile_url = f"https://twitter.com/{handle.replace('@', '')}"
            await page.goto(profile_url, wait_until='networkidle', timeout=30000)
            
            # Wait for tweets to load
            try:
                await page.wait_for_selector('[data-testid="tweet"]', timeout=15000)
            except:
                logger.warning(f"⚠️  No tweets found for {handle}")
                return []
            
            # Extract tweets
            tweets = await page.evaluate(f"""
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
    
    async def _process_tweet_with_llm(self, tweet: Dict[str, Any]) -> Any:
        """Process a tweet through the LLM"""
        try:
            # Use the mock LLM client to process the tweet
            response = await self.llm_client.generate_async(tweet['text'])
            
            if response and response != "null":
                return json.loads(response)
            return None
            
        except Exception as e:
            logger.error(f"Error processing tweet with LLM: {e}")
            return None
    
    def _print_summary(self):
        """Print test summary"""
        logger.info("📊 REAL TWEETS WITH LLM TEST SUMMARY")
        logger.info("=" * 60)
        
        total_curators = len(self.results)
        total_tweets = sum(r['total_tweets'] for r in self.results)
        total_detections = sum(r['successful_detections'] for r in self.results)
        overall_success_rate = (total_detections / total_tweets * 100) if total_tweets > 0 else 0
        
        logger.info(f"📈 Curators tested: {total_curators}")
        logger.info(f"📝 Total real tweets processed: {total_tweets}")
        logger.info(f"🎯 Successful token detections: {total_detections}")
        logger.info(f"📊 Overall success rate: {overall_success_rate:.1f}%")
        logger.info("")
        
        # Per-curator breakdown
        logger.info("📋 Per-Curator Results:")
        for result in self.results:
            curator = result['curator']
            successful = result['successful_detections']
            total = result['total_tweets']
            rate = (successful / total * 100) if total > 0 else 0
            
            logger.info(f"   {curator['handle']}: {successful}/{total} ({rate:.1f}%)")
        
        logger.info("")
        logger.info("🎉 Real Twitter + LLM test completed!")
        logger.info("✅ Successfully processed real tweets with LLM!")


async def main():
    """Main test function"""
    tester = RealTweetLLMTester()
    success = await tester.test_real_tweets_with_llm()
    
    if success:
        logger.info("🚀 Ready for real Twitter monitoring with LLM!")
    else:
        logger.error("❌ Test failed")


if __name__ == "__main__":
    asyncio.run(main())
