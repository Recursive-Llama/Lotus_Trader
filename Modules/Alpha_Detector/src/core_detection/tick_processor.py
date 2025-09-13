"""
Tick Processor for Real-time WebSocket to 1m OHLCV Conversion
Converts incoming WebSocket ticks into 1-minute candles in real-time
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class Tick:
    """Individual tick data from WebSocket"""
    symbol: str
    timestamp: datetime
    price: float
    volume: float
    source: str = 'hyperliquid'

@dataclass
class OHLCVCandle:
    """1-minute OHLCV candle"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    tick_count: int

class TickProcessor:
    """
    Real-time tick processor that converts WebSocket ticks to 1m OHLCV candles
    """
    
    def __init__(self, db_manager, store_callback=None):
        self.db_manager = db_manager
        self.store_callback = store_callback
        
        # Tick buffers for each symbol
        self.tick_buffers: Dict[str, List[Tick]] = {}
        self.current_minute_boundaries: Dict[str, datetime] = {}
        
        # Processing state
        self.is_processing = False
        self.processing_task: Optional[asyncio.Task] = None
        
        logger.info("TickProcessor initialized")
    
    async def start_processing(self):
        """Start the tick processing loop"""
        if self.is_processing:
            return
            
        self.is_processing = True
        self.processing_task = asyncio.create_task(self._processing_loop())
        logger.info("Tick processing started")
    
    async def stop_processing(self):
        """Stop the tick processing loop"""
        self.is_processing = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Tick processing stopped")
    
    async def process_tick(self, tick_data: dict) -> bool:
        """
        Process a single tick from WebSocket
        
        Args:
            tick_data: Raw tick data from WebSocket
            
        Returns:
            bool: True if tick was processed successfully
        """
        try:
            # Convert to Tick object
            # Parse timestamp if it's a string
            if isinstance(tick_data['timestamp'], str):
                timestamp = datetime.fromisoformat(tick_data['timestamp'].replace('Z', '+00:00'))
            else:
                timestamp = tick_data['timestamp']
                
            tick = Tick(
                symbol=tick_data['symbol'],
                timestamp=timestamp,
                price=tick_data['close'],  # Use close price as tick price
                volume=tick_data['volume'],
                source=tick_data.get('source', 'hyperliquid')
            )
            
            # Add to buffer
            await self._add_tick_to_buffer(tick)
            
            # Check if we need to flush a candle
            await self._check_and_flush_candle(tick.symbol, tick.timestamp)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
            return False
    
    async def _add_tick_to_buffer(self, tick: Tick):
        """Add tick to the appropriate symbol buffer"""
        if tick.symbol not in self.tick_buffers:
            self.tick_buffers[tick.symbol] = []
        
        self.tick_buffers[tick.symbol].append(tick)
        
        # Keep only recent ticks (last 2 minutes worth)
        max_ticks = 2000  # Assume max 1000 ticks per minute
        if len(self.tick_buffers[tick.symbol]) > max_ticks:
            self.tick_buffers[tick.symbol] = self.tick_buffers[tick.symbol][-max_ticks:]
    
    async def _check_and_flush_candle(self, symbol: str, current_timestamp: datetime):
        """Check if we need to flush a 1m candle and do so if needed"""
        current_minute = self._get_minute_boundary(current_timestamp)
        
        # If we have a previous minute boundary and it's different, flush the candle
        if (symbol in self.current_minute_boundaries and 
            current_minute != self.current_minute_boundaries[symbol]):
            await self._flush_minute_candle(symbol, self.current_minute_boundaries[symbol])
        
        # Update current minute boundary
        self.current_minute_boundaries[symbol] = current_minute
    
    def _get_minute_boundary(self, timestamp: datetime) -> datetime:
        """Round timestamp down to nearest minute boundary"""
        return timestamp.replace(second=0, microsecond=0)
    
    async def _flush_minute_candle(self, symbol: str, minute_boundary: datetime):
        """Flush ticks for a symbol into a 1m OHLCV candle"""
        if symbol not in self.tick_buffers or not self.tick_buffers[symbol]:
            return
        
        # Get ticks for this minute
        minute_ticks = [
            tick for tick in self.tick_buffers[symbol]
            if self._get_minute_boundary(tick.timestamp) == minute_boundary
        ]
        
        if not minute_ticks:
            return
        
        # Create OHLCV candle
        candle = self._create_ohlcv_candle(symbol, minute_boundary, minute_ticks)
        
        # Store the candle
        await self._store_1m_candle(candle)
        
        # Remove processed ticks from buffer
        self.tick_buffers[symbol] = [
            tick for tick in self.tick_buffers[symbol]
            if self._get_minute_boundary(tick.timestamp) > minute_boundary
        ]
        
        logger.debug(f"Flushed 1m candle for {symbol}: {candle.timestamp} O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} V:{candle.volume}")
    
    def _create_ohlcv_candle(self, symbol: str, timestamp: datetime, ticks: List[Tick]) -> OHLCVCandle:
        """Create OHLCV candle from ticks"""
        if not ticks:
            raise ValueError("Cannot create candle from empty ticks")
        
        # Sort ticks by timestamp
        ticks.sort(key=lambda t: t.timestamp)
        
        return OHLCVCandle(
            symbol=symbol,
            timestamp=timestamp,
            open=ticks[0].price,
            high=max(tick.price for tick in ticks),
            low=min(tick.price for tick in ticks),
            close=ticks[-1].price,
            volume=sum(tick.volume for tick in ticks),
            tick_count=len(ticks)
        )
    
    async def _store_1m_candle(self, candle: OHLCVCandle):
        """Store 1m candle in database"""
        try:
            candle_data = {
                'symbol': candle.symbol,
                'timestamp': candle.timestamp.isoformat(),
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume,
                'data_quality_score': 1.0,
                'source': 'hyperliquid',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store in database
            if self.store_callback:
                await self.store_callback(candle_data)
            else:
                # Default storage method
                result = self.db_manager.client.table('alpha_market_data_1m').upsert(
                    candle_data,
                    on_conflict='symbol,timestamp'
                ).execute()
                
                if not result.data:
                    logger.error(f"Failed to store 1m candle for {candle.symbol}")
            
        except Exception as e:
            logger.error(f"Error storing 1m candle: {e}")
    
    async def _processing_loop(self):
        """Main processing loop (currently just a placeholder)"""
        while self.is_processing:
            await asyncio.sleep(1)  # Check every second for cleanup tasks
    
    def get_buffer_stats(self) -> Dict[str, Dict]:
        """Get statistics about tick buffers"""
        stats = {}
        for symbol, ticks in self.tick_buffers.items():
            if ticks:
                stats[symbol] = {
                    'tick_count': len(ticks),
                    'oldest_tick': min(tick.timestamp for tick in ticks),
                    'newest_tick': max(tick.timestamp for tick in ticks),
                    'current_minute': self.current_minute_boundaries.get(symbol)
                }
        return stats
