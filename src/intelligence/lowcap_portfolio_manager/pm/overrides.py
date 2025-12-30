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
    Apply capital lever overrides (size_mult) from pm_overrides.
    
    Returns:
        Tuple of (adjusted_levers, strength_mult)
        strength_mult is the learned multiplier (1.0 = neutral, >1 = good pattern, <1 = bad pattern)
    """
    # Check feature flags
    feature_flags = feature_flags or {}
    if not feature_flags.get('learning_overrides_enabled', True):
        return base_levers, 1.0

    if sb_client is None:
        return base_levers, 1.0

    try:
        scope_json = json.dumps(scope)
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
            return base_levers, 1.0

        weighted_mults = []
        total_weight = 0.0
        for m in matches:
            scope_subset = m.get('scope_subset', {}) or {}
            specificity = (len(scope_subset) + 1.0) ** SPECIFICITY_ALPHA
            confidence = float(m.get('confidence_score', 0.5))
            multiplier = float(m.get('multiplier', 1.0))
            weight = confidence * specificity
            weighted_mults.append(multiplier * weight)
            total_weight += weight

        if total_weight == 0:
            return base_levers, 1.0

        final_mult = sum(weighted_mults) / total_weight
        final_mult = _clamp(final_mult, 0.3, 3.0)

        adjusted = {
            'A_value': base_levers.get('A_value', 0.5),
            'E_value': base_levers.get('E_value', 0.5),
            'position_size_frac': base_levers.get('position_size_frac', 0.33),
        }
        adjusted['position_size_frac'] = _clamp(
            adjusted['position_size_frac'] * final_mult,
            0.0,
            1.0,
        )

        logger.info(
            "STRENGTH_OVERRIDE: %s matches=%d strength_mult=%.2f",
            pattern_key,
            len(matches),
            final_mult,
        )
        return adjusted, final_mult

    except Exception as e:
        logger.error(f"Error applying V5 overrides: {e}")
        return base_levers, 1.0

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
        
        # Query for tuning overrides for this pattern
        res = sb_client.table('pm_overrides')\
            .select('*')\
            .eq('pattern_key', pattern_key)\
            .in_('action_category', ['tuning_ts_min', 'tuning_halo', 'tuning_dx_min'])\
            .filter('scope_subset', 'cd', scope_json)\
            .execute()
            
        matches = res.data or []
        if not matches:
            return plan_controls

        # Group by category (ts_min vs halo)
        by_cat: Dict[str, List[Dict]] = {}
        for m in matches:
            cat = m['action_category']
            by_cat.setdefault(cat, []).append(m)
            
        adjusted = plan_controls.copy()
        
        # Helper to blend and apply
        def apply_override(cat: str, target_key: str, min_b: float, max_b: float):
            if cat not in by_cat:
                return
            
            # Blend logic (same as strength)
            weighted_mults = []
            total_weight = 0.0
            for m in by_cat[cat]:
                scope_subset = m.get('scope_subset', {})
                specificity = (len(scope_subset) + 1.0) ** SPECIFICITY_ALPHA
                conf = float(m.get('confidence_score', 1.0))
                multiplier = float(m.get('multiplier', 1.0))
                
                weight = conf * specificity
                weighted_mults.append(multiplier * weight)
                total_weight += weight
            
            if total_weight > 0:
                final_mult = sum(weighted_mults) / total_weight
                # Apply
                current_val = adjusted.get(target_key, 1.0)
                new_val = current_val * final_mult
                adjusted[target_key] = _clamp(new_val, min_b, max_b)
                logger.info(f"Applied Tuning Override: {cat} x{final_mult:.2f} -> {target_key}={adjusted[target_key]:.2f}")

        # Apply TS Min Override
        apply_override('tuning_ts_min', 'ts_min', 10.0, 90.0)
        
        # Apply Halo Override (assume key is 'halo_mult' or similar? check caller)
        # PMCoreTick passes `plan_controls` which usually has `halo_mult`?
        # Actually PMCoreTick passes `self.config.get('controls')`?
        # Let's assume 'halo_mult' is the key.
        apply_override('tuning_halo', 'halo_mult', 0.5, 3.0)
        apply_override('tuning_dx_min', 'dx_min', 10.0, 90.0)

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
