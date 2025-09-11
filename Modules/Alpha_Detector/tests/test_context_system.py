"""
Test Context System

Test the context retrieval system to see what's working and what needs fixing.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.intelligence.system_control.central_intelligence_layer import SimplifiedCIL


async def test_context_system():
    """Test the context retrieval system"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Create simplified CIL
        cil = SimplifiedCIL(supabase_manager, llm_client)
        
        logger.info("Testing Context System")
        
        # Test 1: Check database connection
        logger.info("\n--- Testing Database Connection ---")
        try:
            # Test simple query
            result = await supabase_manager.execute_query("SELECT 1 as test")
            logger.info(f"Database connection: {'✅ Working' if result else '❌ Failed'}")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
        
        # Test 2: Test context retrieval
        logger.info("\n--- Testing Context Retrieval ---")
        
        # Create test pattern group
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
        
        # Test exact group context
        logger.info("Testing exact group context...")
        exact_context = await cil.prediction_engine.get_exact_group_context(test_pattern_group)
        logger.info(f"Exact context results: {len(exact_context)} matches")
        
        # Test similar group context
        logger.info("Testing similar group context...")
        similar_context = await cil.prediction_engine.get_similar_group_context(test_pattern_group)
        logger.info(f"Similar context results: {len(similar_context)} matches")
        
        # Test full prediction context
        logger.info("Testing full prediction context...")
        full_context = await cil.prediction_engine.get_prediction_context(test_pattern_group)
        logger.info(f"Full context: {full_context}")
        
        # Test 3: Test learning system
        logger.info("\n--- Testing Learning System ---")
        
        # Check if learning system is accessible
        learning_system = cil.learning_system
        logger.info(f"Learning system: {'✅ Available' if learning_system else '❌ Not available'}")
        
        # Test 4: Test prediction analysis
        logger.info("\n--- Testing Prediction Analysis ---")
        
        # Check if outcome analyzer is accessible
        outcome_analyzer = cil.outcome_analyzer
        logger.info(f"Outcome analyzer: {'✅ Available' if outcome_analyzer else '❌ Not available'}")
        
        logger.info("\n✅ Context system tests completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_context_system())
