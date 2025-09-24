#!/usr/bin/env python3
"""Test total_quantity fix with wallet balance"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

bsc_pk = os.getenv('BSC_WALLET_PRIVATE_KEY')
os.environ['BSC_WALLET_PRIVATE_KEY'] = bsc_pk

import sys
sys.path.append('src')

from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
from utils.supabase_manager import SupabaseManager

async def test_total_quantity_fix():
    """Test that total_quantity uses wallet balance"""
    print('Testing total_quantity fix...')

    try:
        # Set up the V2 trader
        supabase_manager = SupabaseManager()
        trader = TraderLowcapSimpleV2(supabase_manager)
        
        test_token = '0x8dEdf84656fa932157e27C060D8613824e7979e3'
        
        # Test buy
        print('Testing BSC buy...')
        decision = {
            'content': {
                'action': 'approve',
                'token_contract': test_token,
                'token_chain': 'bsc',
                'token_ticker': 'TEST',
                'token_name': 'Test Token',
                'allocation_pct': 0.1
            }
        }
        
        buy_result = await trader.execute_decision(decision)
        print(f'Buy result: {buy_result}')
        
        if buy_result and buy_result.get('position_id'):
            position_id = buy_result['position_id']
            print(f'✅ BSC buy successful! Position ID: {position_id}')
            
            # Check the position
            position = trader.repo.get_position(position_id)
            if position:
                print(f'\\nPosition details:')
                print(f'  Database total_quantity: {position.get("total_quantity", 0)}')
                print(f'  Position entries: {len(position.get("entries", []))}')
                
                # Check wallet balance
                print(f'\\nWallet balance check:')
                wallet_balance = await trader.wallet_manager.get_balance('bsc', test_token)
                print(f'  Wallet balance: {wallet_balance}')
                
                # Test the recalculation method
                print(f'\\nTesting _recalculate_position_totals:')
                await trader._recalculate_position_totals(position)
                print(f'  After recalculation total_quantity: {position.get("total_quantity", 0)}')
                
                # Update the position in database
                trader.repo.update_position(position_id, position)
                print(f'  Updated position in database')
                
                # Check if they match now
                if abs(float(wallet_balance) - position.get('total_quantity', 0)) < 0.000001:
                    print(f'✅ total_quantity now matches wallet balance!')
                else:
                    print(f'❌ total_quantity still doesn\'t match wallet balance')
                    print(f'  Wallet: {wallet_balance}')
                    print(f'  Database: {position.get("total_quantity", 0)}')
            else:
                print('❌ Could not get position')
        else:
            print('❌ BSC buy failed')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_total_quantity_fix())
