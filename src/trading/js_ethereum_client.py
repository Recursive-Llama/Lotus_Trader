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
const axios = require('axios');

async function executeSwap() {{
    try {{
        // Load wallet
        const privateKey = '{self.private_key}';
        const web3 = new Web3('{self.rpc_url}');
        const account = web3.eth.accounts.privateKeyToAccount(privateKey);
        
        // Get quote data
        const quoteData = {json.dumps(quote_data)};
        
        // Execute the swap
        const tx = {{
            from: account.address,
            to: quoteData.to,
            data: quoteData.data,
            value: quoteData.value || '0',
            gas: quoteData.gas,
            gasPrice: quoteData.gasPrice
        }};
        
        // Sign and send transaction
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
