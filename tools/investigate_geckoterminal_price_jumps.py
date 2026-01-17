#!/usr/bin/env python3
"""
Investigate GeckoTerminal Extreme Price Jumps

This script helps diagnose why extreme price jumps are being detected.
It will:
1. Fetch sample OHLCV data from GeckoTerminal
2. Show actual price values
3. Check for unit mismatches
4. Identify patterns
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Dict, Any, List, Optional
import requests
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

GT_BASE = "https://api.geckoterminal.com/api/v2"
GT_HEADERS = {"accept": "application/json;version=20230302"}

NETWORK_MAP = {
    'solana': 'solana',
    'ethereum': 'eth',
    'base': 'base',
    'bsc': 'bsc',
}


def fetch_gt_ohlcv_sample(network: str, pool_address: str, limit: int = 10) -> Dict[str, Any]:
    """Fetch a small sample of OHLCV data to inspect."""
    url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/hour?limit={limit}&aggregate=1"
    
    try:
        resp = requests.get(url, headers=GT_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching OHLCV: {e}")
        return {}


def analyze_ohlcv_response(data: Dict[str, Any], pool_addr: str, quote_symbol: str) -> None:
    """Analyze the OHLCV response to understand what's being returned."""
    ohlcv_list = (data.get('data', {}) or {}).get('attributes', {}).get('ohlcv_list', []) or []
    
    if not ohlcv_list:
        print("No OHLCV data in response")
        return
    
    print(f"\n{'='*80}")
    print(f"OHLCV Analysis for pool {pool_addr[:16]}... (quote: {quote_symbol})")
    print(f"{'='*80}")
    print(f"Total bars: {len(ohlcv_list)}")
    
    # Check response structure
    print(f"\nResponse structure:")
    print(f"  data.attributes keys: {list(data.get('data', {}).get('attributes', {}).keys())}")
    
    # Analyze first few bars
    print(f"\nFirst 5 bars:")
    for i, entry in enumerate(ohlcv_list[:5]):
        try:
            ts_sec = int(entry[0])
            open_val = float(entry[1])
            high_val = float(entry[2])
            low_val = float(entry[3])
            close_val = float(entry[4])
            volume = float(entry[5])
            
            from datetime import datetime, timezone
            ts_dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
            
            ratio = max(close_val / open_val, open_val / close_val) if open_val > 0 and close_val > 0 else 0
            
            print(f"\n  Bar {i+1}: {ts_dt.isoformat()}")
            print(f"    Raw values: open={open_val:.10f} high={high_val:.10f} low={low_val:.10f} close={close_val:.10f}")
            print(f"    Volume: {volume:.2f}")
            print(f"    Open/Close ratio: {ratio:.4f}")
            
            if ratio > 100.0:
                print(f"    ⚠️  EXTREME JUMP DETECTED!")
        except Exception as e:
            print(f"  Bar {i+1}: Error parsing - {e}")
            print(f"    Raw entry: {entry}")
    
    # Check for patterns
    print(f"\n{'='*80}")
    print("Pattern Analysis:")
    print(f"{'='*80}")
    
    ratios = []
    for entry in ohlcv_list:
        try:
            open_val = float(entry[1])
            close_val = float(entry[4])
            if open_val > 0 and close_val > 0:
                ratio = max(close_val / open_val, open_val / close_val)
                ratios.append(ratio)
        except:
            pass
    
    if ratios:
        import statistics
        print(f"  Ratio stats: min={min(ratios):.4f} max={max(ratios):.4f} mean={statistics.mean(ratios):.4f} median={statistics.median(ratios):.4f}")
        extreme_count = sum(1 for r in ratios if r > 100.0)
        print(f"  Extreme jumps (>100x): {extreme_count}/{len(ratios)}")
        
        if extreme_count > 0:
            print(f"\n  ⚠️  Found {extreme_count} extreme jumps in sample!")
            print(f"  This suggests a systemic issue with the data or units.")


def check_pool_info(network: str, pool_address: str) -> Dict[str, Any]:
    """Get pool information to understand quote token."""
    url = f"{GT_BASE}/networks/{network}/pools/{pool_address}"
    
    try:
        resp = requests.get(url, headers=GT_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching pool info: {e}")
        return {}


def main():
    """Main investigation function."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_KEY required")
        return
    
    sb: Client = create_client(supabase_url, supabase_key)
    
    print("\n" + "="*80)
    print("GeckoTerminal Extreme Price Jumps Investigation")
    print("="*80 + "\n")
    
    # Get a few positions that might be showing jumps
    result = sb.table('lowcap_positions').select('token_contract,token_chain,features').in_('status', ['active', 'watchlist']).limit(10).execute()
    
    positions = result.data or []
    if not positions:
        print("No positions found")
        return
    
    print(f"Testing with {len(positions)} positions...\n")
    
    for pos in positions[:3]:  # Test first 3
        token_contract = pos.get('token_contract')
        chain = pos.get('token_chain', '').lower()
        features = pos.get('features') or {}
        
        # Get canonical pool
        canonical = features.get('canonical_pool')
        if not canonical:
            print(f"\n{token_contract[:8]}.../{chain}: No canonical pool found")
            continue
        
        pool_addr = canonical.get('pair_address')
        quote_symbol = canonical.get('quote_symbol', '?')
        network = NETWORK_MAP.get(chain, chain)
        
        if not pool_addr:
            print(f"\n{token_contract[:8]}.../{chain}: No pool address")
            continue
        
        print(f"\n{'='*80}")
        print(f"Token: {token_contract[:16]}.../{chain}")
        print(f"Pool: {pool_addr[:32]}...")
        print(f"Quote: {quote_symbol}")
        print(f"{'='*80}")
        
        # Get pool info
        pool_info = check_pool_info(network, pool_addr)
        if pool_info:
            pool_data = pool_info.get('data', {})
            if pool_data:
                attributes = pool_data.get('attributes', {})
                pool_name = attributes.get('name', '?')
                base_token = attributes.get('base_token', {})
                quote_token = attributes.get('quote_token', {})
                print(f"Pool name: {pool_name}")
                if base_token:
                    print(f"Base token: {base_token.get('symbol', '?')} ({base_token.get('address', '?')[:16]}...)")
                if quote_token:
                    print(f"Quote token: {quote_token.get('symbol', '?')} ({quote_token.get('address', '?')[:16]}...)")
        
        # Fetch OHLCV sample
        ohlcv_data = fetch_gt_ohlcv_sample(network, pool_addr, limit=20)
        if ohlcv_data:
            analyze_ohlcv_response(ohlcv_data, pool_addr, quote_symbol)
        
        print("\n")
    
    print("\n" + "="*80)
    print("Investigation complete!")
    print("="*80)
    print("\nNext steps:")
    print("1. Review the price values - do they look like USD or native units?")
    print("2. Check if quote_symbol matches the quote token in pool info")
    print("3. Compare price magnitudes with known USD prices")
    print("4. Check if extreme jumps correlate with pool switches")
    print("\n")


if __name__ == "__main__":
    main()

