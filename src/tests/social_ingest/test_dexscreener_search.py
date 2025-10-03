#!/usr/bin/env python3
"""
Test DexScreener API Search

Tests the DexScreener API to search for tokens by ticker symbols
and see if we can get contract addresses.
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DexScreenerTester:
    """Test DexScreener API search functionality"""
    
    async def test_dexscreener_search(self):
        """Test DexScreener API with various tokens"""
        logger.info("🔍 DexScreener API Search Test")
        logger.info("=" * 60)
        
        # Test tokens from @0xdetweiler's tweets
        test_tokens = [
            {
                'token_name': 'ASTER',
                'network': '',
                'additional_info': 'Testing ASTER token search with aggregated volume fix'
            },
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
                'token_name': 'SOL',
                'network': 'solana',
                'additional_info': 'Solana native token (known token)'
            },
            {
                'token_name': 'PEPE',
                'network': 'ethereum',
                'additional_info': 'Popular meme token (known token)'
            }
        ]
        
        for i, token_info in enumerate(test_tokens):
            logger.info(f"🔍 TESTING TOKEN {i+1}: {token_info['token_name']}")
            logger.info("-" * 40)
            
            try:
                # Test DexScreener search
                search_results = await self._search_dexscreener(token_info['token_name'])
                
                if search_results:
                    logger.info(f"✅ SUCCESS: Found {len(search_results)} results!")
                    
                    # Show first few results
                    for j, result in enumerate(search_results[:3]):
                        logger.info(f"   📊 Result {j+1}:")
                        logger.info(f"      🏷️  Symbol: {result.get('baseToken', {}).get('symbol', 'N/A')}")
                        logger.info(f"      📝 Name: {result.get('baseToken', {}).get('name', 'N/A')}")
                        logger.info(f"      💰 Contract: {result.get('baseToken', {}).get('address', 'N/A')}")
                        logger.info(f"      🌐 Chain: {result.get('chainId', 'N/A')}")
                        logger.info(f"      💵 Price: ${result.get('priceUsd', 'N/A')}")
                        logger.info(f"      📈 Volume 24h: ${result.get('volume', {}).get('h24', 'N/A')}")
                        logger.info(f"      🏪 DEX: {result.get('dexId', 'N/A')}")
                        logger.info("")
                else:
                    logger.info(f"❌ FAILED: No results found for {token_info['token_name']}")
                
            except Exception as e:
                logger.error(f"❌ ERROR: {e}")
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("")
        
        logger.info("🎉 DexScreener search test completed!")
    
    async def _search_dexscreener(self, ticker: str) -> Optional[list]:
        """Search DexScreener API for a ticker symbol"""
        try:
            import aiohttp
            
            logger.info(f"🔍 Searching DexScreener for: {ticker}")
            
            # DexScreener API endpoint
            base_url = "https://api.dexscreener.com/latest/dex/search"
            params = {"q": ticker}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'pairs' in data and data['pairs']:
                            logger.info(f"✅ Found {len(data['pairs'])} pairs for {ticker}")
                            return data['pairs']
                        else:
                            logger.info(f"❌ No pairs found for {ticker}")
                            return None
                    else:
                        logger.warning(f"DexScreener API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error searching DexScreener: {e}")
            return None


async def main():
    """Main test function"""
    tester = DexScreenerTester()
    await tester.test_dexscreener_search()


if __name__ == "__main__":
    asyncio.run(main())
