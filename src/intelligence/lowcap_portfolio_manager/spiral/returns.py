from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from supabase import create_client, Client  # type: ignore


@dataclass
class ReturnsResult:
    r_btc: float
    r_alt: float
    r_port: float
    closes_now: Dict[str, float]
    closes_prev: Dict[str, float]
    # Optional series (hourly) for meso computations
    series_ts: List[datetime] | None = None
    series_btc_close: List[float] | None = None
    series_alt_close: List[float] | None = None
    series_nav_usd: List[float] | None = None
    series_btc_volume: List[float] | None = None
    series_alt_volume: List[float] | None = None


class ReturnsComputer:
    def __init__(self) -> None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)

        self.alt_basket: List[str] = [s.strip().upper() for s in os.getenv("ALT_BASKET", "SOL,ETH,BNB,HYPE").split(",") if s.strip()]
        self.lookback_min: int = int(os.getenv("RET_LOOKBACK_MIN", "60"))

    def _minute_floor(self, ts: datetime) -> datetime:
        return ts.replace(second=0, microsecond=0)

    def _fetch_last_bar(self, table: str, token: str, ts: datetime, timeframe: Optional[str] = None) -> Optional[dict]:
        if table == "majors_price_data_ohlc":
            # Use majors_price_data_ohlc format
            query = (
                self.sb.table(table)
                .select("close_usd,volume,timestamp")
                .eq("token_contract", token)
                .eq("chain", "hyperliquid")
            )
            if timeframe:
                query = query.eq("timeframe", timeframe)
            query = query.lte("timestamp", ts.isoformat()).order("timestamp", desc=True)
            res = query.limit(1).execute()
            rows = res.data or []
            if not rows:
                return None
            row = rows[0]
            # Normalize to expected format
            return {"close": row["close_usd"], "volume": row["volume"], "ts": row["timestamp"]}
        else:
            # Legacy format (majors_price_data_1m)
            res = (
                self.sb.table(table)
                .select("close,volume,ts")
                .eq("token", token)
                .lte("ts", ts.isoformat())
                .order("ts", desc=True)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            return rows[0] if rows else None

    def _fetch_close(self, table: str, token: str, ts: datetime, timeframe: Optional[str] = None) -> Optional[float]:
        row = self._fetch_last_bar(table, token, ts, timeframe)
        return float(row["close"]) if row and row.get("close") is not None else None

    def _fetch_volume(self, table: str, token: str, ts: datetime, timeframe: Optional[str] = None) -> Optional[float]:
        row = self._fetch_last_bar(table, token, ts, timeframe)
        return float(row["volume"]) if row and row.get("volume") is not None else None

    def _log_return(self, now_close: Optional[float], prev_close: Optional[float]) -> float:
        if now_close is None or prev_close is None or now_close <= 0 or prev_close <= 0:
            return 0.0
        return math.log(now_close) - math.log(prev_close)

    def compute(self, when: Optional[datetime] = None) -> ReturnsResult:
        now = self._minute_floor(when or datetime.now(tz=timezone.utc))
        prev = now - timedelta(minutes=self.lookback_min)

        table = "majors_price_data_ohlc"
        timeframe_filter = "1m"

        # BTC close
        btc_now = self._fetch_close(table, "BTC", now, timeframe_filter)
        btc_prev = self._fetch_close(table, "BTC", prev, timeframe_filter)
        r_btc = self._log_return(btc_now, btc_prev)

        # Alt basket equal-weight close via arithmetic mean of closes
        closes_now: Dict[str, float] = {}
        closes_prev: Dict[str, float] = {}
        for sym in self.alt_basket:
            closes_now[sym] = self._fetch_close(table, sym, now, timeframe_filter) or 0.0
            closes_prev[sym] = self._fetch_close(table, sym, prev, timeframe_filter) or 0.0

        # Equal-weighted log return approximation: log(mean_now) - log(mean_prev)
        mean_now = sum(v for v in closes_now.values() if v > 0) / max(1, sum(1 for v in closes_now.values() if v > 0))
        mean_prev = sum(v for v in closes_prev.values() if v > 0) / max(1, sum(1 for v in closes_prev.values() if v > 0))
        r_alt = self._log_return(mean_now, mean_prev)

        # r_port from nav_usd in portfolio_bands over lookback
        nav_now = self._fetch_nav(now)
        nav_prev = self._fetch_nav(prev)
        r_port = self._log_return(nav_now, nav_prev)

        # Also provide hourly series for meso windows (last 24h)
        ts_series, btc_series, alt_series, nav_series, btc_vol_series, alt_vol_series = self._fetch_hourly_series(now, hours=24 * 7)

        return ReturnsResult(
            r_btc=r_btc,
            r_alt=r_alt,
            r_port=r_port,
            closes_now=closes_now | {"BTC": btc_now or 0.0},
            closes_prev=closes_prev | {"BTC": btc_prev or 0.0},
            series_ts=ts_series,
            series_btc_close=btc_series,
            series_alt_close=alt_series,
            series_nav_usd=nav_series,
            series_btc_volume=btc_vol_series,
            series_alt_volume=alt_vol_series,
        )

    def _fetch_nav(self, ts: datetime) -> Optional[float]:
        res = (
            self.sb.table("portfolio_bands")
            .select("nav_usd,ts")
            .lte("ts", ts.isoformat())
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        val = rows[0].get("nav_usd")
        return float(val) if val is not None else None

    def _fetch_hourly_series(self, end_ts: datetime, hours: int = 24) -> tuple[list[datetime], list[float], list[float], list[float], list[float], list[float]]:
        """Fetch hourly closes and volumes for BTC, equal-weight Alt basket, and NAV USD over window."""
        # Build hourly buckets
        buckets = [(end_ts - timedelta(hours=h)).replace(minute=0, second=0, microsecond=0) for h in range(hours, -1, -1)]

        def close_at_hour(token: str, ts: datetime) -> Optional[float]:
            return self._fetch_close("majors_price_data_ohlc", token, ts, "1m")

        def volume_at_hour(token: str, ts: datetime) -> Optional[float]:
            return self._fetch_volume("majors_price_data_ohlc", token, ts, "1m")

        btc_closes: list[float] = []
        alt_closes: list[float] = []
        nav_vals: list[float] = []
        btc_vols: list[float] = []
        alt_vols: list[float] = []
        for ts in buckets:
            btc = close_at_hour("BTC", ts) or 0.0
            btc_v = volume_at_hour("BTC", ts) or 0.0
            # alt mean of available tokens
            alt_vals = [close_at_hour(sym, ts) or 0.0 for sym in self.alt_basket]
            alt_vol_vals = [volume_at_hour(sym, ts) or 0.0 for sym in self.alt_basket]
            alt_nonzero = [v for v in alt_vals if v > 0]
            alt = (sum(alt_nonzero) / len(alt_nonzero)) if alt_nonzero else 0.0
            alt_vol_nonzero = [v for v in alt_vol_vals if v > 0]
            alt_v = (sum(alt_vol_nonzero) / len(alt_vol_nonzero)) if alt_vol_nonzero else 0.0
            nav = self._fetch_nav(ts) or 0.0
            btc_closes.append(btc)
            alt_closes.append(alt)
            nav_vals.append(nav)
            btc_vols.append(btc_v)
            alt_vols.append(alt_v)

        return buckets, btc_closes, alt_closes, nav_vals, btc_vols, alt_vols


