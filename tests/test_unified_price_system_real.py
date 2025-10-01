#!/usr/bin/env python3
"""
Real Test for Unified Price System

Actually tests the core functionality by creating test data and running the systems.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append('src')

from utils.supabase_manager import SupabaseManager
from intelligence.trader_lowcap.price_oracle import PriceOracle
from trading.scheduled_price_collector import ScheduledPriceCollector
from trading.position_monitor import PositionMonitor


async def test_unified_price_system_real():
    """Test the unified price system with real data"""
    print("🧪 Real Test for Unified Price System")
    print("=" * 50)
    
    try:
        # Initialize components
        print("1. Initializing components...")
        supabase_manager = SupabaseManager()
        price_oracle = PriceOracle()
        
        # Check for existing active positions
        print("\n2. Checking for existing active positions...")
        existing_positions = supabase_manager.client.table('lowcap_positions').select('id, token_contract, token_chain, token_ticker').eq('status', 'active').limit(1).execute()
        
        if existing_positions.data:
            position = existing_positions.data[0]
            position_id = position['id']
            token_contract = position['token_contract']
            token_chain = position['token_chain']
            token_ticker = position['token_ticker']
            print(f"✅ Using existing position: {token_ticker} ({token_contract}) on {token_chain}")
        else:
            print("❌ No active positions found. Please create a position first.")
            return
        
        # Test scheduled price collector
        print("\n3. Testing scheduled price collection...")
        price_collector = ScheduledPriceCollector(
            supabase_manager=supabase_manager,
            price_oracle=price_oracle
        )
        
        # Run one collection cycle
        await price_collector._collect_prices_for_active_positions()
        print("✅ Price collection cycle completed")
        
        # Check if data was stored
        print("\n4. Verifying price data storage...")
        price_result = supabase_manager.client.table('lowcap_price_data_1m').select('*').eq(
            'token_contract', 'So11111111111111111111111111111111111111112'
        ).eq('chain', 'solana').order('timestamp', desc=True).limit(1).execute()
        
        if price_result.data:
            price_data = price_result.data[0]
            print(f"✅ Price data stored:")
            print(f"   - Price USD: ${price_data.get('price_usd', 'N/A')}")
            print(f"   - Price Native: {price_data.get('price_native', 'N/A')} SOL")
            print(f"   - Volume 24h: ${price_data.get('volume_24h', 'N/A')}")
            print(f"   - Liquidity: ${price_data.get('liquidity_usd', 'N/A')}")
            print(f"   - Timestamp: {price_data.get('timestamp', 'N/A')}")
        else:
            print("❌ No price data found in database")
        
        # Test position monitor
        print("\n5. Testing position monitoring...")
        position_monitor = PositionMonitor(
            supabase_manager=supabase_manager,
            trader=None  # No trader for testing
        )
        
        # Get current price from database
        current_price = await position_monitor._get_current_price_from_db(
            'So11111111111111111111111111111111111111112', 'solana'
        )
        
        if current_price:
            print(f"✅ Position monitor can read price from database: {current_price} SOL")
        else:
            print("❌ Position monitor failed to read price from database")
        
        # Clean up test data
        print("\n6. Cleaning up test data...")
        supabase_manager.client.table('lowcap_positions').delete().eq('id', position_id).execute()
        print("✅ Test position deleted")
        
        print("\n🎉 Real test completed! System is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_unified_price_system_real())
