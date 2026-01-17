"""
v5 Learning System Scheduler

Orchestrates Learning System v2 jobs:
- TrajectoryMiner: Mines trajectories → generates overrides (every 2 hours)

Legacy pipeline (DEPRECATED):
- Pattern scope aggregator
- Lesson builder
- Override materializer

Can be run standalone or integrated into main scheduler.
"""

import logging
import os
import asyncio
from typing import Optional
from datetime import datetime, timezone, timedelta

from supabase import create_client, Client

# v2 Learning System
from src.intelligence.lowcap_portfolio_manager.learning.trajectory_miner import TrajectoryMiner

# Legacy imports - kept for backwards compatibility but deprecated
# from .pattern_scope_aggregator import run_pattern_scope_aggregator
# from .lesson_builder_v5 import build_lessons_from_pattern_scope_stats
# from .override_materializer import run_override_materializer

logger = logging.getLogger(__name__)


def run_trajectory_miner(sb_client: Client = None) -> None:
    """
    Run TrajectoryMiner (Learning System v2).
    Mines trajectories and writes overrides to pm_overrides.
    """
    try:
        miner = TrajectoryMiner()
        miner.run()
    except Exception as e:
        logger.error(f"TrajectoryMiner error: {e}", exc_info=True)
        raise


# Legacy - kept for backwards compatibility
def run_lesson_builder(sb_client: Client) -> None:
    """DEPRECATED: Use run_trajectory_miner instead."""
    logger.warning("run_lesson_builder is DEPRECATED. Use run_trajectory_miner.")
    run_trajectory_miner(sb_client)


def get_feature_flags(sb_client: Client) -> dict:
    """
    Get v5 learning feature flags from config.
    
    Returns:
        Dict with feature flags (defaults to enabled if not set)
    """
    try:
        result = (
            sb_client.table('learning_configs')
            .select('config_data')
            .eq('module_id', 'pm')
            .execute()
        )
        
        if result.data and len(result.data) > 0:
            config = result.data[0].get('config_data', {})
            flags = config.get('feature_flags', {})
            return {
                'learning_overrides_enabled': flags.get('learning_overrides_enabled', True),
                'learning_overrides_enabled_regimes': flags.get('learning_overrides_enabled_regimes', []),
                'learning_overrides_enabled_buckets': flags.get('learning_overrides_enabled_buckets', []),
                'v5_aggregation_enabled': flags.get('v5_aggregation_enabled', True),
                'v5_lesson_builder_enabled': flags.get('v5_lesson_builder_enabled', True),
                'v5_override_materializer_enabled': flags.get('v5_override_materializer_enabled', True)
            }
    except Exception as e:
        logger.warning(f"Error loading feature flags: {e}, using defaults")
    
    # Defaults: all enabled
    return {
        'learning_overrides_enabled': True,
        'learning_overrides_enabled_regimes': [],
        'learning_overrides_enabled_buckets': [],
        'v5_aggregation_enabled': True,
        'v5_lesson_builder_enabled': True,
        'v5_override_materializer_enabled': True
    }


async def schedule_v5_learning_jobs(sb_client: Optional[Client] = None):
    """
    Schedule all v5 learning jobs.
    
    Schedule:
    - Pattern scope aggregator: Every 2 hours (at :00, :02)
    - Lesson builder: Every 6 hours (at :00, :06, :12, :18)
    - Override materializer: Every 2 hours (at :05, :07)
    - Regime weight learner (v5.1): Daily at 01:00 UTC
    - Half-life estimator (v5.2): Weekly on Monday at 02:00 UTC
    - Latent factor clusterer (v5.3): Weekly on Monday at 03:00 UTC
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_KEY")
            return
        sb_client = create_client(supabase_url, supabase_key)
    
    async def schedule_hourly(offset_min: int, func, job_name: str):
        """Schedule job to run hourly at :offset_min"""
        while True:
            now = datetime.now(timezone.utc)
            next_run = now.replace(minute=offset_min, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + timedelta(hours=1)
            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"{job_name} scheduled for {next_run.isoformat()} (in {wait_seconds/60:.1f} minutes)")
            await asyncio.sleep(wait_seconds)
            try:
                await asyncio.to_thread(func, sb_client)
                logger.info(f"{job_name} completed")
            except Exception as e:
                logger.error(f"{job_name} error: {e}", exc_info=True)
    
    async def schedule_daily(offset_hour: int, offset_min: int, func, job_name: str):
        """Schedule job to run daily at offset_hour:offset_min UTC"""
        while True:
            now = datetime.now(timezone.utc)
            next_run = now.replace(hour=offset_hour, minute=offset_min, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + timedelta(days=1)
            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"{job_name} scheduled for {next_run.isoformat()} (in {wait_seconds/3600:.1f} hours)")
            await asyncio.sleep(wait_seconds)
            try:
                await asyncio.to_thread(func, sb_client)
                logger.info(f"{job_name} completed")
            except Exception as e:
                logger.error(f"{job_name} error: {e}", exc_info=True)
    
    async def schedule_weekly(weekday: int, offset_hour: int, offset_min: int, func, job_name: str):
        """Schedule job to run weekly on weekday (0=Monday) at offset_hour:offset_min UTC"""
        while True:
            now = datetime.now(timezone.utc)
            days_until_weekday = (weekday - now.weekday()) % 7
            if days_until_weekday == 0:
                # Today is the weekday, check if time has passed
                next_run = now.replace(hour=offset_hour, minute=offset_min, second=0, microsecond=0)
                if next_run <= now:
                    days_until_weekday = 7
            if days_until_weekday > 0:
                next_run = now.replace(hour=offset_hour, minute=offset_min, second=0, microsecond=0) + timedelta(days=days_until_weekday)
            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"{job_name} scheduled for {next_run.isoformat()} (in {wait_seconds/3600:.1f} hours)")
            await asyncio.sleep(wait_seconds)
            try:
                await asyncio.to_thread(func, sb_client)
                logger.info(f"{job_name} completed")
            except Exception as e:
                logger.error(f"{job_name} error: {e}", exc_info=True)
    
    async def schedule_interval(interval_hours: int, func, job_name: str):
        """Schedule job to run every N hours"""
        while True:
            try:
                flags = get_feature_flags(sb_client)
                if flags.get(f'v5_{job_name.lower().replace(" ", "_")}_enabled', True):
                    await asyncio.to_thread(func, sb_client)
                    logger.info(f"{job_name} completed")
                else:
                    logger.debug(f"{job_name} disabled by feature flag")
            except Exception as e:
                logger.error(f"{job_name} error: {e}", exc_info=True)
            await asyncio.sleep(interval_hours * 3600)
    
    # Start all jobs
    logger.info("Starting Learning System v2 scheduler")
    
    # TrajectoryMiner: Every 2 hours (replaces legacy aggregator → builder → materializer)
    asyncio.create_task(schedule_interval(2, run_trajectory_miner, "TrajectoryMiner"))
    
    # Legacy jobs REMOVED:
    # - Pattern scope aggregator: Replaced by trajectory_classifier
    # - Lesson builder: Replaced by TrajectoryMiner._mine_strength_lessons / _mine_tuning_lessons
    # - Override materializer: Replaced by TrajectoryMiner._write_overrides
    
    logger.info("Learning System v2 scheduler started")


async def run_all_jobs_once(sb_client: Optional[Client] = None):
    """
    Run Learning System v2 jobs once (for testing or manual execution).
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_KEY")
            return {'error': 'Missing credentials'}
        sb_client = create_client(supabase_url, supabase_key)
    
    results = {}
    
    # Run TrajectoryMiner (v2 - replaces legacy pipeline)
    logger.info("Running TrajectoryMiner...")
    try:
        await asyncio.to_thread(run_trajectory_miner, sb_client)
        results['trajectory_miner'] = {'status': 'completed'}
    except Exception as e:
        logger.error(f"TrajectoryMiner error: {e}", exc_info=True)
        results['trajectory_miner'] = {'error': str(e)}
    
    return results


if __name__ == "__main__":
    # Standalone execution - run all jobs once
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    results = asyncio.run(run_all_jobs_once())
    print("\n=== v5 Learning System Job Results ===")
    for job, result in results.items():
        print(f"{job}: {result}")

