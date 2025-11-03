import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.trading.js_solana_client import JSSolanaClient

async def test_exact_amount():
    print("🔬 Testing exact amount that's failing in production")
    print("=" * 60)
    
    helius_key = os.getenv('HELIUS_API_KEY')
    solana_rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}" if helius_key else "https://api.mainnet-beta.solana.com"
    sol_private_key = os.getenv('SOL_WALLET_PRIVATE_KEY')
    
    js_client = JSSolanaClient(solana_rpc_url, sol_private_key)
    
    pump_mint = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
    sol_mint = "So11111111111111111111111111111111111111112"
    
    # Test the exact amount that's failing in production
    exact_amount = 3421.691343  # PUMP tokens
    decimals = 6
    amount_raw = int(exact_amount * (10 ** decimals))
    
    print(f"🎯 Testing exact production amount:")
    print(f"   Amount: {exact_amount} PUMP tokens")
    print(f"   Raw units: {amount_raw}")
    print(f"   Decimals: {decimals}")
    
    # Test Jupiter swap with this exact amount
    result = await js_client.execute_jupiter_swap(
        input_mint=pump_mint,
        output_mint=sol_mint,
        amount=amount_raw,
        slippage_bps=100
    )
    
    if result.get('success'):
        print("✅ SUCCESS! The exact amount works")
        print(f"   Transaction: {result.get('signature')}")
        print(f"   Input: {result.get('inputAmount')}")
        print(f"   Output: {result.get('outputAmount')}")
    else:
        print("❌ FAILED! Same error as production")
        print(f"   Error: {result.get('error')}")
        
        # Let's try with different slippage
        print("\n🔄 Trying with higher slippage (300 bps)...")
        result2 = await js_client.execute_jupiter_swap(
            input_mint=pump_mint,
            output_mint=sol_mint,
            amount=amount_raw,
            slippage_bps=300
        )
        
        if result2.get('success'):
            print("✅ SUCCESS with higher slippage!")
            print(f"   Transaction: {result2.get('signature')}")
        else:
            print("❌ Still failed with higher slippage")
            print(f"   Error: {result2.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_exact_amount())
