#!/usr/bin/env python3
"""
Jupiter Trading Client for Solana

Handles token price fetching and trade execution via Jupiter API.
No API key required - Jupiter is a public API.
"""

import aiohttp
import logging
import asyncio
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
        self.base_url = "https://lite-api.jup.ag/swap/v1"
        self.rpc_url = f"https://rpc.helius.xyz/?api-key={helius_api_key}" if helius_api_key else "https://api.mainnet-beta.solana.com"
        
        # No rate limiting needed - was working fine before
        
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
            # Use lite API for price data
            url = "https://lite-api.jup.ag/price/v3"
            params = {
                "ids": token_address
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if token_address in data:
                            price_info = data[token_address]
                            return {
                                "token_address": token_address,
                                "price": Decimal(str(price_info.get("usdPrice", 0))),
                                "vs_token": vs_token,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "source": "jupiter",
                                "block_id": price_info.get("blockId"),
                                "decimals": price_info.get("decimals"),
                                "price_change_24h": price_info.get("priceChange24h")
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
                "prioritizationFeeLamports": "auto"
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
                "prioritizationFeeLamports": "auto" if (priority_fee_lamports == 0) else priority_fee_lamports
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
    
    # Token list functionality removed - use DexScreener for token discovery instead
    
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
            
            # Token search removed - use DexScreener for token discovery
            
        except Exception as e:
            print(f"❌ Error testing Jupiter: {e}")
    
    # Run test
    asyncio.run(test_jupiter())
