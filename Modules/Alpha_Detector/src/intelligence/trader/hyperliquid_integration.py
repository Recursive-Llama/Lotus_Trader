"""
Hyperliquid Integration - Direct integration with Hyperliquid exchange

This component provides direct integration with Hyperliquid exchange using
WebSocket for real-time data and REST API for order management.
"""

import asyncio
import logging
import websockets
import json
import aiohttp
import hmac
import hashlib
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import base64

logger = logging.getLogger(__name__)


class HyperliquidIntegration:
    """Direct integration with Hyperliquid exchange"""
    
    def __init__(self, supabase_manager, llm_client, api_key: str = "", api_secret: str = ""):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.api_key = api_key
        self.api_secret = api_secret
        
        # WebSocket connection
        self.websocket = None
        self.websocket_connected = False
        self.websocket_url = "wss://api.hyperliquid.xyz/ws"
        
        # REST API endpoints
        self.rest_base_url = "https://api.hyperliquid.xyz"
        
        # Connection management
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
        # Subscription management
        self.subscriptions = {}
        self.message_handlers = {}
        
        # Order tracking
        self.active_orders = {}
        self.order_updates = {}
        
    async def connect_websocket(self) -> bool:
        """
        Connect to Hyperliquid WebSocket for real-time data
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info("Connecting to Hyperliquid WebSocket...")
            
            # Create WebSocket connection
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.websocket_connected = True
            self.reconnect_attempts = 0
            
            # Start message handling loop
            asyncio.create_task(self._websocket_message_loop())
            
            # Subscribe to default channels
            await self._subscribe_to_default_channels()
            
            logger.info("Successfully connected to Hyperliquid WebSocket")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Hyperliquid WebSocket: {e}")
            self.websocket_connected = False
            return False
    
    async def disconnect_websocket(self):
        """Disconnect from Hyperliquid WebSocket"""
        try:
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
            
            self.websocket_connected = False
            logger.info("Disconnected from Hyperliquid WebSocket")
            
        except Exception as e:
            logger.error(f"Error disconnecting from WebSocket: {e}")
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place order on Hyperliquid
        
        Args:
            order_data: Order details including symbol, side, quantity, price, etc.
            
        Returns:
            Dict with order placement result
        """
        try:
            # Validate order data
            validation_result = await self._validate_order_data(order_data)
            if not validation_result['valid']:
                return {
                    'status': 'error',
                    'message': validation_result['message'],
                    'order_placed': False
                }
            
            # Prepare order payload
            order_payload = await self._prepare_order_payload(order_data)
            
            # Send order via REST API
            order_result = await self._send_order_request(order_payload)
            
            if order_result.get('status') == 'success':
                order_id = order_result.get('order_id', '')
                
                # Track order
                self.active_orders[order_id] = {
                    'order_data': order_data,
                    'order_payload': order_payload,
                    'placed_at': datetime.now(),
                    'status': 'pending'
                }
                
                # Subscribe to order updates
                await self._subscribe_to_order_updates(order_id)
                
                # Publish order placement strand
                await self._publish_order_placement_strand(order_data, order_result)
            
            return order_result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'order_placed': False
            }
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions from Hyperliquid
        
        Returns:
            List of position data
        """
        try:
            # Prepare request
            endpoint = "/info"
            payload = {
                "type": "clearinghouseState",
                "user": self.api_key
            }
            
            # Send request
            response = await self._send_rest_request("POST", endpoint, payload)
            
            if response.get('status') == 'success':
                positions = response.get('data', {}).get('assetPositions', [])
                
                # Process positions
                processed_positions = []
                for position in positions:
                    processed_position = await self._process_position_data(position)
                    processed_positions.append(processed_position)
                
                # Publish positions strand
                await self._publish_positions_strand(processed_positions)
                
                return processed_positions
            else:
                logger.error(f"Failed to get positions: {response.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get order status from Hyperliquid
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Dict with order status
        """
        try:
            # Check if we have the order in our tracking
            if order_id in self.active_orders:
                order_info = self.active_orders[order_id]
                
                # Get order status from exchange
                endpoint = "/info"
                payload = {
                    "type": "openOrders",
                    "user": self.api_key
                }
                
                response = await self._send_rest_request("POST", endpoint, payload)
                
                if response.get('status') == 'success':
                    open_orders = response.get('data', [])
                    
                    # Find our order
                    order_status = None
                    for order in open_orders:
                        if order.get('oid') == order_id:
                            order_status = order
                            break
                    
                    if order_status:
                        # Update order info
                        order_info['status'] = order_status.get('status', 'unknown')
                        order_info['last_updated'] = datetime.now()
                        
                        # Process order status
                        processed_status = await self._process_order_status(order_status)
                        
                        return processed_status
                    else:
                        # Order not found in open orders, might be filled or cancelled
                        return await self._check_order_history(order_id)
                else:
                    return {
                        'status': 'error',
                        'message': response.get('message', 'Failed to get order status'),
                        'order_id': order_id
                    }
            else:
                return {
                    'status': 'error',
                    'message': f'Order {order_id} not found in active orders',
                    'order_id': order_id
                }
                
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'order_id': order_id
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order on Hyperliquid
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Dict with cancellation result
        """
        try:
            if order_id not in self.active_orders:
                return {
                    'status': 'error',
                    'message': f'Order {order_id} not found in active orders'
                }
            
            # Prepare cancellation payload
            order_info = self.active_orders[order_id]
            order_payload = order_info['order_payload']
            
            cancel_payload = {
                "action": {
                    "type": "cancel",
                    "cancels": [{
                        "oid": order_id
                    }]
                }
            }
            
            # Send cancellation request
            cancel_result = await self._send_order_request(cancel_payload)
            
            if cancel_result.get('status') == 'success':
                # Update order status
                order_info['status'] = 'cancelled'
                order_info['cancelled_at'] = datetime.now()
                
                # Publish cancellation strand
                await self._publish_order_cancellation_strand(order_id, cancel_result)
            
            return cancel_result
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def _websocket_message_loop(self):
        """Handle WebSocket messages"""
        try:
            while self.websocket_connected and not self.websocket.closed:
                try:
                    message = await self.websocket.recv()
                    await self._handle_websocket_message(message)
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    await self._handle_websocket_disconnection()
                    break
                except Exception as e:
                    logger.error(f"Error in WebSocket message loop: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"WebSocket message loop error: {e}")
            await self._handle_websocket_disconnection()
    
    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get('type', '')
            
            # Route message to appropriate handler
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](data)
            else:
                logger.debug(f"Unhandled WebSocket message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def _handle_websocket_disconnection(self):
        """Handle WebSocket disconnection"""
        self.websocket_connected = False
        
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting to reconnect to WebSocket (attempt {self.reconnect_attempts})")
            
            await asyncio.sleep(self.reconnect_delay)
            await self.connect_websocket()
        else:
            logger.error("Max reconnection attempts reached. WebSocket connection failed.")
    
    async def _subscribe_to_default_channels(self):
        """Subscribe to default WebSocket channels"""
        try:
            # Subscribe to order updates
            await self._subscribe_to_channel("orderUpdates", self._handle_order_update)
            
            # Subscribe to position updates
            await self._subscribe_to_channel("positionUpdates", self._handle_position_update)
            
            # Subscribe to trade updates
            await self._subscribe_to_channel("tradeUpdates", self._handle_trade_update)
            
        except Exception as e:
            logger.error(f"Error subscribing to default channels: {e}")
    
    async def _subscribe_to_channel(self, channel: str, handler):
        """Subscribe to a WebSocket channel"""
        try:
            subscription_message = {
                "method": "subscribe",
                "subscription": {
                    "type": channel,
                    "user": self.api_key
                }
            }
            
            await self.websocket.send(json.dumps(subscription_message))
            self.message_handlers[channel] = handler
            
            logger.info(f"Subscribed to channel: {channel}")
            
        except Exception as e:
            logger.error(f"Error subscribing to channel {channel}: {e}")
    
    async def _subscribe_to_order_updates(self, order_id: str):
        """Subscribe to updates for a specific order"""
        try:
            subscription_message = {
                "method": "subscribe",
                "subscription": {
                    "type": "orderUpdates",
                    "user": self.api_key,
                    "oid": order_id
                }
            }
            
            await self.websocket.send(json.dumps(subscription_message))
            logger.info(f"Subscribed to order updates for {order_id}")
            
        except Exception as e:
            logger.error(f"Error subscribing to order updates for {order_id}: {e}")
    
    async def _handle_order_update(self, data: Dict[str, Any]):
        """Handle order update messages"""
        try:
            order_id = data.get('oid', '')
            status = data.get('status', '')
            
            if order_id in self.active_orders:
                order_info = self.active_orders[order_id]
                order_info['status'] = status
                order_info['last_updated'] = datetime.now()
                
                # Store order update
                self.order_updates[order_id] = data
                
                # Publish order update strand
                await self._publish_order_update_strand(order_id, data)
                
                logger.info(f"Order {order_id} status updated to {status}")
                
        except Exception as e:
            logger.error(f"Error handling order update: {e}")
    
    async def _handle_position_update(self, data: Dict[str, Any]):
        """Handle position update messages"""
        try:
            # Process position update
            position_data = await self._process_position_update(data)
            
            # Publish position update strand
            await self._publish_position_update_strand(position_data)
            
            logger.debug(f"Position update received: {position_data.get('symbol', '')}")
            
        except Exception as e:
            logger.error(f"Error handling position update: {e}")
    
    async def _handle_trade_update(self, data: Dict[str, Any]):
        """Handle trade update messages"""
        try:
            # Process trade update
            trade_data = await self._process_trade_update(data)
            
            # Publish trade update strand
            await self._publish_trade_update_strand(trade_data)
            
            logger.debug(f"Trade update received: {trade_data.get('symbol', '')}")
            
        except Exception as e:
            logger.error(f"Error handling trade update: {e}")
    
    async def _validate_order_data(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order data before sending"""
        required_fields = ['symbol', 'side', 'quantity', 'price']
        
        for field in required_fields:
            if field not in order_data:
                return {
                    'valid': False,
                    'message': f'Missing required field: {field}'
                }
        
        # Validate side
        if order_data['side'] not in ['buy', 'sell']:
            return {
                'valid': False,
                'message': 'Side must be "buy" or "sell"'
            }
        
        # Validate quantity
        if order_data['quantity'] <= 0:
            return {
                'valid': False,
                'message': 'Quantity must be positive'
            }
        
        # Validate price
        if order_data['price'] <= 0:
            return {
                'valid': False,
                'message': 'Price must be positive'
            }
        
        return {'valid': True}
    
    async def _prepare_order_payload(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare order payload for Hyperliquid API"""
        # Convert side to Hyperliquid format
        side = "B" if order_data['side'] == 'buy' else "S"
        
        # Prepare order action
        order_action = {
            "type": "order",
            "orders": [{
                "a": order_data['symbol'],  # asset
                "b": side,  # buy/sell
                "p": str(order_data['price']),  # price
                "s": str(order_data['quantity']),  # size
                "r": False,  # reduce only
                "t": "Limit"  # order type
            }]
        }
        
        # Add optional fields
        if 'time_in_force' in order_data:
            order_action['orders'][0]['tif'] = order_data['time_in_force']
        
        if 'post_only' in order_data:
            order_action['orders'][0]['post'] = order_data['post_only']
        
        return {
            "action": order_action
        }
    
    async def _send_order_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send order request to Hyperliquid"""
        try:
            endpoint = "/exchange"
            
            # Add authentication if available
            if self.api_key and self.api_secret:
                payload = await self._add_authentication(payload)
            
            response = await self._send_rest_request("POST", endpoint, payload)
            
            if response.get('status') == 'success':
                # Extract order ID from response
                order_id = response.get('data', {}).get('oid', '')
                
                return {
                    'status': 'success',
                    'order_placed': True,
                    'order_id': order_id,
                    'message': 'Order placed successfully'
                }
            else:
                return {
                    'status': 'error',
                    'order_placed': False,
                    'message': response.get('message', 'Order placement failed')
                }
                
        except Exception as e:
            logger.error(f"Error sending order request: {e}")
            return {
                'status': 'error',
                'order_placed': False,
                'message': str(e)
            }
    
    async def _send_rest_request(self, method: str, endpoint: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send REST API request to Hyperliquid"""
        try:
            url = f"{self.rest_base_url}{endpoint}"
            
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url) as response:
                        data = await response.json()
                elif method == "POST":
                    async with session.post(url, json=payload) as response:
                        data = await response.json()
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status == 200:
                    return {
                        'status': 'success',
                        'data': data
                    }
                else:
                    return {
                        'status': 'error',
                        'message': f'HTTP {response.status}: {data}'
                    }
                    
        except Exception as e:
            logger.error(f"Error sending REST request: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def _add_authentication(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Add authentication to payload"""
        try:
            # Create signature
            timestamp = str(int(time.time() * 1000))
            message = json.dumps(payload) + timestamp
            
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Add authentication headers
            payload['timestamp'] = timestamp
            payload['signature'] = signature
            payload['apiKey'] = self.api_key
            
            return payload
            
        except Exception as e:
            logger.error(f"Error adding authentication: {e}")
            return payload
    
    async def _process_position_data(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Process position data from Hyperliquid"""
        return {
            'symbol': position.get('position', {}).get('coin', ''),
            'side': 'long' if position.get('position', {}).get('szi', 0) > 0 else 'short',
            'quantity': abs(position.get('position', {}).get('szi', 0)),
            'entry_price': position.get('position', {}).get('entryPx', 0),
            'unrealized_pnl': position.get('position', {}).get('unrealizedPnl', 0),
            'position_value': position.get('position', {}).get('positionValue', 0),
            'margin_used': position.get('position', {}).get('marginUsed', 0)
        }
    
    async def _process_order_status(self, order_status: Dict[str, Any]) -> Dict[str, Any]:
        """Process order status from Hyperliquid"""
        return {
            'order_id': order_status.get('oid', ''),
            'status': order_status.get('status', 'unknown'),
            'symbol': order_status.get('coin', ''),
            'side': 'buy' if order_status.get('side') == 'B' else 'sell',
            'quantity': order_status.get('sz', 0),
            'price': order_status.get('limitPx', 0),
            'filled_quantity': order_status.get('sz', 0) - order_status.get('sz', 0),  # Simplified
            'remaining_quantity': order_status.get('sz', 0),
            'timestamp': order_status.get('timestamp', '')
        }
    
    async def _process_position_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process position update data"""
        return {
            'symbol': data.get('coin', ''),
            'side': 'long' if data.get('szi', 0) > 0 else 'short',
            'quantity': abs(data.get('szi', 0)),
            'unrealized_pnl': data.get('unrealizedPnl', 0),
            'position_value': data.get('positionValue', 0),
            'update_timestamp': datetime.now().isoformat()
        }
    
    async def _process_trade_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process trade update data"""
        return {
            'symbol': data.get('coin', ''),
            'side': 'buy' if data.get('side') == 'B' else 'sell',
            'quantity': data.get('sz', 0),
            'price': data.get('px', 0),
            'trade_id': data.get('tid', ''),
            'timestamp': data.get('time', '')
        }
    
    async def _check_order_history(self, order_id: str) -> Dict[str, Any]:
        """Check order history for filled or cancelled orders"""
        try:
            endpoint = "/info"
            payload = {
                "type": "userFills",
                "user": self.api_key
            }
            
            response = await self._send_rest_request("POST", endpoint, payload)
            
            if response.get('status') == 'success':
                fills = response.get('data', [])
                
                # Look for our order in fills
                for fill in fills:
                    if fill.get('oid') == order_id:
                        return {
                            'order_id': order_id,
                            'status': 'filled',
                            'filled_quantity': fill.get('sz', 0),
                            'filled_price': fill.get('px', 0),
                            'fill_timestamp': fill.get('time', '')
                        }
                
                # Order not found in fills, might be cancelled
                return {
                    'order_id': order_id,
                    'status': 'cancelled',
                    'message': 'Order not found in open orders or fills'
                }
            else:
                return {
                    'order_id': order_id,
                    'status': 'unknown',
                    'message': 'Failed to check order history'
                }
                
        except Exception as e:
            logger.error(f"Error checking order history: {e}")
            return {
                'order_id': order_id,
                'status': 'error',
                'message': str(e)
            }
    
    async def _publish_order_placement_strand(self, order_data: Dict[str, Any], order_result: Dict[str, Any]):
        """Publish order placement strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'hyperliquid_order_placement',
                'symbol': order_data.get('symbol', ''),
                'content': {
                    'order_data': order_data,
                    'order_result': order_result,
                    'venue': 'hyperliquid',
                    'placed_at': datetime.now().isoformat()
                },
                'tags': ['trader:order_placement', 'trader:hyperliquid', 'trader:order_status']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published Hyperliquid order placement strand for {order_result.get('order_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing order placement strand: {e}")
    
    async def _publish_order_update_strand(self, order_id: str, update_data: Dict[str, Any]):
        """Publish order update strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'hyperliquid_order_update',
                'content': {
                    'order_id': order_id,
                    'update_data': update_data,
                    'venue': 'hyperliquid',
                    'update_timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:order_update', 'trader:hyperliquid', 'trader:order_status']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published Hyperliquid order update strand for {order_id}")
            
        except Exception as e:
            logger.error(f"Error publishing order update strand: {e}")
    
    async def _publish_order_cancellation_strand(self, order_id: str, cancel_result: Dict[str, Any]):
        """Publish order cancellation strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'hyperliquid_order_cancellation',
                'content': {
                    'order_id': order_id,
                    'cancel_result': cancel_result,
                    'venue': 'hyperliquid',
                    'cancelled_at': datetime.now().isoformat()
                },
                'tags': ['trader:order_cancellation', 'trader:hyperliquid', 'trader:order_status']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published Hyperliquid order cancellation strand for {order_id}")
            
        except Exception as e:
            logger.error(f"Error publishing order cancellation strand: {e}")
    
    async def _publish_positions_strand(self, positions: List[Dict[str, Any]]):
        """Publish positions strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'hyperliquid_positions',
                'content': {
                    'positions': positions,
                    'venue': 'hyperliquid',
                    'positions_count': len(positions),
                    'timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:positions', 'trader:hyperliquid', 'trader:position_management']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published Hyperliquid positions strand with {len(positions)} positions")
            
        except Exception as e:
            logger.error(f"Error publishing positions strand: {e}")
    
    async def _publish_position_update_strand(self, position_data: Dict[str, Any]):
        """Publish position update strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'hyperliquid_position_update',
                'symbol': position_data.get('symbol', ''),
                'content': {
                    'position_data': position_data,
                    'venue': 'hyperliquid',
                    'update_timestamp': position_data.get('update_timestamp', datetime.now().isoformat())
                },
                'tags': ['trader:position_update', 'trader:hyperliquid', 'trader:position_management']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published Hyperliquid position update strand for {position_data.get('symbol', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing position update strand: {e}")
    
    async def _publish_trade_update_strand(self, trade_data: Dict[str, Any]):
        """Publish trade update strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'hyperliquid_trade_update',
                'symbol': trade_data.get('symbol', ''),
                'content': {
                    'trade_data': trade_data,
                    'venue': 'hyperliquid',
                    'trade_timestamp': trade_data.get('timestamp', datetime.now().isoformat())
                },
                'tags': ['trader:trade_update', 'trader:hyperliquid', 'trader:execution_quality']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published Hyperliquid trade update strand for {trade_data.get('symbol', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing trade update strand: {e}")
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status"""
        return {
            'websocket_connected': self.websocket_connected,
            'reconnect_attempts': self.reconnect_attempts,
            'active_orders': len(self.active_orders),
            'subscriptions': list(self.subscriptions.keys()),
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_active_orders(self) -> Dict[str, Any]:
        """Get all active orders"""
        return {
            'active_orders': self.active_orders,
            'order_count': len(self.active_orders),
            'timestamp': datetime.now().isoformat()
        }
