#!/usr/bin/env python3
"""
EVM Trade Smoke Test (Python Uniswap client, no Node, no 0x)

Flow:
1) Load env, derive address, print ETH balance
2) Wrap ETH -> WETH (deposit)
3) Approve SwapRouter02 for WETH
4) Swap WETH -> target token via exactInputSingle (fee 500)

Examples:
  python -m src.tools.evm_trade_smoke --chain base \
    --token 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 --amount_eth 0.001
"""

import os
import argparse
import asyncio
import json
from dotenv import load_dotenv
import aiohttp
from eth_account import Account

from src.trading.evm_uniswap_client import EvmUniswapClient, WETH_ADDRESSES, ROUTER_ADDRESSES


def get_rpc_url(chain: str) -> str:
    if chain == 'ethereum':
        return os.getenv('ETH_RPC_URL', 'https://eth.llamarpc.com')
    if chain == 'base':
        return os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
    return ''


async def _run_smoke_eth(token: str, amount_eth: float) -> None:
    print('ETH path moved to src/tools/evm_trade_smoke_eth.py')
    return


async def run_smoke(chain: str, token: str, amount_eth: float) -> None:
    load_dotenv()

    # Resolve RPC and keys
    rpc_url = get_rpc_url(chain)
    if not rpc_url:
        print(f'Missing RPC URL for {chain}')
        return

    private_key = (
        os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
        or os.getenv('ETH_WALLET_PRIVATE_KEY')
        or os.getenv('BASE_WALLET_PRIVATE_KEY')
    )
    if not private_key:
        print('Missing ETHEREUM_WALLET_PRIVATE_KEY / ETH_WALLET_PRIVATE_KEY in environment')
        return

    derived_address = Account.from_key(private_key).address
    print(f"wallet | chain={chain} rpc={rpc_url} addr={derived_address}")

    # Branch: Ethereum uses 0x + JS client; Base uses Python Uniswap client
    if chain == 'ethereum':
        await _run_smoke_eth(token, amount_eth)
        return

    client = EvmUniswapClient(chain=chain, rpc_url=rpc_url, private_key=private_key)

    # 1) Wrap ETH -> WETH
    print(f"wrap | attempting deposit {amount_eth} ETH to WETH {WETH_ADDRESSES[chain]}")
    wrap_res = client.wrap_eth(amount_eth)
    print(f"wrap | result={wrap_res}")
    if wrap_res.get('status') != 1:
        print('wrap | failed, aborting')
        return

    # 2) Approve routers for WETH (v2 + v3)
    sell_amount_wei = int(amount_eth * 1e18)
    # v3 router
    v3_router = ROUTER_ADDRESSES[chain]
    print(f"approve | spender={v3_router} amount_wei={sell_amount_wei}")
    approve_res_v3 = client.approve_erc20(WETH_ADDRESSES[chain], v3_router, sell_amount_wei)
    print(f"approve | v3 result={approve_res_v3}")
    if approve_res_v3.get('status') != 1:
        print('approve v3 | failed, aborting')
        return
    # v2 router (if available for chain)
    if getattr(client, 'v2_router', None):
        v2_router_addr = client.v2_router.address
        current_allow = client.erc20_allowance(WETH_ADDRESSES[chain], derived_address, v2_router_addr)
        print(f"allowance | v2 spender={v2_router_addr} current={current_allow}")
        if current_allow < sell_amount_wei:
            print(f"approve | v2 spender={v2_router_addr} amount_wei={sell_amount_wei}")
            approve_res_v2 = client.approve_erc20(WETH_ADDRESSES[chain], v2_router_addr, sell_amount_wei)
            print(f"approve | v2 result={approve_res_v2}")
            if approve_res_v2.get('status') != 1:
                print('approve v2 | failed, aborting')
                return

    # 3) Prefer v2 path if available
    if getattr(client, 'v2_router', None):
        amounts = client.v2_get_amounts_out(WETH_ADDRESSES[chain], token, sell_amount_wei)
        if amounts:
            print(f"v2 | getAmountsOut -> {amounts}")
            v2_swap = client.v2_swap_exact_tokens_for_tokens(WETH_ADDRESSES[chain], token, sell_amount_wei, amount_out_min_wei=0)
            print(f"v2 | result={v2_swap}")
            if v2_swap.get('status') == 1:
                print(f"SMOKE OK | chain={chain} token={token} router=v2 tx={v2_swap.get('tx_hash')}")
                return

    # 4) Fallback: v3 fee tiers
    for fee in [500, 3000, 10000]:
        print(f"v3 | WETH -> {token} fee={fee} amountInWei={sell_amount_wei}")
        swap_res = client.swap_exact_input_single(WETH_ADDRESSES[chain], token, sell_amount_wei, fee=fee, amount_out_min=0)
        print(f"v3 | result={swap_res}")
        if swap_res.get('status') == 1:
            print(f"SMOKE OK | chain={chain} token={token} router=v3 fee={fee} tx={swap_res.get('tx_hash')}")
            return

    print("SMOKE FAIL | no success on v2 or v3")

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--chain', required=True, choices=['ethereum', 'base'])
    parser.add_argument('--token', required=True)
    parser.add_argument('--amount_eth', type=float, default=0.001)
    args = parser.parse_args()

    asyncio.run(run_smoke(args.chain, args.token, args.amount_eth))


