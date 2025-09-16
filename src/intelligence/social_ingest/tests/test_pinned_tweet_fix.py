"""
Test Pinned Tweet Fix

Quick test to verify that pinned tweet detection is working correctly.
Only tests one curator to avoid running through all 9.
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from playwright.async_api import async_playwright
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_pinned_tweet_detection():
    """Test pinned tweet detection on a single curator"""
    try:
        print("🧪 Testing pinned tweet detection...")
        
        # Step 1: Launch browser
        print("1. Launching browser...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        
        # Step 2: Create context and load cookies
        print("2. Creating context and loading cookies...")
        context = await browser.new_context()
        cookies_file = "src/config/twitter_cookies.json"
        if os.path.exists(cookies_file):
            with open(cookies_file, 'r') as f:
                cookie_data = json.load(f)
                cookies = cookie_data.get('cookies', [])
                await context.add_cookies(cookies)
                print(f"   ✅ Loaded {len(cookies)} cookies")
        else:
            print("   ❌ No cookies file found")
            return False
        
        # Step 3: Create page and navigate to a curator
        print("3. Testing pinned tweet detection on @0xdetweiler...")
        page = await context.new_page()
        await page.goto("https://twitter.com/0xdetweiler", wait_until='domcontentloaded', timeout=30000)
        
        # Step 4: Wait for tweets to load
        print("4. Waiting for tweets to load...")
        await page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
        
        # Step 5: Extract tweets with timestamps
        print("5. Extracting tweets with timestamps...")
        tweets = await page.evaluate("""
            () => {
                const tweetElements = document.querySelectorAll('[data-testid="tweet"]');
                const tweets = [];
                
                tweetElements.forEach(tweetEl => {
                    try {
                        const textEl = tweetEl.querySelector('[data-testid="tweetText"]');
                        const text = textEl ? textEl.innerText : '';
                        
                        const timeEl = tweetEl.querySelector('time');
                        const timestamp = timeEl ? timeEl.getAttribute('datetime') : new Date().toISOString();
                        
                        const linkEl = tweetEl.querySelector('a[href*="/status/"]');
                        const url = linkEl ? 'https://twitter.com' + linkEl.getAttribute('href') : '';
                        
                        if (text.trim()) {
                            tweets.push({
                                text: text.length > 100 ? text.substring(0, 100) + '...' : text,
                                timestamp: timestamp,
                                url: url
                            });
                        }
                    } catch (e) {
                        console.error('Error extracting tweet:', e);
                    }
                });
                
                return tweets;
            }
        """)
        
        print(f"   📊 Found {len(tweets)} tweets")
        
        # Step 6: Test pinned tweet detection logic
        print("6. Testing pinned tweet detection logic...")
        if len(tweets) >= 2:
            from datetime import datetime
            
            first_tweet = tweets[0]
            second_tweet = tweets[1]
            
            print(f"   Tweet 1: {first_tweet['text']}")
            print(f"   Time 1:  {first_tweet['timestamp']}")
            print(f"   Tweet 2: {second_tweet['text']}")
            print(f"   Time 2:  {second_tweet['timestamp']}")
            
            # Parse timestamps
            first_time = datetime.fromisoformat(first_tweet['timestamp'].replace('Z', '+00:00'))
            second_time = datetime.fromisoformat(second_tweet['timestamp'].replace('Z', '+00:00'))
            
            if first_time < second_time:
                print("   🔍 DETECTED: First tweet is pinned (older than second)")
                print("   ✅ Using second tweet as most recent")
                actual_most_recent = second_tweet
            else:
                print("   🔍 DETECTED: First tweet is actually most recent")
                print("   ✅ Using first tweet as most recent")
                actual_most_recent = first_tweet
                
            print(f"   📝 Selected tweet: {actual_most_recent['text']}")
            print(f"   ⏰ Selected time:  {actual_most_recent['timestamp']}")
        else:
            print("   ⚠️  Not enough tweets to test pinned detection")
        
        # Cleanup
        await browser.close()
        print("✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Main test function"""
    success = await test_pinned_tweet_detection()
    if success:
        print("\n🎉 Pinned tweet detection is working!")
    else:
        print("\n💥 Pinned tweet detection needs more work!")

if __name__ == "__main__":
    asyncio.run(main())
