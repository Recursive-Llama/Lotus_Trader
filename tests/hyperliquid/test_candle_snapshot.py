#!/usr/bin/env python3
"""
Test Hyperliquid candleSnapshot Endpoint

Tests different formats to find the correct API structure.

Run: python tests/hyperliquid/test_candle_snapshot.py
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

URL = "https://api.hyperliquid.xyz/info"

# Test different formats based on Hyperliquid API patterns
TEST_FORMATS = [
    # Format 1: Direct fields
    {"type": "candleSnapshot", "coin": "BTC", "interval": "15m", "n": 100},
    
    # Format 2: Nested req
    {"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "15m", "n": 100}},
    
    # Format 3: Array format (like some Hyperliquid endpoints)
    {"type": "candleSnapshot", "coin": "BTC", "interval": "15m", "n": 100, "startTime": None},
    
    # Format 4: With startTime as timestamp
    {"type": "candleSnapshot", "coin": "BTC", "interval": "15m", "n": 100, "startTime": 0},
    
    # Format 5: Different field names
    {"type": "candleSnapshot", "symbol": "BTC", "timeframe": "15m", "limit": 100},
    
    # Format 6: Check if it's a GET endpoint
    None,  # Will test GET separately
]

def test_get_endpoint():
    """Test if candleSnapshot is a GET endpoint"""
    logger.info("\nTesting GET endpoint...")
    try:
        response = requests.get(
            f"{URL}?type=candleSnapshot&coin=BTC&interval=15m&n=100",
            timeout=10
        )
        logger.info(f"GET Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ GET works! Got {len(data) if isinstance(data, list) else 'dict'} response")
            return True
    except Exception as e:
        logger.info(f"GET failed: {e}")
    return False

def main():
    logger.info("=" * 80)
    logger.info("Hyperliquid candleSnapshot Format Test")
    logger.info("=" * 80)
    
    # Test GET first
    if test_get_endpoint():
        logger.info("\n✅ Found working format: GET endpoint")
        return
    
    # Test POST formats
    for i, test_format in enumerate(TEST_FORMATS, 1):
        if test_format is None:
            continue
            
        logger.info(f"\nTest {i}: {json.dumps(test_format)}")
        try:
            response = requests.post(URL, json=test_format, timeout=10)
            logger.info(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    logger.info(f"   ✅ SUCCESS: Got {len(data)} candles")
                    logger.info(f"   First: {data[0]}")
                    logger.info(f"   Last: {data[-1]}")
                    logger.info(f"\n✅ Found working format!")
                    return
                elif isinstance(data, dict):
                    logger.info(f"   Response (dict): {json.dumps(data, indent=2)[:300]}")
                else:
                    logger.info(f"   Format: {type(data)}")
            else:
                logger.info(f"   Error: {response.text[:200]}")
        except Exception as e:
            logger.info(f"   Exception: {e}")
    
    logger.info("\n❌ No working format found. Need to check Hyperliquid docs.")

if __name__ == "__main__":
    main()

