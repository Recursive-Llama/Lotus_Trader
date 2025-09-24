#!/usr/bin/env python3
"""
Isolated Aerodrome (Solidly) pricing probe on Base.
Tests getAmountsOut with proper Route[] tuples for:
- WETH -> SLC
- SLC -> WETH
- WETH -> USDC -> SLC
- SLC -> USDC -> WETH

Prints detailed successes/failures without touching app code.
"""

import os
import sys
import traceback
from typing import List, Tuple

from web3 import Web3
import requests


BASE_RPC = os.getenv('BASE_RPC_URL') or os.getenv('RPC_URL') or 'https://mainnet.base.org'
AERODROME_ROUTER = Web3.to_checksum_address('0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43')

# Addresses
WETH = Web3.to_checksum_address('0x4200000000000000000000000000000000000006')
USDC = Web3.to_checksum_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
SLC  = Web3.to_checksum_address('0x6Bd83ABC39391Af1E24826E90237C4BD3468b5D2')


SOLIDLY_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {
                "components": [
                    {"internalType": "address", "name": "from", "type": "address"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "bool", "name": "stable", "type": "bool"}
                ],
                "internalType": "struct IRouter.Route[]",
                "name": "routes",
                "type": "tuple[]"
            }
        ],
        "name": "getAmountsOut",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "factory",
        "outputs": [
            {"internalType": "address", "name": "", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "bool", "name": "stable", "type": "bool"}
        ],
        "name": "getPair",
        "outputs": [
            {"internalType": "address", "name": "pair", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

PAIR_ABI = [
    {"inputs": [], "name": "stable", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "tokens", "outputs": [
        {"internalType": "address", "name": "token0", "type": "address"},
        {"internalType": "address", "name": "token1", "type": "address"}
    ], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "amountIn", "type": "uint256"}, {"internalType": "address", "name": "tokenIn", "type": "address"}],
     "name": "getAmountOut", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getReserves", "outputs": [
        {"internalType": "uint256", "name": "_reserve0", "type": "uint256"},
        {"internalType": "uint256", "name": "_reserve1", "type": "uint256"},
        {"internalType": "uint256", "name": "_blockTimestampLast", "type": "uint256"}
    ], "stateMutability": "view", "type": "function"}
]


def call_get_amounts_out(w3: Web3, routes: List[Tuple[str, str, bool]], amount_in: int):
    router = w3.eth.contract(address=AERODROME_ROUTER, abi=SOLIDLY_ROUTER_ABI)
    return router.functions.getAmountsOut(int(amount_in), routes).call()


def try_pair(w3: Web3, label: str, hops: List[Tuple[str, str]], amount_in: int):
    print(f"\n{label}")
    # First attempt volatile hops (stable=False)
    try:
        routes = [(Web3.to_checksum_address(a), Web3.to_checksum_address(b), False) for a, b in hops]
        out = call_get_amounts_out(w3, routes, amount_in)
        print(f"   ✅ Volatile routes OK: {out}")
        return out
    except Exception as e:
        print(f"   ❌ Volatile failed: {e}")
        traceback.print_exc()
    # Then attempt stable
    try:
        routes = [(Web3.to_checksum_address(a), Web3.to_checksum_address(b), True) for a, b in hops]
        out = call_get_amounts_out(w3, routes, amount_in)
        print(f"   ✅ Stable routes OK: {out}")
        return out
    except Exception as e:
        print(f"   ❌ Stable failed: {e}")
        traceback.print_exc()
    return None


def main():
    print(f"Connecting RPC: {BASE_RPC}")
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    if not w3.is_connected():
        print("❌ Failed to connect RPC")
        sys.exit(1)
    print("✅ Connected")

    small_in = int(0.001 * 1e18)  # 0.001 WETH
    slc_in   = int(1000 * 1e18)   # 1000 SLC

    # DexScreener discovery
    try:
        print("\nDexScreener lookup:")
        r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{SLC}", timeout=10)
        if r.ok:
            data = r.json()
            pairs = data.get('pairs') or []
            base_pairs = [p for p in pairs if (p.get('chainId') == 'base')]
            if not base_pairs:
                print("   No Base pairs found on DexScreener")
            aerodrome_pair_addr = None
            for p in base_pairs:
                print(f"   DEX={p.get('dexId')} pair={p.get('pairAddress')} baseToken={p.get('baseToken',{}).get('symbol')} quoteToken={p.get('quoteToken',{}).get('symbol')} liq={p.get('liquidity',{}).get('usd')} priceUsd={p.get('priceUsd')}")
                if (p.get('dexId') == 'aerodrome' and p.get('baseToken',{}).get('symbol') == 'SLC' and p.get('quoteToken',{}).get('symbol') == 'WETH'):
                    aerodrome_pair_addr = p.get('pairAddress')
            # If we found an Aerodrome WETH/SLC pair, query it directly
            if aerodrome_pair_addr:
                print(f"\nUsing Aerodrome pair contract: {aerodrome_pair_addr}")
                pair_addr = Web3.to_checksum_address(aerodrome_pair_addr)
                pair = w3.eth.contract(address=pair_addr, abi=PAIR_ABI)
                try:
                    is_stable = pair.functions.stable().call()
                except Exception:
                    is_stable = None
                try:
                    t0, t1 = pair.functions.tokens().call()
                    print(f"   tokens(): token0={t0} token1={t1}")
                except Exception as e:
                    print(f"   tokens() failed: {e}")
                    t0, t1 = None, None
                try:
                    r0, r1, ts = pair.functions.getReserves().call()
                    print(f"   reserves: r0={r0} r1={r1} ts={ts}")
                except Exception as e:
                    print(f"   getReserves() failed: {e}")
                # Price WETH -> SLC via pair.getAmountOut
                try:
                    out_slc = pair.functions.getAmountOut(int(small_in), WETH).call()
                    print(f"   ✅ Pair.getAmountOut 0.001 WETH -> {out_slc} SLC")
                except Exception as e:
                    print(f"   ❌ Pair.getAmountOut WETH->SLC failed: {e}")
                # Price SLC -> WETH via pair.getAmountOut
                try:
                    out_weth = pair.functions.getAmountOut(int(1000 * 1e18), SLC).call()
                    print(f"   ✅ Pair.getAmountOut 1000 SLC -> {out_weth} WETH")
                except Exception as e:
                    print(f"   ❌ Pair.getAmountOut SLC->WETH failed: {e}")
        else:
            print(f"   DexScreener error: HTTP {r.status_code}")
    except Exception as e:
        print(f"   DexScreener fetch failed: {e}")

    # Discover factory and pair addresses
    router = w3.eth.contract(address=AERODROME_ROUTER, abi=SOLIDLY_ROUTER_ABI)
    try:
        factory_addr = router.functions.factory().call()
        print(f"Factory: {factory_addr}")
        factory = w3.eth.contract(address=factory_addr, abi=FACTORY_ABI)
        # check both stable flags for pair existence
        for stable in (False, True):
            pair = factory.functions.getPair(WETH, SLC, stable).call()
            kind = 'volatile' if not stable else 'stable'
            print(f"Pair WETH/SLC ({kind}): {pair}")
    except Exception as e:
        print(f"Failed to read factory/pairs: {e}")

    # 1) WETH -> SLC
    try_pair(w3, "1) WETH -> SLC", [(WETH, SLC)], small_in)
    # 2) SLC -> WETH
    try_pair(w3, "2) SLC -> WETH", [(SLC, WETH)], slc_in)
    # 3) WETH -> USDC -> SLC
    try_pair(w3, "3) WETH -> USDC -> SLC", [(WETH, USDC), (USDC, SLC)], small_in)
    # 4) SLC -> USDC -> WETH
    try_pair(w3, "4) SLC -> USDC -> WETH", [(SLC, USDC), (USDC, WETH)], slc_in)

    print("\nDone.")


if __name__ == "__main__":
    main()


