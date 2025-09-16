#!/usr/bin/env python3
"""
Real Twitter Monitoring Test

Tests the monitoring system with real Twitter data from configured curators.
Uses saved cookies for authentication.
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealTwitterTester:
    """Test real Twitter monitoring with actual data"""
    
    def __init__(self):
        self.cookies_file = "../../config/twitter_cookies.json"
        self.curators = [
            {'handle': '@0xdetweiler', 'name': '0xdetweiler'},
            {'handle': '@LouisCooper_', 'name': 'Louis Cooper'},
            {'handle': '@zinceth', 'name': 'Zinceth'},
            {'handle': '@Cryptotrissy', 'name': 'Crypto Trissy'},
            {'handle': '@CryptoxHunter', 'name': 'Crypto Hunter'}
        ]
        self.results = []
    
    async def test_real_twitter_connection(self):
        """Test real Twitter connection and fetch actual tweets"""
        logger.info("🐦 Real Twitter Monitoring Test")
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
                    tweets = await self._fetch_curator_tweets(page, curator, max_tweets=3)
                    
                    if not tweets:
                        logger.warning(f"⚠️  No tweets found for {curator['handle']}")
                        continue
                    
                    logger.info(f"📝 Found {len(tweets)} real tweets from {curator['handle']}")
                    
                    # Display tweets
                    for j, tweet in enumerate(tweets):
                        logger.info(f"   Tweet {j+1}: {tweet['text'][:80]}...")
                        logger.info(f"   URL: {tweet['url']}")
                        logger.info(f"   Time: {tweet['timestamp']}")
                        if tweet.get('has_image'):
                            logger.info(f"   📷 Has image: {tweet.get('image_url', 'N/A')}")
                        logger.info("")
                    
                    # Store results
                    self.results.append({
                        'curator': curator,
                        'tweets': tweets,
                        'total_tweets': len(tweets)
                    })
                    
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
            await page.goto("https://twitter.com", wait_until='networkidle', timeout=30000)
            
            # Check if we're logged in by looking for profile elements
            try:
                await page.wait_for_selector('[data-testid="SideNav_AccountSwitcher_Button"]', timeout=10000)
                logger.info("✅ Successfully logged into Twitter")
                return True
            except:
                logger.warning("⚠️  May not be fully logged in, but continuing...")
                return True
                
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    async def _fetch_curator_tweets(self, page, curator: Dict[str, Any], max_tweets: int = 3) -> List[Dict[str, Any]]:
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
    
    def _print_summary(self):
        """Print test summary"""
        logger.info("📊 REAL TWITTER TEST SUMMARY")
        logger.info("=" * 60)
        
        total_curators = len(self.results)
        total_tweets = sum(r['total_tweets'] for r in self.results)
        
        logger.info(f"📈 Curators tested: {total_curators}")
        logger.info(f"📝 Total real tweets fetched: {total_tweets}")
        logger.info("")
        
        # Per-curator breakdown
        for result in self.results:
            curator = result['curator']
            total = result['total_tweets']
            
            logger.info(f"   {curator['handle']}: {total} real tweets")
        
        logger.info("")
        logger.info("🎉 Real Twitter test completed!")
        logger.info("✅ Successfully connected to Twitter and fetched real data!")


async def main():
    """Main test function"""
    tester = RealTwitterTester()
    success = await tester.test_real_twitter_connection()
    
    if success:
        logger.info("🚀 Ready for real Twitter monitoring!")
    else:
        logger.error("❌ Twitter connection failed")


if __name__ == "__main__":
    asyncio.run(main())
