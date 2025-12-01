# --- Environment Setup (MUST BE FIRST) ---
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
import os
import signal
import sys
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# --- Third-party Imports ---
from supabase import create_client
from supabase.lib.client_options import ClientOptions

# --- Project Imports ---
from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient
from trading.jupiter_client import JupiterClient
from trading.wallet_manager import WalletManager
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from intelligence.social_ingest.social_ingest_basic import SocialIngestModule
from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
from trading.scheduled_price_collector import ScheduledPriceCollector
from trading.position_monitor import PositionMonitor

# --- Job Imports ---
from intelligence.lowcap_portfolio_manager.jobs.nav_compute_1h import main as nav_main
from intelligence.lowcap_portfolio_manager.jobs.dominance_ingest_1h import main as dom_main
from intelligence.lowcap_portfolio_manager.jobs.tracker import main as feat_main
from intelligence.lowcap_portfolio_manager.jobs.bands_calc import main as bands_main
from intelligence.lowcap_portfolio_manager.jobs.geometry_build_daily import main as geom_daily_main
from intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import main as pm_core_main
from intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import main as uptrend_engine_main
from intelligence.lowcap_portfolio_manager.jobs.update_bars_count import main as update_bars_count_main
from intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import run_aggregator as pattern_scope_aggregator_job
from intelligence.lowcap_portfolio_manager.jobs.lesson_builder_v5 import build_lessons_from_pattern_scope_stats
from intelligence.lowcap_portfolio_manager.jobs.override_materializer import run_override_materializer
from intelligence.lowcap_portfolio_manager.ingest.rollup_ohlc import GenericOHLCRollup, DataSource, Timeframe
from intelligence.lowcap_portfolio_manager.ingest.rollup import OneMinuteRollup

# --- Logging Configuration ---
def setup_logging():
    os.makedirs('logs', exist_ok=True)
    
    loggers = {
        'social_ingest': 'logs/social_ingest.log',
        'decision_maker': 'logs/decision_maker.log',
        'pm_core': 'logs/pm_core.log',
        'trader': 'logs/trader.log',
        'learning_system': 'logs/learning_system.log',
        'price_collector': 'logs/price_collector.log',
        'position_monitor': 'logs/position_monitor.log',
        'schedulers': 'logs/schedulers.log',
        'system': 'logs/system.log'
    }

    # Configure root logger to suppress debug/info to console
    logging.basicConfig(level=logging.WARNING)

    for name, log_file in loggers.items():
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.propagate = False

setup_logging()
logger = logging.getLogger('system')

# --- Strand Monitor (Glyphic System) ---
class StrandMonitor:
    def __init__(self, supabase: SupabaseManager):
        self.sb = supabase
        
    def start(self):
        try:
            channel = self.sb.client.channel('ad_strands_monitor')
            channel.on(
                'postgres_changes',
                event='INSERT',
                schema='public',
                table='ad_strands',
                callback=self.handle_strand
            ).subscribe()
        except Exception as e:
            logger.error(f"Failed to subscribe to realtime strands: {e}", exc_info=True)
            print(f"❦ Realtime subscription failed: {e}")

    def _get_stage_glyph(self, stage: str) -> str:
        mapping = {
            'S0': '🜁', # Air (Watchlist)
            'S1': '🜂', # Fire (Ignition)
            'S2': '🜃', # Earth (Solid)
            'S3': '🜇', # Water/Aether (Flow)
        }
        return mapping.get(stage, stage)

    def handle_strand(self, payload):
        try:
            record = payload.get('new', {})
            kind = record.get('kind')
            symbol = record.get('symbol', 'UNK')
            content = record.get('content', {}) or {}
            module_intel = record.get('module_intelligence') or {}
            
            output = ""
            
            if kind == 'social_lowcap':
                curator = record.get('signal_pack', {}).get('curator_id', 'Unknown')
                chain = record.get('signal_pack', {}).get('token_chain', '')
                conf = module_intel.get('confidence_score', 0)
                output = f"⟡  SOCIAL   | {curator} → {symbol} ({chain}) | Conf: {conf}"
                
            elif kind == 'decision_lowcap':
                action = content.get('action', 'WAIT')
                alloc = content.get('allocation_percentage', 0)
                reason = (content.get('reasoning') or "")[:50]
                # Check for learning context
                learning_suffix = " | 𓂀" if module_intel else ""
                output = f"∆φ DECISION | {action} {symbol} | Alloc: {alloc}%{learning_suffix}"
                
            elif kind == 'pm_action':
                d_type = content.get('decision_type', 'HOLD')
                tf = record.get('timeframe', '')
                a_val = content.get('a_value', 0)
                e_val = content.get('e_value', 0)
                output = f"🜄  PM EXEC  | {d_type} {symbol} ({tf}) | A:{a_val:.2f} E:{e_val:.2f}"
                
            elif kind == 'position_closed':
                pnl = content.get('pnl_usd', 0)
                rr = content.get('rr', 0)
                output = f"𐄷  CLOSED   | {symbol} | PnL: ${pnl} (R:{rr})"
                
            elif kind == 'uptrend_stage_transition':
                from_s = content.get('from_state', '?')
                to_s = content.get('to_state', '?')
                from_g = self._get_stage_glyph(from_s)
                to_g = self._get_stage_glyph(to_s)
                tf = record.get('timeframe', '')
                output = f"𒀭  STAGE    | {symbol} {from_g} → {to_g} ({tf})"
                
            elif kind == 'uptrend_episode_summary':
                ep_type = content.get('episode_type', '?')
                outcome = content.get('outcome', '?')
                entered = content.get('entered', False)
                output = f"ᛟ  EPISODE  | {symbol} {ep_type} → {outcome} | Entered: {entered}"
            
            else:
                # Fallback
                output = f"⚪ STRAND   | {kind} | {symbol}"

            print(output)
            
        except Exception as e:
            logger.error(f"Error formatting strand: {e}")

# --- Trading System ---
class TradingSystem:
    def __init__(self):
        self.config = self._load_config()
        self.running = False
        self.tasks = []
        self.supabase_manager = None
        self.llm_client = None
        self.jupiter_client = None
        self.wallet_manager = None
        self.learning_system = None
        self.social_ingest = None
        self.decision_maker = None
        self.trader = None
        self.price_collector = None
        self.position_monitor = None
        self.strand_monitor = None
        self.social_monitor = None
        
    def _load_config(self) -> Dict[str, Any]:
        # Replicate config structure from run_social_trading.py
        return {
            'trading': {
                'book_nav': float(os.getenv('BOOK_NAV', '100000.0')),
                'max_exposure_pct': 20.0,
                'min_curator_score': 0.6,
                'default_allocation_pct': 4.0,
                'min_allocation_pct': 2.0,
                'max_allocation_pct': 6.0,
                'slippage_pct': 1.0
            },
            'position_management': {
                'price_check_interval': 30,
                'exit_check_interval': 30,
                'jupiter_price_enabled': True
            },
            'jupiter': {
                'api_url': 'https://lite-api.jup.ag/swap/v1',
                'price_url': 'https://lite-api.jup.ag/price/v3'
            },
            'lotus_buyback': {
                'enabled': True,
                'lotus_contract': "59dG2d251a2d947e977388871854527598425119",
                'buyback_pct': 0.10
            }
        }

    async def initialize(self):
        print("\n⚘⟁⌖ Lotus Trencher System Initializing...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        try:
            self.supabase_manager = SupabaseManager()
            print("   [⋻] Supabase Manager... OK")

            self.llm_client = OpenRouterClient()
            print("   [∴] LLM Client... OK")

            self.jupiter_client = JupiterClient()
            self.wallet_manager = WalletManager()
            print("   [🜄] Trading Core (Jupiter/Wallet)... OK")

            self.learning_system = UniversalLearningSystem(
                supabase_manager=self.supabase_manager,
                llm_client=self.llm_client,
                llm_config=None
            )
            print("   [𓂀] Universal Learning System... Active")

            self.social_ingest = SocialIngestModule(
                supabase_manager=self.supabase_manager,
                llm_client=self.llm_client,
                config_path="src/config/twitter_curators.yaml"
            )
            self.social_ingest.learning_system = self.learning_system
            
            # Get curator list for startup display
            curators = self.social_ingest.get_enabled_curators()
            twitter_curators = [c for c in curators if c.get('platform') == 'twitter']
            twitter_handles = [c.get('platform_data', {}).get('handle', c.get('name', 'unknown')) for c in twitter_curators]
            twitter_list = ', '.join([f"@{h}" for h in twitter_handles[:10]])  # Limit to 10 for display
            if len(twitter_curators) > 10:
                twitter_list += f" (+{len(twitter_curators) - 10} more)"
            
            telegram_active = any(c.get('platform') == 'telegram' for c in curators)
            
            print("   [⟡] Social Ingest... Listening")
            if twitter_curators:
                print(f"      Twitter: {len(twitter_curators)} curators ({twitter_list})")
            if telegram_active:
                print("      Telegram: active")

            self.decision_maker = DecisionMakerLowcapSimple(
                supabase_manager=self.supabase_manager,
                config=self.config,
                learning_system=self.learning_system
            )
            print("   [∆φ] Decision Maker... Ready")

            # Trader initialization
            from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
            trader_config = self.config.get('trading', {}).copy()
            if 'lotus_buyback' in self.config:
                trader_config['lotus_buyback'] = self.config['lotus_buyback']
            
            self.trader = TraderLowcapSimpleV2(
                supabase_manager=self.supabase_manager,
                config=trader_config
            )
            
            # Wire up dependencies
            self.learning_system.trader = self.trader
            self.learning_system.set_decision_maker(self.decision_maker)
            self.wallet_manager.trader = self.trader
            self.supabase_manager.wallet_manager = self.wallet_manager
            print("   [🜄] Trader (V2) & Dependencies... OK")

            self.price_collector = ScheduledPriceCollector(
                supabase_manager=self.supabase_manager,
                price_oracle=self.trader.price_oracle
            )
            print("   [⩜] Scheduled Price Collector... OK")

            self.position_monitor = PositionMonitor(
                supabase_manager=self.supabase_manager,
                trader=self.trader
            )
            print("   [⩜] Position Monitor... OK")

            if os.getenv("ACTIONS_ENABLED", "0") == "1":
                from intelligence.lowcap_portfolio_manager.pm.executor import register_pm_executor
                sb_client = self.supabase_manager.db_manager.client if hasattr(self.supabase_manager, 'db_manager') else self.supabase_manager.client
                register_pm_executor(self.trader, sb_client)  # Fixed: trader first, then sb_client
                print("   [⚡] PM Executor... Registered")
            else:
                print("   [⋇] PM Executor... Disabled (Read-Only)")
            
            # Initialize Strand Monitor
            self.strand_monitor = StrandMonitor(self.supabase_manager)
            self.strand_monitor.start()
            print("   [⟖] Strand Monitor... Started")

            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        except Exception as e:
            logger.critical(f"Initialization failed: {e}", exc_info=True)
            print(f"❦ FATAL: Initialization failed: {e}")
            sys.exit(1)

    # --- Scheduling Helpers ---
    async def _schedule_at_interval(self, interval_seconds: int, func, name: str):
        scheduler_logger = logging.getLogger('schedulers')
        while self.running:
            try:
                scheduler_logger.info(f"Starting {name}")
                await asyncio.to_thread(func)
                scheduler_logger.info(f"{name} completed")
            except Exception as e:
                scheduler_logger.error(f"{name} failed: {e}", exc_info=True)
            await asyncio.sleep(interval_seconds)

    async def _schedule_aligned(self, interval_min: int, offset_min: int, func, name: str):
        """Schedule to run at specific minute offsets (e.g. every hour at :05)"""
        scheduler_logger = logging.getLogger('schedulers')
        while self.running:
            now = datetime.now(timezone.utc)
            await asyncio.sleep(60 - now.second) 
            now = datetime.now(timezone.utc)
            if (now.minute % interval_min) == offset_min:
                try:
                    scheduler_logger.info(f"Starting {name}")
                    await asyncio.to_thread(func)
                    scheduler_logger.info(f"{name} completed")
                except Exception as e:
                    scheduler_logger.error(f"{name} failed: {e}", exc_info=True)

    async def _schedule_hourly(self, offset_min: int, func, name: str):
        scheduler_logger = logging.getLogger('schedulers')
        while self.running:
            now = datetime.now(timezone.utc)
            next_run = now.replace(minute=offset_min, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
            wait_s = (next_run - now).total_seconds()
            scheduler_logger.info(f"{name} scheduled for {next_run.isoformat()}")
            await asyncio.sleep(wait_s)
            try:
                scheduler_logger.info(f"Starting {name}")
                await asyncio.to_thread(func)
                scheduler_logger.info(f"{name} completed")
            except Exception as e:
                scheduler_logger.error(f"{name} failed: {e}", exc_info=True)
    
    async def _schedule_4h(self, offset_min: int, func, name: str):
        scheduler_logger = logging.getLogger('schedulers')
        while self.running:
            now = datetime.now(timezone.utc)
            next_run = now.replace(minute=offset_min, second=0, microsecond=0)
            while next_run <= now or next_run.hour % 4 != 0:
                next_run += timedelta(hours=1)
            wait_s = (next_run - now).total_seconds()
            scheduler_logger.info(f"{name} scheduled for {next_run.isoformat()}")
            await asyncio.sleep(wait_s)
            try:
                scheduler_logger.info(f"Starting {name}")
                await asyncio.to_thread(func)
                scheduler_logger.info(f"{name} completed")
            except Exception as e:
                scheduler_logger.error(f"{name} failed: {e}", exc_info=True)

    # --- Service Client Helper ---
    def _create_service_client(self):
        """Create Supabase service client for learning jobs"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY for learning jobs")
        return create_client(supabase_url, supabase_key)

    # --- Job Wrappers ---
    def _wrap_lesson_builder(self, module):
        try:
            sb_client = self._create_service_client()
            asyncio.run(build_lessons_from_pattern_scope_stats(sb_client, module=module))
        except Exception as e:
            logger.error(f"Lesson builder ({module}) error: {e}", exc_info=True)

    def _wrap_override_materializer(self):
        try:
            sb_client = self._create_service_client()
            run_override_materializer(sb_client=sb_client)
        except Exception as e:
            logger.error(f"Override materializer error: {e}", exc_info=True)
    
    def _wrap_pattern_aggregator(self):
        """Wrapper for pattern scope aggregator (requires service client)"""
        async def _run():
            sb_client = self._create_service_client()
            await pattern_scope_aggregator_job(sb_client=sb_client)
        try:
            asyncio.run(_run())
        except Exception as e:
            logger.error(f"Pattern aggregator error: {e}", exc_info=True)

    def _wrap_pm_core(self, timeframe):
        pm_logger = logging.getLogger('pm_core')
        try:
            pm_logger.info(f"PM Core Tick ({timeframe}) starting")
            pm_core_main(timeframe=timeframe, learning_system=self.learning_system)
            pm_logger.info(f"PM Core Tick ({timeframe}) completed")
        except Exception as e:
            pm_logger.error(f"PM Core ({timeframe}) error: {e}", exc_info=True)

    def _wrap_ta_tracker(self, timeframe):
        from intelligence.lowcap_portfolio_manager.jobs.ta_tracker import main as ta_tracker_main
        try:
            ta_tracker_main(timeframe=timeframe)
        except Exception as e:
            logger.error(f"TA Tracker ({timeframe}) error: {e}", exc_info=True)

    def _wrap_geometry(self, timeframe):
        try:
            geom_daily_main(timeframe=timeframe)
        except Exception as e:
            logger.error(f"Geometry ({timeframe}) error: {e}", exc_info=True)
            
    def _wrap_rollup(self, timeframe_enum, name):
        try:
            rollup = GenericOHLCRollup()
            rollup.rollup_timeframe(DataSource.MAJORS, timeframe_enum)
            rollup.rollup_timeframe(DataSource.LOWCAPS, timeframe_enum)
        except Exception as e:
            logger.error(f"{name} error: {e}", exc_info=True)

    def _wrap_uptrend(self, timeframe):
        try:
            uptrend_engine_main(timeframe=timeframe)
        except Exception as e:
            logger.error(f"Uptrend ({timeframe}) error: {e}", exc_info=True)

    async def start_schedulers(self):
        scheduler_logger = logging.getLogger('schedulers')
        print("⧖ Starting Schedulers...")
        scheduler_logger.info("Starting scheduler system")
        
        # 1. Seed Jobs (Individual error handling per job)
        print("   ⨳ Running Seed Jobs (Dominance -> Features -> Bands -> PM Core)...")
        scheduler_logger.info("Starting seed phase")
        
        try:
            scheduler_logger.info("Seed job: dom_main starting")
            await asyncio.to_thread(dom_main)
            scheduler_logger.info("Seed job: dom_main completed")
        except Exception as e:
            scheduler_logger.error(f"PM seed (dominance) error: {e}", exc_info=True)
            print(f"   ❦ Seed (Dominance) Failed: {e}")
        
        try:
            scheduler_logger.info("Seed job: feat_main starting")
            await asyncio.to_thread(feat_main)
            scheduler_logger.info("Seed job: feat_main completed")
        except Exception as e:
            scheduler_logger.error(f"PM seed (features/phase) error: {e}", exc_info=True)
            print(f"   ❦ Seed (Features) Failed: {e}")
        
        try:
            scheduler_logger.info("Seed job: bands_main starting")
            await asyncio.to_thread(bands_main)
            scheduler_logger.info("Seed job: bands_main completed")
        except Exception as e:
            scheduler_logger.error(f"PM seed (bands) error: {e}", exc_info=True)
            print(f"   ❦ Seed (Bands) Failed: {e}")
        
        try:
            scheduler_logger.info("Seed job: pm_core_main starting")
            await asyncio.to_thread(lambda: pm_core_main(timeframe="1h", learning_system=self.learning_system))
            scheduler_logger.info("Seed job: pm_core_main completed")
        except Exception as e:
            scheduler_logger.error(f"PM seed (core) error: {e}", exc_info=True)
            print(f"   ❦ Seed (PM Core) Failed: {e}")
        
        print("   ⨵ Seed Jobs Complete")
        scheduler_logger.info("Seed phase completed")

        # 2. Recurring Schedule
        tasks = []
        
        # 1 Minute Jobs
        tasks.append(asyncio.create_task(self._schedule_at_interval(60, lambda: self._wrap_ta_tracker("1m"), "TA 1m")))
        tasks.append(asyncio.create_task(self._schedule_at_interval(60, lambda: GenericOHLCRollup().rollup_timeframe(DataSource.LOWCAPS, Timeframe.M1), "OHLC 1m")))
        def majors_1m_rollup_job():
            try:
                rollup = OneMinuteRollup()
                rollup.roll_minute()
            except Exception as e:
                logger.error(f"Majors 1m rollup error: {e}", exc_info=True)
        tasks.append(asyncio.create_task(self._schedule_at_interval(60, majors_1m_rollup_job, "Majors Rollup")))
        tasks.append(asyncio.create_task(self._schedule_at_interval(60, lambda: self._wrap_uptrend("1m"), "Uptrend 1m")))
        tasks.append(asyncio.create_task(self._schedule_at_interval(60, lambda: self._wrap_pm_core("1m"), "PM 1m")))

        # 5 Minute Jobs (Aligned)
        tasks.append(asyncio.create_task(self._schedule_aligned(5, 0, feat_main, "Tracker")))
        tasks.append(asyncio.create_task(self._schedule_aligned(5, 0, lambda: self._wrap_rollup(Timeframe.M5, "Rollup 5m"), "Rollup 5m")))
        tasks.append(asyncio.create_task(self._schedule_aligned(5, 2, self._wrap_pattern_aggregator, "Pattern Aggregator")))

        # 15 Minute Jobs (Aligned)
        tasks.append(asyncio.create_task(self._schedule_aligned(15, 0, lambda: self._wrap_ta_tracker("15m"), "TA 15m")))
        tasks.append(asyncio.create_task(self._schedule_aligned(15, 0, lambda: self._wrap_rollup(Timeframe.M15, "Rollup 15m"), "Rollup 15m")))
        tasks.append(asyncio.create_task(self._schedule_aligned(15, 0, lambda: self._wrap_uptrend("15m"), "Uptrend 15m")))
        tasks.append(asyncio.create_task(self._schedule_aligned(15, 0, lambda: self._wrap_pm_core("15m"), "PM 15m")))

        # Hourly Jobs
        tasks.append(asyncio.create_task(self._schedule_hourly(1, lambda: self._wrap_uptrend("1h"), "Uptrend 1h")))
        tasks.append(asyncio.create_task(self._schedule_hourly(2, nav_main, "NAV")))
        tasks.append(asyncio.create_task(self._schedule_hourly(3, dom_main, "Dominance")))
        tasks.append(asyncio.create_task(self._schedule_hourly(4, lambda: self._wrap_rollup(Timeframe.H1, "Rollup 1h"), "Rollup 1h")))
        tasks.append(asyncio.create_task(self._schedule_hourly(5, bands_main, "Bands")))
        tasks.append(asyncio.create_task(self._schedule_hourly(6, lambda: self._wrap_ta_tracker("1h"), "TA 1h")))
        tasks.append(asyncio.create_task(self._schedule_hourly(6, lambda: self._wrap_pm_core("1h"), "PM 1h")))
        
        # Geometry at :07
        tasks.append(asyncio.create_task(self._schedule_hourly(7, lambda: self._wrap_geometry("1m"), "Geom 1m")))
        tasks.append(asyncio.create_task(self._schedule_hourly(7, lambda: self._wrap_geometry("15m"), "Geom 15m")))
        tasks.append(asyncio.create_task(self._schedule_hourly(7, lambda: self._wrap_geometry("1h"), "Geom 1h")))
        tasks.append(asyncio.create_task(self._schedule_hourly(7, lambda: self._wrap_geometry("4h"), "Geom 4h")))
        tasks.append(asyncio.create_task(self._schedule_hourly(7, update_bars_count_main, "Bars Count")))
        
        tasks.append(asyncio.create_task(self._schedule_hourly(8, lambda: self._wrap_lesson_builder('pm'), "Lesson PM")))
        tasks.append(asyncio.create_task(self._schedule_hourly(9, lambda: self._wrap_lesson_builder('dm'), "Lesson DM")))
        tasks.append(asyncio.create_task(self._schedule_hourly(10, self._wrap_override_materializer, "Override Mat")))

        # 4 Hour Jobs
        tasks.append(asyncio.create_task(self._schedule_4h(0, lambda: self._wrap_ta_tracker("4h"), "TA 4h")))
        tasks.append(asyncio.create_task(self._schedule_4h(0, lambda: self._wrap_rollup(Timeframe.H4, "Rollup 4h"), "Rollup 4h")))
        tasks.append(asyncio.create_task(self._schedule_4h(0, lambda: self._wrap_uptrend("4h"), "Uptrend 4h")))
        tasks.append(asyncio.create_task(self._schedule_4h(0, lambda: self._wrap_pm_core("4h"), "PM 4h")))

        # Start Hyperliquid WS ingester if enabled
        if os.getenv("HL_INGEST_ENABLED", "0") == "1":
            try:
                from intelligence.lowcap_portfolio_manager.ingest.hyperliquid_ws import HyperliquidWSIngester
                ing = HyperliquidWSIngester()
                hl_task = asyncio.create_task(ing.run())
                tasks.append(hl_task)
                scheduler_logger.info("Hyperliquid WS ingester started")
            except Exception as e:
                scheduler_logger.error(f"HL WS ingester not started: {e}", exc_info=True)
        
        print("   [↻] Schedulers... Active")
        scheduler_logger.info("All schedulers started")
        return tasks

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down system")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Shutdown complete")

    async def run(self):
        try:
            await self.initialize()
            self.running = True
            
            # Start schedulers
            tasks = await self.start_schedulers()
            self.tasks.extend(tasks)
            
            # Start Social Media Monitoring (with quiet mode)
            from intelligence.social_ingest.run_social_monitor import SocialMediaMonitor
            self.social_monitor = SocialMediaMonitor(quiet=True)
            self.social_monitor.social_ingest.learning_system = self.learning_system
            social_task = asyncio.create_task(self.social_monitor.start_monitoring())
            self.tasks.append(social_task)
            logger.info("Social media monitoring started (quiet mode)")
            
            # Start Price Collector
            price_task = asyncio.create_task(self.price_collector.start_collection(interval_minutes=1))
            self.tasks.append(price_task)
            logger.info("Price collector started")
            
            # Start Position Monitor
            position_task = asyncio.create_task(self.position_monitor.start_monitoring(check_interval=30))
            self.tasks.append(position_task)
            logger.info("Position monitor started")
            
            # Keep alive
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            print("\n∅ System shutting down...")
            logger.info("System cancelled")
        except Exception as e:
            logger.critical(f"System crash: {e}", exc_info=True)
            print(f"❦ FATAL: System crash: {e}")
            raise
        finally:
            await self.shutdown()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n∅ Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    system = TradingSystem()
    try:
        asyncio.run(system.run())
    except KeyboardInterrupt:
        print("\n∅ Exiting Lotus Trader")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"❦ FATAL: {e}")
        sys.exit(1)
