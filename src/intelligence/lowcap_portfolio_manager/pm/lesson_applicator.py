"""
Learning System v2: Lesson Applicator
Applies learned tuning overrides (gate adjustments) to the PM decision logic.

Reads from pm_overrides table and applies tuning_params deltas.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from src.intelligence.lowcap_portfolio_manager.pm.pattern_keys_v5 import build_unified_scope

logger = logging.getLogger("learning_system")

# Cache overrides to avoid DB hits every tick
_OVERRIDE_CACHE = {}
_LAST_CACHE_UPDATE = 0
CACHE_TTL = 300  # 5 minutes

def apply_tuning_overrides(
    base_controls: Dict[str, Any],
    position: Dict[str, Any],
    sb_client: Any
) -> Dict[str, Any]:
    """
    Apply tuning overrides to base controls.
    
    1. Fetches relevant overrides from pm_overrides
    2. Selects most specific matching override (Tuning v2 rule)
    3. Applies deltas from tuning_params to base_controls
    
    Args:
        base_controls: Base control parameters (e.g., defaults)
        position: The position context
        sb_client: Supabase client
        
    Returns:
        New controls dict with overrides applied
    """
    try:
        # Clone base to avoid mutating
        controls = base_controls.copy()
        
        # Get overrides (cached)
        overrides = _get_overrides(sb_client)
        
        # Build unified scope from position
        scope = build_unified_scope(position=position)
        
        # Find matching tuning overrides
        # Tuning uses "Most Specific" rule (no blending) per spec 2.5
        matches = []
        for ov in overrides:
            cat = ov.get("action_category")
            # tuning_tighten = tightening (from active failure)
            # tuning_gate = loosening (from shadow winner EV check)
            if cat not in ("tuning_tighten", "tuning_gate"):
                continue
                
            scope_subset = ov.get("scope_subset") or {}
            
            # Check match
            is_match = True
            specificity = 0
            for k, v in scope_subset.items():
                if scope.get(k) != v:
                    is_match = False
                    break
                specificity += 1
            
            if is_match:
                matches.append((specificity, ov))
        
        if not matches:
            return controls
            
        # Sort by specificity desc, then confidence desc
        matches.sort(key=lambda x: (x[0], x[1].get("confidence_score", 0)), reverse=True)
        
        # Pick best match
        best_match = matches[0][1]
        tuning_params = best_match.get("tuning_params") or {}
        
        if not tuning_params:
            return controls
            
        logger.debug(f"Applying tuning override for {position.get('token_ticker')}: {tuning_params}")
        
        # Apply deltas
        # tuning_params keys are like "ts_min_delta", "halo_max_delta"
        # We need to apply them to "ts_min", "halo_mult" (halo_max)
        
        # Map tuning param names to control names
        # ts_min_delta -> ts_min
        # halo_max_delta -> halo_mult (controls use 'halo_mult' for max halo)
        # slope_min_delta -> slope_min (usually binary, but if we had a threshold)
        # dx_min_delta -> dx_min
        
        if "ts_min_delta" in tuning_params:
            base_val = float(controls.get("ts_min", 60.0))
            controls["ts_min"] = base_val + float(tuning_params["ts_min_delta"])
            
        if "halo_max_delta" in tuning_params:
            base_val = float(controls.get("halo_mult", 1.0))
            controls["halo_mult"] = base_val + float(tuning_params["halo_max_delta"])
            
        if "dx_min_delta" in tuning_params:
            base_val = float(controls.get("dx_min", 60.0))
            controls["dx_min"] = base_val + float(tuning_params["dx_min_delta"])
            
        return controls
        
    except Exception as e:
        logger.warning(f"Error applying tuning overrides: {e}")
        return base_controls

def _get_overrides(sb) -> List[Dict[str, Any]]:
    global _OVERRIDE_CACHE, _LAST_CACHE_UPDATE
    import time
    
    now = time.time()
    if now - _LAST_CACHE_UPDATE < CACHE_TTL and _OVERRIDE_CACHE:
        return _OVERRIDE_CACHE
        
    try:
        # Fetch valid overrides
        res = sb.table("pm_overrides")\
            .select("*")\
            .gt("confidence_score", 0.2)\
            .execute()
            
        data = res.data or []
        _OVERRIDE_CACHE = data
        _LAST_CACHE_UPDATE = now
        return data
    except Exception as e:
        logger.error(f"Failed to fetch pm_overrides: {e}")
        return []
