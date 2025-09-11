#!/usr/bin/env python3
"""
Raw Data Intelligence Test Runner

Simple test runner for raw data intelligence comprehensive tests.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_raw_data_intelligence import main

if __name__ == "__main__":
    print("🚀 Starting Raw Data Intelligence Tests...")
    try:
        asyncio.run(main())
        print("✅ All tests completed successfully!")
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        sys.exit(1)

