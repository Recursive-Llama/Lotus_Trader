#!/usr/bin/env python3
"""
Lotus Trader Alpha Detector - Main Entry Point
Orchestrates the complete dataflow: WebSocket → Raw Data Intelligence → CIL → Trading Plans
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, Any
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
from intelligence.system_control.central_intelligence_layer.engines.input_processor import InputProcessor
from intelligence.system_control.central_intelligence_layer.core.cil_plan_composer import CILPlanComposer
from intelligence.system_control.central_intelligence_layer.engines.experiment_orchestration_engine import ExperimentOrchestrationEngine
from intelligence.system_control.central_intelligence_layer.engines.prediction_outcome_tracker import PredictionOutcomeTracker
from intelligence.system_control.central_intelligence_layer.engines.learning_feedback_engine import LearningFeedbackEngine
from intelligence.system_control.central_intelligence_layer.engines.output_directive_system import OutputDirectiveSystem
from intelligence.integrated_learning_system import IntegratedLearningSystem
from intelligence.learning_config import LearningConfigManager
from intelligence.learning_monitor import LearningMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('alpha_detector.log')
    ]
)

logger = logging.getLogger(__name__)

class AlphaDetectorOrchestrator:
    """Main orchestrator for the Alpha Detector system"""
    
    def __init__(self):
        self.is_running = False
        self.components = {}
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize_components(self):
        """Initialize all system components"""
        logger.info("🚀 Initializing Alpha Detector components...")
        
        try:
            # Core infrastructure
            logger.info("📊 Setting up database and LLM connections...")
            self.components['supabase_manager'] = SupabaseManager()
            self.components['llm_client'] = OpenRouterClient()
            self.components['market_data_processor'] = MarketDataProcessor(self.components['supabase_manager'])
            
            # Data collection
            logger.info("📡 Setting up WebSocket client...")
            self.components['websocket_client'] = HyperliquidWebSocketClient(['BTC', 'ETH', 'SOL'])
            
            # Raw Data Intelligence
            logger.info("🧠 Initializing Raw Data Intelligence Agent...")
            self.components['raw_data_agent'] = RawDataIntelligenceAgent(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            
            # CIL Components
            logger.info("🎯 Initializing CIL components...")
            self.components['input_processor'] = InputProcessor(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['plan_composer'] = CILPlanComposer(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['experiment_engine'] = ExperimentOrchestrationEngine(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['prediction_tracker'] = PredictionOutcomeTracker(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['learning_engine'] = LearningFeedbackEngine(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['output_directive'] = OutputDirectiveSystem(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            
            # Learning System
            logger.info("🎓 Setting up integrated learning system...")
            self.components['learning_config'] = LearningConfigManager()
            self.components['learning_monitor'] = LearningMonitor()
            self.components['integrated_learning'] = IntegratedLearningSystem(
                self.components['supabase_manager'],
                {'llm_client': self.components['llm_client']}
            )
            
            logger.info("✅ All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            return False
    
    async def setup_data_flow(self):
        """Setup the data flow connections between components"""
        logger.info("🔗 Setting up data flow connections...")
        
        # WebSocket → Raw Data Intelligence
        async def market_data_callback(data: Dict[str, Any]):
            """Process incoming market data through the pipeline"""
            try:
                logger.info(f"📈 Processing market data: {data['symbol']} @ {data['close']}")
                
                # Store market data
                await self.components['market_data_processor'].process_ohlcv_data(data)
                
                # Trigger raw data analysis
                await self.components['raw_data_agent']._analyze_raw_data_enhanced(data)
                
                # Check for new strands and trigger CIL processing
                await self._trigger_cil_processing()
                
            except Exception as e:
                logger.error(f"Error processing market data: {e}")
        
        # Set the callback
        self.components['websocket_client'].set_data_callback(market_data_callback)
        
        logger.info("✅ Data flow connections established")
    
    async def _trigger_cil_processing(self):
        """Trigger CIL processing when new strands are available"""
        try:
            # Get recent strands
            recent_strands = await self.components['supabase_manager'].get_recent_strands(
                limit=20, 
                since=datetime.now(timezone.utc).replace(second=0, microsecond=0)
            )
            
            if not recent_strands:
                return
            
            logger.info(f"🎯 Processing {len(recent_strands)} recent strands through CIL...")
            
            # Process through CIL pipeline
            agent_outputs = await self.components['input_processor'].process_agent_outputs(
                recent_strands, 
                {'market_context': 'live_trading'}
            )
            
            if agent_outputs:
                logger.info(f"📋 Generated {len(agent_outputs)} agent outputs")
                
                # Generate trading plan drafts
                trading_drafts = await self.components['plan_composer']._compose_new_plans()
                
                if trading_drafts:
                    logger.info(f"📝 Created {len(trading_drafts)} trading plan drafts")
                    
                    # Orchestrate experiments
                    experiments = await self.components['experiment_engine'].orchestrate_experiments(
                        trading_drafts, 
                        {'market_context': 'live_trading'}
                    )
                    
                    if experiments:
                        logger.info(f"🧪 Orchestrated {len(experiments)} experiments")
                        
                        # Track predictions
                        for experiment in experiments:
                            await self.components['prediction_tracker'].track_prediction(experiment)
                        
                        logger.info("📊 Predictions being tracked...")
            
        except Exception as e:
            logger.error(f"Error in CIL processing: {e}")
    
    async def start_system(self):
        """Start the complete Alpha Detector system"""
        logger.info("🚀 Starting Alpha Detector System...")
        
        # Initialize components
        if not await self.initialize_components():
            logger.error("❌ Failed to initialize components")
            return False
        
        # Setup data flow
        await self.setup_data_flow()
        
        # Start learning system
        logger.info("🎓 Starting integrated learning system...")
        await self.components['integrated_learning'].start()
        
        # Start raw data intelligence agent
        logger.info("🧠 Starting Raw Data Intelligence Agent...")
        from llm_integration.agent_discovery_system import AgentDiscoverySystem
        discovery_system = AgentDiscoverySystem(self.components['supabase_manager'])
        await self.components['raw_data_agent'].start(discovery_system)
        
        # Connect to WebSocket and start data collection
        logger.info("📡 Connecting to Hyperliquid WebSocket...")
        connected = await self.components['websocket_client'].connect()
        if not connected:
            logger.error("❌ Failed to connect to WebSocket")
            return False
        
        await self.components['websocket_client'].subscribe_to_market_data()
        
        # Start the main data collection loop
        self.is_running = True
        logger.info("✅ Alpha Detector System is now running!")
        logger.info("📊 Monitoring market data and generating trading insights...")
        
        try:
            # Start WebSocket listener
            await self.components['websocket_client'].listen_for_data()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully shutdown the system"""
        if not self.is_running:
            return
            
        logger.info("🛑 Shutting down Alpha Detector System...")
        self.is_running = False
        
        try:
            # Stop WebSocket
            if 'websocket_client' in self.components:
                await self.components['websocket_client'].disconnect()
            
            # Stop raw data agent
            if 'raw_data_agent' in self.components:
                await self.components['raw_data_agent'].stop()
            
            # Stop learning system
            if 'integrated_learning' in self.components:
                await self.components['integrated_learning'].stop()
            
            logger.info("✅ Alpha Detector System shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

async def main():
    """Main entry point"""
    orchestrator = AlphaDetectorOrchestrator()
    await orchestrator.start_system()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
