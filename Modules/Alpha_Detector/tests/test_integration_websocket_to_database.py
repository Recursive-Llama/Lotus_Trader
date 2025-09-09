"""
WebSocket to Database Integration Test

This test validates the complete dataflow:
WebSocket → MarketDataProcessor → alpha_market_data_1m table → Raw Data Intelligence
"""

import pytest
import asyncio
import time
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

from src.data_sources.hyperliquid_client import HyperliquidWebSocketClient
from src.core_detection.market_data_processor import MarketDataProcessor
from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

class TestWebSocketToDatabaseIntegration:
    """Test complete WebSocket to database dataflow"""
    
    @pytest.fixture
    async def setup_integration_components(self):
        """Setup components for WebSocket to database integration"""
        components = {}
        
        try:
            # Initialize database and LLM client
            components['supabase_manager'] = SupabaseManager()
            components['llm_client'] = OpenRouterClient()
            
            # Initialize MarketDataProcessor
            components['market_data_processor'] = MarketDataProcessor(components['supabase_manager'])
            
            # Initialize WebSocket client
            components['websocket_client'] = HyperliquidWebSocketClient(['BTC', 'ETH'])
            
            # Initialize Raw Data Intelligence Agent
            components['raw_data_agent'] = RawDataIntelligenceAgent(
                components['supabase_manager'], 
                components['llm_client']
            )
            
            logger.info("✅ All integration components initialized successfully")
            return components
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize integration components: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_websocket_to_database_flow(self, setup_integration_components):
        """Test complete flow: WebSocket → Database → Raw Data Intelligence"""
        components = await setup_integration_components
        
        # Track data flow
        collected_data = []
        stored_data = []
        
        async def data_callback(market_data: Dict[str, Any]):
            """Callback to handle incoming market data and store it"""
            collected_data.append(market_data)
            logger.info(f"📊 Received market data: {market_data.get('symbol', 'unknown')} - ${market_data.get('close', 0)}")
            
            # Process and store the data
            try:
                success = await components['market_data_processor'].process_ohlcv_data(market_data)
                if success:
                    stored_data.append(market_data)
                    logger.info(f"💾 Stored market data for {market_data.get('symbol', 'unknown')}")
                else:
                    logger.warning(f"⚠️ Failed to store market data for {market_data.get('symbol', 'unknown')}")
            except Exception as e:
                logger.error(f"❌ Error storing market data: {e}")
        
        try:
            # Set up WebSocket client with data callback
            components['websocket_client'].set_data_callback(data_callback)
            
            # Connect to WebSocket
            connected = await components['websocket_client'].connect()
            assert connected, "Failed to connect to Hyperliquid WebSocket"
            
            # Subscribe to market data
            await components['websocket_client'].subscribe_to_market_data()
            
            # Start listening for data (run for 20 seconds to collect real data)
            logger.info("🔄 Collecting and storing real market data for 20 seconds...")
            listen_task = asyncio.create_task(components['websocket_client'].listen_for_data())
            
            # Wait for data collection and storage
            await asyncio.sleep(20)
            
            # Stop listening
            listen_task.cancel()
            await components['websocket_client'].disconnect()
            
            # Verify we collected and stored data
            assert len(collected_data) > 0, "No market data collected from WebSocket"
            assert len(stored_data) > 0, "No market data stored in database"
            logger.info(f"✅ Collected {len(collected_data)} data points, stored {len(stored_data)}")
            
            # Verify data is in the database
            logger.info("🔍 Verifying data in database...")
            
            # Get recent data from database
            recent_data = components['supabase_manager'].client.table('alpha_market_data_1m').select('*').gte(
                'timestamp', (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
            ).order('timestamp', desc=True).limit(10).execute()
            
            assert recent_data.data is not None, "No recent data found in database"
            assert len(recent_data.data) > 0, "Database query returned no results"
            logger.info(f"✅ Found {len(recent_data.data)} recent records in database")
            
            # Test Raw Data Intelligence Agent reading from database
            logger.info("🧠 Testing Raw Data Intelligence Agent...")
            
            # Get market data for analysis
            market_data_df = await components['raw_data_agent']._get_recent_market_data()
            
            if market_data_df is not None and not market_data_df.empty:
                logger.info(f"✅ Raw Data Agent retrieved {len(market_data_df)} data points")
                
                # Test analysis
                analysis_results = await components['raw_data_agent']._analyze_raw_data(market_data_df)
                assert analysis_results is not None, "Raw data analysis failed"
                logger.info(f"✅ Raw data analysis completed: {len(analysis_results.get('signals', []))} signals")
            else:
                logger.warning("⚠️ No market data available for Raw Data Agent analysis")
            
            logger.info("🎉 WebSocket to database integration test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ WebSocket to database integration test failed: {e}")
            raise
        finally:
            # Cleanup
            if components['websocket_client'].is_connected:
                await components['websocket_client'].disconnect()
    
    @pytest.mark.asyncio
    async def test_market_data_processor_storage(self, setup_integration_components):
        """Test MarketDataProcessor storage functionality"""
        components = await setup_integration_components
        
        try:
            # Create test market data
            test_data = {
                'symbol': 'BTC',
                'timestamp': datetime.now(timezone.utc),
                'open': 50000.0,
                'high': 51000.0,
                'low': 49500.0,
                'close': 50500.0,
                'volume': 1000.0,
                'data_quality_score': 1.0,
                'source': 'test',
                'created_at': datetime.now(timezone.utc)
            }
            
            # Test data preparation
            logger.info("🔧 Testing data preparation...")
            db_data = components['market_data_processor'].prepare_db_data(test_data)
            assert db_data is not None, "Data preparation failed"
            assert db_data['symbol'] == 'BTC', "Symbol not preserved"
            assert db_data['close'] == 50500.0, "Close price not preserved"
            logger.info("✅ Data preparation successful")
            
            # Test data storage
            logger.info("💾 Testing data storage...")
            success = components['market_data_processor'].store_market_data(db_data)
            assert success, "Data storage failed"
            logger.info("✅ Data storage successful")
            
            # Verify data was stored
            logger.info("🔍 Verifying stored data...")
            stored_data = components['supabase_manager'].client.table('alpha_market_data_1m').select('*').eq(
                'symbol', 'BTC'
            ).order('timestamp', desc=True).limit(1).execute()
            
            assert stored_data.data is not None, "No data found after storage"
            assert len(stored_data.data) > 0, "Storage verification failed"
            assert stored_data.data[0]['close'] == 50500.0, "Stored data doesn't match input"
            logger.info("✅ Data storage verification successful")
            
            logger.info("🎉 MarketDataProcessor storage test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ MarketDataProcessor storage test failed: {e}")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
