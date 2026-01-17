"""
A/E Posture Calculator v2

Flag-driven, no regime soup. Strength is first-class.

Changes from v1 (regime_ae_calculator.py):
- No 5-driver × 3-timeframe × state/flag/transition deltas
- Simple: active flags from regime drivers → A/E deltas
- Strength is applied AFTER base A/E (not mixed in)
- Clean separation: flags set posture, strength adjusts it
"""

from __future__ import annotations
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AEConfig:
    """Configuration for A/E calculation."""
    
    # Driver weights (sum effects, higher = more influence)
    driver_weights: Dict[str, float] = field(default_factory=lambda: {
        "usdtd": 1.0,    # Strongest (inverse - USDT.d up = risk-off)
        "bucket": 0.9,   # Local signal (nano/small/mid/big driver)
        "btcd": 0.7,     # Inverse (BTC.d up = alts down)
        "alt": 0.5,      # ALT index
        "btc": 0.3,      # BTC (weakest - already reflected in others)
    })
    
    # Flag effects (base delta per flag type)
    flag_effects: Dict[str, float] = field(default_factory=lambda: {
        "buy": 0.15,
        "trim": 0.20,
        "emergency": 0.40,
    })
    
    # Strength caps
    strength_cap: float = 0.25
    
    # Base values
    a_base: float = 0.5
    e_base: float = 0.5


# Inverse drivers (their BUY = our risk-off)
INVERSE_DRIVERS = {"usdtd", "btcd"}


def compute_ae_v2(
    regime_flags: Dict[str, Dict[str, bool]],
    token_bucket: str = "unknown",
    config: Optional[AEConfig] = None,
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Compute A/E from active flags.
    
    Args:
        regime_flags: Dict of driver -> {"buy": bool, "trim": bool, "emergency": bool}
                     Drivers: "usdtd", "bucket", "btcd", "alt", "btc"
        token_bucket: For logging
        config: Optional configuration (uses defaults if None)
    
    Returns:
        Tuple of (A, E, diagnostics)
    """
    config = config or AEConfig()
    
    A = config.a_base
    E = config.e_base
    
    diagnostics: Dict[str, Any] = {
        "base": {"A": config.a_base, "E": config.e_base},
        "flag_contributions": [],
    }
    
    for driver, weight in config.driver_weights.items():
        flags = regime_flags.get(driver, {})
        is_inverse = driver in INVERSE_DRIVERS
        
        for flag_type in ["buy", "trim", "emergency"]:
            if not flags.get(flag_type):
                continue
            
            effect = config.flag_effects.get(flag_type, 0)
            delta_a = 0.0
            delta_e = 0.0
            
            # Determine direction
            if flag_type == "buy":
                if is_inverse:
                    delta_a = -effect * weight  # Risk-off
                    delta_e = +effect * weight
                else:
                    delta_a = +effect * weight  # Risk-on
                    delta_e = -effect * weight
            
            elif flag_type == "trim":
                if is_inverse:
                    delta_a = +effect * weight  # Risk-on (dominance falling)
                    delta_e = -effect * weight
                else:
                    delta_a = -effect * weight  # Risk-off
                    delta_e = +effect * weight
            
            elif flag_type == "emergency":
                # Emergency is always risk-off (reduce exposure)
                delta_a = -effect * weight
                delta_e = +effect * weight
            
            A += delta_a
            E += delta_e
            
            diagnostics["flag_contributions"].append({
                "driver": driver,
                "flag": flag_type,
                "weight": weight,
                "inverse": is_inverse,
                "delta_a": round(delta_a, 4),
                "delta_e": round(delta_e, 4),
            })
    
    # Clamp before strength (strength added later)
    A = max(0.0, min(1.0, A))
    E = max(0.0, min(1.0, E))
    
    diagnostics["after_flags"] = {"A": round(A, 4), "E": round(E, 4)}
    
    # Log computation
    active_flags = {d: [f for f, v in fl.items() if v] for d, fl in regime_flags.items() if any(fl.values())}
    logger.info(
        "AE_V2_COMPUTED: bucket=%s | flags=%s | base: A=%.3f E=%.3f | after_flags: A=%.3f E=%.3f",
        token_bucket,
        active_flags,
        config.a_base, config.e_base,
        A, E,
    )
    
    return A, E, diagnostics


def apply_strength_to_ae(
    a_base: float,
    e_base: float,
    strength_mult: float,
    pattern_key: str = "",
    config: Optional[AEConfig] = None,
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Apply learned strength to A/E.
    
    Strength > 1.0 means pattern is good → A↑, E↓
    Strength < 1.0 means pattern is bad → A↓, E↑
    
    Args:
        a_base: Base A from flags
        e_base: Base E from flags
        strength_mult: Learned strength multiplier (1.0 = neutral)
        pattern_key: For logging
        config: Optional configuration
    
    Returns:
        Tuple of (A_final, E_final, diagnostics)
    """
    config = config or AEConfig()
    
    # Convert multiplier to effect: 1.0 → 0, 1.5 → +0.25 (capped), 0.5 → -0.25 (capped)
    strength_effect = (strength_mult - 1.0)
    strength_effect = max(-config.strength_cap, min(config.strength_cap, strength_effect))
    
    A_final = a_base + strength_effect
    E_final = e_base - strength_effect  # Inverse: good pattern → less urgency to exit
    
    # Final clamp
    A_final = max(0.0, min(1.0, A_final))
    E_final = max(0.0, min(1.0, E_final))
    
    diagnostics = {
        "strength_mult": round(strength_mult, 4),
        "strength_effect": round(strength_effect, 4),
        "a_base": round(a_base, 4),
        "e_base": round(e_base, 4),
        "A_final": round(A_final, 4),
        "E_final": round(E_final, 4),
    }
    
    logger.info(
        "AE_V2_STRENGTH: pattern=%s | strength=%.3f (effect=%.3f) | A: %.3f → %.3f | E: %.3f → %.3f",
        pattern_key,
        strength_mult, strength_effect,
        a_base, A_final,
        e_base, E_final,
    )
    
    return A_final, E_final, diagnostics


def get_regime_book_id(book_id: str) -> str:
    """
    Map crypto book_ids to shared regime driver book_id.
    
    All crypto markets (onchain, spot, perps) use the same crypto regime drivers.
    Other asset classes (stocks, etc.) use their own regime drivers.
    
    Args:
        book_id: Position's book_id (e.g., "perps", "onchain_crypto", "stock_perps")
    
    Returns:
        Regime driver book_id to query (e.g., "onchain_crypto" for crypto, original for others)
    """
    CRYPTO_BOOK_IDS = {"onchain_crypto", "perps", "spot_crypto", "perp_crypto"}
    if book_id in CRYPTO_BOOK_IDS:
        return "onchain_crypto"  # All crypto uses same regime drivers
    return book_id  # Other asset classes use their own


def extract_regime_flags(
    sb_client,
    token_bucket: str,
    book_id: str = "onchain_crypto",
) -> Dict[str, Dict[str, bool]]:
    """
    Extract current flags from regime driver positions.
    
    Args:
        sb_client: Supabase client
        token_bucket: Token's cap bucket (e.g., "micro")
        book_id: Position's book_id (e.g., "perps", "onchain_crypto", "stock_perps")
                 Will be mapped to regime driver book_id internally
    
    Returns:
        Dict of driver -> {"buy": bool, "trim": bool, "emergency": bool}
    """
    flags: Dict[str, Dict[str, bool]] = {}
    
    # Map crypto book_ids to shared regime driver book_id
    regime_book_id = get_regime_book_id(book_id)
    
    # Drivers to check (map internal key to ticker)
    drivers = {
        "usdtd": "USDT.d",
        "bucket": token_bucket,  # "nano", "small", "mid", "big"
        "btcd": "BTC.d",
        "alt": "ALT",
        "btc": "BTC",
    }
    
    for key, ticker in drivers.items():
        try:
            result = (
                sb_client.table("lowcap_positions")
                .select("features")
                .eq("token_ticker", ticker)
                .eq("status", "regime_driver")
                .eq("book_id", regime_book_id)  # Use mapped book_id
                .limit(1)
                .execute()
            )
            
            if result.data:
                features = result.data[0].get("features", {})
                uptrend = features.get("uptrend_engine_v4", {})
                
                flags[key] = {
                    "buy": uptrend.get("buy_signal", False) or uptrend.get("buy_flag", False),
                    "trim": uptrend.get("trim_flag", False),
                    "emergency": uptrend.get("emergency_exit", False),
                }
            else:
                flags[key] = {"buy": False, "trim": False, "emergency": False}
        except Exception as e:
            logger.warning(f"AE_V2: Failed to get regime flags for {ticker}: {e}")
            flags[key] = {"buy": False, "trim": False, "emergency": False}
    
    return flags


def compute_ae_v2_with_flags_lookup(
    sb_client,
    token_bucket: str,
    book_id: str = "onchain_crypto",
    config: Optional[AEConfig] = None,
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Convenience function that extracts flags and computes A/E.
    
    Returns:
        Tuple of (A, E, diagnostics)
    """
    regime_flags = extract_regime_flags(sb_client, token_bucket, book_id)
    return compute_ae_v2(regime_flags, token_bucket, config)

