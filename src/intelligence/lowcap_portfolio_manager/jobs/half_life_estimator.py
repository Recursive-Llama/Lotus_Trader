"""
Half-Life Estimator (v5.2)

Estimates decay half-life for patterns and updates learning_lessons.
Runs weekly to fit exponential decay curves.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

from supabase import create_client, Client

from src.intelligence.lowcap_portfolio_manager.jobs.lesson_builder_v5 import estimate_half_life

logger = logging.getLogger(__name__)


async def update_edge_history(
    sb_client: Client,
    pattern_key: str,
    action_category: str,
    scope_signature: str,
    edge_raw: float,
    n: int
) -> None:
    """
    Update edge history for a pattern+category+scope.
    
    Args:
        sb_client: Supabase client
        pattern_key: Pattern key
        action_category: Action category
        scope_signature: Scope signature (hash or sorted JSON)
        edge_raw: Current edge
        n: Sample count
    """
    try:
        sb_client.table('learning_edge_history').insert({
            'pattern_key': pattern_key,
            'action_category': action_category,
            'scope_signature': scope_signature,
            'edge_raw': edge_raw,
            'n': n,
            'ts': datetime.now(timezone.utc).isoformat()
        }).execute()
    except Exception as e:
        logger.warning(f"Error updating edge history: {e}")


async def run_half_life_estimator(
    sb_client: Optional[Client] = None,
    limit: int = 500
) -> Dict[str, int]:
    """
    Run half-life estimation job.
    
    For each active lesson, estimate half-life from edge history and update.
    
    Args:
        sb_client: Supabase client (creates if None)
        limit: Max lessons to process
    
    Returns:
        Dict with counts: {'processed': N, 'half_lives_updated': M}
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            return {'processed': 0, 'half_lives_updated': 0}
        sb_client = create_client(supabase_url, supabase_key)
    
    try:
        # Query active lessons
        result = (
            sb_client.table('learning_lessons')
            .select('*')
            .eq('status', 'active')
            .limit(limit)
            .execute()
        )
        
        lessons = result.data or []
        half_lives_updated = 0
        
        for lesson in lessons:
            pattern_key = lesson.get('pattern_key')
            action_category = lesson.get('action_category')
            scope_values = lesson.get('scope_values', {})
            
            if not pattern_key or not action_category or not scope_values:
                continue
            
            # Build scope signature
            scope_signature = json.dumps(sorted(scope_values.items()), sort_keys=True)
            
            # Query edge history
            try:
                history_result = (
                    sb_client.table('learning_edge_history')
                    .select('edge_raw,ts')
                    .eq('pattern_key', pattern_key)
                    .eq('action_category', action_category)
                    .eq('scope_signature', scope_signature)
                    .order('ts', desc=True)
                    .limit(30)
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
                
                if len(edge_history) >= 5:
                    half_life_hours = estimate_half_life(edge_history)
                    
                    if half_life_hours:
                        # Update lesson
                        sb_client.table('learning_lessons').update({
                            'decay_halflife_hours': int(half_life_hours),
                            'last_validated': datetime.now(timezone.utc).isoformat()
                        }).eq('id', lesson['id']).execute()
                        
                        half_lives_updated += 1
            except Exception as e:
                logger.warning(f"Error estimating half-life for lesson {lesson.get('id')}: {e}")
                continue
        
        logger.info(f"Processed {len(lessons)} lessons, updated {half_lives_updated} half-lives")
        return {'processed': len(lessons), 'half_lives_updated': half_lives_updated}
        
    except Exception as e:
        logger.error(f"Error running half-life estimator: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'processed': 0, 'half_lives_updated': 0}


async def snapshot_pattern_scope_stats(
    sb_client: Client
) -> int:
    """
    Snapshot current edge_raw from pattern_scope_stats into edge_history.
    Should be called periodically (e.g., daily) to build history.
    
    Args:
        sb_client: Supabase client
    
    Returns:
        Number of snapshots created
    """
    try:
        # Query pattern_scope_stats with sufficient samples
        result = (
            sb_client.table('pattern_scope_stats')
            .select('pattern_key,action_category,scope_values,stats,n')
            .gte('n', 10)
            .execute()
        )
        
        rows = result.data or []
        snapshots_created = 0
        
        for row in rows:
            pattern_key = row.get('pattern_key')
            action_category = row.get('action_category')
            scope_values = row.get('scope_values', {})
            stats = row.get('stats', {})
            n = row.get('n', 0)
            
            if not pattern_key or not action_category:
                continue
            
            scope_signature = json.dumps(sorted(scope_values.items()), sort_keys=True)
            edge_raw = stats.get('edge_raw', 0.0)
            
            try:
                await update_edge_history(
                    sb_client,
                    pattern_key,
                    action_category,
                    scope_signature,
                    edge_raw,
                    n
                )
                snapshots_created += 1
            except Exception as e:
                logger.warning(f"Error creating snapshot: {e}")
                continue
        
        logger.info(f"Created {snapshots_created} edge history snapshots")
        return snapshots_created
        
    except Exception as e:
        logger.error(f"Error snapshotting pattern_scope_stats: {e}")
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
    
    # First snapshot current stats
    print("Snapshotting current stats...")
    snapshots = asyncio.run(snapshot_pattern_scope_stats(sb_client))
    print(f"Created {snapshots} snapshots")
    
    # Then estimate half-lives
    print("Estimating half-lives...")
    result = asyncio.run(run_half_life_estimator(sb_client))
    print(f"Half-life estimator result: {result}")

