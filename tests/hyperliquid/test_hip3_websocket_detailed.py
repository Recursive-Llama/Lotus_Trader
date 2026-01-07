#!/usr/bin/env python3
"""
Hyperliquid HIP-3 WebSocket Test - Detailed

Tests with longer waits and checks for error messages.

Run: python tests/hyperliquid/test_hip3_websocket_detailed.py
"""

import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import websockets

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WS_URL = "wss://api.hyperliquid.xyz/ws"

# Test markets that didn't work
TEST_MARKETS = [
    {"coin": "xyz:TSLA", "description": "Tesla on XYZ DEX"},
    {"coin": "vntl:SPACEX", "description": "SpaceX on Ventuals DEX"},
    {"coin": "flx:TSLA", "description": "Tesla on Felix Exchange"},
]


async def test_market_detailed(coin: str, description: str, interval: str = "15m", wait_time: int = 60):
    """Test with detailed logging and longer wait"""
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing: {coin} ({description})")
    logger.info(f"Interval: {interval}, Wait time: {wait_time}s")
    logger.info(f"{'='*80}")
    
    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10, open_timeout=10) as ws:
            # Subscribe
            subscribe_msg = {
                "method": "subscribe",
                "subscription": {
                    "type": "candle",
                    "coin": coin,
                    "interval": interval,
                },
            }
            
            await ws.send(json.dumps(subscribe_msg))
            logger.info(f"Sent: {json.dumps(subscribe_msg)}")
            
            # Wait for any response
            messages_received = 0
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < wait_time:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(message)
                    messages_received += 1
                    
                    logger.info(f"\nMessage #{messages_received}:")
                    logger.info(json.dumps(data, indent=2))
                    
                    # Check for errors
                    if isinstance(data, dict):
                        if data.get("channel") == "error":
                            logger.error(f"❌ Error: {data.get('data')}")
                            return False
                        elif data.get("channel") == "candle":
                            logger.info(f"✅ Candle message received!")
                            return True
                    
                except asyncio.TimeoutError:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed < 10:
                        continue
                    logger.warning(f"No messages after {elapsed:.1f}s...")
                    # Try different interval
                    if interval == "15m" and elapsed > 30:
                        logger.info("Trying 1h interval...")
                        subscribe_msg_1h = {
                            "method": "subscribe",
                            "subscription": {
                                "type": "candle",
                                "coin": coin,
                                "interval": "1h",
                            },
                        }
                        await ws.send(json.dumps(subscribe_msg_1h))
                        logger.info(f"Sent 1h subscription: {json.dumps(subscribe_msg_1h)}")
            
            if messages_received == 0:
                logger.warning(f"⚠️  No messages received after {wait_time}s")
                logger.warning("Possible reasons:")
                logger.warning("  - Market might be inactive (no recent trades)")
                logger.warning("  - Market might be delisted")
                logger.warning("  - Market might need different interval")
                return False
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    logger.info("=" * 80)
    logger.info("HIP-3 WebSocket Detailed Test")
    logger.info("=" * 80)
    
    results = {}
    
    for market in TEST_MARKETS:
        coin = market["coin"]
        description = market["description"]
        
        # Test with 15m first, then try 1h if no messages
        result_15m = await test_market_detailed(coin, description, "15m", wait_time=60)
        results[f"{coin}_15m"] = result_15m
        
        if not result_15m:
            logger.info(f"\nTrying 1h interval for {coin}...")
            result_1h = await test_market_detailed(coin, description, "1h", wait_time=30)
            results[f"{coin}_1h"] = result_1h
        
        await asyncio.sleep(2)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    
    for key, result in results.items():
        status = "✅ SUPPORTED" if result else "❌ NOT SUPPORTED"
        logger.info(f"{key}: {status}")


if __name__ == "__main__":
    asyncio.run(main())

