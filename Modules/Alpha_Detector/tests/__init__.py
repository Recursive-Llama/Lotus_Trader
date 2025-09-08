"""
Alpha Detector Test Suite
Phase 1.6: Basic Test Suite Implementation

This package contains comprehensive tests for the Alpha Detector module:

Unit Tests:
- test_core_detection.py: Core detection components
- test_trading_plan_generation.py: Trading plan generation system

Integration Tests:
- test_communication.py: Inter-module communication
- test_end_to_end.py: Complete system integration

Legacy Tests:
- test_phase1_3_comprehensive.py: Phase 1.3 comprehensive tests
- test_phase1_3_final.py: Phase 1.3 final validation
- Other component-specific tests

Usage:
    # Run all tests
    python -m unittest discover tests

    # Run specific test category
    python -m unittest tests.test_core_detection
    python -m unittest tests.test_communication

    # Run with test runner
    python tests/run_tests.py
"""

__version__ = "1.0.0"
__author__ = "Alpha Detector Team"

# Test categories for organization
UNIT_TESTS = [
    'test_core_detection',
    'test_trading_plan_generation'
]

INTEGRATION_TESTS = [
    'test_communication', 
    'test_end_to_end'
]

LEGACY_TESTS = [
    'test_phase1_3_comprehensive',
    'test_phase1_3_final',
    'test_signal_processor',
    'test_supabase_client',
    'test_database_operations',
    'test_multi_timeframe',
    'test_all_timeframes',
    'test_mini_section_1',
    'test_phase1_2'
]

ALL_TESTS = UNIT_TESTS + INTEGRATION_TESTS + LEGACY_TESTS

