"""
Comprehensive Hyperliquid Trading API Tests

Tests everything we can without authentication:
1. Market data queries
2. Asset ID computation
3. Market context (mark price, funding, OI)
4. Order book queries
5. Recent trades
6. Error handling

Run with: python tests/hyperliquid/test_trading_api_comprehensive.py
"""

import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Hyperliquid API endpoints
INFO_URL = "https://api.hyperliquid.xyz/info"
EXCHANGE_URL = "https://api.hyperliquid.xyz/exchange"

# Test symbols
TEST_MAIN_DEX = "BTC"
TEST_HIP3 = "xyz:TSLA"


def test_meta_and_universe() -> Dict[str, Any]:
    """Test 1: Query universe and asset metadata."""
    print("\n" + "="*80)
    print("TEST 1: Universe & Asset Metadata")
    print("="*80)
    
    payload = {"type": "meta"}
    response = requests.post(INFO_URL, json=payload, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ Failed: {response.status_code}")
        return {}
    
    data = response.json()
    universe = data.get("universe", [])
    
    print(f"✅ Got {len(universe)} assets in universe")
    print(f"\nSample assets (first 10):")
    for i, asset in enumerate(universe[:10]):
        print(f"  {i}: {asset.get('name')} - Leverage: {asset.get('maxLeverage')}x, Decimals: {asset.get('szDecimals')}")
    
    # Find BTC
    btc = next((a for a in universe if a.get("name") == "BTC"), None)
    if btc:
        print(f"\n✅ BTC Details:")
        print(f"  Asset ID: {universe.index(btc)}")
        print(f"  Max Leverage: {btc.get('maxLeverage')}x")
        print(f"  Size Decimals: {btc.get('szDecimals')}")
        print(f"  Margin Table ID: {btc.get('marginTableId')}")
    
    return data


def test_perp_dexs() -> List[Dict[str, Any]]:
    """Test 2: Query HIP-3 DEXs."""
    print("\n" + "="*80)
    print("TEST 2: HIP-3 PerpDexs")
    print("="*80)
    
    payload = {"type": "perpDexs"}
    response = requests.post(INFO_URL, json=payload, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ Failed: {response.status_code}")
        return []
    
    perp_dexs = response.json()
    print(f"✅ Got {len(perp_dexs)} HIP-3 DEXs")
    
    for i, dex in enumerate(perp_dexs[:10]):
        if isinstance(dex, dict):
            print(f"  {i}: {dex.get('name')} - {dex.get('fullName', 'N/A')}")
        else:
            print(f"  {i}: {dex}")
    
    return perp_dexs


def test_hip3_asset_id() -> Optional[int]:
    """Test 3: Compute HIP-3 asset ID."""
    print("\n" + "="*80)
    print("TEST 3: HIP-3 Asset ID Computation")
    print("="*80)
    
    # Get perpDexs
    perp_dexs = test_perp_dexs()
    if not perp_dexs:
        return None
    
    dex_name, coin = TEST_HIP3.split(":", 1)
    
    # Find dex index
    dex_index = None
    for i, dex in enumerate(perp_dexs):
        if isinstance(dex, dict) and dex.get("name") == dex_name:
            dex_index = i
            break
        elif isinstance(dex, str) and dex == dex_name:
            dex_index = i
            break
    
    if dex_index is None:
        print(f"❌ DEX '{dex_name}' not found")
        return None
    
    print(f"✅ Found DEX '{dex_name}' at index {dex_index}")
    
    # Get DEX universe
    payload = {"type": "meta", "dex": dex_name}
    response = requests.post(INFO_URL, json=payload, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ Failed to get DEX meta: {response.status_code}")
        return None
    
    dex_meta = response.json()
    universe = dex_meta.get("universe", [])
    
    # Find coin
    full_name = f"{dex_name}:{coin}"
    coin_index = None
    for j, asset in enumerate(universe):
        if asset.get("name") == full_name or asset.get("name") == coin:
            coin_index = j
            print(f"✅ Found '{asset.get('name')}' at index {coin_index}")
            print(f"  Max Leverage: {asset.get('maxLeverage')}x")
            print(f"  Size Decimals: {asset.get('szDecimals')}")
            break
    
    if coin_index is None:
        print(f"❌ Coin '{coin}' not found in DEX universe")
        return None
    
    # Compute asset ID
    asset_id = 100000 + dex_index * 10000 + coin_index
    print(f"\n✅ Asset ID: {asset_id}")
    print(f"  Formula: 100000 + {dex_index} * 10000 + {coin_index} = {asset_id}")
    
    return asset_id


def test_market_context() -> None:
    """Test 4: Query market context (mark price, funding, OI)."""
    print("\n" + "="*80)
    print("TEST 4: Market Context (Mark Price, Funding, OI)")
    print("="*80)
    
    payload = {"type": "metaAndAssetCtxs"}
    response = requests.post(INFO_URL, json=payload, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ Failed: {response.status_code}")
        return
    
    data = response.json()
    
    if "meta" in data and "universe" in data["meta"]:
        universe = data["meta"]["universe"]
        print(f"✅ Got universe with {len(universe)} assets")
    
    if "assetCtxs" in data:
        ctxs = data["assetCtxs"]
        print(f"✅ Got market context for {len(ctxs)} assets")
        
        # Show BTC context if available
        if len(ctxs) > 0:
            btc_ctx = ctxs[0]  # Assuming BTC is first
            print(f"\nSample context (first asset):")
            print(f"  Keys: {list(btc_ctx.keys())}")
            if "markPx" in btc_ctx:
                print(f"  Mark Price: {btc_ctx.get('markPx')}")
            if "funding" in btc_ctx:
                print(f"  Funding: {btc_ctx.get('funding')}")
            if "openInterest" in btc_ctx:
                print(f"  Open Interest: {btc_ctx.get('openInterest')}")


def test_orderbook() -> None:
    """Test 5: Query order book."""
    print("\n" + "="*80)
    print("TEST 5: Order Book")
    print("="*80)
    
    payload = {
        "type": "l2Book",
        "coin": TEST_MAIN_DEX
    }
    
    response = requests.post(INFO_URL, json=payload, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Got order book for {TEST_MAIN_DEX}")
        print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        if isinstance(data, dict):
            if "levels" in data:
                levels = data["levels"]
                print(f"  Levels: {len(levels)}")
                if levels:
                    print(f"  First level: {levels[0]}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"  Response: {response.text[:200]}")


def test_recent_trades() -> None:
    """Test 6: Query recent trades."""
    print("\n" + "="*80)
    print("TEST 6: Recent Trades")
    print("="*80)
    
    payload = {
        "type": "trades",
        "coin": TEST_MAIN_DEX
    }
    
    response = requests.post(INFO_URL, json=payload, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Got recent trades for {TEST_MAIN_DEX}")
        
        if isinstance(data, list):
            print(f"  Number of trades: {len(data)}")
            if data:
                print(f"  First trade: {data[0]}")
        elif isinstance(data, dict):
            print(f"  Keys: {list(data.keys())}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"  Response: {response.text[:200]}")


def test_all_assets_metadata() -> None:
    """Test 7: Get metadata for all assets (main DEX + HIP-3)."""
    print("\n" + "="*80)
    print("TEST 7: All Assets Metadata")
    print("="*80)
    
    # Main DEX
    main_meta = test_meta_and_universe()
    main_count = len(main_meta.get("universe", []))
    
    # HIP-3 DEXs
    perp_dexs = test_perp_dexs()
    hip3_count = 0
    
    for dex in perp_dexs[:3]:  # Test first 3 DEXs
        dex_name = dex.get("name") if isinstance(dex, dict) else dex
        payload = {"type": "meta", "dex": dex_name}
        response = requests.post(INFO_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            dex_meta = response.json()
            universe = dex_meta.get("universe", [])
            hip3_count += len(universe)
            print(f"  {dex_name}: {len(universe)} assets")
    
    print(f"\n✅ Total assets:")
    print(f"  Main DEX: {main_count}")
    print(f"  HIP-3 (first 3 DEXs): {hip3_count}")
    print(f"  Total (sampled): {main_count + hip3_count}")


def test_error_handling() -> None:
    """Test 8: Error handling for invalid requests."""
    print("\n" + "="*80)
    print("TEST 8: Error Handling")
    print("="*80)
    
    # Invalid coin
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "INVALID_TOKEN_XYZ123",
            "interval": "15m",
            "startTime": 1000000000000,
            "endTime": 2000000000000
        }
    }
    
    response = requests.post(INFO_URL, json=payload, timeout=10)
    print(f"Invalid coin test:")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200] if response.text else 'None'}")
    
    # Invalid request type
    payload = {"type": "invalidType123"}
    response = requests.post(INFO_URL, json=payload, timeout=10)
    print(f"\nInvalid request type test:")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200] if response.text else 'None'}")
    
    # Malformed payload
    payload = {"type": "meta", "invalid": "field"}
    response = requests.post(INFO_URL, json=payload, timeout=10)
    print(f"\nMalformed payload test:")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        print(f"  ✅ Accepted (extra fields ignored)")
    else:
        print(f"  Response: {response.text[:200] if response.text else 'None'}")


def main():
    """Run all comprehensive tests."""
    print("\n" + "="*80)
    print("HYPERLIQUID TRADING API - COMPREHENSIVE TESTS")
    print("="*80)
    print("\nTesting all read-only endpoints (no authentication required)")
    print("="*80)
    
    # Run all tests
    test_meta_and_universe()
    test_perp_dexs()
    test_hip3_asset_id()
    test_market_context()
    test_orderbook()
    test_recent_trades()
    test_all_assets_metadata()
    test_error_handling()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print("\n✅ All read-only tests completed")
    print("\n⚠️  Next steps (require authentication):")
    print("  1. Set up agent wallet")
    print("  2. Test account info queries")
    print("  3. Test order placement (testnet)")
    print("  4. Test position management")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()



