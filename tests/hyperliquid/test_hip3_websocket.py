#!/usr/bin/env python3
"""
Hyperliquid HIP-3 WebSocket Test

Tests WebSocket subscriptions for HIP-3 markets using {dex}:{coin} format.

Run: python tests/hyperliquid/test_hip3_websocket.py
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import websockets  # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hyperliquid WebSocket URL
WS_URL = "wss://api.hyperliquid.xyz/ws"

# Test markets
TEST_MARKETS = [
    {"coin": "xyz:TSLA", "dex": "xyz", "description": "Tesla on XYZ DEX"},
    {"coin": "vntl:SPACEX", "dex": "vntl", "description": "SpaceX on Ventuals DEX"},
    {"coin": "xyz:AAPL", "dex": "xyz", "description": "Apple on XYZ DEX"},
    {"coin": "flx:TSLA", "dex": "flx", "description": "Tesla on Felix Exchange"},
]


class HIP3WebSocketTester:
    """Test HIP-3 market WebSocket subscriptions"""
    
    def __init__(self):
        self.ws_url = WS_URL
        self.results = {}
    
    async def test_market_subscription(self, market: Dict[str, Any], interval: str = "15m") -> Dict[str, Any]:
        """Test subscription to a HIP-3 market"""
        coin = market["coin"]
        description = market["description"]
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {coin} ({description})")
        logger.info(f"{'='*80}")
        
        result = {
            "coin": coin,
            "description": description,
            "interval": interval,
            "supported": False,
            "messages_received": 0,
            "message_samples": [],
            "errors": [],
        }
        
        try:
            async with websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                open_timeout=10,
                close_timeout=5,
            ) as ws:
                # Subscribe to candles
                subscribe_msg = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "candle",
                        "coin": coin,
                        "interval": interval,
                    },
                }
                
                await ws.send(json.dumps(subscribe_msg))
                logger.info(f"Sent subscription: {json.dumps(subscribe_msg, indent=2)}")
                
                # Wait for subscription confirmation or error
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(response)
                    logger.debug(f"Initial response: {json.dumps(data, indent=2)}")
                    
                    # Check for error
                    if isinstance(data, dict) and data.get("channel") == "error":
                        error_msg = data.get("data", "Unknown error")
                        result["errors"].append(error_msg)
                        logger.error(f"❌ Subscription error: {error_msg}")
                        return result
                    
                except asyncio.TimeoutError:
                    logger.warning("No initial response, waiting for candle data...")
                
                # Collect candle messages
                start_time = asyncio.get_event_loop().time()
                max_wait_time = 30.0  # Wait up to 30 seconds
                min_messages = 1  # Want at least 1 message
                
                logger.info(f"Collecting candle messages (up to {max_wait_time}s)...")
                
                while True:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    if elapsed >= max_wait_time:
                        logger.info(f"Reached max wait time ({max_wait_time}s)")
                        break
                    
                    if result["messages_received"] >= min_messages:
                        # Wait a bit more to see if we get another message
                        try:
                            extra_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            data = json.loads(extra_msg)
                            if self._is_candle_message(data):
                                result["messages_received"] += 1
                                result["message_samples"].append(self._extract_candle_info(data))
                        except asyncio.TimeoutError:
                            pass
                        break
                    
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        data = json.loads(message)
                        
                        if self._is_candle_message(data):
                            result["messages_received"] += 1
                            candle_info = self._extract_candle_info(data)
                            result["message_samples"].append(candle_info)
                            
                            logger.info(
                                f"  ✅ Candle #{result['messages_received']}: "
                                f"ts={candle_info.get('timestamp')}, "
                                f"o={candle_info.get('open')}, "
                                f"h={candle_info.get('high')}, "
                                f"l={candle_info.get('low')}, "
                                f"c={candle_info.get('close')}, "
                                f"v={candle_info.get('volume')}"
                            )
                        else:
                            logger.debug(f"  Non-candle message: {json.dumps(data)[:100]}")
                            
                    except asyncio.TimeoutError:
                        logger.warning(f"  Timeout waiting for message (elapsed: {elapsed:.1f}s)")
                        break
                
                if result["messages_received"] > 0:
                    result["supported"] = True
                    logger.info(f"\n✅ {coin}: SUPPORTED ({result['messages_received']} messages)")
                else:
                    logger.warning(f"\n⚠️  {coin}: No messages received")
                
        except Exception as e:
            logger.error(f"❌ Error testing {coin}: {e}")
            result["errors"].append(str(e))
            import traceback
            result["errors"].append(traceback.format_exc())
        
        return result
    
    def _is_candle_message(self, data: Dict[str, Any]) -> bool:
        """Check if message is a candle message"""
        if not isinstance(data, dict):
            return False
        
        if data.get("channel") == "candle":
            return True
        
        if "data" in data:
            data_obj = data["data"]
            if isinstance(data_obj, dict):
                ohlc_fields = ["o", "h", "l", "c", "open", "high", "low", "close"]
                if any(field in data_obj for field in ohlc_fields):
                    return True
        
        return False
    
    def _extract_candle_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract candle information from message"""
        if not isinstance(data, dict) or "data" not in data:
            return {}
        
        candle_data = data["data"]
        if not isinstance(candle_data, dict):
            return {}
        
        return {
            "timestamp": candle_data.get("t"),
            "end_timestamp": candle_data.get("T"),
            "symbol": candle_data.get("s"),
            "interval": candle_data.get("i"),
            "open": candle_data.get("o"),
            "high": candle_data.get("h"),
            "low": candle_data.get("l"),
            "close": candle_data.get("c"),
            "volume": candle_data.get("v"),
            "trades": candle_data.get("n"),
        }
    
    async def test_all_markets(self) -> Dict[str, Any]:
        """Test all HIP-3 markets"""
        logger.info("=" * 80)
        logger.info("HIP-3 WebSocket Subscription Test")
        logger.info("=" * 80)
        logger.info(f"Testing {len(TEST_MARKETS)} markets")
        logger.info("")
        
        all_results = {}
        
        for market in TEST_MARKETS:
            result = await self.test_market_subscription(market, interval="15m")
            all_results[market["coin"]] = result
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        supported = []
        not_supported = []
        
        for coin, result in all_results.items():
            if result["supported"]:
                supported.append(coin)
                logger.info(f"✅ {coin}: SUPPORTED ({result['messages_received']} messages)")
            else:
                not_supported.append(coin)
                logger.warning(f"❌ {coin}: NOT SUPPORTED")
                if result["errors"]:
                    logger.warning(f"   Errors: {result['errors']}")
        
        logger.info(f"\nSupported: {len(supported)}/{len(TEST_MARKETS)}")
        logger.info(f"  {', '.join(supported) if supported else 'None'}")
        
        if not_supported:
            logger.warning(f"\nNot supported: {', '.join(not_supported)}")
        
        return {
            "supported": supported,
            "not_supported": not_supported,
            "results": all_results,
        }


async def main():
    """Main test entry point"""
    tester = HIP3WebSocketTester()
    summary = await tester.test_all_markets()
    
    # Save results to file
    output_file = "tests/hyperliquid/hip3_websocket_test_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    return summary


if __name__ == "__main__":
    asyncio.run(main())

