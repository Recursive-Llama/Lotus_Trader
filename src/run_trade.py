# --- Environment Setup (MUST BE FIRST) ---
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
import os
import signal
import sys
import json
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
from trading.scheduled_price_collector import ScheduledPriceCollector

# --- Job Imports ---
from intelligence.lowcap_portfolio_manager.jobs.nav_compute_1h import main as nav_main
# Legacy: dominance_ingest_1h and bands_calc removed - regime engine handles A/E via RegimeAECalculator
from intelligence.lowcap_portfolio_manager.jobs.tracker import main as feat_main
from intelligence.lowcap_portfolio_manager.jobs.geometry_build_daily import main as geom_daily_main
from intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import main as pm_core_main
from intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import main as uptrend_engine_main
from intelligence.lowcap_portfolio_manager.jobs.update_bars_count import main as update_bars_count_main
from intelligence.lowcap_portfolio_manager.jobs.bootstrap_system import BootstrapSystem
from intelligence.lowcap_portfolio_manager.jobs.regime_runner import run_regime_pipeline
from intelligence.lowcap_portfolio_manager.ingest.cap_bucket_tagging import main as cap_bucket_tagging_main
from intelligence.lowcap_portfolio_manager.jobs.tracker import main as bucket_tracker_main
from intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import run_aggregator as pattern_scope_aggregator_job
from intelligence.lowcap_portfolio_manager.jobs.lesson_builder_v5 import build_lessons_from_pattern_scope_stats
from intelligence.lowcap_portfolio_manager.jobs.override_materializer import run_override_materializer
from intelligence.lowcap_portfolio_manager.ingest.rollup_ohlc import GenericOHLCRollup, DataSource, Timeframe
from intelligence.lowcap_portfolio_manager.ingest.rollup import OneMinuteRollup
from intelligence.system_observer.jobs.balance_snapshot import BalanceSnapshotJob

# --- Logging Configuration ---
def setup_logging():
    os.makedirs('logs', exist_ok=True)
    
    loggers = {
        'social_ingest': 'logs/social_ingest.log',
        'decision_maker': 'logs/decision_maker.log',
        'pm_core': 'logs/pm_core.log',
        'src.intelligence.lowcap_portfolio_manager.pm.executor': 'logs/pm_executor.log',
        'src.intelligence.lowcap_portfolio_manager.pm.episode_blocking': 'logs/pm_core.log',  # Episode blocking logs go to pm_core.log
        'trader': 'logs/trader.log',
        'learning_system': 'logs/learning_system.log',
        'price_collector': 'logs/price_collector.log',
        'schedulers': 'logs/schedulers.log',
        'system': 'logs/system.log',
        'uptrend_engine': 'logs/uptrend_engine.log',
        'rollup': 'logs/rollup.log',
        'src.intelligence.lowcap_portfolio_manager.jobs.regime_price_collector': 'logs/regime_price_collector.log',
        'src.communication.telegram_signal_notifier': 'logs/telegram_notifier.log',
    }

    # Configure root logger to suppress debug/info to console
    logging.basicConfig(level=logging.WARNING)

    # Rotate logs if they exceed 10MB
    from logging.handlers import RotatingFileHandler
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 3  # Keep 3 backup files

    for name, log_file in loggers.items():
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT
        )
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.propagate = False

setup_logging()
logger = logging.getLogger('system')

# Glyph stream for progress indicators (matching bootstrap_system.py)
GLYPH_STREAM = [
    "⚘", "⟁", "⌖", "❈",  # Core system
    "⋇", "⟡", "↻", "∴", "⧖", "∅", "∞",  # Operations
    "⧉", "⨳", "⨴", "⨵", "⩜", "⋻", "⟖",  # Processes
    "𓂀", "𐄷", "𒀭", "𒉿", "ᛝ", "ᛟ",  # Events
    "🜁", "🜂", "🜃", "🜄", "🜇", "🜔",  # States
    "∆φ", "ℏ", "ψ(ω)", "∫", "φ", "θ", "ρ",  # Math/Physics
]


def show_glyph_loading(message: str, operation: Callable, *args, **kwargs):
    """
    Run an operation while showing animated glyph loading indicator.
    
    Args:
        message: Message to display (e.g., "Bootstrap System...")
        operation: Function to run
        *args, **kwargs: Arguments to pass to operation
    
    Returns:
        Result of operation
    """
    stop_progress = threading.Event()
    glyph_idx = [0]  # Use list to allow modification in nested function
    
    def progress_loop():
        while not stop_progress.is_set():
            glyph = GLYPH_STREAM[glyph_idx[0] % len(GLYPH_STREAM)]
            sys.stdout.write(f"\r   {message} {glyph}")
            sys.stdout.flush()
            glyph_idx[0] += 1
            if stop_progress.wait(0.2):  # Update every 200ms
                break
    
    # Start progress indicator in background thread
    progress_thread = threading.Thread(target=progress_loop, daemon=True)
    progress_thread.start()
    
    try:
        # Run the operation
        result = operation(*args, **kwargs)
        return result
    finally:
        # Stop progress indicator
        stop_progress.set()
        progress_thread.join(timeout=0.5)
        # Clear the progress line
        sys.stdout.write(f"\r   {message}")
        sys.stdout.flush()


async def show_glyph_loading_async(message: str, coro):
    """
    Run an async operation while showing animated glyph loading indicator.
    
    Args:
        message: Message to display (e.g., "Starting Hyperliquid WS...")
        coro: Coroutine to run
    
    Returns:
        Result of coroutine
    """
    stop_progress = threading.Event()
    glyph_idx = [0]
    
    def progress_loop():
        while not stop_progress.is_set():
            glyph = GLYPH_STREAM[glyph_idx[0] % len(GLYPH_STREAM)]
            sys.stdout.write(f"\r   {message} {glyph}")
            sys.stdout.flush()
            glyph_idx[0] += 1
            if stop_progress.wait(0.2):
                break
    
    # Start progress indicator in background thread
    progress_thread = threading.Thread(target=progress_loop, daemon=True)
    progress_thread.start()
    
    try:
        # Run the async operation
        result = await coro
        return result
    finally:
        # Stop progress indicator
        stop_progress.set()
        progress_thread.join(timeout=0.5)
        # Clear the progress line
        sys.stdout.write(f"\r   {message}")
        sys.stdout.flush()

# --- Strand Monitor (Glyphic System) ---
class StrandMonitor:
    def __init__(self, supabase: SupabaseManager):
        self.sb = supabase
        self.running = False
        
    async def start(self):
        """Start polling mode for strand monitoring"""
        # Use polling mode (realtime requires async client which adds complexity)
        # Polling is sufficient since actual processing happens via direct method calls
        await self._polling_fallback()

    async def _polling_fallback(self):
        """Polling mode for strand monitoring"""
        logger.info("Strand monitor using polling mode (5s interval)")
        self.running = True
        last_created_at = None
        while self.running:
            try:
                # Get latest strands - use created_at timestamp for reliable tracking
                query = self.sb.client.table('ad_strands').select('*').order('created_at', desc=False).limit(50)
                if last_created_at:
                    query = query.gt('created_at', last_created_at)
                result = query.execute()
                
                if result.data:
                    # Process new strands (already in chronological order)
                    for strand in result.data:
                        self.handle_strand({'new': strand})
                        strand_created_at = strand.get('created_at')
                        if strand_created_at:
                            # Track the latest timestamp we've seen
                            if not last_created_at or strand_created_at > last_created_at:
                                last_created_at = strand_created_at
                
                await asyncio.sleep(5)  # Poll every 5 seconds
            except Exception as poll_error:
                logger.error(f"Polling error: {poll_error}", exc_info=True)
                await asyncio.sleep(5)

    def _get_stage_glyph(self, stage: str) -> str:
        mapping = {
            'S0': '🜁0',  # Air / Watchlist
            'S1': '🜂1',  # Fire
            'S2': '🜃2',  # Earth
            'S3': '🜓3',  # swap to new symbol
            'S4': '🝪4',  # No clear state
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
                # Curator is nested: signal_pack.curator.id
                signal_pack = record.get('signal_pack', {})
                curator_obj = signal_pack.get('curator', {})
                curator = curator_obj.get('id', curator_obj.get('handle', 'Unknown'))
                # Chain is in signal_pack.token.chain
                token_data = signal_pack.get('token', {})
                chain = token_data.get('chain', '')
                # Intent type from intent_analysis
                intent_analysis = signal_pack.get('intent_analysis', {})
                intent_data = intent_analysis.get('intent_analysis', {}) if isinstance(intent_analysis, dict) else {}
                intent_type = intent_data.get('intent_type', 'unknown')
                output = f"⟡  SOCIAL   | {curator} → {symbol} ({chain}) | Intent: {intent_type}"
                
            elif kind == 'decision_lowcap':
                action = content.get('action', 'WAIT')
                # Decision Maker writes 'allocation_pct', not 'allocation_percentage'
                alloc = content.get('allocation_pct', content.get('allocation_percentage', 0))
                reason = (content.get('reasoning') or "")[:300]
                # Check for learning context
                learning_suffix = " | 𓂀" if module_intel else ""
                output = f"∆φ DECISION | {action} {symbol} | Alloc: {alloc}%{learning_suffix}"
                if reason:
                    output += f" | {reason}"
                
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
                tf = record.get('timeframe', '')
                windows = content.get('windows') or []
                sample_count = 0
                for w in windows:
                    summary = w.get('summary') or {}
                    sample_count += int(summary.get('sample_count') or 0)
                output = f"ᛟ  EPISODE  | {symbol} ({tf}) {ep_type} → {outcome} | Entered: {entered} | samples:{sample_count}"
            
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
        self.price_collector = None
        self.strand_monitor = None
        self.social_monitor = None
        
    def _load_config(self) -> Dict[str, Any]:
        # Replicate config structure from run_social_trading.py
        return {
            'trading': {
                'book_nav': float(os.getenv('BOOK_NAV', '100000.0')),
                'max_exposure_pct': 20.0,
                'min_curator_score': 0.6,
                'default_allocation_pct': 25.0,
                'min_allocation_pct': 10.0,
                'max_allocation_pct': 40.0,
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
        print("\n⚘⟁ Welcome to Lotus⚘⟁3 𓂀")
        print("\n⚘⟁ QI Trading System Initializing...⚘⟁⌖")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        try:
            self.supabase_manager = SupabaseManager()
            print("   ⋻ Supabase Manager... OK")

            self.llm_client = OpenRouterClient()
            print("   ∴ LLM Client... OK")

            self.jupiter_client = JupiterClient()
            self.wallet_manager = WalletManager()
            print("   🜄 Trading Core (Jupiter/Wallet)... OK")

            self.learning_system = UniversalLearningSystem(
                supabase_manager=self.supabase_manager,
                llm_client=self.llm_client,
                llm_config=None
            )
            print("   𓂀 Universal Learning System... Active")

            self.social_ingest = SocialIngestModule(
                supabase_manager=self.supabase_manager,
                llm_client=self.llm_client,
                config_path="src/config/twitter_curators.yaml"
            )
            self.social_ingest.learning_system = self.learning_system
            
            # Get curator list for startup display
            curators = self.social_ingest.get_enabled_curators()
            twitter_curators = [c for c in curators if c.get('platform') == 'twitter']
            telegram_curators = [c for c in curators if c.get('platform') == 'telegram']
            
            # Format Twitter handles (remove @ prefix if present, then add one)
            twitter_handles = []
            for c in twitter_curators:
                handle = c.get('platform_data', {}).get('handle') or c.get('name') or 'unknown'
                # Remove @ if already present, then add one
                if handle:
                    handle = str(handle).lstrip('@')
                twitter_handles.append(f"@{handle}")
            
            # Format Telegram handles
            telegram_handles = []
            for c in telegram_curators:
                handle = c.get('platform_data', {}).get('handle') or c.get('name') or 'unknown'
                if handle:
                    handle = str(handle).lstrip('@')
                telegram_handles.append(f"@{handle}")
            
            print("   ⟡ Social Ingest... Listening")
            if twitter_curators:
                # Format Twitter handles with better spacing (wrap at ~70 chars)
                twitter_list = ', '.join(twitter_handles)
                if len(twitter_list) > 70:
                    # Split into multiple lines, ~3-4 handles per line
                    handles_per_line = 4
                    lines = []
                    for i in range(0, len(twitter_handles), handles_per_line):
                        chunk = twitter_handles[i:i+handles_per_line]
                        lines.append(', '.join(chunk))
                    twitter_display = '\n' + '\n'.join(f"      {line}" for line in lines)
                else:
                    twitter_display = f" ({twitter_list})"
                print(f"      Twitter: {len(twitter_curators)} curators{twitter_display}")
            if telegram_curators:
                # Format Telegram handles with better spacing (wrap at ~70 chars)
                telegram_list = ', '.join(telegram_handles)
                if len(telegram_list) > 70:
                    # Split into multiple lines, ~3-4 handles per line
                    handles_per_line = 4
                    lines = []
                    for i in range(0, len(telegram_handles), handles_per_line):
                        chunk = telegram_handles[i:i+handles_per_line]
                        lines.append(', '.join(chunk))
                    telegram_display = '\n' + '\n'.join(f"      {line}" for line in lines)
                else:
                    telegram_display = f" ({telegram_list})"
                print(f"      Telegram: {len(telegram_curators)} curators{telegram_display}")
            elif not twitter_curators and not telegram_curators:
                print("      No curators configured")

            self.decision_maker = DecisionMakerLowcapSimple(
                supabase_manager=self.supabase_manager,
                config=self.config,
                learning_system=self.learning_system
            )
            print("   ∆φ Decision Maker... Ready")

            # PriceOracle initialization (extracted from TraderLowcapSimpleV2)
            from trading.price_oracle_factory import create_price_oracle
            price_oracle = create_price_oracle()
            print("   ⚡ Price Oracle... OK")
            
            # Wire up dependencies
            self.learning_system.set_decision_maker(self.decision_maker)
            self.supabase_manager.wallet_manager = self.wallet_manager
            print("   🜄 Dependencies... OK")

            self.price_collector = ScheduledPriceCollector(
                supabase_manager=self.supabase_manager,
                price_oracle=price_oracle
            )
            print("   ⩜ Scheduled Price Collector... OK")

            # PM Executor is initialized internally by PM Core Tick (no registration needed)
            if os.getenv("ACTIONS_ENABLED", "0") == "1":
                print("   ⚡ PM Executor... Enabled (via PM Core Tick)")
            else:
                print("   ⋇ PM Executor... Disabled (Read-Only)")
            
            # Initialize Strand Monitor (will start async in run())
            self.strand_monitor = StrandMonitor(self.supabase_manager)
            print("   ⟖ Strand Monitor... Initialized")

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
    
    def _wrap_rollup_catchup(self, timeframe_enum, name, lookback_hours: int = 24):
        """Run catch-up for missed rollup boundaries (separate from normal rollup)"""
        try:
            rollup = GenericOHLCRollup()
            scheduler_logger = logging.getLogger('schedulers')
            scheduler_logger.info(f"Running catch-up for {name} (lookback: {lookback_hours}h)")
            
            catchup_result = rollup.catch_up_rollups(
                data_source=DataSource.LOWCAPS,
                timeframe=timeframe_enum,
                lookback_hours=lookback_hours,
                max_boundaries=100,  # Process up to 100 boundaries per run
                max_tokens=50        # Process up to 50 tokens per run
            )
            
            if catchup_result.get("boundaries_filled", 0) > 0:
                scheduler_logger.info(
                    f"Catch-up {name}: filled {catchup_result['boundaries_filled']} boundaries, "
                    f"skipped {catchup_result['boundaries_skipped']}, "
                    f"tokens: {catchup_result['tokens_processed']}"
                )
            elif catchup_result.get("status") == "no_gaps":
                scheduler_logger.debug(f"Catch-up {name}: no gaps found")
        except Exception as e:
            logger.error(f"Catch-up {name} error: {e}", exc_info=True)

    def _wrap_uptrend(self, timeframe):
        try:
            uptrend_engine_main(timeframe=timeframe)
        except Exception as e:
            logger.error(f"Uptrend ({timeframe}) error: {e}", exc_info=True)
    
    def _wrap_ta_then_uptrend(self, timeframe):
        """Run TA Tracker, then Uptrend Engine sequentially to ensure TA runs first."""
        try:
            self._wrap_ta_tracker(timeframe)
            self._wrap_uptrend(timeframe)
        except Exception as e:
            logger.error(f"TA→Uptrend ({timeframe}) error: {e}", exc_info=True)
    
    def _wrap_ta_then_uptrend_then_pm(self, timeframe):
        """Run TA Tracker → Uptrend Engine → PM Core Tick sequentially."""
        try:
            self._wrap_ta_tracker(timeframe)
            self._wrap_uptrend(timeframe)
            self._wrap_pm_core(timeframe)
        except Exception as e:
            logger.error(f"TA→Uptrend→PM ({timeframe}) error: {e}", exc_info=True)

    async def start_schedulers(self):
        scheduler_logger = logging.getLogger('schedulers')
        print("⧖ Starting Schedulers...")
        scheduler_logger.info("Starting scheduler system")
        
        # 0. Bootstrap System (verify all data collection systems)
        scheduler_logger.info("Starting bootstrap phase")
        
        bootstrap = None
        try:
            bootstrap = BootstrapSystem()
            # Bootstrap prints its own progress messages, no wrapper needed
            bootstrap_results = bootstrap.bootstrap_all()
            scheduler_logger.info(f"Bootstrap status: {bootstrap_results.get('status', 'unknown')}")
        except Exception as e:
            scheduler_logger.error(f"Bootstrap error: {e}", exc_info=True)
            print("   ❦ Bootstrap Failed (see logs/system.log)")
            # Continue anyway - bootstrap failures are non-fatal
        
        # 0.25. Capture initial balance snapshot (if none exists)
        try:
            sb_client = self._create_service_client()
            balance_snapshot_job = BalanceSnapshotJob(sb_client)
            await balance_snapshot_job.ensure_initial_snapshot()
            scheduler_logger.info("Initial balance snapshot ensured")
        except Exception as e:
            scheduler_logger.error(f"Initial balance snapshot error: {e}", exc_info=True)
            # Non-fatal, continue
        
        # 0.5. Start Hyperliquid WS early so we can verify it's working
        hl_ingester = None
        hl_task = None
        if os.getenv("HL_INGEST_ENABLED", "0") == "1":
            try:
                from intelligence.lowcap_portfolio_manager.ingest.hyperliquid_ws import HyperliquidWSIngester
                
                hl_ingester = HyperliquidWSIngester()
                hl_task = asyncio.create_task(hl_ingester.run())
                scheduler_logger.info("Hyperliquid WS ingester started (early)")
                
                # Wait a few seconds for it to connect and receive first data (with glyph loading)
                async def wait_for_hl():
                    await asyncio.sleep(5)
                
                await show_glyph_loading_async("⨳ Starting Hyperliquid WS...", wait_for_hl())
                
                # Check if it's working
                if bootstrap:
                    hl_status = bootstrap._check_hyperliquid_ws()
                    status = hl_status.get("status", "unknown")
                    if status == "ok":
                        tokens = hl_status.get("tokens", 0)
                        age = hl_status.get("age_minutes", 0)
                        print(f"✓ ({tokens} tokens, {age:.1f}m old)")
                    elif status == "stale":
                        age = hl_status.get("age_minutes", 0)
                        print(f"⚠ ({age:.1f}m old)")
                    elif status == "no_data":
                        warning = hl_status.get("warning", "No data")
                        print(f"⚠ ({warning[:30]})")
                        logger.warning(f"Hyperliquid WS: {warning}")
                    else:
                        error = hl_status.get("error", hl_status.get("warning", "Unknown"))
                        print(f"⚠ ({str(error)[:30]})")
                        logger.warning(f"Hyperliquid WS status: {status}, {error}")
                else:
                    print("⌖")
            except Exception as e:
                scheduler_logger.error(f"HL WS early start error: {e}", exc_info=True)
                print("✗")
        
        # 1. Seed Jobs (Individual error handling per job)
        print("   ⨳ Running Seed Jobs...")
        scheduler_logger.info("Starting seed phase")
        
        try:
            scheduler_logger.info("Seed job: feat_main starting")
            await asyncio.to_thread(
                show_glyph_loading,
                "      ⟡ Features tracker...",
                feat_main
            )
            scheduler_logger.info("Seed job: feat_main completed")
            print("      ⟡ Features tracker... ✓")
        except Exception as e:
            scheduler_logger.error(f"PM seed (features/phase) error: {e}", exc_info=True)
            print(f"      ⟡ Features tracker... ✗ ({str(e)[:30]})")
        
        try:
            scheduler_logger.info("Seed job: pm_core_main starting")
            await asyncio.to_thread(
                show_glyph_loading,
                "      ⟡ PM Core tick (1h)...",
                lambda: pm_core_main(timeframe="1h", learning_system=self.learning_system)
            )
            scheduler_logger.info("Seed job: pm_core_main completed")
            print("      ⟡ PM Core tick (1h)... ✓")
        except Exception as e:
            scheduler_logger.error(f"PM seed (core) error: {e}", exc_info=True)
            print(f"      ⟡ PM Core tick (1h)... ✗ ({str(e)[:30]})")
        
        print("   ⨵ Seed Jobs Complete")
        print("   ↻ Starting recurring schedulers...")
        scheduler_logger.info("Seed phase completed")

        # 2. Recurring Schedule
        tasks = []
        
        # Add Hyperliquid WS task if it was started early
        if hl_task:
            tasks.append(hl_task)
        
        # 1 Minute Jobs
        tasks.append(asyncio.create_task(self._schedule_at_interval(60, lambda: GenericOHLCRollup().rollup_timeframe(DataSource.LOWCAPS, Timeframe.M1), "OHLC 1m")))
        def majors_1m_rollup_job():
            try:
                rollup = OneMinuteRollup()
                rollup.roll_minute()
            except Exception as e:
                logger.error(f"Majors 1m rollup error: {e}", exc_info=True)
        tasks.append(asyncio.create_task(self._schedule_at_interval(60, majors_1m_rollup_job, "Majors Rollup")))
        # Run TA → Uptrend → PM sequentially to ensure correct ordering
        tasks.append(asyncio.create_task(self._schedule_at_interval(60, lambda: self._wrap_ta_then_uptrend_then_pm("1m"), "TA→Uptrend→PM 1m")))
        tasks.append(asyncio.create_task(self._schedule_at_interval(60, lambda: run_regime_pipeline(timeframe="1m"), "Regime 1m")))

        # 5 Minute Jobs (Aligned)
        tasks.append(asyncio.create_task(self._schedule_aligned(5, 0, feat_main, "Tracker")))
        tasks.append(asyncio.create_task(self._schedule_aligned(5, 0, lambda: self._wrap_rollup(Timeframe.M5, "Rollup 5m"), "Rollup 5m")))
        tasks.append(asyncio.create_task(self._schedule_aligned(5, 2, self._wrap_pattern_aggregator, "Pattern Aggregator")))

        # 15 Minute Jobs (Aligned)
        tasks.append(asyncio.create_task(self._schedule_aligned(15, 0, feat_main, "Tracker")))
        tasks.append(asyncio.create_task(self._schedule_aligned(15, 0, lambda: self._wrap_rollup(Timeframe.M15, "Rollup 15m"), "Rollup 15m")))
        # Run TA → Uptrend → PM sequentially to ensure correct ordering
        tasks.append(asyncio.create_task(self._schedule_aligned(15, 0, lambda: self._wrap_ta_then_uptrend_then_pm("15m"), "TA→Uptrend→PM 15m")))

        # Hourly Jobs
        tasks.append(asyncio.create_task(self._schedule_hourly(1, lambda: run_regime_pipeline(timeframe="1h"), "Regime 1h")))
        tasks.append(asyncio.create_task(self._schedule_hourly(2, nav_main, "NAV")))
        # Dominance ingest removed in current pipeline (handled by regime engine); skip scheduling
        tasks.append(asyncio.create_task(self._schedule_hourly(4, lambda: self._wrap_rollup(Timeframe.H1, "Rollup 1h"), "Rollup 1h")))
        # Geometry at :05 (before TA/PM at :06)
        tasks.append(asyncio.create_task(self._schedule_hourly(5, lambda: self._wrap_geometry("1m"), "Geom 1m")))
        tasks.append(asyncio.create_task(self._schedule_hourly(5, lambda: self._wrap_geometry("15m"), "Geom 15m")))
        tasks.append(asyncio.create_task(self._schedule_hourly(5, lambda: self._wrap_geometry("1h"), "Geom 1h")))
        tasks.append(asyncio.create_task(self._schedule_hourly(5, lambda: self._wrap_geometry("4h"), "Geom 4h")))
        # Run TA → Uptrend → PM sequentially to ensure correct ordering
        tasks.append(asyncio.create_task(self._schedule_hourly(6, lambda: self._wrap_ta_then_uptrend_then_pm("1h"), "TA→Uptrend→PM 1h")))
        
        tasks.append(asyncio.create_task(self._schedule_hourly(7, update_bars_count_main, "Bars Count")))
        
        tasks.append(asyncio.create_task(self._schedule_hourly(8, lambda: self._wrap_lesson_builder('pm'), "Lesson PM")))
        tasks.append(asyncio.create_task(self._schedule_hourly(9, lambda: self._wrap_lesson_builder('dm'), "Lesson DM")))
        tasks.append(asyncio.create_task(self._schedule_hourly(10, self._wrap_override_materializer, "Override Mat")))
        # Bucket tagging (cap buckets) hourly to keep token_cap_bucket fresh
        tasks.append(asyncio.create_task(self._schedule_hourly(11, cap_bucket_tagging_main, "Cap Bucket Tagging")))
        # Bucket tracker (phase_state_bucket -> bucket_rank) hourly
        tasks.append(asyncio.create_task(self._schedule_hourly(12, bucket_tracker_main, "Bucket Tracker")))

        # 4 Hour Jobs
        tasks.append(asyncio.create_task(self._schedule_4h(0, lambda: self._wrap_rollup(Timeframe.H4, "Rollup 4h"), "Rollup 4h")))
        # Run TA → Uptrend → PM sequentially to ensure correct ordering
        tasks.append(asyncio.create_task(self._schedule_4h(0, lambda: self._wrap_ta_then_uptrend_then_pm("4h"), "TA→Uptrend→PM 4h")))
        
        # Balance snapshots - hierarchical system
        # 1. Hourly snapshot (every hour)
        def _wrap_hourly_snapshot():
            try:
                sb_client = self._create_service_client()
                job = BalanceSnapshotJob(sb_client)
                asyncio.run(job.capture_snapshot("hourly"))
            except Exception as e:
                logger.error(f"Hourly balance snapshot error: {e}", exc_info=True)
        tasks.append(asyncio.create_task(self._schedule_hourly(0, _wrap_hourly_snapshot, "Hourly Balance Snapshot")))
        
        # 2. 4-hour rollup (every 4 hours, at :00)
        def _wrap_4hour_rollup():
            try:
                sb_client = self._create_service_client()
                job = BalanceSnapshotJob(sb_client)
                asyncio.run(job.rollup_4hour_snapshots())
            except Exception as e:
                logger.error(f"4-hour rollup error: {e}", exc_info=True)
        tasks.append(asyncio.create_task(self._schedule_4h(0, _wrap_4hour_rollup, "4-Hour Snapshot Rollup")))
        
        # Catch-up Jobs (run hourly to fill any missed rollup boundaries)
        # Run at :02 to run after normal rollups at :00/:01
        # Lookback: 2 hours (since we run hourly, max gap should be ~1 hour, but 2h gives safety margin)
        tasks.append(asyncio.create_task(self._schedule_hourly(2, lambda: self._wrap_rollup_catchup(Timeframe.M15, "Catch-up 15m", lookback_hours=2), "Catch-up 15m")))
        tasks.append(asyncio.create_task(self._schedule_hourly(2, lambda: self._wrap_rollup_catchup(Timeframe.H1, "Catch-up 1h", lookback_hours=2), "Catch-up 1h")))
        tasks.append(asyncio.create_task(self._schedule_hourly(2, lambda: self._wrap_rollup_catchup(Timeframe.H4, "Catch-up 4h", lookback_hours=6), "Catch-up 4h")))  # 6h lookback for 4h (covers 1.5 boundaries)
        
        # Daily Jobs (1d regime - macro)
        async def schedule_daily(offset_hour: int, func, name: str):
            """Schedule to run daily at specific hour."""
            scheduler_logger = logging.getLogger('schedulers')
            while self.running:
                now = datetime.now(timezone.utc)
                next_run = now.replace(hour=offset_hour, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                wait_s = (next_run - now).total_seconds()
                scheduler_logger.info(f"{name} scheduled for {next_run.isoformat()}")
                await asyncio.sleep(wait_s)
                try:
                    scheduler_logger.info(f"Starting {name}")
                    await asyncio.to_thread(func)
                    scheduler_logger.info(f"{name} completed")
                except Exception as e:
                    scheduler_logger.error(f"{name} failed: {e}", exc_info=True)
        
        tasks.append(asyncio.create_task(schedule_daily(0, lambda: run_regime_pipeline(timeframe="1d"), "Regime 1d")))
        
        # Daily snapshot rollup (every day at 1 AM UTC)
        def _wrap_daily_rollup():
            try:
                sb_client = self._create_service_client()
                job = BalanceSnapshotJob(sb_client)
                asyncio.run(job.rollup_daily_snapshots())
            except Exception as e:
                logger.error(f"Daily rollup error: {e}", exc_info=True)
        tasks.append(asyncio.create_task(schedule_daily(1, _wrap_daily_rollup, "Daily Snapshot Rollup")))
        
        # Weekly Jobs (run on Sunday at 1 AM UTC)
        async def schedule_weekly(offset_hour: int, func, name: str):
            """Schedule to run weekly on Sunday at specific hour."""
            scheduler_logger = logging.getLogger('schedulers')
            while self.running:
                now = datetime.now(timezone.utc)
                # Find next Sunday
                days_until_sunday = (6 - now.weekday()) % 7
                if days_until_sunday == 0 and now.hour >= offset_hour:
                    days_until_sunday = 7  # Already passed this week
                next_run = now.replace(hour=offset_hour, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
                wait_s = (next_run - now).total_seconds()
                scheduler_logger.info(f"{name} scheduled for {next_run.isoformat()}")
                await asyncio.sleep(wait_s)
                try:
                    scheduler_logger.info(f"Starting {name}")
                    await asyncio.to_thread(func)
                    scheduler_logger.info(f"{name} completed")
                except Exception as e:
                    scheduler_logger.error(f"{name} failed: {e}", exc_info=True)
        
        # Weekly snapshot rollup (Sunday 1 AM UTC)
        def _wrap_weekly_rollup():
            try:
                sb_client = self._create_service_client()
                job = BalanceSnapshotJob(sb_client)
                asyncio.run(job.rollup_weekly_snapshots())
            except Exception as e:
                logger.error(f"Weekly rollup error: {e}", exc_info=True)
        tasks.append(asyncio.create_task(schedule_weekly(1, _wrap_weekly_rollup, "Weekly Snapshot Rollup")))
        
        # Monthly Jobs (run on 1st of month at 2 AM UTC)
        async def schedule_monthly(offset_hour: int, func, name: str):
            """Schedule to run monthly on 1st at specific hour."""
            scheduler_logger = logging.getLogger('schedulers')
            while self.running:
                now = datetime.now(timezone.utc)
                # Find next 1st of month
                if now.day == 1 and now.hour >= offset_hour:
                    # Already passed this month, go to next month
                    if now.month == 12:
                        next_run = now.replace(year=now.year + 1, month=1, day=1, hour=offset_hour, minute=0, second=0, microsecond=0)
                    else:
                        next_run = now.replace(month=now.month + 1, day=1, hour=offset_hour, minute=0, second=0, microsecond=0)
                else:
                    # This month's 1st hasn't passed, or we're past it
                    if now.month == 12:
                        next_run = now.replace(year=now.year + 1, month=1, day=1, hour=offset_hour, minute=0, second=0, microsecond=0)
                    else:
                        next_run = now.replace(month=now.month + 1, day=1, hour=offset_hour, minute=0, second=0, microsecond=0)
                wait_s = (next_run - now).total_seconds()
                scheduler_logger.info(f"{name} scheduled for {next_run.isoformat()}")
                await asyncio.sleep(wait_s)
                try:
                    scheduler_logger.info(f"Starting {name}")
                    await asyncio.to_thread(func)
                    scheduler_logger.info(f"{name} completed")
                except Exception as e:
                    scheduler_logger.error(f"{name} failed: {e}", exc_info=True)
        
        # Monthly snapshot rollup (1st of month at 2 AM UTC)
        def _wrap_monthly_rollup():
            try:
                sb_client = self._create_service_client()
                job = BalanceSnapshotJob(sb_client)
                asyncio.run(job.rollup_monthly_snapshots())
            except Exception as e:
                logger.error(f"Monthly rollup error: {e}", exc_info=True)
        tasks.append(asyncio.create_task(schedule_monthly(2, _wrap_monthly_rollup, "Monthly Snapshot Rollup")))

        # Hyperliquid WS task already added to tasks list above if it was started early
        
        print("   ↻ Schedulers... Active")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("\n⚘⟁⌖ System Running - Monitoring strands...\n")
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
            
            # Note: PositionMonitor is legacy and removed - PM Core Tick handles all position management
            
            # Start Strand Monitor (async realtime subscription)
            strand_task = asyncio.create_task(self.strand_monitor.start())
            self.tasks.append(strand_task)
            logger.info("Strand monitor started")
            
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
