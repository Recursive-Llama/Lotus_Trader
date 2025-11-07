"""
Social Ingest Module

Real-time social media scraping and token extraction for social lowcap intelligence.
Uses Playwright for Twitter scraping, LLM for information extraction, and Birdeye/Helix for token verification.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import yaml
import os
import re
from playwright.async_api import async_playwright, Browser, Page
import aiohttp

logger = logging.getLogger(__name__)


class SocialIngestModule:
    """
    Social Ingest Module - Real-time scraping and token extraction
    
    This module:
    - Scrapes Twitter with Playwright (headless browser with saved cookies)
    - Monitors curator accounts in round-robin (1 account/30 seconds)
    - Uses LLM to extract token information from tweets
    - Verifies tokens with Birdeye/Helix API
    - Monitors public Telegram groups
    - Creates social_lowcap strands for DML
    """
    
    def __init__(self, supabase_manager, llm_client, config_path: str = None):
        """
        Initialize Social Ingest Module
        
        Args:
            supabase_manager: Database manager for strand creation
            llm_client: LLM client for information extraction
            config_path: Path to curator configuration file
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Load curator configuration
        if config_path and os.path.exists(config_path):
            self.curators_config = self._load_curators_config(config_path)
        else:
            self.curators_config = self._get_default_curators_config()
        
        self.enabled_curators = {
            curator['curator_id']: curator 
            for curator in self.curators_config['curators'] 
            if curator.get('enabled', True)
        }
        
        # Browser and scraping state
        self.browser = None
        self.page = None
        self.cookies_file = "twitter_cookies.json"
        self.last_check_times = {}
        self.check_interval = 30  # seconds between checks per account
        
        # API clients
        self.birdeye_api_key = os.getenv('BIRDEYE_API_KEY')
        self.helix_api_key = os.getenv('HELIX_API_KEY')
        
        self.logger.info(f"Social Ingest Module initialized with {len(self.enabled_curators)} enabled curators")
    
    def _load_curators_config(self, config_path: str) -> Dict[str, Any]:
        """Load curator configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load curators config: {e}")
            return self._get_default_curators_config()
    
    def _get_default_curators_config(self) -> Dict[str, Any]:
        """Get default curator configuration"""
        return {
            'curators': [
                {'curator_id': 'tw:@alphaOne', 'platform': 'twitter', 'handle': '@alphaOne', 'weight': 1.0, 'enabled': True, 'url': 'https://twitter.com/alphaOne'},
                {'curator_id': 'tw:@smartWhale', 'platform': 'twitter', 'handle': '@smartWhale', 'weight': 0.8, 'enabled': True, 'url': 'https://twitter.com/smartWhale'},
                {'curator_id': 'tw:@cryptoInsider', 'platform': 'twitter', 'handle': '@cryptoInsider', 'weight': 0.9, 'enabled': True, 'url': 'https://twitter.com/cryptoInsider'},
                {'curator_id': 'tg:@lowcapHunter', 'platform': 'telegram', 'handle': '@lowcapHunter', 'weight': 0.7, 'enabled': True, 'group_id': '@lowcapHunter'},
                {'curator_id': 'tg:@scout', 'platform': 'telegram', 'handle': '@scout', 'weight': 1.0, 'enabled': True, 'group_id': '@scout'}
            ]
        }
    
    async def start_monitoring(self):
        """Start the monitoring loop"""
        self.logger.info("Starting social media monitoring...")
        
        # Initialize browser
        await self._init_browser()
        
        # Start monitoring loop
        while True:
            try:
                await self._monitor_round_robin()
                await asyncio.sleep(5)  # Small delay between rounds
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _init_browser(self):
        """Initialize Playwright browser with saved cookies"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            
            # Load saved cookies if they exist
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    await self.page.context.add_cookies(cookies)
                    self.logger.info("Loaded saved Twitter cookies")
            
            # Go to Twitter to verify login
            await self.page.goto("https://twitter.com")
            await asyncio.sleep(2)
            
            # Check if we need to login
            if "login" in self.page.url:
                self.logger.warning("Twitter login required - please login manually and save cookies")
                await self._manual_login()
            
            self.logger.info("Browser initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {e}")
            raise
    
    async def _manual_login(self):
        """Handle manual login process"""
        self.logger.info("Please login to Twitter manually...")
        self.logger.info("Press Enter when login is complete...")
        input()  # Wait for user input
        
        # Save cookies
        cookies = await self.page.context.cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f)
        self.logger.info("Cookies saved for future use")
    
    async def _monitor_round_robin(self):
        """Monitor all curator accounts in round-robin fashion"""
        current_time = datetime.now(timezone.utc)
        
        for curator_id, curator in self.enabled_curators.items():
            # Check if enough time has passed since last check
            last_check = self.last_check_times.get(curator_id, datetime.min.replace(tzinfo=timezone.utc))
            if (current_time - last_check).total_seconds() < self.check_interval:
                continue
            
            try:
                if curator['platform'] == 'twitter':
                    await self._check_twitter_account(curator)
                elif curator['platform'] == 'telegram':
                    await self._check_telegram_group(curator)
                
                self.last_check_times[curator_id] = current_time
                
            except Exception as e:
                self.logger.error(f"Error checking {curator_id}: {e}")
    
    async def _check_twitter_account(self, curator: Dict[str, Any]):
        """Check a Twitter account for new tweets"""
        try:
            url = curator['url']
            await self.page.goto(url)
            await asyncio.sleep(2)
            
            # Get recent tweets
            tweets = await self.page.evaluate("""
                () => {
                    const tweets = [];
                    const tweetElements = document.querySelectorAll('[data-testid="tweet"]');
                    
                    for (let tweet of tweetElements) {
                        const textElement = tweet.querySelector('[data-testid="tweetText"]');
                        const timeElement = tweet.querySelector('time');
                        
                        if (textElement && timeElement) {
                            tweets.push({
                                text: textElement.innerText,
                                timestamp: timeElement.getAttribute('datetime'),
                                url: window.location.href
                            });
                        }
                    }
                    
                    return tweets;
                }
            """)
            
            # Process each tweet
            for tweet in tweets:
                await self._process_tweet(curator, tweet)
                
        except Exception as e:
            self.logger.error(f"Error checking Twitter account {curator['handle']}: {e}")
    
    async def _check_telegram_group(self, curator: Dict[str, Any]):
        """Check a Telegram group for new messages"""
        # Telegram scraping is more complex and requires different approach
        # For now, we'll implement a placeholder
        self.logger.info(f"Telegram monitoring for {curator['handle']} not yet implemented")
        pass
    
    async def _process_tweet(self, curator: Dict[str, Any], tweet: Dict[str, Any]):
        """Process a tweet and extract token information"""
        try:
            # Check if tweet contains token mentions
            if not self._contains_token_mention(tweet['text']):
                return
            
            # Extract token information using LLM
            token_info = await self._extract_token_info_with_llm(tweet['text'])
            if not token_info:
                return
            
            # Verify token with Birdeye/Helix
            verified_token = await self._verify_token_with_api(token_info)
            if not verified_token:
                return
            
            # Create social_lowcap strand
            await self._create_social_strand(curator, tweet, verified_token)
            
        except Exception as e:
            self.logger.error(f"Error processing tweet: {e}")
    
    def _contains_token_mention(self, text: str) -> bool:
        """Check if tweet contains token mentions"""
        # Look for common patterns
        patterns = [
            r'\$[A-Z]{2,10}',  # $TOKEN
            r'[A-Z]{2,10}/SOL',  # TOKEN/SOL
            r'[A-Z]{2,10}/ETH',  # TOKEN/ETH
            r'buy\s+[A-Z]{2,10}',  # buy TOKEN
            r'pump\s+[A-Z]{2,10}',  # pump TOKEN
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    async def _extract_token_info_with_llm(self, tweet_text: str) -> Optional[Dict[str, Any]]:
        """Extract token information using LLM"""
        try:
            prompt = f"""
            Extract token information from this tweet:
            
            "{tweet_text}"
            
            Return a JSON object with:
            - token_name: The token ticker/symbol
            - network: The blockchain network (solana, ethereum, base, etc.)
            - contract_address: If mentioned
            - sentiment: positive, negative, or neutral
            - confidence: 0.0 to 1.0
            - additional_info: Any other relevant information
            
            If no clear token is mentioned, return null.
            """
            
            response = await self.llm_client.generate_async(prompt)
            
            # Parse JSON response
            try:
                token_info = json.loads(response)
                if token_info and token_info.get('token_name'):
                    return token_info
            except json.JSONDecodeError:
                pass
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting token info with LLM: {e}")
            return None
    
    async def _verify_token_with_api(self, token_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verify token with Birdeye/Helix API"""
        try:
            token_name = token_info['token_name']
            network = token_info.get('network', 'solana')
            
            # Use Birdeye API to search for token
            if self.birdeye_api_key:
                verified_token = await self._search_birdeye(token_name, network)
                if verified_token:
                    return verified_token
            
            # Fallback to Helix if available
            if self.helix_api_key:
                verified_token = await self._search_helix(token_name, network)
                if verified_token:
                    return verified_token
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error verifying token with API: {e}")
            return None
    
    async def _search_birdeye(self, token_name: str, network: str) -> Optional[Dict[str, Any]]:
        """Search for token using Birdeye API"""
        try:
            url = f"https://public-api.birdeye.so/public/v1/search?q={token_name}"
            headers = {"X-API-KEY": self.birdeye_api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Find the best match by volume
                        if data.get('tokens'):
                            tokens = data['tokens']
                            # Sort by volume and take the first one
                            best_token = max(tokens, key=lambda x: x.get('volume24h', 0))
                            
                            return {
                                'ticker': best_token.get('symbol', token_name),
                                'contract': best_token.get('address'),
                                'chain': network,
                                'price': best_token.get('price'),
                                'volume_24h': best_token.get('volume24h'),
                                'market_cap': best_token.get('mc'),
                                'liquidity': best_token.get('liquidity'),
                                'dex': best_token.get('dex'),
                                'verified': True
                            }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error searching Birdeye: {e}")
            return None
    
    async def _search_helix(self, token_name: str, network: str) -> Optional[Dict[str, Any]]:
        """Search for token using Helix API"""
        # Placeholder for Helix API integration
        self.logger.info(f"Helix API search for {token_name} not yet implemented")
        return None
    
    async def _create_social_strand(self, curator: Dict[str, Any], tweet: Dict[str, Any], token: Dict[str, Any]):
        """Create social_lowcap strand for DML"""
        try:
            strand = {
                "module": "social_ingest",
                "kind": "social_lowcap",
                "content": {
                    "curator_id": curator['curator_id'],
                    "platform": curator['platform'],
                    "handle": curator['handle'],
                    "token": {
                        "ticker": token['ticker'],
                        "contract": token.get('contract'),
                        "chain": token['chain'],
                        "price": token.get('price'),
                        "volume_24h": token.get('volume_24h'),
                        "market_cap": token.get('market_cap'),
                        "liquidity": token.get('liquidity'),
                        "dex": token.get('dex'),
                        "verified": token.get('verified', False)
                    },
                    "venue": {
                        "dex": token.get('dex', 'Unknown'),
                        "chain": token['chain'],
                        "liq_usd": token.get('liquidity', 0),
                        "vol24h_usd": token.get('volume_24h', 0)
                    },
                    "message": {
                        "text": tweet['text'],
                        "timestamp": tweet['timestamp'],
                        "url": tweet['url']
                    },
                    "curator_weight": curator['weight'],
                    "context_slices": {
                        "liquidity_bucket": self._get_liquidity_bucket(token.get('liquidity', 0)),
                        "volume_bucket": self._get_volume_bucket(token.get('volume_24h', 0)),
                        "time_bucket_utc": self._get_time_bucket(),
                        "sentiment": "positive"  # Would be extracted from LLM
                    }
                },
                "tags": ["curated", "social_signal", "dm_candidate", "verified"],
                "status": "active"
            }
            
            # Create strand in database
            created_strand = self.supabase_manager.create_strand(strand)
            
            self.logger.info(f"Created social_lowcap strand: {curator['handle']} -> {token['ticker']}")
            return created_strand
            
        except Exception as e:
            self.logger.error(f"Error creating social strand: {e}")
            return None
    
    def _get_liquidity_bucket(self, liquidity: float) -> str:
        """Get liquidity bucket for context slicing"""
        if liquidity < 5000:
            return "<5k"
        elif liquidity < 25000:
            return "5-25k"
        elif liquidity < 100000:
            return "25-100k"
        else:
            return "100k+"
    
    def _get_volume_bucket(self, volume: float) -> str:
        """Get volume bucket for context slicing"""
        if volume < 10000:
            return "<10k"
        elif volume < 100000:
            return "10-100k"
        elif volume < 1000000:
            return "100k-1M"
        else:
            return "1M+"
    
    def _get_time_bucket(self) -> str:
        """Get time bucket for context slicing"""
        current_hour = datetime.now(timezone.utc).hour
        if 0 <= current_hour < 6:
            return "0-6"
        elif 6 <= current_hour < 12:
            return "6-12"
        elif 12 <= current_hour < 18:
            return "12-18"
        else:
            return "18-24"
    
    async def stop_monitoring(self):
        """Stop the monitoring loop and cleanup"""
        if self.browser:
            await self.browser.close()
        self.logger.info("Social media monitoring stopped")
    
    def get_enabled_curators(self) -> List[Dict[str, Any]]:
        """Get list of enabled curators"""
        return list(self.enabled_curators.values())
    
    def is_curator_enabled(self, curator_id: str) -> bool:
        """Check if curator is enabled"""
        return curator_id in self.enabled_curators