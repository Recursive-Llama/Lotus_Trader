from __future__ import annotations

import os
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from supabase import create_client, Client  # type: ignore
from .config import load_pm_config
from .bucketing_helpers import bucket_a_e, bucket_score
from .overrides import apply_pattern_strength_overrides, apply_pattern_execution_overrides
from .pattern_keys_v5 import generate_canonical_pattern_key, extract_scope_from_context
from .exposure import ExposureLookup
from .episode_blocking import is_entry_blocked


def _now_iso() -> str:
    """UTC timestamp helper."""
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# TRIM POOL LIFECYCLE FUNCTIONS
# =============================================================================
# Pool model: { "usd_basis": float, "recovery_started": bool, "dx_count": int,
#               "dx_last_price": float|None, "dx_next_arm": float|None }
# Rule: Once recovery_started=True, next trim wipes remainder (locked profit).

def _empty_pool() -> Dict[str, Any]:
    """Return empty pool structure."""
    return {
        "usd_basis": 0.0,
        "recovery_started": False,
        "dx_count": 0,
        "dx_last_price": None,
        "dx_next_arm": None,
    }


def _get_pool(exec_history: Dict[str, Any]) -> Dict[str, Any]:
    """Get trim pool from execution history, ensuring valid structure."""
    pool = exec_history.get("trim_pool")
    if not pool or not isinstance(pool, dict):
        return _empty_pool()
    return pool


def _on_trim(exec_history: Dict[str, Any], trim_usd: float) -> None:
    """Called when a trim happens. Accumulates or resets pool based on recovery state."""
    pool = _get_pool(exec_history)
    
    if pool.get("recovery_started", False):
        # Recovery already started - new trim creates FRESH pool
        # Old pool remainder becomes locked profit (done, gone)
        exec_history["trim_pool"] = {
            "usd_basis": trim_usd,
            "recovery_started": False,
            "dx_count": 0,
            "dx_last_price": None,
            "dx_next_arm": None,
        }
    else:
        # No recovery yet - ACCUMULATE into usd_basis
        pool["usd_basis"] = pool.get("usd_basis", 0) + trim_usd
        exec_history["trim_pool"] = pool


def _on_s2_dip_buy(exec_history: Dict[str, Any], rebuy_usd: float) -> float:
    """Called when S2 dip buy happens. Clears pool immediately. Returns locked profit."""
    pool = _get_pool(exec_history)
    pool_basis = pool.get("usd_basis", 0)
    
    # Unused portion becomes locked profit
    locked_profit = max(0.0, pool_basis - rebuy_usd)
    
    # Clear pool entirely (S2 is one-shot)
    exec_history["trim_pool"] = _empty_pool()
    
    return locked_profit


def _on_dx_buy(exec_history: Dict[str, Any], fill_price: float, atr: float, dx_atr_mult: float = 6.0) -> None:
    """Called when DX buy happens. Uses STEP LADDER (each arm anchored to last fill)."""
    pool = _get_pool(exec_history)
    
    pool["recovery_started"] = True
    pool["dx_count"] = pool.get("dx_count", 0) + 1
    pool["dx_last_price"] = fill_price
    # STEP LADDER: next arm is N×ATR below THIS fill (arms walk down with fills)
    pool["dx_next_arm"] = fill_price - (dx_atr_mult * atr) if atr > 0 else None
    
    # If 3 DX buys done, clear pool (remainder is locked profit)
    if pool["dx_count"] >= 3:
        exec_history["trim_pool"] = _empty_pool()
    else:
        exec_history["trim_pool"] = pool


def _apply_v5_overrides_to_action(
    action: Dict[str, Any],
    position: Dict[str, Any],
    a_final: float,
    e_final: float,
    position_size_frac: float,
    regime_context: Optional[Dict[str, Any]],
    token_bucket: Optional[str],
    sb_client: Optional[Client],
    feature_flags: Optional[Dict[str, Any]],
    exposure_lookup: Optional[ExposureLookup] = None,
    regime_states: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Apply v5 pattern-based overrides plus exposure skew to an action.
    """
    if not sb_client or not regime_context:
        return action
    
    try:
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        state = uptrend.get("state", "")
        decision_type = action.get("decision_type", "").lower()
        
        action_category_map = {
            "add": "entry" if not features.get("pm_execution_history", {}).get("last_s1_buy") else "add",
            "trim": "trim",
            "emergency_exit": "exit"
        }
        action_category = action_category_map.get(decision_type, "entry")
        
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
        
        pattern_key, _ = generate_canonical_pattern_key(
            module="pm",
            action_type=decision_type,
            action_context=action_context,
            uptrend_signals=uptrend
        )
        
        if not pattern_key:
            return action
        
        bucket_rank = regime_context.get("bucket_rank", []) if regime_context else []
        scope = extract_scope_from_context(
            action_context=action_context,
            regime_context=regime_context or {},
            position_bucket=token_bucket,
            bucket_rank=bucket_rank,
            regime_states=regime_states,
            chain=position.get("token_chain"),
            book_id=position.get("book_id") or (position.get("entry_context") or {}).get("book_id"),
        )
        
        entry_context = position.get("entry_context") or {}
        features = position.get("features") or {}
        
        # Extract state from features.uptrend_engine_v4.state or position.state column
        position_state = None
        if isinstance(features, dict):
            uptrend = features.get("uptrend_engine_v4") or {}
            position_state = uptrend.get("state") or position.get("state")
        else:
            position_state = position.get("state")
        
        scope = {
            **scope,
            # Primary scope dimensions (required for exact matching)
            "chain": entry_context.get("chain") or position.get("token_chain"),
            "timeframe": position.get("timeframe", "1h"),
            "book_id": position.get("book_id") or "onchain_crypto",  # Default to onchain crypto book
            "state": position_state or "S4",  # Default to "S4" if not set
            # Secondary scope dimensions
            "curator": entry_context.get("curator"),
            "mcap_bucket": entry_context.get("mcap_bucket") or scope.get("mcap_bucket"),
            "vol_bucket": entry_context.get("vol_bucket"),
            "age_bucket": entry_context.get("age_bucket"),
            "intent": entry_context.get("intent", "unknown"),
            "mcap_vol_ratio_bucket": entry_context.get("mcap_vol_ratio_bucket"),
        }
        
        learning_mults = action.setdefault("learning_multipliers", {})
        exposure_skew = 1.0
        if exposure_lookup:
            exposure_skew = exposure_lookup.lookup(pattern_key, scope)
        learning_mults["exposure_skew"] = exposure_skew
        
        # Learning factors (pm_strength, exposure_skew) should ONLY affect entries (buy/add), not exits
        # Emergency exits are always 100% regardless of learning
        # Trims should be based on E-score only, not learning overrides
        if decision_type == "emergency_exit":
            # Emergency exit: always 100%, skip all learning factors
            size_mult = 1.0
            final_mult = 1.0
            action["size_frac"] = 1.0
        elif decision_type == "trim":
            # Trim: skip learning factors (based on E-score only)
            size_mult = 1.0
            final_mult = 1.0
            # Keep original trim size_frac (from E-score calculation)
            action["size_frac"] = min(1.0, max(0.0, action.get("size_frac", 0.0)))
        else:
            # Entry/add: apply learning factors normally
            base_levers = {
                "A_value": a_final,
                "E_value": e_final,
                "position_size_frac": position_size_frac
            }
            adjusted_levers, strength_mult = apply_pattern_strength_overrides(
                pattern_key=pattern_key,
                action_category=action_category,
                scope=scope,
                base_levers=base_levers,
                sb_client=sb_client,
                feature_flags=feature_flags
            )
            
            # strength_mult is now explicitly returned (1.0 = neutral)
            size_mult = strength_mult
            
            # Apply exposure_skew to entries
            final_mult = size_mult * exposure_skew
            action["size_frac"] = min(1.0, max(0.0, action.get("size_frac", 0.0) * final_mult))
        
        learning_mults["pm_strength"] = size_mult
        learning_mults["combined_multiplier"] = final_mult
        reasons = action.setdefault("reasons", {})
        reasons["pm_strength"] = size_mult
        reasons["exposure_skew"] = exposure_skew
        reasons["pm_final_multiplier"] = final_mult
        
        plan_controls = action.get("reasons", {})
        adjusted_controls = apply_pattern_execution_overrides(
            pattern_key=pattern_key,
            action_category=action_category,
            scope=scope,
            plan_controls=plan_controls,
            sb_client=sb_client,
            feature_flags=feature_flags
        )
        
        if adjusted_controls != plan_controls:
            action["reasons"] = {**plan_controls, **adjusted_controls}
        
    except Exception as e:
        logging.getLogger(__name__).warning(f"Error applying v5 overrides: {e}")
    
    return action


# Legacy plan_actions() function removed - system now uses plan_actions_v4() exclusively
# Removed functions: plan_actions(), mode_from_a(), e_slice_from_e()
# These were only used by the old fallback system which has been removed


# ============================================================================
# Helper functions for plan_actions_v4()
# ============================================================================

def _a_to_entry_size(a_final: float, state: str, buy_signal: bool = False, buy_flag: bool = False, first_dip_buy_flag: bool = False) -> float:
    """
    Calculate entry size based on A score and state.
    
    S1 Entries (Initial entries) - v2 sizing (more aggressive):
    - A >= 0.7 (Aggressive): 90% of remaining allocation
    - A >= 0.3 (Normal): 60% of remaining allocation
    - A < 0.3 (Patient): 30% of remaining allocation
    
    S2/S3 Entries (Add-on entries) - Pool-based, handled separately:
    - S2 dip buy: 60%/30%/10% of pool_basis
    - S3 DX buy: 20%/10%/3.33% of pool_basis per buy (max 3)
    
    Legacy S2/S3 sizing (for first_dip_buy_flag until Phase 5 cleanup):
    - A >= 0.7 (Aggressive): 25% initial allocation
    - A >= 0.3 (Normal): 15% initial allocation
    - A < 0.3 (Patient): 5% initial allocation
    """
    if state == "S1" and buy_signal:
        # S1 initial entry - v2 sizing (more aggressive)
        if a_final >= 0.7:
            return 0.90
        elif a_final >= 0.3:
            return 0.60
        else:
            return 0.30
    elif state in ["S2", "S3"] and (buy_flag or first_dip_buy_flag):
        # Legacy S2/S3 add-on entry (for first_dip_buy_flag compatibility)
        # Pool-based sizing is handled directly in plan_actions_v4()
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
    
    v2 Trim Sizes (more aggressive):
    - E >= 0.7 (Aggressive): 60% trim
    - E >= 0.3 (Normal): 30% trim
    - E < 0.3 (Patient): 15% trim
    
    Note: Actual trim is base * trim_multiplier (extraction-based).
    Combined with extraction dampening, this allows:
    - Early: 60% * 1.5 = 90% max (capped)
    - Late: 60% * 0.3 = 18% (ride the trend)
    """
    if e_final >= 0.7:
        return 0.60
    elif e_final >= 0.3:
        return 0.30
    else:
        return 0.15


def _count_bars_since(timestamp_iso: str, token_contract: str, chain: str, timeframe: str, sb_client: Optional[Client] = None) -> int:
    """
    Count OHLC bars since a timestamp for a specific token/chain/timeframe.
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

def _calculate_halo_dist(price: float, ema60: float, atr: float) -> float:
    if atr > 0 and ema60 > 0:
        return abs(price - ema60) / atr
    return 999.0 # Far away

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
    feature_flags: Optional[Dict[str, Any]] = None,
    exposure_lookup: Optional[ExposureLookup] = None,
    regime_states: Optional[Dict[str, str]] = None,
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
        exposure_lookup: Optional exposure lookup helper (for exposure_skew multiplier)
    
    Returns:
        List of action dicts (empty list = no action, no strand emitted)
    """
    features = position.get("features") or {}
    uptrend = features.get("uptrend_engine_v4") or {}  # This IS the payload (no nested "payload" key)
    exec_history = features.get("pm_execution_history") or {}
    
    state = uptrend.get("state", "")
    prev_state = exec_history.get("prev_state", "")
    actions = []
    
    # Setup logger for decision-making logs (goes to pm_core.log)
    pm_logger = logging.getLogger("pm_core")
    
    # Extract position context for logging
    token_ticker = position.get("token_ticker") or position.get("token_contract", "?")[:20]
    token_chain = position.get("token_chain", "?")
    timeframe = position.get("timeframe", "?")
    total_quantity = float(position.get("total_quantity") or 0.0)
    status = position.get("status", "unknown")
    current_trade_id = position.get("current_trade_id")
    is_new_trade = not current_trade_id
    
    # Extract engine flags for logging
    buy_signal = uptrend.get("buy_signal", False)
    buy_flag = uptrend.get("buy_flag", False)
    trim_flag = uptrend.get("trim_flag", False)
    emergency_exit = uptrend.get("emergency_exit", False)
    exit_position = uptrend.get("exit_position", False)
    reclaimed_ema333 = uptrend.get("reclaimed_ema333", False)
    first_dip_buy_flag = uptrend.get("first_dip_buy_flag", False)
    
    # Log decision planning start with full context
    pm_logger.info(
        "PLAN ACTIONS START: %s/%s tf=%s | "
        "state=%s prev_state=%s | "
        "flags: buy_signal=%s buy_flag=%s trim_flag=%s emergency_exit=%s exit_position=%s reclaimed_ema333=%s first_dip=%s | "
        "position: qty=%.6f status=%s is_new_trade=%s | "
        "scores: a_final=%.4f e_final=%.4f",
        token_ticker, position.get("token_chain", "?"), timeframe,
        state, prev_state,
        buy_signal, buy_flag, trim_flag, emergency_exit, exit_position, reclaimed_ema333, first_dip_buy_flag,
        total_quantity, status, is_new_trade,
        a_final, e_final
    )
    
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
    
    # Trim multiplier (extraction-based)
    # Key insight: E should care more about what we've taken out than position size
    # This lets us "ride the trend" once we've de-risked
    extraction_ratio = total_extracted_usd / total_allocation_usd if total_allocation_usd > 0 else 0.0
    
    if extraction_ratio >= 3.0:
        trim_multiplier = 0.1   # Big winner - very selective trims
    elif extraction_ratio >= 1.0:
        trim_multiplier = 0.3   # House money - ride the trend
    elif extraction_ratio >= 0.5:
        trim_multiplier = 1.0   # Half extracted - moderate
    else:
        trim_multiplier = 1.5   # Full risk - trim aggressively
    
    pm_logger.debug(
        "TRIM_MULT: %s extraction_ratio=%.2f → multiplier=%.2f",
        token_ticker, extraction_ratio, trim_multiplier
    )
    
    # Exit Precedence (highest priority)
    if uptrend.get("exit_position"):
        # Full exit - emergency or structural invalidation
        # No lesson matching for full exits (always 100%)
        exit_reason = uptrend.get("exit_reason", "unknown")
        pm_logger.info(
            "PLAN ACTIONS: exit_position → emergency_exit | %s/%s tf=%s | "
            "exit_reason=%s state=%s qty=%.6f",
            token_ticker, position.get("token_chain", "?"), timeframe,
            exit_reason, state, total_quantity
        )
        action = {
            "decision_type": "emergency_exit",
            "size_frac": 1.0,
            "reasons": {
                "flag": "exit_position",
                "exit_reason": exit_reason,
                "state": state,
            }
        }
        # Apply v5 overrides
        action = _apply_v5_overrides_to_action(
            action, position, a_final, e_final, position_size_frac,
            regime_context, token_bucket, sb_client, feature_flags,
            exposure_lookup=exposure_lookup,
            regime_states=regime_states,
        )
        pm_logger.info(
            "PLAN ACTIONS: RETURN emergency_exit | %s/%s tf=%s | "
            "size_frac=%.4f (after overrides)",
            token_ticker, position.get("token_chain", "?"), timeframe,
            action.get("size_frac", 1.0)
        )
        return [action]
    
    # Emergency Exit Handling (any state)
    # emergency_exit = full exit (sell all tokens)
    # Trade closure happens when state transitions to S0
    if uptrend.get("emergency_exit"):
        # Gating to avoid repeated actions within the same episode
        last_em_exit_ts = exec_history.get("last_emergency_exit_ts")
        total_quantity = float(position.get("total_quantity") or 0.0)

        # Allow new emergency exit only if none recorded in this episode
        # Episode ends when flag clears (price >= EMA333) or state leaves S3 and re-enters
        already_executed_this_episode = bool(last_em_exit_ts)

        if already_executed_this_episode:
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED emergency_exit | %s/%s tf=%s | "
                "reason: already_executed_this_episode | "
                "last_emergency_exit_ts=%s",
                token_ticker, token_chain, timeframe,
                last_em_exit_ts
            )
            return []

        if total_quantity <= 0:
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED emergency_exit | %s/%s tf=%s | "
                "reason: no_tokens_to_sell | "
                "total_quantity=%.6f | "
                "recording attempt to prevent re-spam",
                token_ticker, token_chain, timeframe,
                total_quantity
            )
            # Record the attempt to prevent immediate re-spam; still allow next episode after flag clears
            exec_history["last_emergency_exit_ts"] = _now_iso()
            features["pm_execution_history"] = exec_history
            return []

        # Calculate exit value BEFORE the sell (for reclaim rebuy sizing)
        exit_value_usd = total_quantity * current_price
        
        # No lesson matching for full exits (always 100%)
        pm_logger.info(
            "PLAN ACTIONS: emergency_exit flag → emergency_exit | %s/%s tf=%s | "
            "state=%s qty=%.6f e_score=%.4f exit_value=$%.2f",
            token_ticker, token_chain, timeframe,
            state, total_quantity, e_final, exit_value_usd
        )
        action = {
            "decision_type": "emergency_exit",
            "size_frac": 1.0,
            "reasons": {
                "flag": "emergency_exit",
                "e_score": e_final,
                "state": state,
                "exit_value_usd": exit_value_usd,  # For reclaim rebuy sizing
            }
        }
        # Apply v5 overrides
        action = _apply_v5_overrides_to_action(
            action, position, a_final, e_final, position_size_frac,
            regime_context, token_bucket, sb_client, feature_flags,
            exposure_lookup=exposure_lookup,
            regime_states=regime_states,
        )
        # Stamp execution history to gate further exits in this episode
        # Also record exit_value_usd for reclaim rebuy sizing
        exec_history["last_emergency_exit_ts"] = _now_iso()
        exec_history["last_emergency_exit"] = {
            "timestamp": _now_iso(),
            "exit_value_usd": exit_value_usd,
            "rebuy_used": False,  # One-time reclaim gate
        }
        features["pm_execution_history"] = exec_history
        pm_logger.info(
            "PLAN ACTIONS: RETURN emergency_exit | %s/%s tf=%s | "
            "size_frac=%.4f (after overrides) | "
            "stamped last_emergency_exit_ts",
            token_ticker, token_chain, timeframe,
            action.get("size_frac", 1.0)
        )
        return [action]
    
    # Trim Flags (S2/S3) - Check cooldown and S/R level
    if uptrend.get("trim_flag"):
        # Check if we can trim (cooldown or new S/R level)
        last_trim = exec_history.get("last_trim", {})
        last_trim_ts = last_trim.get("timestamp")
        last_trim_sr_level = last_trim.get("sr_level_price")
        last_trim_signal = exec_history.get("last_trim_signal", {})
        last_trim_signal_sr_level = last_trim_signal.get("sr_level_price")
        
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

        # Enforce one trim signal per SR level (for both learning and execution)
        sr_level_changed_signal = False
        if current_sr_level:
            if last_trim_signal_sr_level:
                sr_level_changed_signal = abs(current_sr_level - last_trim_signal_sr_level) > (current_price * 0.01)  # 1% threshold
            else:
                sr_level_changed_signal = True
        else:
            # If we cannot identify an SR level, skip actionable trim to avoid duplicate noise without level context
            return []
        
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
        
        # Emit actionable trim only when SR level changed vs last signal and we hold tokens
        if can_trim and sr_level_changed_signal and total_quantity > 0:
            base_trim_size = _e_to_trim_size(e_final)
            trim_size = base_trim_size * trim_multiplier
            # Hard cap trims to avoid full exits masquerading as trims
            max_trim_frac = float(os.getenv("PM_MAX_TRIM_FRAC", "0.9"))  # v2: 90% cap
            trim_size = min(trim_size, max_trim_frac)
            
            scores = uptrend.get("scores") or {}
            ox_score = scores.get("ox", 0.0)
            
            pm_logger.info(
                "PLAN ACTIONS: trim_flag → trim | %s/%s tf=%s | "
                "state=%s qty=%.6f | "
                "trim_size=%.4f (base=%.4f * multiplier=%.4f, capped_at=%.4f) | "
                "e_final=%.4f ox_score=%.4f | "
                "cooldown_expired=%s sr_level_changed=%s sr_level=%.8f",
                token_ticker, token_chain, timeframe,
                state, total_quantity,
                trim_size, base_trim_size, trim_multiplier, max_trim_frac,
                e_final, ox_score,
                cooldown_expired, sr_level_changed, current_sr_level or 0.0
            )
            
            # Build context for lesson matching
            context = {
                'state': state,
                'a_bucket': bucket_a_e(a_final),
                'e_bucket': bucket_a_e(e_final),
                'action_type': 'trim',
                'trim_flag': True,
                'ts_score_bucket': bucket_score(scores.get('ts', 0.0)),
                'ox_score_bucket': bucket_score(ox_score),
            }
            
            action = {
                "decision_type": "trim",
                "size_frac": trim_size,
                "reasons": {
                    "flag": "trim_flag",
                    "state": state,
                    "e_score": e_final,
                    "ox_score": ox_score,
                    "trim_multiplier": trim_multiplier,
                    "cooldown_expired": cooldown_expired,
                    "sr_level_changed": sr_level_changed,
                    "sr_level_price": current_sr_level,
                }
            }
            # Apply v5 overrides
            action = _apply_v5_overrides_to_action(
                action, position, a_final, e_final, position_size_frac,
                regime_context, token_bucket, sb_client, feature_flags,
                exposure_lookup=exposure_lookup,
                regime_states=regime_states,
            )
            pm_logger.info(
                "PLAN ACTIONS: RETURN trim | %s/%s tf=%s | "
                "size_frac=%.4f (after overrides)",
                token_ticker, token_chain, timeframe,
                action.get("size_frac", trim_size)
            )
            return [action]
        else:
            if not can_trim:
                pm_logger.info(
                    "PLAN ACTIONS: BLOCKED trim | %s/%s tf=%s | "
                    "reason: cannot_trim | "
                    "cooldown_expired=%s sr_level_changed=%s",
                    token_ticker, token_chain, timeframe,
                    cooldown_expired, sr_level_changed
                )
            elif not sr_level_changed_signal:
                pm_logger.info(
                    "PLAN ACTIONS: BLOCKED trim | %s/%s tf=%s | "
                    "reason: sr_level_not_changed | "
                    "current_sr=%.8f last_signal_sr=%.8f",
                    token_ticker, token_chain, timeframe,
                    current_sr_level or 0.0, last_trim_signal_sr_level or 0.0
                )
            elif total_quantity <= 0:
                pm_logger.info(
                    "PLAN ACTIONS: BLOCKED trim | %s/%s tf=%s | "
                    "reason: no_tokens_to_trim | qty=%.6f",
                    token_ticker, token_chain, timeframe,
                    total_quantity
                )
    
    # Entry Gates (S1, S2, S3) - Check execution history
    base_buy_signal = uptrend.get("buy_signal", False)  # S1
    buy_flag = uptrend.get("buy_flag", False)  # S2 retest or S3 DX
    first_dip_buy_flag = uptrend.get("first_dip_buy_flag", False)  # S3 first dip
    is_new_trade = not position.get("current_trade_id")
    
    # Log first-dip flag detection
    if first_dip_buy_flag:
        ticker = position.get("token_ticker", position.get("token_contract", "?")[:20])
        logging.getLogger("pm_core").info("PM detected first_dip_buy_flag=True for %s (%s, state=%s, is_new_trade=%s)", 
                                        ticker, position.get("timeframe", "?"), state, is_new_trade)
    
    # ------------------------------------------------------------------------
    # S1 Tuning Logic: Re-evaluate Signal with Overrides
    # ------------------------------------------------------------------------
    effective_buy_signal = base_buy_signal
    
    if state == "S1":
        try:
            # Default Controls (Engine Defaults: TS=0.60 -> 60, Halo=1.0)
            tuned_controls = {'ts_min': 60.0, 'halo_mult': 1.0}
            
            # Build Scope
            action_context_s1 = {
                "state": state,
                "timeframe": position.get("timeframe", "1h"),
                "a_final": a_final,
                "e_final": e_final,
                "market_family": "lowcaps",
                "buy_signal": base_buy_signal
            }
            bucket_rank = regime_context.get("bucket_rank", []) if regime_context else []
            scope = extract_scope_from_context(
                action_context=action_context_s1,
                regime_context=regime_context or {},
                position_bucket=token_bucket,
                bucket_rank=bucket_rank
            )
            # Add entry context
            entry_context = position.get("entry_context") or {}
            scope.update({
                "curator": entry_context.get("curator"),
                "chain": entry_context.get("chain") or position.get("token_chain"),
                "mcap_bucket": entry_context.get("mcap_bucket") or scope.get("mcap_bucket"),
            })
            
            # Apply Overrides
            tuned_controls = apply_pattern_execution_overrides(
                pattern_key="pm.uptrend.S1.entry",
                action_category="tuning", # Placeholder
                scope=scope,
                plan_controls=tuned_controls,
                sb_client=sb_client,
                feature_flags=feature_flags
            )
            
            # Re-evaluate if controls changed
            if tuned_controls['ts_min'] != 60.0 or tuned_controls['halo_mult'] != 1.0:
                s1_diag = (uptrend.get("diagnostics") or {}).get("buy_check") or {}
                slope_ok = s1_diag.get("slope_ok", False)
                
                # TS Check
                ts_with_boost = float(s1_diag.get("ts_with_boost", 0.0)) * 100.0
                tuned_ts_ok = ts_with_boost >= tuned_controls['ts_min']
                
                # Halo Check
                price = float(uptrend.get("price", 0.0))
                ema60 = float(uptrend.get("ema", {}).get("ema60", 0.0))
                atr = float(s1_diag.get("atr", 0.0))
                halo_dist = _calculate_halo_dist(price, ema60, atr)
                tuned_zone_ok = halo_dist <= tuned_controls['halo_mult']
                
                effective_buy_signal = slope_ok and tuned_ts_ok and tuned_zone_ok
                
                if effective_buy_signal != base_buy_signal:
                    logging.getLogger(__name__).info(f"Tuning Override: S1 Signal Flipped {base_buy_signal} -> {effective_buy_signal} (TS:{tuned_controls['ts_min']} Halo:{tuned_controls['halo_mult']})")
                    
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error applying S1 tuning overrides: {e}")
    
    # S1: Retest entry (only after S2 breakout has occurred)
    if effective_buy_signal and state == "S1":
        # Check episode blocking first
        token_contract = position.get("token_contract", "")
        if sb_client and is_entry_blocked(sb_client, token_contract, token_chain, timeframe, "S1"):
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED S1 entry (episode block) | %s/%s tf=%s | "
                "reason: token blocked until success observed",
                token_ticker, token_chain, timeframe
            )
            return []
        
        # NEW: S1 buy only enabled after S2 breakout has occurred
        uptrend_meta = features.get("uptrend_episode_meta") or {}
        s2_episode = uptrend_meta.get("s2_episode")
        if not s2_episode:
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED S1 entry (waiting for S2 breakout) | %s/%s tf=%s | "
                "reason: S1 retest entry only enabled after S2 breakout confirmation",
                token_ticker, token_chain, timeframe
            )
            return []
        
        last_s1_buy = exec_history.get("last_s1_buy")
        if not last_s1_buy:
            # Never bought in S1, and we're in S1 (retest after S2 breakout)
            entry_size = _a_to_entry_size(a_final, state, buy_signal=True, buy_flag=False, first_dip_buy_flag=False)
            scores = uptrend.get("scores") or {}
            
            pm_logger.info(
                "PLAN ACTIONS: buy_signal (S1) → %s | %s/%s tf=%s | "
                "state=%s | "
                "entry_size=%.4f | "
                "a_final=%.4f ts_score=%.4f | "
                "no_last_s1_buy",
                "entry" if is_new_trade else "add",
                token_ticker, token_chain, timeframe,
                state,
                entry_size,
                a_final, scores.get("ts", 0.0)
            )
            
            if entry_size > 0:
                # Build context for lesson matching
                context = {
                    'state': state,
                    'a_bucket': bucket_a_e(a_final),
                    'e_bucket': bucket_a_e(e_final),
                    'action_type': 'entry' if is_new_trade else 'add',
                    'buy_signal': True,
                    'buy_flag': False,
                    'ts_score_bucket': bucket_score(scores.get('ts', 0.0)),
                }
                
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
                    regime_context, token_bucket, sb_client, feature_flags,
                    exposure_lookup=exposure_lookup,
                    regime_states=regime_states,
                )
                pm_logger.info(
                    "PLAN ACTIONS: RETURN %s (S1) | %s/%s tf=%s | "
                    "size_frac=%.4f (after overrides)",
                    decision_type, token_ticker, token_chain, timeframe,
                    action.get("size_frac", entry_size)
                )
                return [action]
            else:
                pm_logger.info(
                    "PLAN ACTIONS: BLOCKED %s (S1) | %s/%s tf=%s | "
                    "reason: entry_size=0",
                    "entry" if is_new_trade else "add",
                    token_ticker, token_chain, timeframe
                )
        else:
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED buy_signal (S1) | %s/%s tf=%s | "
                "reason: already_bought_in_s1 | "
                "last_s1_buy=%s",
                token_ticker, token_chain, timeframe,
                last_s1_buy
            )
    elif effective_buy_signal and state != "S1":
        pm_logger.info(
            "PLAN ACTIONS: BLOCKED buy_signal | %s/%s tf=%s | "
            "reason: wrong_state | "
            "state=%s (expected S1)",
            token_ticker, token_chain, timeframe,
            state
        )
    
    # S2/S3: Reset on trim or state transition
    # ------------------------------------------------------------------------
    # S3 Tuning Logic: Re-evaluate Signal with Overrides (DX & TS)
    # ------------------------------------------------------------------------
    effective_buy_flag = buy_flag
    
    if state == "S3" and not first_dip_buy_flag:
        try:
            # Default Controls (Engine Defaults: TS=60, DX=60)
            tuned_controls = {'ts_min': 60.0, 'dx_min': 60.0}
            
            action_context_s3 = {
                "state": state,
                "timeframe": position.get("timeframe", "1h"),
                "a_final": a_final,
                "e_final": e_final,
                "market_family": "lowcaps",
                "buy_flag": buy_flag
            }
            bucket_rank = regime_context.get("bucket_rank", []) if regime_context else []
            scope_s3 = extract_scope_from_context(
                action_context=action_context_s3,
                regime_context=regime_context or {},
                position_bucket=token_bucket,
                bucket_rank=bucket_rank
            )
            
            entry_context = position.get("entry_context") or {}
            scope_s3.update({
                "curator": entry_context.get("curator"),
                "chain": entry_context.get("chain") or position.get("token_chain"),
                "mcap_bucket": entry_context.get("mcap_bucket") or scope_s3.get("mcap_bucket"),
            })
            
            tuned_controls = apply_pattern_execution_overrides(
                pattern_key="pm.uptrend.S3.add",
                action_category="tuning",
                scope=scope_s3,
                plan_controls=tuned_controls,
                sb_client=sb_client,
                feature_flags=feature_flags
            )
            
            if tuned_controls['dx_min'] != 60.0 or tuned_controls['ts_min'] != 60.0:
                s3_diag = (uptrend.get("diagnostics") or {}).get("s3_buy_check") or {}
                
                # Re-evaluate DX Gate
                edx_suppression = float(s3_diag.get("edx_suppression", 0.0))
                price_position_boost = float(s3_diag.get("price_position_boost", 0.0))
                dx = float(s3_diag.get("dx", 0.0))
                
                tuned_dx_threshold = (tuned_controls['dx_min'] / 100.0) + edx_suppression - price_position_boost
                tuned_dx_threshold = max(0.0, tuned_dx_threshold)
                tuned_dx_ok = dx >= tuned_dx_threshold
                
                # Re-evaluate TS Gate (S3 uses TS+Boost)
                ts_with_boost = float(s3_diag.get("ts_with_boost", 0.0)) * 100.0
                tuned_ts_ok = ts_with_boost >= tuned_controls['ts_min']
                
                # Other gates
                slope_ok = s3_diag.get("slope_ok")
                price_in_zone = s3_diag.get("price_in_discount_zone")
                emergency = s3_diag.get("emergency_exit")
                
                effective_buy_flag = tuned_dx_ok and tuned_ts_ok and slope_ok and price_in_zone and not emergency
                
                if effective_buy_flag != buy_flag:
                    logging.getLogger(__name__).info(f"Tuning Override: S3 Signal Flipped {buy_flag} -> {effective_buy_flag} (DX:{tuned_controls['dx_min']} TS:{tuned_controls['ts_min']})")

        except Exception as e:
            logging.getLogger(__name__).warning(f"Error applying S3 tuning overrides: {e}")

    # ==========================================================================
    # S2 DIP BUY (from trim pool only if not flat)
    # ==========================================================================
    if effective_buy_flag and state == "S2":
        # Check episode blocking first
        token_contract = position.get("token_contract", "")
        if sb_client and is_entry_blocked(sb_client, token_contract, token_chain, timeframe, "S2"):
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED S2 entry (episode block) | %s/%s tf=%s | "
                "reason: token blocked until success observed",
                token_ticker, token_chain, timeframe
            )
            return []
        
        is_flat = total_quantity <= 0
        pool = _get_pool(exec_history)
        pool_basis = pool.get("usd_basis", 0)
        has_pool = pool_basis > 0
        recovery_started = pool.get("recovery_started", False)
        
        # Diagnostic logging: Log full pool structure and exec_history state
        pm_logger.info(
            "POOL_DIAG: S2 buy_flag pool check | %s/%s tf=%s | "
            "exec_history_keys=%s | pool=%s | pool_basis=$%.2f has_pool=%s recovery_started=%s",
            token_ticker, token_chain, timeframe,
            list(exec_history.keys()), pool, pool_basis, has_pool, recovery_started
        )
        
        # S2 dip allowed if: flat OR (has pool AND DX not started)
        can_s2_dip = is_flat or (has_pool and not recovery_started)
        
        pm_logger.info(
            "PLAN ACTIONS: S2 buy_flag | %s/%s tf=%s | "
            "is_flat=%s has_pool=%s (basis=$%.2f) recovery_started=%s → can_s2_dip=%s",
            token_ticker, token_chain, timeframe,
            is_flat, has_pool, pool_basis, recovery_started, can_s2_dip
        )
        
        if can_s2_dip:
            scores = uptrend.get("scores") or {}
            
            if is_flat:
                # Case 1: Flat - use remaining allocation (standard sizing)
                base_entry_size = _a_to_entry_size(a_final, state, buy_signal=False, buy_flag=True, first_dip_buy_flag=False)
                entry_size = base_entry_size * entry_multiplier
                notional = usd_alloc_remaining * entry_size
            else:
                # Case 2: Post-trim - size from pool_basis
                if a_final >= 0.7:
                    rebuy_frac = 0.60
                elif a_final >= 0.3:
                    rebuy_frac = 0.30
                else:
                    rebuy_frac = 0.10
                
                notional = pool_basis * rebuy_frac
                notional = min(notional, usd_alloc_remaining)  # Safety cap
                entry_size = notional / usd_alloc_remaining if usd_alloc_remaining > 0 else 0
            
            pm_logger.info(
                "PLAN ACTIONS: S2 dip buy | %s/%s tf=%s | "
                "notional=$%.2f entry_size=%.4f a_final=%.4f | "
                "pool_basis=$%.2f is_flat=%s",
                token_ticker, token_chain, timeframe,
                notional, entry_size, a_final,
                pool_basis, is_flat
            )
            
            if entry_size > 0:
                decision_type = "entry" if is_new_trade else "add"
                action = {
                    "decision_type": decision_type,
                    "size_frac": entry_size,
                    "notional": notional,  # For pool tracking
                    "reasons": {
                        "flag": "buy_flag",
                        "state": state,
                        "a_score": a_final,
                        "ts_score": scores.get("ts", 0.0),
                        "dx_score": scores.get("dx", 0.0),
                        "entry_multiplier": entry_multiplier,
                        "from_pool": not is_flat,
                        "pool_basis": pool_basis,
                    }
                }
                # Apply v5 overrides
                action = _apply_v5_overrides_to_action(
                    action, position, a_final, e_final, position_size_frac,
                    regime_context, token_bucket, sb_client, feature_flags,
                    exposure_lookup=exposure_lookup,
                    regime_states=regime_states,
                )
                pm_logger.info(
                    "PLAN ACTIONS: RETURN S2 dip %s | %s/%s tf=%s | "
                    "size_frac=%.4f (after overrides)",
                    decision_type, token_ticker, token_chain, timeframe,
                    action.get("size_frac", entry_size)
                )
                return [action]
        else:
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED S2 dip buy | %s/%s tf=%s | "
                "reason: no_pool_or_recovery_started | "
                "has_pool=%s recovery_started=%s",
                token_ticker, token_chain, timeframe,
                has_pool, recovery_started
            )
    
    # ==========================================================================
    # S3 DX BUY (from trim pool, 6×ATR ladder, max 3)
    # ==========================================================================
    if effective_buy_flag and state == "S3":
        # Defensive check: Never buy when in emergency exit zone (price < EMA333)
        emergency_exit_active = uptrend.get("emergency_exit", False)
        if emergency_exit_active:
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED S3 DX buy | %s/%s tf=%s | "
                "reason: emergency_exit=True (price < EMA333)",
                token_ticker, token_chain, timeframe
            )
            return []  # Block all buys below EMA333 - wait for reclaim via reclaimed_ema333 path
        
        # DX zone check: EMA144 < price < EMA333
        ema_data = uptrend.get("ema", {})
        ema144 = ema_data.get("ema144", 0)
        ema333 = ema_data.get("ema333", 0)
        in_dx_zone = ema144 > 0 and ema333 > 0 and ema144 < current_price < ema333
        
        pool = _get_pool(exec_history)
        pool_basis = pool.get("usd_basis", 0)
        has_pool = pool_basis > 0
        dx_count = pool.get("dx_count", 0)
        dx_next_arm = pool.get("dx_next_arm")
        
        # Diagnostic logging: Log full pool structure and exec_history state
        pm_logger.info(
            "POOL_DIAG: S3 buy_flag pool check | %s/%s tf=%s | "
            "exec_history_keys=%s | pool=%s | pool_basis=$%.2f has_pool=%s dx_count=%d",
            token_ticker, token_chain, timeframe,
            list(exec_history.keys()), pool, pool_basis, has_pool, dx_count
        )
        
        # DX gating: in zone, has pool, < 3 DX, price at or below arm (or first buy)
        price_at_arm = dx_next_arm is None or current_price <= dx_next_arm
        can_dx = in_dx_zone and has_pool and dx_count < 3 and price_at_arm
        
        pm_logger.info(
            "PLAN ACTIONS: S3 buy_flag (DX check) | %s/%s tf=%s | "
            "in_dx_zone=%s (ema144=%.8f < price=%.8f < ema333=%.8f) | "
            "has_pool=%s (basis=$%.2f) dx_count=%d dx_next_arm=%s | "
            "price_at_arm=%s → can_dx=%s",
            token_ticker, token_chain, timeframe,
            in_dx_zone, ema144, current_price, ema333,
            has_pool, pool_basis, dx_count, dx_next_arm,
            price_at_arm, can_dx
        )
        
        if can_dx:
            scores = uptrend.get("scores") or {}
            atr = uptrend.get("atr", 0)
            
            # Get tunable ATR multiplier (default 6.0)
            dx_atr_mult = tuned_controls.get("dx_atr_mult", 6.0) if tuned_controls else 6.0
            
            # Per-buy sizing from pool_basis
            if a_final >= 0.7:
                dx_frac = 0.20  # 3 buys × 20% ≈ 60% total
            elif a_final >= 0.3:
                dx_frac = 0.10  # 3 buys × 10% ≈ 30% total
            else:
                dx_frac = 0.0333  # 3 buys × 3.33% ≈ 10% total
            
            notional = pool_basis * dx_frac
            notional = min(notional, usd_alloc_remaining)  # Safety cap
            entry_size = notional / usd_alloc_remaining if usd_alloc_remaining > 0 else 0
            
            pm_logger.info(
                "PLAN ACTIONS: S3 DX buy #%d | %s/%s tf=%s | "
                "notional=$%.2f (pool_basis=$%.2f × frac=%.4f) | "
                "entry_size=%.4f a_final=%.4f | "
                "dx_atr_mult=%.1f atr=%.8f",
                dx_count + 1, token_ticker, token_chain, timeframe,
                notional, pool_basis, dx_frac,
                entry_size, a_final,
                dx_atr_mult, atr
            )
            
            if entry_size > 0:
                decision_type = "add"
                action = {
                    "decision_type": decision_type,
                    "size_frac": entry_size,
                    "notional": notional,  # For pool tracking
                    "reasons": {
                        "flag": "buy_flag",
                        "state": state,
                        "a_score": a_final,
                        "ts_score": scores.get("ts", 0.0),
                        "dx_score": scores.get("dx", 0.0),
                        "entry_multiplier": entry_multiplier,
                        "dx_buy_number": dx_count + 1,
                        "pool_basis": pool_basis,
                        "atr": atr,
                        "dx_atr_mult": dx_atr_mult,
                    }
                }
                # Apply v5 overrides
                action = _apply_v5_overrides_to_action(
                    action, position, a_final, e_final, position_size_frac,
                    regime_context, token_bucket, sb_client, feature_flags,
                    exposure_lookup=exposure_lookup,
                    regime_states=regime_states,
                )
                pm_logger.info(
                    "PLAN ACTIONS: RETURN S3 DX #%d add | %s/%s tf=%s | "
                    "size_frac=%.4f (after overrides)",
                    dx_count + 1, token_ticker, token_chain, timeframe,
                    action.get("size_frac", entry_size)
                )
                return [action]
        else:
            if not in_dx_zone:
                pm_logger.debug(
                    "PLAN ACTIONS: S3 DX skipped | %s/%s | reason: not_in_dx_zone",
                    token_ticker, token_chain
                )
            elif not has_pool:
                pm_logger.debug(
                    "PLAN ACTIONS: S3 DX skipped | %s/%s | reason: no_pool",
                    token_ticker, token_chain
                )
            elif dx_count >= 3:
                pm_logger.debug(
                    "PLAN ACTIONS: S3 DX skipped | %s/%s | reason: max_dx_reached",
                    token_ticker, token_chain
                )
            elif not price_at_arm:
                pm_logger.debug(
                    "PLAN ACTIONS: S3 DX skipped | %s/%s | reason: price_above_arm (%.8f > %.8f)",
                    token_ticker, token_chain, current_price, dx_next_arm
                )
    
    # NOTE: first_dip_buy_flag removed in v2 - DX ladder handles S3 recovery
    
    # Reclaimed EMA333 (S3 auto-rebuy based on exit value)
    if state == "S3" and uptrend.get("reclaimed_ema333"):
        # Check if we have an emergency exit to rebuy from and haven't used it yet
        last_emergency = exec_history.get("last_emergency_exit", {})
        exit_value_usd = last_emergency.get("exit_value_usd", 0)
        rebuy_used = last_emergency.get("rebuy_used", False)
        
        pm_logger.info(
            "PLAN ACTIONS: reclaimed_ema333 detected | %s/%s tf=%s | "
            "state=%s qty=%.6f is_new_trade=%s | "
            "exit_value_usd=$%.2f rebuy_used=%s",
            token_ticker, token_chain, timeframe,
            state, total_quantity, is_new_trade,
            exit_value_usd, rebuy_used
        )
        
        if exit_value_usd > 0 and not rebuy_used:
            # Fractional rebuy sizing based on exit value (not remaining allocation)
            if a_final >= 0.7:
                rebuy_frac = 0.60
            elif a_final >= 0.3:
                rebuy_frac = 0.30
            else:
                rebuy_frac = 0.10
            
            rebuy_notional = exit_value_usd * rebuy_frac
            rebuy_notional = min(rebuy_notional, usd_alloc_remaining)  # Safety cap
            rebuy_size = rebuy_notional / usd_alloc_remaining if usd_alloc_remaining > 0 else 0
            
            if rebuy_size > 0:
                scores = uptrend.get("scores") or {}
                decision_type = "entry" if is_new_trade else "add"
                
                pm_logger.info(
                    "PLAN ACTIONS: reclaimed_ema333 → %s | %s/%s tf=%s | "
                    "rebuy_notional=$%.2f (exit_value=$%.2f × frac=%.2f) | "
                    "rebuy_size=%.4f a_final=%.4f",
                    decision_type, token_ticker, token_chain, timeframe,
                    rebuy_notional, exit_value_usd, rebuy_frac,
                    rebuy_size, a_final
                )
                
                action = {
                    "decision_type": decision_type,
                    "size_frac": rebuy_size,
                    "notional": rebuy_notional,
                    "reasons": {
                        "flag": "reclaimed_ema333",
                        "state": state,
                        "a_score": a_final,
                        "exit_value_usd": exit_value_usd,
                        "rebuy_frac": rebuy_frac,
                    }
                }
                # Apply v5 overrides
                action = _apply_v5_overrides_to_action(
                    action, position, a_final, e_final, position_size_frac,
                    regime_context, token_bucket, sb_client, feature_flags
                )
                
                # Mark rebuy as used (one-time gate)
                exec_history["last_emergency_exit"]["rebuy_used"] = True
                features["pm_execution_history"] = exec_history
                
                pm_logger.info(
                    "PLAN ACTIONS: RETURN reclaimed_ema333 %s | %s/%s tf=%s | "
                    "size_frac=%.4f (after overrides) | marked rebuy_used=True",
                    decision_type, token_ticker, token_chain, timeframe,
                    action.get("size_frac", rebuy_size)
                )
                return [action]
            else:
                pm_logger.info(
                    "PLAN ACTIONS: BLOCKED reclaimed_ema333 buy | %s/%s tf=%s | "
                    "reason: rebuy_size=0",
                    token_ticker, token_chain, timeframe
                )
        elif rebuy_used:
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED reclaimed_ema333 buy | %s/%s tf=%s | "
                "reason: rebuy_already_used",
                token_ticker, token_chain, timeframe
            )
        else:
            pm_logger.info(
                "PLAN ACTIONS: BLOCKED reclaimed_ema333 buy | %s/%s tf=%s | "
                "reason: no_emergency_exit_value (exit_value_usd=$%.2f)",
                token_ticker, token_chain, timeframe, exit_value_usd
            )
    
    # Default: No action (don't emit strand for holds)
    if not actions:
        pm_logger.info(
            "PLAN ACTIONS: RETURN [] (no action) | %s/%s tf=%s | "
            "state=%s flags: buy_signal=%s buy_flag=%s trim_flag=%s | "
            "qty=%.6f status=%s",
            token_ticker, position.get("token_chain", "?"), timeframe,
            state, buy_signal, buy_flag, trim_flag,
            total_quantity, status
        )
    return actions  # Empty list = no action, no strand


