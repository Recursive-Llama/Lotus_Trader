from __future__ import annotations

import os
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from supabase import create_client, Client  # type: ignore
from .config import load_pm_config
from .bucketing_helpers import bucket_a_e, bucket_score
from .overrides import apply_pattern_strength_overrides, apply_pattern_execution_overrides
from .pattern_keys_v5 import generate_canonical_pattern_key, extract_scope_from_context
from .exposure import ExposureLookup


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
            bucket_rank=bucket_rank
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
            "book_id": position.get("book_id") or "social",  # Default to "social" if not set
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
            adjusted_levers = apply_pattern_strength_overrides(
                pattern_key=pattern_key,
                action_category=action_category,
                scope=scope,
                base_levers=base_levers,
                sb_client=sb_client,
                feature_flags=feature_flags
            )
            
            if adjusted_levers != base_levers:
                size_mult = adjusted_levers.get("position_size_frac", position_size_frac) / position_size_frac if position_size_frac > 0 else 1.0
            else:
                size_mult = 1.0
            
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
            regime_context, token_bucket, sb_client, feature_flags,
            exposure_lookup=exposure_lookup
        )
        return [action]
    
    # Emergency Exit Handling (any state)
    # emergency_exit = full exit (sell all tokens)
    # Trade closure happens when state transitions to S0
    if uptrend.get("emergency_exit"):
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
            regime_context, token_bucket, sb_client, feature_flags,
            exposure_lookup=exposure_lookup
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
                regime_context, token_bucket, sb_client, feature_flags,
                exposure_lookup=exposure_lookup
            )
            return [action]
    
    # Entry Gates (S1, S2, S3) - Check execution history
    base_buy_signal = uptrend.get("buy_signal", False)  # S1
    buy_flag = uptrend.get("buy_flag", False)  # S2 retest or S3 DX
    first_dip_buy_flag = uptrend.get("first_dip_buy_flag", False)  # S3 first dip
    is_new_trade = not position.get("current_trade_id")
    
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
    
    # S1: One-time initial entry (only on S0 → S1 transition)
    if effective_buy_signal and state == "S1":
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
                    exposure_lookup=exposure_lookup
                )
                return [action]
    
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

    if (effective_buy_flag or first_dip_buy_flag) and state in ["S2", "S3"]:
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
            entry_size = _a_to_entry_size(a_final, state, buy_signal=False, buy_flag=effective_buy_flag, first_dip_buy_flag=first_dip_buy_flag)
            entry_size = entry_size * entry_multiplier  # Apply profit/allocation multiplier
            if entry_size > 0:
                # Build context for lesson matching
                scores = uptrend.get("scores") or {}
                flag_type = "buy_flag" if effective_buy_flag else ("first_dip_buy_flag" if first_dip_buy_flag else "unknown")
                context = {
                    'state': state,
                    'a_bucket': bucket_a_e(a_final),
                    'e_bucket': bucket_a_e(e_final),
                    'action_type': 'entry' if is_new_trade else 'add',
                    'buy_flag': effective_buy_flag,
                    'first_dip_buy_flag': first_dip_buy_flag,
                    'ts_score_bucket': bucket_score(scores.get('ts', 0.0)),
                    'dx_score_bucket': bucket_score(scores.get('dx', 0.0)),
                }
                
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
                    regime_context, token_bucket, sb_client, feature_flags,
                    exposure_lookup=exposure_lookup
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


