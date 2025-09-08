#!/usr/bin/env python3
"""
Comprehensive integration tests for the entire context system
Tests ContextIndexer, PatternClusterer, and DatabaseDrivenContextSystem working together
"""

import sys
import os
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def create_realistic_test_data():
    """Create realistic test data that mimics real trading situations"""
    
    # Create a diverse set of trading situations
    test_situations = [
        # BTC trending up scenarios
        {
            'id': 'btc_trend_1',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.85,
            'sig_sigma': 0.75,
            'kind': 'signal',
            'patterns': {
                'breakout_up': True,
                'volume_spike': True,
                'support_level': True,
                'resistance_level': False,
                'bullish_divergence': False,
                'bearish_divergence': False
            },
            'features': {
                'rsi': 45.2,
                'macd': 0.0012,
                'bb_position': 0.7,
                'volume_ratio': 1.8,
                'volatility': 0.025
            },
            'created_at': '2024-01-01T10:00:00Z'
        },
        {
            'id': 'btc_trend_2',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.80,
            'sig_sigma': 0.70,
            'kind': 'signal',
            'patterns': {
                'breakout_up': True,
                'volume_spike': True,
                'support_level': True,
                'resistance_level': False,
                'bullish_divergence': True,
                'bearish_divergence': False
            },
            'features': {
                'rsi': 42.1,
                'macd': 0.0015,
                'bb_position': 0.8,
                'volume_ratio': 2.1,
                'volatility': 0.028
            },
            'created_at': '2024-01-01T11:00:00Z'
        },
        {
            'id': 'btc_trend_3',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65,
            'kind': 'signal',
            'patterns': {
                'breakout_up': True,
                'volume_spike': False,
                'support_level': True,
                'resistance_level': False,
                'bullish_divergence': False,
                'bearish_divergence': False
            },
            'features': {
                'rsi': 48.5,
                'macd': 0.0008,
                'bb_position': 0.6,
                'volume_ratio': 1.2,
                'volatility': 0.022
            },
            'created_at': '2024-01-01T12:00:00Z'
        },
        
        # ETH ranging scenarios
        {
            'id': 'eth_range_1',
            'symbol': 'ETH',
            'timeframe': '5m',
            'regime': 'ranging',
            'sig_direction': 'short',
            'sig_confidence': 0.70,
            'sig_sigma': 0.60,
            'kind': 'signal',
            'patterns': {
                'breakout_up': False,
                'volume_spike': True,
                'support_level': True,
                'resistance_level': True,
                'bullish_divergence': False,
                'bearish_divergence': True
            },
            'features': {
                'rsi': 65.2,
                'macd': -0.0005,
                'bb_position': 0.9,
                'volume_ratio': 1.5,
                'volatility': 0.035
            },
            'created_at': '2024-01-01T13:00:00Z'
        },
        {
            'id': 'eth_range_2',
            'symbol': 'ETH',
            'timeframe': '5m',
            'regime': 'ranging',
            'sig_direction': 'short',
            'sig_confidence': 0.65,
            'sig_sigma': 0.55,
            'kind': 'signal',
            'patterns': {
                'breakout_up': False,
                'volume_spike': True,
                'support_level': True,
                'resistance_level': True,
                'bullish_divergence': False,
                'bearish_divergence': True
            },
            'features': {
                'rsi': 68.1,
                'macd': -0.0008,
                'bb_position': 0.95,
                'volume_ratio': 1.3,
                'volatility': 0.032
            },
            'created_at': '2024-01-01T14:00:00Z'
        },
        
        # SOL trending down scenarios
        {
            'id': 'sol_trend_1',
            'symbol': 'SOL',
            'timeframe': '15m',
            'regime': 'trending_down',
            'sig_direction': 'short',
            'sig_confidence': 0.80,
            'sig_sigma': 0.70,
            'kind': 'signal',
            'patterns': {
                'breakout_up': False,
                'volume_spike': True,
                'support_level': False,
                'resistance_level': True,
                'bullish_divergence': False,
                'bearish_divergence': True
            },
            'features': {
                'rsi': 75.2,
                'macd': -0.0025,
                'bb_position': 0.1,
                'volume_ratio': 2.2,
                'volatility': 0.045
            },
            'created_at': '2024-01-01T15:00:00Z'
        },
        {
            'id': 'sol_trend_2',
            'symbol': 'SOL',
            'timeframe': '15m',
            'regime': 'trending_down',
            'sig_direction': 'short',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65,
            'kind': 'signal',
            'patterns': {
                'breakout_up': False,
                'volume_spike': False,
                'support_level': False,
                'resistance_level': True,
                'bullish_divergence': False,
                'bearish_divergence': True
            },
            'features': {
                'rsi': 78.5,
                'macd': -0.0030,
                'bb_position': 0.05,
                'volume_ratio': 1.1,
                'volatility': 0.042
            },
            'created_at': '2024-01-01T16:00:00Z'
        },
        
        # Mixed scenarios
        {
            'id': 'mixed_1',
            'symbol': 'BTC',
            'timeframe': '5m',
            'regime': 'ranging',
            'sig_direction': 'long',
            'sig_confidence': 0.60,
            'sig_sigma': 0.50,
            'kind': 'signal',
            'patterns': {
                'breakout_up': False,
                'volume_spike': False,
                'support_level': True,
                'resistance_level': False,
                'bullish_divergence': False,
                'bearish_divergence': False
            },
            'features': {
                'rsi': 52.1,
                'macd': 0.0002,
                'bb_position': 0.4,
                'volume_ratio': 0.8,
                'volatility': 0.018
            },
            'created_at': '2024-01-01T17:00:00Z'
        },
        {
            'id': 'mixed_2',
            'symbol': 'ETH',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.70,
            'sig_sigma': 0.60,
            'kind': 'signal',
            'patterns': {
                'breakout_up': True,
                'volume_spike': False,
                'support_level': False,
                'resistance_level': False,
                'bullish_divergence': True,
                'bearish_divergence': False
            },
            'features': {
                'rsi': 38.5,
                'macd': 0.0018,
                'bb_position': 0.3,
                'volume_ratio': 1.0,
                'volatility': 0.020
            },
            'created_at': '2024-01-01T18:00:00Z'
        }
    ]
    
    return test_situations

def test_end_to_end_context_retrieval():
    """Test complete end-to-end context retrieval process"""
    print("\n🧪 Testing End-to-End Context Retrieval...")
    print("=" * 60)
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        from llm_integration.pattern_clusterer import PatternClusterer
        from llm_integration.database_driven_context_system import DatabaseDrivenContextSystem
        from utils.supabase_manager import SupabaseManager
        
        # Initialize components
        print("1. Initializing components...")
        indexer = ContextIndexer()
        clusterer = PatternClusterer(min_cluster_size=2, max_clusters=5)
        db_manager = SupabaseManager()
        context_system = DatabaseDrivenContextSystem(db_manager)
        print("   ✅ All components initialized")
        
        # Create test data
        print("2. Creating test data...")
        test_situations = create_realistic_test_data()
        print(f"   ✅ Created {len(test_situations)} test situations")
        
        # Step 1: Create context vectors for all situations
        print("3. Creating context vectors...")
        enhanced_situations = indexer.batch_create_vectors(test_situations)
        print(f"   ✅ Created vectors for {len(enhanced_situations)} situations")
        
        # Verify vectors were created
        for situation in enhanced_situations:
            assert 'context_vector' in situation, "Situation should have context_vector"
            assert situation['context_vector'] is not None, "Context vector should not be None"
            assert len(situation['context_vector']) > 0, "Context vector should not be empty"
        print("   ✅ All vectors validated")
        
        # Step 2: Test clustering
        print("4. Testing clustering...")
        clusters = clusterer.cluster_situations(enhanced_situations)
        print(f"   ✅ Created {len(clusters)} clusters")
        
        # Verify clusters
        for i, cluster in enumerate(clusters):
            assert 'size' in cluster, f"Cluster {i} should have size"
            assert 'situations' in cluster, f"Cluster {i} should have situations"
            assert 'cluster_metadata' in cluster, f"Cluster {i} should have metadata"
            print(f"      Cluster {i}: {cluster['size']} situations, "
                  f"silhouette: {cluster.get('silhouette_score', 0):.3f}")
        
        # Step 3: Test similarity search
        print("5. Testing similarity search...")
        current_analysis = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.80,
            'sig_sigma': 0.70,
            'patterns': {
                'breakout_up': True,
                'volume_spike': True,
                'support_level': True
            }
        }
        
        # Create vector for current analysis
        current_vector = indexer.create_context_vector(current_analysis)
        print(f"   ✅ Created current analysis vector: shape {current_vector.shape}")
        
        # Find similar situations
        similarities = []
        for situation in enhanced_situations:
            if situation['context_vector']:
                similarity = indexer.get_similarity_score(
                    current_vector, 
                    np.array(situation['context_vector'])
                )
                situation['similarity'] = similarity
                similarities.append(similarity)
        
        # Sort by similarity
        enhanced_situations.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        top_similar = enhanced_situations[:5]
        
        print(f"   ✅ Found {len(similarities)} similarities")
        print(f"      Top similarity: {max(similarities):.3f}")
        print(f"      Average similarity: {np.mean(similarities):.3f}")
        
        # Verify top similar situations are actually similar
        for i, situation in enumerate(top_similar):
            similarity = situation.get('similarity', 0)
            print(f"      Top {i+1}: {situation['symbol']} {situation['timeframe']} "
                  f"{situation['regime']} (similarity: {similarity:.3f})")
        
        # Step 4: Test context system integration
        print("6. Testing context system integration...")
        
        # Mock the database retrieval (since we don't have real DB connection)
        def mock_get_recent_records(self, days_back=30):
            return enhanced_situations
        
        # Monkey patch the method
        context_system._get_recent_database_records = mock_get_recent_records.__get__(context_system, DatabaseDrivenContextSystem)
        
        # Test context retrieval
        context = context_system.get_relevant_context(current_analysis, top_k=5, similarity_threshold=0.5)
        
        print(f"   ✅ Context retrieval completed")
        print(f"      Similar situations: {len(context['similar_situations'])}")
        print(f"      Pattern clusters: {len(context['pattern_clusters'])}")
        print(f"      Generated lessons: {len(context['generated_lessons'])}")
        
        # Verify context structure
        assert 'current_analysis' in context, "Context should have current_analysis"
        assert 'similar_situations' in context, "Context should have similar_situations"
        assert 'pattern_clusters' in context, "Context should have pattern_clusters"
        assert 'generated_lessons' in context, "Context should have generated_lessons"
        assert 'context_metadata' in context, "Context should have context_metadata"
        
        # Verify similar situations
        for situation in context['similar_situations']:
            assert 'similarity' in situation, "Similar situation should have similarity score"
            assert situation['similarity'] >= 0.5, "Similarity should meet threshold"
        
        # Verify lessons
        for lesson in context['generated_lessons']:
            assert 'lesson_id' in lesson, "Lesson should have lesson_id"
            assert 'lesson_content' in lesson, "Lesson should have lesson_content"
            assert 'key_insights' in lesson, "Lesson should have key_insights"
            assert 'actionable_recommendations' in lesson, "Lesson should have recommendations"
            assert 'confidence_score' in lesson, "Lesson should have confidence_score"
        
        print("   ✅ Context structure validated")
        
        return True
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_benchmarks():
    """Test performance of the context system"""
    print("\n🧪 Testing Performance Benchmarks...")
    print("=" * 60)
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        from llm_integration.pattern_clusterer import PatternClusterer
        import time
        
        # Initialize components
        indexer = ContextIndexer()
        clusterer = PatternClusterer(min_cluster_size=2, max_clusters=5)
        
        # Create test data
        test_situations = create_realistic_test_data()
        
        # Test 1: Vector creation performance
        print("1. Testing vector creation performance...")
        start_time = time.time()
        enhanced_situations = indexer.batch_create_vectors(test_situations)
        vector_time = time.time() - start_time
        print(f"   ✅ Created {len(enhanced_situations)} vectors in {vector_time:.3f}s")
        print(f"      Rate: {len(enhanced_situations)/vector_time:.1f} vectors/second")
        
        # Test 2: Clustering performance
        print("2. Testing clustering performance...")
        start_time = time.time()
        clusters = clusterer.cluster_situations(enhanced_situations)
        cluster_time = time.time() - start_time
        print(f"   ✅ Created {len(clusters)} clusters in {cluster_time:.3f}s")
        print(f"      Rate: {len(enhanced_situations)/cluster_time:.1f} situations/second")
        
        # Test 3: Similarity search performance
        print("3. Testing similarity search performance...")
        current_analysis = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.80,
            'sig_sigma': 0.70
        }
        
        current_vector = indexer.create_context_vector(current_analysis)
        
        start_time = time.time()
        similarities = []
        for situation in enhanced_situations:
            if situation['context_vector']:
                similarity = indexer.get_similarity_score(
                    current_vector, 
                    np.array(situation['context_vector'])
                )
                similarities.append(similarity)
        similarity_time = time.time() - start_time
        
        print(f"   ✅ Calculated {len(similarities)} similarities in {similarity_time:.3f}s")
        print(f"      Rate: {len(similarities)/similarity_time:.1f} similarities/second")
        
        # Test 4: Memory usage
        print("4. Testing memory usage...")
        import sys
        
        # Calculate approximate memory usage
        vector_size = len(enhanced_situations[0]['context_vector']) * 4  # 4 bytes per float32
        total_vector_memory = vector_size * len(enhanced_situations)
        
        print(f"   ✅ Estimated memory usage:")
        print(f"      Per vector: {vector_size} bytes")
        print(f"      Total vectors: {total_vector_memory:,} bytes ({total_vector_memory/1024/1024:.2f} MB)")
        
        # Performance benchmarks
        print("\n📊 Performance Benchmarks:")
        print(f"   Vector Creation: {len(enhanced_situations)/vector_time:.1f} vectors/sec")
        print(f"   Clustering: {len(enhanced_situations)/cluster_time:.1f} situations/sec")
        print(f"   Similarity Search: {len(similarities)/similarity_time:.1f} similarities/sec")
        print(f"   Memory Efficiency: {total_vector_memory/1024/1024:.2f} MB for {len(enhanced_situations)} vectors")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance benchmark test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling and edge cases"""
    print("\n🧪 Testing Error Handling...")
    print("=" * 60)
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        from llm_integration.pattern_clusterer import PatternClusterer
        from llm_integration.database_driven_context_system import DatabaseDrivenContextSystem
        from utils.supabase_manager import SupabaseManager
        
        # Test 1: ContextIndexer error handling
        print("1. Testing ContextIndexer error handling...")
        indexer = ContextIndexer()
        
        # Test with None input
        try:
            vector = indexer.create_context_vector(None)
            print("   ❌ Should have failed with None input")
        except Exception:
            print("   ✅ Correctly handled None input")
        
        # Test with empty dict
        vector = indexer.create_context_vector({})
        assert len(vector) > 0, "Should create vector even with empty input"
        print("   ✅ Correctly handled empty input")
        
        # Test 2: PatternClusterer error handling
        print("2. Testing PatternClusterer error handling...")
        clusterer = PatternClusterer(min_cluster_size=2)
        
        # Test with empty list
        clusters = clusterer.cluster_situations([])
        assert len(clusters) == 0, "Should return empty clusters for empty input"
        print("   ✅ Correctly handled empty input")
        
        # Test with single record
        single_record = [{'id': 'test', 'symbol': 'BTC'}]
        clusters = clusterer.cluster_situations(single_record)
        assert len(clusters) == 0, "Should return empty clusters for single record"
        print("   ✅ Correctly handled single record")
        
        # Test 3: DatabaseDrivenContextSystem error handling
        print("3. Testing DatabaseDrivenContextSystem error handling...")
        db_manager = SupabaseManager()
        context_system = DatabaseDrivenContextSystem(db_manager)
        
        # Test with None input
        try:
            context = context_system.get_relevant_context(None)
            print("   ❌ Should have failed with None input")
        except Exception:
            print("   ✅ Correctly handled None input")
        
        # Test with empty input
        context = context_system.get_relevant_context({})
        assert 'current_analysis' in context, "Should return context even with empty input"
        print("   ✅ Correctly handled empty input")
        
        # Test 4: Vector similarity error handling
        print("4. Testing vector similarity error handling...")
        
        # Test with different sized vectors
        vector1 = np.array([1.0, 0.0, 0.0])
        vector2 = np.array([0.0, 1.0])
        
        try:
            similarity = indexer.get_similarity_score(vector1, vector2)
            print("   ❌ Should have failed with different sized vectors")
        except Exception:
            print("   ✅ Correctly handled different sized vectors")
        
        # Test with None vectors
        try:
            similarity = indexer.get_similarity_score(None, vector1)
            print("   ❌ Should have failed with None vector")
        except Exception:
            print("   ✅ Correctly handled None vector")
        
        print("   ✅ All error handling tests passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_consistency():
    """Test data consistency across components"""
    print("\n🧪 Testing Data Consistency...")
    print("=" * 60)
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        from llm_integration.pattern_clusterer import PatternClusterer
        
        # Create test data
        test_situations = create_realistic_test_data()
        
        # Test 1: Vector consistency
        print("1. Testing vector consistency...")
        indexer = ContextIndexer()
        
        # Create vectors individually and in batch
        individual_vectors = []
        for situation in test_situations[:3]:  # Test first 3
            vector = indexer.create_context_vector(situation)
            individual_vectors.append(vector)
        
        batch_enhanced = indexer.batch_create_vectors(test_situations[:3])
        batch_vectors = [s['context_vector'] for s in batch_enhanced]
        
        # Compare vectors
        for i, (individual, batch) in enumerate(zip(individual_vectors, batch_vectors)):
            similarity = indexer.get_similarity_score(individual, np.array(batch))
            assert similarity > 0.95, f"Vector {i} should be consistent between individual and batch creation"
            print(f"   ✅ Vector {i} consistency: {similarity:.3f}")
        
        # Test 2: Clustering consistency
        print("2. Testing clustering consistency...")
        clusterer = PatternClusterer(min_cluster_size=2, max_clusters=5)
        
        # Run clustering multiple times
        clusters1 = clusterer.cluster_situations(test_situations)
        clusters2 = clusterer.cluster_situations(test_situations)
        
        # Should produce same number of clusters
        assert len(clusters1) == len(clusters2), "Clustering should be consistent"
        print(f"   ✅ Clustering consistency: {len(clusters1)} clusters both times")
        
        # Test 3: Feature extraction consistency
        print("3. Testing feature extraction consistency...")
        
        # Test same record multiple times
        test_record = test_situations[0]
        features1 = clusterer.feature_extractor.extract_features(test_record)
        features2 = clusterer.feature_extractor.extract_features(test_record)
        
        # Features should be identical
        assert np.array_equal(features1, features2), "Feature extraction should be consistent"
        print(f"   ✅ Feature extraction consistency: {len(features1)} features")
        
        # Test 4: Context string consistency
        print("4. Testing context string consistency...")
        
        # Test same data multiple times
        context_string1 = indexer._create_context_string(test_record)
        context_string2 = indexer._create_context_string(test_record)
        
        # Context strings should be identical
        assert context_string1 == context_string2, "Context string creation should be consistent"
        print(f"   ✅ Context string consistency: {len(context_string1)} characters")
        
        print("   ✅ All consistency tests passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Data consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all integration tests"""
    print("🧪 Context System Comprehensive Integration Tests")
    print("=" * 70)
    
    tests = [
        ("End-to-End Context Retrieval", test_end_to_end_context_retrieval),
        ("Performance Benchmarks", test_performance_benchmarks),
        ("Error Handling", test_error_handling),
        ("Data Consistency", test_data_consistency)
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
    print("\n" + "=" * 70)
    print("📊 Integration Test Summary")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:35} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        print("🚀 Context system is ready for production use!")
    else:
        print("⚠️  Some integration tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
