#!/usr/bin/env python3
"""
Position Monitor

Monitors active positions using price data from database and executes planned entries/exits.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PositionMonitor:
    """
    Position monitoring system using database price data
    
    Monitors active positions and executes planned entries/exits when price targets are reached.
    """
    
    def __init__(self, supabase_manager, trader=None):
        """
        Initialize position monitor
        
        Args:
            supabase_manager: Database manager for position and price queries
            trader: Trader instance for executing entries/exits
        """
        self.supabase_manager = supabase_manager
        self.trader = trader
        self.monitoring = False
        self.monitor_task = None
        
        # Handle both DirectTableCommunicator and SupabaseManager
        if hasattr(supabase_manager, 'db_manager'):
            self.client = supabase_manager.db_manager.client
        else:
            self.client = supabase_manager.client
        
        logger.info("Position monitor initialized")
    
    async def start_monitoring(self, check_interval: int = 30):
        """
        Start position monitoring loop
        
        Args:
            check_interval: Seconds between position checks
        """
        if self.monitoring:
            logger.warning("Position monitoring already running")
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop(check_interval))
        logger.info(f"Position monitoring started (interval: {check_interval}s)")
    
    async def stop_monitoring(self):
        """Stop position monitoring"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Position monitoring stopped")
    
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
            
            # Check each position
            for i, position in enumerate(active_positions):
                await self._check_position(position)
                # Add delay between checks to avoid overwhelming the system
                if i < len(active_positions) - 1:
                    await asyncio.sleep(3)
                
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
    
    async def _get_active_positions(self) -> List[Dict[str, Any]]:
        """Get active positions from database"""
        try:
            result = self.client.table('lowcap_positions').select('*').eq('status', 'active').order('created_at', desc=True).execute()
            
            if result.data:
                logger.info(f"📊 Found {len(result.data)} active positions")
                return result.data
            else:
                return []
            
        except Exception as e:
            logger.warning(f"Error getting active positions: {e}")
            return []
    
    async def _check_position(self, position: Dict[str, Any]):
        """Check a single position for exit/entry conditions"""
        try:
            token_contract = position.get('token_contract')
            token_chain = (position.get('token_chain') or '').lower()
            if not token_contract or not token_chain:
                return

            # Get current price from database
            current_price = await self._get_current_price_from_db(token_contract, token_chain)
            if current_price is None:
                logger.warning(f"Could not get price for {token_contract} on {token_chain}")
                return

            logger.info(f"Price check: {current_price} for {token_contract} on {token_chain}")

            # Check planned entries and exits
            await self._check_planned_entries(position, float(current_price))
            await self._check_exits(position, float(current_price))
            
        except Exception as e:
            logger.error(f"Error checking position {position.get('id', 'unknown')}: {e}")
    
    async def _get_current_price_from_db(self, token_contract: str, chain: str) -> Optional[float]:
        """Get current price from database"""
        try:
            # Get latest price from database
            result = self.client.table('lowcap_price_data_1m').select(
                'price_usd', 'price_native', 'quote_token'
            ).eq('token_contract', token_contract).eq('chain', chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if result.data:
                price_data = result.data[0]
                
                # Always return price_native for consistency with entry/exit calculations
                return float(price_data.get('price_native', 0))
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting price from database: {e}")
            return None
    
    async def _check_exits(self, position: Dict[str, Any], current_price: float):
        """Execute pending exits when price target reached"""
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
                                await asyncio.sleep(5)  # Cooldown between exits
                            else:
                                logger.warning(f"Exit {exit_number} execution failed or not confirmed")
                                await asyncio.sleep(10)
                        except Exception as exec_err:
                            logger.error(f"Error executing trader exit: {exec_err}")
                            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error checking exits: {e}")
    
    async def _check_planned_entries(self, position: Dict[str, Any], current_price: float):
        """Execute planned dip entries when targets hit"""
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
                                await asyncio.sleep(5)  # Cooldown between entries
                            else:
                                logger.warning(f"Entry {entry_number} execution failed or not confirmed")
                                await asyncio.sleep(10)
                        except Exception as exec_err:
                            logger.error(f"Error executing trader entry: {exec_err}")
                            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error checking planned entries: {e}")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_position_monitor():
        """Test position monitor functionality"""
        try:
            print("📊 Position Monitor Test")
            print("=" * 40)
            
            # This would require actual database and trader setup
            print("Position monitor test requires database and trader setup")
            print("Run this as part of the main trading system")
            
        except Exception as e:
            print(f"❌ Error testing position monitor: {e}")
    
    # Run test
    asyncio.run(test_position_monitor())
