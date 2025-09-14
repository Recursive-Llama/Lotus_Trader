#!/usr/bin/env python3
"""
CIL Test Runner

This script runs the CIL core features test to validate the system.
"""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from test_cil_core_features import CILCoreFeaturesTester

async def main():
    """Run the CIL core features test"""
    print("🚀 Starting CIL Core Features Test")
    print("=" * 50)
    
    try:
        tester = CILCoreFeaturesTester()
        await tester.run_core_features_test()
        print("\n🎉 Test completed successfully!")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

