#!/usr/bin/env python3
"""
Integration Tests for Communication System
Phase 1.6.2: Communication Integration Testing
"""

import sys
import os
import unittest
import json
import uuid
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from decimal import Decimal

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from communication.direct_table_communicator import DirectTableCommunicator
from communication.module_listener import ModuleListener
from trading_plans.models import TradingPlan, SignalPack
from utils.supabase_manager import SupabaseManager


class TestDirectTableCommunicator(unittest.TestCase):
    """Test DirectTableCommunicator integration"""
    
    def setUp(self):
        self.mock_db_manager = Mock(spec=SupabaseManager)
        self.communicator = DirectTableCommunicator(self.mock_db_manager)
        self.sample_trading_plan = self.create_sample_trading_plan()
        self.sample_signal_pack = self.create_sample_signal_pack()
    
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
            market_context={'current_price': 50000},
            signal_metadata={'source': 'alpha_detector'}
        )
    
    def create_sample_signal_pack(self):
        """Create sample signal pack for testing"""
        return SignalPack(
            pack_id='test_pack_001',
            signal_id='test_signal_001',
            trading_plan_id='test_plan_001',
            features={
                'price_features': {'rsi': 65.0, 'macd_bullish': True},
                'volume_features': {'volume_spike': True}
            },
            patterns={'breakout_up': True},
            regime={'regime': 'trending_up'},
            market_context={'current_price': 50000},
            processing_metadata={'processed_at': datetime.now(timezone.utc).isoformat()},
            llm_format={
                'signal_summary': 'Long BTC signal with 80% confidence',
                'market_context': 'Trending upward market'
            },
            created_at=datetime.now(timezone.utc)
        )
    
    def test_initialization(self):
        """Test DirectTableCommunicator initialization"""
        self.assertEqual(self.communicator.module_type, 'alpha')
        self.assertIsInstance(self.communicator.communication_tags, dict)
        self.assertIn('publish_trading_plan', self.communicator.communication_tags)
        self.assertIn('publish_signal_pack', self.communicator.communication_tags)
    
    def test_serialize_data_trading_plan(self):
        """Test serialization of TradingPlan objects"""
        serialized = self.communicator._serialize_data(self.sample_trading_plan)
        
        self.assertIsInstance(serialized, dict)
        self.assertIn('plan_id', serialized)
        self.assertIn('direction', serialized)
        self.assertIn('entry_price', serialized)
        
        # Check Decimal serialization
        self.assertIsInstance(serialized['entry_price'], (str, float))
        self.assertIsInstance(serialized['position_size'], (str, float))
    
    def test_serialize_data_signal_pack(self):
        """Test serialization of SignalPack objects"""
        serialized = self.communicator._serialize_data(self.sample_signal_pack)
        
        self.assertIsInstance(serialized, dict)
        self.assertIn('pack_id', serialized)
        self.assertIn('signal_id', serialized)
        self.assertIn('features', serialized)
        self.assertIn('llm_format', serialized)
    
    def test_serialize_data_datetime(self):
        """Test serialization of datetime objects"""
        now = datetime.now(timezone.utc)
        serialized = self.communicator._serialize_data(now)
        
        self.assertIsInstance(serialized, str)
        self.assertTrue(serialized.endswith('Z') or '+' in serialized)
    
    def test_serialize_data_decimal(self):
        """Test serialization of Decimal objects"""
        decimal_value = Decimal('123.45')
        serialized = self.communicator._serialize_data(decimal_value)
        
        self.assertIsInstance(serialized, (str, float))
        self.assertEqual(float(serialized), 123.45)
    
    @patch.object(DirectTableCommunicator, '_insert_strand')
    def test_publish_trading_plans(self, mock_insert):
        """Test publishing trading plans"""
        mock_insert.return_value = 'test_strand_id_001'
        
        published_ids = self.communicator.publish_trading_plans([self.sample_trading_plan])
        
        self.assertEqual(len(published_ids), 1)
        self.assertEqual(published_ids[0], 'test_strand_id_001')
        mock_insert.assert_called_once()
        
        # Check the call arguments
        call_args = mock_insert.call_args[0][0]
        self.assertIn('trading_plan', call_args)
        self.assertIn('tags', call_args)
        self.assertEqual(call_args['module'], 'alpha')
        self.assertEqual(call_args['kind'], 'signal')
    
    @patch.object(DirectTableCommunicator, '_insert_strand')
    def test_publish_signal_packs(self, mock_insert):
        """Test publishing signal packs"""
        mock_insert.return_value = 'test_strand_id_002'
        
        published_ids = self.communicator.publish_signal_packs([self.sample_signal_pack])
        
        self.assertEqual(len(published_ids), 1)
        self.assertEqual(published_ids[0], 'test_strand_id_002')
        mock_insert.assert_called_once()
        
        # Check the call arguments
        call_args = mock_insert.call_args[0][0]
        self.assertIn('signal_pack', call_args)
        self.assertIn('tags', call_args)
        self.assertEqual(call_args['module'], 'alpha')
        self.assertEqual(call_args['kind'], 'signal_pack')
    
    @patch.object(DirectTableCommunicator, '_insert_strand')
    def test_publish_multiple_trading_plans(self, mock_insert):
        """Test publishing multiple trading plans and signal packs"""
        mock_insert.side_effect = ['strand_1', 'strand_2']
        
        trading_plans = [self.sample_trading_plan]
        signal_packs = [self.sample_signal_pack]
        
        published_ids = self.communicator.publish_multiple_trading_plans(trading_plans, signal_packs)
        
        self.assertEqual(len(published_ids), 2)
        self.assertEqual(mock_insert.call_count, 2)
    
    def test_get_communication_status(self):
        """Test communication status retrieval"""
        status = self.communicator.get_communication_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('enabled', status)
        self.assertIn('published_count', status)
        self.assertIn('last_publish_time', status)
    
    @patch.object(DirectTableCommunicator, '_insert_strand')
    def test_publish_empty_lists(self, mock_insert):
        """Test publishing empty lists"""
        published_ids = self.communicator.publish_trading_plans([])
        self.assertEqual(len(published_ids), 0)
        mock_insert.assert_not_called()
        
        published_ids = self.communicator.publish_signal_packs([])
        self.assertEqual(len(published_ids), 0)
        mock_insert.assert_not_called()
    
    def test_error_handling_serialization(self):
        """Test error handling in serialization"""
        # Test with non-serializable object
        class NonSerializable:
            def __init__(self):
                self.func = lambda x: x  # Functions are not JSON serializable
        
        non_serializable = NonSerializable()
        
        # Should handle gracefully
        try:
            serialized = self.communicator._serialize_data(non_serializable)
            # If it doesn't raise an exception, it should return something reasonable
            self.assertIsInstance(serialized, (dict, str))
        except (TypeError, ValueError):
            # It's acceptable to raise an exception for non-serializable objects
            pass


class TestModuleListener(unittest.TestCase):
    """Test ModuleListener integration"""
    
    def setUp(self):
        self.mock_db_manager = Mock(spec=SupabaseManager)
        self.listener = ModuleListener(self.mock_db_manager)
    
    def test_initialization(self):
        """Test ModuleListener initialization"""
        self.assertEqual(self.listener.module_type, 'alpha')
        self.assertIsInstance(self.listener.handlers, dict)
        self.assertIsInstance(self.listener.feedback_history, list)
        self.assertFalse(self.listener.is_listening)
    
    def test_register_handler(self):
        """Test handler registration"""
        def test_handler(message):
            return f"Processed: {message}"
        
        self.listener.register_handler('test_tag', test_handler)
        
        self.assertIn('test_tag', self.listener.handlers)
        self.assertEqual(len(self.listener.handlers['test_tag']), 1)
        self.assertEqual(self.listener.handlers['test_tag'][0], test_handler)
    
    def test_register_multiple_handlers(self):
        """Test registering multiple handlers for same tag"""
        def handler1(message):
            return "Handler 1"
        
        def handler2(message):
            return "Handler 2"
        
        self.listener.register_handler('test_tag', handler1)
        self.listener.register_handler('test_tag', handler2)
        
        self.assertEqual(len(self.listener.handlers['test_tag']), 2)
    
    def test_process_message(self):
        """Test message processing"""
        # Register a test handler
        processed_messages = []
        
        def test_handler(message):
            processed_messages.append(message)
        
        self.listener.register_handler('alpha:feedback', test_handler)
        
        # Create test payload
        test_payload = {
            'id': 'test_strand_001',
            'tags': ['alpha:feedback'],
            'data': {'feedback': 'test feedback'},
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Process the message
        self.listener._process_message(test_payload)
        
        # Check that handler was called
        self.assertEqual(len(processed_messages), 1)
        self.assertEqual(processed_messages[0], test_payload)
    
    def test_process_message_multiple_tags(self):
        """Test processing message with multiple tags"""
        processed_messages = []
        
        def handler1(message):
            processed_messages.append(('handler1', message))
        
        def handler2(message):
            processed_messages.append(('handler2', message))
        
        self.listener.register_handler('alpha:feedback', handler1)
        self.listener.register_handler('dm:response', handler2)
        
        # Create test payload with multiple tags
        test_payload = {
            'id': 'test_strand_001',
            'tags': ['alpha:feedback', 'dm:response'],
            'data': {'feedback': 'test feedback'}
        }
        
        self.listener._process_message(test_payload)
        
        # Both handlers should be called
        self.assertEqual(len(processed_messages), 2)
    
    def test_get_listener_status(self):
        """Test listener status retrieval"""
        status = self.listener.get_listener_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('is_listening', status)
        self.assertIn('registered_handlers', status)
        self.assertIn('feedback_count', status)
        self.assertEqual(status['is_listening'], False)
    
    def test_get_feedback_history(self):
        """Test feedback history retrieval"""
        # Add some test feedback
        test_feedback = {
            'id': 'test_001',
            'message': 'test feedback',
            'timestamp': datetime.now(timezone.utc)
        }
        self.listener.feedback_history.append(test_feedback)
        
        history = self.listener.get_feedback_history(limit=10)
        
        self.assertIsInstance(history, list)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['id'], 'test_001')
    
    def test_get_feedback_history_limit(self):
        """Test feedback history with limit"""
        # Add multiple feedback items
        for i in range(5):
            self.listener.feedback_history.append({
                'id': f'test_{i:03d}',
                'message': f'feedback {i}',
                'timestamp': datetime.now(timezone.utc)
            })
        
        history = self.listener.get_feedback_history(limit=3)
        
        self.assertEqual(len(history), 3)
        # Should return most recent items
        self.assertEqual(history[0]['id'], 'test_004')
        self.assertEqual(history[1]['id'], 'test_003')
        self.assertEqual(history[2]['id'], 'test_002')


class TestCommunicationIntegration(unittest.TestCase):
    """Test integrated communication system"""
    
    def setUp(self):
        self.mock_db_manager = Mock(spec=SupabaseManager)
        self.communicator = DirectTableCommunicator(self.mock_db_manager)
        self.listener = ModuleListener(self.mock_db_manager)
        
        self.sample_trading_plan = self.create_sample_trading_plan()
        self.sample_signal_pack = self.create_sample_signal_pack()
    
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
            market_context={'current_price': 50000},
            signal_metadata={'source': 'alpha_detector'}
        )
    
    def create_sample_signal_pack(self):
        """Create sample signal pack for testing"""
        return SignalPack(
            pack_id='test_pack_001',
            signal_id='test_signal_001',
            trading_plan_id='test_plan_001',
            features={'price_features': {'rsi': 65.0}},
            patterns={'breakout_up': True},
            regime={'regime': 'trending_up'},
            market_context={'current_price': 50000},
            processing_metadata={'processed_at': datetime.now(timezone.utc).isoformat()},
            llm_format={'signal_summary': 'Long BTC signal'},
            created_at=datetime.now(timezone.utc)
        )
    
    @patch.object(DirectTableCommunicator, '_insert_strand')
    def test_end_to_end_communication(self, mock_insert):
        """Test end-to-end communication flow"""
        mock_insert.return_value = 'test_strand_001'
        
        # Set up feedback handler
        received_feedback = []
        
        def feedback_handler(message):
            received_feedback.append(message)
        
        self.listener.register_handler('dm:response', feedback_handler)
        
        # 1. Publish trading plan
        published_ids = self.communicator.publish_trading_plans([self.sample_trading_plan])
        self.assertEqual(len(published_ids), 1)
        
        # 2. Simulate feedback from Decision Maker
        feedback_message = {
            'id': 'dm_response_001',
            'tags': ['dm:response'],
            'data': {
                'plan_id': 'test_plan_001',
                'decision': 'approved',
                'confidence': 0.9
            },
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # 3. Process feedback
        self.listener._process_message(feedback_message)
        
        # 4. Verify feedback was received and processed
        self.assertEqual(len(received_feedback), 1)
        self.assertEqual(received_feedback[0]['data']['decision'], 'approved')
    
    def test_communication_tags_alignment(self):
        """Test that communication tags align between components"""
        # Check that communicator and listener use compatible tags
        comm_tags = self.communicator.communication_tags
        
        # Communicator should have tags for publishing
        self.assertIn('publish_trading_plan', comm_tags)
        self.assertIn('publish_signal_pack', comm_tags)
        
        # Tags should be properly formatted for Decision Maker
        dm_tags = comm_tags['publish_trading_plan']
        self.assertIn('dm:evaluate_plan', dm_tags)
    
    def test_error_handling_integration(self):
        """Test error handling in integrated system"""
        # Test with invalid data
        invalid_trading_plan = "not a trading plan"
        
        try:
            self.communicator.publish_trading_plans([invalid_trading_plan])
        except (TypeError, AttributeError) as e:
            # Should handle gracefully
            self.assertIsInstance(e, (TypeError, AttributeError))
    
    @patch.object(DirectTableCommunicator, '_insert_strand')
    def test_communication_status_integration(self, mock_insert):
        """Test communication status across components"""
        mock_insert.return_value = 'test_strand_001'
        
        # Initial status
        comm_status = self.communicator.get_communication_status()
        listener_status = self.listener.get_listener_status()
        
        self.assertIsInstance(comm_status, dict)
        self.assertIsInstance(listener_status, dict)
        
        # Publish something
        self.communicator.publish_trading_plans([self.sample_trading_plan])
        
        # Status should update
        updated_status = self.communicator.get_communication_status()
        self.assertGreaterEqual(updated_status['published_count'], 1)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)

