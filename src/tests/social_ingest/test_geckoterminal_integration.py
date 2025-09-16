#!/usr/bin/env python3
"""
Test GeckoTerminal Integration

Tests the real GeckoTerminal API integration with actual tokens
found in @0xdetweiler's tweets.
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from test_token_detection import MockLLMClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GeckoTerminalTester:
    """Test GeckoTerminal API integration"""
    
    def __init__(self):
        self.llm_client = MockLLMClient()
    
    async def test_geckoterminal_integration(self):
        """Test GeckoTerminal API with real tokens"""
        logger.info("🦎 GeckoTerminal API Integration Test")
        logger.info("=" * 60)
        
        # Test tokens from @0xdetweiler's tweets
        test_tokens = [
            {
                'token_name': 'HABITAT',
                'network': 'solana',
                'additional_info': 'ETH utility investors bridging to sol to bid $HABITAT'
            },
            {
                'token_name': 'OMFG',
                'network': 'solana',
                'additional_info': 'ETH utility investors bridging to sol to bid $OMFG'
            },
            {
                'token_name': 'CODECOPENFLOW',
                'network': 'solana',
                'additional_info': 'Handle mention that might be a token'
            }
        ]
        
        for i, token_info in enumerate(test_tokens):
            logger.info(f"🔍 TESTING TOKEN {i+1}: {token_info['token_name']}")
            logger.info("-" * 40)
            
            try:
                # Test GeckoTerminal verification
                verified_token = await self._verify_token_with_geckoterminal(token_info)
                
                if verified_token:
                    logger.info(f"✅ SUCCESS: Found verified token!")
                    logger.info(f"   📊 Ticker: {verified_token.get('ticker', 'N/A')}")
                    logger.info(f"   🌐 Chain: {verified_token.get('chain', 'N/A')}")
                    logger.info(f"   💰 Contract: {verified_token.get('contract', 'N/A')}")
                    logger.info(f"   💵 Price: ${verified_token.get('price', 0):.6f}")
                    logger.info(f"   📈 Volume 24h: ${verified_token.get('volume_24h', 0):,.2f}")
                    logger.info(f"   🏦 Market Cap: ${verified_token.get('market_cap', 0):,.2f}")
                    logger.info(f"   💧 Liquidity: ${verified_token.get('liquidity', 0):,.2f}")
                    logger.info(f"   🏪 DEX: {verified_token.get('dex', 'N/A')}")
                    logger.info(f"   ✅ Verified: {verified_token.get('verified', False)}")
                else:
                    logger.info(f"❌ FAILED: Token not found or verification failed")
                
            except Exception as e:
                logger.error(f"❌ ERROR: {e}")
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("")
        
        logger.info("🎉 GeckoTerminal integration test completed!")
    
    async def _verify_token_with_geckoterminal(self, token_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verify token using GeckoTerminal API (copied from social_ingest_basic.py)"""
        try:
            import aiohttp
            
            token_name = token_info.get('token_name', '').upper()
            network = token_info.get('network', 'solana')
            
            if not token_name:
                logger.debug("No token name provided for verification")
                return None
            
            logger.info(f"🔍 Verifying token {token_name} on {network} via GeckoTerminal...")
            
            # GeckoTerminal API configuration
            base_url = "https://api.geckoterminal.com/api/v2"
            headers = {"Accept": "application/json;version=20230302"}
            
            # Search for token on GeckoTerminal
            search_url = f"{base_url}/search?query={token_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Find best match for the token
                        best_match = self._find_best_token_match(data, token_name, network)
                        
                        if best_match:
                            # Get detailed token info
                            token_details = await self._get_token_details(best_match, base_url, headers)
                            if token_details:
                                logger.info(f"✅ Found verified token: {token_details['ticker']} on {token_details['chain']}")
                                return token_details
                            else:
                                logger.debug(f"Could not get details for token: {token_name}")
                                return None
                        else:
                            logger.debug(f"No matching token found for: {token_name}")
                            return None
                    else:
                        logger.warning(f"GeckoTerminal API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error verifying token with GeckoTerminal: {e}")
            return None
    
    def _find_best_token_match(self, search_data: Dict[str, Any], token_name: str, network: str) -> Optional[Dict[str, Any]]:
        """Find the best matching token from GeckoTerminal search results"""
        try:
            if 'data' not in search_data or not search_data['data']:
                return None
            
            # Look for exact ticker match first
            for token in search_data['data']:
                if token.get('attributes', {}).get('symbol', '').upper() == token_name.upper():
                    return token
            
            # Look for partial match
            for token in search_data['data']:
                symbol = token.get('attributes', {}).get('symbol', '').upper()
                if token_name.upper() in symbol or symbol in token_name.upper():
                    return token
            
            # Return first result if no exact match
            return search_data['data'][0] if search_data['data'] else None
            
        except Exception as e:
            logger.error(f"Error finding token match: {e}")
            return None
    
    async def _get_token_details(self, token_data: Dict[str, Any], base_url: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Get detailed token information from GeckoTerminal"""
        try:
            import aiohttp
            
            token_id = token_data.get('id')
            if not token_id:
                return None
            
            # Get token details
            details_url = f"{base_url}/tokens/{token_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(details_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'data' in data and data['data']:
                            token_info = data['data']
                            attributes = token_info.get('attributes', {})
                            
                            # Extract token details
                            return {
                                'ticker': attributes.get('symbol', ''),
                                'name': attributes.get('name', ''),
                                'contract': attributes.get('address', ''),
                                'chain': self._map_geckoterminal_chain(attributes.get('network', '')),
                                'price': attributes.get('price_usd', 0),
                                'volume_24h': attributes.get('volume_usd', 0),
                                'market_cap': attributes.get('market_cap_usd', 0),
                                'liquidity': attributes.get('reserve_in_usd', 0),
                                'dex': self._extract_dex_name(attributes.get('dex_id', '')),
                                'verified': True,
                                'geckoterminal_id': token_id
                            }
                        else:
                            return None
                    else:
                        logger.warning(f"GeckoTerminal details API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting token details: {e}")
            return None
    
    def _map_geckoterminal_chain(self, network: str) -> str:
        """Map GeckoTerminal network names to our chain names"""
        chain_mapping = {
            'solana': 'solana',
            'ethereum': 'ethereum',
            'base': 'base',
            'polygon': 'polygon',
            'arbitrum': 'arbitrum',
            'bsc': 'bsc',
            'avalanche': 'avalanche'
        }
        return chain_mapping.get(network.lower(), 'solana')
    
    def _extract_dex_name(self, dex_id: str) -> str:
        """Extract DEX name from GeckoTerminal dex_id"""
        if not dex_id:
            return 'Unknown'
        
        # Common DEX mappings
        dex_mapping = {
            'raydium': 'Raydium',
            'uniswap_v3': 'Uniswap V3',
            'uniswap_v2': 'Uniswap V2',
            'pancakeswap': 'PancakeSwap',
            'sushiswap': 'SushiSwap',
            'curve': 'Curve',
            'balancer': 'Balancer'
        }
        
        return dex_mapping.get(dex_id.lower(), dex_id.title())


async def main():
    """Main test function"""
    tester = GeckoTerminalTester()
    await tester.test_geckoterminal_integration()


if __name__ == "__main__":
    asyncio.run(main())
