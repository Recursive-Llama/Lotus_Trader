#!/usr/bin/env python3
"""
Simple Price Collection Test

Just run the scheduled price collector on existing active positions and see if it works.
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


async def test_price_collection():
    """Test price collection on existing active positions"""
    print("🧪 Simple Price Collection Test")
    print("=" * 40)
    
    try:
        # Initialize components
        print("1. Initializing components...")
        supabase_manager = SupabaseManager()
        price_oracle = PriceOracle()
        price_collector = ScheduledPriceCollector(supabase_manager, price_oracle)
        
        # Get active positions
        print("\n2. Getting active positions...")
        result = supabase_manager.client.table('lowcap_positions').select(
            'id', 'token_contract', 'token_chain', 'token_ticker'
        ).eq('status', 'active').execute()
        
        if not result.data:
            print("❌ No active positions found")
            return
        
        print(f"✅ Found {len(result.data)} active positions:")
        for pos in result.data:
            print(f"   - {pos['token_ticker']} ({pos['token_contract'][:8]}...) on {pos['token_chain']}")
        
        # Run price collection
        print("\n3. Running price collection...")
        await price_collector._collect_prices_for_active_positions()
        print("✅ Price collection completed")
        
        # Check if data was stored
        print("\n4. Checking stored data...")
        for pos in result.data:
            token_contract = pos['token_contract']
            chain = pos['token_chain']
            
            price_result = supabase_manager.client.table('lowcap_price_data_1m').select('*').eq(
                'token_contract', token_contract
            ).eq('chain', chain).order('timestamp', desc=True).limit(1).execute()
            
            if price_result.data:
                price_data = price_result.data[0]
                print(f"✅ {pos['token_ticker']}: ${price_data.get('price_usd', 'N/A')} USD")
            else:
                print(f"❌ {pos['token_ticker']}: No price data found")
        
        print("\n🎉 Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_price_collection())
