#!/usr/bin/env python3
"""
Test script for native balance tracking
- Tests the _store_native_balance method
- Populates initial current values for all chains
- Verifies database storage
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.append('src')

from src.communication.direct_table_communicator import DirectTableCommunicator
from src.intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
from src.trading.wallet_manager import WalletManager
from src.intelligence.trader_lowcap.price_oracle import PriceOracle

async def test_native_balance_tracking():
    """Test native balance tracking functionality"""
    
    print("🧪 Testing Native Balance Tracking")
    print("=" * 50)
    
    try:
        # Initialize components
        print("📡 Initializing components...")
        db_manager = DirectTableCommunicator()
        wallet_manager = WalletManager()
        price_oracle = PriceOracle()
        
        # Initialize trader
        trader = TraderLowcapSimpleV2(db_manager)
        
        # Test chains
        chains = ['solana', 'ethereum', 'base', 'bsc']
        
        print(f"\n🔍 Checking native balances for {len(chains)} chains...")
        
        for chain in chains:
            print(f"\n--- {chain.upper()} ---")
            
            try:
                # Get current balance
                balance = await wallet_manager.get_balance(chain)
                
                if balance is not None:
                    balance_float = float(balance)
                    print(f"✅ {chain.upper()} balance: {balance_float:.6f}")
                    
                    # Test storing the balance
                    await trader._store_native_balance(chain, balance_float)
                    print(f"💾 Stored {chain.upper()} balance in database")
                    
                else:
                    print(f"❌ Could not get {chain.upper()} balance")
                    
            except Exception as e:
                print(f"❌ Error with {chain.upper()}: {e}")
        
        # Verify database storage
        print(f"\n🔍 Verifying database storage...")
        
        for chain in chains:
            try:
                result = db_manager.db_manager.client.table('wallet_balances').select('*').eq('chain', chain).execute()
                
                if result.data:
                    data = result.data[0]
                    print(f"✅ {chain.upper()}: {data['balance']:.6f} tokens, ${data.get('balance_usd', 'N/A'):.2f} USD")
                    print(f"   Wallet: {data.get('wallet_address', 'N/A')}")
                    print(f"   Updated: {data.get('last_updated', 'N/A')}")
                else:
                    print(f"❌ No data found for {chain.upper()}")
                    
            except Exception as e:
                print(f"❌ Error querying {chain.upper()}: {e}")
        
        # Show all balances
        print(f"\n📊 All stored balances:")
        try:
            all_balances = db_manager.db_manager.client.table('wallet_balances').select('*').execute()
            
            if all_balances.data:
                total_usd = 0
                for balance in all_balances.data:
                    chain = balance['chain']
                    bal = balance['balance']
                    usd = balance.get('balance_usd', 0) or 0
                    total_usd += usd
                    
                    print(f"  {chain.upper()}: {bal:.6f} tokens (${usd:.2f})")
                
                print(f"\n💰 Total portfolio value: ${total_usd:.2f}")
            else:
                print("❌ No balances found in database")
                
        except Exception as e:
            print(f"❌ Error querying all balances: {e}")
        
        print(f"\n✅ Native balance tracking test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function"""
    print("🚀 Starting Native Balance Tracking Test")
    print("This will:")
    print("1. Check native balances for all chains")
    print("2. Store them in the wallet_balances table")
    print("3. Verify the data was stored correctly")
    print("4. Show total portfolio value")
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('src'):
        print("❌ Please run this script from the project root directory")
        return
    
    await test_native_balance_tracking()

if __name__ == "__main__":
    asyncio.run(main())
