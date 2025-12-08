"""
Pattern Key Generation v5 - Canonical Format

Generates canonical pattern keys in the format:
  module=pm|pattern_key=family.state.motif

Where:
  - family: Pattern family (e.g., "uptrend", "range", "breakout")
  - state: Engine state (e.g., "S1", "S2", "S3" for uptrend)
  - motif: Behavioral motif (e.g., "buy_flag", "exhaustion", "trim", "panic_exit")
"""

from typing import Dict, Any, Optional, Tuple


def map_action_type_to_category(action_type: str) -> str:
    """
    Map action_type to action_category.
    
    Args:
        action_type: Raw action type (e.g., "entry_immediate", "E1", "trim", "panic_exit")
    
    Returns:
        Action category: "entry", "add", "trim", or "exit"
    """
    action_type_lower = (action_type or "").lower()
    
    # Entry actions
    if action_type_lower in ["entry_immediate", "e1", "e2", "entry"]:
        return "entry"
    
    # Add actions (scaling up)
    if action_type_lower in ["add", "scale_up"]:
        return "add"
    
    # Trim actions (partial exits)
    if action_type_lower in ["trim", "partial_exit"]:
        return "trim"
    
    # Exit actions (full exits)
    if action_type_lower in ["cut", "emergency_exit", "panic_exit", "exit"]:
        return "exit"
    
    if action_type_lower == "allocation":
        return "allocation"
    
    # Default fallback
    return "entry"


def determine_motif(action_type: str, action_context: Dict[str, Any], uptrend_signals: Optional[Dict[str, Any]] = None) -> str:
    """
    Determine the behavioral motif from action context and signals.
    
    Args:
        action_type: Action type (e.g., "entry_immediate", "trim")
        action_context: Action context dict
        uptrend_signals: Uptrend engine signals (optional)
    
    Returns:
        Motif string (e.g., "buy_flag", "exhaustion", "trim", "panic_exit")
    """
    action_type_lower = (action_type or "").lower()
    uptrend_signals = uptrend_signals or {}
    
    # Entry motifs
    if action_type_lower in ["entry_immediate", "e1", "e2", "entry", "buy", "rebuy"]:
        # Check for buy flags
        if action_context.get("buy_flag") or uptrend_signals.get("buy_flag"):
            return "buy_flag"
        if action_context.get("first_dip_buy_flag") or uptrend_signals.get("first_dip_buy_flag"):
            return "first_dip_buy"
        if action_context.get("reclaimed_ema333"):
            return "reclaimed_ema333"
        # Default entry motif
        return "entry"
    
    # Add motifs
    if action_type_lower == "add":
        # Check for specific add triggers
        if uptrend_signals.get("exhaustion"):
            return "exhaustion_add"  # Adding despite exhaustion (rare)
        return "add"
    
    # Trim motifs
    if action_type_lower == "trim":
        # Check for trim triggers
        if uptrend_signals.get("exhaustion"):
            return "exhaustion_trim"
        if action_context.get("at_support"):
            return "support_trim"
        return "trim"
    
    # Exit motifs
    if action_type_lower in ["cut", "emergency_exit", "panic_exit", "exit", "sell"]:
        if action_type_lower == "panic_exit":
            return "panic_exit"
        if uptrend_signals.get("exhaustion"):
            return "exhaustion_exit"
        return "exit"
    
    if action_type_lower == "allocation":
        return "allocation"
    
    # Default fallback
    return "unknown"


def determine_family(module: str, action_context: Dict[str, Any], uptrend_signals: Optional[Dict[str, Any]] = None) -> str:
    """
    Determine the pattern family.
    
    For PM: Currently only "uptrend" is supported (from Uptrend Engine v4).
    Future: Could add "range", "breakout", "mean_revert" based on market conditions.
    
    Args:
        module: "pm" or "dm"
        action_context: Action context dict
        uptrend_signals: Uptrend engine signals (optional)
    
    Returns:
        Family string (e.g., "uptrend")
    """
    if module == "pm":
        # For now, PM only has uptrend engine
        # Future: could detect range/breakout from market conditions
        return "uptrend"
    elif module == "dm":
        # DM families could be based on curator/chain/intent
        # For now, use a generic family
        return "dm_pattern"
    else:
        return "unknown"


def generate_canonical_pattern_key(
    module: str,
    action_type: str,
    action_context: Dict[str, Any],
    uptrend_signals: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    Generate canonical pattern key in format: module=pm|pattern_key=family.state.motif
    
    Args:
        module: "pm" or "dm"
        action_type: Raw action type (e.g., "entry_immediate", "trim")
        action_context: Action context dict (must include "state" for PM)
        uptrend_signals: Uptrend engine signals (optional, for PM)
    
    Returns:
        Tuple of (pattern_key, action_category)
        pattern_key: "module=pm|pattern_key=uptrend.S1.buy_flag"
        action_category: "entry", "add", "trim", or "exit"
    """
    # Determine components
    family = determine_family(module, action_context, uptrend_signals)
    state = action_context.get("state", "Unknown")
    motif = determine_motif(action_type, action_context, uptrend_signals)
    action_category = map_action_type_to_category(action_type)
    
    # Build canonical pattern key
    pattern_key_core = f"{family}.{state}.{motif}"
    pattern_key_full = f"module={module}|pattern_key={pattern_key_core}"
    
    return pattern_key_full, action_category


def extract_scope_from_context(
    action_context: Dict[str, Any],
    regime_context: Dict[str, Any],
    position_bucket: Optional[str] = None,
    bucket_rank: Optional[list] = None,
    regime_states: Optional[Dict[str, str]] = None,
    chain: Optional[str] = None,
    book_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract scope dimensions from action context and regime context.
    
    Args:
        action_context: Action context dict
        regime_context: Regime context from _get_regime_context()
        position_bucket: Token's cap bucket (e.g., "micro")
        bucket_rank: Bucket rank list (e.g., ["micro", "nano", "mid", ...])
    
    Returns:
        Scope dict with all 10 dimensions
    """
    # Bucket context
    bucket_leader = None
    bucket_rank_position = None
    if bucket_rank and len(bucket_rank) > 0:
        bucket_leader = bucket_rank[0]
        if position_bucket and position_bucket in bucket_rank:
            bucket_rank_position = bucket_rank.index(position_bucket) + 1  # 1-indexed
    
    # Market/token dims
    market_family = action_context.get("market_family") or "lowcaps"
    bucket = position_bucket or action_context.get("bucket") or "unknown"
    timeframe = action_context.get("timeframe") or "1h"
    
    # Behavioral dims (A_mode and E_mode from action_context or derived from A/E values)
    A_mode = action_context.get("A_mode")
    E_mode = action_context.get("E_mode")
    
    # If not provided, derive from A/E values if available
    if not A_mode and "a_final" in action_context:
        a_final = float(action_context.get("a_final", 0.5))
        if a_final < 0.33:
            A_mode = "patient"
        elif a_final < 0.67:
            A_mode = "normal"
        else:
            A_mode = "aggressive"
    
    if not E_mode and "e_final" in action_context:
        e_final = float(action_context.get("e_final", 0.5))
        if e_final < 0.33:
            E_mode = "patient"
        elif e_final < 0.67:
            E_mode = "normal"
        else:
            E_mode = "aggressive"
    
    # Build scope dict (no legacy phase fields; regime states provided separately)
    scope = {
        "bucket_leader": bucket_leader,
        "bucket_rank_position": bucket_rank_position,
        "market_family": market_family,
        "bucket": bucket,
        "timeframe": timeframe,
        "A_mode": A_mode or "unknown",
        "E_mode": E_mode or "unknown",
    }

    # Add chain/book if provided
    if chain:
        scope["chain"] = chain
    if book_id:
        scope["book_id"] = book_id

    # Add regime driver S-states (btc/alt/bucket/btcd/usdt.d per macro/meso/micro)
    if regime_states:
        scope.update({k: v for k, v in regime_states.items() if v is not None})
    
    # Remove None values
    scope = {k: v for k, v in scope.items() if v is not None}
    
    return scope


def extract_controls_from_action(
    action_context: Dict[str, Any],
    uptrend_signals: Optional[Dict[str, Any]] = None,
    applied_knobs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract controls (signals + applied knobs) from action.
    
    Args:
        action_context: Action context dict
        uptrend_signals: Uptrend engine signals
        applied_knobs: Applied execution knobs (from plan/overrides)
    
    Returns:
        Controls dict with signals and applied_knobs
    """
    uptrend_signals = uptrend_signals or {}
    applied_knobs = applied_knobs or {}
    
    # Extract signals
    scores = uptrend_signals.get("scores") or {}
    signals = {
        "TS": float(scores.get("ts", 0.0)),
        "OX": float(scores.get("ox", 0.0)),
        "DX": float(scores.get("dx", 0.0)),
        "EDX": float(scores.get("edx", 0.0)),
        "OBV_z": float(uptrend_signals.get("obv_z", 0.0)),
        "volatility_bucket": action_context.get("volatility_bucket"),
        "wickiness_flag": uptrend_signals.get("wickiness_flag", False)
    }
    
    # Applied knobs (from plan or overrides)
    knobs = {
        "entry_delay_bars": applied_knobs.get("entry_delay_bars"),
        "phase1_frac": applied_knobs.get("phase1_frac"),
        "phase_scaling": applied_knobs.get("phase_scaling"),
        "trim_delay": applied_knobs.get("trim_delay"),
        "wait_n_bars_after_trim": applied_knobs.get("wait_n_bars_after_trim"),
        "panic_trigger_level": applied_knobs.get("panic_trigger_level"),
        "trail_speed": applied_knobs.get("trail_speed"),
        "min_ts_for_add": applied_knobs.get("min_ts_for_add"),
        "min_dx_for_add": applied_knobs.get("min_dx_for_add"),
        "max_edx_for_add": applied_knobs.get("max_edx_for_add"),
        "min_ox_for_trim": applied_knobs.get("min_ox_for_trim"),
        "wait_for_signal_x": applied_knobs.get("wait_for_signal_x")
    }
    
    # Remove None values
    signals = {k: v for k, v in signals.items() if v is not None}
    knobs = {k: v for k, v in knobs.items() if v is not None}
    
    return {
        "signals": signals,
        "applied_knobs": knobs
    }

