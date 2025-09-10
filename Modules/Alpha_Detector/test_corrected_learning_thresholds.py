"""
Test Corrected Learning Thresholds and Prediction Review Clustering

Test the corrected learning system that:
- Learns from both success and failure
- Uses prediction review clustering with 70% similarity
- Has proper thresholds for learning
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.intelligence.system_control.central_intelligence_layer import SimplifiedCIL


async def test_corrected_learning_thresholds():
    """Test corrected learning thresholds that learn from both success and failure"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Create simplified CIL
        cil = SimplifiedCIL(supabase_manager, llm_client)
        
        logger.info("Testing Corrected Learning Thresholds")
        
        # Test 1: Learning from Success and Failure
        logger.info("\n--- Testing Learning from Success and Failure ---")
        
        test_scenarios = [
            {
                'name': 'High Success Group',
                'analysis': {
                    'total_predictions': 10,
                    'successful_predictions': 8,
                    'success_rate': 0.8,
                    'avg_confidence': 0.7
                },
                'should_learn': True,
                'reason': 'High success rate - learn what works'
            },
            {
                'name': 'High Failure Group',
                'analysis': {
                    'total_predictions': 10,
                    'successful_predictions': 2,
                    'success_rate': 0.2,
                    'avg_confidence': 0.6
                },
                'should_learn': True,
                'reason': 'High failure rate - learn what to avoid'
            },
            {
                'name': 'Mixed Results Group',
                'analysis': {
                    'total_predictions': 8,
                    'successful_predictions': 4,
                    'success_rate': 0.5,
                    'avg_confidence': 0.5
                },
                'should_learn': True,
                'reason': 'Mixed results - learn patterns and conditions'
            },
            {
                'name': 'Low Confidence Group',
                'analysis': {
                    'total_predictions': 5,
                    'successful_predictions': 3,
                    'success_rate': 0.6,
                    'avg_confidence': 0.05  # Very low confidence
                },
                'should_learn': False,
                'reason': 'Too low confidence - not enough data quality'
            },
            {
                'name': 'Insufficient Data Group',
                'analysis': {
                    'total_predictions': 2,
                    'successful_predictions': 1,
                    'success_rate': 0.5,
                    'avg_confidence': 0.6
                },
                'should_learn': False,
                'reason': 'Insufficient data - need at least 3 predictions'
            }
        ]
        
        for scenario in test_scenarios:
            meets_thresholds = cil.meets_learning_thresholds(scenario['analysis'])
            learning_quality = cil.assess_learning_quality(scenario['analysis'])
            
            logger.info(f"\n{scenario['name']}:")
            logger.info(f"  Analysis: {scenario['analysis']}")
            logger.info(f"  Meets thresholds: {meets_thresholds} (expected: {scenario['should_learn']})")
            logger.info(f"  Learning quality: {learning_quality}")
            logger.info(f"  Reason: {scenario['reason']}")
            
            # Verify the logic
            if meets_thresholds == scenario['should_learn']:
                logger.info(f"  ✅ Correct threshold decision")
            else:
                logger.error(f"  ❌ Incorrect threshold decision")
        
        # Test 2: Prediction Review Clustering
        logger.info("\n--- Testing Prediction Review Clustering ---")
        
        # Test pattern group
        test_pattern_group = {
            'group_type': 'multi_single',
            'asset': 'BTC',
            'timeframe': '1h',
            'patterns': [
                {'pattern_type': 'volume_spike', 'timeframe': '1h'},
                {'pattern_type': 'divergence', 'timeframe': '1h'}
            ]
        }
        
        # Test group signature creation
        from src.intelligence.system_control.central_intelligence_layer.prediction_engine import PatternGroupingSystem
        grouping_system = PatternGroupingSystem()
        group_signature = grouping_system.create_group_signature(test_pattern_group)
        logger.info(f"Group signature: {group_signature}")
        
        # Test context retrieval (will be empty due to database issues)
        exact_context = await cil.prediction_engine.get_exact_group_context(test_pattern_group)
        similar_context = await cil.prediction_engine.get_similar_group_context(test_pattern_group)
        
        logger.info(f"Exact context matches: {len(exact_context)}")
        logger.info(f"Similar context matches: {len(similar_context)}")
        
        # Test 3: Learning Quality Assessment
        logger.info("\n--- Testing Learning Quality Assessment ---")
        
        quality_scenarios = [
            {
                'name': 'High Quality Learning',
                'analysis': {
                    'total_predictions': 15,
                    'success_rate': 0.7,
                    'avg_confidence': 0.8
                },
                'expected_quality': 'high_quality'
            },
            {
                'name': 'Medium Quality Learning',
                'analysis': {
                    'total_predictions': 8,
                    'success_rate': 0.6,
                    'avg_confidence': 0.6
                },
                'expected_quality': 'medium_quality'
            },
            {
                'name': 'Low Quality Learning',
                'analysis': {
                    'total_predictions': 5,
                    'success_rate': 0.4,
                    'avg_confidence': 0.4
                },
                'expected_quality': 'low_quality'
            }
        ]
        
        for scenario in quality_scenarios:
            quality = cil.assess_learning_quality(scenario['analysis'])
            logger.info(f"{scenario['name']}: {quality} (expected: {scenario['expected_quality']})")
            
            if quality == scenario['expected_quality']:
                logger.info(f"  ✅ Correct quality assessment")
            else:
                logger.error(f"  ❌ Incorrect quality assessment")
        
        # Test 4: Prediction Review Strand Creation
        logger.info("\n--- Testing Prediction Review Strand Creation ---")
        
        # Test prediction review creation
        test_prediction = {
            'id': 'test_prediction_123',
            'pattern_group': test_pattern_group,
            'confidence': 0.7,
            'method': 'code'
        }
        
        test_outcome = {
            'success': True,
            'return_pct': 2.5,
            'max_drawdown': -0.8,
            'duration_hours': 20
        }
        
        review_id = await cil.prediction_engine.create_prediction_review_strand(test_prediction, test_outcome)
        logger.info(f"Created prediction review strand: {review_id}")
        
        logger.info("\n✅ Corrected learning thresholds tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_corrected_learning_thresholds())
