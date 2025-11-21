"""
Regime Weight Learner (v5.1)

Learns regime-specific weights for time efficiency, field coherence, recurrence, variance.
Runs daily to update learning_regime_weights table.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from supabase import create_client, Client

logger = logging.getLogger(__name__)


def build_regime_signature(scope: Dict[str, Any]) -> str:
    """
    Build regime signature from scope.
    
    Args:
        scope: Scope dict with macro/meso/micro phases and bucket_rank
    
    Returns:
        Regime signature string
    """
    macro = scope.get('macro_phase', 'Unknown')
    meso = scope.get('meso_phase', 'Unknown')
    micro = scope.get('micro_phase', 'Unknown')
    bucket_rank = scope.get('bucket_rank_position')
    
    sig = f"macro={macro}|meso={meso}|micro={micro}"
    if bucket_rank:
        sig += f"|bucket_rank={bucket_rank}"
    
    return sig


async def learn_regime_weights(
    sb_client: Client,
    pattern_key: str,
    action_category: str,
    regime_signature: str,
    samples: List[Dict[str, Any]]
) -> Optional[Dict[str, float]]:
    """
    Learn regime-specific weights from samples.
    
    Measures which multipliers (time_efficiency, field_coherence, etc.) correlate
    most with edge improvements.
    
    Args:
        sb_client: Supabase client
        pattern_key: Pattern key
        action_category: Action category
        regime_signature: Regime signature
        samples: List of sample dicts with edge_raw, time_efficiency, field_coherence, etc.
    
    Returns:
        Learned weights dict, or None if insufficient data
    """
    if len(samples) < 10:
        return None  # Insufficient data
    
    # Extract features and targets
    features = {
        'time_efficiency': [],
        'field_coherence': [],
        'recurrence': [],
        'variance': []
    }
    targets = []  # edge_raw values
    
    for sample in samples:
        edge_raw = sample.get('edge_raw', 0.0)
        stats = sample.get('stats', {})
        
        time_eff = stats.get('time_efficiency')
        field_coh = stats.get('field_coherence')
        recur = stats.get('recurrence_score')
        variance = stats.get('variance', 0.0)
        
        if time_eff is not None:
            features['time_efficiency'].append(time_eff)
        else:
            features['time_efficiency'].append(None)
        
        if field_coh is not None:
            features['field_coherence'].append(field_coh)
        else:
            features['field_coherence'].append(None)
        
        if recur is not None:
            features['recurrence'].append(recur)
        else:
            features['recurrence'].append(None)
        
        features['variance'].append(variance)
        targets.append(edge_raw)
    
    # Simple correlation-based weighting
    # For each feature, compute correlation with edge_raw
    weights = {}
    
    for feature_name, values in features.items():
        # Filter out None values
        valid_pairs = [(v, t) for v, t in zip(values, targets) if v is not None]
        
        if len(valid_pairs) < 5:
            weights[feature_name] = 1.0  # Default weight
            continue
        
        feature_vals = [v for v, _ in valid_pairs]
        target_vals = [t for _, t in valid_pairs]
        
        # Compute correlation
        n = len(feature_vals)
        mean_f = sum(feature_vals) / n
        mean_t = sum(target_vals) / n
        
        numerator = sum((f - mean_f) * (t - mean_t) for f, t in zip(feature_vals, target_vals))
        denom_f = sum((f - mean_f) ** 2 for f in feature_vals)
        denom_t = sum((t - mean_t) ** 2 for t in target_vals)
        
        if denom_f > 0 and denom_t > 0:
            correlation = numerator / (denom_f * denom_t) ** 0.5
            # Convert correlation to weight (0.5 to 1.5 range)
            weight = 0.5 + correlation
            weight = max(0.3, min(1.7, weight))  # Clamp to reasonable range
        else:
            weight = 1.0  # Default
        
        weights[feature_name] = weight
    
    return weights


async def run_regime_weight_learner(
    sb_client: Optional[Client] = None,
    limit: int = 1000
) -> Dict[str, int]:
    """
    Run regime weight learning job.
    
    Args:
        sb_client: Supabase client (creates if None)
        limit: Max pattern_scope_stats rows to process
    
    Returns:
        Dict with counts: {'processed': N, 'weights_updated': M}
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            return {'processed': 0, 'weights_updated': 0}
        sb_client = create_client(supabase_url, supabase_key)
    
    try:
        # Query pattern_scope_stats with sufficient samples
        result = (
            sb_client.table('pattern_scope_stats')
            .select('*')
            .gte('n', 10)
            .limit(limit)
            .execute()
        )
        
        rows = result.data or []
        
        # Group by (pattern_key, action_category, regime_signature)
        groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
        
        for row in rows:
            pattern_key = row.get('pattern_key')
            action_category = row.get('action_category')
            scope_values = row.get('scope_values', {})
            stats = row.get('stats', {})
            
            if not pattern_key or not action_category:
                continue
            
            regime_sig = build_regime_signature(scope_values)
            
            groups[(pattern_key, action_category, regime_sig)].append({
                'edge_raw': stats.get('edge_raw', 0.0),
                'stats': stats
            })
        
        weights_updated = 0
        
        # Learn weights for each group
        for (pattern_key, action_category, regime_sig), samples in groups.items():
            if len(samples) < 10:
                continue
            
            weights = await learn_regime_weights(
                sb_client,
                pattern_key,
                action_category,
                regime_sig,
                samples
            )
            
            if not weights:
                continue
            
            # Upsert to learning_regime_weights
            try:
                # Check if exists
                existing = (
                    sb_client.table('learning_regime_weights')
                    .select('id')
                    .eq('pattern_key', pattern_key)
                    .eq('action_category', action_category)
                    .eq('regime_signature', regime_sig)
                    .execute()
                )
                
                n_samples = len(samples)
                confidence = min(1.0, n_samples / 50.0)  # Confidence increases with samples
                
                weight_data = {
                    'pattern_key': pattern_key,
                    'action_category': action_category,
                    'regime_signature': regime_sig,
                    'weights': weights,
                    'n_samples': n_samples,
                    'confidence': confidence,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                if existing.data and len(existing.data) > 0:
                    sb_client.table('learning_regime_weights').update(weight_data).eq('id', existing.data[0]['id']).execute()
                else:
                    weight_data['created_at'] = datetime.now(timezone.utc).isoformat()
                    sb_client.table('learning_regime_weights').insert(weight_data).execute()
                
                weights_updated += 1
            except Exception as e:
                logger.warning(f"Error updating regime weights for {pattern_key}/{action_category}/{regime_sig}: {e}")
                continue
        
        logger.info(f"Processed {len(rows)} rows, updated {weights_updated} regime weight entries")
        return {'processed': len(rows), 'weights_updated': weights_updated}
        
    except Exception as e:
        logger.error(f"Error running regime weight learner: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'processed': 0, 'weights_updated': 0}


if __name__ == "__main__":
    # Standalone execution
    import asyncio
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_regime_weight_learner())
    print(f"Regime weight learner result: {result}")

