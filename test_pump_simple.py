#!/usr/bin/env python3
"""
Simple PUMP sell test using existing system configuration
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
        logging.FileHandler('pump_sell_simple.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_pump_sell_with_system():
    """Test PUMP sell using the existing trading system"""
    
    print("🧪 Testing PUMP Sell with Existing System")
    print("=" * 50)
    
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
        
        # PUMP token details
        pump_contract = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
        pump_symbol = "PUMP"
        
        print(f"🎯 Testing token: {pump_symbol} ({pump_contract})")
        
        # Check if we have a PUMP position
        print("\n📊 Checking for PUMP positions...")
        
        # Get positions from database
        positions_result = supabase_manager.client.table('lowcap_positions').select('*').eq('contract', pump_contract).execute()
        
        if not positions_result.data:
            print("❌ No PUMP positions found in database")
            return
        
        print(f"📋 Found {len(positions_result.data)} PUMP positions:")
        for pos in positions_result.data:
            print(f"   - {pos.get('symbol')} | {pos.get('position_id')} | {pos.get('status')}")
        
        # Try to get current balance using the wallet manager
        print("\n💰 Checking current token balance...")
        
        # This will use the existing wallet manager from the trader
        if hasattr(trader, 'wallet_manager') and trader.wallet_manager:
            balance_result = await trader.wallet_manager.get_token_balance(pump_contract, 'solana')
            print(f"Balance result: {balance_result}")
        else:
            print("❌ Wallet manager not available")
            return
        
        # Try a manual sell using the Solana executor
        print("\n🔄 Attempting manual sell...")
        
        if hasattr(trader, 'solana_executor') and trader.solana_executor:
            # Test with a small amount
            test_amount = 1.0  # 1 token
            target_price = 0.00002  # Example target price
            
            print(f"   Amount: {test_amount} {pump_symbol}")
            print(f"   Target price: {target_price} SOL")
            
            result = await trader.solana_executor.execute_sell(
                token_mint=pump_contract,
                tokens_to_sell=test_amount,
                target_price_sol=target_price
            )
            
            print(f"\n📋 Sell result: {result}")
            
            if result:
                print("✅ Sell successful!")
            else:
                print("❌ Sell failed")
        else:
            print("❌ Solana executor not available")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        logger.exception("Full error details:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting PUMP Sell Test with Existing System")
    
    asyncio.run(test_pump_sell_with_system())
    
    print("\n🏁 Test completed. Check pump_sell_simple.log for detailed logs.")
