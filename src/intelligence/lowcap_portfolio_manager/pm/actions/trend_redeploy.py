from __future__ import annotations

import os
from typing import Any, Dict

from supabase import create_client, Client  # type: ignore

from src.intelligence.lowcap_portfolio_manager.events import bus


def _mode_from_a(a_final: float) -> tuple[str, float]:
    # Align with PM_System_v3.0 config: 12/23/38% of proceeds
    if a_final >= 0.7:
        return "aggressive", 0.38
    if a_final >= 0.3:
        return "normal", 0.23
    return "patient", 0.12


def _eligible_prechecks(features: Dict[str, Any], phase_meso: str) -> bool:
    geom = (features.get("geometry") or {}) if isinstance(features, dict) else {}
    sr_break = (geom.get("sr_break") or "none").lower()
    sr_conf = float(geom.get("sr_conf") or 0.0)
    rsi_slope = float((features.get("rsi_slope") or 0.0))
    obv = features.get("obv") or {}
    obv_trend = float(obv.get("obv_slope") or 0.0)
    vo_z = float(features.get("vo_z") or 0.0)
    obv_z = float(obv.get("obv_z") or 0.0)
    dead_score = float((features.get("dead_score") or 0.0))
    pm = (phase_meso or "").lower()
    if pm not in {"double-dip", "oh-shit", "recover", "good"}:
        return False
    if sr_break == "bear":
        return False
    if not (rsi_slope > 0 or obv_trend > 0 or sr_break == "bull"):
        return False
    if not (vo_z > 0.5 or obv_z > 0.0 or sr_conf >= 0.5):
        return False
    if dead_score >= 0.4:
        return False
    return True


def _get_client() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    return create_client(url, key)


def _write_trend_add_strand(sb: Client, token: str, size_frac_hint: float, reasons: Dict[str, Any], phase_meso: str, a_value: float, e_value: float) -> None:
    from datetime import datetime, timezone

    row = {
        "token": token,
        "ts": datetime.now(timezone.utc).replace(second=0, microsecond=0).isoformat(),
        "decision_type": "trend_add",
        "size_frac": max(0.0, size_frac_hint),  # hint; executor may use proceeds directly
        "a_value": a_value,
        "e_value": e_value,
        "reasons": reasons,
        "phase_state": {"meso": phase_meso},
        "new_token_mode": False,
    }
    sb.table("ad_strands").insert(row).execute()


def _on_decision_approved(payload: Dict[str, Any]) -> None:
    # Expect payload to include: decision_type, token, realized_proceeds (native units), phase_meso, a_value, e_value
    try:
        if (payload.get("decision_type") or "").lower() != "trim":
            return
        proceeds = float(payload.get("realized_proceeds") or 0.0)
        if proceeds <= 0:
            return
        token = str(payload.get("token") or "")
        if not token:
            return
        sb = _get_client()
        # Fetch features for prechecks
        pos = sb.table("lowcap_positions").select("features").eq("token_contract", token).limit(1).execute().data or []
        features = (pos[0].get("features") if pos else {}) or {}
        phase_meso = str(payload.get("phase_meso") or "")
        if not _eligible_prechecks(features, phase_meso):
            return
        a_value = float(payload.get("a_value") or 0.0)
        mode, frac = _mode_from_a(a_value)
        # We don't convert proceeds to size_frac here; pass hint and proceeds context
        reasons = {
            "trend_redeploy": True,
            "redeploy_frac": frac,
            "redeploy_mode": mode,
            "proceeds_native": proceeds,
        }
        _write_trend_add_strand(sb, token, 0.0, reasons, phase_meso, a_value, float(payload.get("e_value") or 0.0))
    except Exception:
        # Silent safety; this hook should never break the main loop
        return


def register_trend_redeploy_handler() -> None:
    bus.subscribe("decision_approved", _on_decision_approved)


