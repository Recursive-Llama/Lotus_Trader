"""
Twitter Authentication Setup Script

This script helps you authenticate with Twitter using a headed browser,
save cookies, and test the connection for the social lowcap scanner.
"""

import asyncio
import json
import os
import logging
from datetime import datetime, timezone
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class TwitterAuthSetup:
    """
    Twitter authentication setup using Playwright
    
    This class helps you:
    1. Open a headed browser to log into Twitter
    2. Save cookies for future headless use
    3. Test the connection with saved cookies
    """
    
    def __init__(self, cookies_file: str = None):
        if cookies_file is None:
            # Try different possible paths
            possible_paths = [
                "src/config/twitter_cookies.json",
                "../../config/twitter_cookies.json",
                "config/twitter_cookies.json"
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    cookies_file = path
                    break
            else:
                cookies_file = "src/config/twitter_cookies.json"  # Default
        self.cookies_file = cookies_file
        self.browser: Browser = None
        self.page: Page = None
    
    async def setup_authentication(self):
        """Open headed browser for Twitter authentication"""
        try:
            logger.info("🔐 Starting Twitter authentication setup...")
            
            # Launch headed browser
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=False)
            
            # Create new page
            self.page = await self.browser.new_page()
            
            # Navigate to Twitter login
            logger.info("🌐 Navigating to Twitter login...")
            await self.page.goto("https://twitter.com/login")
            
            # Wait for user to log in
            logger.info("👤 Please log into Twitter in the browser window...")
            logger.info("   - Enter your username/email and password")
            logger.info("   - Complete any 2FA if required")
            logger.info("   - Wait for the main Twitter feed to load")
            logger.info("   - Press Enter here when done...")
            
            # Wait for user input
            input("Press Enter when you've successfully logged in...")
            
            # Verify we're logged in by checking for Twitter feed
            try:
                await self.page.wait_for_selector('[data-testid="primaryColumn"]', timeout=10000)
                logger.info("✅ Successfully logged into Twitter!")
            except Exception as e:
                logger.error(f"❌ Could not verify login: {e}")
                return False
            
            # Save cookies
            await self._save_cookies()
            
            # Test the connection
            success = await self._test_connection()
            
            if success:
                logger.info("🎉 Twitter authentication setup complete!")
                logger.info(f"   Cookies saved to: {self.cookies_file}")
                logger.info("   You can now use headless mode for monitoring")
            else:
                logger.error("❌ Authentication test failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Authentication setup failed: {e}")
            return False
        finally:
            if self.browser:
                await self.browser.close()
    
    async def _save_cookies(self):
        """Save current cookies to file"""
        try:
            cookies = await self.page.context.cookies()
            
            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
            
            # Save cookies with metadata
            cookie_data = {
                'cookies': cookies,
                'saved_at': datetime.now(timezone.utc).isoformat(),
                'user_agent': await self.page.evaluate('navigator.userAgent')
            }
            
            with open(self.cookies_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
            
            logger.info(f"💾 Saved {len(cookies)} cookies to {self.cookies_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save cookies: {e}")
    
    async def _test_connection(self):
        """Test the connection by accessing Twitter"""
        try:
            logger.info("🧪 Testing Twitter connection...")
            
            # Navigate to Twitter home
            await self.page.goto("https://twitter.com/home")
            await self.page.wait_for_selector('[data-testid="primaryColumn"]', timeout=10000)
            
            # Try to get a tweet to verify we're logged in
            tweets = await self.page.query_selector_all('[data-testid="tweet"]')
            
            if len(tweets) > 0:
                logger.info(f"✅ Connection test successful! Found {len(tweets)} tweets")
                return True
            else:
                logger.warning("⚠️  No tweets found, but connection seems OK")
                return True
                
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    async def test_saved_cookies(self):
        """Test connection using saved cookies"""
        try:
            logger.info("🧪 Testing saved cookies...")
            
            # Load cookies
            if not os.path.exists(self.cookies_file):
                logger.error(f"❌ Cookies file not found: {self.cookies_file}")
                logger.info("   Run setup_authentication() first")
                return False
            
            with open(self.cookies_file, 'r') as f:
                cookie_data = json.load(f)
            
            # Launch headless browser
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # Add cookies
            await context.add_cookies(cookie_data['cookies'])
            
            # Create page and test
            page = await context.new_page()
            await page.goto("https://twitter.com/home")
            
            # Wait for content to load
            await page.wait_for_selector('[data-testid="primaryColumn"]', timeout=10000)
            
            # Check if we're logged in
            tweets = await page.query_selector_all('[data-testid="tweet"]')
            
            if len(tweets) > 0:
                logger.info(f"✅ Headless connection successful! Found {len(tweets)} tweets")
                success = True
            else:
                logger.warning("⚠️  No tweets found in headless mode")
                success = True  # Still consider it successful
            
            await browser.close()
            return success
            
        except Exception as e:
            logger.error(f"❌ Headless connection test failed: {e}")
            return False
    
    async def monitor_curator(self, curator_handle: str, max_tweets: int = 5):
        """Test monitoring a specific curator"""
        try:
            logger.info(f"👀 Testing curator monitoring: {curator_handle}")
            
            # Load cookies
            if not os.path.exists(self.cookies_file):
                logger.error(f"❌ Cookies file not found: {self.cookies_file}")
                return False
            
            with open(self.cookies_file, 'r') as f:
                cookie_data = json.load(f)
            
            # Launch headless browser
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            
            # Add cookies
            await context.add_cookies(cookie_data['cookies'])
            page = await context.new_page()
            
            # Navigate to curator profile
            profile_url = f"https://twitter.com/{curator_handle.replace('@', '')}"
            logger.info(f"🌐 Navigating to: {profile_url}")
            
            await page.goto(profile_url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for tweets to load with retry
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
            
            logger.info(f"📝 Found {len(tweets)} tweets from {curator_handle}")
            
            for i, tweet in enumerate(tweets):
                logger.info(f"   Tweet {i+1}: {tweet['text'][:100]}...")
            
            await browser.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Curator monitoring test failed: {e}")
            return False


async def main():
    """Main function for Twitter authentication setup"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    auth_setup = TwitterAuthSetup()
    
    print("🐦 Twitter Authentication Setup for Social Lowcap Scanner")
    print("=" * 60)
    print()
    print("This script will help you:")
    print("1. Open a browser to log into Twitter")
    print("2. Save cookies for headless monitoring")
    print("3. Test the connection")
    print()
    
    # Check if cookies already exist
    if os.path.exists(auth_setup.cookies_file):
        print(f"📁 Found existing cookies: {auth_setup.cookies_file}")
        choice = input("Do you want to test existing cookies? (y/n): ").lower().strip()
        
        if choice == 'y':
            success = await auth_setup.test_saved_cookies()
            if success:
                print("\n✅ Existing cookies work! Testing curator monitoring...")
                await auth_setup.monitor_curator("@0xdetweiler")
            return
    
    # Set up new authentication
    choice = input("Do you want to set up new authentication? (y/n): ").lower().strip()
    if choice == 'y':
        success = await auth_setup.setup_authentication()
        if success:
            print("\n🎉 Setup complete! Testing curator monitoring...")
            await auth_setup.monitor_curator("@0xdetweiler")


if __name__ == "__main__":
    asyncio.run(main())
