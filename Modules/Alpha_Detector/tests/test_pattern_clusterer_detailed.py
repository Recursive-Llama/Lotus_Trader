#!/usr/bin/env python3
"""
Detailed tests for PatternClusterer component
Tests all functionality including edge cases and error handling
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_pattern_clusterer_initialization():
    """Test PatternClusterer initialization with different parameters"""
    print("\n🧪 Testing PatternClusterer Initialization...")
    
    try:
        from llm_integration.pattern_clusterer import PatternClusterer
        
        # Test default initialization
        clusterer1 = PatternClusterer()
        print("✅ Default initialization successful")
        
        # Test custom parameters
        clusterer2 = PatternClusterer(min_cluster_size=5, max_clusters=8)
        print("✅ Custom parameters initialization successful")
        
        # Test parameter validation
        assert clusterer1.min_cluster_size == 3, "Default min_cluster_size should be 3"
        assert clusterer1.max_clusters == 10, "Default max_clusters should be 10"
        assert clusterer2.min_cluster_size == 5, "Custom min_cluster_size should be 5"
        assert clusterer2.max_clusters == 8, "Custom max_clusters should be 8"
        
        print("✅ Parameter validation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        return False

def test_feature_extraction():
    """Test feature extraction from database records"""
    print("\n🧪 Testing Feature Extraction...")
    
    try:
        from llm_integration.pattern_clusterer import PatternClusterer
        clusterer = PatternClusterer()
        
        # Test with complete record
        complete_record = {
            'id': 'test_1',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65,
            'kind': 'signal',
            'patterns': {
                'breakout_up': True,
                'volume_spike': True,
                'support_level': False
            },
            'features': {
                'rsi': 45.2,
                'macd': 0.0012,
                'bb_position': 0.7,
                'volume_ratio': 1.8,
                'volatility': 0.025
            }
        }
        
        features = clusterer.feature_extractor.extract_features(complete_record)
        print(f"✅ Complete record features: shape {features.shape}")
        assert isinstance(features, np.ndarray), "Features should be numpy array"
        assert len(features) > 0, "Features should not be empty"
        
        # Test with minimal record
        minimal_record = {
            'id': 'test_2',
            'symbol': 'ETH',
            'timeframe': '5m',
            'regime': 'ranging',
            'sig_direction': 'short',
            'sig_confidence': 0.60,
            'sig_sigma': 0.55
        }
        
        features2 = clusterer.feature_extractor.extract_features(minimal_record)
        print(f"✅ Minimal record features: shape {features2.shape}")
        assert features.shape == features2.shape, "Feature vectors should have same shape"
        
        # Test with missing fields
        incomplete_record = {
            'id': 'test_3',
            'symbol': 'SOL'
            # Missing most fields
        }
        
        features3 = clusterer.feature_extractor.extract_features(incomplete_record)
        print(f"✅ Incomplete record features: shape {features3.shape}")
        assert features.shape == features3.shape, "Feature vectors should have same shape even with missing fields"
        
        # Test with invalid data types
        invalid_record = {
            'id': 'test_4',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 'invalid',  # Should be float
            'sig_sigma': None,  # Should be float
            'patterns': 'invalid'  # Should be dict
        }
        
        features4 = clusterer.feature_extractor.extract_features(invalid_record)
        print(f"✅ Invalid record features: shape {features4.shape}")
        assert features.shape == features4.shape, "Feature vectors should have same shape even with invalid data"
        
        return True
        
    except Exception as e:
        print(f"❌ Feature extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_clustering_with_various_data():
    """Test clustering with different types of data"""
    print("\n🧪 Testing Clustering with Various Data...")
    
    try:
        from llm_integration.pattern_clusterer import PatternClusterer
        clusterer = PatternClusterer(min_cluster_size=2, max_clusters=5)
        
        # Test 1: Similar situations (should cluster together)
        similar_situations = [
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
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.70,
                'sig_sigma': 0.60,
                'patterns': {'breakout_up': True, 'volume_spike': False},
                'created_at': '2024-01-01T12:00:00Z'
            }
        ]
        
        clusters = clusterer.cluster_situations(similar_situations)
        print(f"✅ Similar situations clustering: {len(clusters)} clusters")
        assert len(clusters) > 0, "Should create at least one cluster"
        
        # Test 2: Mixed situations (should create multiple clusters)
        mixed_situations = [
            # BTC trending up
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
            # ETH ranging
            {
                'id': 'test_3',
                'symbol': 'ETH',
                'timeframe': '5m',
                'regime': 'ranging',
                'sig_direction': 'short',
                'sig_confidence': 0.60,
                'sig_sigma': 0.55,
                'patterns': {'breakout_down': True, 'volume_spike': True},
                'created_at': '2024-01-01T12:00:00Z'
            },
            {
                'id': 'test_4',
                'symbol': 'ETH',
                'timeframe': '5m',
                'regime': 'ranging',
                'sig_direction': 'short',
                'sig_confidence': 0.65,
                'sig_sigma': 0.58,
                'patterns': {'breakout_down': True, 'volume_spike': True},
                'created_at': '2024-01-01T13:00:00Z'
            },
            # SOL trending down
            {
                'id': 'test_5',
                'symbol': 'SOL',
                'timeframe': '15m',
                'regime': 'trending_down',
                'sig_direction': 'short',
                'sig_confidence': 0.70,
                'sig_sigma': 0.60,
                'patterns': {'breakout_down': True, 'volume_spike': False},
                'created_at': '2024-01-01T14:00:00Z'
            },
            {
                'id': 'test_6',
                'symbol': 'SOL',
                'timeframe': '15m',
                'regime': 'trending_down',
                'sig_direction': 'short',
                'sig_confidence': 0.75,
                'sig_sigma': 0.65,
                'patterns': {'breakout_down': True, 'volume_spike': False},
                'created_at': '2024-01-01T15:00:00Z'
            }
        ]
        
        clusters = clusterer.cluster_situations(mixed_situations)
        print(f"✅ Mixed situations clustering: {len(clusters)} clusters")
        assert len(clusters) > 1, "Should create multiple clusters for mixed situations"
        
        # Test 3: Insufficient data (should return empty)
        insufficient_data = [
            {
                'id': 'test_1',
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.75,
                'sig_sigma': 0.65
            }
        ]
        
        clusters = clusterer.cluster_situations(insufficient_data)
        print(f"✅ Insufficient data clustering: {len(clusters)} clusters")
        assert len(clusters) == 0, "Should return empty clusters for insufficient data"
        
        return True
        
    except Exception as e:
        print(f"❌ Clustering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cluster_metadata():
    """Test cluster metadata extraction"""
    print("\n🧪 Testing Cluster Metadata...")
    
    try:
        from llm_integration.pattern_clusterer import PatternClusterer
        clusterer = PatternClusterer(min_cluster_size=2)
        
        # Create test cluster
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
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.70,
                'sig_sigma': 0.60,
                'patterns': {'breakout_up': True, 'volume_spike': False},
                'created_at': '2024-01-01T12:00:00Z'
            }
        ]
        
        clusters = clusterer.cluster_situations(test_situations)
        assert len(clusters) > 0, "Should create at least one cluster"
        
        cluster = clusters[0]
        metadata = cluster.get('cluster_metadata', {})
        
        print(f"✅ Cluster metadata extracted: {len(metadata)} fields")
        
        # Check required metadata fields
        required_fields = ['symbols', 'timeframes', 'regimes', 'directions', 'avg_confidence', 'avg_strength']
        for field in required_fields:
            assert field in metadata, f"{field} should be in cluster metadata"
        
        # Check specific values
        assert 'BTC' in metadata['symbols'], "BTC should be in symbols"
        assert '1h' in metadata['timeframes'], "1h should be in timeframes"
        assert 'trending_up' in metadata['regimes'], "trending_up should be in regimes"
        assert 'long' in metadata['directions'], "long should be in directions"
        assert 0.7 <= metadata['avg_confidence'] <= 0.8, "Average confidence should be in expected range"
        assert 0.6 <= metadata['avg_strength'] <= 0.7, "Average strength should be in expected range"
        
        print("✅ Metadata validation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Cluster metadata test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_optimal_cluster_detection():
    """Test optimal cluster number detection"""
    print("\n🧪 Testing Optimal Cluster Detection...")
    
    try:
        from llm_integration.pattern_clusterer import PatternClusterer
        clusterer = PatternClusterer(min_cluster_size=2, max_clusters=5)
        
        # Create test data with clear clusters
        test_situations = [
            # Cluster 1: BTC trending up
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
            # Cluster 2: ETH ranging
            {
                'id': 'test_3',
                'symbol': 'ETH',
                'timeframe': '5m',
                'regime': 'ranging',
                'sig_direction': 'short',
                'sig_confidence': 0.60,
                'sig_sigma': 0.55,
                'patterns': {'breakout_down': True, 'volume_spike': True},
                'created_at': '2024-01-01T12:00:00Z'
            },
            {
                'id': 'test_4',
                'symbol': 'ETH',
                'timeframe': '5m',
                'regime': 'ranging',
                'sig_direction': 'short',
                'sig_confidence': 0.65,
                'sig_sigma': 0.58,
                'patterns': {'breakout_down': True, 'volume_spike': True},
                'created_at': '2024-01-01T13:00:00Z'
            },
            # Cluster 3: SOL trending down
            {
                'id': 'test_5',
                'symbol': 'SOL',
                'timeframe': '15m',
                'regime': 'trending_down',
                'sig_direction': 'short',
                'sig_confidence': 0.70,
                'sig_sigma': 0.60,
                'patterns': {'breakout_down': True, 'volume_spike': False},
                'created_at': '2024-01-01T14:00:00Z'
            },
            {
                'id': 'test_6',
                'symbol': 'SOL',
                'timeframe': '15m',
                'regime': 'trending_down',
                'sig_direction': 'short',
                'sig_confidence': 0.75,
                'sig_sigma': 0.65,
                'patterns': {'breakout_down': True, 'volume_spike': False},
                'created_at': '2024-01-01T15:00:00Z'
            }
        ]
        
        clusters = clusterer.cluster_situations(test_situations)
        print(f"✅ Optimal cluster detection: {len(clusters)} clusters created")
        
        # Should create multiple clusters for this data
        assert len(clusters) > 1, "Should create multiple clusters for diverse data"
        
        # Check cluster quality
        for i, cluster in enumerate(clusters):
            silhouette_score = cluster.get('silhouette_score', 0)
            size = cluster.get('size', 0)
            print(f"   Cluster {i}: size={size}, silhouette={silhouette_score:.3f}")
            assert size >= clusterer.min_cluster_size, f"Cluster {i} should meet minimum size requirement"
        
        return True
        
    except Exception as e:
        print(f"❌ Optimal cluster detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n🧪 Testing Edge Cases...")
    
    try:
        from llm_integration.pattern_clusterer import PatternClusterer
        clusterer = PatternClusterer(min_cluster_size=2)
        
        # Test 1: Empty data
        clusters = clusterer.cluster_situations([])
        print(f"✅ Empty data: {len(clusters)} clusters")
        assert len(clusters) == 0, "Empty data should return no clusters"
        
        # Test 2: Single record
        single_record = [{
            'id': 'test_1',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65
        }]
        
        clusters = clusterer.cluster_situations(single_record)
        print(f"✅ Single record: {len(clusters)} clusters")
        assert len(clusters) == 0, "Single record should return no clusters"
        
        # Test 3: Identical records
        identical_records = [
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
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.75,
                'sig_sigma': 0.65
            }
        ]
        
        clusters = clusterer.cluster_situations(identical_records)
        print(f"✅ Identical records: {len(clusters)} clusters")
        assert len(clusters) == 1, "Identical records should create one cluster"
        
        # Test 4: Records with missing fields
        incomplete_records = [
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
        
        clusters = clusterer.cluster_situations(incomplete_records)
        print(f"✅ Incomplete records: {len(clusters)} clusters")
        assert len(clusters) >= 0, "Incomplete records should not crash"
        
        # Test 5: Records with invalid data types
        invalid_records = [
            {
                'id': 'test_1',
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 'invalid',
                'sig_sigma': None
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
        
        clusters = clusterer.cluster_situations(invalid_records)
        print(f"✅ Invalid records: {len(clusters)} clusters")
        assert len(clusters) >= 0, "Invalid records should not crash"
        
        return True
        
    except Exception as e:
        print(f"❌ Edge cases test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pattern_feature_extraction():
    """Test pattern feature extraction specifically"""
    print("\n🧪 Testing Pattern Feature Extraction...")
    
    try:
        from llm_integration.pattern_clusterer import PatternClusterer
        clusterer = PatternClusterer()
        
        # Test with various pattern combinations
        test_cases = [
            {
                'name': 'All patterns true',
                'patterns': {
                    'breakout_up': True,
                    'breakout_down': True,
                    'support_level': True,
                    'resistance_level': True,
                    'bullish_divergence': True,
                    'bearish_divergence': True,
                    'volume_spike': True
                }
            },
            {
                'name': 'No patterns',
                'patterns': {
                    'breakout_up': False,
                    'breakout_down': False,
                    'support_level': False,
                    'resistance_level': False,
                    'bullish_divergence': False,
                    'bearish_divergence': False,
                    'volume_spike': False
                }
            },
            {
                'name': 'Mixed patterns',
                'patterns': {
                    'breakout_up': True,
                    'breakout_down': False,
                    'support_level': True,
                    'resistance_level': False,
                    'bullish_divergence': False,
                    'bearish_divergence': True,
                    'volume_spike': True
                }
            },
            {
                'name': 'Missing patterns field',
                'patterns': {}
            }
        ]
        
        for test_case in test_cases:
            record = {
                'id': 'test',
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'trending_up',
                'sig_direction': 'long',
                'sig_confidence': 0.75,
                'sig_sigma': 0.65,
                'patterns': test_case['patterns']
            }
            
            pattern_features = clusterer.feature_extractor._extract_pattern_features(record)
            print(f"✅ {test_case['name']}: {len(pattern_features)} pattern features")
            assert len(pattern_features) == 7, "Should extract 7 pattern features"
            
            # Check that all features are 0 or 1
            for feature in pattern_features:
                assert feature in [0.0, 1.0], "Pattern features should be 0 or 1"
        
        return True
        
    except Exception as e:
        print(f"❌ Pattern feature extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all PatternClusterer tests"""
    print("🧪 PatternClusterer Comprehensive Tests")
    print("=" * 50)
    
    tests = [
        ("Initialization", test_pattern_clusterer_initialization),
        ("Feature Extraction", test_feature_extraction),
        ("Clustering with Various Data", test_clustering_with_various_data),
        ("Cluster Metadata", test_cluster_metadata),
        ("Optimal Cluster Detection", test_optimal_cluster_detection),
        ("Edge Cases", test_edge_cases),
        ("Pattern Feature Extraction", test_pattern_feature_extraction)
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
    print("\n" + "=" * 50)
    print("📊 PatternClusterer Test Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:30} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All PatternClusterer tests passed!")
    else:
        print("⚠️  Some PatternClusterer tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
