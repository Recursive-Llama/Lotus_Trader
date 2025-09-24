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
    
    # Native token addresses for each chain
    NATIVE_TOKENS = {
        'base': '0x4200000000000000000000000000000000000006',      # WETH
        'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
        'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
        'solana': 'So11111111111111111111111111111111111111112',    # SOL
    }
    
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
                        # Filter for WBNB pairs first (native token)
                        wbnb_address = self.NATIVE_TOKENS['bsc']
                        wbnb_pairs = [p for p in bsc_pairs if p.get('quoteToken', {}).get('address', '').lower() == wbnb_address.lower()]
                        
                        if wbnb_pairs:
                            # Get the WBNB pair with highest liquidity
                            best_pair = max(wbnb_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                            price_native = best_pair.get('priceNative')
                            price_usd = best_pair.get('priceUsd')
                            if price_native and price_usd:
                                logger.info(f"BSC price for {token_address}: {price_native} BNB, ${price_usd} USD")
                                return {
                                    'price_native': float(price_native),
                                    'price_usd': float(price_usd),
                                    'quote_token': 'WBNB'
                                }
                        
                        # Fallback: use any pair if no WBNB pairs exist
                        logger.warning(f"No WBNB pairs found for {token_address}, using fallback")
                        best_pair = max(bsc_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                        price_native = best_pair.get('priceNative')
                        price_usd = best_pair.get('priceUsd')
                        if price_native and price_usd:
                            logger.warning(f"BSC fallback price for {token_address}: {price_native} {best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}, ${price_usd} USD")
                            return {
                                'price_native': float(price_native),
                                'price_usd': float(price_usd),
                                'quote_token': best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')
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
                        # Filter for WETH pairs first (native token)
                        weth_address = self.NATIVE_TOKENS['base']
                        weth_pairs = [p for p in base_pairs if p.get('quoteToken', {}).get('address', '').lower() == weth_address.lower()]
                        
                        if weth_pairs:
                            # Get the WETH pair with highest liquidity
                            best_pair = max(weth_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                            price_native = best_pair.get('priceNative')
                            price_usd = best_pair.get('priceUsd')
                            if price_native and price_usd:
                                logger.info(f"Base price for {token_address}: {price_native} ETH, ${price_usd} USD")
                                return {
                                    'price_native': float(price_native),
                                    'price_usd': float(price_usd),
                                    'quote_token': 'WETH'
                                }
                        
                        # Fallback: use any pair if no WETH pairs exist
                        logger.warning(f"No WETH pairs found for {token_address}, using fallback")
                        best_pair = max(base_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                        price_native = best_pair.get('priceNative')
                        price_usd = best_pair.get('priceUsd')
                        if price_native and price_usd:
                            logger.warning(f"Base fallback price for {token_address}: {price_native} {best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}, ${price_usd} USD")
                            return {
                                'price_native': float(price_native),
                                'price_usd': float(price_usd),
                                'quote_token': best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')
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
                        # Filter for WETH pairs first (native token)
                        weth_address = self.NATIVE_TOKENS['ethereum']
                        weth_pairs = [p for p in eth_pairs if p.get('quoteToken', {}).get('address', '').lower() == weth_address.lower()]
                        
                        if weth_pairs:
                            # Get the WETH pair with highest liquidity
                            best_pair = max(weth_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                            price_native = best_pair.get('priceNative')
                            price_usd = best_pair.get('priceUsd')
                            if price_native and price_usd:
                                logger.info(f"ETH price for {token_address}: {price_native} ETH, ${price_usd} USD")
                                return {
                                    'price_native': float(price_native),
                                    'price_usd': float(price_usd),
                                    'quote_token': 'WETH'
                                }
                        
                        # Fallback: use any pair if no WETH pairs exist
                        logger.warning(f"No WETH pairs found for {token_address}, using fallback")
                        best_pair = max(eth_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                        price_native = best_pair.get('priceNative')
                        price_usd = best_pair.get('priceUsd')
                        if price_native and price_usd:
                            logger.warning(f"ETH fallback price for {token_address}: {price_native} {best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}, ${price_usd} USD")
                            return {
                                'price_native': float(price_native),
                                'price_usd': float(price_usd),
                                'quote_token': best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')
                            }
                
                logger.warning(f"No Ethereum price found for {token_address}")
                return None
                
            except Exception as e:
                logger.error(f"DexScreener API error: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error fetching ETH price: {e}")
            return None
    
    def price_solana(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get token price on Solana
        
        Args:
            token_address: Token contract address (mint address)
            
        Returns:
            Dict with price_native (SOL per token) and price_usd (USD per token) or None if failed
        """
        try:
            # Fetch real price from DexScreener
            import requests
            try:
                response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
                if response.ok:
                    data = response.json()
                    pairs = data.get('pairs', [])
                    solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                    
                    if solana_pairs:
                        # Filter for SOL pairs first (native token)
                        sol_address = self.NATIVE_TOKENS['solana']
                        sol_pairs = [p for p in solana_pairs if p.get('quoteToken', {}).get('address', '').lower() == sol_address.lower()]
                        
                        if sol_pairs:
                            # Get the SOL pair with highest liquidity
                            best_pair = max(sol_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                            price_native = best_pair.get('priceNative')
                            price_usd = best_pair.get('priceUsd')
                            if price_native and price_usd:
                                logger.info(f"Solana price for {token_address}: {price_native} SOL, ${price_usd} USD")
                                return {
                                    'price_native': float(price_native),
                                    'price_usd': float(price_usd),
                                    'quote_token': 'SOL'
                                }
                        
                        # Fallback: use any pair if no SOL pairs exist
                        logger.warning(f"No SOL pairs found for {token_address}, using fallback")
                        best_pair = max(solana_pairs, key=lambda p: p.get('liquidity', {}).get('usd', 0))
                        price_native = best_pair.get('priceNative')
                        price_usd = best_pair.get('priceUsd')
                        if price_native and price_usd:
                            logger.warning(f"Solana fallback price for {token_address}: {price_native} {best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')}, ${price_usd} USD")
                            return {
                                'price_native': float(price_native),
                                'price_usd': float(price_usd),
                                'quote_token': best_pair.get('quoteToken', {}).get('symbol', 'UNKNOWN')
                            }
                
                logger.warning(f"No Solana price found for {token_address}")
                return None
                
            except Exception as e:
                logger.error(f"DexScreener API error: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error fetching Solana price: {e}")
            return None