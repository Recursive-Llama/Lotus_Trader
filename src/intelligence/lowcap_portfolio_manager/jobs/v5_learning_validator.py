"""
v5 Learning System Validator

Validates that the v5 learning system is working correctly:
- All tables exist and have data
- Action logging is emitting required fields
- Stats aggregation is working
- Lessons are being created
- Overrides are materialized
- Meta-learning jobs are running
"""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from supabase import create_client, Client

logger = logging.getLogger(__name__)


def validate_v5_learning_system(sb_client: Optional[Client] = None) -> Dict[str, Any]:
    """
    Validate v5 learning system health.
    
    Returns:
        Dict with validation results for each component
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            return {'error': 'Missing Supabase credentials'}
        sb_client = create_client(supabase_url, supabase_key)
    
    results = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'tables': {},
        'logging': {},
        'aggregation': {},
        'lessons': {},
        'overrides': {},
        'meta_learning': {},
        'overall_status': 'unknown'
    }
    
    # 1. Check tables exist and have data
    try:
        # pattern_scope_stats
        stats_result = sb_client.table('pattern_scope_stats').select('id', count='exact').limit(1).execute()
        results['tables']['pattern_scope_stats'] = {
            'exists': True,
            'row_count': stats_result.count if hasattr(stats_result, 'count') else 'unknown'
        }
    except Exception as e:
        results['tables']['pattern_scope_stats'] = {'exists': False, 'error': str(e)}
    
    try:
        # learning_lessons
        lessons_result = sb_client.table('learning_lessons').select('id', count='exact').limit(1).execute()
        results['tables']['learning_lessons'] = {
            'exists': True,
            'row_count': lessons_result.count if hasattr(lessons_result, 'count') else 'unknown'
        }
    except Exception as e:
        results['tables']['learning_lessons'] = {'exists': False, 'error': str(e)}
    
    try:
        # learning_regime_weights
        weights_result = sb_client.table('learning_regime_weights').select('id', count='exact').limit(1).execute()
        results['tables']['learning_regime_weights'] = {
            'exists': True,
            'row_count': weights_result.count if hasattr(weights_result, 'count') else 'unknown'
        }
    except Exception as e:
        results['tables']['learning_regime_weights'] = {'exists': False, 'error': str(e)}
    
    try:
        # learning_edge_history
        history_result = sb_client.table('learning_edge_history').select('id', count='exact').limit(1).execute()
        results['tables']['learning_edge_history'] = {
            'exists': True,
            'row_count': history_result.count if hasattr(history_result, 'count') else 'unknown'
        }
    except Exception as e:
        results['tables']['learning_edge_history'] = {'exists': False, 'error': str(e)}
    
    try:
        # learning_latent_factors
        factors_result = sb_client.table('learning_latent_factors').select('id', count='exact').limit(1).execute()
        results['tables']['learning_latent_factors'] = {
            'exists': True,
            'row_count': factors_result.count if hasattr(factors_result, 'count') else 'unknown'
        }
    except Exception as e:
        results['tables']['learning_latent_factors'] = {'exists': False, 'error': str(e)}
    
    # 2. Check action logging (check recent strands)
    try:
        # Check for v5 fields in recent strands
        strands_result = (
            sb_client.table('ad_strands')
            .select('content')
            .order('ts', desc=True)
            .limit(100)
            .execute()
        )
        
        v5_fields_count = 0
        total_strands = len(strands_result.data or [])
        
        for strand in (strands_result.data or []):
            content = strand.get('content', {})
            if content.get('pattern_key') and content.get('action_category'):
                v5_fields_count += 1
        
        results['logging'] = {
            'recent_strands_checked': total_strands,
            'strands_with_v5_fields': v5_fields_count,
            'v5_logging_rate': v5_fields_count / total_strands if total_strands > 0 else 0.0
        }
    except Exception as e:
        results['logging'] = {'error': str(e)}
    
    # 3. Check aggregation stats
    try:
        stats_sample = (
            sb_client.table('pattern_scope_stats')
            .select('pattern_key, action_category, n, stats')
            .gte('n', 10)
            .limit(10)
            .execute()
        )
        
        subset_sizes = set()
        for stat in (stats_sample.data or []):
            scope_mask = stat.get('scope_mask', 0)
            # Count bits set in mask
            size = bin(scope_mask).count('1')
            subset_sizes.add(size)
        
        results['aggregation'] = {
            'stats_with_n_ge_10': len(stats_sample.data or []),
            'subset_sizes_found': sorted(list(subset_sizes)),
            'has_multiple_subset_sizes': len(subset_sizes) > 1
        }
    except Exception as e:
        results['aggregation'] = {'error': str(e)}
    
    # 4. Check lessons
    try:
        lessons_sample = (
            sb_client.table('learning_lessons')
            .select('pattern_key, action_category, effect, lesson_strength, decay_halflife_hours, latent_factor_id')
            .eq('status', 'active')
            .limit(10)
            .execute()
        )
        
        lessons_with_v5_fields = 0
        for lesson in (lessons_sample.data or []):
            if lesson.get('pattern_key') and lesson.get('action_category'):
                lessons_with_v5_fields += 1
        
        results['lessons'] = {
            'active_lessons': len(lessons_sample.data or []),
            'lessons_with_v5_fields': lessons_with_v5_fields,
            'has_capital_levers': any(
                'capital_levers' in (l.get('effect', {}) or {})
                for l in (lessons_sample.data or [])
            ),
            'has_execution_levers': any(
                'execution_levers' in (l.get('effect', {}) or {})
                for l in (lessons_sample.data or [])
            )
        }
    except Exception as e:
        results['lessons'] = {'error': str(e)}
    
    # 5. Check overrides
    try:
        config_result = (
            sb_client.table('learning_configs')
            .select('config_data')
            .eq('module_id', 'pm')
            .execute()
        )
        
        if config_result.data and len(config_result.data) > 0:
            config = config_result.data[0].get('config_data', {})
            strength_overrides = config.get('pattern_strength_overrides', [])
            execution_overrides = config.get('pattern_overrides', [])
            
            results['overrides'] = {
                'config_exists': True,
                'strength_overrides_count': len(strength_overrides),
                'execution_overrides_count': len(execution_overrides),
                'last_updated': config.get('override_updated_at')
            }
        else:
            results['overrides'] = {'config_exists': False}
    except Exception as e:
        results['overrides'] = {'error': str(e)}
    
    # 6. Check meta-learning
    try:
        weights_count = (
            sb_client.table('learning_regime_weights')
            .select('id', count='exact')
            .limit(1)
            .execute()
        ).count if hasattr((sb_client.table('learning_regime_weights').select('id', count='exact').limit(1).execute()), 'count') else 0
        
        history_count = (
            sb_client.table('learning_edge_history')
            .select('id', count='exact')
            .limit(1)
            .execute()
        ).count if hasattr((sb_client.table('learning_edge_history').select('id', count='exact').limit(1).execute()), 'count') else 0
        
        factors_count = (
            sb_client.table('learning_latent_factors')
            .select('id', count='exact')
            .limit(1)
            .execute()
        ).count if hasattr((sb_client.table('learning_latent_factors').select('id', count='exact').limit(1).execute()), 'count') else 0
        
        results['meta_learning'] = {
            'regime_weights_count': weights_count,
            'edge_history_count': history_count,
            'latent_factors_count': factors_count
        }
    except Exception as e:
        results['meta_learning'] = {'error': str(e)}
    
    # Determine overall status
    all_checks_passed = (
        all(t.get('exists', False) for t in results['tables'].values() if 'exists' in t) and
        results['logging'].get('v5_logging_rate', 0) > 0.5 and
        results['aggregation'].get('has_multiple_subset_sizes', False) and
        results['lessons'].get('lessons_with_v5_fields', 0) > 0
    )
    
    results['overall_status'] = 'healthy' if all_checks_passed else 'degraded'
    
    return results


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    results = validate_v5_learning_system()
    print(json.dumps(results, indent=2))

