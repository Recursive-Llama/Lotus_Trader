"""
Test Hyperliquid Trading API

This script explores the Hyperliquid trading API to understand:
1. Authentication requirements
2. Order placement format
3. Asset ID computation
4. Position management
5. Constraints and error handling

Run with: python tests/hyperliquid/test_trading_api.py
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Hyperliquid API endpoints
INFO_URL = "https://api.hyperliquid.xyz/info"
EXCHANGE_URL = "https://api.hyperliquid.xyz/exchange"

# Test symbols
TEST_MAIN_DEX = "BTC"  # Main DEX token
TEST_HIP3 = "xyz:TSLA"  # HIP-3 token


def test_info_endpoint() -> Dict[str, Any]:
    """Test /info endpoint - query account info, positions, etc."""
    print("\n" + "="*80)
    print("TEST 1: Info Endpoint - Query Account Info")
    print("="*80)
    
    # Test querying meta (to understand asset structure)
    payload = {
        "type": "meta"
    }
    
    try:
        response = requests.post(INFO_URL, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Got meta data")
            print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Look for asset info
            if isinstance(data, dict):
                if "universe" in data:
                    print(f"\nUniverse (first 5):")
                    for i, asset in enumerate(data["universe"][:5]):
                        print(f"  {i}: {asset}")
                
                if "perpDexs" in data:
                    print(f"\nPerpDexs: {data['perpDexs']}")
            
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return {}
    except Exception as e:
        print(f"❌ Exception: {e}")
        return {}


def test_asset_id_computation() -> None:
    """Test computing asset IDs for main DEX and HIP-3 tokens."""
    print("\n" + "="*80)
    print("TEST 2: Asset ID Computation")
    print("="*80)
    
    # Get meta data
    payload = {"type": "meta"}
    response = requests.post(INFO_URL, json=payload, timeout=10)
    
    if response.status_code != 200:
        print("❌ Failed to get meta data")
        return
    
    meta = response.json()
    
    # Test main DEX asset ID
    print(f"\nMain DEX Token: {TEST_MAIN_DEX}")
    if "universe" in meta:
        for i, asset in enumerate(meta["universe"]):
            if asset.get("name") == TEST_MAIN_DEX:
                print(f"  ✅ Found at index {i}")
                print(f"  Asset ID: {i}")
                print(f"  Asset data: {json.dumps(asset, indent=2)[:200]}")
                print(f"  Max Leverage: {asset.get('maxLeverage')}")
                print(f"  Size Decimals: {asset.get('szDecimals')}")
                break
        else:
            print(f"  ❌ {TEST_MAIN_DEX} not found in universe")
    
    # Test HIP-3 asset ID - need to query perpDexs first
    print(f"\nHIP-3 Token: {TEST_HIP3}")
    if ":" in TEST_HIP3:
        dex_name, coin = TEST_HIP3.split(":", 1)
        print(f"  DEX: {dex_name}, Coin: {coin}")
        
        # First, get perpDexs list
        perp_dex_payload = {"type": "perpDexs"}
        perp_dex_response = requests.post(INFO_URL, json=perp_dex_payload, timeout=10)
        
        if perp_dex_response.status_code == 200:
            perp_dexs = perp_dex_response.json()
            print(f"  ✅ Got {len(perp_dexs)} perpDexs")
            
            # Find dex index
            dex_index = None
            for i, dex in enumerate(perp_dexs):
                if isinstance(dex, dict) and dex.get("name") == dex_name:
                    dex_index = i
                    print(f"  ✅ Found DEX '{dex_name}' at index {dex_index}")
                    break
                elif isinstance(dex, str) and dex == dex_name:
                    dex_index = i
                    print(f"  ✅ Found DEX '{dex_name}' at index {dex_index}")
                    break
            
            if dex_index is not None:
                # Query meta for this DEX
                dex_payload = {"type": "meta", "dex": dex_name}
                dex_response = requests.post(INFO_URL, json=dex_payload, timeout=10)
                
                if dex_response.status_code == 200:
                    dex_meta = dex_response.json()
                    if "universe" in dex_meta:
                        print(f"  ✅ DEX universe has {len(dex_meta['universe'])} assets")
                        # HIP-3 tokens use full format "dex:coin" in universe
                        full_token_name = f"{dex_name}:{coin}"
                        for j, asset in enumerate(dex_meta["universe"]):
                            asset_name = asset.get("name", "")
                            # Check both full format and coin-only
                            if asset_name == full_token_name or asset_name == coin:
                                print(f"  ✅ Found coin '{asset_name}' at index {j} in DEX universe")
                                # HIP-3 asset ID formula: 100000 + dex_index * 10000 + coin_index
                                asset_id = 100000 + dex_index * 10000 + j
                                print(f"  Asset ID: {asset_id}")
                                print(f"  Formula: 100000 + {dex_index} * 10000 + {j} = {asset_id}")
                                print(f"  Asset data: {json.dumps(asset, indent=2)[:200]}")
                                if "maxLeverage" in asset:
                                    print(f"  Max Leverage: {asset.get('maxLeverage')}")
                                if "szDecimals" in asset:
                                    print(f"  Size Decimals: {asset.get('szDecimals')}")
                                break
                        else:
                            print(f"  ❌ Coin '{coin}' or '{full_token_name}' not found in DEX universe")
                            print(f"  Available coins (first 5): {[a.get('name') for a in dex_meta['universe'][:5]]}")
                    else:
                        print(f"  ❌ No 'universe' in DEX meta response")
                else:
                    print(f"  ❌ Failed to get DEX meta: {dex_response.status_code}")
                    print(f"  Response: {dex_response.text[:200]}")
            else:
                print(f"  ❌ DEX '{dex_name}' not found in perpDexs")
                print(f"  Available DEXs (first 10): {[d.get('name') if isinstance(d, dict) else d for d in perp_dexs[:10]]}")
        else:
            print(f"  ❌ Failed to get perpDexs: {perp_dex_response.status_code}")


def test_account_info() -> None:
    """Test querying account info (balance, positions)."""
    print("\n" + "="*80)
    print("TEST 3: Account Info (Requires Auth)")
    print("="*80)
    
    # Note: This likely requires wallet signature
    # We'll document what's needed
    
    print("⚠️  Account info queries typically require authentication")
    print("   Check Hyperliquid docs for auth requirements:")
    print("   - Wallet signature?")
    print("   - API key?")
    print("   - Other auth method?")
    
    # Try to see what endpoint structure looks like
    # (This will likely fail without auth, but shows what's needed)
    payload = {
        "type": "clearinghouseState",
        "user": "0x..."  # Placeholder
    }
    
    print(f"\nExample payload structure:")
    print(json.dumps(payload, indent=2))


def test_order_placement() -> None:
    """Test order placement format (dry-run if possible)."""
    print("\n" + "="*80)
    print("TEST 4: Order Placement Format")
    print("="*80)
    
    print("⚠️  Order placement requires authentication")
    print("   Documenting expected format based on Hyperliquid docs")
    
    # Expected order format (based on typical perpetual exchange APIs)
    example_order = {
        "action": {
            "type": "order",
            "orders": [
                {
                    "a": 0,  # Asset ID (computed)
                    "b": True,  # Buy (True) or Sell (False)
                    "p": "100000",  # Price (string, for limit orders)
                    "s": "0.1",  # Size (string, contract size)
                    "r": False,  # Reduce-only
                    "t": {"limit": {"tif": "Gtc"}},  # Order type (limit with time-in-force)
                }
            ],
            "grouping": "na"  # Order grouping
        },
        "nonce": 1234567890,  # Nonce
        "signature": {
            "r": "0x...",
            "s": "0x...",
            "v": 27
        }
    }
    
    print("\nExpected order format:")
    print(json.dumps(example_order, indent=2))
    
    print("\n⚠️  Need to verify:")
    print("   - Exact field names")
    print("   - Asset ID format")
    print("   - Size format (contracts vs notional USD)")
    print("   - Signature format")
    print("   - Nonce generation")


def test_position_queries() -> None:
    """Test querying positions."""
    print("\n" + "="*80)
    print("TEST 5: Position Queries")
    print("="*80)
    
    print("⚠️  Position queries require authentication")
    
    # Expected query format
    payload = {
        "type": "clearinghouseState",
        "user": "0x..."  # Wallet address
    }
    
    print("\nExpected query format:")
    print(json.dumps(payload, indent=2))
    
    print("\n⚠️  Need to verify:")
    print("   - Endpoint for position queries")
    print("   - Response format")
    print("   - Position fields (size, entry price, PnL, etc.)")


def test_error_cases() -> None:
    """Test error handling."""
    print("\n" + "="*80)
    print("TEST 6: Error Handling")
    print("="*80)
    
    print("Testing invalid requests to understand error formats...")
    
    # Test invalid asset ID
    invalid_payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "INVALID_TOKEN_XYZ",
            "interval": "15m",
            "startTime": 1000000000000,
            "endTime": 2000000000000
        }
    }
    
    try:
        response = requests.post(INFO_URL, json=invalid_payload, timeout=10)
        print(f"\nInvalid coin test:")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Exception: {e}")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("HYPERLIQUID TRADING API EXPLORATION")
    print("="*80)
    print("\nThis script explores the Hyperliquid trading API structure.")
    print("Some tests require authentication and may fail.")
    print("\nGoal: Understand API structure before implementation.")
    
    # Run tests
    test_info_endpoint()
    test_asset_id_computation()
    test_account_info()
    test_order_placement()
    test_position_queries()
    test_error_cases()
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. Review Hyperliquid docs for exact API format")
    print("2. Set up authentication (wallet signature?)")
    print("3. Test with small amounts (or testnet if available)")
    print("4. Document findings in hyperliquid_trading_api_findings.md")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()

