#!/usr/bin/env python3
"""
Test PUMP sell with the actual amount that's failing in production
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

from src.intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
from src.utils.supabase_manager import SupabaseManager

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pump_large_amount_test.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_pump_large_amount():
    """Test PUMP sell with the actual amount that's failing in production"""
    
    print("🧪 Testing PUMP Sell with Production Amount")
    print("=" * 60)
    
    try:
        # Initialize the trading system
        print("🔧 Initializing trading system...")
        supabase_manager = SupabaseManager()
        
        trader = TraderLowcapSimpleV2(
            supabase_manager=supabase_manager,
            config={
                'book_id': 'social',
                'min_curator_score': 0.6,
                'max_exposure_pct': 100.0,
                'max_positions': 30,
                'min_allocation_pct': 1.0,
                'default_allocation_pct': 3.0,
                'ignore_tokens': ['SOL', 'ETH', 'BTC', 'USDC', 'USDT', 'WETH'],
                'min_volume_requirements': {
                    'solana': 100000,
                    'ethereum': 25000,
                    'base': 25000,
                }
            }
        )
        
        print("✅ Trading system initialized")
        
        # Check if we have the Solana executor
        if not trader.sol_executor:
            print("❌ Solana executor not available")
            return
        
        if not trader.js_solana_client:
            print("❌ JS Solana client not available")
            return
        
        print("✅ Solana executor and JS client available")
        
        # PUMP token details
        pump_contract = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
        pump_symbol = "PUMP"
        
        print(f"🎯 Testing token: {pump_symbol} ({pump_contract})")
        
        # Check current balance using the wallet manager
        print("\n💰 Checking current token balance...")
        balance = await trader.wallet_manager.get_balance('solana', pump_contract)
        print(f"Balance: {balance}")
        
        if not balance or balance <= 0:
            print("❌ No tokens to sell")
            return
        
        # Test with the actual amount that's failing in production
        production_amount = 4422.691343  # The amount from production logs
        target_price_sol = 0.00002  # Example target price
        
        print(f"\n🔄 Testing sell with PRODUCTION amount:")
        print(f"   Amount: {production_amount} {pump_symbol}")
        print(f"   Target price: {target_price_sol} SOL")
        print(f"   Expected SOL: {production_amount * target_price_sol:.6f} SOL")
        
        # Use the Solana executor directly
        print("\n🔧 Using Solana executor for sell...")
        result = await trader.sol_executor.execute_sell(
            token_mint=pump_contract,
            tokens_to_sell=production_amount,
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

async def test_jupiter_direct_large():
    """Test Jupiter swap directly with the large amount"""
    
    print("\n" + "=" * 60)
    print("🔬 Testing Jupiter Swap Directly with Large Amount")
    print("=" * 60)
    
    try:
        # Initialize the trading system
        supabase_manager = SupabaseManager()
        trader = TraderLowcapSimpleV2(supabase_manager=supabase_manager)
        
        if not trader.js_solana_client:
            print("❌ JS Solana client not available")
            return
        
        pump_contract = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
        sol_mint = "So11111111111111111111111111111111111111112"
        
        # Test with the production amount
        production_amount = 4422.691343  # The amount from production logs
        amount_raw = int(production_amount * 1_000_000)  # 6 decimals
        slippage_bps = 100  # 1% slippage
        
        print(f"🔄 Testing Jupiter swap: {pump_contract} -> {sol_mint}")
        print(f"   Amount: {production_amount} tokens")
        print(f"   Raw amount: {amount_raw} raw units")
        print(f"   Slippage: {slippage_bps} bps")
        
        result = await trader.js_solana_client.execute_jupiter_swap(
            input_mint=pump_contract,
            output_mint=sol_mint,
            amount=amount_raw,
            slippage_bps=slippage_bps
        )
        
        print(f"\n📋 Jupiter swap result: {result}")
        
        if result.get('success'):
            print("✅ Jupiter swap successful!")
            print(f"   Transaction hash: {result.get('signature')}")
            print(f"   Input amount: {result.get('inputAmount')}")
            print(f"   Output amount: {result.get('outputAmount')}")
        else:
            print(f"❌ Jupiter swap failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error during Jupiter test: {e}")
        logger.exception("Full error details:")

if __name__ == "__main__":
    print("🚀 Starting PUMP Large Amount Test")
    
    asyncio.run(test_pump_large_amount())
    asyncio.run(test_jupiter_direct_large())
    
    print("\n🏁 All tests completed. Check pump_large_amount_test.log for detailed logs.")
