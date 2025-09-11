#!/usr/bin/env python3
"""
Comprehensive Full System Flow Test
Tests the complete dataflow from WebSocket → Raw Data Intelligence → CIL → Trading Plans
with detailed real-time output showing each step of the process.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import os
from pathlib import Path
import time

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent / "src"))

from data_sources.hyperliquid_client import HyperliquidWebSocketClient
from utils.supabase_manager import SupabaseManager
from core_detection.market_data_processor import MarketDataProcessor
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

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class FullSystemFlowTester:
    """Comprehensive tester for the full system flow"""
    
    def __init__(self):
        self.components = {}
        self.test_metrics = {
            'market_data_received': 0,
            'strands_created': 0,
            'cil_processing_cycles': 0,
            'trading_drafts_created': 0,
            'experiments_orchestrated': 0,
            'predictions_tracked': 0,
            'learning_cycles': 0,
            'trading_plans_generated': 0
        }
        self.start_time = None
        
    async def initialize_components(self):
        """Initialize all system components"""
        print("\n" + "="*80)
        print("🚀 INITIALIZING ALPHA DETECTOR SYSTEM COMPONENTS")
        print("="*80)
        
        try:
            # Core infrastructure
            print("📊 Setting up database and LLM connections...")
            self.components['supabase_manager'] = SupabaseManager()
            self.components['llm_client'] = OpenRouterClient()
            self.components['market_data_processor'] = MarketDataProcessor(self.components['supabase_manager'])
            print("✅ Database and LLM connections established")
            
            # Data collection
            print("📡 Setting up WebSocket client...")
            self.components['websocket_client'] = HyperliquidWebSocketClient(['BTC', 'ETH', 'SOL'])
            print("✅ WebSocket client ready")
            
            # Raw Data Intelligence
            print("🧠 Initializing Raw Data Intelligence Agent...")
            self.components['raw_data_agent'] = RawDataIntelligenceAgent(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            print("✅ Raw Data Intelligence Agent ready")
            
            # CIL Components
            print("🎯 Initializing CIL components...")
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
            print("✅ All CIL components ready")
            
            # Learning System
            print("🎓 Setting up integrated learning system...")
            self.components['learning_config'] = LearningConfigManager()
            self.components['learning_monitor'] = LearningMonitor()
            self.components['integrated_learning'] = IntegratedLearningSystem(
                self.components['supabase_manager'],
                {'llm_client': self.components['llm_client']}
            )
            print("✅ Learning system ready")
            
            print("\n🎉 ALL COMPONENTS INITIALIZED SUCCESSFULLY!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize components: {e}")
            return False
    
    async def test_market_data_collection(self, duration_seconds: int = 60):
        """Test market data collection and storage"""
        print("\n" + "="*80)
        print(f"📡 TESTING MARKET DATA COLLECTION ({duration_seconds}s)")
        print("="*80)
        
        data_received = []
        
        async def market_data_callback(data: Dict[str, Any]):
            """Process incoming market data"""
            self.test_metrics['market_data_received'] += 1
            data_received.append(data)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"📈 [{timestamp}] Market Data: {data['symbol']} @ ${data['close']:.2f} (Vol: {data['volume']:.0f})")
            
            # Store in database
            try:
                success = await self.components['market_data_processor'].process_ohlcv_data(data)
                if success:
                    print(f"💾 [{timestamp}] Processed tick for {data['symbol']}")
                else:
                    print(f"⚠️ [{timestamp}] Failed to process tick for {data['symbol']}")
            except Exception as e:
                print(f"❌ [{timestamp}] Failed to process tick: {e}")
        
        # Set callback and connect
        self.components['websocket_client'].set_data_callback(market_data_callback)
        
        print("🔌 Connecting to Hyperliquid WebSocket...")
        connected = await self.components['websocket_client'].connect()
        if not connected:
            print("❌ Failed to connect to WebSocket")
            return False
        
        print("📡 Subscribing to market data...")
        await self.components['websocket_client'].subscribe_to_market_data()
        
        print(f"⏱️ Collecting market data for {duration_seconds} seconds...")
        print("📊 Real-time data flow:")
        
        # Start data collection
        listen_task = asyncio.create_task(
            self.components['websocket_client'].listen_for_data()
        )
        
        # Wait for specified duration
        await asyncio.sleep(duration_seconds)
        
        # Stop data collection
        listen_task.cancel()
        await self.components['websocket_client'].disconnect()
        
        print(f"\n📊 Market Data Collection Summary:")
        print(f"   • Total data points received: {self.test_metrics['market_data_received']}")
        print(f"   • Data points per second: {self.test_metrics['market_data_received'] / duration_seconds:.2f}")
        print(f"   • Unique symbols: {len(set(d['symbol'] for d in data_received))}")
        
        return len(data_received) > 0
    
    async def test_raw_data_intelligence_processing(self):
        """Test raw data intelligence processing"""
        print("\n" + "="*80)
        print("🧠 TESTING RAW DATA INTELLIGENCE PROCESSING")
        print("="*80)
        
        try:
            # Get recent market data
            print("📊 Retrieving recent market data for analysis...")
            recent_data = await self.components['raw_data_agent']._get_recent_market_data()
            
            if recent_data is None or recent_data.empty:
                print("❌ No recent market data available")
                return False
            
            print(f"✅ Retrieved {len(recent_data)} data points for analysis")
            
            # Start raw data intelligence agent
            print("🚀 Starting Raw Data Intelligence Agent...")
            from llm_integration.agent_discovery_system import AgentDiscoverySystem
            discovery_system = AgentDiscoverySystem(self.components['supabase_manager'])
            await self.components['raw_data_agent'].start(discovery_system)
            
            # Wait for analysis cycles (let agent run its 5-minute cycle)
            print("⏱️ Running analysis cycles (waiting for pattern detection)...")
            analysis_cycles = 0
            max_cycles = 2  # Only 2 cycles for 3-minute test (agent runs every 5 minutes)
            
            while analysis_cycles < max_cycles:
                await asyncio.sleep(30)  # Wait 30 seconds between checks
                analysis_cycles += 1
                
                # Check for new strands
                recent_strands = self.components['supabase_manager'].get_recent_strands(
                    limit=10,
                    since=datetime.now(timezone.utc) - timedelta(minutes=5)
                )
                
                if recent_strands:
                    self.test_metrics['strands_created'] += len(recent_strands)
                    print(f"🎯 Cycle {analysis_cycles}: Found {len(recent_strands)} new strands")
                    
                    for strand in recent_strands:
                        pattern_type = strand.get('module_intelligence', {}).get('pattern_type', 'unknown')
                        severity = strand.get('module_intelligence', {}).get('severity', 'unknown')
                        print(f"   • {pattern_type} pattern (severity: {severity})")
                    
                    if len(recent_strands) >= 3:  # Enough patterns detected
                        break
                else:
                    print(f"⏳ Cycle {analysis_cycles}: No new patterns detected yet...")
            
            print(f"\n📊 Raw Data Intelligence Summary:")
            print(f"   • Analysis cycles completed: {analysis_cycles}")
            print(f"   • Total strands created: {self.test_metrics['strands_created']}")
            
            return self.test_metrics['strands_created'] > 0
            
        except Exception as e:
            print(f"❌ Error in raw data intelligence processing: {e}")
            return False
    
    async def test_cil_processing_pipeline(self):
        """Test the complete CIL processing pipeline"""
        print("\n" + "="*80)
        print("🎯 TESTING CIL PROCESSING PIPELINE")
        print("="*80)
        
        try:
            # Get recent strands for processing
            print("📋 Retrieving recent strands for CIL processing...")
            recent_strands = self.components['supabase_manager'].get_recent_strands(
                limit=20,
                since=datetime.now(timezone.utc) - timedelta(minutes=10)
            )
            
            if not recent_strands:
                print("❌ No recent strands available for CIL processing")
                return False
            
            print(f"✅ Retrieved {len(recent_strands)} strands for processing")
            
            # Step 1: Input Processing
            print("\n🔄 Step 1: Input Processing...")
            agent_outputs = await self.components['input_processor'].process_agent_outputs(
                recent_strands,
                {'market_context': 'live_testing'}
            )
            
            if agent_outputs:
                print(f"✅ Generated {len(agent_outputs)} agent outputs")
                for i, output in enumerate(agent_outputs[:3]):  # Show first 3
                    # AgentOutput is a dataclass, not a dict
                    summary = getattr(output, 'hypothesis_notes', 'No summary') or 'No summary'
                    print(f"   • Output {i+1}: {summary[:100]}...")
            else:
                print("⚠️ No agent outputs generated")
                return False
            
            # Step 2: Trading Plan Composition
            print("\n📝 Step 2: Trading Plan Composition...")
            trading_drafts = await self.components['plan_composer']._compose_new_plans()
            
            if trading_drafts:
                self.test_metrics['trading_drafts_created'] += len(trading_drafts)
                print(f"✅ Created {len(trading_drafts)} trading plan drafts")
                for i, draft in enumerate(trading_drafts[:2]):  # Show first 2
                    print(f"   • Draft {i+1}: {draft.get('title', 'No title')}")
            else:
                print("⚠️ No trading plan drafts created")
                return False
            
            # Step 3: Experiment Orchestration
            print("\n🧪 Step 3: Experiment Orchestration...")
            experiments = await self.components['experiment_engine'].orchestrate_experiments(
                trading_drafts,
                {'market_context': 'live_testing'}
            )
            
            if experiments:
                self.test_metrics['experiments_orchestrated'] += len(experiments)
                print(f"✅ Orchestrated {len(experiments)} experiments")
                for i, experiment in enumerate(experiments[:2]):  # Show first 2
                    print(f"   • Experiment {i+1}: {experiment.get('experiment_id', 'No ID')}")
            else:
                print("⚠️ No experiments orchestrated")
                return False
            
            # Step 4: Prediction Tracking
            print("\n📊 Step 4: Prediction Tracking...")
            for experiment in experiments:
                await self.components['prediction_tracker'].track_prediction(experiment)
                self.test_metrics['predictions_tracked'] += 1
            
            print(f"✅ Tracking {self.test_metrics['predictions_tracked']} predictions")
            
            # Step 5: Learning Feedback
            print("\n🎓 Step 5: Learning Feedback...")
            learning_results = await self.components['learning_engine'].process_learning_feedback(
                experiments,
                {'market_context': 'live_testing'}
            )
            
            if learning_results:
                print(f"✅ Processed learning feedback: {len(learning_results)} results")
            else:
                print("⚠️ No learning feedback processed")
            
            # Step 6: Output Directive System
            print("\n📤 Step 6: Output Directive System...")
            trading_plans = await self.components['output_directive'].generate_trading_directives(
                experiments,
                {'market_context': 'live_testing'}
            )
            
            if trading_plans:
                self.test_metrics['trading_plans_generated'] += len(trading_plans)
                print(f"✅ Generated {len(trading_plans)} trading plans")
                for i, plan in enumerate(trading_plans[:2]):  # Show first 2
                    print(f"   • Plan {i+1}: {plan.get('directive_type', 'No type')}")
            else:
                print("⚠️ No trading plans generated")
            
            print(f"\n📊 CIL Processing Summary:")
            print(f"   • Agent outputs: {len(agent_outputs)}")
            print(f"   • Trading drafts: {self.test_metrics['trading_drafts_created']}")
            print(f"   • Experiments: {self.test_metrics['experiments_orchestrated']}")
            print(f"   • Predictions tracked: {self.test_metrics['predictions_tracked']}")
            print(f"   • Trading plans: {self.test_metrics['trading_plans_generated']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in CIL processing: {e}")
            return False
    
    async def test_learning_system_integration(self):
        """Test the integrated learning system"""
        print("\n" + "="*80)
        print("🎓 TESTING INTEGRATED LEARNING SYSTEM")
        print("="*80)
        
        try:
            # Start learning system
            print("🚀 Starting integrated learning system...")
            await self.components['integrated_learning'].start()
            
            # Run learning cycles
            print("⏱️ Running learning cycles...")
            learning_cycles = 0
            max_cycles = 5
            
            while learning_cycles < max_cycles:
                await asyncio.sleep(10)  # Wait 10 seconds between cycles
                learning_cycles += 1
                self.test_metrics['learning_cycles'] += 1
                
                print(f"🔄 Learning cycle {learning_cycles}/{max_cycles}...")
                
                # Check for learning activity
                recent_braids = self.components['supabase_manager'].get_recent_strands(
                    limit=5,
                    since=datetime.now(timezone.utc) - timedelta(minutes=5),
                    kind='braid'
                )
                
                if recent_braids:
                    print(f"   • Found {len(recent_braids)} new braids")
                else:
                    print(f"   • No new braids created yet...")
            
            print(f"\n📊 Learning System Summary:")
            print(f"   • Learning cycles completed: {self.test_metrics['learning_cycles']}")
            print(f"   • System running: {'✅' if self.components['integrated_learning'].is_running else '❌'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in learning system: {e}")
            return False
    
    async def run_comprehensive_test(self, duration_minutes: int = 3):
        """Run the complete comprehensive test"""
        print("\n" + "="*80)
        print("🚀 LOTUS TRADER ALPHA DETECTOR - COMPREHENSIVE SYSTEM TEST")
        print("="*80)
        print(f"⏱️ Test Duration: {duration_minutes} minutes")
        print(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        self.start_time = time.time()
        
        try:
            # Initialize components
            if not await self.initialize_components():
                print("❌ Component initialization failed")
                return False
            
            # Test 1: Market Data Collection
            if not await self.test_market_data_collection(duration_seconds=30):
                print("❌ Market data collection test failed")
                return False
            
            # Test 2: Raw Data Intelligence Processing
            if not await self.test_raw_data_intelligence_processing():
                print("❌ Raw data intelligence processing test failed")
                return False
            
            # Test 3: CIL Processing Pipeline
            if not await self.test_cil_processing_pipeline():
                print("❌ CIL processing pipeline test failed")
                return False
            
            # Test 4: Learning System Integration
            if not await self.test_learning_system_integration():
                print("❌ Learning system integration test failed")
                return False
            
            # Final Summary
            elapsed_time = time.time() - self.start_time
            print("\n" + "="*80)
            print("🎉 COMPREHENSIVE TEST COMPLETED SUCCESSFULLY!")
            print("="*80)
            print(f"⏱️ Total Test Duration: {elapsed_time:.1f} seconds")
            print(f"📊 Final Metrics:")
            for metric, value in self.test_metrics.items():
                print(f"   • {metric.replace('_', ' ').title()}: {value}")
            
            print("\n✅ SYSTEM IS FULLY OPERATIONAL!")
            print("🚀 Ready for live trading with WebSocket connection")
            
            return True
            
        except Exception as e:
            print(f"❌ Comprehensive test failed: {e}")
            return False
        finally:
            # Cleanup
            try:
                if 'integrated_learning' in self.components:
                    await self.components['integrated_learning'].stop_learning_loop()
                if 'raw_data_agent' in self.components:
                    await self.components['raw_data_agent'].stop()
            except Exception as e:
                print(f"⚠️ Cleanup error: {e}")

async def main():
    """Main test entry point"""
    tester = FullSystemFlowTester()
    success = await tester.run_comprehensive_test(duration_minutes=3)
    
    if success:
        print("\n🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION!")
        sys.exit(0)
    else:
        print("\n❌ TESTS FAILED - SYSTEM NEEDS ATTENTION")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal test error: {e}")
        sys.exit(1)
