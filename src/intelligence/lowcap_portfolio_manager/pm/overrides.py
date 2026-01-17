"""
Pattern Override Runtime Functions

Apply pattern-based overrides to PM actions at runtime.
Refactored for V5: Queries pm_overrides table directly (using scope_subset <@ current_scope).
"""

import logging
import math
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from functools import lru_cache
from datetime import datetime, timezone

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Constants
EDGE_WEIGHT_SCALE = 1.0
N_TARGET = 25.0
VARIANCE_PENALTY = 1.0
SPECIFICITY_ALPHA = 1.5
MIN_OVERRIDE_WEIGHT = 0.02
MAX_MULTIPLIER_STEP = 0.02
MAX_SCOPE_DIMS_PM = 10

def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to bounds."""
    return max(min_val, min(max_val, value))

def apply_pattern_strength_overrides(
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any],
    base_levers: Dict[str, float],
    sb_client: Optional[Client] = None,
    feature_flags: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, float], float]:
    """
    Apply Strength v2 overrides (dirA, dirE) from pm_overrides.
    
    Logic per Spec 2.5 (Strength):
    - Query all overlapping overrides (scope_subset <@ scope)
    - specific_weight = confidence_eff * (spec_mass + 1.0) ^ ALPHA
    - final_dirA = weighted_avg(dirA)
    - final_dirE = weighted_avg(dirE)
    
    Application:
    - A_value += final_dirA (clamped 0.1-0.9)
    - E_value += final_dirE (clamped 0.1-0.9)
    - position_size_frac *= (1.0 + final_dirA) (simple scaling)
    
    Returns:
        Tuple of (adjusted_levers, final_dirA, applied_overrides)
        applied_overrides: List of matched override dicts for feedback tracking
    """
    # Check feature flags
    feature_flags = feature_flags or {}
    if not feature_flags.get('learning_overrides_enabled', True):
        return base_levers, 1.0, []  # 1.0 = neutral (no scaling)

    if sb_client is None:
        return base_levers, 1.0, []  # 1.0 = neutral (no scaling)

    try:
        scope_json = json.dumps(scope)
        # Fetch overrides with dirA/dirE
        res = (
            sb_client.table('pm_overrides')
            .select('*')
            .eq('pattern_key', pattern_key)
            .eq('action_category', action_category)
            .filter('scope_subset', 'cd', scope_json)
            .execute()
        )
        matches = res.data or []
        if not matches:
            return base_levers, 1.0, []  # 1.0 = neutral (no scaling)

        # Blending accumulators
        weighted_dirA_sum = 0.0
        weighted_dirE_sum = 0.0
        total_weight = 0.0
        applied_overrides = []  # Track for feedback
        
        for m in matches:
            # Check if this is a V2 override (has dirA/dirE)
            # If legacy multiplier only, skip or convert?
            # For now, prioritize V2. If dirA is None, treat as 0.
            dirA = m.get('dirA')
            dirE = m.get('dirE')
            
            if dirA is None and dirE is None:
                # Use legacy multiplier if present to approx dirA? 
                continue
                
            dirA = float(dirA or 0.0)
            dirE = float(dirE or 0.0)
            
            scope_subset = m.get('scope_subset', {}) or {}
            
            # Simple specificity proxy: number of keys
            # Spec says spec_mass = sum weights, but we don't have weights here efficiently.
            # Using count is a reasonable approximation for runtime.
            spec_mass = len(scope_subset) * 1.5 
            
            specificity = (spec_mass + 1.0) ** SPECIFICITY_ALPHA
            confidence = float(m.get('confidence_score', 0.5))
            
            weight = confidence * specificity
            
            weighted_dirA_sum += dirA * weight
            weighted_dirE_sum += dirE * weight
            total_weight += weight
            
            # Track for feedback
            applied_overrides.append({
                "override_id": str(m.get('id', '')),
                "scope_subset": scope_subset,
                "dirA": dirA,
                "dirE": dirE if dirE else None,
                "confidence": confidence,
                "weight": weight,
            })

        if total_weight == 0:
            return base_levers, 1.0, []  # 1.0 = neutral (no scaling)

        final_dirA = weighted_dirA_sum / total_weight
        final_dirE = weighted_dirE_sum / total_weight
        
        # Clamp deltas to avoiding breaking things (-0.5 to +0.5 safe range)
        final_dirA = _clamp(final_dirA, -0.5, 0.5)
        final_dirE = _clamp(final_dirE, -0.5, 0.5)

        adjusted = {
            'A_value': _clamp(base_levers.get('A_value', 0.5) + final_dirA, 0.1, 0.9),
            'E_value': _clamp(base_levers.get('E_value', 0.5) + final_dirE, 0.1, 0.9),
            'position_size_frac': base_levers.get('position_size_frac', 0.33),
        }
        
        # Scale position size by (1 + dirA)
        # dirA > 0 -> size up
        # dirA < 0 -> size down
        size_scaler = 1.0 + final_dirA
        adjusted['position_size_frac'] = _clamp(
            adjusted['position_size_frac'] * size_scaler,
            0.1, 
            1.0
        )

        logger.info(
            "STRENGTH_OVERRIDE_V2: %s matches=%d dirA=%.3f dirE=%.3f",
            pattern_key,
            len(matches),
            final_dirA,
            final_dirE
        )
        return adjusted, final_dirA, applied_overrides

    except Exception as e:
        logger.error(f"Error applying V5 overrides: {e}")
        return base_levers, 1.0, []  # 1.0 = neutral on error (safe fallback)

def apply_pattern_execution_overrides(
    pattern_key: str,
    action_category: str, # e.g. 'entry', 'add'
    scope: Dict[str, Any],
    plan_controls: Dict[str, Any],
    sb_client: Optional[Client] = None,
    feature_flags: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Applies execution overrides (Tuning).
    Queries pm_overrides for categories: 'tuning_ts_min', 'tuning_halo'.
    Applies multipliers to plan_controls['ts_min'] and plan_controls['halo_mult'].
    """
    feature_flags = feature_flags or {}
    if not feature_flags.get('tuning_overrides_enabled', True):
        return plan_controls

    if sb_client is None:
        return plan_controls

    try:
        scope_json = json.dumps(scope)
        
        # Query for V2 tuning overrides
        # Categories: tuning_tighten (tighten), tuning_gate (loosen), tuning_dx (ladder)
        res = sb_client.table('pm_overrides')\
            .select('*')\
            .eq('pattern_key', pattern_key)\
            .in_('action_category', ['tuning_tighten', 'tuning_gate', 'tuning_dx'])\
            .filter('scope_subset', 'cd', scope_json)\
            .execute()
            
        matches = res.data or []
        if not matches:
            return plan_controls

        # Sort by specificity desc, then confidence desc (Best Match strategy)
        # Specificity = number of keys in scope_subset
        def get_specificity(m):
            return len(m.get('scope_subset') or {})
            
        matches.sort(key=lambda x: (get_specificity(x), x.get('confidence_score', 0)), reverse=True)
        
        best_match = matches[0]
        tuning_params = best_match.get('tuning_params') or {}
        
        if not tuning_params:
            return plan_controls
            
        adjusted = plan_controls.copy()
        logger.debug(f"Applying Tuning Override V2: {best_match.get('action_category')} -> {tuning_params}")
        
        # Apply Deltas
        # ts_min_delta -> ts_min
        if 'ts_min_delta' in tuning_params:
            val = float(adjusted.get('ts_min', 60.0))
            adjusted['ts_min'] = _clamp(val + float(tuning_params['ts_min_delta']), 10.0, 300.0)
            
        # halo_max_delta -> halo_mult
        if 'halo_max_delta' in tuning_params:
            val = float(adjusted.get('halo_mult', 1.0))
            adjusted['halo_mult'] = _clamp(val + float(tuning_params['halo_max_delta']), 0.5, 5.0)
            
        # dx_min_delta -> dx_min
        if 'dx_min_delta' in tuning_params:
            val = float(adjusted.get('dx_min', 60.0))
            adjusted['dx_min'] = _clamp(val + float(tuning_params['dx_min_delta']), 10.0, 300.0)
            
        # dx_atr_mult_delta -> dx_atr_mult
        if 'dx_atr_mult_delta' in tuning_params:
            val = float(adjusted.get('dx_atr_mult', 1.0)) # Default 1.0 if missing?
            adjusted['dx_atr_mult'] = _clamp(val + float(tuning_params['dx_atr_mult_delta']), 0.5, 5.0)
            
        # slope_min_delta -> slope_min
        if 'slope_min_delta' in tuning_params:
            val = float(adjusted.get('slope_min', 0.1))
            adjusted['slope_min'] = _clamp(val + float(tuning_params['slope_min_delta']), 0.0, 1.0)
            
        return adjusted

    except Exception as e:
        logger.error(f"Error applying Tuning overrides: {e}")
        return plan_controls

def apply_allocation_overrides(
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any],
    base_allocation_pct: float,
    sb_client: Optional[Client] = None,
    feature_flags: Optional[Dict[str, Any]] = None
) -> float:
    """
    DM Allocation overrides.
    DEPRECATED in V5 (DM Simplification).
    Returns base allocation.
    """
    return base_allocation_pct

def clear_override_cache():
    pass
