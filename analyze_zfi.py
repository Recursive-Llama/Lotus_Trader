#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio

async def analyze_zfi():
    supabase = SupabaseManager()
    
    print('=== ZFI ANALYSIS - NO CHANGES YET ===')
    print()
    
    # Get ZFI position
    result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'ZFI').eq('status', 'active').execute()
    
    if result.data:
        zfi = result.data[0]
        
        print('Current ZFI values in database:')
        print(f'  total_quantity: {zfi.get("total_quantity")} tokens')
        print(f'  total_tokens_bought: {zfi.get("total_tokens_bought")} tokens')
        print(f'  avg_entry_price: {zfi.get("avg_entry_price")} native')
        print(f'  total_investment_native: {zfi.get("total_investment_native")} native')
        print()
        
        # From chat history
        original_qty = 1035.78085717656
        new_qty = 4519.36849
        additional_qty = new_qty - original_qty
        original_price = float(zfi.get('avg_entry_price', 0))
        
        print('From chat history:')
        print(f'  Original quantity: {original_qty} tokens')
        print(f'  New quantity: {new_qty} tokens')
        print(f'  Additional bought: {additional_qty} tokens')
        print(f'  Original entry price: {original_price} native')
        print()
        
        # Get current market price
        price_result = supabase.client.table('lowcap_price_data_1m').select('*').eq('token_contract', zfi.get('token_contract')).order('timestamp', desc=True).limit(1).execute()
        
        if price_result.data:
            current_price = float(price_result.data[0].get('price_native', 0))
            current_price_usd = float(price_result.data[0].get('price_usd', 0))
            
            print(f'Current market price: {current_price:.8f} native (${current_price_usd:.4f} USD)')
            print()
            
            print('What I would update ZFI to:')
            print(f'  total_quantity: {new_qty} tokens (from {zfi.get("total_quantity")})')
            print(f'  total_tokens_bought: {new_qty} tokens (from {zfi.get("total_tokens_bought")})')
            print(f'  avg_entry_price: {current_price:.8f} native (from {original_price:.8f})')
            print(f'  total_investment_native: {new_qty * current_price:.8f} native')
            print()
            
            print(f'This assumes you bought all {new_qty} tokens at the current market price of {current_price:.8f} native.')
            print('Is this correct, or did you buy the additional tokens at a different price?')
            
        else:
            print('❌ No current price data found for ZFI')
    else:
        print('❌ ZFI position not found')

if __name__ == "__main__":
    asyncio.run(analyze_zfi())
