#!/usr/bin/env python3
"""
Phase 1.2 Test: Market Data Collection
Test Hyperliquid WebSocket connection and market data storage
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timezone

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from market_data_collector import MarketDataCollector
from core_detection.market_data_processor import MarketDataProcessor
from utils.supabase_manager import SupabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_market_data_collection():
    """Test complete market data collection pipeline"""
    print("\n🧪 Phase 1.2: Market Data Collection Test")
    print("=" * 60)
    
    try:
        # Test 1: Database connection
        print("\n1️⃣ Testing database connection...")
        db_manager = SupabaseManager()
        if db_manager.test_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
        
        # Test 2: Market data table check
        print("\n2️⃣ Testing market data table...")
        processor = MarketDataProcessor(db_manager)
        try:
            count = processor.get_market_data_count()
            print(f"✅ Market data table accessible: {count} records")
        except Exception as e:
            print(f"❌ Market data table error: {e}")
            return False
        
        # Test 3: WebSocket client creation
        print("\n3️⃣ Testing WebSocket client creation...")
        collector = MarketDataCollector(['BTC', 'ETH', 'SOL'])
        print("✅ WebSocket client created successfully")
        
        # Test 4: Data quality validation
        print("\n4️⃣ Testing data quality validation...")
        test_data = {
            'symbol': 'BTC',
            'timestamp': datetime.now(timezone.utc),
            'open': 50000.0,
            'high': 51000.0,
            'low': 49000.0,
            'close': 50500.0,
            'volume': 100.0,
            'data_quality_score': 1.0,
            'source': 'test'
        }
        
        success = await processor.process_ohlcv_data(test_data)
        if success:
            print("✅ Data quality validation and storage successful")
        else:
            print("❌ Data quality validation or storage failed")
            return False
        
        # Test 5: Retrieve stored data
        print("\n5️⃣ Testing data retrieval...")
        recent_data = processor.get_recent_market_data('BTC', limit=5)
        if recent_data:
            print(f"✅ Retrieved {len(recent_data)} recent records")
            print(f"   Latest BTC price: {recent_data[0]['close']}")
        else:
            print("❌ Failed to retrieve data")
            return False
        
        # Test 6: Processing statistics
        print("\n6️⃣ Testing processing statistics...")
        stats = processor.get_processing_stats()
        print(f"✅ Processing stats: {stats}")
        
        print("\n" + "=" * 60)
        print("✅ ALL PHASE 1.2 TESTS PASSED!")
        print("🎉 Market data collection system is fully functional!")
        print("🚀 Ready to proceed to Phase 1.3 (Basic Signal Detection)")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

async def test_short_collection():
    """Test a short market data collection run"""
    print("\n🔄 Testing short market data collection (10 seconds)...")
    
    collector = MarketDataCollector(['BTC'])
    
    # Start collection in background
    collection_task = asyncio.create_task(collector.start_collection())
    
    # Wait for 10 seconds
    await asyncio.sleep(10)
    
    # Stop collection
    await collector.stop_collection()
    collection_task.cancel()
    
    # Check results
    stats = collector.data_processor.get_processing_stats()
    print(f"Collection stats: {stats}")
    
    if stats['processed_count'] > 0:
        print("✅ Short collection test successful!")
        return True
    else:
        print("❌ No data collected during test")
        return False

async def main():
    """Main test function"""
    print("Alpha Detector Phase 1.2 Test Suite")
    print("Testing market data collection from Hyperliquid WebSocket")
    
    # Run basic tests
    basic_tests_passed = await test_market_data_collection()
    
    if basic_tests_passed:
        # Run short collection test
        collection_test_passed = await test_short_collection()
        
        if collection_test_passed:
            print("\n🎉 ALL TESTS PASSED! Phase 1.2 is complete!")
        else:
            print("\n⚠️ Basic tests passed but collection test failed")
    else:
        print("\n❌ Basic tests failed")

if __name__ == "__main__":
    asyncio.run(main())
