"""
Test Simplified CIL System

Test the simplified CIL with pattern grouping and prediction creation.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.intelligence.system_control.central_intelligence_layer import SimplifiedCIL


async def test_simplified_cil():
    """Test the simplified CIL system"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Create simplified CIL
        cil = SimplifiedCIL(supabase_manager, llm_client)
        
        logger.info("Testing Simplified CIL System")
        
        # Test 1: Check system status
        status = await cil.get_system_status()
        logger.info(f"System Status: {status}")
        
        # Test 2: Test pattern grouping
        test_pattern_group = {
            'group_type': 'multi_single',
            'asset': 'BTC',
            'timeframe': '1h',
            'cycle_time': '2024-01-15T10:00:00Z',
            'patterns': [
                {'pattern_type': 'volume_spike', 'timeframe': '1h'},
                {'pattern_type': 'divergence', 'timeframe': '1h'}
            ]
        }
        
        # Test group signature creation
        from src.intelligence.system_control.central_intelligence_layer.prediction_engine import PatternGroupingSystem
        grouping_system = PatternGroupingSystem()
        signature = grouping_system.create_group_signature(test_pattern_group)
        logger.info(f"Group Signature: {signature}")
        
        # Test 3: Test prediction context
        prediction_engine = cil.prediction_engine
        context = await prediction_engine.get_prediction_context(test_pattern_group)
        logger.info(f"Prediction Context: {context}")
        
        # Test 4: Test prediction creation
        prediction_id = await prediction_engine.create_prediction(test_pattern_group)
        logger.info(f"Created Prediction ID: {prediction_id}")
        
        logger.info("Simplified CIL tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


async def test_pattern_grouping():
    """Test pattern grouping system"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        from src.intelligence.system_control.central_intelligence_layer.prediction_engine import PatternGroupingSystem
        
        grouping_system = PatternGroupingSystem()
        
        # Test data
        test_patterns = [
            {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'},
            {'pattern_type': 'divergence', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'},
            {'pattern_type': 'volume_spike', 'asset': 'ETH', 'timeframe': '4h', 'cycle_time': '2024-01-15T10:00:00Z'}
        ]
        
        # Test grouping
        asset_groups = grouping_system.group_by_asset(test_patterns)
        logger.info(f"Asset Groups: {asset_groups}")
        
        # Test single-single grouping
        single_single = grouping_system.group_single_single(test_patterns)
        logger.info(f"Single-Single Groups: {single_single}")
        
        # Test multi-single grouping
        multi_single = grouping_system.group_multi_single(test_patterns)
        logger.info(f"Multi-Single Groups: {multi_single}")
        
        logger.info("Pattern grouping tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Pattern grouping test failed: {e}")
        raise


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_simplified_cil())
    asyncio.run(test_pattern_grouping())
