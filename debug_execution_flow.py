#!/usr/bin/env python3
"""
Debug script to trace the exact execution flow that creates wrong entries
"""

import sys
import os
sys.path.append('src')

from dotenv import load_dotenv
load_dotenv()

import asyncio
from datetime import datetime, timezone

# Mock the supabase manager to avoid database calls
class MockSupabaseManager:
    def __init__(self):
        self.positions_created = []
        self.entries_updated = []
    
    def create_position(self, position):
        print(f"🔍 MockSupabaseManager.create_position called with:")
        print(f"   position_id: {position.get('id')}")
        print(f"   token_contract: {position.get('token_contract')}")
        print(f"   token_chain: {position.get('token_chain')}")
        self.positions_created.append(position)
        return True
    
    def update_entries(self, position_id, entries):
        print(f"🔍 MockSupabaseManager.update_entries called with:")
        print(f"   position_id: {position_id}")
        print(f"   entries: {entries}")
        self.entries_updated.append((position_id, entries))
        return True

async def debug_execution_flow():
    """Debug the exact execution flow that creates wrong entries"""
    
    print("🔍 Debugging execution flow for token: 0xc56C7A0eAA804f854B536A5F3D5f49D2EC4B12b8")
    print("=" * 80)
    
    # Create mock supabase manager
    mock_supabase = MockSupabaseManager()
    
    # Import and initialize the trader
    from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
    
    trader_config = {
        'book_id': 'social',
        'book_nav': 100000.0,
        'max_position_size_pct': 2.0,
        'entry_strategy': 'three_entry',
        'exit_strategy': 'staged_exit'
    }
    
    trader = TraderLowcapSimpleV2(mock_supabase, trader_config)
    
    # Mock the price oracle to return the exact same data as our test
    def mock_price_eth(contract):
        print(f"🔍 Mock price_eth called for contract: {contract}")
        return {
            'price_native': 0.00000001726,  # This is the correct ETH price
            'price_usd': 0.00007212,        # This is the USD price
            'quote_token': 'WETH'
        }
    
    # Replace the price oracle method
    trader.price_oracle.price_eth = mock_price_eth
    
    # Mock wallet balance
    trader.wallet_manager = type('MockWalletManager', (), {
        'get_balance': lambda self, chain: 0.1  # Mock 0.1 ETH balance
    })()
    
    # Create a mock decision
    decision = {
        'id': 'test_decision_123',
        'content': {
            'token': {
                'ticker': 'TEST',
                'contract': '0xc56C7A0eAA804f854B536A5F3D5f49D2EC4B12b8',
                'chain': 'ethereum'
            },
            'allocation_pct': 0.5,  # 0.5% allocation
            'curator_id': 'test_curator'
        }
    }
    
    print(f"\n📋 Mock decision created:")
    print(f"   token: {decision['content']['token']['ticker']}")
    print(f"   contract: {decision['content']['token']['contract']}")
    print(f"   chain: {decision['content']['token']['chain']}")
    print(f"   allocation_pct: {decision['content']['allocation_pct']}%")
    
    # Execute the decision
    print(f"\n🚀 Executing decision...")
    try:
        result = await trader.execute_decision(decision)
        print(f"\n📊 Execution result: {result}")
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        result = None
    
    # Check what was stored in the database
    if mock_supabase.entries_updated:
        print(f"\n🔍 Database entries that would be stored:")
        for position_id, entries in mock_supabase.entries_updated:
            print(f"   Position ID: {position_id}")
            for entry in entries:
                print(f"   Entry {entry['entry_number']}: price={entry['price']}, amount_native={entry['amount_native']}")
                
                # Check if this matches the wrong database values
                if entry['entry_number'] == 1:
                    if abs(entry['price'] - 0.00007314) < 0.000001:
                        print(f"   ❌ BUG CONFIRMED: Entry 1 price matches wrong database value (USD price)")
                    elif abs(entry['price'] - 0.00000001726) < 0.000001:
                        print(f"   ✅ Entry 1 price is correct (native ETH price)")
                    else:
                        print(f"   ❓ Entry 1 price is neither USD nor native - unexpected value")
    
    print(f"\n🔍 Analysis complete!")

if __name__ == "__main__":
    asyncio.run(debug_execution_flow())
