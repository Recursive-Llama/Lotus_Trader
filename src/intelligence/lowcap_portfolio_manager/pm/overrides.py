"""
Pattern Override Runtime Functions

Apply pattern-based overrides to PM actions at runtime.
Reads from config and matches by pattern_key + action_category + scope.
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


def query_edge_history(
    sb_client: Optional[Client],
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any],
    limit: int = 30
) -> List[Tuple[float, datetime]]:
    """
    Query edge history from learning_edge_history table.
    
    Args:
        sb_client: Supabase client
        pattern_key: Pattern key
        action_category: Action category
        scope: Scope dict (used to build scope_signature)
        limit: Max number of snapshots to return
    
    Returns:
        List of (edge_raw, timestamp) tuples, sorted by timestamp (oldest first)
    """
    if sb_client is None:
        return []
    
    try:
        # Build scope signature (same as in pattern_scope_aggregator)
        scope_signature = json.dumps(sorted(scope.items()), sort_keys=True)
        
        # Query edge history
        result = (
            sb_client.table('learning_edge_history')
            .select('edge_raw,ts')
            .eq('pattern_key', pattern_key)
            .eq('action_category', action_category)
            .eq('scope_signature', scope_signature)
            .order('ts', desc=True)
            .limit(limit)
            .execute()
        )
        
        edge_history = []
        for row in (result.data or []):
            edge_val = row.get('edge_raw', 0.0)
            ts_str = row.get('ts')
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    edge_history.append((edge_val, ts))
                except Exception as e:
                    logger.debug(f"Error parsing timestamp {ts_str}: {e}")
                    continue
        
        # Sort by timestamp (oldest first) for slope calculation
        edge_history.sort(key=lambda x: x[1])
        return edge_history
        
    except Exception as e:
        logger.warning(f"Error querying edge history: {e}")
        return []


def compute_edge_slope(
    edge_history: List[Tuple[float, datetime]],
    min_points: int = 5
) -> Optional[float]:
    """
    Compute slope of edge over time using linear regression.
    
    Simple approach: fit line to (time, edge) points.
    Returns slope (negative = decaying, positive = improving).
    
    Args:
        edge_history: List of (edge_raw, timestamp) tuples (should be sorted by timestamp)
        min_points: Minimum points needed
    
    Returns:
        Slope (edge per hour), or None if insufficient data
    """
    if len(edge_history) < min_points:
        return None
    
    # Ensure sorted by timestamp
    edge_history = sorted(edge_history, key=lambda x: x[1])
    
    # Convert to hours since first observation
    first_ts = edge_history[0][1]
    times = [(ts - first_ts).total_seconds() / 3600.0 for _, ts in edge_history]
    edges = [edge for edge, _ in edge_history]
    
    # Simple linear regression: edge = a + b*t
    # slope = b
    n = len(times)
    sum_t = sum(times)
    sum_e = sum(edges)
    sum_t2 = sum(t * t for t in times)
    sum_te = sum(t * e for t, e in zip(times, edges))
    
    denom = n * sum_t2 - sum_t * sum_t
    if abs(denom) < 1e-10:
        return None
    
    slope = (n * sum_te - sum_t * sum_e) / denom
    return slope


def adjust_multiplier_for_edge_direction(
    base_multiplier: float,
    edge_slope: Optional[float],
    max_adjustment: float = 0.1  # Max ±10% adjustment
) -> float:
    """
    Adjust multiplier based on edge direction (slope).
    
    Simple rule:
    - If edge is improving (slope > 0) → increase multiplier
    - If edge is decaying (slope < 0) → decrease multiplier
    - If edge is stable (slope ≈ 0) → no change
    
    Args:
        base_multiplier: Base multiplier from lesson
        edge_slope: Slope from compute_edge_slope() (edge per hour)
        max_adjustment: Maximum adjustment factor (0.1 = ±10%)
    
    Returns:
        Adjusted multiplier (clamped to bounds)
    """
    if edge_slope is None:
        return base_multiplier  # No data, use base
    
    # Normalize slope: convert to adjustment factor
    # Slope is in "edge per hour" - we need to scale it
    # Use tanh to bound the adjustment smoothly
    # 
    # Example: if slope = -0.01 edge/hour (decaying)
    #   tanh(-0.01 / 0.01) = tanh(-1.0) ≈ -0.76
    #   adjustment = -0.76 * 0.1 = -0.076 (7.6% decrease)
    #
    # Example: if slope = +0.02 edge/hour (improving fast)
    #   tanh(0.02 / 0.01) = tanh(2.0) ≈ 0.96
    #   adjustment = 0.96 * 0.1 = 0.096 (9.6% increase)
    #
    # The normalization factor (0.01) determines what counts as "significant":
    # - 0.01 edge/hour = moderate change → ~76% of max adjustment
    # - 0.02 edge/hour = fast change → ~96% of max adjustment
    # - Very steep slopes are capped at ±1.0 by tanh
    
    # TODO: Calibrate this normalization factor based on actual edge magnitudes
    # For now, using 0.01 edge/hour as "significant" threshold
    slope_normalized = math.tanh(edge_slope / 0.01)  # 0.01 edge/hour = significant change
    adjustment = slope_normalized * max_adjustment
    
    adjusted = base_multiplier * (1.0 + adjustment)
    
    # Clamp to bounds (0.7-1.3 for PM/DM)
    return max(0.7, min(1.3, adjusted))


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
    
    # Apply edge slope adjustments (decay direction)
    # Query edge history and compute slope
    edge_history = query_edge_history(sb_client, pattern_key, action_category, scope, limit=30)
    edge_slope = compute_edge_slope(edge_history, min_points=5)
    
    # Adjust multipliers based on edge direction
    if edge_slope is not None:
        size_mult = adjust_multiplier_for_edge_direction(size_mult, edge_slope, max_adjustment=0.1)
        entry_mult = adjust_multiplier_for_edge_direction(entry_mult, edge_slope, max_adjustment=0.1)
        exit_mult = adjust_multiplier_for_edge_direction(exit_mult, edge_slope, max_adjustment=0.1)
        logger.debug(
            f"Edge slope adjustment: slope={edge_slope:.6f} edge/hour, "
            f"size_mult={size_mult:.3f} entry_mult={entry_mult:.3f} exit_mult={exit_mult:.3f}"
        )
    
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
    
    # Apply edge slope adjustments (decay direction)
    # Query edge history and compute slope
    edge_history = query_edge_history(sb_client, pattern_key, action_category, scope, limit=30)
    edge_slope = compute_edge_slope(edge_history, min_points=5)
    
    # Adjust multiplier based on edge direction
    if edge_slope is not None:
        alloc_mult = adjust_multiplier_for_edge_direction(alloc_mult, edge_slope, max_adjustment=0.1)
        logger.debug(
            f"Edge slope adjustment (DM): slope={edge_slope:.6f} edge/hour, alloc_mult={alloc_mult:.3f}"
        )
    
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

