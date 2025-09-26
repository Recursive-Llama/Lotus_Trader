#!/usr/bin/env python3
"""
Discord Gem Bot Monitor

Monitors Discord channels for new Gem Bot token calls and creates strands.
- Monitors #gembot-risky-calls, #gembot-balanced-calls, #gembot-conservative-calls
- Uses screenshot + LLM to extract token data from Discord messages
- Creates gem_bot strands with appropriate allocation based on channel
- Triggers trader directly via learning system

This bypasses the decision maker since Gem Bot tokens are pre-vetted.
"""

import asyncio
import logging
import json
import re
import time
import base64
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from playwright.async_api import async_playwright, Page, Browser
import os
import sys

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem


class DiscordGemBotMonitor:
    """
    Monitors Discord channels for Gem Bot token calls using screenshot + LLM approach
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient, learning_system: UniversalLearningSystem, 
                 test_mode: bool = False, channels: List[str] = None):
        """
        Initialize Discord Gem Bot Monitor
        
        Args:
            supabase_manager: Database manager for strand operations
            llm_client: LLM client for parsing screenshots
            learning_system: Learning system for strand processing
            test_mode: If True, use lower allocation for testing
            channels: List of channels to monitor ['risky', 'balanced', 'conservative']
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.learning_system = learning_system
        self.logger = logging.getLogger(__name__)
        self.test_mode = test_mode
        self.channels = channels or (['risky'] if test_mode else ['conservative'])
        
        # Track seen messages to detect new ones
        self.seen_messages: Set[str] = set()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # Discord configuration
        self.discord_base_url = "https://discord.com"
        self.server_id = "1393627491352055968"
        self.channel_configs = {
            'risky': {
                'channel_id': '1405408713505771652',  # This is actually conservative from your URL
                'channel_name': '#gembot-conservative-calls',
                'allocation_pct': 1.2 if test_mode else 6.0,
                'strand_kind': 'gem_bot_conservative_test' if test_mode else 'gem_bot_conservative',
                'risk_level': 'low'
            },
            'balanced': {
                'channel_id': '1405408713505771653',  # Placeholder - need actual ID
                'channel_name': '#gembot-balanced-calls',
                'allocation_pct': 2.0 if test_mode else 6.0,
                'strand_kind': 'gem_bot_balanced_test' if test_mode else 'gem_bot_balanced',
                'risk_level': 'medium'
            },
            'conservative': {
                'channel_id': '1405408713505771652',  # Same as risky for now
                'channel_name': '#gembot-conservative-calls',
                'allocation_pct': 1.2 if test_mode else 6.0,
                'strand_kind': 'gem_bot_conservative_test' if test_mode else 'gem_bot_conservative',
                'risk_level': 'low'
            }
        }
        
        self.auto_approve = True    # Auto-approve all Gem Bot tokens
        
        # Cookie management
        self.cookies_file = "src/config/discord_gem_bot_cookies.json"
    
    def _load_cookies(self) -> List[Dict[str, Any]]:
        """Load cookies from file"""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    self.logger.info(f"Loaded {len(cookies)} cookies from {self.cookies_file}")
                    return cookies
            else:
                self.logger.warning(f"Cookie file not found: {self.cookies_file}")
                return []
        except Exception as e:
            self.logger.error(f"Error loading cookies: {e}")
            return []
    
    def _save_cookies(self, cookies: List[Dict[str, Any]]):
        """Save cookies to file"""
        try:
            os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            self.logger.info(f"Saved {len(cookies)} cookies to {self.cookies_file}")
        except Exception as e:
            self.logger.error(f"Error saving cookies: {e}")
    
    async def _setup_authentication(self, page: Page):
        """Setup authentication with saved cookies or prompt for login"""
        try:
            # Try to load existing cookies
            cookies = self._load_cookies()
            if cookies:
                print(f"🍪 Loading {len(cookies)} saved cookies...")
                
                # Filter and fix cookies for Discord
                valid_cookies = []
                for cookie in cookies:
                    # Ensure cookies are for Discord
                    if cookie.get('domain') in ['discord.com', '.discord.com']:
                        # Check if cookie is not expired
                        expires = cookie.get('expires', -1)
                        current_time = time.time()
                        
                        if expires == -1:  # Session cookie (never expires)
                            valid_cookies.append(cookie)
                            print(f"   ✅ Session cookie: {cookie.get('name')}")
                        elif expires > current_time:  # Not expired
                            time_until_expiry = int(expires - current_time)
                            valid_cookies.append(cookie)
                            print(f"   ✅ Valid cookie: {cookie.get('name')} (expires in {time_until_expiry} seconds)")
                        else:
                            time_since_expiry = int(current_time - expires)
                            print(f"   ⏰ Cookie {cookie.get('name')} expired {time_since_expiry} seconds ago")
                    else:
                        print(f"   ❌ Cookie {cookie.get('name')} has wrong domain: {cookie.get('domain')}")
                
                if valid_cookies:
                    print(f"✅ {len(valid_cookies)} valid cookies found")
                    await page.context.add_cookies(valid_cookies)
                    print("✅ Cookies applied to browser context")
                else:
                    print("❌ No valid cookies found")
                    cookies = []  # Clear invalid cookies
                
                # Navigate to Discord to test if cookies work
                print("🌐 Navigating to Discord with saved cookies...")
                channel_id = self.channel_configs[self.channels[0]]['channel_id']
                channel_url = f"{self.discord_base_url}/channels/{self.server_id}/{channel_id}"
                print(f"🌐 Channel URL: {channel_url}")
                await page.goto(channel_url, timeout=90000)
                await page.wait_for_load_state('networkidle', timeout=60000)
                
                # Check if we're logged in by looking for Discord interface
                try:
                    await page.wait_for_timeout(5000)
                    page_content = await page.text_content('body')
                    current_url = page.url
                    print(f"🌐 Current URL: {current_url}")
                    print(f"📄 Page content length: {len(page_content) if page_content else 0}")
                    
                    if page_content and ('Discord' in page_content or 'gembot' in page_content.lower() or 'risky' in page_content.lower()):
                        print("✅ Successfully loaded with saved cookies!")
                        print("✅ Found Discord interface - appears to be logged in")
                        return True
                    else:
                        print("❌ Page loaded but no Discord content found")
                        print(f"📄 First 500 chars: {page_content[:500] if page_content else 'No content'}")
                        cookies = []  # Clear invalid cookies
                except Exception as e:
                    print(f"❌ Error checking page content: {e}")
                    cookies = []  # Clear expired cookies
            
            # If no cookies or they're expired, prompt for manual login
            if not cookies:
                print("🔐 No valid cookies found. Please log in manually...")
                print("1. Browser will open in headed mode")
                print("2. Please log in to Discord")
                print(f"3. Navigate to the Gem Bot server channel: {self.channel_configs[self.channels[0]]['channel_name']}")
                print("4. Press Enter here when you can see the Discord messages")
                
                # Open in headed mode for login
                await page.goto(f"{self.discord_base_url}/channels/{self.server_id}/{self.channel_configs[self.channels[0]]['channel_id']}", timeout=60000)
                await page.wait_for_load_state('domcontentloaded', timeout=30000)
                
                # Wait for user to log in and navigate
                input("Press Enter after logging in and navigating to the Discord channel...")
                
                # Wait a bit for any dynamic content to load
                await page.wait_for_timeout(3000)
                
                # Save ALL cookies after login
                all_cookies = await page.context.cookies()
                self._save_cookies(all_cookies)
                print(f"✅ Saved {len(all_cookies)} cookies for future use")
                
                # Show what cookies we saved
                for cookie in all_cookies:
                    print(f"   🍪 {cookie.get('name')} (domain: {cookie.get('domain')})")
                
                return True
            else:
                # We have cookies but we're still being redirected to login
                print("❌ Cookies loaded but still redirected to login page")
                print("🔐 Discord requires fresh login. Please log in manually...")
                print("1. Browser will open in headed mode")
                print("2. Please log in to Discord")
                print(f"3. Navigate to the Gem Bot server channel: {self.channel_configs[self.channels[0]]['channel_name']}")
                print("4. Press Enter here when you can see the Discord messages")
                
                # Open in headed mode for fresh login
                await page.goto(f"{self.discord_base_url}/channels/{self.server_id}/{self.channel_configs[self.channels[0]]['channel_id']}", timeout=60000)
                await page.wait_for_load_state('domcontentloaded', timeout=30000)
                
                # Wait for user to log in and navigate
                input("Press Enter after logging in and navigating to the Discord channel...")
                
                # Wait a bit for any dynamic content to load
                await page.wait_for_timeout(3000)
                
                # Save ALL cookies after fresh login
                all_cookies = await page.context.cookies()
                self._save_cookies(all_cookies)
                print(f"✅ Saved {len(all_cookies)} fresh cookies for future use")
                
                # Show what cookies we saved
                for cookie in all_cookies:
                    print(f"   🍪 {cookie.get('name')} (domain: {cookie.get('domain')})")
                
                return True
                
        except Exception as e:
            print(f"❌ Authentication setup failed: {e}")
            return False
    
    async def start_monitoring(self, check_interval: int = 10):
        """
        Start monitoring Discord channels for new token calls
        
        Args:
            check_interval: Seconds between checks
        """
        try:
            channels_str = ", ".join([self.channel_configs[ch]['channel_name'] for ch in self.channels])
            print(f"\n🚀 Starting Discord Gem Bot monitoring...")
            print(f"📊 Monitoring channels: {channels_str}")
            print(f"💰 Test mode: {'ON' if self.test_mode else 'OFF'}")
            print(f"⏱️  Check interval: {check_interval} seconds")
            print(f"🌐 Discord URL: {self.discord_base_url}")
            print("=" * 60)
            
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            # Always start in headed mode for debugging
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Always headed for debugging
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = await self.browser.new_page()
            
            # Setup authentication
            print("🔐 Setting up authentication...")
            auth_success = await self._setup_authentication(self.page)
            if not auth_success:
                print("❌ Authentication failed, cannot proceed")
                return
            
            print("✅ Authentication successful!")
            
            # Load initial messages from all channels
            await self._load_initial_messages()
            
            total_messages = len(self.seen_messages)
            print(f"✅ Monitoring started successfully!")
            print(f"📈 Found {total_messages} existing messages across all channels")
            print(f"👀 Watching for NEW messages only...")
            print("=" * 60)
            
            # Start monitoring loop
            while True:
                try:
                    # Check if browser is still alive
                    if not self.browser or not self.page:
                        print("❌ Browser closed, restarting...")
                        await self._restart_browser()
                        continue
                    
                    await self._check_for_new_messages()
                    await asyncio.sleep(check_interval)
                except Exception as e:
                    print(f"❌ Error in monitoring loop: {e}")
                    # Try to restart browser if it's closed
                    if "closed" in str(e).lower():
                        print("🔄 Attempting to restart browser...")
                        await self._restart_browser()
                    await asyncio.sleep(check_interval)
                    
        except Exception as e:
            print(f"❌ Failed to start monitoring: {e}")
        finally:
            await self._cleanup()
    
    async def _restart_browser(self):
        """Restart the browser and page"""
        try:
            await self._cleanup()
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False, args=['--no-sandbox', '--disable-dev-shm-usage'])
            self.page = await self.browser.new_page()
            
            # Re-authenticate
            auth_success = await self._setup_authentication(self.page)
            if auth_success:
                print("✅ Browser restarted successfully")
            else:
                print("❌ Failed to restart browser")
        except Exception as e:
            print(f"❌ Error restarting browser: {e}")
    
    async def _load_initial_messages(self):
        """Load initial messages from the risky channel"""
        try:
            print("🔍 Scanning Discord channel for existing messages...")
            
            channel_name = self.channels[0]  # Just use the first (and only) channel
            print(f"\n📊 Scanning {self.channel_configs[channel_name]['channel_name']}...")
            
            # Navigate to channel (only once)
            channel_id = self.channel_configs[channel_name]['channel_id']
            channel_url = f"{self.discord_base_url}/channels/{self.server_id}/{channel_id}"
            await self.page.goto(channel_url, timeout=60000)
            await self.page.wait_for_load_state('networkidle', timeout=30000)
            await self.page.wait_for_timeout(3000)
            
            # Find message elements
            message_elements = await self.page.query_selector_all('[data-list-item-id*="chat-messages"]')
            print(f"✅ Found {len(message_elements)} messages in {self.channel_configs[channel_name]['channel_name']}")
            
            # Extract message IDs (we'll use these to detect new messages)
            for i, message in enumerate(message_elements[:10]):  # Limit to first 10 messages
                try:
                    message_id = await message.get_attribute('data-list-item-id')
                    if message_id:
                        self.seen_messages.add(message_id)
                        if i == 0:
                            print(f"   🥇 Most recent message ID: {message_id}")
                except Exception as e:
                    continue
            
            print(f"   📈 Found {len([m for m in message_elements if m])} messages in {self.channel_configs[channel_name]['channel_name']}")
            print(f"\n✅ Total existing messages found: {len(self.seen_messages)}")
            print("👀 Now watching for NEW messages only...")
            
        except Exception as e:
            print(f"❌ Error loading initial messages: {e}")
            import traceback
            traceback.print_exc()
    
    async def _check_for_new_messages(self):
        """Check for new messages in the current channel (no page reloading)"""
        try:
            # Check if browser is still alive
            if not self.browser or not self.page:
                print("❌ Browser closed, cannot check for messages")
                return
                
            new_messages_found = 0
            channel_name = self.channels[0]  # Just use the first (and only) channel
            
            # Find message elements on current page (no navigation)
            # Try multiple selectors to find Discord messages
            message_elements = []
            selectors_to_try = [
                '[data-list-item-id*="chat-messages"]',
                '[data-list-item-id]',
                'div[class*="message"]',
                'div[class*="Message"]',
                'article[class*="message"]',
                'div[role="listitem"]',
                'div[class*="container"][class*="message"]'
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if len(elements) > 0:
                        message_elements = elements
                        print(f"✅ Found {len(elements)} messages using selector: {selector}")
                        break
                except:
                    continue
            
            for message in message_elements[:5]:  # Check first 5 messages for new ones
                try:
                    message_id = await message.get_attribute('data-list-item-id')
                    if not message_id or message_id in self.seen_messages:
                        continue
                    
                    # New message found!
                    new_messages_found += 1
                    print(f"\n🆕 NEW MESSAGE DETECTED!")
                    print(f"📊 Channel: {self.channel_configs[channel_name]['channel_name']}")
                    print(f"📝 Message ID: {message_id}")
                    print(f"💰 Allocation: {self.channel_configs[channel_name]['allocation_pct']}%")
                    print("-" * 50)
                    
                    # Add to seen messages
                    self.seen_messages.add(message_id)
                    
                    # Take screenshot and parse with LLM
                    await self._process_new_message(message, channel_name)
                    
                except Exception as e:
                    print(f"   ❌ Error processing message: {e}")
                    continue
            
            if new_messages_found == 0:
                print(f"👀 No new messages found in {self.channel_configs[channel_name]['channel_name']}")
            
        except Exception as e:
            print(f"❌ Error checking for new messages: {e}")
            # If browser is closed, try to restart
            if "closed" in str(e).lower():
                print("🔄 Browser closed, attempting restart...")
                await self._restart_browser()
    
    async def _process_new_message(self, message_element, channel_name: str):
        """Process a new message by taking screenshot and parsing with LLM"""
        try:
            print(f"📸 Taking screenshot of new message...")
            
            # Take screenshot of the message
            screenshot_bytes = await message_element.screenshot()
            
            # Convert to base64 for LLM
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Parse with LLM
            print(f"🤖 Parsing message with LLM...")
            token_data = await self._parse_message_with_llm(screenshot_b64, channel_name)
            
            if token_data and token_data.get('contract'):
                print(f"✅ Extracted token data: {token_data['ticker']} - {token_data['contract'][:20]}...")
                
                # Create strand and trigger trader
                await self._create_gem_bot_strand(token_data, channel_name)
            else:
                print("❌ Could not extract valid token data from message")
                
        except Exception as e:
            print(f"❌ Error processing message: {e}")
    
    async def _parse_message_with_llm(self, screenshot_b64: str, channel_name: str) -> Optional[Dict[str, Any]]:
        """Parse Discord message screenshot with LLM to extract token data"""
        try:
            prompt = f"""
            Analyze this Discord message screenshot from the {self.channel_configs[channel_name]['channel_name']} channel.
            
            Extract the following token information if present:
            - Token name/ticker
            - Contract address (mint address)
            - Market cap (MC)
            - Liquidity
            - Transactions (TXNS)
            - Holders
            - Creator percentage
            - Bundle percentage
            - Sniped percentage
            - Any other relevant metrics
            
            Return the data as JSON in this format:
            {{
                "ticker": "TOKEN_NAME",
                "contract": "CONTRACT_ADDRESS",
                "market_cap": 123456,
                "liquidity": 12345,
                "transactions": 1234,
                "holders": 123,
                "creator_pct": 2.5,
                "bundle_pct": 4.8,
                "sniped_pct": 6.8,
                "timestamp": "2025-01-20T12:31:00Z"
            }}
            
            If no token data is found, return null.
            """
            
            # Use the LLM client to parse the screenshot (without image for now)
            response = await self.llm_client.generate_async(
                prompt=prompt,
                max_tokens=500
            )
            
            # Parse JSON response
            if response and response.strip():
                try:
                    token_data = json.loads(response.strip())
                    return token_data
                except json.JSONDecodeError:
                    print(f"❌ Failed to parse LLM response as JSON: {response}")
                    return None
            else:
                print("❌ Empty response from LLM")
                return None
                
        except Exception as e:
            print(f"❌ Error parsing message with LLM: {e}")
            return None
    
    async def _create_gem_bot_strand(self, token_data: Dict[str, Any], channel_name: str):
        """
        Create a gem_bot strand for the trader
        
        Args:
            token_data: Extracted token data from Discord message
            channel_name: Name of the Discord channel
        """
        try:
            # Get channel configuration
            config = self.channel_configs[channel_name]
            
            # Generate strand ID
            strand_id = f"gem_bot_{token_data['ticker']}_{int(datetime.now().timestamp())}"
            
            print(f"🚀 Creating strand for {token_data['ticker']} from {config['channel_name']}...")
            
            # Create the strand with proper structure for trader
            strand = {
                "id": strand_id,
                "module": "discord_gem_bot_monitor",
                "kind": config['strand_kind'],
                "symbol": token_data['ticker'],
                "timeframe": None,
                "session_bucket": f"gem_bot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}",
                "regime": channel_name.lower(),
                "tags": ["gem_bot", channel_name.lower(), "auto_approved", "high_quality", "pre_vetted", "discord"],
                "target_agent": "trader_lowcap",  # Direct to trader
                "sig_sigma": 1.0,  # High confidence for Gem Bot tokens
                "sig_confidence": 0.95,  # Very high confidence
                "confidence": 0.95,
                "sig_direction": "buy",  # Always buy for Gem Bot tokens
                "data": {
                    "token": {
                        "ticker": token_data['ticker'],
                        "contract": token_data['contract'],
                        "chain": "solana",  # Assuming Solana for Gem Bot
                        "dex": "jupiter",  # Assuming Jupiter for Solana
                        "liq_usd": token_data.get('liquidity', 0),
                        "vol24h_usd": 0  # Not available from Discord
                    },
                    "curator": {
                        "id": f"gem_bot_{channel_name.lower()}",
                        "platform": "discord",
                        "handle": config['channel_name'],
                        "weight": 1.0,  # Maximum weight for Gem Bot tokens
                        "verified": True,
                        "reliability_score": 0.95
                    },
                    "trading_signals": {
                        "action": "buy",
                        "confidence": 0.95,
                        "allocation_pct": config['allocation_pct'],
                        "allocation_usd": None,  # Will be calculated by trader
                        "reasoning": f"{config['channel_name']} token: {token_data['ticker']} - Pre-vetted high-quality token",
                        "risk_level": config['risk_level'],
                        "auto_approve": self.auto_approve
                    },
                    "message": {
                        "text": f"New {config['channel_name']} token: {token_data['ticker']} - {token_data.get('contract', '')}",
                        "timestamp": token_data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                        "url": f"https://discord.com/channels/{self.server_id}/{config['channel_id']}"
                    }
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "agent_id": "discord_gem_bot_monitor",
                "team_member": f"{channel_name.lower()}_channel"
            }
            
            # Save strand to database
            success = await self.supabase_manager.create_strand(strand)
            if success:
                print(f"✅ Created strand: {strand_id}")
                
                # Process strand through learning system
                await self.learning_system.process_strand_event(strand)
                print(f"✅ Processed strand through learning system")
            else:
                self.logger.error(f"❌ Failed to create gem_bot strand: {strand_id}")
                
        except Exception as e:
            self.logger.error(f"Error creating gem_bot strand: {e}")
    
    async def _cleanup(self):
        """Clean up resources"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


async def main():
    """Main entry point for testing"""
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    learning_system = UniversalLearningSystem(
        supabase_manager=supabase_manager,
        llm_client=llm_client,
        llm_config=None
    )
    
    # Create monitor in test mode
    monitor = DiscordGemBotMonitor(
        supabase_manager=supabase_manager,
        llm_client=llm_client,
        learning_system=learning_system,
        test_mode=True,
        channels=['risky']
    )
    
    print("🚀 Starting Discord Gem Bot monitor in test mode...")
    print("   - Will monitor #gembot-risky-calls for new messages")
    print("   - Will create strands with 1.2% allocation (test mode)")
    print("   - Press Ctrl+C to stop")
    
    try:
        await monitor.start_monitoring(check_interval=10)
    except KeyboardInterrupt:
        print("\n👋 Stopping monitor...")
    finally:
        await monitor._cleanup()


if __name__ == "__main__":
    asyncio.run(main())
