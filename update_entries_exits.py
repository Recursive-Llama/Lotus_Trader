#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio
from datetime import datetime, timezone

async def update_entries_exits():
    supabase = SupabaseManager()
    
    print('=== UPDATING ENTRIES, EXITS, AND EXIT_RULES ===')
    print()
    
    # Exit strategy from config
    exit_strategy = {
        'stages': [
            {'exit_pct': 100.0, 'gain_pct': 1590.0},  # Final exit
            {'exit_pct': 30.0, 'gain_pct': 38.2},
            {'exit_pct': 30.0, 'gain_pct': 61.8},
            {'exit_pct': 30.0, 'gain_pct': 161.8},
            {'exit_pct': 30.0, 'gain_pct': 261.8},
            {'exit_pct': 30.0, 'gain_pct': 361.8},
            {'exit_pct': 30.0, 'gain_pct': 561.8},
            {'exit_pct': 30.0, 'gain_pct': 761.8},
            {'exit_pct': 30.0, 'gain_pct': 1061.8}
        ]
    }
    
    # Positions that need updates (with their additional purchase data)
    positions_to_update = {
        'FACY': {
            'additional_tokens': 1545.4879598671212,
            'additional_investment': 0.01914860,
            'new_avg_price': 0.00001239
        },
        'ZFI': {
            'additional_tokens': 2546.31051282344,
            'additional_investment': 0.01409637,
            'new_avg_price': 0.00000616
        },
        'DLMM': {
            'additional_tokens': 84701.4399454052,
            'additional_investment': 0.33592591,
            'new_avg_price': 0.00000330
        },
        'HYDX': {
            'additional_tokens': 68.18792567686799,
            'additional_investment': 0.01358303,
            'new_avg_price': 0.00012785
        },
        'URA': {
            'additional_tokens': 10182.910395070303,
            'additional_investment': 0.13278515,
            'new_avg_price': 0.00001628
        },
        'PRDN': {
            'additional_tokens': 113621.0238149514,
            'additional_investment': 0.34961189,
            'new_avg_price': 0.00000306
        },
        'ANYONE': {
            'additional_tokens': 82.29592327533541,
            'additional_investment': 0.01080545,
            'new_avg_price': 0.00011680
        },
        'RAIN': {
            'additional_tokens': 6201.65430573706,
            'additional_investment': 0.20645307,
            'new_avg_price': 0.00003282
        },
        'WAGER': {
            'additional_tokens': 111961.7780657278,
            'additional_investment': 0.32592074,
            'new_avg_price': 0.00000291
        },
        'PPW': {
            'additional_tokens': 21596.0292121941,
            'additional_investment': 0.13555828,
            'new_avg_price': 0.00000746
        },
        'RETAKE': {
            'additional_tokens': 573487.0486753411,
            'additional_investment': 0.00617072,
            'new_avg_price': 0.00000001
        },
        'SERV': {
            'additional_tokens': 1161.417512020329,
            'additional_investment': 0.00789764,
            'new_avg_price': 0.00000555
        },
        'META': {
            'additional_tokens': 7.161283609234885,
            'additional_investment': 0.20414027,
            'new_avg_price': 0.02750552
        },
        'neet': {
            'additional_tokens': 1202.7556920420939,
            'additional_investment': 0.14036159,
            'new_avg_price': 0.00008288
        },
        'USELESS': {
            'additional_tokens': 95.9167251867816,
            'additional_investment': 0.12066324,
            'new_avg_price': 0.00125800
        },
        'ZC': {
            'additional_tokens': 9922.453883118003,
            'additional_investment': 0.04048361,
            'new_avg_price': 0.00000426
        },
        'BETLY': {
            'additional_tokens': 129296.6529900483,
            'additional_investment': 0.09551144,
            'new_avg_price': 0.00000082
        },
        'ICM.RUN': {
            'additional_tokens': 1822.62847215897,
            'additional_investment': 0.13833750,
            'new_avg_price': 0.00007768
        }
    }
    
    # Start with FACY as test case
    ticker = 'FACY'
    print(f'=== UPDATING {ticker} ===')
    
    # Get position
    result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', ticker).eq('status', 'active').execute()
    
    if result.data:
        pos = result.data[0]
        position_id = pos.get('id')
        
        # Get current data
        current_entries = pos.get('entries', [])
        current_exits = pos.get('exits', [])
        current_exit_rules = pos.get('exit_rules', {})
        
        print(f'Current entries: {len(current_entries)}')
        print(f'Current exits: {len(current_exits)}')
        print(f'Exit rules populated: {bool(current_exit_rules)}')
        
        # Get position data
        pos_data = positions_to_update[ticker]
        additional_tokens = pos_data['additional_tokens']
        additional_investment = pos_data['additional_investment']
        new_avg_price = pos_data['new_avg_price']
        
        # Create new entry record
        now = datetime.now(timezone.utc).isoformat()
        next_entry_number = len(current_entries) + 1
        
        new_entry = {
            'entry_number': next_entry_number,
            'price': new_avg_price,
            'amount_native': additional_investment,
            'tokens_bought': additional_tokens,
            'entry_type': 'additional_purchase',
            'status': 'executed',
            'unit': 'NATIVE',
            'native_symbol': 'SOL',
            'cost_native': additional_investment,
            'cost_usd': None,
            'tx_hash': 'manual_correction',
            'created_at': now,
            'executed_at': now
        }
        
        # Add to entries
        updated_entries = current_entries + [new_entry]
        
        # Create new exit records with updated prices
        updated_exits = []
        for i, stage in enumerate(exit_strategy['stages'], 1):
            gain_pct = stage['gain_pct']
            exit_pct = stage['exit_pct']
            exit_price = new_avg_price * (1 + gain_pct / 100)
            
            new_exit = {
                'exit_number': i,
                'price': exit_price,
                'exit_pct': exit_pct,
                'gain_pct': gain_pct,
                'status': 'pending',
                'created_at': now
            }
            updated_exits.append(new_exit)
        
        print(f'New entry: {new_entry}')
        print(f'New exit prices: {[exit["price"] for exit in updated_exits[:3]]}...')
        
        # Update database
        update_result = supabase.client.table('lowcap_positions').update({
            'entries': updated_entries,
            'exits': updated_exits,
            'exit_rules': exit_strategy
        }).eq('id', position_id).execute()
        
        if update_result.data:
            print(f'✅ {ticker} updated successfully!')
        else:
            print(f'❌ Failed to update {ticker}')
    else:
        print(f'❌ {ticker} position not found')

if __name__ == "__main__":
    asyncio.run(update_entries_exits())
