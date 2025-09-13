#!/usr/bin/env python3
"""
Complete System Test Runner

This script runs the complete system test suite, including:
1. Database setup and validation
2. Complete system testing
3. Performance validation
4. Integration testing
5. Cleanup and reporting

Usage:
    python run_complete_tests.py [--setup-only] [--test-only] [--cleanup-only]
"""

import asyncio
import argparse
import logging
import sys
import time
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir.parent.parent / "Modules" / "Alpha_Detector"))
sys.path.append(str(current_dir.parent.parent / "Modules" / "Alpha_Detector" / "src"))

from setup_database import DatabaseSetup
from complete_system_test_suite import CompleteSystemTestSuite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('complete_system_test.log')
    ]
)
logger = logging.getLogger(__name__)

class TestRunner:
    """Complete test runner orchestrator"""
    
    def __init__(self):
        self.database_setup = DatabaseSetup()
        self.test_suite = CompleteSystemTestSuite()
        self.start_time = None
        self.end_time = None
        self.results = {
            'database_setup': False,
            'system_tests': False,
            'performance_tests': False,
            'integration_tests': False,
            'cleanup': False
        }
    
    async def run_setup(self):
        """Run database setup"""
        logger.info("🚀 Starting database setup...")
        self.start_time = time.time()
        
        try:
            success = await self.database_setup.setup_database()
            self.results['database_setup'] = success
            
            if success:
                logger.info("✅ Database setup completed successfully")
            else:
                logger.error("❌ Database setup failed")
            
            return success
            
        except Exception as e:
            logger.error(f"💥 Database setup crashed: {e}")
            self.results['database_setup'] = False
            return False
    
    async def run_tests(self):
        """Run complete system tests"""
        logger.info("🧪 Starting complete system tests...")
        
        try:
            success = await self.test_suite.run_complete_test_suite()
            self.results['system_tests'] = success
            
            if success:
                logger.info("✅ System tests completed successfully")
            else:
                logger.error("❌ System tests failed")
            
            return success
            
        except Exception as e:
            logger.error(f"💥 System tests crashed: {e}")
            self.results['system_tests'] = False
            return False
    
    async def run_cleanup(self):
        """Run cleanup"""
        logger.info("🧹 Starting cleanup...")
        
        try:
            await self.database_setup.cleanup_database()
            self.results['cleanup'] = True
            logger.info("✅ Cleanup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"💥 Cleanup crashed: {e}")
            self.results['cleanup'] = False
            return False
    
    def print_summary(self):
        """Print test summary"""
        self.end_time = time.time()
        total_time = self.end_time - self.start_time if self.start_time else 0
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 COMPLETE SYSTEM TEST SUMMARY")
        logger.info("=" * 80)
        
        # Test results
        logger.info("🔍 Test Results:")
        for test_name, result in self.results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        # Overall status
        all_passed = all(self.results.values())
        overall_status = "🎉 ALL TESTS PASSED" if all_passed else "⚠️  SOME TESTS FAILED"
        logger.info(f"\n🏆 Overall Status: {overall_status}")
        
        # Timing
        logger.info(f"\n⏱️  Total Execution Time: {total_time:.2f} seconds")
        
        # System stats (if available)
        if hasattr(self.test_suite, 'system_stats'):
            stats = self.test_suite.system_stats
            logger.info(f"\n📈 System Statistics:")
            logger.info(f"   Strands Created: {stats.get('strands_created', 0)}")
            logger.info(f"   LLM Calls Made: {stats.get('llm_calls_made', 0)}")
            logger.info(f"   Database Operations: {stats.get('database_operations', 0)}")
            logger.info(f"   Errors Encountered: {stats.get('errors_encountered', 0)}")
            logger.info(f"   Memory Usage: {stats.get('memory_usage_mb', 0):.2f} MB")
            logger.info(f"   CPU Usage: {stats.get('cpu_usage_percent', 0):.2f}%")
        
        logger.info("=" * 80)
        
        return all_passed
    
    async def run_complete(self):
        """Run complete test suite"""
        logger.info("🚀 Starting Complete System Test Suite")
        logger.info("=" * 80)
        
        try:
            # 1. Database setup
            setup_success = await self.run_setup()
            if not setup_success:
                logger.error("❌ Database setup failed, aborting tests")
                return False
            
            # 2. System tests
            test_success = await self.run_tests()
            if not test_success:
                logger.error("❌ System tests failed")
            
            # 3. Cleanup
            cleanup_success = await self.run_cleanup()
            if not cleanup_success:
                logger.warning("⚠️  Cleanup failed, but tests completed")
            
            # 4. Summary
            all_passed = self.print_summary()
            
            return all_passed
            
        except Exception as e:
            logger.error(f"💥 Test runner crashed: {e}")
            return False

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Complete System Test Runner')
    parser.add_argument('--setup-only', action='store_true', help='Run only database setup')
    parser.add_argument('--test-only', action='store_true', help='Run only system tests')
    parser.add_argument('--cleanup-only', action='store_true', help='Run only cleanup')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    runner = TestRunner()
    
    try:
        if args.setup_only:
            success = await runner.run_setup()
        elif args.test_only:
            success = await runner.run_tests()
        elif args.cleanup_only:
            success = await runner.run_cleanup()
        else:
            success = await runner.run_complete()
        
        if success:
            logger.info("🎉 All operations completed successfully!")
            return 0
        else:
            logger.error("❌ Some operations failed!")
            return 1
            
    except KeyboardInterrupt:
        logger.info("🛑 Test runner interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Test runner crashed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

