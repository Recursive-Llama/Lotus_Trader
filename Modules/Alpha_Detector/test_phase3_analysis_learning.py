"""
Test Phase 3: Analysis & Learning Integration

Test the complete analysis and learning system with:
- Prediction analysis
- Group-level learning
- Learning thresholds
- Learning strand creation
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.intelligence.system_control.central_intelligence_layer import SimplifiedCIL


async def test_phase3_analysis_learning():
    """Test Phase 3: Analysis & Learning Integration"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Create simplified CIL
        cil = SimplifiedCIL(supabase_manager, llm_client)
        
        logger.info("Testing Phase 3: Analysis & Learning Integration")
        
        # Test 1: Prediction Analysis
        logger.info("\n--- Testing Prediction Analysis ---")
        
        # Create test prediction data
        test_prediction = {
            'id': 'test_prediction_123',
            'kind': 'prediction',
            'content': {
                'pattern_group': {
                    'group_type': 'multi_single',
                    'asset': 'BTC',
                    'timeframe': '1h',
                    'patterns': [
                        {'pattern_type': 'volume_spike', 'timeframe': '1h'},
                        {'pattern_type': 'divergence', 'timeframe': '1h'}
                    ]
                },
                'context_metadata': {
                    'exact_count': 2,
                    'similar_count': 3,
                    'confidence_level': 0.8
                },
                'confidence': 0.75,
                'outcome_score': 0.6
            }
        }
        
        # Test individual prediction analysis
        analysis = await cil.outcome_analyzer.analyze_completed_prediction('test_prediction_123')
        logger.info(f"Individual analysis: {analysis}")
        
        # Test group analysis
        test_pattern_group = {
            'group_type': 'multi_single',
            'asset': 'BTC',
            'timeframe': '1h',
            'patterns': [
                {'pattern_type': 'volume_spike', 'timeframe': '1h'},
                {'pattern_type': 'divergence', 'timeframe': '1h'}
            ]
        }
        
        group_analysis = await cil.outcome_analyzer.analyze_prediction_group(test_pattern_group)
        logger.info(f"Group analysis: {group_analysis}")
        
        # Test 2: Learning Thresholds
        logger.info("\n--- Testing Learning Thresholds ---")
        
        # Test threshold checking
        test_group_analysis = {
            'total_predictions': 5,
            'success_rate': 0.6,
            'avg_confidence': 0.7
        }
        
        meets_thresholds = cil.meets_learning_thresholds(test_group_analysis)
        logger.info(f"Meets learning thresholds: {meets_thresholds}")
        
        # Test learning quality assessment
        learning_quality = cil.assess_learning_quality(test_group_analysis)
        logger.info(f"Learning quality: {learning_quality}")
        
        # Test 3: Learning Integration
        logger.info("\n--- Testing Learning Integration ---")
        
        # Test learning cycle processing
        await cil.process_learning_cycle()
        logger.info("Learning cycle processed")
        
        # Test group learning processing
        await cil.process_group_learning()
        logger.info("Group learning processed")
        
        # Test 4: Analysis Quality Assessment
        logger.info("\n--- Testing Analysis Quality Assessment ---")
        
        # Test different analysis qualities
        high_quality_prediction = {
            'confidence': 0.8,
            'outcome_score': 0.7,
            'context_metadata': {
                'exact_count': 5,
                'similar_count': 3
            }
        }
        
        medium_quality_prediction = {
            'confidence': 0.5,
            'outcome_score': 0.4,
            'context_metadata': {
                'exact_count': 3,
                'similar_count': 2
            }
        }
        
        low_quality_prediction = {
            'confidence': 0.3,
            'outcome_score': 0.2,
            'context_metadata': {
                'exact_count': 1,
                'similar_count': 0
            }
        }
        
        # Test quality assessment
        high_quality = cil.outcome_analyzer.assess_analysis_quality(high_quality_prediction)
        medium_quality = cil.outcome_analyzer.assess_analysis_quality(medium_quality_prediction)
        low_quality = cil.outcome_analyzer.assess_analysis_quality(low_quality_prediction)
        
        logger.info(f"High quality analysis: {high_quality}")
        logger.info(f"Medium quality analysis: {medium_quality}")
        logger.info(f"Low quality analysis: {low_quality}")
        
        # Test 5: Trend Analysis
        logger.info("\n--- Testing Trend Analysis ---")
        
        # Test confidence trend
        test_predictions = [
            {'confidence': 0.5, 'created_at': '2024-01-01T10:00:00Z'},
            {'confidence': 0.6, 'created_at': '2024-01-01T11:00:00Z'},
            {'confidence': 0.7, 'created_at': '2024-01-01T12:00:00Z'},
            {'confidence': 0.8, 'created_at': '2024-01-01T13:00:00Z'}
        ]
        
        confidence_trend = cil.outcome_analyzer.calculate_confidence_trend(test_predictions)
        outcome_trend = cil.outcome_analyzer.calculate_outcome_trend(test_predictions)
        
        logger.info(f"Confidence trend: {confidence_trend}")
        logger.info(f"Outcome trend: {outcome_trend}")
        
        # Test 6: System Status
        logger.info("\n--- Testing System Status ---")
        
        status = await cil.get_system_status()
        logger.info(f"System status: {status}")
        
        logger.info("\n✅ Phase 3: Analysis & Learning Integration tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


async def test_learning_thresholds():
    """Test learning threshold system"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        from src.intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
        from src.utils.supabase_manager import SupabaseManager
        from src.llm_integration.openrouter_client import OpenRouterClient
        
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        cil = SimplifiedCIL(supabase_manager, llm_client)
        
        logger.info("Testing Learning Thresholds")
        
        # Test different threshold scenarios
        test_scenarios = [
            {
                'name': 'High Quality Group',
                'analysis': {
                    'total_predictions': 10,
                    'success_rate': 0.7,
                    'avg_confidence': 0.8
                },
                'expected': True
            },
            {
                'name': 'Medium Quality Group',
                'analysis': {
                    'total_predictions': 5,
                    'success_rate': 0.5,
                    'avg_confidence': 0.5
                },
                'expected': True
            },
            {
                'name': 'Low Quality Group',
                'analysis': {
                    'total_predictions': 2,
                    'success_rate': 0.3,
                    'avg_confidence': 0.4
                },
                'expected': False
            },
            {
                'name': 'Insufficient Predictions',
                'analysis': {
                    'total_predictions': 1,
                    'success_rate': 0.8,
                    'avg_confidence': 0.9
                },
                'expected': False
            }
        ]
        
        for scenario in test_scenarios:
            meets_thresholds = cil.meets_learning_thresholds(scenario['analysis'])
            learning_quality = cil.assess_learning_quality(scenario['analysis'])
            
            logger.info(f"{scenario['name']}:")
            logger.info(f"  Meets thresholds: {meets_thresholds} (expected: {scenario['expected']})")
            logger.info(f"  Learning quality: {learning_quality}")
            logger.info(f"  Analysis: {scenario['analysis']}")
            logger.info("")
        
        logger.info("✅ Learning threshold tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Learning threshold test failed: {e}")
        raise


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_phase3_analysis_learning())
    asyncio.run(test_learning_thresholds())
