from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

# L2 Lever Engine:
# Phases (Macro/Meso/Micro) and dominance/cut_pressure shape A/E only.
# Downstream Actions use only A/E + geometry/flow confirmations; they never read phases directly.


def _map_meso_policy(phase_meso: str) -> Tuple[float, float]:
    p = (phase_meso or "").lower()
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
        # existing winners patient, new/laggards aggressive; use mid default
        return 0.4, 0.5
    return 0.5, 0.5


def _apply_macro(a: float, e: float, phase_macro: str) -> Tuple[float, float]:
    m = (phase_macro or "").lower()
    if m == "dip":
        return a * 0.6, e * 1.4
    if m == "double-dip":
        return a * 0.8, e * 1.2
    if m == "oh-shit":
        return a * 1.2, e * 0.8
    if m == "recover":
        return a * 1.3, e * 1.0
    if m == "good":
        return a * 1.1, e * 1.1
    if m == "euphoria":
        return a * 1.0, e * 1.4
    return a, e


def _apply_cut_pressure(a: float, e: float, cut_pressure: float, features: Dict[str, Any]) -> Tuple[float, float]:
    """
    Apply cut pressure with 9-position target curve.
    Above 9: exponential dampening
    Below 9: linear easing
    """
    cp = max(0.0, min(1.0, float(cut_pressure or 0.0)))
    active_positions = int(features.get("active_positions", 0))
    
    # Apply base cut pressure
    a_base = a * (1.0 - 0.33 * cp)
    e_base = e * (1.0 + 0.33 * cp)
    
    # Apply 9-position curve
    if active_positions > 9:
        # Exponential dampening above 9
        excess = active_positions - 9
        a_final = a_base * math.exp(-0.10 * excess)
        e_final = e_base * math.exp(+0.10 * excess)
    elif active_positions < 9:
        # Linear easing below 9
        deficit = 9 - active_positions
        a_final = min(1.0, a_base * (1 + 0.05 * deficit))
        e_final = max(0.0, e_base * (1 - 0.05 * deficit))
    else:
        # Exactly 9 positions - no additional adjustment
        a_final = a_base
        e_final = e_base
    
    return a_final, e_final


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _compute_age_component(features: Dict[str, Any]) -> Tuple[float, float]:
    """
    Token age adjustments based on pair creation date
    Returns: (a_boost, e_boost) as multipliers
    """
    # Calculate age from stored pair_created_at
    pair_created_at = features.get("pair_created_at")
    if not pair_created_at:
        return 1.0, 1.0  # No boost if no pair creation date
    
    try:
        created_dt = datetime.fromisoformat(pair_created_at.replace('Z', '+00:00'))
        age_h = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
    except:
        return 1.0, 1.0  # No boost on error
    
    if age_h < 6:
        return 1.15, 1.15  # +15% boost for <6 hours
    elif age_h < 12:
        return 1.10, 1.10  # +10% boost for <12 hours
    elif age_h < 72:  # 3 days
        return 1.05, 1.05  # +5% boost for <3 days
    else:
        return 1.0, 1.0    # No boost for >3 days


def _compute_market_cap_component(features: Dict[str, Any]) -> Tuple[float, float]:
    """
    Market cap adjustments
    Returns: (a_boost, e_boost) as multipliers
    """
    market_cap = float(features.get("market_cap", 0.0))
    
    if market_cap < 100000:  # <$100k
        return 1.15, 1.15  # +15% boost
    elif market_cap < 500000:  # <$500k
        return 1.10, 1.10  # +10% boost
    elif market_cap < 1000000:  # <$1m
        return 1.05, 1.05  # +5% boost
    else:
        return 1.0, 1.0    # No boost for >$1m


def _apply_intent_deltas(a: float, e: float, features: Dict[str, Any]) -> Tuple[float, float, Dict[str, float]]:
    """
    Apply intent-based deltas to A/E scores.
    Technical analysis components removed - only intent channels remain.
    """
    # Intent channels (aggregate simple signals if present)
    intent = features.get("intent_metrics") or {}
    hi_buy = float(intent.get("hi_buy", 0.0))
    med_buy = float(intent.get("med_buy", 0.0))
    profit = float(intent.get("profit", 0.0))
    sell = float(intent.get("sell", 0.0))
    mock = float(intent.get("mock", 0.0))

    deltas = {"dA": 0.0, "dE": 0.0}

    # Intent channels (corrected mock severity)
    deltas["dA"] += 0.25 * _clamp(hi_buy, 0.0, 1.0)
    deltas["dE"] -= 0.10 * _clamp(hi_buy, 0.0, 1.0)
    deltas["dA"] += 0.15 * _clamp(med_buy, 0.0, 1.0)
    deltas["dE"] -= 0.05 * _clamp(med_buy, 0.0, 1.0)
    deltas["dA"] -= 0.15 * _clamp(profit, 0.0, 1.0)
    deltas["dE"] += 0.15 * _clamp(profit, 0.0, 1.0)
    deltas["dA"] -= 0.25 * _clamp(sell, 0.0, 1.0)
    deltas["dE"] += 0.35 * _clamp(sell, 0.0, 1.0)
    deltas["dA"] -= 0.30 * _clamp(mock, 0.0, 1.0)  # Fixed: stronger than profit
    deltas["dE"] += 0.50 * _clamp(mock, 0.0, 1.0)  # Fixed: stronger than profit

    # Clamp combined intent impact per lever to ±0.4
    dA = _clamp(deltas["dA"], -0.4, 0.4)
    dE = _clamp(deltas["dE"], -0.4, 0.4)
    return a + dA, e + dE, {"dA": dA, "dE": dE, "intent_components": {
        "hi_buy": hi_buy, "med_buy": med_buy, "profit": profit, "sell": sell, "mock": mock
    }}


def _compute_position_sizing(a_final: float) -> float:
    """
    Convert continuous A score to position sizing fraction.
    Pure continuous mapping instead of discrete modes.
    """
    # Linear interpolation: A=0.0 → 10%, A=1.0 → 60%
    return 0.10 + (a_final * 0.50)


def compute_levers(phase_macro: str, phase_meso: str, cut_pressure: float, features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute continuous A (add appetite) and E (exit assertiveness) in [0,1].
    Note: Macro/Meso/Micro phases and dominance influence A/E here only.
    Actions (entry/exit/redeploy) downstream rely solely on A/E + geometry/flow.
    """
    # Global components
    a_pol, e_pol = _map_meso_policy(phase_meso)
    a_mac, e_mac = _apply_macro(a_pol, e_pol, phase_macro)
    a_cp, e_cp = _apply_cut_pressure(a_mac, e_mac, cut_pressure, features)
    
    # Per-token components
    a_intent, e_intent, intent_diag = _apply_intent_deltas(a_cp, e_cp, features)
    a_age, e_age = _compute_age_component(features)
    a_mcap, e_mcap = _compute_market_cap_component(features)
    
    # Combine components
    a_base = a_intent
    e_base = e_intent
    
    a_boost = a_age * a_mcap
    e_boost = e_age * e_mcap
    
    # Final calculation
    a_final = _clamp(a_base * a_boost, 0.0, 1.0)
    e_final = _clamp(e_base * e_boost, 0.0, 1.0)
    
    # Continuous position sizing
    position_size_frac = _compute_position_sizing(a_final)
    
    # Enhanced diagnostics
    diagnostics = {
        **intent_diag,
        "components": {
            "global": {"phase": (a_pol, e_pol), "macro": (a_mac, e_mac), "cut_pressure": (a_cp, e_cp)},
            "per_token": {"age": (a_age, e_age), "mcap": (a_mcap, e_mcap)},
            "boosts": {"a_boost": a_boost, "e_boost": e_boost}
        },
        "position_sizing": {"continuous_frac": position_size_frac}
    }
    
    return {
        "A_value": a_final,
        "E_value": e_final,
        "position_size_frac": position_size_frac,
        "diagnostics": diagnostics,
    }


