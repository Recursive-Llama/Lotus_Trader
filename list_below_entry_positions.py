#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.supabase_manager import SupabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    supabase_manager = SupabaseManager()
    
    # Get active positions
    positions_response = supabase_manager.client.table('lowcap_positions').select('*').eq('status', 'active').execute()
    positions = positions_response.data
    logger.info(f"Found {len(positions)} active positions")
    
    below_entry_positions = []
    
    for position in positions:
        print(f"Position fields: {list(position.keys())}")
        position_id = position.get('id', position.get('position_id', 'unknown'))
        ticker = position.get('token_ticker', 'UNKNOWN')
        chain = position.get('token_chain', 'unknown')
        avg_entry_price = position.get('avg_entry_price', 0)
        
        if avg_entry_price <= 0:
            continue
            
        # Get current price
        try:
            price_data = supabase_manager.client.table('lowcap_price_data_1m').select(
                'price_native, price_usd, timestamp'
            ).eq('token_contract', position['token_contract']).eq('chain', chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if price_data.data:
                current_price_native = price_data.data[0]['price_native']
                current_price_usd = price_data.data[0]['price_usd']
                
                # Calculate proximity
                proximity_pct = abs((current_price_native - avg_entry_price) / avg_entry_price * 100)
                direction = "below" if current_price_native < avg_entry_price else "above"
                
                if direction == "below":
                    below_entry_positions.append({
                        'ticker': ticker,
                        'chain': chain,
                        'entry_price': avg_entry_price,
                        'current_price': current_price_native,
                        'current_price_usd': current_price_usd,
                        'proximity_pct': proximity_pct
                    })
                    
        except Exception as e:
            logger.warning(f"Error getting price for {ticker}: {e}")
            continue
    
    # Sort by proximity (closest to entry first)
    below_entry_positions.sort(key=lambda x: x['proximity_pct'])
    
    print(f"\n📉 POSITIONS BELOW ENTRY PRICE ({len(below_entry_positions)} total):")
    print("=" * 80)
    
    for i, pos in enumerate(below_entry_positions, 1):
        native_symbol = "SOL" if pos['chain'] == "solana" else "ETH" if pos['chain'] in ["ethereum", "base"] else "BNB" if pos['chain'] == "bsc" else pos['chain'].upper()
        
        print(f"{i:2d}. {pos['ticker']} ({pos['chain']})")
        print(f"    Entry: {pos['entry_price']:.8f} {native_symbol}")
        print(f"    Current: {pos['current_price']:.8f} {native_symbol}")
        print(f"    USD: ${pos['current_price_usd']:.8f}")
        print(f"    Below by: {pos['proximity_pct']:.2f}%")
        print()

if __name__ == "__main__":
    main()
