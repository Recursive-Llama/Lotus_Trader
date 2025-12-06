from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# L2 Lever Engine:
# Regime-driven A/E calculation using Uptrend Engine states across 5 drivers × 3 timeframes.
# Replaces old phase-based system (phase_macro, phase_meso, cut_pressure).
# Keeps: Intent deltas, Bucket multiplier (bucket ordering/rank)
# Removed: Age boost, Market cap boost, Phase-based A/E


def _clamp(x: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi."""
    return max(lo, min(hi, x))


def _compute_bucket_multiplier(
    position_bucket: str | None,
    bucket_context: Dict[str, Any] | None,
    bucket_config: Dict[str, Any] | None,
) -> Tuple[float, Dict[str, Any]]:
    diag = {
        "bucket": position_bucket,
        "rank": None,
        "slope": 0.0,
        "confidence": 0.0,
        "multiplier": 1.0,
    }
    if not position_bucket or not bucket_context or not bucket_config:
        return 1.0, diag

    phases = bucket_context.get("bucket_phases") or {}
    bucket_entry = phases.get(position_bucket) or {}
    ranks = bucket_context.get("bucket_rank") or []
    rank_idx = None
    if position_bucket in ranks:
        rank_idx = ranks.index(position_bucket) + 1

    adjustments = bucket_config.get("rank_adjustments") or {}
    slope_weight = float(bucket_config.get("slope_weight", 0.0))
    min_conf = float(bucket_config.get("min_confidence", 0.0))
    min_mult = float(bucket_config.get("min_multiplier", 0.7))
    max_mult = float(bucket_config.get("max_multiplier", 1.3))

    slope = float(bucket_entry.get("slope") or 0.0)
    confidence = float(bucket_entry.get("confidence") or 0.0)
    diag["rank"] = rank_idx
    diag["slope"] = slope
    diag["confidence"] = confidence

    multiplier = 1.0
    if confidence >= min_conf:
        if rank_idx is not None:
            multiplier += float(adjustments.get(str(rank_idx), 0.0))
        multiplier += slope_weight * slope

    multiplier = _clamp(multiplier, min_mult, max_mult)
    diag["multiplier"] = multiplier
    return multiplier, diag




def _compute_position_sizing(a_final: float) -> float:
    """
    Convert continuous A score to position sizing fraction.
    Pure continuous mapping instead of discrete modes.
    """
    # Linear interpolation: A=0.0 → 10%, A=1.0 → 60%
    return 0.10 + (a_final * 0.50)


def compute_levers(
    features: Dict[str, Any],
    bucket_context: Dict[str, Any] | None = None,
    position_bucket: str | None = None,
    bucket_config: Dict[str, Any] | None = None,
    exec_timeframe: str = "1h",  # Trading timeframe for regime A/E calculation
) -> Dict[str, Any]:
    """
    Compute continuous A (add appetite) and E (exit assertiveness) in [0,1].
    
    Uses regime-driven A/E from Uptrend Engine states (BTC, ALT, bucket, BTC.d, USDT.d)
    across 3 timeframes (1d macro, 1h meso, 1m micro).
    
    Keeps:
    - Intent deltas (hi_buy, profit, sell, mock)
    - Bucket multiplier (bucket ordering/rank)
    
    Removed:
    - Phase-based A/E (phase_macro, phase_meso, cut_pressure)
    - Age boost
    - Market cap boost
    """
    from src.intelligence.lowcap_portfolio_manager.jobs.regime_ae_calculator import (
        RegimeAECalculator,
    )
    
    # Get intent deltas from features
    intent = features.get("intent_metrics") or {}
    intent_delta_a = (
        0.25 * float(intent.get("hi_buy", 0.0)) +
        0.15 * float(intent.get("med_buy", 0.0)) -
        0.15 * float(intent.get("profit", 0.0)) -
        0.25 * float(intent.get("sell", 0.0)) -
        0.30 * float(intent.get("mock", 0.0))
    )
    intent_delta_e = (
        -0.10 * float(intent.get("hi_buy", 0.0)) -
        0.05 * float(intent.get("med_buy", 0.0)) +
        0.15 * float(intent.get("profit", 0.0)) +
        0.35 * float(intent.get("sell", 0.0)) +
        0.50 * float(intent.get("mock", 0.0))
    )
    
    # Clamp intent deltas (capped at ±0.4 per original design)
    intent_delta_a = _clamp(intent_delta_a, -0.4, 0.4)
    intent_delta_e = _clamp(intent_delta_e, -0.4, 0.4)
    
    # Compute regime-based A/E
    try:
        calculator = RegimeAECalculator()
        a_regime, e_regime = calculator.compute_ae_for_token(
            token_bucket=position_bucket or "small",
            exec_timeframe=exec_timeframe,
            intent_delta_a=intent_delta_a,
            intent_delta_e=intent_delta_e,
        )
    except Exception as e:
        # Fallback to neutral if regime calculation fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Regime A/E calculation failed, using neutral: {e}")
        a_regime = 0.5
        e_regime = 0.5
    
    # Apply bucket multiplier (bucket ordering)
    bucket_multiplier, bucket_diag = _compute_bucket_multiplier(position_bucket, bucket_context, bucket_config)
    
    # Final calculation (bucket multiplier affects A, inverse affects E)
    a_final = _clamp(a_regime * bucket_multiplier, 0.0, 1.0)
    e_final = _clamp(e_regime / max(bucket_multiplier, 0.2), 0.0, 1.0)
    
    # Continuous position sizing
    position_size_frac = _compute_position_sizing(a_final)
    
    # Diagnostics
    intent_diag = {
        "dA": intent_delta_a,
        "dE": intent_delta_e,
        "intent_components": {
            "hi_buy": float(intent.get("hi_buy", 0.0)),
            "med_buy": float(intent.get("med_buy", 0.0)),
            "profit": float(intent.get("profit", 0.0)),
            "sell": float(intent.get("sell", 0.0)),
            "mock": float(intent.get("mock", 0.0)),
        }
    }
    
    diagnostics = {
        **intent_diag,
        "components": {
            "regime": {"a_regime": a_regime, "e_regime": e_regime},
            "bucket": {"multiplier": bucket_multiplier},
        },
        "bucket": bucket_diag,
        "position_sizing": {"continuous_frac": position_size_frac},
    }
    
    return {
        "A_value": a_final,
        "E_value": e_final,
        "position_size_frac": position_size_frac,
        "diagnostics": diagnostics,
    }


