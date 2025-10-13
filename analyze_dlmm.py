#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio

async def analyze_dlmm():
    supabase = SupabaseManager()
    
    print('=== DLMM ANALYSIS - NO CHANGES YET ===')
    print()
    
    # Get DLMM position
    result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', 'DLMM').eq('status', 'active').execute()
    
    if result.data:
        dlmm = result.data[0]
        
        print('Current DLMM values in database:')
        print(f'  total_quantity: {dlmm.get("total_quantity")} tokens')
        print(f'  total_tokens_bought: {dlmm.get("total_tokens_bought")} tokens')
        print(f'  avg_entry_price: {dlmm.get("avg_entry_price")} native')
        print(f'  total_investment_native: {dlmm.get("total_investment_native")} native')
        print()
        
        # From chat history
        original_qty = 16138.5600545948
        new_qty = 100840
        additional_qty = new_qty - original_qty
        original_price = float(dlmm.get('avg_entry_price', 0))
        
        print('From chat history:')
        print(f'  Original quantity: {original_qty} tokens')
        print(f'  New quantity: {new_qty} tokens')
        print(f'  Additional bought: {additional_qty} tokens')
        print(f'  Original entry price: {original_price} native')
        print()
        
        # Get current market price
        price_result = supabase.client.table('lowcap_price_data_1m').select('*').eq('token_contract', dlmm.get('token_contract')).order('timestamp', desc=True).limit(1).execute()
        
        if price_result.data:
            current_price = float(price_result.data[0].get('price_native', 0))
            current_price_usd = float(price_result.data[0].get('price_usd', 0))
            
            print(f'Current market price: {current_price:.8f} native (${current_price_usd:.4f} USD)')
            print()
            
            # Calculate weighted average
            existing_investment = original_qty * original_price
            additional_investment = additional_qty * current_price
            total_investment = existing_investment + additional_investment
            weighted_avg_price = total_investment / new_qty
            
            print('Weighted Average Calculation:')
            print(f'  Existing: {original_qty} tokens × {original_price:.8f} = {existing_investment:.8f} native')
            print(f'  Additional: {additional_qty} tokens × {current_price:.8f} = {additional_investment:.8f} native')
            print(f'  Total investment: {total_investment:.8f} native')
            print(f'  Weighted avg price: {total_investment:.8f} ÷ {new_qty} = {weighted_avg_price:.8f} native')
            print()
            
            print('What I would update DLMM to:')
            print(f'  total_quantity: {new_qty} tokens')
            print(f'  total_tokens_bought: {new_qty} tokens')
            print(f'  avg_entry_price: {weighted_avg_price:.8f} native')
            print(f'  total_investment_native: {total_investment:.8f} native')
            print()
            
            print('Does this look correct?')
            
        else:
            print('❌ No current price data found for DLMM')
    else:
        print('❌ DLMM position not found')

if __name__ == "__main__":
    asyncio.run(analyze_dlmm())
