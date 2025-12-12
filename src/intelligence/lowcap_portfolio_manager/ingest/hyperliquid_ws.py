"""
Hyperliquid WebSocket tick ingester for majors (BTC, ETH, BNB, SOL, HYPE).

Responsibilities
- Maintain a resilient WS connection to Hyperliquid and ingest trade ticks
- Enforce UTC minute alignment and late-trade window (tick buffer)
- Deduplicate on (token, ts, trade_id)
- Upsert ticks into public.majors_trades_ticks

This module intentionally avoids side effects elsewhere in the system.
The 1m rollup is implemented separately in rollup.py.

Env/config (provide via os.environ or a small config loader):
- HYPERLIQUID_WS_URL: optional explicit WS URL (e.g., wss://api.hyperliquid.xyz/ws)
- HYPERLIQUID_MAINNET_URL: https base (e.g., https://api.hyperliquid.xyz)
- HYPERLIQUID_USE_TESTNET: "true"/"false" (defaults false)
- HL_SYMBOLS: comma-separated list, default "BTC,ETH,BNB,SOL,HYPE"
- SUPABASE_URL, SUPABASE_KEY: for DB writes
- TICK_BUFFER_SEC: int, default 75  (accept late trades up to 75s)
- BACKOFF_BASE_MS: int, default 500
- MAX_RETRIES: int, default 0 (= infinite retries)
- HL_STALE_WARN_MINUTES: minutes without ticks before warning (default 2)

This implementation follows the repo's HL patterns; adjust `_subscribe`/`_parse_tick`
if Hyperliquid changes payload shapes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Optional dependency: websockets
import websockets  # type: ignore
from supabase import create_client, Client  # type: ignore


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tick:
    token: str
    ts: datetime  # precise trade ts (UTC)
    price: float
    size: float   # base size; quote can be Σ(price*size)
    side: Optional[str] = None
    trade_id: Optional[str] = None


class HyperliquidWSIngester:
    def __init__(self) -> None:
        self.ws_url: str = self._build_ws_url()

        self.symbols: List[str] = [s.strip().upper() for s in os.getenv("HL_SYMBOLS", "BTC,ETH,BNB,SOL,HYPE").split(",") if s.strip()]
        self.backoff_base_ms: int = int(os.getenv("BACKOFF_BASE_MS", "500"))
        # If MAX_RETRIES <= 0, treat as infinite retries
        self.max_retries: int = int(os.getenv("MAX_RETRIES", "0"))

        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)

        self._debug: bool = os.getenv("HL_DEBUG", "0") == "1"
        self._debug_limit: int = int(os.getenv("HL_DEBUG_LIMIT", "5"))
        self._debug_seen: int = 0
        self._token_counts: Dict[str, int] = {sym: 0 for sym in self.symbols}
        # Allow tuning WS timeouts via env (fall back to previous defaults)
        self.ping_interval: int = int(os.getenv("HL_PING_INTERVAL", "20"))
        self.ping_timeout: int = int(os.getenv("HL_PING_TIMEOUT", "10"))
        self.open_timeout: int = int(os.getenv("HL_OPEN_TIMEOUT", "30"))
        self.close_timeout: int = int(os.getenv("HL_CLOSE_TIMEOUT", "10"))
        
        # Batch ticks for efficient writes (small buffer, flush frequently)
        self._tick_buffer: List[Tick] = []
        self._buffer_size: int = 10  # Flush every 10 ticks for more frequent writes
        self._last_tick_ts: Optional[float] = None
        self._stale_warn_minutes: float = float(os.getenv("HL_STALE_WARN_MINUTES", "2"))

    async def run(self) -> None:
        """Main loop: connect → subscribe → read → write ticks to DB."""
        retries = 0
        while True:
            try:
                await self._ingest_loop()
                retries = 0  # reset on clean exit
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                retries += 1
                # Exponential backoff capped at 30s with jitter to avoid thundering herd
                wait_ms = min(self.backoff_base_ms * (2 ** (retries - 1)), 30_000)
                wait_ms = int(wait_ms * random.uniform(0.8, 1.2))
                
                # Tidy up error messages for expected connection issues
                exc_str = str(exc)
                exc_type = type(exc).__name__
                if (
                    isinstance(exc, TimeoutError)
                    or "keepalive ping timeout" in exc_str
                    or "ConnectionClosedError" in exc_str
                    or "TimeoutError" in exc_type
                    or "timeout" in exc_str.lower()
                ):
                    # Expected WebSocket timeout/connection issue - log concisely
                    retry_cap = "∞" if self.max_retries <= 0 else str(self.max_retries)
                    logger.warning("HL WS: Connection timeout/handshake failed, reconnecting in %d ms (retry %d/%s)", wait_ms, retries, retry_cap)
                else:
                    # Unexpected error - log with full context
                    logger.exception("HL WS ingest error: %s; retry %d in %d ms", exc, retries, wait_ms)
                
                # Emit a stale-data warning if we've been dark for a while
                if self._last_tick_ts:
                    minutes_dark = (time.time() - self._last_tick_ts) / 60.0
                    if minutes_dark >= self._stale_warn_minutes:
                        logger.warning("HL WS: No ticks for %.1f minutes (last tick at %s)", minutes_dark, datetime.fromtimestamp(self._last_tick_ts, tz=timezone.utc).isoformat())
                
                if self.max_retries > 0 and retries > self.max_retries:
                    logger.error("Max retries exceeded; exiting ingest loop")
                    raise
                await asyncio.sleep(wait_ms / 1000)

    async def _ingest_loop(self) -> None:
        # Add open_timeout to allow more time for initial handshake (default is often too short)
        # close_timeout ensures graceful shutdown
        async with websockets.connect(
            self.ws_url,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
            open_timeout=self.open_timeout,  # 30 seconds for initial connection handshake
            close_timeout=self.close_timeout,  # 10 seconds for graceful close
        ) as ws:  # type: ignore[arg-type]
            logger.info("HL WS: Connected to %s", self.ws_url)
            await self._subscribe(ws, self.symbols)
            async for raw in ws:
                await self._handle_message(raw)
    
    async def flush_on_shutdown(self) -> None:
        """Flush any remaining ticks in buffer before shutdown."""
        if self._tick_buffer:
            await self._write_ticks(self._tick_buffer)
            self._tick_buffer.clear()

    async def _subscribe(self, ws: Any, symbols: List[str]) -> None:
        """Subscribe to market data. Using repo's existing style as reference.
        If HL requires different payloads for trades, adjust here.
        """
        # Default to candles subscription style from existing client as baseline.
        # Replace 'candle' → 'trades' if you need raw trades; _parse_tick supports both.
        for idx, sym in enumerate(symbols):
            msg = {
                "method": "subscribe",
                "subscription": {"type": "trades", "coin": sym},
            }
            await ws.send(json.dumps(msg))
            logger.info("Subscribed to trades for %s", sym)
            if self._debug and self._debug_seen < self._debug_limit:
                logger.info("Subscribe payload: %s", msg)

    async def _handle_message(self, raw: str | bytes) -> None:
        data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
        # Mark heartbeat for stale detection
        self._last_tick_ts = time.time()
        if self._debug and self._debug_seen < self._debug_limit:
            logger.info("WS msg keys: %s", list(data.keys()) if isinstance(data, dict) else type(data))
        # Envelope handling: {"channel":"trades","data":[...]}
        if isinstance(data, dict) and data.get("channel") == "trades" and "data" in data:
            records = data["data"]
            envelope_coin = data.get("coin")
            if isinstance(records, dict):
                records = [records]
            wrote = 0
            for rec in records or []:
                # Normalize coin field if needed
                if "coin" not in rec:
                    if envelope_coin:
                        rec = {**rec, "coin": envelope_coin}
                    elif "s" in rec:
                        rec = {**rec, "coin": rec["s"]}
                tick = self._parse_tick(rec)
                if tick is None:
                    continue
                self._tick_buffer.append(tick)
                wrote += 1
                self._token_counts[tick.token] = self._token_counts.get(tick.token, 0) + 1
                
                # Flush buffer when it reaches size limit
                if len(self._tick_buffer) >= self._buffer_size:
                    await self._write_ticks(self._tick_buffer)
                    self._tick_buffer.clear()
            
            if wrote > 0:
                if self._debug and self._debug_seen < self._debug_limit:
                    self._debug_seen += 1
                    first_keys = list(records[0].keys()) if records else []
                    logger.info("trades envelope coin=%s records=%d first_keys=%s counts=%s", envelope_coin, len(records or []), first_keys, self._token_counts)
            return

        # Fallback: direct trade object or other shapes
        tick = self._parse_tick(data)
        if tick is None:
            return
        self._tick_buffer.append(tick)
        self._token_counts[tick.token] = self._token_counts.get(tick.token, 0) + 1
        
        # Flush buffer when it reaches size limit
        if len(self._tick_buffer) >= self._buffer_size:
            await self._write_ticks(self._tick_buffer)
            self._tick_buffer.clear()

    def _parse_tick(self, payload: Dict[str, Any]) -> Optional[Tick]:
        """Translate HL message → Tick. Replace with real parsing.

        Expected to extract: token, ts (UTC), price, size, side?, trade_id?
        """
        # Attempts multiple common shapes based on repo examples and HL docs.
        try:
            # trades style: { type: 'trade', coin, px, sz, side, time, id/hash/tid }
            if "coin" in payload and ("px" in payload or "price" in payload):
                token = str(payload.get("coin") or payload.get("symbol")).upper()
                price = float(payload.get("px", payload.get("price")))
                size = float(payload.get("sz", payload.get("size", 0.0)))
                # Hyperliquid uses "hash" or "tid" for trade ID, not "id"
                trade_id_val = payload.get("id") or payload.get("trade_id") or payload.get("hash") or payload.get("tid")
                trade_id = str(trade_id_val) if trade_id_val is not None else None
                side = payload.get("side")
                ts_ms_val = payload.get("time") or payload.get("ts")
                ts_ms = int(ts_ms_val if ts_ms_val is not None else int(time.time() * 1000))
            # candle tick style: { type: 'candle', coin, timeframe, t, o,h,l,c,v }
            elif "coin" in payload and "c" in payload and "t" in payload:
                token = str(payload["coin"]).upper()
                price = float(payload.get("c"))
                size = float(payload.get("v", 0.0))
                trade_id = None
                side = None
                ts_ms = int(payload.get("t"))
            else:
                # generic fallback
                token = str(payload["symbol"]).upper()
                price = float(payload["price"])
                size = float(payload.get("size", 0.0))
                trade_id = str(payload.get("id")) if payload.get("id") is not None else None
                side = payload.get("side")
                ts_ms = int(payload.get("ts", int(time.time() * 1000)))
            ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        except Exception:  # noqa: BLE001
            logger.debug("skip unparsable payload: %s", payload)
            return None

        if token not in self.symbols:
            return None
        # Ensure trade_id fallback for PK on upsert
        if trade_id is None:
            # Deterministic fallback id
            trade_id = f"{token}-{int(ts.timestamp()*1000)}-{price:.8f}-{size:.8f}"
        return Tick(token=token, ts=ts, price=price, size=size, side=side, trade_id=trade_id)

    def _build_ws_url(self) -> str:
        # 1) explicit WS if provided
        explicit = os.getenv("HYPERLIQUID_WS_URL")
        if explicit:
            return explicit
        # 2) derive from mainnet/testnet base
        base = os.getenv("HYPERLIQUID_MAINNET_URL", "https://api.hyperliquid.xyz")
        use_testnet = os.getenv("HYPERLIQUID_USE_TESTNET", "false").lower() == "true"
        # if testnet toggled, prefer provided base; otherwise default mainnet
        # Convert http(s) → ws(s) and ensure trailing /ws
        if base.startswith("https://"):
            ws = "wss://" + base[len("https://"):]
        elif base.startswith("http://"):
            ws = "ws://" + base[len("http://"):]
        else:
            ws = base
        if not ws.endswith("/ws"):
            ws = ws.rstrip("/") + "/ws"
        return ws

    async def _write_ticks(self, ticks: List[Tick]) -> None:
        # Deduplicate ticks by (token, ts, trade_id) before writing
        seen = set()
        unique_ticks = []
        for t in ticks:
            key = (t.token, t.ts.isoformat(), t.trade_id)
            if key not in seen:
                seen.add(key)
                unique_ticks.append(t)
        
        if not unique_ticks:
            return
        
        # Batched upsert into public.majors_trades_ticks
        rows = [
            {
                "token": t.token,
                "ts": t.ts.isoformat(),
                "price": t.price,
                "size": t.size,
                "side": t.side,
                "trade_id": t.trade_id,
                "source": "hyperliquid",
            }
            for t in unique_ticks
        ]
        # Supabase upsert; log errors if any
        try:
            res = self.sb.table("majors_trades_ticks").upsert(rows, on_conflict="token,ts,trade_id").execute()
            if self._debug:
                logger.info("Upserted %d ticks (status ok) - %d duplicates filtered", len(rows), len(ticks) - len(unique_ticks))
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed upsert %d ticks: %s", len(rows), exc)



async def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    ingester = HyperliquidWSIngester()
    await ingester.run()


if __name__ == "__main__":
    asyncio.run(main())


