#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio

async def update_batch_3():
    supabase = SupabaseManager()
    
    print('=== UPDATING BATCH 3 - PPW, RETAKE, SERV ===')
    print()
    
    # Update PPW with calculated values
    print('--- PPW ---')
    ppw_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'PPW').eq('status', 'active').execute()
    
    if ppw_result.data:
        ppw = ppw_result.data[0]
        ppw_id = ppw.get('id')
        
        # Calculated values for PPW
        ppw_qty = 43570.92408
        ppw_price = 0.00000746
        ppw_investment = ppw_qty * ppw_price
        
        print(f'Updating PPW:')
        print(f'  total_quantity: {ppw_qty} tokens')
        print(f'  total_tokens_bought: {ppw_qty} tokens')
        print(f'  avg_entry_price: {ppw_price:.8f} native')
        print(f'  total_investment_native: {ppw_investment:.8f} native')
        
        ppw_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': ppw_qty,
            'total_tokens_bought': ppw_qty,
            'avg_entry_price': ppw_price,
            'total_investment_native': ppw_investment
        }).eq('id', ppw_id).execute()
        
        if ppw_update.data:
            print('✅ PPW updated successfully!')
        else:
            print('❌ Failed to update PPW')
        print()
    
    # Update RETAKE with calculated values
    print('--- RETAKE ---')
    retake_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'RETAKE').eq('status', 'active').execute()
    
    if retake_result.data:
        retake = retake_result.data[0]
        retake_id = retake.get('id')
        
        # Calculated values for RETAKE
        retake_qty = 1010000
        retake_price = 0.00000001
        retake_investment = retake_qty * retake_price
        
        print(f'Updating RETAKE:')
        print(f'  total_quantity: {retake_qty} tokens')
        print(f'  total_tokens_bought: {retake_qty} tokens')
        print(f'  avg_entry_price: {retake_price:.8f} native')
        print(f'  total_investment_native: {retake_investment:.8f} native')
        
        retake_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': retake_qty,
            'total_tokens_bought': retake_qty,
            'avg_entry_price': retake_price,
            'total_investment_native': retake_investment
        }).eq('id', retake_id).execute()
        
        if retake_update.data:
            print('✅ RETAKE updated successfully!')
        else:
            print('❌ Failed to update RETAKE')
        print()
    
    # Update SERV with corrected price
    print('--- SERV ---')
    serv_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'SERV').eq('status', 'active').execute()
    
    if serv_result.data:
        serv = serv_result.data[0]
        serv_id = serv.get('id')
        
        # Corrected values for SERV
        serv_qty = 1437.95335
        serv_price = 0.00000555  # As corrected by user
        serv_investment = serv_qty * serv_price
        
        print(f'Updating SERV:')
        print(f'  total_quantity: {serv_qty} tokens')
        print(f'  total_tokens_bought: {serv_qty} tokens')
        print(f'  avg_entry_price: {serv_price:.8f} native')
        print(f'  total_investment_native: {serv_investment:.8f} native')
        
        serv_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': serv_qty,
            'total_tokens_bought': serv_qty,
            'avg_entry_price': serv_price,
            'total_investment_native': serv_investment
        }).eq('id', serv_id).execute()
        
        if serv_update.data:
            print('✅ SERV updated successfully!')
        else:
            print('❌ Failed to update SERV')
        print()

if __name__ == "__main__":
    asyncio.run(update_batch_3())
