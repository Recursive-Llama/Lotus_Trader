#!/usr/bin/env python3
"""
Debug script to test the exact flow that creates entries
"""

import sys
import os
sys.path.append('src')

from dotenv import load_dotenv
load_dotenv()

import requests

def test_price_oracle_flow():
    """Test the exact flow that creates entries"""
    
    token_address = "0xc56C7A0eAA804f854B536A5F3D5f49D2EC4B12b8"
    
    print(f"Testing Price Oracle flow for token: {token_address}")
    print("=" * 60)
    
    # Simulate the exact Price Oracle logic
    try:
        response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
        if response.ok:
            data = response.json()
            pairs = data.get('pairs', [])
            eth_pairs = [p for p in pairs if p.get('chainId') == 'ethereum']
            
            if eth_pairs:
                # Get the pair with highest liquidity (exact same logic as Price Oracle)
                eth_pairs.sort(key=lambda p: (p.get('liquidity', {}).get('usd') or 0), reverse=True)
                best_pair = eth_pairs[0]
                price_native = best_pair.get('priceNative')
                price_usd = best_pair.get('priceUsd')
                
                if price_native and price_usd:
                    print("✅ Price Oracle would return:")
                    print(f"  price_native: {price_native}")
                    print(f"  price_usd: {price_usd}")
                    
                    # Simulate the exact code from trader_lowcap_simple_v2.py
                    price_info = {
                        'price_native': float(price_native),
                        'price_usd': float(price_usd),
                        'quote_token': 'WETH'
                    }
                    
                    # This is the exact line from the code:
                    price = price_info['price_native'] if price_info else None
                    
                    print(f"\n📊 Entry creation would use:")
                    print(f"  price = {price}")
                    
                    # Now simulate EntryExitPlanner.build_entries
                    from intelligence.trader_lowcap.entry_exit_planner import EntryExitPlanner
                    
                    # Use a sample allocation amount
                    total_native = 0.000209373  # This is alloc_native / 3.0 from your data
                    
                    entries = EntryExitPlanner.build_entries(price, total_native)
                    
                    print(f"\n🎯 Generated entries:")
                    for entry in entries:
                        print(f"  Entry {entry['entry_number']}: price={entry['price']}, amount_native={entry['amount_native']}")
                    
                    # Compare with your actual database entries
                    print(f"\n📋 Your actual database entries:")
                    print(f"  Entry 1: price=0.00007314, amount_native=0.00006979100223031817")
                    print(f"  Entry 2: price=0.00005119799999999999, amount_native=0.00006979100223031817")
                    print(f"  Entry 3: price=0.000029256, amount_native=0.00006979100223031817")
                    
                    # Check if there's a mismatch
                    if abs(entries[0]['price'] - 0.00007314) < 0.000001:
                        print("✅ Generated entry 1 matches database entry 1")
                    else:
                        print(f"❌ Mismatch: Generated {entries[0]['price']} vs Database 0.00007314")
                        
                    # Check if the generated price looks like USD
                    if price > 0.00001:  # If > 0.00001, likely USD
                        print("⚠️  WARNING: The price being used looks like USD price, not ETH price!")
                        print("   This suggests there's a bug where USD price is being used as native price")
                    else:
                        print("✅ The price being used looks like ETH price")
                        
            else:
                print("❌ No Ethereum pairs found")
        else:
            print(f"❌ DexScreener API error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_price_oracle_flow()