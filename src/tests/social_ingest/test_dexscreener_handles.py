#!/usr/bin/env python3
"""
Test DexScreener API with Twitter Handles

Tests if DexScreener can search for tokens using Twitter handles
like @Codecopenflow, @habitat, etc.
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


class DexScreenerHandleTester:
    """Test DexScreener API with Twitter handles"""
    
    async def test_dexscreener_handles(self):
        """Test DexScreener API with Twitter handles"""
        logger.info("🔍 DexScreener API - Twitter Handle Search Test")
        logger.info("=" * 70)
        
        # Test Twitter handles
        test_handles = [
            {
                'handle': '@Codecopenflow',
                'clean_handle': 'Codecopenflow',
                'additional_info': 'Twitter handle that might be a token'
            },
            {
                'handle': '@habitat',
                'clean_handle': 'habitat',
                'additional_info': 'Twitter handle that might be a token'
            },
            {
                'handle': '@omfg',
                'clean_handle': 'omfg',
                'additional_info': 'Twitter handle that might be a token'
            },
            {
                'handle': '@solana',
                'clean_handle': 'solana',
                'additional_info': 'Known project handle'
            }
        ]
        
        for i, handle_info in enumerate(test_handles):
            logger.info(f"🔍 TESTING HANDLE {i+1}: {handle_info['handle']}")
            logger.info("-" * 50)
            
            try:
                # Test DexScreener search with handle
                search_results = await self._search_dexscreener_handle(handle_info['clean_handle'])
                
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
                    logger.info(f"❌ FAILED: No results found for {handle_info['handle']}")
                
            except Exception as e:
                logger.error(f"❌ ERROR: {e}")
            
            logger.info("")
            logger.info("=" * 70)
            logger.info("")
        
        logger.info("🎉 DexScreener handle search test completed!")
    
    async def _search_dexscreener_handle(self, handle: str) -> Optional[list]:
        """Search DexScreener API for a Twitter handle"""
        try:
            import aiohttp
            
            logger.info(f"🔍 Searching DexScreener for handle: {handle}")
            
            # DexScreener API endpoint
            base_url = "https://api.dexscreener.com/latest/dex/search"
            params = {"q": handle}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'pairs' in data and data['pairs']:
                            logger.info(f"✅ Found {len(data['pairs'])} pairs for {handle}")
                            return data['pairs']
                        else:
                            logger.info(f"❌ No pairs found for {handle}")
                            return None
                    else:
                        logger.warning(f"DexScreener API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error searching DexScreener: {e}")
            return None


async def main():
    """Main test function"""
    tester = DexScreenerHandleTester()
    await tester.test_dexscreener_handles()


if __name__ == "__main__":
    asyncio.run(main())
