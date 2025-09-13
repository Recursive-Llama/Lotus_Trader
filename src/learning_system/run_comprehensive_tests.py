#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner
Orchestrates all comprehensive functionality and quality tests
"""

import sys
import os
import asyncio
import time
from datetime import datetime
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

class ComprehensiveTestRunner:
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    async def run_all_tests(self):
        """Run all comprehensive tests"""
        print("🚀 COMPREHENSIVE TEST SUITE RUNNER")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        self.start_time = time.time()
        
        # Test modules
        test_modules = [
            ("LLM Response Quality", "test_llm_response_quality"),
            ("Real Workflow Validation", "test_real_workflow_validation"),
            ("Comprehensive Functionality", "test_comprehensive_functionality")
        ]
        
        for test_name, test_module in test_modules:
            print(f"\n{'='*60}")
            print(f"🧪 RUNNING: {test_name}")
            print(f"{'='*60}")
            
            try:
                # Import and run the test module
                module = __import__(test_module)
                if hasattr(module, 'main'):
                    success = await module.main()
                    self.test_results[test_name] = {
                        "success": success,
                        "error": None
                    }
                else:
                    print(f"❌ {test_name}: No main() function found")
                    self.test_results[test_name] = {
                        "success": False,
                        "error": "No main() function found"
                    }
            except Exception as e:
                print(f"❌ {test_name}: Failed with exception: {e}")
                traceback.print_exc()
                self.test_results[test_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        self.end_time = time.time()
        self.print_final_summary()
        
        return self._overall_success()
    
    def print_final_summary(self):
        """Print final comprehensive summary"""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE TEST SUITE FINAL SUMMARY")
        print("="*80)
        
        total_duration = self.end_time - self.start_time
        
        print(f"Test Duration: {total_duration:.2f} seconds")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*80)
        
        passed_tests = 0
        failed_tests = 0
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            error_info = f" - {result['error']}" if result["error"] else ""
            print(f"{test_name}: {status}{error_info}")
            
            if result["success"]:
                passed_tests += 1
            else:
                failed_tests += 1
        
        print("-"*80)
        print(f"TOTAL: {passed_tests} passed, {failed_tests} failed")
        
        if failed_tests == 0:
            print("🎉 ALL COMPREHENSIVE TESTS PASSED!")
            print("✅ System is ready for production deployment")
        else:
            print("⚠️  SOME TESTS FAILED!")
            print("❌ Review and fix issues before deployment")
        
        print("="*80)
    
    def _overall_success(self):
        """Determine overall test success"""
        return all(result["success"] for result in self.test_results.values())

async def main():
    """Main entry point"""
    runner = ComprehensiveTestRunner()
    success = await runner.run_all_tests()
    
    if success:
        print("\n🎯 All comprehensive tests completed successfully!")
        return 0
    else:
        print("\n💥 Some comprehensive tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
