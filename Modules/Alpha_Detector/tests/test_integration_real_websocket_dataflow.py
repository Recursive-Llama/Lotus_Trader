"""
Real WebSocket Dataflow Integration Test

This test uses real market data from Hyperliquid WebSocket to validate
the complete dataflow: WebSocket → Raw Data Intelligence → CIL → Learning
"""

import pytest
import asyncio
import time
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

from src.data_sources.hyperliquid_client import HyperliquidWebSocketClient
from src.intelligence.raw_data_intelligence.divergence_detector import RawDataDivergenceDetector
from src.intelligence.raw_data_intelligence.volume_analyzer import VolumePatternAnalyzer
from src.intelligence.raw_data_intelligence.cross_asset_analyzer import CrossAssetPatternAnalyzer
from src.intelligence.system_control.central_intelligence_layer.core.strategic_pattern_miner import StrategicPatternMiner
from src.intelligence.system_control.central_intelligence_layer.engines.input_processor import InputProcessor
from src.intelligence.system_control.central_intelligence_layer.engines.global_synthesis_engine import GlobalSynthesisEngine
from src.intelligence.system_control.central_intelligence_layer.engines.learning_feedback_engine import LearningFeedbackEngine
from src.intelligence.system_control.central_intelligence_layer.engines.prediction_outcome_tracker import PredictionOutcomeTracker
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

class TestRealWebSocketDataflow:
    """Test real dataflow with WebSocket market data"""
    
    @pytest.fixture
    async def setup_real_components(self):
        """Setup components for real dataflow testing"""
        components = {}
        
        try:
            # Initialize database and LLM client
            components['supabase_manager'] = SupabaseManager()
            components['llm_client'] = OpenRouterClient()
            
            # Initialize WebSocket client
            components['websocket_client'] = HyperliquidWebSocketClient(['BTC', 'ETH'])
            
            # Initialize Raw Data Intelligence components
            components['divergence_detector'] = RawDataDivergenceDetector()
            components['volume_analyzer'] = VolumePatternAnalyzer()
            components['cross_asset_analyzer'] = CrossAssetPatternAnalyzer()
            
            # Initialize CIL components
            components['strategic_pattern_miner'] = StrategicPatternMiner(
                components['supabase_manager'], 
                components['llm_client']
            )
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
            
            logger.info("✅ All components initialized successfully")
            return components
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_real_websocket_to_cil_dataflow(self, setup_real_components):
        """Test complete dataflow from real WebSocket data to CIL processing"""
        components = await setup_real_components
        
        # Track data collected
        collected_data = []
        processed_signals = []
        
        async def data_callback(market_data: Dict[str, Any]):
            """Callback to handle incoming market data"""
            collected_data.append(market_data)
            logger.info(f"📊 Received market data: {market_data.get('symbol', 'unknown')} - {market_data.get('close', 0)}")
        
        try:
            # Set up WebSocket client with data callback
            components['websocket_client'].set_data_callback(data_callback)
            
            # Connect to WebSocket
            connected = await components['websocket_client'].connect()
            assert connected, "Failed to connect to Hyperliquid WebSocket"
            
            # Subscribe to market data
            await components['websocket_client'].subscribe_to_market_data()
            
            # Start listening for data (run for 30 seconds to collect real data)
            logger.info("🔄 Collecting real market data for 30 seconds...")
            listen_task = asyncio.create_task(components['websocket_client'].listen_for_data())
            
            # Wait for data collection
            await asyncio.sleep(30)
            
            # Stop listening
            listen_task.cancel()
            await components['websocket_client'].disconnect()
            
            # Verify we collected real data
            assert len(collected_data) > 0, "No market data collected from WebSocket"
            logger.info(f"✅ Collected {len(collected_data)} market data points")
            
            # Process data through Raw Data Intelligence
            logger.info("🔍 Processing data through Raw Data Intelligence...")
            
            # Convert collected data to DataFrame for processing
            if len(collected_data) > 0:
                # Group data by symbol and create DataFrames
                symbols = set(data.get('symbol', 'UNKNOWN') for data in collected_data)
                
                for symbol in symbols:
                    symbol_data = [data for data in collected_data if data.get('symbol') == symbol]
                    
                    if len(symbol_data) >= 2:  # Need at least 2 data points for analysis
                        # Convert to DataFrame
                        df_data = {
                            'timestamp': [data.get('timestamp') for data in symbol_data],
                            'open': [data.get('open', 0) for data in symbol_data],
                            'high': [data.get('high', 0) for data in symbol_data],
                            'low': [data.get('low', 0) for data in symbol_data],
                            'close': [data.get('close', 0) for data in symbol_data],
                            'volume': [data.get('volume', 0) for data in symbol_data],
                            'symbol': [symbol] * len(symbol_data)
                        }
                        
                        market_df = pd.DataFrame(df_data)
                        
                        try:
                            # Process through divergence detector
                            divergence_result = await components['divergence_detector'].analyze(market_df)
                            if divergence_result and not divergence_result.get('error'):
                                processed_signals.append(divergence_result)
                                logger.info(f"📈 Divergence analysis for {symbol}: {divergence_result.get('divergences_detected', 0)} divergences")
                            
                            # Process through volume analyzer
                            volume_result = await components['volume_analyzer'].analyze(market_df)
                            if volume_result and not volume_result.get('error'):
                                processed_signals.append(volume_result)
                                logger.info(f"📊 Volume analysis for {symbol}: {volume_result.get('volume_patterns_detected', 0)} patterns")
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Error processing {symbol} data: {e}")
            
            # Verify signals were created
            assert len(processed_signals) > 0, "No signals generated from real market data"
            logger.info(f"✅ Generated {len(processed_signals)} signals from real data")
            
            # Process through CIL Input Processor
            logger.info("🧠 Processing signals through CIL...")
            cil_outputs = await components['input_processor'].process_agent_outputs()
            
            # Verify CIL processed the signals
            assert len(cil_outputs) > 0, "CIL did not process any signals"
            logger.info(f"✅ CIL processed {len(cil_outputs)} agent outputs")
            
            # Test Global Synthesis Engine
            logger.info("🔄 Testing Global Synthesis Engine...")
            synthesis_results = await components['global_synthesis_engine'].synthesize_global_view({})
            
            # Verify synthesis results
            assert synthesis_results is not None, "Global synthesis failed"
            logger.info(f"✅ Global synthesis completed: {len(synthesis_results.get('insights', []))} insights")
            
            # Test Learning Feedback Engine
            logger.info("📚 Testing Learning Feedback Engine...")
            learning_results = await components['learning_feedback_engine'].process_learning_feedback({})
            
            # Verify learning results
            assert learning_results is not None, "Learning feedback failed"
            logger.info(f"✅ Learning feedback completed: {len(learning_results.get('prediction_outcomes', {}))} prediction outcomes")
            
            # Test Prediction Outcome Tracker
            logger.info("🎯 Testing Prediction Outcome Tracker...")
            prediction_stats = await components['prediction_tracker'].get_prediction_accuracy_stats()
            
            # Verify prediction tracking
            assert prediction_stats is not None, "Prediction tracking failed"
            logger.info(f"✅ Prediction tracking: {prediction_stats.get('total_predictions', 0)} total predictions")
            
            logger.info("🎉 Real WebSocket dataflow test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Real dataflow test failed: {e}")
            raise
        finally:
            # Cleanup
            if components['websocket_client'].is_connected:
                await components['websocket_client'].disconnect()
    
    @pytest.mark.asyncio
    async def test_real_market_data_processing(self, setup_real_components):
        """Test processing of real market data through the system"""
        components = await setup_real_components
        
        # Simulate real market data (since we can't guarantee WebSocket data in tests)
        # Create DataFrame with multiple data points for proper analysis
        market_data_dict = {
            'timestamp': [
                datetime.now(timezone.utc) - timedelta(minutes=5),
                datetime.now(timezone.utc) - timedelta(minutes=4),
                datetime.now(timezone.utc) - timedelta(minutes=3),
                datetime.now(timezone.utc) - timedelta(minutes=2),
                datetime.now(timezone.utc) - timedelta(minutes=1),
                datetime.now(timezone.utc)
            ],
            'open': [50000.0, 50100.0, 50200.0, 50300.0, 50400.0, 50500.0],
            'high': [51000.0, 51100.0, 51200.0, 51300.0, 51400.0, 51500.0],
            'low': [49500.0, 49600.0, 49700.0, 49800.0, 49900.0, 50000.0],
            'close': [50100.0, 50200.0, 50300.0, 50400.0, 50500.0, 50600.0],
            'volume': [1000.0, 1200.0, 1100.0, 1300.0, 1400.0, 1500.0],
            'symbol': ['BTC'] * 6
        }
        
        real_market_data = pd.DataFrame(market_data_dict)
        
        processed_signals = []
        
        try:
            # Process the market data DataFrame
            logger.info(f"📊 Processing BTC data: ${real_market_data['close'].iloc[-1]:.2f} (latest close)")
            
            # Process through divergence detector
            divergence_result = await components['divergence_detector'].analyze(real_market_data)
            if divergence_result and not divergence_result.get('error'):
                processed_signals.append(divergence_result)
                logger.info(f"📈 Divergence analysis completed: {divergence_result.get('divergences_detected', 0)} divergences detected")
            
            # Process through volume analyzer
            volume_result = await components['volume_analyzer'].analyze(real_market_data)
            if volume_result and not volume_result.get('error'):
                processed_signals.append(volume_result)
                logger.info(f"📊 Volume analysis completed: {volume_result.get('volume_patterns_detected', 0)} patterns detected")
            
            # Verify analysis results were created
            assert len(processed_signals) > 0, "No analysis results generated from real market data"
            logger.info(f"✅ Generated {len(processed_signals)} analysis results from real market data")
            
            # Verify analysis results have proper structure
            for result in processed_signals:
                assert 'timestamp' in result, "Analysis result missing timestamp"
                assert 'data_points' in result, "Analysis result missing data_points"
                assert not result.get('error'), f"Analysis result contains error: {result.get('error')}"
            
            logger.info("🎉 Real market data processing test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Real market data processing test failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_prediction_tracking_with_real_data(self, setup_real_components):
        """Test prediction tracking with real market data"""
        components = await setup_real_components
        
        try:
            # Create a test prediction
            test_prediction = {
                'id': f"real_prediction_{int(time.time())}",
                'kind': 'price_prediction',
                'module': 'alpha',
                'symbol': 'BTC',
                'timeframe': '1h',
                'session_bucket': 'US',
                'regime': 'trending',
                'tags': ['agent:raw_data_intelligence:prediction:price_movement'],
                'sig_sigma': 0.8,
                'sig_confidence': 0.75,
                'sig_direction': 'long',
                'agent_id': 'raw_data_intelligence',
                'cil_team_member': 'divergence_detector',
                'prediction_score': None,  # Will be updated by tracker
                'outcome_score': None,
                'content': {
                    'prediction_type': 'price_movement',
                    'target_price': 52000.0,
                    'current_price': 50000.0,
                    'timeframe_hours': 1.0
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert prediction into database
            result = components['supabase_manager'].insert_strand(test_prediction)
            assert result is not None, "Failed to insert prediction"
            
            # Test prediction tracking
            logger.info("🎯 Testing prediction tracking with real data...")
            
            # Get prediction accuracy stats
            stats = await components['prediction_tracker'].get_prediction_accuracy_stats()
            assert stats is not None, "Failed to get prediction stats"
            
            # Process prediction outcomes
            outcomes = await components['prediction_tracker'].process_prediction_outcomes()
            assert outcomes is not None, "Failed to process prediction outcomes"
            
            logger.info(f"✅ Prediction tracking stats: {stats.get('total_predictions', 0)} predictions")
            logger.info("🎉 Prediction tracking with real data test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Prediction tracking test failed: {e}")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
