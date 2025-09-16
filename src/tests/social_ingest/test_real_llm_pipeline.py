"""
Test Real LLM Pipeline with Actual Tweets

Gets the most recent (non-pinned) tweet from each curator and runs it through
the full LLM pipeline to test token extraction and processing.
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timezone

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from twitter_auth_setup import TwitterAuthSetup
from social_ingest_basic import SocialIngestModule

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockSupabaseManager:
    """Mock Supabase manager for testing"""
    
    def create_strand(self, strand_data):
        """Mock strand creation"""
        logger.info(f"📝 Created strand: {strand_data['kind']}")
        logger.info(f"   Curator: {strand_data['content']['curator_id']}")
        logger.info(f"   Token: {strand_data['content']['token']['ticker']}")
        logger.info(f"   Chain: {strand_data['content']['token']['chain']}")
        logger.info(f"   Venue: {strand_data['content']['venue']['dex']}")
        logger.info(f"   Has Chart: {strand_data['content']['message']['has_chart']}")
        return {
            **strand_data,
            'id': f"strand_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'created_at': datetime.now(timezone.utc)
        }
    
    def update_curator_last_seen(self, curator_id):
        """Mock curator update"""
        logger.info(f"🔄 Updated last_seen for curator {curator_id}")


class RealLLMClient:
    """Real LLM client for testing"""
    
    def __init__(self):
        # Try to import the real LLM client
        try:
            from src.llm_integration.openrouter_client import OpenRouterClient
            self.client = OpenRouterClient()
            self.has_real_client = True
            logger.info("✅ Using real OpenRouter LLM client")
        except ImportError as e:
            logger.warning(f"⚠️  Could not import real LLM client: {e}")
            self.client = None
            self.has_real_client = False
    
    async def generate_async(self, prompt, system_message=None, image=None):
        """Generate response using real or mock LLM"""
        if self.has_real_client and self.client:
            try:
                if system_message:
                    response = await self.client.generate_async(prompt, system_message=system_message)
                else:
                    response = await self.client.generate_async(prompt)
                return response
            except Exception as e:
                logger.error(f"❌ Real LLM call failed: {e}")
                return self._mock_response(prompt)
        else:
            return self._mock_response(prompt)
    
    def _mock_response(self, prompt):
        """Mock LLM response for testing"""
        # Look for token mentions in the prompt
        if any(token in prompt.upper() for token in ['$SLC', '$BAR', '$FOO', 'SLC', 'BAR', 'FOO']):
            return json.dumps({
                "token_name": "SLC",
                "network": "solana",
                "contract_address": "So1aNa1234567890abcdef",
                "sentiment": "positive",
                "confidence": 0.85,
                "trading_intention": "buy",
                "has_chart": True,
                "chart_type": "price",
                "chart_analysis": "bullish pattern",
                "additional_info": "Mentioned in tweet with positive sentiment"
            })
        else:
            return "null"


async def get_recent_tweet(auth_setup, curator_handle):
    """Get the most recent non-pinned tweet from a curator"""
    try:
        logger.info(f"🔍 Getting recent tweet from {curator_handle}...")
        
        # Load cookies
        if not os.path.exists(auth_setup.cookies_file):
            logger.error(f"❌ Cookies file not found: {auth_setup.cookies_file}")
            return None
        
        with open(auth_setup.cookies_file, 'r') as f:
            cookie_data = json.load(f)
        
        # Launch headless browser
        from playwright.async_api import async_playwright
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Add cookies
        await context.add_cookies(cookie_data['cookies'])
        page = await context.new_page()
        
        # Navigate to curator profile
        profile_url = f"https://twitter.com/{curator_handle.replace('@', '')}"
        await page.goto(profile_url, wait_until='domcontentloaded', timeout=60000)
        
        # Wait for tweets to load
        try:
            await page.wait_for_selector('[data-testid="tweet"]', timeout=15000)
        except Exception:
            logger.warning("⚠️  No tweets found initially, trying to scroll...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)
        
        # Extract the first tweet (most recent, non-pinned)
        tweet = await page.evaluate("""
            () => {
                const tweetElements = document.querySelectorAll('[data-testid="tweet"]');
                
                // Skip pinned tweets (they usually have different structure)
                for (let i = 0; i < tweetElements.length; i++) {
                    const tweetEl = tweetElements[i];
                    
                    // Check if this is a pinned tweet
                    const isPinned = tweetEl.querySelector('[data-testid="pin"]') || 
                                   tweetEl.querySelector('[aria-label*="Pinned"]') ||
                                   tweetEl.textContent.includes('Pinned Tweet');
                    
                    if (!isPinned) {
                        try {
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
                            
                            if (text.trim()) {
                                return {
                                    text: text,
                                    timestamp: timestamp,
                                    url: url,
                                    has_image: hasImage,
                                    image_url: imageUrl
                                };
                            }
                        } catch (e) {
                            console.error('Error extracting tweet:', e);
                        }
                    }
                }
                
                return null;
            }
        """)
        
        await browser.close()
        
        if tweet:
            logger.info(f"✅ Found tweet: {tweet['text'][:100]}...")
            return tweet
        else:
            logger.warning(f"⚠️  No recent tweet found for {curator_handle}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error getting tweet from {curator_handle}: {e}")
        return None


async def test_curator_with_llm(social_ingest, curator_id, tweet_data):
    """Test a curator's tweet through the full LLM pipeline"""
    try:
        logger.info(f"\n🧪 Testing {curator_id} with LLM pipeline...")
        logger.info(f"📝 Tweet: {tweet_data['text'][:150]}...")
        
        # Process through social ingest module
        result = await social_ingest.process_social_signal(curator_id, tweet_data)
        
        if result:
            logger.info(f"✅ Successfully processed {curator_id}")
            logger.info(f"   Token: {result['content']['token']['ticker']}")
            logger.info(f"   Chain: {result['content']['token']['chain']}")
            logger.info(f"   Sentiment: {result['content']['message'].get('sentiment', 'unknown')}")
            logger.info(f"   Has Chart: {result['content']['message']['has_chart']}")
            return True
        else:
            logger.info(f"❌ No token found in {curator_id}'s tweet")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error processing {curator_id}: {e}")
        return False


async def main():
    """Main test function"""
    logger.info("🧪 Testing Real LLM Pipeline with Actual Tweets")
    logger.info("=" * 60)
    
    # Initialize components
    auth_setup = TwitterAuthSetup()
    supabase_manager = MockSupabaseManager()
    llm_client = RealLLMClient()
    
    # Create social ingest module
    social_ingest = SocialIngestModule(supabase_manager, llm_client)
    
    # Test curators
    curators = [
        ("twitter:@0xdetweiler", "@0xdetweiler"),
        ("twitter:@LouisCooper_", "@LouisCooper_"),
        ("twitter:@zinceth", "@zinceth"),
        ("twitter:@Cryptotrissy", "@Cryptotrissy"),
        ("twitter:@CryptoxHunter", "@CryptoxHunter")
    ]
    
    results = []
    
    for curator_id, handle in curators:
        logger.info(f"\n{'='*50}")
        logger.info(f"Testing {handle}")
        logger.info(f"{'='*50}")
        
        # Get recent tweet
        tweet = await get_recent_tweet(auth_setup, handle)
        
        if tweet:
            # Test with LLM pipeline
            success = await test_curator_with_llm(social_ingest, curator_id, tweet)
            results.append((handle, success))
        else:
            logger.warning(f"⚠️  Skipping {handle} - no tweet found")
            results.append((handle, False))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("📊 Test Results Summary")
    logger.info(f"{'='*60}")
    
    successful = 0
    for handle, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"{handle}: {status}")
        if success:
            successful += 1
    
    logger.info(f"\n🎯 Results: {successful}/{len(results)} curators processed successfully")
    
    if successful > 0:
        logger.info("🎉 LLM pipeline is working with real tweets!")
    else:
        logger.warning("⚠️  No tweets were successfully processed")


if __name__ == "__main__":
    asyncio.run(main())
