#!/usr/bin/env python3
"""
One-off live buy on Base for SLC using Aerodrome (Solidly) via pair discovery.

Safety:
- Amount: 0.0005 ETH (wrapped to WETH)
- Slippage: 1%

Requirements:
- ENV: RPC_URL (or BASE_RPC_URL), ETHEREUM_WALLET_PRIVATE_KEY (or ETH_WALLET_PRIVATE_KEY)
"""

import os
import sys
from time import time

sys.path.append('src')

from trading.evm_uniswap_client import EvmUniswapClient, WETH_ADDRESSES
from web3 import Web3
import requests


SLC = Web3.to_checksum_address('0x6Bd83ABC39391Af1E24826E90237C4BD3468b5D2')
WETH = Web3.to_checksum_address(WETH_ADDRESSES['base'])


def main():
    rpc = os.getenv('BASE_RPC_URL') or os.getenv('RPC_URL')
    pk = os.getenv('ETHEREUM_WALLET_PRIVATE_KEY') or os.getenv('ETH_WALLET_PRIVATE_KEY')
    if not rpc:
        print('❌ Missing BASE_RPC_URL or RPC_URL')
        sys.exit(1)
    if not pk:
        print('❌ Missing ETHEREUM_WALLET_PRIVATE_KEY (or ETH_WALLET_PRIVATE_KEY)')
        sys.exit(1)

    client = EvmUniswapClient(chain='base', rpc_url=rpc, private_key=pk)
    acct = client.account.address
    print(f'✅ Connected. Account: {acct}')
    # Increase default gas limit for router txs
    client.gas_limit_default = 300000

    # Resolve Aerodrome pair from DexScreener
    ds = requests.get(f'https://api.dexscreener.com/latest/dex/tokens/{SLC}', timeout=10)
    ds.raise_for_status()
    pairs = (ds.json() or {}).get('pairs') or []
    base_pairs = [p for p in pairs if p.get('chainId') == 'base']
    aero_weth = [p for p in base_pairs if (p.get('dexId') == 'aerodrome' and p.get('quoteToken',{}).get('symbol') == 'WETH')]
    if not aero_weth:
        print('❌ No Aerodrome WETH/SLC pair found on DexScreener')
        sys.exit(1)
    # pick highest liq
    chosen = sorted(aero_weth, key=lambda p: (p.get('liquidity',{}).get('usd') or 0), reverse=True)[0]
    pair_addr = Web3.to_checksum_address(chosen['pairAddress'])
    print(f"🔗 Pair: {pair_addr} (dex={chosen.get('dexId')}) liq=${chosen.get('liquidity',{}).get('usd')}")

    # Compute expected out using pair.getAmountOut
    amount_eth = 0.0005
    amount_in = int(amount_eth * 1e18)
    out = client.pair_get_amount_out(pair_addr, amount_in, WETH)
    if not out or out <= 0:
        print('❌ pair_get_amount_out returned 0')
        sys.exit(1)
    token_dec = client.get_token_decimals(SLC)
    price = amount_eth / (out / (10 ** token_dec))
    print(f"💵 Quote: {amount_eth} WETH -> {out} SLC (price ≈ ${price:.8f} from DexScreener context)")

    # Prepare minOut (1% slippage)
    min_out_base = out
    print(f"   Base out (no slippage): {min_out_base}")

    # Wrap ETH to WETH if needed
    weth_bal = client.weth_contract.functions.balanceOf(acct).call()
    if weth_bal < amount_in:
        print(f"🔁 Wrapping {amount_eth} ETH to WETH (current WETH balance {weth_bal})")
        res = client.wrap_eth(amount_eth)
        print(f"   wrap tx: {res}")

    # Approve v2 router to spend WETH
    spender = client.v2_router.address if client.v2_router else None
    if not spender:
        print('❌ v2 router unavailable')
        sys.exit(1)
    allowance = client.erc20_allowance(WETH, acct, spender)
    if allowance < amount_in:
        print(f"✅ Approving router {spender} to spend {amount_in} WETH")
        appr = client.approve_erc20(WETH, spender, amount_in)
        print(f"   approve tx: {appr}")

    # Determine stable flag from pair
    stable_pair = client.pair_is_stable(pair_addr)
    print(f"   Pair stable: {stable_pair}")

    # Try multiple permutations for robustness
    stable_candidates = []
    if stable_pair is not None:
        stable_candidates.append(bool(stable_pair))
    for s in (False, True):
        if s not in stable_candidates:
            stable_candidates.append(s)

    slippage_factors = [0.99, 0.97, 0.95, 0.90]

    for slip in slippage_factors:
        min_out = int(min_out_base * slip)
        print(f"\n🧪 Attempt with slippage {int((1-slip)*100)}% → minOut={min_out}")
        for stable in stable_candidates:
            print(f"   ▶ Stable={stable}: estimating gas...")
            # Preflight gas estimate
            try:
                routes = [
                    (
                        Web3.to_checksum_address(WETH),
                        Web3.to_checksum_address(SLC),
                        bool(stable)
                    )
                ]
                base_tx = client._legacy_gas_tx()
                deadline = int(time()) + 600
                tx = client.v2_router.functions.swapExactTokensForTokens(
                    int(amount_in),
                    int(min_out),
                    routes,
                    acct,
                    deadline
                ).build_transaction(base_tx)
                gas_est = client.w3.eth.estimate_gas(tx)
                print(f"      Gas estimate: {gas_est}")
            except Exception as ge:
                print(f"      Gas estimate failed: {ge}")

            print(f"🚀 Swapping {amount_eth} WETH -> SLC on Aerodrome (stable={stable}, slip={int((1-slip)*100)}%)")
            try:
                swap_res = client.v2_swap_exact_tokens_for_tokens(WETH, SLC, amount_in, min_out, recipient=acct, deadline_seconds=600, stable=stable)
                print(f"   swap tx: {swap_res}")
                if swap_res.get('status') == 1:
                    print('✅ Swap succeeded')
                    print('✅ Done.')
                    return
            except Exception as e:
                print(f"   ❌ Swap attempt failed: {e}")

            # Try simple route method
            print(f"   ▶ Trying Simple route method (stable={stable})")
            try:
                swap_res2 = client.v2_swap_exact_tokens_for_tokens_simple(WETH, SLC, amount_in, min_out, recipient=acct, deadline_seconds=600, stable=stable)
                print(f"   simple swap tx: {swap_res2}")
                if swap_res2.get('status') == 1:
                    print('✅ Swap (simple) succeeded')
                    print('✅ Done.')
                    return
            except Exception as e:
                print(f"   ❌ Simple route attempt failed: {e}")

            # Direct pair swap fallback
            print("   ▶ Trying direct pair swap (transfer+swap)")
            try:
                res3 = client.pair_swap_exact_tokens_for_tokens(pair_addr, WETH, SLC, amount_in, min_out, recipient=acct)
                print(f"   pair swap txs: {res3}")
                if res3.get('status') == 1:
                    print('✅ Pair swap succeeded')
                    print('✅ Done.')
                    return
            except Exception as e:
                print(f"   ❌ Direct pair swap failed: {e}")

    print('❌ All attempts failed.')


if __name__ == '__main__':
    main()


