from __future__ import annotations

import os
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from supabase import create_client, Client  # type: ignore
from .config import load_pm_config
from .braiding_helpers import bucket_a_e, bucket_score
from .braiding_system import apply_lessons_to_action_size
from .overrides import apply_pattern_strength_overrides, apply_pattern_execution_overrides
from .pattern_keys_v5 import generate_canonical_pattern_key, extract_scope_from_context


def _apply_lessons_sync(sb_client: Optional[Client], base_size_frac: float, context: Dict[str, Any]) -> float:
    """
    Synchronous wrapper for apply_lessons_to_action_size.
    
    Args:
        sb_client: Supabase client (optional, creates if None)
        base_size_frac: Base size fraction
        context: Context dict
    
    Returns:
        Final size fraction after lesson adjustments
    """
    if sb_client is None:
        return base_size_frac
    
    try:
        # Run async function in sync context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use asyncio.run()
            # Just return base size for now (lessons will be applied later)
            return base_size_frac
        else:
            return asyncio.run(apply_lessons_to_action_size(sb_client, base_size_frac, context))
    except Exception:
        # If anything fails, return base size
        return base_size_frac


def _apply_v5_overrides_to_action(
    action: Dict[str, Any],
    position: Dict[str, Any],
    a_final: float,
    e_final: float,
    position_size_frac: float,
    regime_context: Optional[Dict[str, Any]],
    token_bucket: Optional[str],
    sb_client: Optional[Client],
    feature_flags: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Apply v5 pattern-based overrides to an action.
    
    Args:
        action: Action dict
        position: Position dict
        a_final: Final A value
        e_final: Final E value
        position_size_frac: Position size fraction
        regime_context: Regime context
        token_bucket: Token bucket
        sb_client: Supabase client
        feature_flags: Feature flags
    
    Returns:
        Modified action dict
    """
    if not sb_client or not regime_context:
        return action
    
    try:
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        state = uptrend.get("state", "")
        decision_type = action.get("decision_type", "").lower()
        
        # Map decision_type to action_category
        action_category_map = {
            "add": "entry" if not features.get("pm_execution_history", {}).get("last_s1_buy") else "add",
            "trim": "trim",
            "emergency_exit": "exit"
        }
        action_category = action_category_map.get(decision_type, "entry")
        
        # Build action_context for pattern key generation
        action_context = {
            "state": state,
            "timeframe": position.get("timeframe", "1h"),
            "a_final": a_final,
            "e_final": e_final,
            "buy_flag": uptrend.get("buy_flag", False),
            "first_dip_buy_flag": uptrend.get("first_dip_buy_flag", False),
            "reclaimed_ema333": uptrend.get("reclaimed_ema333", False),
            "at_support": (features.get("geometry") or {}).get("at_support", False),
            "market_family": "lowcaps",
        }
        
        # Generate pattern key
        pattern_key, _ = generate_canonical_pattern_key(
            module="pm",
            action_type=decision_type,
            action_context=action_context,
            uptrend_signals=uptrend
        )
        
        if not pattern_key:
            return action
        
        # Extract scope
        bucket_rank = regime_context.get("bucket_rank", []) if regime_context else []
        scope = extract_scope_from_context(
            action_context=action_context,
            regime_context=regime_context or {},
            position_bucket=token_bucket,
            bucket_rank=bucket_rank
        )
        
        # Apply strength overrides (affects size_frac)
        base_levers = {
            "A_value": a_final,
            "E_value": e_final,
            "position_size_frac": position_size_frac
        }
        adjusted_levers = apply_pattern_strength_overrides(
            pattern_key=pattern_key,
            action_category=action_category,
            scope=scope,
            base_levers=base_levers,
            sb_client=sb_client,
            feature_flags=feature_flags
        )
        
        # Adjust size_frac based on overrides
        if adjusted_levers != base_levers:
            size_mult = adjusted_levers.get("position_size_frac", position_size_frac) / position_size_frac if position_size_frac > 0 else 1.0
            action["size_frac"] = min(1.0, max(0.0, action.get("size_frac", 0.0) * size_mult))
        
        # Apply execution overrides (affects reasons/controls)
        plan_controls = action.get("reasons", {})
        adjusted_controls = apply_pattern_execution_overrides(
            pattern_key=pattern_key,
            action_category=action_category,
            scope=scope,
            plan_controls=plan_controls,
            sb_client=sb_client,
            feature_flags=feature_flags
        )
        
        # Merge adjusted controls into reasons
        if adjusted_controls != plan_controls:
            action["reasons"] = {**plan_controls, **adjusted_controls}
        
    except Exception as e:
        # Log but don't fail
        import logging
        logging.getLogger(__name__).warning(f"Error applying v5 overrides: {e}")
    
    return action


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


# ============================================================================
# Helper functions for plan_actions_v4()
# ============================================================================

def _a_to_entry_size(a_final: float, state: str, buy_signal: bool = False, buy_flag: bool = False, first_dip_buy_flag: bool = False) -> float:
    """
    Calculate entry size based on A score and state.
    
    S1 Entries (Initial entries):
    - A >= 0.7 (Aggressive): 50% initial allocation
    - A >= 0.3 (Normal): 30% initial allocation
    - A < 0.3 (Patient): 10% initial allocation
    
    S2/S3 Entries (Add-on entries):
    - A >= 0.7 (Aggressive): 25% initial allocation
    - A >= 0.3 (Normal): 15% initial allocation
    - A < 0.3 (Patient): 5% initial allocation
    """
    if state == "S1" and buy_signal:
        # S1 initial entry
        if a_final >= 0.7:
            return 0.50
        elif a_final >= 0.3:
            return 0.30
        else:
            return 0.10
    elif state in ["S2", "S3"] and (buy_flag or first_dip_buy_flag):
        # S2/S3 add-on entry
        if a_final >= 0.7:
            return 0.25
        elif a_final >= 0.3:
            return 0.15
        else:
            return 0.05
    return 0.0


def _e_to_trim_size(e_final: float) -> float:
    """
    Calculate trim size based on E score.
    
    Base Trim Sizes:
    - E >= 0.7 (Aggressive): 10% trim
    - E >= 0.3 (Normal): 50% trim
    - E < 0.3 (Patient): 3% trim
    """
    if e_final >= 0.7:
        return 0.10
    elif e_final >= 0.3:
        return 0.50
    else:
        return 0.03


def _count_bars_since(timestamp_iso: str, token_contract: str, chain: str, timeframe: str, sb_client: Optional[Client] = None) -> int:
    """
    Count OHLC bars since a timestamp for a specific token/chain/timeframe.
    
    Args:
        timestamp_iso: ISO timestamp string (e.g., "2024-01-15T10:00:00Z")
        token_contract: Token contract address
        chain: Chain (solana, ethereum, base, bsc)
        timeframe: Timeframe (1m, 15m, 1h, 4h)
        sb_client: Optional Supabase client (creates one if not provided)
    
    Returns:
        Number of bars since the timestamp
    """
    if sb_client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            return 0
        sb_client = create_client(url, key)
    
    try:
        result = (
            sb_client.table("lowcap_price_data_ohlc")
            .select("timestamp", count="exact")
            .eq("token_contract", token_contract)
            .eq("chain", chain)
            .eq("timeframe", timeframe)
            .gte("timestamp", timestamp_iso)
            .execute()
        )
        return result.count if hasattr(result, "count") else len(result.data) if result.data else 0
    except Exception:
        return 0


# ============================================================================
# plan_actions_v4() - New PM action planning using Uptrend Engine v4 signals
# ============================================================================

def plan_actions_v4(
    position: Dict[str, Any], 
    a_final: float, 
    e_final: float, 
    phase_meso: str, 
    sb_client: Optional[Client] = None,
    regime_context: Optional[Dict[str, Any]] = None,
    token_bucket: Optional[str] = None,
    feature_flags: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    New PM action planning using Uptrend Engine v4 signals + A/E scores.
    
    Includes:
    - Signal execution tracking (prevents duplicate executions)
    - Profit/allocation multipliers (affects sizing)
    - Cooldown logic (trims: 3 bars per timeframe or new S/R level)
    - Pattern-based overrides (v5 learning system)
    
    Args:
        position: Position dict with features, total_allocation_usd, etc.
        a_final: Final aggressiveness score (0-1)
        e_final: Final exit assertiveness score (0-1)
        phase_meso: Meso phase string
        sb_client: Optional Supabase client for database queries
        regime_context: Optional regime context dict (for override matching)
        token_bucket: Optional token bucket (for override matching)
        feature_flags: Optional feature flags dict
    
    Returns:
        List of action dicts (empty list = no action, no strand emitted)
    """
    features = position.get("features") or {}
    uptrend = features.get("uptrend_engine_v4") or {}  # This IS the payload (no nested "payload" key)
    exec_history = features.get("pm_execution_history") or {}
    
    state = uptrend.get("state", "")
    prev_state = exec_history.get("prev_state", "")
    actions = []
    
    # Compute position_size_frac for override application (from A value)
    # This is a simplified version - in practice it comes from compute_levers()
    # For override purposes, we'll use a default or compute from a_final
    position_size_frac = 0.10 + (a_final * 0.50)  # Linear interpolation: A=0.0 → 10%, A=1.0 → 60%
    
    # Calculate profit/allocation multipliers (used for sizing)
    # Use usd_alloc_remaining for sizing decisions (remaining capacity)
    usd_alloc_remaining = float(position.get("usd_alloc_remaining") or 0.0)
    total_allocation_usd = float(position.get("total_allocation_usd") or 0.0)
    total_extracted_usd = float(position.get("total_extracted_usd") or 0.0)
    total_quantity = float(position.get("total_quantity") or 0.0)
    current_price = float(uptrend.get("price") or 0.0)
    current_position_value = total_quantity * current_price if current_price > 0 else 0.0
    
    # Entry multiplier (for S2/S3 only, S1 uses base size)
    # Profit ratio based on extracted USD vs allocated USD
    profit_ratio = total_extracted_usd / total_allocation_usd if total_allocation_usd > 0 else 0.0
    if profit_ratio >= 1.0:
        entry_multiplier = 0.3  # 100%+ profit: smaller buys
    elif profit_ratio >= 0.0:
        entry_multiplier = 1.0  # Breakeven: normal buys
    else:
        entry_multiplier = 1.5  # In loss: larger buys to average down
    
    # Trim multiplier
    # Allocation deployed ratio: current position value vs total allocated
    allocation_deployed_ratio = current_position_value / total_allocation_usd if total_allocation_usd > 0 else 0.0
    if allocation_deployed_ratio >= 0.8:
        trim_multiplier = 3.0  # Nearly maxed out: take more profit
    elif profit_ratio >= 1.0:
        trim_multiplier = 0.3  # 100%+ profit: take less profit
    elif profit_ratio >= 0.0:
        trim_multiplier = 1.0  # Breakeven: normal trims
    else:
        trim_multiplier = 0.5  # In loss: smaller trims, preserve capital
    
    # Exit Precedence (highest priority)
    if uptrend.get("exit_position"):
        # Full exit - emergency or structural invalidation
        # No lesson matching for full exits (always 100%)
        action = {
            "decision_type": "emergency_exit",
            "size_frac": 1.0,
            "reasons": {
                "flag": "exit_position",
                "exit_reason": uptrend.get("exit_reason", "unknown"),
                "state": state,
            }
        }
        # Apply v5 overrides
        action = _apply_v5_overrides_to_action(
            action, position, a_final, e_final, position_size_frac,
            regime_context, token_bucket, sb_client, feature_flags
        )
        return [action]
    
    # Emergency Exit Handling (S3 only)
    # v4 simplified: emergency_exit = full exit (no bounce protocol)
    if state == "S3" and uptrend.get("emergency_exit"):
        # No lesson matching for full exits (always 100%)
        action = {
            "decision_type": "emergency_exit",
            "size_frac": 1.0,
            "reasons": {
                "flag": "emergency_exit",
                "e_score": e_final,
                "state": state
            }
        }
        # Apply v5 overrides
        action = _apply_v5_overrides_to_action(
            action, position, a_final, e_final, position_size_frac,
            regime_context, token_bucket, sb_client, feature_flags
        )
        return [action]
    
    # Trim Flags (S2/S3) - Check cooldown and S/R level
    if uptrend.get("trim_flag"):
        # Check if we can trim (cooldown or new S/R level)
        last_trim = exec_history.get("last_trim", {})
        last_trim_ts = last_trim.get("timestamp")
        last_trim_sr_level = last_trim.get("sr_level_price")
        
        # Get current S/R level (closest to price)
        geometry = features.get("geometry", {})
        sr_levels = geometry.get("levels", {}).get("sr_levels", []) if isinstance(geometry, dict) else []
        current_sr_level = None
        if sr_levels and current_price > 0:
            try:
                closest_sr = min(sr_levels, key=lambda x: abs(float(x.get("price", 0)) - current_price))
                current_sr_level = float(closest_sr.get("price", 0))
            except Exception:
                pass
        
        can_trim = False
        cooldown_expired = False
        sr_level_changed = False
        
        if not last_trim_ts:
            # Never trimmed before
            can_trim = True
            cooldown_expired = True
        else:
            # Check cooldown (3 bars for position's timeframe)
            timeframe = position.get("timeframe", "1h")
            token_contract = position.get("token_contract", "")
            chain = position.get("token_chain", "").lower()
            
            bars_since_trim = _count_bars_since(last_trim_ts, token_contract, chain, timeframe, sb_client)
            cooldown_expired = bars_since_trim >= 3
            
            # Check if price moved to new S/R level
            if last_trim_sr_level and current_sr_level:
                # Price moved to different S/R level (up or down)
                sr_level_changed = abs(current_sr_level - last_trim_sr_level) > (current_price * 0.01)  # 1% threshold
            
            can_trim = cooldown_expired or sr_level_changed
        
        if can_trim:
            trim_size = _e_to_trim_size(e_final) * trim_multiplier
            trim_size = min(trim_size, 1.0)  # Cap at 100%
            
            # Build context for lesson matching
            scores = uptrend.get("scores") or {}
            context = {
                'state': state,
                'a_bucket': bucket_a_e(a_final),
                'e_bucket': bucket_a_e(e_final),
                'action_type': 'trim',
                'trim_flag': True,
                'ts_score_bucket': bucket_score(scores.get('ts', 0.0)),
                'ox_score_bucket': bucket_score(scores.get('ox', 0.0)),
            }
            
            # Apply lessons
            trim_size = _apply_lessons_sync(sb_client, trim_size, context)
            
            action = {
                "decision_type": "trim",
                "size_frac": trim_size,
                "reasons": {
                    "flag": "trim_flag",
                    "state": state,
                    "e_score": e_final,
                    "ox_score": scores.get("ox", 0.0),
                    "trim_multiplier": trim_multiplier,
                    "cooldown_expired": cooldown_expired,
                    "sr_level_changed": sr_level_changed,
                }
            }
            # Apply v5 overrides
            action = _apply_v5_overrides_to_action(
                action, position, a_final, e_final, position_size_frac,
                regime_context, token_bucket, sb_client, feature_flags
            )
            return [action]
    
    # Entry Gates (S1, S2, S3) - Check execution history
    buy_signal = uptrend.get("buy_signal", False)  # S1
    buy_flag = uptrend.get("buy_flag", False)  # S2 retest or S3 DX
    first_dip_buy_flag = uptrend.get("first_dip_buy_flag", False)  # S3 first dip
    is_new_trade = not position.get("current_trade_id")
    
    # S1: One-time initial entry (only on S0 → S1 transition)
    if buy_signal and state == "S1":
        last_s1_buy = exec_history.get("last_s1_buy")
        if not last_s1_buy:
            # Never bought in S1, and we're in S1 (transitioned from S0)
            entry_size = _a_to_entry_size(a_final, state, buy_signal=True, buy_flag=False, first_dip_buy_flag=False)
            if entry_size > 0:
                # Build context for lesson matching
                scores = uptrend.get("scores") or {}
                context = {
                    'state': state,
                    'a_bucket': bucket_a_e(a_final),
                    'e_bucket': bucket_a_e(e_final),
                    'action_type': 'entry' if is_new_trade else 'add',
                    'buy_signal': True,
                    'buy_flag': False,
                    'ts_score_bucket': bucket_score(scores.get('ts', 0.0)),
                }
                
                # Apply lessons
                entry_size = _apply_lessons_sync(sb_client, entry_size, context)
                
                decision_type = "entry" if is_new_trade else "add"
                action = {
                    "decision_type": decision_type,
                    "size_frac": entry_size,
                    "reasons": {
                        "flag": "buy_signal",
                        "state": state,
                        "a_score": a_final,
                        "ts_score": scores.get("ts", 0.0),
                    }
                }
                # Apply v5 overrides
                action = _apply_v5_overrides_to_action(
                    action, position, a_final, e_final, position_size_frac,
                    regime_context, token_bucket, sb_client, feature_flags
                )
                return [action]
    
    # S2/S3: Reset on trim or state transition
    if (buy_flag or first_dip_buy_flag) and state in ["S2", "S3"]:
        last_buy = exec_history.get(f"last_{state.lower()}_buy", {})
        last_trim_ts = exec_history.get("last_trim", {}).get("timestamp")
        state_transitioned = (prev_state != state)  # State changed (S2 → S3 or S3 → S2)
        
        # Reset conditions: trim happened OR state transitioned
        can_buy = False
        if not last_buy:
            # Never bought in this state
            can_buy = True
        elif state_transitioned:
            # State transitioned (S2 → S3 or S3 → S2) - reset buy eligibility
            can_buy = True
        elif last_trim_ts:
            # Check if trim happened after last buy
            last_buy_ts = last_buy.get("timestamp")
            if last_buy_ts:
                try:
                    trim_dt = datetime.fromisoformat(last_trim_ts.replace("Z", "+00:00"))
                    buy_dt = datetime.fromisoformat(last_buy_ts.replace("Z", "+00:00"))
                    if trim_dt > buy_dt:
                        # Trim happened after last buy - reset buy eligibility
                        can_buy = True
                except Exception:
                    pass
        
        if can_buy:
            entry_size = _a_to_entry_size(a_final, state, buy_signal=False, buy_flag=buy_flag, first_dip_buy_flag=first_dip_buy_flag)
            entry_size = entry_size * entry_multiplier  # Apply profit/allocation multiplier
            if entry_size > 0:
                # Build context for lesson matching
                scores = uptrend.get("scores") or {}
                flag_type = "buy_flag" if buy_flag else ("first_dip_buy_flag" if first_dip_buy_flag else "unknown")
                context = {
                    'state': state,
                    'a_bucket': bucket_a_e(a_final),
                    'e_bucket': bucket_a_e(e_final),
                    'action_type': 'entry' if is_new_trade else 'add',
                    'buy_flag': buy_flag,
                    'first_dip_buy_flag': first_dip_buy_flag,
                    'ts_score_bucket': bucket_score(scores.get('ts', 0.0)),
                    'dx_score_bucket': bucket_score(scores.get('dx', 0.0)),
                }
                
                # Apply lessons
                entry_size = _apply_lessons_sync(sb_client, entry_size, context)
                
                decision_type = "entry" if is_new_trade else "add"
                action = {
                    "decision_type": decision_type,
                    "size_frac": entry_size,
                    "reasons": {
                        "flag": flag_type,
                        "state": state,
                        "a_score": a_final,
                        "ts_score": scores.get("ts", 0.0),
                        "dx_score": scores.get("dx", 0.0),
                        "entry_multiplier": entry_multiplier,
                    }
                }
                # Apply v5 overrides
                action = _apply_v5_overrides_to_action(
                    action, position, a_final, e_final, position_size_frac,
                    regime_context, token_bucket, sb_client, feature_flags
                )
                return [action]
    
    # Reclaimed EMA333 (S3 auto-rebuy)
    if state == "S3" and uptrend.get("reclaimed_ema333"):
        # Check if we already rebought on this reclaim
        last_reclaim_buy = exec_history.get("last_reclaim_buy", {})
        reclaimed_at = uptrend.get("ts")  # Timestamp when EMA333 was reclaimed
        if not last_reclaim_buy or last_reclaim_buy.get("reclaimed_at") != reclaimed_at:
            rebuy_size = _a_to_entry_size(a_final, state, False, False, False) * entry_multiplier
            if rebuy_size > 0:
                # Build context for lesson matching
                scores = uptrend.get("scores") or {}
                context = {
                    'state': state,
                    'a_bucket': bucket_a_e(a_final),
                    'e_bucket': bucket_a_e(e_final),
                    'action_type': 'entry' if is_new_trade else 'add',
                    'reclaimed_ema333': True,
                    'ts_score_bucket': bucket_score(scores.get('ts', 0.0)),
                }
                
                # Apply lessons
                rebuy_size = _apply_lessons_sync(sb_client, rebuy_size, context)
                
                decision_type = "entry" if is_new_trade else "add"
                action = {
                    "decision_type": decision_type,
                    "size_frac": rebuy_size,
                    "reasons": {
                        "flag": "reclaimed_ema333",
                        "state": state,
                        "a_score": a_final,
                        "entry_multiplier": entry_multiplier,
                    }
                }
                # Apply v5 overrides
                action = _apply_v5_overrides_to_action(
                    action, position, a_final, e_final, position_size_frac,
                    regime_context, token_bucket, sb_client, feature_flags
                )
                return [action]
    
    # Default: No action (don't emit strand for holds)
    return actions  # Empty list = no action, no strand


