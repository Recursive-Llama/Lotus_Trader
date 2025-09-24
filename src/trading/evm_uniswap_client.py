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
    'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',  # WBNB on BSC (correct)
}

USDC_ADDRESSES = {
    'ethereum': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    'base': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'bsc': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'
}

ROUTER_ADDRESSES = {
    # SwapRouter02
    'ethereum': '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45',
    'base': '0x2626664c2603336E57B271c5C0b26F421741e481',
    'bsc': '0x1b81D678ffb9C0263b24A97847620C99d213eB14',  # PancakeSwap V3 Router
}

# v2-style routers (UniswapV2 for ETH, Solidly/Aerodrome for Base)
V2_ROUTER_ADDRESSES = {
    # Uniswap v2 on Ethereum (not used here, but included for completeness)
    'ethereum': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
    # Aerodrome Router on Base (Solidly-style)
    'base': '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43',
    # PancakeSwap V2 Router on BSC
    'bsc': '0x10ED43C718714eb63d5aA57B78B54704E256024E',
}

# QuoterV2 contracts for Uniswap v3 price quotes
QUOTER_V2_ADDRESSES = {
    'ethereum': '0x61fFE014bA17989E743c5F6cB21bF9697530B21e',
    'base': '0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a',
    'bsc': '0xB048Bf43c3C641C026C4C52c61Df7C4C0364e8c1',  # PancakeSwap V3 QuoterV2
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
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
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


# Uniswap SwapRouter02 ABI (Base/Ethereum) - NO deadline
UNISWAP_V3_ROUTER_ABI = [
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

# PancakeSwap V3 Router ABI (BSC) - WITH deadline
PANCAKE_V3_ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
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

V2_UNISWAP_ROUTER_ABI = [
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

# Solidly/Aerodrome router ABI (uses Route[] with stable flag)
V2_SOLIDLY_ROUTER_ABI = [
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
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {
                "components": [
                    {"internalType": "address", "name": "from", "type": "address"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "bool", "name": "stable", "type": "bool"}
                ],
                "internalType": "struct IRouter.Route[]",
                "name": "routes",
                "type": "tuple[]"
            },
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

# Optional Solidly "Simple" swap (single-hop)
V2_SOLIDLY_ROUTER_ABI.append(
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address", "name": "tokenFrom", "type": "address"},
            {"internalType": "address", "name": "tokenTo", "type": "address"},
            {"internalType": "bool", "name": "stable", "type": "bool"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokensSimple",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
)

# Solidly Pair ABI (subset)
SOLIDLY_PAIR_ABI = [
    {
        "inputs": [],
        "name": "stable",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "tokens",
        "outputs": [
            {"internalType": "address", "name": "token0", "type": "address"},
            {"internalType": "address", "name": "token1", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address", "name": "tokenIn", "type": "address"}
        ],
        "name": "getAmountOut",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint256", "name": "_reserve0", "type": "uint256"},
            {"internalType": "uint256", "name": "_reserve1", "type": "uint256"},
            {"internalType": "uint256", "name": "_blockTimestampLast", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amount0Out", "type": "uint256"},
            {"internalType": "uint256", "name": "amount1Out", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "bytes", "name": "data", "type": "bytes"}
        ],
        "name": "swap",
        "outputs": [],
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

# Extend QuoterV2 with quoteExactInput for multi-hop path pricing
QUOTER_V2_ABI.append(
    {
        "inputs": [
            {"internalType": "bytes", "name": "path", "type": "bytes"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"}
        ],
        "name": "quoteExactInput",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
            {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
)


class EvmUniswapClient:
    def __init__(self, chain: str, rpc_url: Optional[str] = None, private_key: Optional[str] = None, gas_limit_default: int = 300000):
        self.chain = chain.lower()
        self.chain_id = 1 if self.chain == 'ethereum' else 8453 if self.chain == 'base' else 56 if self.chain == 'bsc' else None
        if self.chain_id is None:
            raise ValueError(f"Unsupported chain: {chain}")

        self.rpc_url = rpc_url or (
            os.getenv('ETH_RPC_URL') if self.chain == 'ethereum' else (
                os.getenv('BASE_RPC_URL') or os.getenv('RPC_URL')
            ) if self.chain == 'base' else (
                os.getenv('BSC_RPC_URL') or 'https://bsc-dataseed.binance.org'
            )
        )
        if not self.rpc_url:
            raise ValueError(f"Missing RPC URL for {self.chain}")

        self.private_key = private_key or (
            os.getenv('BSC_WALLET_PRIVATE_KEY') if self.chain == 'bsc' else (
                os.getenv('ETHEREUM_WALLET_PRIVATE_KEY') or os.getenv('ETH_WALLET_PRIVATE_KEY')
            )
        )
        if not self.private_key:
            raise ValueError(f"Missing private key for {self.chain} in environment")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError(f"Failed to connect to RPC: {self.rpc_url}")

        self.account = Account.from_key(self.private_key)
        self.gas_limit_default = gas_limit_default

        self.weth_address = Web3.to_checksum_address(WETH_ADDRESSES[self.chain])
        self.usdc_address = Web3.to_checksum_address(USDC_ADDRESSES[self.chain])
        self.router_address = Web3.to_checksum_address(ROUTER_ADDRESSES[self.chain])

        self.weth_contract = self.w3.eth.contract(address=self.weth_address, abi=WETH_ABI)
        
        # Select correct ABI based on chain
        if self.chain == 'bsc':
            router_abi = PANCAKE_V3_ROUTER_ABI
        else:  # base, ethereum
            router_abi = UNISWAP_V3_ROUTER_ABI
        self.router_contract = self.w3.eth.contract(address=self.router_address, abi=router_abi)
        # v2 router (if available for chain). Base uses Solidly/Aerodrome ABI
        v2_addr = V2_ROUTER_ADDRESSES.get(self.chain)
        if v2_addr:
            if self.chain == 'base':
                self.v2_router = self.w3.eth.contract(address=Web3.to_checksum_address(v2_addr), abi=V2_SOLIDLY_ROUTER_ABI)
                self.v2_is_solidly = True
            else:
                self.v2_router = self.w3.eth.contract(address=Web3.to_checksum_address(v2_addr), abi=V2_UNISWAP_ROUTER_ABI)
                self.v2_is_solidly = False
        else:
            self.v2_router = None
            self.v2_is_solidly = False
        # quoter v2 (for v3 price quotes)
        quoter_addr = QUOTER_V2_ADDRESSES.get(self.chain)
        self.quoter = self.w3.eth.contract(address=Web3.to_checksum_address(quoter_addr), abi=QUOTER_V2_ABI) if quoter_addr else None
        
        # Nonce management for sequential transactions
        self._current_nonce = None

    def _get_next_nonce(self) -> int:
        """Monotonic local nonce initialized from pending, with error-based refresh in send()."""
        if self._current_nonce is None:
            self._current_nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
        else:
            self._current_nonce += 1
        return self._current_nonce

    def _legacy_gas_tx(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        gas_price = self.w3.eth.gas_price
        nonce = self._get_next_nonce()
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
        def _bump_gas_price(txd: Dict[str, Any]) -> None:
            gp = int(txd.get('gasPrice') or self.w3.eth.gas_price)
            bumped = int(gp * 125 // 100)
            txd['gasPrice'] = bumped

        attempts = 0
        while True:
            attempts += 1
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            try:
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60, poll_latency=1)
                return {'tx_hash': tx_hash.hex(), 'status': int(receipt.status), 'gas_used': int(receipt.gasUsed)}
            except Exception as e:
                msg = str(e)
                if 'nonce too low' in msg:
                    # Refresh local nonce and rebuild
                    tx['nonce'] = self.w3.eth.get_transaction_count(self.account.address, 'pending')
                    _bump_gas_price(tx)
                    if attempts >= 3:
                        raise
                    continue
                if 'replacement transaction underpriced' in msg or 'fee too low' in msg:
                    # Keep same nonce, bump gas price
                    _bump_gas_price(tx)
                    if attempts >= 3:
                        raise
                    continue
                if 'Too Many Requests' in msg or '429' in msg:
                    # Backoff and retry
                    import time as _t
                    _t.sleep(1.0 * attempts)
                    if attempts >= 3:
                        raise
                    continue
                # Unknown error or wait_for_transaction_receipt timeout
                raise

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
    def v2_get_amounts_out(self, token_in: str, token_out: str, amount_in_wei: int, stable: Optional[bool] = None) -> Optional[list[int]]:
        if not self.v2_router:
            print("❌ No V2 router available")
            return None
        try:
            print(f"Getting amounts out: {token_in} -> {token_out}, amount: {amount_in_wei}")
            if self.v2_is_solidly:
                # Solidly requires Route[] with stable flag per hop
                # Try volatile first (stable=False) unless explicitly provided
                routes = [
                    (
                        Web3.to_checksum_address(token_in),
                        Web3.to_checksum_address(token_out),
                        bool(False if stable is None else stable)
                    )
                ]
                return self.v2_router.functions.getAmountsOut(int(amount_in_wei), routes).call()
            else:
                path = [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)]
                return self.v2_router.functions.getAmountsOut(int(amount_in_wei), path).call()
        except Exception as e:
            print(f"🔍 V2 getAmountsOut error (expected for some tokens): {e}")
            # For Solidly, if volatile failed and stable not specified, try stable
            if self.v2_is_solidly and stable is None:
                try:
                    print("Trying stable route...")
                    routes = [
                        (
                            Web3.to_checksum_address(token_in),
                            Web3.to_checksum_address(token_out),
                            True
                        )
                    ]
                    return self.v2_router.functions.getAmountsOut(int(amount_in_wei), routes).call()
                except Exception as e2:
                    print(f"🔍 Stable route error (expected for some tokens): {e2}")
                    return None
            return None

    def v2_swap_exact_tokens_for_tokens(self, token_in: str, token_out: str, amount_in_wei: int, amount_out_min_wei: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600, stable: Optional[bool] = None) -> Dict[str, Any]:
        if not self.v2_router:
            return { 'status': 0, 'error': 'v2_router_unavailable' }
        recipient = recipient or self.account.address
        from time import time
        deadline = int(time()) + deadline_seconds
        base = self._legacy_gas_tx()
        if self.v2_is_solidly:
            # Build Solidly Route[]
            routes = [
                (
                    Web3.to_checksum_address(token_in),
                    Web3.to_checksum_address(token_out),
                    bool(False if stable is None else stable)
                )
            ]
            try:
                tx = self.v2_router.functions.swapExactTokensForTokens(
                    int(amount_in_wei),
                    int(amount_out_min_wei),
                    routes,
                    recipient,
                    deadline
                ).build_transaction(base)
                return self.send(tx)
            except Exception as e:
                # Try stable route as fallback
                try:
                    routes = [
                        (
                            Web3.to_checksum_address(token_in),
                            Web3.to_checksum_address(token_out),
                            True
                        )
                    ]
                    tx = self.v2_router.functions.swapExactTokensForTokens(
                        int(amount_in_wei),
                        int(amount_out_min_wei),
                        routes,
                        recipient,
                        deadline
                    ).build_transaction(base)
                    return self.send(tx)
                except Exception:
                    return { 'status': 0, 'error': 'swap_failed' }
        else:
            path = [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)]
            tx = self.v2_router.functions.swapExactTokensForTokens(
                int(amount_in_wei),
                int(amount_out_min_wei),
                path,
                recipient,
                deadline
            ).build_transaction(base)
            return self.send(tx)

    def v2_swap_exact_tokens_for_tokens_simple(self, token_in: str, token_out: str, amount_in_wei: int, amount_out_min_wei: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600, stable: bool = False) -> Dict[str, Any]:
        if not self.v2_router:
            return { 'status': 0, 'error': 'v2_router_unavailable' }
        if not self.v2_is_solidly:
            return { 'status': 0, 'error': 'simple_not_supported' }
        recipient = recipient or self.account.address
        from time import time
        deadline = int(time()) + deadline_seconds
        base = self._legacy_gas_tx()
        tx = self.v2_router.functions.swapExactTokensForTokensSimple(
            int(amount_in_wei),
            int(amount_out_min_wei),
            Web3.to_checksum_address(token_in),
            Web3.to_checksum_address(token_out),
            bool(stable),
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

    # --- Solidly Pair helpers ---
    def get_pair_contract(self, pair_address: str):
        return self.w3.eth.contract(address=Web3.to_checksum_address(pair_address), abi=SOLIDLY_PAIR_ABI)

    def pair_is_stable(self, pair_address: str) -> Optional[bool]:
        try:
            return bool(self.get_pair_contract(pair_address).functions.stable().call())
        except Exception:
            return None

    def pair_tokens(self, pair_address: str) -> Optional[tuple[str, str]]:
        try:
            t0, t1 = self.get_pair_contract(pair_address).functions.tokens().call()
            return Web3.to_checksum_address(t0), Web3.to_checksum_address(t1)
        except Exception:
            return None

    def pair_get_amount_out(self, pair_address: str, amount_in_wei: int, token_in: str) -> Optional[int]:
        try:
            return int(self.get_pair_contract(pair_address).functions.getAmountOut(int(amount_in_wei), Web3.to_checksum_address(token_in)).call())
        except Exception:
            return None

    def pair_swap_exact_tokens_for_tokens(self, pair_address: str, token_in: str, token_out: str, amount_in_wei: int, min_out_wei: int, recipient: Optional[str] = None) -> Dict[str, Any]:
        """Direct swap on Solidly pair: transfer token_in to pair, then call swap with minOut on correct side."""
        recipient = recipient or self.account.address
        pair = self.get_pair_contract(pair_address)
        # Transfer token_in to pair
        token_in = Web3.to_checksum_address(token_in)
        token_out = Web3.to_checksum_address(token_out)
        pair_addr = Web3.to_checksum_address(pair_address)
        # 1) transfer token_in to pair
        erc20 = self.w3.eth.contract(address=token_in, abi=ERC20_ABI)
        base1 = self._legacy_gas_tx()
        tx1 = erc20.functions.transfer(pair_addr, int(amount_in_wei)).build_transaction(base1)
        res1 = self.send(tx1)
        # 2) swap from pair to recipient
        t0, t1 = self.pair_tokens(pair_address) or (None, None)
        if not t0 or not t1:
            return {'status': 0, 'error': 'pair_tokens_failed'}
        amount0Out = 0
        amount1Out = 0
        if token_out.lower() == t0.lower():
            amount0Out = int(min_out_wei)
        else:
            amount1Out = int(min_out_wei)
        base2 = self._legacy_gas_tx()
        tx2 = pair.functions.swap(int(amount0Out), int(amount1Out), Web3.to_checksum_address(recipient), b"").build_transaction(base2)
        res2 = self.send(tx2)
        return {'approve_or_transfer_tx': res1, 'swap_tx': res2, 'status': int(res1.get('status', 0) and res2.get('status', 0))}

    def swap_exact_input_single(self, token_in: str, token_out: str, amount_in_wei: int, fee: int = 500, amount_out_min: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600) -> Dict[str, Any]:
        token_in = Web3.to_checksum_address(token_in)
        token_out = Web3.to_checksum_address(token_out)
        recipient = recipient or self.account.address
        
        # Build params based on chain
        if self.chain == 'bsc':
            # PancakeSwap V3: includes deadline
            from time import time
            deadline = int(time()) + int(deadline_seconds)
            params = (
                token_in,
                token_out,
                fee,
                recipient,
                deadline,
                amount_in_wei,
                amount_out_min,
                0,  # sqrtPriceLimitX96
            )
        else:
            # Uniswap SwapRouter02: no deadline
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


    # --- v3 multi-hop helpers ---
    def v3_build_path(self, tokens: list[str], fees: list[int]) -> bytes:
        """Build a Uniswap v3 path bytes: token(20) + fee(3) + token(20) ..."""
        assert len(tokens) >= 2, "Need at least two tokens for a path"
        assert len(fees) == len(tokens) - 1, "fees must be tokens-1 length"
        path = b""
        for i, token in enumerate(tokens):
            path += bytes.fromhex(Web3.to_checksum_address(token)[2:])
            if i < len(fees):
                path += int(fees[i]).to_bytes(3, byteorder='big')
        return path

    def v3_quote_exact_input(self, path: bytes, amount_in_wei: int) -> Optional[int]:
        if not self.quoter:
            return None
        try:
            res = self.quoter.functions.quoteExactInput(path, int(amount_in_wei)).call()
            amount_out = int(res[0]) if isinstance(res, (list, tuple)) else int(res)
            return amount_out
        except Exception:
            return None

    def v3_exact_input(self, path: bytes, amount_in_wei: int, amount_out_min_wei: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600) -> Dict[str, Any]:
        """Execute v3 exactInput for multi-hop path."""
        recipient = recipient or self.account.address
        from time import time
        deadline = int(time()) + int(deadline_seconds)
        params = (
            path,
            recipient,
            deadline,
            int(amount_in_wei),
            int(amount_out_min_wei)
        )
        # exactInput((bytes path,address recipient,uint256 deadline,uint256 amountIn,uint256 amountOutMinimum))
        # Add ABI entry for exactInput dynamically to router if not present
        # Safer: build a transient contract with an ABI that includes exactInput
        exact_input_abi = [
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "bytes", "name": "path", "type": "bytes"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"}
                        ],
                        "internalType": "struct ISwapRouter.ExactInputParams",
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "exactInput",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function"
            }
        ]
        router = self.w3.eth.contract(address=self.router_address, abi=ROUTER_ABI + exact_input_abi)
        base = self._legacy_gas_tx({'value': 0})
        tx = router.functions.exactInput(params).build_transaction(base)
        return self.send(tx)

    def simulate_v3_exact_input_single(self, token_in: str, token_out: str, amount_in_wei: int, fee: int = 3000, amount_out_min: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600) -> bool:
        try:
            token_in = Web3.to_checksum_address(token_in)
            token_out = Web3.to_checksum_address(token_out)
            recipient = recipient or self.account.address
            from time import time
            deadline = int(time()) + int(deadline_seconds)
            params = (
                token_in,
                token_out,
                int(fee),
                recipient,
                deadline,
                int(amount_in_wei),
                int(amount_out_min),
                0,
            )
            base = self._legacy_gas_tx({'value': 0})
            tx = self.router_contract.functions.exactInputSingle(params).build_transaction(base)
            # eth_call simulation
            call = {
                'from': tx['from'],
                'to': tx['to'],
                'data': tx['data'],
                'value': tx.get('value', 0),
            }
            self.w3.eth.call(call)
            return True
        except Exception:
            return False

    def get_token_balance(self, token_address: str) -> Optional[float]:
        """
        Get ERC-20 token balance for the wallet
        
        Args:
            token_address: ERC-20 token contract address
            
        Returns:
            Token balance in token units (not wei)
        """
        try:
            # Create ERC-20 contract instance
            erc20_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=[{
                    "constant": True,
                    "inputs": [{"name": "account", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                }]
            )
            
            # Get balance in wei
            balance_wei = erc20_contract.functions.balanceOf(self.account.address).call()
            
            # Get token decimals
            decimals = self.get_token_decimals(token_address)
            
            # Convert to token units
            balance = balance_wei / (10 ** decimals)
            
            return balance
            
        except Exception as e:
            print(f"Error getting token balance for {token_address}: {e}")
            return None

    def simulate_v3_exact_input(self, path: bytes, amount_in_wei: int, amount_out_min_wei: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600) -> bool:
        try:
            recipient = recipient or self.account.address
            from time import time
            deadline = int(time()) + int(deadline_seconds)
            params = (
                path,
                recipient,
                deadline,
                int(amount_in_wei),
                int(amount_out_min_wei)
            )
            exact_input_abi = [
                {
                    "inputs": [
                        {
                            "components": [
                                {"internalType": "bytes", "name": "path", "type": "bytes"},
                                {"internalType": "address", "name": "recipient", "type": "address"},
                                {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                                {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"}
                            ],
                            "internalType": "struct ISwapRouter.ExactInputParams",
                            "name": "params",
                            "type": "tuple"
                        }
                    ],
                    "name": "exactInput",
                    "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                    "stateMutability": "payable",
                    "type": "function"
                }
            ]
            router = self.w3.eth.contract(address=self.router_address, abi=ROUTER_ABI + exact_input_abi)
            base = self._legacy_gas_tx({'value': 0})
            tx = router.functions.exactInput(params).build_transaction(base)
            call = {
                'from': tx['from'],
                'to': tx['to'],
                'data': tx['data'],
                'value': tx.get('value', 0),
            }
            self.w3.eth.call(call)
            return True
        except Exception:
            return False

    def get_token_balance(self, token_address: str) -> Optional[float]:
        """
        Get ERC-20 token balance for the wallet
        
        Args:
            token_address: ERC-20 token contract address
            
        Returns:
            Token balance in token units (not wei)
        """
        try:
            # Create ERC-20 contract instance
            erc20_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=[{
                    "constant": True,
                    "inputs": [{"name": "account", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                }]
            )
            
            # Get balance in wei
            balance_wei = erc20_contract.functions.balanceOf(self.account.address).call()
            
            # Get token decimals
            decimals = self.get_token_decimals(token_address)
            
            # Convert to token units
            balance = balance_wei / (10 ** decimals)
            
            return balance
            
        except Exception as e:
            print(f"Error getting token balance for {token_address}: {e}")
            return None

