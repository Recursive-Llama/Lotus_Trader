"""
Integration Test Runner

This script runs all integration tests in sequence to validate the complete
data flow through the system with real websocket connections and LLM calls.
"""

import pytest
import asyncio
import sys
import os
import time
from datetime import datetime
import logging

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integration_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IntegrationTestRunner:
    """Runs all integration tests in sequence"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    async def run_all_integration_tests(self):
        """Run all integration tests in sequence"""
        logger.info("🚀 Starting Integration Test Suite...")
        self.start_time = time.time()
        
        # Test 1: Raw Data → CIL Flow
        logger.info("=" * 80)
        logger.info("TEST 1: Raw Data Intelligence → CIL Flow")
        logger.info("=" * 80)
        
        try:
            result = await self._run_test("test_integration_raw_data_to_cil_flow.py")
            self.test_results['raw_data_to_cil'] = result
            logger.info(f"✅ Raw Data → CIL Flow: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            logger.error(f"❌ Raw Data → CIL Flow FAILED: {e}")
            self.test_results['raw_data_to_cil'] = False
        
        # Test 2: CIL → Decision Maker Flow
        logger.info("=" * 80)
        logger.info("TEST 2: CIL → Decision Maker Flow")
        logger.info("=" * 80)
        
        try:
            result = await self._run_test("test_integration_cil_to_decision_maker_flow.py")
            self.test_results['cil_to_decision_maker'] = result
            logger.info(f"✅ CIL → Decision Maker Flow: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            logger.error(f"❌ CIL → Decision Maker Flow FAILED: {e}")
            self.test_results['cil_to_decision_maker'] = False
        
        # Test 3: Decision Maker → Trader Flow
        logger.info("=" * 80)
        logger.info("TEST 3: Decision Maker → Trader Flow")
        logger.info("=" * 80)
        
        try:
            result = await self._run_test("test_integration_decision_maker_to_trader_flow.py")
            self.test_results['decision_maker_to_trader'] = result
            logger.info(f"✅ Decision Maker → Trader Flow: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            logger.error(f"❌ Decision Maker → Trader Flow FAILED: {e}")
            self.test_results['decision_maker_to_trader'] = False
        
        # Test 4: Trader → CIL Feedback Flow
        logger.info("=" * 80)
        logger.info("TEST 4: Trader → CIL Feedback Flow")
        logger.info("=" * 80)
        
        try:
            result = await self._run_test("test_integration_trader_to_cil_feedback.py")
            self.test_results['trader_to_cil_feedback'] = result
            logger.info(f"✅ Trader → CIL Feedback Flow: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            logger.error(f"❌ Trader → CIL Feedback Flow FAILED: {e}")
            self.test_results['trader_to_cil_feedback'] = False
        
        # Test 5: Full Cycle Integration
        logger.info("=" * 80)
        logger.info("TEST 5: Full Cycle Integration")
        logger.info("=" * 80)
        
        try:
            result = await self._run_test("test_integration_full_cycle_flow.py")
            self.test_results['full_cycle_integration'] = result
            logger.info(f"✅ Full Cycle Integration: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            logger.error(f"❌ Full Cycle Integration FAILED: {e}")
            self.test_results['full_cycle_integration'] = False
        
        # Generate final report
        self.end_time = time.time()
        self._generate_final_report()
    
    async def _run_test(self, test_file: str) -> bool:
        """Run a specific integration test"""
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        
        if not os.path.exists(test_path):
            logger.error(f"Test file not found: {test_path}")
            return False
        
        try:
            # Run the test using pytest
            result = pytest.main([test_path, "-v", "-s", "--tb=short"])
            return result == 0
        except Exception as e:
            logger.error(f"Error running test {test_file}: {e}")
            return False
    
    def _generate_final_report(self):
        """Generate final test report"""
        logger.info("=" * 80)
        logger.info("INTEGRATION TEST SUITE RESULTS")
        logger.info("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.start_time and self.end_time:
            total_time = self.end_time - self.start_time
            logger.info(f"Total Execution Time: {total_time:.2f} seconds")
        
        logger.info("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"  {test_name}: {status}")
        
        # Data flow summary
        logger.info("\nData Flow Summary:")
        if self.test_results.get('raw_data_to_cil', False):
            logger.info("  ✅ Raw Data Intelligence → CIL: Working")
        else:
            logger.info("  ❌ Raw Data Intelligence → CIL: Failed")
        
        if self.test_results.get('cil_to_decision_maker', False):
            logger.info("  ✅ CIL → Decision Maker: Working")
        else:
            logger.info("  ❌ CIL → Decision Maker: Failed")
        
        if self.test_results.get('decision_maker_to_trader', False):
            logger.info("  ✅ Decision Maker → Trader: Working")
        else:
            logger.info("  ❌ Decision Maker → Trader: Failed")
        
        if self.test_results.get('trader_to_cil_feedback', False):
            logger.info("  ✅ Trader → CIL Feedback: Working")
        else:
            logger.info("  ❌ Trader → CIL Feedback: Failed")
        
        if self.test_results.get('full_cycle_integration', False):
            logger.info("  ✅ Full Cycle Integration: Working")
        else:
            logger.info("  ❌ Full Cycle Integration: Failed")
        
        # Overall system status
        if all(self.test_results.values()):
            logger.info("\n🎉 ALL INTEGRATION TESTS PASSED!")
            logger.info("The complete data flow through the system is working correctly.")
            logger.info("Ready for production deployment!")
        else:
            logger.info("\n⚠️  SOME INTEGRATION TESTS FAILED!")
            logger.info("Please review the failed tests and fix the issues before deployment.")
        
        logger.info("=" * 80)


async def main():
    """Main function to run integration tests"""
    runner = IntegrationTestRunner()
    await runner.run_all_integration_tests()


if __name__ == "__main__":
    # Run the integration test suite
    asyncio.run(main())
