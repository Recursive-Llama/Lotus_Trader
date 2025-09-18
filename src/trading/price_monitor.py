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
        # Support both BASE_RPC_URL and legacy RPC_URL for Base
        self.base_rpc_url = os.getenv('BASE_RPC_URL') or os.getenv('RPC_URL')
        self.eth_rpc_url = os.getenv('ETH_RPC_URL')
        
        # Log client initialization status
        logger.info(f"Price monitor clients: Jupiter=✅, Base={'✅' if self.base_rpc_url else '❌'}, Ethereum={'✅' if self.eth_rpc_url else '❌'}")
        self.monitoring = False
        self.monitor_task = None
        # Cached SOL/USD for SOL-denominated comparisons
        self._sol_usd_price: Optional[float] = None
        self._sol_usd_time: Optional[datetime] = None
        self._sol_cache_ttl: int = 60  # seconds
        
        logger.info("Price monitor initialized")
    
    def _get_base_client(self):
        """Lazy initialization of Base client"""
        if self.base_client is None:
            try:
                if self.base_rpc_url:
                    self.base_client = EvmUniswapClient(chain='base', rpc_url=self.base_rpc_url)
                else:
                    self.base_client = EvmUniswapClient(chain='base')
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
            for exit_order in exits:
                if exit_order.get('status') == 'pending':
                    target_price = float(exit_order.get('price', 0))
                    exit_number = exit_order.get('exit_number')
                    if current_price >= target_price and self.trader:
                        logger.info(f"Triggering exit {exit_number} for {position.get('token_ticker')} at {current_price:.6f} (target {target_price:.6f})")
                        try:
                            await self.trader._execute_exit(position_id, exit_number)
                        except Exception as exec_err:
                            logger.error(f"Error executing trader exit: {exec_err}")
        except Exception as e:
            logger.error(f"Error checking exits: {e}")
    
    async def _check_planned_entries(self, position: Dict[str, Any], current_price: float):
        """Execute planned dip entries when targets hit using Trader if available"""
        try:
            entries = position.get('entries', [])
            if not entries:
                return
            position_id = position.get('id')
            for entry in entries:
                if entry.get('status') == 'pending':
                    target_price = float(entry.get('price', 0))
                    entry_number = entry.get('entry_number')
                    if current_price <= target_price and self.trader:
                        logger.info(f"Triggering planned entry {entry_number} at {current_price:.6f} (target {target_price:.6f})")
                        try:
                            await self.trader._execute_entry(position_id, entry_number)
                        except Exception as exec_err:
                            logger.error(f"Error executing trader entry: {exec_err}")
        except Exception as e:
            logger.error(f"Error checking planned entries: {e}")

    async def _get_current_price_by_chain(self, token_contract: str, chain: str, ticker: Optional[str] = None) -> Optional[float]:
        """Fetch current price depending on chain"""
        try:
            if chain == 'solana':
                # Use simple price method for monitoring
                logger.warning(f"Getting price for Solana token: {token_contract}")
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
                # Use Base Uniswap client for pricing
                logger.warning(f"Getting price for Base token: {token_contract}")
                try:
                    amount_in = int(0.001 * 1e18)  # 0.001 WETH
                    # Try v2 first
                    amounts = base_client.v2_get_amounts_out(BASE_WETH_ADDRESSES['base'], token_contract, amount_in)
                    if amounts and len(amounts) >= 2:
                        out = amounts[-1]
                        token_dec = base_client.get_token_decimals(token_contract)
                        price = (0.001) / (out / (10 ** token_dec))
                        return price
                    # Try larger input on v2 to avoid zero rounding
                    amount_in_large = int(0.01 * 1e18)  # 0.01 WETH
                    amounts = base_client.v2_get_amounts_out(BASE_WETH_ADDRESSES['base'], token_contract, amount_in_large)
                    if amounts and len(amounts) >= 2 and amounts[-1] > 0:
                        out = amounts[-1]
                        token_dec = base_client.get_token_decimals(token_contract)
                        price = (0.01) / (out / (10 ** token_dec))
                        return price
                    # Fallback to v3
                    for fee in [500, 3000, 10000]:
                        try:
                            out = base_client.v3_quote_amount_out(BASE_WETH_ADDRESSES['base'], token_contract, amount_in, fee=fee)
                            if out and out > 0:
                                token_dec = base_client.get_token_decimals(token_contract)
                                price = (0.001) / (out / (10 ** token_dec))
                                return price
                        except Exception:
                            continue
                    # Try larger input on v3
                    for fee in [500, 3000, 10000]:
                        try:
                            out = base_client.v3_quote_amount_out(BASE_WETH_ADDRESSES['base'], token_contract, amount_in_large, fee=fee)
                            if out and out > 0:
                                token_dec = base_client.get_token_decimals(token_contract)
                                price = (0.01) / (out / (10 ** token_dec))
                                return price
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug(f"Base pricing error: {e}")
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
