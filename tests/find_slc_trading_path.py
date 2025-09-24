#!/usr/bin/env python3
"""
Find the correct trading path for SLC on Base
"""

import os
import sys
sys.path.append('src')

from trading.evm_uniswap_client import EvmUniswapClient

# SLC token data
SLC_CONTRACT = '0x6Bd83ABC39391Af1E24826E90237C4BD3468b5D2'
WETH_ADDRESS = '0x4200000000000000000000000000000000000006'
USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
DAI_ADDRESS = '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb'

def test_trading_paths():
    """Test different trading paths for SLC"""
    
    # Initialize Base client
    base_rpc = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
    evm_pk = os.getenv('EVM_PRIVATE_KEY')
    
    if not evm_pk:
        print("❌ EVM_PRIVATE_KEY not set")
        return
    
    try:
        client = EvmUniswapClient(chain='base', rpc_url=base_rpc, private_key=evm_pk)
        print(f"✅ Base client connected to {base_rpc}")
    except Exception as e:
        print(f"❌ Failed to connect to Base: {e}")
        return
    
    # Test different trading paths
    amount_in = int(0.001 * 1e18)  # 0.001 WETH
    amount_slc = int(1000 * 1e18)  # 1000 SLC tokens
    
    print(f"\n🔍 Testing trading paths for SLC: {SLC_CONTRACT}")
    print(f"   WETH: {WETH_ADDRESS}")
    print(f"   USDC: {USDC_ADDRESS}")
    print(f"   DAI:  {DAI_ADDRESS}")
    
    # Test 1: Direct SLC -> WETH
    print("\n1️⃣ Testing SLC -> WETH (direct)")
    try:
        result = client.v2_router.functions.getAmountsOut(
            amount_slc,
            [SLC_CONTRACT, WETH_ADDRESS]
        ).call()
        print(f"   ✅ SLC -> WETH: {result}")
        if result and len(result) >= 2 and result[-1] > 0:
            price = (0.001) / (result[-1] / 1e18)
            print(f"   💰 Price: ${price:.6f}")
    except Exception as e:
        print(f"   ❌ SLC -> WETH failed: {e}")
    
    # Test 2: WETH -> SLC (reverse)
    print("\n2️⃣ Testing WETH -> SLC (reverse)")
    try:
        result = client.v2_router.functions.getAmountsOut(
            amount_in,
            [WETH_ADDRESS, SLC_CONTRACT]
        ).call()
        print(f"   ✅ WETH -> SLC: {result}")
        if result and len(result) >= 2 and result[-1] > 0:
            price = (0.001) / (result[-1] / 1e18)
            print(f"   💰 Price: ${price:.6f}")
    except Exception as e:
        print(f"   ❌ WETH -> SLC failed: {e}")
    
    # Test 3: SLC -> USDC -> WETH
    print("\n3️⃣ Testing SLC -> USDC -> WETH")
    try:
        result = client.v2_router.functions.getAmountsOut(
            amount_slc,
            [SLC_CONTRACT, USDC_ADDRESS, WETH_ADDRESS]
        ).call()
        print(f"   ✅ SLC -> USDC -> WETH: {result}")
        if result and len(result) >= 3 and result[-1] > 0:
            price = (0.001) / (result[-1] / 1e18)
            print(f"   💰 Price: ${price:.6f}")
    except Exception as e:
        print(f"   ❌ SLC -> USDC -> WETH failed: {e}")
    
    # Test 4: WETH -> USDC -> SLC
    print("\n4️⃣ Testing WETH -> USDC -> SLC")
    try:
        result = client.v2_router.functions.getAmountsOut(
            amount_in,
            [WETH_ADDRESS, USDC_ADDRESS, SLC_CONTRACT]
        ).call()
        print(f"   ✅ WETH -> USDC -> SLC: {result}")
        if result and len(result) >= 3 and result[-1] > 0:
            price = (0.001) / (result[-1] / 1e18)
            print(f"   💰 Price: ${price:.6f}")
    except Exception as e:
        print(f"   ❌ WETH -> USDC -> SLC failed: {e}")
    
    # Test 5: SLC -> USDC (direct)
    print("\n5️⃣ Testing SLC -> USDC (direct)")
    try:
        result = client.v2_router.functions.getAmountsOut(
            amount_slc,
            [SLC_CONTRACT, USDC_ADDRESS]
        ).call()
        print(f"   ✅ SLC -> USDC: {result}")
        if result and len(result) >= 2 and result[-1] > 0:
            usdc_amount = result[-1] / 1e6  # USDC has 6 decimals
            print(f"   💰 USDC amount: {usdc_amount:.2f}")
    except Exception as e:
        print(f"   ❌ SLC -> USDC failed: {e}")
    
    # Test 6: Check if SLC has any liquidity on Uniswap V3
    print("\n6️⃣ Testing Uniswap V3 (WETH -> SLC)")
    for fee in [500, 3000, 10000]:
        try:
            out = client.v3_quote_amount_out(WETH_ADDRESS, SLC_CONTRACT, amount_in, fee=fee)
            if out and out > 0:
                price = (0.001) / (out / 1e18)
                print(f"   ✅ Uniswap V3 (fee={fee}): {out} tokens, price: ${price:.6f}")
                break
        except Exception as e:
            print(f"   ❌ Uniswap V3 (fee={fee}) failed: {e}")
    
    print("\n🔍 Summary:")
    print("   If any path works, we can use that for trading")
    print("   If none work, the token might not be tradeable on Base")

if __name__ == "__main__":
    test_trading_paths()
