#!/usr/bin/env python3
"""
Test @0xdetweiler - 3 Real Tweets

Gets the last 3 tweets from @0xdetweiler and examines them in detail
using the working method.
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


class DetweilerTester:
    """Test @0xdetweiler with 3 real tweets"""
    
    def __init__(self):
        self.cookies_file = "../../config/twitter_cookies.json"
        self.llm_client = MockLLMClient()
        self.curator_handle = '@0xdetweiler'
    
    async def test_detweiler_3_tweets(self):
        """Test @0xdetweiler with 3 real tweets"""
        logger.info("🐦 @0xdetweiler - 3 Real Tweets Test")
        logger.info("=" * 60)
        
        # Check if cookies exist
        if not os.path.exists(self.cookies_file):
            logger.error("❌ No cookies found. Please run twitter_auth_setup.py first")
            return False
        
        logger.info(f"✅ Found cookies file: {self.cookies_file}")
        
        # Load cookies
        with open(self.cookies_file, 'r') as f:
            cookie_data = json.load(f)
        
        try:
            # Get 3 real tweets from @0xdetweiler
            tweets = await self._get_detweiler_tweets(cookie_data, max_tweets=3)
            
            if not tweets:
                logger.error("❌ No tweets found for @0xdetweiler")
                return False
            
            logger.info(f"📝 Found {len(tweets)} real tweets from {self.curator_handle}")
            logger.info("")
            
            # Examine each tweet in detail
            for i, tweet in enumerate(tweets):
                logger.info(f"🔍 TWEET {i+1} ANALYSIS")
                logger.info("-" * 40)
                logger.info(f"📝 Text: {tweet['text']}")
                logger.info(f"🕒 Timestamp: {tweet['timestamp']}")
                logger.info(f"🔗 URL: {tweet['url']}")
                logger.info("")
                
                # Process with LLM
                logger.info("🤖 LLM Analysis:")
                result = await self._process_tweet_with_llm(tweet)
                
                if result:
                    logger.info(f"   ✅ Token detected: {result.get('token_name', 'unknown')}")
                    logger.info(f"   🌐 Network: {result.get('network', 'unknown')}")
                    logger.info(f"   💰 Contract: {result.get('contract_address', 'unknown')}")
                    logger.info(f"   😊 Sentiment: {result.get('sentiment', 'unknown')}")
                    logger.info(f"   🎯 Confidence: {result.get('confidence', 'unknown')}")
                    logger.info(f"   📈 Trading: {result.get('trading_intention', 'unknown')}")
                    
                    if result.get('handle_mentioned'):
                        logger.info(f"   🔍 Handle mentioned: {result.get('handle_mentioned')}")
                        logger.info(f"   🔍 Needs verification: {result.get('needs_verification', False)}")
                    
                    if result.get('has_chart'):
                        logger.info(f"   📊 Has chart: {result.get('has_chart')}")
                        logger.info(f"   📊 Chart type: {result.get('chart_type', 'unknown')}")
                    
                    logger.info(f"   ℹ️  Additional info: {result.get('additional_info', 'none')}")
                else:
                    logger.info("   ❌ No token detected")
                
                logger.info("")
                logger.info("=" * 60)
                logger.info("")
            
            # Summary
            logger.info("📊 @0xdetweiler ANALYSIS SUMMARY")
            logger.info("=" * 60)
            logger.info(f"📝 Total tweets analyzed: {len(tweets)}")
            logger.info(f"🎯 Tweets with tokens: {sum(1 for tweet in tweets if await self._process_tweet_with_llm(tweet))}")
            logger.info("")
            logger.info("🎉 Real Twitter analysis completed!")
            logger.info("✅ Successfully processed real tweets from @0xdetweiler!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error testing @0xdetweiler: {e}")
            return False
    
    async def _get_detweiler_tweets(self, cookie_data: dict, max_tweets: int = 3):
        """Get tweets from @0xdetweiler using the working method"""
        try:
            logger.info(f"👀 Getting tweets from: {self.curator_handle}")
            
            # Launch headless browser (EXACT same as working method)
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # Add cookies (EXACT same as working method)
            await context.add_cookies(cookie_data['cookies'])
            page = await context.new_page()
            
            # Navigate to curator profile (EXACT same as working method)
            profile_url = f"https://twitter.com/{self.curator_handle.replace('@', '')}"
            logger.info(f"🌐 Navigating to: {profile_url}")
            
            await page.goto(profile_url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for tweets to load with retry (EXACT same as working method)
            try:
                await page.wait_for_selector('[data-testid="tweet"]', timeout=15000)
            except Exception as e:
                logger.warning(f"⚠️  No tweets found initially: {e}")
                # Try waiting a bit more
                await page.wait_for_timeout(3000)
                try:
                    await page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
                except Exception:
                    logger.warning("⚠️  Still no tweets found, but continuing...")
            
            # Extract tweets (EXACT same as working method)
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
                                    url: url
                                }});
                            }}
                        }} catch (e) {{
                            console.error('Error extracting tweet:', e);
                        }}
                    }}
                    
                    return tweets;
                }}
            """)
            
            logger.info(f"📝 Found {len(tweets)} tweets from {self.curator_handle}")
            
            # Close browser (EXACT same as working method)
            await browser.close()
            await playwright.stop()
            
            return tweets
            
        except Exception as e:
            logger.error(f"Error getting tweets from {self.curator_handle}: {e}")
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


async def main():
    """Main test function"""
    tester = DetweilerTester()
    success = await tester.test_detweiler_3_tweets()
    
    if success:
        logger.info("🚀 @0xdetweiler analysis completed successfully!")
    else:
        logger.error("❌ @0xdetweiler analysis failed")


if __name__ == "__main__":
    asyncio.run(main())
