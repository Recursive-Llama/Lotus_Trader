#!/usr/bin/env python3
"""
Hyperliquid Candle Subscription Test

Tests whether Hyperliquid WebSocket supports candle/OHLC subscriptions,
and whether REST API provides candle endpoints.

Run: python tests/hyperliquid/test_candle_subscriptions.py
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
import requests  # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hyperliquid endpoints
WS_URL = "wss://api.hyperliquid.xyz/ws"
REST_BASE_URL = "https://api.hyperliquid.xyz"

# Test symbols
TEST_SYMBOLS = ["BTC", "ETH", "SOL"]


class HyperliquidCandleTester:
    """Test Hyperliquid for candle/OHLC data availability"""
    
    def __init__(self):
        self.ws_url = WS_URL
        self.rest_base = REST_BASE_URL
        self.test_results = {
            "websocket_candles": None,
            "rest_candles": None,
            "subscription_formats": [],
            "message_formats": [],
            "rate_limits": {},
        }
    
    # ============================================================================
    # Test 1: WebSocket Candle Subscriptions
    # ============================================================================
    
    async def test_websocket_candle_subscriptions(self) -> Dict[str, Any]:
        """Test if Hyperliquid WS supports candle subscriptions"""
        logger.info("=" * 80)
        logger.info("TEST 1: WebSocket Candle Subscriptions")
        logger.info("=" * 80)
        
        results = {
            "supported": False,
            "subscription_formats": [],
            "message_formats": [],
            "available_intervals": [],
            "errors": [],
        }
        
        # Try different subscription formats
        subscription_formats = [
            {"type": "candle", "coin": "BTC", "interval": "1m"},
            {"type": "candles", "coin": "BTC", "interval": "1m"},
            {"type": "interval", "coin": "BTC", "interval": "1m"},
            {"type": "ohlc", "coin": "BTC", "interval": "1m"},
            {"type": "candle", "coin": "BTC", "timeframe": "1m"},
            {"type": "candle", "symbol": "BTC", "interval": "1m"},
        ]
        
        # Try different intervals
        intervals_to_test = ["1m", "5m", "15m", "1h", "4h", "1d"]
        
        for sub_format in subscription_formats:
            for interval in intervals_to_test:
                sub_format_copy = sub_format.copy()
                sub_format_copy["interval"] = interval
                
                logger.info(f"\nTrying subscription format: {sub_format_copy}")
                
                try:
                    result = await self._test_single_candle_subscription(sub_format_copy)
                    if result["success"]:
                        results["supported"] = True
                        results["subscription_formats"].append(sub_format_copy)
                        results["message_formats"].append(result["message_format"])
                        if interval not in results["available_intervals"]:
                            results["available_intervals"].append(interval)
                        logger.info(f"✅ SUCCESS with format: {sub_format_copy}")
                        logger.info(f"   Message format: {result['message_format']}")
                        break  # Found working format, try next interval
                    else:
                        results["errors"].append(f"{sub_format_copy}: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    logger.error(f"❌ Error testing {sub_format_copy}: {e}")
                    results["errors"].append(f"{sub_format_copy}: {str(e)}")
        
        self.test_results["websocket_candles"] = results
        return results
    
    async def _test_single_candle_subscription(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single subscription format"""
        try:
            async with websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                open_timeout=10,
                close_timeout=5,
            ) as ws:
                # Send subscription
                subscribe_msg = {
                    "method": "subscribe",
                    "subscription": subscription,
                }
                
                await ws.send(json.dumps(subscribe_msg))
                logger.debug(f"Sent: {json.dumps(subscribe_msg, indent=2)}")
                
                # Wait for response (success or error)
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(response)
                    logger.debug(f"Received: {json.dumps(data, indent=2)}")
                    
                    # Check if it's an error
                    if "error" in data or "Error" in str(data):
                        return {
                            "success": False,
                            "error": data.get("error", str(data)),
                            "message_format": None,
                        }
                    
                    # Check if it's a candle message
                    if self._is_candle_message(data):
                        # Wait for actual candle data
                        candle_data = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        candle = json.loads(candle_data)
                        logger.debug(f"Candle data: {json.dumps(candle, indent=2)}")
                        
                        return {
                            "success": True,
                            "message_format": self._extract_message_format(candle),
                            "error": None,
                        }
                    
                    # Check if subscription was accepted (might need to wait for data)
                    if "subscribed" in str(data).lower() or "success" in str(data).lower():
                        # Wait a bit for candle data
                        try:
                            candle_data = await asyncio.wait_for(ws.recv(), timeout=10.0)
                            candle = json.loads(candle_data)
                            if self._is_candle_message(candle):
                                return {
                                    "success": True,
                                    "message_format": self._extract_message_format(candle),
                                    "error": None,
                                }
                        except asyncio.TimeoutError:
                            return {
                                "success": False,
                                "error": "Subscription accepted but no candle data received",
                                "message_format": None,
                            }
                    
                    return {
                        "success": False,
                        "error": f"Unexpected response: {data}",
                        "message_format": None,
                    }
                    
                except asyncio.TimeoutError:
                    return {
                        "success": False,
                        "error": "Timeout waiting for response",
                        "message_format": None,
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message_format": None,
            }
    
    def _is_candle_message(self, data: Dict[str, Any]) -> bool:
        """Check if message is a candle/OHLC message"""
        if not isinstance(data, dict):
            return False
        
        # Check for candle indicators
        candle_indicators = ["candle", "candles", "ohlc", "interval", "bar", "bars"]
        data_str = json.dumps(data).lower()
        
        # Check channel
        if "channel" in data:
            channel = str(data["channel"]).lower()
            if any(indicator in channel for indicator in candle_indicators):
                return True
        
        # Check keys
        keys = [str(k).lower() for k in data.keys()]
        if any(indicator in " ".join(keys) for indicator in candle_indicators):
            return True
        
        # Check for OHLC fields
        ohlc_fields = ["open", "high", "low", "close", "o", "h", "l", "c"]
        if any(field in data_str for field in ohlc_fields):
            # Make sure it's not just a trade (trades have price, not OHLC)
            if "price" in data_str and not any(field in data_str for field in ["open", "high", "low"]):
                return False
            return True
        
        return False
    
    def _extract_message_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message format structure"""
        format_info = {
            "channel": data.get("channel"),
            "keys": list(data.keys()),
            "data_structure": None,
        }
        
        if "data" in data:
            format_info["data_structure"] = list(data["data"].keys()) if isinstance(data["data"], dict) else type(data["data"]).__name__
        
        return format_info
    
    # ============================================================================
    # Test 2: REST API Candle Endpoints
    # ============================================================================
    
    def test_rest_candle_endpoints(self) -> Dict[str, Any]:
        """Test Hyperliquid REST API for candle/OHLC endpoints"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 2: REST API Candle Endpoints")
        logger.info("=" * 80)
        
        results = {
            "endpoints_found": [],
            "endpoints_tested": [],
            "rate_limits": {},
            "available_intervals": [],
            "errors": [],
        }
        
        # Common endpoint patterns
        endpoints_to_try = [
            "/info",
            "/candles",
            "/ohlc",
            "/klines",
            "/bars",
            "/candle",
            "/v1/candles",
            "/v1/ohlc",
            "/api/v1/candles",
            "/api/v1/klines",
        ]
        
        # Common parameter patterns
        param_patterns = [
            {"symbol": "BTC", "interval": "1m", "limit": 10},
            {"coin": "BTC", "interval": "1m", "limit": 10},
            {"pair": "BTC", "timeframe": "1m", "limit": 10},
            {"market": "BTC", "period": "1m", "limit": 10},
        ]
        
        for endpoint in endpoints_to_try:
            for params in param_patterns:
                url = f"{self.rest_base}{endpoint}"
                results["endpoints_tested"].append(f"{endpoint} with {params}")
                
                logger.info(f"\nTesting: {url}")
                logger.info(f"  Params: {params}")
                
                try:
                    response = requests.get(url, params=params, timeout=5)
                    logger.info(f"  Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.debug(f"  Response: {json.dumps(data, indent=2)[:500]}")
                            
                            # Check if it looks like candle data
                            if self._is_candle_response(data):
                                results["endpoints_found"].append({
                                    "endpoint": endpoint,
                                    "params": params,
                                    "response_structure": self._extract_response_structure(data),
                                })
                                logger.info(f"  ✅ Found candle endpoint: {endpoint}")
                                
                                # Extract intervals if available
                                if isinstance(data, list) and len(data) > 0:
                                    # Check if interval is in response
                                    if "interval" in str(data):
                                        results["available_intervals"].append("1m")  # At least this one works
                                
                                break  # Found working endpoint, try next
                            else:
                                logger.debug(f"  Response doesn't look like candle data")
                        except json.JSONDecodeError:
                            logger.debug(f"  Response is not JSON")
                    elif response.status_code == 404:
                        logger.debug(f"  404 - Endpoint not found")
                    else:
                        logger.debug(f"  Status {response.status_code}: {response.text[:200]}")
                        
                except requests.exceptions.RequestException as e:
                    logger.debug(f"  Error: {e}")
                    results["errors"].append(f"{endpoint}: {str(e)}")
        
        # Check rate limits (if we found an endpoint)
        if results["endpoints_found"]:
            rate_limit_info = self._test_rate_limits(results["endpoints_found"][0])
            results["rate_limits"] = rate_limit_info
        
        self.test_results["rest_candles"] = results
        return results
    
    def _is_candle_response(self, data: Any) -> bool:
        """Check if REST response is candle/OHLC data"""
        if isinstance(data, list):
            if len(data) == 0:
                return False
            # Check first item
            first = data[0]
            if isinstance(first, (list, tuple)) and len(first) >= 4:
                # Common candle format: [timestamp, open, high, low, close, volume]
                return True
            elif isinstance(first, dict):
                # Check for OHLC fields
                ohlc_fields = ["open", "high", "low", "close", "o", "h", "l", "c"]
                if any(field in first for field in ohlc_fields):
                    return True
        
        elif isinstance(data, dict):
            # Check for candle indicators
            if "candles" in data or "ohlc" in data or "bars" in data or "klines" in data:
                return True
            # Check for OHLC fields directly
            ohlc_fields = ["open", "high", "low", "close", "o", "h", "l", "c"]
            if any(field in data for field in ohlc_fields):
                return True
        
        return False
    
    def _extract_response_structure(self, data: Any) -> Dict[str, Any]:
        """Extract response structure"""
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, (list, tuple)):
                return {
                    "type": "array_of_arrays",
                    "length": len(first),
                    "sample": first[:6] if len(first) >= 6 else first,
                }
            elif isinstance(first, dict):
                return {
                    "type": "array_of_objects",
                    "keys": list(first.keys()),
                    "sample": first,
                }
        
        elif isinstance(data, dict):
            return {
                "type": "object",
                "keys": list(data.keys()),
                "sample": {k: str(v)[:50] for k, v in list(data.items())[:5]},
            }
        
        return {"type": "unknown", "data": str(data)[:100]}
    
    def _test_rate_limits(self, endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
        """Test rate limits for REST endpoint"""
        logger.info(f"\nTesting rate limits for {endpoint_info['endpoint']}")
        
        endpoint = endpoint_info["endpoint"]
        params = endpoint_info["params"]
        url = f"{self.rest_base}{endpoint}"
        
        # Make multiple rapid requests
        success_count = 0
        rate_limit_hit = False
        
        for i in range(10):
            try:
                response = requests.get(url, params=params, timeout=2)
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:  # Rate limit
                    rate_limit_hit = True
                    logger.info(f"  Rate limit hit at request {i+1}")
                    break
                elif response.status_code == 403:
                    rate_limit_hit = True
                    logger.info(f"  403 Forbidden at request {i+1} (possible rate limit)")
                    break
            except Exception as e:
                logger.debug(f"  Request {i+1} failed: {e}")
        
        return {
            "successful_requests": success_count,
            "rate_limit_hit": rate_limit_hit,
            "estimated_limit": f">={success_count} requests" if not rate_limit_hit else f"<{success_count} requests",
        }
    
    # ============================================================================
    # Test 3: Compare Trades vs Candles (if candles available)
    # ============================================================================
    
    async def test_message_volume_comparison(self) -> Dict[str, Any]:
        """Compare message volume between trades and candles"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 3: Message Volume Comparison (Trades vs Candles)")
        logger.info("=" * 80)
        
        results = {
            "trades_volume": None,
            "candles_volume": None,
            "comparison": None,
        }
        
        # Test trades subscription
        logger.info("\nTesting trades subscription message volume...")
        trades_count = await self._count_messages_for_duration("trades", duration_seconds=30)
        results["trades_volume"] = {
            "messages_per_30s": trades_count,
            "estimated_per_minute": trades_count * 2,
        }
        logger.info(f"  Trades: {trades_count} messages in 30s (~{trades_count * 2}/min)")
        
        # Test candles subscription (if available)
        if self.test_results["websocket_candles"] and self.test_results["websocket_candles"]["supported"]:
            logger.info("\nTesting candles subscription message volume...")
            candles_count = await self._count_messages_for_duration("candles", duration_seconds=30)
            results["candles_volume"] = {
                "messages_per_30s": candles_count,
                "estimated_per_minute": candles_count * 2,
            }
            logger.info(f"  Candles: {candles_count} messages in 30s (~{candles_count * 2}/min)")
            
            # Comparison
            if trades_count > 0:
                ratio = trades_count / max(candles_count, 1)
                results["comparison"] = {
                    "trades_to_candles_ratio": ratio,
                    "reduction_pct": (1 - (candles_count / trades_count)) * 100 if trades_count > 0 else 0,
                }
                logger.info(f"  Ratio: {ratio:.1f}x more trades than candles")
                logger.info(f"  Reduction: {(1 - (candles_count / trades_count)) * 100:.1f}% fewer messages with candles")
        
        return results
    
    async def _count_messages_for_duration(self, subscription_type: str, duration_seconds: int = 30) -> int:
        """Count messages received for a given duration"""
        count = 0
        
        try:
            async with websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
                open_timeout=10,
            ) as ws:
                # Subscribe
                if subscription_type == "trades":
                    subscribe_msg = {
                        "method": "subscribe",
                        "subscription": {"type": "trades", "coin": "BTC"},
                    }
                elif subscription_type == "candles":
                    # Use first working format from test results
                    if self.test_results["websocket_candles"] and self.test_results["websocket_candles"]["subscription_formats"]:
                        subscribe_msg = {
                            "method": "subscribe",
                            "subscription": self.test_results["websocket_candles"]["subscription_formats"][0],
                        }
                    else:
                        return 0
                else:
                    return 0
                
                await ws.send(json.dumps(subscribe_msg))
                
                # Count messages for duration
                start_time = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        count += 1
                    except asyncio.TimeoutError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error counting messages: {e}")
        
        return count
    
    # ============================================================================
    # Test 4: Check Official Documentation
    # ============================================================================
    
    def check_official_documentation(self) -> Dict[str, Any]:
        """Check Hyperliquid official docs for candle/OHLC information"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 4: Official Documentation Check")
        logger.info("=" * 80)
        
        docs_info = {
            "websocket_docs": "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket",
            "rest_api_docs": "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api",
            "rate_limits_docs": "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits",
            "notes": [
                "Check WebSocket subscription types",
                "Check REST API endpoints",
                "Check rate limits",
                "Check available timeframes",
            ],
        }
        
        logger.info("\nPlease check these documentation pages:")
        for key, url in docs_info.items():
            if key.endswith("_docs"):
                logger.info(f"  {key.replace('_docs', '').replace('_', ' ').title()}: {url}")
        
        logger.info("\nLook for:")
        for note in docs_info["notes"]:
            logger.info(f"  - {note}")
        
        return docs_info
    
    # ============================================================================
    # Main Test Runner
    # ============================================================================
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests"""
        logger.info("=" * 80)
        logger.info("Hyperliquid Candle Data Test Suite")
        logger.info("=" * 80)
        logger.info(f"WebSocket URL: {self.ws_url}")
        logger.info(f"REST Base URL: {self.rest_base}")
        logger.info("")
        
        # Test 1: WebSocket candles
        ws_results = await self.test_websocket_candle_subscriptions()
        
        # Test 2: REST API candles
        rest_results = self.test_rest_candle_endpoints()
        
        # Test 3: Message volume comparison (if candles available)
        if ws_results["supported"]:
            volume_results = await self.test_message_volume_comparison()
        else:
            volume_results = {"skipped": "Candles not available via WebSocket"}
        
        # Test 4: Documentation check
        docs_info = self.check_official_documentation()
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        logger.info(f"\nWebSocket Candles: {'✅ SUPPORTED' if ws_results['supported'] else '❌ NOT SUPPORTED'}")
        if ws_results["supported"]:
            logger.info(f"  Working formats: {len(ws_results['subscription_formats'])}")
            logger.info(f"  Available intervals: {ws_results['available_intervals']}")
        
        logger.info(f"\nREST API Candles: {'✅ FOUND' if rest_results['endpoints_found'] else '❌ NOT FOUND'}")
        if rest_results["endpoints_found"]:
            logger.info(f"  Endpoints: {[e['endpoint'] for e in rest_results['endpoints_found']]}")
        
        logger.info(f"\nRecommendation:")
        if ws_results["supported"]:
            logger.info("  ✅ Use WebSocket candles for OHLC (lower message volume)")
        elif rest_results["endpoints_found"]:
            logger.info("  ✅ Use REST API candles (polling approach)")
        else:
            logger.info("  ⚠️  Use trades aggregation (candles not available)")
        
        return {
            "websocket": ws_results,
            "rest": rest_results,
            "volume_comparison": volume_results,
            "documentation": docs_info,
        }


async def main():
    """Main test entry point"""
    tester = HyperliquidCandleTester()
    results = await tester.run_all_tests()
    
    # Save results to file
    output_file = "tests/hyperliquid/candle_test_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    return results


if __name__ == "__main__":
    asyncio.run(main())

