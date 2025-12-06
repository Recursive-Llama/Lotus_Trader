#!/usr/bin/env python3
"""
Isolated test for USDC balance fetching on Solana.
Run: python src/tests/test_usdc_balance.py

This tests USDC balance fetching in isolation before integrating into WalletManager.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# USDC mint address on Solana
USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'


async def test_sol_balance_python():
    """Test SOL balance using Python Solana RPC (this works)"""
    print("\n=== Test 1: SOL Balance (Python RPC) ===")
    try:
        from solana.rpc.api import Client
        from solders.pubkey import Pubkey as PublicKey
        
        # Get RPC URL
        helius_key = os.getenv('HELIUS_API_KEY')
        if helius_key:
            rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
        else:
            rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        
        print(f"RPC URL: {rpc_url.replace(helius_key if helius_key else '', '***') if helius_key else rpc_url}")
        
        # Get wallet address
        private_key = os.getenv('SOL_WALLET_PRIVATE_KEY')
        if not private_key:
            print("❌ SOL_WALLET_PRIVATE_KEY not found in .env")
            return None
        
        # Load wallet to get address
        from trading.wallet_manager import WalletManager
        wallet_manager = WalletManager()
        wallet_address = wallet_manager.get_wallet_address('solana')
        
        if not wallet_address:
            print("❌ Could not get wallet address")
            return None
        
        print(f"Wallet address: {wallet_address}")
        
        # Get SOL balance
        client = Client(rpc_url)
        pubkey = PublicKey.from_string(wallet_address)
        balance_result = client.get_balance(pubkey)
        
        if balance_result.value is not None:
            sol_balance = balance_result.value / 1e9
            print(f"✅ SOL balance: {sol_balance:.6f} SOL")
            return sol_balance
        else:
            print("❌ Failed to get SOL balance")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_usdc_balance_js():
    """Test USDC balance using JSSolanaClient (what we need to fix)"""
    print("\n=== Test 2: USDC Balance (JSSolanaClient) ===")
    try:
        # Get RPC URL
        helius_key = os.getenv('HELIUS_API_KEY')
        if helius_key:
            rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
        else:
            rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        
        print(f"RPC URL: {rpc_url.replace(helius_key if helius_key else '', '***') if helius_key else rpc_url}")
        
        # Get private key
        private_key = os.getenv('SOL_WALLET_PRIVATE_KEY')
        if not private_key:
            print("❌ SOL_WALLET_PRIVATE_KEY not found in .env")
            return None
        
        print(f"Private key format: {private_key[:20]}... (length: {len(private_key)})")
        
        # Get wallet address
        from trading.wallet_manager import WalletManager
        wallet_manager = WalletManager()
        wallet_address = wallet_manager.get_wallet_address('solana')
        
        if not wallet_address:
            print("❌ Could not get wallet address")
            return None
        
        print(f"Wallet address: {wallet_address}")
        
        # Create JSSolanaClient directly (no trader dependency)
        from trading.js_solana_client import JSSolanaClient
        js_client = JSSolanaClient(rpc_url=rpc_url, private_key=private_key)
        
        print(f"USDC mint: {USDC_MINT}")
        print("Calling get_spl_token_balance...")
        
        # Get USDC balance
        result = await js_client.get_spl_token_balance(USDC_MINT, wallet_address)
        
        print(f"Result: {result}")
        
        if result.get('success'):
            balance = result.get('balance', '0')
            print(f"✅ USDC balance: {balance} USDC")
            return float(balance)
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Failed to get USDC balance: {error}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_usdc_balance_python_rpc():
    """Test USDC balance using Python Solana RPC directly (alternative approach)"""
    print("\n=== Test 3: USDC Balance (Python RPC - Alternative) ===")
    try:
        from solana.rpc.api import Client
        from solders.pubkey import Pubkey as PublicKey
        
        # Get RPC URL
        helius_key = os.getenv('HELIUS_API_KEY')
        if helius_key:
            rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
        else:
            rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        
        # Get wallet address
        from trading.wallet_manager import WalletManager
        wallet_manager = WalletManager()
        wallet_address = wallet_manager.get_wallet_address('solana')
        
        if not wallet_address:
            print("❌ Could not get wallet address")
            return None
        
        print(f"Wallet address: {wallet_address}")
        print(f"USDC mint: {USDC_MINT}")
        
        # Try to get token accounts using Python RPC
        client = Client(rpc_url)
        wallet_pubkey = PublicKey.from_string(wallet_address)
        usdc_mint_pubkey = PublicKey.from_string(USDC_MINT)
        
        # Get token accounts by owner
        # Note: This requires the SPL Token program ID
        spl_token_program = PublicKey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
        
        print("Calling get_token_accounts_by_owner...")
        token_accounts = client.get_token_accounts_by_owner(
            wallet_pubkey,
            {"mint": usdc_mint_pubkey}
        )
        
        if token_accounts.value:
            # Parse balance from token account data
            account = token_accounts.value[0]
            account_data = account.account.data
            
            # Amount is at offset 64-72 (8 bytes, little-endian)
            import struct
            amount_bytes = account_data[64:72]
            amount = struct.unpack('<Q', amount_bytes)[0]  # Q = unsigned long long (8 bytes)
            
            # USDC has 6 decimals
            usdc_balance = amount / 1e6
            print(f"✅ USDC balance (Python RPC): {usdc_balance:.6f} USDC")
            return usdc_balance
        else:
            print("⚠️  No USDC token account found (wallet may have 0 USDC)")
            return 0.0
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all tests"""
    print("=" * 60)
    print("USDC Balance Test - Isolated")
    print("=" * 60)
    
    # Check environment
    print("\n📋 Environment Check:")
    has_helius = bool(os.getenv('HELIUS_API_KEY'))
    has_rpc = bool(os.getenv('SOLANA_RPC_URL'))
    has_key = bool(os.getenv('SOL_WALLET_PRIVATE_KEY'))
    
    print(f"  HELIUS_API_KEY: {'✅' if has_helius else '❌'}")
    print(f"  SOLANA_RPC_URL: {'✅' if has_rpc else '❌ (will use public RPC)'}")
    print(f"  SOL_WALLET_PRIVATE_KEY: {'✅' if has_key else '❌'}")
    
    if not has_key:
        print("\n❌ SOL_WALLET_PRIVATE_KEY is required!")
        return
    
    # Test 1: SOL balance (this works)
    sol_balance = await test_sol_balance_python()
    
    # Test 2: USDC balance via JSSolanaClient (what we're fixing)
    usdc_balance_js = await test_usdc_balance_js()
    
    # Test 3: USDC balance via Python RPC (alternative)
    usdc_balance_python = await test_usdc_balance_python_rpc()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"SOL Balance: {sol_balance:.6f} SOL" if sol_balance else "SOL Balance: ❌ Failed")
    print(f"USDC Balance (JS): {usdc_balance_js:.6f} USDC" if usdc_balance_js is not None else "USDC Balance (JS): ❌ Failed")
    print(f"USDC Balance (Python): {usdc_balance_python:.6f} USDC" if usdc_balance_python is not None else "USDC Balance (Python): ❌ Failed")
    
    if usdc_balance_js is not None or usdc_balance_python is not None:
        print("\n✅ At least one method works!")
    else:
        print("\n❌ Both methods failed - need to investigate")


if __name__ == "__main__":
    asyncio.run(main())

