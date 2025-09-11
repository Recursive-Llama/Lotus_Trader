#!/usr/bin/env python3
"""
Test script for CIL Learning System

This script tests the CIL learning components including:
1. CIL clustering with trading-specific features
2. Prediction tracking with market data integration
3. Outcome analysis engine
4. Conditional plan manager
5. Integrated CIL learning system
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.intelligence.cil_learning import (
    CILClustering, CILPatternClusterer,
    PredictionTracker, PredictionStatus, PredictionOutcome, PredictionData,
    OutcomeAnalysisEngine, AnalysisType, AnalysisResult,
    ConditionalPlanManager, PlanStatus, PlanType, ConditionalPlan,
    CILLearningSystem
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_cil_clustering():
    """Test CIL clustering system"""
    print("\n=== Testing CIL Clustering ===")
    
    clustering = CILClustering()
    
    # Test trading strands
    test_strands = [
        {
            'id': 'trading_1',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'volume_spike',
            'strength_range': 'strong',
            'rr_profile': 'moderate',
            'market_conditions': 'moderate_volatility',
            'braid_level': 0,
            'volume_ratio': 2.5,
            'rr_ratio': 2.5,
            'max_drawdown': 0.08,
            'sig_confidence': 0.8
        },
        {
            'id': 'trading_2',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'volume_spike',
            'strength_range': 'strong',
            'rr_profile': 'moderate',
            'market_conditions': 'moderate_volatility',
            'braid_level': 0,
            'volume_ratio': 2.3,
            'rr_ratio': 2.2,
            'max_drawdown': 0.09,
            'sig_confidence': 0.75
        },
        {
            'id': 'trading_3',
            'symbol': 'ETH',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'strength_range': 'moderate',
            'rr_profile': 'conservative',
            'market_conditions': 'low_volatility',
            'braid_level': 0,
            'volume_ratio': 1.8,
            'rr_ratio': 1.8,
            'max_drawdown': 0.05,
            'sig_confidence': 0.7
        }
    ]
    
    # Test clustering
    clusters = clustering.cluster_trading_strands(test_strands, braid_level=0)
    
    print(f"CIL clustered {len(test_strands)} strands into {len(clusters)} clusters")
    for i, cluster in enumerate(clusters):
        print(f"Cluster {i+1}: {cluster.size} strands, key={cluster.cluster_key}")
        print(f"  Meets threshold: {clustering.cluster_meets_threshold(cluster)}")
    
    # Test strength range classification
    print("\n--- Testing Strength Range Classification ---")
    for strand in test_strands:
        strength_range = clustering.classify_strength_range(strand)
        print(f"Strand {strand['id']}: {strand['pattern_type']} -> {strength_range}")
    
    # Test R/R profile classification
    print("\n--- Testing R/R Profile Classification ---")
    for strand in test_strands:
        rr_profile = clustering.classify_rr_profile(strand)
        print(f"Strand {strand['id']}: R/R={strand['rr_ratio']}, DD={strand['max_drawdown']} -> {rr_profile}")
    
    # Test market conditions classification
    print("\n--- Testing Market Conditions Classification ---")
    for strand in test_strands:
        market_conditions = clustering.classify_market_conditions(strand)
        print(f"Strand {strand['id']}: {strand['regime']}, volatility={strand.get('volatility', 0.5)} -> {market_conditions}")


async def test_prediction_tracker():
    """Test prediction tracking system"""
    print("\n=== Testing Prediction Tracker ===")
    
    # Mock supabase manager for testing
    class MockSupabaseManager:
        def __init__(self):
            self.client = MockSupabaseClient()
    
    class MockSupabaseClient:
        def table(self, table_name):
            return MockTable()
    
    class MockTable:
        def select(self, columns):
            return self
        def eq(self, column, value):
            return self
        def order(self, column, desc=False):
            return self
        def limit(self, count):
            return self
        def execute(self):
            return MockResult()
        def update(self, data):
            return self
    
    class MockResult:
        def __init__(self):
            self.data = [{'close': 50000.0}]
    
    supabase_manager = MockSupabaseManager()
    tracker = PredictionTracker(supabase_manager)
    
    # Test prediction strand
    prediction_strand = {
        'id': 'prediction_test_1',
        'kind': 'prediction',
        'symbol': 'BTC',
        'timeframe': '1h',
        'prediction_data': {
            'entry_price': 50000.0,
            'target_price': 52000.0,
            'stop_loss': 48000.0,
            'max_time': 120  # 2 hours
        }
    }
    
    # Test tracking
    success = await tracker.track_prediction(prediction_strand)
    print(f"Prediction tracking started: {success}")
    
    # Test update with current price
    success = await tracker.update_prediction_outcome('prediction_test_1', 51000.0)
    print(f"Prediction updated: {success}")
    
    # Test getting active predictions
    active_predictions = await tracker.get_active_predictions()
    print(f"Active predictions: {len(active_predictions)}")
    
    # Test finalization
    success = await tracker.finalize_prediction('prediction_test_1', PredictionOutcome.TARGET_HIT)
    print(f"Prediction finalized: {success}")


async def test_outcome_analysis():
    """Test outcome analysis engine"""
    print("\n=== Testing Outcome Analysis Engine ===")
    
    # Mock supabase manager
    class MockSupabaseManager:
        def __init__(self):
            self.client = MockSupabaseClient()
    
    class MockSupabaseClient:
        def table(self, table_name):
            return MockTable()
    
    class MockTable:
        def select(self, columns):
            return self
        def eq(self, column, value):
            return self
        def execute(self):
            return MockResult()
    
    class MockResult:
        def __init__(self):
            self.data = []
    
    supabase_manager = MockSupabaseManager()
    engine = OutcomeAnalysisEngine(supabase_manager)
    
    # Test prediction data
    test_predictions = [
        {
            'id': 'pred_1',
            'symbol': 'BTC',
            'timeframe': '1h',
            'pattern_type': 'volume_spike',
            'strength_range': 'strong',
            'rr_profile': 'moderate',
            'market_conditions': 'moderate_volatility',
            'prediction_data': {
                'entry_price': 50000.0,
                'target_price': 52000.0,
                'stop_loss': 48000.0
            },
            'outcome_data': {
                'outcome': 'target_hit',
                'final_price': 52100.0,
                'max_drawdown': 0.02,
                'duration_minutes': 45
            }
        },
        {
            'id': 'pred_2',
            'symbol': 'BTC',
            'timeframe': '1h',
            'pattern_type': 'volume_spike',
            'strength_range': 'strong',
            'rr_profile': 'moderate',
            'market_conditions': 'moderate_volatility',
            'prediction_data': {
                'entry_price': 50000.0,
                'target_price': 52000.0,
                'stop_loss': 48000.0
            },
            'outcome_data': {
                'outcome': 'stop_hit',
                'final_price': 47900.0,
                'max_drawdown': 0.04,
                'duration_minutes': 30
            }
        }
    ]
    
    # Test analysis
    result = await engine.analyze_outcome_batch('test_cluster', test_predictions)
    print(f"Analysis result: {result}")
    
    # Test R/R optimization
    rr_result = await engine.calculate_rr_optimization(test_predictions)
    print(f"R/R optimization: {rr_result}")
    
    # Test plan evolution
    evolution = await engine.generate_plan_evolution('test_cluster', result)
    print(f"Plan evolution: {evolution}")


async def test_conditional_plan_manager():
    """Test conditional plan manager"""
    print("\n=== Testing Conditional Plan Manager ===")
    
    # Mock supabase manager
    class MockSupabaseManager:
        def __init__(self):
            self.client = MockSupabaseClient()
    
    class MockSupabaseClient:
        def table(self, table_name):
            return MockTable()
    
    class MockTable:
        def select(self, columns):
            return self
        def eq(self, column, value):
            return self
        def execute(self):
            return MockResult()
        def insert(self, data):
            return self
        def update(self, data):
            return self
    
    class MockResult:
        def __init__(self):
            self.data = [{'id': 'test_plan_1'}]
    
    supabase_manager = MockSupabaseManager()
    manager = ConditionalPlanManager(supabase_manager)
    
    # Test cluster analysis
    cluster_analysis = {
        'cluster_key': 'BTC_1h_volume_spike_strong_moderate_moderate_volatility',
        'overall_success_rate': 0.75,
        'avg_rr': 2.5,
        'sample_size': 15,
        'symbol': 'BTC',
        'timeframe': '1h',
        'pattern_type': 'volume_spike',
        'strength_range': 'strong',
        'rr_profile': 'moderate',
        'market_conditions': 'moderate_volatility'
    }
    
    # Test plan creation
    result = await manager.create_conditional_plan(cluster_analysis)
    print(f"Plan creation result: {result}")
    
    # Test plan update
    if 'plan_id' in result:
        evolution = {
            'success_rate': 0.8,
            'avg_rr': 2.8,
            'sample_size': 20,
            'recommendations': ['increase target prices', 'tighten stop losses'],
            'evolution_priority': 'medium'
        }
        update_result = await manager.update_conditional_plan(result['plan_id'], evolution)
        print(f"Plan update result: {update_result}")
    
    # Test getting active plans
    active_plans = await manager.get_active_plans()
    print(f"Active plans: {len(active_plans)}")


async def test_cil_learning_system():
    """Test integrated CIL learning system"""
    print("\n=== Testing CIL Learning System ===")
    
    # Mock supabase manager
    class MockSupabaseManager:
        def __init__(self):
            self.client = MockSupabaseClient()
    
    class MockSupabaseClient:
        def table(self, table_name):
            return MockTable()
    
    class MockTable:
        def select(self, columns):
            return self
        def eq(self, column, value):
            return self
        def order(self, column, desc=False):
            return self
        def limit(self, count):
            return self
        def execute(self):
            return MockResult()
        def update(self, data):
            return self
        def insert(self, data):
            return self
    
    class MockResult:
        def __init__(self):
            self.data = [{'close': 50000.0}]
    
    supabase_manager = MockSupabaseManager()
    learning_system = CILLearningSystem(supabase_manager)
    
    # Test prediction tracking
    prediction_strand = {
        'id': 'test_prediction_1',
        'kind': 'prediction',
        'symbol': 'BTC',
        'timeframe': '1h',
        'pattern_type': 'volume_spike',
        'strength_range': 'strong',
        'rr_profile': 'moderate',
        'market_conditions': 'moderate_volatility',
        'prediction_data': {
            'entry_price': 50000.0,
            'target_price': 52000.0,
            'stop_loss': 48000.0,
            'max_time': 120
        }
    }
    
    # Test tracking
    success = await learning_system.track_new_prediction(prediction_strand)
    print(f"Prediction tracking started: {success}")
    
    # Test getting active predictions
    active_predictions = await learning_system.get_active_predictions()
    print(f"Active predictions: {len(active_predictions)}")
    
    # Test getting active plans
    active_plans = await learning_system.get_active_plans()
    print(f"Active plans: {len(active_plans)}")


async def main():
    """Run all tests"""
    print("Starting CIL Learning System Tests")
    print("=" * 50)
    
    try:
        # Test individual components
        await test_cil_clustering()
        await test_prediction_tracker()
        await test_outcome_analysis()
        await test_conditional_plan_manager()
        await test_cil_learning_system()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\nTest failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
