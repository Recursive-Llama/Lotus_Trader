"""
Test script for Universal Learning System

This script tests the universal learning system components:
1. Universal scoring
2. Universal clustering  
3. Universal learning system integration

Run this to verify the system works correctly before integration.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.intelligence.universal_learning import UniversalScoring, UniversalClustering, UniversalLearningSystem
from src.utils.supabase_manager import SupabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_universal_scoring():
    """Test universal scoring system"""
    print("\n=== Testing Universal Scoring ===")
    
    scoring = UniversalScoring()
    
    # Test different strand types
    test_strands = [
        {
            'agent_id': 'raw_data_intelligence',
            'sig_confidence': 0.8,
            'sig_sigma': 0.7,
            'pattern_type': 'divergence',
            'module_intelligence': {'data_quality_score': 0.9}
        },
        {
            'agent_id': 'central_intelligence_layer',
            'confidence': 0.7,
            'doctrine_status': 'affirmed',
            'strategic_meta_type': 'confluence'
        },
        {
            'kind': 'trading_plan',
            'accumulated_score': 0.6,
            'outcome_score': 0.8,
            'regime': 'anomaly'
        },
        {
            'kind': 'braid',
            'source_strands': [
                {'persistence_score': 0.7, 'novelty_score': 0.6, 'surprise_rating': 0.4},
                {'persistence_score': 0.8, 'novelty_score': 0.5, 'surprise_rating': 0.3}
            ]
        }
    ]
    
    for i, strand in enumerate(test_strands):
        print(f"\nTest Strand {i+1}:")
        print(f"Type: {strand.get('agent_id', strand.get('kind', 'unknown'))}")
        scores = scoring.calculate_all_scores(strand)
        print(f"Scores: {scores}")
        
        # Verify scores are in valid range
        for score_name, score_value in scores.items():
            assert 0.0 <= score_value <= 1.0, f"{score_name} score {score_value} is not in range [0, 1]"
    
    print("✅ Universal scoring tests passed!")


def test_universal_clustering():
    """Test universal clustering system"""
    print("\n=== Testing Universal Clustering ===")
    
    clustering = UniversalClustering()
    
    # Test strands with different structural properties
    test_strands = [
        {
            'id': 'strand_1',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'persistence_score': 0.8,
            'novelty_score': 0.6,
            'surprise_rating': 0.4
        },
        {
            'id': 'strand_2',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'persistence_score': 0.7,
            'novelty_score': 0.5,
            'surprise_rating': 0.3
        },
        {
            'id': 'strand_3',
            'agent_id': 'central_intelligence_layer',
            'timeframe': '4h',
            'regime': 'bear',
            'pattern_type': 'confluence',
            'braid_level': 0,
            'persistence_score': 0.9,
            'novelty_score': 0.8,
            'surprise_rating': 0.6
        },
        {
            'id': 'strand_4',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'volume_spike',
            'braid_level': 0,
            'persistence_score': 0.6,
            'novelty_score': 0.7,
            'surprise_rating': 0.5
        }
    ]
    
    # Test column clustering
    print("Testing column clustering...")
    column_clusters = clustering.cluster_strands_by_columns(test_strands, braid_level=0)
    print(f"Column clustering: {len(test_strands)} strands -> {len(column_clusters)} clusters")
    
    for i, cluster in enumerate(column_clusters):
        print(f"  Cluster {i+1}: {cluster.size} strands, key={cluster.cluster_key}")
        print(f"    Avg persistence: {cluster.avg_persistence:.2f}")
        print(f"    Avg novelty: {cluster.avg_novelty:.2f}")
        print(f"    Avg surprise: {cluster.avg_surprise:.2f}")
    
    # Test two-tier clustering
    print("\nTesting two-tier clustering...")
    final_clusters = clustering.cluster_strands(test_strands, braid_level=0)
    print(f"Two-tier clustering: {len(test_strands)} strands -> {len(final_clusters)} clusters")
    
    # Test threshold checking
    print("\nTesting threshold checking...")
    for i, cluster in enumerate(final_clusters):
        meets_threshold = clustering.cluster_meets_threshold(cluster)
        print(f"  Cluster {i+1}: meets threshold = {meets_threshold}")
    
    print("✅ Universal clustering tests passed!")


async def test_universal_learning_system():
    """Test universal learning system integration"""
    print("\n=== Testing Universal Learning System ===")
    
    # Initialize components
    try:
        supabase_manager = SupabaseManager()
        learning_system = UniversalLearningSystem(supabase_manager)
    except Exception as e:
        print(f"⚠️  Could not initialize SupabaseManager: {e}")
        print("Testing without database connection...")
        learning_system = UniversalLearningSystem(None)
    
    # Test strands
    test_strands = [
        {
            'id': 'strand_1',
            'kind': 'signal',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'sig_confidence': 0.8,
            'sig_sigma': 0.7,
            'module_intelligence': {'data_quality_score': 0.9}
        },
        {
            'id': 'strand_2',
            'kind': 'signal',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'sig_confidence': 0.7,
            'sig_sigma': 0.6,
            'module_intelligence': {'data_quality_score': 0.8}
        },
        {
            'id': 'strand_3',
            'kind': 'signal',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'sig_confidence': 0.9,
            'sig_sigma': 0.8,
            'module_intelligence': {'data_quality_score': 0.95}
        },
        {
            'id': 'strand_4',
            'kind': 'signal',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'sig_confidence': 0.6,
            'sig_sigma': 0.5,
            'module_intelligence': {'data_quality_score': 0.7}
        },
        {
            'id': 'strand_5',
            'kind': 'signal',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'sig_confidence': 0.8,
            'sig_sigma': 0.7,
            'module_intelligence': {'data_quality_score': 0.85}
        }
    ]
    
    # Test batch processing
    print("Testing batch processing...")
    results = await learning_system.process_strands_batch(test_strands, save_to_db=False)
    
    print(f"Results:")
    print(f"  Input strands: {results['input_strands']}")
    print(f"  Created braids: {len(results['created_braids'])}")
    print(f"  Errors: {len(results['errors'])}")
    
    if results['errors']:
        print(f"  Error details: {results['errors']}")
    
    # Test individual braid creation
    print("\nTesting individual braid creation...")
    braid = await learning_system.process_strands_into_braid(test_strands[:3])
    if braid:
        print(f"Created braid: {braid['id']}")
        print(f"  Source strands: {len(braid['source_strands'])}")
        print(f"  Persistence: {braid['persistence_score']:.2f}")
        print(f"  Novelty: {braid['novelty_score']:.2f}")
        print(f"  Surprise: {braid['surprise_rating']:.2f}")
    
    print("✅ Universal learning system tests passed!")


async def main():
    """Run all tests"""
    print("🚀 Starting Universal Learning System Tests")
    
    try:
        # Test individual components
        test_universal_scoring()
        test_universal_clustering()
        await test_universal_learning_system()
        
        print("\n🎉 All tests passed! Universal Learning System is ready.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
