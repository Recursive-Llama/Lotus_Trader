"""
Braiding Lesson Builder Job

Periodic job to build lessons from braids.
Runs after trades close to compress braids into actionable lessons.

Usage:
    - Run after every N closed trades (e.g., every 5 trades)
    - Or run on a schedule (e.g., daily)
    - Can be called from learning system or as standalone job
"""

import logging
import os
from typing import Optional
from supabase import create_client, Client

from src.intelligence.lowcap_portfolio_manager.pm.braiding_system import build_lessons_from_braids

logger = logging.getLogger(__name__)


def run_lesson_builder(
    sb_client: Optional[Client] = None,
    module: str = 'pm',
    n_min: int = 10,
    edge_min: float = 0.5,
    incremental_min: float = 0.1,
    max_lessons_per_family: int = 3
) -> int:
    """
    Run lesson builder for a module.
    
    Args:
        sb_client: Supabase client (creates if None)
        module: 'pm' or 'dm'
        n_min: Minimum sample size
        edge_min: Minimum edge score
        incremental_min: Minimum incremental edge vs parents
        max_lessons_per_family: Maximum lessons per family
    
    Returns:
        Number of lessons created/updated
    """
    import asyncio
    
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            return 0
        sb_client = create_client(supabase_url, supabase_key)
    
    try:
        # Run async function
        return asyncio.run(build_lessons_from_braids(
            sb_client=sb_client,
            module=module,
            n_min=n_min,
            edge_min=edge_min,
            incremental_min=incremental_min,
            max_lessons_per_family=max_lessons_per_family
        ))
    except Exception as e:
        logger.error(f"Error running lesson builder: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 0


def run_all_modules(
    sb_client: Optional[Client] = None,
    n_min: int = 10,
    edge_min: float = 0.5,
    incremental_min: float = 0.1,
    max_lessons_per_family: int = 3
) -> dict:
    """
    Run lesson builder for both PM and DM modules.
    
    Args:
        sb_client: Supabase client (creates if None)
        n_min: Minimum sample size
        edge_min: Minimum edge score
        incremental_min: Minimum incremental edge vs parents
        max_lessons_per_family: Maximum lessons per family
    
    Returns:
        Dict with counts: {'pm': N, 'dm': M}
    """
    results = {}
    
    # Build PM lessons
    logger.info("Building PM lessons...")
    results['pm'] = run_lesson_builder(
        sb_client=sb_client,
        module='pm',
        n_min=n_min,
        edge_min=edge_min,
        incremental_min=incremental_min,
        max_lessons_per_family=max_lessons_per_family
    )
    
    # Build DM lessons
    logger.info("Building DM lessons...")
    results['dm'] = run_lesson_builder(
        sb_client=sb_client,
        module='dm',
        n_min=n_min,
        edge_min=edge_min,
        incremental_min=incremental_min,
        max_lessons_per_family=max_lessons_per_family
    )
    
    logger.info(f"Lesson builder complete: PM={results['pm']}, DM={results['dm']}")
    return results


if __name__ == "__main__":
    # Standalone execution
    logging.basicConfig(level=logging.INFO)
    results = run_all_modules()
    print(f"Lessons created: {results}")

