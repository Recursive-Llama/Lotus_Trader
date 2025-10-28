from __future__ import annotations

import os
import logging
from typing import Any, Dict, List
from datetime import datetime, timezone

from supabase import create_client, Client  # type: ignore
from src.intelligence.lowcap_portfolio_manager.pm.actions import plan_actions
from src.intelligence.lowcap_portfolio_manager.pm.levers import compute_levers


logger = logging.getLogger(__name__)


def _map_meso_to_policy(phase: str) -> tuple[float, float]:
    p = (phase or "").lower()
    if p == "dip":
        return 0.2, 0.8
    if p == "double-dip":
        return 0.4, 0.7
    if p == "oh-shit":
        return 0.9, 0.8
    if p == "recover":
        return 1.0, 0.5
    if p == "good":
        return 0.5, 0.3
    if p == "euphoria":
        return 0.4, 0.5
    return 0.5, 0.5


def _apply_cut_pressure(a: float, e: float, cut_pressure: float) -> tuple[float, float]:
    a2 = max(0.0, min(1.0, a * (1.0 - 0.33 * max(0.0, cut_pressure))))
    e2 = max(0.0, min(1.0, e * (1.0 + 0.33 * max(0.0, cut_pressure))))
    return a2, e2


class PMCoreTick:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)

    def _latest_phase(self) -> Dict[str, Any]:
        # Use portfolio-level meso phase for now
        res = (
            self.sb.table("phase_state")
            .select("phase,score,ts")
            .eq("token", "PORTFOLIO")
            .eq("horizon", "meso")
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else {"phase": None, "score": 0.0}

    def _latest_cut_pressure(self) -> float:
        res = self.sb.table("portfolio_bands").select("cut_pressure").order("ts", desc=True).limit(1).execute()
        rows = res.data or []
        try:
            return float((rows[0] or {}).get("cut_pressure") or 0.0)
        except Exception:
            return 0.0

    def _active_positions(self) -> List[Dict[str, Any]]:
        res = self.sb.table("lowcap_positions").select("id,token_contract,token_chain,token_ticker,features,avg_entry_price").eq("status", "active").limit(2000).execute()
        return res.data or []


    def _write_strands(self, token: str, now: datetime, a_val: float, e_val: float, phase: str, cut_pressure: float, actions: list[dict]) -> None:
        rows = []
        for act in actions:
            # Merge lever diagnostics into reasons for audit
            lever_diag = {}
            try:
                lever_diag = (act.get("lever_diag") or {})  # actions may not include; fallback below
            except Exception:
                lever_diag = {}
            reasons = {**(act.get("reasons") or {}), **lever_diag, "phase_meso": phase, "cut_pressure": cut_pressure}
            # Derive a simple ordered reasons list for audit (stable key order)
            preferred_order = [
                "phase_meso",
                "cut_pressure",
                "envelope",
                "mode",
                "sr_break",
                "diag_break",
                "sr_conf",
                "diag_conf",
                "trail",
                "obv_slope",
                "vo_z",
                "retrace_r",
                "zone",
                "std_hits",
                "strong",
                "zone_trim_count",
                "moon_bag_target",
                "moon_bag_clamped",
            ]
            reasons_ordered: list[dict] = []
            for k in preferred_order:
                if k in reasons:
                    reasons_ordered.append({"name": k, "value": reasons[k]})
            # append any remaining keys deterministically
            for k in sorted(reasons.keys()):
                if k not in {r["name"] for r in reasons_ordered}:
                    reasons_ordered.append({"name": k, "value": reasons[k]})
            rows.append({
                "token": token,
                "ts": now.replace(second=0, microsecond=0, tzinfo=timezone.utc).isoformat(),
                "decision_type": act.get("decision_type"),
                "size_frac": float(act.get("size_frac", 0.0)),
                "a_value": a_val,
                "e_value": e_val,
                "reasons": {"ordered": reasons_ordered, **reasons},
                "phase_state": {"meso": phase},
                "new_token_mode": False,
            })
        if not rows:
            return
        try:
            self.sb.table("ad_strands").insert(rows).execute()
            # Emit decision_approved events (note: realized_proceeds not available here)
            try:
                from src.intelligence.lowcap_portfolio_manager.events.bus import emit
                for r in rows:
                    if str(r.get("decision_type") or "").lower() != "hold":
                        emit("decision_approved", {
                            "token": r["token"],
                            "decision_type": r["decision_type"],
                            "a_value": r["a_value"],
                            "e_value": r["e_value"],
                            "phase_meso": phase,
                            "realized_proceeds": 0.0,
                        })
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"strand write failed for {token}: {e}")

    def run(self) -> int:
        now = datetime.now(timezone.utc)
        meso = self._latest_phase()
        phase = meso.get("phase") or ""
        cp = self._latest_cut_pressure()
        # Load macro phase (portfolio-level); neutral if missing
        macro_row = (
            self.sb.table("phase_state")
            .select("phase,ts")
            .eq("token", "PORTFOLIO")
            .eq("horizon", "macro")
            .order("ts", desc=True)
            .limit(1)
            .execute()
            .data
            or [{}]
        )[0]
        macro_phase = macro_row.get("phase") or ""

        positions = self._active_positions()
        written = 0
        actions_enabled = (os.getenv("ACTIONS_ENABLED", "0") == "1")
        for p in positions:
            token = p.get("token_contract") or p.get("token_ticker") or "UNKNOWN"
            features = p.get("features") or {}
            le = compute_levers(macro_phase, str(phase), cp, features)
            a_final = float(le["A_value"])  # per-position intent deltas + age/mcap boosts
            e_final = float(le["E_value"])  # cut_pressure and macro applied
            position_size_frac = float(le.get("position_size_frac", 0.33))  # continuous sizing
            actions = plan_actions(p, a_final, e_final, str(phase)) if actions_enabled else [{"decision_type": "hold", "size_frac": 0.0, "reasons": {}}]
            # Attach enhanced A/E diagnostics to each action for strand auditing
            try:
                diag = le.get("diagnostics") or {}
                for act in actions:
                    act["lever_diag"] = {
                        **diag,
                        "a_e_components": {
                            "a_final": a_final,
                            "e_final": e_final,
                            "position_size_frac": position_size_frac,
                            "phase_macro": macro_phase,
                            "phase_meso": str(phase),
                            "cut_pressure": cp,
                            "active_positions": len(positions)
                        }
                    }
            except Exception:
                pass
            self._write_strands(str(token), now, a_final, e_final, str(phase), cp, actions)
            written += len(actions)
        logger.info("pm_core_tick wrote %d strands for %d positions", written, len(positions))
        return written


# Event-subscribe path for immediate recompute on structure/trail changes
def _subscribe_events() -> None:
    try:
        from intelligence.lowcap_portfolio_manager.events.bus import subscribe

        def on_structure_change(_payload: dict) -> None:
            try:
                PMCoreTick().run()
            except Exception:
                pass

        subscribe('structure_change', on_structure_change)

        def on_phase_transition(_payload: dict) -> None:
            try:
                # Recompute on phase flips (affects A/E globally)
                PMCoreTick().run()
            except Exception:
                pass

        subscribe('phase_transition', on_phase_transition)

        def on_sr_break(_payload: dict) -> None:
            try:
                PMCoreTick().run()
            except Exception:
                pass

        def on_trail_breach(_payload: dict) -> None:
            try:
                PMCoreTick().run()
            except Exception:
                pass

        subscribe('sr_break_detected', on_sr_break)
        subscribe('ema_trail_breach', on_trail_breach)
    except Exception:
        pass


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    _subscribe_events()
    PMCoreTick().run()


if __name__ == "__main__":
    main()


