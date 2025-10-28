from __future__ import annotations

from typing import Any, Dict, List, Tuple
from .config import load_pm_config


def mode_from_a(a_final: float) -> Tuple[str, float]:
    if a_final >= 0.7:
        return "aggressive", 0.50
    if a_final >= 0.3:
        return "normal", 0.33
    return "patient", 0.10


def e_slice_from_e(e_final: float) -> float:
    if e_final >= 0.7:
        return 0.35
    if e_final >= 0.3:
        return 0.22
    return 0.12


def plan_actions(position: Dict[str, Any], a_final: float, e_final: float, phase_meso: str) -> List[Dict[str, Any]]:
    """Minimal v1 mapping from A/E and geometry flags to actions.
    Returns a list of decision dicts with keys: decision_type, size_frac, reasons.
    """
    actions: List[Dict[str, Any]] = []
    features = position.get("features") or {}
    geometry = (features.get("geometry") if isinstance(features, dict) else None) or {}
    sr_break = (geometry.get("sr_break") or "none").lower()
    sr_conf = float((geometry.get("sr_conf") or 0.0))
    diag_break = (geometry.get("diag_break") or "none").lower()
    diag_conf = float((geometry.get("diag_conf") or 0.0))

    # Reasons collected for audit
    reasons = {
        "sr_break": sr_break,
        "sr_conf": sr_conf,
        "diag_break": diag_break,
        "diag_conf": diag_conf,
        "a_final": a_final,
        "e_final": e_final,
    }

    # Exit ladders (profit targets from avg entry) — v1 simple implementation
    # Exit ladders handled in per-minute position_monitor (runtime). Mapper focuses on structure & readiness.

    # Load config and envelope sizes
    cfg = load_pm_config()
    mode, f_mode = mode_from_a(a_final)
    mode_cfg = (cfg.get("mode_sizes", {}) or {}).get(mode, {"immediate": 0.0, "e1": 0.0, "e2": 0.0})
    at_support = bool(((features.get("geometry") or {}).get("at_support")) if isinstance(features, dict) else False)
    in_res_zone = bool(((features.get("geometry") or {}).get("in_resistance_zone")) if isinstance(features, dict) else False)
    zone_trim_count = int((((features.get("geometry") or {}).get("zone_trim_count")) if isinstance(features, dict) else 0) or 0)
    breakout = ((features.get("geometry") or {}).get("breakout") or {}) if isinstance(features, dict) else {}
    retrace_r = breakout.get("retrace_r")
    r_min, r_max = cfg.get("e2_retrace_window", [0.68, 1.0])

    # Resistance-zone trims: exhaustion signals inside zone (two standard or one strong)
    obv = features.get("obv") or {}
    obv_slope = float(obv.get("obv_slope") or 0.0)
    vo_z = float(features.get("vo_z") or 0.0)
    fall_th = float((cfg.get("obv_slope_per_bar") or {}).get("fall", -0.05))
    voz_cfg = (cfg.get("voz") or {})
    climax_th = float(voz_cfg.get("strong", 0.8)) * 1.5  # strong climax
    rsi_div_flag = float((geometry.get("rsi_div") if isinstance(geometry, dict) else 0.0) or 0.0) < 0.0
    ema_mid_break = bool((geometry.get("ema_mid_15m_break") if isinstance(geometry, dict) else False))
    # Entry pillars (mode-based): RSI divergence, OBV slope up, VO_z moderate+
    rise_th = float((cfg.get("obv_slope_per_bar") or {}).get("rise", 0.05))
    moderate_vo = float(voz_cfg.get("moderate", 0.3))
    bull_div = float((geometry.get("rsi_div") if isinstance(geometry, dict) else 0.0) or 0.0) > 0.0
    pillars = 0
    if bull_div:
        pillars += 1
    if obv_slope >= rise_th:
        pillars += 1
    if vo_z >= moderate_vo:
        pillars += 1
    # Mode-based pillar requirement only
    required = 1 if mode == "aggressive" else (2 if mode == "normal" else 3)
    std_hits = 0
    if rsi_div_flag:
        std_hits += 1
    if obv_slope <= fall_th:
        std_hits += 1
    if ema_mid_break:
        std_hits += 1
    strong_exhaustion = (vo_z >= climax_th and ema_mid_break)
    if in_res_zone and zone_trim_count < 2 and (strong_exhaustion or std_hits >= 2):
        # Moon-bag guard: clamp trim to not breach target when data available
        moon_bag_target = float((features.get("moon_bag_target_frac") if isinstance(features, dict) else None) or (cfg.get("moon_bag_target_frac") or 0.10))
        remaining_frac = features.get("position_remaining_frac") if isinstance(features, dict) else None
        trim_size = e_slice_from_e(e_final)
        clamped = False
        if remaining_frac is not None:
            try:
                rem = float(remaining_frac)
                max_trim_allowed = max(0.0, rem - float(moon_bag_target))
                if trim_size > max_trim_allowed:
                    trim_size = max_trim_allowed
                    clamped = True
            except Exception:
                pass
        if trim_size > 0:
            actions.append({
                "decision_type": "trim",
                "size_frac": trim_size,
                "reasons": {**reasons, "zone": "resistance", "obv_slope": obv_slope, "vo_z": vo_z, "std_hits": std_hits, "strong": strong_exhaustion, "zone_trim_count": zone_trim_count, "moon_bag_target": moon_bag_target, "moon_bag_clamped": clamped},
            })
            return actions

    # E2 breakout retrace add (mode-based pillars only)
    if retrace_r is not None and sr_break != "bear" and diag_break != "bear":
        try:
            r = float(retrace_r)
            if r_min <= r <= r_max and pillars >= required and (sr_break == "bull" or diag_break == "bull" or sr_conf >= 0.5 or diag_conf >= 0.5):
                size_frac = float(mode_cfg.get("e2", 0.0))
                if size_frac > 0:
                    actions.append({
                        "decision_type": "add",
                        "size_frac": size_frac,
                        "reasons": {**reasons, "envelope": "E2", "retrace_r": r, "mode": mode},
                    })
                    return actions
        except Exception:
            pass

    # E1 support/wedge add (mode-based pillars only)
    if at_support and sr_conf >= 0.5 and sr_break != "bear" and diag_break != "bear" and pillars >= required:
        size_frac = float(mode_cfg.get("e1", 0.0))
        if size_frac > 0:
            actions.append({
                "decision_type": "add",
                "size_frac": size_frac,
                "reasons": {**reasons, "envelope": "E1", "mode": mode},
            })
            return actions

    # Profit-only trail fire (pending + momentum overlay)
    trail_pending = bool(((features.get("geometry") or {}).get("trail_pending")) if isinstance(features, dict) else False)
    if trail_pending and (obv_slope < 0.0 or vo_z < 0.0):
        actions.append({
            "decision_type": "trim",
            "size_frac": e_slice_from_e(e_final),
            "reasons": {**reasons, "trail": True, "obv_slope": obv_slope, "vo_z": vo_z},
        })
        return actions

    # DeadScore demotion (hard trigger)
    try:
        dead_score_final = float(features.get("dead_score_final") or features.get("dead_score") or 0.0)
    except Exception:
        dead_score_final = 0.0
    if dead_score_final > 0.6:
        actions.append({
            "decision_type": "demote",
            "size_frac": 0.8,  # sell 80%, keep ~moon-bag
            "reasons": {**reasons, "dead_score_final": dead_score_final},
        })
        return actions

    # Trims require a trigger; do not trim on E alone. v1 triggers: structure breaks.
    if sr_break == "bear" or diag_break == "bear":
        actions.append({
            "decision_type": "trim",
            "size_frac": e_slice_from_e(e_final),
            "reasons": reasons,
        })
        return actions

    # General add: rely on A (mode) and structure confirmation only
    if a_final >= 0.3 and sr_break != "bear" and diag_break != "bear":
        if sr_break == "bull" or diag_break == "bull" or sr_conf >= 0.5 or diag_conf >= 0.5:
            size_frac = f_mode * a_final
            actions.append({
                "decision_type": "add",
                "size_frac": size_frac,
                "reasons": {**reasons, "mode": mode},
            })
            return actions

    # Otherwise hold
    actions.append({
        "decision_type": "hold",
        "size_frac": 0.0,
        "reasons": reasons,
    })
    return actions


