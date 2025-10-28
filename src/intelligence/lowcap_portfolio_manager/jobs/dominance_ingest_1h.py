"""
Fetch BTC.D and USDT.D levels hourly, compute 7d deltas and z-scores over 90d,
and write diagnostics to portfolio_bands (slope_z, curv_z, level_z; deltas).

This scaffold expects a data source for dominance series (REST or DB). Provide one of:
- DOM_SQL: SQL that returns rows { ts, btc_d, usdt_d } for at least 90d
- DOM_ENDPOINT_{BTC,USDT}: REST endpoints returning JSON time series

Writes: upsert into portfolio_bands at the hour bucket.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import json
import statistics
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from supabase import create_client, Client  # type: ignore


logger = logging.getLogger(__name__)


@dataclass
class DomPoint:
    ts: datetime
    btc_d: float
    usdt_d: float


class DominanceIngest:
    def __init__(self) -> None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)
        # No DOM_SQL needed; we fetch from CoinGecko

    def _hour_bucket(self, dt: Optional[datetime] = None) -> datetime:
        now = dt or datetime.now(tz=timezone.utc)
        return now.replace(minute=0, second=0, microsecond=0)

    def _z(self, series: List[float], value: float) -> float:
        if len(series) < 5:
            return 0.0
        mean = statistics.fmean(series)
        stdev = statistics.pstdev(series) or 1.0
        return (value - mean) / stdev

    def _slope(self, ys: List[float]) -> float:
        # Simple linear regression slope over index
        n = len(ys)
        if n < 3:
            return 0.0
        xs = list(range(n))
        xbar = statistics.fmean(xs)
        ybar = statistics.fmean(ys)
        num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
        den = sum((x - xbar) ** 2 for x in xs) or 1.0
        return num / den

    def _curvature(self, ys: List[float]) -> float:
        # Second derivative approx: slope of slopes on halves
        n = len(ys)
        if n < 6:
            return 0.0
        mid = n // 2
        return self._slope(ys[mid:]) - self._slope(ys[:mid])

    def _delta_ndays(self, pts: List[float], hours: int) -> float:
        if len(pts) < hours + 1:
            return 0.0
        return pts[-1] - pts[-(hours + 1)]

    def _fetch_json(self, path: str, params: Optional[dict] = None) -> dict:
        base = "https://api.coingecko.com/api/v3"
        url = f"{base}{path}"
        if params:
            url += f"?{urlencode(params)}"
        req = Request(url, headers={"Accept": "application/json", "User-Agent": "LotusPM/1.0"})
        with urlopen(req, timeout=20) as resp:  # nosec - public API
            return json.loads(resp.read().decode("utf-8"))

    def _fetch_current_levels(self) -> tuple[float, float]:
        data = self._fetch_json("/global").get("data", {})
        mkt = data.get("market_cap_percentage", {}) or {}
        btc_d = float(mkt.get("btc")) if mkt.get("btc") is not None else None
        usdt_d = mkt.get("usdt")
        if btc_d is None:
            raise RuntimeError("CoinGecko global missing btc dominance")
        if usdt_d is None:
            # fallback compute from total and tether market caps
            total_mc = (data.get("total_market_cap") or {}).get("usd")
            if not total_mc:
                raise RuntimeError("CoinGecko global missing total market cap")
            tether = self._fetch_json("/coins/markets", {"vs_currency": "usd", "ids": "tether"})
            usdt_mc = float(tether[0].get("market_cap") or 0.0) if tether else 0.0
            usdt_d = 100.0 * (usdt_mc / float(total_mc)) if usdt_mc and total_mc else 0.0
        return btc_d, float(usdt_d)

    def _load_dom_series(self) -> List[DomPoint]:
        """Build a 90d hourly series from portfolio_bands raw levels if present.
        We append the current point from CoinGecko at the end.
        """
        # read past 90d from portfolio_bands if raw level columns exist
        ninety_days_ago = self._hour_bucket() - timedelta(days=90)
        rows = (
            self.sb.table("portfolio_bands")
            .select("ts, btc_dom_level, usdt_dom_level")
            .gte("ts", ninety_days_ago.isoformat())
            .order("ts", desc=False)
            .execute()
            .data
            or []
        )
        out: List[DomPoint] = []
        for r in rows:
            ts = r.get("ts")
            b = r.get("btc_dom_level")
            u = r.get("usdt_dom_level")
            if ts is None or b is None or u is None:
                continue
            out.append(DomPoint(ts=datetime.fromisoformat(ts), btc_d=float(b), usdt_d=float(u)))
        # Append current
        btc_now, usdt_now = self._fetch_current_levels()
        out.append(DomPoint(ts=self._hour_bucket(), btc_d=btc_now, usdt_d=usdt_now))
        return out

    def compute_and_write(self) -> bool:
        pts = self._load_dom_series()
        if len(pts) < 24 * 7 + 1:
            logger.warning("Insufficient dominance history (need >= 7d)")
            return False
        # Use last 90d for z if available (hourly points)
        last_vals_btc = [p.btc_d for p in pts[-24 * 90 :]]
        last_vals_usdt = [p.usdt_d for p in pts[-24 * 90 :]]
        # Current and deltas
        btc_now = last_vals_btc[-1]
        usdt_now = last_vals_usdt[-1]
        btc_delta_7d = self._delta_ndays(last_vals_btc, 24 * 7)
        usdt_delta_7d = self._delta_ndays(last_vals_usdt, 24 * 7)
        # Z diagnostics
        btc_level_z = self._z(last_vals_btc, btc_now)
        usdt_level_z = self._z(last_vals_usdt, usdt_now)
        btc_slope_z = self._z(last_vals_btc, self._slope(last_vals_btc))
        usdt_slope_z = self._z(last_vals_usdt, self._slope(last_vals_usdt))
        btc_curv_z = self._z(last_vals_btc, self._curvature(last_vals_btc))
        usdt_curv_z = self._z(last_vals_usdt, self._curvature(last_vals_usdt))

        ts_hour = self._hour_bucket()
        row = {
            "ts": ts_hour.isoformat(),
            "btc_dom_delta": btc_delta_7d,
            "usdt_dom_delta": usdt_delta_7d,
            "dominance_delta": btc_delta_7d - usdt_delta_7d,
            "btc_dom_level": btc_now,
            "usdt_dom_level": usdt_now,
            "btc_dom_level_z": btc_level_z,
            "btc_dom_slope_z": btc_slope_z,
            "btc_dom_curv_z": btc_curv_z,
            "usdt_dom_level_z": usdt_level_z,
            "usdt_dom_slope_z": usdt_slope_z,
            "usdt_dom_curv_z": usdt_curv_z,
        }
        try:
            self.sb.table("portfolio_bands").upsert([row], on_conflict="ts").execute()
            logger.info("Wrote dominance diags at %s", ts_hour.isoformat())
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to write dominance diags: %s", exc)
            return False


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    job = DominanceIngest()
    job.compute_and_write()


if __name__ == "__main__":
    main()


