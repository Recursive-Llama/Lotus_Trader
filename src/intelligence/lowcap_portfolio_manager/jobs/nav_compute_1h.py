"""
Compute and persist portfolio NAV (USD) hourly into portfolio_bands.nav_usd.

Configuration:
- SUPABASE_URL, SUPABASE_KEY (required)
- NAV_SQL (optional): a SQL statement that returns a single row with column `nav_usd`.
  Example (adjust to your schema):
    SELECT SUM(p.quantity * px.close) AS nav_usd
    FROM public.lowcap_positions p
    JOIN (
      SELECT token, close
      FROM public.lowcap_price_data_1m
      WHERE ts = date_trunc('minute', now() at time zone 'utc')
    ) px ON px.token = p.token;

If NAV_SQL is not provided, the job logs a warning and exits without writing.

Behavior:
- Aligns writes to the hour start (UTC) using date_trunc('hour', now()).
- Upserts into portfolio_bands on (ts) with nav_usd populated; other fields untouched.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict

from supabase import create_client, Client  # type: ignore


logger = logging.getLogger(__name__)


class NavComputer:
    def __init__(self) -> None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)
        self.nav_sql: Optional[str] = os.getenv("NAV_SQL")

    def _hour_bucket(self, dt: Optional[datetime] = None) -> datetime:
        now = dt or datetime.now(tz=timezone.utc)
        return now.replace(minute=0, second=0, microsecond=0)

    def _fetch_active_positions(self) -> List[Dict[str, Any]]:
        res = (
            self.sb.table("lowcap_positions")
            .select("token_contract, token_chain, total_quantity, status")
            .eq("status", "active")
            .limit(2000)
            .execute()
        )
        return res.data or []

    def _fetch_last_price(self, token_contract: str, chain: str, ts: datetime) -> Optional[float]:
        res = (
            self.sb.table("lowcap_price_data_1m")
            .select("price_usd, timestamp")
            .eq("token_contract", token_contract)
            .eq("chain", chain)
            .lte("timestamp", ts.isoformat())
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        val = rows[0].get("price_usd")
        return float(val) if val is not None else None

    def compute_nav(self) -> Optional[float]:
        try:
            ts = self._hour_bucket()
            acc = 0.0
            positions = self._fetch_active_positions()
            for p in positions:
                qty = float(p.get("total_quantity") or 0.0)
                if qty <= 0:
                    continue
                contract = p.get("token_contract")
                chain = p.get("token_chain")
                if not contract or not chain:
                    continue
                price = self._fetch_last_price(str(contract), str(chain), ts)
                if price is None or price <= 0:
                    continue
                acc += qty * price
            if acc <= 0:
                logger.warning("NAV compute: no priced active positions; result=0")
            return acc
        except Exception as exc:  # noqa: BLE001
            logger.error("NAV compute failed: %s", exc)
            return None

    def write_nav(self, nav_usd: float, when: Optional[datetime] = None) -> bool:
        ts_hour = self._hour_bucket(when)
        try:
            # Try update existing row first
            existing = (
                self.sb.table("portfolio_bands")
                .select("ts")
                .eq("ts", ts_hour.isoformat())
                .limit(1)
                .execute()
                .data
                or []
            )
            if existing:
                self.sb.table("portfolio_bands").update({"nav_usd": nav_usd}).eq("ts", ts_hour.isoformat()).execute()
                logger.info("Updated nav_usd=%.2f at %s", nav_usd, ts_hour.isoformat())
                return True
            # Insert new row with required NOT NULL defaults
            core_count = self._count_active_positions()
            row = {
                "ts": ts_hour.isoformat(),
                "core_count": core_count,
                "cut_pressure": 0.0,
                "cut_pressure_raw": 0.0,
                "phase_tension": 0.0,
                "core_congestion": 0.0,
                "liquidity_stress": 0.0,
                "intent_skew": 0.0,
                "nav_usd": nav_usd,
            }
            self.sb.table("portfolio_bands").insert(row).execute()
            logger.info("Inserted nav_usd=%.2f at %s (core_count=%d)", nav_usd, ts_hour.isoformat(), core_count)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to write nav_usd: %s", exc)
            return False

    def _count_active_positions(self) -> int:
        res = self.sb.table("lowcap_positions").select("id", count="exact").eq("status", "active").execute()
        # supabase-py doesn't always return count without request options; fallback to len(data)
        if getattr(res, "count", None) is not None:
            return int(res.count or 0)
        return len(res.data or [])


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    job = NavComputer()
    nav = job.compute_nav()
    if nav is not None:
        job.write_nav(nav)


if __name__ == "__main__":
    main()


