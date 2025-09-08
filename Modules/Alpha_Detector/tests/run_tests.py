#!/usr/bin/env python3
"""
Alpha Detector Test Runner
Phase 1.6.3: Comprehensive Test Suite Runner

This script provides a comprehensive test runner for the Alpha Detector module
with detailed reporting, categorization, and performance metrics.
"""

import sys
import os
import unittest
import time
import argparse
from io import StringIO
from datetime import datetime

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import test categories
from tests import UNIT_TESTS, INTEGRATION_TESTS, LEGACY_TESTS, ALL_TESTS


class ColoredTextTestResult(unittest.TextTestResult):
    """Custom test result class with colored output"""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.success_count = 0
        self.start_time = None
        self.test_times = {}
    
    def startTest(self, test):
        super().startTest(test)
        self.start_time = time.time()
        if self.verbosity >= 2:
            self.stream.write(f"Running {test._testMethodName} ... ")
            self.stream.flush()
    
    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_count += 1
        test_time = time.time() - self.start_time
        self.test_times[str(test)] = test_time
        
        if self.verbosity >= 2:
            self.stream.write(f"\033[92m✓ PASS\033[0m ({test_time:.3f}s)\n")
            self.stream.flush()
    
    def addError(self, test, err):
        super().addError(test, err)
        test_time = time.time() - self.start_time
        self.test_times[str(test)] = test_time
        
        if self.verbosity >= 2:
            self.stream.write(f"\033[91m✗ ERROR\033[0m ({test_time:.3f}s)\n")
            self.stream.flush()
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        test_time = time.time() - self.start_time
        self.test_times[str(test)] = test_time
        
        if self.verbosity >= 2:
            self.stream.write(f"\033[91m✗ FAIL\033[0m ({test_time:.3f}s)\n")
            self.stream.flush()
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        test_time = time.time() - self.start_time
        self.test_times[str(test)] = test_time
        
        if self.verbosity >= 2:
            self.stream.write(f"\033[93m- SKIP\033[0m ({test_time:.3f}s): {reason}\n")
            self.stream.flush()


class TestRunner:
    """Comprehensive test runner with reporting"""
    
    def __init__(self, verbosity=2):
        self.verbosity = verbosity
        self.results = {}
    
    def run_test_category(self, category_name, test_modules):
        """Run a category of tests"""
        print(f"\n{'='*60}")
        print(f"🧪 RUNNING {category_name.upper()} TESTS")
        print(f"{'='*60}")
        
        suite = unittest.TestSuite()
        loader = unittest.TestLoader()
        
        # Load tests from specified modules
        for test_module in test_modules:
            try:
                module = __import__(f'tests.{test_module}', fromlist=[test_module])
                suite.addTests(loader.loadTestsFromModule(module))
            except ImportError as e:
                print(f"\033[93m⚠ Warning: Could not import {test_module}: {e}\033[0m")
                continue
        
        # Run tests
        runner = unittest.TextTestRunner(
            stream=sys.stdout,
            verbosity=self.verbosity,
            resultclass=ColoredTextTestResult
        )
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # Store results
        self.results[category_name] = {
            'result': result,
            'duration': end_time - start_time,
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped),
            'success_count': getattr(result, 'success_count', 0)
        }
        
        return result
    
    def run_all_tests(self):
        """Run all test categories"""
        print(f"\033[96m{'='*80}\033[0m")
        print(f"\033[96m🚀 ALPHA DETECTOR COMPREHENSIVE TEST SUITE\033[0m")
        print(f"\033[96m{'='*80}\033[0m")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        overall_start = time.time()
        
        # Run unit tests
        self.run_test_category('Unit Tests', UNIT_TESTS)
        
        # Run integration tests
        self.run_test_category('Integration Tests', INTEGRATION_TESTS)
        
        overall_end = time.time()
        
        # Generate summary report
        self.generate_summary_report(overall_end - overall_start)
    
    def run_legacy_tests(self):
        """Run legacy tests separately"""
        print(f"\n{'='*60}")
        print(f"🔧 RUNNING LEGACY TESTS")
        print(f"{'='*60}")
        print("Note: These are pre-Phase 1.6 tests maintained for compatibility")
        
        self.run_test_category('Legacy Tests', LEGACY_TESTS)
    
    def run_specific_tests(self, test_modules):
        """Run specific test modules"""
        print(f"\n{'='*60}")
        print(f"🎯 RUNNING SPECIFIC TESTS")
        print(f"{'='*60}")
        
        self.run_test_category('Specific Tests', test_modules)
    
    def generate_summary_report(self, total_duration):
        """Generate comprehensive summary report"""
        print(f"\n\033[96m{'='*80}\033[0m")
        print(f"\033[96m📊 TEST SUMMARY REPORT\033[0m")
        print(f"\033[96m{'='*80}\033[0m")
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_skipped = 0
        total_success = 0
        
        # Category summaries
        for category, stats in self.results.items():
            total_tests += stats['tests_run']
            total_failures += stats['failures']
            total_errors += stats['errors']
            total_skipped += stats['skipped']
            total_success += stats['success_count']
            
            # Category status
            if stats['failures'] == 0 and stats['errors'] == 0:
                status = f"\033[92m✓ PASSED\033[0m"
            else:
                status = f"\033[91m✗ FAILED\033[0m"
            
            print(f"\n{category}: {status}")
            print(f"  Tests Run: {stats['tests_run']}")
            print(f"  Successes: {stats['success_count']}")
            print(f"  Failures: {stats['failures']}")
            print(f"  Errors: {stats['errors']}")
            print(f"  Skipped: {stats['skipped']}")
            print(f"  Duration: {stats['duration']:.2f}s")
        
        # Overall summary
        print(f"\n\033[1mOVERALL RESULTS:\033[0m")
        print(f"  Total Tests: {total_tests}")
        print(f"  Successes: {total_success}")
        print(f"  Failures: {total_failures}")
        print(f"  Errors: {total_errors}")
        print(f"  Skipped: {total_skipped}")
        print(f"  Total Duration: {total_duration:.2f}s")
        
        # Success rate
        if total_tests > 0:
            success_rate = (total_success / total_tests) * 100
            if success_rate == 100:
                print(f"  Success Rate: \033[92m{success_rate:.1f}%\033[0m")
            elif success_rate >= 80:
                print(f"  Success Rate: \033[93m{success_rate:.1f}%\033[0m")
            else:
                print(f"  Success Rate: \033[91m{success_rate:.1f}%\033[0m")
        
        # Final status
        if total_failures == 0 and total_errors == 0:
            print(f"\n\033[92m🎉 ALL TESTS PASSED!\033[0m")
            print(f"\033[92m✅ Alpha Detector Phase 1.6 Test Suite Complete\033[0m")
        else:
            print(f"\n\033[91m❌ SOME TESTS FAILED\033[0m")
            print(f"\033[91m⚠️  Please review failures and errors above\033[0m")
        
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\033[96m{'='*80}\033[0m")


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(
        description='Alpha Detector Comprehensive Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all core tests
  python run_tests.py --all              # Run all tests including legacy
  python run_tests.py --unit             # Run only unit tests
  python run_tests.py --integration      # Run only integration tests
  python run_tests.py --legacy           # Run only legacy tests
  python run_tests.py --specific test_core_detection test_communication
  python run_tests.py --verbose          # Increase verbosity
  python run_tests.py --quiet            # Reduce verbosity
        """
    )
    
    parser.add_argument('--all', action='store_true',
                       help='Run all tests including legacy tests')
    parser.add_argument('--unit', action='store_true',
                       help='Run only unit tests')
    parser.add_argument('--integration', action='store_true',
                       help='Run only integration tests')
    parser.add_argument('--legacy', action='store_true',
                       help='Run only legacy tests')
    parser.add_argument('--specific', nargs='+', metavar='TEST_MODULE',
                       help='Run specific test modules')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Increase verbosity')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Reduce verbosity')
    
    args = parser.parse_args()
    
    # Determine verbosity
    verbosity = 2  # Default
    if args.verbose:
        verbosity = 3
    elif args.quiet:
        verbosity = 1
    
    # Create test runner
    runner = TestRunner(verbosity=verbosity)
    
    try:
        if args.specific:
            # Run specific tests
            runner.run_specific_tests(args.specific)
        elif args.unit:
            # Run only unit tests
            runner.run_test_category('Unit Tests', UNIT_TESTS)
        elif args.integration:
            # Run only integration tests
            runner.run_test_category('Integration Tests', INTEGRATION_TESTS)
        elif args.legacy:
            # Run only legacy tests
            runner.run_legacy_tests()
        elif args.all:
            # Run all tests including legacy
            runner.run_all_tests()
            runner.run_legacy_tests()
        else:
            # Default: Run core tests (unit + integration)
            runner.run_all_tests()
        
        # Generate final summary if we have results
        if runner.results and not (args.unit or args.integration or args.specific):
            # Summary already generated in run_all_tests
            pass
        elif runner.results:
            # Generate summary for partial runs
            total_duration = sum(stats['duration'] for stats in runner.results.values())
            runner.generate_summary_report(total_duration)
    
    except KeyboardInterrupt:
        print(f"\n\033[93m⚠️  Test run interrupted by user\033[0m")
        return 1
    except Exception as e:
        print(f"\n\033[91m❌ Test run failed with error: {e}\033[0m")
        return 1
    
    # Return exit code based on test results
    if runner.results:
        for stats in runner.results.values():
            if stats['failures'] > 0 or stats['errors'] > 0:
                return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

