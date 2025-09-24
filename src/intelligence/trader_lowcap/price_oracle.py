#!/usr/bin/env python3
"""
Price Oracle for Multi-Chain Token Pricing

Provides unified price fetching across BSC, Base, and Ethereum chains.
"""

import logging
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class PriceOracle:
    """
    Price Oracle for fetching token prices across multiple chains
    
    Provides simple price fetching methods for BSC, Base, and Ethereum tokens.
    """
    
    def __init__(self, bsc_client=None, base_client=None, eth_client=None):
        """
        Initialize price oracle with chain clients
        
        Args:
            bsc_client: BSC Uniswap client
            base_client: Base Uniswap client  
            eth_client: Ethereum Uniswap client
        """
        self.bsc_client = bsc_client
        self.base_client = base_client
        self.eth_client = eth_client
        
        logger.info("Price oracle initialized")
    
    def price_bsc(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get token price on BSC
        
        Args:
            token_address: Token contract address
            
        Returns:
            Dict with price_native (BNB per token) and price_usd (USD per token) or None if failed
        """
        try:
            if not self.bsc_client:
                logger.warning("BSC client not available")
                return None
                
            # Fetch real price from DexScreener
            import requests
            try:
                response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
                if response.ok:
                    data = response.json()
                    pairs = data.get('pairs', [])
                    bsc_pairs = [p for p in pairs if p.get('chainId') == 'bsc']
                    
                    if bsc_pairs:
                        # Get the pair with highest liquidity
                        bsc_pairs.sort(key=lambda p: (p.get('liquidity', {}).get('usd') or 0), reverse=True)
                        best_pair = bsc_pairs[0]
                        price_native = best_pair.get('priceNative')
                        price_usd = best_pair.get('priceUsd')
                        if price_native and price_usd:
                            logger.info(f"BSC price for {token_address}: {price_native} BNB, ${price_usd} USD")
                            return {
                                'price_native': float(price_native),
                                'price_usd': float(price_usd),
                                'quote_token': 'WBNB'
                            }
                
                logger.warning(f"No BSC price found for {token_address}")
                return None
                
            except Exception as e:
                logger.error(f"DexScreener API error: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error fetching BSC price: {e}")
            return None
    
    def price_base(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get token price on Base
        
        Args:
            token_address: Token contract address
            
        Returns:
            Dict with price_native (ETH per token) and price_usd (USD per token) or None if failed
        """
        try:
            if not self.base_client:
                logger.warning("Base client not available")
                return None
                
            # Fetch real price from DexScreener
            import requests
            try:
                response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
                if response.ok:
                    data = response.json()
                    pairs = data.get('pairs', [])
                    base_pairs = [p for p in pairs if p.get('chainId') == 'base']
                    
                    if base_pairs:
                        # Get the pair with highest liquidity
                        base_pairs.sort(key=lambda p: (p.get('liquidity', {}).get('usd') or 0), reverse=True)
                        best_pair = base_pairs[0]
                        price_native = best_pair.get('priceNative')
                        price_usd = best_pair.get('priceUsd')
                        if price_native and price_usd:
                            logger.info(f"Base price for {token_address}: {price_native} ETH, ${price_usd} USD")
                            return {
                                'price_native': float(price_native),
                                'price_usd': float(price_usd),
                                'quote_token': 'WETH'
                            }
                
                logger.warning(f"No Base price found for {token_address}")
                return None
                
            except Exception as e:
                logger.error(f"DexScreener API error: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error fetching Base price: {e}")
            return None
    
    def price_eth(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get token price on Ethereum
        
        Args:
            token_address: Token contract address
            
        Returns:
            Dict with price_native (ETH per token) and price_usd (USD per token) or None if failed
        """
        try:
            if not self.eth_client:
                logger.warning("Ethereum client not available")
                return None
                
            # Fetch real price from DexScreener
            import requests
            try:
                response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
                if response.ok:
                    data = response.json()
                    pairs = data.get('pairs', [])
                    eth_pairs = [p for p in pairs if p.get('chainId') == 'ethereum']
                    
                    if eth_pairs:
                        # Get the pair with highest liquidity
                        eth_pairs.sort(key=lambda p: (p.get('liquidity', {}).get('usd') or 0), reverse=True)
                        best_pair = eth_pairs[0]
                        price_native = best_pair.get('priceNative')
                        price_usd = best_pair.get('priceUsd')
                        if price_native and price_usd:
                            logger.info(f"ETH price for {token_address}: {price_native} ETH, ${price_usd} USD")
                            return {
                                'price_native': float(price_native),
                                'price_usd': float(price_usd),
                                'quote_token': 'WETH'
                            }
                
                logger.warning(f"No Ethereum price found for {token_address}")
                return None
                
            except Exception as e:
                logger.error(f"DexScreener API error: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error fetching ETH price: {e}")
            return None