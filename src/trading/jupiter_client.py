#!/usr/bin/env python3
"""
Jupiter Trading Client for Solana

Handles token price fetching and trade execution via Jupiter API.
No API key required - Jupiter is a public API.
"""

import aiohttp
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class JupiterClient:
    """
    Jupiter API client for Solana token trading
    
    Provides:
    - Token price fetching
    - Trade route calculation
    - Trade execution via Helius RPC
    """
    
    def __init__(self, helius_api_key: str = None):
        """
        Initialize Jupiter client
        
        Args:
            helius_api_key: Helius API key for RPC calls
        """
        self.helius_api_key = helius_api_key
        self.base_url = "https://quote-api.jup.ag/v6"
        self.rpc_url = f"https://rpc.helius.xyz/?api-key={helius_api_key}" if helius_api_key else "https://api.mainnet-beta.solana.com"
        
        logger.info("Jupiter client initialized")
    
    async def get_token_price(self, token_address: str, vs_token: str = "So11111111111111111111111111111111111111112") -> Optional[Dict[str, Any]]:
        """
        Get token price from Jupiter
        
        Args:
            token_address: Token contract address
            vs_token: Quote token address (default: SOL)
            
        Returns:
            Price information or None if failed
        """
        try:
            url = f"{self.base_url}/price"
            params = {
                "ids": token_address,
                "vsToken": vs_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if token_address in data.get("data", {}):
                            price_info = data["data"][token_address]
                            return {
                                "token_address": token_address,
                                "price": Decimal(str(price_info.get("price", 0))),
                                "vs_token": vs_token,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "source": "jupiter"
                            }
                        else:
                            logger.warning(f"Token {token_address} not found in Jupiter response")
                            return None
                    else:
                        logger.error(f"Jupiter API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return None
    
    async def get_quote(self, 
                       input_mint: str, 
                       output_mint: str, 
                       amount: int, 
                       slippage_bps: int = 50) -> Optional[Dict[str, Any]]:
        """
        Get trade quote from Jupiter
        
        Args:
            input_mint: Input token address
            output_mint: Output token address  
            amount: Amount in smallest units (e.g., lamports for SOL)
            slippage_bps: Slippage in basis points (50 = 0.5%)
            
        Returns:
            Raw Jupiter quote response or None if failed
        """
        try:
            url = f"{self.base_url}/quote"
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": str(slippage_bps),
                "swapMode": "ExactIn",
                "onlyDirectRoutes": "false",
                "prioritizationFeeLamports": "0"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "error" in data:
                            logger.error(f"Jupiter quote error: {data['error']}")
                            return None
                        
                        return data  # Return raw response for swap API
                    else:
                        logger.error(f"Jupiter quote API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            return None
    
    async def get_swap_transaction(self, 
                                 quote: Dict[str, Any], 
                                 user_public_key: str,
                                 priority_fee_lamports: int = 0) -> Optional[Dict[str, Any]]:
        """
        Get swap transaction from Jupiter
        
        Args:
            quote: Quote data from get_quote()
            user_public_key: User's wallet public key
            priority_fee_lamports: Priority fee in lamports
            
        Returns:
            Transaction data or None if failed
        """
        try:
            url = f"{self.base_url}/swap"
            
            payload = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": True,
                "asLegacyTransaction": False,
                "prioritizationFeeLamports": priority_fee_lamports
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if "error" in data:
                            logger.error(f"Jupiter swap error: {data['error']}")
                            return None
                        
                        return {
                            "swap_transaction": data.get("swapTransaction"),
                            "user_public_key": user_public_key,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    else:
                        logger.error(f"Jupiter swap API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting swap transaction: {e}")
            return None
    
    async def get_token_list(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of supported tokens from Jupiter
        
        Returns:
            List of token information or None if failed
        """
        try:
            url = f"{self.base_url}/tokens"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"Jupiter tokens API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting token list: {e}")
            return None
    
    async def search_tokens(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for tokens by symbol or name
        
        Args:
            query: Search query (symbol or name)
            
        Returns:
            List of matching tokens or None if failed
        """
        try:
            tokens = await self.get_token_list()
            if not tokens:
                return None
            
            # Simple search in Python (Jupiter doesn't have search endpoint)
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
    
    def get_sol_mint_address(self) -> str:
        """Get SOL mint address"""
        return "So11111111111111111111111111111111111111112"
    
    def get_usdc_mint_address(self) -> str:
        """Get USDC mint address on Solana"""
        return "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    def get_usdt_mint_address(self) -> str:
        """Get USDT mint address on Solana"""
        return "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_jupiter():
        """Test Jupiter client functionality"""
        try:
            # Initialize client
            helius_key = os.getenv('HELIUS_API_KEY')
            jupiter = JupiterClient(helius_key)
            
            print("🪐 Jupiter Client Test")
            print("=" * 40)
            
            # Test token price
            sol_address = jupiter.get_sol_mint_address()
            usdc_address = jupiter.get_usdc_mint_address()
            
            print(f"Getting SOL price...")
            sol_price = await jupiter.get_token_price(sol_address)
            if sol_price:
                print(f"SOL Price: ${sol_price['price']}")
            
            # Test quote
            print(f"\nGetting SOL -> USDC quote...")
            quote = await jupiter.get_quote(
                input_mint=sol_address,
                output_mint=usdc_address,
                amount=1000000000,  # 1 SOL in lamports
                slippage_bps=50
            )
            
            if quote:
                print(f"Quote: {quote['in_amount']} -> {quote['out_amount']}")
                print(f"Price Impact: {quote['price_impact_pct']}%")
            
            # Test token search
            print(f"\nSearching for 'BONK'...")
            bonk_tokens = await jupiter.search_tokens("BONK")
            if bonk_tokens:
                print(f"Found {len(bonk_tokens)} BONK tokens")
                for token in bonk_tokens[:3]:
                    print(f"  - {token['symbol']}: {token['address']}")
            
        except Exception as e:
            print(f"❌ Error testing Jupiter: {e}")
    
    # Run test
    asyncio.run(test_jupiter())
