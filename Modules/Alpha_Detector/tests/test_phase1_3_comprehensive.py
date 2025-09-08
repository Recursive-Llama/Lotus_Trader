#!/usr/bin/env python3
"""
Comprehensive Testing Framework for Phase 1.3
Multi-Timeframe Alpha Detector Testing Suite
"""

import sys
import os
import logging
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core_detection.core_detection_engine import CoreDetectionEngine
from core_detection.multi_timeframe_processor import MultiTimeframeProcessor
from core_detection.feature_extractors import BasicFeatureExtractor
from core_detection.pattern_detectors import PatternDetector
from core_detection.regime_detector import RegimeDetector
from core_detection.signal_generator import SignalGenerator
from core_detection.multi_timeframe_signal_combiner import MultiTimeframeSignalCombiner
from core_detection.signal_processor import SignalProcessor, SignalFilter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestPhase1_3Comprehensive(unittest.TestCase):
    """Comprehensive test suite for Phase 1.3 Multi-Timeframe Alpha Detector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_data = self.create_extended_sample_market_data()
        self.engine = CoreDetectionEngine()
        self.custom_filter = SignalFilter(
            min_confidence=0.6,
            min_strength=0.5,
            signal_cooldown_minutes=5,  # Short for testing
            max_signals_per_symbol=3,
            max_signals_per_timeframe=2
        )
        self.engine_with_filter = CoreDetectionEngine(signal_filter=self.custom_filter)
    
    def create_extended_sample_market_data(self, periods=2000):
        """Create extended sample market data for comprehensive testing"""
        # Generate 2000+ data points for higher timeframes
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1min')
        
        # Generate realistic price data with different market conditions
        np.random.seed(42)
        base_price = 50000
        
        # Create different market regimes
        regime_periods = [
            (0, 500, 0.001),     # Upward trend
            (500, 1000, -0.0005), # Downward trend
            (1000, 1500, 0.0001), # Sideways
            (1500, 2000, 0.0015), # Strong upward
        ]
        
        prices = [base_price]
        for i in range(1, periods):
            # Find current regime
            trend_rate = 0.0001  # Default small positive trend
            for start, end, rate in regime_periods:
                if start <= i < end:
                    trend_rate = rate
                    break
            
            # Add noise and volatility
            noise = np.random.normal(0, 0.001)
            new_price = prices[-1] * (1 + trend_rate + noise)
            prices.append(new_price)
        
        # Generate OHLCV data
        data = {
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, periods),
            'symbol': 'BTC'
        }
        
        return pd.DataFrame(data)
    
    def test_multi_timeframe_processor(self):
        """Test MultiTimeframeProcessor functionality"""
        print("\n🧪 Testing MultiTimeframeProcessor...")
        
        processor = MultiTimeframeProcessor()
        mtf_data = processor.process_multi_timeframe(self.sample_data)
        
        # Check that all expected timeframes are present
        expected_timeframes = ['1m', '5m', '15m', '1h']
        self.assertEqual(set(mtf_data.keys()), set(expected_timeframes))
        
        # Check data quality for each timeframe
        for tf_name in expected_timeframes:
            tf_data = mtf_data[tf_name]
            self.assertGreaterEqual(tf_data['data_points'], 100)
            self.assertIn('ohlc', tf_data)
            self.assertIsInstance(tf_data['ohlc'], pd.DataFrame)
            
            # Check OHLCV columns
            ohlc = tf_data['ohlc']
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                self.assertIn(col, ohlc.columns)
        
        print("✅ MultiTimeframeProcessor tests passed")
    
    def test_feature_extractors(self):
        """Test BasicFeatureExtractor functionality"""
        print("\n🧪 Testing BasicFeatureExtractor...")
        
        extractor = BasicFeatureExtractor()
        
        # Test with 1m data
        mtf_processor = MultiTimeframeProcessor()
        mtf_data = mtf_processor.process_multi_timeframe(self.sample_data)
        
        for tf_name, tf_data in mtf_data.items():
            features = extractor.extract_all_features(tf_data['ohlc'])
            
            # Check that features are extracted
            self.assertIsInstance(features, dict)
            self.assertGreater(len(features), 0)
            
            # Check specific feature types
            expected_feature_types = ['price', 'volume', 'technical']
            for feature_type in expected_feature_types:
                type_features = [k for k in features.keys() if feature_type in k.lower()]
                self.assertGreater(len(type_features), 0, f"No {feature_type} features found")
        
        print("✅ BasicFeatureExtractor tests passed")
    
    def test_pattern_detectors(self):
        """Test PatternDetector functionality"""
        print("\n🧪 Testing PatternDetector...")
        
        detector = PatternDetector()
        
        # Test with 1m data
        mtf_processor = MultiTimeframeProcessor()
        mtf_data = mtf_processor.process_multi_timeframe(self.sample_data)
        
        for tf_name, tf_data in mtf_data.items():
            patterns = detector.detect_all_patterns(tf_data['ohlc'], {})
            
            # Check that patterns are detected
            self.assertIsInstance(patterns, dict)
            
            # Check specific pattern types
            expected_pattern_types = ['support_resistance', 'breakouts', 'divergences']
            for pattern_type in expected_pattern_types:
                self.assertIn(pattern_type, patterns)
        
        print("✅ PatternDetector tests passed")
    
    def test_regime_detector(self):
        """Test RegimeDetector functionality"""
        print("\n🧪 Testing RegimeDetector...")
        
        detector = RegimeDetector()
        
        # Test with 1m data
        mtf_processor = MultiTimeframeProcessor()
        mtf_data = mtf_processor.process_multi_timeframe(self.sample_data)
        
        for tf_name, tf_data in mtf_data.items():
            regime = detector.detect_regime(tf_data['ohlc'], {})
            
            # Check that regime is detected
            self.assertIsInstance(regime, dict)
            self.assertIn('regime', regime)
            self.assertIn('confidence', regime)
            
            # Check regime values
            valid_regimes = ['trending_up', 'trending_down', 'ranging']
            self.assertIn(regime['regime'], valid_regimes)
            self.assertGreaterEqual(regime['confidence'], 0.0)
            self.assertLessEqual(regime['confidence'], 1.0)
        
        print("✅ RegimeDetector tests passed")
    
    def test_signal_generator(self):
        """Test SignalGenerator functionality"""
        print("\n🧪 Testing SignalGenerator...")
        
        generator = SignalGenerator()
        
        # Test with sample features and patterns
        sample_features = {
            'rsi': 45,
            'macd_bullish': True,
            'bb_position': 0.3,
            'volume_spike': True,
            'sma_crossover': True
        }
        
        sample_patterns = {
            'breakout_up': True,
            'support_levels': [48000, 49000],
            'resistance_levels': [52000, 53000]
        }
        
        sample_regime = 'trending_up'
        
        signals = generator.generate_signals(sample_features, sample_patterns, sample_regime)
        
        # Check that signals are generated
        self.assertIsInstance(signals, list)
        
        # Check signal structure
        for signal in signals:
            self.assertIn('direction', signal)
            self.assertIn('confidence', signal)
            self.assertIn('strength', signal)
            self.assertIn('timestamp', signal)
            
            # Check signal values
            self.assertIn(signal['direction'], ['long', 'short'])
            self.assertGreaterEqual(signal['confidence'], 0.0)
            self.assertLessEqual(signal['confidence'], 1.0)
            self.assertGreaterEqual(signal['strength'], 0.0)
            self.assertLessEqual(signal['strength'], 1.0)
        
        print("✅ SignalGenerator tests passed")
    
    def test_multi_timeframe_signal_combiner(self):
        """Test MultiTimeframeSignalCombiner functionality"""
        print("\n🧪 Testing MultiTimeframeSignalCombiner...")
        
        combiner = MultiTimeframeSignalCombiner()
        
        # Create sample multi-timeframe signals
        mtf_signals = {
            '1h': [
                {
                    'direction': 'long',
                    'confidence': 0.8,
                    'strength': 0.7,
                    'timeframe': '1h',
                    'timestamp': datetime.now(timezone.utc)
                }
            ],
            '15m': [
                {
                    'direction': 'long',
                    'confidence': 0.7,
                    'strength': 0.6,
                    'timeframe': '15m',
                    'timestamp': datetime.now(timezone.utc)
                }
            ],
            '5m': [
                {
                    'direction': 'short',
                    'confidence': 0.6,
                    'strength': 0.5,
                    'timeframe': '5m',
                    'timestamp': datetime.now(timezone.utc)
                }
            ]
        }
        
        combined_signals = combiner.combine_signals(mtf_signals)
        
        # Check that signals are combined
        self.assertIsInstance(combined_signals, list)
        
        # Check combined signal structure
        for signal in combined_signals:
            self.assertIn('direction', signal)
            self.assertIn('confidence', signal)
            self.assertIn('strength', signal)
            self.assertIn('timeframe_confirmations', signal)
            self.assertIn('confirmation_ratio', signal)
        
        print("✅ MultiTimeframeSignalCombiner tests passed")
    
    def test_signal_processor(self):
        """Test SignalProcessor functionality"""
        print("\n🧪 Testing SignalProcessor...")
        
        processor = SignalProcessor(self.custom_filter)
        
        # Create sample signals
        sample_signals = [
            {
                'direction': 'long',
                'confidence': 0.8,
                'strength': 0.7,
                'volume_ratio': 1.5,
                'timeframe': '1h',
                'timestamp': datetime.now(timezone.utc)
            },
            {
                'direction': 'short',
                'confidence': 0.6,
                'strength': 0.5,
                'volume_ratio': 1.1,
                'timeframe': '15m',
                'timestamp': datetime.now(timezone.utc)
            }
        ]
        
        processed = processor.process_signals(sample_signals, 'BTC')
        
        # Check that signals are processed
        self.assertIsInstance(processed, list)
        self.assertLessEqual(len(processed), len(sample_signals))
        
        # Check processed signal structure
        for signal in processed:
            self.assertIn('processing_metadata', signal)
            self.assertIn('quality_score', signal)
            self.assertIn('direction', signal)
            self.assertIn('confidence', signal)
            self.assertIn('strength', signal)
        
        print("✅ SignalProcessor tests passed")
    
    def test_core_detection_engine_integration(self):
        """Test Core Detection Engine integration"""
        print("\n🧪 Testing Core Detection Engine Integration...")
        
        # Test with default engine
        signals = self.engine.detect_signals(self.sample_data)
        
        # Check that signals are detected
        self.assertIsInstance(signals, list)
        
        # Test with custom filter engine
        signals_filtered = self.engine_with_filter.detect_signals(self.sample_data)
        
        # Check that filtered signals are detected
        self.assertIsInstance(signals_filtered, list)
        
        # Test engine methods
        summary = self.engine.get_detection_summary(signals)
        self.assertIn('total_signals', summary)
        self.assertIn('long_signals', summary)
        self.assertIn('short_signals', summary)
        
        quality = self.engine.validate_detection_quality(signals)
        self.assertIn('valid', quality)
        self.assertIn('issues', quality)
        
        print("✅ Core Detection Engine Integration tests passed")
    
    def test_signal_processor_integration(self):
        """Test SignalProcessor integration with engine"""
        print("\n🧪 Testing SignalProcessor Integration...")
        
        # Test processor methods through engine
        stats = self.engine_with_filter.get_signal_processor_stats('BTC')
        self.assertIn('symbol', stats)
        self.assertIn('recent_signals', stats)
        self.assertIn('total_processed', stats)
        
        cooldown = self.engine_with_filter.get_cooldown_status('BTC')
        self.assertIn('symbol', cooldown)
        self.assertIn('cooldown_active', cooldown)
        self.assertIn('time_remaining', cooldown)
        
        # Test filter update
        new_config = {'min_confidence': 0.8}
        self.engine_with_filter.update_signal_filter(new_config)
        
        print("✅ SignalProcessor Integration tests passed")
    
    def test_end_to_end_pipeline(self):
        """Test complete end-to-end pipeline"""
        print("\n🧪 Testing End-to-End Pipeline...")
        
        # Test complete pipeline with different data sizes
        test_sizes = [500, 1000, 2000]
        
        for size in test_sizes:
            print(f"   Testing with {size} data points...")
            
            # Create test data
            test_data = self.create_extended_sample_market_data(size)
            
            # Run detection
            signals = self.engine_with_filter.detect_signals(test_data)
            
            # Check results
            self.assertIsInstance(signals, list)
            
            # Check signal quality
            for signal in signals:
                self.assertIn('direction', signal)
                self.assertIn('confidence', signal)
                self.assertIn('strength', signal)
                self.assertIn('quality_score', signal)
                self.assertIn('processing_metadata', signal)
        
        print("✅ End-to-End Pipeline tests passed")
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        print("\n🧪 Testing Performance Benchmarks...")
        
        import time
        
        # Test detection speed
        start_time = time.time()
        signals = self.engine.detect_signals(self.sample_data)
        detection_time = time.time() - start_time
        
        # Check that detection completes in reasonable time
        self.assertLess(detection_time, 10.0, "Detection took too long")
        
        # Test with filter
        start_time = time.time()
        signals_filtered = self.engine_with_filter.detect_signals(self.sample_data)
        filtered_time = time.time() - start_time
        
        # Check that filtered detection completes in reasonable time
        self.assertLess(filtered_time, 10.0, "Filtered detection took too long")
        
        print(f"   Detection time: {detection_time:.3f}s")
        print(f"   Filtered detection time: {filtered_time:.3f}s")
        print("✅ Performance Benchmarks tests passed")
    
    def test_error_handling(self):
        """Test error handling and edge cases"""
        print("\n🧪 Testing Error Handling...")
        
        # Test with empty data
        empty_data = pd.DataFrame()
        signals = self.engine.detect_signals(empty_data)
        self.assertEqual(len(signals), 0)
        
        # Test with insufficient data
        small_data = self.create_extended_sample_market_data(50)
        signals = self.engine.detect_signals(small_data)
        self.assertIsInstance(signals, list)
        
        # Test with malformed data
        malformed_data = self.sample_data.copy()
        malformed_data['close'] = None
        signals = self.engine.detect_signals(malformed_data)
        self.assertIsInstance(signals, list)
        
        print("✅ Error Handling tests passed")
    
    def test_configuration_management(self):
        """Test configuration management"""
        print("\n🧪 Testing Configuration Management...")
        
        # Test custom filter configuration
        custom_filter = SignalFilter(
            min_confidence=0.8,
            min_strength=0.7,
            signal_cooldown_minutes=60,
            max_signals_per_symbol=1
        )
        
        custom_engine = CoreDetectionEngine(signal_filter=custom_filter)
        
        # Test filter update
        new_config = {
            'min_confidence': 0.9,
            'signal_cooldown_minutes': 120
        }
        custom_engine.update_signal_filter(new_config)
        
        # Test combiner configuration
        combiner = MultiTimeframeSignalCombiner()
        
        # Test weight update
        new_weights = {
            '1h': 0.5,
            '15m': 0.3,
            '5m': 0.2,
            '1m': 0.0
        }
        combiner.update_weights(new_weights)
        
        print("✅ Configuration Management tests passed")

def run_comprehensive_tests():
    """Run comprehensive test suite"""
    print("🚀 Phase 1.3 Comprehensive Testing Framework")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase1_3Comprehensive)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 ALL COMPREHENSIVE TESTS PASSED!")
        print("✅ Phase 1.3 Multi-Timeframe Alpha Detector is fully functional!")
        print("🚀 Ready to proceed to Phase 1.4 (Trading Plan Generation)")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)

