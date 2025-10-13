#!/usr/bin/env python3

import sys
sys.path.append('src')
from utils.supabase_manager import SupabaseManager
import asyncio

async def analyze_batch_2():
    supabase = SupabaseManager()
    
    print('=== BATCH 2 ANALYSIS - ANYONE, RAIN, WAGER ===')
    print()
    
    # Positions to analyze
    positions = ['ANYONE', 'RAIN', 'WAGER']
    
    for ticker in positions:
        print(f'--- {ticker} ---')
        
        # Get position
        result = supabase.client.table('lowcap_positions').select('*').eq('token_ticker', ticker).eq('status', 'active').execute()
        
        if result.data:
            pos = result.data[0]
            
            print(f'Current values:')
            print(f'  total_quantity: {pos.get("total_quantity")} tokens')
            print(f'  total_tokens_bought: {pos.get("total_tokens_bought")} tokens')
            print(f'  avg_entry_price: {pos.get("avg_entry_price")} native')
            print(f'  total_investment_native: {pos.get("total_investment_native")} native')
            
            # From chat history - original quantities
            original_quantities = {
                'ANYONE': 49.5864367246646,
                'RAIN': 3598.25431426294,
                'WAGER': 88.2219342722001
            }
            
            # New quantities from portfolio
            new_quantities = {
                'ANYONE': 131.88236,
                'RAIN': 9799.90862,
                'WAGER': 112050
            }
            
            original_qty = original_quantities[ticker]
            new_qty = new_quantities[ticker]
            additional_qty = new_qty - original_qty
            original_price = float(pos.get('avg_entry_price', 0))
            
            print(f'From chat history:')
            print(f'  Original: {original_qty} tokens')
            print(f'  New: {new_qty} tokens')
            print(f'  Additional: {additional_qty} tokens')
            print(f'  Original price: {original_price:.8f} native')
            
            # Get current market price
            price_result = supabase.client.table('lowcap_price_data_1m').select('*').eq('token_contract', pos.get('token_contract')).order('timestamp', desc=True).limit(1).execute()
            
            if price_result.data:
                current_price = float(price_result.data[0].get('price_native', 0))
                current_price_usd = float(price_result.data[0].get('price_usd', 0))
                
                print(f'Current market price: {current_price:.8f} native (${current_price_usd:.4f} USD)')
                
                # Calculate weighted average
                existing_investment = original_qty * original_price
                additional_investment = additional_qty * current_price
                total_investment = existing_investment + additional_investment
                weighted_avg_price = total_investment / new_qty
                
                print(f'Weighted average calculation:')
                print(f'  Existing: {original_qty} × {original_price:.8f} = {existing_investment:.8f} native')
                print(f'  Additional: {additional_qty} × {current_price:.8f} = {additional_investment:.8f} native')
                print(f'  Total: {total_investment:.8f} native')
                print(f'  Weighted avg: {weighted_avg_price:.8f} native')
                print()
                
            else:
                print(f'❌ No current price data found for {ticker}')
                print()
        else:
            print(f'❌ {ticker} position not found')
            print()

if __name__ == "__main__":
    asyncio.run(analyze_batch_2())
