#!/usr/bin/env python3
"""
Isolated test for wallet balance bootstrapping.
Run: python src/tests/test_wallet_bootstrap.py
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from datetime import datetime, timezone


async def test_wallet_bootstrap():
    """Test wallet balance collection and writing."""
    print("Testing wallet balance bootstrap...")
    
    # 1. Test database connection
    print("\n1. Testing database connection...")
    try:
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        print("   ✓ Supabase connected")
    except Exception as e:
        print(f"   ✗ Supabase connection failed: {e}")
        return
    
    # 2. Test wallet_balances table exists
    print("\n2. Testing wallet_balances table...")
    try:
        result = sb.table("wallet_balances").select("*").limit(0).execute()
        print("   ✓ wallet_balances table exists")
    except Exception as e:
        print(f"   ✗ wallet_balances table error: {e}")
        return
    
    # 3. Test WalletManager creation
    print("\n3. Testing WalletManager creation...")
    try:
        from trading.wallet_manager import WalletManager
        wallet_manager = WalletManager()
        print("   ✓ WalletManager created")
    except Exception as e:
        print(f"   ✗ WalletManager creation failed: {e}")
        print("   (This is OK - wallet balances can be collected later)")
        return
    
    # 4. Test balance collection for Solana
    print("\n4. Testing Solana balance collection...")
    try:
        sol_balance = await wallet_manager.get_balance("solana", None)
        print(f"   ✓ Solana balance: {sol_balance}")
        
        # Try wallet address
        sol_address = wallet_manager.get_wallet_address("solana")
        print(f"   ✓ Solana address: {sol_address[:8]}...{sol_address[-8:]}")
    except Exception as e:
        print(f"   ✗ Solana balance error: {e}")
    
    # 5. Test USDC balance
    print("\n5. Testing USDC balance...")
    try:
        usdc_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
        usdc_balance = await wallet_manager.get_balance("solana", usdc_address)
        print(f"   ✓ USDC balance: {usdc_balance}")
    except Exception as e:
        print(f"   ✗ USDC balance error: {e}")
    
    # 6. Test writing to database
    print("\n6. Testing database write...")
    try:
        test_data = {
            'chain': 'solana',
            'balance': float(sol_balance) if sol_balance else 0.0,
            'usdc_balance': float(usdc_balance) if usdc_balance else 0.0,
            'wallet_address': sol_address if sol_address else '',
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        sb.table('wallet_balances').upsert([test_data]).execute()
        print(f"   ✓ Wrote wallet balance to database")
    except Exception as e:
        print(f"   ✗ Database write error: {e}")
    
    # 7. Verify data was written
    print("\n7. Verifying data...")
    try:
        result = sb.table("wallet_balances").select("*").eq("chain", "solana").execute()
        if result.data:
            row = result.data[0]
            print(f"   ✓ Data verified:")
            print(f"      Balance: {row.get('balance')}")
            print(f"      USDC: {row.get('usdc_balance')}")
            print(f"      Updated: {row.get('last_updated')}")
        else:
            print("   ✗ No data found")
    except Exception as e:
        print(f"   ✗ Verification error: {e}")
    
    print("\n✓ Wallet bootstrap test complete")


if __name__ == "__main__":
    asyncio.run(test_wallet_bootstrap())

