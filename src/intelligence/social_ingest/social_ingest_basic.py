"""
Social Ingest Module - Basic Version

Real-time social media scraping and token extraction for social lowcap intelligence.
Uses LLM for information extraction and mock API for token verification.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import yaml
import os
import re

logger = logging.getLogger(__name__)


class SocialIngestModule:
    """
    Social Ingest Module - Basic real-time scraping and token extraction
    
    This module:
    - Monitors curator accounts (Twitter, Telegram)
    - Uses LLM to extract token information from messages
    - Verifies tokens with mock API (can be replaced with real APIs)
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
                {'curator_id': 'tw:@alphaOne', 'platform': 'twitter', 'handle': '@alphaOne', 'weight': 1.0, 'enabled': True},
                {'curator_id': 'tw:@smartWhale', 'platform': 'twitter', 'handle': '@smartWhale', 'weight': 0.8, 'enabled': True},
                {'curator_id': 'tw:@cryptoInsider', 'platform': 'twitter', 'handle': '@cryptoInsider', 'weight': 0.9, 'enabled': True},
                {'curator_id': 'tg:@lowcapHunter', 'platform': 'telegram', 'handle': '@lowcapHunter', 'weight': 0.7, 'enabled': True},
                {'curator_id': 'tg:@scout', 'platform': 'telegram', 'handle': '@scout', 'weight': 1.0, 'enabled': True}
            ]
        }
    
    def process_social_signal(self, curator_id: str, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a social media signal from a curator
        
        Args:
            curator_id: Curator identifier (e.g., "tw:@alphaOne")
            message_data: Raw message data from social media
            
        Returns:
            Created strand data or None if processing failed
        """
        try:
            # Check if curator is enabled
            if curator_id not in self.enabled_curators:
                self.logger.debug(f"Curator {curator_id} not enabled, skipping")
                return None
            
            curator = self.enabled_curators[curator_id]
            
            # Check if message contains token mentions
            if not self._contains_token_mention(message_data.get('text', '')):
                self.logger.debug(f"No token mention found in message from {curator_id}")
                return None
            
            # Extract token information using LLM
            token_info = asyncio.run(self._extract_token_info_with_llm(message_data.get('text', '')))
            if not token_info:
                self.logger.debug(f"No token info extracted from message by {curator_id}")
                return None
            
            # Verify token with mock API
            verified_token = self._verify_token_with_mock_api(token_info)
            if not verified_token:
                self.logger.debug(f"Token verification failed for {token_info.get('token_name', 'unknown')}")
                return None
            
            # Create social_lowcap strand
            strand = self._create_social_strand(curator, message_data, verified_token)
            
            # Update curator last_seen_at
            self._update_curator_last_seen(curator_id)
            
            self.logger.info(f"Created social_lowcap strand for {curator_id} -> {verified_token.get('ticker', 'unknown')}")
            return strand
            
        except Exception as e:
            self.logger.error(f"Failed to process social signal from {curator_id}: {e}")
            return None
    
    def _contains_token_mention(self, text: str) -> bool:
        """Check if message contains token mentions"""
        # Look for common patterns
        patterns = [
            r'\$[A-Z]{2,10}',  # $TOKEN
            r'[A-Z]{2,10}/SOL',  # TOKEN/SOL
            r'[A-Z]{2,10}/ETH',  # TOKEN/ETH
            r'buy\s+[A-Z]{2,10}',  # buy TOKEN
            r'pump\s+[A-Z]{2,10}',  # pump TOKEN
            r'[A-Z]{2,10}\s+token',  # TOKEN token
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    async def _extract_token_info_with_llm(self, message_text: str) -> Optional[Dict[str, Any]]:
        """Extract token information using LLM with proper prompt templates"""
        try:
            # Use the proper prompt template from the prompt manager
            if hasattr(self.llm_client, 'get_prompt'):
                prompt_data = self.llm_client.get_prompt('social_lowcap', 'token_extraction')
                prompt = prompt_data['prompt'].format(message_text=message_text)
                system_message = prompt_data.get('system_message', '')
            else:
                # Fallback to hardcoded prompt if prompt manager not available
                prompt = f"""
                Extract token information from this social media message:
                
                "{message_text}"
                
                Return a JSON object with:
                - token_name: The token ticker/symbol
                - network: The blockchain network (solana, ethereum, base, etc.)
                - contract_address: If mentioned
                - sentiment: positive, negative, or neutral
                - confidence: 0.0 to 1.0
                - additional_info: Any other relevant information
                
                If no clear token is mentioned, return null.
                """
                system_message = ""
            
            # Generate response with system message if available
            if system_message:
                response = await self.llm_client.generate_async(prompt, system_message=system_message)
            else:
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
    
    def _verify_token_with_mock_api(self, token_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verify token with mock API (can be replaced with real Birdeye/Helix API)"""
        try:
            token_name = token_info['token_name']
            network = token_info.get('network', 'solana')
            
            # Mock API response based on token name
            mock_responses = {
                'FOO': {
                    'ticker': 'FOO',
                    'contract': 'So1aNa1234567890abcdef',
                    'chain': 'solana',
                    'price': 0.25,
                    'volume_24h': 50000,
                    'market_cap': 1000000,
                    'liquidity': 15000,
                    'dex': 'Raydium',
                    'verified': True
                },
                'BAR': {
                    'ticker': 'BAR',
                    'contract': '0x1234567890abcdef',
                    'chain': 'ethereum',
                    'price': 0.15,
                    'volume_24h': 75000,
                    'market_cap': 2000000,
                    'liquidity': 25000,
                    'dex': 'Uniswap',
                    'verified': True
                }
            }
            
            # Return mock data if available, otherwise create generic mock
            if token_name in mock_responses:
                return mock_responses[token_name]
            else:
                return {
                    'ticker': token_name,
                    'contract': f"mock_contract_{token_name}",
                    'chain': network,
                    'price': 0.20,
                    'volume_24h': 30000,
                    'market_cap': 500000,
                    'liquidity': 10000,
                    'dex': 'Raydium',
                    'verified': True
                }
            
        except Exception as e:
            self.logger.error(f"Error verifying token with mock API: {e}")
            return None
    
    def _create_social_strand(self, curator: Dict[str, Any], message_data: Dict[str, Any], token: Dict[str, Any]) -> Dict[str, Any]:
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
                        "text": message_data.get('text', ''),
                        "timestamp": message_data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                        "url": message_data.get('url', '')
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
    
    def _update_curator_last_seen(self, curator_id: str):
        """Update curator last_seen_at timestamp"""
        try:
            # Update curator in database
            self.supabase_manager.update_curator_last_seen(curator_id)
        except Exception as e:
            self.logger.error(f"Failed to update curator last_seen: {e}")
    
    def get_enabled_curators(self) -> List[Dict[str, Any]]:
        """Get list of enabled curators"""
        return list(self.enabled_curators.values())
    
    def is_curator_enabled(self, curator_id: str) -> bool:
        """Check if curator is enabled"""
        return curator_id in self.enabled_curators
