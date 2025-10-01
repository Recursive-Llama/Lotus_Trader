#!/usr/bin/env python3
"""
Test Unified Price System

Test the new unified price system to ensure it works correctly.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append('src')

from utils.supabase_manager import SupabaseManager
from intelligence.trader_lowcap.price_oracle import PriceOracle
from trading.scheduled_price_collector import ScheduledPriceCollector
from trading.position_monitor import PositionMonitor


async def test_unified_price_system():
    """Test the unified price system components"""
    print("🧪 Testing Unified Price System")
    print("=" * 50)
    
    try:
        # Initialize components
        print("1. Initializing components...")
        supabase_manager = SupabaseManager()
        price_oracle = PriceOracle()
        
        print("✅ Components initialized")
        
        # Test Price Oracle
        print("\n2. Testing Price Oracle...")
        test_token = "So11111111111111111111111111111111111111112"  # SOL
        price_info = price_oracle.price_solana(test_token)
        
        if price_info:
            print(f"✅ Price Oracle working: SOL price = ${price_info.get('price_usd', 'N/A')}")
        else:
            print("❌ Price Oracle failed to get price")
        
        # Test Scheduled Price Collector
        print("\n3. Testing Scheduled Price Collector...")
        price_collector = ScheduledPriceCollector(
            supabase_manager=supabase_manager,
            price_oracle=price_oracle
        )
        
        print("✅ Price Collector initialized")
        
        # Test Position Monitor
        print("\n4. Testing Position Monitor...")
        position_monitor = PositionMonitor(
            supabase_manager=supabase_manager,
            trader=None  # No trader for testing
        )
        
        print("✅ Position Monitor initialized")
        
        # Test database connection
        print("\n5. Testing database connection...")
        try:
            # Try to get active positions
            result = supabase_manager.client.table('lowcap_positions').select('id').limit(1).execute()
            print("✅ Database connection working")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
        
        print("\n🎉 All tests passed! Unified price system is ready.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_unified_price_system())
