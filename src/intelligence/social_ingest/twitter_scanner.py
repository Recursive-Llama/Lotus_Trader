"""
Twitter Scanner for Social Lowcap Intelligence

Simple Twitter monitoring using Playwright for headless browsing.
Monitors configured curators and extracts token information.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import yaml
import os
from playwright.async_api import async_playwright, Browser, Page
from .social_ingest_basic import SocialIngestModule

logger = logging.getLogger(__name__)


class TwitterScanner:
    """
    Twitter Scanner using Playwright for headless browsing
    
    Features:
    - Round-robin monitoring of configured curators
    - Cookie-based authentication
    - Image analysis for chart detection
    - LLM-powered token extraction
    """
    
    def __init__(self, social_ingest_module: SocialIngestModule, config_path: str = None):
        """
        Initialize Twitter Scanner
        
        Args:
            social_ingest_module: Social ingest module for processing signals
            config_path: Path to curator configuration file
        """
        self.social_ingest = social_ingest_module
        self.config_path = config_path or "src/config/twitter_curators.yaml"
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config()
        
        # Browser and page instances
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # Monitoring state
        self.is_running = False
        self.current_curator_index = 0
        
        # Track processed tweets to avoid duplicates
        self.processed_tweets = set()  # Store tweet URLs we've already processed
        
        # Track last seen tweet for each curator (for incremental monitoring)
        self.curator_last_seen = {}  # {curator_id: last_tweet_url}
        
        # Get Twitter curators
        self.twitter_curators = self._get_twitter_curators()
        
        self.logger.info(f"Twitter Scanner initialized with {len(self.twitter_curators)} curators")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                self.logger.warning(f"Config file not found: {self.config_path}")
                return {}
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}
    
    def _get_twitter_curators(self) -> List[Dict[str, Any]]:
        """Get list of active Twitter curators"""
        curators = []
        for curator in self.config.get('curators', []):
            if curator.get('enabled', True) and 'twitter' in curator.get('platforms', {}):
                twitter_data = curator['platforms']['twitter']
                if twitter_data.get('active', True):
                    curators.append({
                        'id': curator['id'],
                        'name': curator['name'],
                        'handle': twitter_data['handle'],
                        'weight': twitter_data.get('weight', 0.5),
                        'priority': twitter_data.get('priority', 'medium'),
                        'tags': curator.get('tags', [])
                    })
        return curators
    
    async def start_monitoring(self):
        """Start monitoring Twitter curators"""
        try:
            self.logger.info("Starting Twitter monitoring...")
            
            # Initialize Playwright
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            
            # Create new context and add cookies BEFORE creating page
            self.context = await self.browser.new_context()
            await self._load_cookies()
            
            # Create page from the context with cookies
            self.page = await self.context.new_page()
            
            # Start monitoring loop
            self.is_running = True
            await self._monitoring_loop()
            
        except Exception as e:
            self.logger.error(f"Error starting Twitter monitoring: {e}")
        finally:
            await self.stop_monitoring()
    
    async def stop_monitoring(self):
        """Stop monitoring and cleanup"""
        self.is_running = False
        
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        
        self.logger.info("Twitter monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop with round-robin - 30 seconds per curator"""
        profile_wait_time = 30  # 30 seconds per profile
        
        while self.is_running:
            try:
                # Process current curator
                if self.twitter_curators:
                    curator = self.twitter_curators[self.current_curator_index]
                    await self._check_curator(curator)
                    
                    # Wait 30 seconds on this profile before moving to next
                    self.logger.debug(f"Waiting {profile_wait_time} seconds on {curator['handle']}...")
                    await asyncio.sleep(profile_wait_time)
                    
                    # Move to next curator
                    self.current_curator_index = (self.current_curator_index + 1) % len(self.twitter_curators)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(profile_wait_time)
    
    async def _check_curator(self, curator: Dict[str, Any]):
        """Check a specific curator for new posts"""
        try:
            handle = curator['handle']
            curator_id = f"twitter:{handle}"
            self.logger.debug(f"Checking curator: {handle}")
            
            # Navigate to curator's Twitter profile
            profile_url = f"https://twitter.com/{handle.replace('@', '')}"
            await self.page.goto(profile_url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for tweets to load
            await self.page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
            
            # Get recent tweets
            tweets = await self._extract_tweets()
            
            if not tweets:
                self.logger.debug(f"No tweets found for {handle}")
                return
            
            # Always detect and skip pinned tweets
            actual_most_recent_tweet = self._get_actual_most_recent_tweet(tweets)
            most_recent_tweet_url = actual_most_recent_tweet.get('url', '')
            
            # Check if first tweet is pinned (older than second tweet)
            is_pinned = len(tweets) >= 2 and self._is_pinned_tweet(tweets[0], tweets[1])
            if is_pinned:
                print(f"   📌 Pinned tweet detected - skipping")
            
            # Show most recent tweet info
            most_recent_text = actual_most_recent_tweet.get('text', '')[:100]
            most_recent_time = actual_most_recent_tweet.get('timestamp', '')
            print(f"   📝 Most recent: {most_recent_text}...")
            print(f"   🕐 Time: {most_recent_time}")
            
            # Check if we've seen this curator before
            if curator_id in self.curator_last_seen:
                last_seen_url = self.curator_last_seen[curator_id]

                # Optional context: show last seen info if available in current list
                last_seen_ts = None
                for t in tweets:
                    if t.get('url', '') == last_seen_url:
                        last_seen_ts = t.get('timestamp', None)
                        break
                last_seen_tail = last_seen_url.rsplit('/', 1)[-1] if last_seen_url else ''
                if last_seen_url:
                    print(f"   👀 Last seen: {last_seen_ts or 'unknown time'} (…{last_seen_tail})")

                # If the most recent tweet is the same as last time, no new tweets
                if most_recent_tweet_url == last_seen_url:
                    print(f"   ⏸️  No new tweets (same as last check)")
                    return

                # Collect new tweets strictly after last seen, skipping pinned if present
                start_index = 1 if is_pinned else 0
                new_tweets = []
                for tweet in tweets[start_index:]:
                    tweet_url = tweet.get('url', '')
                    if tweet_url == last_seen_url:
                        break  # Stop when we reach the last seen tweet
                    new_tweets.append(tweet)

                print(f"   🆕 Found {len(new_tweets)} new tweets")
            else:
                # First time checking this curator - process only the actual most recent tweet
                new_tweets = [actual_most_recent_tweet]
                print(f"   🆕 First time checking - processing most recent tweet")
            
            # Process new tweets
            for tweet in new_tweets:
                tweet_url = tweet.get('url', '')
                if tweet_url and tweet_url not in self.processed_tweets:
                    print(f"   🔍 Processing tweet: {tweet.get('text', '')[:50]}...")
                    result = await self._process_tweet(curator, tweet)
                    self.processed_tweets.add(tweet_url)
                    if result:
                        print(f"   ✅ Tweet processed successfully")
                    else:
                        print(f"   ⚠️  No tokens found in tweet")
                else:
                    print(f"   ⏭️  Skipping duplicate tweet")
            
            # Update last seen tweet for this curator
            self.curator_last_seen[curator_id] = most_recent_tweet_url
            
        except Exception as e:
            self.logger.error(f"Error checking curator {curator['handle']}: {e}")
    
    def _is_pinned_tweet(self, first_tweet: Dict[str, Any], second_tweet: Dict[str, Any]) -> bool:
        """
        Check if the first tweet is pinned by comparing timestamps.
        If first tweet is older than second tweet, it's pinned.
        """
        try:
            from datetime import datetime
            
            first_tweet_time = datetime.fromisoformat(first_tweet['timestamp'].replace('Z', '+00:00'))
            second_tweet_time = datetime.fromisoformat(second_tweet['timestamp'].replace('Z', '+00:00'))
            
            return first_tweet_time < second_tweet_time
                
        except Exception as e:
            self.logger.warning(f"Error parsing timestamps for pinned check: {e}")
            return False
    
    def _get_actual_most_recent_tweet(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get the actual most recent tweet, handling pinned tweets.
        If first tweet is pinned, return the second tweet.
        """
        if len(tweets) < 2:
            return tweets[0] if tweets else {}
        
        # Check if first tweet is pinned
        if self._is_pinned_tweet(tweets[0], tweets[1]):
            return tweets[1]  # Second tweet is the actual most recent
        else:
            return tweets[0]  # First tweet is the most recent
    
    async def _extract_tweets(self) -> List[Dict[str, Any]]:
        """Extract tweet data from the current page"""
        try:
            tweets = await self.page.evaluate("""
                () => {
                    const tweetElements = document.querySelectorAll('[data-testid="tweet"]');
                    const tweets = [];
                    
                    tweetElements.forEach(tweetEl => {
                        try {
                            // Extract tweet text
                            const textEl = tweetEl.querySelector('[data-testid="tweetText"]');
                            const text = textEl ? textEl.innerText : '';
                            
                            // Extract timestamp
                            const timeEl = tweetEl.querySelector('time');
                            const timestamp = timeEl ? timeEl.getAttribute('datetime') : new Date().toISOString();
                            
                            // Extract tweet URL
                            const linkEl = tweetEl.querySelector('a[href*="/status/"]');
                            const url = linkEl ? 'https://twitter.com' + linkEl.getAttribute('href') : '';
                            
                            // Check for images
                            const imageEl = tweetEl.querySelector('[data-testid="tweetPhoto"] img');
                            const hasImage = !!imageEl;
                            const imageUrl = imageEl ? imageEl.src : null;
                            
                            if (text.trim()) {
                                tweets.push({
                                    text: text,
                                    timestamp: timestamp,
                                    url: url,
                                    has_image: hasImage,
                                    image_url: imageUrl
                                });
                            }
                        } catch (e) {
                            console.error('Error extracting tweet:', e);
                        }
                    });
                    
                    return tweets;
                }
            """)
            
            return tweets
            
        except Exception as e:
            self.logger.error(f"Error extracting tweets: {e}")
            return []
    
    async def _process_tweet(self, curator: Dict[str, Any], tweet: Dict[str, Any]):
        """Process a single tweet for token information"""
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
            
            if result and len(result) > 0:
                self.logger.info(f"Processed tweet from {curator['handle']}: {tweet['text'][:50]}...")
                return True
            else:
                self.logger.debug(f"No token found in tweet from {curator['handle']}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing tweet: {e}")
            return False
    
    async def _download_image(self, image_url: str) -> Optional[bytes]:
        """Download image data from URL"""
        try:
            response = await self.page.request.get(image_url)
            if response.ok:
                return await response.body()
        except Exception as e:
            self.logger.error(f"Error downloading image: {e}")
        return None
    
    async def _load_cookies(self):
        """Load saved cookies for authentication"""
        try:
            cookies_file = "src/config/twitter_cookies.json"
            if os.path.exists(cookies_file):
                with open(cookies_file, 'r') as f:
                    cookie_data = json.load(f)
                    if 'cookies' in cookie_data:
                        await self.context.add_cookies(cookie_data['cookies'])
                        self.logger.info(f"Loaded {len(cookie_data['cookies'])} Twitter cookies")
                    else:
                        # Legacy format
                        await self.context.add_cookies(cookie_data)
                        self.logger.info("Loaded Twitter cookies (legacy format)")
        except Exception as e:
            self.logger.warning(f"Could not load cookies: {e}")
    
    async def _save_cookies(self):
        """Save current cookies for future use"""
        try:
            cookies = await self.page.context.cookies()
            cookies_file = "src/config/twitter_cookies.json"
            os.makedirs(os.path.dirname(cookies_file), exist_ok=True)
            
            # Save with metadata
            cookie_data = {
                'cookies': cookies,
                'saved_at': datetime.now(timezone.utc).isoformat(),
                'user_agent': await self.page.evaluate('navigator.userAgent')
            }
            
            with open(cookies_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
            
            self.logger.info(f"Saved {len(cookies)} Twitter cookies")
        except Exception as e:
            self.logger.error(f"Error saving cookies: {e}")


# Example usage
async def main():
    """Example usage of Twitter Scanner"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create social ingest module
    social_ingest = SocialIngestModule(supabase_manager, llm_client)
    
    # Create Twitter scanner
    scanner = TwitterScanner(social_ingest)
    
    try:
        # Start monitoring
        await scanner.start_monitoring()
    except KeyboardInterrupt:
        print("Stopping Twitter scanner...")
    finally:
        await scanner.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
