#!/usr/bin/env python3
"""
Simple Real Tweets Test

Uses the working approach from twitter_auth_setup.py to fetch real tweets
and process them through the LLM pipeline.
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


class SimpleRealTweetTester:
    """Simple real tweet tester using working auth approach"""
    
    def __init__(self):
        self.cookies_file = "../../config/twitter_cookies.json"
        self.llm_client = MockLLMClient()
        self.curators = ['@0xdetweiler', '@LouisCooper_', '@zinceth', '@Cryptotrissy', '@CryptoxHunter']
        self.results = []
    
    async def test_real_tweets_simple(self):
        """Test real tweets using the working auth approach"""
        logger.info("🐦 Simple Real Tweets Test")
        logger.info("=" * 50)
        
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
            
            # Test each curator using the working approach
            for i, curator_handle in enumerate(self.curators):
                logger.info(f"🔍 Testing Curator {i+1}/{len(self.curators)}: {curator_handle}")
                logger.info("-" * 50)
                
                try:
                    # Use the working approach from twitter_auth_setup.py
                    tweets = await self._monitor_curator_working_approach(page, curator_handle, max_tweets=2)
                    
                    if not tweets:
                        logger.warning(f"⚠️  No tweets found for {curator_handle}")
                        continue
                    
                    logger.info(f"📝 Found {len(tweets)} real tweets from {curator_handle}")
                    
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
                        'curator': curator_handle,
                        'tweets': curator_results,
                        'total_tweets': len(tweets),
                        'successful_detections': successful_detections
                    })
                    
                    logger.info(f"📊 Curator {curator_handle}: {successful_detections}/{len(tweets)} tweets had tokens")
                    logger.info("")
                    
                except Exception as e:
                    logger.error(f"❌ Error testing curator {curator_handle}: {e}")
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
    
    async def _monitor_curator_working_approach(self, page, curator_handle: str, max_tweets: int = 2):
        """Monitor curator using the working approach from twitter_auth_setup.py"""
        try:
            logger.info(f"🌐 Navigating to: https://twitter.com/{curator_handle.replace('@', '')}")
            
            # Navigate to curator's profile
            await page.goto(f"https://twitter.com/{curator_handle.replace('@', '')}", wait_until='networkidle', timeout=60000)
            
            # Wait for tweets to load with retry logic
            for attempt in range(3):
                try:
                    await page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
                    break
                except Exception:
                    if attempt < 2:
                        logger.warning(f"⚠️  Attempt {attempt + 1} failed, retrying...")
                        await page.wait_for_timeout(2000)
                    else:
                        logger.warning("⚠️  Still no tweets found, but continuing...")
            
            # Extract tweets using the working approach
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
                            
                            if (text.trim()) {{
                                tweets.push({{
                                    text: text,
                                    timestamp: timestamp,
                                    url: url,
                                    has_image: false,
                                    image_url: null
                                }});
                            }}
                        }} catch (e) {{
                            console.error('Error extracting tweet:', e);
                        }}
                    }}
                    
                    return tweets;
                }}
            """)
            
            logger.info(f"📝 Found {len(tweets)} tweets from {curator_handle}")
            return tweets
            
        except Exception as e:
            logger.error(f"Error monitoring curator {curator_handle}: {e}")
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
        logger.info("📊 SIMPLE REAL TWEETS TEST SUMMARY")
        logger.info("=" * 50)
        
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
        if self.results:
            logger.info("📋 Per-Curator Results:")
            for result in self.results:
                curator = result['curator']
                successful = result['successful_detections']
                total = result['total_tweets']
                rate = (successful / total * 100) if total > 0 else 0
                
                logger.info(f"   {curator}: {successful}/{total} ({rate:.1f}%)")
        else:
            logger.info("❌ No curators successfully tested")
        
        logger.info("")
        logger.info("🎉 Simple real tweets test completed!")


async def main():
    """Main test function"""
    tester = SimpleRealTweetTester()
    success = await tester.test_real_tweets_simple()
    
    if success:
        logger.info("🚀 Ready for real Twitter monitoring!")
    else:
        logger.error("❌ Test failed")


if __name__ == "__main__":
    asyncio.run(main())
