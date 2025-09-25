#!/usr/bin/env python3
"""Test BSC trading with V2 trader"""

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

async def test_bsc_trading():
    """Test BSC trading with V2 trader"""
    print('Testing BSC trading with V2 trader...')

    try:
        # Set up the V2 trader
        supabase_manager = SupabaseManager()
        trader = TraderLowcapSimpleV2(supabase_manager)
        
        test_token = '0xb5761f36FdFE2892f1b54Bc8EE8baBb2a1b698D3'  # The failing token
        
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
        
        # Debug: Check trader components
        print(f'BSC client available: {trader.bsc_client is not None}')
        print(f'BSC executor available: {trader.bsc_executor is not None}')
        print(f'Price oracle available: {trader.price_oracle is not None}')
        
        # Test price oracle
        price_info = trader.price_oracle.price_bsc(test_token)
        if price_info:
            print(f'Price: {price_info["price_native"]} BNB per token')
            print(f'USD Price: ${price_info["price_usd"]} USD per token')
        else:
            print('Price: None')
        
        # Test wallet balance
        balance = await trader.wallet_manager.get_balance('bsc')
        print(f'BSC balance: {balance}')
        
        # Test venue resolution
        venue = trader._resolve_bsc_venue(test_token)
        print(f'Venue: {venue}')
        
        # Debug the decision structure
        print(f'Decision structure: {decision}')
        
        # Check if the decision has the right structure
        content = decision.get('content', {})
        print(f'Content: {content}')
        print(f'Action: {content.get("action")}')
        print(f'Token: {content.get("token")}')
        
        # The decision needs a 'signal_pack' field with 'token' inside
        decision_fixed = {
            'content': {
                'action': 'approve',
                'allocation_pct': 0.005  # 0.005 BNB test
            },
            'signal_pack': {
                'token': {
                    'chain': 'bsc',
                    'contract': test_token,
                    'ticker': 'TEST'
                }
            }
        }
        
        print(f'Fixed decision: {decision_fixed}')
        
        # Check current nonce
        if trader.bsc_client:
            current_nonce = trader.bsc_client.w3.eth.get_transaction_count(trader.bsc_client.account.address)
            print(f'Current nonce: {current_nonce}')
            
            # Wait a bit for any pending transactions to be confirmed
            print('Waiting for pending transactions to be confirmed...')
            await asyncio.sleep(15)
            
            new_nonce = trader.bsc_client.w3.eth.get_transaction_count(trader.bsc_client.account.address)
            print(f'New nonce: {new_nonce}')
        
        try:
            buy_result = await trader.execute_decision(decision_fixed)
            print(f'Buy result: {buy_result}')
        except Exception as e:
            print(f'Exception in execute_decision: {e}')
            import traceback
            traceback.print_exc()
        
        if buy_result and buy_result.get('position_id'):
            position_id = buy_result['position_id']
            print(f'✅ BSC buy successful! Position ID: {position_id}')
            
            # Check the position
            position = trader.repo.get_position(position_id)
            if position:
                print(f'Position total_quantity: {position.get("total_quantity", 0)}')
                print(f'Position entries: {len(position.get("entries", []))}')
                
                # Test wallet balance check
                print('\nTesting wallet balance check...')
                wallet_balance = await trader.wallet_manager.get_balance('bsc', test_token)
                print(f'Wallet balance: {wallet_balance}')
                
                # Test sell
                print('\nTesting BSC sell...')
                sell_result = await trader._execute_exit(position_id, 1)
                print(f'Sell result: {sell_result}')
                
                if sell_result:
                    print('✅ BSC sell successful!')
                else:
                    print('❌ BSC sell failed')
            else:
                print('❌ Could not get position')
        else:
            print('❌ BSC buy failed')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bsc_trading())

