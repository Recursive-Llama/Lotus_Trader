#!/usr/bin/env python3
"""Test BSC trading with wallet balance check"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

bsc_pk = os.getenv('BSC_WALLET_PRIVATE_KEY')
os.environ['BSC_WALLET_PRIVATE_KEY'] = bsc_pk

import sys
sys.path.append('src')

from intelligence.trader_lowcap.evm_executors import BscExecutor
from intelligence.trader_lowcap.position_repository import PositionRepository
from trading.evm_uniswap_client import EvmUniswapClient
from trading.wallet_manager import WalletManager
from utils.supabase_manager import SupabaseManager

async def test_bsc_balance():
    """Test BSC trading with wallet balance check"""
    print('Testing BSC trading with wallet balance check...')

    try:
        # Set up the position repository
        supabase_manager = SupabaseManager()
        position_repo = PositionRepository(supabase_manager)
        
        # Set up the BSC executor
        bsc_rpc = os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org')
        bsc_client = EvmUniswapClient(chain='bsc', rpc_url=bsc_rpc, private_key=bsc_pk)
        bsc_executor = BscExecutor(bsc_client, position_repo)
        
        # Set up wallet manager
        wallet_manager = WalletManager()
        
        test_token = '0x8dEdf84656fa932157e27C060D8613824e7979e3'
        
        # Test buy
        print('Testing BSC buy...')
        buy_result = bsc_executor.execute_buy(test_token, 0.001)  # 0.001 BNB
        print(f'Buy result: {buy_result}')
        
        if buy_result:
            print('✅ BSC buy successful!')
            
            # Check wallet balance using wallet manager
            print('\nChecking wallet balance...')
            balance = await wallet_manager.get_balance('bsc', test_token)
            print(f'Token balance: {balance}')
            
            # Test sell
            print('\nTesting BSC sell...')
            sell_result = bsc_executor.execute_sell(test_token, 100.0, 0.00001)  # 100 tokens, target price 0.00001 BNB
            print(f'Sell result: {sell_result}')
            
            if sell_result:
                print('✅ BSC sell successful!')
            else:
                print('❌ BSC sell failed')
        else:
            print('❌ BSC buy failed')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bsc_balance())

