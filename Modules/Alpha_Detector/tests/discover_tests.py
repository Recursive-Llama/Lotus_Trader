#!/usr/bin/env python3
"""
Test Discovery Script for Alpha Detector
Phase 1.6.3: Test Discovery and Organization
"""

import sys
import os
import unittest
import importlib
from pathlib import Path

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


def discover_all_tests():
    """Discover all available tests in the tests directory"""
    tests_dir = Path(__file__).parent
    test_modules = []
    
    # Find all Python test files
    for test_file in tests_dir.glob('test_*.py'):
        if test_file.name != '__init__.py':
            module_name = test_file.stem
            test_modules.append(module_name)
    
    return sorted(test_modules)


def discover_tests_by_category():
    """Discover tests organized by category"""
    from tests import UNIT_TESTS, INTEGRATION_TESTS, LEGACY_TESTS
    
    categories = {
        'Unit Tests': UNIT_TESTS,
        'Integration Tests': INTEGRATION_TESTS,
        'Legacy Tests': LEGACY_TESTS
    }
    
    return categories


def get_test_info(module_name):
    """Get information about a specific test module"""
    try:
        module = importlib.import_module(f'tests.{module_name}')
        
        # Get test classes
        test_classes = []
        for name, obj in vars(module).items():
            if (isinstance(obj, type) and 
                issubclass(obj, unittest.TestCase) and 
                obj != unittest.TestCase):
                test_classes.append(name)
        
        # Get test methods
        test_methods = []
        for test_class in test_classes:
            class_obj = getattr(module, test_class)
            methods = [method for method in dir(class_obj) 
                      if method.startswith('test_')]
            test_methods.extend(methods)
        
        return {
            'module': module_name,
            'test_classes': test_classes,
            'test_methods': test_methods,
            'total_tests': len(test_methods)
        }
    
    except ImportError as e:
        return {
            'module': module_name,
            'error': str(e),
            'test_classes': [],
            'test_methods': [],
            'total_tests': 0
        }


def print_test_discovery_report():
    """Print a comprehensive test discovery report"""
    print("🔍 ALPHA DETECTOR TEST DISCOVERY REPORT")
    print("=" * 60)
    
    # Discover all tests
    all_tests = discover_all_tests()
    print(f"\n📁 Found {len(all_tests)} test modules:")
    for test in all_tests:
        print(f"  - {test}")
    
    # Discover by category
    categories = discover_tests_by_category()
    print(f"\n📊 Test Categories:")
    for category, tests in categories.items():
        print(f"\n{category}:")
        for test in tests:
            info = get_test_info(test)
            if 'error' in info:
                print(f"  ❌ {test}: {info['error']}")
            else:
                print(f"  ✅ {test}: {info['total_tests']} tests")
    
    # Detailed test information
    print(f"\n📋 Detailed Test Information:")
    print("-" * 60)
    
    for test in all_tests:
        info = get_test_info(test)
        print(f"\n{test}:")
        if 'error' in info:
            print(f"  Error: {info['error']}")
        else:
            print(f"  Test Classes: {len(info['test_classes'])}")
            for test_class in info['test_classes']:
                print(f"    - {test_class}")
            print(f"  Test Methods: {len(info['test_methods'])}")
            for method in info['test_methods'][:5]:  # Show first 5
                print(f"    - {method}")
            if len(info['test_methods']) > 5:
                print(f"    ... and {len(info['test_methods']) - 5} more")
    
    # Summary
    total_tests = sum(info['total_tests'] for test in all_tests 
                     for info in [get_test_info(test)] 
                     if 'error' not in info)
    
    print(f"\n📈 SUMMARY:")
    print(f"  Total Test Modules: {len(all_tests)}")
    print(f"  Total Test Methods: {total_tests}")
    print(f"  Categories: {len(categories)}")


def main():
    """Main discovery function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--detailed':
        print_test_discovery_report()
    else:
        # Simple discovery
        all_tests = discover_all_tests()
        print("Available test modules:")
        for test in all_tests:
            print(f"  - {test}")
        print(f"\nTotal: {len(all_tests)} test modules")
        print("\nRun with --detailed for full report")


if __name__ == '__main__':
    main()

