#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio

async def update_batch_2():
    supabase = SupabaseManager()
    
    print('=== UPDATING BATCH 2 - ANYONE, RAIN, WAGER ===')
    print()
    
    # Update ANYONE with corrected price
    print('--- ANYONE ---')
    anyone_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'ANYONE').eq('status', 'active').execute()
    
    if anyone_result.data:
        anyone = anyone_result.data[0]
        anyone_id = anyone.get('id')
        
        # Corrected values for ANYONE
        anyone_qty = 131.88236
        anyone_price = 0.00011680  # As corrected by user
        anyone_investment = anyone_qty * anyone_price
        
        print(f'Updating ANYONE:')
        print(f'  total_quantity: {anyone_qty} tokens')
        print(f'  total_tokens_bought: {anyone_qty} tokens')
        print(f'  avg_entry_price: {anyone_price:.8f} native')
        print(f'  total_investment_native: {anyone_investment:.8f} native')
        
        anyone_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': anyone_qty,
            'total_tokens_bought': anyone_qty,
            'avg_entry_price': anyone_price,
            'total_investment_native': anyone_investment
        }).eq('id', anyone_id).execute()
        
        if anyone_update.data:
            print('✅ ANYONE updated successfully!')
        else:
            print('❌ Failed to update ANYONE')
        print()
    
    # Update RAIN with calculated values
    print('--- RAIN ---')
    rain_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'RAIN').eq('status', 'active').execute()
    
    if rain_result.data:
        rain = rain_result.data[0]
        rain_id = rain.get('id')
        
        # Calculated values for RAIN
        rain_qty = 9799.90862
        rain_price = 0.00003282
        rain_investment = rain_qty * rain_price
        
        print(f'Updating RAIN:')
        print(f'  total_quantity: {rain_qty} tokens')
        print(f'  total_tokens_bought: {rain_qty} tokens')
        print(f'  avg_entry_price: {rain_price:.8f} native')
        print(f'  total_investment_native: {rain_investment:.8f} native')
        
        rain_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': rain_qty,
            'total_tokens_bought': rain_qty,
            'avg_entry_price': rain_price,
            'total_investment_native': rain_investment
        }).eq('id', rain_id).execute()
        
        if rain_update.data:
            print('✅ RAIN updated successfully!')
        else:
            print('❌ Failed to update RAIN')
        print()
    
    # Update WAGER with calculated values
    print('--- WAGER ---')
    wager_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'WAGER').eq('status', 'active').execute()
    
    if wager_result.data:
        wager = wager_result.data[0]
        wager_id = wager.get('id')
        
        # Calculated values for WAGER
        wager_qty = 112050
        wager_price = 0.00000291
        wager_investment = wager_qty * wager_price
        
        print(f'Updating WAGER:')
        print(f'  total_quantity: {wager_qty} tokens')
        print(f'  total_tokens_bought: {wager_qty} tokens')
        print(f'  avg_entry_price: {wager_price:.8f} native')
        print(f'  total_investment_native: {wager_investment:.8f} native')
        
        wager_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': wager_qty,
            'total_tokens_bought': wager_qty,
            'avg_entry_price': wager_price,
            'total_investment_native': wager_investment
        }).eq('id', wager_id).execute()
        
        if wager_update.data:
            print('✅ WAGER updated successfully!')
        else:
            print('❌ Failed to update WAGER')
        print()

if __name__ == "__main__":
    asyncio.run(update_batch_2())
