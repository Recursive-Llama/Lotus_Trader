#!/usr/bin/env python3
"""
Detailed tests for ContextIndexer component
Tests all functionality including edge cases and error handling
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_context_indexer_initialization():
    """Test ContextIndexer initialization with different models"""
    print("\n🧪 Testing ContextIndexer Initialization...")
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        
        # Test default initialization
        indexer1 = ContextIndexer()
        print("✅ Default initialization successful")
        
        # Test custom model initialization
        indexer2 = ContextIndexer("all-MiniLM-L6-v2")
        print("✅ Custom model initialization successful")
        
        # Test model loading
        assert indexer1.embedding_model is not None, "Embedding model should be loaded"
        assert indexer2.embedding_model is not None, "Custom embedding model should be loaded"
        print("✅ Embedding models loaded correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        return False

def test_context_string_creation():
    """Test context string creation with various data types"""
    print("\n🧪 Testing Context String Creation...")
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        indexer = ContextIndexer()
        
        # Test 1: Basic data
        basic_data = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65
        }
        
        context_string = indexer._create_context_string(basic_data)
        print(f"✅ Basic context string: {len(context_string)} chars")
        assert 'BTC' in context_string, "Symbol should be in context string"
        assert '1h' in context_string, "Timeframe should be in context string"
        
        # Test 2: With patterns
        data_with_patterns = {
            'symbol': 'ETH',
            'timeframe': '5m',
            'regime': 'ranging',
            'sig_direction': 'short',
            'sig_confidence': 0.60,
            'sig_sigma': 0.55,
            'patterns': {
                'breakout_down': True,
                'volume_spike': True,
                'support_level': False
            }
        }
        
        context_string = indexer._create_context_string(data_with_patterns)
        print(f"✅ Pattern context string: {len(context_string)} chars")
        assert 'breakout_down' in context_string, "Patterns should be in context string"
        
        # Test 3: With features
        data_with_features = {
            'symbol': 'SOL',
            'timeframe': '15m',
            'regime': 'trending_down',
            'sig_direction': 'short',
            'sig_confidence': 0.80,
            'sig_sigma': 0.70,
            'features': {
                'rsi': 45.2,
                'macd': 0.0012,
                'bb_position': 0.7,
                'volume_ratio': 1.8,
                'volatility': 0.025
            }
        }
        
        context_string = indexer._create_context_string(data_with_features)
        print(f"✅ Feature context string: {len(context_string)} chars")
        assert 'rsi' in context_string, "Features should be in context string"
        
        # Test 4: Empty data
        empty_data = {}
        context_string = indexer._create_context_string(empty_data)
        print(f"✅ Empty context string: {len(context_string)} chars")
        assert len(context_string) == 0, "Empty data should produce empty string"
        
        # Test 5: Mixed data types
        mixed_data = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65,
            'patterns': ['breakout_up', 'volume_spike'],
            'features': {
                'rsi': 45.2,
                'macd': 0.0012
            },
            'market_conditions': {
                'volatility': 'high',
                'volume': 'above_average'
            }
        }
        
        context_string = indexer._create_context_string(mixed_data)
        print(f"✅ Mixed context string: {len(context_string)} chars")
        assert 'breakout_up' in context_string, "List patterns should be in context string"
        assert 'volatility' in context_string, "Market conditions should be in context string"
        
        return True
        
    except Exception as e:
        print(f"❌ Context string creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_creation():
    """Test vector creation with various data"""
    print("\n🧪 Testing Vector Creation...")
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        indexer = ContextIndexer()
        
        # Test 1: Basic vector creation
        test_data = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65
        }
        
        vector = indexer.create_context_vector(test_data)
        print(f"✅ Basic vector created: shape {vector.shape}")
        assert isinstance(vector, np.ndarray), "Vector should be numpy array"
        assert len(vector) > 0, "Vector should not be empty"
        
        # Test 2: Different data should produce different vectors
        test_data2 = {
            'symbol': 'ETH',
            'timeframe': '5m',
            'regime': 'ranging',
            'sig_direction': 'short',
            'sig_confidence': 0.60,
            'sig_sigma': 0.55
        }
        
        vector2 = indexer.create_context_vector(test_data2)
        print(f"✅ Second vector created: shape {vector2.shape}")
        assert vector.shape == vector2.shape, "Vectors should have same shape"
        
        # Test 3: Similar data should produce similar vectors
        test_data3 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.80,  # Slightly different
            'sig_sigma': 0.70       # Slightly different
        }
        
        vector3 = indexer.create_context_vector(test_data3)
        similarity = indexer.get_similarity_score(vector, vector3)
        print(f"✅ Similar data similarity: {similarity:.3f}")
        assert similarity > 0.8, "Similar data should have high similarity"
        
        # Test 4: Very different data should produce different vectors
        similarity2 = indexer.get_similarity_score(vector, vector2)
        print(f"✅ Different data similarity: {similarity2:.3f}")
        assert similarity2 < similarity, "Different data should have lower similarity"
        
        return True
        
    except Exception as e:
        print(f"❌ Vector creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_similarity_calculation():
    """Test similarity calculation with edge cases"""
    print("\n🧪 Testing Similarity Calculation...")
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        indexer = ContextIndexer()
        
        # Create test vectors
        vector1 = np.array([1.0, 0.0, 0.0])
        vector2 = np.array([0.0, 1.0, 0.0])
        vector3 = np.array([1.0, 0.0, 0.0])  # Same as vector1
        vector4 = np.array([0.0, 0.0, 0.0])  # Zero vector
        
        # Test 1: Identical vectors
        similarity = indexer.get_similarity_score(vector1, vector3)
        print(f"✅ Identical vectors similarity: {similarity:.3f}")
        assert abs(similarity - 1.0) < 0.001, "Identical vectors should have similarity 1.0"
        
        # Test 2: Orthogonal vectors
        similarity = indexer.get_similarity_score(vector1, vector2)
        print(f"✅ Orthogonal vectors similarity: {similarity:.3f}")
        assert abs(similarity - 0.0) < 0.001, "Orthogonal vectors should have similarity 0.0"
        
        # Test 3: Zero vector
        similarity = indexer.get_similarity_score(vector1, vector4)
        print(f"✅ Zero vector similarity: {similarity:.3f}")
        assert similarity == 0.0, "Zero vector should have similarity 0.0"
        
        # Test 4: Same vector with itself
        similarity = indexer.get_similarity_score(vector1, vector1)
        print(f"✅ Self similarity: {similarity:.3f}")
        assert abs(similarity - 1.0) < 0.001, "Vector with itself should have similarity 1.0"
        
        # Test 5: Negative similarity (should be clamped to 0)
        vector5 = np.array([-1.0, 0.0, 0.0])
        similarity = indexer.get_similarity_score(vector1, vector5)
        print(f"✅ Negative similarity (clamped): {similarity:.3f}")
        assert similarity >= 0.0, "Similarity should be clamped to 0.0 minimum"
        
        return True
        
    except Exception as e:
        print(f"❌ Similarity calculation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_processing():
    """Test batch processing functionality"""
    print("\n🧪 Testing Batch Processing...")
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        indexer = ContextIndexer()
        
        # Create test records
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
            },
            {
                'id': 'test_3',
                'symbol': 'SOL',
                'timeframe': '15m',
                'regime': 'trending_down',
                'sig_direction': 'short',
                'sig_confidence': 0.80,
                'sig_sigma': 0.70
            }
        ]
        
        # Test batch processing
        enhanced_records = indexer.batch_create_vectors(test_records)
        print(f"✅ Batch processing: {len(enhanced_records)} records processed")
        
        # Verify all records have vectors
        for record in enhanced_records:
            assert 'context_vector' in record, "Record should have context_vector"
            assert 'context_string' in record, "Record should have context_string"
            assert 'vector_created_at' in record, "Record should have vector_created_at"
            assert record['context_vector'] is not None, "Context vector should not be None"
            assert len(record['context_vector']) > 0, "Context vector should not be empty"
        
        print("✅ All records have proper vector data")
        
        # Test individual vs batch consistency
        individual_vector = indexer.create_context_vector(test_records[0])
        batch_vector = enhanced_records[0]['context_vector']
        
        # Vectors should be similar (allowing for small differences due to batch processing)
        similarity = indexer.get_similarity_score(individual_vector, np.array(batch_vector))
        print(f"✅ Individual vs batch consistency: {similarity:.3f}")
        assert similarity > 0.95, "Individual and batch vectors should be very similar"
        
        return True
        
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_feature_extraction():
    """Test feature extraction functionality"""
    print("\n🧪 Testing Feature Extraction...")
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        indexer = ContextIndexer()
        
        # Test with various feature combinations
        test_data = {
            'features': {
                'rsi': 45.2,
                'macd': 0.0012,
                'bb_position': 0.7,
                'volume_ratio': 1.8,
                'volatility': 0.025,
                'sma_20': 50000,
                'ema_12': 50100,
                'atr_14': 500
            }
        }
        
        key_features = indexer._extract_key_features(test_data['features'])
        print(f"✅ Key features extracted: {key_features}")
        
        # Check that important indicators are included
        important_indicators = ['rsi', 'macd', 'bb_position', 'volume_ratio', 'volatility']
        for indicator in important_indicators:
            assert indicator in key_features, f"{indicator} should be in key features"
        
        # Test with missing features
        test_data2 = {
            'features': {
                'rsi': 45.2,
                'macd': 0.0012
                # Missing other indicators
            }
        }
        
        key_features2 = indexer._extract_key_features(test_data2['features'])
        print(f"✅ Partial features extracted: {key_features2}")
        assert 'rsi' in key_features2, "Available features should be extracted"
        
        # Test with empty features
        test_data3 = {'features': {}}
        key_features3 = indexer._extract_key_features(test_data3['features'])
        print(f"✅ Empty features: {key_features3}")
        assert len(key_features3) == 0, "Empty features should produce empty string"
        
        return True
        
    except Exception as e:
        print(f"❌ Feature extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_categorization():
    """Test record categorization functionality"""
    print("\n🧪 Testing Record Categorization...")
    
    try:
        from llm_integration.context_indexer import ContextIndexer
        indexer = ContextIndexer()
        
        # Test record with all categories
        test_record = {
            'id': 'test_1',
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'trending_up',
            'sig_direction': 'long',
            'sig_confidence': 0.75,
            'sig_sigma': 0.65,
            'kind': 'signal',
            'patterns': {'breakout_up': True},
            'outcome': 'success',
            'performance_score': 0.8,
            'market_conditions': {'volatility': 'high'},
            'lesson': 'Test lesson',
            'source_strands': ['strand_1', 'strand_2']
        }
        
        categorized = indexer.categorize_record(test_record)
        print(f"✅ Record categorized: {len(categorized['categories'])} categories")
        
        # Check that all expected categories exist
        expected_categories = ['market_data', 'signal_data', 'pattern_data', 'performance_data', 'context_data', 'learning_data']
        for category in expected_categories:
            assert category in categorized['categories'], f"{category} should be in categories"
        
        # Check specific category contents
        market_data = categorized['categories']['market_data']
        assert 'symbol' in market_data, "Symbol should be in market_data"
        assert market_data['symbol'] == 'BTC', "Symbol value should be preserved"
        
        signal_data = categorized['categories']['signal_data']
        assert 'sig_confidence' in signal_data, "Signal confidence should be in signal_data"
        assert signal_data['sig_confidence'] == 0.75, "Signal confidence value should be preserved"
        
        return True
        
    except Exception as e:
        print(f"❌ Categorization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all ContextIndexer tests"""
    print("🧪 ContextIndexer Comprehensive Tests")
    print("=" * 50)
    
    tests = [
        ("Initialization", test_context_indexer_initialization),
        ("Context String Creation", test_context_string_creation),
        ("Vector Creation", test_vector_creation),
        ("Similarity Calculation", test_similarity_calculation),
        ("Batch Processing", test_batch_processing),
        ("Feature Extraction", test_feature_extraction),
        ("Categorization", test_categorization)
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
    print("📊 ContextIndexer Test Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All ContextIndexer tests passed!")
    else:
        print("⚠️  Some ContextIndexer tests failed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
