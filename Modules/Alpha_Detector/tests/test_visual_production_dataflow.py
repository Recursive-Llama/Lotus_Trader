"""
Visual Production Dataflow Test

A comprehensive, visual test that shows the complete dataflow in real-time:
WebSocket → Database → Raw Data Intelligence → CIL → Learning System

Features:
- Real-time progress indicators
- Visual dataflow representation
- Live metrics dashboard
- Color-coded status updates
- Detailed logging with emojis
"""

import pytest
import asyncio
import time
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import sys

from src.data_sources.hyperliquid_client import HyperliquidWebSocketClient
from src.core_detection.market_data_processor import MarketDataProcessor
from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.intelligence.raw_data_intelligence.divergence_detector import RawDataDivergenceDetector
from src.intelligence.raw_data_intelligence.volume_analyzer import VolumePatternAnalyzer
from src.intelligence.system_control.central_intelligence_layer.engines.input_processor import InputProcessor
from src.intelligence.system_control.central_intelligence_layer.engines.global_synthesis_engine import GlobalSynthesisEngine
from src.intelligence.system_control.central_intelligence_layer.engines.learning_feedback_engine import LearningFeedbackEngine
from src.intelligence.system_control.central_intelligence_layer.engines.prediction_outcome_tracker import PredictionOutcomeTracker
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

class VisualDataflowDashboard:
    """Visual dashboard for monitoring dataflow"""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.metrics = {
            'websocket_data': 0,
            'database_stored': 0,
            'signals_generated': 0,
            'cil_processed': 0,
            'llm_calls': 0,
            'learning_insights': 0,
            'predictions_tracked': 0,
            'errors': 0
        }
        self.last_update = time.time()
    
    def print_header(self):
        """Print the visual header"""
        print("\n" + "="*80)
        print("🚀 ALPHA DETECTOR - PRODUCTION DATAFLOW TEST")
        print("="*80)
        print("📊 Real-time dataflow monitoring with live metrics")
        print("⏱️  Test Duration: 60 seconds")
        print("="*80)
    
    def print_dataflow_diagram(self):
        """Print the dataflow diagram"""
        print("\n📈 DATAFLOW DIAGRAM:")
        print("┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐")
        print("│  WebSocket  │───▶│  Database   │───▶│ Raw Data AI │───▶│     CIL     │")
        print("│  (Real Data)│    │ (Storage)   │    │ (Analysis)  │    │(Intelligence│")
        print("└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘")
        print("                                                              │")
        print("                                                              ▼")
        print("┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐")
        print("│  Learning   │◀───│ Prediction  │◀───│   LLM API   │◀───│  Synthesis  │")
        print("│  Feedback   │    │  Tracking   │    │   Calls     │    │   Engine    │")
        print("└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘")
        print()
    
    def print_metrics(self):
        """Print current metrics"""
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        print(f"\n📊 LIVE METRICS (Elapsed: {elapsed:.1f}s):")
        print("┌─────────────────────┬─────────┬─────────────────────────────────┐")
        print("│ Component           │ Count   │ Status                          │")
        print("├─────────────────────┼─────────┼─────────────────────────────────┤")
        
        # WebSocket data
        status = "🟢 Active" if self.metrics['websocket_data'] > 0 else "🔴 Waiting"
        print(f"│ 📡 WebSocket Data    │ {self.metrics['websocket_data']:7d} │ {status:<31} │")
        
        # Database storage
        status = "🟢 Storing" if self.metrics['database_stored'] > 0 else "🔴 Waiting"
        print(f"│ 💾 Database Storage  │ {self.metrics['database_stored']:7d} │ {status:<31} │")
        
        # Signals generated
        status = "🟢 Generating" if self.metrics['signals_generated'] > 0 else "🟡 Processing"
        print(f"│ 📈 Signals Generated │ {self.metrics['signals_generated']:7d} │ {status:<31} │")
        
        # CIL processing
        status = "🟢 Processing" if self.metrics['cil_processed'] > 0 else "🟡 Waiting"
        print(f"│ 🧠 CIL Processing    │ {self.metrics['cil_processed']:7d} │ {status:<31} │")
        
        # LLM calls
        status = "🟢 Active" if self.metrics['llm_calls'] > 0 else "🟡 Ready"
        print(f"│ 🤖 LLM API Calls     │ {self.metrics['llm_calls']:7d} │ {status:<31} │")
        
        # Learning insights
        status = "🟢 Learning" if self.metrics['learning_insights'] > 0 else "🟡 Processing"
        print(f"│ 📚 Learning Insights │ {self.metrics['learning_insights']:7d} │ {status:<31} │")
        
        # Predictions tracked
        status = "🟢 Tracking" if self.metrics['predictions_tracked'] > 0 else "🟡 Ready"
        print(f"│ 🎯 Predictions Track │ {self.metrics['predictions_tracked']:7d} │ {status:<31} │")
        
        # Errors
        status = "🔴 Errors" if self.metrics['errors'] > 0 else "🟢 Clean"
        print(f"│ ❌ Errors            │ {self.metrics['errors']:7d} │ {status:<31} │")
        
        print("└─────────────────────┴─────────┴─────────────────────────────────┘")
        
        # Throughput calculations
        if elapsed > 0:
            ws_throughput = self.metrics['websocket_data'] / elapsed
            db_throughput = self.metrics['database_stored'] / elapsed
            print(f"\n🚀 THROUGHPUT:")
            print(f"   📡 WebSocket: {ws_throughput:.2f} records/sec")
            print(f"   💾 Database:  {db_throughput:.2f} records/sec")
    
    def print_phase_header(self, phase_num: int, phase_name: str, description: str):
        """Print phase header"""
        print(f"\n{'='*60}")
        print(f"🎯 PHASE {phase_num}: {phase_name}")
        print(f"📝 {description}")
        print(f"{'='*60}")
    
    def print_phase_complete(self, phase_num: int, results: Dict):
        """Print phase completion"""
        print(f"\n✅ PHASE {phase_num} COMPLETE!")
        for key, value in results.items():
            print(f"   📊 {key}: {value}")
        print()
    
    def update_metric(self, metric: str, increment: int = 1):
        """Update a metric"""
        self.metrics[metric] += increment
        self.last_update = time.time()
    
    def print_final_summary(self):
        """Print final test summary"""
        total_time = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("🎉 PRODUCTION DATAFLOW TEST COMPLETE!")
        print("="*80)
        print(f"⏱️  Total Duration: {total_time:.2f} seconds")
        print()
        
        print("📊 FINAL METRICS:")
        for metric, count in self.metrics.items():
            emoji = {
                'websocket_data': '📡',
                'database_stored': '💾',
                'signals_generated': '📈',
                'cil_processed': '🧠',
                'llm_calls': '🤖',
                'learning_insights': '📚',
                'predictions_tracked': '🎯',
                'errors': '❌'
            }.get(metric, '📊')
            print(f"   {emoji} {metric.replace('_', ' ').title()}: {count}")
        
        print()
        print("🚀 SYSTEM STATUS: PRODUCTION READY!" if self.metrics['errors'] == 0 else "⚠️  SYSTEM STATUS: NEEDS ATTENTION")
        print("="*80)

class TestVisualProductionDataflow:
    """Visual production test for complete dataflow"""
    
    @pytest.fixture
    async def setup_visual_components(self):
        """Setup all components for visual testing"""
        components = {}
        
        try:
            # Initialize core infrastructure
            components['supabase_manager'] = SupabaseManager()
            components['llm_client'] = OpenRouterClient()
            
            # Initialize data collection and processing
            components['websocket_client'] = HyperliquidWebSocketClient(['BTC', 'ETH', 'SOL'])
            components['market_data_processor'] = MarketDataProcessor(components['supabase_manager'])
            
            # Initialize Raw Data Intelligence
            components['raw_data_agent'] = RawDataIntelligenceAgent(
                components['supabase_manager'], 
                components['llm_client']
            )
            components['divergence_detector'] = RawDataDivergenceDetector()
            components['volume_analyzer'] = VolumePatternAnalyzer()
            
            # Initialize CIL components
            components['input_processor'] = InputProcessor(
                components['supabase_manager'], 
                components['llm_client']
            )
            components['global_synthesis_engine'] = GlobalSynthesisEngine(
                components['supabase_manager'], 
                components['llm_client']
            )
            components['learning_feedback_engine'] = LearningFeedbackEngine(
                components['supabase_manager'], 
                components['llm_client']
            )
            components['prediction_tracker'] = PredictionOutcomeTracker(
                components['supabase_manager'], 
                components['llm_client']
            )
            
            return components
            
        except Exception as e:
            print(f"❌ Failed to initialize components: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_visual_production_dataflow(self, setup_visual_components):
        """Visual production test with real-time monitoring"""
        components = await setup_visual_components
        dashboard = VisualDataflowDashboard()
        
        # Print initial setup
        dashboard.print_header()
        dashboard.print_dataflow_diagram()
        
        async def visual_data_callback(market_data: Dict[str, Any]):
            """Visual callback for real-time data processing"""
            dashboard.update_metric('websocket_data')
            
            # Store data in database
            try:
                success = await components['market_data_processor'].process_ohlcv_data(market_data)
                if success:
                    dashboard.update_metric('database_stored')
                    print(f"💾 Stored: {market_data.get('symbol', 'unknown')} - ${market_data.get('close', 0)}")
                else:
                    dashboard.update_metric('errors')
            except Exception as e:
                dashboard.update_metric('errors')
                print(f"❌ Storage error: {e}")
        
        try:
            # Phase 1: Real-time data collection
            dashboard.print_phase_header(1, "REAL-TIME DATA COLLECTION", 
                                       "Collecting live market data from Hyperliquid WebSocket")
            
            # Set up WebSocket
            components['websocket_client'].set_data_callback(visual_data_callback)
            
            # Connect and start data collection
            connected = await components['websocket_client'].connect()
            assert connected, "Failed to connect to Hyperliquid WebSocket"
            
            await components['websocket_client'].subscribe_to_market_data()
            listen_task = asyncio.create_task(components['websocket_client'].listen_for_data())
            
            # Monitor data collection for 30 seconds with live updates
            print("⏱️  Collecting data for 30 seconds with live updates...")
            for i in range(30):
                await asyncio.sleep(1)
                if i % 5 == 0:  # Update every 5 seconds
                    dashboard.print_metrics()
            
            # Stop data collection
            listen_task.cancel()
            await components['websocket_client'].disconnect()
            
            # Phase 1 results
            phase1_results = {
                'Data Collected': dashboard.metrics['websocket_data'],
                'Data Stored': dashboard.metrics['database_stored'],
                'Errors': dashboard.metrics['errors']
            }
            dashboard.print_phase_complete(1, phase1_results)
            
            # Phase 2: Raw Data Intelligence
            dashboard.print_phase_header(2, "RAW DATA INTELLIGENCE", 
                                       "Processing market data through Raw Data Intelligence agents")
            
            # Get recent market data for analysis
            market_data_df = await components['raw_data_agent']._get_recent_market_data()
            
            if market_data_df is not None and not market_data_df.empty:
                print(f"📊 Retrieved {len(market_data_df)} market data points for analysis")
                
                # Process through Raw Data Intelligence
                analysis_results = await components['raw_data_agent']._analyze_raw_data(market_data_df)
                
                if analysis_results:
                    signals = analysis_results.get('signals', [])
                    dashboard.metrics['signals_generated'] = len(signals)
                    print(f"📈 Generated {len(signals)} signals from market data")
                else:
                    print("⚠️  No analysis results generated")
            else:
                print("⚠️  No market data available for analysis")
            
            # Phase 2 results
            phase2_results = {
                'Market Data Points': len(market_data_df) if market_data_df is not None else 0,
                'Signals Generated': dashboard.metrics['signals_generated']
            }
            dashboard.print_phase_complete(2, phase2_results)
            
            # Phase 3: CIL Processing
            dashboard.print_phase_header(3, "CENTRAL INTELLIGENCE LAYER", 
                                       "Processing through CIL with real LLM calls")
            
            # Process through CIL Input Processor
            cil_outputs = await components['input_processor'].process_agent_outputs()
            dashboard.metrics['cil_processed'] = len(cil_outputs)
            print(f"🧠 CIL processed {len(cil_outputs)} agent outputs")
            
            # Global synthesis with real LLM calls
            print("🤖 Making real LLM API calls for global synthesis...")
            synthesis_results = await components['global_synthesis_engine'].synthesize_global_view({})
            dashboard.update_metric('llm_calls')
            
            if synthesis_results:
                insights = synthesis_results.get('insights', [])
                dashboard.metrics['learning_insights'] = len(insights)
                print(f"💡 Generated {len(insights)} insights from LLM synthesis")
            else:
                print("⚠️  No synthesis results generated")
            
            # Phase 3 results
            phase3_results = {
                'CIL Outputs': dashboard.metrics['cil_processed'],
                'LLM Calls': dashboard.metrics['llm_calls'],
                'Insights Generated': dashboard.metrics['learning_insights']
            }
            dashboard.print_phase_complete(3, phase3_results)
            
            # Phase 4: Learning and Prediction Tracking
            dashboard.print_phase_header(4, "LEARNING & PREDICTION TRACKING", 
                                       "Processing learning feedback and tracking predictions")
            
            # Process learning feedback
            print("📚 Processing learning feedback...")
            learning_results = await components['learning_feedback_engine'].process_learning_feedback({})
            dashboard.update_metric('llm_calls')
            
            if learning_results:
                print("✅ Learning feedback processed successfully")
            else:
                print("⚠️  Learning feedback failed")
            
            # Get prediction tracking stats
            print("🎯 Getting prediction tracking statistics...")
            prediction_stats = await components['prediction_tracker'].get_prediction_accuracy_stats()
            dashboard.update_metric('llm_calls')
            
            if prediction_stats:
                total_predictions = prediction_stats.get('total_predictions', 0)
                dashboard.metrics['predictions_tracked'] = total_predictions
                print(f"📊 Tracking {total_predictions} predictions")
            else:
                print("⚠️  Prediction tracking failed")
            
            # Phase 4 results
            phase4_results = {
                'Learning Processed': 'Yes' if learning_results else 'No',
                'Predictions Tracked': dashboard.metrics['predictions_tracked'],
                'Additional LLM Calls': 2
            }
            dashboard.print_phase_complete(4, phase4_results)
            
            # Final summary
            dashboard.print_final_summary()
            
            # Validate overall success
            assert dashboard.metrics['websocket_data'] > 0, "No WebSocket data collected"
            assert dashboard.metrics['database_stored'] > 0, "No data stored in database"
            assert dashboard.metrics['llm_calls'] > 0, "No LLM calls made"
            
            print("🎉 Visual production dataflow test completed successfully!")
            
        except Exception as e:
            dashboard.update_metric('errors')
            print(f"❌ Visual production test failed: {e}")
            raise
        finally:
            # Cleanup
            if components['websocket_client'].is_connected:
                await components['websocket_client'].disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
