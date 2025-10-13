#!/usr/bin/env python3

import sys
import os
sys.path.append('src')
from utils.supabase_manager import SupabaseManager

def main():
    sm = SupabaseManager()

    # Get current prices for each token
    tokens = [
        ('RAIN', '4W7cM6SUuqhv9jp2t3jfmonXzNbDsJt5PCWqt7w1Axa2', 'solana'),
        ('LAUNCHCOIN', 'Ey59PH7Z4BFU4HjyKnyMdWt5GGN76KazTAwQihoUXRnk', 'solana'),
        ('USELESS', 'Dz9mQ9NzkBcCsuGPFJ3r1bS4wgqKMHBPiVuniW8Mbonk', 'solana')
    ]

    for ticker, contract, chain in tokens:
        price_data = sm.client.table('lowcap_price_data_1m').select('price_native, price_usd, timestamp').eq('token_contract', contract).eq('chain', chain).order('timestamp', desc=True).limit(1).execute()
        
        if price_data.data:
            current_price = price_data.data[0]['price_native']
            current_price_usd = price_data.data[0]['price_usd']
            entry_price_plus_5 = current_price * 1.05
            print(f'{ticker}: {current_price:.8f} SOL (${current_price_usd:.8f})')
            print(f'  Entry price +5%: {entry_price_plus_5:.8f} SOL')
            print()
        else:
            print(f'{ticker}: No price data found')
            print()

if __name__ == "__main__":
    main()
