#!/usr/bin/env python3
"""
Python EVM Uniswap Client (Base/Ethereum)

Implements:
- wrap_eth_to_weth (WETH deposit)
- approve_erc20 (ERC20 approve spender)
- uniswap_v3_exact_input_single (SwapRouter02)

Defaults:
- Base chain IDs, router, and WETH addresses included

Note: Keep code explicit and readable. Avoid hidden magic.
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any

from web3 import Web3
from eth_account import Account


WETH_ADDRESSES = {
    'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    'base': '0x4200000000000000000000000000000000000006',
}

ROUTER_ADDRESSES = {
    # SwapRouter02
    'ethereum': '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45',
    'base': '0x2626664c2603336E57B271c5C0b26F421741e481',
}

# v2-style routers (for direct pairs)
V2_ROUTER_ADDRESSES = {
    # Uniswap v2 on Ethereum (not used here, but included for completeness)
    'ethereum': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
    # Aerodrome Router on Base (v2-style)
    'base': '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43',
}

# QuoterV2 contracts for Uniswap v3 price quotes
QUOTER_V2_ADDRESSES = {
    'ethereum': '0x61fFE014bA17989E743c5F6cB21bF9697530B21e',
    'base': '0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a',
}


WETH_ABI = [
    {
        "constant": False,
        "inputs": [],
        "name": "deposit",
        "outputs": [],
        "payable": True,
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    },
]


ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]


ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "internalType": "struct ISwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    }
]

V2_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

QUOTER_V2_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "internalType": "struct IQuoterV2.QuoteExactInputSingleParams",
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
            {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


class EvmUniswapClient:
    def __init__(self, chain: str, rpc_url: Optional[str] = None, private_key: Optional[str] = None, gas_limit_default: int = 300000):
        self.chain = chain.lower()
        self.chain_id = 1 if self.chain == 'ethereum' else 8453 if self.chain == 'base' else None
        if self.chain_id is None:
            raise ValueError(f"Unsupported chain: {chain}")

        self.rpc_url = rpc_url or (
            os.getenv('ETH_RPC_URL') if self.chain == 'ethereum' else os.getenv('BASE_RPC_URL')
        )
        if not self.rpc_url:
            raise ValueError(f"Missing RPC URL for {self.chain}")

        self.private_key = private_key or os.getenv('ETHEREUM_WALLET_PRIVATE_KEY') or os.getenv('ETH_WALLET_PRIVATE_KEY')
        if not self.private_key:
            raise ValueError("Missing Ethereum private key in environment")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError(f"Failed to connect to RPC: {self.rpc_url}")

        self.account = Account.from_key(self.private_key)
        self.gas_limit_default = gas_limit_default

        self.weth_address = Web3.to_checksum_address(WETH_ADDRESSES[self.chain])
        self.router_address = Web3.to_checksum_address(ROUTER_ADDRESSES[self.chain])

        self.weth_contract = self.w3.eth.contract(address=self.weth_address, abi=WETH_ABI)
        self.router_contract = self.w3.eth.contract(address=self.router_address, abi=ROUTER_ABI)
        # v2 router (if available for chain)
        v2_addr = V2_ROUTER_ADDRESSES.get(self.chain)
        self.v2_router = self.w3.eth.contract(address=Web3.to_checksum_address(v2_addr), abi=V2_ROUTER_ABI) if v2_addr else None
        # quoter v2 (for v3 price quotes)
        quoter_addr = QUOTER_V2_ADDRESSES.get(self.chain)
        self.quoter = self.w3.eth.contract(address=Web3.to_checksum_address(quoter_addr), abi=QUOTER_V2_ABI) if quoter_addr else None

    def _legacy_gas_tx(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        gas_price = self.w3.eth.gas_price
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        base = {
            'from': self.account.address,
            'gas': self.gas_limit_default,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': self.chain_id,
        }
        if overrides:
            base.update(overrides)
        return base

    def send(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {'tx_hash': tx_hash.hex(), 'status': int(receipt.status), 'gas_used': int(receipt.gasUsed)}

    def wrap_eth(self, amount_eth: float, gas_limit: int = 70000) -> Dict[str, Any]:
        amount_wei = self.w3.to_wei(amount_eth, 'ether')
        base = self._legacy_gas_tx({'gas': gas_limit, 'value': amount_wei})
        tx = self.weth_contract.functions.deposit().build_transaction(base)
        return self.send(tx)

    def erc20_allowance(self, token: str, owner: str, spender: str) -> int:
        erc20 = self.w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
        return int(erc20.functions.allowance(Web3.to_checksum_address(owner), Web3.to_checksum_address(spender)).call())

    def get_token_decimals(self, token: str) -> int:
        try:
            erc20 = self.w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
            return int(erc20.functions.decimals().call())
        except Exception:
            return 18

    # --- Uniswap v2 helpers (for chains with v2-style routers like Base/Aerodrome) ---
    def v2_get_amounts_out(self, token_in: str, token_out: str, amount_in_wei: int) -> Optional[list[int]]:
        if not self.v2_router:
            return None
        try:
            path = [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)]
            return self.v2_router.functions.getAmountsOut(amount_in_wei, path).call()
        except Exception:
            return None

    def v2_swap_exact_tokens_for_tokens(self, token_in: str, token_out: str, amount_in_wei: int, amount_out_min_wei: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600) -> Dict[str, Any]:
        if not self.v2_router:
            return { 'status': 0, 'error': 'v2_router_unavailable' }
        recipient = recipient or self.account.address
        from time import time
        deadline = int(time()) + deadline_seconds
        path = [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)]
        base = self._legacy_gas_tx()
        tx = self.v2_router.functions.swapExactTokensForTokens(
            amount_in_wei,
            amount_out_min_wei,
            path,
            recipient,
            deadline
        ).build_transaction(base)
        return self.send(tx)

    # --- v3 QuoterV2 helpers ---
    def v3_quote_amount_out(self, token_in: str, token_out: str, amount_in_wei: int, fee: int = 3000) -> Optional[int]:
        if not self.quoter:
            return None
        try:
            params = (
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                int(amount_in_wei),
                int(fee),
                0
            )
            # Some providers require dict, but ABI accepts tuple
            res = self.quoter.functions.quoteExactInputSingle(params).call()
            amount_out = int(res[0]) if isinstance(res, (list, tuple)) else int(res)
            return amount_out
        except Exception:
            return None

    def approve_erc20(self, token: str, spender: str, amount_wei: int, gas_limit: int = 100000) -> Dict[str, Any]:
        token = Web3.to_checksum_address(token)
        spender = Web3.to_checksum_address(spender)
        erc20 = self.w3.eth.contract(address=token, abi=ERC20_ABI)
        base = self._legacy_gas_tx({'gas': gas_limit})
        tx = erc20.functions.approve(spender, amount_wei).build_transaction(base)
        return self.send(tx)

    def swap_exact_input_single(self, token_in: str, token_out: str, amount_in_wei: int, fee: int = 500, amount_out_min: int = 0, recipient: Optional[str] = None) -> Dict[str, Any]:
        token_in = Web3.to_checksum_address(token_in)
        token_out = Web3.to_checksum_address(token_out)
        recipient = recipient or self.account.address
        params = (
            token_in,
            token_out,
            fee,
            recipient,
            amount_in_wei,
            amount_out_min,
            0,  # sqrtPriceLimitX96
        )
        base = self._legacy_gas_tx({'value': 0})
        tx = self.router_contract.functions.exactInputSingle(params).build_transaction(base)
        return self.send(tx)


