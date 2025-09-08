"""
Order Manager - Intelligent order execution with condition monitoring

This component manages intelligent order execution by monitoring entry conditions
and placing orders only when conditions are met, rather than blindly executing.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class OrderManager:
    """Manages intelligent order execution with condition monitoring"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.active_orders = {}  # Track active orders
        self.condition_monitors = {}  # Track condition monitoring
        
    async def monitor_entry_conditions(self, trading_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor market conditions for order entry
        
        Args:
            trading_plan: Trading plan with entry conditions from Decision Maker
            
        Returns:
            Dict with condition status and readiness
        """
        try:
            # Extract entry conditions from trading plan
            entry_conditions = trading_plan.get('entry_conditions', {})
            symbol = trading_plan.get('symbol', '')
            timeframe = trading_plan.get('timeframe', '1h')
            
            if not entry_conditions:
                return {
                    'status': 'error',
                    'message': 'No entry conditions found in trading plan',
                    'ready': False
                }
            
            # Parse different types of entry conditions
            condition_status = await self._parse_entry_conditions(entry_conditions, symbol, timeframe)
            
            # Create condition monitoring strand
            await self._publish_condition_monitoring_strand(trading_plan, condition_status)
            
            return {
                'status': 'monitoring',
                'conditions': condition_status,
                'ready': condition_status.get('all_conditions_met', False),
                'symbol': symbol,
                'timeframe': timeframe
            }
            
        except Exception as e:
            logger.error(f"Error monitoring entry conditions: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'ready': False
            }
    
    async def place_order_when_ready(self, trading_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place order when entry conditions are met
        
        Args:
            trading_plan: Trading plan with entry conditions and order details
            
        Returns:
            Dict with order execution result
        """
        try:
            # Check if entry conditions are satisfied
            condition_check = await self.monitor_entry_conditions(trading_plan)
            
            if not condition_check.get('ready', False):
                return {
                    'status': 'waiting',
                    'message': 'Entry conditions not yet met',
                    'order_placed': False
                }
            
            # Extract order details from trading plan
            order_details = trading_plan.get('order_details', {})
            symbol = trading_plan.get('symbol', '')
            
            if not order_details:
                return {
                    'status': 'error',
                    'message': 'No order details found in trading plan',
                    'order_placed': False
                }
            
            # Place order (this will be connected to Hyperliquid in Phase 2)
            order_result = await self._place_order_internal(order_details, symbol)
            
            # Track order in active orders
            if order_result.get('order_placed', False):
                order_id = order_result.get('order_id', '')
                self.active_orders[order_id] = {
                    'trading_plan': trading_plan,
                    'order_details': order_details,
                    'placed_at': datetime.now(),
                    'status': 'pending'
                }
            
            # Create order placement strand
            await self._publish_order_placement_strand(trading_plan, order_result)
            
            return order_result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'order_placed': False
            }
    
    async def track_order_lifecycle(self, order_id: str) -> Dict[str, Any]:
        """
        Track order from placement to completion
        
        Args:
            order_id: ID of the order to track
            
        Returns:
            Dict with order lifecycle status
        """
        try:
            if order_id not in self.active_orders:
                return {
                    'status': 'error',
                    'message': f'Order {order_id} not found in active orders',
                    'order_status': 'unknown'
                }
            
            order_info = self.active_orders[order_id]
            
            # Get order status (this will be connected to Hyperliquid in Phase 2)
            order_status = await self._get_order_status_internal(order_id)
            
            # Update order info
            order_info['status'] = order_status.get('status', 'unknown')
            order_info['last_updated'] = datetime.now()
            
            # Handle different order statuses
            if order_status.get('status') == 'filled':
                await self._handle_order_filled(order_id, order_status)
            elif order_status.get('status') == 'cancelled':
                await self._handle_order_cancelled(order_id, order_status)
            elif order_status.get('status') == 'partial_fill':
                await self._handle_partial_fill(order_id, order_status)
            
            # Create order tracking strand
            await self._publish_order_tracking_strand(order_id, order_status)
            
            return {
                'status': 'tracking',
                'order_id': order_id,
                'order_status': order_status.get('status', 'unknown'),
                'order_info': order_info,
                'tracking_data': order_status
            }
            
        except Exception as e:
            logger.error(f"Error tracking order lifecycle: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'order_status': 'error'
            }
    
    async def _parse_entry_conditions(self, entry_conditions: Dict[str, Any], symbol: str, timeframe: str) -> Dict[str, Any]:
        """Parse and evaluate entry conditions"""
        condition_results = {}
        all_conditions_met = True
        
        for condition_type, condition_data in entry_conditions.items():
            if condition_type == 'price_breakout':
                # Example: "breakout_above_30000"
                threshold = condition_data.get('threshold', 0)
                direction = condition_data.get('direction', 'above')
                
                # Get current price (this will be connected to real market data)
                current_price = await self._get_current_price(symbol)
                
                condition_met = False
                if direction == 'above' and current_price > threshold:
                    condition_met = True
                elif direction == 'below' and current_price < threshold:
                    condition_met = True
                
                condition_results[condition_type] = {
                    'met': condition_met,
                    'current_price': current_price,
                    'threshold': threshold,
                    'direction': direction
                }
                
                if not condition_met:
                    all_conditions_met = False
            
            elif condition_type == 'volume_spike':
                # Example: volume above 2x average
                multiplier = condition_data.get('multiplier', 2.0)
                
                # Get current volume (this will be connected to real market data)
                current_volume = await self._get_current_volume(symbol)
                avg_volume = await self._get_average_volume(symbol, timeframe)
                
                condition_met = current_volume > (avg_volume * multiplier)
                
                condition_results[condition_type] = {
                    'met': condition_met,
                    'current_volume': current_volume,
                    'average_volume': avg_volume,
                    'multiplier': multiplier
                }
                
                if not condition_met:
                    all_conditions_met = False
            
            elif condition_type == 'time_based':
                # Example: wait until specific time
                target_time = condition_data.get('target_time', '')
                
                # Check if target time has been reached
                current_time = datetime.now()
                target_datetime = datetime.fromisoformat(target_time) if target_time else current_time
                
                condition_met = current_time >= target_datetime
                
                condition_results[condition_type] = {
                    'met': condition_met,
                    'current_time': current_time.isoformat(),
                    'target_time': target_time
                }
                
                if not condition_met:
                    all_conditions_met = False
        
        return {
            'all_conditions_met': all_conditions_met,
            'condition_results': condition_results,
            'evaluated_at': datetime.now().isoformat()
        }
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol (placeholder for real market data)"""
        # This will be connected to real market data in Phase 2
        # For now, return a mock price
        mock_prices = {
            'BTC': 30000.0,
            'ETH': 2000.0,
            'SOL': 100.0
        }
        return mock_prices.get(symbol, 100.0)
    
    async def _get_current_volume(self, symbol: str) -> float:
        """Get current volume for symbol (placeholder for real market data)"""
        # This will be connected to real market data in Phase 2
        # For now, return a mock volume
        mock_volumes = {
            'BTC': 1000000.0,
            'ETH': 500000.0,
            'SOL': 200000.0
        }
        return mock_volumes.get(symbol, 100000.0)
    
    async def _get_average_volume(self, symbol: str, timeframe: str) -> float:
        """Get average volume for symbol and timeframe (placeholder for real market data)"""
        # This will be connected to real market data in Phase 2
        # For now, return a mock average volume
        mock_avg_volumes = {
            'BTC': 800000.0,
            'ETH': 400000.0,
            'SOL': 150000.0
        }
        return mock_avg_volumes.get(symbol, 80000.0)
    
    async def _place_order_internal(self, order_details: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Place order internally (placeholder for Hyperliquid integration)"""
        # This will be connected to Hyperliquid in Phase 2
        # For now, simulate order placement
        
        order_id = f"order_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{symbol}"
        
        return {
            'status': 'success',
            'order_placed': True,
            'order_id': order_id,
            'symbol': symbol,
            'order_details': order_details,
            'placed_at': datetime.now().isoformat(),
            'message': 'Order placed successfully (simulated)'
        }
    
    async def _get_order_status_internal(self, order_id: str) -> Dict[str, Any]:
        """Get order status internally (placeholder for Hyperliquid integration)"""
        # This will be connected to Hyperliquid in Phase 2
        # For now, simulate order status
        
        if order_id in self.active_orders:
            order_info = self.active_orders[order_id]
            placed_at = order_info['placed_at']
            time_since_placed = datetime.now() - placed_at
            
            # Simulate order progression over time
            if time_since_placed < timedelta(minutes=1):
                status = 'pending'
            elif time_since_placed < timedelta(minutes=5):
                status = 'partial_fill'
            else:
                status = 'filled'
            
            return {
                'status': status,
                'order_id': order_id,
                'filled_quantity': 0.5 if status == 'partial_fill' else 1.0 if status == 'filled' else 0.0,
                'remaining_quantity': 0.5 if status == 'partial_fill' else 0.0 if status == 'filled' else 1.0,
                'last_updated': datetime.now().isoformat()
            }
        else:
            return {
                'status': 'not_found',
                'order_id': order_id,
                'message': 'Order not found'
            }
    
    async def _handle_order_filled(self, order_id: str, order_status: Dict[str, Any]):
        """Handle order filled event"""
        logger.info(f"Order {order_id} filled: {order_status}")
        
        # Remove from active orders
        if order_id in self.active_orders:
            del self.active_orders[order_id]
    
    async def _handle_order_cancelled(self, order_id: str, order_status: Dict[str, Any]):
        """Handle order cancelled event"""
        logger.info(f"Order {order_id} cancelled: {order_status}")
        
        # Remove from active orders
        if order_id in self.active_orders:
            del self.active_orders[order_id]
    
    async def _handle_partial_fill(self, order_id: str, order_status: Dict[str, Any]):
        """Handle partial fill event"""
        logger.info(f"Order {order_id} partially filled: {order_status}")
        
        # Update order info with partial fill data
        if order_id in self.active_orders:
            self.active_orders[order_id]['partial_fills'] = self.active_orders[order_id].get('partial_fills', [])
            self.active_orders[order_id]['partial_fills'].append(order_status)
    
    async def _publish_condition_monitoring_strand(self, trading_plan: Dict[str, Any], condition_status: Dict[str, Any]):
        """Publish condition monitoring strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'condition_monitoring',
                'symbol': trading_plan.get('symbol', ''),
                'timeframe': trading_plan.get('timeframe', '1h'),
                'content': {
                    'trading_plan_id': trading_plan.get('id', ''),
                    'entry_conditions': trading_plan.get('entry_conditions', {}),
                    'condition_status': condition_status,
                    'monitoring_active': True
                },
                'tags': ['trader:condition_monitoring', 'trader:order_status']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published condition monitoring strand for {trading_plan.get('symbol', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing condition monitoring strand: {e}")
    
    async def _publish_order_placement_strand(self, trading_plan: Dict[str, Any], order_result: Dict[str, Any]):
        """Publish order placement strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'order_placement',
                'symbol': trading_plan.get('symbol', ''),
                'timeframe': trading_plan.get('timeframe', '1h'),
                'content': {
                    'trading_plan_id': trading_plan.get('id', ''),
                    'order_result': order_result,
                    'order_details': trading_plan.get('order_details', {}),
                    'placed_at': datetime.now().isoformat()
                },
                'tags': ['trader:order_placement', 'trader:order_status']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published order placement strand for {order_result.get('order_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing order placement strand: {e}")
    
    async def _publish_order_tracking_strand(self, order_id: str, order_status: Dict[str, Any]):
        """Publish order tracking strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'order_tracking',
                'content': {
                    'order_id': order_id,
                    'order_status': order_status,
                    'tracked_at': datetime.now().isoformat()
                },
                'tags': ['trader:order_tracking', 'trader:order_status']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published order tracking strand for {order_id}")
            
        except Exception as e:
            logger.error(f"Error publishing order tracking strand: {e}")
    
    async def get_active_orders(self) -> Dict[str, Any]:
        """Get all active orders"""
        return {
            'active_orders': self.active_orders,
            'count': len(self.active_orders),
            'timestamp': datetime.now().isoformat()
        }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        try:
            if order_id not in self.active_orders:
                return {
                    'status': 'error',
                    'message': f'Order {order_id} not found in active orders'
                }
            
            # Cancel order (this will be connected to Hyperliquid in Phase 2)
            cancel_result = await self._cancel_order_internal(order_id)
            
            if cancel_result.get('cancelled', False):
                # Remove from active orders
                del self.active_orders[order_id]
                
                # Publish cancellation strand
                await self._publish_order_cancellation_strand(order_id, cancel_result)
            
            return cancel_result
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def _cancel_order_internal(self, order_id: str) -> Dict[str, Any]:
        """Cancel order internally (placeholder for Hyperliquid integration)"""
        # This will be connected to Hyperliquid in Phase 2
        # For now, simulate order cancellation
        
        return {
            'status': 'success',
            'cancelled': True,
            'order_id': order_id,
            'cancelled_at': datetime.now().isoformat(),
            'message': 'Order cancelled successfully (simulated)'
        }
    
    async def _publish_order_cancellation_strand(self, order_id: str, cancel_result: Dict[str, Any]):
        """Publish order cancellation strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'order_cancellation',
                'content': {
                    'order_id': order_id,
                    'cancel_result': cancel_result,
                    'cancelled_at': datetime.now().isoformat()
                },
                'tags': ['trader:order_cancellation', 'trader:order_status']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published order cancellation strand for {order_id}")
            
        except Exception as e:
            logger.error(f"Error publishing order cancellation strand: {e}")
