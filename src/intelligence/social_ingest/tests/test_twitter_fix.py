"""
Test Twitter Fix - Simple and Direct

Test if the cookie loading fix actually works.
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

async def test_twitter_connection():
    """Test Twitter connection with the fixed approach"""
    try:
        print("🧪 Testing Twitter connection with fixed cookie loading...")
        
        # Step 1: Launch browser
        print("1. Launching browser...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        
        # Step 2: Create context
        print("2. Creating context...")
        context = await browser.new_context()
        
        # Step 3: Load cookies
        print("3. Loading cookies...")
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
        
        # Step 4: Create page from context
        print("4. Creating page from context...")
        page = await context.new_page()
        
        # Step 5: Test connection
        print("5. Testing connection to Twitter...")
        await page.goto("https://twitter.com", wait_until='domcontentloaded', timeout=30000)
        print("   ✅ Successfully loaded Twitter")
        
        # Step 6: Test curator access
        print("6. Testing curator access...")
        await page.goto("https://twitter.com/0xdetweiler", wait_until='domcontentloaded', timeout=30000)
        print("   ✅ Successfully loaded @0xdetweiler profile")
        
        # Step 7: Check for tweets
        print("7. Checking for tweets...")
        try:
            await page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
            tweets = await page.query_selector_all('[data-testid="tweet"]')
            print(f"   ✅ Found {len(tweets)} tweets")
        except Exception as e:
            print(f"   ⚠️  No tweets found: {e}")
        
        # Cleanup
        await browser.close()
        print("✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Main test function"""
    success = await test_twitter_connection()
    if success:
        print("\n🎉 Twitter fix is working!")
    else:
        print("\n💥 Twitter fix needs more work!")

if __name__ == "__main__":
    asyncio.run(main())
