#!/usr/bin/env python3
"""
Test Jupiter swap using JavaScript approach
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_js_jupiter():
    """Test Jupiter swap using JavaScript"""
    try:
        from src.trading.js_solana_client import JSSolanaClient
        
        # Get environment variables
        private_key = os.getenv('SOL_WALLET_PRIVATE_KEY')
        helius_key = os.getenv('HELIUS_API_KEY')
        
        if not private_key:
            print("❌ No SOL_WALLET_PRIVATE_KEY in environment")
            return
        
        # Get RPC URL
        if helius_key:
            rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
        else:
            rpc_url = "https://api.mainnet-beta.solana.com"
        
        # Create JavaScript client
        js_client = JSSolanaClient(rpc_url, private_key)
        
        print("🔍 Testing Jupiter swap using JavaScript approach...")
        
        # Test SOL → BONK swap
        result = await js_client.execute_jupiter_swap(
            input_mint='So11111111111111111111111111111111111111112',  # SOL
            output_mint='DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  # BONK
            amount=1000000,  # 0.001 SOL in lamports
            slippage_bps=100
        )
        
        if result.get('success'):
            print("🎉 SUCCESS! Jupiter swap executed!")
            print(f"Signature: {result.get('signature')}")
            print(f"Input Amount: {result.get('inputAmount')}")
            print(f"Output Amount: {result.get('outputAmount')}")
            print(f"Price Impact: {result.get('priceImpact')}%")
        else:
            print(f"❌ FAILED: {result.get('error')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_js_jupiter())
