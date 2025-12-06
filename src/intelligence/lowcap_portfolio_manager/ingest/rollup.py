"""
Roll up Hyperliquid ticks → 1m OHLCV bars for majors.

Reads: public.majors_trades_ticks
Writes: public.majors_price_data_ohlc (timeframe='1m')

Rules
- Bars aligned to minute start (UTC)
- open: first trade price in minute; close: last trade price; high/low: extrema
- volume: quote-USD if available; else Σ(price×size)
- Upsert by (token, ts)
- Skip empty minutes (no synthetic candles)

Schedule: run every minute offset by +5s to catch late trades; or triggered by ingest heartbeat.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from supabase import create_client, Client  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class Bar:
    token: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OneMinuteRollup:
    def __init__(self) -> None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)

    def _minute_bounds(self, dt: datetime) -> tuple[datetime, datetime]:
        start = dt.replace(second=0, microsecond=0)
        end = start + timedelta(minutes=1)
        return start, end

    def _to_utc(self, dt: datetime) -> datetime:
        return dt.astimezone(timezone.utc)

    def _compute_bar(self, token: str, ticks: List[dict]) -> Optional[Bar]:
        if not ticks:
            return None
        prices = [float(t["price"]) for t in ticks]
        sizes = [float(t.get("size", 0.0)) for t in ticks]
        # first and last are by ts ascending
        ticks_sorted = sorted(ticks, key=lambda t: t["ts"])  # ts already ISO8601
        open_price = float(ticks_sorted[0]["price"])
        close_price = float(ticks_sorted[-1]["price"])
        high_price = max(prices)
        low_price = min(prices)
        # quote volume
        quote_volume = sum(float(t["price"]) * float(t.get("size", 0.0)) for t in ticks)
        ts = datetime.fromisoformat(ticks_sorted[0]["ts"]).astimezone(timezone.utc)
        ts_minute = ts.replace(second=0, microsecond=0)
        return Bar(token=token, ts=ts_minute, open=open_price, high=high_price, low=low_price, close=close_price, volume=quote_volume)

    def roll_minute(self, when: Optional[datetime] = None, symbols: Optional[List[str]] = None) -> int:
        """Roll up a single minute for optional symbols; returns bars written.
        
        If when is None, rolls up the most recent complete minute (2 minutes ago to avoid race conditions).
        """
        if when is None:
            # Look back 2 minutes to ensure we're rolling up a complete minute
            # This avoids race conditions where ticks are still coming in
            when = datetime.now(tz=timezone.utc) - timedelta(minutes=2)
        when = self._to_utc(when)
        start, end = self._minute_bounds(when)

        bars: List[Bar] = []
        # fetch distinct tokens to process
        if symbols is None:
            # Get distinct tokens from ticks in window using direct query
            # Query all ticks and extract unique tokens (simpler than exec_sql)
            res = self.sb.table("majors_trades_ticks").select("token").gte("ts", start.isoformat()).lt("ts", end.isoformat()).execute()
            tokens = list(set(r["token"] for r in (res.data or [])))
        else:
            tokens = symbols

        for token in tokens:
            # Fetch ticks for window
            res = self.sb.table("majors_trades_ticks").select("token,ts,price,size").gte("ts", start.isoformat()).lt("ts", end.isoformat()).eq("token", token).execute()
            ticks: List[dict] = res.data or []
            bar = self._compute_bar(token, ticks)
            if bar:
                bars.append(bar)

        if not bars:
            return 0

        # Write to majors_price_data_ohlc with timeframe='1m'
        ohlc_rows = []
        for b in bars:
            # Majors: Using USD prices only (native prices set to 0.0 for consistency)
            ohlc_rows.append({
                "token_contract": b.token,
                "chain": "hyperliquid",
                "timeframe": "1m",
                "timestamp": b.ts.isoformat(),
                "open_native": 0.0,
                "high_native": 0.0,
                "low_native": 0.0,
                "close_native": 0.0,
                "open_usd": b.open,
                "high_usd": b.high,
                "low_usd": b.low,
                "close_usd": b.close,
                "volume": b.volume,
                "source": "hyperliquid"
            })
        
        self.sb.table("majors_price_data_ohlc").upsert(
            ohlc_rows, 
            on_conflict="token_contract,chain,timeframe,timestamp"
        ).execute()
        return len(bars)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    job = OneMinuteRollup()
    written = job.roll_minute()
    logger.info("1m rollup wrote %d bars", written)


if __name__ == "__main__":
    main()


