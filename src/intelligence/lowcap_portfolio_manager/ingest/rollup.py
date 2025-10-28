"""
Roll up Hyperliquid ticks → 1m OHLCV bars for majors.

Reads: public.majors_trades_ticks
Writes: public.majors_price_data_1m

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
        """Roll up a single minute for optional symbols; returns bars written."""
        if when is None:
            when = datetime.now(tz=timezone.utc) - timedelta(seconds=5)
        when = self._to_utc(when)
        start, end = self._minute_bounds(when)

        bars: List[Bar] = []
        # fetch distinct tokens to process
        if symbols is None:
            # Using a heuristic: select distinct tokens with ticks in window
            resp = self.sb.rpc("exec_sql", {"sql": f"SELECT DISTINCT token FROM public.majors_trades_ticks WHERE ts >= '{start.isoformat()}' AND ts < '{end.isoformat()}'"}).execute()
            tokens = [r["token"] for r in (resp.data or [])]
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

        rows = [
            {
                "token": b.token,
                "ts": b.ts.isoformat(),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "source": "hyperliquid",
            }
            for b in bars
        ]
        self.sb.table("majors_price_data_1m").upsert(rows, on_conflict="token,ts").execute()
        return len(bars)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    job = OneMinuteRollup()
    written = job.roll_minute()
    logger.info("1m rollup wrote %d bars", written)


if __name__ == "__main__":
    main()


