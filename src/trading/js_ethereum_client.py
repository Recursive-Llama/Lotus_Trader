#!/usr/bin/env python3
"""
JavaScript Ethereum Client - Uses web3.js via Node.js
For executing Ethereum and Base trades
"""

import asyncio
import subprocess
import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class JSEthereumClient:
    """
    Ethereum client that uses JavaScript web3.js via Node.js
    """
    
    def __init__(self, rpc_url: str, private_key: str, chain_id: int = 1):
        self.rpc_url = rpc_url
        self.private_key = private_key
        self.chain_id = chain_id  # 1 for Ethereum, 8453 for Base
        
    async def execute_swap(self, 
                          sell_token: str, 
                          buy_token: str, 
                          sell_amount: str,
                          quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a 0x swap using JavaScript"""
        try:
            # Create JavaScript code for 0x swap
            js_code = f"""
const {{ Web3 }} = require('web3');

async function executeSwap() {{
    try {{
        const privateKey = '{self.private_key}';
        const web3 = new Web3('{self.rpc_url}');
        const account = web3.eth.accounts.privateKeyToAccount(privateKey);

        const quoteData = {json.dumps(quote_data)};

        const toHex = (v) => {{
            if (v === undefined || v === null) return undefined;
            try {{
                if (typeof v === 'string') return v.startsWith('0x') ? v : web3.utils.toHex(v);
                return web3.utils.toHex(v);
            }} catch (e) {{
                try {{ return '0x' + BigInt(v).toString(16); }} catch (_) {{ return v.toString(); }}
            }}
        }};

        // Build base tx
        const tx = {{
            from: account.address,
            to: quoteData.to,
            data: quoteData.data,
            value: toHex(quoteData.value || '0'),
            chainId: {self.chain_id}
        }};

        // Prefer EIP-1559 fee fields if present; otherwise gasPrice
        if (quoteData.maxFeePerGas && quoteData.maxPriorityFeePerGas) {{
            tx.maxFeePerGas = toHex(quoteData.maxFeePerGas);
            tx.maxPriorityFeePerGas = toHex(quoteData.maxPriorityFeePerGas);
        }} else if (quoteData.gasPrice) {{
            tx.gasPrice = toHex(quoteData.gasPrice);
        }} else {{
            // Fallback to current network gas price
            tx.gasPrice = toHex(await web3.eth.getGasPrice());
        }}

        // Set gas if provided; otherwise estimate
        if (quoteData.gas) {{
            tx.gas = toHex(quoteData.gas);
        }} else {{
            const est = await web3.eth.estimateGas({{
                from: tx.from, to: tx.to, data: tx.data, value: tx.value
            }});
            tx.gas = toHex(est);
        }}

        const signedTx = await web3.eth.accounts.signTransaction(tx, privateKey);
        const receipt = await web3.eth.sendSignedTransaction(signedTx.rawTransaction);

        console.log(JSON.stringify({{
            success: true,
            tx_hash: receipt.transactionHash,
            gas_used: receipt.gasUsed,
            block_number: receipt.blockNumber
        }}));
    }} catch (error) {{
        console.log(JSON.stringify({{
            success: false,
            error: error.message
        }}));
    }}
}}

executeSwap();
"""
            
            # Execute JavaScript
            process = await asyncio.create_subprocess_exec(
                'node', '-e', js_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result = json.loads(stdout.decode())
                if result.get('success'):
                    logger.info(f"✅ Ethereum swap executed: {result.get('tx_hash')}")
                    return result
                else:
                    logger.error(f"❌ Ethereum swap failed: {result.get('error')}")
                    return result
            else:
                error_msg = stderr.decode()
                logger.error(f"❌ JavaScript execution failed: {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Error executing Ethereum swap: {e}")
            return {"success": False, "error": str(e)}

    async def wrap_eth(self, amount_wei: str) -> Dict[str, Any]:
        """Wrap native ETH to WETH via deposit()."""
        try:
            weth = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2' if self.chain_id == 1 else '0x4200000000000000000000000000000000000006'
            js_code = f"""
 const {{ Web3 }} = require('web3');
 
 async function wrap() {{
   try {{
     const privateKey = '{self.private_key}';
     const web3 = new Web3('{self.rpc_url}');
     const account = web3.eth.accounts.privateKeyToAccount(privateKey);
     const toHex = (v) => (typeof v === 'string' && v.startsWith('0x')) ? v : web3.utils.toHex(v);
     const depositSelector = '0xd0e30db0';
     const valueWei = '{amount_wei}';
 
     // Base tx skeleton
     let tx = {{ from: account.address, to: '{weth}', data: depositSelector, value: toHex(valueWei), chainId: {self.chain_id} }};
 
     // Use direct send (no estimate) with safe gas and fees
     const gasLimit = 70000; // safe for WETH deposit
     const balanceWei = await web3.eth.getBalance(account.address);
 
     if ({self.chain_id} === 8453) {{
       // Base: legacy gasPrice
       const gasPriceWei = await web3.eth.getGasPrice();
       const nonce = await web3.eth.getTransactionCount(account.address);
       tx.gas = toHex(gasLimit);
       tx.gasPrice = toHex(gasPriceWei);
       tx.nonce = toHex(nonce);
       const requiredWei = (BigInt(valueWei) + BigInt(gasPriceWei) * BigInt(gasLimit)).toString();
       const sufficient = BigInt(balanceWei) >= BigInt(requiredWei);
       if (!sufficient) {{
         console.log(JSON.stringify({{success:false, error:'insufficient_funds_calc', details:{{balanceWei, valueWei, gasLimit, gasPriceWei, requiredWei}}}}));
         return;
       }}
     }} else {{
       // Ethereum: simple EIP-1559
       const baseFee = await web3.eth.getGasPrice();
       const priority = '1000000'; // 0.001 gwei
       const maxFee = (BigInt(baseFee) * 2n + BigInt(priority)).toString();
       const nonce = await web3.eth.getTransactionCount(account.address);
       tx.gas = toHex(gasLimit);
       tx.maxFeePerGas = toHex(maxFee);
       tx.maxPriorityFeePerGas = toHex(priority);
       tx.nonce = toHex(nonce);
       const requiredWei = (BigInt(valueWei) + BigInt(maxFee) * BigInt(gasLimit)).toString();
       const sufficient = BigInt(balanceWei) >= BigInt(requiredWei);
       if (!sufficient) {{
         console.log(JSON.stringify({{success:false, error:'insufficient_funds_calc', details:{{balanceWei, valueWei, gasLimit, maxFee, requiredWei}}}}));
         return;
       }}
     }}
 
     const signed = await web3.eth.accounts.signTransaction(tx, privateKey);
     const receipt = await web3.eth.sendSignedTransaction(signed.rawTransaction);
     console.log(JSON.stringify({{success:true, tx_hash: receipt.transactionHash}}));
   }} catch (e) {{
     console.log(JSON.stringify({{success:false, error: e.message}}));
   }}
 }}
 wrap();
 """
             process = await asyncio.create_subprocess_exec('node', '-e', js_code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
             stdout, stderr = await process.communicate()
             if process.returncode == 0:
                 try:
                     return json.loads(stdout.decode())
                 except Exception:
                     return {"success": False, "error": stdout.decode()}
             else:
                 return {"success": False, "error": stderr.decode()}
        except Exception as e:
            logger.error(f"Error wrapping ETH: {e}")
            return {"success": False, "error": str(e)}

    async def approve_erc20(self, token: str, spender: str, amount_wei: str) -> Dict[str, Any]:
        """Approve spender for ERC20 token amount."""
        try:
            js_code = f"""
const {{ Web3 }} = require('web3');

async function approve() {{
  try {{
    const privateKey = '{self.private_key}';
    const web3 = new Web3('{self.rpc_url}');
    const account = web3.eth.accounts.privateKeyToAccount(privateKey);
    const toHex = (v) => (typeof v === 'string' && v.startsWith('0x')) ? v : web3.utils.toHex(v);
    const token = '{token}';
    const spender = '{spender}';
    const amount = '{amount_wei}';
    // approve(address,uint256) selector 0x095ea7b3
    const selector = '0x095ea7b3';
    const paddedSpender = spender.toLowerCase().replace('0x','').padStart(64,'0');
    const paddedAmount = BigInt(amount).toString(16).padStart(64,'0');
    const data = selector + paddedSpender + paddedAmount;
    let tx = {{
      from: account.address,
      to: token,
      data: '0x'+data,
      value: '0x0',
      chainId: {self.chain_id}
    }};
    // EIP-1559 fees
    try {{
      const baseFee = await web3.eth.getGasPrice();
      tx.maxFeePerGas = toHex(baseFee);
      tx.maxPriorityFeePerGas = toHex(baseFee);
    }} catch {{}}
    // Gas estimate
    try {{
      const est = await web3.eth.estimateGas({{from: tx.from, to: tx.to, data: tx.data}});
      tx.gas = toHex(est);
    }} catch {{}}
    const signed = await web3.eth.accounts.signTransaction(tx, privateKey);
    const receipt = await web3.eth.sendSignedTransaction(signed.rawTransaction);
    console.log(JSON.stringify({{success:true, tx_hash: receipt.transactionHash}}));
  }} catch (e) {{
    console.log(JSON.stringify({{success:false, error: e.message}}));
  }}
}}
approve();
"""
            process = await asyncio.create_subprocess_exec('node', '-e', js_code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                try:
                    return json.loads(stdout.decode())
                except Exception:
                    return {"success": False, "error": stdout.decode()}
            else:
                return {"success": False, "error": stderr.decode()}
        except Exception as e:
            logger.error(f"Error approving ERC20: {e}")
            return {"success": False, "error": str(e)}

    async def uniswap_v3_exact_input_single(self, router: str, token_in: str, token_out: str, fee: int, amount_in_wei: str, amount_out_min_wei: str, recipient: str) -> Dict[str, Any]:
        """Swap via Uniswap v3 SwapRouter02 exactInputSingle using WETH as input."""
        try:
            js_code = f"""
const {{ Web3 }} = require('web3');

async function swap() {{
  try {{
    const web3 = new Web3('{self.rpc_url}');
    const privateKey = '{self.private_key}';
    const account = web3.eth.accounts.privateKeyToAccount(privateKey);
    const toHex = (v) => (typeof v === 'string' && v.startsWith('0x')) ? v : web3.utils.toHex(v);

    const router = new web3.eth.Contract([
      {{
        "inputs": [
          {{
            "components": [
              {{"internalType":"address","name":"tokenIn","type":"address"}},
              {{"internalType":"address","name":"tokenOut","type":"address"}},
              {{"internalType":"uint24","name":"fee","type":"uint24"}},
              {{"internalType":"address","name":"recipient","type":"address"}},
              {{"internalType":"uint256","name":"deadline","type":"uint256"}},
              {{"internalType":"uint256","name":"amountIn","type":"uint256"}},
              {{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"}},
              {{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}}
            ],
            "internalType":"struct ISwapRouter.ExactInputSingleParams",
            "name":"params",
            "type":"tuple"
          }}
        ],
        "name":"exactInputSingle",
        "outputs":[{{"internalType":"uint256","name":"amountOut","type":"uint256"}}],
        "stateMutability":"payable",
        "type":"function"
      }}
    ], '{router}');

    const deadline = Math.floor(Date.now()/1000) + 600;
    const params = {{
      tokenIn: '{token_in}',
      tokenOut: '{token_out}',
      fee: {fee},
      recipient: '{recipient}',
      deadline: toHex(deadline),
      amountIn: '{amount_in_wei}',
      amountOutMinimum: '{amount_out_min_wei}',
      sqrtPriceLimitX96: '0'
    }};

    const data = router.methods.exactInputSingle(params).encodeABI();
    let tx = {{
      from: account.address,
      to: '{router}',
      data: data,
      value: '0x0',
      chainId: {self.chain_id}
    }};

    try {{
      const baseFee = await web3.eth.getGasPrice();
      tx.maxFeePerGas = toHex(baseFee);
      tx.maxPriorityFeePerGas = toHex(baseFee);
    }} catch {{}}

    try {{
      const est = await web3.eth.estimateGas({{from: tx.from, to: tx.to, data: tx.data, value: tx.value}});
      tx.gas = toHex(est);
    }} catch {{}}

    const signed = await web3.eth.accounts.signTransaction(tx, privateKey);
    const receipt = await web3.eth.sendSignedTransaction(signed.rawTransaction);
    console.log(JSON.stringify({{success:true, tx_hash: receipt.transactionHash}}));
  }} catch (e) {{
    console.log(JSON.stringify({{success:false, error: e.message}}));
  }}
}}
swap();
"""
            process = await asyncio.create_subprocess_exec('node', '-e', js_code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                try:
                    return json.loads(stdout.decode())
                except Exception:
                    return {"success": False, "error": stdout.decode()}
            else:
                return {"success": False, "error": stderr.decode()}
        except Exception as e:
            logger.error(f"Error swapping Uniswap v3: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_balance(self, token_address: str = None) -> Optional[float]:
        """Get ETH or token balance"""
        try:
            if token_address:
                # Token balance (would need ERC20 contract interaction)
                return None
            else:
                # ETH balance
                js_code = f"""
const {{ Web3 }} = require('web3');

async function getBalance() {{
    try {{
        const web3 = new Web3('{self.rpc_url}');
        const privateKey = '{self.private_key}';
        const account = web3.eth.accounts.privateKeyToAccount(privateKey);
        const balance = await web3.eth.getBalance(account.address);
        const ethBalance = web3.utils.fromWei(balance, 'ether');
        console.log(ethBalance);
    }} catch (error) {{
        console.log('0');
    }}
}}

getBalance();
"""
                
                process = await asyncio.create_subprocess_exec(
                    'node', '-e', js_code,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    balance = float(stdout.decode().strip())
                    return balance
                else:
                    logger.error(f"Error getting ETH balance: {stderr.decode()}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None

if __name__ == "__main__":
    async def test_ethereum():
        client = JSEthereumClient(
            rpc_url="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY",
            private_key="0x...",
            chain_id=1
        )
        
        balance = await client.get_balance()
        print(f"ETH Balance: {balance}")
    
    asyncio.run(test_ethereum())
