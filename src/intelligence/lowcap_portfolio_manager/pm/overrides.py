"""
Pattern Override Runtime Functions

Apply pattern-based overrides to PM actions at runtime.
Reads from config and matches by pattern_key + action_category + scope.
"""

import logging
import math
import os
from typing import Dict, List, Any, Optional, Tuple
from functools import lru_cache
from datetime import datetime, timezone

from supabase import create_client, Client

logger = logging.getLogger(__name__)


EDGE_WEIGHT_SCALE = 1.0
N_TARGET = 25.0
VARIANCE_PENALTY = 1.0
SPECIFICITY_ALPHA = 1.5
MIN_OVERRIDE_WEIGHT = 0.02
MAX_MULTIPLIER_STEP = 0.02
MAX_ALLOC_MULT_STEP = 0.02
MAX_SCOPE_DIMS_PM = 10
MAX_SCOPE_DIMS_DM = 10
MAX_THRESHOLD_STEP = 0.05


@lru_cache(maxsize=1)
def _load_config_overrides(sb_client: Optional[Client] = None, config_table: str = 'learning_configs', config_key: str = 'pm') -> Dict[str, Any]:
    """
    Load override config from Supabase (cached).
    
    Args:
        sb_client: Supabase client (creates if None)
        config_table: Config table name
        config_key: Config key
    
    Returns:
        Config dict with pattern_strength_overrides and pattern_overrides
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            logger.warning("Missing Supabase credentials, returning empty overrides")
            return {'pattern_strength_overrides': [], 'pattern_overrides': []}
        sb_client = create_client(supabase_url, supabase_key)
    
    try:
        result = (
            sb_client.table(config_table)
            .select('config_data')
            .eq('module_id', config_key)
            .execute()
        )
        if result.data:
            config = result.data[0].get('config_data', {}) or {}
            return {
                'pattern_strength_overrides': config.get('pattern_strength_overrides', []),
                'pattern_overrides': config.get('pattern_overrides', []),
                'alloc_overrides': config.get('alloc_overrides', []),
            }
    except Exception as e:
        logger.warning(f"Error loading override config: {e}")
    
    return {
        'pattern_strength_overrides': [],
        'pattern_overrides': [],
        'alloc_overrides': [],
    }


def _scope_matches(override_scope: Dict[str, Any], current_scope: Dict[str, Any]) -> bool:
    """
    Check if override scope matches current scope (subset matching).
    
    Override scope must be a subset of current scope.
    
    Args:
        override_scope: Scope from override (subset)
        current_scope: Current action scope (full)
    
    Returns:
        True if override scope is subset of current scope
    """
    for key, value in override_scope.items():
        if key not in current_scope:
            return False
        if current_scope[key] != value:
            return False
    return True


def _find_matching_overrides(
    overrides: List[Dict[str, Any]],
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Find all overrides that match the current context.
    
    Args:
        overrides: List of override dicts
        pattern_key: Current pattern key
        action_category: Current action category
        scope: Current scope
    
    Returns:
        List of matching overrides (sorted by specificity)
    """
    matches = []
    
    for override in overrides:
        # Check pattern_key match
        if override.get('pattern_key') != pattern_key:
            continue
        
        # Check action_category match
        if override.get('action_category') != action_category:
            continue
        
        # Check scope subset match
        override_scope = override.get('scope', {})
        if not _scope_matches(override_scope, scope):
            continue
        
        # Check if enabled
        lesson = override.get('lesson', {})
        if not lesson.get('enabled', True):
            continue
        
        matches.append(override)
    
    # Sort by specificity (more scope dims = more specific)
    matches.sort(key=lambda m: len(m.get('scope', {})), reverse=True)
    
    return matches


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to bounds."""
    return max(min_val, min(max_val, value))


def _parse_iso_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        return None


def _compute_override_weight(override: Dict[str, Any], max_scope_dims: int) -> float:
    stats = override.get('stats') or {}
    lesson_meta = override.get('lesson') or {}
    
    edge_raw = float(stats.get('edge_raw') or 0.0)
    w_edge = math.tanh(abs(edge_raw) / EDGE_WEIGHT_SCALE)
    
    n = max(float(stats.get('n') or 0.0), 0.0)
    w_n = 1.0 - math.exp(-n / N_TARGET)
    
    variance = max(float(stats.get('variance') or 0.0), 0.0)
    w_var = 1.0 / (1.0 + VARIANCE_PENALTY * variance)
    
    decay_halflife_hours = lesson_meta.get('decay_halflife_hours')
    created_at = lesson_meta.get('created_at')
    w_decay = 1.0
    if decay_halflife_hours and decay_halflife_hours > 0 and created_at:
        created_dt = _parse_iso_ts(created_at)
        if created_dt:
            age_hours = max((datetime.now(timezone.utc) - created_dt).total_seconds() / 3600.0, 0.0)
            w_decay = math.exp(-age_hours / max(decay_halflife_hours, 1.0))
    
    scope = override.get('scope', {})
    num_scope_dims = len(scope)
    max_dims = max(max_scope_dims, 1)
    ratio = min(1.0, num_scope_dims / max_dims)
    w_spec = ratio ** SPECIFICITY_ALPHA
    
    strength = float(lesson_meta.get('strength', 0.5))
    
    weight = w_edge * w_n * w_var * w_decay * w_spec * strength
    return weight


def _blend_multiplier(
    weighted_overrides: List[Tuple[Dict[str, Any], float]],
    lever_key: str,
    max_delta: float,
    min_bound: float,
    max_bound: float
) -> float:
    numerator = 0.0
    denom = 0.0
    
    for override, weight in weighted_overrides:
        levers = override.get('levers') or {}
        target = levers.get(lever_key)
        if target is None:
            continue
        numerator += weight * target
        denom += weight
    
    if denom == 0:
        return 1.0
    
    weighted_target = numerator / denom
    delta = _clamp(weighted_target - 1.0, -max_delta, max_delta)
    final_mult = _clamp(1.0 + delta, min_bound, max_bound)
    return final_mult


def apply_pattern_strength_overrides(
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any],
    base_levers: Dict[str, float],
    sb_client: Optional[Client] = None,
    feature_flags: Optional[Dict[str, Any]] = None
) -> Dict[str, float]:
    """
    Apply capital lever overrides (size_mult, entry_aggression_mult, exit_aggression_mult).
    
    Args:
        pattern_key: Pattern key
        action_category: Action category
        scope: Current scope
        base_levers: Base levers { A_value, E_value, position_size_frac }
        sb_client: Supabase client (optional, for config loading)
        feature_flags: Feature flags dict (optional)
    
    Returns:
        Adjusted levers
    """
    # Check feature flags
    feature_flags = feature_flags or {}
    if not feature_flags.get('learning_overrides_enabled', True):
        return base_levers
    
    # Check regime/bucket flags
    enabled_regimes = feature_flags.get('learning_overrides_enabled_regimes', [])
    if enabled_regimes:
        current_regime = scope.get('macro_phase', '')
        if current_regime not in enabled_regimes:
            return base_levers
    
    enabled_buckets = feature_flags.get('learning_overrides_enabled_buckets', [])
    if enabled_buckets:
        current_bucket = scope.get('bucket', '')
        if current_bucket not in enabled_buckets:
            return base_levers
    
    # Load overrides
    config = _load_config_overrides(sb_client)
    strength_overrides = config.get('pattern_strength_overrides', [])
    
    # Find matches
    matches = _find_matching_overrides(strength_overrides, pattern_key, action_category, scope)
    
    weighted_matches: List[Tuple[Dict[str, Any], float]] = []
    for override in matches:
        weight = _compute_override_weight(override, MAX_SCOPE_DIMS_PM)
        if weight >= MIN_OVERRIDE_WEIGHT:
            weighted_matches.append((override, weight))
    
    if not weighted_matches:
        return base_levers
    
    size_mult = _blend_multiplier(weighted_matches, 'size_mult', MAX_MULTIPLIER_STEP, 0.7, 1.3)
    entry_mult = _blend_multiplier(weighted_matches, 'entry_aggression_mult', MAX_MULTIPLIER_STEP, 0.8, 1.2)
    exit_mult = _blend_multiplier(weighted_matches, 'exit_aggression_mult', MAX_MULTIPLIER_STEP, 0.8, 1.2)
    
    adjusted = {
        'A_value': base_levers.get('A_value', 0.5),
        'E_value': base_levers.get('E_value', 0.5),
        'position_size_frac': base_levers.get('position_size_frac', 0.33)
    }
    
    adjusted['position_size_frac'] = _clamp(adjusted['position_size_frac'] * size_mult, 0.0, 1.0)
    
    if action_category in ['entry', 'add']:
        adjusted['A_value'] = _clamp(adjusted['A_value'] * entry_mult, 0.0, 1.0)
    if action_category in ['trim', 'exit']:
        adjusted['E_value'] = _clamp(adjusted['E_value'] * exit_mult, 0.0, 1.0)
    
    logger.debug(
        f"Applied strength overrides: matches={len(weighted_matches)} "
        f"size_mult={size_mult:.3f} entry_mult={entry_mult:.3f} exit_mult={exit_mult:.3f}"
    )
    
    return adjusted


def apply_allocation_overrides(
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any],
    base_allocation_pct: float,
    sb_client: Optional[Client] = None,
    feature_flags: Optional[Dict[str, Any]] = None
) -> float:
    """
    Apply DM allocation overrides (alloc_mult).
    """
    feature_flags = feature_flags or {}
    if not feature_flags.get('learning_overrides_enabled', True):
        return base_allocation_pct
    
    config = _load_config_overrides(sb_client, config_key='dm')
    alloc_overrides = config.get('alloc_overrides', [])
    matches = _find_matching_overrides(alloc_overrides, pattern_key, action_category, scope)
    
    weighted_matches: List[Tuple[Dict[str, Any], float]] = []
    for override in matches:
        weight = _compute_override_weight(override, MAX_SCOPE_DIMS_DM)
        if weight >= MIN_OVERRIDE_WEIGHT:
            weighted_matches.append((override, weight))
    
    if not weighted_matches:
        return base_allocation_pct
    
    alloc_mult = _blend_multiplier(weighted_matches, 'alloc_mult', MAX_ALLOC_MULT_STEP, 0.7, 1.3)
    final_allocation = _clamp(base_allocation_pct * alloc_mult, 0.0, 100.0)
    
    logger.debug(
        f"Applied DM allocation overrides: matches={len(weighted_matches)} alloc_mult={alloc_mult:.3f}"
    )
    
    return final_allocation


def apply_pattern_execution_overrides(
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any],
    plan_controls: Dict[str, Any],
    sb_client: Optional[Client] = None,
    feature_flags: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Apply execution lever overrides (entry_delay_bars, thresholds, trail_mult, etc.).
    
    Args:
        pattern_key: Pattern key
        action_category: Action category
        scope: Current scope
        plan_controls: Base plan controls
        sb_client: Supabase client (optional)
        feature_flags: Feature flags dict (optional)
    
    Returns:
        Adjusted controls
    """
    # Check feature flags
    feature_flags = feature_flags or {}
    if not feature_flags.get('learning_overrides_enabled', True):
        return plan_controls
    
    # Check regime/bucket flags
    enabled_regimes = feature_flags.get('learning_overrides_enabled_regimes', [])
    if enabled_regimes:
        current_regime = scope.get('macro_phase', '')
        if current_regime not in enabled_regimes:
            return plan_controls
    
    enabled_buckets = feature_flags.get('learning_overrides_enabled_buckets', [])
    if enabled_buckets:
        current_bucket = scope.get('bucket', '')
        if current_bucket not in enabled_buckets:
            return plan_controls
    
    # Load overrides
    config = _load_config_overrides(sb_client)
    execution_overrides = config.get('pattern_overrides', [])
    
    matches = _find_matching_overrides(execution_overrides, pattern_key, action_category, scope)
    
    weighted_matches: List[Tuple[Dict[str, Any], float]] = []
    for override in matches:
        weight = _compute_override_weight(override, MAX_SCOPE_DIMS_PM)
        if weight >= MIN_OVERRIDE_WEIGHT:
            weighted_matches.append((override, weight))
    
    if not weighted_matches:
        return plan_controls

    adjusted = dict(plan_controls)

    signal_thresholds = (plan_controls.get('signal_thresholds') or {}).copy()
    threshold_keys = ['ts_min', 'sr_boost', 'halo_multiplier', 'dx_min', 'edx_supp_mult']
    for key in threshold_keys:
        base_value = signal_thresholds.get(key)
        if base_value is None:
            continue
        numerator = 0.0
        denom = 0.0
        for override, weight in weighted_matches:
            thresholds = (override.get('levers') or {}).get('signal_thresholds') or {}
            if key not in thresholds:
                continue
            numerator += weight * thresholds[key]
            denom += weight
        if denom == 0:
            continue
        weighted_target = numerator / denom
        delta = _clamp(weighted_target - base_value, -MAX_THRESHOLD_STEP, MAX_THRESHOLD_STEP)
        signal_thresholds[key] = _clamp(base_value + delta, 0.0, 5.0)
    adjusted['signal_thresholds'] = signal_thresholds

    logger.debug(
        f"Applied execution overrides: matches={len(weighted_matches)} thresholds={signal_thresholds}"
    )

    return adjusted


def clear_override_cache():
    """Clear the override config cache (call after materializer runs)."""
    _load_config_overrides.cache_clear()

