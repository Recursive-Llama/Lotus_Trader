#!/usr/bin/env python3
"""
Gem Bot Monitor

Monitors the Conservative column of the Gem Bot dashboard for new coin entries.
Creates strands directly for the trader with 6% allocation and auto-approval.

This bypasses the decision maker since Conservative column tokens are pre-vetted.
"""

import asyncio
import logging
import json
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from playwright.async_api import async_playwright, Page, Browser
import os
import sys

# Add src to path for imports
sys.path.append('src')

from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem

logger = logging.getLogger(__name__)


class GemBotMonitor:
    """
    Monitors Gem Bot Conservative column for new coin entries
    
    This module:
    - Uses Playwright to monitor the Conservative column
    - Detects new coin entries by watching DOM changes
    - Extracts token data (address, name, metrics)
    - Creates gem_bot strands with 6% allocation
    - Triggers trader directly via learning system
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient, learning_system: UniversalLearningSystem, 
                 test_mode: bool = False, columns: List[str] = None):
        """
        Initialize Gem Bot Monitor
        
        Args:
            supabase_manager: Database manager for strand operations
            llm_client: LLM client for any text processing
            learning_system: Learning system for strand processing
            test_mode: If True, use lower allocation for testing
            columns: List of columns to monitor ['risky', 'balanced', 'conservative']
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.learning_system = learning_system
        self.logger = logging.getLogger(__name__)
        self.test_mode = test_mode
        self.columns = columns or (['risky'] if test_mode else ['conservative'])
        
        # Track seen tokens to detect new ones
        self.seen_tokens: Set[str] = set()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # Configuration
        self.gem_bot_url = "https://gembot.io/feed"
        
        # Column configurations
        self.column_configs = {
            'risky': {
                'selector': "text=Risky",
                'allocation_pct': 1.2 if test_mode else 3.0,
                'strand_kind': 'gem_bot_risky_test' if test_mode else 'gem_bot_risky',
                'risk_level': 'high'
            },
            'balanced': {
                'selector': "text=Balanced", 
                'allocation_pct': 2.0 if test_mode else 6.0,
                'strand_kind': 'gem_bot_balanced_test' if test_mode else 'gem_bot_balanced',
                'risk_level': 'medium'
            },
            'conservative': {
                'selector': "text=Conservative",
                'allocation_pct': 1.2 if test_mode else 6.0,
                'strand_kind': 'gem_bot_conservative_test' if test_mode else 'gem_bot_conservative', 
                'risk_level': 'low'
            }
        }
        
        self.auto_approve = True    # Auto-approve all Gem Bot tokens
        
        # Cookie management
        self.cookies_file = "src/config/gem_bot_cookies.json"
    
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
                
                # Filter and fix cookies for the correct domain
                valid_cookies = []
                for cookie in cookies:
                    # Ensure cookies are for the correct domain
                    if cookie.get('domain') in ['gembot.io', '.gembot.io', '.privy.io']:
                        # Fix domain if needed
                        if cookie.get('domain') == '.privy.io':
                            cookie['domain'] = '.privy.io'  # Keep as is
                        elif cookie.get('domain') == 'gembot.io':
                            cookie['domain'] = 'gembot.io'  # Keep as is
                        
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
                
                # Navigate to the site to test if cookies work
                print("🌐 Navigating to Gem Bot with saved cookies...")
                print(f"🌐 URL: {self.gem_bot_url}")
                await page.goto(self.gem_bot_url, timeout=60000)
                print("✅ Page navigation completed")
                await page.wait_for_load_state('networkidle', timeout=30000)
                print("✅ Network idle state reached")
                
                # Check the actual URL we ended up on
                current_url = page.url
                print(f"🌐 Current URL: {current_url}")
                
                # Check if we're on the right page (feed vs landing page)
                if '/feed' not in current_url:
                    print("❌ Redirected to landing page - not logged in")
                    cookies = []  # Clear invalid cookies
                else:
                    print("✅ On feed page - checking content...")
                
                # Check if we're logged in by looking for the main content
                try:
                    # Wait a bit for the page to fully load
                    await page.wait_for_timeout(5000)
                    
                    # Check if we can see the main content (not a login page)
                    page_content = await page.text_content('body')
                    print(f"📄 Page content length: {len(page_content) if page_content else 0} characters")
                    
                    if page_content:
                        # Check for various indicators of being logged in
                        logged_in_indicators = [
                            'Risky' in page_content,
                            'Conservative' in page_content, 
                            'Balanced' in page_content,
                            'Buy' in page_content,
                            '$' in page_content,
                            'token' in page_content.lower()
                        ]
                        
                        if any(logged_in_indicators):
                            print("✅ Successfully loaded with saved cookies!")
                            print("✅ Found main content - appears to be logged in")
                            return True
                        else:
                            print("❌ Page loaded but no main content found")
                            print(f"📄 First 500 chars: {page_content[:500]}")
                            
                            # Check if we're on a login page
                            if any(word in page_content.lower() for word in ['login', 'sign in', 'authenticate', 'connect wallet']):
                                print("❌ Appears to be on login page - cookies may be invalid")
                            cookies = []  # Clear invalid cookies
                    else:
                        print("❌ No page content found")
                        cookies = []  # Clear invalid cookies
                except Exception as e:
                    print(f"❌ Error checking page content: {e}")
                    cookies = []  # Clear expired cookies
            
            # If no cookies or they're expired, prompt for manual login
            if not cookies:
                print("🔐 No valid cookies found. Please log in manually...")
                print("1. Browser will open in headed mode")
                print("2. Please log in to Gem Bot")
                print("3. Navigate to the feed page (https://gembot.io/feed)")
                print("4. Press Enter here when you can see the Risky/Conservative columns")
                
                # Open in headed mode for login
                await page.goto(self.gem_bot_url, timeout=60000)
                await page.wait_for_load_state('domcontentloaded', timeout=30000)
                
                # Wait for user to log in and navigate to feed
                input("Press Enter after logging in and navigating to the feed page...")
                
                # Verify we're on the feed page
                current_url = page.url
                print(f"🌐 Current URL: {current_url}")
                
                if '/feed' not in current_url:
                    print("⚠️  You're not on the feed page. Please navigate to https://gembot.io/feed")
                    input("Press Enter after navigating to the feed page...")
                    current_url = page.url
                    print(f"🌐 Current URL: {current_url}")
                
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
                
        except Exception as e:
            self.logger.error(f"Authentication setup failed: {e}")
            return False
        
    async def start_monitoring(self, check_interval: int = 5):
        """
        Start monitoring the specified columns
        
        Args:
            check_interval: Seconds between checks
        """
        try:
            columns_str = ", ".join([col.title() for col in self.columns])
            print(f"\n🚀 Starting Gem Bot monitoring...")
            print(f"📊 Monitoring columns: {columns_str}")
            print(f"💰 Test mode: {'ON' if self.test_mode else 'OFF'}")
            print(f"⏱️  Check interval: {check_interval} seconds")
            print(f"🌐 URL: {self.gem_bot_url}")
            print("=" * 60)
            
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False, args=['--no-sandbox', '--disable-dev-shm-usage'])
            self.page = await self.browser.new_page()
            
            # Setup authentication
            print("🔐 Setting up authentication...")
            auth_success = await self._setup_authentication(self.page)
            if not auth_success:
                print("❌ Authentication failed, cannot proceed")
                return
            
            print("✅ Authentication successful!")
            
            # Load initial tokens from all columns
            await self._load_initial_tokens()
            
            total_tokens = len(self.seen_tokens)
            print(f"✅ Monitoring started successfully!")
            print(f"📈 Found {total_tokens} existing tokens across all columns")
            print(f"👀 Watching for NEW tokens only...")
            print("=" * 60)
            
            # Start monitoring loop
            while True:
                try:
                    # Check if browser is still alive
                    if not self.browser or not self.page:
                        print("❌ Browser closed, restarting...")
                        await self._restart_browser()
                        continue
                    
                    await self._check_for_new_tokens()
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
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=False, args=['--no-sandbox', '--disable-dev-shm-usage'])
            self.page = await self.browser.new_page()
            
            # Re-authenticate
            auth_success = await self._setup_authentication(self.page)
            if auth_success:
                print("✅ Browser restarted successfully")
            else:
                print("❌ Failed to restart browser")
        except Exception as e:
            print(f"❌ Error restarting browser: {e}")
    
    async def _load_initial_tokens(self):
        """Load initial tokens from all monitored columns"""
        try:
            print("🔍 Scanning page for existing tokens...")
            
            # Wait for page to fully load
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(5000)
            
            # Debug: Let's see what's actually on the page
            print("🔍 Debugging page structure...")
            
            # Check if we can see any text on the page
            page_text = await self.page.text_content('body')
            if page_text:
                print(f"📄 Page loaded, content length: {len(page_text)} characters")
                if "Risky" in page_text:
                    print("✅ Found 'Risky' text on page")
                else:
                    print("❌ 'Risky' text not found on page")
                if "Conservative" in page_text:
                    print("✅ Found 'Conservative' text on page")
                else:
                    print("❌ 'Conservative' text not found on page")
            else:
                print("❌ No page content found")
                return
            
            total_found = 0
            
            for column_name in self.columns:
                print(f"\n📊 Scanning {column_name.title()} column...")
                
                # Try multiple ways to find the column
                column_selectors = [
                    f"text={column_name.title()}",
                    f"*:has-text('{column_name.title()}')",
                    f"[class*='{column_name.lower()}']",
                    f"[data-testid*='{column_name.lower()}']"
                ]
                
                column_element = None
                for selector in column_selectors:
                    try:
                        column_element = await self.page.query_selector(selector)
                        if column_element:
                            print(f"✅ Found {column_name.title()} using selector: {selector}")
                            break
                    except:
                        continue
                
                if not column_element:
                    print(f"❌ Could not find '{column_name.title()}' column with any selector")
                    continue
                
                # Get the column container - try multiple parent levels
                column_container = None
                for i in range(3):  # Try up to 3 parent levels
                    try:
                        if i == 0:
                            column_container = await column_element.query_selector("xpath=..")
                        else:
                            column_container = await column_container.query_selector("xpath=..")
                        
                        if column_container:
                            # Check if this container has multiple child divs (likely cards)
                            child_divs = await column_container.query_selector_all("div")
                            if len(child_divs) > 2:  # If it has multiple child divs, it's probably the right container
                                print(f"✅ Found {column_name.title()} column container with {len(child_divs)} child divs")
                                break
                    except:
                        continue
                
                if not column_container:
                    print(f"❌ Could not find proper container for {column_name.title()} column")
                    continue
                
                # Look for cards within this column with more specific selectors
                card_selectors = [
                    "div[class*='card']",
                    "div[class*='token']", 
                    "div[class*='coin']",
                    "div[class*='entry']",
                    "div:has-text('Buy')",
                    "div:has-text('$')",
                    "div"
                ]
                
                cards = []
                for selector in card_selectors:
                    try:
                        cards = await column_container.query_selector_all(selector)
                        print(f"🔍 Selector '{selector}': {len(cards)} elements")
                        if len(cards) > 2:  # If we find more than 2 cards, this is probably right
                            print(f"✅ Found {len(cards)} cards using selector: {selector}")
                            break
                    except Exception as e:
                        print(f"❌ Error with selector '{selector}': {e}")
                        continue
                
                if len(cards) == 0:
                    print(f"❌ No cards found in {column_name.title()} column with any selector")
                    continue
                
                # Extract tokens from cards
                column_tokens = 0
                for i, card in enumerate(cards[:10]):  # Limit to first 10 cards
                    try:
                        # Debug: show what's in each card
                        card_text = await card.text_content()
                        if card_text:
                            print(f"   🃏 Card {i+1}: {card_text[:100]}...")
                        
                        token_data = await self._extract_token_data(card, column_name)
                        if token_data and token_data.get('contract'):
                            self.seen_tokens.add(token_data['contract'])
                            column_tokens += 1
                            total_found += 1
                            
                            # Show the top token for verification
                            if i == 0:
                                print(f"   🥇 Top token: {token_data['ticker']} - {token_data['contract'][:20]}...")
                            
                    except Exception as e:
                        print(f"   ❌ Error parsing card {i+1}: {e}")
                        continue  # Skip cards that can't be parsed
                
                print(f"   📈 Found {column_tokens} tokens in {column_name.title()} column")
            
            print(f"\n✅ Total existing tokens found: {total_found}")
            print("👀 Now watching for NEW tokens only...")
            
        except Exception as e:
            print(f"❌ Error loading initial tokens: {e}")
            import traceback
            traceback.print_exc()
    
    async def _check_for_new_tokens(self):
        """Check for new tokens in all monitored columns"""
        try:
            new_tokens_found = 0
            
            for column_name in self.columns:
                # Find the column
                column_text = await self.page.query_selector(f"text={column_name.title()}")
                if not column_text:
                    continue
                
                column_container = await column_text.query_selector("xpath=..")
                if not column_container:
                    continue
                
                # Get cards in this column
                cards = await column_container.query_selector_all("div")
                
                for card in cards[:5]:  # Check first 5 cards for new tokens
                    try:
                        token_data = await self._extract_token_data(card, column_name)
                        if not token_data or not token_data.get('contract'):
                            continue
                        
                        # Check if this is a new token
                        if token_data['contract'] not in self.seen_tokens:
                            new_tokens_found += 1
                            print(f"\n🆕 NEW TOKEN DETECTED!")
                            print(f"📊 Column: {column_name.title()}")
                            print(f"🪙 Token: {token_data['ticker']}")
                            print(f"📝 Contract: {token_data['contract']}")
                            print(f"💰 Allocation: {self.column_configs[column_name]['allocation_pct']}%")
                            print("-" * 50)
                            
                            # Add to seen tokens
                            self.seen_tokens.add(token_data['contract'])
                            
                            # Create strand and trigger trader
                            await self._create_gem_bot_strand(token_data, column_name)
                            
                    except Exception as e:
                        continue  # Skip cards that can't be parsed
            
            if new_tokens_found == 0:
                print(f"👀 No new tokens found (checking {len(self.columns)} columns)")
            
        except Exception as e:
            print(f"❌ Error checking for new tokens: {e}")
    
    async def _extract_token_data(self, card_element, column_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Extract token data from a coin card element
        
        Args:
            card_element: Playwright element for the coin card
            
        Returns:
            Token data dictionary or None if extraction failed
        """
        try:
            token_data = {}
            
            # Extract token name/ticker (usually in a heading or prominent text)
            name_element = await card_element.query_selector("h1, h2, h3, h4, .token-name, [class*='name'], [class*='ticker']")
            if name_element:
                token_data['ticker'] = await name_element.text_content()
                token_data['ticker'] = token_data['ticker'].strip() if token_data['ticker'] else None
            
            # Extract project name/description
            desc_element = await card_element.query_selector(".description, [class*='desc'], [class*='project']")
            if desc_element:
                token_data['project_name'] = await desc_element.text_content()
                token_data['project_name'] = token_data['project_name'].strip() if token_data['project_name'] else None
            
            # Extract contract address (look for long alphanumeric strings)
            text_content = await card_element.text_content()
            contract_match = re.search(r'[A-Za-z0-9]{32,44}', text_content)
            if contract_match:
                token_data['contract'] = contract_match.group()
            
            # Extract metrics from the grid
            metrics = await self._extract_metrics(card_element)
            token_data.update(metrics)
            
            # Extract timestamp
            time_element = await card_element.query_selector("[class*='time'], [class*='timestamp'], time")
            if time_element:
                token_data['timestamp'] = await time_element.text_content()
                token_data['timestamp'] = token_data['timestamp'].strip() if token_data['timestamp'] else None
            
            # Extract multiplier if present (look for X pattern)
            multiplier_match = re.search(r'(\d+)X', text_content)
            if multiplier_match:
                token_data['multiplier'] = int(multiplier_match.group(1))
            
            # Set defaults for required fields
            token_data.setdefault('chain', 'solana')
            token_data.setdefault('dex', 'Raydium')
            token_data.setdefault('verified', True)  # Conservative tokens are pre-vetted
            
            return token_data if token_data.get('contract') else None
            
        except Exception as e:
            self.logger.error(f"Error extracting token data: {e}")
            return None
    
    async def _extract_metrics(self, card_element) -> Dict[str, Any]:
        """Extract trading metrics from the card"""
        try:
            metrics = {}
            text_content = await card_element.text_content()
            
            # Extract market cap
            market_cap_match = re.search(r'Market Cap[:\s]*\$?([0-9,]+\.?[0-9]*[KMB]?)', text_content, re.IGNORECASE)
            if market_cap_match:
                metrics['market_cap'] = self._parse_metric_value(market_cap_match.group(1))
            
            # Extract liquidity
            liquidity_match = re.search(r'Liquidity[:\s]*\$?([0-9,]+\.?[0-9]*[KMB]?)', text_content, re.IGNORECASE)
            if liquidity_match:
                metrics['liquidity'] = self._parse_metric_value(liquidity_match.group(1))
            
            # Extract transactions
            transactions_match = re.search(r'Transactions[:\s]*([0-9,]+)', text_content, re.IGNORECASE)
            if transactions_match:
                metrics['transactions'] = int(transactions_match.group(1).replace(',', ''))
            
            # Extract holders
            holders_match = re.search(r'Holders[:\s]*([0-9,]+)', text_content, re.IGNORECASE)
            if holders_match:
                metrics['holders'] = int(holders_match.group(1).replace(',', ''))
            
            # Extract percentages
            creator_match = re.search(r'Creator[:\s]*([0-9.]+)%', text_content, re.IGNORECASE)
            if creator_match:
                metrics['creator_pct'] = float(creator_match.group(1))
            
            bundled_match = re.search(r'Bundled[:\s]*([0-9.]+)%', text_content, re.IGNORECASE)
            if bundled_match:
                metrics['bundled_pct'] = float(bundled_match.group(1))
            
            snipers_match = re.search(r'Snipers[:\s]*([0-9.]+)%', text_content, re.IGNORECASE)
            if snipers_match:
                metrics['snipers_pct'] = float(snipers_match.group(1))
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error extracting metrics: {e}")
            return {}
    
    def _parse_metric_value(self, value_str: str) -> float:
        """Parse metric value string (e.g., '1.2K', '500M') to float"""
        try:
            value_str = value_str.replace(',', '').upper()
            if value_str.endswith('K'):
                return float(value_str[:-1]) * 1000
            elif value_str.endswith('M'):
                return float(value_str[:-1]) * 1000000
            elif value_str.endswith('B'):
                return float(value_str[:-1]) * 1000000000
            else:
                return float(value_str)
        except:
            return 0.0
    
    async def _create_gem_bot_strand(self, token_data: Dict[str, Any], column_name: str):
        """
        Create a gem_bot strand for the trader
        
        Args:
            token_data: Extracted token data from Conservative column
        """
        try:
            # Get column configuration
            config = self.column_configs[column_name]
            
            # Generate strand ID
            strand_id = f"gem_bot_{token_data['ticker']}_{int(datetime.now().timestamp())}"
            
            print(f"🚀 Creating strand for {token_data['ticker']} from {column_name.title()} column...")
            
            # Create the strand with proper structure for trader
            strand = {
                "id": strand_id,
                "module": "gem_bot_monitor",
                "kind": config['strand_kind'],
                "symbol": token_data['ticker'],
                "timeframe": None,
                "session_bucket": f"gem_bot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}",
                "regime": column_name.lower(),
                "tags": ["gem_bot", column_name.lower(), "auto_approved", "high_quality", "pre_vetted"],
                "target_agent": "trader_lowcap",  # Direct to trader
                "sig_sigma": 1.0,  # High confidence for Conservative tokens
                "sig_confidence": 0.95,  # Very high confidence
                "confidence": 0.95,
                "sig_direction": "buy",  # Always buy for Conservative tokens
                "trading_plan": None,  # Will be filled by trader
                "signal_pack": {
                    "token": {
                        "ticker": token_data['ticker'],
                        "contract": token_data['contract'],
                        "chain": token_data['chain'],
                        "price": None,  # Will be fetched by trader
                        "volume_24h": None,
                        "market_cap": token_data.get('market_cap'),
                        "liquidity": token_data.get('liquidity'),
                        "dex": token_data['dex'],
                        "verified": token_data['verified'],
                        "project_name": token_data.get('project_name'),
                        "multiplier": token_data.get('multiplier'),
                        "holders": token_data.get('holders'),
                        "transactions": token_data.get('transactions'),
                        "creator_pct": token_data.get('creator_pct'),
                        "bundled_pct": token_data.get('bundled_pct'),
                        "snipers_pct": token_data.get('snipers_pct')
                    },
                    "venue": {
                        "dex": token_data['dex'],
                        "chain": token_data['chain'],
                        "liq_usd": token_data.get('liquidity', 0),
                        "vol24h_usd": 0  # Not available from Conservative column
                    },
                    "curator": {
                        "id": f"gem_bot_{column_name.lower()}",
                        "platform": "gem_bot",
                        "handle": f"{column_name.title()} Column",
                        "weight": 1.0,  # Maximum weight for Gem Bot tokens
                        "verified": True,
                        "reliability_score": 0.95
                    },
                    "trading_signals": {
                        "action": "buy",
                        "confidence": 0.95,
                        "allocation_pct": config['allocation_pct'],
                        "allocation_usd": None,  # Will be calculated by trader
                        "reasoning": f"{column_name.title()} column token: {token_data['ticker']} - Pre-vetted high-quality token",
                        "risk_level": config['risk_level'],
                        "auto_approve": self.auto_approve
                    },
                    "message": {
                        "text": f"New {column_name.title()} token: {token_data['ticker']} - {token_data.get('project_name', '')}",
                        "timestamp": token_data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                        "url": f"https://gembot.io/feed"
                    }
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "agent_id": "gem_bot_monitor",
                "team_member": f"{column_name.lower()}_column"
            }
            
            # Save strand to database
            success = await self.supabase_manager.create_strand(strand)
            if success:
                self.logger.info(f"✅ Created gem_bot strand: {strand_id} for {token_data['ticker']}")
                
                # Process strand through learning system (will trigger trader)
                await self.learning_system.process_strand_event(strand)
                
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
    
    # Create and start monitor
    monitor = GemBotMonitor(supabase_manager, llm_client, learning_system)
    await monitor.start_monitoring(check_interval=5)


if __name__ == "__main__":
    asyncio.run(main())
