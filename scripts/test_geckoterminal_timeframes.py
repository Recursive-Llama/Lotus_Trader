#!/usr/bin/env python3
"""
Test script to verify GeckoTerminal API supports different timeframes.
Tests 1m, 5m, 15m, and 1h endpoints with a known token.
"""

import os
import sys
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.intelligence.lowcap_portfolio_manager.jobs.geckoterminal_backfill import (
    GT_BASE,
    GT_HEADERS,
    NETWORK_MAP,
    _select_canonical_pool_from_gt,
)

load_dotenv()

# Test token: LUMEN (we know this works)
TEST_TOKEN = {
    "ticker": "LUMEN",
    "contract": "BkpaxHhE6snExazrPkVAjxDyZa8Nq3oDEzm5GQm2pump",
    "chain": "solana",
}


def test_timeframe_endpoint(network: str, pool_address: str, timeframe: str, aggregate: int = None):
    """
    Test a specific timeframe endpoint.
    
    Args:
        network: Network name (e.g., 'solana')
        pool_address: Pool address
        timeframe: 'minute', 'hour', or 'day'
        aggregate: For minute/hour, the aggregation interval (1, 5, 15 for minute; 1, 4, 12 for hour)
    """
    params = ["limit=10"]  # Just get 10 bars to test
    
    # Build URL based on timeframe
    if timeframe == "minute":
        if aggregate:
            url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/minute?aggregate={aggregate}&" + "&".join(params)
        else:
            url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/minute?" + "&".join(params)
    elif timeframe == "hour":
        if aggregate:
            url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/hour?aggregate={aggregate}&" + "&".join(params)
        else:
            url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/hour?" + "&".join(params)
    elif timeframe == "day":
        url = f"{GT_BASE}/networks/{network}/pools/{pool_address}/ohlcv/day?" + "&".join(params)
    else:
        return None, f"Unknown timeframe: {timeframe}"
    
    try:
        print(f"  Testing: {url}")
        resp = requests.get(url, headers=GT_HEADERS, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            ohlcv_data = data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
            if ohlcv_data:
                return True, f"✅ Success! Got {len(ohlcv_data)} bars"
            else:
                return False, f"⚠️  Success but no data returned"
        elif resp.status_code == 404:
            return False, f"❌ 404 Not Found - endpoint doesn't exist"
        elif resp.status_code == 429:
            return False, f"❌ 429 Rate Limited - try again later"
        else:
            return False, f"❌ {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"❌ Exception: {str(e)}"


def main():
    print("="*70)
    print("TESTING GECKOTERMINAL API TIMEFRAMES")
    print("="*70)
    print(f"\nTest Token: {TEST_TOKEN['ticker']} ({TEST_TOKEN['contract'][:30]}...)")
    print(f"Chain: {TEST_TOKEN['chain']}")
    
    # Get pool address
    print("\n" + "="*70)
    print("Step 1: Finding pool address...")
    print("="*70)
    
    network = NETWORK_MAP.get(TEST_TOKEN['chain'], TEST_TOKEN['chain'])
    pool_info = _select_canonical_pool_from_gt(TEST_TOKEN['chain'], TEST_TOKEN['contract'])
    
    if not pool_info:
        print("❌ Failed to find pool for test token")
        return
    
    pool_address, dex_id, quote_symbol = pool_info
    print(f"✅ Found pool: {pool_address}")
    print(f"   DEX: {dex_id}")
    print(f"   Quote: {quote_symbol}")
    
    # Test different timeframes
    print("\n" + "="*70)
    print("Step 2: Testing timeframe endpoints...")
    print("="*70)
    
    tests = [
        # (timeframe, aggregate, description)
        ("minute", 1, "1m bars"),
        ("minute", 5, "5m bars"),
        ("minute", 15, "15m bars"),
        ("hour", 1, "1h bars"),
        ("hour", 4, "4h bars"),
        ("hour", 12, "12h bars"),
        ("day", None, "1d bars"),
    ]
    
    results = []
    for timeframe, aggregate, description in tests:
        print(f"\n📊 Testing {description}...")
        success, message = test_timeframe_endpoint(network, pool_address, timeframe, aggregate)
        results.append((description, success, message))
        print(f"   {message}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for description, success, message in results:
        status = "✅" if success else "❌"
        print(f"{status} {description:15s} - {message}")
    
    successful = sum(1 for _, success, _ in results if success)
    total = len(results)
    print(f"\n✅ {successful}/{total} endpoints working")
    
    # Recommendations
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    working_timeframes = []
    for description, success, _ in results:
        if success:
            if "1m" in description:
                working_timeframes.append("1m")
            elif "5m" in description:
                working_timeframes.append("5m")
            elif "15m" in description:
                working_timeframes.append("15m")
            elif "1h" in description:
                working_timeframes.append("1h")
    
    if working_timeframes:
        print(f"\n✅ Working timeframes for our use case: {', '.join(working_timeframes)}")
        print("\nMapping to our plan:")
        print("  - 1 day old tokens → Use 1m (if available)")
        print("  - 3 days old tokens → Use 5m (if available)")
        print("  - 7 days old tokens → Use 15m (if available)")
        print("  - 14+ days old tokens → Use 1h (current)")
    else:
        print("\n⚠️  No working timeframes found - check API documentation")


if __name__ == "__main__":
    main()

