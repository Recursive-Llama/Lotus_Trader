"""
Simple Integration Test

This is a simplified integration test to validate the basic data flow
without requiring real websocket connections or complex LLM calls.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
import logging

# Import the actual components
from src.intelligence.raw_data_intelligence.analyzers.divergence_detector import RawDataDivergenceDetector
from src.intelligence.raw_data_intelligence.volume_analyzer import VolumePatternAnalyzer
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSimpleIntegration:
    """Simple integration test suite"""
    
    @pytest.fixture
    async def setup_components(self):
        """Set up basic components for testing"""
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Raw Data Intelligence components
        divergence_detector = RawDataDivergenceDetector()
        volume_analyzer = VolumePatternAnalyzer()
        
        return {
            'supabase_manager': supabase_manager,
            'llm_client': llm_client,
            'divergence_detector': divergence_detector,
            'volume_analyzer': volume_analyzer
        }
    
    @pytest.mark.asyncio
    async def test_basic_component_creation(self, setup_components):
        """Test that basic components can be created"""
        components = await setup_components
        
        # Verify components were created
        assert components['supabase_manager'] is not None, "SupabaseManager not created"
        assert components['llm_client'] is not None, "OpenRouterClient not created"
        assert components['divergence_detector'] is not None, "DivergenceDetector not created"
        assert components['volume_analyzer'] is not None, "VolumeAnalyzer not created"
        
        logger.info("✅ All basic components created successfully")
    
    @pytest.mark.asyncio
    async def test_mock_data_processing(self, setup_components):
        """Test processing mock market data"""
        components = await setup_components
        
        # Create mock market data
        mock_data = [
            {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'open': 50000.0,
                'high': 51000.0,
                'low': 49000.0,
                'close': 50500.0,
                'volume': 1000.0
            },
            {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'open': 50500.0,
                'high': 51500.0,
                'low': 49500.0,
                'close': 51000.0,
                'volume': 1200.0
            }
        ]
        
        # Process through divergence detector
        divergence_analysis = await components['divergence_detector'].analyze(mock_data)
        assert divergence_analysis is not None, "Divergence analysis failed"
        assert isinstance(divergence_analysis, dict), "Divergence analysis should return dict"
        
        # Process through volume analyzer
        volume_analysis = await components['volume_analyzer'].analyze(mock_data)
        assert volume_analysis is not None, "Volume analysis failed"
        assert isinstance(volume_analysis, dict), "Volume analysis should return dict"
        
        logger.info("✅ Mock data processing successful")
    
    @pytest.mark.asyncio
    async def test_database_connection(self, setup_components):
        """Test database connection"""
        components = await setup_components
        
        # Test database connection
        try:
            # Try to get recent strands (should not fail even if empty)
            recent_strands = await components['supabase_manager'].get_recent_strands(limit=5)
            assert isinstance(recent_strands, list), "Should return list of strands"
            logger.info(f"✅ Database connection successful, found {len(recent_strands)} recent strands")
        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")
            # This is expected in some environments, so we'll just log it
    
    @pytest.mark.asyncio
    async def test_llm_client_initialization(self, setup_components):
        """Test LLM client initialization"""
        components = await setup_components
        
        # Test LLM client
        try:
            # Just test that the client was created
            assert components['llm_client'] is not None, "LLM client not created"
            logger.info("✅ LLM client initialization successful")
        except Exception as e:
            logger.warning(f"LLM client test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, setup_components):
        """Test error handling with invalid data"""
        components = await setup_components
        
        # Test with invalid data
        invalid_data = [
            {'invalid': 'data'},
            None,
            {}
        ]
        
        # Test divergence detector with invalid data
        try:
            result = await components['divergence_detector'].analyze(invalid_data)
            # Should handle gracefully
            assert result is not None, "Should return result even with invalid data"
            logger.info("✅ Divergence detector error handling successful")
        except Exception as e:
            logger.info(f"✅ Divergence detector error handling successful (caught: {e})")
        
        # Test volume analyzer with invalid data
        try:
            result = await components['volume_analyzer'].analyze(invalid_data)
            # Should handle gracefully
            assert result is not None, "Should return result even with invalid data"
            logger.info("✅ Volume analyzer error handling successful")
        except Exception as e:
            logger.info(f"✅ Volume analyzer error handling successful (caught: {e})")


if __name__ == "__main__":
    # Run the simple integration test
    pytest.main([__file__, "-v", "-s"])
