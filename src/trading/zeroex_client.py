#!/usr/bin/env python3
"""
0x Protocol Client for EVM Trading

Handles token price fetching and trade execution via 0x Protocol API.
Supports Ethereum, Base, Polygon, Arbitrum, and other EVM chains.
"""

import aiohttp
import os
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ZeroExClient:
    """
    0x Protocol API client for EVM token trading
    
    Provides:
    - Token price fetching
    - Trade quote calculation
    - Trade execution via 0x Protocol
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize 0x Protocol client
        
        Args:
            api_key: 0x Protocol API key (optional, has free tier)
        """
        self.api_key = api_key
        self.base_url = "https://api.0x.org"
        
        # Chain-specific endpoints
        self.chain_endpoints = {
            'ethereum': 'https://api.0x.org',
            'base': 'https://base.api.0x.org',
            'polygon': 'https://polygon.api.0x.org',
            'arbitrum': 'https://arbitrum.api.0x.org',
            'bsc': 'https://bsc.api.0x.org',
            'avalanche': 'https://avalanche.api.0x.org'
        }
        
        logger.info("0x Protocol client initialized")
    
    def _get_chain_url(self, chain: str) -> str:
        """Get API URL for specific chain"""
        return self.chain_endpoints.get(chain.lower(), self.base_url)
    
    async def get_token_price(self, chain: str, token_address: str, vs_token: str = None) -> Optional[Dict[str, Any]]:
        """
        Get token price from 0x Protocol (legacy v1 helper)
        
        Args:
            chain: Blockchain network (ethereum, base, polygon, etc.)
            token_address: Token contract address
            vs_token: Quote token address (default: WETH)
            
        Returns:
            Price information or None if failed
        """
        try:
            if not vs_token:
                vs_token = self._get_weth_address(chain)
            
            url = f"{self._get_chain_url(chain)}/swap/v1/price"
            params = {
                "sellToken": token_address,
                "buyToken": vs_token,
                "sellAmount": "1000000000000000000",  # 1 token (18 decimals)
            }
            
            if self.api_key:
                params["apiKey"] = self.api_key
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return {
                            "token_address": token_address,
                            "vs_token": vs_token,
                            "price": Decimal(str(data.get("price", 0))),
                            "chain": chain,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "source": "0x_protocol"
                        }
                    else:
                        logger.error(f"0x Protocol API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting token price from 0x: {e}")
            return None

    async def get_implied_price_v2(self, chain: str, token_address: str) -> Optional[Dict[str, Any]]:
        """Derive price via 0x v2 quote by asking for a tiny WETH->token swap."""
        try:
            weth = self._get_weth_address(chain)
            # 1e15 wei (~0.001 WETH) small sell amount for price inference
            sell_amount = str(10**15)
            taker = os.getenv('ETHEREUM_WALLET_ADDRESS') or "0x0000000000000000000000000000000000000001"
            quote = await self.get_quote(
                chain=chain,
                sell_token=weth,
                buy_token=token_address,
                sell_amount=sell_amount,
                taker=taker,
                slippage_bps=50
            )
            if not quote or not quote.get('buy_amount'):
                return None
            buy_amount = int(quote['buy_amount'])
            # Assume 18 decimals for WETH; token decimals unknown → price in WETH per raw units
            # For our use we only need a positive scalar to proceed/log; execution uses full quote anyway
            price_weth_per_token = (10**15) / max(buy_amount, 1)
            return {
                'price': Decimal(str(price_weth_per_token)),
                'chain': chain,
                'source': '0x_v2_quote_implied',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error deriving implied price via v2: {e}")
            return None
    
    async def get_quote(self, 
                       chain: str,
                       sell_token: str, 
                       buy_token: str, 
                       sell_amount: str,
                       taker: str,
                       slippage_bps: int = 50) -> Optional[Dict[str, Any]]:
        """
        Get trade quote from 0x Protocol v2 API
        
        Args:
            chain: Blockchain network
            sell_token: Token to sell
            buy_token: Token to buy
            sell_amount: Amount to sell (in smallest units)
            taker: Taker wallet address
            slippage_bps: Slippage tolerance in basis points
            
        Returns:
            Quote information or None if failed
        """
        try:
            # Map chain names to chain IDs
            chain_ids = {
                'ethereum': 1,
                'base': 8453,
                'polygon': 137,
                'arbitrum': 42161,
                'bsc': 56,
                'avalanche': 43114
            }
            
            chain_id = chain_ids.get(chain.lower(), 1)
            # Use v2 Swap quote (not allowance-holder) for native sells
            url = f"{self._get_chain_url(chain)}/swap/quote"
            params = {
                "chainId": str(chain_id),
                "sellToken": sell_token,
                "buyToken": buy_token,
                "sellAmount": sell_amount,
                "taker": taker,
                "slippageBps": str(slippage_bps)
            }
            
            headers = {"0x-version": "v2"}
            if self.api_key:
                headers["0x-api-key"] = self.api_key
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract transaction details from v2 API response
                        transaction = data.get("transaction", {})
                        
                        return {
                            "chain": chain,
                            "sell_token": sell_token,
                            "buy_token": buy_token,
                            "sell_amount": sell_amount,
                            "buy_amount": data.get("buyAmount"),
                            "price": data.get("price"),
                            "slippage_bps": slippage_bps,
                            "gas_price": transaction.get("gasPrice"),
                            "gas": transaction.get("gas"),
                            "to": transaction.get("to"),
                            "data": transaction.get("data"),
                            "value": transaction.get("value"),
                            "allowance_target": data.get("allowanceTarget"),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"0x Protocol quote API error: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting quote from 0x: {e}")
            return None
    
    async def get_tokens(self, chain: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of supported tokens for a chain
        
        Args:
            chain: Blockchain network
            
        Returns:
            List of token information or None if failed
        """
        try:
            url = f"{self._get_chain_url(chain)}/swap/v1/tokens"
            
            if self.api_key:
                params = {"apiKey": self.api_key}
            else:
                params = {}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("records", [])
                    else:
                        logger.error(f"0x Protocol tokens API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting tokens from 0x: {e}")
            return None
    
    def _get_weth_address(self, chain: str) -> str:
        """Get WETH address for specific chain"""
        weth_addresses = {
            'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'base': '0x4200000000000000000000000000000000000006',
            'polygon': '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619',
            'arbitrum': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
            'bsc': '0x2170Ed0880ac9A755fd29B2688956BD959F933F8',
            'avalanche': '0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB'
        }
        return weth_addresses.get(chain.lower(), weth_addresses['ethereum'])
    
    def get_usdc_address(self, chain: str) -> str:
        """Get USDC address for specific chain"""
        usdc_addresses = {
            'ethereum': '0xA0b86a33E6441b8c4C8C0d4Ce0a0b86a33E6441b8',
            'base': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            'polygon': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
            'arbitrum': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
            'bsc': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
            'avalanche': '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E'
        }
        return usdc_addresses.get(chain.lower(), usdc_addresses['ethereum'])
    
    def get_usdt_address(self, chain: str) -> str:
        """Get USDT address for specific chain"""
        usdt_addresses = {
            'ethereum': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            'base': '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb',
            'polygon': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
            'arbitrum': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
            'bsc': '0x55d398326f99059fF775485246999027B3197955',
            'avalanche': '0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7'
        }
        return usdt_addresses.get(chain.lower(), usdt_addresses['ethereum'])
    
    async def search_tokens(self, chain: str, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for tokens by symbol or name
        
        Args:
            chain: Blockchain network
            query: Search query (symbol or name)
            
        Returns:
            List of matching tokens or None if failed
        """
        try:
            tokens = await self.get_tokens(chain)
            if not tokens:
                return None
            
            # Simple search in Python
            query_lower = query.lower()
            matches = []
            
            for token in tokens:
                symbol = token.get("symbol", "").lower()
                name = token.get("name", "").lower()
                
                if query_lower in symbol or query_lower in name:
                    matches.append(token)
            
            return matches[:10]  # Return top 10 matches
            
        except Exception as e:
            logger.error(f"Error searching tokens: {e}")
            return None


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_zeroex():
        """Test 0x Protocol client functionality"""
        try:
            # Initialize client
            zeroex = ZeroExClient()
            
            print("🔄 0x Protocol Client Test")
            print("=" * 40)
            
            # Test token price
            print("Getting ETH price on Ethereum...")
            eth_price = await zeroex.get_token_price(
                chain='ethereum',
                token_address='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'  # WETH
            )
            if eth_price:
                print(f"ETH Price: ${eth_price['price']}")
            
            # Test quote
            print("\nGetting ETH -> USDC quote...")
            quote = await zeroex.get_quote(
                chain='ethereum',
                sell_token='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                buy_token='0xA0b86a33E6441b8c4C8C0d4Ce0a0b86a33E6441b8',  # USDC
                sell_amount='1000000000000000000',  # 1 ETH
                slippage_percentage=0.5
            )
            
            if quote:
                print(f"Quote: {quote['sell_amount']} -> {quote['buy_amount']}")
                print(f"Price: {quote['price']}")
            
            # Test token search
            print(f"\nSearching for 'USDC' on Ethereum...")
            usdc_tokens = await zeroex.search_tokens('ethereum', 'USDC')
            if usdc_tokens:
                print(f"Found {len(usdc_tokens)} USDC tokens")
                for token in usdc_tokens[:3]:
                    print(f"  - {token['symbol']}: {token['address']}")
            
        except Exception as e:
            print(f"❌ Error testing 0x Protocol: {e}")
    
    # Run test
    asyncio.run(test_zeroex())
