#!/usr/bin/env python3
"""
Isolated Uniswap V3 multi-hop test for a Base token (WETH->USDC->TOKEN).
Tries a small set of fee pairs once, prints quote and tx hash.
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

sys.path.append('src')

from web3 import Web3  # type: ignore
from trading.evm_uniswap_client import EvmUniswapClient, WETH_ADDRESSES  # type: ignore


def main():
    token = os.getenv('TEST_BASE_TOKEN') or '0x696F9436B67233384889472Cd7cD58A6fB5DF4f1'
    amount_eth = float(os.getenv('TEST_AMOUNT_ETH') or '0.0005')
    amount_wei = int(amount_eth * 1e18)

    print('🔬 Uniswap V3 isolated multi-hop test (WETH→USDC→TOKEN)')
    print(f'   token={token} amount_eth={amount_eth}')

    client = EvmUniswapClient(chain='base')
    weth = Web3.to_checksum_address(WETH_ADDRESSES['base'])
    usdc = client.usdc_address

    # Wrap ETH
    print('⛏️  Wrapping ETH → WETH...')
    wrap_res = client.wrap_eth(amount_eth)
    print(f'   wrap_res={wrap_res}')
    if wrap_res.get('status') != 1:
        print('   ❌ wrap failed; aborting')
        return

    # Approve WETH
    router = client.router_address
    allowance = client.erc20_allowance(weth, client.account.address, router)
    if allowance < amount_wei:
        print(f'🔑 Approving WETH for router: {amount_wei} wei')
        appr = client.approve_erc20(weth, router, amount_wei)
        print(f'   approve={appr}')
        if appr.get('status') != 1:
            print('   ❌ approve failed; aborting')
            return

    # Try a few fee pairs
    fee_pairs = [(500, 3000), (3000, 3000), (500, 10000), (3000, 10000), (10000, 3000)]
    for fa, fb in fee_pairs:
        try:
            path = client.v3_build_path([weth, usdc, token], [fa, fb])
            q = client.v3_quote_exact_input(path, amount_wei)
            print(f'   fees=({fa},{fb}) quote={q}')
            if q and q > 0:
                print(f'🔁 exactInput with fees=({fa},{fb}) ...')
                res = client.v3_exact_input(path, amount_wei, 0, recipient=client.account.address)
                print(f'   tx={res}')
                break
        except Exception as e:
            print(f'   fees=({fa},{fb}) error: {e}')


if __name__ == '__main__':
    main()


