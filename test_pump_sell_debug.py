#!/usr/bin/env python3
"""
Isolated test script to debug PUMP token sell issues
"""

import asyncio
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.trading.js_solana_client import JSSolanaClient
from src.intelligence.trader_lowcap.solana_executor import SolanaExecutor

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pump_sell_debug.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_pump_sell():
    """Test PUMP token sell with detailed logging"""
    
    print("🧪 Testing PUMP Token Sell with Detailed Logging")
    print("=" * 60)
    
    # PUMP token details
    pump_mint = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
    pump_symbol = "PUMP"
    
    try:
        # Initialize JS Solana client
        print("🔧 Initializing JS Solana client...")
        js_client = JSSolanaClient(
            rpc_url="https://mainnet.helius-rpc.com/?api-key=your-api-key",  # Replace with actual API key
            private_key="your-private-key"  # Replace with actual private key
        )
        
        # Initialize Solana executor
        executor = SolanaExecutor(js_client)
        
        print(f"✅ Components initialized")
        print(f"🎯 Testing token: {pump_symbol} ({pump_mint})")
        
        # Get current token balance
        print("\n📊 Checking current token balance...")
        balance_result = await js_client.get_spl_token_balance(pump_mint, "8VYRUrQkugXnySsCfq55gXei88HhhimXYfsj7tsBhfyV")
        print(f"Balance result: {balance_result}")
        
        if not balance_result.get('success'):
            print(f"❌ Failed to get balance: {balance_result.get('error')}")
            return
        
        current_balance = float(balance_result.get('balance', 0))
        print(f"💰 Current balance: {current_balance} {pump_symbol}")
        
        if current_balance <= 0:
            print("❌ No tokens to sell")
            return
        
        # Test with a small amount first
        test_amount = min(current_balance * 0.01, 100)  # 1% or max 100 tokens
        target_price_sol = 0.00002  # Example target price
        
        print(f"\n🔄 Attempting to sell {test_amount} {pump_symbol} tokens")
        print(f"🎯 Target price: {target_price_sol} SOL")
        
        # Execute the sell with detailed logging
        print("\n📝 Executing sell with detailed logging...")
        result = await executor.execute_sell(
            token_mint=pump_mint,
            tokens_to_sell=test_amount,
            target_price_sol=target_price_sol
        )
        
        print(f"\n📋 Sell result: {result}")
        
        if result:
            print("✅ Sell successful!")
            print(f"   Transaction hash: {result.get('tx_hash')}")
            print(f"   SOL received: {result.get('actual_sol_received')}")
        else:
            print("❌ Sell failed - no result returned")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        logger.exception("Full error details:")
        import traceback
        traceback.print_exc()

async def test_jupiter_direct():
    """Test Jupiter swap directly with detailed logging"""
    
    print("\n" + "=" * 60)
    print("🔬 Testing Jupiter Swap Directly")
    print("=" * 60)
    
    pump_mint = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
    sol_mint = "So11111111111111111111111111111111111111112"
    
    try:
        # Initialize JS Solana client
        js_client = JSSolanaClient(
            rpc_url="https://mainnet.helius-rpc.com/?api-key=your-api-key",  # Replace with actual API key
            private_key="your-private-key"  # Replace with actual private key
        )
        
        # Test with a very small amount
        test_amount = 1  # 1 token (6 decimals = 1,000,000 raw units)
        slippage_bps = 100  # 1% slippage
        
        print(f"🔄 Testing Jupiter swap: {pump_mint} -> {sol_mint}")
        print(f"💰 Amount: {test_amount} tokens")
        print(f"📊 Slippage: {slippage_bps} bps")
        
        # Convert to raw units (6 decimals for PUMP)
        amount_raw = int(test_amount * 1_000_000)
        
        print(f"🔢 Raw amount: {amount_raw}")
        
        # Execute Jupiter swap
        result = await js_client.execute_jupiter_swap(
            input_mint=pump_mint,
            output_mint=sol_mint,
            amount=amount_raw,
            slippage_bps=slippage_bps
        )
        
        print(f"\n📋 Jupiter swap result: {result}")
        
        if result.get('success'):
            print("✅ Jupiter swap successful!")
        else:
            print(f"❌ Jupiter swap failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error during Jupiter test: {e}")
        logger.exception("Full error details:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting PUMP Sell Debug Test")
    print("⚠️  Make sure to update the API key and private key in the script!")
    
    # Run both tests
    asyncio.run(test_pump_sell())
    asyncio.run(test_jupiter_direct())
    
    print("\n🏁 Test completed. Check pump_sell_debug.log for detailed logs.")
