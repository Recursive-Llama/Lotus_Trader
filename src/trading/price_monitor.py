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

from .jupiter_client import JupiterClient
from .wallet_manager import WalletManager

logger = logging.getLogger(__name__)


class PriceMonitor:
    """
    Price monitoring system for active positions
    
    Monitors:
    - Current position prices for exit conditions
    - Planned entry prices for dip entries
    - Portfolio exposure and risk management
    """
    
    def __init__(self, supabase_manager, jupiter_client: JupiterClient, wallet_manager: WalletManager):
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
        self.monitoring = False
        self.monitor_task = None
        
        logger.info("Price monitor initialized")
    
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
            
            for position in active_positions:
                await self._check_position(position)
                
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
            token_address = position.get('token_address')
            if not token_address:
                return
            
            # Get current price
            price_info = await self.jupiter_client.get_token_price(token_address)
            if not price_info:
                logger.warning(f"Could not get price for {token_address}")
                return
            
            current_price = price_info['price']
            
            # Check exit conditions
            await self._check_exit_conditions(position, current_price)
            
            # Check planned entries
            await self._check_planned_entries(position, current_price)
            
        except Exception as e:
            logger.error(f"Error checking position {position.get('id', 'unknown')}: {e}")
    
    async def _check_exit_conditions(self, position: Dict[str, Any], current_price: Decimal):
        """Check if position should be exited based on current price"""
        try:
            entries = position.get('entries', [])
            exits = position.get('exits', [])
            exit_rules = position.get('exit_rules', [])
            
            if not entries or not exit_rules:
                return
            
            # Calculate current P&L
            total_invested = sum(entry.get('amount_usd', 0) for entry in entries)
            total_quantity = sum(entry.get('quantity', 0) for entry in entries)
            
            if total_quantity == 0:
                return
            
            current_value = float(total_quantity) * float(current_price)
            pnl_pct = ((current_value - total_invested) / total_invested) * 100
            
            # Check each exit rule
            for rule in exit_rules:
                exit_price = rule.get('exit_price')
                exit_pct = rule.get('exit_pct', 30)  # Default 30% of remaining
                gain_threshold = rule.get('gain_threshold', 100)  # Default 100% gain
                
                if pnl_pct >= gain_threshold:
                    # Calculate remaining quantity (subtract already exited)
                    remaining_quantity = total_quantity
                    for exit in exits:
                        remaining_quantity -= exit.get('quantity', 0)
                    
                    if remaining_quantity > 0:
                        # Execute exit
                        exit_quantity = remaining_quantity * (exit_pct / 100)
                        await self._execute_exit(position, exit_quantity, current_price, rule)
                        
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
    
    async def _check_planned_entries(self, position: Dict[str, Any], current_price: Decimal):
        """Check if planned dip entries should be executed"""
        try:
            entries = position.get('entries', [])
            planned_entries = position.get('planned_entries', [])
            
            if not planned_entries:
                return
            
            # Get the first entry price as reference
            if not entries:
                return
            
            first_entry_price = entries[0].get('price_usd', 0)
            if first_entry_price == 0:
                return
            
            # Check each planned entry
            for planned_entry in planned_entries:
                if planned_entry.get('executed', False):
                    continue
                
                dip_threshold = planned_entry.get('dip_threshold', 30)  # Default -30%
                entry_amount = planned_entry.get('amount_usd', 0)
                
                # Calculate target price
                target_price = first_entry_price * (1 - dip_threshold / 100)
                
                if current_price <= target_price:
                    # Execute planned entry
                    await self._execute_planned_entry(position, planned_entry, current_price)
                    
        except Exception as e:
            logger.error(f"Error checking planned entries: {e}")
    
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
