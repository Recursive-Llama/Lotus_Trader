#!/usr/bin/env python3
"""
Test if there's a bug in the Price Oracle where it's swapping price_native and price_usd
"""

import sys
import os
sys.path.append('src')

from dotenv import load_dotenv
load_dotenv()

import requests

def test_price_oracle_bug():
    """Test if Price Oracle is swapping native and USD prices"""
    
    token_address = "0xc56C7A0eAA804f854B536A5F3D5f49D2EC4B12b8"
    
    print(f"Testing Price Oracle bug for token: {token_address}")
    print("=" * 60)
    
    # Test direct DexScreener API call (same as Price Oracle)
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
                
                print("📊 DexScreener raw data:")
                print(f"  priceNative: {price_native}")
                print(f"  priceUsd: {price_usd}")
                
                # Compare with the database entries
                db_entry_1_price = 0.00007314
                
                print(f"\n🔍 Comparison:")
                print(f"  Database entry 1 price: {db_entry_1_price}")
                print(f"  DexScreener priceNative: {price_native}")
                print(f"  DexScreener priceUsd: {price_usd}")
                
                # Check which one matches
                if abs(float(price_native) - db_entry_1_price) < 0.000001:
                    print("  ✅ Database entry matches priceNative (CORRECT)")
                elif abs(float(price_usd) - db_entry_1_price) < 0.000001:
                    print("  ❌ Database entry matches priceUsd (BUG!)")
                    print("     This means the Price Oracle is using USD price as native price!")
                else:
                    print("  ⚠️  Database entry doesn't match either (UNKNOWN)")
                    
                # Check the ratio
                native_to_usd_ratio = float(price_native) / float(price_usd) if float(price_usd) > 0 else 0
                db_to_native_ratio = db_entry_1_price / float(price_native) if float(price_native) > 0 else 0
                db_to_usd_ratio = db_entry_1_price / float(price_usd) if float(price_usd) > 0 else 0
                
                print(f"\n📈 Ratios:")
                print(f"  priceNative/priceUsd: {native_to_usd_ratio:.6f}")
                print(f"  db_entry/priceNative: {db_to_native_ratio:.6f}")
                print(f"  db_entry/priceUsd: {db_to_usd_ratio:.6f}")
                
                if abs(db_to_usd_ratio - 1.0) < 0.01:  # Within 1%
                    print("  🚨 CONFIRMED BUG: Database entry is using USD price as native price!")
                
            else:
                print("❌ No Ethereum pairs found")
        else:
            print(f"❌ DexScreener API error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_price_oracle_bug()
