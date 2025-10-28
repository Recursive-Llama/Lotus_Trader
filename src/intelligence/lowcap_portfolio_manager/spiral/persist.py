from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict

from supabase import create_client, Client  # type: ignore
import json


class SpiralPersist:
    def __init__(self) -> None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)

    def write_phase_state(self, token: str, horizon: str, ts: datetime, payload: Dict[str, Any]) -> None:
        row = {
            "token": token,
            "horizon": horizon,
            "ts": ts.replace(second=0, microsecond=0, tzinfo=timezone.utc).isoformat(),
            **payload,
        }
        # Determine prior phase to emit event on flip
        try:
            prior = (
                self.sb.table("phase_state")
                .select("phase,ts")
                .eq("token", token)
                .eq("horizon", horizon)
                .order("ts", desc=True)
                .limit(1)
                .execute()
                .data
                or []
            )
            prior_phase = (prior[0] or {}).get("phase") if prior else None
        except Exception:
            prior_phase = None
        self.sb.table("phase_state").upsert([row], on_conflict="token,ts,horizon").execute()
        # Emit phase_transition on change
        try:
            if prior_phase is not None and str(prior_phase) != str(payload.get("phase")):
                from intelligence.lowcap_portfolio_manager.events.bus import emit
                emit(
                    "phase_transition",
                    {
                        "token": token,
                        "horizon": horizon,
                        "prev": prior_phase,
                        "next": payload.get("phase"),
                        "score": payload.get("score"),
                        "ts": row["ts"],
                    },
                )
        except Exception:
            pass

    def get_latest_phase_state(self, token: str, horizon: str) -> Dict[str, Any] | None:
        res = (
            self.sb.table("phase_state")
            .select("phase,score,ts,dwell_remaining")
            .eq("token", token)
            .eq("horizon", horizon)
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None

    def write_features_portfolio_context(self, features: Dict[str, Any]) -> None:
        """Attach shared portfolio-context features to all active positions.
        Implementation: read active ids + existing features, merge in Python, update per row.
        """
        from copy import deepcopy

        rows = (
            self.sb.table("lowcap_positions")
            .select("id,features")
            .eq("status", "active")
            .limit(1000)
            .execute()
            .data
            or []
        )
        for r in rows:
            pid = r.get("id")
            cur = r.get("features") or {}
            newf = deepcopy(cur)
            newf["portfolio_context"] = features
            self.sb.table("lowcap_positions").update({"features": newf}).eq("id", pid).execute()

    def write_features_token_geometry(self, position_id: str, geometry_updates: Dict[str, Any]) -> None:
        row = (
            self.sb.table("lowcap_positions").select("features").eq("id", position_id).limit(1).execute().data or []
        )
        cur = (row[0].get("features") if row else {}) or {}
        geo = (cur.get("geometry") if isinstance(cur, dict) else {}) or {}
        geo.update(geometry_updates)
        cur["geometry"] = geo
        self.sb.table("lowcap_positions").update({"features": cur}).eq("id", position_id).execute()


