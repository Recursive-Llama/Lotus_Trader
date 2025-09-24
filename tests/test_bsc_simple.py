#!/usr/bin/env python3
"""Simple BSC test"""

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
from utils.supabase_manager import SupabaseManager

async def test_bsc_simple():
    """Simple BSC test"""
    print('Testing BSC with simple test...')

    try:
        # Set up the position repository
        supabase_manager = SupabaseManager()
        position_repo = PositionRepository(supabase_manager)
        
        # Set up the BSC executor
        bsc_rpc = os.getenv('BSC_RPC_URL', 'https://bsc-dataseed.binance.org')
        bsc_client = EvmUniswapClient(chain='bsc', rpc_url=bsc_rpc, private_key=bsc_pk)
        bsc_executor = BscExecutor(bsc_client, position_repo)
        
        test_token = '0x8dEdf84656fa932157e27C060D8613824e7979e3'
        print(f'Using token: {test_token}')
        
        # Test buy
        print('Testing BSC buy...')
        buy_result = bsc_executor.execute_buy(test_token, 0.001)  # 0.001 BNB
        print(f'Buy result: {buy_result}')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bsc_simple())
