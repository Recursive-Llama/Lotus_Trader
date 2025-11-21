from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from supabase import Client, create_client  # type: ignore

logger = logging.getLogger(__name__)


BUCKET_THRESHOLDS = [
    ("nano", 0, 100_000),
    ("micro", 100_000, 5_000_000),
    ("mid", 5_000_000, 50_000_000),
    ("big", 50_000_000, 500_000_000),
    ("large", 500_000_000, 1_000_000_000),
    ("xl", 1_000_000_000, float("inf")),
]


def classify_bucket(market_cap: float) -> str:
    for name, lower, upper in BUCKET_THRESHOLDS:
        if lower <= market_cap < upper:
            return name
    return "xl"


@dataclass
class TokenMarketCap:
    token_contract: str
    chain: str
    market_cap: float
    timestamp: datetime


class CapBucketTagger:
    def __init__(self, lookback_hours: int = 24, min_market_cap: float = 10_000.0) -> None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)
        self.lookback_hours = lookback_hours
        self.min_market_cap = min_market_cap

    def run(self) -> int:
        tokens = self._fetch_latest_market_caps()
        if not tokens:
            logger.info("No tokens found for cap bucket tagging")
            return 0
        rows = []
        for tm in tokens:
            if tm.market_cap < self.min_market_cap:
                continue
            bucket = classify_bucket(tm.market_cap)
            rows.append(
                {
                    "token_contract": tm.token_contract,
                    "chain": tm.chain,
                    "bucket": bucket,
                    "market_cap_usd": tm.market_cap,
                    "updated_at": tm.timestamp.replace(tzinfo=timezone.utc).isoformat(),
                }
            )
        if not rows:
            logger.info("No rows qualified for bucket tagging")
            return 0
        try:
            self.sb.table("token_cap_bucket").upsert(rows, on_conflict="token_contract,chain").execute()
            logger.info("Upserted %d bucket tags", len(rows))
            return len(rows)
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to upsert bucket tags: %s", exc)
            return 0

    def _fetch_latest_market_caps(self) -> List[TokenMarketCap]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)
        page_size = 2000
        results: Dict[tuple[str, str], TokenMarketCap] = {}
        from_ts = cutoff.isoformat()
        try:
            offset = 0
            while True:
                resp = (
                    self.sb.table("lowcap_price_data_ohlc")
                    .select("token_contract,chain,market_cap,timestamp")
                    .eq("timeframe", "1m")
                    .gte("timestamp", from_ts)
                    .order("timestamp", desc=True)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                rows = resp.data or []
                if not rows:
                    break
                for row in rows:
                    key = (row.get("token_contract"), row.get("chain"))
                    if not key[0] or not key[1]:
                        continue
                    if key in results:
                        continue
                    mc = float(row.get("market_cap") or 0.0)
                    ts_raw = row.get("timestamp")
                    if not ts_raw:
                        continue
                    ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    results[key] = TokenMarketCap(
                        token_contract=key[0],
                        chain=key[1],
                        market_cap=mc,
                        timestamp=ts,
                    )
                if len(rows) < page_size:
                    break
                offset += page_size
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to fetch market caps: %s", exc)
        return list(results.values())


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    tagger = CapBucketTagger()
    tagger.run()


if __name__ == "__main__":
    main()

