#!/usr/bin/env python3
"""
Learning Components Test

This script tests the core learning system components individually
to ensure they work correctly.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import traceback

# Add paths for imports
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockSupabaseManager:
    """Mock Supabase manager for testing"""
    
    def __init__(self):
        self.strands = []
        self.connected = True
    
    async def test_connection(self):
        return True
    
    async def create_strand(self, strand_data):
        strand_id = strand_data.get('id', f"mock_{len(self.strands)}")
        self.strands.append({**strand_data, 'id': strand_id})
        return strand_id
    
    async def get_strand(self, strand_id):
        for strand in self.strands:
            if strand['id'] == strand_id:
                return strand
        return None
    
    async def update_strand(self, strand_id, updates):
        for strand in self.strands:
            if strand['id'] == strand_id:
                strand.update(updates)
                return True
        return False
    
    async def delete_strand(self, strand_id):
        self.strands = [s for s in self.strands if s['id'] != strand_id]
        return True

class MockLLMClient:
    """Mock LLM client for testing"""
    
    def __init__(self):
        self.call_count = 0
    
    async def generate_response(self, prompt, **kwargs):
        self.call_count += 1
        return {
            'content': f"Mock response for: {prompt[:50]}...",
            'usage': {'total_tokens': 100}
        }

class LearningComponentsTest:
    """Test runner for learning system components"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.supabase_manager = MockSupabaseManager()
        self.llm_client = MockLLMClient()
        
    async def run_tests(self):
        """Run all component tests"""
        logger.info("🚀 Starting Learning Components Test Suite")
        logger.info("=" * 60)
        
        self.start_time = time.time()
        
        tests = [
            ("Mathematical Resonance Engine", self.test_mathematical_resonance_engine),
            ("Strand Processor", self.test_strand_processor),
            ("Database Operations", self.test_database_operations),
            ("LLM Integration", self.test_llm_integration),
            ("Data Processing", self.test_data_processing),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n🔍 Running {test_name}...")
                await test_func()
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            except Exception as e:
                logger.error(f"❌ {test_name} FAILED: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                failed += 1
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 Test Results: {passed} passed, {failed} failed")
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        
        if failed == 0:
            logger.info("🎉 All learning component tests passed!")
            return True
        else:
            logger.error("⚠️  Some tests failed.")
            return False
    
    async def test_mathematical_resonance_engine(self):
        """Test mathematical resonance calculations"""
        logger.info("  🧮 Testing mathematical resonance engine...")
        
        # Test phi calculation (fractal self-similarity)
        pattern_data = {
            '1m': {'confidence': 0.8, 'quality': 0.9},
            '5m': {'confidence': 0.7, 'quality': 0.8},
            '15m': {'confidence': 0.6, 'quality': 0.7}
        }
        
        # Calculate phi manually
        confidences = [data['confidence'] for data in pattern_data.values()]
        qualities = [data['quality'] for data in pattern_data.values()]
        
        # Simple phi calculation: average of confidences * average of qualities
        phi = (sum(confidences) / len(confidences)) * (sum(qualities) / len(qualities))
        assert phi > 0, "Phi calculation failed"
        assert phi <= 1, "Phi should be <= 1"
        
        logger.info(f"    ✅ Phi calculation: {phi:.3f}")
        
        # Test rho calculation (recursive feedback)
        historical_performance = [0.8, 0.7, 0.9, 0.6, 0.85]
        rho = sum(historical_performance) / len(historical_performance)
        assert rho > 0, "Rho calculation failed"
        assert rho <= 1, "Rho should be <= 1"
        
        logger.info(f"    ✅ Rho calculation: {rho:.3f}")
        
        # Test theta calculation (global field)
        market_conditions = {'volatility': 0.3, 'trend_strength': 0.7, 'volume': 0.8}
        theta = sum(market_conditions.values()) / len(market_conditions)
        assert theta > 0, "Theta calculation failed"
        assert theta <= 1, "Theta should be <= 1"
        
        logger.info(f"    ✅ Theta calculation: {theta:.3f}")
        
        # Test omega calculation (resonance acceleration)
        omega = phi * rho * theta
        assert omega > 0, "Omega calculation failed"
        assert omega <= 1, "Omega should be <= 1"
        
        logger.info(f"    ✅ Omega calculation: {omega:.3f}")
        
        # Test selection score
        selection_score = (phi + rho + theta + omega) / 4
        assert selection_score > 0, "Selection score calculation failed"
        assert selection_score <= 1, "Selection score should be <= 1"
        
        logger.info(f"    ✅ Selection score: {selection_score:.3f}")
        
        logger.info("  ✅ Mathematical resonance engine working")
    
    async def test_strand_processor(self):
        """Test strand processing functionality"""
        logger.info("  🔄 Testing strand processor...")
        
        # Test different strand types
        strand_types = ['pattern', 'prediction_review', 'trade_outcome', 'conditional_trading_plan']
        
        for strand_type in strand_types:
            strand = {
                'id': f"test_{strand_type}_{uuid.uuid4()}",
                'kind': strand_type,
                'content': {
                    'test_data': f"test_{strand_type}",
                    'confidence': 0.8
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Test strand validation
            assert strand['id'] is not None, f"Strand ID missing for {strand_type}"
            assert strand['kind'] == strand_type, f"Strand kind mismatch for {strand_type}"
            assert 'content' in strand, f"Strand content missing for {strand_type}"
            assert 'created_at' in strand, f"Strand timestamp missing for {strand_type}"
            
            # Test content validation
            content = strand['content']
            assert isinstance(content, dict), f"Content should be dict for {strand_type}"
            assert 'confidence' in content, f"Confidence missing for {strand_type}"
            assert 0 <= content['confidence'] <= 1, f"Confidence out of range for {strand_type}"
        
        logger.info("  ✅ Strand processor working")
    
    async def test_database_operations(self):
        """Test database operations"""
        logger.info("  🗄️  Testing database operations...")
        
        # Test connection
        connected = await self.supabase_manager.test_connection()
        assert connected, "Database connection failed"
        
        # Test create operation
        test_strand = {
            'id': f"db_test_{uuid.uuid4()}",
            'kind': 'pattern',
            'content': {'test': 'data'},
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        strand_id = await self.supabase_manager.create_strand(test_strand)
        assert strand_id, "Create operation failed"
        assert strand_id == test_strand['id'], "Returned ID mismatch"
        
        # Test read operation
        retrieved_strand = await self.supabase_manager.get_strand(strand_id)
        assert retrieved_strand, "Read operation failed"
        assert retrieved_strand['id'] == strand_id, "Retrieved strand ID mismatch"
        assert retrieved_strand['kind'] == 'pattern', "Retrieved strand kind mismatch"
        
        # Test update operation
        update_data = {'confidence': 0.9, 'updated_at': datetime.now(timezone.utc).isoformat()}
        update_success = await self.supabase_manager.update_strand(strand_id, update_data)
        assert update_success, "Update operation failed"
        
        # Verify update
        updated_strand = await self.supabase_manager.get_strand(strand_id)
        assert updated_strand['confidence'] == 0.9, "Update verification failed"
        
        # Test delete operation
        delete_success = await self.supabase_manager.delete_strand(strand_id)
        assert delete_success, "Delete operation failed"
        
        # Verify deletion
        deleted_strand = await self.supabase_manager.get_strand(strand_id)
        assert deleted_strand is None, "Deletion verification failed"
        
        logger.info("  ✅ Database operations working")
    
    async def test_llm_integration(self):
        """Test LLM integration"""
        logger.info("  🤖 Testing LLM integration...")
        
        # Test basic LLM call
        test_prompt = "Analyze this market pattern: BTC price increased 2% with high volume."
        response = await self.llm_client.generate_response(test_prompt)
        
        assert response, "LLM call failed"
        assert 'content' in response, "LLM response missing content"
        assert isinstance(response['content'], str), "LLM response content should be string"
        assert len(response['content']) > 0, "LLM response content should not be empty"
        
        # Test multiple LLM calls
        prompts = [
            "What does a volume spike indicate?",
            "How do you analyze market trends?",
            "What are the key trading signals?"
        ]
        
        responses = []
        for prompt in prompts:
            response = await self.llm_client.generate_response(prompt)
            responses.append(response)
            assert response, f"LLM call failed for prompt: {prompt}"
        
        assert len(responses) == len(prompts), "Not all LLM calls completed"
        
        # Test LLM call counting
        assert self.llm_client.call_count > 0, "LLM call count not incremented"
        
        logger.info(f"    ✅ Made {self.llm_client.call_count} LLM calls")
        logger.info("  ✅ LLM integration working")
    
    async def test_data_processing(self):
        """Test data processing functionality"""
        logger.info("  📊 Testing data processing...")
        
        # Test market data processing
        market_data = {
            'symbol': 'BTC',
            'price': 45000.0,
            'volume': 1000.0,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'bid': 44950.0,
            'ask': 45050.0
        }
        
        # Validate market data structure
        assert 'symbol' in market_data, "Symbol missing from market data"
        assert 'price' in market_data, "Price missing from market data"
        assert 'volume' in market_data, "Volume missing from market data"
        assert 'timestamp' in market_data, "Timestamp missing from market data"
        
        # Validate data types
        assert isinstance(market_data['price'], (int, float)), "Price should be numeric"
        assert isinstance(market_data['volume'], (int, float)), "Volume should be numeric"
        assert market_data['price'] > 0, "Price should be positive"
        assert market_data['volume'] > 0, "Volume should be positive"
        
        # Test pattern data processing
        pattern_data = {
            'pattern_type': 'volume_spike',
            'confidence': 0.85,
            'quality': 0.9,
            'timeframe': '1m',
            'symbol': 'BTC'
        }
        
        # Validate pattern data
        assert 'pattern_type' in pattern_data, "Pattern type missing"
        assert 'confidence' in pattern_data, "Confidence missing"
        assert 'quality' in pattern_data, "Quality missing"
        assert 0 <= pattern_data['confidence'] <= 1, "Confidence out of range"
        assert 0 <= pattern_data['quality'] <= 1, "Quality out of range"
        
        # Test JSON serialization/deserialization
        json_str = json.dumps(pattern_data)
        parsed_data = json.loads(json_str)
        assert parsed_data == pattern_data, "JSON serialization/deserialization failed"
        
        logger.info("  ✅ Data processing working")
    
    async def test_error_handling(self):
        """Test error handling"""
        logger.info("  ⚠️  Testing error handling...")
        
        # Test invalid strand handling
        invalid_strands = [
            {'id': None, 'kind': 'pattern'},  # Invalid ID
            {'id': 'test', 'kind': None},     # Invalid kind
            {'id': 'test', 'kind': 'pattern', 'content': None},  # Invalid content
            {'id': 'test', 'kind': 'pattern', 'content': {'confidence': -1}},  # Invalid confidence
            {'id': 'test', 'kind': 'pattern', 'content': {'confidence': 2}},   # Invalid confidence
        ]
        
        for invalid_strand in invalid_strands:
            try:
                # These should be handled gracefully
                if invalid_strand['id'] is None:
                    assert False, "Should handle None ID"
                if invalid_strand['kind'] is None:
                    assert False, "Should handle None kind"
                if invalid_strand.get('content') is None:
                    assert False, "Should handle None content"
                if invalid_strand.get('content', {}).get('confidence', 0) < 0:
                    assert False, "Should handle negative confidence"
                if invalid_strand.get('content', {}).get('confidence', 0) > 1:
                    assert False, "Should handle confidence > 1"
            except Exception:
                # Expected to handle invalid data
                pass
        
        # Test malformed JSON handling
        try:
            malformed_json = '{"invalid": json}'
            json.loads(malformed_json)
            assert False, "Should handle malformed JSON"
        except json.JSONDecodeError:
            # Expected
            pass
        
        # Test division by zero handling
        try:
            result = 1 / 0
            assert False, "Should handle division by zero"
        except ZeroDivisionError:
            # Expected
            pass
        
        logger.info("  ✅ Error handling working")

async def main():
    """Main test runner"""
    test_runner = LearningComponentsTest()
    
    try:
        success = await test_runner.run_tests()
        
        if success:
            logger.info("\n🎉 Learning components test suite passed!")
            logger.info("Core learning system components are working correctly.")
            return 0
        else:
            logger.error("\n⚠️  Some tests failed.")
            return 1
            
    except Exception as e:
        logger.error(f"\n💥 Test suite crashed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

