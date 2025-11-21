from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Tuple

def fetch_bucket_phase_snapshot(sb_client, horizon: str = "meso") -> Dict[str, Any]:
    bucket_phases: Dict[str, Dict[str, Any]] = {}
    bucket_population: Dict[str, int] = {}
    try:
        res = (
            sb_client.table("phase_state_bucket")
            .select("bucket,phase,score,slope,confidence,population_count,ts")
            .eq("horizon", horizon)
            .order("ts", desc=True)
            .limit(200)
            .execute()
        )
        rows = res.data or []
        for row in rows:
            bucket = row.get("bucket")
            if not bucket or bucket in bucket_phases:
                continue
            bucket_phases[bucket] = {
                "phase": row.get("phase") or "",
                "score": float(row.get("score") or 0.0),
                "slope": float(row.get("slope") or 0.0),
                "confidence": float(row.get("confidence") or 0.0),
                "ts": row.get("ts") or datetime.now(timezone.utc).isoformat(),
            }
            bucket_population[bucket] = int(row.get("population_count") or 0)
    except Exception:
        pass

    bucket_rank = sorted(
        bucket_phases.keys(),
        key=lambda b: bucket_phases[b]["score"],
        reverse=True,
    )

    return {
        "bucket_phases": bucket_phases,
        "bucket_population": bucket_population,
        "bucket_rank": bucket_rank,
    }

