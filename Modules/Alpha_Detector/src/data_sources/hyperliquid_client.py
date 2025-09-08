"""
Hyperliquid WebSocket Client for Alpha Detector Module
Phase 1.2: Market data collection from Hyperliquid WebSocket
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), '.env'))

logger = logging.getLogger(__name__)

class HyperliquidWebSocketClient:
    """WebSocket client for Hyperliquid market data"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL']
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.websocket = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        self.data_callback = None
        self.health_monitor = WebSocketHealthMonitor()
        self.data_gap_detector = DataGapDetector()
        
    def set_data_callback(self, callback: Callable):
        """Set callback function for incoming market data"""
        self.data_callback = callback
        
    async def connect(self):
        """Connect to Hyperliquid WebSocket"""
        try:
            logger.info(f"Connecting to Hyperliquid WebSocket: {self.ws_url}")
            self.websocket = await websockets.connect(self.ws_url)
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("Successfully connected to Hyperliquid WebSocket")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Hyperliquid WebSocket: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from Hyperliquid WebSocket")
    
    async def subscribe_to_market_data(self):
        """Subscribe to 1-minute OHLCV data for configured symbols"""
        if not self.is_connected:
            logger.error("Not connected to WebSocket")
            return False
            
        try:
            # Hyperliquid subscription message format
            subscription_message = {
                "method": "subscribe",
                "subscription": {
                    "type": "candle",
                    "coin": self.symbols[0],  # Start with first symbol
                    "interval": "1m"
                }
            }
            
            await self.websocket.send(json.dumps(subscription_message))
            logger.info(f"Subscribed to 1m data for {self.symbols[0]}")
            
            # Subscribe to additional symbols
            for symbol in self.symbols[1:]:
                subscription_message["subscription"]["coin"] = symbol
                await self.websocket.send(json.dumps(subscription_message))
                logger.info(f"Subscribed to 1m data for {symbol}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to market data: {e}")
            return False
    
    async def listen_for_data(self):
        """Listen for incoming market data"""
        if not self.is_connected:
            logger.error("Not connected to WebSocket")
            return
            
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
            await self.handle_reconnection()
        except Exception as e:
            logger.error(f"Error in listen_for_data: {e}")
            self.is_connected = False
    
    async def handle_message(self, data: Dict):
        """Handle incoming WebSocket message"""
        try:
            # Check if this is candle data
            if data.get('channel') == 'candle' and 'data' in data:
                candle_data = data['data']
                
                # Process the candle data
                processed_data = self.process_candle_data(candle_data)
                
                if processed_data:
                    # Update health monitor
                    self.health_monitor.update_data_received(processed_data['symbol'])
                    
                    # Check for data gaps
                    self.data_gap_detector.check_data_gap(processed_data)
                    
                    # Call data callback if set
                    if self.data_callback:
                        await self.data_callback(processed_data)
                    else:
                        logger.info(f"Received data for {processed_data['symbol']}: {processed_data['close']}")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def process_candle_data(self, candle_data: Dict) -> Dict:
        """Process raw candle data into structured format"""
        try:
            # Extract OHLCV data from Hyperliquid format
            processed = {
                'symbol': candle_data.get('s', 'UNKNOWN'),  # 's' is the symbol field
                'timestamp': datetime.fromtimestamp(candle_data.get('t', 0) / 1000, tz=timezone.utc),
                'open': float(candle_data.get('o', 0)),
                'high': float(candle_data.get('h', 0)),
                'low': float(candle_data.get('l', 0)),
                'close': float(candle_data.get('c', 0)),
                'volume': float(candle_data.get('v', 0)),
                'data_quality_score': 1.0,  # Default quality score
                'source': 'hyperliquid',
                'created_at': datetime.now(timezone.utc)
            }
            
            # Validate data quality
            processed['data_quality_score'] = self.validate_data_quality(processed)
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing candle data: {e}")
            return None
    
    def validate_data_quality(self, data: Dict) -> float:
        """Validate data quality and return score (0-1)"""
        try:
            score = 1.0
            
            # Check for zero or negative values
            if data['open'] <= 0 or data['high'] <= 0 or data['low'] <= 0 or data['close'] <= 0:
                score -= 0.5
            
            # Check for logical consistency
            if data['high'] < data['low'] or data['high'] < data['open'] or data['high'] < data['close']:
                score -= 0.3
            
            if data['low'] > data['open'] or data['low'] > data['close']:
                score -= 0.3
            
            # Check for reasonable price movement (not too volatile)
            price_range = (data['high'] - data['low']) / data['close']
            if price_range > 0.1:  # More than 10% range in 1 minute
                score -= 0.2
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Error validating data quality: {e}")
            return 0.5
    
    async def handle_reconnection(self):
        """Handle WebSocket reconnection"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        await asyncio.sleep(self.reconnect_delay)
        
        if await self.connect():
            await self.subscribe_to_market_data()
            await self.listen_for_data()
    
    async def run(self):
        """Main run loop"""
        try:
            if await self.connect():
                if await self.subscribe_to_market_data():
                    await self.listen_for_data()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in run loop: {e}")
        finally:
            await self.disconnect()


class WebSocketHealthMonitor:
    """Monitor WebSocket connection health"""
    
    def __init__(self):
        self.last_data_received = {}
        self.connection_health = {}
        
    def update_data_received(self, symbol: str):
        """Update last data received timestamp for symbol"""
        self.last_data_received[symbol] = datetime.now(timezone.utc)
        self.connection_health[symbol] = 'healthy'
    
    def check_health(self) -> Dict[str, str]:
        """Check health status for all symbols"""
        current_time = datetime.now(timezone.utc)
        health_status = {}
        
        for symbol, last_received in self.last_data_received.items():
            time_since_last = (current_time - last_received).total_seconds()
            
            if time_since_last > 300:  # 5 minutes
                health_status[symbol] = 'unhealthy'
            elif time_since_last > 120:  # 2 minutes
                health_status[symbol] = 'warning'
            else:
                health_status[symbol] = 'healthy'
        
        return health_status


class DataGapDetector:
    """Detect data gaps in market data stream"""
    
    def __init__(self):
        self.last_timestamps = {}
        
    def check_data_gap(self, data: Dict):
        """Check for data gaps"""
        symbol = data['symbol']
        current_timestamp = data['timestamp']
        
        if symbol in self.last_timestamps:
            last_timestamp = self.last_timestamps[symbol]
            time_diff = (current_timestamp - last_timestamp).total_seconds()
            
            # Check for gaps longer than 2 minutes (allowing for 1 minute + buffer)
            if time_diff > 120:
                logger.warning(f"Data gap detected for {symbol}: {time_diff} seconds")
        
        self.last_timestamps[symbol] = current_timestamp
