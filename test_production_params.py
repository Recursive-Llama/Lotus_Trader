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

async def test_production_params():
    print("🔬 Testing with production parameters")
    print("=" * 60)
    
    helius_key = os.getenv('HELIUS_API_KEY')
    solana_rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}" if helius_key else "https://api.mainnet-beta.solana.com"
    sol_private_key = os.getenv('SOL_WALLET_PRIVATE_KEY')
    
    js_client = JSSolanaClient(solana_rpc_url, sol_private_key)
    
    pump_mint = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
    sol_mint = "So11111111111111111111111111111111111111112"
    
    # Test with production parameters
    exact_amount = 3421.691343  # PUMP tokens
    decimals = 6
    amount_raw = int(exact_amount * (10 ** decimals))
    
    # Test different slippage settings like production
    slippage_tests = [
        (50, "Default slippage (50 bps)"),
        (250, "Token-2022 slippage (250 bps)"),
        (100, "My test slippage (100 bps)"),
        (500, "High slippage (500 bps)")
    ]
    
    for slippage_bps, description in slippage_tests:
        print(f"\n🔄 Testing {description}")
        print(f"   Amount: {exact_amount} PUMP tokens")
        print(f"   Slippage: {slippage_bps} bps")
        
        result = await js_client.execute_jupiter_swap(
            input_mint=pump_mint,
            output_mint=sol_mint,
            amount=amount_raw,
            slippage_bps=slippage_bps
        )
        
        if result.get('success'):
            print(f"✅ SUCCESS with {slippage_bps} bps slippage!")
            print(f"   Transaction: {result.get('signature')}")
            print(f"   Input: {result.get('inputAmount')}")
            print(f"   Output: {result.get('outputAmount')}")
        else:
            print(f"❌ FAILED with {slippage_bps} bps slippage")
            print(f"   Error: {result.get('error')}")
            
            # Check if it's the same 0x1788 error
            if '0x1788' in str(result.get('error', '')):
                print("   🎯 This is the SAME 0x1788 error as production!")
            else:
                print("   Different error than production")

if __name__ == "__main__":
    asyncio.run(test_production_params())
