#!/usr/bin/env python3
"""
Test WalletManager USDC balance fetching after fix.
Run: python src/tests/test_wallet_manager_usdc.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

async def test_wallet_manager_usdc():
    """Test WalletManager USDC balance fetching"""
    print("=" * 60)
    print("Testing WalletManager USDC Balance Fetching")
    print("=" * 60)
    
    from trading.wallet_manager import WalletManager
    
    # Create WalletManager (should initialize JSSolanaClient)
    print("\n1. Creating WalletManager...")
    wallet_manager = WalletManager()
    print("   ✅ WalletManager created")
    
    # Check if JSSolanaClient was initialized
    if wallet_manager.js_solana_client:
        print("   ✅ JSSolanaClient initialized")
    else:
        print("   ❌ JSSolanaClient not initialized")
        return
    
    # Get wallet address
    wallet_address = wallet_manager.get_wallet_address('solana')
    print(f"\n2. Wallet address: {wallet_address}")
    
    # Test SOL balance (should work)
    print("\n3. Testing SOL balance...")
    try:
        sol_balance = await wallet_manager.get_balance('solana', None)
        print(f"   ✅ SOL balance: {sol_balance:.6f} SOL")
    except Exception as e:
        print(f"   ❌ SOL balance error: {e}")
        return
    
    # Test USDC balance (this is what we're fixing)
    print("\n4. Testing USDC balance...")
    usdc_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
    try:
        usdc_balance = await wallet_manager.get_balance('solana', usdc_address)
        if usdc_balance is not None:
            print(f"   ✅ USDC balance: {usdc_balance:.6f} USDC")
            print(f"   ✅ USDC balance in USD: ${usdc_balance:.2f}")
        else:
            print("   ❌ USDC balance returned None")
    except Exception as e:
        print(f"   ❌ USDC balance error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_wallet_manager_usdc())

