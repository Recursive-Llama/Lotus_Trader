#!/usr/bin/env python3
"""
Simple pytest-based test runner for EVM trading tests
"""

import pytest
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_evm_tests():
    """Run EVM trading tests"""
    test_files = [
        'test_evm_uniswap_client_base.py',
        'test_evm_uniswap_client_eth.py', 
        'test_trader_evm_decision.py'
    ]
    
    # Convert to full paths
    test_paths = [os.path.join(os.path.dirname(__file__), f) for f in test_files]
    
    # Run pytest
    pytest_args = [
        '-v',  # verbose
        '--tb=short',  # short traceback
        '--disable-warnings',  # disable warnings
    ] + test_paths
    
    return pytest.main(pytest_args)

if __name__ == "__main__":
    exit_code = run_evm_tests()
    sys.exit(exit_code)
