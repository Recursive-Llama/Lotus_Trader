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
        if action_context.get("is_dx_buy"):
            return "dx"
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
    pattern_key_full = f"module=pm|pattern_key={pattern_key_core}"
    
    return pattern_key_full, action_category


def build_unified_scope(
    position: Dict[str, Any],
    entry_context: Optional[Dict[str, Any]] = None,
    regime_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build canonical 15-dimension scope for Learning System v2.
    
    Fields:
      1. book_id (Asset class/venue) - replaces market_family
      2. timeframe
      3. chain
      4. ticker
      5. mcap_bucket
      6. vol_bucket
      7. age_bucket
      8. curator
      9. intent
      10. bucket_leader
      11. bucket_rank_position
      12. opp_meso_bin
      13. conf_meso_bin
      14. riskoff_meso_bin
      15. bucket_rank_meso_bin
    
    Args:
        position: Position dict (must contain book_id, timeframe, chain, ticker)
        entry_context: Entry context dict (buckets, intent, regimes)
        regime_context: Regime context dict (bucket_rank)
        
    Returns:
        Scope dict with non-None values
    """
    entry_context = entry_context or position.get("entry_context") or {}
    bucket_rank = (regime_context or {}).get("bucket_rank", [])
    mcap_bucket = entry_context.get("mcap_bucket")
    
    # Bucket rank processing
    bucket_leader = None
    bucket_rank_pos = None
    if bucket_rank:
        bucket_leader = bucket_rank[0]
        if mcap_bucket and mcap_bucket in bucket_rank:
            bucket_rank_pos = bucket_rank.index(mcap_bucket) + 1  # 1-indexed
    
    scope = {
        # Primary identifier
        "book_id": position.get("book_id") or entry_context.get("book_id"),
        
        # Token dims
        "timeframe": position.get("timeframe"),
        "chain": position.get("token_chain"),
        "ticker": position.get("token_ticker"),
        
        # Token characteristics  
        "mcap_bucket": mcap_bucket,
        "vol_bucket": entry_context.get("vol_bucket"),
        "age_bucket": entry_context.get("age_bucket"),
        
        # Signal dims
        "curator": entry_context.get("curator"),
        "intent": entry_context.get("intent"),
        
        # Bucket rotation
        "bucket_leader": bucket_leader,
        "bucket_rank_position": bucket_rank_pos,
        
        # 4 Regime meso bins
        "opp_meso_bin": entry_context.get("opp_meso_bin"),
        "conf_meso_bin": entry_context.get("conf_meso_bin"),
        "riskoff_meso_bin": entry_context.get("riskoff_meso_bin"),
        "bucket_rank_meso_bin": entry_context.get("bucket_rank_meso_bin"),
    }
    
    return {k: v for k, v in scope.items() if v is not None}


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
    DEPRECATED: Use build_unified_scope instead.
    Kept for backward compatibility during migration.
    """
    # Best effort reconstruction of position/entry_context from loose args
    position = {
        "book_id": book_id or action_context.get("book_id"),
        "timeframe": action_context.get("timeframe"),
        "token_chain": chain or action_context.get("chain"),
        "token_ticker": action_context.get("ticker"), 
    }
    
    entry_context = {
        "mcap_bucket": position_bucket or action_context.get("bucket"),
        "opp_meso_bin": (regime_states or {}).get("opp_meso_bin"),
        "conf_meso_bin": (regime_states or {}).get("conf_meso_bin"),
        "riskoff_meso_bin": (regime_states or {}).get("riskoff_meso_bin"),
        "bucket_rank_meso_bin": (regime_states or {}).get("bucket_rank_meso_bin"),
    }
    
    # Pass regex_context explicitly to capture bucket_rank
    return build_unified_scope(position, entry_context, regime_context)


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
