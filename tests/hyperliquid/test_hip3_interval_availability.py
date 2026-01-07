#!/usr/bin/env python3
"""
Test HIP-3 Market Interval Availability

Tests whether 15m candles are unavailable or just inactive during test window.
Checks by waiting longer and trying to get current candle state.

Run: python tests/hyperliquid/test_hip3_interval_availability.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import websockets
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WS_URL = "wss://api.hyperliquid.xyz/ws"
REST_URL = "https://api.hyperliquid.xyz/info"

# Markets that didn't get 15m candles
TEST_MARKETS = [
    {"coin": "vntl:SPACEX", "dex": "vntl", "description": "SpaceX on Ventuals"},
    {"coin": "flx:TSLA", "dex": "flx", "description": "Tesla on Felix Exchange"},
]


async def test_interval_availability(coin: str, dex: str, description: str):
    """Test if 15m interval is available or just inactive"""
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing: {coin} ({description})")
    logger.info(f"{'='*80}")
    
    # First, check if we can get market data via REST to see if market is active
    logger.info("\nStep 1: Checking market status via REST API...")
    try:
        # Try to get market data
        response = requests.post(REST_URL, json={"type": "metaAndAssetCtxs", "dex": dex}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Look for this coin in asset contexts
            asset_ctxs = data.get("assetContexts", {})
            logger.info(f"Found {len(asset_ctxs)} asset contexts")
            
            # Check if our coin exists
            for asset_id, ctx in asset_ctxs.items():
                # We'd need to compute asset ID, but let's just check if market exists
                pass
    except Exception as e:
        logger.warning(f"Could not check REST API: {e}")
    
    # Test 1: Subscribe and wait for a full 15m period (or at least 5 minutes)
    logger.info("\nStep 2: Subscribing to 15m candles and waiting 5+ minutes...")
    logger.info("This will tell us if 15m candles exist but just need time to close")
    
    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10, open_timeout=10) as ws:
            # Subscribe to 15m
            subscribe_msg = {
                "method": "subscribe",
                "subscription": {
                    "type": "candle",
                    "coin": coin,
                    "interval": "15m",
                },
            }
            
            await ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to 15m candles for {coin}")
            
            # Wait for subscription confirmation
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                if data.get("channel") == "subscriptionResponse":
                    logger.info("✅ Subscription confirmed")
                elif data.get("channel") == "error":
                    logger.error(f"❌ Subscription error: {data.get('data')}")
                    return False
            except asyncio.TimeoutError:
                logger.warning("No subscription confirmation")
            
            # Wait up to 6 minutes (longer than a 15m candle period)
            # This will catch a candle if it closes during our wait
            wait_time = 360  # 6 minutes
            start_time = time.time()
            messages_received = 0
            last_message_time = None
            
            logger.info(f"Waiting up to {wait_time}s for 15m candles...")
            logger.info("(A 15m candle closes every 15 minutes, so we might need to wait)")
            
            while (time.time() - start_time) < wait_time:
                elapsed = time.time() - start_time
                
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(message)
                    messages_received += 1
                    last_message_time = time.time()
                    
                    if data.get("channel") == "candle":
                        candle_data = data.get("data", {})
                        logger.info(f"\n✅ Received 15m candle after {elapsed:.1f}s:")
                        logger.info(f"   Timestamp: {candle_data.get('t')}")
                        logger.info(f"   Symbol: {candle_data.get('s')}")
                        logger.info(f"   Interval: {candle_data.get('i')}")
                        logger.info(f"   OHLC: O={candle_data.get('o')}, H={candle_data.get('h')}, L={candle_data.get('l')}, C={candle_data.get('c')}")
                        logger.info(f"   Volume: {candle_data.get('v')}")
                        return True
                    elif data.get("channel") == "error":
                        logger.error(f"❌ Error: {data.get('data')}")
                        return False
                    else:
                        logger.debug(f"Other message: {data.get('channel')}")
                        
                except asyncio.TimeoutError:
                    elapsed = time.time() - start_time
                    if elapsed % 30 < 5:  # Log every 30 seconds
                        logger.info(f"  Waiting... {elapsed:.0f}s elapsed, {messages_received} messages received")
            
            if messages_received == 0:
                logger.warning(f"\n⚠️  No 15m candles received after {wait_time}s")
                logger.warning("Possible reasons:")
                logger.warning("  1. Market is inactive (no trades)")
                logger.warning("  2. 15m interval not supported for this market")
                logger.warning("  3. Need to wait for next 15m candle close (could be up to 15 minutes)")
                return False
            else:
                logger.info(f"Received {messages_received} messages, but no candle data")
                return False
                
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_1h_for_comparison(coin: str):
    """Test 1h interval to confirm market is active"""
    logger.info(f"\nStep 3: Testing 1h interval for comparison...")
    
    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10, open_timeout=10) as ws:
            subscribe_msg = {
                "method": "subscribe",
                "subscription": {
                    "type": "candle",
                    "coin": coin,
                    "interval": "1h",
                },
            }
            
            await ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to 1h candles for {coin}")
            
            # Wait up to 2 minutes for 1h candle
            wait_time = 120
            start_time = time.time()
            
            while (time.time() - start_time) < wait_time:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(message)
                    
                    if data.get("channel") == "candle":
                        candle_data = data.get("data", {})
                        interval = candle_data.get("i")
                        if interval == "1h":
                            logger.info(f"✅ Received 1h candle (confirms market is active)")
                            return True
                except asyncio.TimeoutError:
                    pass
            
            logger.warning("No 1h candle received (market might be inactive)")
            return False
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


async def main():
    logger.info("=" * 80)
    logger.info("HIP-3 Interval Availability Test")
    logger.info("=" * 80)
    logger.info("Testing whether 15m candles are unavailable or just inactive")
    logger.info("")
    
    results = {}
    
    for market in TEST_MARKETS:
        coin = market["coin"]
        dex = market["dex"]
        description = market["description"]
        
        # Test 15m with long wait
        result_15m = await test_interval_availability(coin, dex, description)
        results[f"{coin}_15m"] = result_15m
        
        # Test 1h for comparison
        result_1h = await test_1h_for_comparison(coin)
        results[f"{coin}_1h"] = result_1h
        
        await asyncio.sleep(2)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    
    for key, result in results.items():
        status = "✅ AVAILABLE" if result else "❌ NOT AVAILABLE/INACTIVE"
        logger.info(f"{key}: {status}")


if __name__ == "__main__":
    asyncio.run(main())

