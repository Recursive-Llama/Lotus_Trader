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
from llm_integration.openrouter_client import OpenRouterClient

# Import real components
from intelligence.social_ingest.social_ingest_basic import SocialIngestModule
from intelligence.social_ingest.discord_monitor_integrated import DiscordMonitorIntegrated
from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
# Defer trader imports to initialization to allow V2-only startup without
# importing V1 when refactor is underway.
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from trading.jupiter_client import JupiterClient
from trading.wallet_manager import WalletManager
from trading.trading_executor import TradingExecutor
from trading.scheduled_price_collector import ScheduledPriceCollector
from trading.position_monitor import PositionMonitor


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
        self.discord_monitor = None
        self.decision_maker = None
        self.trader = None
        self.learning_system = None
        self.price_collector = None
        self.position_monitor = None
        
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
                    'default_allocation_pct': 4.0,  # 4% default allocation
                    'min_allocation_pct': 2.0,  # Minimum 2% allocation
                    'max_allocation_pct': 6.0,  # Maximum 6% allocation
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
            self.trading_executor = TradingExecutor(self.jupiter_client, self.wallet_manager)
            
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
            
            # Initialize Gem Bot monitor
            from intelligence.social_ingest.discord_gem_bot_monitor_v2 import DiscordGemBotMonitor
            self.gem_bot_monitor = DiscordGemBotMonitor(
                check_interval=30,  # Check every 30 seconds
                test_mode=False  # Production mode
            )
            
            # Initialize Discord monitor
            self.discord_monitor = DiscordMonitorIntegrated(
                learning_system=self.learning_system,
                check_interval=60  # Check every 60 seconds
            )
            
            # Initialize decision maker with learning system reference
            self.decision_maker = DecisionMakerLowcapSimple(
                supabase_manager=self.supabase_manager,
                config=self.config,  # Pass full config so AllocationManager can access allocation_config
                learning_system=self.learning_system
            )
            
            # Initialize trader (V2 - improved Base trading and modular design)
            from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
            
            # Prepare trader config with both trading and lotus_buyback sections
            trader_config = self.config.get('trading', {}).copy()
            if 'lotus_buyback' in self.config:
                trader_config['lotus_buyback'] = self.config['lotus_buyback']
            
            self.trader = TraderLowcapSimpleV2(
                supabase_manager=self.supabase_manager,
                config=trader_config
            )
            
            # Share trader instance with learning system to avoid conflicts
            self.learning_system.trader = self.trader
            
            # Set the decision maker reference in learning system
            self.learning_system.set_decision_maker(self.decision_maker)
            
            # Set trader reference in wallet manager for SPL token balance checking
            self.wallet_manager.trader = self.trader
            print(f"DEBUG: Set trader reference in wallet manager: {self.wallet_manager.trader}")
            
            # Attach wallet manager to supabase manager for price collector
            self.supabase_manager.wallet_manager = self.wallet_manager
            
            # Initialize scheduled price collector
            self.price_collector = ScheduledPriceCollector(
                supabase_manager=self.supabase_manager,
                price_oracle=self.trader.price_oracle
            )
            
            # Initialize position monitor
            self.position_monitor = PositionMonitor(
                supabase_manager=self.supabase_manager,
                trader=self.trader
            )

            # Register PM executor (event-driven) if actions are enabled
            try:
                if os.getenv("ACTIONS_ENABLED", "0") == "1":
                    from intelligence.lowcap_portfolio_manager.pm.executor import register_pm_executor
                    # Supabase client reference
                    sb_client = self.supabase_manager.db_manager.client if hasattr(self.supabase_manager, 'db_manager') else self.supabase_manager.client
                    register_pm_executor(self.trader, sb_client)
            except Exception as e:
                logger.warning(f"PM executor registration skipped: {e}")
            
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
            
            # Start position monitoring (30-second intervals)
            await self.position_monitor.start_monitoring(check_interval=30)
            
        except Exception as e:
            print(f"❌ Position management failed: {e}")
    
    async def start_gem_bot_monitoring(self):
        """Start Gem Bot monitoring"""
        try:
            print("🤖 Starting Gem Bot monitoring...")
            await self.gem_bot_monitor.start_monitoring()
            
        except Exception as e:
            print(f"❌ Failed to start Gem Bot monitoring: {e}")
    
    async def start_discord_monitoring(self):
        """Start Discord monitoring"""
        try:
            print("🔍 Starting Discord monitoring...")
            await self.discord_monitor.start_monitoring()
            
        except Exception as e:
            print(f"❌ Failed to start Discord monitoring: {e}")
    
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
                # asyncio.create_task(self.start_discord_monitoring()),  # Disabled for now
                # asyncio.create_task(self.start_gem_bot_monitoring()),  # Disabled for now
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

        # Import job entrypoints lazily
        from intelligence.lowcap_portfolio_manager.jobs.nav_compute_1h import main as nav_main
        from intelligence.lowcap_portfolio_manager.jobs.dominance_ingest_1h import main as dom_main
        from intelligence.lowcap_portfolio_manager.jobs.tracker import main as feat_main
        from intelligence.lowcap_portfolio_manager.jobs.bands_calc import main as bands_main
        from intelligence.lowcap_portfolio_manager.jobs.geometry_build_daily import main as geom_daily_main
        from intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import main as pm_core_main

        # Fire background schedulers
        asyncio.create_task(schedule_hourly(2, nav_main))
        asyncio.create_task(schedule_hourly(3, dom_main))
        asyncio.create_task(schedule_5min(0, feat_main))  # Tracker every 5 minutes
        asyncio.create_task(schedule_hourly(5, bands_main))
        asyncio.create_task(schedule_hourly(6, pm_core_main))
        # GeckoTerminal backfill is triggered only on new-position onboarding; no hourly scan.
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
        asyncio.create_task(schedule_daily(10, geom_daily_main))

        # One-shot seed after startup: dominance → features/phase → bands → pm_core
        async def seed_pm_once():
            try:
                await asyncio.to_thread(dom_main)
            except Exception as e:
                print(f"PM seed (dominance) error: {e}")
            try:
                await asyncio.to_thread(feat_main)
            except Exception as e:
                print(f"PM seed (features/phase) error: {e}")
            try:
                await asyncio.to_thread(bands_main)
            except Exception as e:
                print(f"PM seed (bands) error: {e}")
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