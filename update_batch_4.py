#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio

async def update_batch_4():
    supabase = SupabaseManager()
    
    print('=== UPDATING BATCH 4 - META, neet, USELESS, ZC, BETLY ===')
    print()
    
    # Update META with corrected values (decimal place fix)
    print('--- META ---')
    meta_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'META').eq('status', 'active').execute()
    
    if meta_result.data:
        meta = meta_result.data[0]
        meta_id = meta.get('id')
        
        # Corrected values for META (decimal place fix)
        meta_qty = 7.1653
        meta_price = 0.02750552  # Corrected from 28.50552
        meta_investment = meta_qty * meta_price
        
        print(f'Updating META:')
        print(f'  total_quantity: {meta_qty} tokens')
        print(f'  total_tokens_bought: {meta_qty} tokens')
        print(f'  avg_entry_price: {meta_price:.8f} native')
        print(f'  total_investment_native: {meta_investment:.8f} native')
        
        meta_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': meta_qty,
            'total_tokens_bought': meta_qty,
            'avg_entry_price': meta_price,
            'total_investment_native': meta_investment
        }).eq('id', meta_id).execute()
        
        if meta_update.data:
            print('✅ META updated successfully!')
        else:
            print('❌ Failed to update META')
        print()
    
    # Update neet with corrected price (all tokens at same price)
    print('--- neet ---')
    neet_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'neet').eq('status', 'active').execute()
    
    if neet_result.data:
        neet = neet_result.data[0]
        neet_id = neet.get('id')
        
        # Corrected values for neet (all tokens at same price)
        neet_qty = 1767.50255
        neet_price = 0.00008288  # All tokens at this price
        neet_investment = neet_qty * neet_price
        
        print(f'Updating neet:')
        print(f'  total_quantity: {neet_qty} tokens')
        print(f'  total_tokens_bought: {neet_qty} tokens')
        print(f'  avg_entry_price: {neet_price:.8f} native')
        print(f'  total_investment_native: {neet_investment:.8f} native')
        
        neet_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': neet_qty,
            'total_tokens_bought': neet_qty,
            'avg_entry_price': neet_price,
            'total_investment_native': neet_investment
        }).eq('id', neet_id).execute()
        
        if neet_update.data:
            print('✅ neet updated successfully!')
        else:
            print('❌ Failed to update neet')
        print()
    
    # Update USELESS with corrected price (all tokens at same price)
    print('--- USELESS ---')
    useless_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'USELESS').eq('status', 'active').execute()
    
    if useless_result.data:
        useless = useless_result.data[0]
        useless_id = useless.get('id')
        
        # Corrected values for USELESS (all tokens at same price)
        useless_qty = 151.90402
        useless_price = 0.00125800  # All tokens at this price
        useless_investment = useless_qty * useless_price
        
        print(f'Updating USELESS:')
        print(f'  total_quantity: {useless_qty} tokens')
        print(f'  total_tokens_bought: {useless_qty} tokens')
        print(f'  avg_entry_price: {useless_price:.8f} native')
        print(f'  total_investment_native: {useless_investment:.8f} native')
        
        useless_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': useless_qty,
            'total_tokens_bought': useless_qty,
            'avg_entry_price': useless_price,
            'total_investment_native': useless_investment
        }).eq('id', useless_id).execute()
        
        if useless_update.data:
            print('✅ USELESS updated successfully!')
        else:
            print('❌ Failed to update USELESS')
        print()
    
    # Update ZC with calculated values
    print('--- ZC ---')
    zc_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'ZC').eq('status', 'active').execute()
    
    if zc_result.data:
        zc = zc_result.data[0]
        zc_id = zc.get('id')
        
        # Calculated values for ZC
        zc_qty = 41821.99532
        zc_price = 0.00000426
        zc_investment = zc_qty * zc_price
        
        print(f'Updating ZC:')
        print(f'  total_quantity: {zc_qty} tokens')
        print(f'  total_tokens_bought: {zc_qty} tokens')
        print(f'  avg_entry_price: {zc_price:.8f} native')
        print(f'  total_investment_native: {zc_investment:.8f} native')
        
        zc_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': zc_qty,
            'total_tokens_bought': zc_qty,
            'avg_entry_price': zc_price,
            'total_investment_native': zc_investment
        }).eq('id', zc_id).execute()
        
        if zc_update.data:
            print('✅ ZC updated successfully!')
        else:
            print('❌ Failed to update ZC')
        print()
    
    # Update BETLY with calculated values
    print('--- BETLY ---')
    betly_result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'BETLY').eq('status', 'active').execute()
    
    if betly_result.data:
        betly = betly_result.data[0]
        betly_id = betly.get('id')
        
        # Calculated values for BETLY
        betly_qty = 179790
        betly_price = 0.00000082
        betly_investment = betly_qty * betly_price
        
        print(f'Updating BETLY:')
        print(f'  total_quantity: {betly_qty} tokens')
        print(f'  total_tokens_bought: {betly_qty} tokens')
        print(f'  avg_entry_price: {betly_price:.8f} native')
        print(f'  total_investment_native: {betly_investment:.8f} native')
        
        betly_update = supabase.client.table('lowcap_positions').update({
            'total_quantity': betly_qty,
            'total_tokens_bought': betly_qty,
            'avg_entry_price': betly_price,
            'total_investment_native': betly_investment
        }).eq('id', betly_id).execute()
        
        if betly_update.data:
            print('✅ BETLY updated successfully!')
        else:
            print('❌ Failed to update BETLY')
        print()

if __name__ == "__main__":
    asyncio.run(update_batch_4())
