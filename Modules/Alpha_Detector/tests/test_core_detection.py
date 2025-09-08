#!/usr/bin/env python3
"""
Unit Tests for Core Detection Components
Phase 1.6.1: Unit Testing Framework
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

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


class TestMultiTimeframeProcessor(unittest.TestCase):
    """Test MultiTimeframeProcessor component"""
    
    def setUp(self):
        self.processor = MultiTimeframeProcessor()
        self.sample_data = self.create_sample_data()
    
    def create_sample_data(self, periods=2000):
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1min')
        np.random.seed(42)
        base_price = 50000
        returns = np.random.normal(0, 0.001, periods)
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, periods),
            'symbol': ['BTC'] * periods
        })
    
    def test_process_multi_timeframe_success(self):
        """Test successful multi-timeframe processing"""
        result = self.processor.process_multi_timeframe(self.sample_data)
        
        # Should return dictionary with timeframe data
        self.assertIsInstance(result, dict)
        self.assertTrue(len(result) > 0)
        
        # Check expected timeframes are present
        expected_timeframes = ['1m', '5m', '15m', '1h']
        for tf in expected_timeframes:
            if tf in result:  # Some may not have enough data
                self.assertIn('ohlc', result[tf])
                self.assertIn('timeframe', result[tf])
                self.assertIn('data_points', result[tf])
    
    def test_process_multi_timeframe_insufficient_data(self):
        """Test behavior with insufficient data"""
        small_data = self.sample_data.head(50)  # Too small for higher timeframes
        result = self.processor.process_multi_timeframe(small_data)
        
        # Should return dict, but may be empty or have fewer timeframes
        self.assertIsInstance(result, dict)
        # 1m should still work with 50 data points
        if '1m' in result:
            self.assertEqual(result['1m']['timeframe'], '1m')
    
    def test_roll_up_ohlc(self):
        """Test OHLC data roll-up functionality"""
        # Test 5-minute roll-up
        rolled_data = self.processor._roll_up_ohlc(self.sample_data, '5min')
        
        self.assertIsInstance(rolled_data, pd.DataFrame)
        self.assertTrue(len(rolled_data) > 0)
        self.assertTrue(len(rolled_data) < len(self.sample_data))  # Should be smaller
        
        # Check required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            self.assertIn(col, rolled_data.columns)


class TestBasicFeatureExtractor(unittest.TestCase):
    """Test BasicFeatureExtractor component"""
    
    def setUp(self):
        self.extractor = BasicFeatureExtractor()
        self.sample_ohlc = self.create_sample_ohlc()
    
    def create_sample_ohlc(self, periods=200):
        """Create sample OHLC data"""
        np.random.seed(42)
        base_price = 50000
        returns = np.random.normal(0, 0.001, periods)
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        return pd.DataFrame({
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, periods)
        })
    
    def test_extract_all_features(self):
        """Test comprehensive feature extraction"""
        features = self.extractor.extract_all_features(self.sample_ohlc)
        
        self.assertIsInstance(features, dict)
        self.assertTrue(len(features) > 0)
        
        # Check for expected individual features (flat structure)
        expected_features = ['rsi', 'macd', 'bb_upper', 'volume_sma_20', 'sma_20']
        for feature in expected_features:
            self.assertIn(feature, features)
            self.assertIsInstance(features[feature], (int, float, np.number, bool))
    
    def test_extract_price_features(self):
        """Test price feature extraction"""
        features = self.extractor.extract_price_features(self.sample_ohlc)
        
        # Check for key price features
        expected_price_features = ['rsi', 'macd', 'bb_upper', 'bb_lower', 'bb_middle']
        for feature in expected_price_features:
            self.assertIn(feature, features)
            self.assertIsInstance(features[feature], (int, float, np.number))
    
    def test_extract_volume_features(self):
        """Test volume feature extraction"""
        features = self.extractor.extract_volume_features(
            self.sample_ohlc
        )
        
        # Check for key volume features
        expected_volume_features = ['volume_sma_20', 'volume_ratio']
        for feature in expected_volume_features:
            self.assertIn(feature, features)
            self.assertIsInstance(features[feature], (int, float, np.number))
    
    def test_extract_technical_features(self):
        """Test technical indicator extraction"""
        features = self.extractor.extract_technical_features(self.sample_ohlc)
        
        # Check for key technical features
        expected_technical_features = ['sma_20', 'sma_50', 'ema_12', 'volatility_20']
        for feature in expected_technical_features:
            self.assertIn(feature, features)
            self.assertIsInstance(features[feature], (int, float, np.number))


class TestSignalGenerator(unittest.TestCase):
    """Test SignalGenerator component"""
    
    def setUp(self):
        self.generator = SignalGenerator()
        self.sample_features = self.create_sample_features()
        self.sample_patterns = self.create_sample_patterns()
    
    def create_sample_features(self):
        """Create sample features for testing"""
        return {
            'price_features': {
                'rsi': 65.0,
                'macd_bullish': True,
                'bb_position': 0.7
            },
            'volume_features': {
                'volume_spike': True,
                'volume_ratio': 1.5
            },
            'technical_features': {
                'momentum_10': 0.02,
                'volatility_20': 0.015
            }
        }
    
    def create_sample_patterns(self):
        """Create sample patterns for testing"""
        return {
            'breakout_up': True,
            'breakout_down': False,
            'support_levels': [49000, 48500],
            'resistance_levels': [51000, 51500]
        }
    
    def test_generate_signals_long(self):
        """Test long signal generation"""
        signals = self.generator.generate_signals(
            self.sample_features, 
            self.sample_patterns, 
            'trending_up'
        )
        
        self.assertIsInstance(signals, list)
        
        # If signals generated, check structure
        if signals:
            signal = signals[0]
            self.assertIn('direction', signal)
            self.assertIn('confidence', signal)
            self.assertIn('strength', signal)
            self.assertIn('timestamp', signal)
    
    def test_generate_signals_short(self):
        """Test short signal generation"""
        # Modify features for short signal
        short_features = self.sample_features.copy()
        short_features['price_features']['rsi'] = 35.0
        short_features['price_features']['macd_bullish'] = False
        
        short_patterns = self.sample_patterns.copy()
        short_patterns['breakout_up'] = False
        short_patterns['breakout_down'] = True
        
        signals = self.generator.generate_signals(
            short_features, 
            short_patterns, 
            'trending_down'
        )
        
        self.assertIsInstance(signals, list)
        
        # If signals generated, check for short direction
        if signals:
            signal = signals[0]
            self.assertEqual(signal['direction'], 'short')
    
    def test_check_signal_conditions(self):
        """Test signal condition checking"""
        # Test long conditions
        long_valid = self.generator._check_long_conditions(
            self.sample_features, 
            self.sample_patterns, 
            'trending_up'
        )
        self.assertIsInstance(long_valid, bool)
        
        # Test short conditions
        short_valid = self.generator._check_short_conditions(
            self.sample_features, 
            self.sample_patterns, 
            'trending_down'
        )
        self.assertIsInstance(short_valid, bool)


class TestSignalProcessor(unittest.TestCase):
    """Test SignalProcessor component"""
    
    def setUp(self):
        self.filter = SignalFilter(
            min_confidence=0.6,
            min_strength=0.5,
            signal_cooldown_minutes=30,
            max_signals_per_symbol=3
        )
        self.processor = SignalProcessor(self.filter)
        self.sample_signals = self.create_sample_signals()
    
    def create_sample_signals(self):
        """Create sample signals for testing"""
        return [
            {
                'direction': 'long',
                'confidence': 0.8,
                'strength': 0.7,
                'timestamp': datetime.now(timezone.utc)
            },
            {
                'direction': 'short',
                'confidence': 0.5,  # Below threshold
                'strength': 0.6,
                'timestamp': datetime.now(timezone.utc)
            },
            {
                'direction': 'long',
                'confidence': 0.9,
                'strength': 0.4,  # Below threshold
                'timestamp': datetime.now(timezone.utc)
            }
        ]
    
    def test_process_signals_filtering(self):
        """Test signal filtering functionality"""
        filtered_signals = self.processor.process_signals(self.sample_signals, 'BTC')
        
        self.assertIsInstance(filtered_signals, list)
        
        # Should filter out signals below thresholds
        for signal in filtered_signals:
            self.assertGreaterEqual(signal['confidence'], 0.6)
            self.assertGreaterEqual(signal['strength'], 0.5)
    
    def test_process_signals_empty_input(self):
        """Test processing empty signal list"""
        result = self.processor.process_signals([], 'BTC')
        self.assertEqual(result, [])
    
    def test_signal_cooldown(self):
        """Test signal cooldown functionality"""
        symbol = 'BTC'
        
        # Process first batch
        filtered1 = self.processor.process_signals(self.sample_signals[:1], symbol)
        
        # Process second batch immediately (should be filtered by cooldown)
        filtered2 = self.processor.process_signals(self.sample_signals[1:2], symbol)
        
        # Second batch should be empty due to cooldown
        self.assertEqual(len(filtered2), 0)


class TestCoreDetectionEngine(unittest.TestCase):
    """Test CoreDetectionEngine integration"""
    
    def setUp(self):
        self.engine = CoreDetectionEngine(enable_communication=False)
        self.sample_data = self.create_sample_data()
    
    def create_sample_data(self, periods=2000):
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1min')
        np.random.seed(42)
        base_price = 50000
        returns = np.random.normal(0, 0.001, periods)
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, periods),
            'symbol': ['BTC'] * periods
        })
    
    def test_detect_signals_basic(self):
        """Test basic signal detection"""
        result = self.engine.detect_signals(self.sample_data)
        
        # Should return dict when trading plans enabled
        if self.engine.enable_trading_plans:
            self.assertIsInstance(result, dict)
            self.assertIn('signals', result)
            self.assertIn('trading_plans', result)
            self.assertIn('signal_packs', result)
        else:
            # Should return list when trading plans disabled
            self.assertIsInstance(result, list)
    
    def test_detect_signals_empty_data(self):
        """Test behavior with empty data"""
        empty_data = pd.DataFrame()
        
        try:
            result = self.engine.detect_signals(empty_data)
            # Should handle gracefully
            if self.engine.enable_trading_plans:
                self.assertIsInstance(result, dict)
            else:
                self.assertIsInstance(result, list)
        except Exception as e:
            # Should not crash, but may raise informative exception
            self.assertIsInstance(e, (ValueError, KeyError))
    
    def test_detect_signals_insufficient_data(self):
        """Test behavior with insufficient data"""
        small_data = self.sample_data.head(50)
        
        result = self.engine.detect_signals(small_data)
        
        # Should handle gracefully
        if self.engine.enable_trading_plans:
            self.assertIsInstance(result, dict)
            self.assertIn('signals', result)
        else:
            self.assertIsInstance(result, list)
    
    @patch('src.core_detection.core_detection_engine.logger')
    def test_detect_signals_logging(self, mock_logger):
        """Test that appropriate logging occurs"""
        self.engine.detect_signals(self.sample_data)
        
        # Should have logged some information
        self.assertTrue(mock_logger.debug.called or mock_logger.info.called)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
