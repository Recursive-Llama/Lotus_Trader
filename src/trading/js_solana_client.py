#!/usr/bin/env python3
"""
JavaScript Solana Client - Uses @solana/web3.js via Node.js
This is the working approach that actually works!
"""

import asyncio
import subprocess
import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class JSSolanaClient:
    """
    Solana client that uses JavaScript @solana/web3.js via Node.js
    This is the working approach that actually works!
    """
    
    def __init__(self, rpc_url: str, private_key: str):
        self.rpc_url = rpc_url
        self.private_key = private_key
        
    async def execute_transfer(self, to_pubkey: str, lamports: int) -> Dict[str, Any]:
        """Execute a SOL transfer using JavaScript"""
        try:
            # Create JavaScript code
            js_code = f"""
const {{ Connection, Keypair, VersionedTransaction, LAMPORTS_PER_SOL }} = require('@solana/web3.js');
const bs58 = require('bs58');

async function executeTransfer() {{
    try {{
        // Load wallet
        const privateKey = '{self.private_key}';
        const keyBytes = bs58.decode(privateKey);
        const wallet = Keypair.fromSecretKey(keyBytes);
        
        // Get RPC client
        const connection = new Connection('{self.rpc_url}');
        
        // Get recent blockhash
        const {{ blockhash }} = await connection.getLatestBlockhash();
        
        // Create transfer instruction
        const {{ SystemProgram }} = require('@solana/web3.js');
        const transferInstruction = SystemProgram.transfer({{
            fromPubkey: wallet.publicKey,
            toPubkey: new (require('@solana/web3.js')).PublicKey('{to_pubkey}'),
            lamports: {lamports}
        }});
        
        // Create VersionedTransaction
        const {{ TransactionMessage }} = require('@solana/web3.js');
        const message = new VersionedTransaction(
            new TransactionMessage({{
                payerKey: wallet.publicKey,
                recentBlockhash: blockhash,
                instructions: [transferInstruction]
            }}).compileToV0Message()
        );
        
        // Sign the transaction
        message.sign([wallet]);
        
        // Send the transaction
        const signature = await connection.sendTransaction(message, {{
            skipPreflight: false,
            preflightCommitment: 'processed'
        }});
        
        // Wait for confirmation
        const confirmation = await connection.confirmTransaction(signature, 'confirmed');
        
        if (confirmation.value.err) {{
            throw new Error(`Transaction failed: ${{confirmation.value.err}}`);
        }}
        
        return {{
            success: true,
            signature: signature
        }};
        
    }} catch (error) {{
        return {{
            success: false,
            error: error.message
        }};
    }}
}}

executeTransfer().then(result => {{
    console.log(JSON.stringify(result));
}}).catch(error => {{
    console.error(JSON.stringify({{ success: false, error: error.message }}));
}});
"""
            
            # Write JavaScript to temporary file
            with open('temp_transfer.js', 'w') as f:
                f.write(js_code)
            
            # Execute JavaScript
            result = subprocess.run(
                ['node', 'temp_transfer.js'],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            # Clean up
            os.remove('temp_transfer.js')
            
            if result.returncode != 0:
                raise Exception(f"JavaScript execution failed: {result.stderr}")
            
            # Parse result
            result_data = json.loads(result.stdout.strip())
            
            if not result_data.get('success'):
                raise Exception(f"Transaction failed: {result_data.get('error')}")
            
            return result_data
            
        except Exception as e:
            logger.error(f"Error executing transfer: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_jupiter_swap(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50) -> Dict[str, Any]:
        """Execute a Jupiter swap using JavaScript"""
        try:
            # Create JavaScript code for Jupiter swap
            js_code = f"""
const {{ Connection, Keypair, VersionedTransaction }} = require('@solana/web3.js');
const bs58 = require('bs58');
const axios = require('axios');

async function executeJupiterSwap() {{
    try {{
        // Load wallet
        const privateKey = '{self.private_key}';
        const keyBytes = bs58.decode(privateKey);
        const wallet = Keypair.fromSecretKey(keyBytes);
        
        // Get RPC client
        const connection = new Connection('{self.rpc_url}');
        
        // Get quote from Jupiter
        const quoteResponse = await axios.get('https://quote-api.jup.ag/v6/quote', {{
            params: {{
                inputMint: '{input_mint}',
                outputMint: '{output_mint}',
                amount: '{amount}',
                slippageBps: '{slippage_bps}',
                onlyDirectRoutes: 'false',
                asLegacyTransaction: 'false'
            }}
        }});
        
        if (!quoteResponse.data || quoteResponse.data.error) {{
            throw new Error(quoteResponse.data?.error || 'Invalid quote response');
        }}
        
        // Get swap transaction
        const swapRequest = {{
            quoteResponse: quoteResponse.data,
            userPublicKey: wallet.publicKey.toString(),
            wrapAndUnwrapSol: true,
            useSharedAccounts: false,
            prioritizationFeeLamports: 'auto',
            asLegacyTransaction: false
        }};
        
        const swapResponse = await axios.post('https://quote-api.jup.ag/v6/swap', swapRequest);
        
        if (!swapResponse.data || swapResponse.data.error) {{
            throw new Error(swapResponse.data?.error || 'Invalid swap response');
        }}
        
        // Deserialize and sign the transaction
        const swapTransactionBuf = Buffer.from(swapResponse.data.swapTransaction, 'base64');
        const transaction = VersionedTransaction.deserialize(swapTransactionBuf);
        
        // Sign the transaction
        transaction.sign([wallet]);
        
        // Send the transaction
        const signature = await connection.sendTransaction(transaction, {{
            skipPreflight: false,
            preflightCommitment: 'processed'
        }});
        
        // Wait for confirmation
        const confirmation = await connection.confirmTransaction(signature, 'confirmed');
        
        if (confirmation.value.err) {{
            throw new Error(`Transaction failed: ${{confirmation.value.err}}`);
        }}
        
        return {{
            success: true,
            signature: signature,
            inputAmount: quoteResponse.data.inAmount,
            outputAmount: quoteResponse.data.outAmount,
            priceImpact: quoteResponse.data.priceImpactPct
        }};
        
    }} catch (error) {{
        return {{
            success: false,
            error: error.message
        }};
    }}
}}

executeJupiterSwap().then(result => {{
    console.log(JSON.stringify(result));
}}).catch(error => {{
    console.error(JSON.stringify({{ success: false, error: error.message }}));
}});
"""
            
            # Write JavaScript to temporary file
            with open('temp_jupiter.js', 'w') as f:
                f.write(js_code)
            
            # Execute JavaScript
            result = subprocess.run(
                ['node', 'temp_jupiter.js'],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            # Clean up
            os.remove('temp_jupiter.js')
            
            if result.returncode != 0:
                raise Exception(f"JavaScript execution failed: {result.stderr}")
            
            # Parse result
            result_data = json.loads(result.stdout.strip())
            
            if not result_data.get('success'):
                raise Exception(f"Jupiter swap failed: {result_data.get('error')}")
            
            return result_data
            
        except Exception as e:
            logger.error(f"Error executing Jupiter swap: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_token_decimals(self, mint_address: str) -> Dict[str, Any]:
        """Get token decimals for a given mint address"""
        try:
            # Create JavaScript code to get token decimals
            js_code = f"""
const {{ Connection, PublicKey }} = require('@solana/web3.js');
const {{ getMint }} = require('@solana/spl-token');

async function getTokenDecimals() {{
    try {{
        const connection = new Connection('{self.rpc_url}');
        const mintAddress = new PublicKey('{mint_address}');
        
        const mintInfo = await getMint(connection, mintAddress);
        
        return {{
            success: true,
            decimals: mintInfo.decimals,
            mint: mintAddress.toString()
        }};
        
    }} catch (error) {{
        return {{
            success: false,
            error: error.message
        }};
    }}
}}

getTokenDecimals().then(result => {{
    console.log(JSON.stringify(result));
}}).catch(error => {{
    console.error(JSON.stringify({{ success: false, error: error.message }}));
}});
"""
            
            # Write JavaScript to temporary file
            with open('temp_decimals.js', 'w') as f:
                f.write(js_code)
            
            # Execute JavaScript
            result = subprocess.run(
                ['node', 'temp_decimals.js'],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            # Clean up
            os.remove('temp_decimals.js')
            
            if result.returncode != 0:
                raise Exception(f"JavaScript execution failed: {result.stderr}")
            
            # Parse result
            result_data = json.loads(result.stdout.strip())
            
            if not result_data.get('success'):
                raise Exception(f"Failed to get token decimals: {result_data.get('error')}")
            
            return result_data
            
        except Exception as e:
            logger.error(f"Error getting token decimals: {e}")
            return {
                'success': False,
                'error': str(e)
            }
