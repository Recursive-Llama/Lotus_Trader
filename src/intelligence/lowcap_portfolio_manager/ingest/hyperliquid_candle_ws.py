"""
Hyperliquid WebSocket Candle Ingester for trading positions.

Responsibilities:
- Subscribe to candle streams for Hyperliquid perps (main DEX + HIP-3)
- Handle partial candle updates (timestamp change detection)
- Write complete candles to hyperliquid_price_data_ohlc table
- Support backpressure, reconnection, and subscription management

Env/config:
- HYPERLIQUID_WS_URL: optional explicit WS URL (e.g., wss://api.hyperliquid.xyz/ws)
- HYPERLIQUID_MAINNET_URL: https base (e.g., https://api.hyperliquid.xyz)
- HL_CANDLE_TIMEFRAMES: comma-separated, default "15m,1h,4h"
- HL_CANDLE_SYMBOLS: comma-separated list of symbols to subscribe (or "all" for all)
- SUPABASE_URL, SUPABASE_KEY: for DB writes
- HL_CANDLE_DEBUG: "1" to enable debug logging
- HL_CANDLE_BUFFER_SIZE: max candles to buffer before flush (default 50)

This ingester uses candle subscriptions (not trades) for efficient OHLC data collection.
Partial updates are filtered using timestamp change detection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import websockets  # type: ignore
from supabase import create_client, Client  # type: ignore

logger = logging.getLogger(__name__)

# Symbol routing constants
MAJORS = ["BTC", "SOL", "ETH", "BNB", "HYPE"]  # Symbols that go to majors_price_data_ohlc
REGIME_DRIVERS = ["BTC"]  # Symbols that go to regime_price_data_ohlc


@dataclass
class Candle:
    """Represents a complete OHLC candle."""
    token: str           # "BTC" or "xyz:TSLA"
    timeframe: str       # "15m", "1h", "4h"
    ts: datetime         # Start of candle
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int


class HyperliquidCandleWSIngester:
    """WebSocket ingester for Hyperliquid candle data."""
    
    def __init__(self, symbols: Optional[List[str]] = None, timeframes: Optional[List[str]] = None, 
                 discover_from_positions: bool = True) -> None:
        """
        Initialize the candle ingester.
        
        Args:
            symbols: List of symbols to subscribe (e.g., ["BTC", "ETH", "xyz:TSLA"])
                     If None and discover_from_positions=True, discovers from positions table.
                     If None and discover_from_positions=False, reads from HL_CANDLE_SYMBOLS env var.
            timeframes: List of timeframes to subscribe (e.g., ["15m", "1h", "4h"])
                        If None, reads from HL_CANDLE_TIMEFRAMES env var.
            discover_from_positions: If True, automatically discover symbols from positions table.
        """
        self.ws_url: str = self._build_ws_url()
        
        # Supabase client (needed for symbol discovery)
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)
        
        # Parse symbols
        if symbols:
            self.symbols = symbols
        elif discover_from_positions:
            self.symbols = self._discover_symbols_from_positions()
            logger.info("Discovered %d symbols from positions table: %s", 
                      len(self.symbols), ", ".join(self.symbols[:10]) + ("..." if len(self.symbols) > 10 else ""))
        else:
            symbols_env = os.getenv("HL_CANDLE_SYMBOLS", "BTC,ETH,SOL")
            self.symbols = [s.strip() for s in symbols_env.split(",") if s.strip()]
        
        # Parse timeframes
        if timeframes:
            self.timeframes = timeframes
        else:
            timeframes_env = os.getenv("HL_CANDLE_TIMEFRAMES", "15m,1h,4h")
            self.timeframes = [t.strip() for t in timeframes_env.split(",") if t.strip()]
        
        # Symbol discovery settings
        self.discover_from_positions = discover_from_positions
        self.symbol_refresh_interval = int(os.getenv("HL_SYMBOL_REFRESH_MINUTES", "10"))  # Refresh every 10 minutes
        self._last_symbol_refresh: Optional[float] = None
        
        # Connection settings
        self.backoff_base_ms: int = int(os.getenv("BACKOFF_BASE_MS", "500"))
        self.max_retries: int = int(os.getenv("MAX_RETRIES", "0"))  # 0 = infinite
        self.ping_interval: int = int(os.getenv("HL_PING_INTERVAL", "20"))
        self.ping_timeout: int = int(os.getenv("HL_PING_TIMEOUT", "10"))
        self.open_timeout: int = int(os.getenv("HL_OPEN_TIMEOUT", "30"))
        self.close_timeout: int = int(os.getenv("HL_CLOSE_TIMEOUT", "10"))
        
        # Debug settings
        self._debug: bool = os.getenv("HL_CANDLE_DEBUG", "0") == "1"
        self._debug_limit: int = int(os.getenv("HL_DEBUG_LIMIT", "10"))
        self._debug_seen: int = 0
        
        # Buffer for candles (partial update handling)
        self._candle_buffer: Dict[str, Dict[str, Any]] = {}  # key: (token, timeframe) -> last message
        self._complete_candles: List[Candle] = []
        self._buffer_size: int = int(os.getenv("HL_CANDLE_BUFFER_SIZE", "50"))
        
        # Stats
        self._last_message_ts: Optional[float] = None
        self._messages_received: int = 0
        self._candles_written: int = 0
        self._stale_warn_minutes: float = float(os.getenv("HL_STALE_WARN_MINUTES", "2"))
        
        # Active subscriptions tracking
        self._active_subscriptions: Set[str] = set()  # (token, timeframe) pairs

    def _discover_symbols_from_positions(self) -> List[str]:
        """
        Discover Hyperliquid symbols from positions table.
        
        Returns:
            List of unique symbols (token_contract values) for Hyperliquid positions.
        """
        try:
            res = (
                self.sb.table("lowcap_positions")
                .select("token_contract")
                .eq("token_chain", "hyperliquid")
                .in_("book_id", ["perps", "stock_perps"])
                .in_("status", ["watchlist", "active", "dormant"])
                .execute()
            )
            
            symbols = set()
            for row in (res.data or []):
                token = row.get("token_contract")
                if token:
                    symbols.add(token)
            
            if not symbols:
                logger.warning("No Hyperliquid positions found, falling back to default symbols")
                # Fallback to defaults
                symbols_env = os.getenv("HL_CANDLE_SYMBOLS", "BTC,ETH,SOL")
                return [s.strip() for s in symbols_env.split(",") if s.strip()]
            
            return sorted(list(symbols))
        
        except Exception as e:
            logger.error("Failed to discover symbols from positions: %s", e)
            # Fallback to defaults
            symbols_env = os.getenv("HL_CANDLE_SYMBOLS", "BTC,ETH,SOL")
            return [s.strip() for s in symbols_env.split(",") if s.strip()]
    
    def _refresh_symbols_if_needed(self) -> None:
        """Refresh symbol list from positions table if needed."""
        if not self.discover_from_positions:
            return
        
        now = time.time()
        if self._last_symbol_refresh is None or (now - self._last_symbol_refresh) > (self.symbol_refresh_interval * 60):
            new_symbols = self._discover_symbols_from_positions()
            
            # Check if symbols changed
            if set(new_symbols) != set(self.symbols):
                logger.info("Symbol list changed: %d -> %d symbols", len(self.symbols), len(new_symbols))
                self.symbols = new_symbols
                # Note: Re-subscription will happen on next reconnection
            
            self._last_symbol_refresh = now
    
    def _build_ws_url(self) -> str:
        """Build WebSocket URL from env."""
        explicit = os.getenv("HYPERLIQUID_WS_URL")
        if explicit:
            return explicit
        
        base = os.getenv("HYPERLIQUID_MAINNET_URL", "https://api.hyperliquid.xyz")
        
        # Convert http(s) → ws(s)
        if base.startswith("https://"):
            ws = "wss://" + base[len("https://"):]
        elif base.startswith("http://"):
            ws = "ws://" + base[len("http://"):]
        else:
            ws = base
        
        if not ws.endswith("/ws"):
            ws = ws.rstrip("/") + "/ws"
        
        return ws

    async def run(self) -> None:
        """Main loop: connect → subscribe → read → write candles to DB."""
        retries = 0
        while True:
            try:
                await self._ingest_loop()
                retries = 0
            except asyncio.CancelledError:
                # Flush remaining candles before exit
                await self._flush_candles()
                raise
            except Exception as exc:
                retries += 1
                wait_ms = min(self.backoff_base_ms * (2 ** (retries - 1)), 30_000)
                wait_ms = int(wait_ms * random.uniform(0.8, 1.2))
                
                exc_str = str(exc)
                if "timeout" in exc_str.lower() or "ConnectionClosed" in exc_str:
                    logger.warning(
                        "HL Candle WS: Connection issue, reconnecting in %d ms (retry %d)",
                        wait_ms, retries
                    )
                else:
                    logger.exception("HL Candle WS error: %s; retry %d in %d ms", exc, retries, wait_ms)
                
                # Stale data warning
                if self._last_message_ts:
                    minutes_dark = (time.time() - self._last_message_ts) / 60.0
                    if minutes_dark >= self._stale_warn_minutes:
                        logger.warning(
                            "HL Candle WS: No messages for %.1f minutes",
                            minutes_dark
                        )
                
                if self.max_retries > 0 and retries > self.max_retries:
                    logger.error("Max retries exceeded; exiting ingest loop")
                    raise
                
                await asyncio.sleep(wait_ms / 1000)

    async def _ingest_loop(self) -> None:
        """Connect and process messages."""
        async with websockets.connect(
            self.ws_url,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
            open_timeout=self.open_timeout,
            close_timeout=self.close_timeout,
        ) as ws:
            logger.info("HL Candle WS: Connected to %s", self.ws_url)
            
            # Refresh symbols before subscribing
            self._refresh_symbols_if_needed()
            
            total_subscriptions = len(self.symbols) * len(self.timeframes)
            logger.info("HL Candle WS: Subscribing to %d symbols x %d timeframes = %d subscriptions",
                       len(self.symbols), len(self.timeframes), total_subscriptions)
            
            if total_subscriptions > 1000:
                logger.warning("HL Candle WS: %d subscriptions exceeds recommended limit (1000)", total_subscriptions)
            
            await self._subscribe_all(ws)
            
            async for raw in ws:
                await self._handle_message(raw)
                
                # Periodic flush
                if len(self._complete_candles) >= self._buffer_size:
                    await self._flush_candles()
                
                # Periodic symbol refresh (check every 100 messages)
                if self._messages_received % 100 == 0:
                    self._refresh_symbols_if_needed()

    async def _subscribe_all(self, ws: Any) -> None:
        """Subscribe to candle streams for all symbols and timeframes."""
        self._active_subscriptions.clear()
        
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                msg = {
                    "method": "subscribe",
                    "subscription": {
                        "type": "candle",
                        "coin": symbol,
                        "interval": timeframe
                    }
                }
                await ws.send(json.dumps(msg))
                self._active_subscriptions.add(f"{symbol}:{timeframe}")
                
                if self._debug and self._debug_seen < self._debug_limit:
                    logger.info("HL Candle WS: Subscribed to %s %s", symbol, timeframe)
                    self._debug_seen += 1
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.01)
        
        logger.info("HL Candle WS: Subscribed to %d candle streams", len(self._active_subscriptions))

    async def _handle_message(self, raw: str | bytes) -> None:
        """Process incoming WebSocket message."""
        self._last_message_ts = time.time()
        self._messages_received += 1
        
        try:
            data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
        except json.JSONDecodeError:
            logger.debug("HL Candle WS: Failed to parse message")
            return
        
        # Debug logging
        if self._debug and self._debug_seen < self._debug_limit:
            logger.info("HL Candle WS: Message keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))
            self._debug_seen += 1
        
        # Handle candle channel
        if isinstance(data, dict) and data.get("channel") == "candle" and "data" in data:
            candle_data = data["data"]
            self._process_candle_update(candle_data)

    def _process_candle_update(self, candle_data: Dict[str, Any]) -> None:
        """
        Process candle update with partial update filtering.
        
        Hyperliquid sends multiple messages per candle with the same timestamp
        but updated OHLC values. We detect complete candles when the timestamp changes.
        """
        # Extract fields
        ts_ms = candle_data.get("t")  # Start timestamp in ms
        symbol = candle_data.get("s")  # Symbol (e.g., "BTC" or "xyz:TSLA")
        interval = candle_data.get("i")  # Interval (e.g., "15m")
        
        if not all([ts_ms, symbol, interval]):
            return
        
        # Create buffer key
        buffer_key = f"{symbol}:{interval}"
        
        # Check for timestamp change (previous candle is complete)
        if buffer_key in self._candle_buffer:
            prev = self._candle_buffer[buffer_key]
            prev_ts = prev.get("t")
            
            if prev_ts and prev_ts != ts_ms:
                # Previous candle is complete - add to complete candles list
                candle = Candle(
                    token=prev.get("s"),
                    timeframe=prev.get("i"),
                    ts=datetime.fromtimestamp(prev_ts / 1000, tz=timezone.utc),
                    open=float(prev.get("o", 0)),
                    high=float(prev.get("h", 0)),
                    low=float(prev.get("l", 0)),
                    close=float(prev.get("c", 0)),
                    volume=float(prev.get("v", 0)),
                    trades=int(prev.get("n", 0)),
                )
                self._complete_candles.append(candle)
                
                if self._debug:
                    logger.debug(
                        "HL Candle WS: Complete candle %s %s ts=%s c=%.4f v=%.4f",
                        candle.token, candle.timeframe, candle.ts, candle.close, candle.volume
                    )
        
        # Update buffer with latest message
        self._candle_buffer[buffer_key] = candle_data

    async def _flush_candles(self) -> None:
        """Write complete candles to database (multiple tables based on symbol)."""
        if not self._complete_candles:
            return
        
        candles_to_write = self._complete_candles.copy()
        self._complete_candles.clear()
        
        # 1. Always write to hyperliquid_price_data_ohlc (all candles)
        hyperliquid_rows = [
            {
                "token": c.token,
                "timeframe": c.timeframe,
                "ts": c.ts.isoformat(),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "trades": c.trades,
                "source": "hyperliquid_ws",
            }
            for c in candles_to_write
        ]
        
        # 2. Write majors to majors_price_data_ohlc (BTC, SOL, ETH, BNB, HYPE)
        majors_rows = [
            {
                "token_contract": c.token,
                "chain": "hyperliquid",
                "timeframe": c.timeframe,
                "timestamp": c.ts.isoformat(),
                "open_usd": c.open,
                "high_usd": c.high,
                "low_usd": c.low,
                "close_usd": c.close,
                "open_native": 0.0,
                "high_native": 0.0,
                "low_native": 0.0,
                "close_native": 0.0,
                "volume": c.volume,
                "source": "hyperliquid",
            }
            for c in candles_to_write
            if c.token in MAJORS
        ]
        
        # 3. Write regime drivers to regime_price_data_ohlc (BTC only)
        regime_rows = [
            {
                "driver": c.token,
                "timeframe": c.timeframe,
                "timestamp": c.ts.isoformat(),
                "book_id": "onchain_crypto",
                "open_usd": c.open,
                "high_usd": c.high,
                "low_usd": c.low,
                "close_usd": c.close,
                "volume": c.volume,
                "source": "hyperliquid",
            }
            for c in candles_to_write
            if c.token in REGIME_DRIVERS
        ]
        
        # Write to hyperliquid_price_data_ohlc (all candles)
        try:
            self.sb.table("hyperliquid_price_data_ohlc").upsert(
                hyperliquid_rows,
                on_conflict="token,timeframe,ts"
            ).execute()
            self._candles_written += len(hyperliquid_rows)
            if self._debug:
                logger.info("HL Candle WS: Wrote %d candles to hyperliquid_price_data_ohlc (total: %d)", 
                          len(hyperliquid_rows), self._candles_written)
        except Exception as e:
            logger.error("HL Candle WS: Failed to write to hyperliquid_price_data_ohlc: %s", e)
        
        # Write to majors_price_data_ohlc (majors only)
        if majors_rows:
            try:
                self.sb.table("majors_price_data_ohlc").upsert(
                    majors_rows,
                    on_conflict="token_contract,chain,timeframe,timestamp"
                ).execute()
                if self._debug:
                    logger.info("HL Candle WS: Wrote %d candles to majors_price_data_ohlc", len(majors_rows))
            except Exception as e:
                logger.error("HL Candle WS: Failed to write to majors_price_data_ohlc: %s", e)
        
        # Write to regime_price_data_ohlc (regime drivers only)
        if regime_rows:
            try:
                self.sb.table("regime_price_data_ohlc").upsert(
                    regime_rows,
                    on_conflict="driver,book_id,timeframe,timestamp"
                ).execute()
                if self._debug:
                    logger.info("HL Candle WS: Wrote %d candles to regime_price_data_ohlc", len(regime_rows))
            except Exception as e:
                logger.error("HL Candle WS: Failed to write to regime_price_data_ohlc: %s", e)

    async def flush_on_shutdown(self) -> None:
        """Flush any remaining candles before shutdown."""
        # Mark current buffered candles as complete and flush
        for buffer_key, candle_data in self._candle_buffer.items():
            ts_ms = candle_data.get("t")
            if ts_ms:
                candle = Candle(
                    token=candle_data.get("s"),
                    timeframe=candle_data.get("i"),
                    ts=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
                    open=float(candle_data.get("o", 0)),
                    high=float(candle_data.get("h", 0)),
                    low=float(candle_data.get("l", 0)),
                    close=float(candle_data.get("c", 0)),
                    volume=float(candle_data.get("v", 0)),
                    trades=int(candle_data.get("n", 0)),
                )
                self._complete_candles.append(candle)
        
        self._candle_buffer.clear()
        await self._flush_candles()

    def get_stats(self) -> Dict[str, Any]:
        """Get ingester stats."""
        return {
            "messages_received": self._messages_received,
            "candles_written": self._candles_written,
            "active_subscriptions": len(self._active_subscriptions),
            "buffer_size": len(self._complete_candles),
            "last_message_ts": self._last_message_ts,
        }


async def main() -> None:
    """Run the candle ingester."""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    ingester = HyperliquidCandleWSIngester()
    try:
        await ingester.run()
    except asyncio.CancelledError:
        await ingester.flush_on_shutdown()
        logger.info("HL Candle WS: Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())

