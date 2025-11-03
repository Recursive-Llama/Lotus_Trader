#!/usr/bin/env python3
"""
Test PUMP sell using real system configuration
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
from src.trading.wallet_manager import WalletManager

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pump_real_config_test.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_pump_with_real_system():
    """Test PUMP sell using the real trading system configuration"""
    
    print("🧪 Testing PUMP Sell with Real System Configuration")
    print("=" * 60)
    
    try:
        # Initialize components
        print("🔧 Initializing system components...")
        supabase_manager = SupabaseManager()
        
        # Initialize wallet manager
        wallet_manager = WalletManager()
        
        print("✅ Components initialized")
        
        # PUMP token details
        pump_contract = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
        pump_symbol = "PUMP"
        
        print(f"🎯 Testing token: {pump_symbol} ({pump_contract})")
        
        # Check current balance
        print("\n💰 Checking current token balance...")
        balance_result = await wallet_manager.get_token_balance(pump_contract, 'solana')
        print(f"Balance result: {balance_result}")
        
        if not balance_result.get('success'):
            print(f"❌ Failed to get balance: {balance_result.get('error')}")
            return
        
        current_balance = float(balance_result.get('balance', 0))
        print(f"💰 Current balance: {current_balance} {pump_symbol}")
        
        if current_balance <= 0:
            print("❌ No tokens to sell")
            return
        
        # Test with a very small amount
        test_amount = min(current_balance * 0.001, 1.0)  # 0.1% or max 1 token
        target_price_sol = 0.00002  # Example target price
        
        print(f"\n🔄 Testing sell with small amount:")
        print(f"   Amount: {test_amount} {pump_symbol}")
        print(f"   Target price: {target_price_sol} SOL")
        
        # Get the Solana executor from wallet manager
        if hasattr(wallet_manager, 'js_solana_client') and wallet_manager.js_solana_client:
            print("\n🔧 Using JS Solana client for direct test...")
            
            # Test Jupiter swap directly
            amount_raw = int(test_amount * 1_000_000)  # 6 decimals for PUMP
            slippage_bps = 100  # 1% slippage
            
            print(f"   Raw amount: {amount_raw}")
            print(f"   Slippage: {slippage_bps} bps")
            
            result = await wallet_manager.js_solana_client.execute_jupiter_swap(
                input_mint=pump_contract,
                output_mint="So11111111111111111111111111111111111111112",  # SOL
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
                
                # Try with higher slippage
                print("\n🔄 Retrying with higher slippage (500 bps)...")
                result2 = await wallet_manager.js_solana_client.execute_jupiter_swap(
                    input_mint=pump_contract,
                    output_mint="So11111111111111111111111111111111111111112",
                    amount=amount_raw,
                    slippage_bps=500  # 5% slippage
                )
                
                print(f"📋 Retry result: {result2}")
                
                if result2.get('success'):
                    print("✅ Retry successful!")
                else:
                    print(f"❌ Retry also failed: {result2.get('error')}")
        else:
            print("❌ JS Solana client not available")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        logger.exception("Full error details:")
        import traceback
        traceback.print_exc()

async def test_different_amounts():
    """Test with different amounts to see if there's a threshold issue"""
    
    print("\n" + "=" * 60)
    print("🔬 Testing Different Amounts")
    print("=" * 60)
    
    try:
        wallet_manager = WalletManager()
        
        pump_contract = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
        
        # Test different amounts
        test_amounts = [0.001, 0.01, 0.1, 1.0, 10.0]  # Different token amounts
        
        for amount in test_amounts:
            print(f"\n🔄 Testing amount: {amount} tokens")
            
            amount_raw = int(amount * 1_000_000)  # 6 decimals
            
            result = await wallet_manager.js_solana_client.execute_jupiter_swap(
                input_mint=pump_contract,
                output_mint="So11111111111111111111111111111111111111112",
                amount=amount_raw,
                slippage_bps=100
            )
            
            if result.get('success'):
                print(f"   ✅ Success: {result.get('signature')}")
            else:
                print(f"   ❌ Failed: {result.get('error')}")
                
    except Exception as e:
        print(f"❌ Error testing amounts: {e}")

if __name__ == "__main__":
    print("🚀 Starting PUMP Test with Real Configuration")
    
    asyncio.run(test_pump_with_real_system())
    asyncio.run(test_different_amounts())
    
    print("\n🏁 All tests completed. Check pump_real_config_test.log for detailed logs.")
