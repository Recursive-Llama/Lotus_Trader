#!/usr/bin/env python3
"""
Isolated Uniswap V3 single-hop test for a Base token (fee=10000 only).
No fallbacks. Logs tx hash immediately.
"""

import os
import sys
from time import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

sys.path.append('src')

from web3 import Web3  # type: ignore
from trading.evm_uniswap_client import EvmUniswapClient, WETH_ADDRESSES  # type: ignore


def main():
    # AVNT on Base
    token = os.getenv('TEST_BASE_TOKEN') or '0x696F9436B67233384889472Cd7cD58A6fB5DF4f1'
    amount_eth = float(os.getenv('TEST_AMOUNT_ETH') or '0.0005')
    fee = int(os.getenv('TEST_V3_FEE') or '10000')  # 1%

    print('🔬 Uniswap V3 isolated single-hop test')
    print(f'   token={token} fee={fee} amount_eth={amount_eth}')

    client = EvmUniswapClient(chain='base')
    weth = Web3.to_checksum_address(WETH_ADDRESSES['base'])
    amount_wei = int(amount_eth * 1e18)

    # Balance check (rough)
    bal = client.w3.eth.get_balance(client.account.address)
    print(f'   wallet={client.account.address} balance={bal/1e18:.6f} ETH')

    # Wrap ETH to WETH (amount)
    print('⛏️  Wrapping ETH → WETH...')
    wrap_res = client.wrap_eth(amount_eth)
    print(f'   wrap_res={wrap_res}')
    if wrap_res.get('status') != 1:
        print('   ❌ wrap failed; aborting')
        return

    # Approve WETH for router if needed
    router = client.router_address
    allowance = client.erc20_allowance(weth, client.account.address, router)
    if allowance < amount_wei:
        print(f'🔑 Approving WETH for router: {amount_wei} wei')
        appr = client.approve_erc20(weth, router, amount_wei)
        print(f'   approve={appr}')
        if appr.get('status') != 1:
            print('   ❌ approve failed; aborting')
            return

    # Perform single-hop swap
    print(f'🔁 Swapping WETH → token via v3 fee {fee}...')
    try:
        # Build tx and send
        res = client.swap_exact_input_single(weth, token, amount_wei, fee=fee, amount_out_min=0)
        print(f'   tx={res}')
    except Exception as e:
        print(f'   ❌ swap error: {e}')


if __name__ == '__main__':
    main()


