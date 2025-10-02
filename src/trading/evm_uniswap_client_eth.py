#!/usr/bin/env python3
"""
Ethereum Uniswap Client (EIP-1559, SwapRouter02)

Separate from Base client to avoid regressions.
Implements wrap ETH->WETH, approve ERC20, exactInputSingle swap with EIP-1559 fees.
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any

from web3 import Web3
from eth_account import Account


WETH_ADDRESS = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
ROUTER02_ADDRESS = '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'  # Uniswap v3 SwapRouter02
V3_ROUTER_ADDRESS = '0xE592427A0AEce92De3Edee1F18E0157C05861564'  # Uniswap v3 Router (classic)
V2_ROUTER_ADDRESS = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'  # Uniswap v2 Router02


WETH_ABI = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"},
]

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
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
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokensSupportingFeeOnTransferTokens",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

QUOTER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenIn", "type": "address"},
            {"internalType": "address", "name": "tokenOut", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"},
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

QUOTER_ADDRESS = '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6'


class EthUniswapClient:
    def __init__(self, rpc_url: Optional[str] = None, private_key: Optional[str] = None, gas_limit_default: int = 300000):
        self.chain_id = 1
        self.rpc_url = rpc_url or os.getenv('ETH_RPC_URL')
        if not self.rpc_url:
            raise ValueError('Missing ETH_RPC_URL')
        self.private_key = private_key or os.getenv('ETHEREUM_WALLET_PRIVATE_KEY') or os.getenv('ETH_WALLET_PRIVATE_KEY')
        if not self.private_key:
            raise ValueError('Missing Ethereum private key')

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError(f'Failed to connect: {self.rpc_url}')
        self.account = Account.from_key(self.private_key)
        self.gas_limit_default = gas_limit_default

        self.weth = self.w3.eth.contract(address=Web3.to_checksum_address(WETH_ADDRESS), abi=WETH_ABI)
        self.router = self.w3.eth.contract(address=Web3.to_checksum_address(ROUTER02_ADDRESS), abi=ROUTER_ABI)
        self.v3_router = self.w3.eth.contract(address=Web3.to_checksum_address(V3_ROUTER_ADDRESS), abi=ROUTER_ABI)
        self.v2_router = self.w3.eth.contract(address=Web3.to_checksum_address(V2_ROUTER_ADDRESS), abi=V2_ROUTER_ABI)
        self.quoter = self.w3.eth.contract(address=Web3.to_checksum_address(QUOTER_ADDRESS), abi=QUOTER_ABI)

    def _eip1559_base(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base_fee = self.w3.eth.gas_price
        priority = int(1e9)  # 1 gwei
        max_fee = base_fee * 2 + priority
        nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
        tx = {
            'from': self.account.address,
            'chainId': self.chain_id,
            'nonce': nonce,
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': priority,
            'gas': self.gas_limit_default,
        }
        if overrides:
            tx.update(overrides)
        return tx

    def _send(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {'tx_hash': tx_hash.hex(), 'status': int(receipt.status), 'gas_used': int(receipt.gasUsed)}

    def wrap_eth(self, amount_eth: float, gas_limit: int = 70000) -> Dict[str, Any]:
        amount_wei = self.w3.to_wei(amount_eth, 'ether')
        # Do not set 'to' when building a contract function transaction; web3 sets it
        base = self._eip1559_base({'gas': gas_limit, 'value': amount_wei})
        tx = self.weth.functions.deposit().build_transaction(base)
        return self._send(tx)

    def approve_erc20(self, token: str, spender: str, amount_wei: int, gas_limit: int = 100000) -> Dict[str, Any]:
        erc20 = self.w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
        base = self._eip1559_base({'gas': gas_limit})
        tx = erc20.functions.approve(Web3.to_checksum_address(spender), amount_wei).build_transaction(base)
        return self._send(tx)

    def erc20_allowance(self, token: str, owner: str, spender: str) -> int:
        erc20 = self.w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
        return int(erc20.functions.allowance(Web3.to_checksum_address(owner), Web3.to_checksum_address(spender)).call())

    def get_token_decimals(self, token: str) -> int:
        try:
            erc20 = self.w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
            return int(erc20.functions.decimals().call())
        except Exception:
            return 18

    def swap_exact_input_single(self, token_in: str, token_out: str, amount_in_wei: int, fee: int = 3000, amount_out_min: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600) -> Dict[str, Any]:
        recipient = recipient or self.account.address
        from time import time
        deadline = int(time()) + deadline_seconds
        params = (
            Web3.to_checksum_address(token_in),
            Web3.to_checksum_address(token_out),
            fee,
            recipient,
            deadline,
            amount_in_wei,
            amount_out_min,
            0,
        )
        base = self._eip1559_base({'value': 0})
        tx = self.router.functions.exactInputSingle(params).build_transaction(base)
        return self._send(tx)

    def v3_swap_exact_input_single(self, token_in: str, token_out: str, amount_in_wei: int, fee: int = 3000, amount_out_min: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600) -> Dict[str, Any]:
        """Classic V3 Router swap (more reliable for problematic tokens)"""
        recipient = recipient or self.account.address
        from time import time
        deadline = int(time()) + deadline_seconds
        params = (
            Web3.to_checksum_address(token_in),
            Web3.to_checksum_address(token_out),
            fee,
            recipient,
            deadline,
            amount_in_wei,
            amount_out_min,
            0,
        )
        base = self._eip1559_base({'value': 0})
        tx = self.v3_router.functions.exactInputSingle(params).build_transaction(base)
        return self._send(tx)

    def v3_quote_amount_out(self, token_in: str, token_out: str, amount_in_wei: int, fee: int = 3000) -> Optional[int]:
        try:
            out = self.quoter.functions.quoteExactInputSingle(
                Web3.to_checksum_address(token_in),
                Web3.to_checksum_address(token_out),
                fee,
                amount_in_wei,
                0
            ).call()
            return int(out)
        except Exception:
            return None

    # --- Uniswap v2 helpers ---
    def v2_get_amounts_out(self, token_in: str, token_out: str, amount_in_wei: int) -> Optional[list[int]]:
        try:
            path = [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)]
            return self.v2_router.functions.getAmountsOut(amount_in_wei, path).call()
        except Exception:
            return None

    def v2_swap_exact_tokens_for_tokens(self, token_in: str, token_out: str, amount_in_wei: int, amount_out_min_wei: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600) -> Dict[str, Any]:
        recipient = recipient or self.account.address
        path = [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)]
        from time import time
        deadline = int(time()) + deadline_seconds
        base = self._eip1559_base()
        tx = self.v2_router.functions.swapExactTokensForTokens(
            amount_in_wei,
            amount_out_min_wei,
            path,
            recipient,
            deadline
        ).build_transaction(base)
        return self._send(tx)

    def v2_swap_exact_tokens_for_tokens_supporting_fee(self, token_in: str, token_out: str, amount_in_wei: int, amount_out_min_wei: int = 0, recipient: Optional[str] = None, deadline_seconds: int = 600) -> Dict[str, Any]:
        recipient = recipient or self.account.address
        path = [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)]
        from time import time
        deadline = int(time()) + deadline_seconds
        base = self._eip1559_base()
        tx = self.v2_router.functions.swapExactTokensForTokensSupportingFeeOnTransferTokens(
            amount_in_wei,
            amount_out_min_wei,
            path,
            recipient,
            deadline
        ).build_transaction(base)
        return self._send(tx)

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


