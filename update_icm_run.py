#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio

async def update_icm_run():
    supabase = SupabaseManager()
    
    print('=== UPDATING ICM.RUN ===')
    print()
    
    # Get ICM.RUN position
    result = supabase.client.table('lowcap_positions').select('*').eq('token_contract', 'G5bStqnKXv11fmPvMaagUbZi86BGnpf9zZtyPQtAdaos').eq('status', 'active').execute()
    
    if result.data:
        icm = result.data[0]
        icm_id = icm.get('id')
        
        # Current values
        current_qty = float(icm.get('total_quantity', 0))
        current_bought = float(icm.get('total_tokens_bought', 0))
        current_price = float(icm.get('avg_entry_price', 0))
        
        # New values from portfolio
        new_qty = 3139.31858
        additional_qty = new_qty - current_bought
        
        print(f'Current ICM.RUN values:')
        print(f'  total_quantity: {current_qty} tokens')
        print(f'  total_tokens_bought: {current_bought} tokens')
        print(f'  avg_entry_price: {current_price:.8f} native')
        print()
        
        print(f'Portfolio shows: {new_qty} tokens')
        print(f'Additional to buy: {additional_qty} tokens')
        print()
        
        # Get current market price
        price_result = supabase.client.table('lowcap_price_data_1m').select('*').eq('token_contract', icm.get('token_contract')).order('timestamp', desc=True).limit(1).execute()
        
        if price_result.data:
            market_price = float(price_result.data[0].get('price_native', 0))
            market_price_usd = float(price_result.data[0].get('price_usd', 0))
            
            print(f'Current market price: {market_price:.8f} native (${market_price_usd:.4f} USD)')
            print()
            
            # Calculate weighted average
            existing_investment = current_bought * current_price
            additional_investment = additional_qty * market_price
            total_investment = existing_investment + additional_investment
            weighted_avg_price = total_investment / new_qty
            
            print(f'Weighted average calculation:')
            print(f'  Existing: {current_bought} × {current_price:.8f} = {existing_investment:.8f} native')
            print(f'  Additional: {additional_qty} × {market_price:.8f} = {additional_investment:.8f} native')
            print(f'  Total: {total_investment:.8f} native')
            print(f'  Weighted avg: {weighted_avg_price:.8f} native')
            print()
            
            print(f'Updating ICM.RUN with:')
            print(f'  total_quantity: {new_qty} tokens')
            print(f'  total_tokens_bought: {new_qty} tokens')
            print(f'  avg_entry_price: {weighted_avg_price:.8f} native')
            print(f'  total_investment_native: {total_investment:.8f} native')
            
            # Update the position
            update_result = supabase.client.table('lowcap_positions').update({
                'total_quantity': new_qty,
                'total_tokens_bought': new_qty,
                'avg_entry_price': weighted_avg_price,
                'total_investment_native': total_investment
            }).eq('id', icm_id).execute()
            
            if update_result.data:
                print('✅ ICM.RUN updated successfully!')
            else:
                print('❌ Failed to update ICM.RUN')
        else:
            print('❌ No current price data found for ICM.RUN')
    else:
        print('❌ ICM.RUN position not found')

if __name__ == "__main__":
    asyncio.run(update_icm_run())
