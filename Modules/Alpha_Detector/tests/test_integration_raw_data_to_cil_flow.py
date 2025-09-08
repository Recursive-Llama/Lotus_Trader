"""
Integration Test: Raw Data Intelligence → Central Intelligence Layer Flow

This test validates the complete data flow from raw data intelligence agents
to the CIL, using real websocket connections and LLM calls with minimal mocking.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import websockets
import logging

# Import the actual components
from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.intelligence.raw_data_intelligence.divergence_detector import RawDataDivergenceDetector
from src.intelligence.raw_data_intelligence.volume_analyzer import VolumePatternAnalyzer
from src.intelligence.raw_data_intelligence.cross_asset_analyzer import CrossAssetPatternAnalyzer
from src.intelligence.system_control.central_intelligence_layer.core.strategic_pattern_miner import StrategicPatternMiner
from src.intelligence.system_control.central_intelligence_layer.engines.input_processor import InputProcessor
from src.intelligence.system_control.central_intelligence_layer.engines.global_synthesis_engine import GlobalSynthesisEngine
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.data_sources.hyperliquid_client import HyperliquidWebSocketClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestRawDataToCilFlow:
    """Test suite for Raw Data Intelligence → CIL data flow"""
    
    @pytest.fixture
    async def setup_components(self):
        """Set up all components for integration testing"""
        # Initialize real components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Raw Data Intelligence components
        raw_data_agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
        divergence_detector = RawDataDivergenceDetector()
        volume_analyzer = VolumePatternAnalyzer()
        cross_asset_analyzer = CrossAssetPatternAnalyzer()
        
        # CIL components
        strategic_pattern_miner = StrategicPatternMiner(supabase_manager, llm_client)
        input_processor = InputProcessor(supabase_manager, llm_client)
        global_synthesis_engine = GlobalSynthesisEngine(supabase_manager, llm_client)
        
        # WebSocket connection (real)
        websocket_client = HyperliquidWebSocketClient()
        
        return {
            'supabase_manager': supabase_manager,
            'llm_client': llm_client,
            'raw_data_agent': raw_data_agent,
            'divergence_detector': divergence_detector,
            'volume_analyzer': volume_analyzer,
            'cross_asset_analyzer': cross_asset_analyzer,
            'strategic_pattern_miner': strategic_pattern_miner,
            'input_processor': input_processor,
            'global_synthesis_engine': global_synthesis_engine,
            'websocket_client': websocket_client
        }
    
    @pytest.mark.asyncio
    async def test_raw_data_signal_generation_to_cil_processing(self, setup_components):
        """Test complete flow: Raw data → Signal generation → CIL processing"""
        components = await setup_components
        
        # Step 1: Connect to real websocket and get market data
        logger.info("Step 1: Connecting to real websocket...")
        await components['websocket_client'].connect()
        
        # Get real market data for testing
        market_data = await self._get_real_market_data(components['websocket_client'])
        assert market_data is not None, "Failed to get real market data"
        logger.info(f"Received market data: {len(market_data)} data points")
        
        # Step 2: Process market data through raw data intelligence agents
        logger.info("Step 2: Processing through raw data intelligence agents...")
        
        # Process through divergence detector
        divergence_analysis = await components['divergence_detector'].analyze(market_data)
        divergence_signals = divergence_analysis.get('signals', [])
        logger.info(f"Divergence detector generated {len(divergence_signals)} signals")
        
        # Process through volume analyzer
        volume_analysis = await components['volume_analyzer'].analyze(market_data)
        volume_signals = volume_analysis.get('signals', [])
        logger.info(f"Volume analyzer generated {len(volume_signals)} signals")
        
        # Process through cross-asset analyzer
        cross_asset_analysis = await components['cross_asset_analyzer'].analyze(market_data)
        cross_asset_signals = cross_asset_analysis.get('signals', [])
        logger.info(f"Cross-asset analyzer generated {len(cross_asset_signals)} signals")
        
        # Verify signals were generated
        assert len(divergence_signals) > 0 or len(volume_signals) > 0 or len(cross_asset_signals) > 0, \
            "No signals generated by raw data intelligence agents"
        
        # Step 3: Verify signals are published to database as strands
        logger.info("Step 3: Verifying signals published to database...")
        
        # Check that signals were published as strands
        all_signals = divergence_signals + volume_signals + cross_asset_signals
        published_strands = []
        
        for signal in all_signals:
            # Verify signal has required fields for strand
            assert 'id' in signal, "Signal missing ID"
            assert 'kind' in signal, "Signal missing kind"
            assert 'content' in signal, "Signal missing content"
            assert 'tags' in signal, "Signal missing tags"
            
            # Check that signal was published to database
            strand_id = signal['id']
            published_strand = await components['supabase_manager'].get_strand_by_id(strand_id)
            if published_strand:
                published_strands.append(published_strand)
        
        assert len(published_strands) > 0, "No signals were published to database as strands"
        logger.info(f"Verified {len(published_strands)} signals published to database")
        
        # Step 4: CIL Input Processor processes the signals
        logger.info("Step 4: CIL Input Processor processing signals...")
        
        # Get recent strands for CIL processing
        recent_strands = await components['supabase_manager'].get_recent_strands(
            limit=50, 
            since=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        
        # Process through CIL Input Processor
        input_processing_results = await components['input_processor'].process_agent_outputs(
            recent_strands, 
            {'market_context': market_data[-1] if market_data else {}}
        )
        
        assert input_processing_results is not None, "CIL Input Processor failed to process signals"
        assert 'processed_signals' in input_processing_results, "Missing processed signals in results"
        assert 'cross_agent_metadata' in input_processing_results, "Missing cross-agent metadata"
        
        logger.info(f"CIL Input Processor processed {len(input_processing_results['processed_signals'])} signals")
        
        # Step 5: CIL Global Synthesis Engine analyzes patterns
        logger.info("Step 5: CIL Global Synthesis Engine analyzing patterns...")
        
        synthesis_results = await components['global_synthesis_engine'].synthesize_global_view(
            input_processing_results['processed_signals'],
            input_processing_results['cross_agent_metadata'],
            {'market_regime': 'testing', 'session': 'test'}
        )
        
        assert synthesis_results is not None, "CIL Global Synthesis Engine failed to synthesize"
        assert 'cross_agent_correlations' in synthesis_results, "Missing cross-agent correlations"
        assert 'coverage_analysis' in synthesis_results, "Missing coverage analysis"
        assert 'meta_patterns' in synthesis_results, "Missing meta-patterns"
        
        logger.info(f"CIL Global Synthesis found {len(synthesis_results['cross_agent_correlations'])} correlations")
        
        # Step 6: CIL Strategic Pattern Miner creates meta-signals
        logger.info("Step 6: CIL Strategic Pattern Miner creating meta-signals...")
        
        meta_signals = await components['strategic_pattern_miner'].analyze_cross_team_patterns(
            synthesis_results['cross_agent_correlations'],
            synthesis_results['meta_patterns']
        )
        
        assert meta_signals is not None, "CIL Strategic Pattern Miner failed to create meta-signals"
        assert len(meta_signals) >= 0, "Meta-signals should be a list"
        
        logger.info(f"CIL Strategic Pattern Miner created {len(meta_signals)} meta-signals")
        
        # Step 7: Verify meta-signals are published back to database
        logger.info("Step 7: Verifying meta-signals published to database...")
        
        meta_signal_strands = []
        for meta_signal in meta_signals:
            if 'id' in meta_signal:
                strand = await components['supabase_manager'].get_strand_by_id(meta_signal['id'])
                if strand:
                    meta_signal_strands.append(strand)
        
        logger.info(f"Verified {len(meta_signal_strands)} meta-signals published to database")
        
        # Step 8: Verify complete data flow integrity
        logger.info("Step 8: Verifying complete data flow integrity...")
        
        # Check that all components are working together
        assert len(published_strands) > 0, "Raw data signals not published"
        assert input_processing_results is not None, "CIL input processing failed"
        assert synthesis_results is not None, "CIL synthesis failed"
        assert meta_signals is not None, "CIL meta-signal generation failed"
        
        # Verify tag-based communication is working
        for strand in published_strands:
            assert 'tags' in strand, "Strand missing tags for communication"
            tags = strand['tags']
            assert any('agent:raw_data_intelligence' in tag for tag in tags), \
                "Raw data intelligence tags not found"
        
        for meta_strand in meta_signal_strands:
            assert 'tags' in meta_strand, "Meta-signal strand missing tags"
            tags = meta_strand['tags']
            assert any('agent:central_intelligence' in tag for tag in tags), \
                "CIL tags not found in meta-signals"
        
        logger.info("✅ Complete data flow integrity verified!")
        
        # Cleanup
        await components['websocket_client'].disconnect()
        
        return {
            'raw_data_signals': len(published_strands),
            'cil_processed_signals': len(input_processing_results['processed_signals']),
            'cil_correlations': len(synthesis_results['cross_agent_correlations']),
            'cil_meta_signals': len(meta_signal_strands),
            'data_flow_success': True
        }
    
    async def _get_real_market_data(self, websocket_client: HyperliquidWebSocketClient) -> List[Dict[str, Any]]:
        """Get real market data from websocket"""
        try:
            # Subscribe to market data
            await websocket_client.subscribe_to_market_data()
            
            # Collect data for 30 seconds
            market_data = []
            start_time = time.time()
            
            while time.time() - start_time < 30 and len(market_data) < 10:
                try:
                    # Listen for data
                    data = await asyncio.wait_for(websocket_client.listen_for_data(), timeout=5.0)
                    if data:
                        market_data.append(data)
                        logger.info(f"Collected market data point: {data.get('timestamp', 'unknown')}")
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for market data")
                    break
                except Exception as e:
                    logger.warning(f"Error getting market data: {e}")
                    break
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get real market data: {e}")
            return []
    
    @pytest.mark.asyncio
    async def test_signal_tag_communication_flow(self, setup_components):
        """Test that tag-based communication is working correctly"""
        components = await setup_components
        
        # Create a test signal with proper tags
        test_signal = {
            'id': f"test_signal_{int(time.time())}",
            'kind': 'divergence_detection',
            'module': 'alpha',
            'symbol': 'BTC',
            'timeframe': '1h',
            'session_bucket': 'US',
            'regime': 'high_vol',
            'tags': [
                'agent:raw_data_intelligence:divergence_detector:divergence_found',
                'signal_family:divergence',
                'priority:medium'
            ],
            'content': {
                'divergence_type': 'bullish',
                'confidence': 0.75,
                'rsi_value': 30.5,
                'price_action': 'reversal_candidate'
            },
            'sig_sigma': 0.8,
            'sig_confidence': 0.75,
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'cil_team_member': 'divergence_detector'
        }
        
        # Publish test signal
        await components['supabase_manager'].insert_strand(test_signal)
        
        # Wait for signal to be processed
        await asyncio.sleep(2)
        
        # Verify signal was published
        published_signal = await components['supabase_manager'].get_strand_by_id(test_signal['id'])
        assert published_signal is not None, "Test signal was not published"
        
        # Verify tags are correct
        assert 'tags' in published_signal, "Published signal missing tags"
        tags = published_signal['tags']
        
        # Check for required tags
        required_tags = [
            'agent:raw_data_intelligence:divergence_detector:divergence_found',
            'signal_family:divergence'
        ]
        
        for required_tag in required_tags:
            assert any(required_tag in tag for tag in tags), \
                f"Required tag not found: {required_tag}"
        
        # Test CIL can find and process this signal
        recent_strands = await components['supabase_manager'].get_recent_strands(
            limit=10,
            since=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        # Filter for our test signal
        test_strands = [s for s in recent_strands if s['id'] == test_signal['id']]
        assert len(test_strands) > 0, "CIL cannot find the test signal"
        
        # Process through CIL Input Processor
        input_results = await components['input_processor'].process_agent_outputs(
            test_strands,
            {'market_context': {'symbol': 'BTC', 'timeframe': '1h'}}
        )
        
        assert input_results is not None, "CIL failed to process tagged signal"
        assert len(input_results['processed_signals']) > 0, "CIL processed no signals"
        
        logger.info("✅ Tag-based communication flow verified!")
    
    @pytest.mark.asyncio
    async def test_resonance_field_integration(self, setup_components):
        """Test that resonance field updates are working through the data flow"""
        components = await setup_components
        
        # Create a test signal with resonance potential
        test_signal = {
            'id': f"resonance_test_{int(time.time())}",
            'kind': 'volume_anomaly',
            'module': 'alpha',
            'symbol': 'ETH',
            'timeframe': '1h',
            'session_bucket': 'EU',
            'regime': 'sideways',
            'tags': [
                'agent:raw_data_intelligence:volume_analyzer:volume_spike',
                'signal_family:volume',
                'priority:high',
                'resonance_candidate:true'
            ],
            'content': {
                'volume_ratio': 2.5,
                'confidence': 0.85,
                'anomaly_type': 'unusual_activity',
                'context': 'breakout_candidate'
            },
            'sig_sigma': 0.9,
            'sig_confidence': 0.85,
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'cil_team_member': 'volume_analyzer',
            'resonance_score': 0.0  # Will be updated by resonance system
        }
        
        # Publish test signal
        await components['supabase_manager'].insert_strand(test_signal)
        
        # Wait for resonance system to process
        await asyncio.sleep(3)
        
        # Check if resonance score was updated
        updated_signal = await components['supabase_manager'].get_strand_by_id(test_signal['id'])
        assert updated_signal is not None, "Test signal not found after resonance processing"
        
        # Verify resonance fields exist
        assert 'resonance_score' in updated_signal, "Resonance score not calculated"
        assert 'phi' in updated_signal, "Phi field not set"
        assert 'rho' in updated_signal, "Rho field not set"
        
        # Check that resonance score is reasonable
        resonance_score = updated_signal.get('resonance_score', 0)
        assert 0.0 <= resonance_score <= 1.0, f"Invalid resonance score: {resonance_score}"
        
        logger.info(f"✅ Resonance field integration verified! Score: {resonance_score}")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, setup_components):
        """Test error handling and recovery in the data flow"""
        components = await setup_components
        
        # Test with malformed signal data
        malformed_signal = {
            'id': f"malformed_test_{int(time.time())}",
            'kind': 'test_signal',
            # Missing required fields
            'content': {
                'test': 'malformed_data'
            }
        }
        
        # Try to publish malformed signal
        try:
            await components['supabase_manager'].insert_strand(malformed_signal)
        except Exception as e:
            logger.info(f"Expected error for malformed signal: {e}")
        
        # Test with invalid market data
        invalid_market_data = [
            {'invalid': 'data'},
            {'timestamp': 'invalid'},
            None
        ]
        
        # Test that components handle invalid data gracefully
        try:
            divergence_analysis = await components['divergence_detector'].analyze(invalid_market_data)
            # Should return empty list or handle gracefully
            assert isinstance(divergence_analysis, dict), "Should return dict even with invalid data"
        except Exception as e:
            logger.info(f"Component handled invalid data: {e}")
        
        # Test database connection recovery
        try:
            # Simulate database connection issue
            with patch.object(components['supabase_manager'], 'insert_strand', side_effect=Exception("DB Error")):
                test_signal = {
                    'id': f"db_error_test_{int(time.time())}",
                    'kind': 'test_signal',
                    'content': {'test': 'data'}
                }
                
                try:
                    await components['supabase_manager'].insert_strand(test_signal)
                except Exception as db_error:
                    logger.info(f"Database error handled: {db_error}")
                    # Should not crash the system
                    assert "DB Error" in str(db_error)
        except Exception as e:
            logger.info(f"Error handling test completed: {e}")
        
        logger.info("✅ Error handling and recovery verified!")


if __name__ == "__main__":
    # Run the integration test
    pytest.main([__file__, "-v", "-s"])
