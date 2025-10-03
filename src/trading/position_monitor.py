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

            # Check planned entries, exits, trend entries, and trend exits
            await self._check_planned_entries(position, float(current_price))
            await self._check_exits(position, float(current_price))
            await self._check_trend_entries(position, float(current_price))
            await self._check_trend_exits(position, float(current_price))
            
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
                
                native = float(price_data.get('price_native', 0) or 0)
                if native > 0:
                    return native
                # Fallback: compute native from USD when native is zero (tiny price precision)
                usd = float(price_data.get('price_usd', 0) or 0)
                if usd > 0:
                    # Fetch latest WETH USD price
                    weth_row = self.client.table('lowcap_price_data_1m').select('price_usd').eq('token_contract', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2').eq('chain', 'ethereum').order('timestamp', desc=True).limit(1).execute()
                    if weth_row.data:
                        weth_usd = float(weth_row.data[0].get('price_usd', 0) or 0)
                        if weth_usd > 0:
                            return usd / weth_usd
                return None
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

    async def _check_trend_entries(self, position: Dict[str, Any], current_price: float):
        """Execute pending trend entries (dip buys) when price targets hit"""
        try:
            trend_entries = position.get('trend_entries', [])
            if not trend_entries:
                return
            
            position_id = position.get('id')
            token_ticker = position.get('token_ticker', 'Unknown')
            
            # Process trend entries sequentially to avoid nonce conflicts
            for trend_entry in trend_entries:
                if trend_entry.get('status') == 'pending':
                    target_price = float(trend_entry.get('entry_price', 0))
                    trend_entry_number = trend_entry.get('trend_entry_number')
                    batch_id = trend_entry.get('batch_id')
                    allocated_native = float(trend_entry.get('allocated_native', 0))
                    
                    # Check if current price is at or below the dip target price
                    if current_price <= target_price and self.trader:
                        logger.info(f"🎯 Triggering trend entry {trend_entry_number} for {token_ticker} at {current_price:.6f} (target {target_price:.6f})")
                        logger.info(f"   Batch: {batch_id}, Amount: {allocated_native:.6f}")
                        
                        try:
                            # Execute trend entry
                            success = await self._execute_trend_entry(
                                position_id=position_id,
                                batch_id=batch_id,
                                trend_entry_number=trend_entry_number,
                                allocated_native=allocated_native,
                                target_price=target_price,
                                current_price=current_price
                            )
                            
                            if success:
                                logger.info(f"✅ Trend entry {trend_entry_number} executed successfully")
                                await asyncio.sleep(5)  # Cooldown between entries
                            else:
                                logger.warning(f"❌ Trend entry {trend_entry_number} execution failed")
                                await asyncio.sleep(10)
                                
                        except Exception as exec_err:
                            logger.error(f"Error executing trend entry: {exec_err}")
                            await asyncio.sleep(10)
                            
        except Exception as e:
            logger.error(f"Error checking trend entries: {e}")

    async def _execute_trend_entry(self, position_id: str, batch_id: str, trend_entry_number: int, 
                                 allocated_native: float, target_price: float, current_price: float) -> bool:
        """Execute a trend entry (dip buy)"""
        try:
            if not self.trader:
                logger.error("No trader instance available for trend entry execution")
                return False
            
            # Get position data
            position = self.trader.repo.get_position(position_id)
            if not position:
                logger.error(f"Position {position_id} not found")
                return False
            
            token_contract = position.get('token_contract')
            token_chain = (position.get('token_chain') or '').lower()
            token_ticker = position.get('token_ticker', 'Unknown')
            
            if not token_contract or not token_chain:
                logger.error("Missing token contract or chain for trend entry")
                return False
            
            # Calculate tokens to buy
            tokens_to_buy = allocated_native / current_price
            
            logger.info(f"Executing trend entry: {allocated_native:.6f} native → {tokens_to_buy:.6f} {token_ticker}")
            
            # Execute the buy transaction
            tx_hash = None
            if token_chain == 'bsc' and hasattr(self.trader, 'bsc_executor') and self.trader.bsc_executor:
                tx_hash = self.trader.bsc_executor.execute_buy(token_contract, allocated_native)
            elif token_chain == 'base' and hasattr(self.trader, 'base_executor') and self.trader.base_executor:
                tx_hash = self.trader.base_executor.execute_buy(token_contract, allocated_native)
            elif token_chain == 'ethereum' and hasattr(self.trader, 'eth_executor') and self.trader.eth_executor:
                tx_hash = self.trader.eth_executor.execute_buy(token_contract, allocated_native)
            elif token_chain == 'solana' and hasattr(self.trader, 'sol_executor') and self.trader.sol_executor:
                tx_hash = await self.trader.sol_executor.execute_buy(token_contract, allocated_native)
            
            if not tx_hash:
                logger.error(f"Failed to execute trend entry buy for {token_ticker}")
                # Mark trend entry as failed to prevent endless retries
                try:
                    self.trader.repo.mark_trend_entry_failed(position_id, batch_id, trend_entry_number, reason='execution_failed')
                except Exception:
                    pass
                return False
            
            logger.info(f"Trend entry buy executed: {tx_hash}")
            
            # Mark trend entry as executed in database
            success = self.trader.repo.mark_trend_entry_executed(
                position_id=position_id,
                batch_id=batch_id,
                trend_entry_number=trend_entry_number,
                tx_hash=tx_hash,
                cost_native=allocated_native,
                tokens_bought=tokens_to_buy
            )
            
            if not success:
                logger.error("Failed to mark trend entry as executed in database")
                return False
            
            # Calculate dip percentage for notification
            # Get the source exit price that funded this trend entry batch
            source_exit_price = 0.0
            trend_entries = position.get('trend_entries', [])
            for te in trend_entries:
                if (te.get('batch_id') == batch_id and 
                    te.get('trend_entry_number') == trend_entry_number):
                    source_exit_id = te.get('source_exit_id')
                    if source_exit_id:
                        # Find the source exit price
                        exits = position.get('exits', [])
                        for exit in exits:
                            if str(exit.get('exit_number')) == str(source_exit_id):
                                source_exit_price = float(exit.get('price', 0))
                                break
                    break
            
            # Calculate dip percentage from source exit price
            if source_exit_price > 0:
                dip_pct = ((current_price - source_exit_price) / source_exit_price) * 100
            else:
                # Fallback to avg_entry_price if source exit not found
                avg_entry_price = position.get('avg_entry_price', 0)
                if avg_entry_price > 0:
                    dip_pct = ((current_price - avg_entry_price) / avg_entry_price) * 100
                else:
                    dip_pct = 0.0
            
            # Ensure trend exits for this batch exist only after first entry executes
            try:
                from intelligence.trader_lowcap.entry_exit_planner import EntryExitPlanner
                existing_trend_exits = position.get('trend_exits', []) or []
                has_batch_exits = any(x.get('batch_id') == batch_id for x in existing_trend_exits)
                if not has_batch_exits and source_exit_price > 0:
                    new_trend_exits = EntryExitPlanner.build_trend_exits_for_batch(
                        exit_price=source_exit_price,
                        batch_id=batch_id,
                    )
                    existing_trend_exits.extend(new_trend_exits)
                    self.trader.repo.update_trend_exits(position_id, existing_trend_exits)
                    logger.info(f"Created {len(new_trend_exits)} trend exits for batch {batch_id} after first entry execution")
            except Exception as e:
                logger.error(f"Error ensuring trend exits for batch {batch_id}: {e}")

            # Send trend entry notification via service notifier if available
            try:
                if getattr(self.trader, "_service", None) and getattr(self.trader, "telegram_notifier", None):
                    await self.trader._service.send_trend_entry_notification(
                        position_id=position_id,
                        entry_number=trend_entry_number,
                        tx_hash=tx_hash,
                        amount_native=allocated_native,
                        price=current_price,
                        dip_pct=dip_pct,
                        batch_id=batch_id,
                    )
            except Exception:
                pass
            
            # Update position totals
            await self.trader._update_tokens_bought(position_id, tokens_to_buy)
            await self.trader._update_total_investment_native(position_id, allocated_native)
            await self.trader._update_position_pnl(position_id)
            
            logger.info(f"✅ Trend entry {trend_entry_number} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error executing trend entry: {e}")
            return False

    async def _check_trend_exits(self, position: Dict[str, Any], current_price: float):
        """Execute pending trend exits when price targets hit"""
        try:
            trend_exits = position.get('trend_exits', [])
            if not trend_exits:
                return
            
            position_id = position.get('id')
            token_ticker = position.get('token_ticker', 'Unknown')
            
            # Process trend exits sequentially to avoid nonce conflicts
            for trend_exit in trend_exits:
                if trend_exit.get('status') == 'pending':
                    # Trend exits store target under 'price'
                    target_price = float(trend_exit.get('price', 0))
                    trend_exit_number = trend_exit.get('trend_exit_number')
                    batch_id = trend_exit.get('batch_id')
                    
                    # Check if current price is at or above the exit target price
                    if current_price >= target_price and self.trader:
                        logger.info(f"🎯 Triggering trend exit {trend_exit_number} for {token_ticker} at {current_price:.6f} (target {target_price:.6f})")
                        logger.info(f"   Batch: {batch_id}")
                        
                        try:
                            # Execute trend exit
                            success = await self._execute_trend_exit(
                                position_id=position_id,
                                batch_id=batch_id,
                                trend_exit_number=trend_exit_number,
                                target_price=target_price,
                                current_price=current_price
                            )
                            
                            if success:
                                logger.info(f"✅ Trend exit {trend_exit_number} executed successfully")
                                await asyncio.sleep(5)  # Cooldown between exits
                            else:
                                logger.warning(f"❌ Trend exit {trend_exit_number} execution failed")
                                await asyncio.sleep(10)
                                
                        except Exception as exec_err:
                            logger.error(f"Error executing trend exit: {exec_err}")
                            await asyncio.sleep(10)
                            
        except Exception as e:
            logger.error(f"Error checking trend exits: {e}")

    async def _execute_trend_exit(self, position_id: str, batch_id: str, trend_exit_number: int, 
                                target_price: float, current_price: float) -> bool:
        """Execute a trend exit (sell)"""
        try:
            if not self.trader:
                logger.error("No trader instance available for trend exit execution")
                return False
            
            # Get position data
            position = self.trader.repo.get_position(position_id)
            if not position:
                logger.error(f"Position {position_id} not found")
                return False
            
            token_contract = position.get('token_contract')
            token_chain = (position.get('token_chain') or '').lower()
            token_ticker = position.get('token_ticker', 'Unknown')
            
            if not token_contract or not token_chain:
                logger.error("Missing token contract or chain for trend exit")
                return False
            
            # Find the specific trend exit to get exit percentage
            trend_exits = position.get('trend_exits', [])
            trend_exit_data = None
            for te in trend_exits:
                if (te.get('batch_id') == batch_id and 
                    te.get('trend_exit_number') == trend_exit_number and 
                    te.get('status') == 'pending'):
                    trend_exit_data = te
                    break
            
            if not trend_exit_data:
                logger.error(f"Trend exit {trend_exit_number} not found in batch {batch_id}")
                return False
            
            # Calculate tokens to sell from trend entries in the same batch
            trend_entries = position.get('trend_entries', [])
            total_tokens_available = 0
            for te in trend_entries:
                if (te.get('batch_id') == batch_id and 
                    te.get('status') == 'executed'):
                    total_tokens_available += float(te.get('tokens_remaining', te.get('tokens_bought', 0)))
            
            if total_tokens_available <= 0:
                logger.error(f"No tokens available for trend exit in batch {batch_id}")
                return False
            
            # Calculate tokens to sell (use exit_pct from trend exit)
            exit_pct = float(trend_exit_data.get('exit_pct', 100))  # Default to 100% if not specified
            tokens_to_sell = total_tokens_available * (exit_pct / 100)
            
            logger.info(f"Executing trend exit: {tokens_to_sell:.6f} {token_ticker} @ {current_price:.6f}")
            
            # Execute the sell transaction
            tx_hash = None
            if token_chain == 'bsc' and hasattr(self.trader, 'bsc_executor') and self.trader.bsc_executor:
                tx_hash = self.trader.bsc_executor.execute_sell(token_contract, tokens_to_sell)
            elif token_chain == 'base' and hasattr(self.trader, 'base_executor') and self.trader.base_executor:
                tx_hash = self.trader.base_executor.execute_sell(token_contract, tokens_to_sell)
            elif token_chain == 'ethereum' and hasattr(self.trader, 'eth_executor') and self.trader.eth_executor:
                tx_hash = self.trader.eth_executor.execute_sell(token_contract, tokens_to_sell)
            elif token_chain == 'solana' and hasattr(self.trader, 'sol_executor') and self.trader.sol_executor:
                tx_hash = await self.trader.sol_executor.execute_sell(token_contract, tokens_to_sell)
            
            if not tx_hash:
                logger.error(f"Failed to execute trend exit sell for {token_ticker}")
                return False
            
            logger.info(f"Trend exit sell executed: {tx_hash}")
            
            # Calculate native amount received
            native_amount = tokens_to_sell * current_price
            
            # Mark trend exit as executed in database
            success = self.trader.repo.mark_trend_exit_executed(
                position_id=position_id,
                batch_id=batch_id,
                trend_exit_number=trend_exit_number,
                tx_hash=tx_hash,
                tokens_sold=tokens_to_sell,
                native_amount=native_amount
            )
            
            if not success:
                logger.error("Failed to mark trend exit as executed in database")
                return False
            
            # Calculate gain percentage for notification
            # Get average entry price from trend entries in this batch
            total_cost = 0
            total_tokens = 0
            for te in trend_entries:
                if (te.get('batch_id') == batch_id and 
                    te.get('status') == 'executed'):
                    cost = float(te.get('cost_native', 0))
                    tokens = float(te.get('tokens_bought', 0))
                    total_cost += cost
                    total_tokens += tokens
            
            avg_entry_price = total_cost / total_tokens if total_tokens > 0 else 0
            gain_pct = ((current_price - avg_entry_price) / avg_entry_price) * 100 if avg_entry_price > 0 else 0
            
            # Send trend exit notification via service notifier if available
            try:
                if getattr(self.trader, "_service", None) and getattr(self.trader, "telegram_notifier", None):
                    await self.trader._service.send_trend_exit_notification(
                        position_id=position_id,
                        exit_number=trend_exit_number,
                        tx_hash=tx_hash,
                        tokens_sold=tokens_to_sell,
                        sell_price=current_price,
                        gain_pct=gain_pct,
                        batch_id=batch_id,
                        profit_pct=gain_pct,
                        profit_usd=native_amount * 0.0001,
                    )
            except Exception:
                pass
            
            # Update position P&L
            await self.trader._update_position_pnl(position_id)
            
            logger.info(f"✅ Trend exit {trend_exit_number} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error executing trend exit: {e}")
            return False


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
