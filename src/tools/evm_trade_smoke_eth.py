#!/usr/bin/env python3
"""
ETH Uniswap Smoke Test (no 0x)

Flow:
1) Load env (use Ankr ETH RPC if provided)
2) Wrap ETH -> WETH
3) Approve SwapRouter02
4) Try swap WETH -> token across fee tiers [500, 3000, 10000]
"""

import os
import argparse
from dotenv import load_dotenv
from eth_account import Account

from src.trading.evm_uniswap_client_eth import EthUniswapClient, WETH_ADDRESS, ROUTER02_ADDRESS


def get_eth_rpc() -> str:
    return os.getenv('ETH_RPC_URL', 'https://eth.llamarpc.com')


def main(chain_token: str, amount_eth: float):
    load_dotenv()
    rpc = get_eth_rpc()
    pk = os.getenv('ETHEREUM_WALLET_PRIVATE_KEY') or os.getenv('ETH_WALLET_PRIVATE_KEY')
    if not pk:
        print('Missing ETHEREUM_WALLET_PRIVATE_KEY')
        return
    addr = Account.from_key(pk).address
    print(f"wallet | chain=ethereum rpc={rpc} addr={addr}")

    client = EthUniswapClient(rpc_url=rpc, private_key=pk)

    # 1) Wrap
    print(f"wrap | attempting deposit {amount_eth} ETH to WETH {WETH_ADDRESS}")
    wrap_res = client.wrap_eth(amount_eth)
    print(f"wrap | result={wrap_res}")
    if wrap_res.get('status') != 1:
        print('wrap | failed, aborting')
        return

    # 2) Approve routers as needed (v2 and v3)
    amount_wei = int(amount_eth * 1e18)
    for spender in [ROUTER02_ADDRESS, '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D']:
        current_allow = client.erc20_allowance(WETH_ADDRESS, addr, spender)
        print(f"allowance | spender={spender} current={current_allow}")
        if current_allow < amount_wei:
            print(f"approve | spender={spender} amount_wei={amount_wei}")
            approve_res = client.approve_erc20(WETH_ADDRESS, spender, amount_wei)
            print(f"approve | result={approve_res}")
            if approve_res.get('status') != 1:
                print('approve | failed, aborting')
                return

    # 3) Prefer Uniswap v2 if direct pair exists
    amounts = client.v2_get_amounts_out(WETH_ADDRESS, chain_token, amount_wei)
    if amounts:
        print(f"v2 | getAmountsOut -> {amounts}")
        print("v2 | executing swapExactTokensForTokens")
        v2_res = client.v2_swap_exact_tokens_for_tokens(WETH_ADDRESS, chain_token, amount_wei, amount_out_min_wei=0)
        print(f"v2 | result={v2_res}")
        if v2_res.get('status') == 1:
            print(f"SMOKE OK | chain=ethereum token={chain_token} router=v2 tx={v2_res.get('tx_hash')}")
            return

    # 4) Fallback: try Uniswap v3 fee tiers
    for fee in [500, 3000, 10000]:
        print(f"v3 | WETH -> {chain_token} fee={fee} amountInWei={amount_wei}")
        swap_res = client.swap_exact_input_single(WETH_ADDRESS, chain_token, amount_wei, fee=fee, amount_out_min=0)
        print(f"v3 | result={swap_res}")
        if swap_res.get('status') == 1:
            print(f"SMOKE OK | chain=ethereum token={chain_token} router=v3 fee={fee} tx={swap_res.get('tx_hash')}")
            return

    print('SMOKE FAIL | no success on v2 or v3')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', required=True)
    parser.add_argument('--amount_eth', type=float, default=0.0003)
    args = parser.parse_args()
    main(args.token, args.amount_eth)


