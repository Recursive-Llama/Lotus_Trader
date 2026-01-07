#!/usr/bin/env python3
"""
Hyperliquid Candle Interval Test

Tests all candle intervals to verify they work:
- 1m, 5m, 15m, 1h, 4h, 1d

Run: python tests/hyperliquid/test_candle_intervals.py
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import websockets  # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hyperliquid WebSocket URL
WS_URL = "wss://api.hyperliquid.xyz/ws"

# Intervals to test
INTERVALS_TO_TEST = ["1m", "5m", "15m", "1h", "4h", "1d"]

# Test symbol
TEST_SYMBOL = "BTC"


class IntervalTester:
    """Test Hyperliquid candle intervals"""
    
    def __init__(self):
        self.ws_url = WS_URL
        self.results = {}
    
    async def test_interval(self, interval: str) -> Dict[str, Any]:
        """Test a single interval"""
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing interval: {interval}")
        logger.info(f"{'='*80}")
        
        result = {
            "interval": interval,
            "supported": False,
            "messages_received": 0,
            "message_samples": [],
            "errors": [],
            "test_duration_seconds": 0,
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
                        "coin": TEST_SYMBOL,
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
                
                # Collect candle messages for 60 seconds (or until we get a few)
                start_time = asyncio.get_event_loop().time()
                max_wait_time = 60.0  # Wait up to 60 seconds
                min_messages = 2  # Want at least 2 messages
                
                logger.info(f"Collecting candle messages (up to {max_wait_time}s or {min_messages} messages)...")
                
                while True:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    # Stop if we've waited too long
                    if elapsed >= max_wait_time:
                        logger.info(f"Reached max wait time ({max_wait_time}s)")
                        break
                    
                    # Stop if we have enough messages
                    if result["messages_received"] >= min_messages:
                        # For longer intervals (1h, 4h, 1d), we might not get 2 messages in 60s
                        # So wait a bit more if it's a short interval
                        if interval in ["1m", "5m", "15m"]:
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
                    
                    # Wait for message
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
                        # For longer intervals, this is expected
                        if interval in ["1h", "4h", "1d"]:
                            logger.info(f"  Expected timeout for {interval} interval (candles close less frequently)")
                            break
                        continue
                
                result["test_duration_seconds"] = asyncio.get_event_loop().time() - start_time
                
                if result["messages_received"] > 0:
                    result["supported"] = True
                    logger.info(f"\n✅ Interval {interval}: SUPPORTED")
                    logger.info(f"   Messages received: {result['messages_received']}")
                    logger.info(f"   Test duration: {result['test_duration_seconds']:.1f}s")
                else:
                    logger.warning(f"\n⚠️  Interval {interval}: No messages received")
                    logger.warning(f"   Test duration: {result['test_duration_seconds']:.1f}s")
                    logger.warning(f"   This might be normal for longer intervals (1h, 4h, 1d)")
                
        except Exception as e:
            logger.error(f"❌ Error testing interval {interval}: {e}")
            result["errors"].append(str(e))
        
        return result
    
    def _is_candle_message(self, data: Dict[str, Any]) -> bool:
        """Check if message is a candle message"""
        if not isinstance(data, dict):
            return False
        
        # Check channel
        if data.get("channel") == "candle":
            return True
        
        # Check for candle data structure
        if "data" in data:
            data_obj = data["data"]
            if isinstance(data_obj, dict):
                # Check for OHLC fields
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
    
    async def test_all_intervals(self) -> Dict[str, Any]:
        """Test all intervals"""
        logger.info("=" * 80)
        logger.info("Hyperliquid Candle Interval Test Suite")
        logger.info("=" * 80)
        logger.info(f"Testing intervals: {', '.join(INTERVALS_TO_TEST)}")
        logger.info(f"Test symbol: {TEST_SYMBOL}")
        logger.info("")
        
        all_results = {}
        
        for interval in INTERVALS_TO_TEST:
            result = await self.test_interval(interval)
            all_results[interval] = result
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        supported = []
        not_supported = []
        
        for interval, result in all_results.items():
            if result["supported"]:
                supported.append(interval)
                logger.info(f"✅ {interval}: SUPPORTED ({result['messages_received']} messages)")
            else:
                not_supported.append(interval)
                if result["messages_received"] == 0 and interval in ["1h", "4h", "1d"]:
                    logger.info(f"⚠️  {interval}: No messages (expected for longer intervals in short test)")
                else:
                    logger.warning(f"❌ {interval}: NOT SUPPORTED")
        
        logger.info(f"\nSupported intervals: {len(supported)}/{len(INTERVALS_TO_TEST)}")
        logger.info(f"  {', '.join(supported) if supported else 'None'}")
        
        if not_supported:
            logger.info(f"\nNot supported or no messages: {', '.join(not_supported)}")
            logger.info("  (For 1h, 4h, 1d: No messages might be normal - candles close less frequently)")
        
        return {
            "supported": supported,
            "not_supported": not_supported,
            "results": all_results,
        }


async def main():
    """Main test entry point"""
    tester = IntervalTester()
    summary = await tester.test_all_intervals()
    
    # Save results to file
    output_file = "tests/hyperliquid/interval_test_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    return summary


if __name__ == "__main__":
    asyncio.run(main())

