"""
Isolated test for Hyperliquid WebSocket to figure out what works.

This test connects to Hyperliquid WS and tries different subscription formats
to see which one actually receives data.
"""

import pytest
import asyncio
import json
import websockets
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_hyperliquid_ws_connection():
    """Test basic Hyperliquid WebSocket connection and message reception."""
    ws_url = "wss://api.hyperliquid.xyz/ws"
    symbols = ["BTC", "ETH", "SOL"]
    messages_received = []
    
    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
            logger.info(f"✅ Connected to {ws_url}")
            
            # Try subscription format 1: "trades" type (what ingester uses)
            logger.info("\n📡 Trying subscription format 1: 'trades' type...")
            for symbol in symbols:
                msg = {
                    "method": "subscribe",
                    "subscription": {"type": "trades", "coin": symbol},
                }
                await ws.send(json.dumps(msg))
                logger.info(f"   Sent: {json.dumps(msg)}")
            
            # Wait for messages
            logger.info("   Waiting for messages (10 seconds)...")
            try:
                async with asyncio.timeout(10):
                    async for raw in ws:
                        data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
                        messages_received.append(data)
                        logger.info(f"   📨 Received: {json.dumps(data)[:200]}...")
                        if len(messages_received) >= 5:
                            break
            except asyncio.TimeoutError:
                logger.warning("   ⚠️  No messages received with 'trades' format")
            
            if messages_received:
                logger.info(f"✅ 'trades' format works! Received {len(messages_received)} messages")
                return
            
            # Try subscription format 2: "candle" type (what hyperliquid_client.py uses)
            logger.info("\n📡 Trying subscription format 2: 'candle' type...")
            messages_received = []
            for symbol in symbols:
                msg = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "candle",
                        "coin": symbol,
                        "interval": "1m"
                    },
                }
                await ws.send(json.dumps(msg))
                logger.info(f"   Sent: {json.dumps(msg)}")
            
            # Wait for messages
            logger.info("   Waiting for messages (10 seconds)...")
            try:
                async with asyncio.timeout(10):
                    async for raw in ws:
                        data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
                        messages_received.append(data)
                        logger.info(f"   📨 Received: {json.dumps(data)[:200]}...")
                        if len(messages_received) >= 5:
                            break
            except asyncio.TimeoutError:
                logger.warning("   ⚠️  No messages received with 'candle' format")
            
            if messages_received:
                logger.info(f"✅ 'candle' format works! Received {len(messages_received)} messages")
                return
            
            # Try subscription format 3: "l2Book" or other types
            logger.info("\n📡 Trying subscription format 3: 'l2Book' type...")
            messages_received = []
            for symbol in symbols:
                msg = {
                    "method": "subscribe",
                    "subscription": {"type": "l2Book", "coin": symbol},
                }
                await ws.send(json.dumps(msg))
                logger.info(f"   Sent: {json.dumps(msg)}")
            
            # Wait for messages
            logger.info("   Waiting for messages (10 seconds)...")
            try:
                async with asyncio.timeout(10):
                    async for raw in ws:
                        data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
                        messages_received.append(data)
                        logger.info(f"   📨 Received: {json.dumps(data)[:200]}...")
                        if len(messages_received) >= 5:
                            break
            except asyncio.TimeoutError:
                logger.warning("   ⚠️  No messages received with 'l2Book' format")
            
            if messages_received:
                logger.info(f"✅ 'l2Book' format works! Received {len(messages_received)} messages")
                return
            
            # If we get here, none of the formats worked
            pytest.fail(
                "❌ None of the subscription formats received messages. "
                "Check Hyperliquid API documentation for correct format."
            )
            
    except Exception as e:
        pytest.fail(f"❌ WebSocket connection failed: {e}")


@pytest.mark.asyncio
async def test_hyperliquid_ws_raw_connection():
    """Test raw connection without subscriptions to see what Hyperliquid sends."""
    ws_url = "wss://api.hyperliquid.xyz/ws"
    messages_received = []
    
    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
            logger.info(f"✅ Connected to {ws_url}")
            logger.info("   Waiting for any messages (5 seconds)...")
            
            try:
                async with asyncio.timeout(5):
                    async for raw in ws:
                        data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
                        messages_received.append(data)
                        logger.info(f"   📨 Received: {json.dumps(data)[:200]}...")
                        if len(messages_received) >= 3:
                            break
            except asyncio.TimeoutError:
                logger.info("   ℹ️  No unsolicited messages (this is normal)")
            
            logger.info(f"   Total messages received: {len(messages_received)}")
            if messages_received:
                logger.info("   Sample message structure:")
                logger.info(f"   {json.dumps(messages_received[0], indent=2)}")
            
    except Exception as e:
        pytest.fail(f"❌ WebSocket connection failed: {e}")

