from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def resample_15m_to_1h(rows_15m: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Resample 15m OHLCV rows into 1h OHLCV bars.

    Input rows must contain keys: timestamp, open_native, high_native, low_native, close_native, volume.
    Output bars: {"t0": datetime, "o": float, "h": float, "l": float, "c": float, "v": float}
    """
    if not rows_15m:
        return []

    # Ensure sorted ascending by timestamp
    rows = sorted(rows_15m, key=lambda r: str(r.get("timestamp", "")))

    from collections import defaultdict
    buckets: Dict[datetime, List[Dict[str, Any]]] = defaultdict(list)

    for r in rows:
        ts_raw = str(r.get("timestamp"))
        # Accept ISO strings with or without Z
        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        hour_key = ts.replace(minute=0, second=0, microsecond=0)
        buckets[hour_key].append(r)

    out: List[Dict[str, Any]] = []
    for hour_ts, bucket in sorted(buckets.items(), key=lambda kv: kv[0]):
        if not bucket:
            continue
        bucket_sorted = sorted(bucket, key=lambda r: str(r.get("timestamp", "")))
        o = float(bucket_sorted[0]["open_native"])
        c = float(bucket_sorted[-1]["close_native"])
        h = max(float(b["high_native"]) for b in bucket_sorted)
        l = min(float(b["low_native"]) for b in bucket_sorted)
        v = sum(float(b.get("volume") or 0.0) for b in bucket_sorted)
        out.append({"t0": hour_ts, "o": o, "h": h, "l": l, "c": c, "v": v})

    return out


