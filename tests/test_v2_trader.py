#!/usr/bin/env python3
"""
Test V2 trader with Base trading
"""

import sys
import os
import asyncio
sys.path.append('src')

from utils.supabase_manager import SupabaseManager
from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2

async def test_v2_trader():
    """Test V2 trader with Base trading"""
    
    # Initialize components
    supabase_manager = SupabaseManager()
    
    # Initialize trader
    trader = TraderLowcapSimpleV2(
        supabase_manager=supabase_manager,
        config={}
    )
    
    print("🚀 Testing V2 Trader with Base trading")
    
    # Test balance
    print("\n💰 Testing wallet balance...")
    balance = await trader.wallet_manager.get_balance('base')
    if balance:
        print(f"   ✅ Base ETH balance: {balance:.6f} ETH")
    else:
        print("   ❌ Could not get Base ETH balance")
        return
    
    # Test price oracle
    print("\n🔍 Testing price oracle...")
    test_contract = '0x696F9436B67233384889472Cd7cD58A6fB5DF4f1'
    try:
        price_usd = trader.price_oracle.price_base(test_contract)
        if price_usd:
            print(f"   ✅ PriceOracle USD price: ${price_usd:.6f} USD per token")
            # Convert to ETH (assuming ETH = $4180)
            eth_usd_price = 4180
            price_eth = price_usd / eth_usd_price
            print(f"   ✅ PriceOracle ETH price: {price_eth:.10f} ETH per token")
        else:
            print("   ❌ PriceOracle price lookup failed")
    except Exception as e:
        print(f"   ❌ PriceOracle error: {e}")
    
    # Test venue resolution
    print("\n🔍 Testing venue resolution...")
    try:
        venue = trader._resolve_base_venue(test_contract)
        print(f"   ✅ Venue resolved: {venue}")
    except Exception as e:
        print(f"   ❌ Venue resolution error: {e}")
    
    # Test Base executor directly
    print("\n🔍 Testing Base executor...")
    if trader.base_executor:
        try:
            # Test with 0.0005 ETH as requested
            test_amount = 0.0005  # 0.0005 ETH
            print(f"   Testing with {test_amount} ETH...")
            result = trader.base_executor.execute_buy(test_contract, test_amount)
            if result:
                print(f"   ✅ Base executor success: {result}")
            else:
                print("   ❌ Base executor failed")
        except Exception as e:
            print(f"   ❌ Base executor error: {e}")
    else:
        print("   ❌ Base executor not available")
    
    # Test full decision execution
    print("\n🔄 Testing full decision execution...")
    decision = {
        'id': 'test_decision_123',
        'content': {
            'action': 'approve',
            'allocation_pct': 1.0,  # 1% allocation
            'curator_id': 'test_curator'
        },
        'signal_pack': {
            'token': {
                'ticker': 'TEST',
                'contract': test_contract,
                'chain': 'base'
            }
        }
    }
    
    try:
        result = await trader.execute_decision(decision)
        if result:
            print(f"   ✅ Decision execution success: {result}")
        else:
            print("   ❌ Decision execution failed")
    except Exception as e:
        print(f"   ❌ Decision execution error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_v2_trader())
