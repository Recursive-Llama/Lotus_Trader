#!/usr/bin/env python3
"""
End-to-End Integration Tests for Alpha Detector
Phase 1.6.2: Complete System Integration Testing
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core_detection.core_detection_engine import CoreDetectionEngine
from trading_plans.trading_plan_builder import TradingPlanBuilder
from trading_plans.signal_pack_generator import SignalPackGenerator
from communication.direct_table_communicator import DirectTableCommunicator
from communication.module_listener import ModuleListener
from utils.supabase_manager import SupabaseManager


class TestEndToEndIntegration(unittest.TestCase):
    """Test complete end-to-end Alpha Detector functionality"""
    
    def setUp(self):
        """Set up complete system for testing"""
        # Mock database manager
        self.mock_db_manager = Mock(spec=SupabaseManager)
        
        # Initialize core components
        self.detection_engine = CoreDetectionEngine(
            db_manager=self.mock_db_manager,
            enable_trading_plans=True,
            enable_communication=False  # Disable for unit testing
        )
        
        # Sample market data
        self.sample_market_data = self.create_comprehensive_market_data()
    
    def create_comprehensive_market_data(self, periods=2000):
        """Create comprehensive market data for end-to-end testing"""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1min')
        np.random.seed(42)  # For reproducible tests
        
        # Create realistic price movements with trends
        base_price = 50000
        trend_periods = [
            (0, 400, 0.0008),    # Upward trend
            (400, 800, -0.0004), # Downward trend
            (800, 1200, 0.0002), # Sideways
            (1200, 1600, 0.0012), # Strong upward
            (1600, 2000, -0.0006) # Correction
        ]
        
        prices = [base_price]
        for i in range(1, periods):
            # Find current trend
            trend_rate = 0.0001  # Default
            for start, end, rate in trend_periods:
                if start <= i < end:
                    trend_rate = rate
                    break
            
            # Add noise
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
            'volume': np.random.uniform(500, 2000, periods),
            'symbol': ['BTC'] * periods
        }
        
        return pd.DataFrame(data)
    
    def test_complete_signal_detection_pipeline(self):
        """Test complete signal detection from raw data to final signals"""
        # Run complete detection pipeline
        result = self.detection_engine.detect_signals(self.sample_market_data)
        
        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn('signals', result)
        self.assertIn('trading_plans', result)
        self.assertIn('signal_packs', result)
        
        # Verify signals were generated
        signals = result['signals']
        self.assertIsInstance(signals, list)
        
        # If signals were generated, verify structure
        if signals:
            signal = signals[0]
            self.assertIn('direction', signal)
            self.assertIn('confidence', signal)
            self.assertIn('strength', signal)
            self.assertIn('timestamp', signal)
            
            # Confidence and strength should be reasonable
            self.assertGreaterEqual(signal['confidence'], 0.0)
            self.assertLessEqual(signal['confidence'], 1.0)
            self.assertGreaterEqual(signal['strength'], 0.0)
            self.assertLessEqual(signal['strength'], 1.0)
    
    def test_trading_plan_generation_integration(self):
        """Test trading plan generation integration"""
        result = self.detection_engine.detect_signals(self.sample_market_data)
        
        trading_plans = result['trading_plans']
        self.assertIsInstance(trading_plans, list)
        
        # If trading plans were generated, verify structure
        if trading_plans:
            plan = trading_plans[0]
            
            # Verify required fields
            self.assertIsNotNone(plan.plan_id)
            self.assertIsNotNone(plan.signal_id)
            self.assertIn(plan.direction, ['long', 'short'])
            self.assertIsInstance(plan.entry_price, Decimal)
            self.assertIsInstance(plan.position_size, Decimal)
            self.assertIsInstance(plan.stop_loss, Decimal)
            self.assertIsInstance(plan.take_profit, Decimal)
            
            # Verify risk management
            self.assertGreaterEqual(plan.risk_reward_ratio, Decimal('1.0'))
            self.assertGreater(plan.position_size, Decimal('0'))
            self.assertLessEqual(plan.position_size, Decimal('1.0'))  # Max 100%
            
            # Verify price relationships
            if plan.direction == 'long':
                self.assertLess(plan.stop_loss, plan.entry_price)
                self.assertGreater(plan.take_profit, plan.entry_price)
            else:  # short
                self.assertGreater(plan.stop_loss, plan.entry_price)
                self.assertLess(plan.take_profit, plan.entry_price)
    
    def test_signal_pack_generation_integration(self):
        """Test signal pack generation integration"""
        result = self.detection_engine.detect_signals(self.sample_market_data)
        
        signal_packs = result['signal_packs']
        self.assertIsInstance(signal_packs, list)
        
        # If signal packs were generated, verify structure
        if signal_packs:
            pack = signal_packs[0]
            
            # Verify required fields
            self.assertIsNotNone(pack.pack_id)
            self.assertIsNotNone(pack.signal_id)
            self.assertIsNotNone(pack.trading_plan_id)
            self.assertIsInstance(pack.features, dict)
            self.assertIsInstance(pack.llm_format, dict)
            
            # Verify LLM format structure
            self.assertIn('signal_summary', pack.llm_format)
            self.assertIn('market_context', pack.llm_format)
            self.assertIn('trading_plan_summary', pack.llm_format)
    
    def test_multi_timeframe_integration(self):
        """Test multi-timeframe processing integration"""
        # Use the multi-timeframe processor directly
        mtf_processor = self.detection_engine.multi_timeframe_processor
        mtf_data = mtf_processor.process_multi_timeframe(self.sample_market_data)
        
        # Should have processed multiple timeframes
        self.assertIsInstance(mtf_data, dict)
        self.assertTrue(len(mtf_data) > 0)
        
        # Check that higher timeframes have fewer data points
        if '1m' in mtf_data and '5m' in mtf_data:
            self.assertGreater(
                mtf_data['1m']['data_points'],
                mtf_data['5m']['data_points']
            )
        
        if '5m' in mtf_data and '15m' in mtf_data:
            self.assertGreater(
                mtf_data['5m']['data_points'],
                mtf_data['15m']['data_points']
            )
    
    def test_feature_extraction_integration(self):
        """Test feature extraction integration across timeframes"""
        # Extract features for multiple timeframes
        mtf_processor = self.detection_engine.multi_timeframe_processor
        feature_extractor = self.detection_engine.feature_extractors
        
        mtf_data = mtf_processor.process_multi_timeframe(self.sample_market_data)
        
        # Extract features for each timeframe
        for tf_name, tf_data in mtf_data.items():
            features = feature_extractor.extract_all_features(tf_data['ohlc'])
            
            # Verify feature structure
            self.assertIsInstance(features, dict)
            self.assertIn('price_features', features)
            self.assertIn('volume_features', features)
            self.assertIn('technical_features', features)
            
            # Verify key features are present
            price_features = features['price_features']
            self.assertIn('rsi', price_features)
            self.assertIn('macd', price_features)
            self.assertIn('bb_upper', price_features)
    
    def test_signal_processing_integration(self):
        """Test signal processing and filtering integration"""
        # Run detection with custom filter
        from core_detection.signal_processor import SignalFilter
        
        custom_filter = SignalFilter(
            min_confidence=0.7,
            min_strength=0.6,
            signal_cooldown_minutes=5,  # Short for testing
            max_signals_per_symbol=2
        )
        
        engine_with_filter = CoreDetectionEngine(
            db_manager=self.mock_db_manager,
            signal_filter=custom_filter,
            enable_trading_plans=True,
            enable_communication=False
        )
        
        result = engine_with_filter.detect_signals(self.sample_market_data)
        signals = result['signals']
        
        # Verify filtering was applied
        for signal in signals:
            self.assertGreaterEqual(signal['confidence'], 0.7)
            self.assertGreaterEqual(signal['strength'], 0.6)
        
        # Should not exceed max signals per symbol
        self.assertLessEqual(len(signals), 2)
    
    def test_error_handling_integration(self):
        """Test error handling throughout the system"""
        # Test with empty data
        empty_data = pd.DataFrame()
        
        try:
            result = self.detection_engine.detect_signals(empty_data)
            # Should handle gracefully
            self.assertIsInstance(result, dict)
            self.assertIn('signals', result)
        except Exception as e:
            # Should raise informative exceptions
            self.assertIsInstance(e, (ValueError, KeyError, IndexError))
        
        # Test with insufficient data
        small_data = self.sample_market_data.head(10)
        
        try:
            result = self.detection_engine.detect_signals(small_data)
            # Should handle gracefully
            self.assertIsInstance(result, dict)
        except Exception as e:
            # Should raise informative exceptions
            self.assertIsInstance(e, (ValueError, KeyError, IndexError))
    
    def test_performance_integration(self):
        """Test system performance with realistic data"""
        import time
        
        # Measure detection time
        start_time = time.time()
        result = self.detection_engine.detect_signals(self.sample_market_data)
        end_time = time.time()
        
        detection_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(detection_time, 30.0, "Detection took too long")
        
        # Should produce reasonable results
        self.assertIsInstance(result, dict)
        self.assertIn('signals', result)
    
    def test_data_consistency_integration(self):
        """Test data consistency throughout the pipeline"""
        result = self.detection_engine.detect_signals(self.sample_market_data)
        
        signals = result['signals']
        trading_plans = result['trading_plans']
        signal_packs = result['signal_packs']
        
        # If we have all three types, verify consistency
        if signals and trading_plans and signal_packs:
            # Should have matching counts (1:1:1 relationship)
            self.assertEqual(len(signals), len(trading_plans))
            self.assertEqual(len(trading_plans), len(signal_packs))
            
            # Verify ID relationships
            signal = signals[0]
            trading_plan = trading_plans[0]
            signal_pack = signal_packs[0]
            
            self.assertEqual(trading_plan.signal_id, signal.get('signal_id'))
            self.assertEqual(signal_pack.signal_id, signal.get('signal_id'))
            self.assertEqual(signal_pack.trading_plan_id, trading_plan.plan_id)
    
    def test_configuration_integration(self):
        """Test configuration integration across components"""
        # Test with different configuration
        from trading_plans.config import TradingPlanConfig
        
        # Mock configuration loading
        with patch('trading_plans.config.yaml.safe_load') as mock_yaml:
            mock_yaml.return_value = {
                'risk_management': {
                    'high_confidence': {'max_position_size': 0.20},
                    'medium_confidence': {'max_position_size': 0.15},
                    'low_confidence': {'max_position_size': 0.08}
                },
                'position_sizing': {
                    'base_percentage': 0.08,
                    'max_percentage': 0.20
                }
            }
            
            # Run detection with custom config
            result = self.detection_engine.detect_signals(self.sample_market_data)
            
            # Verify configuration was applied
            trading_plans = result['trading_plans']
            if trading_plans:
                plan = trading_plans[0]
                # Position size should respect configuration limits
                self.assertLessEqual(float(plan.position_size), 0.20)


class TestSystemResilience(unittest.TestCase):
    """Test system resilience and edge cases"""
    
    def setUp(self):
        self.mock_db_manager = Mock(spec=SupabaseManager)
        self.detection_engine = CoreDetectionEngine(
            db_manager=self.mock_db_manager,
            enable_trading_plans=True,
            enable_communication=False
        )
    
    def test_extreme_market_conditions(self):
        """Test system behavior in extreme market conditions"""
        # Create extreme volatility data
        dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
        base_price = 50000
        
        # Extreme price movements
        extreme_returns = np.random.normal(0, 0.05, 1000)  # 5% volatility
        prices = [base_price]
        
        for ret in extreme_returns[1:]:
            new_price = max(prices[-1] * (1 + ret), 1000)  # Prevent negative prices
            prices.append(new_price)
        
        extreme_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 5000, 1000),
            'symbol': ['BTC'] * 1000
        })
        
        # System should handle extreme conditions gracefully
        try:
            result = self.detection_engine.detect_signals(extreme_data)
            self.assertIsInstance(result, dict)
            self.assertIn('signals', result)
        except Exception as e:
            # Should not crash on extreme data
            self.fail(f"System crashed on extreme data: {e}")
    
    def test_missing_data_handling(self):
        """Test handling of missing or corrupted data"""
        # Create data with missing values
        dates = pd.date_range(start='2024-01-01', periods=500, freq='1min')
        prices = [50000 + i for i in range(500)]
        
        corrupted_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': [np.nan if i % 50 == 0 else 1000 for i in range(500)],  # Missing volume
            'symbol': ['BTC'] * 500
        })
        
        # System should handle missing data gracefully
        try:
            result = self.detection_engine.detect_signals(corrupted_data)
            self.assertIsInstance(result, dict)
        except Exception as e:
            # Should handle missing data appropriately
            self.assertIsInstance(e, (ValueError, TypeError))
    
    def test_concurrent_access_simulation(self):
        """Test system behavior under concurrent access patterns"""
        # Simulate multiple simultaneous detection requests
        sample_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=1000, freq='1min'),
            'open': [50000] * 1000,
            'high': [50100] * 1000,
            'low': [49900] * 1000,
            'close': [50050] * 1000,
            'volume': [1000] * 1000,
            'symbol': ['BTC'] * 1000
        })
        
        # Run multiple detections (simulating concurrent requests)
        results = []
        for i in range(3):
            result = self.detection_engine.detect_signals(sample_data)
            results.append(result)
        
        # All should succeed
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertIn('signals', result)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)

