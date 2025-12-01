"""
Social Ingest Module - Basic Version

Real-time social media scraping and token extraction for social lowcap intelligence.
Uses LLM for information extraction and mock API for token verification.
"""

import logging
import asyncio
import json
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import yaml
import os
import re
from src.intelligence.lowcap_portfolio_manager.regime.bucket_context import fetch_bucket_phase_snapshot

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
        
        # Token ignore list - load from learning_configs, fallback to hardcoded
        self.ignored_tokens = self._load_ignored_tokens()
        # Allowed chains and minimum volume thresholds (USD) for early filtering
        self.allowed_chains = ['solana', 'ethereum', 'base', 'bsc']
        self.min_volume_requirements = {
            'solana': 100000,   # $100k on Solana
            'ethereum': 25000,  # $25k on Ethereum
            'base': 25000,      # $25k on Base
            'bsc': 100000        # $100k on BSC
        }
        # Minimum liquidity requirements (USD) for early filtering
        self.min_liquidity_requirements = {
            'solana': 20000,    # $20k on Solana
            'ethereum': 20000,  # $20k on Ethereum
            'base': 20000,      # $20k on Base
            'bsc': 20000        # $20k on BSC
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
            self.logger.debug(f"LLM Response: {extraction_result}")
            
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
                token_name = token_info.get('token_name', 'unknown')
                identifier_used = "contract" if token_info.get('contract_address') else "ticker"
                self.logger.debug(f"Processing token: {token_name} (using {identifier_used})")
                
                # Check if token is in ignore list (contract addresses bypass ignore list)
                if token_name.upper() in self.ignored_tokens and not token_info.get('contract_address'):
                    self.logger.info(f"Skipping ignored token: {token_name}")
                    continue
                
                # Verify token with DexScreener API
                verified_token = await self._verify_token_with_dexscreener(token_info, curator_id)
                if not verified_token:
                    self.logger.debug(f"Token verification failed for {token_info.get('token_name', 'unknown')}")
                    continue
                else:
                    self.logger.debug(f"Token verified: {verified_token.get('ticker', 'unknown')}")
                
                # Stage 2: Analyze curator intent for this token
                self.logger.debug(f"Analyzing intent for {verified_token.get('ticker', 'unknown')}")
                intent_analysis = await self._analyze_curator_intent(
                    message_data.get('text', ''),
                    token_info,
                    curator_id
                )
                
                if not intent_analysis:
                    self.logger.warning(f"Intent analysis failed for {verified_token.get('ticker', 'unknown')}")
                    continue
                
                # Check if this should be a buy signal based on intent type
                intent_data = intent_analysis.get('intent_analysis', {})
                intent_type = intent_data.get('intent_type', 'unknown')
                
                # Define buy signal intent types
                buy_intent_types = {
                    'adding_to_position',
                    'research_positive', 
                    'new_discovery',
                    'comparison_highlighted',
                    'other_positive'
                }
                
                if intent_type not in buy_intent_types:
                    self.logger.info(f"Skipping {verified_token.get('ticker', 'unknown')} - intent: {intent_type}")
                    continue
                
                self.logger.debug(f"Intent analysis passed: {intent_analysis.get('intent_analysis', {}).get('intent_type', 'unknown')}")
                
                # Create social_lowcap strand for this token with intent data
                self.logger.debug(f"Creating strand for {verified_token.get('ticker', 'unknown')}")
                strand = await self._create_social_strand(curator, message_data, verified_token, extraction_result, intent_analysis, identifier_used)
                if strand:
                    created_strands.append(strand)
                    self.logger.info(f"Created social_lowcap strand for {curator_id} -> {verified_token.get('ticker', 'unknown')}")
                else:
                    self.logger.warning(f"Strand creation failed for {verified_token.get('ticker', 'unknown')}")
            
            # Update curator last_seen_at
            # TODO: Implement curator last_seen update
            # self._update_curator_last_seen(curator_id)
            
            self.logger.info(f"Final result: {len(created_strands)} strands created")
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
            self.logger.debug(f"Calling LLM with text: {message_text[:100]}...")
            
            # Use prompt manager to get token extraction template
            prompt = self.prompt_manager.format_prompt(
                'token_extraction', 
                {'message_text': message_text}
            )
            system_message = self.prompt_manager.get_system_message('token_extraction')
            
            self.logger.debug(f"Using prompt manager: True")
            self.logger.debug(f"System message: {system_message[:50] if system_message else 'None'}...")
            
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
            
            self.logger.debug(f"Raw LLM response: {response}")
            
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
            self.logger.error(f"LLM error: {e}", exc_info=True)
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
            
            self.logger.warning("Could not parse JSON from response")
            return None
            
        except Exception as e:
            self.logger.error(f"Parser error: {e}", exc_info=True)
            return None
    
    async def _verify_token_with_dexscreener(self, token_info: Dict[str, Any], curator_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Verify token using DexScreener API"""
        try:
            token_name = token_info.get('token_name', '').upper()
            # Get curator for chain detection (if available)
            curator_obj = None
            if curator_id:
                try:
                    curator_result = self.supabase_manager.client.table('curators').select('*').eq('curator_id', curator_id).limit(1).execute()
                    if curator_result.data:
                        curator_obj = curator_result.data[0]
                except Exception as e:
                    self.logger.debug(f"Could not fetch curator for chain detection: {e}")
            
            network, mapping_reason = self._detect_chain(token_info, curator_obj)
            
            if not token_name:
                self.logger.debug("No token name provided for verification")
                return None
            
            self.logger.info(f"🔍 Verifying token {token_name} on {network} via DexScreener...")
            
            # Search for token on DexScreener
                if token_info.get('contract_address'):
                    params = {"q": token_info.get('contract_address')}
                    self.logger.debug(f"Searching by contract address: {token_info.get('contract_address')}")
                else:
                    params = {"q": token_name}
                    self.logger.debug(f"Searching by ticker: {token_name}")
            
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
                                    # Calculate identification source (how token was identified)
                                    identification_source = self._calculate_token_identification_source(token_info, token_details)
                                    self.logger.debug(f"Token identification source: {identification_source}")
                                    
                                    # Map identification source to confidence level for threshold relaxation
                                    # (keeping the relaxation logic but using source-based mapping)
                                    confidence_map = {
                                        "contract_address": "highest",
                                        "ticker_exact": "high",
                                        "ticker_approximate": "medium",
                                        "ticker_bare": "low"
                                    }
                                    confidence = confidence_map.get(identification_source, "low")
                                    
                                    # Early filter: only trade on allowed chains (still blocks)
                                    chain = token_details.get('chain', 'unknown').lower()
                                    vol24 = float(token_details.get('volume_24h', 0))
                                    liq = float(token_details.get('liquidity', 0))
                                    min_vol = self.min_volume_requirements.get(chain, None)
                                    min_liq = self.min_liquidity_requirements.get(chain, None)
                                    
                                    # Apply confidence-based filter relaxation (using mapped confidence)
                                    relaxed_min_vol = self._get_relaxed_volume_threshold(min_vol, confidence) if min_vol else None
                                    relaxed_min_liq = self._get_relaxed_liquidity_threshold(min_liq, confidence) if min_liq else None

                                    if chain not in self.allowed_chains:
                                        self.logger.info(f"Skipping token on unsupported chain: {chain} (raw_chainId={best_match.get('chainId')})")
                                        return None

                                    # Calculate health metrics (NOTE, don't BLOCK)
                                    volume_health = {
                                        "vol24h": vol24,
                                        "min_required": relaxed_min_vol if relaxed_min_vol else min_vol,
                                        "meets_threshold": relaxed_min_vol is None or vol24 >= relaxed_min_vol
                                    }
                                    
                                    liquidity_health = {
                                        "liquidity": liq,
                                        "min_required": relaxed_min_liq if relaxed_min_liq else min_liq,
                                        "meets_threshold": relaxed_min_liq is None or liq >= relaxed_min_liq
                                    }
                                    
                                    # Store health metrics in token_details (DM can evaluate)
                                    token_details['volume_health'] = volume_health
                                    token_details['liquidity_health'] = liquidity_health
                                    
                                    # Log health status (but don't block)
                                    if relaxed_min_vol is not None and vol24 < relaxed_min_vol:
                                        self.logger.info(f"Low volume token on {chain}: ${vol24:,.0f} < ${relaxed_min_vol:,.0f} required (confidence: {confidence}) - NOTE only")
                                    else:
                                        self.logger.debug(f"Volume: ${vol24:,.0f} (required: ${relaxed_min_vol:,.0f} for {chain})")
                                    
                                    if relaxed_min_liq is not None and liq < relaxed_min_liq:
                                        self.logger.info(f"Low liquidity token on {chain}: ${liq:,.0f} < ${relaxed_min_liq:,.0f} required (confidence: {confidence}) - NOTE only")
                                    else:
                                        self.logger.debug(f"Liquidity: ${liq:,.0f} (required: ${relaxed_min_liq:,.0f} for {chain})")

                                    # Liquidity-to-market cap ratio (NOTE, don't BLOCK)
                                    market_cap = float(token_details.get('market_cap', 0))
                                    if market_cap > 0:
                                        liq_mcap_ratio = (liq / market_cap) * 100  # Convert to percentage
                                        required_ratio = self._get_required_liq_mcap_ratio(market_cap)
                                        relaxed_required_ratio = self._get_relaxed_liq_mcap_ratio(required_ratio, confidence)
                                        
                                        # Store ratio in token_details
                                        token_details['liq_mcap_ratio'] = liq_mcap_ratio
                                        
                                        # Log ratio status (but don't block)
                                        if liq_mcap_ratio < relaxed_required_ratio:
                                            self.logger.info(f"Low liq/mcap ratio on {chain}: {liq_mcap_ratio:.2f}% < {relaxed_required_ratio:.1f}% required (mcap: ${market_cap:,.0f}, liq: ${liq:,.0f}, confidence: {confidence}) - NOTE only")
                                        else:
                                            self.logger.debug(f"Liquidity/market cap ratio: {liq_mcap_ratio:.2f}% (required: {relaxed_required_ratio:.1f}%)")
                                        
                                        # Add liquidity health bonus to token details for scoring
                                        ratio_excess = liq_mcap_ratio - required_ratio
                                        liquidity_bonus = min(0.1, max(0, (ratio_excess / required_ratio) * 0.1))  # Max 10% bonus
                                        token_details['liquidity_health_bonus'] = liquidity_bonus
                                    else:
                                        self.logger.info(f"Zero market cap on {chain} - NOTE only")
                                        token_details['liq_mcap_ratio'] = 0.0

                                    # Store mapping_reason in token_details for strand creation
                                    token_details['mapping_reason'] = mapping_reason if mapping_reason else 'ticker_only'
                                    # Store identification source for signal_pack
                                    token_details['identification_source'] = identification_source
                                    # Determine mapping_status
                                    if not network:
                                        token_details['mapping_status'] = 'chain_unresolved'
                                    elif token_info.get('contract_address'):
                                        token_details['mapping_status'] = 'resolved'
                                    else:
                                        token_details['mapping_status'] = 'resolved'  # Default to resolved if we got this far
                                    
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
        """Select best DexScreener match using exact symbol matching and smart scoring."""
        try:
            if not pairs:
                return None

            def symbol_of(p):
                return (p.get('baseToken', {}) or {}).get('symbol', '').upper()

            def contract_of(p):
                return (p.get('baseToken', {}) or {}).get('address', '')

            # Step 1: Filter to exact symbol matches only
            exact_matches = [p for p in pairs if symbol_of(p) == token_name.upper()]
            if not exact_matches:
                self.logger.info(f"No exact symbol matches found for {token_name}")
                return None

            # Step 2: Filter by allowed chains
            allowed = set(self.allowed_chains)
            if network:
                allowed = {network.lower()}

            allowed_matches = [p for p in exact_matches if (p.get('chainId', '') or '').lower() in allowed]
            if not allowed_matches:
                self.logger.info(f"No exact matches on allowed chains for {token_name}")
                return None

            # Step 3: Group by contract address and aggregate pairs
            from collections import defaultdict
            token_groups = defaultdict(list)
            
            for pair in allowed_matches:
                contract = contract_of(pair)
                if contract:
                    token_groups[contract].append(pair)

            if not token_groups:
                self.logger.info(f"No valid contract addresses found for {token_name}")
                return None

            # Step 4: Score each unique token (contract address)
            best_token = None
            best_score = -1
            best_aggregated_volume = 0
            best_aggregated_liquidity = 0

            for contract, pairs_for_token in token_groups.items():
                # Aggregate all pairs for this token
                total_volume = sum(float((p.get('volume', {}) or {}).get('h24', 0) or 0) for p in pairs_for_token)
                total_liquidity = sum(float((p.get('liquidity', {}) or {}).get('usd', 0) or 0) for p in pairs_for_token)
                
                # Use the first pair for other metrics (they should be the same for same contract)
                first_pair = pairs_for_token[0]
                market_cap = float(first_pair.get('marketCap', 0) or 0)
                chain = (first_pair.get('chainId', '') or '').lower()
                age_str = first_pair.get('pairCreatedAt', '')
                
                # Calculate liquidity health bonus for scoring
                liquidity_bonus = 0.0
                if market_cap > 0:
                    liq_mcap_ratio = (total_liquidity / market_cap) * 100
                    required_ratio = self._get_required_liq_mcap_ratio(market_cap)
                    if liq_mcap_ratio >= required_ratio:
                        ratio_excess = liq_mcap_ratio - required_ratio
                        liquidity_bonus = min(0.1, max(0, (ratio_excess / required_ratio) * 0.1))
                
                # Calculate scores
                score = self._calculate_token_score(
                    pairs_for_token, total_volume, total_liquidity, 
                    market_cap, chain, age_str, token_name, liquidity_bonus
                )
                
                if score > best_score:
                    best_score = score
                    best_token = first_pair  # Return the first pair as representative
                    best_aggregated_volume = total_volume
                    best_aggregated_liquidity = total_liquidity

            if best_token:
                self.logger.info(f"Selected {symbol_of(best_token)} with score {best_score:.3f}, aggregated volume ${best_aggregated_volume:,.0f}")
                # Add aggregated volume and liquidity to the returned pair for use in verification
                best_token['_aggregated_volume'] = best_aggregated_volume
                best_token['_aggregated_liquidity'] = best_aggregated_liquidity
            
            return best_token

        except Exception as e:
            self.logger.error(f"Error finding DexScreener match: {e}")
            return None

    def _calculate_token_score(self, pairs: list, total_volume: float, total_liquidity: float, 
                             market_cap: float, chain: str, age_str: str, token_name: str, liquidity_bonus: float = 0.0) -> float:
        """Calculate weighted score for a token based on multiple factors."""
        try:
            import math
            from datetime import datetime, timezone
            
            # A. DexScreener Position Score (0-1)
            # Use the position of the first pair in original results
            position_score = 1.0  # We'll improve this if we track original positions
            
            # B. Volume Score (0-1) with 3x multiplier for Base/Ethereum - NO CAP for legitimacy
            volume_multiplier = 3.0 if chain in ['base', 'ethereum'] else 1.0
            adjusted_volume = total_volume * volume_multiplier
            # Remove cap to properly differentiate high volume tokens
            volume_score = min(2.0, math.log10(max(adjusted_volume, 1)) / 5)  # Scale to 2.0 max, /5 instead of /6
            
            # C. Liquidity Score (0-1) - NO CAP for legitimacy
            # Remove cap to properly differentiate high liquidity tokens
            liquidity_score = min(2.0, math.log10(max(total_liquidity, 1)) / 5)  # Scale to 2.0 max, /5 instead of /6
            
            # D. Market Cap Score (0-1) - PREFERENCE ONLY, not filtering
            # Higher market cap is generally better for legitimacy, sweet spot is just preference
            if market_cap >= 1_000_000_000:  # $1B+ is excellent
                market_cap_score = 1.0
            elif market_cap >= 100_000_000:  # $100M+ is very good
                market_cap_score = 0.9
            elif market_cap >= 10_000_000:   # $10M+ is good
                market_cap_score = 0.8
            elif market_cap >= 1_000_000:    # $1M+ is acceptable
                market_cap_score = 0.7
            else:  # < $1M is low but not disqualifying
                market_cap_score = 0.5
            
            # E. Age Score (0-1) - PREFERENCE ONLY, not filtering
            age_score = self._calculate_age_score(age_str)
            
            # Weighted final score - PRIORITIZE VOLUME AND LIQUIDITY
            total_score = (
                0.1 * position_score +      # Reduced from 0.3
                0.5 * volume_score +        # Increased from 0.3 - PRIMARY factor
                0.3 * liquidity_score +     # Increased from 0.2 - SECONDARY factor
                0.05 * market_cap_score +   # Reduced from 0.15 - PREFERENCE only
                0.05 * age_score            # Reduced from 0.05 - PREFERENCE only
            )
            
            # Add liquidity health bonus (0-10% bonus for exceeding ratio thresholds)
            total_score += liquidity_bonus
            
            return total_score
            
        except Exception as e:
            self.logger.error(f"Error calculating token score: {e}")
            return 0.0

    def _get_required_liq_mcap_ratio(self, market_cap: float) -> float:
        """Get required liquidity-to-market cap ratio based on market cap tiers"""
        if market_cap < 500_000:
            return 10.0  # 10%
        elif market_cap < 1_000_000:
            return 6.0   # 6%
        elif market_cap < 5_000_000:
            return 4.0   # 4%
        elif market_cap < 50_000_000:
            return 3.0   # 3%
        elif market_cap < 200_000_000:
            return 2.0   # 2%
        else:
            return 1.0   # 1%

    def _calculate_age_score(self, age_str: str) -> float:
        """Calculate age score based on token age. Sweet spot: 30-180 days."""
        try:
            if not age_str:
                return 0.5  # Default if no age info
            
            # Parse age string (e.g., "2mo 6d", "1y 1m 6d")
            from datetime import datetime, timezone, timedelta
            
            # Convert to datetime
            try:
                created_at = datetime.fromisoformat(age_str.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created_at).days
            except:
                return 0.5  # Default if parsing fails
            
            # Age scoring logic
            if 30 <= age_days <= 180:
                return 1.0  # Sweet spot
            elif age_days < 30:
                return age_days / 30  # Linear scale up
            elif age_days <= 365:
                return 1.0 - (age_days - 180) / 185  # Linear decay
            else:
                return max(0, 0.5 - (age_days - 365) / 730)  # Further decay
                
        except Exception as e:
            self.logger.error(f"Error calculating age score: {e}")
            return 0.5
    
    def _calculate_age_days(self, pair_created_at: str) -> int:
        """Calculate age in days from pairCreatedAt timestamp"""
        try:
            if not pair_created_at:
                return 999  # Default to "old" if no data
            
            from datetime import datetime, timezone
            # Parse DexScreener timestamp (ISO format with Z suffix)
            created_at = datetime.fromisoformat(pair_created_at.replace('Z', '+00:00'))
            # Calculate days since creation
            age_days = (datetime.now(timezone.utc) - created_at).days
            return max(0, age_days)  # Ensure non-negative
        except:
            return 999  # Default to "old" if parsing fails
    
    def _extract_dexscreener_token_details(self, pair_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract token details from DexScreener pair data"""
        try:
            base_token = pair_data.get('baseToken', {})
            quote_token = pair_data.get('quoteToken', {})
            raw_chain_id = pair_data.get('chainId', '')
            mapped_chain = self._map_dexscreener_chain(raw_chain_id)
            
            # Use aggregated volume if available (from scoring process), otherwise use single pair volume
            volume_24h = pair_data.get('_aggregated_volume')
            if volume_24h is None:
                volume_24h = float(pair_data.get('volume', {}).get('h24', 0))
            else:
                volume_24h = float(volume_24h)
            
            # Use aggregated liquidity if available, otherwise use single pair liquidity
            liquidity = pair_data.get('_aggregated_liquidity')
            if liquidity is None:
                liquidity = float(pair_data.get('liquidity', {}).get('usd', 0))
            else:
                liquidity = float(liquidity)
            
            # Calculate age in days from pairCreatedAt timestamp
            age_days = self._calculate_age_days(pair_data.get('pairCreatedAt', ''))
            
            # Extract pair creation date from pairCreatedAt (ISO8601 format)
            pair_created_at = pair_data.get('pairCreatedAt', '')
            if pair_created_at:
                try:
                    # Ensure it's in ISO8601 format
                    from datetime import datetime
                    dt = datetime.fromisoformat(pair_created_at.replace('Z', '+00:00'))
                    pair_created_at = dt.isoformat()
                except:
                    pair_created_at = ''  # Fallback to empty if parsing fails
            
            # Extract social links from info section
            social_links = {}
            info_section = pair_data.get('info', {})
            if info_section and 'socials' in info_section:
                for social in info_section['socials']:
                    social_type = social.get('type', '').lower()
                    social_url = social.get('url', '')
                    if social_type and social_url:
                        social_links[social_type] = social_url
            
            # Extract token details
            return {
                'ticker': base_token.get('symbol', ''),
                'name': base_token.get('name', ''),
                'contract': base_token.get('address', ''),
                'chain': mapped_chain,
                'price': float(pair_data.get('priceUsd', 0)),
                'volume_24h': volume_24h,
                'market_cap': float(pair_data.get('marketCap', 0)),
                'liquidity': liquidity,
                'dex': pair_data.get('dexId', 'Unknown'),
                'verified': True,
                'dexscreener_pair_id': pair_data.get('pairAddress', ''),
                'quote_token': quote_token.get('symbol', ''),
                'quote_contract': quote_token.get('address', ''),
                'raw_chain_id': raw_chain_id,
                'age_days': age_days,
                'pair_created_at': pair_created_at,  # Added for A/E age component
                'social_links': social_links
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
    
    def _detect_chain(self, token_info: Dict[str, Any], curator: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        """
        Detect blockchain network from token info and context.
        
        Args:
            token_info: Token information from LLM extraction
            curator: Optional curator dict with chain_counts for prior weighting
            
        Returns:
            Tuple of (detected_chain, mapping_reason)
            - detected_chain: Chain name or empty string if unresolved
            - mapping_reason: How chain was resolved ("contract_link", "ticker+chain_phrase", "curator_chain_prior", "ticker_only", "")
        """
        try:
            mapping_reason = ""
            chain_score = {}
            
            # Check if network was explicitly mentioned (highest priority)
            network = token_info.get('network', '').lower()
            if network in ['solana', 'ethereum', 'base', 'polygon', 'arbitrum', 'bsc', 'bnb', 'tron']:
                return network, "ticker+chain_phrase"
            
            # Check for chain-specific keywords in additional info
            additional_info = token_info.get('additional_info', '').lower()
            if any(keyword in additional_info for keyword in ['sol', 'solana', 'raydium', 'jupiter']):
                chain_score['solana'] = 1.0
                mapping_reason = "ticker+chain_phrase"
            elif any(keyword in additional_info for keyword in ['eth', 'ethereum', 'uniswap', '1inch']):
                chain_score['ethereum'] = 1.0
                mapping_reason = "ticker+chain_phrase"
            elif any(keyword in additional_info for keyword in ['base', 'baseswap']):
                chain_score['base'] = 1.0
                mapping_reason = "ticker+chain_phrase"
            elif any(keyword in additional_info for keyword in ['polygon', 'matic']):
                chain_score['polygon'] = 1.0
                mapping_reason = "ticker+chain_phrase"
            elif any(keyword in additional_info for keyword in ['bsc', 'bnb', 'pancakeswap']):
                chain_score['bsc'] = 1.0
                mapping_reason = "ticker+chain_phrase"
            elif any(keyword in additional_info for keyword in ['trx', 'tron', 'sunswap', 'wtrx']):
                chain_score['tron'] = 1.0
                mapping_reason = "ticker+chain_phrase"
            
            # Add curator chain prior as small weight (if available and no explicit chain found)
            if curator and not chain_score:
                chain_counts = curator.get('chain_counts', {})
                if chain_counts and isinstance(chain_counts, dict):
                    total_count = sum(chain_counts.values())
                    if total_count > 0:
                        for chain, count in chain_counts.items():
                            chain_score[chain] = 0.1 * (count / total_count)  # Small weight (0.1x normalized)
                        mapping_reason = "curator_chain_prior"
            
            # Return best chain if we have scores
            if chain_score:
                best_chain = max(chain_score.items(), key=lambda x: x[1])[0]
                return best_chain, mapping_reason
            
            # Unknown when not sure (avoid defaulting to Solana)
            return '', ""
            
        except Exception as e:
            self.logger.error(f"Error detecting chain: {e}")
            return '', ""
    
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
    
    def _calculate_confidence_grade(self, token: Dict[str, Any], identifier_used: str) -> str:
        """
        Calculate confidence grade for token identification.
        
        Args:
            token: Verified token dict
            identifier_used: "contract" or "ticker"
            
        Returns:
            "high" | "med" | "low"
        """
        # High: Contract address provided (unambiguous)
        if identifier_used == "contract" or token.get('contract'):
            return "high"
        
        # Med: $TICKER (exact cashtag, less ambiguous)
        ticker_source = token.get('ticker_source', '')
        if ticker_source.startswith('$'):
            return "med"
        
        # Low: Bare TICKER (no $, no contract, most ambiguous)
        return "low"
    
    def _calculate_token_identification_source(self, token_info: Dict[str, Any], verified_token: Dict[str, Any]) -> str:
        """
        Calculate how token was identified (identification source).
        
        Returns:
            "contract_address" - Contract address was provided
            "ticker_exact" - Exact ticker ($TICKER) with Twitter match
            "ticker_approximate" - Exact ticker ($TICKER) without Twitter match
            "ticker_bare" - Bare ticker (no $, no contract)
        """
        # Contract address: most reliable identification
        if token_info.get('contract_address'):
            return "contract_address"
        
        # Check if exact ticker (has $)
        ticker_source = token_info.get('ticker_source', '')
        is_exact_ticker = ticker_source.startswith('$')
        
        # Check Twitter match (if we have social links from Dexscreener)
        twitter_match = self._check_twitter_handle_match(
            token_info.get('twitter_handles', []), 
            verified_token.get('social_links', {})
        )
        
        if is_exact_ticker and twitter_match:
            return "ticker_exact"
        elif is_exact_ticker:
            return "ticker_approximate"
        else:
            return "ticker_bare"
    
    def _check_twitter_handle_match(self, extracted_handles: list, token_socials: dict) -> bool:
        """Check if any extracted Twitter handles match the token's official socials"""
        if not extracted_handles or not token_socials:
            return False
        
        # Get Twitter URL from social links
        twitter_url = token_socials.get('twitter', '')
        if not twitter_url:
            return False
            
        # Extract handle from Twitter URL (e.g., "https://twitter.com/bonk_inu" -> "bonk_inu")
        if 'twitter.com/' in twitter_url.lower():
            twitter_handle = twitter_url.split('twitter.com/')[-1].split('/')[0].split('?')[0].lower()
        else:
            twitter_handle = twitter_url.lower()
        
        # Check if any extracted handle matches exactly
        for handle in extracted_handles:
            handle_clean = handle.lower().replace('@', '')
            # Exact match only
            if handle_clean == twitter_handle:
                return True
        return False
    
    def _get_relaxed_volume_threshold(self, base_threshold: float, confidence: str) -> float:
        """Get relaxed volume threshold based on confidence"""
        if confidence == "highest":
            return base_threshold * 0.1  # 90% reduction
        elif confidence == "high":
            return base_threshold * 0.4  # 60% reduction
        elif confidence == "medium":
            return base_threshold * 0.7  # 30% reduction
        else:  # low
            return base_threshold
    
    def _get_relaxed_liquidity_threshold(self, base_threshold: float, confidence: str) -> float:
        """Get relaxed liquidity threshold based on confidence"""
        if confidence == "highest":
            return base_threshold * 0.1  # 90% reduction
        elif confidence == "high":
            return base_threshold * 0.7  # 30% reduction
        else:  # medium, low
            return base_threshold
    
    def _get_relaxed_liq_mcap_ratio(self, base_ratio: float, confidence: str) -> float:
        """Get relaxed liquidity/market cap ratio based on confidence"""
        if confidence == "highest":
            return base_ratio * 0.1  # 90% reduction
        elif confidence == "high":
            return base_ratio * 0.7  # 30% reduction
        else:  # medium, low
            return base_ratio
    
    async def _analyze_curator_intent(self, message_text: str, token_info: Dict[str, Any], curator_id: str) -> Optional[Dict[str, Any]]:
        """
        Analyze curator intent for a specific token mention (Stage 2)
        
        Args:
            message_text: Original tweet/message text
            token_info: Token information from Stage 1
            curator_id: Curator identifier
            
        Returns:
            Intent analysis result or None if analysis failed
        """
        try:
            # Prepare prompt variables
            prompt_vars = {
                'message_text': message_text,
                'token_name': token_info.get('token_name', ''),
                'network': token_info.get('network', '')
            }
            
            self.logger.debug(f"Calling LLM for intent analysis: {token_info.get('token_name', 'unknown')}")
            
            # Use prompt manager to get intent analysis template
            prompt = self.prompt_manager.format_prompt(
                'curator_intent_analysis', 
                prompt_vars
            )
            system_message = self.prompt_manager.get_system_message('curator_intent_analysis')
            
            self.logger.debug(f"Using prompt manager: True")
            self.logger.debug(f"System message: {system_message[:50] if system_message else 'None'}...")
            
            # Generate response with system message if available
            if system_message:
                response = await self.llm_client.generate_async(prompt, system_message=system_message)
            else:
                response = await self.llm_client.generate_async(prompt)
            
            self.logger.debug(f"Raw LLM response: {response}")
            
            if not response:
                self.logger.warning(f"Intent analysis failed for token {token_info.get('token_name', 'unknown')}")
                return None
            
            # Parse the result
            if isinstance(response, str):
                import json
                try:
                    result = json.loads(response)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse intent analysis JSON: {e}")
                    return None
            else:
                result = response
            
            self.logger.info(f"Intent analysis for {token_info.get('token_name', 'unknown')}: {result.get('intent_analysis', {}).get('intent_type', 'unknown')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing curator intent: {e}", exc_info=True)
            return None
    
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
    
    async def _create_social_strand(self, curator: Dict[str, Any], message_data: Dict[str, Any], token: Dict[str, Any], extraction_result: Dict[str, Any] = None, intent_analysis: Dict[str, Any] = None, identifier_used: str = "ticker") -> Dict[str, Any]:
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
            
            # Get regime context (macro/meso/micro phases)
            regime_context = self._get_regime_context()
            
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
                "tags": ["curated", "social_signal", "dm_candidate", "verified"],
                "target_agent": "decision_maker_lowcap",  # Target the decision maker
                "signal_pack": {
                    "token": {
                        "ticker": token['ticker'],
                        "contract": token.get('contract'),
                        "identifier_used": identifier_used,
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
                    },
                    "intent_analysis": intent_analysis if intent_analysis else None,
                    # Token identification metadata
                    "identification_source": token.get('identification_source'),  # How token was identified
                    "mapping_reason": token.get('mapping_reason', 'ticker_only'),
                    "confidence_grade": self._calculate_confidence_grade(token, identifier_used),
                    "volume_health": token.get('volume_health'),
                    "liquidity_health": token.get('liquidity_health'),
                    "liq_mcap_ratio": token.get('liq_mcap_ratio'),
                    "mapping_status": token.get('mapping_status', 'resolved')
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
                    "token_ticker": token['ticker']
                },
                "regime_context": regime_context,  # Macro/meso/micro phases
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Create strand in database
            self.logger.debug(f"Creating strand in database...")
            created_strand = await self.supabase_manager.create_strand(strand)
            self.logger.debug(f"Database response: {created_strand}")
            
            # Increment curator chain_counts on successful strand creation
            if created_strand and token.get('chain'):
                try:
                    chain = token['chain'].lower()
                    curator_id = curator['id']
                    # Get current chain_counts
                    curator_result = self.supabase_manager.client.table('curators').select('chain_counts').eq('curator_id', curator_id).limit(1).execute()
                    if curator_result.data:
                        current_counts = curator_result.data[0].get('chain_counts', {}) or {}
                        if not isinstance(current_counts, dict):
                            current_counts = {}
                        # Increment count for this chain
                        current_counts[chain] = current_counts.get(chain, 0) + 1
                        # Update curator
                        self.supabase_manager.client.table('curators').update({
                            'chain_counts': current_counts
                        }).eq('curator_id', curator_id).execute()
                        self.logger.debug(f"Incremented chain_counts for {curator_id}: {chain} = {current_counts[chain]}")
                except Exception as e:
                    self.logger.warning(f"Failed to increment chain_counts for {curator_id}: {e}")
            
            # Log strand creation (strand monitor will show this in terminal)
            token_info = strand['signal_pack']['token']
            curator_id = strand['signal_pack']['curator']['id']
            vol = token_info.get('volume_24h', 0)
            liq = token_info.get('liquidity', 0)
            strand_id_short = created_strand.get('id', '')[:8] + '…'
            self.logger.info(f"NEW SIGNAL {curator_id} → {token_info['ticker']} ({token_info['chain']}) vol ${vol:,.0f} liq ${liq:,.0f}")
            self.logger.info(f"Strand created: {strand_id_short} → target: decision_maker_lowcap")
            
            # Trigger learning system to process the strand
            if hasattr(self, 'learning_system') and self.learning_system:
                self.logger.debug("Processing with Decision Maker")
                try:
                    # Use asyncio.create_task to handle the async call
                    asyncio.create_task(self.learning_system.process_strand_event(created_strand))
                    self.logger.debug("Learning system task created")
                except Exception as e:
                    self.logger.error(f"Error creating learning system task: {e}", exc_info=True)
            else:
                self.logger.warning("Learning system not available - skipping Decision Maker trigger")
            
            return created_strand
            
        except Exception as e:
            self.logger.error(f"Error creating social strand: {e}", exc_info=True)
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
            self.logger.info("Populating curators table from YAML config...")
            
            for curator in self.curators_config['curators']:
                if not curator.get('enabled', True):
                    continue
                    
                curator_id = curator['id']
                
                # Check if curator already exists using Supabase client directly
                existing_curator = self._get_curator_by_id_sync(curator_id)
                
                if existing_curator:
                    self.logger.debug(f"Curator {curator_id} already exists in database")
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
                self.logger.info(f"Added curator {curator_id} to database")
            
            self.logger.info("Curators table population completed")
            
        except Exception as e:
            self.logger.error(f"Failed to populate curators table: {e}", exc_info=True)
    
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
    
    def _get_regime_context(self) -> Dict[str, Dict[str, Any]]:
        """
        Get macro/meso/micro phases plus bucket snapshot for downstream use.
        """
        regime_context = {}
        
        for horizon in ["macro", "meso", "micro"]:
            try:
                res = (
                    self.supabase_manager.client.table("phase_state")
                    .select("phase,score,ts")
                    .eq("token", "PORTFOLIO")
                    .eq("horizon", horizon)
                    .order("ts", desc=True)
                    .limit(1)
                    .execute()
                )
                rows = res.data or []
                if rows:
                    regime_context[horizon] = {
                        "phase": rows[0].get("phase") or "",
                        "score": float(rows[0].get("score") or 0.0),
                        "ts": rows[0].get("ts") or datetime.now(timezone.utc).isoformat()
                    }
                else:
                    regime_context[horizon] = {
                        "phase": "",
                        "score": 0.0,
                        "ts": datetime.now(timezone.utc).isoformat()
                    }
            except Exception as e:
                self.logger.warning(f"Error fetching {horizon} phase: {e}")
                regime_context[horizon] = {
                    "phase": "",
                    "score": 0.0,
                    "ts": datetime.now(timezone.utc).isoformat()
                }
        bucket_snapshot = fetch_bucket_phase_snapshot(self.supabase_manager.client)
        regime_context["bucket_phases"] = bucket_snapshot.get("bucket_phases", {})
        regime_context["bucket_population"] = bucket_snapshot.get("bucket_population", {})
        regime_context["bucket_rank"] = bucket_snapshot.get("bucket_rank", [])

        return regime_context
    
    def _load_ignored_tokens(self) -> set:
        """
        Load ignored tokens from learning_configs table, fallback to hardcoded list.
        
        Returns:
            Set of token names (uppercase) to ignore
        """
        try:
            # Try to load from learning_configs
            result = (
                self.supabase_manager.client.table('learning_configs')
                .select('config_data')
                .eq('module_id', 'social_ingest')
                .limit(1)
                .execute()
            )
            
            if result.data and len(result.data) > 0:
                config_data = result.data[0].get('config_data', {})
                ambiguous_terms = config_data.get('ambiguous_terms', {})
                major_tokens = config_data.get('major_tokens', {})
                
                # Combine all tokens from both categories
                ignored = set()
                for token, info in ambiguous_terms.items():
                    if info.get('rule') == 'suppress':
                        ignored.add(token.upper())
                for token, info in major_tokens.items():
                    if info.get('rule') == 'hard_block':
                        ignored.add(token.upper())
                
                if ignored:
                    self.logger.info(f"Loaded {len(ignored)} ignored tokens from learning_configs")
                    return ignored
        
        except Exception as e:
            self.logger.warning(f"Failed to load ignored tokens from learning_configs: {e}. Using fallback.")
        
        # Fallback to hardcoded list
        fallback = {
            # Major tokens (not suitable for lowcap trading)
            'SOL', 'ETH', 'BTC', 'USDC', 'USDT', 'WETH', 'STETH', 'BNB',
            'BITCOIN', 'ETHEREUM', 'SOLANA',  # Full names for major tokens
            'HYPE', 'TAO', 'DAI', 'OHM',
            
            # Problematic/ambiguous tokens
            'TRUMP',
            'YZI', 'YZILABS',  # Specific tokens to avoid
            'DOGE',  # Major meme token
            'PEPE',  # Major meme token
            'BONK',  # Major meme token
            'WLFI',  # Specific token to avoid
            'APEX',  # ApeX Token - only has USDT pairs, no WETH pairs
            'XPL',   # Specific token to avoid
            'WEED',  # Specific token to avoid
            'BLV',   # Specific token to avoid
            'LIGHTER',  # Specific token to avoid
            'BSC',    # BSC token - avoid confusion with BSC chain
            '$4',     # Specific token to avoid
            '4',      # Specific token to avoid
            'XING',   # Specific token to avoid
            'JEWCOIN',  # Specific token to avoid
        }
        self.logger.info(f"Using fallback ignored tokens list ({len(fallback)} tokens)")
        return fallback
