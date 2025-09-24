#!/usr/bin/env python3
"""
One-off live buy on BSC for STBL using Pancake (v2 pair-first).

Safety:
- Amount: 0.0003 BNB (wrapped to WBNB)
- Slippage: 1%

Env:
- BSC_RPC_URL (fallback: https://bsc-dataseed.binance.org)
- BSC_WALLET_PRIVATE_KEY (fallback: ETHEREUM_WALLET_PRIVATE_KEY)
"""

import os
import sys
from time import time

sys.path.append('src')

from trading.evm_uniswap_client import EvmUniswapClient, WETH_ADDRESSES
from web3 import Web3
import requests


def pick_bsc_stbl_pair():
    r = requests.get('https://api.dexscreener.com/latest/dex/search', params={'q': 'stbl'}, timeout=10)
    r.raise_for_status()
    pairs = (r.json() or {}).get('pairs') or []
    bsc_pairs = [p for p in pairs if (p.get('chainId') == 'bsc')]
    # Prefer WBNB/BNB quote pairs with symbol STBL and highest liquidity
    cand = [p for p in bsc_pairs if (p.get('baseToken',{}).get('symbol','').upper() == 'STBL' and p.get('quoteToken',{}).get('symbol') in ('WBNB','BNB'))]
    if not cand:
        raise RuntimeError('No BSC STBL/WBNB pairs found on DexScreener')
    cand.sort(key=lambda p: (p.get('liquidity',{}).get('usd') or 0), reverse=True)
    chosen = cand[0]
    return {
        'pair': Web3.to_checksum_address(chosen['pairAddress']),
        'contract': Web3.to_checksum_address(chosen['baseToken']['address']),
        'dex': chosen.get('dexId', 'unknown'),
        'liq': chosen.get('liquidity',{}).get('usd')
    }


def main():
    rpc = os.getenv('BSC_RPC_URL') or 'https://bsc-dataseed.binance.org'
    pk = os.getenv('BSC_WALLET_PRIVATE_KEY') or os.getenv('ETHEREUM_WALLET_PRIVATE_KEY') or os.getenv('ETH_WALLET_PRIVATE_KEY')
    if not pk:
        print('❌ Missing BSC_WALLET_PRIVATE_KEY (or ETHEREUM_WALLET_PRIVATE_KEY)')
        sys.exit(1)

    client = EvmUniswapClient(chain='bsc', rpc_url=rpc, private_key=pk)
    acct = client.account.address
    print(f'✅ Connected. Account: {acct}')

    info = pick_bsc_stbl_pair()
    pair_addr = info['pair']
    token = info['contract']
    print(f"🔗 Pair: {pair_addr} (dex={info['dex']}) liq=${info['liq']}")

    WBNB = Web3.to_checksum_address(WETH_ADDRESSES['bsc'])
    amount_bnb = 0.003
    amount_in = int(amount_bnb * 1e18)

    # Quote via v2 pair formula; if zero, fallback to router quote
    out = client.pair_get_amount_out(pair_addr, amount_in, WBNB)
    if out and out > 0:
        dec = client.get_token_decimals(token)
        price = amount_bnb / (out / (10 ** dec))
        print(f"💵 Pair quote: {amount_bnb} WBNB -> {out} STBL (implied price ≈ ${price:.8f})")
        min_out = int(out * 0.99)
        print(f"   Slippage 1% → minOut: {min_out}")
    else:
        print('⚠️ v2 pair getAmountOut returned 0 - trying router getAmountsOut')
        out_list = client.v2_get_amounts_out(WBNB, token, amount_in)
        if out_list and len(out_list) >= 2 and out_list[-1] > 0:
            out = out_list[-1]
            dec = client.get_token_decimals(token)
            price = amount_bnb / (out / (10 ** dec))
            print(f"💵 Router quote: {amount_bnb} WBNB -> {out} STBL (implied price ≈ ${price:.8f})")
            min_out = int(out * 0.99)
            print(f"   Slippage 1% → minOut: {min_out}")
        else:
            print('❌ Router getAmountsOut returned 0')
            min_out = 0

    # Wrap BNB→WBNB if needed for the intended amount
    wbnb_bal = client.weth_contract.functions.balanceOf(acct).call()
    if wbnb_bal < amount_in:
        needed = (amount_in - wbnb_bal) / 1e18
        print(f"🔁 Wrapping {needed:.6f} BNB to WBNB (current WBNB balance {wbnb_bal})")
        res = client.wrap_eth(float(needed))
        print(f"   wrap tx: {res}")

    # Try pair-direct only if we have a concrete exactOut from reserves
    pair_exact_out = client.pair_get_amount_out(pair_addr, amount_in, WBNB)
    if pair_exact_out and pair_exact_out > 0:
        print("🚀 Swapping on Pancake v2 pair (direct transfer+swap, exactOut)")
        try:
            res_pair = client.pair_swap_exact_tokens_for_tokens(pair_addr, WBNB, token, amount_in, int(pair_exact_out), recipient=acct)
            print(f"   pair swap result: {res_pair}")
            if res_pair.get('status') == 1:
                print('✅ Swap succeeded via pair')
                return
            else:
                print('⚠️ Pair swap reverted; not attempting router to avoid double-spend')
                return
        except Exception as e:
            print(f"   ❌ Pair swap error: {e}")
            print('⚠️ Skipping router fallback because pair transfer may have moved funds')
            return

    # Router path
    print("▶ Router path")
    try:
        router_addr = client.v2_router.address if client.v2_router else None
        if router_addr:
            # Ensure balance before swap
            wbnb_bal = client.weth_contract.functions.balanceOf(acct).call()
            if wbnb_bal < amount_in:
                needed = (amount_in - wbnb_bal) / 1e18
                print(f"🔁 Wrapping extra {needed:.6f} BNB to WBNB for router swap")
                res = client.wrap_eth(float(needed))
                print(f"   wrap tx: {res}")
            client.approve_erc20(WBNB, router_addr, amount_in)
            res_router = client.v2_swap_exact_tokens_for_tokens(WBNB, token, amount_in, amount_out_min_wei=min_out)
            print(f"   router swap: {res_router}")
            if not res_router or res_router.get('status') != 1:
                print("   ▶ Router supporting-fee variant")
                res_router2 = client.v2_swap_exact_tokens_for_tokens_supporting_fee(WBNB, token, amount_in, amount_out_min_wei=min_out)
                print(f"   router swap (supporting-fee): {res_router2}")
        else:
            print("   ❌ No v2 router configured")
    except Exception as e:
        print(f"   ❌ Router path error: {e}")


if __name__ == '__main__':
    main()


