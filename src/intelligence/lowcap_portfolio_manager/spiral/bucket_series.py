from __future__ import annotations

import math
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Sequence

from supabase import Client, create_client  # type: ignore


@dataclass
class BucketSeriesResult:
    series_by_bucket: Dict[str, List[float]]
    population_by_bucket: Dict[str, int]
    composite_series: List[float]


def _iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).replace(microsecond=0).isoformat()


class BucketSeriesComputer:
    def __init__(
        self,
        ts_series: Sequence[datetime],
        composite_weights: Dict[str, float],
        min_population: int = 8,
        max_tokens_per_bucket: int = 64,
    ) -> None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)
        self.ts_series = list(ts_series)
        self.composite_weights = composite_weights
        self.min_population = min_population
        self.max_tokens_per_bucket = max_tokens_per_bucket

    def compute(self) -> BucketSeriesResult:
        if not self.ts_series:
            return BucketSeriesResult({}, {}, [])

        members = self._fetch_bucket_members()
        if not members:
            return BucketSeriesResult({}, {}, [])

        series_by_bucket: Dict[str, List[float]] = {}
        population_by_bucket: Dict[str, int] = {}

        for bucket, rows in members.items():
            agg, population = self._build_bucket_series(bucket, rows)
            if agg:
                series_by_bucket[bucket] = agg
                population_by_bucket[bucket] = population

        composite = self._build_composite_series(series_by_bucket)
        return BucketSeriesResult(series_by_bucket, population_by_bucket, composite)

    def _fetch_bucket_members(self) -> Dict[str, List[dict]]:
        res = (
            self.sb.table("token_cap_bucket")
            .select("token_contract,chain,bucket,market_cap_usd,updated_at")
            .execute()
        )
        rows = res.data or []
        grouped: Dict[str, List[dict]] = defaultdict(list)
        for row in rows:
            bucket = row.get("bucket")
            token = row.get("token_contract")
            chain = row.get("chain")
            mc = float(row.get("market_cap_usd") or 0.0)
            if not bucket or not token or not chain:
                continue
            grouped[bucket].append(
                {
                    "token_contract": token,
                    "chain": chain,
                    "market_cap_usd": mc,
                    "updated_at": row.get("updated_at"),
                }
            )
        for bucket, items in grouped.items():
            items.sort(key=lambda r: float(r.get("market_cap_usd") or 0.0), reverse=True)
        return grouped

    def _build_bucket_series(self, bucket: str, rows: List[dict]) -> tuple[List[float], int]:
        tokens = rows[: self.max_tokens_per_bucket]
        ts_iso = [_iso(ts) for ts in self.ts_series]
        bucket_values = [0.0] * len(ts_iso)
        counts = [0] * len(ts_iso)
        tokens_with_data = 0

        for row in tokens:
            closes = self._fetch_token_series(row["token_contract"], row["chain"])
            if not closes:
                continue
            tokens_with_data += 1
            last_price = None
            for idx, ts in enumerate(ts_iso):
                price = closes.get(ts)
                if price is None and last_price is not None:
                    price = last_price
                if price is None or price <= 0:
                    continue
                bucket_values[idx] += price
                counts[idx] += 1
                last_price = price

        if tokens_with_data < self.min_population:
            return [], tokens_with_data

        agg_series: List[float] = []
        last_value = 0.0
        for idx in range(len(ts_iso)):
            if counts[idx] == 0:
                agg_series.append(last_value)
            else:
                value = bucket_values[idx] / counts[idx]
                agg_series.append(value)
                last_value = value

        return agg_series, tokens_with_data

    def _fetch_token_series(self, token: str, chain: str) -> Dict[str, float]:
        if not self.ts_series:
            return {}
        start_iso = _iso(self.ts_series[0])
        end_iso = _iso(self.ts_series[-1])
        try:
            res = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("timestamp,close_usd")
                .eq("token_contract", token)
                .eq("chain", chain)
                .eq("timeframe", "1h")
                .gte("timestamp", start_iso)
                .lte("timestamp", end_iso)
                .order("timestamp", desc=False)
                .execute()
            )
        except Exception:
            return {}
        rows = res.data or []
        series: Dict[str, float] = {}
        for row in rows:
            ts = row.get("timestamp")
            close = row.get("close_usd")
            if ts is None or close is None:
                continue
            try:
                price = float(close)
            except (TypeError, ValueError):
                continue
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except ValueError:
                continue
            series[_iso(dt)] = price
        return series

    def _build_composite_series(self, series_by_bucket: Dict[str, List[float]]) -> List[float]:
        if not self.ts_series:
            return []
        composite: List[float] = []
        weight_sum = sum(v for v in self.composite_weights.values() if v > 0)
        if weight_sum <= 0:
            weight_sum = 1.0
        length = len(self.ts_series)
        for idx in range(length):
            total = 0.0
            acc_weight = 0.0
            for bucket, weight in self.composite_weights.items():
                if weight <= 0:
                    continue
                series = series_by_bucket.get(bucket)
                if not series or idx >= len(series):
                    continue
                total += weight * series[idx]
                acc_weight += weight
            if acc_weight == 0:
                composite.append(0.0 if not composite else composite[-1])
            else:
                composite.append(total / acc_weight)
        return composite

