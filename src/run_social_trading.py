#!/usr/bin/env python3
"""
Social Trading System - Main Entry Point

Orchestrates the complete social trading flow:
Social Monitoring → Decision Making → Trading → Position Management
"""

import asyncio
import logging
import signal
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.append('src')

# Configure logging to be minimal
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('social_trading.log')
    ]
)

logger = logging.getLogger(__name__)

# Import real components
from utils.supabase_manager import SupabaseManager
from supabase import create_client
from llm_integration.openrouter_client import OpenRouterClient

# Import real components
from intelligence.social_ingest.social_ingest_basic import SocialIngestModule
from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
# Defer trader imports to initialization to allow V2-only startup without
# importing V1 when refactor is underway.
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from trading.jupiter_client import JupiterClient
from trading.wallet_manager import WalletManager
from trading.scheduled_price_collector import ScheduledPriceCollector


class SocialTradingSystem:
    """
    Main Social Trading System
    
    Orchestrates all components:
    - Social monitoring (Twitter/Telegram)
    - Decision making
    - Trading execution
    - Position management
    - Learning system
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the social trading system"""
        self.config = config or self._get_default_config()
        self.running = False
        self.tasks = []
        
        # Initialize components (will be set up in initialize())
        self.supabase_manager = None
        self.llm_client = None
        self.social_ingest = None
        self.decision_maker = None
        self.learning_system = None
        self.price_collector = None
        
        # Output tracking
        self.last_output_time = datetime.now()
        self.output_interval = 5  # seconds between status updates
        
        print("🚀 Social Trading System initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration from YAML file"""
        import yaml
        from pathlib import Path
        
        config_path = Path(__file__).parent / 'config' / 'social_trading_config.yaml'
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                # Override with environment variables if available
                if os.getenv('SUPABASE_URL'):
                    config['database']['url'] = os.getenv('SUPABASE_URL')
                if os.getenv('SUPABASE_KEY'):
                    config['database']['key'] = os.getenv('SUPABASE_KEY')
                if os.getenv('BOOK_NAV'):
                    config['trading']['book_nav'] = float(os.getenv('BOOK_NAV'))
                return config
        else:
            # Fallback to hardcoded config if YAML doesn't exist
            return {
                'database': {
                    'url': os.getenv('SUPABASE_URL', 'postgresql://postgres:password@localhost:5432/lotus_trader'),
                    'key': os.getenv('SUPABASE_KEY', ''),
                    'schema': 'public'
                },
                'social_monitoring': {
                    'twitter_enabled': True,
                    'telegram_enabled': True,
                    'check_interval': 30  # seconds
                },
                'trading': {
                    'book_nav': float(os.getenv('BOOK_NAV', '100000.0')),  # $100k
                    'max_exposure_pct': 20.0,
                    'min_curator_score': 0.6,
                    'default_allocation_pct': 25.0,  # 25% default allocation
                    'min_allocation_pct': 10.0,  # Minimum 10% allocation
                    'max_allocation_pct': 40.0,  # Maximum 40% allocation
                    'slippage_pct': 1.0
                },
                'position_management': {
                    'price_check_interval': 30,  # seconds - check prices every 30s
                    'exit_check_interval': 30,   # seconds
                    'jupiter_price_enabled': True
                },
                'jupiter': {
                    'api_url': 'https://lite-api.jup.ag/swap/v1',
                    'price_url': 'https://lite-api.jup.ag/price/v3'
                }
            }
    
    async def initialize(self):
        """Initialize all system components"""
        try:
            print("🔧 Initializing components...")
            
            # Initialize Supabase manager (loads from environment variables)
            self.supabase_manager = SupabaseManager()
            
            # Initialize LLM client
            self.llm_client = OpenRouterClient()
            
            # Initialize trading components
            self.jupiter_client = JupiterClient()
            self.wallet_manager = WalletManager()
            
            # Initialize learning system first
            self.learning_system = UniversalLearningSystem(
                supabase_manager=self.supabase_manager,
                llm_client=self.llm_client,
                llm_config=None
            )
            
            # Initialize social ingest module
            self.social_ingest = SocialIngestModule(
                supabase_manager=self.supabase_manager,
                llm_client=self.llm_client,
                config_path="src/config/twitter_curators.yaml"
            )
            
            # Pass learning system to social ingest for strand processing
            self.social_ingest.learning_system = self.learning_system
            
            # Initialize decision maker with learning system reference
            self.decision_maker = DecisionMakerLowcapSimple(
                supabase_manager=self.supabase_manager,
                config=self.config,  # Pass full config so AllocationManager can access allocation_config
                learning_system=self.learning_system
            )
            
            # PriceOracle initialization (extracted from TraderLowcapSimpleV2)
            from trading.price_oracle_factory import create_price_oracle
            price_oracle = create_price_oracle()
            print("   [⚡] Price Oracle... OK")
            
            # Wire up dependencies
            self.learning_system.set_decision_maker(self.decision_maker)
            self.supabase_manager.wallet_manager = self.wallet_manager
            
            # Initialize scheduled price collector (using extracted PriceOracle)
            self.price_collector = ScheduledPriceCollector(
                supabase_manager=self.supabase_manager,
                price_oracle=price_oracle
            )
            
            # PM Executor is initialized directly in pm_core_tick.py (no registration needed)
            # PM uses direct calls to PMExecutor, not event-driven execution
                if os.getenv("ACTIONS_ENABLED", "0") == "1":
                print("   [⚡] PM Executor... Enabled (Direct calls from PM Core Tick)")
            else:
                print("   [⋇] PM Executor... Disabled (Read-Only)")
            
            print("✅ All components initialized")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize system: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def start_social_monitoring(self):
        """Start social media monitoring with clean output"""
        try:
            print("📱 Starting social media monitoring...")
            
            # Import and run the existing social monitor
            from intelligence.social_ingest.run_social_monitor import SocialMediaMonitor
            
            # Create and start the social media monitor with learning system
            social_monitor = SocialMediaMonitor()
            # Connect the learning system to the social ingest module
            social_monitor.social_ingest.learning_system = self.learning_system
            await social_monitor.start_monitoring()
            
        except Exception as e:
            print(f"❌ Failed to start social monitoring: {e}")
    
    async def start_position_management(self):
        """Start position management loop with minimal output"""
        try:
            print("📊 Starting position management...")
            
            # Start scheduled price collection (1-minute intervals)
            await self.price_collector.start_collection(interval_minutes=1)
            
            # Position management is handled by PM Core Tick (scheduled jobs)
            # No separate position monitor needed
            
        except Exception as e:
            print(f"❌ Position management failed: {e}")
    
    async def start_learning_system(self):
        """Start the learning system"""
        try:
            print("🧠 Learning system ready to process strands")
            
        except Exception as e:
            print(f"❌ Failed to start learning system: {e}")
    
    async def run(self):
        """Run the complete social trading system"""
        try:
            print("🚀 Starting Social Trading System...")
            print("=" * 50)
            
            # Initialize system
            if not await self.initialize():
                print("❌ Failed to initialize system")
                return False
            
            self.running = True
            
            # Start all components
            tasks = [
                asyncio.create_task(self.start_social_monitoring()),
                asyncio.create_task(self.start_position_management()),
                asyncio.create_task(self.start_learning_system()),
                asyncio.create_task(self.start_pm_jobs())
            ]
            
            self.tasks = tasks
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down gracefully...")
        except Exception as e:
            print(f"❌ System error: {e}")
        finally:
            await self.shutdown()

    async def start_pm_jobs(self):
        """Start hourly PM jobs (NAV, Dominance, Features/Phase) aligned to UTC.
        Offsets: :02 NAV, :03 Dominance, :04 Features.
        """
        async def schedule_5min(offset_min: int, func):
            # wait until next 5-minute mark at :offset_min
            while True:
                now = datetime.now(timezone.utc)
                next_run = now.replace(minute=(now.minute // 5) * 5 + offset_min, second=0, microsecond=0)
                if next_run <= now:
                    from datetime import timedelta
                    next_run = next_run + timedelta(minutes=5)
                await asyncio.sleep((next_run - now).total_seconds())
                try:
                    # run sync job in thread
                    await asyncio.to_thread(func)
                except Exception as e:
                    print(f"PM job error: {e}")

        async def schedule_hourly(offset_min: int, func):
            # wait until next hour at :offset_min
            while True:
                now = datetime.now(timezone.utc)
                next_run = now.replace(minute=offset_min, second=0, microsecond=0)
                if next_run <= now:
                    from datetime import timedelta
                    next_run = next_run + timedelta(hours=1)
                await asyncio.sleep((next_run - now).total_seconds())
                try:
                    # run sync job in thread
                    await asyncio.to_thread(func)
                except Exception as e:
                    print(f"PM job error: {e}")

        async def schedule_1min(func):
            """Schedule job to run every 1 minute"""
            while True:
                await asyncio.sleep(60)  # Wait 1 minute
                try:
                    await asyncio.to_thread(func)
                except Exception as e:
                    print(f"1m job error: {e}")

        async def schedule_15min(offset_min: int, func):
            """Schedule job to run every 15 minutes at :offset_min"""
            while True:
                now = datetime.now(timezone.utc)
                # Calculate next 15-minute boundary
                minute_boundary = (now.minute // 15) * 15
                next_run = now.replace(minute=minute_boundary + offset_min, second=0, microsecond=0)
                if next_run <= now:
                    from datetime import timedelta
                    next_run = next_run + timedelta(minutes=15)
                await asyncio.sleep((next_run - now).total_seconds())
                try:
                    await asyncio.to_thread(func)
                except Exception as e:
                    print(f"15m job error: {e}")

        async def schedule_4h(offset_hour: int, func):
            """Schedule job to run every 4 hours at :offset_hour"""
            while True:
                now = datetime.now(timezone.utc)
                # Calculate next 4-hour boundary
                hour_boundary = (now.hour // 4) * 4
                next_run = now.replace(hour=hour_boundary + offset_hour, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    from datetime import timedelta
                    next_run = next_run + timedelta(hours=4)
                await asyncio.sleep((next_run - now).total_seconds())
                try:
                    await asyncio.to_thread(func)
                except Exception as e:
                    print(f"4h job error: {e}")

        # Import job entrypoints lazily
        from intelligence.lowcap_portfolio_manager.jobs.nav_compute_1h import main as nav_main
        # Legacy: dominance_ingest_1h and bands_calc removed - regime engine handles A/E via RegimeAECalculator
        from intelligence.lowcap_portfolio_manager.jobs.tracker import main as feat_main
        from intelligence.lowcap_portfolio_manager.jobs.geometry_build_daily import main as geom_daily_main
        from intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import main as pm_core_main
        from intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import main as uptrend_engine_main
        from intelligence.lowcap_portfolio_manager.jobs.update_bars_count import main as update_bars_count_main
        from intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import run_aggregator
        from intelligence.lowcap_portfolio_manager.jobs.lesson_builder_v5 import build_lessons_from_pattern_scope_stats
        from intelligence.lowcap_portfolio_manager.jobs.override_materializer import run_override_materializer
        from intelligence.lowcap_portfolio_manager.ingest.rollup_ohlc import GenericOHLCRollup, DataSource, Timeframe
        from intelligence.lowcap_portfolio_manager.ingest.rollup import OneMinuteRollup
        def majors_1m_rollup_job():
            """Convert Hyperliquid ticks to 1m OHLC bars (every 1 minute)"""
            try:
                rollup = OneMinuteRollup()
                majors_written = rollup.roll_minute()
                print(f"Majors 1m rollup: {majors_written} bars")
            except Exception as e:
                print(f"Majors 1m rollup error: {e}")


        # OHLC conversion and rollup jobs (v4 - multi-timeframe support)
        def convert_1m_ohlc_job():
            """Convert 1m price points to 1m OHLC bars (every 1 minute)"""
            try:
                rollup = GenericOHLCRollup()
                # Convert 1m price points to 1m OHLC bars for lowcaps
                lowcaps_written = rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.M1)
                print(f"1m OHLC conversion: {lowcaps_written} lowcap bars")
            except Exception as e:
                print(f"1m OHLC conversion error: {e}")

        def rollup_5m_job():
            """Roll up 1m OHLC to 5m OHLC (every 5 minutes)"""
            try:
                rollup = GenericOHLCRollup()
                majors_written = rollup.rollup_timeframe(DataSource.MAJORS, Timeframe.M5)
                lowcaps_written = rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.M5)
                print(f"5m rollup: {majors_written} majors + {lowcaps_written} lowcaps = {majors_written + lowcaps_written} total bars")
            except Exception as e:
                print(f"5m rollup error: {e}")

        def rollup_15m_job():
            """Roll up 1m OHLC to 15m OHLC (every 15 minutes)"""
            try:
                rollup = GenericOHLCRollup()
                majors_written = rollup.rollup_timeframe(DataSource.MAJORS, Timeframe.M15)
                lowcaps_written = rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.M15)
                print(f"15m rollup: {majors_written} majors + {lowcaps_written} lowcaps = {majors_written + lowcaps_written} total bars")
            except Exception as e:
                print(f"15m rollup error: {e}")

        def rollup_1h_job():
            """Roll up 1m OHLC to 1h OHLC (every 1 hour)"""
            try:
                rollup = GenericOHLCRollup()
                majors_written = rollup.rollup_timeframe(DataSource.MAJORS, Timeframe.H1)
                lowcaps_written = rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.H1)
                print(f"1h rollup: {majors_written} majors + {lowcaps_written} lowcaps = {majors_written + lowcaps_written} total bars")
            except Exception as e:
                print(f"1h rollup error: {e}")

        def rollup_4h_job():
            """Roll up 1m OHLC to 4h OHLC (every 4 hours)"""
            try:
                rollup = GenericOHLCRollup()
                majors_written = rollup.rollup_timeframe(DataSource.MAJORS, Timeframe.H4)
                lowcaps_written = rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.H4)
                print(f"4h rollup: {majors_written} majors + {lowcaps_written} lowcaps = {majors_written + lowcaps_written} total bars")
            except Exception as e:
                print(f"4h rollup error: {e}")

        # Uptrend Engine v4 jobs (v4 - multi-timeframe support)
        def uptrend_engine_1m_job():
            """Run Uptrend Engine v4 for 1m timeframe (every 1 minute)"""
            try:
                uptrend_engine_main(timeframe="1m")
            except Exception as e:
                print(f"Uptrend Engine v4 (1m) error: {e}")

        def uptrend_engine_15m_job():
            """Run Uptrend Engine v4 for 15m timeframe (every 15 minutes)"""
            try:
                uptrend_engine_main(timeframe="15m")
            except Exception as e:
                print(f"Uptrend Engine v4 (15m) error: {e}")

        def uptrend_engine_1h_job():
            """Run Uptrend Engine v4 for 1h timeframe (every 1 hour)"""
            try:
                uptrend_engine_main(timeframe="1h")
            except Exception as e:
                print(f"Uptrend Engine v4 (1h) error: {e}")

        def uptrend_engine_4h_job():
            """Run Uptrend Engine v4 for 4h timeframe (every 4 hours)"""
            try:
                uptrend_engine_main(timeframe="4h")
            except Exception as e:
                print(f"Uptrend Engine v4 (4h) error: {e}")

        def _create_service_client():
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not supabase_url or not supabase_key:
                raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY for learning jobs")
            return create_client(supabase_url, supabase_key)

        def pattern_scope_aggregator_job():
            async def _run():
                sb_client = _create_service_client()
                await run_aggregator(sb_client=sb_client)
            try:
                asyncio.run(_run())
            except Exception as e:
                print(f"Pattern scope aggregator error: {e}")

        def lesson_builder_job(module: str):
            async def _run():
                sb_client = _create_service_client()
                await build_lessons_from_pattern_scope_stats(sb_client, module=module)
            try:
                asyncio.run(_run())
            except Exception as e:
                print(f"Lesson builder ({module}) error: {e}")

        def override_materializer_job():
            try:
                sb_client = _create_service_client()
                run_override_materializer(sb_client=sb_client)
            except Exception as e:
                print(f"Override materializer error: {e}")

        # Fire background schedulers
        asyncio.create_task(schedule_hourly(2, nav_main))
        asyncio.create_task(schedule_5min(0, feat_main))  # Tracker every 5 minutes
        
        # v4: Multi-timeframe TA Tracker
        from intelligence.lowcap_portfolio_manager.jobs.ta_tracker import main as ta_tracker_main
        
        def ta_tracker_1m_job():
            """Run TA Tracker for 1m timeframe (every 1 minute)"""
            try:
                ta_tracker_main(timeframe="1m")
            except Exception as e:
                print(f"TA Tracker (1m) error: {e}")
        
        def ta_tracker_15m_job():
            """Run TA Tracker for 15m timeframe (every 15 minutes)"""
            try:
                ta_tracker_main(timeframe="15m")
            except Exception as e:
                print(f"TA Tracker (15m) error: {e}")
        
        def ta_tracker_1h_job():
            """Run TA Tracker for 1h timeframe (every 1 hour)"""
            try:
                ta_tracker_main(timeframe="1h")
            except Exception as e:
                print(f"TA Tracker (1h) error: {e}")
        
        def ta_tracker_4h_job():
            """Run TA Tracker for 4h timeframe (every 4 hours)"""
            try:
                ta_tracker_main(timeframe="4h")
            except Exception as e:
                print(f"TA Tracker (4h) error: {e}")
        
        # Schedule TA Tracker per timeframe
        asyncio.create_task(schedule_1min(ta_tracker_1m_job))  # 1m TA Tracker every 1 minute
        asyncio.create_task(schedule_15min(0, ta_tracker_15m_job))  # 15m TA Tracker every 15 minutes
        asyncio.create_task(schedule_hourly(6, ta_tracker_1h_job))  # 1h TA Tracker every 1 hour
        asyncio.create_task(schedule_4h(0, ta_tracker_4h_job))  # 4h TA Tracker every 4 hours
        
        # v4: Multi-timeframe OHLC conversion and rollup
        asyncio.create_task(schedule_1min(convert_1m_ohlc_job))  # 1m OHLC conversion every 1 minute
        asyncio.create_task(schedule_1min(majors_1m_rollup_job))  # Majors tick → 1m conversion every 1 minute
        asyncio.create_task(schedule_5min(0, rollup_5m_job))  # 5m rollup every 5 minutes
        asyncio.create_task(schedule_15min(0, rollup_15m_job))  # 15m rollup every 15 minutes
        asyncio.create_task(schedule_hourly(4, rollup_1h_job))  # 1h rollup every 1 hour
        asyncio.create_task(schedule_4h(0, rollup_4h_job))  # 4h rollup every 4 hours
        
        # v4: Multi-timeframe Uptrend Engine v4 (runs for dormant/watchlist/active positions)
        asyncio.create_task(schedule_1min(uptrend_engine_1m_job))  # 1m Uptrend Engine every 1 minute
        asyncio.create_task(schedule_15min(0, uptrend_engine_15m_job))  # 15m Uptrend Engine every 15 minutes
        asyncio.create_task(schedule_hourly(1, uptrend_engine_1h_job))  # 1h Uptrend Engine every 1 hour
        asyncio.create_task(schedule_4h(0, uptrend_engine_4h_job))  # 4h Uptrend Engine every 4 hours
        
        # v4: Multi-timeframe Geometry Builder (runs every 1 hour for all timeframes)
        def geometry_build_1m_job():
            """Run Geometry Builder for 1m timeframe (every 1 hour)"""
            try:
                geom_daily_main(timeframe="1m")
            except Exception as e:
                print(f"Geometry Builder (1m) error: {e}")
        
        def geometry_build_15m_job():
            """Run Geometry Builder for 15m timeframe (every 1 hour)"""
            try:
                geom_daily_main(timeframe="15m")
            except Exception as e:
                print(f"Geometry Builder (15m) error: {e}")
        
        def geometry_build_1h_job():
            """Run Geometry Builder for 1h timeframe (every 1 hour)"""
            try:
                geom_daily_main(timeframe="1h")
            except Exception as e:
                print(f"Geometry Builder (1h) error: {e}")
        
        def geometry_build_4h_job():
            """Run Geometry Builder for 4h timeframe (every 1 hour)"""
            try:
                geom_daily_main(timeframe="4h")
            except Exception as e:
                print(f"Geometry Builder (4h) error: {e}")
        
        # Schedule Geometry Builder per timeframe (every 1 hour for all timeframes)
        asyncio.create_task(schedule_hourly(7, geometry_build_1m_job))  # 1m Geometry Builder every 1 hour
        asyncio.create_task(schedule_hourly(7, geometry_build_15m_job))  # 15m Geometry Builder every 1 hour
        asyncio.create_task(schedule_hourly(7, geometry_build_1h_job))  # 1h Geometry Builder every 1 hour
        asyncio.create_task(schedule_hourly(7, geometry_build_4h_job))  # 4h Geometry Builder every 1 hour
        
        # PM Core Tick jobs (v4 - multi-timeframe support)
        # Pass learning_system to enable position_closed strand processing
        def pm_core_1m_job():
            """Run PM Core Tick for 1m timeframe (every 1 minute)"""
            try:
                pm_core_main(timeframe="1m", learning_system=self.learning_system)
            except Exception as e:
                print(f"PM Core Tick (1m) error: {e}")

        def pm_core_15m_job():
            """Run PM Core Tick for 15m timeframe (every 15 minutes)"""
            try:
                pm_core_main(timeframe="15m", learning_system=self.learning_system)
            except Exception as e:
                print(f"PM Core Tick (15m) error: {e}")

        def pm_core_1h_job():
            """Run PM Core Tick for 1h timeframe (every 1 hour)"""
            try:
                pm_core_main(timeframe="1h", learning_system=self.learning_system)
            except Exception as e:
                print(f"PM Core Tick (1h) error: {e}")

        def pm_core_4h_job():
            """Run PM Core Tick for 4h timeframe (every 4 hours)"""
            try:
                pm_core_main(timeframe="4h", learning_system=self.learning_system)
            except Exception as e:
                print(f"PM Core Tick (4h) error: {e}")

        # Schedule PM Core Tick per timeframe (runs at same rate as timeframe being checked)
        asyncio.create_task(schedule_1min(pm_core_1m_job))  # 1m PM every 1 minute
        asyncio.create_task(schedule_15min(0, pm_core_15m_job))  # 15m PM every 15 minutes
        asyncio.create_task(schedule_hourly(6, pm_core_1h_job))  # 1h PM every 1 hour
        asyncio.create_task(schedule_4h(0, pm_core_4h_job))  # 4h PM every 4 hours
        asyncio.create_task(schedule_hourly(7, update_bars_count_main))  # Update bars_count and check dormant→watchlist transitions
        asyncio.create_task(schedule_5min(2, pattern_scope_aggregator_job))  # Learning aggregator every 5 minutes
        asyncio.create_task(schedule_hourly(8, lambda: lesson_builder_job('pm')))  # PM lessons hourly
        asyncio.create_task(schedule_hourly(9, lambda: lesson_builder_job('dm')))  # DM lessons hourly
        asyncio.create_task(schedule_hourly(10, override_materializer_job))  # Override materializer hourly
        # GeckoTerminal 15m backfill is triggered only on new-position onboarding (14 days); no hourly scan.
        # Daily geometry at :10 once per day
        async def schedule_daily(offset_min: int, func):
            from datetime import timedelta
            while True:
                now = datetime.now(timezone.utc)
                # next top-of-day UTC at offset_min
                next_run = now.replace(hour=0, minute=offset_min, second=0, microsecond=0)
                if next_run <= now:
                    next_run = next_run + timedelta(days=1)
                await asyncio.sleep((next_run - now).total_seconds())
                try:
                    await asyncio.to_thread(func)
                except Exception as e:
                    print(f"PM daily job error: {e}")
        # Geometry Builder is now scheduled hourly per timeframe (see below)

        # One-shot seed after startup: dominance → features/phase → bands → pm_core
        async def seed_pm_once():
            try:
                await asyncio.to_thread(feat_main)
            except Exception as e:
                print(f"PM seed (features/phase) error: {e}")
            try:
                await asyncio.to_thread(pm_core_main)
            except Exception as e:
                print(f"PM seed (core) error: {e}")

        asyncio.create_task(seed_pm_once())

        # Start Hyperliquid WS ingester for majors if enabled
        async def start_hl_ws_if_enabled():
            try:
                if os.getenv("HL_INGEST_ENABLED", "0") == "1":
                    from intelligence.lowcap_portfolio_manager.ingest.hyperliquid_ws import HyperliquidWSIngester
                    ing = HyperliquidWSIngester()
                    asyncio.create_task(ing.run())
            except Exception as e:
                print(f"HL WS ingester not started: {e}")

        asyncio.create_task(start_hl_ws_if_enabled())
    
    async def shutdown(self):
        """Shutdown the system gracefully"""
        try:
            print("Shutting down Social Trading System...")
            
            self.running = False
            
            # Cancel all tasks
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
            print("✅ Shutdown complete")
            
        except Exception as e:
            print(f"Error during shutdown: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {signum}, shutting down...")
    sys.exit(0)


async def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run the system
    system = SocialTradingSystem()
    await system.run()


if __name__ == "__main__":
    print("""
    🚀 Social Trading System
    ========================
    
    This system monitors social media for crypto signals,
    makes trading decisions, and executes trades automatically.
    
    Components:
    - Social Monitoring (Twitter/Telegram)
    - Discord Monitoring (Conservative Channel)
    - Decision Making (AI-powered)
    - Trading Execution (Multi-entry/exit)
    - Position Management (Real-time)
    - Learning System (Continuous improvement)
    
    Press Ctrl+C to stop the system.
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)