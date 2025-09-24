#!/usr/bin/env python3
"""
Test the exact production flow to see where USD prices are being used
"""

import sys
import os
sys.path.append('src')

from dotenv import load_dotenv
load_dotenv()

from intelligence.trader_lowcap.price_oracle import PriceOracle
from intelligence.trader_lowcap.entry_exit_planner import EntryExitPlanner

def test_production_flow():
    """Test the exact production flow"""
    
    token_address = "0xc56C7A0eAA804f854B536A5F3D5f49D2EC4B12b8"
    
    print(f"Testing production flow for token: {token_address}")
    print("=" * 60)
    
    # Initialize Price Oracle (same as production)
    price_oracle = PriceOracle()
    
    # Test the exact line from trader_lowcap_simple_v2.py line 129-130
    print("1. Testing Price Oracle call...")
    price_info = price_oracle.price_eth(token_address)
    print(f"   price_info = {price_info}")
    
    if price_info:
        print(f"   price_info['price_native'] = {price_info['price_native']}")
        print(f"   price_info['price_usd'] = {price_info['price_usd']}")
        
        # Test the exact line from trader_lowcap_simple_v2.py line 130
        price = price_info['price_native'] if price_info else None
        print(f"   price = {price}")
        
        # Test the exact line from trader_lowcap_simple_v2.py line 203
        alloc_native = 0.000209373  # Sample allocation
        entries = EntryExitPlanner.build_entries(price, alloc_native)
        
        print(f"\n2. Generated entries:")
        for entry in entries:
            print(f"   Entry {entry['entry_number']}: price={entry['price']}, amount_native={entry['amount_native']}")
        
        # Check if this matches the database
        print(f"\n3. Database comparison:")
        print(f"   Database Entry 1: price=0.00007314")
        print(f"   Generated Entry 1: price={entries[0]['price']}")
        
        if abs(entries[0]['price'] - 0.00007314) < 0.000001:
            print("   ✅ MATCH: Generated entry matches database")
        else:
            print("   ❌ MISMATCH: Generated entry does NOT match database")
            
        # Check if the generated price looks like USD
        if entries[0]['price'] > 0.00001:
            print("   ⚠️  WARNING: Generated price looks like USD, not ETH!")
        else:
            print("   ✅ Generated price looks like ETH")
            
    else:
        print("   ❌ Price Oracle returned None")

if __name__ == "__main__":
    test_production_flow()
