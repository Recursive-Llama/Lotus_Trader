#!/usr/bin/env python3
"""
Unit Tests for Trading Plan Generation Components
Phase 1.6.1: Trading Plan Testing Framework
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from trading_plans.trading_plan_builder import TradingPlanBuilder
from trading_plans.signal_pack_generator import SignalPackGenerator
from trading_plans.models import TradingPlan, SignalPack, RiskMetrics, ExecutionParameters
from trading_plans.config import TradingPlanConfig


class TestTradingPlanBuilder(unittest.TestCase):
    """Test TradingPlanBuilder component"""
    
    def setUp(self):
        self.builder = TradingPlanBuilder()
        self.sample_signal = self.create_sample_signal()
        self.sample_market_data = self.create_sample_market_data()
    
    def create_sample_signal(self):
        """Create sample signal for testing"""
        return {
            'signal_id': 'test_signal_001',
            'direction': 'long',
            'confidence': 0.8,
            'strength': 0.7,
            'timeframe': '15m',
            'features': {
                'price_features': {'rsi': 65.0, 'macd_bullish': True},
                'volume_features': {'volume_spike': True},
                'technical_features': {'momentum_10': 0.02}
            },
            'patterns': {
                'breakout_up': True,
                'support_levels': [49000, 48500]
            },
            'regime': 'trending_up',
            'timestamp': datetime.now(timezone.utc)
        }
    
    def create_sample_market_data(self):
        """Create sample market data"""
        return pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1min'),
            'open': [50000] * 100,
            'high': [50100] * 100,
            'low': [49900] * 100,
            'close': [50050] * 100,
            'volume': [1000] * 100,
            'symbol': ['BTC'] * 100
        })
    
    def test_build_trading_plan_success(self):
        """Test successful trading plan creation"""
        trading_plan = self.builder.build_trading_plan(self.sample_signal, self.sample_market_data)
        
        self.assertIsInstance(trading_plan, TradingPlan)
        self.assertEqual(trading_plan.direction, 'long')
        self.assertEqual(trading_plan.signal_id, 'test_signal_001')
        self.assertIsInstance(trading_plan.position_size, Decimal)
        self.assertIsInstance(trading_plan.entry_price, Decimal)
        self.assertIsInstance(trading_plan.stop_loss, Decimal)
        self.assertIsInstance(trading_plan.take_profit, Decimal)
    
    def test_build_trading_plan_long_signal(self):
        """Test trading plan for long signal"""
        trading_plan = self.builder.build_trading_plan(self.sample_signal, self.sample_market_data)
        
        # For long signals: stop_loss < entry_price < take_profit
        self.assertLess(trading_plan.stop_loss, trading_plan.entry_price)
        self.assertGreater(trading_plan.take_profit, trading_plan.entry_price)
        self.assertGreaterEqual(trading_plan.risk_reward_ratio, Decimal('1.5'))
    
    def test_build_trading_plan_short_signal(self):
        """Test trading plan for short signal"""
        short_signal = self.sample_signal.copy()
        short_signal['direction'] = 'short'
        
        trading_plan = self.builder.build_trading_plan(short_signal, self.sample_market_data)
        
        # For short signals: take_profit < entry_price < stop_loss
        self.assertGreater(trading_plan.stop_loss, trading_plan.entry_price)
        self.assertLess(trading_plan.take_profit, trading_plan.entry_price)
        self.assertGreaterEqual(trading_plan.risk_reward_ratio, Decimal('1.5'))
    
    def test_position_size_calculation(self):
        """Test position size calculation"""
        position_size_pct = self.builder._calculate_position_size_percentage(
            self.sample_signal, 
            self.sample_market_data
        )
        
        # Should return percentage between 0 and 1
        self.assertIsInstance(position_size_pct, float)
        self.assertGreater(position_size_pct, 0.0)
        self.assertLessEqual(position_size_pct, 1.0)
    
    def test_risk_metrics_calculation(self):
        """Test risk metrics calculation"""
        trading_plan = self.builder.build_trading_plan(self.sample_signal, self.sample_market_data)
        
        # Validate risk metrics
        self.assertIsInstance(trading_plan.position_size, Decimal)
        self.assertGreater(trading_plan.position_size, 0)
        self.assertLessEqual(float(trading_plan.position_size), 1.0)  # Max 100% position
        
        # Risk-reward ratio should be reasonable
        self.assertGreaterEqual(trading_plan.risk_reward_ratio, Decimal('1.0'))
        self.assertLessEqual(trading_plan.risk_reward_ratio, Decimal('5.0'))
    
    def test_entry_price_calculation(self):
        """Test entry price calculation"""
        entry_price = self.builder._calculate_entry_price(self.sample_signal, self.sample_market_data, 'long')
        
        self.assertIsInstance(entry_price, Decimal)
        self.assertGreater(entry_price, 0)
        
        # Should be close to current market price
        current_price = float(self.sample_market_data['close'].iloc[-1])
        self.assertAlmostEqual(float(entry_price), current_price, delta=current_price * 0.01)
    
    def test_stop_loss_calculation(self):
        """Test stop loss calculation"""
        entry_price = Decimal('50000')
        stop_loss, take_profit = self.builder._calculate_stop_loss_take_profit(
            entry_price, 'long', self.sample_signal, {}
        )
        
        self.assertIsInstance(stop_loss, Decimal)
        self.assertGreater(stop_loss, 0)
        
        # For long signal, stop loss should be below entry
        self.assertLess(stop_loss, entry_price)
    
    def test_take_profit_calculation(self):
        """Test take profit calculation"""
        entry_price = Decimal('50000')
        stop_loss, take_profit = self.builder._calculate_stop_loss_take_profit(
            entry_price, 'long', self.sample_signal, {}
        )
        
        self.assertIsInstance(take_profit, Decimal)
        self.assertGreater(take_profit, 0)
        
        # For long signal, take profit should be above entry
        self.assertGreater(take_profit, entry_price)


class TestSignalPackGenerator(unittest.TestCase):
    """Test SignalPackGenerator component"""
    
    def setUp(self):
        self.generator = SignalPackGenerator()
        self.sample_signal = self.create_sample_signal()
        self.sample_trading_plan = self.create_sample_trading_plan()
        self.sample_market_data = self.create_sample_market_data()
    
    def create_sample_signal(self):
        """Create sample signal for testing"""
        return {
            'signal_id': 'test_signal_001',
            'direction': 'long',
            'confidence': 0.8,
            'strength': 0.7,
            'timeframe': '15m',
            'features': {
                'price_features': {'rsi': 65.0, 'macd_bullish': True},
                'volume_features': {'volume_spike': True},
                'technical_features': {'momentum_10': 0.02}
            },
            'patterns': {
                'breakout_up': True,
                'support_levels': [49000, 48500]
            },
            'regime': 'trending_up',
            'timestamp': datetime.now(timezone.utc)
        }
    
    def create_sample_trading_plan(self):
        """Create sample trading plan for testing"""
        return TradingPlan(
            plan_id='test_plan_001',
            signal_id='test_signal_001',
            symbol='BTC',
            timeframe='15m',
            direction='long',
            entry_conditions={'type': 'market'},
            entry_price=Decimal('50000'),
            position_size=Decimal('0.05'),
            stop_loss=Decimal('49000'),
            take_profit=Decimal('52000'),
            risk_reward_ratio=Decimal('2.0'),
            confidence_score=0.8,
            strength_score=0.7,
            time_horizon='4h',
            valid_until=datetime.now(timezone.utc) + timedelta(hours=4),
            created_at=datetime.now(timezone.utc),
            market_context={},
            signal_metadata={}
        )
    
    def create_sample_market_data(self):
        """Create sample market data"""
        return pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1min'),
            'open': [50000] * 100,
            'high': [50100] * 100,
            'low': [49900] * 100,
            'close': [50050] * 100,
            'volume': [1000] * 100,
            'symbol': ['BTC'] * 100
        })
    
    def test_generate_signal_pack_success(self):
        """Test successful signal pack generation"""
        signal_pack = self.generator.generate_signal_pack(
            self.sample_signal, 
            self.sample_trading_plan, 
            self.sample_market_data
        )
        
        self.assertIsInstance(signal_pack, SignalPack)
        self.assertEqual(signal_pack.signal_id, 'test_signal_001')
        self.assertEqual(signal_pack.trading_plan_id, 'test_plan_001')
        self.assertIsInstance(signal_pack.features, dict)
        self.assertIsInstance(signal_pack.llm_format, dict)
    
    def test_signal_pack_structure(self):
        """Test signal pack structure"""
        signal_pack = self.generator.generate_signal_pack(
            self.sample_signal, 
            self.sample_trading_plan, 
            self.sample_market_data
        )
        
        # Check required fields
        self.assertIsNotNone(signal_pack.pack_id)
        self.assertIsInstance(signal_pack.created_at, datetime)
        self.assertIsInstance(signal_pack.processing_metadata, dict)
        
        # Check LLM format structure
        self.assertIn('summary', signal_pack.llm_format)
        self.assertIn('structured_data', signal_pack.llm_format)
        self.assertIn('natural_language', signal_pack.llm_format)
    
    def test_aggregate_features(self):
        """Test feature aggregation"""
        aggregated = self.generator._aggregate_features(self.sample_signal)
        
        self.assertIsInstance(aggregated, dict)
        self.assertIn('price_features', aggregated)
        self.assertIn('volume_features', aggregated)
        self.assertIn('technical_features', aggregated)
    
    def test_build_market_context(self):
        """Test market context building"""
        context = self.generator._build_market_context(
            self.sample_market_data,
            self.sample_signal,
            self.sample_trading_plan
        )
        
        self.assertIsInstance(context, dict)
        self.assertIn('current_price', context)
        self.assertIn('current_price', context)
        self.assertIn('volume_24h', context)
    
    def test_format_for_llm(self):
        """Test LLM formatting"""
        signal_pack_data = {
            'signal': self.sample_signal,
            'trading_plan': self.sample_trading_plan,
            'features': {'test': 'data'},
            'market_context': {'test': 'context'}
        }
        
        llm_format = self.generator._format_for_llm(
            self.sample_signal,
            self.sample_trading_plan,
            signal_pack_data['features'],
            {'test': 'pattern'},
            {'test': 'regime'},
            signal_pack_data['market_context']
        )
        
        self.assertIsInstance(llm_format, dict)
        self.assertIn('summary', llm_format)
        self.assertIn('structured_data', llm_format)


class TestTradingPlanModels(unittest.TestCase):
    """Test TradingPlan data models"""
    
    def test_trading_plan_creation(self):
        """Test TradingPlan model creation"""
        trading_plan = TradingPlan(
            plan_id='test_plan_001',
            signal_id='test_signal_001',
            symbol='BTC',
            timeframe='15m',
            direction='long',
            entry_conditions={'type': 'market'},
            entry_price=Decimal('50000'),
            position_size=Decimal('0.05'),
            stop_loss=Decimal('49000'),
            take_profit=Decimal('52000'),
            risk_reward_ratio=Decimal('2.0'),
            confidence_score=0.8,
            strength_score=0.7,
            time_horizon='4h',
            valid_until=datetime.now(timezone.utc) + timedelta(hours=4),
            created_at=datetime.now(timezone.utc),
            market_context={},
            signal_metadata={}
        )
        
        self.assertEqual(trading_plan.plan_id, 'test_plan_001')
        self.assertEqual(trading_plan.direction, 'long')
        self.assertIsInstance(trading_plan.entry_price, Decimal)
        self.assertIsInstance(trading_plan.created_at, datetime)
    
    def test_signal_pack_creation(self):
        """Test SignalPack model creation"""
        signal_pack = SignalPack(
            pack_id='test_pack_001',
            signal_id='test_signal_001',
            trading_plan_id='test_plan_001',
            features={'test': 'features'},
            patterns={'test': 'patterns'},
            regime={'test': 'regime'},
            market_context={'test': 'context'},
            processing_metadata={'test': 'metadata'},
            llm_format={'test': 'llm_format'},
            created_at=datetime.now(timezone.utc)
        )
        
        self.assertEqual(signal_pack.pack_id, 'test_pack_001')
        self.assertEqual(signal_pack.signal_id, 'test_signal_001')
        self.assertIsInstance(signal_pack.features, dict)
        self.assertIsInstance(signal_pack.created_at, datetime)
    
    def test_risk_metrics_creation(self):
        """Test RiskMetrics model creation"""
        risk_metrics = RiskMetrics(
            position_size=Decimal('0.05'),
            risk_amount=Decimal('0.01'),
            risk_percentage=0.02,
            stop_loss_distance=Decimal('1000'),
            take_profit_distance=Decimal('2000'),
            risk_reward_ratio=Decimal('2.0'),
            max_drawdown=0.15,
            volatility_adjustment=1.0
        )
        
        self.assertIsInstance(risk_metrics.position_size, Decimal)
        self.assertIsInstance(risk_metrics.risk_percentage, float)
        self.assertEqual(risk_metrics.risk_reward_ratio, Decimal('2.0'))


class TestTradingPlanConfig(unittest.TestCase):
    """Test TradingPlanConfig component"""
    
    def setUp(self):
        # Create a mock config for testing
        self.mock_config = {
            'risk_management': {
                'high_confidence': {
                    'max_position_size': 0.15,
                    'risk_per_trade': 0.03
                },
                'medium_confidence': {
                    'max_position_size': 0.10,
                    'risk_per_trade': 0.02
                },
                'low_confidence': {
                    'max_position_size': 0.05,
                    'risk_per_trade': 0.01
                }
            },
            'position_sizing': {
                'base_percentage': 0.05,
                'max_percentage': 0.15
            }
        }
    
    @patch('trading_plans.config.yaml.safe_load')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_config_loading(self, mock_open, mock_yaml):
        """Test configuration loading"""
        mock_yaml.return_value = self.mock_config
        
        config = TradingPlanConfig()
        
        self.assertIsInstance(config.risk_config, dict)
        self.assertIsInstance(config.position_sizing, dict)
    
    @patch('trading_plans.config.yaml.safe_load')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_get_risk_config(self, mock_open, mock_yaml):
        """Test risk configuration retrieval"""
        mock_yaml.return_value = self.mock_config
        
        config = TradingPlanConfig()
        
        # Test high confidence
        high_conf_config = config.get_risk_config(0.9)
        self.assertEqual(high_conf_config['max_position_size'], 0.15)
        
        # Test medium confidence
        med_conf_config = config.get_risk_config(0.7)
        self.assertEqual(med_conf_config['max_position_size'], 0.10)
        
        # Test low confidence
        low_conf_config = config.get_risk_config(0.5)
        self.assertEqual(low_conf_config['max_position_size'], 0.05)
    
    @patch('trading_plans.config.yaml.safe_load')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_get_position_size_percentage(self, mock_open, mock_yaml):
        """Test position size percentage calculation"""
        mock_yaml.return_value = self.mock_config
        
        config = TradingPlanConfig()
        
        # Test position size calculation
        position_size = config.get_position_size_percentage(0.8)  # High strength
        
        self.assertIsInstance(position_size, float)
        self.assertGreater(position_size, 0.0)
        self.assertLessEqual(position_size, config.position_sizing['max_percentage'])


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
