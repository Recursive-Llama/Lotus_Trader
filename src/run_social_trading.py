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
from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
from intelligence.trader_lowcap.trader_lowcap_simple import TraderLowcapSimple
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from trading.jupiter_client import JupiterClient
from trading.wallet_manager import WalletManager
from trading.trading_executor import TradingExecutor
from trading.price_monitor import PriceMonitor


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
        self.trader = None
        self.learning_system = None
        self.price_monitor = None
        
        # Output tracking
        self.last_output_time = datetime.now()
        self.output_interval = 5  # seconds between status updates
        
        print("🚀 Social Trading System initialized")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
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
                'default_allocation_pct': 3.0,  # 3% default allocation
                'slippage_pct': 1.0
            },
            'position_management': {
                'price_check_interval': 30,  # seconds - check prices every 30s
                'exit_check_interval': 30,   # seconds
                'jupiter_price_enabled': True
            },
            'jupiter': {
                'api_url': 'https://quote-api.jup.ag/v6',
                'price_url': 'https://price.jup.ag/v4'
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
            
            # Initialize decision maker
            self.decision_maker = DecisionMakerLowcapSimple(
                supabase_manager=self.supabase_manager,
                config=self.config.get('trading', {})
            )
            
            # Initialize trader
            self.trader = TraderLowcapSimple(
                supabase_manager=self.supabase_manager,
                config=self.config.get('trading', {})
            )
            
            # Initialize price monitor
            self.price_monitor = PriceMonitor(
                supabase_manager=self.supabase_manager,
                jupiter_client=self.jupiter_client,
                wallet_manager=self.wallet_manager
            )
            
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
            
            # Start price monitoring with minimal output
            await self.price_monitor.start_monitoring(
                check_interval=self.config['position_management']['price_check_interval']
            )
            
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
                asyncio.create_task(self.start_learning_system())
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