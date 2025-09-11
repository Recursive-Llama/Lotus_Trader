"""
Test Prediction System - Phase 2

Test the complete prediction system with:
- Pattern grouping
- Context retrieval
- Code-based predictions
- LLM-based predictions
- Prediction strand creation
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.intelligence.system_control.central_intelligence_layer import SimplifiedCIL


async def test_prediction_system():
    """Test the complete prediction system"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Create simplified CIL
        cil = SimplifiedCIL(supabase_manager, llm_client)
        
        logger.info("Testing Prediction System - Phase 2")
        
        # Test 1: Pattern Grouping
        test_patterns = [
            {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'},
            {'pattern_type': 'divergence', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'},
            {'pattern_type': 'flow_anomaly', 'asset': 'BTC', 'timeframe': '4h', 'cycle_time': '2024-01-15T10:00:00Z'}
        ]
        
        # Test pattern grouping
        from src.intelligence.system_control.central_intelligence_layer.prediction_engine import PatternGroupingSystem
        grouping_system = PatternGroupingSystem()
        
        # Group by asset
        asset_groups = grouping_system.group_by_asset(test_patterns)
        logger.info(f"Asset Groups: {list(asset_groups.keys())}")
        
        # Test all 6 grouping categories
        for asset, patterns in asset_groups.items():
            logger.info(f"\n--- Testing {asset} patterns ---")
            
            # Single-Single
            single_single = grouping_system.group_single_single(patterns)
            logger.info(f"Single-Single groups: {len(single_single)}")
            
            # Multi-Single
            multi_single = grouping_system.group_multi_single(patterns)
            logger.info(f"Multi-Single groups: {len(multi_single)}")
            
            # Single-Multi
            single_multi = grouping_system.group_single_multi(patterns)
            logger.info(f"Single-Multi groups: {len(single_multi)}")
            
            # Multi-Multi
            multi_multi = grouping_system.group_multi_multi(patterns)
            logger.info(f"Multi-Multi groups: {len(multi_multi)}")
            
            # Single-Multi-Cycle
            single_multi_cycle = grouping_system.group_single_multi_cycle(patterns)
            logger.info(f"Single-Multi-Cycle groups: {len(single_multi_cycle)}")
            
            # Multi-Multi-Cycle
            multi_multi_cycle = grouping_system.group_multi_multi_cycle(patterns)
            logger.info(f"Multi-Multi-Cycle groups: {len(multi_multi_cycle)}")
        
        # Test 2: Prediction Creation
        logger.info("\n--- Testing Prediction Creation ---")
        
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
        
        # Test group signature
        signature = grouping_system.create_group_signature(test_pattern_group)
        logger.info(f"Group Signature: {signature}")
        
        # Test prediction creation
        prediction_engine = cil.prediction_engine
        
        # Test context retrieval
        context = await prediction_engine.get_prediction_context(test_pattern_group)
        logger.info(f"Prediction Context: {context}")
        
        # Test code prediction
        code_prediction = await prediction_engine.create_code_prediction(test_pattern_group, context)
        logger.info(f"Code Prediction: {code_prediction}")
        
        # Test LLM prediction
        llm_prediction = await prediction_engine.create_llm_prediction(test_pattern_group, context)
        logger.info(f"LLM Prediction: {llm_prediction}")
        
        # Test full prediction creation
        prediction_id = await prediction_engine.create_prediction(test_pattern_group)
        logger.info(f"Created Prediction ID: {prediction_id}")
        
        # Test 3: Prediction Tracking
        logger.info("\n--- Testing Prediction Tracking ---")
        
        # Test prediction tracking
        tracking_result = await cil.prediction_tracker.track_prediction(prediction_id)
        logger.info(f"Tracking Result: {tracking_result}")
        
        # Test 4: System Status
        logger.info("\n--- Testing System Status ---")
        
        status = await cil.get_system_status()
        logger.info(f"System Status: {status}")
        
        logger.info("\n✅ Prediction System tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


async def test_pattern_grouping_comprehensive():
    """Test comprehensive pattern grouping scenarios"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        from src.intelligence.system_control.central_intelligence_layer.prediction_engine import PatternGroupingSystem
        
        grouping_system = PatternGroupingSystem()
        
        # Test comprehensive pattern scenarios
        test_scenarios = [
            {
                'name': 'Single Pattern, Single Timeframe',
                'patterns': [
                    {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'}
                ]
            },
            {
                'name': 'Multiple Patterns, Single Timeframe',
                'patterns': [
                    {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'},
                    {'pattern_type': 'divergence', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'}
                ]
            },
            {
                'name': 'Single Pattern, Multiple Timeframes',
                'patterns': [
                    {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'},
                    {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '4h', 'cycle_time': '2024-01-15T10:00:00Z'}
                ]
            },
            {
                'name': 'Multiple Patterns, Multiple Timeframes',
                'patterns': [
                    {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'},
                    {'pattern_type': 'divergence', 'asset': 'BTC', 'timeframe': '4h', 'cycle_time': '2024-01-15T10:00:00Z'}
                ]
            },
            {
                'name': 'Single Pattern, Multiple Cycles',
                'patterns': [
                    {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'},
                    {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T14:00:00Z'}
                ]
            },
            {
                'name': 'Multiple Patterns, Multiple Cycles',
                'patterns': [
                    {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T10:00:00Z'},
                    {'pattern_type': 'divergence', 'asset': 'BTC', 'timeframe': '1h', 'cycle_time': '2024-01-15T14:00:00Z'}
                ]
            }
        ]
        
        for scenario in test_scenarios:
            logger.info(f"\n--- Testing: {scenario['name']} ---")
            
            patterns = scenario['patterns']
            asset_groups = grouping_system.group_by_asset(patterns)
            
            for asset, asset_patterns in asset_groups.items():
                logger.info(f"Asset: {asset}")
                
                # Test all grouping methods
                single_single = grouping_system.group_single_single(asset_patterns)
                multi_single = grouping_system.group_multi_single(asset_patterns)
                single_multi = grouping_system.group_single_multi(asset_patterns)
                multi_multi = grouping_system.group_multi_multi(asset_patterns)
                single_multi_cycle = grouping_system.group_single_multi_cycle(asset_patterns)
                multi_multi_cycle = grouping_system.group_multi_multi_cycle(asset_patterns)
                
                logger.info(f"  Single-Single: {len(single_single)} groups")
                logger.info(f"  Multi-Single: {len(multi_single)} groups")
                logger.info(f"  Single-Multi: {len(single_multi)} groups")
                logger.info(f"  Multi-Multi: {len(multi_multi)} groups")
                logger.info(f"  Single-Multi-Cycle: {len(single_multi_cycle)} groups")
                logger.info(f"  Multi-Multi-Cycle: {len(multi_multi_cycle)} groups")
                
                # Test group signatures
                for group_type, groups in [
                    ('single_single', single_single),
                    ('multi_single', multi_single),
                    ('single_multi', single_multi),
                    ('multi_multi', multi_multi),
                    ('single_multi_cycle', single_multi_cycle),
                    ('multi_multi_cycle', multi_multi_cycle)
                ]:
                    for group_key, group in groups.items():
                        signature = grouping_system.create_group_signature(group)
                        logger.info(f"    {group_type} signature: {signature}")
        
        logger.info("\n✅ Comprehensive pattern grouping tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Pattern grouping test failed: {e}")
        raise


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_prediction_system())
    asyncio.run(test_pattern_grouping_comprehensive())
