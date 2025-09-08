"""
Market Data Collector for Alpha Detector Module
Phase 1.2: Main orchestrator for market data collection
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List

# Add src/utils and src/core_detection to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core_detection'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_sources'))

from supabase_manager import SupabaseManager
from market_data_processor import MarketDataProcessor
from hyperliquid_client import HyperliquidWebSocketClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketDataCollector:
    """Main market data collector orchestrator"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['BTC', 'ETH', 'SOL']
        self.db_manager = SupabaseManager()
        self.data_processor = MarketDataProcessor(self.db_manager)
        self.websocket_client = HyperliquidWebSocketClient(self.symbols)
        self.is_running = False
        self.start_time = None
        
        # Set up data callback
        self.websocket_client.set_data_callback(self.handle_market_data)
        
    async def handle_market_data(self, data: Dict):
        """Handle incoming market data from WebSocket"""
        try:
            success = await self.data_processor.process_ohlcv_data(data)
            if success:
                logger.debug(f"Processed data for {data['symbol']}: {data['close']}")
            else:
                logger.warning(f"Failed to process data for {data['symbol']}")
        except Exception as e:
            logger.error(f"Error handling market data: {e}")
    
    async def start_collection(self):
        """Start market data collection"""
        try:
            logger.info("Starting market data collection...")
            logger.info(f"Symbols: {self.symbols}")
            
            # Test database connection
            if not self.db_manager.test_connection():
                logger.error("Database connection failed")
                return False
            
            # Check if market_data_1m table exists
            try:
                count = self.data_processor.get_market_data_count()
                logger.info(f"Found {count} existing market data records")
            except Exception as e:
                logger.error(f"Market data table not found or error: {e}")
                logger.info("Please create the market_data_1m table first")
                return False
            
            self.is_running = True
            self.start_time = datetime.now(timezone.utc)
            
            # Start WebSocket client
            await self.websocket_client.run()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in market data collection: {e}")
        finally:
            await self.stop_collection()
    
    async def stop_collection(self):
        """Stop market data collection"""
        try:
            logger.info("Stopping market data collection...")
            self.is_running = False
            
            # Disconnect WebSocket
            await self.websocket_client.disconnect()
            
            # Print final statistics
            stats = self.data_processor.get_processing_stats()
            logger.info(f"Collection completed. Stats: {stats}")
            
        except Exception as e:
            logger.error(f"Error stopping collection: {e}")
    
    def get_status(self) -> Dict:
        """Get current collection status"""
        stats = self.data_processor.get_processing_stats()
        health = self.websocket_client.health_monitor.check_health()
        
        return {
            'is_running': self.is_running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'symbols': self.symbols,
            'processing_stats': stats,
            'connection_health': health,
            'websocket_connected': self.websocket_client.is_connected
        }


async def main():
    """Main function for testing market data collection"""
    logger.info("Alpha Detector Market Data Collector - Phase 1.2")
    logger.info("=" * 60)
    
    # Create collector
    collector = MarketDataCollector(['BTC', 'ETH', 'SOL'])
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(collector.stop_collection())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start collection
        await collector.start_collection()
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        logger.info("Market data collection stopped")


if __name__ == "__main__":
    # Run the collector
    asyncio.run(main())

