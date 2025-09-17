"""
Social Ingest Module - Basic Version

Real-time social media scraping and token extraction for social lowcap intelligence.
Uses LLM for information extraction and mock API for token verification.
"""

import logging
import asyncio
import json
import aiohttp
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
    - Verifies tokens with DexScreener API
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
        
        # Initialize prompt manager for template-based prompts
        from llm_integration.prompt_manager import PromptManager
        self.prompt_manager = PromptManager()
        
        # DexScreener API configuration
        self.dexscreener_base_url = "https://api.dexscreener.com/latest/dex/search"
        # Allowed chains and minimum volume thresholds (USD) for early filtering
        self.allowed_chains = ['solana', 'ethereum', 'base']
        self.min_volume_requirements = {
            'solana': 100000,   # $100k on Solana
            'ethereum': 25000,  # $25k on Ethereum
            'base': 25000       # $25k on Base
        }
        # Minimum liquidity requirements (USD) for early filtering
        self.min_liquidity_requirements = {
            'solana': 20000,    # $20k on Solana
            'ethereum': 20000,  # $20k on Ethereum
            'base': 20000       # $20k on Base
        }
        
        # Load curator configuration
        if config_path and os.path.exists(config_path):
            self.curators_config = self._load_curators_config(config_path)
            self.logger.info(f"Loaded curator config from: {config_path}")
        else:
            # Default to src/config/twitter_curators.yaml
            default_config_path = "src/config/twitter_curators.yaml"
            if os.path.exists(default_config_path):
                self.curators_config = self._load_curators_config(default_config_path)
                self.logger.info(f"Loaded curator config from: {default_config_path}")
            else:
                self.curators_config = self._get_default_curators_config()
        
        # Build enabled curators dictionary with platform support
        self.enabled_curators = {}
        for curator in self.curators_config['curators']:
            if curator.get('enabled', True):
                curator_id = curator['id']
                self.enabled_curators[curator_id] = curator
                
                # Add platform-specific entries for easy lookup
                for platform, platform_data in curator.get('platforms', {}).items():
                    if platform_data.get('active', True):
                        platform_curator_id = f"{platform}:{platform_data['handle']}"
                        self.enabled_curators[platform_curator_id] = {
                            **curator,
                            'platform': platform,
                            'platform_data': platform_data
                        }
        
        # Populate curators table on startup (synchronous)
        self._populate_curators_table_sync()
        
        # Count unique curators (not platform-specific entries)
        unique_curators = len([c for c in self.curators_config['curators'] if c.get('enabled', True)])
        self.logger.info(f"Social Ingest Module initialized with {unique_curators} curators ({len(self.enabled_curators)} total entries including platform-specific)")
    
    def _load_curators_config(self, config_path: str) -> Dict[str, Any]:
        """Load curator configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load curators config: {e}")
            return self._get_default_curators_config()
    
    def _get_default_curators_config(self) -> Dict[str, Any]:
        """Get default curator configuration - fallback if YAML file not found"""
        self.logger.warning("Using fallback curator configuration - YAML file not found")
        return {
            'curators': [
                {
                    'id': '0xdetweiler',
                    'name': '0xDetweiler',
                    'platforms': {
                        'twitter': {
                            'handle': '@0xdetweiler',
                            'active': True,
                            'weight': 0.8,
                            'priority': 'high'
                        }
                    },
                    'tags': ['defi', 'alpha', 'technical'],
                    'enabled': True
                }
            ]
        }
    
    async def process_social_signal(self, curator_id: str, message_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a social media signal from a curator
        
        Args:
            curator_id: Curator identifier (e.g., "tw:@alphaOne")
            message_data: Raw message data from social media
            
        Returns:
            List of created strand data (one per token) or empty list if processing failed
        """
        try:
            # Check if curator is enabled
            if curator_id not in self.enabled_curators:
                self.logger.debug(f"Curator {curator_id} not enabled, skipping")
                return []
            
            curator = self.enabled_curators[curator_id]
            
            # Skip regex filtering - go straight to LLM for all messages
            # (Regex was too restrictive and missing many valid tokens)
            
            # Extract token information using LLM (with image if available)
            image_data = message_data.get('image_data')
            extraction_result = await self._extract_token_info_with_llm(message_data.get('text', ''), image_data)
            
            # Debug: Show what the LLM returned
            print(f"   🔍 LLM Response: {extraction_result}")
            
            if not extraction_result or not extraction_result.get('tokens'):
                self.logger.debug(f"No token info extracted from message by {curator_id}")
                return []
            
            # Check if LLM found a handle that needs verification
            if extraction_result.get('handle_mentioned') and extraction_result.get('needs_verification'):
                self.logger.info(f"🔍 Found handle mention: {extraction_result['handle_mentioned']}, scanning for token info...")
                handle_token_info = await self._scan_handle_for_token(extraction_result['handle_mentioned'])
                if handle_token_info:
                    # Replace tokens with handle token info
                    extraction_result['tokens'] = [handle_token_info]
                    self.logger.info(f"✅ Found token info for handle: {handle_token_info.get('token_name', 'unknown')}")
                else:
                    self.logger.debug(f"No token info found for handle: {extraction_result['handle_mentioned']}")
                    return []
            
            # Process each token found
            created_strands = []
            for token_info in extraction_result['tokens']:
                print(f"   🔍 Processing token: {token_info.get('token_name', 'unknown')}")
                # Verify token with DexScreener API
                verified_token = await self._verify_token_with_dexscreener(token_info)
                if not verified_token:
                    print(f"   ❌ Token verification failed for {token_info.get('token_name', 'unknown')}")
                    self.logger.debug(f"Token verification failed for {token_info.get('token_name', 'unknown')}")
                    continue
                else:
                    print(f"   ✅ Token verified: {verified_token.get('ticker', 'unknown')}")
                
                # Create social_lowcap strand for this token
                print(f"   🔧 Creating strand for {verified_token.get('ticker', 'unknown')}...")
                strand = await self._create_social_strand(curator, message_data, verified_token, extraction_result)
                if strand:
                    created_strands.append(strand)
                    print(f"   ✅ Strand created successfully for {verified_token.get('ticker', 'unknown')}")
                    self.logger.info(f"Created social_lowcap strand for {curator_id} -> {verified_token.get('ticker', 'unknown')}")
                else:
                    print(f"   ❌ Strand creation failed for {verified_token.get('ticker', 'unknown')}")
            
            # Update curator last_seen_at
            # TODO: Implement curator last_seen update
            # self._update_curator_last_seen(curator_id)
            
            print(f"   📊 Final result: {len(created_strands)} strands created")
            return created_strands
            
        except Exception as e:
            self.logger.error(f"Failed to process social signal from {curator_id}: {e}")
            return []
    
    def _contains_token_mention(self, text: str) -> bool:
        """Check if message contains token mentions"""
        # Look for common patterns
        patterns = [
            r'\$[A-Z]{2,10}',  # $TOKEN
            r'@[A-Za-z0-9_]+',  # @handle (might be token)
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
    
    async def _extract_token_info_with_llm(self, message_text: str, image_data: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
        """Extract token information using LLM with proper prompt templates and image analysis"""
        try:
            print(f"   🔧 Calling LLM with text: {message_text[:100]}...")
            
            # Use prompt manager to get token extraction template
            prompt = self.prompt_manager.format_prompt(
                'token_extraction', 
                {'message_text': message_text}
            )
            system_message = self.prompt_manager.get_system_message('token_extraction')
            
            print(f"   🔧 Using prompt manager: True")
            print(f"   🔧 System message: {system_message[:50] if system_message else 'None'}...")
            
            # Generate response with system message if available
            if system_message:
                if image_data:
                    response = await self.llm_client.generate_async(prompt, system_message=system_message, image=image_data)
                else:
                    response = await self.llm_client.generate_async(prompt, system_message=system_message)
            else:
                if image_data:
                    response = await self.llm_client.generate_async(prompt, image=image_data)
                else:
                    response = await self.llm_client.generate_async(prompt)
            
            print(f"   🔧 Raw LLM response: {response}")
            
            # Parse JSON response with robust parsing
            parsed_response = self._parse_llm_response(response)
            if parsed_response and parsed_response.get('tokens'):
                # LLM now returns {"tokens": [...]} format
                return parsed_response
            elif parsed_response and (parsed_response.get('token_name') or parsed_response.get('handle_mentioned')):
                # Fallback for old single token format
                return {'tokens': [parsed_response]}
            
            return None
            
        except Exception as e:
            print(f"   ❌ LLM error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Robustly parse LLM response, handling markdown and various formats"""
        try:
            # First try direct JSON parsing
            if response.strip().startswith('{'):
                return json.loads(response)
            
            # Look for JSON in markdown code blocks
            import re
            
            # Pattern 1: ```json ... ```
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            matches = re.findall(json_pattern, response, re.DOTALL)
            if matches:
                for match in matches:
                    try:
                        return json.loads(match.strip())
                    except json.JSONDecodeError:
                        continue
            
            # Pattern 2: ``` ... ``` (any code block)
            code_pattern = r'```\s*(\{.*?\})\s*```'
            matches = re.findall(code_pattern, response, re.DOTALL)
            if matches:
                for match in matches:
                    try:
                        return json.loads(match.strip())
                    except json.JSONDecodeError:
                        continue
            
            # Pattern 3: Look for JSON object anywhere in the response
            json_obj_pattern = r'\{[^{}]*"token_name"[^{}]*\}'
            matches = re.findall(json_obj_pattern, response, re.DOTALL)
            if matches:
                for match in matches:
                    try:
                        return json.loads(match.strip())
                    except json.JSONDecodeError:
                        continue
            
            # Pattern 4: Handle null responses
            if 'null' in response.lower() or 'no clear token' in response.lower():
                return None
            
            print(f"   ⚠️  Could not parse JSON from response")
            return None
            
        except Exception as e:
            print(f"   ❌ Parser error: {e}")
            return None
    
    async def _verify_token_with_dexscreener(self, token_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verify token using DexScreener API"""
        try:
            token_name = token_info.get('token_name', '').upper()
            network = self._detect_chain(token_info)
            
            if not token_name:
                self.logger.debug("No token name provided for verification")
                return None
            
            self.logger.info(f"🔍 Verifying token {token_name} on {network} via DexScreener...")
            
            # Search for token on DexScreener
            params = {"q": token_name}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.dexscreener_base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'pairs' in data and data['pairs']:
                            # Find best match for the token (highest volume)
                            best_match = self._find_best_dexscreener_match(data['pairs'], token_name, network)
                            
                            if best_match:
                                # Extract token details from DexScreener result
                                token_details = self._extract_dexscreener_token_details(best_match)
                                if token_details:
                                    # Early filter: only trade on allowed chains
                                    chain = token_details.get('chain', 'unknown').lower()
                                    vol24 = float(token_details.get('volume_24h', 0))
                                    liq = float(token_details.get('liquidity', 0))
                                    min_vol = self.min_volume_requirements.get(chain, None)
                                    min_liq = self.min_liquidity_requirements.get(chain, None)

                                    if chain not in self.allowed_chains:
                                        print(f"   ⚠️  Skipping unsupported chain from DexScreener: raw_chainId={best_match.get('chainId')} mapped={chain}")
                                        self.logger.info(f"Skipping token on unsupported chain: {chain}")
                                        return None

                                    if min_vol is not None and vol24 < min_vol:
                                        print(f"   ⚠️  Skipping low-volume token: ${vol24:,.0f} < ${min_vol:,.0f} required for {chain}")
                                        self.logger.info(f"Skipping low-volume token on {chain}: {vol24} < {min_vol}")
                                        return None

                                    if min_liq is not None and liq < min_liq:
                                        print(f"   ⚠️  Skipping low-liquidity token: ${liq:,.0f} < ${min_liq:,.0f} required for {chain}")
                                        self.logger.info(f"Skipping low-liquidity token on {chain}: {liq} < {min_liq}")
                                        return None

                                    self.logger.info(f"✅ Found verified token: {token_details['ticker']} on {token_details['chain']}")
                                    return token_details
                                else:
                                    self.logger.debug(f"Could not extract details for token: {token_name}")
                                    return None
                            else:
                                self.logger.debug(f"No matching token found for: {token_name}")
                                return None
                        else:
                            self.logger.debug(f"No pairs found for: {token_name}")
                            return None
                    else:
                        self.logger.warning(f"DexScreener API error: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Error verifying token with DexScreener: {e}")
            return None
    
    def _find_best_dexscreener_match(self, pairs: list, token_name: str, network: str) -> Optional[Dict[str, Any]]:
        """Select best DexScreener match with allowed-chain filtering and composite scoring."""
        try:
            if not pairs:
                return None

            # Group by base symbol
            def symbol_of(p):
                return (p.get('baseToken', {}) or {}).get('symbol', '').upper()

            # Partition by allowed chains first (unless network explicitly specified)
            allowed = set(self.allowed_chains)
            if network:
                allowed = {network.lower()}

            allowed_pairs = [p for p in pairs if (p.get('chainId', '') or '').lower() in allowed]
            other_pairs = [p for p in pairs if p not in allowed_pairs]

            # Build global context per symbol (max mc/vol across all chains)
            from collections import defaultdict
            global_stats = defaultdict(lambda: {'max_vol': 0.0, 'max_mc': 0.0})
            for p in pairs:
                sym = symbol_of(p)
                vol = float((p.get('volume', {}) or {}).get('h24', 0) or 0)
                mc = float(p.get('marketCap', 0) or 0)
                gs = global_stats[sym]
                if vol > gs['max_vol']:
                    gs['max_vol'] = vol
                if mc > gs['max_mc']:
                    gs['max_mc'] = mc

            # Threshold filter within allowed chains
            def passes_threshold(p):
                chain = (p.get('chainId', '') or '').lower()
                vol = float((p.get('volume', {}) or {}).get('h24', 0) or 0)
                min_vol = self.min_volume_requirements.get(chain, 0)
                return vol >= min_vol

            candidates = [p for p in allowed_pairs if passes_threshold(p)]
            if not candidates:
                self.logger.info(f"Dexscreener: no allowed-chain candidates above thresholds for {token_name}")
                return None

            # Composite scoring: volume, liquidity, verified
            def score(p):
                vol = float((p.get('volume', {}) or {}).get('h24', 0) or 0)
                liq = float((p.get('liquidity', {}) or {}).get('usd', 0) or 0)
                verified = 1.0 if p.get('verified', False) else 0.0
                import math
                return 0.5 * math.log10(max(vol, 1)) + 0.3 * math.log10(max(liq, 1)) + 0.2 * verified

            # Pick best by score, tie-break by liquidity then (if available) marketCap
            candidates.sort(key=lambda p: (score(p), float((p.get('liquidity', {}) or {}).get('usd', 0) or 0), float(p.get('marketCap', 0) or 0)), reverse=True)
            best = candidates[0]

            # Caution log if chosen mc << global mc for the symbol
            sym = symbol_of(best)
            chosen_mc = float(best.get('marketCap', 0) or 0)
            gl_mc = global_stats[sym]['max_mc']
            if gl_mc > 0 and chosen_mc < 0.3 * gl_mc:
                self.logger.info(f"Dexscreener: caution selected {sym} on {best.get('chainId')} mc ${chosen_mc:,.0f} vs global ${gl_mc:,.0f}")

            return best

        except Exception as e:
            self.logger.error(f"Error finding DexScreener match: {e}")
            return None
    
    def _extract_dexscreener_token_details(self, pair_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract token details from DexScreener pair data"""
        try:
            base_token = pair_data.get('baseToken', {})
            quote_token = pair_data.get('quoteToken', {})
            raw_chain_id = pair_data.get('chainId', '')
            mapped_chain = self._map_dexscreener_chain(raw_chain_id)
            
            # Extract token details
            return {
                'ticker': base_token.get('symbol', ''),
                'name': base_token.get('name', ''),
                'contract': base_token.get('address', ''),
                'chain': mapped_chain,
                'price': float(pair_data.get('priceUsd', 0)),
                'volume_24h': float(pair_data.get('volume', {}).get('h24', 0)),
                'market_cap': float(pair_data.get('marketCap', 0)),
                'liquidity': float(pair_data.get('liquidity', {}).get('usd', 0)),
                'dex': pair_data.get('dexId', 'Unknown'),
                'verified': True,
                'dexscreener_pair_id': pair_data.get('pairAddress', ''),
                'quote_token': quote_token.get('symbol', ''),
                'quote_contract': quote_token.get('address', ''),
                'raw_chain_id': raw_chain_id
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting DexScreener token details: {e}")
            return None
    
    def _map_dexscreener_chain(self, chain_id: str) -> str:
        """Map DexScreener chain IDs to our chain names (no default to Solana)"""
        chain_mapping = {
            'solana': 'solana',
            'ethereum': 'ethereum',
            'base': 'base',
            'polygon': 'polygon',
            'arbitrum': 'arbitrum',
            'bsc': 'bsc',
            'bnb': 'bsc',
            'avalanche': 'avalanche',
            'pulsechain': 'pulsechain',
            'osmosis': 'osmosis',
            'tron': 'tron',
            'ton': 'ton'
        }
        cid = (chain_id or '').lower()
        return chain_mapping.get(cid, cid or 'unknown')
    
    def _detect_chain(self, token_info: Dict[str, Any]) -> str:
        """Detect blockchain network from token info and context"""
        try:
            # Check if network was explicitly mentioned
            network = token_info.get('network', '').lower()
            if network in ['solana', 'ethereum', 'base', 'polygon', 'arbitrum', 'bsc', 'bnb', 'tron']:
                return network
            
            # Check for chain-specific keywords in additional info
            additional_info = token_info.get('additional_info', '').lower()
            if any(keyword in additional_info for keyword in ['sol', 'solana', 'raydium', 'jupiter']):
                return 'solana'
            elif any(keyword in additional_info for keyword in ['eth', 'ethereum', 'uniswap', '1inch']):
                return 'ethereum'
            elif any(keyword in additional_info for keyword in ['base', 'baseswap']):
                return 'base'
            elif any(keyword in additional_info for keyword in ['polygon', 'matic']):
                return 'polygon'
            elif any(keyword in additional_info for keyword in ['bsc', 'bnb', 'pancakeswap']):
                return 'bsc'
            elif any(keyword in additional_info for keyword in ['trx', 'tron', 'sunswap', 'wtrx']):
                return 'tron'
            
            # Unknown when not sure (avoid defaulting to Solana)
            return ''
            
        except Exception as e:
            self.logger.error(f"Error detecting chain: {e}")
            return ''
    
    def _select_venue(self, chain: str) -> str:
        """Select best venue for the given chain"""
        try:
            venue_mapping = {
                'solana': 'Jupiter',
                'ethereum': '1inch',
                'base': '1inch',
                'polygon': '1inch',
                'arbitrum': '1inch'
            }
            return venue_mapping.get(chain, 'Jupiter')
        except Exception as e:
            self.logger.error(f"Error selecting venue: {e}")
            return 'Jupiter'
    
    async def _scan_handle_for_token(self, handle: str) -> Optional[Dict[str, Any]]:
        """Scan a Twitter handle's profile for token information"""
        try:
            # This would use Playwright to scan the handle's profile
            # For now, return mock data for handles we know have tokens
            known_tokens = {
                '@Codecopenflow': {
                    'token_name': 'CODECOPENFLOW',
                    'network': 'solana',
                    'contract_address': 'So1aNaCodecopenflow1234567890abcdef',
                    'sentiment': 'positive',
                    'confidence': 0.8,
                    'trading_intention': 'buy',
                    'has_chart': False,
                    'chart_type': None,
                    'chart_analysis': None,
                    'additional_info': 'Found token info from handle profile scan'
                },
                '@example_token': {
                    'token_name': 'EXAMPLE',
                    'network': 'ethereum',
                    'contract_address': '0x1234567890abcdef',
                    'sentiment': 'positive',
                    'confidence': 0.7,
                    'trading_intention': 'buy',
                    'has_chart': False,
                    'chart_type': None,
                    'chart_analysis': None,
                    'additional_info': 'Found token info from handle profile scan'
                }
            }
            
            if handle in known_tokens:
                self.logger.info(f"Found known token for handle: {handle}")
                return known_tokens[handle]
            else:
                self.logger.debug(f"No known token for handle: {handle}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error scanning handle {handle}: {e}")
            return None
    
    async def _create_social_strand(self, curator: Dict[str, Any], message_data: Dict[str, Any], token: Dict[str, Any], extraction_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create social_lowcap strand for DML"""
        try:
            # Verbose details moved to DEBUG level to keep INFO concise
            self.logger.debug(f"Creating strand with token: {token.get('ticker', 'unknown')}")
            self.logger.debug(f"Curator: {curator.get('id', 'unknown')}")
            self.logger.debug(f"Token data: {token}")
            # Extract platform info
            platform = curator.get('platform', 'unknown')
            platform_data = curator.get('platform_data', {})
            handle = platform_data.get('handle', curator.get('name', 'unknown'))
            weight = platform_data.get('weight', 0.5)
            
            # Generate unique ID for the strand
            import uuid
            strand_id = str(uuid.uuid4())
            
            # Extract confidence and trading signals from LLM response
            token_confidence = 0.7  # Default confidence
            trading_action = "buy"  # Default action
            trading_timing = None
            trading_confidence = 0.7
            
            if extraction_result and extraction_result.get('tokens'):
                for token_info in extraction_result['tokens']:
                    if token_info.get('token_name', '').upper() == token['ticker'].upper():
                        token_confidence = token_info.get('confidence', 0.7)
                        trading_signals = token_info.get('trading_signals', {})
                        trading_action = trading_signals.get('action', 'buy')
                        trading_timing = trading_signals.get('timing')
                        trading_confidence = trading_signals.get('confidence', token_confidence)
                        break
            
            strand = {
                "id": strand_id,
                "module": "social_ingest",
                "kind": "social_lowcap",
                "symbol": token['ticker'],  # Use proper symbol column
                "timeframe": None,  # Not applicable for social signals
                "session_bucket": f"social_{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}",  # Hourly session
                "regime": None,  # Market regime - not applicable for social signals
                "tags": ["curated", "social_signal", "dm_candidate", "verified"],
                "target_agent": "decision_maker_lowcap",  # Target the decision maker
                "sig_sigma": None,  # Signal strength - not applicable for social signals
                "sig_confidence": trading_confidence,  # Signal confidence from trading signals
                "confidence": token_confidence,  # Generic confidence from LLM
                "sig_direction": trading_action,  # Trading action from LLM (buy/sell)
                "trading_plan": None,  # Will be filled by decision maker
                "signal_pack": {
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
                    "curator": {
                        "id": curator['id'],
                        "name": curator.get('name', 'Unknown'),
                        "platform": platform,
                        "handle": handle,
                        "weight": weight,
                        "priority": platform_data.get('priority', 'medium'),
                        "tags": curator.get('tags', [])
                    },
                    "trading_signals": {
                        "action": trading_action,
                        "timing": trading_timing,
                        "confidence": trading_confidence
                    }
                },
                "module_intelligence": {
                    "social_signal": {
                        "message": {
                            "text": message_data.get('text', ''),
                            "timestamp": message_data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                            "url": message_data.get('url', ''),
                            "has_image": bool(message_data.get('image_data')),
                            "has_chart": token.get('has_chart', False),
                            "chart_type": token.get('chart_type', None)
                        },
                        "context_slices": {
                            "liquidity_bucket": self._get_liquidity_bucket(token.get('liquidity', 0)),
                            "volume_bucket": self._get_volume_bucket(token.get('volume_24h', 0)),
                            "time_bucket_utc": self._get_time_bucket(),
                            "sentiment": "positive"  # Would be extracted from LLM
                        }
                    }
                },
                "content": {
                    "summary": f"Social signal for {token['ticker']} from {curator.get('name', 'Unknown')}",
                    "curator_id": curator['id'],
                    "platform": platform,
                    "token_ticker": token['ticker'],
                    "confidence": token_confidence
                },
                "status": "active"
            }
            
            # Create strand in database
            self.logger.debug(f"Creating strand in database...")
            created_strand = await self.supabase_manager.create_strand(strand)
            self.logger.debug(f"Database response: {created_strand}")
            
            # Show what we found
            token_info = strand['signal_pack']['token']
            curator_id = strand['signal_pack']['curator']['id']
            vol = token_info.get('volume_24h', 0)
            liq = token_info.get('liquidity', 0)
            strand_id_short = created_strand.get('id', '')[:8] + '…'
            # Concise, stage-tagged lines
            print(f"social | NEW SIGNAL {curator_id} → {token_info['ticker']} ({token_info['chain']}) vol ${vol:,.0f} liq ${liq:,.0f}")
            print(f"social | Strand created: {strand_id_short}  → target: decision_maker_lowcap")
            
            # Trigger learning system to process the strand
            if hasattr(self, 'learning_system') and self.learning_system:
                print(f"   🔄 Processing with Decision Maker...")
                try:
                    # Use asyncio.create_task to handle the async call
                    asyncio.create_task(self.learning_system.process_strand_event(created_strand))
                    print(f"   ✅ Learning system task created")
                except Exception as e:
                    print(f"   ❌ Error creating learning system task: {e}")
            else:
                print(f"   ⚠️  Learning system not available - skipping Decision Maker trigger")
            
            return created_strand
            
        except Exception as e:
            print(f"   ❌ Error creating social strand: {e}")
            import traceback
            traceback.print_exc()
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
    
    def _populate_curators_table_sync(self):
        """Populate curators table from YAML config on startup (synchronous)"""
        try:
            print("🔄 Populating curators table from YAML config...")
            
            for curator in self.curators_config['curators']:
                if not curator.get('enabled', True):
                    continue
                    
                curator_id = curator['id']
                
                # Check if curator already exists using Supabase client directly
                existing_curator = self._get_curator_by_id_sync(curator_id)
                
                if existing_curator:
                    print(f"   ✅ Curator {curator_id} already exists in database")
                    continue
                
                # Extract platform handles
                twitter_handle = None
                telegram_handle = None
                
                for platform, platform_data in curator.get('platforms', {}).items():
                    if platform == 'twitter' and platform_data.get('active', True):
                        twitter_handle = platform_data.get('handle')
                    elif platform == 'telegram' and platform_data.get('active', True):
                        telegram_handle = platform_data.get('handle')
                
                # Create curator record matching actual schema
                curator_data = {
                    'curator_id': curator_id,
                    'name': curator.get('name', curator_id),
                    'description': curator.get('notes', ''),
                    'twitter_handle': twitter_handle,
                    'telegram_handle': telegram_handle,
                    'total_signals': 0,
                    'successful_signals': 0,
                    'failed_signals': 0,
                    'win_rate': 0.0,
                    'total_pnl_pct': 0.0,
                    'base_weight': 0.6,  # Start all curators at 0.6
                    'performance_weight': 0.6,
                    'final_weight': 0.6,
                    'status': 'active',
                    'tags': curator.get('tags', []),
                    'notes': curator.get('notes', '')
                }
                
                # Insert curator into database
                self._insert_curator_sync(curator_data)
                print(f"   ✅ Added curator {curator_id} to database")
            
            print("✅ Curators table population completed")
            
        except Exception as e:
            self.logger.error(f"Failed to populate curators table: {e}")
            print(f"❌ Failed to populate curators table: {e}")
    
    def _get_curator_by_id_sync(self, curator_id: str) -> Dict[str, Any]:
        """Get curator by ID from database (synchronous)"""
        try:
            result = self.supabase_manager.client.table('curators').select('*').eq('curator_id', curator_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(f"Failed to get curator {curator_id}: {e}")
            return None
    
    def _insert_curator_sync(self, curator_data: Dict[str, Any]):
        """Insert curator into database (synchronous)"""
        try:
            result = self.supabase_manager.client.table('curators').insert(curator_data).execute()
            if not result.data:
                raise Exception(f"Failed to insert curator {curator_data['curator_id']}: No data returned")
        except Exception as e:
            self.logger.error(f"Failed to insert curator {curator_data['curator_id']}: {e}")
            raise
