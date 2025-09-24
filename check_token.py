#!/usr/bin/env python3
import requests

token = '0x8dEdf84656fa932157e27C060D8613824e7979e3'
print(f'Checking token {token} on DexScreener...')

try:
    response = requests.get(f'https://api.dexscreener.com/latest/dex/tokens/{token}', timeout=10)
    if response.ok:
        data = response.json()
        pairs = data.get('pairs', [])
        bsc_pairs = [p for p in pairs if p.get('chainId') == 'bsc']
        
        print(f'Found {len(bsc_pairs)} BSC pairs')
        
        # Look for WBNB pairs specifically
        wbnb_pairs = [p for p in bsc_pairs if 'WBNB' in p.get('quoteToken', {}).get('symbol', '') or 'WBNB' in p.get('baseToken', {}).get('symbol', '')]
        print(f'Found {len(wbnb_pairs)} WBNB pairs:')
        for i, pair in enumerate(wbnb_pairs):
            base_symbol = pair.get('baseToken', {}).get('symbol', 'Unknown')
            quote_symbol = pair.get('quoteToken', {}).get('symbol', 'Unknown')
            liquidity = pair.get('liquidity', {}).get('usd', 0)
            dex = pair.get('dexId', 'Unknown')
            print(f'  WBNB Pair {i+1}: {base_symbol} / {quote_symbol} - Liquidity: ${liquidity:,.0f} - DEX: {dex}')
        
        # Show all pairs sorted by liquidity
        bsc_pairs.sort(key=lambda p: p.get('liquidity', {}).get('usd', 0), reverse=True)
        print(f'\nAll pairs (top 10 by liquidity):')
        for i, pair in enumerate(bsc_pairs[:10]):
            base_symbol = pair.get('baseToken', {}).get('symbol', 'Unknown')
            quote_symbol = pair.get('quoteToken', {}).get('symbol', 'Unknown')
            liquidity = pair.get('liquidity', {}).get('usd', 0)
            print(f'  {i+1}: {base_symbol} / {quote_symbol} - Liquidity: ${liquidity:,.0f}')
    else:
        print(f'DexScreener error: {response.status_code}')
except Exception as e:
    print(f'Error: {e}')
