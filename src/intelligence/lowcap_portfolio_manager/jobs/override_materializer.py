"""
Override Materializer Job

Reads active lessons from learning_lessons and materializes them into config overrides.
Applies decay (v5.2) and handles latent factors (v5.3) to prevent double-counting.

Runs periodically to update pattern_strength_overrides and pattern_overrides in config.
"""

import logging
import os
import math
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

from supabase import create_client, Client

logger = logging.getLogger(__name__)


def apply_decay(
    lever_value: float,
    lesson_strength: float,
    decay_halflife_hours: Optional[int],
    lesson_age_hours: float
) -> float:
    """
    Decay lever strength toward 1.0 (neutral) based on half-life (v5.2).
    
    Args:
        lever_value: Current lever value
        lesson_strength: Lesson strength (0.0-1.0)
        decay_halflife_hours: Half-life in hours (None if not estimated)
        lesson_age_hours: Age of lesson in hours
    
    Returns:
        Decayed lever value
    """
    if decay_halflife_hours is None or decay_halflife_hours <= 0:
        # No decay if half-life not estimated
        return lever_value
    
    if lesson_age_hours <= 0:
        return lever_value
    
    # Exponential decay: value(t) = neutral + (value_0 - neutral) * exp(-lambda * t)
    # lambda = ln(2) / half_life
    decay_rate = math.log(2) / decay_halflife_hours
    decay_factor = math.exp(-decay_rate * lesson_age_hours)
    
    neutral = 1.0
    decayed = neutral + (lever_value - neutral) * decay_factor * lesson_strength
    
    return decayed


def merge_latent_factor_levers(
    lessons: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Merge levers from lessons in the same latent factor (v5.3).
    
    If multiple lessons share a latent_factor_id, merge their levers by weighted average.
    
    Args:
        lessons: List of lesson dicts with same latent_factor_id
    
    Returns:
        Merged lever dict
    """
    if not lessons:
        return {}
    
    if len(lessons) == 1:
        return lessons[0].get('effect', {})
    
    # Weight by lesson_strength and n
    total_weight = 0.0
    weighted_capital = {}
    weighted_execution = {}
    
    for lesson in lessons:
        effect = lesson.get('effect', {})
        stats = lesson.get('stats', {})
        strength = lesson.get('lesson_strength', 0.5)
        n = stats.get('n', 0)
        
        # Weight = strength * log(1 + n)
        weight = strength * math.log(1 + max(n, 1))
        total_weight += weight
        
        capital_levers = effect.get('capital_levers', {})
        execution_levers = effect.get('execution_levers', {})
        
        # Accumulate weighted capital levers
        for key, value in capital_levers.items():
            if key not in weighted_capital:
                weighted_capital[key] = 0.0
            weighted_capital[key] += value * weight
        
        # Accumulate weighted execution levers
        for key, value in execution_levers.items():
            if isinstance(value, dict):
                # Nested dict (e.g., signal_thresholds, phase_scaling)
                if key not in weighted_execution:
                    weighted_execution[key] = {}
                for sub_key, sub_value in value.items():
                    if sub_key not in weighted_execution[key]:
                        weighted_execution[key][sub_key] = 0.0
                    weighted_execution[key][sub_key] += sub_value * weight
            else:
                # Simple value
                if key not in weighted_execution:
                    weighted_execution[key] = 0.0
                weighted_execution[key] += value * weight
    
    # Normalize
    if total_weight > 0:
        for key in weighted_capital:
            weighted_capital[key] /= total_weight
        for key in weighted_execution:
            if isinstance(weighted_execution[key], dict):
                for sub_key in weighted_execution[key]:
                    weighted_execution[key][sub_key] /= total_weight
            else:
                weighted_execution[key] /= total_weight
    
    return {
        'capital_levers': weighted_capital,
        'execution_levers': weighted_execution
    }


def _build_lesson_metadata(lesson: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    lesson_strength = lesson.get('lesson_strength', 0.5)
    decay_halflife_hours = lesson.get('decay_halflife_hours')
    created_at = lesson.get('created_at') or now.isoformat()
    return {
        'id': str(lesson.get('id', '')),
        'strength': lesson_strength,
        'decay_halflife_hours': decay_halflife_hours,
        'enabled': True,
        'created_at': created_at
    }


def _build_pm_override_payload(lessons: List[Dict[str, Any]], now: datetime) -> Dict[str, Any]:
    # Existing latent-factor merge logic
    factor_groups: Dict[Optional[str], List[Dict[str, Any]]] = {}
    no_factor_lessons: List[Dict[str, Any]] = []
    
    for lesson in lessons:
        factor_id = lesson.get('latent_factor_id')
        if factor_id:
            factor_groups.setdefault(factor_id, []).append(lesson)
        else:
            no_factor_lessons.append(lesson)
    
    processed_lessons: List[Dict[str, Any]] = []
    
    for factor_id, factor_lessons in factor_groups.items():
        representative = max(factor_lessons, key=lambda l: (
            l.get('lesson_strength', 0.0),
            l.get('created_at', '')
        ))
        merged_effect = merge_latent_factor_levers(factor_lessons)
        merged_lesson = {
            **representative,
            'effect': merged_effect,
            'latent_factor_id': factor_id,
            'merged_from': len(factor_lessons)
        }
        processed_lessons.append(merged_lesson)
    
    processed_lessons.extend(no_factor_lessons)
    
    strength_overrides: List[Dict[str, Any]] = []
    execution_overrides: List[Dict[str, Any]] = []
    
    for lesson in processed_lessons:
        pattern_key = lesson.get('pattern_key')
        action_category = lesson.get('action_category')
        scope_values = lesson.get('scope_values', {})
        lesson_strength = lesson.get('lesson_strength', 0.5)
        decay_halflife_hours = lesson.get('decay_halflife_hours')
        created_at = lesson.get('created_at')
        scope_dims = lesson.get('scope_dims', [])
        stats = lesson.get('stats', {})
        lesson_type = lesson.get('lesson_type') or 'pm_strength'
        
        if not pattern_key or not action_category:
            continue
        
        lesson_meta = _build_lesson_metadata(lesson, now)
        
        capital_levers = (lesson.get('effect') or {}).get('capital_levers', {})
        if capital_levers:
            decayed_capital = {}
            for lever_name, lever_value in capital_levers.items():
                decayed_capital[lever_name] = apply_decay(
                    lever_value,
                    lesson_strength,
                    decay_halflife_hours,
                    0.0  # already decayed when lesson created; runtime handles aging further
                )
            strength_overrides.append({
                'pattern_key': pattern_key,
                'action_category': action_category,
                'scope': scope_values,
                'scope_dims': scope_dims,
                'levers': decayed_capital,
                'lesson': lesson_meta,
                'stats': stats,
                'lesson_type': lesson_type
            })
        
        execution_levers = (lesson.get('effect') or {}).get('execution_levers', {})
        if execution_levers:
            decayed_execution: Dict[str, Any] = {}
            for lever_name, lever_value in execution_levers.items():
                if isinstance(lever_value, dict):
                    decayed_execution[lever_name] = {}
                    for sub_key, sub_value in lever_value.items():
                        decayed_execution[lever_name][sub_key] = apply_decay(
                            sub_value,
                            lesson_strength,
                            decay_halflife_hours,
                            0.0
                        )
                else:
                    decayed_execution[lever_name] = apply_decay(
                        lever_value,
                        lesson_strength,
                        decay_halflife_hours,
                        0.0
                    )
            
            execution_overrides.append({
                'pattern_key': pattern_key,
                'action_category': action_category,
                'scope': scope_values,
                'scope_dims': scope_dims,
                'levers': decayed_execution,
                'lesson': lesson_meta,
                'stats': stats,
                'lesson_type': lesson_type
            })
    
    return {
        'pattern_strength_overrides': strength_overrides,
        'pattern_overrides': execution_overrides
    }


def _build_dm_override_payload(lessons: List[Dict[str, Any]], now: datetime) -> List[Dict[str, Any]]:
    alloc_overrides: List[Dict[str, Any]] = []
    
    for lesson in lessons:
        pattern_key = lesson.get('pattern_key')
        action_category = lesson.get('action_category') or 'allocation'
        scope_values = lesson.get('scope_values', {})
        scope_dims = lesson.get('scope_dims', [])
        stats = lesson.get('stats', {})
        lesson_strength = lesson.get('lesson_strength', 0.5)
        decay_halflife_hours = lesson.get('decay_halflife_hours')
        lesson_type = lesson.get('lesson_type') or 'dm_alloc'
        
        effect = lesson.get('effect') or {}
        alloc_mult = None
        if 'capital_levers' in effect:
            alloc_mult = effect['capital_levers'].get('alloc_mult')
        if alloc_mult is None:
            alloc_mult = effect.get('alloc_multiplier')
        
        if not pattern_key or alloc_mult is None:
            continue
        
        lesson_meta = _build_lesson_metadata(lesson, now)
        decayed_alloc = apply_decay(alloc_mult, lesson_strength, decay_halflife_hours, 0.0)
        
        alloc_overrides.append({
            'pattern_key': pattern_key,
            'action_category': action_category,
            'scope': scope_values,
            'scope_dims': scope_dims,
            'levers': {'alloc_mult': decayed_alloc},
            'lesson': lesson_meta,
            'stats': stats,
            'lesson_type': lesson_type
        })
    
    return alloc_overrides


def materialize_overrides(
    sb_client: Client,
    module: str = 'pm',
    config_table: str = 'learning_configs',
    config_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Materialize active lessons into config overrides.
    
    Args:
        sb_client: Supabase client
        config_table: Table name for config (default 'learning_configs')
        config_key: Config key/ID (default 'pm_config')
    
    Returns:
        Dict with counts: {'lessons_processed': N, 'strength_overrides': M, 'execution_overrides': K}
    """
    try:
        config_key = config_key or module
        
        result = (
            sb_client.table('learning_lessons')
            .select('*')
            .eq('status', 'active')
            .eq('module', module)
            .execute()
        )
        
        lessons = result.data or []
        
        if not lessons:
            logger.info(f"No active lessons found for module {module}")
            return {'lessons_processed': 0}
        
        now = datetime.now(timezone.utc)
        
        if module == 'pm':
            payload = _build_pm_override_payload(lessons, now)
            counts = {
                'lessons_processed': len(lessons),
                'strength_overrides': len(payload['pattern_strength_overrides']),
                'execution_overrides': len(payload['pattern_overrides'])
            }
            config_update = {
                'pattern_strength_overrides': payload['pattern_strength_overrides'],
                'pattern_overrides': payload['pattern_overrides'],
                'override_updated_at': now.isoformat()
            }
        else:
            alloc_overrides = _build_dm_override_payload(lessons, now)
            counts = {
                'lessons_processed': len(lessons),
                'alloc_overrides': len(alloc_overrides)
            }
            config_update = {
                'alloc_overrides': alloc_overrides,
                'override_updated_at': now.isoformat()
            }
        
        try:
            config_result = (
                sb_client.table(config_table)
                .select('*')
                .eq('module_id', config_key)
                .execute()
            )
            
            config_data = {}
            if config_result.data and len(config_result.data) > 0:
                config_data = config_result.data[0].get('config_data', {}) or {}
            
            config_data.update(config_update)
            
            # Upsert config
            if config_result.data and len(config_result.data) > 0:
                sb_client.table(config_table).update({
                    'config_data': config_data,
                    'updated_at': now.isoformat(),
                    'updated_by': 'learning_system'
                }).eq('module_id', config_key).execute()
            else:
                sb_client.table(config_table).insert({
                    'module_id': config_key,
                    'config_data': config_data,
                    'updated_at': now.isoformat(),
                    'updated_by': 'learning_system'
                }).execute()
            
            logger.info(f"Materialized overrides for module {module}: {counts}")
            return counts
            
        except Exception as e:
            logger.error(f"Error writing to config: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Error materializing overrides: {e}")
        import traceback
        logger.error(traceback.format_exc())
        if module == 'pm':
            return {'lessons_processed': 0, 'strength_overrides': 0, 'execution_overrides': 0}
        return {'lessons_processed': 0, 'alloc_overrides': 0}


def run_override_materializer(
    sb_client: Optional[Client] = None
) -> Dict[str, int]:
    """
    Run override materializer job.
    
    Args:
        sb_client: Supabase client (creates if None)
    
    Returns:
        Dict with counts
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            return {
                'pm': {'lessons_processed': 0, 'strength_overrides': 0, 'execution_overrides': 0},
                'dm': {'lessons_processed': 0, 'alloc_overrides': 0}
            }
        sb_client = create_client(supabase_url, supabase_key)
    
    pm_counts = materialize_overrides(sb_client, module='pm', config_key='pm')
    dm_counts = materialize_overrides(sb_client, module='dm', config_key='dm')
    return {'pm': pm_counts, 'dm': dm_counts}


if __name__ == "__main__":
    # Standalone execution
    logging.basicConfig(level=logging.INFO)
    result = run_override_materializer()
    print(f"Override materializer result: {result}")

