#!/usr/bin/env python3
"""
Test script for Phase 1A Day 2: Intelligent Context System
Tests ContextIndexer, PatternClusterer, and DatabaseDrivenContextSystem
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_context_indexer():
    """Test the ContextIndexer functionality"""
    print("\n🧪 Testing ContextIndexer...")
    print("=" * 50)
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        
        # Initialize context indexer
        indexer = ContextIndexer()
        print("✅ ContextIndexer initialized successfully")
        
        # Test data
        test_analysis = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65,
            'patterns': {
                'breakout_up': True,
                'volume_spike': True,
                'support_level': False
            },
            'features': {
                'rsi': 45.2,
                'macd': 0.0012,
                'bb_position': 0.7,
                'volume_ratio': 1.8
            }
        }
        
        # Test context vector creation
        context_vector = indexer.create_context_vector(test_analysis)
        print(f"✅ Context vector created: shape {context_vector.shape}")
        
        # Test context string creation
        context_string = indexer._create_context_string(test_analysis)
        print(f"✅ Context string created: {len(context_string)} characters")
        print(f"   Preview: {context_string[:100]}...")
        
        # Test similarity calculation
        test_vector2 = indexer.create_context_vector({
            'symbol': 'ETH',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.80,
            'sig_sigma': 0.70
        })
        
        similarity = indexer.get_similarity_score(context_vector, test_vector2)
        print(f"✅ Similarity calculation: {similarity:.3f}")
        
        # Test batch processing
        test_records = [test_analysis, {
            'symbol': 'ETH',
            'timeframe': '5m',
            'regime': 'ranging',
            'sig_direction': 'short',
            'sig_confidence': 0.60,
            'sig_sigma': 0.55
        }]
        
        enhanced_records = indexer.batch_create_vectors(test_records)
        print(f"✅ Batch processing: {len(enhanced_records)} records processed")
        
        return True
        
    except Exception as e:
        print(f"❌ ContextIndexer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pattern_clusterer():
    """Test the PatternClusterer functionality"""
    print("\n🧪 Testing PatternClusterer...")
    print("=" * 50)
    
    try:
        from llm_integration.pattern_clusterer import PatternClusterer
        
        # Initialize pattern clusterer
        clusterer = PatternClusterer(min_cluster_size=2, max_clusters=5)
        print("✅ PatternClusterer initialized successfully")
        
        # Test data - similar situations
        test_situations = [
            {
                'id': 'test_1',
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.75,
                'sig_sigma': 0.65,
                'patterns': {'breakout_up': True, 'volume_spike': True},
                'created_at': '2024-01-01T10:00:00Z'
            },
            {
                'id': 'test_2',
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.80,
                'sig_sigma': 0.70,
                'patterns': {'breakout_up': True, 'volume_spike': True},
                'created_at': '2024-01-01T11:00:00Z'
            },
            {
                'id': 'test_3',
                'symbol': 'ETH',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.70,
                'sig_sigma': 0.60,
                'patterns': {'breakout_up': True, 'volume_spike': False},
                'created_at': '2024-01-01T12:00:00Z'
            },
            {
                'id': 'test_4',
                'symbol': 'SOL',
                'timeframe': '5m',
                'regime': 'ranging',
                'sig_direction': 'short',
                'sig_confidence': 0.60,
                'sig_sigma': 0.55,
                'patterns': {'breakout_down': True, 'volume_spike': True},
                'created_at': '2024-01-01T13:00:00Z'
            },
            {
                'id': 'test_5',
                'symbol': 'SOL',
                'timeframe': '5m',
                'regime': 'ranging',
                'sig_direction': 'short',
                'sig_confidence': 0.65,
                'sig_sigma': 0.58,
                'patterns': {'breakout_down': True, 'volume_spike': True},
                'created_at': '2024-01-01T14:00:00Z'
            }
        ]
        
        # Test clustering
        clusters = clusterer.cluster_situations(test_situations)
        print(f"✅ Clustering completed: {len(clusters)} clusters created")
        
        for i, cluster in enumerate(clusters):
            print(f"   Cluster {i}: {cluster['size']} situations, "
                  f"silhouette: {cluster['silhouette_score']:.3f}")
            
            metadata = cluster.get('cluster_metadata', {})
            if metadata:
                print(f"      Symbols: {metadata.get('symbols', [])}")
                print(f"      Regimes: {metadata.get('regimes', [])}")
                print(f"      Avg Confidence: {metadata.get('avg_confidence', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ PatternClusterer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_driven_context_system():
    """Test the DatabaseDrivenContextSystem functionality"""
    print("\n🧪 Testing DatabaseDrivenContextSystem...")
    print("=" * 50)
    
    try:
        from llm_integration.database_driven_context_system import DatabaseDrivenContextSystem
        from utils.supabase_manager import SupabaseManager
        
        # Initialize database manager (without connection for testing)
        db_manager = SupabaseManager()
        print("✅ Database manager initialized")
        
        # Initialize context system
        context_system = DatabaseDrivenContextSystem(db_manager)
        print("✅ DatabaseDrivenContextSystem initialized successfully")
        
        # Test current analysis
        current_analysis = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65,
            'patterns': {
                'breakout_up': True,
                'volume_spike': True
            }
        }
        
        # Test context retrieval (will return empty context since no DB connection)
        print("⚠️  Testing context retrieval (no DB connection - will return empty context)")
        context = context_system.get_relevant_context(current_analysis)
        
        print(f"✅ Context retrieval completed")
        print(f"   Similar situations: {len(context['similar_situations'])}")
        print(f"   Pattern clusters: {len(context['pattern_clusters'])}")
        print(f"   Generated lessons: {len(context['generated_lessons'])}")
        
        # Test context indexing
        test_records = [
            {
                'id': 'test_1',
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.75,
                'sig_sigma': 0.65
            },
            {
                'id': 'test_2',
                'symbol': 'ETH',
                'timeframe': '5m',
                'regime': 'ranging',
                'sig_direction': 'short',
                'sig_confidence': 0.60,
                'sig_sigma': 0.55
            }
        ]
        
        print("⚠️  Testing context indexing (no DB connection - will skip storage)")
        enhanced_records = context_system.index_database_records(test_records)
        print(f"✅ Context indexing completed: {len(enhanced_records)} records processed")
        
        return True
        
    except Exception as e:
        print(f"❌ DatabaseDrivenContextSystem test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test integration between components"""
    print("\n🧪 Testing Component Integration...")
    print("=" * 50)
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        from llm_integration.pattern_clusterer import PatternClusterer
        
        # Initialize components
        indexer = ContextIndexer()
        clusterer = PatternClusterer(min_cluster_size=2)
        print("✅ Components initialized")
        
        # Create test data
        test_situations = [
            {
                'id': 'test_1',
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.75,
                'sig_sigma': 0.65,
                'patterns': {'breakout_up': True, 'volume_spike': True}
            },
            {
                'id': 'test_2',
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.80,
                'sig_sigma': 0.70,
                'patterns': {'breakout_up': True, 'volume_spike': True}
            },
            {
                'id': 'test_3',
                'symbol': 'ETH',
                'timeframe': '5m',
                'regime': 'ranging',
                'sig_direction': 'short',
                'sig_confidence': 0.60,
                'sig_sigma': 0.55,
                'patterns': {'breakout_down': True, 'volume_spike': True}
            }
        ]
        
        # Test end-to-end flow
        print("1. Creating context vectors...")
        enhanced_situations = indexer.batch_create_vectors(test_situations)
        print(f"   ✅ {len(enhanced_situations)} vectors created")
        
        print("2. Clustering situations...")
        clusters = clusterer.cluster_situations(enhanced_situations)
        print(f"   ✅ {len(clusters)} clusters created")
        
        print("3. Testing similarity calculation...")
        if len(enhanced_situations) >= 2:
            vector1 = enhanced_situations[0]['context_vector']
            vector2 = enhanced_situations[1]['context_vector']
            similarity = indexer.get_similarity_score(vector1, vector2)
            print(f"   ✅ Similarity: {similarity:.3f}")
        
        print("✅ Integration test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Phase 1A Day 2: Intelligent Context System Tests")
    print("=" * 60)
    
    tests = [
        ("ContextIndexer", test_context_indexer),
        ("PatternClusterer", test_pattern_clusterer),
        ("DatabaseDrivenContextSystem", test_database_driven_context_system),
        ("Integration", test_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:30} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Intelligent Context System is working correctly.")
        print("🚀 Ready to proceed to Day 3: LLM Lesson Generation")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
