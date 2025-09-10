#!/usr/bin/env python3
"""
Lotus Trader Alpha Detector - Main Dashboard
Clean, high-level view of the complete trading intelligence system
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent / "src"))

from data_sources.hyperliquid_client import HyperliquidWebSocketClient
from market_data_collector import MarketDataCollector
from core_detection.market_data_processor import MarketDataProcessor
from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient
from intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
from llm_integration.agent_discovery_system import AgentDiscoverySystem

# Configure minimal logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SystemStats:
    """Track system statistics for dashboard display"""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.patterns_detected = 0
        self.predictions_created = 0
        self.predictions_completed = 0
        self.predictions_accurate = 0
        self.trading_plans_generated = 0
        self.learning_updates = 0
        self.last_pattern_time = None
        self.last_prediction_time = None
        self.active_patterns = []
        self.active_predictions = []
        
    def add_pattern(self, pattern_type: str, symbol: str):
        """Record a new pattern detection"""
        self.patterns_detected += 1
        self.last_pattern_time = datetime.now(timezone.utc)
        self.active_patterns.append({
            'type': pattern_type,
            'symbol': symbol,
            'time': self.last_pattern_time
        })
        # Keep only last 5 active patterns
        if len(self.active_patterns) > 5:
            self.active_patterns.pop(0)
    
    def add_prediction(self, symbol: str, confidence: float):
        """Record a new prediction"""
        self.predictions_created += 1
        self.last_prediction_time = datetime.now(timezone.utc)
        self.active_predictions.append({
            'symbol': symbol,
            'confidence': confidence,
            'time': self.last_prediction_time
        })
        # Keep only last 3 active predictions
        if len(self.active_predictions) > 3:
            self.active_predictions.pop(0)
    
    def complete_prediction(self, was_accurate: bool):
        """Record a completed prediction"""
        self.predictions_completed += 1
        if was_accurate:
            self.predictions_accurate += 1
    
    def add_trading_plan(self):
        """Record a new trading plan"""
        self.trading_plans_generated += 1
    
    def add_learning_update(self):
        """Record a learning update"""
        self.learning_updates += 1
    
    def get_accuracy_rate(self) -> float:
        """Calculate prediction accuracy rate"""
        if self.predictions_completed == 0:
            return 0.0
        return self.predictions_accurate / self.predictions_completed
    
    def get_uptime(self) -> str:
        """Get system uptime"""
        uptime = datetime.now(timezone.utc) - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

class AlphaDetectorDashboard:
    """Main dashboard for the Alpha Detector system"""
    
    def __init__(self):
        self.is_running = False
        self.stats = SystemStats()
        self.components = {}
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            print("\n🛑 Shutting down gracefully...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize_components(self):
        """Initialize all system components"""
        try:
            # Core infrastructure
            self.components['supabase_manager'] = SupabaseManager()
            self.components['llm_client'] = OpenRouterClient()
            self.components['market_data_processor'] = MarketDataProcessor(self.components['supabase_manager'])
            
            # WebSocket client
            self.components['websocket_client'] = HyperliquidWebSocketClient(['BTC', 'ETH', 'SOL'])
            
            # Raw Data Intelligence
            self.components['raw_data_agent'] = RawDataIntelligenceAgent(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            
            # Central Intelligence Layer
            self.components['cil'] = SimplifiedCIL(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            
            # Agent discovery
            self.components['discovery_system'] = AgentDiscoverySystem(self.components['supabase_manager'])
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize components: {e}")
            return False
    
    async def setup_data_flow(self):
        """Setup the data flow connections"""
        
        async def market_data_callback(data: Dict[str, Any]):
            """Process incoming market data"""
            try:
                # Store market data
                await self.components['market_data_processor'].process_ohlcv_data(data)
                
                # Analyze with Raw Data Intelligence
                analysis_result = await self.components['raw_data_agent']._analyze_raw_data_enhanced(data)
                
                # Check for patterns and update stats
                if analysis_result and 'patterns' in analysis_result:
                    for pattern in analysis_result['patterns']:
                        self.stats.add_pattern(
                            pattern.get('type', 'unknown'),
                            data['symbol']
                        )
                
                # Trigger CIL processing
                await self._trigger_cil_processing()
                
            except Exception as e:
                print(f"⚠️  Error processing market data: {e}")
        
        # Set the callback
        self.components['websocket_client'].set_data_callback(market_data_callback)
    
    async def _trigger_cil_processing(self):
        """Trigger CIL processing when new patterns are available"""
        try:
            # Get recent strands from Raw Data Intelligence
            recent_strands = await self.components['supabase_manager'].get_recent_strands(
                limit=10, 
                since=datetime.now(timezone.utc) - timedelta(minutes=5)
            )
            
            if not recent_strands:
                return
            
            # Process through CIL
            predictions = await self.components['cil'].process_patterns(recent_strands)
            
            # Update stats
            for prediction in predictions:
                self.stats.add_prediction(
                    prediction.get('symbol', 'unknown'),
                    prediction.get('confidence', 0.0)
                )
            
            # Check for trading plans
            plans = await self.components['cil'].get_active_plans()
            if plans:
                self.stats.add_trading_plan()
            
            # Update learning
            self.stats.add_learning_update()
            
        except Exception as e:
            print(f"⚠️  Error in CIL processing: {e}")
    
    def display_dashboard(self):
        """Display the main dashboard"""
        # Clear screen and move cursor to top
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🚀 LOTUS TRADER ALPHA DETECTOR")
        print("═" * 60)
        print()
        
        # System Status
        print("📊 SYSTEM STATUS")
        status_color = "✅" if self.is_running else "❌"
        print(f"├── Raw Data Intelligence: {status_color} ACTIVE ({self.stats.patterns_detected} patterns detected)")
        print(f"├── Central Intelligence Layer: {status_color} ACTIVE ({len(self.stats.active_predictions)} predictions active)")
        print(f"├── Learning System: {status_color} ACTIVE (accuracy: {self.stats.get_accuracy_rate():.1%})")
        print(f"└── Market Data: {status_color} CONNECTED (BTC, ETH, SOL)")
        print()
        
        # Live Statistics
        print("📈 LIVE STATISTICS (Last 5 minutes)")
        print(f"├── Patterns Detected: {self.stats.patterns_detected}")
        print(f"├── Predictions Created: {self.stats.predictions_created}")
        print(f"├── Predictions Completed: {self.stats.predictions_completed} (accuracy: {self.stats.get_accuracy_rate():.1%})")
        print(f"├── Trading Plans Generated: {self.stats.trading_plans_generated}")
        print(f"└── Learning Updates: {self.stats.learning_updates}")
        print()
        
        # Current Focus
        print("🎯 CURRENT FOCUS")
        if self.stats.active_patterns:
            print("├── Active Patterns:")
            for pattern in self.stats.active_patterns[-3:]:  # Show last 3
                time_str = pattern['time'].strftime("%H:%M:%S")
                print(f"│   ├── {pattern['type']} ({pattern['symbol']}) - {time_str}")
        else:
            print("├── Active Patterns: None")
        
        if self.stats.active_predictions:
            print("├── Active Predictions:")
            for pred in self.stats.active_predictions[-3:]:  # Show last 3
                time_str = pred['time'].strftime("%H:%M:%S")
                print(f"│   ├── {pred['symbol']} (confidence: {pred['confidence']:.2f}) - {time_str}")
        else:
            print("├── Active Predictions: None")
        
        print(f"└── System Uptime: {self.stats.get_uptime()}")
        print()
        print("═" * 60)
        print("Press Ctrl+C to stop")
    
    async def start_system(self):
        """Start the complete system"""
        print("🚀 Starting Lotus Trader Alpha Detector...")
        
        # Initialize components
        if not await self.initialize_components():
            print("❌ Failed to initialize components")
            return False
        
        # Setup data flow
        await self.setup_data_flow()
        
        # Start Raw Data Intelligence
        await self.components['raw_data_agent'].start(self.components['discovery_system'])
        
        # Start CIL
        await self.components['cil'].start()
        
        # Connect to WebSocket
        connected = await self.components['websocket_client'].connect()
        if not connected:
            print("❌ Failed to connect to WebSocket")
            return False
        
        await self.components['websocket_client'].subscribe_to_market_data()
        
        # Start the system
        self.is_running = True
        print("✅ System started successfully!")
        
        # Start dashboard update loop
        try:
            while self.is_running:
                self.display_dashboard()
                await asyncio.sleep(300)  # Update every 5 minutes
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully shutdown the system"""
        if not self.is_running:
            return
            
        print("🛑 Shutting down system...")
        self.is_running = False
        
        try:
            # Stop WebSocket
            if 'websocket_client' in self.components:
                await self.components['websocket_client'].disconnect()
            
            # Stop agents
            if 'raw_data_agent' in self.components:
                await self.components['raw_data_agent'].stop()
            
            if 'cil' in self.components:
                await self.components['cil'].stop()
            
            print("✅ Shutdown complete")
            
        except Exception as e:
            print(f"⚠️  Error during shutdown: {e}")

async def main():
    """Main entry point"""
    dashboard = AlphaDetectorDashboard()
    await dashboard.start_system()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)
