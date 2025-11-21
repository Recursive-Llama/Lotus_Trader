"""
v5 Learning System Scheduler

Orchestrates all v5 learning jobs:
- Pattern scope aggregator (every 1-4 hours)
- Lesson builder (periodic, e.g., every 6 hours)
- Override materializer (periodic, e.g., every 2 hours)
- Meta-learning jobs (v5.1 daily, v5.2/v5.3 weekly)

Can be run standalone or integrated into main scheduler.
"""

import logging
import os
import asyncio
from typing import Optional
from datetime import datetime, timezone, timedelta

from supabase import create_client, Client

from .pattern_scope_aggregator import run_pattern_scope_aggregator
from .lesson_builder_v5 import run_lesson_builder
from .override_materializer import run_override_materializer
from .regime_weight_learner import run_regime_weight_learner
from .half_life_estimator import run_half_life_estimator
from .latent_factor_clusterer import run_latent_factor_clusterer

logger = logging.getLogger(__name__)


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
                'v5_meta_learning_enabled': flags.get('v5_meta_learning_enabled', True),
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
        'v5_meta_learning_enabled': True,
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
    logger.info("Starting v5 learning system scheduler")
    
    # Pattern scope aggregator: Every 2 hours
    asyncio.create_task(schedule_interval(2, run_pattern_scope_aggregator, "Pattern Scope Aggregator"))
    
    # Lesson builder: Every 6 hours
    asyncio.create_task(schedule_interval(6, run_lesson_builder, "Lesson Builder"))
    
    # Override materializer: Every 2 hours
    asyncio.create_task(schedule_interval(2, run_override_materializer, "Override Materializer"))
    
    # Regime weight learner (v5.1): Daily at 01:00 UTC
    asyncio.create_task(schedule_daily(1, 0, run_regime_weight_learner, "Regime Weight Learner (v5.1)"))
    
    # Half-life estimator (v5.2): Weekly on Monday at 02:00 UTC
    asyncio.create_task(schedule_weekly(0, 2, 0, run_half_life_estimator, "Half-Life Estimator (v5.2)"))
    
    # Latent factor clusterer (v5.3): Weekly on Monday at 03:00 UTC
    asyncio.create_task(schedule_weekly(0, 3, 0, run_latent_factor_clusterer, "Latent Factor Clusterer (v5.3)"))
    
    logger.info("All v5 learning jobs scheduled")


async def run_all_jobs_once(sb_client: Optional[Client] = None):
    """
    Run all v5 learning jobs once (for testing or manual execution).
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_KEY")
            return
        sb_client = create_client(supabase_url, supabase_key)
    
    flags = get_feature_flags(sb_client)
    
    results = {}
    
    if flags.get('v5_aggregation_enabled', True):
        logger.info("Running Pattern Scope Aggregator...")
        try:
            results['aggregator'] = await asyncio.to_thread(run_pattern_scope_aggregator, sb_client)
        except Exception as e:
            logger.error(f"Aggregator error: {e}", exc_info=True)
            results['aggregator'] = {'error': str(e)}
    
    if flags.get('v5_lesson_builder_enabled', True):
        logger.info("Running Lesson Builder...")
        try:
            results['lesson_builder'] = await asyncio.to_thread(run_lesson_builder, sb_client)
        except Exception as e:
            logger.error(f"Lesson Builder error: {e}", exc_info=True)
            results['lesson_builder'] = {'error': str(e)}
    
    if flags.get('v5_override_materializer_enabled', True):
        logger.info("Running Override Materializer...")
        try:
            results['override_materializer'] = await asyncio.to_thread(run_override_materializer, sb_client)
        except Exception as e:
            logger.error(f"Override Materializer error: {e}", exc_info=True)
            results['override_materializer'] = {'error': str(e)}
    
    if flags.get('v5_meta_learning_enabled', True):
        logger.info("Running Regime Weight Learner (v5.1)...")
        try:
            results['regime_weight_learner'] = await asyncio.to_thread(run_regime_weight_learner, sb_client)
        except Exception as e:
            logger.error(f"Regime Weight Learner error: {e}", exc_info=True)
            results['regime_weight_learner'] = {'error': str(e)}
        
        logger.info("Running Half-Life Estimator (v5.2)...")
        try:
            results['half_life_estimator'] = await asyncio.to_thread(run_half_life_estimator, sb_client)
        except Exception as e:
            logger.error(f"Half-Life Estimator error: {e}", exc_info=True)
            results['half_life_estimator'] = {'error': str(e)}
        
        logger.info("Running Latent Factor Clusterer (v5.3)...")
        try:
            results['latent_factor_clusterer'] = await asyncio.to_thread(run_latent_factor_clusterer, sb_client)
        except Exception as e:
            logger.error(f"Latent Factor Clusterer error: {e}", exc_info=True)
            results['latent_factor_clusterer'] = {'error': str(e)}
    
    return results


if __name__ == "__main__":
    # Standalone execution - run all jobs once
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    results = asyncio.run(run_all_jobs_once())
    print("\n=== v5 Learning System Job Results ===")
    for job, result in results.items():
        print(f"{job}: {result}")

