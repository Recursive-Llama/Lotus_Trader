"""
Lesson Builder v5 - Build lessons from pattern_scope_stats

Extends the learning system to build lessons from pattern_scope_stats with:
- v5.2: Half-life estimation for decay modeling
- v5.3: Latent factor checking for deduplication
- Full lever payload: capital + execution levers
"""

import logging
import os
import json
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

from supabase import create_client, Client

# Optional imports for curve fitting
try:
    import numpy as np
    from scipy.optimize import curve_fit
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger.warning("scipy not available, half-life estimation will be limited")

logger = logging.getLogger(__name__)


def estimate_half_life(
    edge_history: List[Tuple[float, datetime]]
) -> Optional[float]:
    """
    Estimate half-life from edge history using exponential decay fitting (v5.2).
    
    Fits: edge(t) = edge_0 * exp(-lambda * t)
    Returns: half_life_hours = ln(2) / lambda
    
    Args:
        edge_history: List of (edge_raw, timestamp) tuples
    
    Returns:
        Half-life in hours, or None if insufficient data
    """
    if not HAS_SCIPY:
        # Fallback: simple linear regression on log(edge)
        if len(edge_history) < 5:
            return None
        
        edge_history = sorted(edge_history, key=lambda x: x[1])
        first_ts = edge_history[0][1]
        times = [(ts - first_ts).total_seconds() / 3600.0 for _, ts in edge_history]
        edges = [max(abs(e), 0.001) for e, _ in edge_history]  # Avoid log(0)
        
        # Simple linear fit on log space
        log_edges = [math.log(e) for e in edges]
        if len(times) < 2:
            return None
        
        # Linear regression: log(edge) = a + b*t
        n = len(times)
        sum_t = sum(times)
        sum_log_e = sum(log_edges)
        sum_t2 = sum(t * t for t in times)
        sum_t_log_e = sum(t * le for t, le in zip(times, log_edges))
        
        denom = n * sum_t2 - sum_t * sum_t
        if abs(denom) < 1e-10:
            return None
        
        b = (n * sum_t_log_e - sum_t * sum_log_e) / denom
        
        if b >= 0:
            return None  # Not decaying
        
        # half_life = ln(2) / |b|
        half_life_hours = math.log(2) / abs(b)
        return max(1.0, min(half_life_hours, 8760.0))
    
    if len(edge_history) < 5:
        return None  # Insufficient data
    
    # Sort by timestamp
    edge_history = sorted(edge_history, key=lambda x: x[1])
    
    # Extract times (hours since first observation)
    first_ts = edge_history[0][1]
    times = [(ts - first_ts).total_seconds() / 3600.0 for _, ts in edge_history]
    edges = [edge for edge, _ in edge_history]
    
    # Filter out invalid data
    valid_indices = [i for i, (t, e) in enumerate(zip(times, edges)) if t >= 0 and not math.isnan(e) and not math.isinf(e)]
    if len(valid_indices) < 5:
        return None
    
    times = [times[i] for i in valid_indices]
    edges = [edges[i] for i in valid_indices]
    
    # Exponential decay model: edge(t) = a * exp(-b * t)
    def decay_model(t, a, b):
        return a * np.exp(-b * t)
    
    try:
        # Initial guess: a = first edge, b = small decay rate
        initial_a = edges[0] if edges[0] > 0 else 1.0
        initial_b = 0.001  # Small decay rate
        
        # Fit curve
        popt, _ = curve_fit(
            decay_model,
            times,
            edges,
            p0=[initial_a, initial_b],
            maxfev=1000,
            bounds=([0, 0], [np.inf, 1.0])  # a > 0, 0 < b < 1
        )
        
        a, b = popt
        
        # Compute half-life: t_half = ln(2) / b
        if b > 0:
            half_life_hours = math.log(2) / b
            # Clamp to reasonable range (1 hour to 1 year)
            half_life_hours = max(1.0, min(half_life_hours, 8760.0))
            return half_life_hours
        else:
            return None
    except Exception as e:
        logger.warning(f"Error fitting decay curve: {e}")
        return None


def get_latent_factor(
    sb_client: Client,
    pattern_key: str
) -> Optional[str]:
    """
    Check if pattern_key belongs to an existing latent factor cluster (v5.3).
    
    Args:
        sb_client: Supabase client
        pattern_key: Pattern key to check
    
    Returns:
        factor_id if found, None if unique
    """
    try:
        result = (
            sb_client.table('learning_latent_factors')
            .select('factor_id,pattern_keys')
            .execute()
        )
        
        factors = result.data or []
        for factor in factors:
            pattern_keys = factor.get('pattern_keys', [])
            if pattern_key in pattern_keys:
                return factor.get('factor_id')
        
        return None
    except Exception as e:
        logger.warning(f"Error checking latent factors: {e}")
        return None


def _clamp_edge_contribution(edge_raw: float, learning_rate: float, edge_scale: float) -> float:
    return max(-0.10, min(0.10, (edge_raw / edge_scale) * learning_rate))


def map_edge_to_levers_pm(
    edge_raw: float,
    action_category: str,
    stats: Dict[str, Any],
    learning_rate: float = 0.02,
    edge_scale: float = 20.0
) -> Dict[str, Any]:
    """
    Map edge to PM capital + execution levers.
    """
    edge_contribution = _clamp_edge_contribution(edge_raw, learning_rate, edge_scale)
    
    size_mult = max(0.7, min(1.3, 1.0 + edge_contribution))
    if action_category == "entry":
        entry_aggression_mult = max(0.8, min(1.2, 1.0 + edge_contribution))
        exit_aggression_mult = 1.0
    elif action_category == "add":
        entry_aggression_mult = max(0.8, min(1.2, 1.0 + edge_contribution))
        exit_aggression_mult = 1.0
    elif action_category == "trim":
        entry_aggression_mult = 1.0
        exit_aggression_mult = max(0.8, min(1.2, 1.0 - edge_contribution))
    else:
        entry_aggression_mult = 1.0
        exit_aggression_mult = max(0.8, min(1.2, 1.0 - edge_contribution))
    
    capital_levers = {
        "size_mult": size_mult,
        "entry_aggression_mult": entry_aggression_mult,
        "exit_aggression_mult": exit_aggression_mult
    }
    
    execution_levers: Dict[str, Any] = {}
    cf_entry = stats.get('cf_entry_improvement_bucket')
    cf_exit = stats.get('cf_exit_improvement_bucket')
    
    if action_category in ["entry", "add"]:
        if cf_entry == "large":
            execution_levers["entry_delay_bars"] = 0
        elif cf_entry == "medium":
            execution_levers["entry_delay_bars"] = 1
        elif cf_entry == "small":
            execution_levers["entry_delay_bars"] = 2
        
        if edge_raw > 0.5:
            execution_levers["phase1_frac_mult"] = min(1.5, 1.0 + edge_contribution * 2)
        elif edge_raw < -0.5:
            execution_levers["phase1_frac_mult"] = max(0.5, 1.0 + edge_contribution * 2)
    
    if action_category in ["trim", "exit"]:
        if cf_exit == "large":
            execution_levers["trim_delay_mult"] = 0.5
        elif cf_exit == "medium":
            execution_levers["trim_delay_mult"] = 0.8
        elif cf_exit == "small":
            execution_levers["trim_delay_mult"] = 1.0
        
        if edge_raw > 0.5:
            execution_levers["trail_mult"] = max(0.5, min(2.0, 1.0 + edge_contribution))
        elif edge_raw < -0.5:
            execution_levers["trail_mult"] = max(0.5, min(2.0, 1.0 - edge_contribution))
    
    if edge_raw > 0.3:
        signal_thresholds = {}
        if action_category in ["entry", "add"]:
            signal_thresholds["min_ts_for_add"] = 0.55
        if action_category == "trim":
            signal_thresholds["min_ox_for_trim"] = 0.40
        
        if signal_thresholds:
            execution_levers["signal_thresholds"] = signal_thresholds
    
    return {
        "capital_levers": capital_levers,
        "execution_levers": execution_levers
    }


def map_edge_to_levers_dm(
    edge_raw: float,
    learning_rate: float = 0.02,
    edge_scale: float = 20.0
) -> Dict[str, Any]:
    """
    Map edge to DM allocation lever.
    """
    edge_contribution = _clamp_edge_contribution(edge_raw, learning_rate, edge_scale)
    alloc_mult = max(0.7, min(1.3, 1.0 + edge_contribution))
    return {
        "capital_levers": {"alloc_mult": alloc_mult},
        "execution_levers": {}
    }


def _extract_tuning_overrides(stats: Dict[str, Any], episode_type: str) -> Dict[str, Any]:
    tuning = stats.get('tuning') or {}
    type_stats = tuning.get(episode_type)
    if not type_stats:
        return {}

    outcomes = type_stats.get('outcomes') or {}
    total = sum(outcomes.values())
    if total <= 0:
        return {}

    # positive score means tighten, negative means loosen
    outcome_score = (
        outcomes.get('failure', 0) * 1.0 +
        outcomes.get('missed', 0) * 0.7 -
        outcomes.get('success', 0) * 1.0
    ) / total

    lever_stats = type_stats.get('levers') or {}
    overrides: Dict[str, Any] = {}

    for lever_name, bucket in lever_stats.items():
        count = bucket.get('count', 0)
        if count <= 0:
            continue
        avg_delta = float(bucket.get('sum_delta', 0.0)) / count
        avg_severity = float(bucket.get('sum_severity', 0.0)) / count
        avg_conf = float(bucket.get('sum_confidence', 0.0)) / count
        score = outcome_score * avg_severity * avg_conf

        if abs(score) < 0.05:
            continue

        target = avg_delta * max(0.2, min(1.0, abs(score)))
        if lever_name in {"ts_min", "sr_boost", "halo_multiplier", "dx_min", "edx_supp_mult"}:
            thresholds = overrides.setdefault("signal_thresholds", {})
            thresholds[lever_name] = target

    return overrides


def compute_incremental_edge_vs_parents(
    pattern_key: str,
    action_category: str,
    scope_dims: List[str],
    edge_raw: float,
    sb_client: Client
) -> float:
    """
    Compute incremental edge vs parent scope subsets.
    
    Args:
        pattern_key: Pattern key
        action_category: Action category
        scope_dims: List of scope dimension names
        edge_raw: Current edge
        sb_client: Supabase client
    
    Returns:
        Incremental edge (edge_raw - max(parent_edges))
    """
    if len(scope_dims) <= 1:
        return edge_raw  # No parents
    
    # Generate parent subsets (remove one dim at a time)
    parent_edges = []
    
    for i in range(len(scope_dims)):
        parent_dims = scope_dims[:i] + scope_dims[i+1:]
        
        # Query pattern_scope_stats for parent subset
        try:
            # Build scope_values from parent_dims (would need actual values, simplified here)
            # For now, we'll query by pattern_key + action_category and filter in Python
            result = (
                sb_client.table('pattern_scope_stats')
                .select('stats')
                .eq('pattern_key', pattern_key)
                .eq('action_category', action_category)
                .execute()
            )
            
            # Find matching parent subset (simplified - would need proper mask matching)
            # For now, return edge_raw as incremental (can be refined)
            if result.data:
                for row in result.data:
                    stats = row.get('stats', {})
                    parent_edge = stats.get('edge_raw', 0.0)
                    if parent_edge != 0.0:
                        parent_edges.append(parent_edge)
        except Exception:
            pass
    
    if not parent_edges:
        return edge_raw  # No parent data
    
    max_parent_edge = max(parent_edges)
    incremental = edge_raw - max_parent_edge
    
    return incremental


async def build_lessons_from_pattern_scope_stats(
    sb_client: Client,
    module: str = 'pm',
    n_min: int = 10,
    edge_min: float = 0.5,
    incremental_min: float = 0.1,
    max_lessons_per_pattern: int = 3
) -> int:
    """
    Build lessons from pattern_scope_stats (v5).
    
    Args:
        sb_client: Supabase client
        module: 'pm' or 'dm'
        n_min: Minimum sample size
        edge_min: Minimum edge score
        incremental_min: Minimum incremental edge vs parents
        max_lessons_per_pattern: Maximum lessons per (pattern_key, action_category)
    
    Returns:
        Number of lessons created/updated
    """
    try:
        # Query pattern_scope_stats for candidates
        result = (
            sb_client.table('pattern_scope_stats')
            .select('*')
            .gte('n', n_min)
            .execute()
        )
        
        rows = result.data or []
        
        if not rows:
            logger.info(f"No pattern_scope_stats rows found for module {module}")
            return 0
        
        # Group by (pattern_key, action_category)
        pattern_groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        
        for row in rows:
            pattern_key = row.get('pattern_key', '')
            action_category = row.get('action_category', '')
            stats = row.get('stats', {})
            edge_raw = stats.get('edge_raw', 0.0)
            
            # Filter by edge_min
            if abs(edge_raw) < edge_min:
                continue
            
            # Extract scope dimensions from scope_values
            scope_values = row.get('scope_values', {})
            scope_dims = list(scope_values.keys())
            
            key = (pattern_key, action_category)
            if key not in pattern_groups:
                pattern_groups[key] = []
            
            pattern_groups[key].append({
                'row': row,
                'scope_dims': scope_dims,
                'scope_values': scope_values,
                'edge_raw': edge_raw,
                'stats': stats,
                'n': row.get('n', 0)
            })
        
        if not pattern_groups:
            logger.info(f"No candidates found (edge_min={edge_min})")
            return 0
        
        lessons_created = 0
        
        # Process each (pattern_key, action_category) group
        for (pattern_key, action_category), candidates in pattern_groups.items():
            # Sort by simplicity (fewer dims first) then by edge_raw
            candidates.sort(key=lambda x: (len(x['scope_dims']), -abs(x['edge_raw'])))
            
            selected = []
            
            for candidate in candidates:
                if len(selected) >= max_lessons_per_pattern:
                    break
                
                scope_dims = candidate['scope_dims']
                scope_values = candidate['scope_values']
                edge_raw = candidate['edge_raw']
                stats = candidate['stats']
                n = candidate['n']
                
                # Compute incremental edge vs parents
                incremental_edge = compute_incremental_edge_vs_parents(
                    pattern_key,
                    action_category,
                    scope_dims,
                    edge_raw,
                    sb_client
                )
                
                # Skip if incremental edge is too small
                if incremental_edge < incremental_min:
                    continue
                
                # Estimate half-life (v5.2)
                # Query edge history for this pattern+category+scope
                scope_signature = json.dumps(sorted(scope_values.items()), sort_keys=True)
                try:
                    history_result = (
                        sb_client.table('learning_edge_history')
                        .select('edge_raw,ts')
                        .eq('pattern_key', pattern_key)
                        .eq('action_category', action_category)
                        .eq('scope_signature', scope_signature)
                        .order('ts', desc=True)
                        .limit(20)
                        .execute()
                    )
                    
                    edge_history = []
                    for hist_row in (history_result.data or []):
                        edge_val = hist_row.get('edge_raw', 0.0)
                        ts_str = hist_row.get('ts')
                        if ts_str:
                            try:
                                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                edge_history.append((edge_val, ts))
                            except Exception:
                                pass
                    
                    half_life_hours = estimate_half_life(edge_history) if edge_history else None
                except Exception as e:
                    logger.warning(f"Error estimating half-life: {e}")
                    half_life_hours = None
                
                # Check latent factor (v5.3)
                latent_factor_id = get_latent_factor(sb_client, pattern_key)
                
                # Map edge to levers (module-specific)
                if module == 'dm':
                    levers = map_edge_to_levers_dm(edge_raw)
                    lesson_type = 'dm_alloc'
                else:
                    levers = map_edge_to_levers_pm(edge_raw, action_category, stats)
                    lesson_type = 'pm_strength'
                
                # Compute lesson strength (0.0-1.0)
                edge_scale_for_strength = 20.0
                lesson_strength = min(1.0, abs(edge_raw) / edge_scale_for_strength if edge_raw != 0 else 0.0)
                
                # Determine status
                edge_promote = 0.5
                n_promote = 20
                status = 'active' if (n >= n_promote and abs(edge_raw) > edge_promote) else 'candidate'
                
                # Build lesson
                lesson = {
                    'module': module,
                    'pattern_key': pattern_key,  # Store pattern_key for reference
                    'action_category': action_category,
                    'scope_dims': scope_dims,
                    'scope_values': scope_values,
                    'trigger': scope_values,  # For backward compatibility
                    'effect': levers,
                    'lesson_type': lesson_type,
                    'stats': {
                        'edge_raw': edge_raw,
                        'incremental_edge': incremental_edge,
                        'n': n,
                        'avg_rr': stats.get('avg_rr', 0.0),
                        'variance': stats.get('variance', 0.0),
                        'time_efficiency': stats.get('time_efficiency'),
                        'field_coherence': stats.get('field_coherence'),
                        'recurrence_score': stats.get('recurrence_score')
                    },
                    'lesson_strength': lesson_strength,
                    'decay_halflife_hours': int(half_life_hours) if half_life_hours else None,
                    'latent_factor_id': latent_factor_id,
                    'status': status,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Check if lesson exists (by pattern_key + action_category + scope_values)
                # Note: pattern_key is stored in trigger for backward compatibility, but we use scope_values for matching
                try:
                    # Try to find by scope_values match (JSONB containment)
                    existing = (
                        sb_client.table('learning_lessons')
                        .select('id')
                        .eq('module', module)
                        .eq('action_category', action_category)
                        .execute()
                    )
                    
                    # Filter in Python for exact scope_values match
                    matching_lesson = None
                    for lesson_row in (existing.data or []):
                        # Check if scope_values match (would need to query full row)
                        # For now, use a simpler approach: check by pattern_key if available
                        pass
                    
                    # For simplicity, always update/insert (let DB handle uniqueness)
                    existing_ids = [row['id'] for row in (existing.data or [])]
                    
                    # For now, always insert (can be refined to check for exact matches)
                    # The unique constraint on (module, action_category, scope_values) will prevent duplicates
                    try:
                        sb_client.table('learning_lessons').insert(lesson).execute()
                    except Exception as insert_error:
                        # If insert fails due to uniqueness, try update
                        if 'unique' in str(insert_error).lower() or 'duplicate' in str(insert_error).lower():
                            # Find existing by scope_values
                            update_result = (
                                sb_client.table('learning_lessons')
                                .select('id')
                                .eq('module', module)
                                .eq('action_category', action_category)
                                .eq('scope_values', scope_values)
                                .execute()
                            )
                            if update_result.data and len(update_result.data) > 0:
                                sb_client.table('learning_lessons').update({
                                    **lesson,
                                    'last_validated': datetime.now(timezone.utc).isoformat()
                                }).eq('id', update_result.data[0]['id']).execute()
                            else:
                                raise
                        else:
                            raise
                    
                    lessons_created += 1
                    selected.append(candidate)

                    tuning_overrides = {}
                    if module == 'pm':
                        tuning_overrides.update(_extract_tuning_overrides(stats, 's1_entry'))
                        tuning_overrides.update(_extract_tuning_overrides(stats, 's3_retest'))
                    if tuning_overrides:
                        tuning_lesson = dict(lesson)
                        tuning_lesson['lesson_type'] = 'pm_tuning'
                        tuning_lesson['effect'] = tuning_overrides
                        tuning_lesson['lesson_strength'] = min(1.0, abs(edge_raw) / 10.0)
                        try:
                            sb_client.table('learning_lessons').insert(tuning_lesson).execute()
                            lessons_created += 1
                        except Exception as insert_error:
                            if 'unique' in str(insert_error).lower() or 'duplicate' in str(insert_error).lower():
                                update_result = (
                                    sb_client.table('learning_lessons')
                                    .select('id')
                                    .eq('module', module)
                                    .eq('action_category', action_category)
                                    .eq('scope_values', scope_values)
                                    .eq('lesson_type', 'pm_tuning')
                                    .execute()
                                )
                                if update_result.data:
                                    sb_client.table('learning_lessons').update({
                                        **tuning_lesson,
                                        'last_validated': datetime.now(timezone.utc).isoformat()
                                    }).eq('id', update_result.data[0]['id']).execute()
                            else:
                                logger.warning(f"Error creating tuning lesson for {pattern_key}: {insert_error}")
                    
                except Exception as e:
                    logger.warning(f"Error creating lesson for {pattern_key}/{action_category}: {e}")
                    continue
        
        logger.info(f"Created/updated {lessons_created} lessons from pattern_scope_stats for module {module}")
        return lessons_created
        
    except Exception as e:
        logger.error(f"Error building lessons from pattern_scope_stats: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0


if __name__ == "__main__":
    # Standalone execution
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        exit(1)
    
    sb_client = create_client(supabase_url, supabase_key)
    result = asyncio.run(build_lessons_from_pattern_scope_stats(sb_client, module='pm'))
    print(f"Lessons created: {result}")

