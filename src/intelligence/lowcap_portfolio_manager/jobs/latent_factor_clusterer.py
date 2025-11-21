"""
Latent Factor Clusterer (v5.3)

Detects overlapping patterns and clusters them into latent factors.
Runs weekly to prevent double-counting in lessons/overrides.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from supabase import create_client, Client

logger = logging.getLogger(__name__)


def compute_pattern_overlap(
    pattern1_trades: Set[str],
    pattern2_trades: Set[str]
) -> float:
    """
    Compute overlap/correlation between two pattern match sets.
    
    Uses Jaccard similarity: |A ∩ B| / |A ∪ B|
    
    Args:
        pattern1_trades: Set of trade IDs matched by pattern1
        pattern2_trades: Set of trade IDs matched by pattern2
    
    Returns:
        Overlap score (0.0-1.0)
    """
    if not pattern1_trades or not pattern2_trades:
        return 0.0
    
    intersection = len(pattern1_trades & pattern2_trades)
    union = len(pattern1_trades | pattern2_trades)
    
    if union == 0:
        return 0.0
    
    return intersection / union


async def extract_pattern_match_sets(
    sb_client: Client,
    pattern_keys: List[str]
) -> Dict[str, Set[str]]:
    """
    Extract match sets for patterns from position_closed strands.
    
    For each pattern, find which trades (position IDs) matched it.
    
    Args:
        sb_client: Supabase client
        pattern_keys: List of pattern keys to extract
    
    Returns:
        Dict mapping pattern_key -> set of position IDs
    """
    match_sets: Dict[str, Set[str]] = defaultdict(set)
    
    try:
        # Query recent position_closed strands
        result = (
            sb_client.table('ad_strands')
            .select('id,content')
            .eq('kind', 'position_closed')
            .eq('module', 'pm')
            .order('created_at', desc=True)
            .limit(1000)
            .execute()
        )
        
        strands = result.data or []
        
        for strand in strands:
            content = strand.get('content', {})
            completed_trades = content.get('completed_trades', [])
            position_id = content.get('position_id') or strand.get('id', '')
            
            if not completed_trades or not position_id:
                continue
            
            # Check each action in completed_trades
            for trade_entry in completed_trades:
                if not isinstance(trade_entry, dict):
                    continue
                
                # Skip trade summary
                if 'outcome_class' in trade_entry:
                    continue
                
                pattern_key = trade_entry.get('pattern_key')
                if pattern_key and pattern_key in pattern_keys:
                    match_sets[pattern_key].add(str(position_id))
        
        return dict(match_sets)
        
    except Exception as e:
        logger.error(f"Error extracting pattern match sets: {e}")
        return {}


def cluster_patterns(
    match_sets: Dict[str, Set[str]],
    overlap_threshold: float = 0.7
) -> Dict[str, List[str]]:
    """
    Cluster patterns by overlap using hierarchical clustering.
    
    Args:
        match_sets: Dict mapping pattern_key -> set of trade IDs
        overlap_threshold: Minimum overlap to cluster together
    
    Returns:
        Dict mapping factor_id -> list of pattern_keys
    """
    if not match_sets:
        return {}
    
    pattern_keys = list(match_sets.keys())
    clusters: Dict[str, List[str]] = {}
    assigned: Set[str] = set()
    factor_counter = 1
    
    for pattern_key in pattern_keys:
        if pattern_key in assigned:
            continue
        
        # Start new cluster
        cluster = [pattern_key]
        assigned.add(pattern_key)
        
        # Find all patterns that overlap significantly
        pattern_trades = match_sets[pattern_key]
        
        for other_key in pattern_keys:
            if other_key in assigned or other_key == pattern_key:
                continue
            
            other_trades = match_sets[other_key]
            overlap = compute_pattern_overlap(pattern_trades, other_trades)
            
            if overlap >= overlap_threshold:
                cluster.append(other_key)
                assigned.add(other_key)
        
        # Create factor
        if len(cluster) > 1:  # Only create factor if multiple patterns
            factor_id = f"factor_{factor_counter:03d}"
            clusters[factor_id] = cluster
            factor_counter += 1
        # If single pattern, it's unique (no factor)
    
    return clusters


async def run_latent_factor_clusterer(
    sb_client: Optional[Client] = None,
    overlap_threshold: float = 0.7
) -> Dict[str, int]:
    """
    Run latent factor clustering job.
    
    Args:
        sb_client: Supabase client (creates if None)
        overlap_threshold: Minimum overlap to cluster (default 0.7)
    
    Returns:
        Dict with counts: {'patterns_processed': N, 'factors_created': M}
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            return {'patterns_processed': 0, 'factors_created': 0}
        sb_client = create_client(supabase_url, supabase_key)
    
    try:
        # Get all active pattern keys from lessons
        result = (
            sb_client.table('learning_lessons')
            .select('pattern_key')
            .eq('status', 'active')
            .execute()
        )
        
        lessons = result.data or []
        pattern_keys = list(set(lesson.get('pattern_key') for lesson in lessons if lesson.get('pattern_key')))
        
        if not pattern_keys:
            logger.info("No active patterns found")
            return {'patterns_processed': 0, 'factors_created': 0}
        
        # Extract match sets
        match_sets = await extract_pattern_match_sets(sb_client, pattern_keys)
        
        if not match_sets:
            logger.info("No match sets extracted (insufficient data)")
            return {'patterns_processed': len(pattern_keys), 'factors_created': 0}
        
        # Cluster patterns
        clusters = cluster_patterns(match_sets, overlap_threshold)
        
        factors_created = 0
        
        # Update learning_latent_factors table
        for factor_id, pattern_keys_in_cluster in clusters.items():
            # Find representative pattern (highest edge or most common)
            # For now, use first pattern as representative
            representative = pattern_keys_in_cluster[0]
            
            # Build correlation matrix
            correlation_matrix = {}
            for i, p1 in enumerate(pattern_keys_in_cluster):
                correlations = {}
                for j, p2 in enumerate(pattern_keys_in_cluster):
                    if i != j:
                        overlap = compute_pattern_overlap(
                            match_sets.get(p1, set()),
                            match_sets.get(p2, set())
                        )
                        correlations[p2] = overlap
                correlation_matrix[p1] = correlations
            
            try:
                # Check if factor exists
                existing = (
                    sb_client.table('learning_latent_factors')
                    .select('id')
                    .eq('factor_id', factor_id)
                    .execute()
                )
                
                factor_data = {
                    'factor_id': factor_id,
                    'pattern_keys': pattern_keys_in_cluster,
                    'representative_pattern': representative,
                    'correlation_matrix': correlation_matrix,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                if existing.data and len(existing.data) > 0:
                    sb_client.table('learning_latent_factors').update(factor_data).eq('id', existing.data[0]['id']).execute()
                else:
                    factor_data['created_at'] = datetime.now(timezone.utc).isoformat()
                    sb_client.table('learning_latent_factors').insert(factor_data).execute()
                
                factors_created += 1
            except Exception as e:
                logger.warning(f"Error creating factor {factor_id}: {e}")
                continue
        
        logger.info(f"Processed {len(pattern_keys)} patterns, created {factors_created} factors")
        return {'patterns_processed': len(pattern_keys), 'factors_created': factors_created}
        
    except Exception as e:
        logger.error(f"Error running latent factor clusterer: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'patterns_processed': 0, 'factors_created': 0}


if __name__ == "__main__":
    # Standalone execution
    import asyncio
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_latent_factor_clusterer())
    print(f"Latent factor clusterer result: {result}")

