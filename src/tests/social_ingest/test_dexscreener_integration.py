#!/usr/bin/env python3
"""
Test DexScreener Integration

Tests the complete DexScreener integration with real tokens
from @0xdetweiler's tweets.
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

# Mock LLM Client for testing
class MockLLMClient:
    def __init__(self):
        pass
    
    async def generate_async(self, prompt, system_message=None, image=None):
        # Mock response for testing
        if "HABITAT" in prompt or "habitat" in prompt:
            return json.dumps({
                "token_name": "HABITAT",
                "network": "solana",
                "sentiment": "positive",
                "confidence": 0.8,
                "trading_intention": "buy",
                "has_chart": False,
                "chart_type": None,
                "additional_info": "ETH utility investors bridging to sol to bid $HABITAT"
            })
        elif "OMFG" in prompt or "omfg" in prompt:
            return json.dumps({
                "token_name": "OMFG",
                "network": "solana",
                "sentiment": "positive",
                "confidence": 0.7,
                "trading_intention": "buy",
                "has_chart": False,
                "chart_type": None,
                "additional_info": "ETH utility investors bridging to sol to bid $OMFG"
            })
        elif "CODECOPENFLOW" in prompt or "codecopenflow" in prompt:
            return json.dumps({
                "token_name": "CODECOPENFLOW",
                "network": "solana",
                "sentiment": "positive",
                "confidence": 0.6,
                "trading_intention": "buy",
                "has_chart": False,
                "chart_type": None,
                "handle_mentioned": "@Codecopenflow",
                "needs_verification": True,
                "additional_info": "Handle mention that might be a token"
            })
        else:
            return "null"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DexScreenerIntegrationTester:
    """Test complete DexScreener integration"""
    
    def __init__(self):
        self.llm_client = MockLLMClient()
    
    async def test_dexscreener_integration(self):
        """Test complete DexScreener integration with real tokens"""
        logger.info("🔍 DexScreener Integration Test")
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
                # Test DexScreener verification
                verified_token = await self._verify_token_with_dexscreener(token_info)
                
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
        
        logger.info("🎉 DexScreener integration test completed!")
    
    async def _verify_token_with_dexscreener(self, token_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Verify token using DexScreener API (copied from social_ingest_basic.py)"""
        try:
            import aiohttp
            
            token_name = token_info.get('token_name', '').upper()
            network = token_info.get('network', 'solana')
            
            if not token_name:
                logger.debug("No token name provided for verification")
                return None
            
            logger.info(f"🔍 Verifying token {token_name} on {network} via DexScreener...")
            
            # DexScreener API configuration
            base_url = "https://api.dexscreener.com/latest/dex/search"
            params = {"q": token_name}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'pairs' in data and data['pairs']:
                            # Find best match for the token (highest volume)
                            best_match = self._find_best_dexscreener_match(data['pairs'], token_name, network)
                            
                            if best_match:
                                # Extract token details from DexScreener result
                                token_details = self._extract_dexscreener_token_details(best_match)
                                if token_details:
                                    logger.info(f"✅ Found verified token: {token_details['ticker']} on {token_details['chain']}")
                                    return token_details
                                else:
                                    logger.debug(f"Could not extract details for token: {token_name}")
                                    return None
                            else:
                                logger.debug(f"No matching token found for: {token_name}")
                                return None
                        else:
                            logger.debug(f"No pairs found for: {token_name}")
                            return None
                    else:
                        logger.warning(f"DexScreener API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error verifying token with DexScreener: {e}")
            return None
    
    def _find_best_dexscreener_match(self, pairs: list, token_name: str, network: str) -> Optional[Dict[str, Any]]:
        """Find the best matching token from DexScreener search results (highest volume)"""
        try:
            if not pairs:
                return None
            
            # Filter by network if specified
            if network and network != 'solana':
                filtered_pairs = [p for p in pairs if p.get('chainId', '').lower() == network.lower()]
                if filtered_pairs:
                    pairs = filtered_pairs
            
            # Look for exact ticker match first
            for pair in pairs:
                if pair.get('baseToken', {}).get('symbol', '').upper() == token_name.upper():
                    return pair
            
            # Look for partial match
            for pair in pairs:
                symbol = pair.get('baseToken', {}).get('symbol', '').upper()
                if token_name.upper() in symbol or symbol in token_name.upper():
                    return pair
            
            # Return first result (already ordered by volume by DexScreener)
            return pairs[0] if pairs else None
            
        except Exception as e:
            logger.error(f"Error finding DexScreener match: {e}")
            return None
    
    def _extract_dexscreener_token_details(self, pair_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract token details from DexScreener pair data"""
        try:
            base_token = pair_data.get('baseToken', {})
            quote_token = pair_data.get('quoteToken', {})
            
            # Extract token details
            return {
                'ticker': base_token.get('symbol', ''),
                'name': base_token.get('name', ''),
                'contract': base_token.get('address', ''),
                'chain': self._map_dexscreener_chain(pair_data.get('chainId', '')),
                'price': float(pair_data.get('priceUsd', 0)),
                'volume_24h': float(pair_data.get('volume', {}).get('h24', 0)),
                'market_cap': float(pair_data.get('marketCap', 0)),
                'liquidity': float(pair_data.get('liquidity', {}).get('usd', 0)),
                'dex': pair_data.get('dexId', 'Unknown'),
                'verified': True,
                'dexscreener_pair_id': pair_data.get('pairAddress', ''),
                'quote_token': quote_token.get('symbol', ''),
                'quote_contract': quote_token.get('address', '')
            }
            
        except Exception as e:
            logger.error(f"Error extracting DexScreener token details: {e}")
            return None
    
    def _map_dexscreener_chain(self, chain_id: str) -> str:
        """Map DexScreener chain IDs to our chain names"""
        chain_mapping = {
            'solana': 'solana',
            'ethereum': 'ethereum',
            'base': 'base',
            'polygon': 'polygon',
            'arbitrum': 'arbitrum',
            'bsc': 'bsc',
            'avalanche': 'avalanche',
            'pulsechain': 'pulsechain',
            'osmosis': 'osmosis'
        }
        return chain_mapping.get(chain_id.lower(), 'solana')


async def main():
    """Main test function"""
    tester = DexScreenerIntegrationTester()
    await tester.test_dexscreener_integration()


if __name__ == "__main__":
    asyncio.run(main())
