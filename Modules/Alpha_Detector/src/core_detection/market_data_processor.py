"""
Market Data Processor for Alpha Detector Module
Phase 1.2: Process and store market data from Hyperliquid WebSocket
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
import sys
import os
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), '.env'))

# Add src/utils to sys.path to import SupabaseManager
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils'))

from supabase_manager import SupabaseManager
from .tick_processor import TickProcessor

logger = logging.getLogger(__name__)

class MarketDataProcessor:
    """Process and store market data from WebSocket"""
    
    def __init__(self, db_manager: SupabaseManager = None):
        self.db_manager = db_manager or SupabaseManager()
        self.data_quality_validator = DataQualityValidator()
        self.tick_processor = TickProcessor(db_manager, self._async_store_callback)
        self.processed_count = 0
        self.error_count = 0
        
    async def process_ohlcv_data(self, raw_data: Dict) -> bool:
        """Process raw OHLCV data as tick and convert to 1m candles"""
        try:
            # Validate data quality
            if not self.data_quality_validator.validate(raw_data):
                logger.warning(f"Data quality validation failed for {raw_data.get('symbol', 'unknown')}")
                self.error_count += 1
                return False
            
            # Process as tick data (will be converted to 1m candles automatically)
            success = await self.tick_processor.process_tick(raw_data)
            
            if success:
                self.processed_count += 1
                logger.debug(f"Processed tick for {raw_data['symbol']}: {raw_data['close']}")
            else:
                self.error_count += 1
                logger.error(f"Failed to process tick for {raw_data['symbol']}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing tick data: {e}")
            self.error_count += 1
            return False
    
    def prepare_db_data(self, raw_data: Dict) -> Dict:
        """Prepare raw data for database insertion"""
        try:
            # Convert timestamp to ISO format for database
            timestamp_iso = raw_data['timestamp'].isoformat()
            
            db_data = {
                'symbol': raw_data['symbol'],
                'timestamp': timestamp_iso,
                'open': raw_data['open'],
                'high': raw_data['high'],
                'low': raw_data['low'],
                'close': raw_data['close'],
                'volume': raw_data['volume'],
                'data_quality_score': raw_data.get('data_quality_score', 1.0),
                'source': raw_data.get('source', 'hyperliquid'),
                'created_at': raw_data.get('created_at', datetime.now(timezone.utc)).isoformat()
            }
            
            return db_data
            
        except Exception as e:
            logger.error(f"Error preparing database data: {e}")
            return None
    
    def store_market_data(self, db_data: Dict) -> bool:
        """Store market data in alpha_market_data_1m table with duplicate handling"""
        try:
            # Use upsert to handle duplicates gracefully
            # This will insert new data or update existing data if the same symbol+timestamp exists
            result = self.db_manager.client.table('alpha_market_data_1m').upsert(
                db_data,
                on_conflict='symbol,timestamp'
            ).execute()
            
            if result.data:
                return True
            else:
                logger.error(f"Failed to upsert market data. Result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing market data: {e}")
            return False
    
    def get_recent_market_data(self, symbol: str, limit: int = 10) -> list:
        """Get recent market data for a symbol"""
        try:
            result = self.db_manager.client.table('alpha_market_data_1m')\
                .select('*')\
                .eq('symbol', symbol)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting recent market data for {symbol}: {e}")
            return []
    
    def get_market_data_count(self) -> int:
        """Get total count of market data records"""
        try:
            # Use a simple select with limit to get count
            result = self.db_manager.client.table('alpha_market_data_1m')\
                .select('symbol')\
                .execute()
            
            return len(result.data) if result.data else 0
            
        except Exception as e:
            logger.error(f"Error getting market data count: {e}")
            return 0
    
    async def start_tick_processing(self):
        """Start the tick processing system"""
        await self.tick_processor.start_processing()
    
    async def stop_tick_processing(self):
        """Stop the tick processing system"""
        await self.tick_processor.stop_processing()
    
    async def _async_store_callback(self, candle_data):
        """Async callback for storing 1m candles"""
        return self.store_market_data(candle_data)
    
    def get_tick_buffer_stats(self) -> Dict:
        """Get tick buffer statistics"""
        return self.tick_processor.get_buffer_stats()
    
    def get_processing_stats(self) -> Dict:
        """Get processing statistics"""
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'success_rate': self.processed_count / (self.processed_count + self.error_count) if (self.processed_count + self.error_count) > 0 else 0,
            'tick_buffers': self.get_tick_buffer_stats()
        }


class DataQualityValidator:
    """Validate market data quality"""
    
    def __init__(self):
        self.min_price = 0.000001  # Minimum reasonable price
        self.max_price = 1000000   # Maximum reasonable price
        self.max_volume = 1000000000  # Maximum reasonable volume
        
    def validate(self, data: Dict) -> bool:
        """Validate market data quality"""
        try:
            # Check required fields
            required_fields = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            for field in required_fields:
                if field not in data or data[field] is None:
                    logger.warning(f"Missing required field: {field}")
                    return False
            
            # Check price values
            prices = [data['open'], data['high'], data['low'], data['close']]
            for price in prices:
                if not isinstance(price, (int, float)) or price <= 0:
                    logger.warning(f"Invalid price value: {price}")
                    return False
                
                if price < self.min_price or price > self.max_price:
                    logger.warning(f"Price out of reasonable range: {price}")
                    return False
            
            # Check volume
            if not isinstance(data['volume'], (int, float)) or data['volume'] < 0:
                logger.warning(f"Invalid volume value: {data['volume']}")
                return False
            
            if data['volume'] > self.max_volume:
                logger.warning(f"Volume too high: {data['volume']}")
                return False
            
            # Check OHLC logic
            if data['high'] < data['low']:
                logger.warning("High price is less than low price")
                return False
            
            if data['high'] < data['open'] or data['high'] < data['close']:
                logger.warning("High price is less than open or close")
                return False
            
            if data['low'] > data['open'] or data['low'] > data['close']:
                logger.warning("Low price is greater than open or close")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating data quality: {e}")
            return False
