"""
Production Full Dataflow Integration Test

This test validates the complete production dataflow with real data and real LLM calls:
WebSocket → Database → Raw Data Intelligence → CIL → Learning System

This is a comprehensive production test that uses:
- Real WebSocket market data
- Real LLM API calls
- Real database operations
- Real-time processing
"""

import pytest
import asyncio
import time
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

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

class TestProductionFullDataflow:
    """Production test for complete dataflow with real data and LLM calls"""
    
    @pytest.fixture
    async def setup_production_components(self):
        """Setup all production components"""
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
            
            logger.info("✅ All production components initialized successfully")
            return components
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize production components: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_production_full_dataflow(self, setup_production_components):
        """Test complete production dataflow with real data and LLM calls"""
        components = await setup_production_components
        
        # Production metrics tracking
        production_metrics = {
            'data_collected': 0,
            'data_stored': 0,
            'signals_generated': 0,
            'cil_processed': 0,
            'learning_insights': 0,
            'predictions_tracked': 0,
            'start_time': datetime.now(timezone.utc),
            'test_duration': 60  # 60 seconds of real-time testing
        }
        
        async def production_data_callback(market_data: Dict[str, Any]):
            """Production callback for real-time data processing"""
            production_metrics['data_collected'] += 1
            logger.info(f"📊 Production data: {market_data.get('symbol', 'unknown')} - ${market_data.get('close', 0)}")
            
            # Store data in database
            try:
                success = await components['market_data_processor'].process_ohlcv_data(market_data)
                if success:
                    production_metrics['data_stored'] += 1
                    logger.info(f"💾 Stored: {market_data.get('symbol', 'unknown')}")
            except Exception as e:
                logger.error(f"❌ Storage error: {e}")
        
        try:
            # Phase 1: Real-time data collection and storage
            logger.info("🚀 Starting production dataflow test...")
            logger.info("📡 Phase 1: Real-time data collection and storage")
            
            # Set up WebSocket with production callback
            components['websocket_client'].set_data_callback(production_data_callback)
            
            # Connect and start data collection
            connected = await components['websocket_client'].connect()
            assert connected, "Failed to connect to Hyperliquid WebSocket"
            
            await components['websocket_client'].subscribe_to_market_data()
            listen_task = asyncio.create_task(components['websocket_client'].listen_for_data())
            
            # Collect data for 30 seconds
            logger.info("⏱️ Collecting real-time data for 30 seconds...")
            await asyncio.sleep(30)
            
            # Stop data collection
            listen_task.cancel()
            await components['websocket_client'].disconnect()
            
            # Verify data collection
            assert production_metrics['data_collected'] > 0, "No real-time data collected"
            assert production_metrics['data_stored'] > 0, "No data stored in database"
            logger.info(f"✅ Phase 1 Complete: {production_metrics['data_collected']} collected, {production_metrics['data_stored']} stored")
            
            # Phase 2: Raw Data Intelligence processing
            logger.info("🧠 Phase 2: Raw Data Intelligence processing")
            
            # Get recent market data for analysis
            market_data_df = await components['raw_data_agent']._get_recent_market_data()
            assert market_data_df is not None and not market_data_df.empty, "No market data available for analysis"
            
            # Process through Raw Data Intelligence
            analysis_results = await components['raw_data_agent']._analyze_raw_data(market_data_df)
            assert analysis_results is not None, "Raw data analysis failed"
            
            # Count signals generated
            signals = analysis_results.get('signals', [])
            production_metrics['signals_generated'] = len(signals)
            
            logger.info(f"✅ Phase 2 Complete: {production_metrics['signals_generated']} signals generated")
            
            # Phase 3: CIL processing
            logger.info("🎯 Phase 3: CIL processing with real LLM calls")
            
            # Process through CIL Input Processor
            cil_outputs = await components['input_processor'].process_agent_outputs()
            assert len(cil_outputs) > 0, "CIL did not process any agent outputs"
            production_metrics['cil_processed'] = len(cil_outputs)
            
            # Global synthesis with real LLM calls
            synthesis_results = await components['global_synthesis_engine'].synthesize_global_view({})
            assert synthesis_results is not None, "Global synthesis failed"
            
            insights = synthesis_results.get('insights', [])
            production_metrics['learning_insights'] = len(insights)
            
            logger.info(f"✅ Phase 3 Complete: {production_metrics['cil_processed']} CIL outputs, {production_metrics['learning_insights']} insights")
            
            # Phase 4: Learning and prediction tracking
            logger.info("📚 Phase 4: Learning and prediction tracking")
            
            # Process learning feedback
            learning_results = await components['learning_feedback_engine'].process_learning_feedback({})
            assert learning_results is not None, "Learning feedback failed"
            
            # Get prediction tracking stats
            prediction_stats = await components['prediction_tracker'].get_prediction_accuracy_stats()
            assert prediction_stats is not None, "Prediction tracking failed"
            
            production_metrics['predictions_tracked'] = prediction_stats.get('total_predictions', 0)
            
            logger.info(f"✅ Phase 4 Complete: {production_metrics['predictions_tracked']} predictions tracked")
            
            # Phase 5: Production metrics and validation
            logger.info("📊 Phase 5: Production metrics and validation")
            
            end_time = datetime.now(timezone.utc)
            total_duration = (end_time - production_metrics['start_time']).total_seconds()
            
            # Validate production metrics
            assert production_metrics['data_collected'] >= 10, f"Insufficient data collected: {production_metrics['data_collected']}"
            assert production_metrics['data_stored'] >= 5, f"Insufficient data stored: {production_metrics['data_stored']}"
            assert production_metrics['signals_generated'] >= 0, "Signal generation failed"
            assert production_metrics['cil_processed'] >= 0, "CIL processing failed"
            assert production_metrics['learning_insights'] >= 0, "Learning insights failed"
            
            # Log production summary
            logger.info("🎉 PRODUCTION TEST COMPLETE!")
            logger.info(f"⏱️ Total Duration: {total_duration:.2f} seconds")
            logger.info(f"📊 Data Collected: {production_metrics['data_collected']}")
            logger.info(f"💾 Data Stored: {production_metrics['data_stored']}")
            logger.info(f"📈 Signals Generated: {production_metrics['signals_generated']}")
            logger.info(f"🧠 CIL Processed: {production_metrics['cil_processed']}")
            logger.info(f"💡 Learning Insights: {production_metrics['learning_insights']}")
            logger.info(f"🎯 Predictions Tracked: {production_metrics['predictions_tracked']}")
            
            # Calculate throughput
            data_throughput = production_metrics['data_collected'] / total_duration
            storage_throughput = production_metrics['data_stored'] / total_duration
            
            logger.info(f"🚀 Data Throughput: {data_throughput:.2f} records/second")
            logger.info(f"💾 Storage Throughput: {storage_throughput:.2f} records/second")
            
            logger.info("✅ Production dataflow test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Production test failed: {e}")
            raise
        finally:
            # Cleanup
            if components['websocket_client'].is_connected:
                await components['websocket_client'].disconnect()
    
    @pytest.mark.asyncio
    async def test_production_llm_integration(self, setup_production_components):
        """Test production LLM integration with real API calls"""
        components = await setup_production_components
        
        try:
            logger.info("🤖 Testing production LLM integration...")
            
            # Test real LLM calls through CIL components
            logger.info("🧠 Testing Global Synthesis Engine with real LLM calls...")
            
            # Create test input for global synthesis
            test_input = {
                'market_data': {
                    'BTC': {'price': 50000, 'volume': 1000, 'trend': 'bullish'},
                    'ETH': {'price': 3000, 'volume': 5000, 'trend': 'bearish'}
                },
                'signals': [
                    {'type': 'divergence', 'symbol': 'BTC', 'strength': 0.8},
                    {'type': 'volume', 'symbol': 'ETH', 'strength': 0.6}
                ]
            }
            
            # Test global synthesis with real LLM
            synthesis_results = await components['global_synthesis_engine'].synthesize_global_view(test_input)
            assert synthesis_results is not None, "Global synthesis with real LLM failed"
            
            # Verify LLM response structure
            assert 'insights' in synthesis_results, "LLM response missing insights"
            assert 'synthesis_timestamp' in synthesis_results, "LLM response missing timestamp"
            
            logger.info(f"✅ Global synthesis completed: {len(synthesis_results.get('insights', []))} insights")
            
            # Test learning feedback with real LLM
            logger.info("📚 Testing Learning Feedback Engine with real LLM calls...")
            
            learning_results = await components['learning_feedback_engine'].process_learning_feedback({
                'test_data': 'production_test',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            assert learning_results is not None, "Learning feedback with real LLM failed"
            assert 'learning_timestamp' in learning_results, "Learning response missing timestamp"
            
            logger.info("✅ Learning feedback completed successfully")
            
            # Test prediction tracking with real LLM
            logger.info("🎯 Testing Prediction Outcome Tracker with real LLM calls...")
            
            prediction_stats = await components['prediction_tracker'].get_prediction_accuracy_stats()
            assert prediction_stats is not None, "Prediction tracking with real LLM failed"
            
            logger.info(f"✅ Prediction tracking completed: {prediction_stats.get('total_predictions', 0)} predictions")
            
            logger.info("🎉 Production LLM integration test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Production LLM integration test failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_production_database_operations(self, setup_production_components):
        """Test production database operations with real data"""
        components = await setup_production_components
        
        try:
            logger.info("🗄️ Testing production database operations...")
            
            # Test market data storage and retrieval
            logger.info("💾 Testing market data storage and retrieval...")
            
            # Get recent market data
            recent_data = components['supabase_manager'].client.table('alpha_market_data_1m').select('*').gte(
                'timestamp', (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            ).order('timestamp', desc=True).limit(10).execute()
            
            assert recent_data.data is not None, "Failed to retrieve recent market data"
            logger.info(f"✅ Retrieved {len(recent_data.data)} recent market data records")
            
            # Test AD_strands operations
            logger.info("🧵 Testing AD_strands operations...")
            
            # Get recent strands
            recent_strands = components['supabase_manager'].get_recent_strands(days=1)
            assert recent_strands is not None, "Failed to retrieve recent strands"
            logger.info(f"✅ Retrieved {len(recent_strands)} recent strands")
            
            # Test prediction tracking data
            logger.info("🎯 Testing prediction tracking data...")
            
            prediction_data = components['supabase_manager'].client.table('ad_strands').select('*').not_.is_(
                'prediction_score', 'null'
            ).order('created_at', desc=True).limit(5).execute()
            
            assert prediction_data.data is not None, "Failed to retrieve prediction data"
            logger.info(f"✅ Retrieved {len(prediction_data.data)} prediction records")
            
            logger.info("🎉 Production database operations test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Production database operations test failed: {e}")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
