#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio

async def update_batch_1():
    supabase = SupabaseManager()
    
    print('=== UPDATING BATCH 1 - HYDX, URA, PRDN ===')
    print()
    
    # Update HYDX with corrected values
    print('--- HYDX ---')
    hydx_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'HYDX').eq('status', 'active').execute()
    
    if hydx_result.data:
        hydx = hydx_result.data[0]
        hydx_id = hydx.get('id')
        
        # Corrected values for HYDX
        hydx_qty = 87.60162
        hydx_investment = 0.0112  # As corrected by user
        hydx_price = hydx_investment / hydx_qty
        
        print(f'Updating HYDX:')
        print(f'  total_quantity: {hydx_qty} tokens')
        print(f'  total_tokens_bought: {hydx_qty} tokens')
        print(f'  avg_entry_price: {hydx_price:.8f} native')
        print(f'  total_investment_native: {hydx_investment} native')
        
        hydx_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': hydx_qty,
            'total_tokens_bought': hydx_qty,
            'avg_entry_price': hydx_price,
            'total_investment_native': hydx_investment
        }).eq('id', hydx_id).execute()
        
        if hydx_update.data:
            print('✅ HYDX updated successfully!')
        else:
            print('❌ Failed to update HYDX')
        print()
    
    # Update URA with calculated values
    print('--- URA ---')
    ura_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'URA').eq('status', 'active').execute()
    
    if ura_result.data:
        ura = ura_result.data[0]
        ura_id = ura.get('id')
        
        # Calculated values for URA
        ura_qty = 26811.98656
        ura_price = 0.00001628
        ura_investment = ura_qty * ura_price
        
        print(f'Updating URA:')
        print(f'  total_quantity: {ura_qty} tokens')
        print(f'  total_tokens_bought: {ura_qty} tokens')
        print(f'  avg_entry_price: {ura_price:.8f} native')
        print(f'  total_investment_native: {ura_investment:.8f} native')
        
        ura_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': ura_qty,
            'total_tokens_bought': ura_qty,
            'avg_entry_price': ura_price,
            'total_investment_native': ura_investment
        }).eq('id', ura_id).execute()
        
        if ura_update.data:
            print('✅ URA updated successfully!')
        else:
            print('❌ Failed to update URA')
        print()
    
    # Update PRDN with calculated values
    print('--- PRDN ---')
    prdn_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'PRDN').eq('status', 'active').execute()
    
    if prdn_result.data:
        prdn = prdn_result.data[0]
        prdn_id = prdn.get('id')
        
        # Calculated values for PRDN
        prdn_qty = 131780
        prdn_price = 0.00000306
        prdn_investment = prdn_qty * prdn_price
        
        print(f'Updating PRDN:')
        print(f'  total_quantity: {prdn_qty} tokens')
        print(f'  total_tokens_bought: {prdn_qty} tokens')
        print(f'  avg_entry_price: {prdn_price:.8f} native')
        print(f'  total_investment_native: {prdn_investment:.8f} native')
        
        prdn_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': prdn_qty,
            'total_tokens_bought': prdn_qty,
            'avg_entry_price': prdn_price,
            'total_investment_native': prdn_investment
        }).eq('id', prdn_id).execute()
        
        if prdn_update.data:
            print('✅ PRDN updated successfully!')
        else:
            print('❌ Failed to update PRDN')
        print()

if __name__ == "__main__":
    asyncio.run(update_batch_1())
