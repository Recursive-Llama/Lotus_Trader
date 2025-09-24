#!/usr/bin/env python3
"""
Test tax detection by doing a real buy of the tax token 0x696025Fab2f3E2ADE78E57A3f553e993D2996615
"""

import asyncio
import os
import sys
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
from intelligence.trader_lowcap.evm_executors import EthExecutor
from trading.evm_uniswap_client_eth import EthUniswapClient
from utils.supabase_manager import SupabaseManager

async def test_tax_detection_with_buy():
    """Test tax detection by doing a real buy of the tax token"""
    try:
        print("🔍 Testing tax detection with real buy...")
        print("=" * 60)
        
        # Initialize components
        supabase_manager = SupabaseManager()
        trader = TraderLowcapSimpleV2(supabase_manager)
        
        # Initialize Ethereum client and executor
        eth_rpc_url = os.getenv('ETH_RPC_URL', 'https://eth.llamarpc.com')
        eth_private_key = os.getenv('ETHEREUM_WALLET_PRIVATE_KEY')
        
        if not eth_private_key:
            print("❌ No ETHEREUM_WALLET_PRIVATE_KEY found in environment")
            return
        
        eth_client = EthUniswapClient(rpc_url=eth_rpc_url, private_key=eth_private_key)
        eth_executor = EthExecutor(eth_client)
        
        print("✅ All components initialized")
        
        # Test token (the tax token)
        test_token = '0x696025Fab2f3E2ADE78E57A3f553e993D2996615'
        test_chain = 'ethereum'
        test_amount = 0.00001  # Very small amount for testing
        
        # Check current balance before buy
        print(f"\n💰 Checking balance before buy...")
        balance_before = await trader.wallet_manager.get_balance(test_chain, test_token)
        print(f"Balance before: {balance_before} tokens")
        
        # Check ETH balance
        eth_balance = eth_client.w3.eth.get_balance(eth_client.account.address)
        eth_balance_eth = eth_balance / 1e18
        print(f"ETH balance: {eth_balance_eth:.6f} ETH")
        
        if eth_balance_eth < test_amount + 0.005:  # Need extra for gas
            print(f"⚠️  Insufficient ETH balance for test (need ~{test_amount + 0.005:.6f} ETH)")
            return
        
        # Get current price
        price = trader.price_oracle.price_eth(test_token)
        if not price:
            print(f"❌ Could not get price for token")
            return
        
        print(f"Current price: {price} ETH per token")
        expected_tokens = test_amount / price
        print(f"Expected tokens: {expected_tokens}")
        
        # Execute the buy
        print(f"\n🚀 Executing buy...")
        print("-" * 40)
        tx_hash = eth_executor.execute_buy(test_token, test_amount)
        print("-" * 40)
        
        if tx_hash:
            print(f"✅ Buy successful: {tx_hash}")
            
            # Now test the tax detection
            print(f"\n🔍 Testing tax detection after buy...")
            await trader._detect_and_update_tax_token(test_token, test_amount, price, test_chain)
            
            # Check balance after buy
            print(f"\n💰 Checking balance after buy...")
            balance_after = await trader.wallet_manager.get_balance(test_chain, test_token)
            print(f"Balance after: {balance_after} tokens")
            
            # Calculate actual tokens received
            if balance_before is not None and balance_after is not None:
                actual_tokens_received = float(balance_after) - float(balance_before)
                print(f"Actual tokens received: {actual_tokens_received}")
                print(f"Expected tokens: {expected_tokens}")
                
                # Calculate tax percentage
                if expected_tokens > 0:
                    tax_pct = ((expected_tokens - actual_tokens_received) / expected_tokens) * 100
                    print(f"Tax percentage: {tax_pct:.2f}%")
                    
                    if tax_pct > 1.0:
                        print(f"✅ Tax detected: {tax_pct:.2f}%")
                    else:
                        print(f"✅ No significant tax detected")
            
            # Check database
            print(f"\n🔍 Checking database...")
            position = trader.repo.get_position_by_token(test_token)
            if position and 'tax_pct' in position:
                db_tax_pct = position['tax_pct']
                print(f"Database tax_pct: {db_tax_pct}%")
            
        else:
            print(f"❌ Buy failed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tax_detection_with_buy())
