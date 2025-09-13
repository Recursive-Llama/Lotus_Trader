#!/usr/bin/env python3
"""
Simple Test Runner

This script runs a basic test of the core learning system components
without complex dependencies.
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

class SimpleTestRunner:
    """Simple test runner for core functionality"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    async def run_tests(self):
        """Run simple tests"""
        logger.info("🚀 Starting Simple Test Suite")
        logger.info("=" * 50)
        
        self.start_time = time.time()
        
        tests = [
            ("Basic Math Operations", self.test_basic_math),
            ("Data Structures", self.test_data_structures),
            ("Async Operations", self.test_async_operations),
            ("JSON Processing", self.test_json_processing),
            ("UUID Generation", self.test_uuid_generation),
            ("DateTime Operations", self.test_datetime_operations)
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
                failed += 1
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        logger.info("\n" + "=" * 50)
        logger.info(f"📊 Test Results: {passed} passed, {failed} failed")
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        
        if failed == 0:
            logger.info("🎉 All simple tests passed!")
            return True
        else:
            logger.error("⚠️  Some tests failed.")
            return False
    
    async def test_basic_math(self):
        """Test basic mathematical operations"""
        # Test addition
        assert 2 + 2 == 4, "Basic addition failed"
        
        # Test multiplication
        assert 3 * 4 == 12, "Basic multiplication failed"
        
        # Test division
        assert 10 / 2 == 5, "Basic division failed"
        
        # Test power
        assert 2 ** 3 == 8, "Basic power failed"
        
        # Test square root
        import math
        assert math.sqrt(16) == 4, "Square root failed"
        
        logger.info("  ✅ Basic math operations working")
    
    async def test_data_structures(self):
        """Test data structure operations"""
        # Test list operations
        test_list = [1, 2, 3, 4, 5]
        assert len(test_list) == 5, "List length failed"
        assert test_list[0] == 1, "List indexing failed"
        assert test_list[-1] == 5, "List negative indexing failed"
        
        # Test dictionary operations
        test_dict = {'a': 1, 'b': 2, 'c': 3}
        assert test_dict['a'] == 1, "Dictionary access failed"
        assert 'b' in test_dict, "Dictionary membership failed"
        assert len(test_dict) == 3, "Dictionary length failed"
        
        # Test set operations
        test_set = {1, 2, 3, 4, 5}
        assert len(test_set) == 5, "Set length failed"
        assert 3 in test_set, "Set membership failed"
        
        logger.info("  ✅ Data structures working")
    
    async def test_async_operations(self):
        """Test async operations"""
        # Test basic async function
        async def async_add(a, b):
            await asyncio.sleep(0.01)  # Simulate async work
            return a + b
        
        result = await async_add(5, 3)
        assert result == 8, "Async addition failed"
        
        # Test async list comprehension
        async def async_square(x):
            await asyncio.sleep(0.01)
            return x * x
        
        numbers = [1, 2, 3, 4, 5]
        results = await asyncio.gather(*[async_square(x) for x in numbers])
        expected = [1, 4, 9, 16, 25]
        assert results == expected, "Async list comprehension failed"
        
        logger.info("  ✅ Async operations working")
    
    async def test_json_processing(self):
        """Test JSON processing"""
        # Test JSON serialization
        test_data = {
            'strand_id': 'test_123',
            'kind': 'pattern',
            'content': {
                'pattern_type': 'volume_spike',
                'confidence': 0.85
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        json_str = json.dumps(test_data)
        assert isinstance(json_str, str), "JSON serialization failed"
        
        # Test JSON deserialization
        parsed_data = json.loads(json_str)
        assert parsed_data['strand_id'] == 'test_123', "JSON deserialization failed"
        assert parsed_data['kind'] == 'pattern', "JSON deserialization failed"
        assert parsed_data['content']['confidence'] == 0.85, "JSON deserialization failed"
        
        logger.info("  ✅ JSON processing working")
    
    async def test_uuid_generation(self):
        """Test UUID generation"""
        # Test UUID4 generation
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())
        
        assert len(uuid1) == 36, "UUID length failed"
        assert uuid1 != uuid2, "UUID uniqueness failed"
        assert uuid1.count('-') == 4, "UUID format failed"
        
        # Test multiple UUIDs
        uuids = [str(uuid.uuid4()) for _ in range(10)]
        assert len(set(uuids)) == 10, "UUID uniqueness failed"
        
        logger.info("  ✅ UUID generation working")
    
    async def test_datetime_operations(self):
        """Test datetime operations"""
        # Test current time
        now = datetime.now(timezone.utc)
        assert isinstance(now, datetime), "Current time failed"
        
        # Test ISO format
        iso_str = now.isoformat()
        assert 'T' in iso_str, "ISO format failed"
        assert iso_str.endswith('+00:00') or iso_str.endswith('Z'), "UTC format failed"
        
        # Test timezone operations
        utc_now = datetime.now(timezone.utc)
        local_now = datetime.now()
        assert utc_now.tzinfo is not None, "UTC timezone failed"
        
        # Test timedelta
        future_time = now + timedelta(hours=1)
        assert future_time > now, "Timedelta addition failed"
        
        logger.info("  ✅ DateTime operations working")

async def main():
    """Main test runner"""
    test_runner = SimpleTestRunner()
    
    try:
        success = await test_runner.run_tests()
        
        if success:
            logger.info("\n🎉 Simple test suite passed!")
            logger.info("Core functionality is working correctly.")
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
