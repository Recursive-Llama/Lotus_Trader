#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio

async def calculate_facy_weighted_average():
    supabase = SupabaseManager()
    
    print('=== FACY WEIGHTED AVERAGE CALCULATION ===')
    print()
    
    # Get FACY position
    result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'FACY').eq('status', 'active').execute()
    
    if result.data:
        facy = result.data[0]
        
        # From chat history
        original_qty = 657.752620132879
        new_qty = 2203.24058
        additional_qty = new_qty - original_qty
        original_price = 0.000004939  # From database
        
        print('FACY Calculation:')
        print(f'  Original: {original_qty} tokens @ {original_price:.8f} native')
        print(f'  Additional: {additional_qty} tokens @ current market price')
        print(f'  New total: {new_qty} tokens')
        print()
        
        # Get current price from database
        price_result = supabase.client.table('lowcap_price_data_1m').select('*').eq('token_contract', facy.get('token_contract')).order('timestamp', desc=True).limit(1).execute()
        
        if price_result.data:
            current_price = float(price_result.data[0].get('price_native', 0))
            current_price_usd = float(price_result.data[0].get('price_usd', 0))
            
            print(f'Current Market Price: {current_price:.8f} native (${current_price_usd:.4f} USD)')
            print()
            
            # Calculate investments
            original_investment = original_qty * original_price
            additional_investment = additional_qty * current_price
            total_investment = original_investment + additional_investment
            
            print('Investment Calculation:')
            print(f'  Original: {original_qty} × {original_price:.8f} = {original_investment:.8f} native')
            print(f'  Additional: {additional_qty} × {current_price:.8f} = {additional_investment:.8f} native')
            print(f'  Total: {total_investment:.8f} native')
            print()
            
            # Calculate weighted average
            weighted_avg_price = total_investment / new_qty
            
            print('Weighted Average:')
            print(f'  {total_investment:.8f} ÷ {new_qty} = {weighted_avg_price:.8f} native')
            print()
            
            print('Current vs Calculated:')
            print(f'  Current Entry Price: {facy.get("avg_entry_price")} native')
            print(f'  Calculated Entry Price: {weighted_avg_price:.8f} native')
            print(f'  Difference: {abs(float(facy.get("avg_entry_price", 0)) - weighted_avg_price):.8f} native')
            print()
            
            print('Does this look correct?')
            print(f'  We bought {additional_qty} more tokens at {current_price:.8f} native')
            print(f'  So the average entry price should be {weighted_avg_price:.8f} native')
            
        else:
            print('❌ No current price data found for FACY')
    else:
        print('❌ FACY position not found')

if __name__ == "__main__":
    asyncio.run(calculate_facy_weighted_average())
