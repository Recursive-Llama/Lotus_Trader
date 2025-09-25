#!/usr/bin/env python3
"""
Price Monitor for Active Positions

Monitors token prices and checks exit/entry conditions for active positions.
Handles both immediate entries and planned dip entries.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import json

import os
from .jupiter_client import JupiterClient
from .wallet_manager import WalletManager
from .evm_uniswap_client import EvmUniswapClient, WETH_ADDRESSES as BASE_WETH_ADDRESSES
from .evm_uniswap_client_eth import EthUniswapClient, WETH_ADDRESS as ETH_WETH_ADDRESS

logger = logging.getLogger(__name__)


class PriceMonitor:
    """
    Price monitoring system for active positions
    
    Monitors:
    - Current position prices for exit conditions
    - Planned entry prices for dip entries
    - Portfolio exposure and risk management
    """
    
    def __init__(self, supabase_manager, jupiter_client: JupiterClient, wallet_manager: WalletManager, trader=None):
        """
        Initialize price monitor
        
        Args:
            supabase_manager: Database manager for position queries
            jupiter_client: Jupiter client for price fetching
            wallet_manager: Wallet manager for balance checks
        """
        self.supabase_manager = supabase_manager
        self.jupiter_client = jupiter_client
        self.wallet_manager = wallet_manager
        self.trader = trader  # Optional: use trader to execute planned entries/exits
        # Initialize EVM clients for pricing (lazy initialization)
        self.base_client = None
        self.eth_client = None
        self.bsc_client = None
        # Support both BASE_RPC_URL and legacy RPC_URL for Base; BSC via BSC_RPC_URL
        self.base_rpc_url = os.getenv('BASE_RPC_URL') or os.getenv('RPC_URL')
        self.eth_rpc_url = os.getenv('ETH_RPC_URL')
        self.bsc_rpc_url = os.getenv('BSC_RPC_URL')
        
        # Log client initialization status
        logger.info(f"Price monitor clients: Jupiter=✅, Base={'✅' if self.base_rpc_url else '❌'}, Ethereum={'✅' if self.eth_rpc_url else '❌'}, BSC={'✅' if self.bsc_rpc_url else '❌'}")
        self.monitoring = False
        self.monitor_task = None
        # Price lookup cache: {chain}_{token} -> {method}
        self.price_lookup_cache = {}
    
    def _get_cached_method(self, chain: str, token_contract: str) -> Optional[str]:
        """Get cached successful method for token lookup"""
        cache_key = f"{chain}_{token_contract}"
        return self.price_lookup_cache.get(cache_key)
    
    def _cache_successful_method(self, chain: str, token_contract: str, method: str):
        """Cache successful lookup method for future use"""
        cache_key = f"{chain}_{token_contract}"
        self.price_lookup_cache[cache_key] = method
        logger.debug(f"Cached successful method for {token_contract} on {chain}: {method}")
        # Cached SOL/USD for SOL-denominated comparisons
        self._sol_usd_price: Optional[float] = None
        self._sol_usd_time: Optional[datetime] = None
        self._sol_cache_ttl: int = 60  # seconds
        
        logger.info("Price monitor initialized")
    
    def _get_base_client(self):
        """Lazy initialization of Base client"""
        if self.base_client is None:
            try:
                # Check if we have a private key for Base trading
                base_pk = (
                    os.getenv('BASE_WALLET_PRIVATE_KEY')
                    or os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
                    or os.getenv('ETH_WALLET_PRIVATE_KEY')
                )
                if not base_pk:
                    logger.warning("No private key available for Base client - price lookups will be limited")
                    self.base_client = False
                    return None
                
                if self.base_rpc_url:
                    self.base_client = EvmUniswapClient(chain='base', rpc_url=self.base_rpc_url, private_key=base_pk)
                else:
                    self.base_client = EvmUniswapClient(chain='base', private_key=base_pk)
                logger.warning("Base Uniswap client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Base client: {e}")
                self.base_client = False  # Mark as failed to avoid retrying
        return self.base_client if self.base_client is not False else None
    
    def _get_eth_client(self):
        """Lazy initialization of Ethereum client"""
        if self.eth_client is None and self.eth_rpc_url:
            try:
                self.eth_client = EthUniswapClient(rpc_url=self.eth_rpc_url)
                logger.warning("Ethereum Uniswap client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Ethereum client: {e}")
                self.eth_client = False  # Mark as failed to avoid retrying
        return self.eth_client if self.eth_client is not False else None

    def _get_bsc_client(self):
        """Lazy initialization of BSC client"""
        if self.bsc_client is None and self.bsc_rpc_url:
            try:
                # Get BSC private key
                bsc_pk = os.getenv('BSC_WALLET_PRIVATE_KEY')
                if not bsc_pk:
                    logger.warning("No BSC private key available - BSC price lookups will be limited")
                    self.bsc_client = False
                    return None
                
                # Chain is 'bsc'; RPC explicit
                self.bsc_client = EvmUniswapClient(chain='bsc', rpc_url=self.bsc_rpc_url, private_key=bsc_pk)
                logger.warning("BSC Pancake client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize BSC client: {e}")
                self.bsc_client = False
        return self.bsc_client if self.bsc_client is not False else None
    
    async def start_monitoring(self, check_interval: int = 30):
        """
        Start price monitoring loop
        
        Args:
            check_interval: Seconds between price checks
        """
        if self.monitoring:
            logger.warning("Price monitoring already running")
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop(check_interval))
        logger.info(f"Price monitoring started (interval: {check_interval}s)")
    
    async def stop_monitoring(self):
        """Stop price monitoring"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Price monitoring stopped")
    
    async def _monitoring_loop(self, check_interval: int):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                await self._check_all_positions()
                await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(check_interval)
    
    async def _check_all_positions(self):
        """Check all active positions for exit/entry conditions"""
        try:
            # Get active positions from database
            active_positions = await self._get_active_positions()
            
            if not active_positions:
                return
            
            logger.info(f"Checking {len(active_positions)} active positions")
            
            # Add delay between position checks to avoid rate limiting
            for i, position in enumerate(active_positions):
                await self._check_position(position)
                # Add 3 second delay between checks to avoid rate limiting
                if i < len(active_positions) - 1:  # Don't delay after last position
                    await asyncio.sleep(3)
                
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
    
    async def _get_active_positions(self) -> List[Dict[str, Any]]:
        """Get active positions from database using direct Supabase client"""
        try:
            # Use direct Supabase client instead of RPC
            result = self.supabase_manager.client.table('lowcap_positions').select('*').eq('status', 'active').order('created_at', desc=True).execute()
            
            if result.data:
                logger.info(f"📊 Found {len(result.data)} active positions")
                return result.data
            else:
                # Only log this occasionally, not every 30 seconds
                return []
            
        except Exception as e:
            logger.warning(f"Error getting active positions (table may not exist): {e}")
            return []
    
    async def _check_position(self, position: Dict[str, Any]):
        """Check a single position for exit/entry conditions"""
        try:
            token_contract = position.get('token_contract')
            token_chain = (position.get('token_chain') or '').lower()
            if not token_contract or not token_chain:
                return

            # Get current price by chain
            current_price = await self._get_current_price_by_chain(token_contract, token_chain)
            if token_chain == 'solana' and current_price is not None:
                # Convert USD to SOL for SOL-denominated targets
                sol_usd = await self._get_sol_usd_price()
                if not sol_usd or sol_usd <= 0:
                    logger.warning("Skipping check: unable to refresh SOL/USD for SOL-denominated targets")
                    return
                price_in_sol = float(current_price) / float(sol_usd)
                logger.warning(f"Price monitor (SOL): {price_in_sol:.10f} SOL (≈ ${current_price:.8f}) for {token_contract} on solana")
                current_price = price_in_sol
            else:
                logger.warning(f"Price monitor got price: {current_price} for {token_contract} on {token_chain}")
            if current_price is None:
                logger.warning(f"Could not get price for {token_contract} on {token_chain}")
                return

            # Planned entries and exits (DB arrays) executed via Trader if available
            await self._check_planned_entries(position, float(current_price))
            await self._check_exits(position, float(current_price))
            
        except Exception as e:
            logger.error(f"Error checking position {position.get('id', 'unknown')}: {e}")
    
    async def _check_exits(self, position: Dict[str, Any], current_price: float):
        """Execute pending exits when price target reached using Trader if available"""
        try:
            exits = position.get('exits', [])
            if not exits:
                return
            position_id = position.get('id')
            
            # Process exits sequentially to avoid nonce conflicts
            for exit_order in exits:
                if exit_order.get('status') == 'pending':
                    target_price = float(exit_order.get('price', 0))
                    exit_number = exit_order.get('exit_number')
                    if current_price >= target_price and self.trader:
                        logger.info(f"Triggering exit {exit_number} for {position.get('token_ticker')} at {current_price:.6f} (target {target_price:.6f})")
                        try:
                            # Execute exit and wait for confirmation
                            success = await self.trader._execute_exit(position_id, exit_number)
                            if success:
                                logger.info(f"Exit {exit_number} executed and confirmed successfully")
                                # Add cooldown between exits to prevent nonce conflicts
                                await asyncio.sleep(5)
                            else:
                                logger.warning(f"Exit {exit_number} execution failed or not confirmed")
                                # Add longer cooldown on failure
                                await asyncio.sleep(10)
                        except Exception as exec_err:
                            logger.error(f"Error executing trader exit: {exec_err}")
                            # Add cooldown on error
                            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error checking exits: {e}")
    
    async def _check_planned_entries(self, position: Dict[str, Any], current_price: float):
        """Execute planned dip entries when targets hit using Trader if available"""
        try:
            entries = position.get('entries', [])
            if not entries:
                return
            position_id = position.get('id')
            
            # Process entries sequentially to avoid nonce conflicts
            for entry in entries:
                if entry.get('status') == 'pending':
                    target_price = float(entry.get('price', 0))
                    entry_number = entry.get('entry_number')
                    if current_price <= target_price and self.trader:
                        logger.info(f"Triggering planned entry {entry_number} at {current_price:.6f} (target {target_price:.6f})")
                        try:
                            # Execute entry and wait for confirmation
                            success = await self.trader._execute_entry_with_confirmation(position_id, entry_number)
                            if success:
                                logger.info(f"Entry {entry_number} executed and confirmed successfully")
                                # Add cooldown between entries to prevent nonce conflicts
                                await asyncio.sleep(5)
                            else:
                                logger.warning(f"Entry {entry_number} execution failed or not confirmed")
                                # Add longer cooldown on failure
                                await asyncio.sleep(10)
                        except Exception as exec_err:
                            logger.error(f"Error executing trader entry: {exec_err}")
                            # Add cooldown on error
                            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error checking planned entries: {e}")

    async def _get_current_price_by_chain(self, token_contract: str, chain: str, ticker: Optional[str] = None) -> Optional[float]:
        """Fetch current price depending on chain"""
        try:
            if chain == 'solana':
                # Try PriceOracle first (via trader), then fallback to Jupiter
                logger.warning(f"Getting price for Solana token: {token_contract}")
                
                # Try PriceOracle if trader is available
                if self.trader and hasattr(self.trader, 'price_oracle'):
                    try:
                        price_info = self.trader.price_oracle.price_solana(token_contract)
                        if price_info and price_info.get('price_usd'):
                            logger.warning(f"Solana price from PriceOracle: ${price_info['price_usd']} USD")
                            return float(price_info['price_usd'])
                    except Exception as e:
                        logger.warning(f"PriceOracle failed for Solana: {e}, trying Jupiter fallback")
                
                # Fallback to Jupiter
                price_info = await self.jupiter_client.get_token_price(token_contract, chain)
                logger.warning(f"Jupiter response: {price_info}")
                if price_info:
                    logger.warning(f"Price info exists, extracting USD price: {price_info.get('price')}")
                    return float(price_info['price'])
                logger.warning(f"No price info returned for {token_contract}")
                return None
            elif chain == 'base':
                base_client = self._get_base_client()
                if not base_client:
                    return None
                
                # Check cache first
                cached_method = self._get_cached_method(chain, token_contract)
                logger.warning(f"Getting price for Base token: {token_contract}")
                
                try:
                    amount_in = int(0.001 * 1e18)  # 0.001 WETH
                    
                    # Try cached method first if available
                    if cached_method == 'aerodrome_pair':
                        try:
                            import requests
                            r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}", timeout=8)
                            if r.ok:
                                data = r.json() or {}
                                pairs = data.get('pairs') or []
                                base_pairs = [p for p in pairs if p.get('chainId') == 'base']
                                aerodrome_pairs = [p for p in base_pairs if p.get('dexId') == 'aerodrome' and p.get('quoteToken',{}).get('symbol') == 'WETH']
                                if aerodrome_pairs:
                                    preferred = sorted(aerodrome_pairs, key=lambda p: (p.get('liquidity',{}).get('usd') or 0), reverse=True)[0]
                                    if preferred and preferred.get('pairAddress'):
                                        pair_addr = preferred['pairAddress']
                                        out = base_client.pair_get_amount_out(pair_addr, amount_in, BASE_WETH_ADDRESSES['base'])
                                        if out and out > 0:
                                            token_dec = base_client.get_token_decimals(token_contract)
                                            price = (0.001) / (out / (10 ** token_dec))
                                            logger.warning(f"Base pair price (cached aerodrome): {price}")
                                            return price
                        except Exception as e:
                            logger.debug(f"Cached aerodrome method failed: {e}")
                    
                    elif cached_method == 'v3_quoter':
                        try:
                            for fee in [500, 3000, 10000]:
                                q = base_client.v3_quote_amount_out(BASE_WETH_ADDRESSES['base'], token_contract, amount_in, fee=fee)
                                if q and q > 0:
                                    token_dec = base_client.get_token_decimals(token_contract)
                                    price = (0.001) / (q / (10 ** token_dec))
                                    logger.warning(f"Base v3 price (cached, fee={fee}): {price}")
                                    return price
                        except Exception as e:
                            logger.debug(f"Cached v3 method failed: {e}")
                    
                    # If no cache or cached method failed, try all methods
                    # Pair-based primary pricing (DexScreener resolution)
                    import requests
                    ds_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}"
                    try:
                        r = requests.get(ds_url, timeout=8)
                        if r.ok:
                            data = r.json() or {}
                            pairs = data.get('pairs') or []
                            base_pairs = [p for p in pairs if p.get('chainId') == 'base']
                            # Prefer Aerodrome WETH quote, else Uniswap WETH quote
                            preferred = None
                            for dex in ('aerodrome', 'uniswap'):
                                cand = [p for p in base_pairs if (p.get('dexId') == dex and p.get('quoteToken',{}).get('symbol') == 'WETH')]
                                if cand:
                                    # pick highest liquidity
                                    preferred = sorted(cand, key=lambda p: (p.get('liquidity',{}).get('usd') or 0), reverse=True)[0]
                                    break
                            if preferred and preferred.get('pairAddress'):
                                pair_addr = preferred['pairAddress']
                                out = base_client.pair_get_amount_out(pair_addr, amount_in, BASE_WETH_ADDRESSES['base'])
                                if out and out > 0:
                                    token_dec = base_client.get_token_decimals(token_contract)
                                    price = (0.001) / (out / (10 ** token_dec))
                                    logger.warning(f"Base pair price (dex={preferred.get('dexId')}): {price}")
                                    # Cache successful method
                                    self._cache_successful_method(chain, token_contract, 'aerodrome_pair')
                                    return price
                    except Exception as ext:
                        logger.debug(f"DexScreener pair resolution failed: {ext}")

                    # Router/Quoter fallbacks
                    logger.debug(f"Pair pricing failed, trying router/quoter fallbacks for {token_contract}")
                    out = base_client.v2_get_amounts_out(BASE_WETH_ADDRESSES['base'], token_contract, amount_in)
                    if out and len(out) >= 2 and out[-1] > 0:
                        token_dec = base_client.get_token_decimals(token_contract)
                        price = (0.001) / (out[-1] / (10 ** token_dec))
                        logger.warning(f"Base v2 router price: {price}")
                        self._cache_successful_method(chain, token_contract, 'v2_router')
                        return price
                    
                    for fee in [500, 3000, 10000]:
                        q = base_client.v3_quote_amount_out(BASE_WETH_ADDRESSES['base'], token_contract, amount_in, fee=fee)
                        if q and q > 0:
                            token_dec = base_client.get_token_decimals(token_contract)
                            price = (0.001) / (q / (10 ** token_dec))
                            logger.warning(f"Base v3 price (fee={fee}): {price}")
                            self._cache_successful_method(chain, token_contract, 'v3_quoter')
                            return price
                except Exception as e:
                    logger.debug(f"Base pricing error: {e}")
                return None
            elif chain == 'bsc':
                bsc_client = self._get_bsc_client()
                if not bsc_client:
                    return None
                logger.warning(f"Getting price for BSC token: {token_contract}")
                try:
                    import requests
                    amount_in = int(0.01 * 1e18)  # 0.01 WBNB
                    
                    # Try DexScreener pair pricing first
                    try:
                        r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}", timeout=8)
                        if r.ok:
                            data = r.json() or {}
                            pairs = data.get('pairs') or []
                            bsc_pairs = [p for p in pairs if p.get('chainId') == 'bsc']
                            # Prefer WBNB quote pairs by highest liquidity
                            cand = [p for p in bsc_pairs if (p.get('quoteToken',{}).get('symbol') in ('WBNB','BNB'))]
                            if cand:
                                cand.sort(key=lambda p: (p.get('liquidity',{}).get('usd') or 0), reverse=True)
                                chosen = cand[0]
                                pair_addr = chosen.get('pairAddress')
                                dex_id = chosen.get('dexId','')
                                logger.warning(f"BSC pricing via pair: dex={dex_id} pair={pair_addr}")
                                
                                # Try v2 pair direct formula if not v3
                                if pair_addr and ('v3' not in (dex_id or '').lower()):
                                    out = bsc_client.v2_pair_get_amount_out(pair_addr, amount_in, bsc_client.weth_address)
                                    if out and out > 0:
                                        token_dec = bsc_client.get_token_decimals(token_contract)
                                        price = (0.01) / (out / (10 ** token_dec))
                                        logger.warning(f"BSC v2 pair price: {price}")
                                        return price
                                # Try v3 pair direct formula if v3
                                elif pair_addr and ('v3' in (dex_id or '').lower()):
                                    # For v3 pairs, try v3 quoter with different fees
                                    v3_success = False
                                    for fee in [10000, 3000, 500, 2500]:  # Same order as trading system
                                        out = bsc_client.v3_quote_amount_out(bsc_client.weth_address, token_contract, amount_in, fee=fee)
                                        if out and out > 0:
                                            token_dec = bsc_client.get_token_decimals(token_contract)
                                            price = (0.01) / (out / (10 ** token_dec))
                                            logger.warning(f"BSC v3 pair price (fee={fee}): {price}")
                                            return price
                                        else:
                                            logger.debug(f"BSC v3 quoter failed for fee {fee}, trying next fee")
                                    # If all V3 fees failed, don't return - continue to V2 router fallback
                                    if not v3_success:
                                        logger.debug(f"All V3 quoter attempts failed for {token_contract}, will try V2 router fallback")
                    except Exception as e:
                        logger.debug(f"BSC DexScreener pricing error: {e}")
                    
                    # Fallback: v2 router path
                    try:
                        out_list = bsc_client.v2_get_amounts_out(bsc_client.weth_address, token_contract, amount_in)
                        if out_list and len(out_list) >= 2 and out_list[-1] > 0:
                            token_dec = bsc_client.get_token_decimals(token_contract)
                            price = (0.01) / (out_list[-1] / (10 ** token_dec))
                            logger.warning(f"BSC v2 router price: {price}")
                            return price
                    except Exception as e:
                        logger.debug(f"BSC v2 router pricing error: {e}")
                    
                    # Fallback: v3 quoter if configured
                    try:
                        for fee in [10000, 3000, 500, 2500]:  # Same order as trading system
                            out = bsc_client.v3_quote_amount_out(bsc_client.weth_address, token_contract, amount_in, fee=fee)
                            if out and out > 0:
                                token_dec = bsc_client.get_token_decimals(token_contract)
                                price = (0.01) / (out / (10 ** token_dec))
                                logger.warning(f"BSC v3 price (fee={fee}): {price}")
                                return price
                    except Exception as e:
                        logger.debug(f"BSC v3 quoter pricing error: {e}")
                        
                except Exception as e:
                    logger.debug(f"BSC pricing error: {e}")
                return None
            elif chain == 'ethereum':
                eth_client = self._get_eth_client()
                if not eth_client:
                    return None
                # Use Ethereum Uniswap client for pricing
                logger.warning(f"Getting price for Ethereum token: {token_contract}")
                try:
                    amount_in = int(0.001 * 1e18)  # 0.001 WETH
                    # Try v2 first
                    amounts = eth_client.v2_get_amounts_out(ETH_WETH_ADDRESS, token_contract, amount_in)
                    if amounts and len(amounts) >= 2:
                        out = amounts[-1]
                        token_dec = eth_client.get_token_decimals(token_contract)
                        price = (0.001) / (out / (10 ** token_dec))
                        return price
                    # Fallback to v3
                    if hasattr(eth_client, 'v3_quote_amount_out'):
                        for fee in [500, 3000, 10000]:
                            try:
                                out = eth_client.v3_quote_amount_out(ETH_WETH_ADDRESS, token_contract, amount_in, fee=fee)
                                if out and out > 0:
                                    token_dec = eth_client.get_token_decimals(token_contract)
                                    price = (0.001) / (out / (10 ** token_dec))
                                    return price
                            except Exception:
                                continue
                except Exception as e:
                    logger.debug(f"Ethereum pricing error: {e}")
                return None
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching price for {ticker or token_contract} on {chain}: {e}")
            return None

    async def _get_sol_usd_price(self) -> Optional[float]:
        """Fetch SOL/USD and cache briefly to align Solana targets in SOL."""
        try:
            now = datetime.now(timezone.utc)
            if self._sol_usd_price is not None and self._sol_usd_time is not None:
                if (now - self._sol_usd_time) <= timedelta(seconds=self._sol_cache_ttl):
                    return self._sol_usd_price
            sol_mint = self.jupiter_client.get_sol_mint_address()
            sol_info = await self.jupiter_client.get_token_price(sol_mint)
            if sol_info and sol_info.get('price'):
                self._sol_usd_price = float(sol_info['price'])
                self._sol_usd_time = now
                logger.warning(f"Refreshed SOL/USD: {self._sol_usd_price}")
                return self._sol_usd_price
            return None
        except Exception as e:
            logger.warning(f"Failed to refresh SOL/USD: {e}")
            return None
    
    async def _execute_exit(self, position: Dict[str, Any], quantity: float, price: Decimal, rule: Dict[str, Any]):
        """Execute a position exit"""
        try:
            # This would integrate with the actual trading execution
            # For now, just log the exit
            logger.info(f"🚪 EXIT: {quantity} tokens at ${price} (rule: {rule})")
            
            # Update position in database
            exit_data = {
                'quantity': quantity,
                'price_usd': float(price),
                'amount_usd': quantity * float(price),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'exit_rule': rule
            }
            
            # Add to exits array
            await self._add_position_exit(position['id'], exit_data)
            
        except Exception as e:
            logger.error(f"Error executing exit: {e}")
    
    async def _execute_planned_entry(self, position: Dict[str, Any], planned_entry: Dict[str, Any], price: Decimal):
        """Execute a planned dip entry"""
        try:
            amount_usd = planned_entry.get('amount_usd', 0)
            quantity = amount_usd / float(price)
            
            logger.info(f"📈 DIP ENTRY: {quantity} tokens at ${price} (${amount_usd})")
            
            # Update position in database
            entry_data = {
                'quantity': quantity,
                'price_usd': float(price),
                'amount_usd': amount_usd,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'entry_type': 'dip'
            }
            
            # Add to entries array
            await self._add_position_entry(position['id'], entry_data)
            
            # Mark planned entry as executed
            await self._mark_planned_entry_executed(position['id'], planned_entry['id'])
            
        except Exception as e:
            logger.error(f"Error executing planned entry: {e}")
    
    async def _add_position_exit(self, position_id: str, exit_data: Dict[str, Any]):
        """Add exit to position in database using direct client"""
        try:
            # Get current position
            result = self.supabase_manager.client.table('lowcap_positions').select('exits').eq('id', position_id).execute()
            if not result.data:
                logger.error(f"Position {position_id} not found")
                return
            
            current_exits = result.data[0].get('exits', [])
            current_exits.append(exit_data)
            
            # Update the position with new exit
            update_result = self.supabase_manager.client.table('lowcap_positions').update({
                'exits': current_exits
            }).eq('id', position_id).execute()
            
            if update_result.data:
                logger.info(f"Added exit to position {position_id}")
            else:
                logger.error(f"Failed to add exit to position {position_id}")
            
        except Exception as e:
            logger.error(f"Error adding position exit: {e}")
    
    async def _add_position_entry(self, position_id: str, entry_data: Dict[str, Any]):
        """Add entry to position in database using direct client"""
        try:
            # Get current position
            result = self.supabase_manager.client.table('lowcap_positions').select('entries').eq('id', position_id).execute()
            if not result.data:
                logger.error(f"Position {position_id} not found")
                return
            
            current_entries = result.data[0].get('entries', [])
            current_entries.append(entry_data)
            
            # Update the position with new entry
            update_result = self.supabase_manager.client.table('lowcap_positions').update({
                'entries': current_entries
            }).eq('id', position_id).execute()
            
            if update_result.data:
                logger.info(f"Added entry to position {position_id}")
            else:
                logger.error(f"Failed to add entry to position {position_id}")
            
        except Exception as e:
            logger.error(f"Error adding position entry: {e}")
    
    async def _mark_planned_entry_executed(self, position_id: str, planned_entry_id: str):
        """Mark a planned entry as executed"""
        try:
            # This would update the planned_entries array in the database
            # Implementation depends on the exact database schema
            logger.info(f"Marked planned entry {planned_entry_id} as executed")
            
        except Exception as e:
            logger.error(f"Error marking planned entry as executed: {e}")
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary with current values"""
        try:
            # Get all active positions
            positions = await self._get_active_positions()
            
            total_invested = 0
            total_current_value = 0
            position_count = len(positions)
            
            for position in positions:
                entries = position.get('entries', [])
                total_invested += sum(entry.get('amount_usd', 0) for entry in entries)
                
                # Get current price and calculate value
                token_address = position.get('token_address')
                if token_address:
                    price_info = await self.jupiter_client.get_token_price(token_address)
                    if price_info:
                        total_quantity = sum(entry.get('quantity', 0) for entry in entries)
                        current_value = total_quantity * float(price_info['price'])
                        total_current_value += current_value
            
            pnl = total_current_value - total_invested
            pnl_pct = (pnl / total_invested * 100) if total_invested > 0 else 0
            
            return {
                'total_invested': total_invested,
                'total_current_value': total_current_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'position_count': position_count,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {}


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_price_monitor():
        """Test price monitor functionality"""
        try:
            print("📊 Price Monitor Test")
            print("=" * 40)
            
            # This would require actual database and client setup
            print("Price monitor test requires database and client setup")
            print("Run this as part of the main trading system")
            
        except Exception as e:
            print(f"❌ Error testing price monitor: {e}")
    
    # Run test
    asyncio.run(test_price_monitor())
