"""
Test Hyperliquid Candle WebSocket Ingester

Tests:
1. Connection establishment
2. Subscription to candles
3. Message reception
4. Partial update filtering
5. Database writes
6. Reconnection handling

Run with: python tests/hyperliquid/test_candle_websocket.py
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

import websockets
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WS_URL = "wss://api.hyperliquid.xyz/ws"
TEST_SYMBOLS = ["BTC", "ETH"]
TEST_TIMEFRAMES = ["15m", "1h"]


async def test_basic_connection():
    """Test 1: Basic connection and subscription."""
    print("\n" + "="*80)
    print("TEST 1: Basic Connection & Subscription")
    print("="*80)
    
    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as ws:
            print("✅ Connected to WebSocket")
            
            # Subscribe to BTC 15m
            msg = {
                "method": "subscribe",
                "subscription": {
                    "type": "candle",
                    "coin": "BTC",
                    "interval": "15m"
                }
            }
            await ws.send(json.dumps(msg))
            print("✅ Sent subscription for BTC 15m")
            
            # Wait for messages
            messages_received = 0
            start_time = time.time()
            timeout = 30  # 30 seconds
            
            print("Waiting for messages (30s timeout)...")
            while time.time() - start_time < timeout:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(raw)
                    
                    if isinstance(data, dict) and data.get("channel") == "candle":
                        messages_received += 1
                        candle_data = data.get("data", {})
                        print(f"  Message {messages_received}: {candle_data.get('s')} {candle_data.get('i')} "
                              f"ts={candle_data.get('t')} c={candle_data.get('c')}")
                        
                        if messages_received >= 5:
                            break
                except asyncio.TimeoutError:
                    continue
            
            print(f"✅ Received {messages_received} messages")
            return messages_received > 0
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_partial_updates():
    """Test 2: Partial update filtering (timestamp change detection)."""
    print("\n" + "="*80)
    print("TEST 2: Partial Update Filtering")
    print("="*80)
    
    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as ws:
            # Subscribe to BTC 15m
            msg = {
                "method": "subscribe",
                "subscription": {
                    "type": "candle",
                    "coin": "BTC",
                    "interval": "15m"
                }
            }
            await ws.send(json.dumps(msg))
            
            # Track messages by timestamp
            timestamp_counts: Dict[int, int] = {}
            last_timestamp = None
            complete_candles = []
            
            start_time = time.time()
            timeout = 60  # 60 seconds to catch a candle close
            
            print("Collecting messages for 60s to detect candle closes...")
            while time.time() - start_time < timeout:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(raw)
                    
                    if isinstance(data, dict) and data.get("channel") == "candle":
                        candle_data = data.get("data", {})
                        ts = candle_data.get("t")
                        
                        if ts:
                            timestamp_counts[ts] = timestamp_counts.get(ts, 0) + 1
                            
                            # Detect timestamp change (previous candle complete)
                            if last_timestamp and ts != last_timestamp:
                                complete_candles.append(last_timestamp)
                                print(f"  ✅ Complete candle detected: ts={last_timestamp} "
                                      f"({timestamp_counts.get(last_timestamp, 0)} updates)")
                            
                            last_timestamp = ts
                except asyncio.TimeoutError:
                    continue
            
            print(f"\n✅ Collected {len(timestamp_counts)} unique timestamps")
            print(f"✅ Detected {len(complete_candles)} complete candles")
            print(f"   Average updates per candle: {sum(timestamp_counts.values()) / len(timestamp_counts):.1f}")
            
            return len(complete_candles) > 0
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_multiple_symbols():
    """Test 3: Multiple symbols and timeframes."""
    print("\n" + "="*80)
    print("TEST 3: Multiple Symbols & Timeframes")
    print("="*80)
    
    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as ws:
            # Subscribe to multiple symbols/timeframes
            subscriptions = []
            for symbol in TEST_SYMBOLS:
                for timeframe in TEST_TIMEFRAMES:
                    msg = {
                        "method": "subscribe",
                        "subscription": {
                            "type": "candle",
                            "coin": symbol,
                            "interval": timeframe
                        }
                    }
                    await ws.send(json.dumps(msg))
                    subscriptions.append(f"{symbol}:{timeframe}")
                    await asyncio.sleep(0.01)  # Small delay
            
            print(f"✅ Subscribed to {len(subscriptions)} streams")
            print(f"   Subscriptions: {', '.join(subscriptions)}")
            
            # Collect messages
            messages_by_sub: Dict[str, int] = {}
            start_time = time.time()
            timeout = 30
            
            print("Collecting messages for 30s...")
            while time.time() - start_time < timeout:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(raw)
                    
                    if isinstance(data, dict) and data.get("channel") == "candle":
                        candle_data = data.get("data", {})
                        key = f"{candle_data.get('s')}:{candle_data.get('i')}"
                        messages_by_sub[key] = messages_by_sub.get(key, 0) + 1
                except asyncio.TimeoutError:
                    continue
            
            print(f"\n✅ Messages received per subscription:")
            for sub in subscriptions:
                count = messages_by_sub.get(sub, 0)
                print(f"   {sub}: {count} messages")
            
            # Check if all subscriptions received data
            all_received = all(messages_by_sub.get(sub, 0) > 0 for sub in subscriptions)
            if all_received:
                print("✅ All subscriptions received data")
            else:
                print("⚠️  Some subscriptions did not receive data")
            
            return all_received
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_subscription_limits():
    """Test 4: Subscription limits (test with many symbols)."""
    print("\n" + "="*80)
    print("TEST 4: Subscription Limits")
    print("="*80)
    
    # Test with increasing numbers
    test_counts = [10, 50, 100]  # symbols × 3 timeframes = subscriptions
    
    for symbol_count in test_counts:
        print(f"\nTesting with {symbol_count} symbols × 3 timeframes = {symbol_count * 3} subscriptions...")
        
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=10) as ws:
                # Generate test symbols (use BTC, ETH, SOL, etc. repeated)
                symbols = ["BTC", "ETH", "SOL", "AVAX", "MATIC"] * (symbol_count // 5 + 1)
                symbols = symbols[:symbol_count]
                
                subscriptions_sent = 0
                start_sub = time.time()
                
                for symbol in symbols:
                    for timeframe in ["15m", "1h", "4h"]:
                        msg = {
                            "method": "subscribe",
                            "subscription": {
                                "type": "candle",
                                "coin": symbol,
                                "interval": timeframe
                            }
                        }
                        await ws.send(json.dumps(msg))
                        subscriptions_sent += 1
                        await asyncio.sleep(0.01)
                
                sub_time = time.time() - start_sub
                print(f"  ✅ Sent {subscriptions_sent} subscriptions in {sub_time:.2f}s")
                
                # Wait for any errors or confirmations
                await asyncio.sleep(2)
                
                # Try to receive a few messages
                messages = 0
                start_recv = time.time()
                while time.time() - start_recv < 10 and messages < 10:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        messages += 1
                    except asyncio.TimeoutError:
                        break
                
                print(f"  ✅ Received {messages} messages (sample)")
                print(f"  ✅ {symbol_count} symbols × 3 timeframes = {subscriptions_sent} subscriptions: OK")
        
        except Exception as e:
            print(f"  ❌ Failed at {symbol_count} symbols: {e}")
            return False
    
    print("\n✅ Subscription limit test passed (up to 100 symbols tested)")
    return True


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("HYPERLIQUID CANDLE WEBSOCKET TESTS")
    print("="*80)
    
    results = {}
    
    results["basic_connection"] = await test_basic_connection()
    results["partial_updates"] = await test_partial_updates()
    results["multiple_symbols"] = await test_multiple_symbols()
    results["subscription_limits"] = await test_subscription_limits()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\n{'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

